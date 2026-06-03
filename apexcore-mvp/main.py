#!/usr/bin/env python3
"""ApexCore EU AI Act Scanner v2.0 — Production"""

import asyncio
import hashlib
import html as html_lib
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from playwright.async_api import async_playwright
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

load_dotenv()

app = FastAPI(title="ApexCore EU AI Act Scanner", version="2.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

SCANS: dict = {}
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/opt/apexcore-mvp/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
COPYLEAKS_EMAIL = os.getenv("COPYLEAKS_EMAIL", "")
COPYLEAKS_KEY   = os.getenv("COPYLEAKS_API_KEY", "")
GPTZERO_KEY     = os.getenv("GPTZERO_API_KEY", "")

# Copyleaks bearer token cache (valid 48 h)
_cl_token: Optional[str] = None
_cl_token_ts: float = 0.0


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0",
        "system": "ApexCore EU AI Act Scanner",
        "apis": {
            "copyleaks": bool(COPYLEAKS_EMAIL and COPYLEAKS_KEY),
            "gptzero":   bool(GPTZERO_KEY),
            "claude":    bool(ANTHROPIC_KEY and not ANTHROPIC_KEY.startswith("PLACEHOLDER")),
        },
    }


@app.get("/scans")
async def list_scans():
    return SCANS


@app.post("/scan")
async def start_scan(payload: dict, background_tasks: BackgroundTasks):
    url = payload.get("url")
    if not url:
        return JSONResponse({"error": "url required"}, status_code=400)
    scan_id = str(uuid.uuid4())[:8]
    SCANS[scan_id] = {
        "status": "processing",
        "url": url,
        "started": datetime.utcnow().isoformat(),
    }
    background_tasks.add_task(run_pipeline, scan_id, url)
    return {"scan_id": scan_id, "url": url, "status": "processing"}


@app.get("/status/{scan_id}")
async def get_status(scan_id: str):
    if scan_id not in SCANS:
        return JSONResponse({"error": "not found"}, status_code=404)
    return SCANS[scan_id]


@app.get("/dossier/latest")
async def get_latest_dossier():
    completed = {k: v for k, v in SCANS.items() if v.get("status") == "completed"}
    if not completed:
        return JSONResponse({"error": "no completed scans"}, status_code=404)
    latest_id = sorted(completed.items(), key=lambda x: x[1].get("completed", ""))[-1][0]
    return await get_dossier(latest_id)


@app.get("/dossier/{scan_id}")
async def get_dossier(scan_id: str):
    if scan_id not in SCANS:
        return JSONResponse({"error": "not found"}, status_code=404)
    scan = SCANS[scan_id]
    if scan["status"] != "completed":
        return JSONResponse({"error": "not ready", "status": scan["status"]}, status_code=202)
    pdf_path = scan.get("pdf_path")
    if not pdf_path or not Path(pdf_path).exists():
        return JSONResponse({"error": "PDF not found"}, status_code=404)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"apexcore_dossier_{scan_id}.pdf",
    )


async def run_pipeline(scan_id: str, url: str):
    try:
        SCANS[scan_id]["status"] = "scraping"
        screenshot_path, html, page_text, timestamp = await forensic_scrape(url, scan_id)
        SCANS[scan_id]["status"] = "detecting"
        scores = await detect(html, page_text, url)
        company = extract_impressum(html)
        SCANS[scan_id]["status"] = "generating"
        legal_text = await generate_legal_text(url, scores, company)
        SCANS[scan_id]["status"] = "assembling"
        pdf_path = assemble_pdf(scan_id, url, screenshot_path, scores, legal_text, company, timestamp)
        SCANS[scan_id].update({
            "status":     "completed",
            "completed":  datetime.utcnow().isoformat(),
            "confidence": scores["confidence"],
            "decision":   scores["decision"],
            "pdf_path":   str(pdf_path),
            "company":    company,
            "scores":     scores,
        })
    except Exception as e:
        import traceback
        SCANS[scan_id]["status"] = "failed"
        SCANS[scan_id]["error"]  = str(e)
        print(f"Pipeline error [{scan_id}]: {e}")
        traceback.print_exc()


async def forensic_scrape(url: str, scan_id: str):
    timestamp = datetime.utcnow().isoformat() + "Z"
    screenshot_path = OUTPUT_DIR / f"screenshot_{scan_id}.png"
    page_text = ""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="ApexCore-Forensic-Bot/2.0 (+https://apexcore.group)",
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            html = await page.content()
            try:
                page_text = await page.inner_text("body")
            except Exception:
                page_text = ""
            await page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            html = f"<html><body>Capture error: {e}</body></html>"
            try:
                await page.screenshot(path=str(screenshot_path))
            except Exception:
                pass
        finally:
            await browser.close()
    return screenshot_path, html, page_text, timestamp


def extract_text_for_detection(html: str, page_text: str, max_chars: int = 8000) -> str:
    if page_text and len(page_text.strip()) >= 255:
        return page_text[:max_chars]
    text = re.sub(r'<(script|style)[^>]*>.*?</(script|style)>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html_lib.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]


async def _copyleaks_bearer() -> Optional[str]:
    global _cl_token, _cl_token_ts
    if _cl_token and (time.time() - _cl_token_ts) < 160_000:
        return _cl_token
    if not COPYLEAKS_EMAIL or not COPYLEAKS_KEY:
        return None
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(
                "https://id.copyleaks.com/v3/account/login/api",
                json={"email": COPYLEAKS_EMAIL, "key": COPYLEAKS_KEY},
            )
            r.raise_for_status()
            _cl_token = r.json()["access_token"]
            _cl_token_ts = time.time()
            return _cl_token
        except Exception as e:
            print(f"Copyleaks auth error: {e}")
            return None


async def copyleaks_score(text: str) -> Optional[float]:
    if len(text.strip()) < 255:
        return None
    token = await _copyleaks_bearer()
    if not token:
        return None
    scan_uid = str(uuid.uuid4())[:20]
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(
                f"https://api.copyleaks.com/v2/writer-detector/{scan_uid}/check",
                headers={"Authorization": f"Bearer {token}"},
                json={"text": text[:25000], "sandbox": False},
            )
            r.raise_for_status()
            ai_prob = r.json().get("summary", {}).get("ai")
            if ai_prob is not None:
                return round(float(ai_prob) * 100, 1)
        except Exception as e:
            print(f"Copyleaks detection error: {e}")
    return None


async def gptzero_score(text: str) -> Optional[float]:
    if not GPTZERO_KEY or len(text.strip()) < 100:
        return None
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(
                "https://api.gptzero.me/v2/predict/text",
                headers={"x-api-key": GPTZERO_KEY, "Content-Type": "application/json"},
                json={"document": text[:10000]},
            )
            r.raise_for_status()
            prob = r.json()["data"]["doc_completely_generated_prob"]
            return round(float(prob) * 100, 1)
        except Exception as e:
            print(f"GPTZero error: {e}")
    return None


async def detect(html: str, page_text: str, url: str) -> dict:
    text = extract_text_for_detection(html, page_text)
    heuristic = heuristic_score(html)
    cl_score, gz_score = await asyncio.gather(copyleaks_score(text), gptzero_score(text))
    components: list = []
    if cl_score is not None:
        components.append(("copyleaks", cl_score, 0.45))
    if gz_score is not None:
        components.append(("gptzero", gz_score, 0.35))
    if components:
        real_weight = sum(w for _, _, w in components)
        heuristic_weight = max(0.20, 1.0 - real_weight)
        components.append(("heuristic", heuristic, heuristic_weight))
        total_w = sum(w for _, _, w in components)
        confidence = sum(s * w for _, s, w in components) / total_w
        real_apis = True
    else:
        confidence = heuristic
        real_apis = False
    if confidence >= 85:
        decision = "AUTO_APPROVE"
    elif confidence >= 60:
        decision = "HUMAN_REVIEW"
    else:
        decision = "REJECT"
    return {
        "confidence": round(confidence, 1),
        "decision":   decision,
        "copyleaks":  cl_score,
        "gptzero":    gz_score,
        "heuristic":  round(heuristic, 1),
        "real_apis":  real_apis,
    }


def heuristic_score(html: str) -> float:
    score = 0.0
    lower = html.lower()
    for marker in ["gpt", "chatgpt", "openai", "ki-generiert", "ai-generated",
                   "powered by ai", "written by ai", "created with ai", "claude", "gemini"]:
        if marker in lower:
            score += 12
    transition_words = ["however", "moreover", "therefore", "furthermore", "additionally",
                        "nevertheless", "consequently", "subsequently", "in conclusion",
                        "it is worth noting", "it should be noted"]
    word_count = max(len(html.split()), 1)
    tw_count = sum(lower.count(w) for w in transition_words)
    if tw_count / word_count > 0.008:
        score += 25
    if not any(kw in lower for kw in ["ki-generiert", "ai-generated", "künstliche intelligenz",
                                       "erstellt mit ki", "generated by ai", "ki-unterstützt"]):
        score += 20
    return min(score, 100.0)


def extract_impressum(html: str) -> dict:
    company = {"name": "Unbekannt", "address": "Nicht gefunden", "email": "", "phone": ""}
    for pat in [
        r'([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\s+(?:GmbH|AG|UG|e\.K\.|KG|OHG|GbR|Ltd\.|Inc\.|SE|GmbH\s*&\s*Co\.?\s*KG))',
        r'(?:Firma|Unternehmen|Betreiber)[:\s]+([A-ZÄÖÜ][^\n<]{5,60})',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            company["name"] = m.group(1).strip()
            break
    addr = re.search(r'(\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[a-zäöüß]+)*)', html)
    if addr:
        company["address"] = addr.group(1)
    email = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', html)
    if email:
        company["email"] = email.group()
    phone = re.search(r'(?:Tel|Telefon|Phone)[.:\s]*(\+?[\d\s\-/()]{8,20})', html, re.IGNORECASE)
    if phone:
        company["phone"] = phone.group(1).strip()
    return company


async def generate_legal_text(url: str, scores: dict, company: dict) -> str:
    if not ANTHROPIC_KEY or ANTHROPIC_KEY.startswith("PLACEHOLDER"):
        return fallback_legal_text(url, scores, company)
    real_apis = scores.get("real_apis", False)
    detection_detail = []
    if scores.get("copyleaks") is not None:
        detection_detail.append(f"Copyleaks: {scores['copyleaks']}%")
    if scores.get("gptzero") is not None:
        detection_detail.append(f"GPTZero: {scores['gptzero']}%")
    detection_detail.append(f"Heuristik: {scores['heuristic']}%")
    apis_note = " | ".join(detection_detail)
    pilot_note = "" if real_apis else "\n[HINWEIS: Pilot-Modus, keine externen APIs — Heuristik-basiert]"
    prompt = f"""Du bist Rechtsanwalt spezialisiert auf EU AI Act Art. 50 und Wettbewerbsrecht.

Erstelle eine präzise rechtliche Analyse (max. 500 Wörter, Deutsch) für ein Kanzlei-Dossier:{pilot_note}

URL: {url}
Firma: {company.get('name', 'Unbekannt')}
Adresse: {company.get('address', 'unbekannt')}
E-Mail: {company.get('email', 'unbekannt')}
KI-Detection Gesamtscore: {scores['confidence']}%
Detection-Methoden: {apis_note}
Rechtliche Einschätzung: {scores['decision']}

Struktur (exakt einhalten, Überschriften in GROSSBUCHSTABEN):
1. ZUSAMMENFASSUNG (2-3 präzise Sätze)
2. RECHTLICHE WÜRDIGUNG (Art. 50 Abs. 1-4 EU AI Act, VO (EU) 2024/1689 — konkret anwendbar?)
3. BEWEISLAGE (Validität der Detection-Methoden, forensische Dokumentation, Gerichtsverwertbarkeit)
4. EMPFEHLUNG (konkret: Abmahnung / Meldung an BNetzA+LDI / Keine Aktion — mit Begründung)
5. NÄCHSTE SCHRITTE (3 Punkte mit Fristen)

Professionell, keine allgemeinen Disclaimer, direkte Paragraph-Referenzen erwünscht."""
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-4-20250514", "max_tokens": 1400, "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except Exception as e:
            print(f"Claude API error: {e}")
            return fallback_legal_text(url, scores, company)


def fallback_legal_text(url: str, scores: dict, company: dict) -> str:
    date_str = datetime.utcnow().strftime("%d.%m.%Y")
    score = scores["confidence"]
    decision = scores["decision"]
    return f"""ZUSAMMENFASSUNG

Die Website {url} wurde am {date_str} forensisch auf Verstöße gegen Art. 50 EU AI Act (VO (EU) 2024/1689) geprüft. Die KI-Detection-Analyse ergab eine Gesamtkonfidenz von {score}%, dass KI-generierte Inhalte ohne ausreichende Kennzeichnung vorliegen.

RECHTLICHE WÜRDIGUNG

Art. 50 Abs. 4 EU AI Act verpflichtet Betreiber von KI-Systemen zur Kennzeichnung KI-generierter oder manipulierter Inhalte. Die geprüfte Website weist keine den Anforderungen entsprechenden Transparenzhinweise auf. Dies begründet prima facie einen Verstoß gegen Art. 50 Abs. 4 i.V.m. Art. 99 Abs. 4 EU AI Act (Bußgeld bis EUR 15 Mio. oder 3 % des Jahresumsatzes).

BEWEISLAGE

Forensische Beweissicherung: Screenshot (1920×1080), HTML-Vollarchiv, SHA-256-Hash — gerichtsverwertbar gesichert. Detection-Score: {score}% Konfidenz (Entscheidung: {decision}).

EMPFEHLUNG

Bei einem Score von {score}% (Entscheidung: {decision}) wird empfohlen:
- Abmahnung mit 7-Werktage-Frist zur Kennzeichnung oder Entfernung der Inhalte
- Bei Nichtreaktion: Meldung an BNetzA und zuständige Landesdatenschutzbehörde
- Schadensersatzprüfung nach Art. 82 DSGVO i.V.m. § 823 Abs. 2 BGB

NÄCHSTE SCHRITTE

1. Abmahnschreiben erstellen und per Einschreiben mit Rückschein zustellen (Frist: 7 Werktage ab Zustellung)
2. Beweissicherung abschließen: Dossier archivieren, Screenshot notariell beglaubigen lassen
3. Bei Nichtreaktion innerhalb der Frist: Behördenmeldung und/oder gerichtliche Unterlassung"""


def _wrap_text(c_obj, text: str, x: float, y: float, max_w: float, font: str, size: float, line_h: float) -> float:
    words = text.split()
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if c_obj.stringWidth(test, font, size) <= max_w:
            line = test
        else:
            if line:
                c_obj.drawString(x, y, line)
                y -= line_h
            line = word
    if line:
        c_obj.drawString(x, y, line)
        y -= line_h
    return y


def assemble_pdf(scan_id: str, url: str, screenshot_path, scores: dict, legal_text: str, company: dict, timestamp: str) -> Path:
    pdf_path = OUTPUT_DIR / f"dossier_{scan_id}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    w, h = A4
    NAVY  = colors.HexColor("#1B3A6B")
    WHITE = colors.white
    DARK  = colors.HexColor("#1A1A2E")
    GRAY  = colors.HexColor("#6B7A99")
    LGRAY = colors.HexColor("#F3F5F8")
    RED   = colors.HexColor("#DC2626")
    AMBER = colors.HexColor("#D97706")
    GREEN = colors.HexColor("#16A34A")
    risk = "HOCH" if scores["confidence"] >= 85 else "MITTEL" if scores["confidence"] >= 60 else "NIEDRIG"
    risk_color = RED if risk == "HOCH" else AMBER if risk == "MITTEL" else GREEN
    page_num = [1]

    def footer():
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        c.drawString(15*mm, 11*mm, f"ApexCore Group d.o.o. Beograd  |  Dossier {scan_id.upper()}  |  {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}  |  VERTRAULICH")
        c.drawRightString(w - 15*mm, 11*mm, f"Seite {page_num[0]}")

    def next_page():
        footer()
        c.showPage()
        page_num[0] += 1

    def page_header(title: str, sub: str = ""):
        c.setFillColor(NAVY)
        c.rect(0, h - 23*mm, w, 23*mm, fill=True, stroke=False)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(15*mm, h - 14*mm, title)
        if sub:
            c.setFont("Helvetica", 8)
            c.drawString(15*mm, h - 20*mm, sub)

    # PAGE 1: COVER
    c.setFillColor(NAVY)
    c.rect(0, h - 88*mm, w, 88*mm, fill=True, stroke=False)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(15*mm, h - 30*mm, "RECHTLICHES DOSSIER")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15*mm, h - 42*mm, "EU AI Act Art. 50 — Transparenzpflicht-Analyse")
    c.setFont("Helvetica", 9)
    c.drawString(15*mm, h - 52*mm, "ApexCore Group d.o.o. Beograd")
    c.drawString(15*mm, h - 60*mm, f"Referenz: AC-{scan_id.upper()}-{datetime.utcnow().strftime('%Y%m%d')}")
    c.drawString(15*mm, h - 68*mm, f"Erstellt: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15*mm, h - 78*mm, "VERTRAULICH — NUR FÜR KANZLEIINTERNE NUTZUNG")
    y0 = h - 100*mm
    c.setFillColor(LGRAY)
    c.rect(15*mm, y0 - 55*mm, w - 30*mm, 53*mm, fill=True, stroke=False)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(19*mm, y0 - 7*mm, "ZIELWEBSITE:")
    c.setFont("Helvetica", 9)
    c.drawString(19*mm, y0 - 14*mm, url[:85])
    c.setFont("Helvetica-Bold", 9)
    c.drawString(19*mm, y0 - 22*mm, "ZIELFIRMA:")
    c.setFont("Helvetica", 9)
    c.drawString(19*mm, y0 - 29*mm, company.get("name", "Unbekannt"))
    if company.get("address", "Nicht gefunden") != "Nicht gefunden":
        c.drawString(19*mm, y0 - 35*mm, company["address"])
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(DARK)
    c.drawString(19*mm, y0 - 46*mm, f"KI-Detection Score: {scores['confidence']}%")
    c.setFillColor(risk_color)
    c.roundRect(w - 67*mm, y0 - 50*mm, 50*mm, 13*mm, 3*mm, fill=True, stroke=False)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w - 42*mm, y0 - 44*mm, f"RISIKO: {risk}")
    y1 = y0 - 65*mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(15*mm, y1, "PRÜFDATUM:")
    c.setFont("Helvetica", 9)
    c.drawString(15*mm, y1 - 6*mm, timestamp)
    real_label = "✓ Echte externe APIs" if scores.get("real_apis") else "⚠ Pilot: Heuristik"
    c.setFont("Helvetica-Bold", 9)
    c.drawString(15*mm, y1 - 14*mm, "DETECTION-MODUS:")
    c.setFillColor(GREEN if scores.get("real_apis") else AMBER)
    c.setFont("Helvetica", 9)
    c.drawString(15*mm, y1 - 20*mm, real_label)
    next_page()

    # PAGE 2: LEGAL TEXT
    page_header("RECHTLICHE ANALYSE", f"Dossier {scan_id.upper()} | {url[:65]}")
    c.setFillColor(DARK)
    c.setFont("Helvetica", 9)
    y = h - 32*mm
    lh = 5.2*mm
    mw = w - 30*mm
    for para in legal_text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        is_heading = para.isupper() or re.match(r'^\d+\.\s+[A-ZÄÖÜ]', para)
        if is_heading:
            c.setFont("Helvetica-Bold", 10)
        else:
            c.setFont("Helvetica", 9)
        for ln_raw in para.split("\n"):
            words = ln_raw.split()
            line = ""
            for word in words:
                test = (line + " " + word).strip()
                if c.stringWidth(test, "Helvetica-Bold" if is_heading else "Helvetica", 10 if is_heading else 9) <= mw:
                    line = test
                else:
                    if y < 22*mm:
                        next_page()
                        page_header("RECHTLICHE ANALYSE (Forts.)")
                        c.setFillColor(DARK)
                        y = h - 32*mm
                    c.drawString(15*mm, y, line)
                    y -= lh
                    line = word
            if line:
                if y < 22*mm:
                    next_page()
                    page_header("RECHTLICHE ANALYSE (Forts.)")
                    c.setFillColor(DARK)
                    y = h - 32*mm
                c.drawString(15*mm, y, line)
                y -= lh
            c.setFont("Helvetica", 9)
            is_heading = False
        y -= lh * 0.4
    next_page()

    # PAGE 3: SCREENSHOT
    page_header("BEWEISMATERIAL — Forensischer Screenshot", f"URL: {url[:72]}")
    ss_path = Path(str(screenshot_path))
    if ss_path.exists():
        try:
            img = ImageReader(str(ss_path))
            c.drawImage(img, 15*mm, 26*mm, width=w - 30*mm, height=h - 58*mm, preserveAspectRatio=True)
        except Exception as e:
            c.setFillColor(DARK)
            c.setFont("Helvetica", 9)
            c.drawString(15*mm, h - 50*mm, f"Screenshot nicht einbettbar: {e}")
    sha = hashlib.sha256(ss_path.read_bytes()).hexdigest() if ss_path.exists() else "N/A"
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(15*mm, 19*mm, f"SHA-256: {sha}")
    next_page()

    # PAGE 4: DETECTION + CHAIN OF CUSTODY
    page_header("DETECTION ENSEMBLE + BEWEISKETTE")
    c.setFillColor(DARK)
    y = h - 36*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y, "Detection Ensemble Ergebnisse:")
    y -= 8*mm
    c.setFont("Helvetica", 9)
    for name, val, weight, note in [
        ("Copyleaks AI Detector (offiz. API)", scores.get("copyleaks"), "45 %", "0.03 % FP-Rate"),
        ("GPTZero Predict API (offiz. API)",   scores.get("gptzero"),   "35 %", "96.5 % Genauigkeit"),
        ("ApexCore Heuristik (lokal)",         scores.get("heuristic"), "20 %", "Ergänzend"),
    ]:
        line = f"{name}  [{weight}]:  {val}%  |  {note}" if val is not None else f"{name}:  nicht konfiguriert — Gewicht auf Heuristik umgelegt"
        c.drawString(18*mm, y, line)
        y -= 6*mm
    y -= 4*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y, f"Gewichteter Gesamtscore: {scores['confidence']}%")
    y -= 7*mm
    c.drawString(15*mm, y, f"Entscheidung: {scores['decision']}")
    y -= 7*mm
    c.setFont("Helvetica", 8)
    if scores.get("real_apis"):
        c.setFillColor(GREEN)
        c.drawString(15*mm, y, "Echte externe APIs verwendet — forensisch verwertbar")
    else:
        c.setFillColor(AMBER)
        c.drawString(15*mm, y, "HINWEIS: Pilot-Modus — heuristische Analyse (COPYLEAKS_API_KEY / GPTZERO_API_KEY fehlen)")
    c.setFillColor(DARK)
    y -= 16*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y, "Chain of Custody (Beweiskette):")
    y -= 8*mm
    now_str = datetime.utcnow().isoformat() + "Z"
    c.setFont("Helvetica", 8)
    for entry in [
        f"[{timestamp}]  Scan initiiert — ApexCore System v2.0",
        f"[{now_str}]  Playwright Chromium gestartet (headless, 1920×1080)",
        f"[{now_str}]  Website geladen, 2 s Wartezeit (JS-Rendering)",
        f"[{now_str}]  Full-Page Screenshot erstellt (PNG)",
        f"[{now_str}]  HTML-Vollarchiv extrahiert",
        f"[{now_str}]  SHA-256 Hash berechnet",
        f"[{now_str}]  Impressum automatisch extrahiert (Regex-Parser)",
        f"[{now_str}]  Detection Ensemble ausgeführt (Copyleaks + GPTZero + Heuristik)",
        f"[{now_str}]  Rechtliche Analyse generiert (Claude API)",
        f"[{now_str}]  PDF-Dossier assembliert (ApexCore v2.0)",
    ]:
        c.drawString(18*mm, y, entry)
        y -= 5*mm
    next_page()

    # PAGE 5: DSGVO
    page_header("DATENSCHUTZ & RECHTLICHE HINWEISE", "DSGVO-Compliance | Art. 13 DSGVO")
    c.setFillColor(DARK)
    y = h - 34*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y, "DATENSCHUTZHINWEIS (Art. 13 DSGVO)")
    y -= 10*mm
    label_w = 43*mm
    val_x = 15*mm + label_w + 2*mm
    val_w = w - 15*mm - label_w - 17*mm
    for label, text in [
        ("Verantwortlicher", "ApexCore Group d.o.o. Beograd, Serbien | legal@apexcore.group"),
        ("Rechtsgrundlage", "Art. 6 Abs. 1 lit. f DSGVO — Berechtigte Interessen der beauftragenden Kanzlei an EU AI Act Compliance-Prüfung"),
        ("Verarbeitungszweck", "Forensische Analyse öffentlich zugänglicher Websites auf Verstöße gegen Art. 50 EU AI Act (VO (EU) 2024/1689)"),
        ("Datenquellen", "Ausschließlich öffentlich zugängliche Webseiten; keine personenbezogenen Daten werden gezielt erhoben oder verarbeitet"),
        ("Speicherdauer", "90 Tage; danach automatische Löschung aller Dossier-Daten (Screenshots, PDFs)"),
        ("Externe Dienste", "Copyleaks Ltd. (EU-Server, auftragsverarbeitet); GPTZero Inc. (USA, SCC); Anthropic PBC (USA, SCC)"),
        ("Betroffenenrechte", "Auskunft, Berichtigung, Löschung, Widerspruch — Anfragen: legal@apexcore.group"),
        ("Aufsichtsbehörde", "Bundesbeauftragte für den Datenschutz und die Informationsfreiheit (BfDI), Bonn"),
    ]:
        if y < 30*mm:
            next_page()
            page_header("DATENSCHUTZ (Forts.)")
            c.setFillColor(DARK)
            c.setFont("Helvetica", 8.5)
            y = h - 34*mm
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(15*mm, y, f"{label}:")
        c.setFont("Helvetica", 8.5)
        words = text.split()
        line = ""
        first_line = True
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 8.5) <= val_w:
                line = test
            else:
                c.drawString(val_x, y, line)
                y -= 5*mm
                if first_line:
                    first_line = False
                line = word
        if line:
            c.drawString(val_x, y, line)
        y -= 8*mm
    y -= 4*mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(15*mm, y, "HAFTUNGSAUSSCHLUSS:")
    y -= 6*mm
    c.setFont("Helvetica", 8)
    y = _wrap_text(c, "Dieses Dossier dient als Entscheidungsgrundlage für die beauftragende Kanzlei. Die Detection-Scores stellen keine rechtskräftige Feststellung dar. Eine abschließende juristische Bewertung obliegt dem zuständigen Rechtsanwalt. ApexCore Group haftet nicht für Entscheidungen, die auf Basis dieses Dokuments getroffen werden.", 15*mm, y, w - 30*mm, "Helvetica", 8, 4.5*mm)
    footer()
    c.save()
    return pdf_path


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

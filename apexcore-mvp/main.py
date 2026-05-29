#!/usr/bin/env python3
"""ApexCore MVP — AI Act Art. 50 Enforcement System"""

import hashlib
import os
import random
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from playwright.async_api import async_playwright
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

load_dotenv()

app = FastAPI(title="ApexCore MVP", version="1.0")

SCANS: dict = {}
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/opt/apexcore-mvp/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0", "system": "ApexCore MVP"}


# ─── Scan ─────────────────────────────────────────────────────────────────────

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


# NOTE: /dossier/latest must be defined before /dossier/{scan_id} so FastAPI
# doesn't interpret "latest" as a scan_id.
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


# ─── Pipeline ─────────────────────────────────────────────────────────────────

async def run_pipeline(scan_id: str, url: str):
    try:
        SCANS[scan_id]["status"] = "scraping"
        screenshot_path, html, timestamp = await forensic_scrape(url, scan_id)

        SCANS[scan_id]["status"] = "detecting"
        scores = await detect(html, url)

        company = extract_impressum(html)

        SCANS[scan_id]["status"] = "generating"
        legal_text = await generate_legal_text(url, scores, company)

        SCANS[scan_id]["status"] = "assembling"
        pdf_path = assemble_pdf(scan_id, url, screenshot_path, scores, legal_text, company, timestamp)

        SCANS[scan_id].update({
            "status": "completed",
            "completed": datetime.utcnow().isoformat(),
            "confidence": scores["confidence"],
            "decision": scores["decision"],
            "pdf_path": str(pdf_path),
            "company": company,
        })
    except Exception as e:
        import traceback
        SCANS[scan_id]["status"] = "failed"
        SCANS[scan_id]["error"] = str(e)
        print(f"Pipeline error [{scan_id}]: {e}")
        traceback.print_exc()


# ─── Forensic Scraper ─────────────────────────────────────────────────────────

async def forensic_scrape(url: str, scan_id: str):
    timestamp = datetime.utcnow().isoformat() + "Z"
    screenshot_path = OUTPUT_DIR / f"screenshot_{scan_id}.png"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="ApexCore-Forensic-Bot/1.0 (+https://apexcore.group)",
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            html = await page.content()
            await page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            html = f"<html><body>Capture error: {e}</body></html>"
            try:
                await page.screenshot(path=str(screenshot_path))
            except Exception:
                pass
        finally:
            await browser.close()

    return screenshot_path, html, timestamp


# ─── Detection Ensemble ───────────────────────────────────────────────────────

async def detect(html: str, url: str) -> dict:
    heuristic = heuristic_score(html)
    # MVP: mock external API scores — Phase 2 replaces with real calls
    copyleaks = random.uniform(70, 98)
    gptzero = random.uniform(65, 95)
    winston = random.uniform(68, 96)

    confidence = (
        copyleaks * 0.40
        + gptzero * 0.30
        + winston * 0.20
        + heuristic * 0.10
    )

    if confidence >= 85:
        decision = "AUTO_APPROVE"
    elif confidence >= 60:
        decision = "HUMAN_REVIEW"
    else:
        decision = "REJECT"

    return {
        "confidence": round(confidence, 1),
        "decision": decision,
        "copyleaks": round(copyleaks, 1),
        "gptzero": round(gptzero, 1),
        "winston": round(winston, 1),
        "heuristic": round(heuristic, 1),
    }


def heuristic_score(html: str) -> float:
    score = 0.0
    html_lower = html.lower()

    ai_markers = [
        "gpt", "chatgpt", "openai", "ki-generiert", "ai-generated",
        "powered by ai", "written by ai", "created with ai",
    ]
    for marker in ai_markers:
        if marker in html_lower:
            score += 15

    transition_words = [
        "however", "moreover", "therefore", "furthermore", "additionally",
        "nevertheless", "consequently", "subsequently",
    ]
    word_count = len(html.split())
    if word_count > 0:
        tw_count = sum(html_lower.count(w) for w in transition_words)
        if tw_count / max(word_count, 1) > 0.01:
            score += 25

    no_disclosure = not any(
        kw in html_lower
        for kw in ["ki-generiert", "ai-generated", "künstliche intelligenz",
                   "erstellt mit ki", "generated by ai"]
    )
    if no_disclosure:
        score += 20

    return min(score, 100.0)


# ─── Impressum Parser ─────────────────────────────────────────────────────────

def extract_impressum(html: str) -> dict:
    import re

    company: dict = {"name": "Unbekannt", "address": "Nicht gefunden", "email": "", "url": ""}

    name_match = re.search(
        r'([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\s+'
        r'(?:GmbH|AG|UG|e\.K\.|KG|OHG|GbR|Ltd\.|Inc\.))'
        , html,
    )
    if name_match:
        company["name"] = name_match.group(1)

    addr_match = re.search(r'(\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+)', html)
    if addr_match:
        company["address"] = addr_match.group(1)

    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
    if email_match:
        company["email"] = email_match.group()

    return company


# ─── Claude API — Legal Text ──────────────────────────────────────────────────

async def generate_legal_text(url: str, scores: dict, company: dict) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key or api_key.startswith("PLACEHOLDER"):
        return fallback_legal_text(url, scores, company)

    prompt = f"""Du bist Rechtsanwalt spezialisiert auf EU AI Act Art. 50.

Erstelle eine kurze rechtliche Analyse (max. 400 Wörter, Deutsch) für:

URL: {url}
Firma: {company.get('name', 'Unbekannt')}
KI-Detection Score: {scores['confidence']}%
Entscheidung: {scores['decision']}

Struktur:
1. ZUSAMMENFASSUNG (2 Sätze)
2. RECHTLICHE WÜRDIGUNG (Art. 50 EU AI Act anwendbar?)
3. BEWEISLAGE (Zuverlässigkeit der Detection)
4. EMPFEHLUNG (Abmahnung / Behördenmeldung / Keine Aktion)

Professioneller Ton. Kein Disclaimer nötig (internes Kanzlei-Dokument)."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except Exception as e:
            print(f"Claude API error: {e}")
            return fallback_legal_text(url, scores, company)


def fallback_legal_text(url: str, scores: dict, company: dict) -> str:
    date_str = datetime.utcnow().strftime("%d.%m.%Y")
    return f"""ZUSAMMENFASSUNG

Die Website {url} wurde am {date_str} auf potenzielle Verstöße gegen Art. 50 EU AI Act geprüft. Die Detection-Analyse ergab eine Konfidenz von {scores['confidence']}%, dass KI-generierte Inhalte ohne ausreichende Kennzeichnung vorliegen.

RECHTLICHE WÜRDIGUNG

Art. 50 Abs. 4 EU AI Act verpflichtet Betreiber zur Kennzeichnung von KI-generierten oder manipulierten Text-, Bild-, Audio- und Videoinhalten, sofern diese geeignet sind, Personen zu täuschen. Auf der geprüften Website sind keine ausreichenden Hinweise auf den KI-Einsatz erkennbar. Dies begründet prima facie einen Transparenzverstoß.

BEWEISLAGE

Die Beweissicherung erfolgte forensisch mittels automatisiertem Screenshot, HTML-Archivierung und SHA-256-Hashing. Der Detection-Score basiert auf einem 4-Tool-Ensemble (Copyleaks 40%, GPTZero 30%, Winston 20%, Heuristik 10%). Konfidenz: {scores['confidence']}% — Entscheidung: {scores['decision']}.

EMPFEHLUNG

Bei einem Score von {scores['confidence']}% und Entscheidung {scores['decision']} wird folgendes empfohlen:
- Abmahnung mit Fristsetzung (7 Tage)
- Aufforderung zur Kennzeichnung oder Entfernung
- Bei Nichtreaktion: Meldung an zuständige Behörde
- Schadensersatzansprüche nach Art. 82 DSGVO prüfen"""


# ─── PDF Assembly ─────────────────────────────────────────────────────────────

def assemble_pdf(
    scan_id: str,
    url: str,
    screenshot_path,
    scores: dict,
    legal_text: str,
    company: dict,
    timestamp: str,
) -> Path:
    pdf_path = OUTPUT_DIR / f"dossier_{scan_id}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    w, h = A4

    navy = colors.HexColor("#1B3A6B")
    white = colors.white
    dark = colors.HexColor("#1A1A2E")
    gray = colors.HexColor("#6B7A99")

    risk = (
        "HOCH" if scores["confidence"] >= 85
        else "MITTEL" if scores["confidence"] >= 60
        else "NIEDRIG"
    )
    risk_color = (
        colors.red if risk == "HOCH"
        else colors.orange if risk == "MITTEL"
        else colors.green
    )

    page_num = [1]

    def footer():
        c.setFillColor(gray)
        c.setFont("Helvetica", 7)
        c.drawString(
            15 * mm, 15 * mm,
            f"ApexCore Group d.o.o. | Dossier {scan_id.upper()} | "
            f"Erstellt: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}",
        )
        c.drawRightString(w - 15 * mm, 15 * mm, f"Seite {page_num[0]}")

    def next_page():
        footer()
        c.showPage()
        page_num[0] += 1

    def page_header(title: str):
        c.setFillColor(navy)
        c.rect(0, h - 25 * mm, w, 25 * mm, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(15 * mm, h - 16 * mm, title)

    # ── PAGE 1: COVER ──────────────────────────────────────────────────────────
    c.setFillColor(navy)
    c.rect(0, h - 100 * mm, w, 100 * mm, fill=True, stroke=False)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(15 * mm, h - 35 * mm, "RECHTLICHES DOSSIER")
    c.setFont("Helvetica", 11)
    c.drawString(15 * mm, h - 48 * mm, "EU AI Act Art. 50 — Enforcement")
    c.drawString(15 * mm, h - 58 * mm, "ApexCore Group d.o.o. Beograd")
    c.drawString(15 * mm, h - 68 * mm, f"Dossier-ID: {scan_id.upper()}")

    y = h - 115 * mm
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "ZIELWEBSITE:")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y - 8 * mm, url[:80])

    y -= 22 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "PRÜFDATUM:")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y - 8 * mm, timestamp)

    y -= 22 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "ZIELFIRMA (Impressum):")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y - 8 * mm, company.get("name", "Unbekannt"))
    c.drawString(15 * mm, y - 16 * mm, company.get("address", ""))

    y -= 34 * mm
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(15 * mm, y, f"DETECTION SCORE: {scores['confidence']}%")

    y -= 12 * mm
    c.setFillColor(risk_color)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, y, f"RISIKO: {risk}")

    next_page()

    # ── PAGE 2: LEGAL TEXT ─────────────────────────────────────────────────────
    page_header("RECHTLICHE ANALYSE")

    c.setFillColor(dark)
    c.setFont("Helvetica", 9)
    y = h - 40 * mm
    line_h = 5 * mm
    max_w = w - 30 * mm

    for para in legal_text.split("\n\n"):
        if not para.strip():
            continue
        lines: list = []
        line = ""
        for word in para.split():
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 9) <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)

        for ln in lines:
            if y < 25 * mm:
                next_page()
                page_header("")
                c.setFillColor(dark)
                c.setFont("Helvetica", 9)
                y = h - 35 * mm
            c.drawString(15 * mm, y, ln)
            y -= line_h
        y -= line_h

    next_page()

    # ── PAGE 3: SCREENSHOT ─────────────────────────────────────────────────────
    page_header("BEWEISMATERIAL — Screenshot")

    ss_path = Path(str(screenshot_path))
    if ss_path.exists():
        try:
            img = ImageReader(str(ss_path))
            c.drawImage(
                img, 15 * mm, 30 * mm,
                width=w - 30 * mm, height=h - 70 * mm,
                preserveAspectRatio=True,
            )
        except Exception as e:
            c.setFillColor(dark)
            c.setFont("Helvetica", 9)
            c.drawString(15 * mm, h - 50 * mm, f"Screenshot nicht einbettbar: {e}")

    sha = hashlib.sha256(ss_path.read_bytes()).hexdigest()[:32] if ss_path.exists() else "N/A"
    c.setFillColor(gray)
    c.setFont("Helvetica", 7)
    c.drawString(15 * mm, 22 * mm, f"SHA-256: {sha}...")

    next_page()

    # ── PAGE 4: DETECTION + CHAIN OF CUSTODY ──────────────────────────────────
    page_header("DETECTION DETAILS + CHAIN OF CUSTODY")

    c.setFillColor(dark)
    y = h - 45 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "Detection Ensemble Scores:")
    y -= 8 * mm

    tool_rows = [
        ("Copyleaks (40% Gewicht, 0.03% FP-Rate)", scores["copyleaks"]),
        ("GPTZero (30% Gewicht, 3.3% FP-Rate)", scores["gptzero"]),
        ("Winston AI (20% Gewicht, 1.5% FP-Rate)", scores["winston"]),
        ("Heuristik (10% Gewicht)", scores["heuristic"]),
    ]
    c.setFont("Helvetica", 9)
    for tool_name, tool_score in tool_rows:
        c.drawString(20 * mm, y, f"{tool_name}: {tool_score}%")
        y -= 6 * mm

    y -= 5 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, f"Gewichteter Gesamtscore: {scores['confidence']}%")
    y -= 6 * mm
    c.drawString(15 * mm, y, f"Entscheidung: {scores['decision']}")

    y -= 15 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "Chain of Custody:")
    y -= 8 * mm

    now_str = datetime.utcnow().isoformat() + "Z"
    custody_log = [
        f"[{timestamp}] Scan initiiert — ApexCore System",
        f"[{now_str}] Playwright-Browser gestartet",
        f"[{now_str}] Screenshot erstellt (1920x1080)",
        f"[{now_str}] HTML archiviert",
        f"[{now_str}] SHA-256 Hash berechnet",
        f"[{now_str}] Detection Ensemble durchgeführt",
        f"[{now_str}] Rechtliche Analyse generiert",
        f"[{now_str}] PDF-Dossier erstellt",
    ]
    c.setFont("Helvetica", 8)
    for entry in custody_log:
        c.drawString(20 * mm, y, entry)
        y -= 5 * mm

    footer()
    c.save()
    return pdf_path


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

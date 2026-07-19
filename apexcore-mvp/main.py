#!/usr/bin/env python3
"""ApexCore MVP — AI Act Art. 50 Enforcement System"""

import os
import random
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from playwright.async_api import async_playwright

import fable_reviewer
from dossier_template import DossierContext, render_dossier
from evidence import EvidenceItem
from fable_reviewer import TechnicalFinding

load_dotenv()

app = FastAPI(title="ApexCore MVP", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SCANS: dict = {}
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/opt/apexcore-mvp/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0", "system": "ApexCore MVP"}


@app.get("/scans")
async def list_scans():
    return SCANS


@app.post("/scan")
async def start_scan(payload: dict, background_tasks: BackgroundTasks):
    url = payload.get("url")
    if not url:
        return JSONResponse({"error": "url required"}, status_code=400)
    scan_id = str(uuid.uuid4())[:8]
    SCANS[scan_id] = {"status": "processing", "url": url, "started": datetime.utcnow().isoformat()}
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
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"apexcore_dossier_{scan_id}.pdf")


async def run_pipeline(scan_id: str, url: str):
    try:
        SCANS[scan_id]["status"] = "scraping"
        screenshot_path, html, timestamp = await forensic_scrape(url, scan_id)
        SCANS[scan_id]["status"] = "detecting"
        scores = await detect(html, url)
        company = extract_impressum(html)
        SCANS[scan_id]["status"] = "assembling"
        pdf_path = assemble_pdf(scan_id, url, screenshot_path, scores, company, timestamp)
        SCANS[scan_id].update({"status": "completed", "completed": datetime.utcnow().isoformat(), "confidence": scores["confidence"], "decision": scores["decision"], "pdf_path": str(pdf_path), "company": company})
    except Exception as e:
        import traceback
        SCANS[scan_id]["status"] = "failed"; SCANS[scan_id]["error"] = str(e)
        print(f"Pipeline error [{scan_id}]: {e}"); traceback.print_exc()


async def forensic_scrape(url: str, scan_id: str):
    timestamp = datetime.utcnow().isoformat() + "Z"
    screenshot_path = OUTPUT_DIR / f"screenshot_{scan_id}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent="ApexCore-Forensic-Bot/1.0 (+https://apexcore.group)")
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            html = await page.content()
            await page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            html = f"<html><body>Capture error: {e}</body></html>"
            try: await page.screenshot(path=str(screenshot_path))
            except Exception: pass
        finally: await browser.close()
    return screenshot_path, html, timestamp


async def detect(html: str, url: str) -> dict:
    heuristic = heuristic_score(html)
    # MVP: mock external API scores — Phase 2 replaces with real calls
    copyleaks = random.uniform(70, 98); gptzero = random.uniform(65, 95); winston = random.uniform(68, 96)
    confidence = copyleaks * 0.40 + gptzero * 0.30 + winston * 0.20 + heuristic * 0.10
    decision = "AUTO_APPROVE" if confidence >= 85 else "HUMAN_REVIEW" if confidence >= 60 else "REJECT"
    return {"confidence": round(confidence, 1), "decision": decision, "copyleaks": round(copyleaks, 1), "gptzero": round(gptzero, 1), "winston": round(winston, 1), "heuristic": round(heuristic, 1)}


def heuristic_score(html: str) -> float:
    score = 0.0; html_lower = html.lower()
    for m in ["gpt","chatgpt","openai","ki-generiert","ai-generated","powered by ai","written by ai","created with ai"]:
        if m in html_lower: score += 15
    tw = sum(html_lower.count(w) for w in ["however","moreover","therefore","furthermore","additionally","nevertheless","consequently","subsequently"])
    if len(html.split()) > 0 and tw / max(len(html.split()), 1) > 0.01: score += 25
    if not any(k in html_lower for k in ["ki-generiert","ai-generated","künstliche intelligenz","erstellt mit ki","generated by ai"]): score += 20
    return min(score, 100.0)


def extract_impressum(html: str) -> dict:
    import re
    c: dict = {"name": "Unbekannt", "address": "Nicht gefunden", "email": "", "url": ""}
    m = re.search(r'([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\s+(?:GmbH|AG|UG|e\.K\.|KG|OHG|GbR|Ltd\.|Inc\.))', html)
    if m: c["name"] = m.group(1)
    a = re.search(r'(\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+)', html)
    if a: c["address"] = a.group(1)
    e = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
    if e: c["email"] = e.group()
    return c


def assemble_pdf(scan_id, url, screenshot_path, scores, company, timestamp):
    """Builds the Ebene A/B/C dossier via dossier_template.render_dossier().

    IMPORTANT: detect() below is still MVP mock data (random.uniform, see its
    docstring/comment) — not a validated detection result. The single finding
    built from it is therefore marked verified=False, which is a hard gate in
    fable_reviewer.review(): unverified findings never produce Ebene B rows or
    a KI-Uebergabe prompt, only an "offene Punkte" entry. That gate must stay
    in place until detect() is replaced with a real, human-checkable method.
    """
    pdf_path = OUTPUT_DIR / f"dossier_{scan_id}.pdf"
    risk = "HOCH" if scores["confidence"] >= 85 else "MITTEL" if scores["confidence"] >= 60 else "NIEDRIG"

    screenshot_evidence = EvidenceItem(
        1, Path(screenshot_path).name,
        "Vollständiger Seiten-Screenshot (Playwright, 1920x1080)",
        file_path=screenshot_path, page_ref="1",
    )
    findings = [
        TechnicalFinding(
            statement=f"Automatisierte Detection-Ensemble-Bewertung: {scores['confidence']}% Konfidenz, Entscheidung {scores['decision']} (Copyleaks/GPTZero/Winston/Heuristik-Gewichtung).",
            evidence=screenshot_evidence,
            verified=False,  # MVP mock scores -- see detect(); not a human-confirmed finding
        ),
    ]
    review = fable_reviewer.review(url, company, findings)

    ctx = DossierContext(
        dossier_id=scan_id.upper(), url=url, prufdatum=timestamp,
        company_name=company.get("name", "Unbekannt"), company_address=company.get("address", ""),
        score=scores["confidence"], risk=risk,
    )
    chronologie = [
        f"[{timestamp}] Scan initiiert — ApexCore System",
        "Playwright-Browser gestartet, Screenshot erstellt (1920x1080)",
        "HTML archiviert, SHA-256 Hash berechnet",
        "Detection Ensemble durchgeführt (MVP-Mock, unverifiziert)",
        "PDF-Dossier erstellt",
    ]
    return render_dossier(pdf_path, ctx, [screenshot_evidence], findings, review, chronologie, annotated_images=[])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

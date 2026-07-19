#!/usr/bin/env python3
"""Worked example: Fall 1 — ARAG SE (Case-ID AX-2026-0E8E4D2534).

Renders one full dossier using the redesigned Ebene A/B/C template, for
review before the structure is rolled out to other cases.

Source of the case facts: the 2026-07-17 Tageszusammenfassung provided in
chat (Cognigy "Concierge-Bot", kein sichtbarer KI-Hinweis, Consent-before-Load
kein Verstoss (CMP-gated), Art. 13 DSGVO-Informationspflicht verletzt,
Fable-Gesamtrisiko: mittel, Score 98 / Detector-Konfidenz 0.92).

This script does NOT have access to /data/apexcore/data/cases/AX-2026-0E8E4D2534/
(no filesystem or network access to that server from this session). Anywhere
an exact value was not given in chat — the precise checked URL, exact
timestamp, real SHA-256 hashes, real screenshot files — this script uses an
explicit, visibly-marked placeholder instead of inventing one. Swap the
PLACEHOLDER_* constants below for the real values from the case folder
before this leaves draft status.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dossier_template import DossierContext, render_dossier
from evidence import EvidenceItem
from fable_reviewer import DISCLAIMER, FableReviewResult, LegalSubsumptionRow, TechnicalFinding, build_ki_uebergabe_prompt
from screenshot_annotate import Annotation, annotate_screenshot

from _mock_screenshot import build_mock_widget_screenshot

OUT_DIR = Path(__file__).resolve().parent / "output" / "arag_demo"

# --- values NOT provided in chat: explicit placeholders, not invented facts ---
PLACEHOLDER_URL = "[geprüfte URL nicht übermittelt — aus Case AX-2026-0E8E4D2534 zu übernehmen]"
PLACEHOLDER_TIME = "17.07.2026, Uhrzeit: [nicht übermittelt]"


def build_evidence() -> list[EvidenceItem]:
    # Filenames follow the pipeline's own naming convention (browser_capture.py /
    # gdpr_consent_check.py) but are illustrative — the exact filenames from the
    # real case folder were not given in chat and should replace these 1:1.
    return [
        EvidenceItem(1, "screenshot-initial.png", "Startzustand der Website: Concierge-Bot-Icon sichtbar, kein KI-Hinweis im initialen Seitenbereich.", page_ref="1"),
        EvidenceItem(2, "screenshot-widget-open.png", "Geöffnetes Cognigy-Chatfenster ('Concierge-Bot'): kein KI-Hinweis im Chat-UI.", page_ref="2"),
        EvidenceItem(3, "datenschutzerklaerung-auszug.pdf", "Auszug Datenschutzerklärung ARAG SE: Cognigy als Verarbeiter nicht genannt (Art. 13 DSGVO).", page_ref="1"),
        EvidenceItem(4, "cmp-consent-log.json", "Consent-Timing-Log: Cognigy-Requests erst nach CMP-Consent beobachtet (kein Consent-before-Load-Verstoß).", page_ref="1"),
    ]


def build_findings(evidence: list[EvidenceItem]) -> list[TechnicalFinding]:
    ev_by_label = {e.label: e for e in evidence}
    return [
        TechnicalFinding(
            statement="Weder im initialen noch im geöffneten Zustand des Cognigy-Chatbots ('Concierge-Bot') ist ein sichtbarer Hinweis auf den KI-Einsatz vorhanden.",
            evidence=ev_by_label["Anlage 1"],
            verified=True,
        ),
        TechnicalFinding(
            statement="Der Chatbot-Anbieter Cognigy wird in der Datenschutzerklärung der ARAG SE nicht als Auftragsverarbeiter genannt.",
            evidence=ev_by_label["Anlage 3"],
            verified=True,
        ),
        TechnicalFinding(
            statement="Cognigy-Requests wurden ausschließlich nach erteiltem CMP-Consent beobachtet — kein Consent-before-Load-Verstoß festgestellt.",
            evidence=ev_by_label["Anlage 4"],
            verified=True,
        ),
        TechnicalFinding(
            statement="Genaue Prüf-Uhrzeit und exakte Widget-Interaktionssequenz wurden im Tagesbericht nicht mitgeteilt.",
            evidence=ev_by_label["Anlage 2"],
            verified=False,
        ),
    ]


def build_review(url: str, evidence: list[EvidenceItem]) -> FableReviewResult:
    ev = {e.label: e for e in evidence}
    sachverhalt = (
        f"Am 17.07.2026 wurde die Website der ARAG SE ({url}) forensisch untersucht. "
        f"Geprüft wurde der auf der Seite eingebundene Chatbot 'Concierge-Bot' (Anbieter: Cognigy). "
        f"Sowohl im initialen Seitenzustand ({ev['Anlage 1'].label}) als auch nach Öffnen des Chatfensters "
        f"({ev['Anlage 2'].label}) war kein Hinweis auf den KI-Einsatz erkennbar. Die Datenschutzerklärung "
        f"der ARAG SE nennt Cognigy nicht als Auftragsverarbeiter ({ev['Anlage 3'].label}). Die Prüfung des "
        f"Consent-Timings ergab keinen Verstoß gegen das Vor-Consent-Ladeverbot: Anfragen an Cognigy-Endpunkte "
        f"wurden erst nach erteiltem Consent über die Consent-Management-Plattform beobachtet ({ev['Anlage 4'].label}).\n\n"
        f"Chronologisch: (1) Aufruf der Website im initialen Zustand und Screenshot, (2) Öffnen des Concierge-Bot-Widgets "
        f"und erneuter Screenshot, (3) Netzwerk-Log-Auswertung auf Consent-Timing, (4) Abgleich der Datenschutzerklärung "
        f"gegen die technisch beobachteten Drittanbieter."
    )
    subsumtion = (
        f"{DISCLAIMER}\n\n"
        f"Vorliegend spricht die fehlende Kennzeichnung des Cognigy-Chatbots als KI-System in beiden geprüften "
        f"Zuständen ({ev['Anlage 1'].inline_ref()}; {ev['Anlage 2'].inline_ref()}) dafür, dass eine Kennzeichnungspflicht "
        f"gegenüber Nutzern nicht erfüllt wurde; eine abschließende Einordnung unter Art. 50 Abs. 4 AI Act ist erst mit "
        f"Wirksamwerden der Vorschrift am 02.08.2026 rechtlich relevant und wird hier nur als paralleler technischer Befund "
        f"dokumentiert. Ferner spricht das Fehlen der Nennung von Cognigy in der Datenschutzerklärung "
        f"({ev['Anlage 3'].inline_ref()}) dafür, dass die Informationspflicht aus Art. 13 DSGVO gegenüber Betroffenen nicht "
        f"vollständig erfüllt wurde. Kein Verstoß liegt hinsichtlich des Ladezeitpunkts von Cognigy-Diensten vor, da die "
        f"Auswertung des Consent-Logs ({ev['Anlage 4'].inline_ref()}) keine Datenübertragung vor Consent-Erteilung zeigt."
    )
    chain = [
        LegalSubsumptionRow(
            norm="Art. 13 Abs. 1 lit. e DSGVO",
            tatbestandsmerkmal="Informationspflicht über Empfänger/Auftragsverarbeiter personenbezogener Daten",
            feststellung="Cognigy als eingesetzter Chatbot-Verarbeiter wird in der Datenschutzerklärung nicht genannt.",
            beweis_referenz=ev["Anlage 3"].inline_ref(),
            offene_punkte="Zu prüfen: greift eine Ausnahme (z.B. Unterauftragsverarbeiter-Sammelliste an anderer Stelle)? Vollständige Datenschutzerklärung durch Kanzlei zu sichten.",
        ),
        LegalSubsumptionRow(
            norm="Art. 50 Abs. 4 AI Act",
            tatbestandsmerkmal="Kennzeichnungspflicht für KI-gestützte Chatbots gegenüber Nutzern",
            feststellung="Kein KI-Hinweis im initialen oder geöffneten Widget-Zustand feststellbar.",
            beweis_referenz=f"{ev['Anlage 1'].inline_ref()}; {ev['Anlage 2'].inline_ref()}",
            offene_punkte="Vorschrift erst ab 02.08.2026 anwendbar — vor diesem Datum keine unmittelbare Rechtsfolge; als paralleler Befund für spätere Geltendmachung dokumentiert.",
        ),
        LegalSubsumptionRow(
            norm="Art. 6 Abs. 1 lit. a DSGVO (Consent-before-Load)",
            tatbestandsmerkmal="Keine Datenverarbeitung/Drittanbieter-Laden vor Einwilligung",
            feststellung="Kein Verstoß: Cognigy-Requests ausschließlich nach CMP-Consent beobachtet.",
            beweis_referenz=ev["Anlage 4"].inline_ref(),
            offene_punkte="Keine — dieser Punkt wird als entlastender Befund dokumentiert, nicht als Verstoß.",
        ),
    ]
    prompt = build_ki_uebergabe_prompt(url, sachverhalt, subsumtion, chain)
    return FableReviewResult(sachverhalt_prosa=sachverhalt, subsumtion_prosa=subsumtion, legal_subsumption_chain=chain, ki_uebergabe_prompt=prompt)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence()

    mock_shot = build_mock_widget_screenshot(OUT_DIR / "mock-screenshot-widget-open.png", "ARAG SE", "Concierge-Bot (Cognigy)")
    annotated = annotate_screenshot(
        mock_shot,
        OUT_DIR / "mock-screenshot-widget-open-annotated.png",
        [Annotation(box=(1180, 260, 1540, 330), label="Kein KI-Hinweis im Chat-Header erwartet, aber nicht vorhanden", kind="missing")],
    )

    findings = build_findings(evidence)
    review = build_review(PLACEHOLDER_URL, evidence)

    ctx = DossierContext(
        dossier_id="AX-2026-0E8E4D2534",
        url=PLACEHOLDER_URL,
        prufdatum=PLACEHOLDER_TIME,
        company_name="ARAG SE",
        company_address="[Anschrift aus Impressum zu übernehmen]",
        score=98,
        risk="MITTEL",
    )

    chronologie = [
        "Website im Ausgangszustand geladen, Screenshot erstellt (Anlage 1).",
        "Concierge-Bot-Widget geöffnet, Screenshot erstellt (Anlage 2).",
        "Netzwerk-Requests auf Consent-Timing gegen Cognigy-Endpunkte ausgewertet (Anlage 4).",
        "Datenschutzerklärung auf Nennung von Cognigy als Auftragsverarbeiter geprüft (Anlage 3).",
        "Technische Feststellungen dem Fable-Reviewer zur strukturierten Vorprüfung übergeben.",
    ]

    out_pdf = OUT_DIR / "ARAG_SE_Dossier_BEISPIEL.pdf"
    render_dossier(
        out_pdf, ctx, evidence, findings, review, chronologie,
        annotated_images=[(annotated, "MUSTER-DARSTELLUNG, kein echter Screenshot — demonstriert nur die Annotation-Mechanik von screenshot_annotate.py. Reale Anlage aus dem Case-Ordner einsetzen.")],
    )
    print(f"Demo-Dossier geschrieben: {out_pdf}")
    print(f"Annotierter Muster-Screenshot: {annotated}")


if __name__ == "__main__":
    main()

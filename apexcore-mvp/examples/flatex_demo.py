#!/usr/bin/env python3
"""Worked example: Fall 2 — flatexDEGIRO Bank AG (Case-ID AX-2026-576B23137D).

Renders one full dossier using the redesigned Ebene A/B/C template, in the
same structure as examples/arag_demo.py, so the two can be compared side by
side before the template is rolled out further.

Source of the case facts: the 2026-07-17 Tageszusammenfassung provided in
chat (moinAI-Chatbot, kein sichtbarer KI-Hinweis, Consent-before-Load =
Verstoss (9 moin.ai-Requests vor Consent, HAR-verifiziert), Art.-13 =
Verstoss (weder moinAI noch knowhere genannt, auch nicht in eigener
Cookiebot-Anbieterliste), Fable-Gesamtrisiko: Hoch, Score 98 / Detector-
Konfidenz 0.88, bekannter offener Vorbehalt: Widget-Open-Capture technisch
defekt (Cross-Origin-iframe), Art.-50-Achse dadurch eingeschraenkt
beweisfaehig).

Same discipline as the ARAG example: this script has no filesystem or
network access to /data/apexcore/data/cases/AX-2026-576B23137D/. Any value
not given in chat -- exact checked URL, exact timestamp, real SHA-256
hashes, real screenshots/HAR file -- is an explicit, visibly-marked
placeholder, not an invented fact. The known capture defect on the widget-
open state is modelled honestly: no fabricated "widget open" screenshot is
produced, only a documented technical-failure note.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dossier_template import DossierContext, render_dossier, render_dossier_markdown
from evidence import EvidenceItem
from fable_reviewer import DISCLAIMER, FableReviewResult, LegalSubsumptionRow, TechnicalFinding, build_ki_uebergabe_prompt
from screenshot_annotate import Annotation, annotate_screenshot

from _mock_screenshot import build_mock_widget_screenshot

OUT_DIR = Path(__file__).resolve().parent / "output" / "flatex_demo"

PLACEHOLDER_URL = "[geprüfte URL nicht übermittelt — aus Case AX-2026-576B23137D zu übernehmen; vermutlich flatex.de/flatexdegiro.de-Domain, exakte Unterseite aus Case-Ordner]"
PLACEHOLDER_TIME = "17.07.2026, Uhrzeit: [nicht übermittelt]"


def build_evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(1, "screenshot-initial.png", "Startzustand der Website: moinAI-Widget-Icon sichtbar, kein KI-Hinweis im initialen Seitenbereich.", page_ref="1"),
        EvidenceItem(2, "har-consent-timing.har", "HAR-Aufzeichnung: 9 Requests an moin.ai-Endpunkte, sämtlich vor erteiltem CMP-Consent beobachtet.", page_ref="1-3"),
        EvidenceItem(3, "cookiebot-anbieterliste-datenschutz-auszug.pdf", "Auszug Cookiebot-Anbieterliste und Datenschutzerklärung: weder 'moinAI' noch 'knowhere' als Anbieter/Auftragsverarbeiter genannt.", page_ref="1-2"),
        EvidenceItem(4, "capture-error-log.txt", "Fehlerprotokoll: Öffnung des moinAI-Widgets (Cross-Origin-iframe) technisch nicht zuverlässig aufzeichenbar — kein verwertbarer 'Widget geöffnet'-Screenshot verfügbar.", page_ref="1"),
    ]


def build_findings(evidence: list[EvidenceItem]) -> list[TechnicalFinding]:
    ev = {e.label: e for e in evidence}
    return [
        TechnicalFinding(
            statement="Im initialen Seitenzustand ist beim moinAI-Chatbot-Widget kein sichtbarer Hinweis auf den KI-Einsatz vorhanden.",
            evidence=ev["Anlage 1"],
            verified=True,
        ),
        TechnicalFinding(
            statement="9 Netzwerk-Requests an moin.ai-Endpunkte wurden HAR-verifiziert vor Erteilung des CMP-Consents beobachtet.",
            evidence=ev["Anlage 2"],
            verified=True,
        ),
        TechnicalFinding(
            statement="Weder der Chatbot-Anbieter 'moinAI' noch der (laut Tagesbericht mitgeteilte) Anbieter 'knowhere' werden in der Datenschutzerklärung genannt — auch nicht in der eigenen Cookiebot-Anbieterliste der Website.",
            evidence=ev["Anlage 3"],
            verified=True,
        ),
        TechnicalFinding(
            statement="Der geöffnete Zustand des moinAI-Widgets konnte wegen eines Cross-Origin-iframe-Problems technisch nicht zuverlässig erfasst werden. Ob im geöffneten Chatfenster selbst ein KI-Hinweis vorhanden ist, ist damit nicht beweisfähig festgestellt.",
            evidence=ev["Anlage 4"],
            verified=False,
        ),
    ]


def build_review(url: str, evidence: list[EvidenceItem]) -> FableReviewResult:
    ev = {e.label: e for e in evidence}
    sachverhalt = (
        f"Am 17.07.2026 wurde die Website der flatexDEGIRO Bank AG ({url}) forensisch untersucht. "
        f"Geprüft wurde der auf der Seite eingebundene Chatbot (Anbieter: moinAI). Im initialen "
        f"Seitenzustand war kein Hinweis auf den KI-Einsatz erkennbar ({ev['Anlage 1'].label}). Die "
        f"Auswertung des Netzwerkverkehrs (HAR) ergab 9 Requests an moin.ai-Endpunkte, die sämtlich vor "
        f"Erteilung des Consents über die Consent-Management-Plattform stattfanden ({ev['Anlage 2'].label}). "
        f"Weder 'moinAI' noch 'knowhere' werden in der Datenschutzerklärung oder der eigenen "
        f"Cookiebot-Anbieterliste der Website genannt ({ev['Anlage 3'].label}). Der geöffnete Zustand des "
        f"Chat-Widgets konnte wegen eines technischen Cross-Origin-iframe-Problems nicht zuverlässig "
        f"aufgezeichnet werden ({ev['Anlage 4'].label}); ob im geöffneten Chatfenster selbst ein KI-Hinweis "
        f"vorhanden ist, bleibt daher technisch ungeklärt. Als Bank im Anwendungsbereich von DORA besteht "
        f"ein erhöhter regulatorischer Kontext, der hier jedoch nicht eigenständig rechtlich bewertet wird.\n\n"
        f"Chronologisch: (1) Aufruf der Website im initialen Zustand und Screenshot, (2) Versuch der Öffnung "
        f"des Chat-Widgets, technisch fehlgeschlagen (Cross-Origin-iframe), (3) Netzwerk-Log-Auswertung (HAR) "
        f"auf Consent-Timing, (4) Abgleich der Datenschutzerklärung und Cookiebot-Anbieterliste gegen die "
        f"technisch beobachteten Drittanbieter."
    )
    subsumtion = (
        f"{DISCLAIMER}\n\n"
        f"Vorliegend spricht die HAR-verifizierte Beobachtung von 9 Requests an moin.ai-Endpunkte vor "
        f"Consent-Erteilung ({ev['Anlage 2'].inline_ref()}) dafür, dass ein Verstoß gegen das "
        f"Vor-Consent-Ladeverbot vorliegt. Ferner spricht das Fehlen der Nennung von 'moinAI' und "
        f"'knowhere' in der Datenschutzerklärung sowie der eigenen Cookiebot-Anbieterliste "
        f"({ev['Anlage 3'].inline_ref()}) dafür, dass die Informationspflicht aus Art. 13 DSGVO gegenüber "
        f"Betroffenen nicht erfüllt wurde. Hinsichtlich einer Kennzeichnungspflicht nach Art. 50 Abs. 4 "
        f"AI Act ist die Beweislage eingeschränkt: der initiale Seitenzustand ohne KI-Hinweis ist belegt "
        f"({ev['Anlage 1'].inline_ref()}), der geöffnete Widget-Zustand konnte jedoch wegen eines "
        f"technischen Erfassungsfehlers nicht aufgezeichnet werden ({ev['Anlage 4'].inline_ref()}); eine "
        f"abschließende Einordnung ist zudem erst mit Wirksamwerden der Vorschrift am 02.08.2026 rechtlich "
        f"relevant. Der Bank-/DORA-Kontext wird als Risikoerhöhung dokumentiert, aber hier nicht als "
        f"eigenständiger Tatbestand subsumiert."
    )
    chain = [
        LegalSubsumptionRow(
            norm="Art. 6 Abs. 1 lit. a DSGVO i.V.m. § 25 Abs. 1 TTDSG (Consent-before-Load)",
            tatbestandsmerkmal="Keine Datenverarbeitung/Drittanbieter-Laden vor Einwilligung",
            feststellung="9 Requests an moin.ai-Endpunkte HAR-verifiziert vor Consent-Erteilung beobachtet.",
            beweis_referenz=ev["Anlage 2"].inline_ref(),
            offene_punkte="Vollständigkeit der HAR-Aufzeichnung (Zeitraum, alle Endpunkte erfasst?) durch Kanzlei zu prüfen.",
        ),
        LegalSubsumptionRow(
            norm="Art. 13 Abs. 1 lit. e DSGVO",
            tatbestandsmerkmal="Informationspflicht über Empfänger/Auftragsverarbeiter personenbezogener Daten",
            feststellung="Weder moinAI noch knowhere in Datenschutzerklärung oder Cookiebot-Anbieterliste genannt.",
            beweis_referenz=ev["Anlage 3"].inline_ref(),
            offene_punkte="Zu prüfen: vollständige Datenschutzerklärung und Cookiebot-Konfiguration durch Kanzlei sichten; ist 'knowhere' Unterauftragsverarbeiter von moinAI oder eigenständiger Anbieter?",
        ),
        LegalSubsumptionRow(
            norm="Art. 50 Abs. 4 AI Act",
            tatbestandsmerkmal="Kennzeichnungspflicht für KI-gestützte Chatbots gegenüber Nutzern",
            feststellung="Kein KI-Hinweis im initialen Zustand feststellbar; geöffneter Widget-Zustand nicht auswertbar.",
            beweis_referenz=f"{ev['Anlage 1'].inline_ref()}; {ev['Anlage 4'].inline_ref()}",
            offene_punkte="Widget-Open-Capture technisch defekt (Cross-Origin-iframe) — Beweisfähigkeit für den geöffneten Zustand eingeschränkt. Erneute Erfassung mit korrigierter Capture-Methode empfohlen. Vorschrift zudem erst ab 02.08.2026 anwendbar.",
        ),
    ]
    prompt = build_ki_uebergabe_prompt(url, sachverhalt, subsumtion, chain)
    return FableReviewResult(sachverhalt_prosa=sachverhalt, subsumtion_prosa=subsumtion, legal_subsumption_chain=chain, ki_uebergabe_prompt=prompt)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence()

    mock_shot = build_mock_widget_screenshot(OUT_DIR / "mock-screenshot-initial.png", "flatexDEGIRO", "moinAI Chat")
    annotated = annotate_screenshot(
        mock_shot,
        OUT_DIR / "mock-screenshot-initial-annotated.png",
        [Annotation(box=(1180, 260, 1540, 330), label="Kein KI-Hinweis am Widget-Icon erwartet, aber nicht vorhanden", kind="missing")],
    )

    findings = build_findings(evidence)
    review = build_review(PLACEHOLDER_URL, evidence)

    ctx = DossierContext(
        dossier_id="AX-2026-576B23137D",
        url=PLACEHOLDER_URL,
        prufdatum=PLACEHOLDER_TIME,
        company_name="flatexDEGIRO Bank AG",
        company_address="[Anschrift aus Impressum zu übernehmen]",
        score=98,
        risk="HOCH",
    )

    chronologie = [
        "Website im Ausgangszustand geladen, Screenshot erstellt (Anlage 1).",
        "Öffnen des moinAI-Widgets versucht — technisch fehlgeschlagen, Cross-Origin-iframe (Anlage 4).",
        "HAR-Aufzeichnung auf Consent-Timing gegen moin.ai-Endpunkte ausgewertet: 9 Requests vor Consent (Anlage 2).",
        "Datenschutzerklärung und Cookiebot-Anbieterliste auf Nennung von moinAI/knowhere geprüft (Anlage 3).",
        "Technische Feststellungen dem Fable-Reviewer zur strukturierten Vorprüfung übergeben.",
    ]

    out_pdf = OUT_DIR / "Flatex_Dossier_BEISPIEL.pdf"
    render_dossier(
        out_pdf, ctx, evidence, findings, review, chronologie,
        annotated_images=[(annotated, "MUSTER-DARSTELLUNG, kein echter Screenshot — demonstriert nur die Annotation-Mechanik von screenshot_annotate.py. Reale Anlage aus dem Case-Ordner einsetzen. Hinweis: Ein 'Widget geöffnet'-Screenshot existiert für diesen Fall nicht (Capture-Defekt, siehe Anlage 4).")],
    )
    out_md = OUT_DIR / "Flatex_Dossier_BEISPIEL.md"
    render_dossier_markdown(out_md, ctx, evidence, findings, review, chronologie)

    print(f"Demo-Dossier geschrieben: {out_pdf}")
    print(f"Demo-Dossier (Markdown): {out_md}")
    print(f"Annotierter Muster-Screenshot: {annotated}")


if __name__ == "__main__":
    main()

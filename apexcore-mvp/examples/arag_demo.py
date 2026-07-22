#!/usr/bin/env python3
"""Worked example: Fall 1 — ARAG SE (Case-ID AX-2026-0E8E4D2534).

Renders one full dossier using the redesigned Ebene A/B/C template, extended
per Kanzlei-Feedback (Olaf Bitter, 2026-07-19) with the full Gutachtenstil
subsumption, Anspruchsgrundlage/Rechtsfolgen, expected-defense analysis,
procedural risk assessment, and the Mandats-/Abmahnungsparameter block.

Source of the case facts: the 2026-07-17 Tageszusammenfassung provided in
chat (Cognigy "Concierge-Bot", kein sichtbarer KI-Hinweis, Consent-before-Load
kein Verstoss (CMP-gated), Art. 13 DSGVO-Informationspflicht verletzt,
Fable-Gesamtrisiko: mittel, Score 98 / Detector-Konfidenz 0.92) plus the
"Offene Punkte" item from that summary (Kläger-Frage Wettbewerber vs. Verband,
BGH März 2025) used to populate Aktivlegitimation below.

This script does NOT have access to /data/apexcore/data/cases/AX-2026-0E8E4D2534/
(no filesystem or network access to that server from this session). Anywhere
an exact value was not given in chat — the precise checked URL, exact
timestamp, real SHA-256 hashes, real screenshot files, Gegenstandswert,
Vertragsstrafe, Frist, Kosten — this script uses an explicit, visibly-marked
placeholder instead of inventing one. Swap the PLACEHOLDER_* constants and
the MandateParameters fields below for the real values before this leaves
draft status.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dossier_template import DossierContext, render_dossier, render_dossier_markdown
from evidence import EvidenceItem
from fable_reviewer import (
    DISCLAIMER,
    ExpectedDefense,
    FableReviewResult,
    LegalSubsumptionRow,
    MandateParameters,
    TechnicalFinding,
    build_ki_uebergabe_prompt,
)
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
        EvidenceItem(
            1, "screenshot-initial.png",
            "Startzustand der Website: Concierge-Bot-Icon sichtbar, kein KI-Hinweis im initialen Seitenbereich.",
            page_ref="1",
            quality="Mittel (Screenshot grundsätzlich manipulierbar, hier aber automatisiert erstellt und mit SHA-256-Hash/Zeitstempel abgesichert).",
        ),
        EvidenceItem(
            2, "screenshot-widget-open.png",
            "Geöffnetes Cognigy-Chatfenster ('Concierge-Bot'): kein KI-Hinweis im Chat-UI.",
            page_ref="2",
            quality="Mittel; genaue Interaktionssequenz beim Öffnen nicht protokolliert (s. Ebene A, unverifizierte Feststellung).",
        ),
        EvidenceItem(
            3, "datenschutzerklaerung-auszug.pdf",
            "Auszug Datenschutzerklärung ARAG SE: Cognigy als Verarbeiter nicht genannt (Art. 13 DSGVO).",
            page_ref="1",
            quality="Hoch (Auszug aus öffentlich zugänglichem Rechtsdokument, direkt nachprüfbar).",
        ),
        EvidenceItem(
            4, "cmp-consent-log.json",
            "Consent-Timing-Log: Cognigy-Requests erst nach CMP-Consent beobachtet (kein Consent-before-Load-Verstoß).",
            page_ref="1",
            quality="Hoch (automatisiert erfasstes Netzwerk-Log, zeitgestempelt, reproduzierbar).",
        ),
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


def build_review(url: str, evidence: list[EvidenceItem], mandate: MandateParameters) -> FableReviewResult:
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
            subsumtion="Da Cognigy als Chatbot-Betreiber technisch nachweisbar personenbezogene Daten (Chat-Eingaben, IP-Adresse) verarbeitet, wäre eine Nennung als Empfänger/Auftragsverarbeiter nach Art. 13 Abs. 1 lit. e DSGVO erforderlich gewesen; diese fehlt im geprüften Auszug.",
            ergebnis="(vorläufig) erfüllt",
            anspruchsgrundlage="Bei Aktivlegitimation als Mitbewerber: § 8 Abs. 1, Abs. 3 Nr. 1 UWG i.V.m. § 3a UWG (DSGVO als Marktverhaltensregel). Bei Verbandsklagebefugnis: § 8 Abs. 3 Nr. 2–4 UWG bzw. § 2 UKlaG. Abhängig von der noch offenen Klärung der Aktivlegitimation (s. Ebene C).",
            rechtsfolgen="Unterlassung; bei berechtigter Abmahnung Erstattung der Abmahnkosten (§ 13 Abs. 3 UWG).",
        ),
        LegalSubsumptionRow(
            norm="Art. 50 Abs. 4 AI Act",
            tatbestandsmerkmal="Kennzeichnungspflicht für KI-gestützte Chatbots gegenüber Nutzern",
            feststellung="Kein KI-Hinweis im initialen oder geöffneten Widget-Zustand feststellbar.",
            beweis_referenz=f"{ev['Anlage 1'].inline_ref()}; {ev['Anlage 2'].inline_ref()}",
            offene_punkte="Vorschrift erst ab 02.08.2026 anwendbar — vor diesem Datum keine unmittelbare Rechtsfolge; als paralleler Befund für spätere Geltendmachung dokumentiert.",
            subsumtion="Die Feststellung des fehlenden Hinweises betrifft exakt das Tatbestandsmerkmal der Kennzeichnungspflicht; die Rechtsfolge tritt jedoch erst mit Wirksamwerden der Norm am 02.08.2026 ein.",
            ergebnis="Tatbestandsmerkmal (vorläufig) erfüllt, Rechtsfolge vor 02.08.2026 nicht durchsetzbar",
            anspruchsgrundlage="Art. 50 Abs. 4 AI Act ist keine eigenständige zivilrechtliche Anspruchsgrundlage; Durchsetzung primär über Marktüberwachungsbehörden. Eine ergänzende zivilrechtliche Geltendmachung über § 3a UWG ist denkbar, aber rechtlich nicht abschließend geklärt.",
            rechtsfolgen="Vor 02.08.2026: keine. Danach ggf. ergänzender Kontext zu einem UWG-Anspruch, kein eigenständiger Unterlassungsanspruch aus der Norm selbst.",
        ),
        LegalSubsumptionRow(
            norm="Art. 6 Abs. 1 lit. a DSGVO (Consent-before-Load)",
            tatbestandsmerkmal="Keine Datenverarbeitung/Drittanbieter-Laden vor Einwilligung",
            feststellung="Kein Verstoß: Cognigy-Requests ausschließlich nach CMP-Consent beobachtet.",
            beweis_referenz=ev["Anlage 4"].inline_ref(),
            offene_punkte="Keine — dieser Punkt wird als entlastender Befund dokumentiert, nicht als Verstoß.",
            subsumtion="Das Consent-Log zeigt keine Datenübertragung vor Consent-Erteilung; das Tatbestandsmerkmal eines Vor-Consent-Ladens ist damit nicht erfüllt.",
            ergebnis="nicht erfüllt (entlastend)",
            anspruchsgrundlage="Entfällt — kein Verstoß festgestellt.",
            rechtsfolgen="Keine.",
        ),
    ]
    defenses = [
        ExpectedDefense(
            einwendung="ARAG könnte vortragen, ein KI-Hinweis sei an anderer, hier nicht geprüfter Stelle vorhanden (z.B. Impressum, AGB, Cookie-Banner-Text).",
            erwiderung="Die Kennzeichnungspflicht dürfte einen für den Nutzer im unmittelbaren Interaktionskontext erkennbaren Hinweis erfordern; ein an anderer Stelle versteckter Hinweis genügt voraussichtlich nicht. Vor Versand zu prüfen, ob ARAG einen solchen Hinweis tatsächlich vorweisen kann.",
            bezug="Art. 50 Abs. 4 AI Act",
        ),
        ExpectedDefense(
            einwendung="ARAG könnte vortragen, Cognigy sei reiner technischer Dienstleister ohne Verarbeitung personenbezogener Daten und daher nicht nennungspflichtig.",
            erwiderung="Chat-Eingaben und IP-Adresse dürften regelmäßig personenbezogene Daten sein; zu prüfen, ob ein Auftragsverarbeitungsvertrag vorliegt und ob dieser die Informationspflicht aus Art. 13 DSGVO berührt (eine vertragliche Abbedingung dieser Pflicht ist grundsätzlich nicht möglich).",
            bezug="Art. 13 Abs. 1 lit. e DSGVO",
        ),
        ExpectedDefense(
            einwendung="ARAG könnte die Aktivlegitimation der anspruchstellenden Partei bestreiten (kein Wettbewerbsverhältnis, keine Verbandsklagebefugnis).",
            erwiderung="Aktivlegitimation ist vor Versand einer Abmahnung zu klären (s. Mandats-/Abmahnungsparameter, Ebene C); ohne geklärte Aktivlegitimation besteht ein erhebliches prozessuales Risiko unabhängig von der technischen Beweislage.",
            bezug="Aktivlegitimation (Ebene C)",
        ),
    ]
    risiko = (
        "Die Beweislage zur fehlenden KI-Kennzeichnung stützt sich auf zwei automatisiert erstellte Screenshots "
        f"({ev['Anlage 1'].label}, {ev['Anlage 2'].label}); deren Beweisqualität ist als 'Mittel' eingestuft (s. Anlagenverzeichnis). "
        "Die Aktivlegitimation ist zum Zeitpunkt dieser Vorprüfung nicht geklärt (Wettbewerber- vs. Verbandsstatus, vgl. BGH März 2025) "
        "und stellt das größte offene Risiko für eine Abmahnung dar — unabhängig davon, wie stark die technische Beweislage ist. "
        "Die AI-Act-Achse (Art. 50 Abs. 4) ist vor dem 02.08.2026 nicht unmittelbar durchsetzbar und sollte in einer vor diesem Datum "
        "versandten Abmahnung nicht als eigenständiger Anspruch, sondern allenfalls als Kontext angeführt werden. Die DSGVO-Achse "
        "(Art. 13) erscheint auf Basis der vorliegenden Feststellung vergleichsweise robust, sofern die vollständige "
        "Datenschutzerklärung durch die Kanzlei gesichtet und keine Ausnahme gefunden wird."
    )
    prompt = build_ki_uebergabe_prompt(url, sachverhalt, subsumtion, chain, defenses, risiko, mandate)
    return FableReviewResult(
        sachverhalt_prosa=sachverhalt, subsumtion_prosa=subsumtion, legal_subsumption_chain=chain,
        erwartete_einwendungen=defenses, prozessuale_risikobewertung=risiko, ki_uebergabe_prompt=prompt,
    )


def build_mandate() -> MandateParameters:
    # Only the Aktivlegitimation open-question text is known (from the daily
    # summary's own "Offene Punkte" list). Everything else genuinely needs
    # Mandatsdaten this session does not have -- left blank on purpose.
    return MandateParameters(
        aktivlegitimation=(
            "OFFEN — Kläger-Frage noch nicht geklärt: Wettbewerber (§ 8 Abs. 3 Nr. 1 UWG) oder "
            "klagebefugter Verband (§ 8 Abs. 3 Nr. 2–4 UWG / § 2 UKlaG)? Kanzlei-Rückmeldung ausstehend "
            "(vgl. BGH-Rechtsprechung zur Wettbewerber-Aktivlegitimation, März 2025)."
        ),
        passivlegitimation="ARAG SE — [Anschrift/Registerdaten aus Impressum bzw. Handelsregister zu verifizieren].",
    )


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
    mandate = build_mandate()
    review = build_review(PLACEHOLDER_URL, evidence, mandate)

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
        mandate=mandate,
    )
    out_md = OUT_DIR / "ARAG_SE_Dossier_BEISPIEL.md"
    render_dossier_markdown(out_md, ctx, evidence, findings, review, chronologie, mandate=mandate)

    print(f"Demo-Dossier geschrieben: {out_pdf}")
    print(f"Demo-Dossier (Markdown): {out_md}")
    print(f"Annotierter Muster-Screenshot: {annotated}")


if __name__ == "__main__":
    main()

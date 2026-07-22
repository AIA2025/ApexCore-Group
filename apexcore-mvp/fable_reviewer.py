"""Fable-Reviewer: structured legal-technical review prompt.

Turns a set of *human-confirmed* technical findings into structured JSON
that drives Ebene B (rechtliche Einordnung), the full Gutachtenstil
subsumption, claim mapping, expected-defense analysis, procedural risk
notes, and the KI-Uebergabe prompt block.

Hard rule, unchanged from the first version of this module: this module
never reads raw detector output (e.g. the mocked confidence scores in
main.py's detect()) directly. It only accepts TechnicalFinding objects that
a human has explicitly marked verified=True. Unverified findings are
rendered as open questions, never as the basis for a legal claim or a
ready-to-send prompt.

Second hard rule, added per Kanzlei-Feedback (Olaf Bitter, 2026-07-19):
mandate-specific parameters that cannot be derived from a technical scan --
Aktivlegitimation, Passivlegitimation, Gegenstandswert, Vertragsstrafe,
Frist, Kosten -- are modelled as MandateParameters, a plain data container
with no defaults derived by this module. review() never fills these in;
they stay blank until a human (Kanzlei, from Mandatsdaten) sets them. The
KI-Uebergabe prompt says so explicitly wherever a field is still empty.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import httpx

from evidence import EvidenceItem

DISCLAIMER = "Automatisierte Vorprüfung, keine Rechtsberatung. Rechtliche Bewertung obliegt ausschließlich der Kanzlei."

MANDATE_FIELD_LABELS = {
    "aktivlegitimation": "Aktivlegitimation",
    "passivlegitimation": "Passivlegitimation",
    "gegenstandswert": "Gegenstandswert",
    "vertragsstrafe": "Vertragsstrafe",
    "frist": "Frist",
    "kosten": "Kosten",
}


@dataclass
class TechnicalFinding:
    statement: str          # e.g. "Kein KI-Hinweis im sichtbaren Seitenbereich gefunden"
    evidence: EvidenceItem
    verified: bool = False  # must be explicitly set True by a human reviewer


@dataclass
class LegalSubsumptionRow:
    norm: str                        # "Art. 50 Abs. 4 AI Act"
    tatbestandsmerkmal: str          # "Kennzeichnungspflicht bei KI-generierten Inhalten"
    feststellung: str                # what was technically found
    beweis_referenz: str             # formatted evidence reference string
    offene_punkte: str               # what still needs human/legal review
    subsumtion: str = ""             # Gutachtenstil step 3: reasoning linking Feststellung to Tatbestandsmerkmal
    ergebnis: str = ""               # Gutachtenstil step 4: preliminary verdict, e.g. "(vorläufig) erfüllt"
    anspruchsgrundlage: str = ""     # e.g. "§ 8 Abs. 1, Abs. 3 Nr. 1 UWG (bei Aktivlegitimation als Mitbewerber)"
    rechtsfolgen: str = ""           # e.g. "Unterlassung, Beseitigung, Erstattung Abmahnkosten"


@dataclass
class ExpectedDefense:
    einwendung: str   # anticipated counter-argument from the other side
    erwiderung: str   # possible rebuttal
    bezug: str        # which norm/finding this relates to


@dataclass
class MandateParameters:
    """Never populated by review() -- these come from the Kanzlei's
    Mandatsdaten or standardized firm input fields, not from a technical
    scan. All blank by default; render_dossier() shows blanks as fillable
    fields, never as invented values."""
    aktivlegitimation: str = ""
    passivlegitimation: str = ""
    gegenstandswert: str = ""
    vertragsstrafe: str = ""
    frist: str = ""
    kosten: str = ""

    def missing_fields(self) -> list[str]:
        return [MANDATE_FIELD_LABELS[k] for k, v in self.__dict__.items() if not v.strip()]


@dataclass
class FableReviewResult:
    sachverhalt_prosa: str
    subsumtion_prosa: str
    legal_subsumption_chain: list[LegalSubsumptionRow] = field(default_factory=list)
    erwartete_einwendungen: list[ExpectedDefense] = field(default_factory=list)
    prozessuale_risikobewertung: str = ""
    ki_uebergabe_prompt: str | None = None  # None if gate not satisfied


def build_fable_reviewer_prompt(url: str, company: dict, findings: list[TechnicalFinding]) -> str:
    """The prompt sent to the Fable-Reviewer model. Requests the full
    Gutachtenstil chain, claim mapping, expected-defense analysis and a
    procedural risk note, in addition to the original schema."""
    findings_block = "\n".join(
        f'- [{"VERIFIZIERT" if f.verified else "UNVERIFIZIERT"}] {f.statement} '
        f'(Beweis: {f.evidence.inline_ref()}'
        + (f', Beweisqualität: {f.evidence.quality}' if f.evidence.quality else '')
        + ')'
        for f in findings
    )
    return f"""Du bist ein juristisch-technischer Prüfassistent ("Fable-Reviewer") für eine \
deutsche Anwaltskanzlei. Du erstellst KEINE Rechtsberatung, sondern eine strukturierte \
Vorprüfung im Gutachtenstil (Tatbestandsmerkmal - Feststellung - Subsumtion - Ergebnis), \
die eine Anwältin/ein Anwalt anschließend eigenverantwortlich bewertet und freigibt.

ZIELWEBSITE: {url}
FIRMA (Impressum): {company.get('name', 'Unbekannt')}

TECHNISCHE FESTSTELLUNGEN (nur VERIFIZIERT-markierte dürfen als Tatsachengrundlage \
für eine rechtliche Einordnung dienen; UNVERIFIZIERT-Feststellungen gehören ausschließlich \
in "Offene Punkte"):
{findings_block}

Gib ausschließlich valides JSON zurück mit exakt diesen Feldern:
{{
  "sachverhalt_prosa": "Fließtext für einen Schriftsatz: Datum/Uhrzeit der Untersuchung, \
geprüfte URL, wesentliche technische Feststellungen in Prosa, chronologischer Ablauf.",
  "subsumtion_prosa": "Zusammenhängender Fließtext nach dem Muster 'Vorliegend spricht \
[Feststellung X, Beleg Y] dafür, dass [Tatbestandsmerkmal Z] erfüllt ist...'. \
Nur auf VERIFIZIERT-Feststellungen stützen. Explizit als automatisiert generiert \
und vorläufig kennzeichnen.",
  "legal_subsumption_chain": [
    {{
      "norm": "z.B. Art. 50 Abs. 4 AI Act",
      "tatbestandsmerkmal": "was muss erfüllt sein (Obersatz)",
      "feststellung": "was wurde technisch festgestellt (nur VERIFIZIERT)",
      "subsumtion": "ein bis zwei Sätze, die Feststellung und Tatbestandsmerkmal verknüpfen",
      "ergebnis": "vorläufiges Ergebnis, z.B. '(vorläufig) erfüllt' / 'nicht erfüllt' / 'offen'",
      "beweis_referenz": "Anlage/Hash/Seite aus der Feststellung",
      "offene_punkte": "was ist unklar oder braucht menschliche Prüfung",
      "anspruchsgrundlage": "einschlägige Anspruchsgrundlage, sofern eindeutig; sonst '[abhängig von Aktivlegitimation, durch Kanzlei zu bestimmen]'",
      "rechtsfolgen": "standardmäßig daraus folgende Ansprüche, z.B. Unterlassung, Beseitigung, Erstattung Abmahnkosten, Schadensersatz"
    }}
  ],
  "erwartete_einwendungen": [
    {{
      "einwendung": "denkbarer Einwand der Gegenseite",
      "erwiderung": "mögliche Erwiderung darauf",
      "bezug": "auf welche Norm/Feststellung sich das bezieht"
    }}
  ],
  "prozessuale_risikobewertung": "kurzer, vorläufiger Absatz zur Beweislage, offenen Punkten \
und ihrer Bedeutung für ein etwaiges Verfahren -- keine Erfolgsprognose, nur Risikofaktoren benennen."
}}

Regeln:
- Verwende ausschließlich Fakten aus der obigen Liste. Erfinde keine Feststellungen.
- Jede Zeile in legal_subsumption_chain braucht eine konkrete beweis_referenz.
- Wenn eine Norm nur auf UNVERIFIZIERT-Feststellungen gestützt werden könnte, nimm sie \
NICHT in legal_subsumption_chain auf, sondern erwähne sie unter offene_punkte einer \
verwandten Zeile oder lasse sie ganz weg.
- anspruchsgrundlage/rechtsfolgen sind Standardrecht (welche Ansprüche eine Norm typischerweise \
auslöst), keine Einzelfallbewertung von Gegenstandswert, Vertragsstrafe oder Frist -- diese \
Parameter kommen ausschließlich aus Mandatsdaten und gehören NICHT in dieses JSON.
- {DISCLAIMER}"""


def review(url: str, company: dict, findings: list[TechnicalFinding]) -> FableReviewResult:
    """Run the Fable-Reviewer. Falls back to a deterministic, clearly-labelled
    stub if no API key is configured (mirrors the existing generate_legal_text
    fallback pattern in main.py). Note: never receives or returns
    MandateParameters -- those are attached separately, by a human, when the
    KI-Uebergabe prompt is (re)built via build_ki_uebergabe_prompt()."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    prompt = build_fable_reviewer_prompt(url, company, findings)
    verified = [f for f in findings if f.verified]

    if api_key and not api_key.startswith("PLACEHOLDER"):
        try:
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={
                    "model": "claude-fable-5",
                    "max_tokens": 3000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = json.loads(resp.json()["content"][0]["text"])
            chain = [LegalSubsumptionRow(**row) for row in data.get("legal_subsumption_chain", [])]
            defenses = [ExpectedDefense(**row) for row in data.get("erwartete_einwendungen", [])]
            return FableReviewResult(
                sachverhalt_prosa=data["sachverhalt_prosa"],
                subsumtion_prosa=data["subsumtion_prosa"],
                legal_subsumption_chain=chain,
                erwartete_einwendungen=defenses,
                prozessuale_risikobewertung=data.get("prozessuale_risikobewertung", ""),
                ki_uebergabe_prompt=build_ki_uebergabe_prompt(url, data["sachverhalt_prosa"], data["subsumtion_prosa"], chain, defenses, data.get("prozessuale_risikobewertung", "")) if verified else None,
            )
        except Exception as e:
            print(f"Fable-Reviewer error, falling back to stub: {e}")

    return _fallback_review(url, company, findings, verified)


def _fallback_review(url: str, company: dict, findings: list[TechnicalFinding], verified: list[TechnicalFinding]) -> FableReviewResult:
    sachverhalt = (
        f"[AUTOMATISCH ERSTELLT — Fable-Reviewer nicht verfügbar, Platzhaltertext] "
        f"Am geprüften Datum wurde die Website {url} untersucht. "
        f"{len(verified)} von {len(findings)} technischen Feststellungen sind menschlich verifiziert."
    )
    subsumtion = (
        "[AUTOMATISCH ERSTELLT, VORLÄUFIG] Ohne aktive Fable-Reviewer-Anbindung kann keine "
        "belastbare Subsumtion erzeugt werden. " + DISCLAIMER
    )
    chain = [
        LegalSubsumptionRow(
            norm="[zu bestimmen]",
            tatbestandsmerkmal="[zu bestimmen]",
            feststellung=f.statement,
            beweis_referenz=f.evidence.inline_ref(),
            offene_punkte="Fable-Reviewer nicht verfügbar — manuelle rechtliche Prüfung durch Kanzlei erforderlich.",
            subsumtion="[Fable-Reviewer nicht verfügbar]",
            ergebnis="offen",
            anspruchsgrundlage="[abhängig von Aktivlegitimation, durch Kanzlei zu bestimmen]",
            rechtsfolgen="[durch Kanzlei zu bestimmen]",
        )
        for f in verified
    ]
    return FableReviewResult(
        sachverhalt_prosa=sachverhalt, subsumtion_prosa=subsumtion, legal_subsumption_chain=chain,
        erwartete_einwendungen=[], prozessuale_risikobewertung="[Fable-Reviewer nicht verfügbar — keine Risikobewertung erzeugt.]",
        ki_uebergabe_prompt=None,
    )


def build_ki_uebergabe_prompt(
    url: str, sachverhalt: str, subsumtion: str, chain: list[LegalSubsumptionRow],
    expected_defenses: list[ExpectedDefense] | None = None,
    prozessuale_risikobewertung: str = "",
    mandate: MandateParameters | None = None,
) -> str:
    """The copy-paste prompt block for the final 'KI-Uebergabe' section.
    Only ever called with verified-derived content (see review() gate above).

    mandate is optional and, when omitted or incomplete, the prompt says so
    explicitly rather than proceeding as if the missing values didn't matter
    -- Aktivlegitimation/Gegenstandswert/Vertragsstrafe/Frist change what a
    correct Abmahnung looks like and must not be silently skipped."""
    expected_defenses = expected_defenses or []
    mandate = mandate or MandateParameters()
    normen = ", ".join(sorted({row.norm for row in chain})) or "[Norm ergänzen]"

    missing = mandate.missing_fields()
    mandate_block = "\n".join(f"{MANDATE_FIELD_LABELS[k]}: {v or '[NOCH NICHT ERGÄNZT]'}" for k, v in mandate.__dict__.items())
    mandate_warning = (
        f"\nACHTUNG — Mandatsdaten unvollständig: {', '.join(missing)} noch nicht ergänzt. "
        "Erstelle den Entwurf trotzdem, aber markiere jede Stelle, die von diesen Angaben abhängt "
        "(insbesondere Fristsetzung, Vertragsstrafeversprechen, Kostenberechnung), deutlich als "
        "'[Platzhalter, durch Kanzlei zu ergänzen]'." if missing else ""
    )

    defenses_block = "\n".join(f"- Einwand: {d.einwendung}\n  Erwiderung: {d.erwiderung} (Bezug: {d.bezug})" for d in expected_defenses) or "[keine erwarteten Einwendungen dokumentiert]"
    claims_block = "\n".join(f"- {row.norm}: {row.anspruchsgrundlage or '[offen]'} → {row.rechtsfolgen or '[offen]'}" for row in chain)

    return f"""Du bist Rechtsanwalt. Erstelle auf Basis des folgenden Sachverhalts und der \
rechtlichen Würdigung einen Entwurf für eine Abmahnung wegen {normen}. \
Halte dich strikt an die Fakten, markiere Unsicherheiten explizit, und ergänze keine \
Tatsachen, die nicht im Sachverhalt oder der Würdigung genannt sind.{mandate_warning}

GEPRÜFTE URL: {url}

SACHVERHALT:
{sachverhalt}

RECHTLICHE WÜRDIGUNG (vorläufig, automatisiert erstellt — von der Kanzlei zu prüfen):
{subsumtion}

NORM-TATBESTAND-BEWEIS-KETTE (inkl. Subsumtion/Ergebnis im Gutachtenstil):
{json.dumps([row.__dict__ for row in chain], ensure_ascii=False, indent=2)}

ANSPRUCHSGRUNDLAGEN UND RECHTSFOLGEN:
{claims_block}

ERWARTETE EINWENDUNGEN DER GEGENSEITE UND MÖGLICHE ERWIDERUNGEN:
{defenses_block}

PROZESSUALE RISIKOBEWERTUNG (vorläufig):
{prozessuale_risikobewertung or "[nicht erzeugt]"}

MANDATS- UND ABMAHNUNGSPARAMETER (aus Mandatsdaten/Kanzlei-Eingabe, nicht aus der technischen Prüfung):
{mandate_block}

Hinweis: Dies ist eine automatisierte Vorprüfung, keine Rechtsberatung. Die rechtliche \
Bewertung und Freigabe obliegt ausschließlich der Kanzlei."""

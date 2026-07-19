"""Fable-Reviewer: structured legal-technical review prompt.

Turns a set of *human-confirmed* technical findings into structured JSON
that drives Ebene B (rechtliche Einordnung), the "Vorlaeufige rechtliche
Subsumtion" prose, and the KI-Uebergabe prompt block.

Hard rule: this module never reads raw detector output (e.g. the mocked
confidence scores in main.py's detect()) directly. It only accepts
TechnicalFinding objects that a human has explicitly marked verified=True.
Unverified findings are rendered as open questions, never as the basis for
a legal claim or a ready-to-send prompt. This is the gate that keeps
unvalidated "AI detection" numbers from turning into a drafted Abmahnung.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import httpx

from evidence import EvidenceItem

DISCLAIMER = "Automatisierte Vorprüfung, keine Rechtsberatung. Rechtliche Bewertung obliegt ausschließlich der Kanzlei."


@dataclass
class TechnicalFinding:
    statement: str          # e.g. "Kein KI-Hinweis im sichtbaren Seitenbereich gefunden"
    evidence: EvidenceItem
    verified: bool = False  # must be explicitly set True by a human reviewer


@dataclass
class LegalSubsumptionRow:
    norm: str                    # "Art. 50 Abs. 4 AI Act"
    tatbestandsmerkmal: str      # "Kennzeichnungspflicht bei KI-generierten Inhalten"
    feststellung: str            # what was technically found
    beweis_referenz: str         # formatted evidence reference string
    offene_punkte: str           # what still needs human/legal review


@dataclass
class FableReviewResult:
    sachverhalt_prosa: str
    subsumtion_prosa: str
    legal_subsumption_chain: list[LegalSubsumptionRow] = field(default_factory=list)
    ki_uebergabe_prompt: str | None = None  # None if gate not satisfied


def build_fable_reviewer_prompt(url: str, company: dict, findings: list[TechnicalFinding]) -> str:
    """The prompt sent to the Fable-Reviewer model. Requests the extended
    JSON schema including legal_subsumption_chain."""
    findings_block = "\n".join(
        f'- [{"VERIFIZIERT" if f.verified else "UNVERIFIZIERT"}] {f.statement} '
        f'(Beweis: {f.evidence.inline_ref()})'
        for f in findings
    )
    return f"""Du bist ein juristisch-technischer Prüfassistent ("Fable-Reviewer") für eine \
deutsche Anwaltskanzlei. Du erstellst KEINE Rechtsberatung, sondern eine strukturierte \
Vorprüfung, die eine Anwältin/ein Anwalt anschließend eigenverantwortlich bewertet.

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
      "tatbestandsmerkmal": "was muss erfüllt sein",
      "feststellung": "was wurde technisch festgestellt (nur VERIFIZIERT)",
      "beweis_referenz": "Anlage/Hash/Seite aus der Feststellung",
      "offene_punkte": "was ist unklar oder braucht menschliche Prüfung"
    }}
  ]
}}

Regeln:
- Verwende ausschließlich Fakten aus der obigen Liste. Erfinde keine Feststellungen.
- Jede Zeile in legal_subsumption_chain braucht eine konkrete beweis_referenz.
- Wenn eine Norm nur auf UNVERIFIZIERT-Feststellungen gestützt werden könnte, nimm sie \
NICHT in legal_subsumption_chain auf, sondern erwähne sie unter offene_punkte einer \
verwandten Zeile oder lasse sie ganz weg.
- {DISCLAIMER}"""


def review(url: str, company: dict, findings: list[TechnicalFinding]) -> FableReviewResult:
    """Run the Fable-Reviewer. Falls back to a deterministic, clearly-labelled
    stub if no API key is configured (mirrors the existing generate_legal_text
    fallback pattern in main.py)."""
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
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = json.loads(resp.json()["content"][0]["text"])
            chain = [LegalSubsumptionRow(**row) for row in data.get("legal_subsumption_chain", [])]
            return FableReviewResult(
                sachverhalt_prosa=data["sachverhalt_prosa"],
                subsumtion_prosa=data["subsumtion_prosa"],
                legal_subsumption_chain=chain,
                ki_uebergabe_prompt=build_ki_uebergabe_prompt(url, data["sachverhalt_prosa"], data["subsumtion_prosa"], chain) if verified else None,
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
        )
        for f in verified
    ]
    return FableReviewResult(sachverhalt_prosa=sachverhalt, subsumtion_prosa=subsumtion, legal_subsumption_chain=chain, ki_uebergabe_prompt=None)


def build_ki_uebergabe_prompt(url: str, sachverhalt: str, subsumtion: str, chain: list[LegalSubsumptionRow]) -> str:
    """The copy-paste prompt block for the final 'KI-Uebergabe' section.
    Only ever called with verified-derived content (see review() gate above)."""
    normen = ", ".join(sorted({row.norm for row in chain})) or "[Norm ergänzen]"
    return f"""Du bist Rechtsanwalt. Erstelle auf Basis des folgenden Sachverhalts und der \
rechtlichen Würdigung einen Entwurf für eine Abmahnung wegen {normen}. \
Halte dich strikt an die Fakten, markiere Unsicherheiten explizit, und ergänze keine \
Tatsachen, die nicht im Sachverhalt oder der Würdigung genannt sind.

GEPRÜFTE URL: {url}

SACHVERHALT:
{sachverhalt}

RECHTLICHE WÜRDIGUNG (vorläufig, automatisiert erstellt — von der Kanzlei zu prüfen):
{subsumtion}

NORM-TATBESTAND-BEWEIS-KETTE:
{json.dumps([row.__dict__ for row in chain], ensure_ascii=False, indent=2)}

Hinweis: Dies ist eine automatisierte Vorprüfung, keine Rechtsberatung. Die rechtliche \
Bewertung und Freigabe obliegt ausschließlich der Kanzlei."""

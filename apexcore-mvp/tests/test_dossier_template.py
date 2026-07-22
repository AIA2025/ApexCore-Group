#!/usr/bin/env python3
"""Smoke tests for the dossier template.

Runs standalone (`python3 tests/test_dossier_template.py`) so it works in
this repo without adding pytest as a hard dependency, but every check is a
plain `test_*` function so pytest picks it up too if it's installed.

These exist because the two real bugs found while building the ARAG/Flatex
examples (a Table row-height overflow, and the KI-Uebergabe prompt being
wired to an empty MandateParameters instead of the real one) were both only
caught by manually rendering and eyeballing the PDF. That doesn't scale --
these tests catch the same class of regression automatically:
  - render_dossier()/render_dossier_markdown() must complete without raising
    for edge-case inputs (empty chain, long field text, unicode, all-
    unverified findings) -- a reportlab LayoutError like the one hit earlier
    raises during doc.build(), so a plain "did it run" check has real value.
  - the KI-Uebergabe prompt must actually reflect the MandateParameters it
    was given, not silently fall back to blank ones.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dossier_template import DossierContext, render_dossier, render_dossier_markdown
from evidence import EvidenceItem
from fable_reviewer import (
    ExpectedDefense,
    FableReviewResult,
    LegalSubsumptionRow,
    MandateParameters,
    TechnicalFinding,
    build_ki_uebergabe_prompt,
)


def _sample_evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(1, "screenshot.png", "Beispiel-Screenshot", page_ref="1", quality="Hoch (Beispiel)"),
        EvidenceItem(2, "log.har", "Beispiel-Netzwerklog", page_ref="1-2", quality="Hoch (Beispiel)"),
    ]


def _sample_findings(evidence: list[EvidenceItem]) -> list[TechnicalFinding]:
    return [
        TechnicalFinding(statement="Verifizierte Beispiel-Feststellung.", evidence=evidence[0], verified=True),
        TechnicalFinding(statement="Unverifizierte Beispiel-Feststellung.", evidence=evidence[1], verified=False),
    ]


def _sample_chain(evidence: list[EvidenceItem]) -> list[LegalSubsumptionRow]:
    return [
        LegalSubsumptionRow(
            norm="Art. 13 Abs. 1 lit. e DSGVO",
            tatbestandsmerkmal="Beispiel-Tatbestandsmerkmal",
            feststellung="Beispiel-Feststellung",
            beweis_referenz=evidence[0].inline_ref(),
            offene_punkte="Beispiel offener Punkt",
            subsumtion="Beispiel-Subsumtionssatz, der Feststellung und Tatbestandsmerkmal verknuepft.",
            ergebnis="(vorläufig) erfüllt",
            anspruchsgrundlage="§ 8 Abs. 1 UWG (Beispiel)",
            rechtsfolgen="Unterlassung (Beispiel)",
        ),
    ]


def _long_mandate() -> MandateParameters:
    # Regression case for the row-height overflow bug: a field long enough
    # to wrap across multiple lines, which previously overlapped the next
    # table row when the Table had a fixed rowHeight.
    return MandateParameters(
        aktivlegitimation=(
            "OFFEN — sehr lange Beispielbegründung, die über mehrere Zeilen umbrechen muss, um "
            "sicherzustellen, dass eine feste Zeilenhoehe in der Mandatsparameter-Tabelle nicht mehr "
            "zu einer Ueberlappung mit der naechsten Zeile fuehrt, egal wie lang der Text wird."
        ),
        passivlegitimation="Beispiel GmbH, Musterstraße 1, 12345 Musterstadt",
    )


def test_render_dossier_minimal_completes():
    ctx = DossierContext(dossier_id="TEST-MIN", url="https://example.test", prufdatum="01.01.2026", company_name="Testfirma GmbH")
    review = FableReviewResult(sachverhalt_prosa="Testtext.", subsumtion_prosa="Testtext.")
    with tempfile.TemporaryDirectory() as tmp:
        out = render_dossier(Path(tmp) / "out.pdf", ctx, [], [], review, [], annotated_images=[])
        assert out.exists()
        assert out.stat().st_size > 1000
        assert out.read_bytes()[:5] == b"%PDF-"
        assert review.ki_uebergabe_prompt is None  # no findings -> gate must hold


def test_render_dossier_full_completes():
    evidence = _sample_evidence()
    findings = _sample_findings(evidence)
    chain = _sample_chain(evidence)
    defenses = [ExpectedDefense(einwendung="Beispiel-Einwand", erwiderung="Beispiel-Erwiderung", bezug="Art. 13 DSGVO")]
    mandate = _long_mandate()
    prompt = build_ki_uebergabe_prompt(
        ctx_url := "https://example.test/seite", "Sachverhalt-Beispiel.", "Subsumtion-Beispiel.",
        chain, defenses, "Risiko-Beispiel.", mandate,
    )
    review = FableReviewResult(
        sachverhalt_prosa="Sachverhalt-Beispiel.", subsumtion_prosa="Subsumtion-Beispiel.",
        legal_subsumption_chain=chain, erwartete_einwendungen=defenses,
        prozessuale_risikobewertung="Risiko-Beispiel.", ki_uebergabe_prompt=prompt,
    )
    ctx = DossierContext(dossier_id="TEST-FULL", url=ctx_url, prufdatum="01.01.2026", company_name="Testfirma GmbH", score=90, risk="HOCH")
    with tempfile.TemporaryDirectory() as tmp:
        out = render_dossier(
            Path(tmp) / "out.pdf", ctx, evidence, findings, review,
            ["Schritt 1.", "Schritt 2."], annotated_images=[], mandate=mandate,
        )
        assert out.exists()
        assert out.stat().st_size > 3000
        assert out.read_bytes()[:5] == b"%PDF-"


def test_render_dossier_markdown_contains_all_sections():
    evidence = _sample_evidence()
    findings = _sample_findings(evidence)
    chain = _sample_chain(evidence)
    mandate = _long_mandate()
    review = FableReviewResult(
        sachverhalt_prosa="Sachverhalt-Beispiel.", subsumtion_prosa="Subsumtion-Beispiel.",
        legal_subsumption_chain=chain,
        erwartete_einwendungen=[ExpectedDefense(einwendung="E", erwiderung="R", bezug="B")],
        prozessuale_risikobewertung="Risiko-Beispiel.",
        ki_uebergabe_prompt="Beispiel-Prompt",
    )
    ctx = DossierContext(dossier_id="TEST-MD", url="https://example.test", prufdatum="01.01.2026", company_name="Testfirma GmbH")
    with tempfile.TemporaryDirectory() as tmp:
        out = render_dossier_markdown(Path(tmp) / "out.md", ctx, evidence, findings, review, ["Schritt 1."], mandate=mandate)
        text = out.read_text(encoding="utf-8")
        for heading in (
            "## 1. Sachverhalt für den anwaltlichen Schriftsatz",
            "## Ebene A — Technische Tatsachen",
            "## Ebene B — Vorläufige rechtliche Einordnung",
            "## Vorläufige rechtliche Subsumtion",
            "## Gutachterliche Prüfung im Detail",
            "## Anspruchsgrundlage und Rechtsfolgen",
            "## Erwartete Einwendungen der Gegenseite und mögliche Erwiderungen",
            "## Prozessuale Risikobewertung",
            "## Ebene C — Anwaltliche Entscheidung",
            "## Anlagen — Beweismittelverzeichnis",
            "## KI-Übergabe",
        ):
            assert heading in text, f"missing section: {heading}"
        assert "Musterstraße 1" in text  # mandate value actually reached the output


def test_ki_uebergabe_prompt_reflects_provided_mandate():
    # Regression test for the wiring bug: build_ki_uebergabe_prompt() must use
    # the mandate it's given, not silently produce a "missing" warning for
    # fields that were in fact provided.
    mandate = MandateParameters(aktivlegitimation="Mitbewerber, geklärt.", passivlegitimation="Beispiel AG")
    chain = _sample_chain(_sample_evidence())
    prompt = build_ki_uebergabe_prompt("https://example.test", "S.", "W.", chain, [], "R.", mandate)
    assert "Mitbewerber, geklärt." in prompt
    assert "Beispiel AG" in prompt
    assert "ACHTUNG" in prompt  # 4 of 6 mandate fields are still blank
    warning_line = next(line for line in prompt.split("\n") if line.startswith("ACHTUNG"))
    assert "Aktivlegitimation" not in warning_line  # was provided, must not be listed as missing
    assert "Passivlegitimation" not in warning_line  # was provided, must not be listed as missing
    assert "Gegenstandswert" in warning_line  # genuinely never set -> must be listed as missing


def test_mandate_missing_fields():
    empty = MandateParameters()
    assert set(empty.missing_fields()) == {"Aktivlegitimation", "Passivlegitimation", "Gegenstandswert", "Vertragsstrafe", "Frist", "Kosten"}
    partial = MandateParameters(aktivlegitimation="x", gegenstandswert="10.000 EUR")
    missing = partial.missing_fields()
    assert "Aktivlegitimation" not in missing
    assert "Gegenstandswert" not in missing
    assert "Passivlegitimation" in missing


def test_evidence_inline_ref_and_annex_row():
    ev = EvidenceItem(3, "datei.pdf", "Beschreibung", page_ref="2", quality="Mittel")
    assert ev.label == "Anlage 3"
    assert "Anlage 3" in ev.inline_ref()
    assert "datei.pdf" in ev.inline_ref()
    row = ev.annex_row()
    assert row == ("Anlage 3", "datei.pdf", "Beschreibung", "2", "N/A", "Mittel")


def run_all() -> int:
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_") and callable(obj)]
    failures = []
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures.append(t.__name__)
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:
            failures.append(t.__name__)
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run_all())

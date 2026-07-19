"""Kanzlei-Dossier PDF renderer — Ebene A / B / C structure.

Layout (in this order, per the redesign spec):
  0. Deckblatt
  1. Sachverhalt fuer den anwaltlichen Schriftsatz
  2. Ebene A  - Technische Tatsachen (jede Aussage mit Beweismittel-Verweis)
  3. Ebene B  - Vorlaeufige rechtliche Einordnung (Tabelle, Pflicht-Disclaimer)
  4. Vorlaeufige rechtliche Subsumtion (Fliesstext, als automatisiert markiert)
  5. Ebene C  - Anwaltliche Entscheidung (Freitext-Bloecke fuer die Kanzlei)
  6. Anlagen  - Beweismittelverzeichnis + annotierte Screenshots
  7. KI-Uebergabe (nur wenn review.ki_uebergabe_prompt gesetzt ist, siehe fable_reviewer.review())

Built on reportlab.platypus so tables/paragraphs wrap correctly, instead of
the manual line-wrapping the previous single-function canvas version used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from evidence import EvidenceItem
from fable_reviewer import DISCLAIMER, FableReviewResult, LegalSubsumptionRow, TechnicalFinding

NAVY = colors.HexColor("#1B3A6B")
WHITE = colors.white
DARK = colors.HexColor("#1A1A2E")
GRAY = colors.HexColor("#6B7A99")
LIGHT_GRAY = colors.HexColor("#EEF1F6")
RED = colors.HexColor("#D62728")
AMBER = colors.HexColor("#B8860B")
GREEN = colors.HexColor("#1E7A34")

PAGE_W, PAGE_H = A4


@dataclass
class DossierContext:
    dossier_id: str
    url: str
    prufdatum: str  # display string, e.g. "17.07.2026, Uhrzeit: [von Kanzlei zu ergaenzen]"
    company_name: str
    company_address: str = ""
    score: float | None = None
    risk: str = ""  # "HOCH" | "MITTEL" | "NIEDRIG"


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H1", parent=ss["Heading1"], textColor=NAVY, fontSize=15, spaceAfter=8, spaceBefore=4))
    ss.add(ParagraphStyle("H2", parent=ss["Heading2"], textColor=DARK, fontSize=11.5, spaceAfter=6, spaceBefore=10))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=9.3, leading=13, alignment=TA_JUSTIFY))
    ss.add(ParagraphStyle("BodySmall", parent=ss["Normal"], fontSize=8.3, leading=11.5, textColor=DARK))
    ss.add(ParagraphStyle("Cell", parent=ss["Normal"], fontSize=8, leading=10.5))
    ss.add(ParagraphStyle("CellHead", parent=ss["Normal"], fontSize=8.3, leading=10.5, textColor=WHITE, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("EvidenceRef", parent=ss["Normal"], fontSize=7.6, leading=10, textColor=NAVY, fontName="Helvetica-Oblique"))
    ss.add(ParagraphStyle("Disclaimer", parent=ss["Normal"], fontSize=8.6, leading=12, textColor=colors.white, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle(
        "Mono", parent=ss["Normal"], fontSize=8, leading=11.5, fontName="Courier",
        backColor=LIGHT_GRAY, borderColor=DARK, borderWidth=0.75, borderPadding=8, borderRadius=2,
    ))
    ss.add(ParagraphStyle("Caption", parent=ss["Normal"], fontSize=7.6, leading=10, textColor=GRAY))
    return ss


# ---------------------------------------------------------------- cover ----

def _draw_cover(c, doc, ctx: DossierContext):
    w, h = PAGE_W, PAGE_H
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, h - 100 * mm, w, 100 * mm, fill=True, stroke=False)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(15 * mm, h - 35 * mm, "RECHTLICHES DOSSIER")
    c.setFont("Helvetica", 11)
    c.drawString(15 * mm, h - 48 * mm, "Kanzlei-Vorlage — Ebene A/B/C")
    c.drawString(15 * mm, h - 58 * mm, "ApexCore Group d.o.o. Beograd")
    c.drawString(15 * mm, h - 68 * mm, f"Dossier-ID: {ctx.dossier_id}")

    y = h - 115 * mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "ZIELWEBSITE:")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y - 8 * mm, (ctx.url or "[nicht übermittelt]")[:90])

    y -= 22 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "PRÜFDATUM:")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y - 8 * mm, ctx.prufdatum)

    y -= 22 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "ZIELFIRMA:")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y - 8 * mm, ctx.company_name)
    if ctx.company_address:
        c.drawString(15 * mm, y - 16 * mm, ctx.company_address)

    if ctx.risk:
        y -= 34 * mm
        risk_color = {"HOCH": RED, "MITTEL": AMBER, "NIEDRIG": GREEN}.get(ctx.risk, GRAY)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 12)
        if ctx.score is not None:
            c.drawString(15 * mm, y, f"FABLE-GESAMTRISIKO-SCORE: {ctx.score}")
            y -= 8 * mm
        c.setFillColor(risk_color)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(15 * mm, y, f"RISIKO: {ctx.risk}")

    y -= 18 * mm
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(15 * mm, y, DISCLAIMER)

    _footer(c, doc, ctx)
    c.restoreState()


def _footer(c, doc, ctx: DossierContext):
    c.saveState()
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(15 * mm, 15 * mm, f"ApexCore Group d.o.o. | Dossier {ctx.dossier_id} | Erstellt: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}")
    c.drawRightString(PAGE_W - 15 * mm, 15 * mm, f"Seite {c.getPageNumber()}")
    c.restoreState()


def _draw_later_page(c, doc, ctx: DossierContext):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 14 * mm, PAGE_W, 14 * mm, fill=True, stroke=False)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(15 * mm, PAGE_H - 9.5 * mm, f"ApexCore Group — Rechtliches Dossier {ctx.dossier_id}")
    c.restoreState()
    _footer(c, doc, ctx)


# ---------------------------------------------------- section: Sachverhalt --

def _section_sachverhalt(ss, ctx: DossierContext, sachverhalt_prosa: str, evidence_items: list[EvidenceItem], chronologie: list[str]) -> list:
    flow = [Paragraph("1. Sachverhalt für den anwaltlichen Schriftsatz", ss["H1"])]
    flow.append(Paragraph(
        f"Untersuchung vom {ctx.prufdatum} — geprüfte URL: {escape(ctx.url or '[nicht übermittelt]')}",
        ss["BodySmall"],
    ))
    flow.append(Spacer(1, 4 * mm))
    for para in sachverhalt_prosa.split("\n\n"):
        if para.strip():
            flow.append(Paragraph(escape(para.strip()).replace("\n", "<br/>"), ss["Body"]))
            flow.append(Spacer(1, 3 * mm))

    flow.append(Paragraph("Anlagenverzeichnis", ss["H2"]))
    rows = [[Paragraph("Anlage", ss["CellHead"]), Paragraph("Datei", ss["CellHead"]), Paragraph("Beschreibung", ss["CellHead"])]]
    for ev in evidence_items:
        rows.append([Paragraph(ev.label, ss["Cell"]), Paragraph(escape(ev.filename), ss["Cell"]), Paragraph(escape(ev.description), ss["Cell"])])
    t = Table(rows, colWidths=[22 * mm, 48 * mm, 105 * mm])
    t.setStyle(_table_style())
    flow.append(t)

    if chronologie:
        flow.append(Spacer(1, 4 * mm))
        flow.append(Paragraph("Chronologische Zusammenfassung", ss["H2"]))
        for entry in chronologie:
            flow.append(Paragraph(f"• {escape(entry)}", ss["BodySmall"]))
    flow.append(PageBreak())
    return flow


# --------------------------------------------------------- section: Ebene A --

def _section_ebene_a(ss, findings: list[TechnicalFinding]) -> list:
    flow = [Paragraph("Ebene A — Technische Tatsachen", ss["H1"])]
    flow.append(Paragraph(
        "Jede Feststellung verweist unmittelbar auf das zugrundeliegende Beweismittel "
        "(Anlage, Datei, Seite, Hash) statt nur gesammelt im Anhang zu erscheinen.",
        ss["BodySmall"],
    ))
    flow.append(Spacer(1, 4 * mm))
    for f in findings:
        tag = "VERIFIZIERT" if f.verified else "UNVERIFIZIERT"
        tag_color = "#1E7A34" if f.verified else "#B8860B"
        flow.append(Paragraph(
            f'<font color="{tag_color}"><b>[{tag}]</b></font> {escape(f.statement)}',
            ss["Body"],
        ))
        flow.append(Paragraph(f"↳ Beweismittel: {escape(f.evidence.inline_ref())}", ss["EvidenceRef"]))
        flow.append(Spacer(1, 2.5 * mm))
    flow.append(PageBreak())
    return flow


# --------------------------------------------------------- section: Ebene B --

def _section_ebene_b(ss, rows: list[LegalSubsumptionRow]) -> list:
    flow = [Paragraph("Ebene B — Vorläufige rechtliche Einordnung", ss["H1"])]

    disclaimer_table = Table(
        [[Paragraph(DISCLAIMER, ss["Disclaimer"])]],
        colWidths=[180 * mm],
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RED),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    flow.append(disclaimer_table)
    flow.append(Spacer(1, 5 * mm))

    header = ["Norm", "Tatbestandsmerkmal", "Feststellung", "Beweismittel-Ref.", "Offene Punkte"]
    data = [[Paragraph(h, ss["CellHead"]) for h in header]]
    for row in rows:
        data.append([
            Paragraph(escape(row.norm), ss["Cell"]),
            Paragraph(escape(row.tatbestandsmerkmal), ss["Cell"]),
            Paragraph(escape(row.feststellung), ss["Cell"]),
            Paragraph(escape(row.beweis_referenz), ss["Cell"]),
            Paragraph(escape(row.offene_punkte), ss["Cell"]),
        ])
    if len(data) == 1:
        data.append([Paragraph("—", ss["Cell"])] * 5)
    t = Table(data, colWidths=[28 * mm, 34 * mm, 42 * mm, 36 * mm, 40 * mm], repeatRows=1)
    t.setStyle(_table_style())
    flow.append(t)
    flow.append(PageBreak())
    return flow


def _table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


# ------------------------------------------------------- section: Subsumtion --

def _section_subsumtion(ss, subsumtion_prosa: str) -> list:
    flow = [Paragraph("Vorläufige rechtliche Subsumtion", ss["H1"])]
    badge = Table([[Paragraph("AUTOMATISIERT GENERIERT · VORLÄUFIG · KEINE RECHTSBERATUNG", ss["Disclaimer"])]], colWidths=[180 * mm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AMBER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    flow.append(badge)
    flow.append(Spacer(1, 4 * mm))
    for para in subsumtion_prosa.split("\n\n"):
        if para.strip():
            flow.append(Paragraph(escape(para.strip()).replace("\n", "<br/>"), ss["Body"]))
            flow.append(Spacer(1, 3 * mm))
    flow.append(PageBreak())
    return flow


# ----------------------------------------------------------- section: Ebene C --

def _blank_box(ss, label: str, height_mm: float = 40) -> Table:
    t = Table([[Paragraph(label, ss["H2"])], [Spacer(1, height_mm * mm)]], colWidths=[180 * mm])
    t.setStyle(TableStyle([
        ("BOX", (0, 1), (0, 1), 0.75, DARK),
        ("TOPPADDING", (0, 0), (-1, 0), 0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
    ]))
    return t


def _section_ebene_c(ss) -> list:
    flow = [Paragraph("Ebene C — Anwaltliche Entscheidung", ss["H1"])]
    flow.append(Paragraph(
        "Dritter Block nach Ebene A (Tatsachen) und Ebene B (vorläufige Einordnung). "
        "Ausschließlich die Kanzlei entscheidet hier verbindlich.",
        ss["BodySmall"],
    ))
    flow.append(Spacer(1, 4 * mm))
    flow.append(_blank_box(ss, "Kanzlei-Notizen", height_mm=45))
    flow.append(Spacer(1, 6 * mm))
    flow.append(_blank_box(ss, "Finale Entscheidung (z.B. Abmahnung / Behördenmeldung / keine Aktion)", height_mm=35))
    flow.append(Spacer(1, 8 * mm))
    sig = Table([[Paragraph("Datum, Unterschrift bearbeitende(r) Anwält(in)", ss["BodySmall"])], [Spacer(1, 12 * mm)]], colWidths=[100 * mm])
    sig.setStyle(TableStyle([("LINEBELOW", (0, 1), (0, 1), 0.75, DARK)]))
    flow.append(sig)
    flow.append(PageBreak())
    return flow


# ------------------------------------------------------------- section: Anlagen --

def _section_annex(ss, evidence_items: list[EvidenceItem], annotated_images: list[tuple[Path, str]]) -> list:
    flow = [Paragraph("Anlagen — Beweismittelverzeichnis", ss["H1"])]
    header = ["Anlage", "Datei", "Beschreibung", "Seite", "SHA-256 (Kurzform)"]
    data = [[Paragraph(h, ss["CellHead"]) for h in header]]
    for ev in evidence_items:
        label, filename, desc, page, sha = ev.annex_row()
        data.append([Paragraph(label, ss["Cell"]), Paragraph(escape(filename), ss["Cell"]), Paragraph(escape(desc), ss["Cell"]), Paragraph(page, ss["Cell"]), Paragraph(sha, ss["Cell"])])
    t = Table(data, colWidths=[20 * mm, 40 * mm, 65 * mm, 20 * mm, 35 * mm], repeatRows=1)
    t.setStyle(_table_style())
    flow.append(t)
    flow.append(PageBreak())

    for img_path, caption in annotated_images:
        if not Path(img_path).exists():
            continue
        flow.append(Paragraph("Annotierter Screenshot", ss["H2"]))
        flow.append(Image(str(img_path), width=180 * mm, height=180 * mm * 9 / 16, kind="proportional"))
        flow.append(Paragraph(escape(caption), ss["Caption"]))
        flow.append(PageBreak())
    return flow


# --------------------------------------------------------- section: KI-Uebergabe --

def _section_ki_uebergabe(ss, prompt: str | None) -> list:
    flow = [Paragraph("KI-Übergabe", ss["H1"])]
    if not prompt:
        flow.append(Paragraph(
            "Kein Prompt verfügbar: Der KI-Übergabe-Block wird ausschließlich auf Basis "
            "menschlich verifizierter Ebene-A-Feststellungen erzeugt (siehe fable_reviewer.review()). "
            "Für diesen Fall liegen keine oder zu wenige verifizierte Feststellungen vor.",
            ss["BodySmall"],
        ))
        return flow
    flow.append(Paragraph(
        "Kopierbarer Prompt-Block. Zur Eingabe in ein LLM zusammen mit den Dossier-Inhalten als Kontext, "
        "zur Erstellung eines ersten Abmahnungs-/Schriftsatz-Entwurfs. Ersetzt keine anwaltliche Prüfung.",
        ss["BodySmall"],
    ))
    flow.append(Spacer(1, 3 * mm))
    # A bare Paragraph (not a single-cell Table) so it can split across pages
    # if the prompt is long -- Table rows don't paginate, Paragraphs do.
    mono_text = escape(prompt).replace("\n", "<br/>")
    flow.append(Paragraph(mono_text, ss["Mono"]))
    return flow


# ------------------------------------------------------------------- entry --

def render_dossier(
    output_path: str | Path,
    ctx: DossierContext,
    evidence_items: list[EvidenceItem],
    findings: list[TechnicalFinding],
    review: FableReviewResult,
    chronologie: list[str],
    annotated_images: list[tuple[Path, str]],
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ss = _styles()

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=22 * mm, bottomMargin=22 * mm,
        title=f"Rechtliches Dossier {ctx.dossier_id}",
    )

    story: list = [PageBreak()]
    story += _section_sachverhalt(ss, ctx, review.sachverhalt_prosa, evidence_items, chronologie)
    story += _section_ebene_a(ss, findings)
    story += _section_ebene_b(ss, review.legal_subsumption_chain)
    story += _section_subsumtion(ss, review.subsumtion_prosa)
    story += _section_ebene_c(ss)
    story += _section_annex(ss, evidence_items, annotated_images)
    story += _section_ki_uebergabe(ss, review.ki_uebergabe_prompt)

    def on_first(c, d):
        _draw_cover(c, d, ctx)

    def on_later(c, d):
        _draw_later_page(c, d, ctx)

    doc.build(story, onFirstPage=on_first, onLaterPages=on_later)
    return output_path

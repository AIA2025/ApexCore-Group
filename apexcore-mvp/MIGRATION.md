# Dossier-Template-Redesign — Migrationshinweise

Gebaut in diesem Repo (`AIA2025/ApexCore-Group`), weil diese Session keinen Zugriff
auf `/data/apexcore` (KVM8) hat — dort läuft laut Tageszusammenfassung vom
17.07.2026 die echte, validierte Dossier-Pipeline (`browser_capture.py`,
`gdpr_consent_check.py`, `kanzlei_summary.py`, ...). Dieses Verzeichnis ist
dafür gedacht, von einer Claude-Code-Session mit KVM8-Zugriff übernommen zu werden.

## Neue Module (apexcore-mvp/)

- `evidence.py` — `EvidenceItem`: Anlage-Nr., Datei, Beschreibung, Seite, SHA-256.
  `inline_ref()` liefert den Kurzverweis, der überall im Dossier neben einer
  Aussage steht.
- `screenshot_annotate.py` — Pillow-basierte Bounding-Box/Pfeil-Overlays für
  `page-detail.png`-artige Screenshots. `Annotation(box, label, kind)`,
  `kind="violation"` (durchgezogen) oder `"missing"` (gestrichelt, für
  "erwarteter Hinweis fehlt").
- `fable_reviewer.py` — Prompt + Schema für die strukturierte Vorprüfung,
  inkl. neuem `legal_subsumption_chain`-Key (norm/tatbestandsmerkmal/
  feststellung/beweis_referenz/offene_punkte). **Harte Regel:**
  `TechnicalFinding.verified` muss von einem Menschen gesetzt werden.
  Nur verifizierte Feststellungen fließen in Ebene B oder den
  KI-Übergabe-Prompt; unverifizierte landen ausschließlich unter
  "Offene Punkte". Diese Gate-Logik nicht umgehen.
- `dossier_template.py` — `render_dossier()`: baut das PDF in der Reihenfolge
  Sachverhalt → Ebene A → Ebene B → Subsumtion → Ebene C → Anlagen →
  KI-Übergabe.

## Anbindung an die echte Pipeline (Vorschlag)

1. `browser_capture.py` / `gdpr_consent_check.py`-Output → Liste von
   `EvidenceItem` (echte Dateien aus `data/cases/<CASE-ID>/`, echte SHA-256
   via `file_path=`) und `TechnicalFinding` (mit `verified=True` nur, wenn ein
   Mensch die Feststellung geprüft hat — z.B. das bestehende
   Kanzlei-Review, nicht automatisch aus dem Scraper).
2. `kanzlei_summary.py` (2-Seiten-Minimalpaket) kann `render_dossier()`
   direkt aufrufen statt eigenes PDF-Layout zu pflegen.
3. Reale annotierte Screenshots: `screenshot_annotate.annotate_screenshot()`
   auf das echte `page-detail.png` aus dem Case-Ordner anwenden, nicht auf
   die Mock-Bilder aus `examples/_mock_screenshot.py`.
4. `fable_reviewer.review()` erwartet echte `TechnicalFinding`-Objekte; wenn
   der bestehende Fable-Standard (`docs/23-fable-plausibility-review-standard.md`
   in apex-core-central) bereits ein GDPR-Schema liefert, dessen Output auf
   `TechnicalFinding`/`LegalSubsumptionRow` mappen statt zu duplizieren.

## Beispiel

`examples/arag_demo.py` — vollständiger Durchlauf für Fall 1 (ARAG SE,
AX-2026-0E8E4D2534) mit den Fakten aus der Tageszusammenfassung. Werte, die
nicht übermittelt wurden (genaue URL, Uhrzeit, echte Hashes/Dateinamen), sind
als sichtbare Platzhalter markiert — vor Versand durch die Kanzlei mit den
echten Werten aus dem Case-Ordner ersetzen. Ausführen:

```bash
cd apexcore-mvp/examples && python3 arag_demo.py
```

## `apexcore-mvp/main.py` (dieses Repo)

`detect()` liefert weiterhin `random.uniform()`-Mock-Scores (Kommentar im
Code). `assemble_pdf()` markiert die daraus gebaute Feststellung deshalb als
`verified=False` — das Live-`/scan`-Ergebnis dieses MVP enthält also nie
automatisch Ebene-B-Zeilen oder einen KI-Übergabe-Prompt, nur einen
"nicht verifiziert"-Hinweis. Das bleibt so, bis `detect()` durch eine echte,
menschlich nachprüfbare Methode ersetzt wird.

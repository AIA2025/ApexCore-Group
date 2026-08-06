# LinkedIn-Clip „Art. 50 KI-VO“

12-Sekunden-Clip im Format 9:16 für LinkedIn, Zielgruppe Fachanwältinnen und
Fachanwälte für IT- und Wettbewerbsrecht (DACH).

**Ergebnis:** `out/art50_linkedin_9x16.mp4` — 1080 × 1920, 12,00 s, 30 fps,
H.264 High 4.2 / yuv420p / bt709, stille AAC-Tonspur, `+faststart`, **0,54 MB**.
Untertitel sind eingebrannt; `out/art50_linkedin_9x16.srt` liegt als Sidecar bei.

## Erzeugen

```bash
./fetch_fonts.sh          # Source Serif 4 + JetBrains Mono (SIL OFL 1.1)
python3 render_clip.py    # → out/art50_linkedin_9x16.mp4 + .srt
```

Voraussetzungen: `ffmpeg` (libx264, aac) und `pillow`. Jedes Frame wird
deterministisch mit Pillow gezeichnet und als rohes RGB an ffmpeg gepiped —
es entstehen keine Zwischendateien. Laufzeit ca. 30 s.

Einzelframe zur Layoutkontrolle:

```bash
python3 render_clip.py --still 9.35     # schreibt ein PNG nach out/
```

## Kennzeichnung nach Art. 50 KI-VO

Der Clip enthält **keine synthetische Stimme und keine KI-generierte Person**.
Auf dem Buildsystem war kein Schlüssel für HeyGen, Synthesia oder ElevenLabs
hinterlegt; der Clip besteht ausschließlich aus animierten Textkarten, die
deterministisch aus dem redaktionell verfassten Skript gerendert werden.

Damit wird die Offenlegungspflicht für Deepfakes aus **Art. 50 Abs. 4 KI-VO**
nicht ausgelöst — es fehlt an Bild-, Ton- oder Videoinhalten, die
existierenden Personen, Gegenständen oder Ereignissen nachempfunden sind. Ein
eingebranntes „KI-generiert“-Label wäre hier sachlich unzutreffend. Gerade für
ein Produkt, das die Durchsetzung dieser Kennzeichnungspflicht anbietet, ist
ein falsch gesetztes Label das größere Risiko als ein fehlendes.

Zur Transparenz ist die Produktionsweise stattdessen in den
Container-Metadaten des MP4 dokumentiert:

```bash
ffprobe -v error -show_entries format_tags=comment out/art50_linkedin_9x16.mp4
```

**Sobald ein Voiceover oder ein Avatar ergänzt wird**, ist in `render_clip.py`

```python
AI_DISCLOSURE = True
```

zu setzen. Dann wird ein dauerhaft sichtbares Label direkt unter der Kopflinie
eingebrannt (`AI_DISCLOSURE_TEXT` anpassen, Vorgabe:
`KI-GENERIERTE STIMME · ART. 50 KI-VO`). Der Schalter ist getestet.

Die Einordnung beschreibt die Produktionsentscheidung, nicht die rechtliche
Bewertung — die liegt bei der Kanzlei.

## Drehbuch

Vier Sätze, vier Schnitte, zehn Einblendungen mit **maximal fünf Wörtern**:

| # | Szene | Einblendung | Dauer |
|---|-------|-------------|-------|
| 1 | 00,00–03,10 | „Seit dem 2. August“ | 1,05 s |
| 2 | | „ist Art. 50 der KI-Verordnung“ | 1,25 s |
| 3 | | „Pflicht.“ | 0,80 s |
| 4 | 03,10–05,80 | „Die Verstöße bleiben trotzdem“ | 1,35 s |
| 5 | | „fast alle unentdeckt.“ | 1,35 s |
| 6 | 05,80–09,20 | „Weil forensische Beweisführung“ | 1,05 s |
| 7 | | „Zeit und Know-how kostet,“ | 1,15 s |
| 8 | | „das im Kanzleialltag fehlt.“ | 1,20 s |
| 9 | 09,20–12,00 | „Ich liefere das gerichtsfeste Dossier,“ | 1,45 s |
| 10 | | „Sie die rechtliche Bewertung.“ | 1,35 s |

Das Tempo liegt bei rund 195 Wörtern pro Minute und damit über der für
Untertitel üblichen Leserate von 160–180 wpm. Das ergibt sich zwingend aus
39 Wörtern in 12 Sekunden. Abhilfe, falls gewünscht: `DURATION` in
`render_clip.py` auf 14–15 s erhöhen — die Dauern der Einblendungen sind
Einzelwerte im Drehbuch und werden gegen `DURATION` geprüft.

## Gestaltung

* Marineblau `#16233B` auf Papierweiß `#EEF1F6`. Szene 4 läuft invertiert;
  der Wechsel erfolgt als Farbwischer von unten (0,40 s).
* Headlines in **Source Serif 4** (variabel, `wght 600`, `opsz 60`),
  Größe automatisch zwischen 108 px und 64 px eingepasst, oben ausgerichtet,
  damit der Satzspiegel zwischen zwei- und dreizeiligen Karten nicht springt.
* Technische Details in **JetBrains Mono** mit gesperrter Auszeichnung.
* Keine weitere Akzentfarbe: Hierarchie entsteht über Deckkraftstufen des
  Marineblaus und die Invertierung.
* Sämtliche Zahlen und Nebentexte sind qualitativ. Es wird **keine
  Detektionsquote** oder sonstige Statistik behauptet — in einem
  Rechtsmarketing-Asset wäre eine erfundene Kennzahl ein echtes Problem.
  Das einzige Datum im Bild, `02 · 08 · 2026`, ist der Geltungsbeginn.

## Schriften

Source Serif 4 und JetBrains Mono stehen unter der SIL Open Font License 1.1.
Sie werden per `fetch_fonts.sh` aus dem Repository `google/fonts` geladen und
bewusst nicht mitversioniert.

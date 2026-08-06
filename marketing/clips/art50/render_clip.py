#!/usr/bin/env python3
"""
LinkedIn-Clip "Art. 50 KI-VO" — 1080x1920 (9:16), 12,00 s, 30 fps.

Rein typografischer Clip: jedes Frame wird deterministisch mit Pillow
gezeichnet und als rohes RGB an ffmpeg gepiped. Es kommt weder eine
KI-generierte Person noch eine synthetische Stimme zum Einsatz
(siehe AI_DISCLOSURE unten und README.md).

    python3 render_clip.py [--out PFAD] [--fps 30] [--crf 19]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Kennzeichnung nach Art. 50 KI-VO
# ---------------------------------------------------------------------------
# Dieser Clip enthält KEINE synthetische Stimme und KEINE KI-generierte
# Person. Die Kennzeichnungspflicht aus Art. 50 Abs. 4 KI-VO (Deepfake)
# wird dadurch nicht ausgelöst; ein "KI-generiert"-Badge wäre hier sachlich
# unzutreffend. Sobald ein Voiceover (ElevenLabs o. ä.) oder ein Avatar
# (HeyGen/Synthesia) ergänzt wird, ist der Schalter auf True zu setzen —
# dann wird ein sichtbares, dauerhaftes Label eingebrannt.
AI_DISCLOSURE = False
AI_DISCLOSURE_TEXT = "KI-GENERIERTE STIMME · ART. 50 KI-VO"

# ---------------------------------------------------------------------------
# Format & Marke
# ---------------------------------------------------------------------------
W, H = 1080, 1920
DURATION = 12.0

INK = (0x16, 0x23, 0x3B)      # Marineblau
PAPER = (0xEE, 0xF1, 0xF6)    # Papierweiß

MARGIN = 96
COL = W - 2 * MARGIN          # 888 px Satzspiegel

FONT_DIR = Path(__file__).resolve().parent / "fonts"
SERIF_TTF = FONT_DIR / "SourceSerif4[opsz,wght].ttf"
MONO_TTF = FONT_DIR / "JetBrainsMono[wght].ttf"


@dataclass(frozen=True)
class Palette:
    """Vordergrund/Hintergrund — Szene 4 läuft invertiert."""

    fg: tuple
    bg: tuple

    def tint(self, alpha: float) -> tuple:
        """Vordergrundfarbe mit Deckkraft 0..1 als RGBA."""
        return (*self.fg, max(0, min(255, round(alpha * 255))))


LIGHT = Palette(fg=INK, bg=PAPER)
DARK = Palette(fg=PAPER, bg=INK)


# ---------------------------------------------------------------------------
# Schriften
# ---------------------------------------------------------------------------
@lru_cache(maxsize=256)
def serif(size: int, wght: int = 600, opsz: int = 60) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(SERIF_TTF), size)
    f.set_variation_by_axes([wght, opsz])
    return f


@lru_cache(maxsize=256)
def mono(size: int, wght: int = 500) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(MONO_TTF), size)
    f.set_variation_by_axes([wght])
    return f


# ---------------------------------------------------------------------------
# Drehbuch — 4 Sätze, 10 Einblendungen à max. 5 Wörter
# ---------------------------------------------------------------------------
@dataclass
class Scene:
    eyebrow: str                 # Mono-Zeile über der Headline
    chunks: list                 # (Text, Dauer in s)
    accent: str                  # Schlüssel für den unteren Akzent
    accent_data: tuple = ()
    palette: Palette = LIGHT
    sentence: str = ""


SCENES: list[Scene] = [
    Scene(
        eyebrow="VO (EU) 2024/1689 · ART. 50",
        chunks=[
            ("Seit dem 2. August", 1.05),
            ("ist Art. 50 der KI-Verordnung", 1.25),
            ("Pflicht.", 0.80),
        ],
        accent="date",
        accent_data=("02 · 08 · 2026", "GELTUNGSBEGINN"),
        sentence="Seit dem 2. August ist Art. 50 der KI-Verordnung Pflicht.",
    ),
    Scene(
        eyebrow="TRANSPARENZ- UND KENNZEICHNUNGSPFLICHT",
        chunks=[
            ("Die Verstöße bleiben trotzdem", 1.35),
            ("fast alle unentdeckt.", 1.35),
        ],
        accent="triad",
        accent_data=("UNMARKIERT", "UNBEMERKT", "UNVERFOLGT"),
        sentence="Die Verstöße bleiben trotzdem fast alle unentdeckt.",
    ),
    Scene(
        eyebrow="AUFWAND FORENSISCHER BEWEISFÜHRUNG",
        chunks=[
            ("Weil forensische Beweisführung", 1.05),
            ("Zeit und Know-how kostet,", 1.15),
            ("das im Kanzleialltag fehlt.", 1.20),
        ],
        accent="chips",
        accent_data=("ZEIT", "KNOW-HOW"),
        sentence="Weil forensische Beweisführung Zeit und Know-how kostet, "
                 "das im Kanzleialltag fehlt.",
    ),
    Scene(
        eyebrow="ARBEITSTEILUNG",
        chunks=[
            ("Ich liefere das gerichtsfeste Dossier,", 1.45),
            ("Sie die rechtliche Bewertung.", 1.35),
        ],
        accent="split",
        accent_data=(("APEXCORE", "DOSSIER"), ("KANZLEI", "BEWERTUNG")),
        palette=DARK,
        sentence="Ich liefere das gerichtsfeste Dossier, Sie die rechtliche Bewertung.",
    ),
]

INVERT_AT = sum(d for s in SCENES[:3] for _, d in s.chunks)  # Start Szene 4
INVERT_WIPE = 0.40                                            # Dauer des Farbwischers

# Vertikales Raster — Headline oben ausgerichtet, damit der Satzspiegel
# zwischen zwei- und dreizeiligen Einblendungen nicht springt.
Y_KICKER = 148
Y_RULE = 206
Y_EYEBROW = 560       # Grundlinie der Mono-Zeile
Y_HEADLINE_TOP = 660  # Oberkante des Headline-Blocks
Y_ACCENT = 1210       # Oberkante der Akzentzone
Y_PROGRESS = 1700
Y_FOOTER = 1772

CHUNK_IN = 0.16       # Einblendung
CHUNK_OUT = 0.10      # Ausblendung


@dataclass
class Cue:
    text: str
    start: float
    end: float
    scene: int
    scene_start: float
    scene_end: float
    fields: dict = field(default_factory=dict)


def build_timeline() -> list[Cue]:
    cues: list[Cue] = []
    t = 0.0
    for si, sc in enumerate(SCENES):
        s_start = t
        s_end = t + sum(d for _, d in sc.chunks)
        for text, dur in sc.chunks:
            cues.append(Cue(text, t, t + dur, si, s_start, s_end))
            t += dur
    total = round(t, 4)
    if abs(total - DURATION) > 1e-6:
        raise SystemExit(f"Drehbuch dauert {total}s statt {DURATION}s")
    return cues


TIMELINE = build_timeline()


# ---------------------------------------------------------------------------
# Zeichen-Helfer
# ---------------------------------------------------------------------------
def ease_out(t: float) -> float:
    """Kubisches Ease-Out, t in 0..1."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def chunk_anim(cue: Cue, t: float) -> tuple:
    """(Deckkraft, vertikaler Versatz) für eine Einblendung."""
    if t < cue.start or t >= cue.end:
        return 0.0, 0.0
    since = t - cue.start
    left = cue.end - t
    if since < CHUNK_IN:
        p = ease_out(since / CHUNK_IN)
        return p, (1.0 - p) * 26.0
    if left < CHUNK_OUT:
        p = ease_out(left / CHUNK_OUT)
        return p, (1.0 - p) * -10.0
    return 1.0, 0.0


def tracked(draw, xy, text, font, fill, tracking=0.0, anchor="ls"):
    """Text mit Sperrung (Letterspacing) — Pillow kennt kein tracking."""
    chars = list(text)
    widths = [font.getlength(c) for c in chars]
    total = sum(widths) + tracking * max(0, len(chars) - 1)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    for c, w in zip(chars, widths):
        draw.text((x, y), c, font=font, fill=fill, anchor="l" + anchor[1])
        x += w + tracking
    return total


def tracked_width(text: str, font, tracking: float = 0.0) -> float:
    return sum(font.getlength(c) for c in text) + tracking * max(0, len(text) - 1)


def wrap(text: str, font, max_width: float) -> list:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if font.getlength(trial) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


@lru_cache(maxsize=64)
def fit_headline(text: str, max_width: int = COL, max_lines: int = 3) -> tuple:
    """Größte Schriftgröße, bei der der Text in Spalte und Zeilenzahl passt."""
    for size in range(108, 63, -2):
        f = serif(size, wght=600, opsz=60)
        lines = wrap(text, f, max_width)
        if len(lines) <= max_lines and all(f.getlength(l) <= max_width for l in lines):
            return size, tuple(lines)
    f = serif(64, wght=600, opsz=60)
    return 64, tuple(wrap(text, f, max_width))


# ---------------------------------------------------------------------------
# Akzentzone je Szene
# ---------------------------------------------------------------------------
def draw_accent(d, sc: Scene, pal: Palette, alpha: float, dy: float):
    if alpha <= 0.01:
        return
    y = Y_ACCENT + dy
    cx = W / 2

    if sc.accent == "date":
        date, label = sc.accent_data
        tracked(d, (cx, y + 62), date, mono(64, 600),
                pal.tint(0.92 * alpha), tracking=6, anchor="ms")
        tracked(d, (cx, y + 122), label, mono(24, 500),
                pal.tint(0.50 * alpha), tracking=7, anchor="ms")

    elif sc.accent == "triad":
        f = mono(28, 500)
        parts, gap, trk = sc.accent_data, 22, 5
        widths = [tracked_width(p, f, trk) for p in parts]
        sep_w = f.getlength("·")
        total = sum(widths) + (len(parts) - 1) * (2 * gap + sep_w)
        x = cx - total / 2
        for i, (p, w) in enumerate(zip(parts, widths)):
            tracked(d, (x, y + 70), p, f, pal.tint(0.78 * alpha), tracking=trk)
            x += w
            if i < len(parts) - 1:
                d.text((x + gap, y + 70), "·", font=f,
                       fill=pal.tint(0.35 * alpha), anchor="ls")
                x += gap * 2 + sep_w

    elif sc.accent == "chips":
        f = mono(30, 600)
        pad_x, pad_h, gap = 30, 60, 22
        widths = [f.getlength(p) + 2 * pad_x for p in sc.accent_data]
        total = sum(widths) + gap * (len(widths) - 1)
        x = cx - total / 2
        for p, w in zip(sc.accent_data, widths):
            d.rounded_rectangle([x, y + 34, x + w, y + 34 + pad_h], radius=6,
                                outline=pal.tint(0.34 * alpha), width=2)
            d.text((x + w / 2, y + 34 + pad_h / 2 + 1), p, font=f,
                   fill=pal.tint(0.88 * alpha), anchor="mm")
            x += w + gap

    elif sc.accent == "split":
        left, right = sc.accent_data
        f_who, f_what, gap = mono(26, 600), mono(34, 500), 92
        col_w = lambda c: max(tracked_width(c[0], f_who, 5),
                              tracked_width(c[1], f_what, 3))
        wl, wr = col_w(left), col_w(right)
        x0 = cx - (wl + gap + wr) / 2          # Gruppe als Ganzes zentrieren
        mid = x0 + wl + gap / 2
        d.line([mid, y + 26, mid, y + 132], fill=pal.tint(0.26 * alpha), width=2)
        for (who, what), ax, anchor in ((left, x0 + wl, "r"),
                                        (right, x0 + wl + gap, "l")):
            tracked(d, (ax, y + 66), who, f_who,
                    pal.tint(0.55 * alpha), tracking=5, anchor=anchor + "s")
            tracked(d, (ax, y + 116), what, f_what,
                    pal.tint(0.95 * alpha), tracking=3, anchor=anchor + "s")


# ---------------------------------------------------------------------------
# Frame
# ---------------------------------------------------------------------------
def render_frame(t: float, pal: Palette) -> Image.Image:
    img = Image.new("RGB", (W, H), pal.bg)
    d = ImageDraw.Draw(img, "RGBA")

    cue = next((c for c in TIMELINE if c.start <= t < c.end), TIMELINE[-1])
    sc = SCENES[cue.scene]
    alpha, dy = chunk_anim(cue, t)

    # Szenenweiche Ein-/Ausblendung für die statischen Szenenelemente
    s_in = min(1.0, (t - cue.scene_start) / 0.30)
    s_out = min(1.0, max(0.0, (cue.scene_end - t) / 0.22))
    s_alpha = ease_out(s_in) * ease_out(s_out)
    s_dy = (1.0 - ease_out(s_in)) * 16.0

    # --- Kopfzeile ---------------------------------------------------------
    tracked(d, (MARGIN, Y_KICKER), "APEXCORE · KI-FORENSIK", mono(24, 600),
            pal.tint(0.62), tracking=7)
    tracked(d, (W - MARGIN, Y_KICKER), f"0{cue.scene + 1} / 04", mono(24, 500),
            pal.tint(0.42), tracking=7, anchor="rs")
    d.line([MARGIN, Y_RULE, W - MARGIN, Y_RULE], fill=pal.tint(0.18), width=2)

    # --- Eyebrow -----------------------------------------------------------
    tracked(d, (MARGIN, Y_EYEBROW + s_dy), sc.eyebrow, mono(26, 500),
            pal.tint(0.55 * s_alpha), tracking=6)
    d.line([MARGIN, Y_EYEBROW + 26 + s_dy, MARGIN + 64, Y_EYEBROW + 26 + s_dy],
           fill=pal.tint(0.45 * s_alpha), width=3)

    # --- Headline (= eingebrannter Untertitel) -----------------------------
    size, lines = fit_headline(cue.text)
    f = serif(size, wght=600, opsz=60)
    lh = size * 1.15
    top = Y_HEADLINE_TOP + dy
    for i, line in enumerate(lines):
        d.text((MARGIN, top + i * lh + lh * 0.5), line, font=f,
               fill=pal.tint(alpha), anchor="lm")

    # --- Akzentzone --------------------------------------------------------
    draw_accent(d, sc, pal, s_alpha, s_dy)

    # --- Fortschritt & Fußzeile -------------------------------------------
    p = max(0.0, min(1.0, t / DURATION))
    d.line([MARGIN, Y_PROGRESS, W - MARGIN, Y_PROGRESS], fill=pal.tint(0.14), width=4)
    if p > 0:
        d.line([MARGIN, Y_PROGRESS, MARGIN + COL * p, Y_PROGRESS],
               fill=pal.tint(0.85), width=4)

    tracked(d, (MARGIN, Y_FOOTER), "apexcore.group", mono(23, 500),
            pal.tint(0.55), tracking=3)
    tracked(d, (W - MARGIN, Y_FOOTER), "ART. 50 KI-VO · SEIT 02.08.2026",
            mono(23, 500), pal.tint(0.42), tracking=3, anchor="rs")

    if AI_DISCLOSURE:
        bw, bh = 470, 54
        bx, by = MARGIN, Y_RULE + 34
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=8,
                            fill=pal.tint(0.92))
        d.text((bx + bw / 2, by + bh / 2 + 1), AI_DISCLOSURE_TEXT,
               font=mono(21, 700), fill=(*pal.bg, 255), anchor="mm")

    return img


def frame_at(t: float) -> Image.Image:
    """Frame inkl. Farbwischer beim Übergang in die invertierte Szene 4."""
    if t < INVERT_AT:
        return render_frame(t, LIGHT)
    if t >= INVERT_AT + INVERT_WIPE:
        return render_frame(t, DARK)

    p = ease_out((t - INVERT_AT) / INVERT_WIPE)
    light = render_frame(t, LIGHT)
    dark = render_frame(t, DARK)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, H - H * p, W, H], fill=255)
    return Image.composite(dark, light, mask)


# ---------------------------------------------------------------------------
# Untertitel-Sidecar
# ---------------------------------------------------------------------------
def srt_time(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def write_srt(path: Path):
    out = []
    for i, c in enumerate(TIMELINE, 1):
        out.append(f"{i}\n{srt_time(c.start)} --> {srt_time(c.end)}\n{c.text}\n")
    path.write_text("\n".join(out), encoding="utf-8")


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------
def encode(out_path: Path, fps: int, crf: int):
    n = int(round(DURATION * fps))
    comment = (
        "Typografischer Motion-Clip, deterministisch aus redaktionellem Text "
        "gerendert (Pillow/ffmpeg). Keine synthetische Stimme, keine "
        "KI-generierte Person, kein Deepfake i.S.v. Art. 50 Abs. 4 KI-VO."
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
        "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-shortest",
        "-c:v", "libx264", "-preset", "slow", "-profile:v", "high",
        "-level", "4.2", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-x264-params", f"keyint={fps * 2}:min-keyint={fps}:scenecut=0",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        "-metadata", f"title=Art. 50 KI-VO — gerichtsfeste Beweisführung",
        "-metadata", f"comment={comment}",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(n):
            proc.stdin.write(frame_at(i / fps).tobytes())
            if i % 60 == 0:
                print(f"  Frame {i:3d}/{n}", file=sys.stderr)
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg fehlgeschlagen")


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--out", type=Path, default=here / "out" / "art50_linkedin_9x16.mp4")
    ap.add_argument("--fps", type=int, default=30)
    # CRF 14 statt des üblichen 19: Flächen sind einfarbig, das Budget von
    # 30 MB wird bei Weitem nicht ausgeschöpft, und die Serifen bleiben sauber.
    ap.add_argument("--crf", type=int, default=14)
    ap.add_argument("--still", type=float, default=None,
                    help="Statt Video ein einzelnes Frame zu diesem Zeitpunkt als PNG")
    args = ap.parse_args()

    for ttf in (SERIF_TTF, MONO_TTF):
        if not ttf.exists():
            raise SystemExit(f"Schrift fehlt: {ttf}\nBitte ./fetch_fonts.sh ausführen.")

    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.still is not None:
        png = args.out.with_suffix("").with_name(
            f"{args.out.stem}_t{args.still:0.2f}".replace(".", "-") + ".png")
        frame_at(args.still).save(png)
        print(png)
        return

    print(f"Rendere {int(DURATION * args.fps)} Frames @ {args.fps} fps …", file=sys.stderr)
    encode(args.out, args.fps, args.crf)
    write_srt(args.out.with_suffix(".srt"))
    size_mb = args.out.stat().st_size / 1e6
    print(f"{args.out}  ({size_mb:.2f} MB)")
    print(f"{args.out.with_suffix('.srt')}")


if __name__ == "__main__":
    main()

"""Visual annotation of forensic screenshots.

Draws red bounding boxes, arrows and labels onto a page screenshot so a
reader can see immediately *where* a violation is visible, or *where* an
expected notice is missing, without hunting through the full-page image.
Pure Pillow, no external services.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RED = (214, 39, 40, 255)
LABEL_BG = (214, 39, 40, 230)
LABEL_FG = (255, 255, 255, 255)


@dataclass
class Annotation:
    box: tuple[int, int, int, int]  # x0, y0, x1, y1 in source-image pixel coords
    label: str
    kind: str = "violation"  # "violation" (found) | "missing" (expected but absent)


def _load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def annotate_screenshot(src_path: str | Path, dest_path: str | Path, annotations: list[Annotation]) -> Path:
    """Overlay bounding boxes/arrows/labels on src_path, write result to dest_path."""
    src_path, dest_path = Path(src_path), Path(dest_path)
    base = Image.open(src_path).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(max(14, base.width // 90))
    line_w = max(3, base.width // 400)

    for i, ann in enumerate(annotations, start=1):
        x0, y0, x1, y1 = ann.box
        dash = ann.kind == "missing"
        _draw_box(draw, (x0, y0, x1, y1), line_w, dashed=dash)

        tag = f"[{i}] {ann.label}"
        text_bbox = draw.textbbox((0, 0), tag, font=font)
        tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        pad = 6
        label_x, label_y = x0, max(0, y0 - th - 2 * pad - 6)
        draw.rectangle([label_x, label_y, label_x + tw + 2 * pad, label_y + th + 2 * pad], fill=LABEL_BG)
        draw.text((label_x + pad, label_y + pad), tag, font=font, fill=LABEL_FG)
        # connector between label and box
        draw.line([(label_x + 10, label_y + th + 2 * pad), (x0 + 10, y0)], fill=RED, width=line_w)

    composed = Image.alpha_composite(base, overlay).convert("RGB")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save(dest_path, "PNG")
    return dest_path


def _draw_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], width: int, dashed: bool = False) -> None:
    x0, y0, x1, y1 = box
    if not dashed:
        draw.rectangle([x0, y0, x1, y1], outline=RED, width=width)
        return
    # dashed rectangle for "expected but missing" markers
    dash_len, gap_len = 14, 8
    for (sx, sy, ex, ey) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        _dashed_line(draw, (sx, sy), (ex, ey), width, dash_len, gap_len)


def _dashed_line(draw: ImageDraw.ImageDraw, start, end, width, dash_len, gap_len) -> None:
    import math

    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0)
    if length == 0:
        return
    dx, dy = (x1 - x0) / length, (y1 - y0) / length
    pos = 0.0
    while pos < length:
        seg_end = min(pos + dash_len, length)
        draw.line([(x0 + dx * pos, y0 + dy * pos), (x0 + dx * seg_end, y0 + dy * seg_end)], fill=RED, width=width)
        pos += dash_len + gap_len

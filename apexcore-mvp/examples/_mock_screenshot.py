"""Builds a clearly-labelled MOCKUP page screenshot for template demos.

This is NOT real captured evidence. It exists only so the dossier template
and the Pillow annotation step can be demonstrated end-to-end without a real
page-detail.png from a case folder. Every image it produces is watermarked
as a mockup. In production, annotate_screenshot() is run on the real
Playwright screenshot from the case's evidence directory instead.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size, bold=False):
    paths = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    )
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def build_mock_widget_screenshot(dest_path: str | Path, company_label: str, widget_label: str) -> Path:
    dest_path = Path(dest_path)
    w, h = 1600, 1000
    img = Image.new("RGB", (w, h), (245, 246, 248))
    draw = ImageDraw.Draw(img)

    # fake browser chrome
    draw.rectangle([0, 0, w, 60], fill=(230, 230, 232))
    draw.ellipse([20, 22, 36, 38], fill=(255, 95, 87))
    draw.ellipse([46, 22, 62, 38], fill=(255, 189, 46))
    draw.ellipse([72, 22, 88, 38], fill=(39, 201, 63))
    draw.rectangle([140, 16, w - 140, 46], fill=(255, 255, 255), outline=(200, 200, 200))
    draw.text((155, 22), f"https://www.{company_label.lower().replace(' ', '')}.de/", font=_font(16), fill=(80, 80, 80))

    # fake page header
    draw.rectangle([0, 60, w, 150], fill=(255, 255, 255))
    draw.text((40, 95), company_label, font=_font(28, bold=True), fill=(20, 30, 60))

    # fake chatbot widget window
    wx0, wy0, wx1, wy1 = w - 420, 260, w - 60, 760
    draw.rectangle([wx0, wy0, wx1, wy1], fill=(255, 255, 255), outline=(210, 210, 215), width=2)
    draw.rectangle([wx0, wy0, wx1, wy0 + 70], fill=(27, 58, 107))
    draw.text((wx0 + 20, wy0 + 22), widget_label, font=_font(18, bold=True), fill=(255, 255, 255))
    for i, txt in enumerate(["Hallo! Wie kann ich helfen?", "Ich beantworte Ihre Fragen rund um die Uhr."]):
        by = wy0 + 100 + i * 60
        draw.rounded_rectangle([wx0 + 20, by, wx1 - 20, by + 45], radius=10, fill=(240, 242, 246))
        draw.text((wx0 + 34, by + 13), txt, font=_font(14), fill=(40, 40, 40))
    draw.rectangle([wx0 + 20, wy1 - 60, wx1 - 20, wy1 - 20], outline=(200, 200, 200))
    draw.text((wx0 + 34, wy1 - 48), "Ihre Nachricht ...", font=_font(13), fill=(150, 150, 150))

    # watermark — must stay unmistakably a mockup
    wm_font = _font(46, bold=True)
    draw.text((w / 2, h / 2), "MUSTER-DARSTELLUNG\nKEIN ECHTER SCREENSHOT", font=wm_font, fill=(214, 39, 40, 90), anchor="mm", align="center")

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, "PNG")
    return dest_path

#!/usr/bin/env python3
"""Build the repo artwork from real rendered frames (no mockups).

    python3 tools/build_assets.py

banner.png     1280x640   title + a filmstrip of six styles rendered by tools/render_style.py
gallery.png    1600x900   the six stills on a grid, labelled by style id
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
FONTS = os.environ.get("ATLAS_FONTS", "")

BOLD = os.path.join(FONTS, "Poppins-Bold.ttf")
SEMI = os.path.join(FONTS, "Poppins-SemiBold.ttf")
REG = os.path.join(FONTS, "Poppins-Regular.ttf")
BG = (7, 11, 20)
INK = (255, 255, 255)
MUTED = (183, 194, 212)
TEAL = (43, 227, 196)
VIOLET = (140, 123, 255)

STYLES = ["B4", "C4", "D2", "G1", "E1", "D4"]
STILLS = os.path.join(ROOT, "stills")


def font(path, size):
    """Use ATLAS_FONTS if set, otherwise fall back to any bold system sans."""
    name = os.path.basename(path)
    if FONTS and os.path.exists(os.path.join(FONTS, name)):
        return ImageFont.truetype(os.path.join(FONTS, name), size)
    for candidate in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def grid_bg(size, step=40, alpha=9):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=(255, 255, 255, alpha), width=1)
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=(255, 255, 255, alpha), width=1)
    return layer


def glow(size, center, radius, color, peak=70):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(radius, 0, -8):
        a = int(peak * (1 - i / radius) ** 2)
        d.ellipse([center[0] - i, center[1] - i, center[0] + i, center[1] + i],
                  fill=color + (a,))
    return layer.filter(ImageFilter.GaussianBlur(28))


def banner():
    w, h = 1280, 640
    img = Image.new("RGB", (w, h), BG)
    img = Image.alpha_composite(img.convert("RGBA"), glow((w, h), (1090, 90), 420, VIOLET, 80))
    img = Image.alpha_composite(img, glow((w, h), (90, 560), 420, TEAL, 46))
    img = Image.alpha_composite(img, grid_bg((w, h)))
    d = ImageDraw.Draw(img)

    d.rectangle([84, 86, 130, 88], fill=TEAL)
    d.text((144, 78), "OPEN LIBRARY  —  341 STYLES", font=font(SEMI, 14), fill=TEAL)

    d.text((78, 112), "CODE", font=font(BOLD, 96), fill=INK)
    d.text((78, 200), "ANIMATION", font=font(BOLD, 96), fill=INK)
    d.text((78, 288), "ATLAS", font=font(BOLD, 96), fill=(120, 240, 220))
    d.text((84, 404), "Every look is a prompt and, for 29 of them, the code that draws it.",
           font=font(REG, 22), fill=MUTED)
    d.text((84, 440), "Pick a style  ·  render frames headless  ·  encode an MP4",
           font=font(SEMI, 22), fill=INK)

    # filmstrip of real frames: 2x2 grid on the right
    gx, gy, tw, th, gap = 812, 150, 170, 196, 16
    for i, sid in enumerate(STYLES[:4]):
        p = os.path.join(STILLS, sid + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB").resize((tw, th))
        x = gx + (i % 2) * (tw + gap)
        y = gy + (i // 2) * (th + gap)
        img.paste(im, (x, y))
        d.text((x + 8, y + 6), sid, font=font(SEMI, 12), fill=(255, 255, 255))

    d.text((84, 600), "prompt library: XiaoyeCodes/code-animation-prompts (free to share, not for resale)",
           font=font(REG, 14), fill=MUTED)
    d.text((w - 84, 600), "github.com/ahmadvahidi/code-animation-atlas", font=font(SEMI, 14),
           fill=MUTED, anchor="ra")
    d.rectangle([0, 0, w - 1, h - 1], outline=(27, 36, 54))
    os.makedirs(ASSETS, exist_ok=True)
    img.convert("RGB").save(os.path.join(ASSETS, "banner.png"))
    print("banner.png", img.size)


def gallery():
    cols, cw, ch, pad = 3, 500, 780, 20
    w = cols * cw + (cols + 1) * pad
    rows = 2
    h = rows * (ch + 34) + (rows + 1) * pad + 60
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.text((pad + 8, 24), "SIX STYLES, RENDERED BY THE RENDERER IN THIS REPO",
           font=font(BOLD, 26), fill=INK)
    for i, sid in enumerate(STYLES):
        p = os.path.join(STILLS, sid + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB").resize((cw, ch - 34))
        x = pad + (i % cols) * (cw + pad)
        y = 80 + (i // cols) * (ch + 34 + pad)
        img.paste(im, (x, y))
        d.text((x + 6, y + ch - 30), sid, font=font(SEMI, 18), fill=(255, 255, 255))
    img.save(os.path.join(ASSETS, "gallery.png"))
    print("gallery.png", img.size)


if __name__ == "__main__":
    banner()
    gallery()

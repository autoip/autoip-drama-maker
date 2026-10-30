"""YouTube thumbnail toolkit (1280x720) built from MV frames: no credits spent.

Gothic-theatre look: heavy serif title in white with a blood-red edge and ember glow, gold caps, slanted banner,
film grain. See examples/mv/demo/thumbs.py for a full A/B/C set.

    import thumbkit as tk
    tk.setup(title_font="fonts/PSSerifBlack.ttf", latin_font="fonts/NotoSerif-Bold.ttf")
    im = tk.shade(tk.frame("thumb_src/LS04_3.4.png", 1.15), "bottom")
    tk.title(im, (640, 560), "TITLE", 168); tk.caps(im, (640, 690), "SUBTITLE", 30); tk.badge(im)
    tk.grain(im).save("thumbnails/thumb_A.jpg", quality=95)

Grab frames with: ffmpeg -ss <t> -i out/<name>.mp4 -frames:v 1 thumb_src/<id>_<t>.png
Rules that held up: one face or one gag per thumbnail, title never over a face, text readable at 320 px wide.

Shorts thumbnails (1080x1920): set  tk.W, tk.H = 1080, 1920  first. frame / shade / split / badge / grain read W and H
at call time. Grab frames from clips/<id>.mp4 (the vertical render has lyrics burned in), keep key text above y = 1440
(the mobile Shorts shelf lays the video title over the bottom quarter) and check it at 180 px wide.
"""
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H = 1280, 720
BLOOD, EMBER, GOLD, WHITE, INK = (176, 16, 26), (255, 122, 26), (242, 197, 92), (255, 255, 255), (8, 5, 8)
_F = {}


def setup(title_font, latin_font):
    _F["title"], _F["latin"] = title_font, latin_font


SERIF = lambda size: ImageFont.truetype(_F["title"], size)
LATIN = lambda size: ImageFont.truetype(_F["latin"], size)


def frame(path, zoom=1.0, cx=0.5, cy=0.5):
    """Cover-crop a frame to 1280x720 around (cx, cy), a little extra contrast and sharpening."""
    im = Image.open(path).convert("RGB")
    s = max(W / im.width, H / im.height) * zoom
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x0 = int(min(max(0, im.width * cx - W / 2), im.width - W)); y0 = int(min(max(0, im.height * cy - H / 2), im.height - H))
    im = im.crop((x0, y0, x0 + W, y0 + H))
    im = ImageEnhance.Contrast(im).enhance(1.12)
    im = ImageEnhance.Color(im).enhance(1.08)
    return im.filter(ImageFilter.UnsharpMask(2, 70, 2))


def shade(im, side, strength=230, width=0.45):
    """Darken towards one edge (bottom/top/left/right) so text has a calm ground."""
    g = Image.new("L", (W, H)); d = ImageDraw.Draw(g)
    n = H if side in ("bottom", "top") else W
    for i in range(n):
        t = i / n if side in ("bottom", "right") else 1 - i / n
        a = int(strength * min(1, max(0.0, (t - (1 - width)) / width) * 1.4))
        if side in ("bottom", "top"):
            d.line((0, i, W, i), fill=a)
        else:
            d.line((i, 0, i, H), fill=a)
    return Image.composite(Image.new("RGB", (W, H), INK), im, g)


def split(left, right, top_x=700, bottom_x=560):
    """Two frames split by a slanted blood seam (duel layout)."""
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(top_x, 0), (W, 0), (W, H), (bottom_x, H)], fill=255)
    im = Image.composite(right, left, mask.filter(ImageFilter.GaussianBlur(2)))
    ImageDraw.Draw(im).line((top_x, 0, bottom_x, H), fill=BLOOD, width=12)
    ImageDraw.Draw(im).line((top_x + 8, 0, bottom_x + 8, H), fill=EMBER, width=3)
    return im


def title(im, xy, text, size, spacing=0.06):
    """White heavy serif centred at xy, thick blood-red edge, ember glow behind."""
    f = SERIF(size)
    d0 = ImageDraw.Draw(im)
    w = sum(d0.textlength(c, font=f) for c in text) + size * spacing * (len(text) - 1)
    x, y = xy[0] - w / 2, xy[1]
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for c in text:
        g.text((x, y), c, font=f, fill=EMBER + (255,), anchor="lm", stroke_width=size // 6, stroke_fill=EMBER + (255,))
        d.text((x + 6, y + 8), c, font=f, fill=(0, 0, 0, 200), anchor="lm", stroke_width=size // 10, stroke_fill=(0, 0, 0, 200))
        d.text((x, y), c, font=f, fill=WHITE + (255,), anchor="lm", stroke_width=size // 12, stroke_fill=BLOOD + (255,))
        x += d0.textlength(c, font=f) + size * spacing
    glow = glow.filter(ImageFilter.GaussianBlur(size // 5))
    im.paste(glow, (0, 0), glow.split()[3].point(lambda v: int(v * 0.75)))
    im.paste(lay, (0, 0), lay)


def text(im, xy, s, size, edge=(0, 0, 0), stroke=7):
    """Left-anchored punchline text."""
    ImageDraw.Draw(im).text(xy, s, font=SERIF(size), fill=WHITE, anchor="lm", stroke_width=stroke, stroke_fill=edge)


def strike(im, x0, x1, y, width=12):
    ImageDraw.Draw(im).line((x0, y, x1, y), fill=BLOOD, width=width)


def caps(im, xy, text, size, color=GOLD, spacing=10):
    """Letter-spaced latin caps centred at xy."""
    d = ImageDraw.Draw(im); f = LATIN(size)
    w = sum(d.textlength(c, font=f) for c in text) + spacing * (len(text) - 1)
    x = xy[0] - w / 2
    for c in text:
        d.text((x, xy[1]), c, font=f, fill=color, anchor="lm", stroke_width=2, stroke_fill=(0, 0, 0))
        x += d.textlength(c, font=f) + spacing
    return w


def rule(im, cx, y, w, color=GOLD, t=3):
    ImageDraw.Draw(im).rectangle((cx - w / 2, y, cx + w / 2, y + t), fill=color)


def banner(im, cx, cy, text, size, fill=BLOOD, color=WHITE, slant=16):
    d = ImageDraw.Draw(im); f = SERIF(size)
    w = d.textlength(text, font=f); hw, hh = w / 2 + 30, size * 0.78
    d.polygon([(cx - hw + slant, cy - hh), (cx + hw + slant, cy - hh), (cx + hw - slant, cy + hh), (cx - hw - slant, cy + hh)], fill=fill)
    d.text((cx, cy), text, font=f, fill=color, anchor="mm")


def badge(im, text="MV"):
    d = ImageDraw.Draw(im)
    d.rectangle((W - 116, 22, W - 22, 70), fill=(0, 0, 0), outline=GOLD, width=3)
    d.text((W - 69, 46), text, font=LATIN(30), fill=GOLD, anchor="mm")


def grain(im, amount=10, seed=3):
    random.seed(seed)
    n = Image.effect_noise((W, H), 40).convert("L")
    n = n.point(lambda v: 128 + (v - 128) * amount // 40)
    return Image.blend(im, Image.merge("RGB", (n, n, n)), 0.06)

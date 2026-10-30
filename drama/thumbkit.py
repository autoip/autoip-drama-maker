"""Episode covers built from frames of the clips: no credits spent.

Vertical 1080x1920 by default (short-drama apps, Shorts, Reels); set  tk.W, tk.H = 1280, 720  first for a landscape
YouTube thumbnail: every function reads W and H at call time. See examples/drama/demo/covers.py for a full set.

    import thumbkit as tk
    tk.setup(title_font="fonts/DKSansBlack.ttf", latin_font="fonts/DKSansBlack.ttf")
    im = tk.shade(tk.frame("thumb_src/S2_08_1.2.png", 1.1, 0.5, 0.4), "bottom")
    tk.hook(im, (540, 260), "鉤子文案", 120); tk.title(im, (540, 1500), "劇名", 150); tk.badge(im, "第1集")
    tk.grain(im).save("covers/cover_A.jpg", quality=95)

Grab frames from the clips, not from the render (the render has subtitles burned in):
    ffmpeg -ss <t> -i clips/<id>.mp4 -frames:v 1 thumb_src/<id>_<t>.png
Rules that held up for MV thumbnails and carry over: one face or one hook per cover, the title never over a face,
text readable when the cover is 180 px wide (a phone shelf), key text above y = 1440 on vertical covers (apps lay
their own title over the bottom quarter).
"""
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H = 1080, 1920
RED, EMBER, GOLD, WHITE, INK, YELLOW = (190, 20, 30), (255, 122, 26), (242, 197, 92), (255, 255, 255), (8, 5, 8), (255, 214, 0)
_F = {}


def setup(title_font, latin_font=None):
    _F["title"], _F["latin"] = title_font, latin_font or title_font


SERIF = lambda size: ImageFont.truetype(_F["title"], size)
LATIN = lambda size: ImageFont.truetype(_F["latin"], size)


def frame(path, zoom=1.0, cx=0.5, cy=0.5):
    """Cover-crop a frame to W x H around (cx, cy), a little extra contrast and sharpening."""
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


def split(a, b, cut=0.5, slant=0.08, horizontal=None):
    """Two frames split by a slanted red seam: top / bottom on a vertical cover, left / right on a landscape one."""
    horizontal = H > W if horizontal is None else horizontal
    mask = Image.new("L", (W, H), 0)
    if horizontal:
        y0, y1 = H * (cut - slant), H * (cut + slant)
        ImageDraw.Draw(mask).polygon([(0, y1), (W, y0), (W, H), (0, H)], fill=255)
        line = (0, y1, W, y0)
    else:
        x0, x1 = W * (cut + slant), W * (cut - slant)
        ImageDraw.Draw(mask).polygon([(x0, 0), (W, 0), (W, H), (x1, H)], fill=255)
        line = (x0, 0, x1, H)
    im = Image.composite(b, a, mask.filter(ImageFilter.GaussianBlur(2)))
    ImageDraw.Draw(im).line(line, fill=RED, width=max(8, W // 100))
    return im


def title(im, xy, text, size, spacing=0.06, edge=RED):
    """White heavy title centred at xy, thick coloured edge, a soft glow behind."""
    f = SERIF(size)
    d0 = ImageDraw.Draw(im)
    w = sum(d0.textlength(c, font=f) for c in text) + size * spacing * (len(text) - 1)
    x, y = xy[0] - w / 2, xy[1]
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for c in text:
        g.text((x, y), c, font=f, fill=EMBER + (255,), anchor="lm", stroke_width=size // 6, stroke_fill=EMBER + (255,))
        d.text((x + 6, y + 8), c, font=f, fill=(0, 0, 0, 200), anchor="lm", stroke_width=size // 10, stroke_fill=(0, 0, 0, 200))
        d.text((x, y), c, font=f, fill=WHITE + (255,), anchor="lm", stroke_width=size // 12, stroke_fill=edge + (255,))
        x += d0.textlength(c, font=f) + size * spacing
    glow = glow.filter(ImageFilter.GaussianBlur(size // 5))
    im.paste(glow, (0, 0), glow.split()[3].point(lambda v: int(v * 0.6)))
    im.paste(lay, (0, 0), lay)


def hook(im, xy, s, size, color=YELLOW, edge=INK):
    """The episode's hook line, centred at xy: bright fill, heavy black edge (reads at thumbnail size)."""
    d = ImageDraw.Draw(im)
    d.text(xy, s, font=SERIF(size), fill=color, anchor="mm", stroke_width=max(6, size // 9), stroke_fill=edge)


def text(im, xy, s, size, edge=(0, 0, 0), stroke=7, color=WHITE):
    """Left-anchored line of text."""
    ImageDraw.Draw(im).text(xy, s, font=SERIF(size), fill=color, anchor="lm", stroke_width=stroke, stroke_fill=edge)


def strike(im, x0, x1, y, width=12):
    ImageDraw.Draw(im).line((x0, y, x1, y), fill=RED, width=width)


def caps(im, xy, s, size, color=GOLD, spacing=10):
    """Letter-spaced latin caps centred at xy."""
    d = ImageDraw.Draw(im); f = LATIN(size)
    w = sum(d.textlength(c, font=f) for c in s) + spacing * (len(s) - 1)
    x = xy[0] - w / 2
    for c in s:
        d.text((x, xy[1]), c, font=f, fill=color, anchor="lm", stroke_width=2, stroke_fill=(0, 0, 0))
        x += d.textlength(c, font=f) + spacing
    return w


def rule(im, cx, y, w, color=GOLD, t=3):
    ImageDraw.Draw(im).rectangle((cx - w / 2, y, cx + w / 2, y + t), fill=color)


def banner(im, cx, cy, s, size, fill=RED, color=WHITE, slant=16):
    """A slanted tag (genre, 「全集」, 「大結局」)."""
    d = ImageDraw.Draw(im); f = SERIF(size)
    w = d.textlength(s, font=f); hw, hh = w / 2 + 30, size * 0.78
    d.polygon([(cx - hw + slant, cy - hh), (cx + hw + slant, cy - hh), (cx + hw - slant, cy + hh), (cx - hw - slant, cy + hh)], fill=fill)
    d.text((cx, cy), s, font=f, fill=color, anchor="mm")


def badge(im, s="第1集"):
    """Episode number in the top right corner."""
    d = ImageDraw.Draw(im); f = SERIF(round(W * 0.045))
    w = d.textlength(s, font=f)
    x1, y0 = W - round(W * 0.03), round(W * 0.03)
    d.rectangle((x1 - w - 36, y0, x1, y0 + round(W * 0.075)), fill=(0, 0, 0), outline=GOLD, width=3)
    d.text((x1 - w / 2 - 18, y0 + round(W * 0.0375)), s, font=f, fill=GOLD, anchor="mm")


def grain(im, amount=10, seed=3):
    random.seed(seed)
    n = Image.effect_noise((W, H), 40).convert("L")
    n = n.point(lambda v: 128 + (v - 128) * amount // 40)
    return Image.blend(im, Image.merge("RGB", (n, n, n)), 0.06)

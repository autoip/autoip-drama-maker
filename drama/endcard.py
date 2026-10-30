"""A text end card (a call to action after the cliffhanger) over the episode's own last frame, blurred and darkened.

usage: python drama/endcard.py PROJECT_DIR BACKGROUND.png OUT.png     a preview, from project.RENDER["end_card"]
render_ep.py makes it by itself when RENDER["end_card"] is a dict (the background is the body's last frame):
  end_card=dict(lines=[("這部短劇的演員、場景、配音", 50, "accent"), ("全是 AI 做的", 118), ("你也可以是短劇導演", 72)],
                button="autoip.ai"),
  end_s=3.0
lines   (text, size in px at 1080 wide[, colour]): colour "accent" (TYPO accent), RRGGBB or white by default
button  the address in a pill of the accent colour under the lines (optional)
"""
import glob, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
from common import load_project, label_font


def font_file(proj, D):
    """The series font (TYPO font, a file in fonts/ of the episode or the series folder), else a CJK system font."""
    want = getattr(proj, "TYPO", {}).get("font", "").replace(" ", "").lower()
    for d in (os.path.join(D, "fonts"), os.path.join(os.path.dirname(D), "fonts")):
        files = sorted(glob.glob(os.path.join(d, "*.[ot]t[fc]")))
        hit = [f for f in files if want and want in os.path.basename(f).replace(" ", "").lower()] or files
        if hit:
            return hit[0]
    return None


def make(proj, D, spec, bg, out, W, H):
    T = getattr(proj, "TYPO", {})
    accent = "#" + T.get("accent", "F2C55C").lstrip("#")
    u = W / 1080
    ff = font_file(proj, D)
    font = (lambda px: ImageFont.truetype(ff, round(px * u))) if ff else (lambda px: label_font(round(px * u), cjk=True))
    im = Image.open(bg).convert("RGB").resize((W, H), Image.LANCZOS)
    im = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(28 * u))).enhance(0.38)
    d = ImageDraw.Draw(im)
    rows = []
    for ln in spec.get("lines", []):
        text, px, colour = (list(ln) + [None])[:3]
        f = font(px)
        colour = accent if colour == "accent" else ("#" + colour.lstrip("#") if colour else "white")
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
        rows.append((text, f, colour, x1 - x0, y1 - y0, y0, px))
    bf = font(64)
    btn = spec.get("button")
    bw, bh, by0 = 0, 0, 0
    if btn:
        x0, by0, x1, y1 = d.textbbox((0, 0), btn, font=bf)
        bw, bh = x1 - x0, y1 - by0
    gap = 34 * u
    total = sum(r[4] for r in rows) + gap * max(0, len(rows) - 1) + ((bh + 2 * 34 * u) + 70 * u if btn else 0)
    y = (H - total) / 2 - 40 * u
    for text, f, colour, w, h, top, px in rows:
        d.text(((W - w) / 2, y - top), text, font=f, fill=colour, stroke_width=round(3 * u), stroke_fill="black")
        y += h + gap
    if btn:
        y += 70 * u - gap
        pw, ph = bw + 2 * 70 * u, bh + 2 * 34 * u
        d.rounded_rectangle(((W - pw) / 2, y, (W + pw) / 2, y + ph), radius=ph / 2, fill=accent)
        d.text(((W - bw) / 2, y + 34 * u - by0), btn, font=bf, fill="white")
    im.save(out)
    return out


if __name__ == "__main__":
    proj = load_project(sys.argv[1])
    W, H = (1080, 1920) if getattr(proj, "ASPECT", "9:16") == "9:16" else (1920, 1080)
    print(make(proj, proj.DIR, proj.RENDER["end_card"], sys.argv[2], sys.argv[3], W, H))

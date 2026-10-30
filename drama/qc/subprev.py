"""Subtitle-only preview: the edit's subtitles and cards at given seconds, over frames of the last body render (or a
flat frame), as one sheet. Seconds per check instead of minutes per render.

usage: python drama/qc/subprev.py PROJECT_DIR MODE out.jpg t1 t2 ...     (episode seconds)
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw
import subs, timeline
from common import load_project, label_font as font

proj = load_project(sys.argv[1])
MODE, out = sys.argv[2], sys.argv[3]
times = [float(x) for x in sys.argv[4:]]
tl = timeline.resolve(proj, MODE)
W, H = tl["edit"]["size"]
ass, cues = subs.build(proj, tl, W, H)
d = tempfile.mkdtemp()
open(os.path.join(d, "p.ass"), "w", encoding="utf-8-sig").write(ass)
fonts = next((p for p in (os.path.join(proj.DIR, "fonts"), os.path.join(os.path.dirname(proj.DIR), "fonts")) if os.path.isdir(p)),
             os.path.join(proj.DIR, "fonts")).replace("\\", "/").replace(":", "\\:")
body = os.path.join(proj.DIR, f"render_{MODE}", "body_raw.mp4")
print("cues", len(cues), "| background:", "body_raw.mp4" if os.path.exists(body) else "flat")
if [t for t in times if t >= tl["total"]]:
    print(f"skipped (the cut is {tl['total']:.2f} s):", [t for t in times if t >= tl["total"]])
    times = [t for t in times if t < tl["total"]]
tw, th = (360, 640) if H > W else (640, 360)
ims = []
for t in times:
    p = os.path.join(d, f"f_{t:.2f}.png")
    src = ["-ss", f"{t:.2f}", "-i", body] if os.path.exists(body) else ["-f", "lavfi", "-i", f"color=c=0x403a44:s={W}x{H}:d={t + 1}:r=25"]
    vf = f"setpts=PTS+{t:.3f}/TB,subtitles=p.ass:fontsdir='{fonts}'" if os.path.exists(body) else f"subtitles=p.ass:fontsdir='{fonts}'"
    seek = [] if os.path.exists(body) else ["-ss", f"{t:.2f}"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *src, "-vf", vf, *seek, "-frames:v", "1", p], cwd=d, check=True)
    im = Image.open(p).convert("RGB").resize((tw, th))
    ImageDraw.Draw(im).text((8, 4), f"{t:.2f}", fill="yellow", font=font(22))
    ims.append(im)
cols = 6 if H > W else 4
sh = Image.new("RGB", (tw * cols, th * ((len(ims) + cols - 1) // cols)))
for i, im in enumerate(ims):
    sh.paste(im, ((i % cols) * tw, (i // cols) * th))
sh.save(out, quality=85)
print(out)

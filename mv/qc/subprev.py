"""Subtitle-only preview: render the kinetic ASS for song range [a, b] over a flat frame, sheet of frames.

usage: python mv/qc/subprev.py PROJECT_DIR a b out.jpg t1 t2 ...   (song seconds)
Seconds per check instead of minutes per render: iterate on typography here, render the MV once.
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw
import epic
from common import load_project, jload, audio_path, label_font as font

proj = load_project(sys.argv[1])
a, b, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
times = [float(x) for x in sys.argv[5:]]
sections = jload(os.path.join(proj.DIR, "shots.json"))["sections"]
wp = audio_path(proj, "words")
words = jload(wp) if os.path.exists(wp) else []
beats = jload(audio_path(proj, "beats"))["beats"]
epic.configure(proj.TYPO, proj.DIR)
epic.OFFSCREEN.clear()
rows = epic.build(sections, words, a, a, b, beats, proj.TYPO)
d = tempfile.mkdtemp()
open(os.path.join(d, "p.ass"), "w", encoding="utf-8-sig").write("\n".join(rows) + "\n")
fonts = os.path.join(proj.DIR, "fonts").replace("\\", "/").replace(":", "\\:")
print("events", len(rows), "offscreen", epic.OFFSCREEN[:20])
ims = []
for t in times:
    p = os.path.join(d, f"f_{t:.2f}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x302830:s=1920x1080:d={b - a + 1}:r=25",
                    "-vf", f"subtitles=p.ass:fontsdir='{fonts}'", "-ss", f"{t - a:.2f}", "-frames:v", "1", p], cwd=d, check=True)
    im = Image.open(p).convert("RGB").resize((640, 360))
    ImageDraw.Draw(im).text((8, 4), f"{t:.2f}", fill="yellow", font=font(22))
    ims.append(im)
cols = 4
sh = Image.new("RGB", (640 * cols, 360 * ((len(ims) + cols - 1) // cols)))
for i, im in enumerate(ims):
    sh.paste(im, ((i % cols) * 640, (i // cols) * 360))
sh.save(out, quality=85)
print(out)

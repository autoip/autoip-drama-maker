"""Contact sheets for review (send these to whoever approves, before spending credits on video).

usage: python mv/qc/sheets.py stills  out.jpg DIR [id ...]          keyframe stills (DIR/<id>.png), 4 per row
       python mv/qc/sheets.py video   out.jpg video.mp4 t1 t2 ...   frames of one video at given seconds
       python mv/qc/sheets.py strips  out.jpg clip1.mp4 clip2.mp4   6 evenly spaced frames per clip, one row each
"""
import glob, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw
from common import label_font as font


def label(im, text, size=24):
    ImageDraw.Draw(im).text((8, 4), text, font=font(size), fill="yellow", stroke_width=2, stroke_fill="black")


def grid(ims, out, cols=4):
    w, h = ims[0].size
    sh = Image.new("RGB", (w * cols, h * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims):
        sh.paste(im, ((i % cols) * w, (i // cols) * h))
    sh.save(out, quality=85)
    print(out, len(ims))


def grab(video, t, width):
    p = os.path.join(tempfile.mkdtemp(), "f.png")  # frames are labelled with PIL: ffmpeg drawtext needs fontconfig
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", f"scale={width}:-2", p], check=True)
    return Image.open(p).convert("RGB")


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


kind, out = sys.argv[1], sys.argv[2]
if kind == "stills":
    d = sys.argv[3]
    ids = sys.argv[4:] or sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(d, "*.png")))
    ims = []
    for k in ids:
        im = Image.open(os.path.join(d, k + ".png")).convert("RGB").resize((640, 360)); label(im, k, 26); ims.append(im)
    grid(ims, out)
elif kind == "video":
    ims = []
    for t in map(float, sys.argv[4:]):
        im = grab(sys.argv[3], t, 480); label(im, f"{t:g}"); ims.append(im)
    grid(ims, out)
else:
    N, W, H = 6, 320, 180
    clips = sys.argv[3:]
    sheet = Image.new("RGB", (W * N + 80, H * len(clips)), "black")
    d = ImageDraw.Draw(sheet)
    for r, c in enumerate(clips):
        dd = dur(c)
        d.text((4, r * H + 4), os.path.basename(c)[:-4], font=font(16), fill="yellow")
        d.text((4, r * H + 24), f"{dd:.1f}s", font=font(16), fill="yellow")
        for k in range(N):
            sheet.paste(grab(c, dd * (k + 0.5) / N, W).resize((W, H)), (80 + k * W, r * H))
    sheet.save(out, quality=85)
    print(out)

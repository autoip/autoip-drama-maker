"""Contact sheets for review (send these to whoever approves, before spending credits on video).

usage: python drama/qc/sheets.py stills  out.jpg DIR [id ...]          stills (DIR/<id>.png), 4 per row
       python drama/qc/sheets.py jobs    out.jpg JOBS.json [id ...]    one row per job: its input pictures, dialogue,
                                                                          prompt (what a multi-reference shot will get)
       python drama/qc/sheets.py video   out.jpg video.mp4 t1 t2 ...   frames of one video at given seconds
       python drama/qc/sheets.py strips  out.jpg clip1.mp4 clip2.mp4   6 evenly spaced frames per clip, one row each
"""
import glob, json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw
from common import label_font as font, estimate


def label(im, text, size=24):
    ImageDraw.Draw(im).text((8, 4), text, font=font(size, cjk=True), fill="yellow", stroke_width=2, stroke_fill="black")


def fit(im, w, h):
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    out = Image.new("RGB", (w, h), (24, 24, 24))
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    out.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return out


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


def wrap(text, f, width, draw):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            if draw.textlength(cur + ch, font=f) > width:
                lines.append(cur); cur = ""
            cur += ch
        lines.append(cur)
    return lines


kind, out = sys.argv[1], sys.argv[2]
if kind == "stills":
    d = sys.argv[3]
    ids = sys.argv[4:] or sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(d, "*.png")))
    ims = []
    for k in ids:
        im = Image.open(os.path.join(d, k + ".png"))
        im = fit(im, 360, 640) if im.height > im.width else fit(im, 640, 360)
        label(im, k, 26); ims.append(im)
    grid(ims, out, 6 if ims[0].height > ims[0].width else 4)
elif kind == "jobs":
    jobs = json.load(open(sys.argv[3], encoding="utf-8"))
    if sys.argv[4:]:
        jobs = [j for j in jobs if j["id"] in sys.argv[4:]]
    TW, TH, TXT, RH = 180, 240, 980, 320
    f_id, f_txt = font(28, cjk=True), font(20, cjk=True)
    sheet = Image.new("RGB", (TW * 6 + TXT, RH * len(jobs)), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    for r, j in enumerate(jobs):
        y = r * RH
        pics = [(f"@圖片 {n + 1}" if k == "images[]" else k, p) for k, v in j.get("files", {}).items()
                for n, p in enumerate(v if isinstance(v, list) else [v])
                if os.path.splitext(p)[1].lower() in (".png", ".jpg", ".jpeg", ".webp")]
        descs = j["fields"].get("descriptions[]", [])
        for n, (tag, p) in enumerate(pics[:6]):
            im = fit(Image.open(p), TW, TH) if os.path.exists(p) else Image.new("RGB", (TW, TH), (90, 0, 0))
            sheet.paste(im, (n * TW, y))
            d.text((n * TW + 6, y + 4), tag, font=font(18, cjk=True), fill="yellow", stroke_width=2, stroke_fill="black")
            if n < len(descs):
                d.text((n * TW + 4, y + TH + 4), "\n".join(wrap(descs[n], font(14, cjk=True), TW - 8, d)[:3]),
                       font=font(14, cjk=True), fill=(200, 200, 200))
        x = TW * 6 + 16
        f = j["fields"]
        head = f"{j['id']}  {j['endpoint'].split('/')[-1]}  {f.get('duration_seconds', '')}s  ~{estimate(j)} credits"
        if "voice_sample" in j.get("files", {}):
            head += "  voice: " + os.path.basename(j["files"]["voice_sample"])
        d.text((x, y + 8), head, font=f_id, fill="yellow")
        yy = y + 48
        if f.get("dialogue_text"):
            for ln in wrap("台詞：" + f["dialogue_text"], f_txt, TXT - 32, d)[:2]:
                d.text((x, yy), ln, font=f_txt, fill=(255, 220, 120)); yy += 26
        for ln in wrap(f.get("prompt", ""), f_txt, TXT - 32, d)[:(RH - (yy - y) - 8) // 25]:
            d.text((x, yy), ln, font=f_txt, fill="white"); yy += 25
        d.line((0, y + RH - 1, sheet.width, y + RH - 1), fill=(60, 60, 60))
    sheet.save(out, quality=85)
    print(out, len(jobs), "jobs, about", sum(map(estimate, jobs)), "credits")
elif kind == "video":
    ims = []
    for t in map(float, sys.argv[4:]):
        im = grab(sys.argv[3], t, 480)
        im = fit(im, 360, 640) if im.height > im.width else fit(im, 480, 270)
        label(im, f"{t:g}"); ims.append(im)
    grid(ims, out, 6 if ims[0].height > ims[0].width else 4)
else:
    N = 6
    clips = sys.argv[3:]
    first = grab(clips[0], 0.1, 320)
    W, H = (180, 320) if first.height > first.width else (320, 180)
    sheet = Image.new("RGB", (W * N + 90, H * len(clips)), "black")
    d = ImageDraw.Draw(sheet)
    for r, c in enumerate(clips):
        dd = dur(c)
        d.text((4, r * H + 4), os.path.splitext(os.path.basename(c))[0], font=font(16), fill="yellow")
        d.text((4, r * H + 24), f"{dd:.1f}s", font=font(16), fill="yellow")
        for k in range(N):
            sheet.paste(fit(grab(c, dd * (k + 0.5) / N, 320), W, H), (90 + k * W, r * H))
    sheet.save(out, quality=85)
    print(out)

"""Subtitle looks side by side, so the user picks one before the render.

usage: python explain/sub_styles.py PROJECT_DIR [--text TEXT] [--size N]   -> out/subtitle_styles.jpg
Every look in common.SUBS (outline, heavy, gold, band) in every font in FONT's folder, on the episode's lightest and
darkest pictures (the bottom strip, where subtitles sit), each row labelled. Show it to the user, then write the pick
into project.py, e.g. SUBS = dict(style="band", font="DFKai-SB", size=66); render.py reads it.
"""
import glob, os, subprocess, sys, tempfile
from fontTools.ttLib import TTFont
from PIL import Image, ImageStat
from common import load_project, chapters, lines, SUBS, sub_styles, sub_events, ass_time

W, H = 1920, 1080
HEAD = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"]


def esc(p):
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def families(folder):
    """The family name of every font file in the folder, as libass matches it."""
    out = []
    for f in sorted(glob.glob(os.path.join(folder, "*.tt[fc]")) + glob.glob(os.path.join(folder, "*.otf"))):
        try:
            name = TTFont(f, fontNumber=0)["name"]
            fam = name.getName(1, 3, 1, 0x409) or name.getName(1, 1, 0, 0)
            if fam and str(fam) not in out:
                out.append(str(fam))
        except Exception:
            print(f"  skipped {os.path.basename(f)} (not a font fontTools can read)")
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    proj = load_project(sys.argv[1])
    D, args = proj.DIR, sys.argv[2:]
    font, fonts = getattr(proj, "FONT", ("Explainer Serif", "fonts"))
    fonts = next((p for p in (os.path.join(D, fonts), os.path.join(D, "..", fonts)) if os.path.isdir(p)), os.path.join(D, fonts))
    fams = families(fonts) or [font]
    size = int(args[args.index("--size") + 1]) if "--size" in args else getattr(proj, "SUBS", {}).get("size", 58)
    if "--text" in args:
        text = args[args.index("--text") + 1]
    else:   # the first subtitle line of the first real chapter
        _, body = (chapters(proj)[1:] or chapters(proj))[0]
        text = next(s for _, _, s in lines(body) if len(s) >= 8)
    # the lightest and the darkest picture, judged by the bottom third where the subtitles go
    pics = sorted(glob.glob(os.path.join(D, "images", "*.png")) + glob.glob(os.path.join(D, "images", "*.jpg")))
    if not pics:
        sys.exit("no images/ yet: make the pictures first")

    def low(p):
        im = Image.open(p).convert("L").resize((64, 36))
        return ImageStat.Stat(im.crop((0, 24, 64, 36))).mean[0]
    lum = sorted(pics, key=low)
    backs = [lum[-1], lum[0]] if len(lum) > 1 else lum
    out = os.path.join(D, "out", "subtitle_styles.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        strips = []
        for style, look in SUBS.items():
            for fam in fams:
                sub = dict(style=style, font=fam, size=size)
                ass = HEAD + sub_styles(sub) + [
                    f"Style: Label,{fams[0]},30,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,3,8,0,7,0,0,0,1",
                    "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
                ass += sub_events(sub, [(0.0, 5.0, text)], W, H)
                ass.append(f"Dialogue: 5,{ass_time(0)},{ass_time(5)},Label,,0,0,0,,{{\\pos(24,790)}}"
                           f'style="{style}"  font="{fam}"  size={size}：{look["label"]}')
                sp = os.path.join(tmp, f"{len(strips)}.ass")
                open(sp, "w", encoding="utf-8-sig").write("\n".join(ass) + "\n")
                for b in backs:   # 0.4 s in: the band's fade-in is over
                    png = os.path.join(tmp, f"{len(strips)}.png")
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "1", "-i", b, "-vf",
                                    f"scale={W}:{H},subtitles='{esc(sp)}':fontsdir='{esc(fonts)}',crop={W}:310:0:770,scale=960:-2",
                                    "-ss", "0.4", "-frames:v", "1", png], check=True)
                    strips.append(png)
        cmd = ["ffmpeg", "-v", "error", "-y"]
        for s in strips:
            cmd += ["-i", s]
        cols = len(backs)
        layout = "|".join(f"{(k % cols) * 960}_{(k // cols) * 155}" for k in range(len(strips)))
        subprocess.run(cmd + ["-filter_complex", f"xstack=inputs={len(strips)}:layout={layout}", "-frames:v", "1", out], check=True)
    print(f"{os.path.relpath(out, D)}  {len(SUBS)} looks x {len(fams)} fonts ({', '.join(fams)}), size {size}: show it to "
          f"the user, then SUBS = dict(style=..., font=..., size=...) in project.py")


if __name__ == "__main__":
    main()

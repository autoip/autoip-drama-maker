"""Join finished episodes (and other videos) into one upload: a season compilation, a recap, episodes + an MV.

usage: python dramakit/compile.py COMP_DIR
COMP_DIR/project.py:
  NAME   = "series_s1_compilation"
  PARTS  = [dict(ep="../s1e01_x", end_card=False),       # an episode's out/<NAME>.mp4, its end card cut off
            dict(ep="../s1e10_x"),                        # ... or kept (the default)
            dict(card=dict(lines=[(text, size[, colour]), ...], button=None), secs=2.5, bg="next"),
                                                          # a text card (endcard.py) over the next part's first frame
                                                          # (bg="prev": the previous part's last frame)
            dict(video="path.mp4", srt="path.srt", chapter="MV")]   # any video in the same frame size
  RENDER = dict(lufs=-16, lang="zh-TW", fps=25); TYPO = dict(font=..., accent=...) for the cards
out: COMP_DIR/out/<NAME>.mp4, <NAME>.<lang>.srt (every part's subtitles, shifted) and <NAME>_chapters.txt
     (YouTube chapters: one per episode / video; a card belongs to the part it introduces).
Each part is levelled to RENDER["lufs"] on its own, so a louder MV does not jump out of the episodes.
"""
import json, os, re, subprocess, sys
from common import load_project, run, dur_of, has_audio, venc, canvas
import endcard

proj = load_project(sys.argv[1])
D = proj.DIR
R = dict(dict(lufs=-16, lang="zh-TW", fps=25), **getattr(proj, "RENDER", {}))
W, H = canvas(proj)
FPS = R["fps"]
WORK, OUT = os.path.join(D, "render"), os.path.join(D, "out")
os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def srt_read(path):
    if not path or not os.path.exists(path):
        return []
    t = lambda s: sum(float(x) * k for x, k in zip(s.replace(",", ".").split(":"), (3600, 60, 1)))
    out = []
    for block in open(path, encoding="utf-8-sig").read().strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) >= 3 and "-->" in lines[1]:
            a, b = (t(x.strip()) for x in lines[1].split("-->"))
            out.append((a, b, "\n".join(lines[2:])))
    return out


def srt_ts(v):
    v = max(0.0, v)
    return f"{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round(v % 1 * 1000)) % 1000:03d}"


# ---------- resolve the parts
parts = []
for p in proj.PARTS:
    if "ep" in p:
        e = load_project(os.path.join(D, p["ep"]))
        src = os.path.join(e.DIR, "out", e.NAME + ".mp4")
        er = getattr(e, "RENDER", {})
        card_s = (er.get("end_s") or 3.0) if er.get("end_card") else 0.0
        cut = 0.0 if p.get("end_card", True) else card_s
        title = os.path.basename(os.path.normpath(e.DIR)).split("_", 1)[-1]
        parts.append(dict(kind="video", src=src, dur=dur_of(src) - cut,
                          srt=os.path.join(e.DIR, "out", f"{e.NAME}.{R['lang']}.srt"),
                          chapter=p.get("chapter") or f"第{getattr(e, 'EPISODE', '?')}集 {title}"))
    elif "video" in p:
        parts.append(dict(kind="video", src=p["video"], dur=dur_of(p["video"]), srt=p.get("srt"),
                          chapter=p.get("chapter") or os.path.splitext(os.path.basename(p["video"]))[0]))
    else:
        parts.append(dict(kind="card", spec=p["card"], dur=float(p.get("secs", 2.5)), bg=p.get("bg", "next"), chapter=None))

# ---------- one segment per part, all in the same format, so they join without re-encoding
segs = []
for n, p in enumerate(parts):
    out = os.path.join(WORK, f"part_{n:02d}.mp4")
    if p["kind"] == "card":
        nb = parts[n + 1] if p["bg"] == "next" else parts[n - 1]
        at = ["-ss", "0.3"] if p["bg"] == "next" else ["-sseof", "-0.1"]
        bg = os.path.join(WORK, f"part_{n:02d}_bg.png")
        run(["ffmpeg", "-v", "error", "-y", *at, "-i", nb["src"], "-frames:v", "1", "-update", "1", bg])
        pic = endcard.make(proj, D, p["spec"], bg, os.path.join(WORK, f"part_{n:02d}.png"), W, H)
        nf = int(p["dur"] * FPS)
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", pic, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-vf", f"scale={round(W * 1.1)}:{round(H * 1.1)},zoompan=z='1+0.02*on/{nf}':x='iw/2-(iw/zoom/2)':"
                    f"y='ih/2-(ih/zoom/2)':d={nf}:s={W}x{H}:fps={FPS},fade=in:st=0:d=0.4,"
                    f"fade=out:st={p['dur'] - 0.4:.2f}:d=0.4,setsar=1,format=yuv420p",
             "-frames:v", str(nf), "-t", f"{nf / FPS:.3f}", *venc("final"), "-c:a", "aac", "-b:a", "256k", out])
    else:
        lv = loudness(p["src"]) if has_audio(p["src"]) else None
        gain = 0.0 if lv is None else R["lufs"] - lv
        audio = ["-af", f"volume={gain:.2f}dB,aresample=48000"] if lv is not None else []
        ins = ["-i", p["src"]] + ([] if lv is not None else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
        run(["ffmpeg", "-v", "error", "-y", *ins, "-t", f"{p['dur']:.3f}", "-map", "0:v", "-map", "0:a" if lv is not None else "1:a",
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},"
                    "setsar=1,format=yuv420p", *audio, "-ac", "2", *venc("final"), "-c:a", "aac", "-b:a", "256k", out])
        print(f"{n:2d} {p['chapter']:24} {p['dur']:6.2f}s  {'' if lv is None else f'{lv:.1f} LUFS -> {gain:+.1f} dB'}", flush=True)
    p["seg"] = out
    segs.append(out)

lst = os.path.join(WORK, "parts.txt")
open(lst, "w", encoding="utf-8").write("".join(f"file '{s.replace(os.sep, '/')}'\n" for s in segs))
final = os.path.join(OUT, proj.NAME + ".mp4")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", final])

# ---------- chapters and subtitles on the joined timeline
t, chapters, cues, pending = 0.0, [], [], None
for n, p in enumerate(parts):
    d = dur_of(p["seg"])
    if p["kind"] == "card":
        if p["bg"] == "next":
            pending = pending if pending is not None else t
    else:
        chapters.append((pending if pending is not None else t, p["chapter"]))
        pending = None
        cues += [(t + a, t + min(b, d), x) for a, b, x in srt_read(p.get("srt")) if a < d]
    t += d
mmss = lambda v: f"{int(v // 3600)}:{int(v % 3600 // 60):02d}:{int(v % 60):02d}" if v >= 3600 else f"{int(v // 60):02d}:{int(v % 60):02d}"
open(os.path.join(OUT, f"{proj.NAME}_chapters.txt"), "w", encoding="utf-8").write(
    "".join(f"{mmss(0 if k == 0 else a)} {c}\n" for k, (a, c) in enumerate(chapters)))
open(os.path.join(OUT, f"{proj.NAME}.{R['lang']}.srt"), "w", encoding="utf-8-sig").write(
    "".join(f"{k}\n{srt_ts(a)} --> {srt_ts(b)}\n{x}\n\n" for k, (a, b, x) in enumerate(cues, 1)))
print("FINAL", final, round(dur_of(final), 2), "s,", len(chapters), "chapters,", len(cues), "subtitle cues,",
      f"{loudness(final):.1f} LUFS")

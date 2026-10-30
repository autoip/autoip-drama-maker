"""Assemble the MV: EDL -> beat-snapped segments -> body + kinetic ASS + optional promo cards + song audio.

usage: python mvkit/render_mv.py PROJECT_DIR MODE        MODE = a key of project.EDITS ("full", "short", ...)
env:   REUSE_BODY=1   keep render_<MODE>/body_raw.mp4 (subtitle / card changes only)
       VENC=x264      encode on the CPU (by default the NVIDIA GPU encodes whenever ffmpeg can: dreamfab.util.nvenc_on)
       JOBS=4         segments encoded in parallel (default 4 on the GPU, else 1)
       SUBST="B17:B05" temporary stand-ins for clips that are not ready yet
edit:  size=(1080, 1920) renders a portrait cut: focus={src: 0..1} picks the horizontal crop centre per clip
       ("src@row_time": 0..1 for one shot, when the subject moves across the clip),
       zones={...} replaces epic.ZONES, open_card / end_card override RENDER's cards,
       crop={src: filter} is merged over RENDER's crop (e.g. a crop only the landscape cut needs)
       render=dict(fps=60, enhance=True) overrides RENDER for this edit, e.g. a 60 fps cut to compare
enhance=True (RENDER or an edit's render=): each clip's clips_hd/ copy from enhance.py (2x super resolution + frame
       generation) when there is one newer than the clip; crop= / delogo= pixel values in crop filters are scaled to it
       labels=False drops the project.FEATURE corner tags ("AutoIP｜<feature>" when the clip's feature changes)
out:   PROJECT_DIR/out/<NAME><suffix>.mp4 and .<lang>.srt

The EDL is resolved from project.EDITS here, at render time: there is no intermediate edl.json that could belong
to a different cut.
"""
import os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import epic
from common import P, load_project, jload, audio_path, run, dur_of, edit, venc, nvenc_on, hd_path

proj = load_project(sys.argv[1])
MODE = sys.argv[2]
D = proj.DIR
R = dict(fps=25, crop={}, grade="eq=contrast=1.07:saturation=1.06,vignette=PI/5,noise=alls=4:allf=t", lang="zh-TW",
         open_card="", end_card="", tail_guard=0.35, enhance=False)
R.update(getattr(proj, "RENDER", {}))
E = edit(proj, MODE)
R.update({k: E[k] for k in ("open_card", "end_card") if k in E})
R["crop"] = {**R["crop"], **E.get("crop", {})}
R.update(E.get("render", {}))
FPS, (W, H) = R["fps"], E.get("size", (1920, 1080))
FOCUS = E.get("focus", {})
OPEN_S, END_S = E.get("open_s", 0), E.get("end_s", 0)
card_path = lambda k: os.path.join(D, R[k]) if R[k] and os.path.exists(os.path.join(D, R[k])) else None
if not card_path("open_card"):
    OPEN_S = 0
if not card_path("end_card"):
    END_S = 0
NAME = proj.NAME + E.get("suffix", "")
CLIPS, WORK, OUT = os.path.join(D, "clips"), os.path.join(D, f"render_{MODE}"), os.path.join(D, "out")
os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
SUBST = dict(x.split(":") for x in os.environ.get("SUBST", "").split(",") if x)
SONG = os.path.join(D, proj.SONG)
ap = os.path.join(D, "align.json")
align = jload(ap) if os.path.exists(ap) else {}
beats = jload(audio_path(proj, "beats"))["beats"]
words = jload(audio_path(proj, "words")) if os.path.exists(audio_path(proj, "words")) else []
sb = jload(os.path.join(D, "storyboard.json"))
sections = jload(os.path.join(D, "shots.json"))["sections"]


HD_MISSING = set()


def picture(path):
    """enhance=True: the clip's clips_hd/ copy (enhance.py) when there is one newer than the clip, and how many times
    larger it is; otherwise the clip itself."""
    hd = hd_path(path)
    if not R["enhance"]:
        return path, 1
    if os.path.exists(hd) and os.path.getmtime(hd) >= os.path.getmtime(path):
        k = probe_w(hd) / probe_w(path)
        return hd, int(k) if k == int(k) else k
    HD_MISSING.add(os.path.basename(path))
    return path, 1


def probe_w(p):
    return int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width", "-of",
                               "csv=p=0", p], capture_output=True, text=True).stdout.split()[0])


def at_scale(vf, k):
    """RENDER["crop"] filters count pixels of the clip: scale crop= and delogo= values for a k times larger copy."""
    if k == 1:
        return vf
    num = lambda m: str(round(float(m.group(0)) * k))
    out = []
    for f in re.findall(r"(?:'[^']*'|\([^)]*\)|[^,'(])+", vf):   # commas inside quotes or brackets stay
        name, _, args = f.partition("=")
        if name == "crop":
            args = ":".join(re.sub(r"^\d+(\.\d+)?$", num, a) for a in args.split(":"))
        elif name == "delogo":
            args = ":".join(re.sub(r"(?<=^[xywh]=)\d+(\.\d+)?$", num, a) if a[:2] in ("x=", "y=", "w=", "h=") else a
                            for a in args.split(":"))
        out.append(f"{name}={args}" if args else name)
    return ",".join(out)


def snap(t):
    b = min(beats, key=lambda x: abs(x - t))
    return b if abs(b - t) <= 0.08 else t


# ---------- segments
shots = E["shots"]
CUT, END = E["cut"], E["end"]
starts = [CUT] + [snap(s[0]) for s in shots[1:]] + [END]
fr = [round((t - CUT) * FPS) for t in starts]
seglist, jobs = [], []
body = os.path.join(WORK, "body_raw.mp4")
for i, s in enumerate([] if os.environ.get("REUSE_BODY") and os.path.exists(body) else shots):
    src = SUBST.get(s[1], s[1]); off = s[2] if len(s) > 2 else 0; flags = s[3] if len(s) > 3 else ""
    n = fr[i + 1] - fr[i]
    d = n / FPS
    p, k = picture(os.path.join(CLIPS, src + ".mp4"))
    vf = []
    if src in align:  # lip-sync: the offset follows the song so the mouth stays in sync
        a = align[src]
        off = starts[i] - a["start"]
        avail = a["dur"] - off - R["tail_guard"]  # lip-sync tails often end in a white smear
        if off < 0:
            print(f"WARN {src} shot at {starts[i]:.2f} before clip start {a['start']}"); off = 0
        if avail < d:
            print(f"WARN {src} short by {d - avail:.2f}s at {starts[i]:.2f} -> freeze tail")
            vf.append(f"tpad=stop_mode=clone:stop_duration={d - avail + 0.1:.2f}")
    else:
        avail = dur_of(p) - off - 0.05
        if avail < d:  # stretch a short clip (<= 1.8x still looks natural)
            vf.append(f"setpts={d / avail:.4f}*PTS")
            print(f"slow {src} x{d / avail:.2f} at {starts[i]:.2f}")
    if src in R["crop"]:  # e.g. clips with burned-in captions
        vf.append(at_scale(R["crop"][src], k))
    fx = FOCUS.get(f"{src}@{s[0]:g}", FOCUS.get(src, 0.5))  # "LS06@133.2": one shot of a clip whose subject drifts
    vf += [f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})/2",
           f"fps={FPS}", "setsar=1",
           # same colour tags on every segment: when body_raw switches from untagged (e.g. matte_video.py output) to bt709/tv
           # mid-stream, the final ffmpeg re-inits the whole filtergraph and the song's atrim restarts -> ~2 s of audio squeezed out
           "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"]
    if "flash" in flags:
        vf.append("fade=in:st=0:d=0.16:color=white")
    out = os.path.join(WORK, f"seg_{i:03d}.mp4")
    jobs.append(["ffmpeg", "-v", "error", "-y", "-ss", f"{off:.3f}", "-i", p, "-vf", ",".join(vf), "-frames:v", str(n),
                 "-an", *venc("inter"), out])
    seglist.append(out)
    print(f"{i:3d} {starts[i]:7.2f} {d:5.2f}s {src} off={off:.2f}", flush=True)
if HD_MISSING:
    print(f"WARN enhance: no current clips_hd copy for {', '.join(sorted(HD_MISSING))} (python mvkit/enhance.py {D})")
with ThreadPoolExecutor(int(os.environ.get("JOBS", 4 if nvenc_on() else 1))) as ex:  # segments are independent
    list(ex.map(run, jobs))

if seglist:
    lst = os.path.join(WORK, "segs.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{P(p)}'\n" for p in seglist))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", body])

# ---------- kinetic subtitles
TH = proj.TYPO
epic.configure(TH, D)
epic.W, epic.H = W, H
if "zones" in E:
    epic.ZONES = E["zones"]
band = {b["id"]: b for b in sb["band"]}
sp = [x["span"] for x in sections if TH.get("specials", {}).get(x["name"].split("：")[0]) == "plates"]


def role(sid):
    b = band.get(sid)
    if not b:
        return None
    if len(b["chars"]) > 1:
        return TH.get("band_plate")
    return tuple(sb["chars"][b["chars"][0]].get("role") or ()) or None


plates = [(starts[i], starts[i + 1], *role(s[1])) for i, s in enumerate(shots)
          if sp and sp[0][0] <= starts[i] < sp[0][1] and role(s[1])]
epic.OFFSCREEN.clear()
subp = os.path.join(WORK, "lyrics.ass")
open(subp, "w", encoding="utf-8-sig").write("\n".join(epic.build(sections, words, CUT, CUT, END, beats, TH, plates=plates)) + "\n")
if epic.OFFSCREEN:
    print("WARN glyphs near the frame edge:", epic.OFFSCREEN[:10])
srt, k = [], 1  # plain SRT for the platform's CC track, timed against the final video
f = lambda v: f"{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round(v % 1 * 1000)) % 1000:03d}"
for s in sections:
    lines = s.get("lines") or []
    for i, (t, x) in enumerate(lines):
        t1 = lines[i + 1][0] if i + 1 < len(lines) else min(s["span"][1], t + 2.5)
        if CUT <= t < END:
            srt.append(f"{k}\n{f(t - CUT + OPEN_S)} --> {f(min(t1, END) - CUT + OPEN_S)}\n{x}\n"); k += 1
open(os.path.join(OUT, f"{NAME}.{R['lang']}.srt"), "w", encoding="utf-8-sig").write("\n".join(srt))

# ---------- feature tags: project.FEATURE {clip id prefix: "feature name"}; when the cut lands on a clip made with another
# feature than the previous shot, an "AutoIP｜<feature>" tag (AutoIP in orange) fades in at the top right for ~2 s (edit labels=False: none)
labp = ""
FEAT = getattr(proj, "FEATURE", {})
if FEAT and E.get("labels", True):
    feat = lambda src: next((v for k, v in sorted(FEAT.items(), key=lambda kv: -len(kv[0])) if src.startswith(k)), None)
    fs = round(46 * W / 1920) if W > H else round(52 * W / 1080)   # phones: 34 px was readable only on a big screen
    ev, prev = [], None
    for i, s in enumerate(shots):
        f_ = feat(SUBST.get(s[1], s[1]))
        if f_ and f_ != prev:
            a_, b_ = starts[i] - CUT + 0.12, min(starts[i + 1] - CUT - 0.05, starts[i] - CUT + 2.3)
            if b_ - a_ > 0.6:
                ts = lambda v: f"{int(v // 3600)}:{int(v % 3600 // 60):02d}:{v % 60:05.2f}"
                ev.append(f"Dialogue: 0,{ts(a_)},{ts(b_)},Tag,,0,0,0,,{{\\fad(250,300)\\c&H5078FF&}}AutoIP{{\\c&HFFFFFF&}}｜{f_}")
        prev = f_
    labp = os.path.join(WORK, "labels.ass")
    open(labp, "w", encoding="utf-8-sig").write("\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Tag,{proj.TYPO['font']},{fs},&H00FFFFFF,&H000000FF,&H60000000,&H60000000,0,0,0,0,100,100,1,0,3,{max(6, fs // 4)},0,9,"
        f"{round(40 * W / 1920)},{round(40 * W / 1920)},{round(36 * H / 1080)},1", "",
        "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text", *ev]) + "\n")


# ---------- promo cards (slow push-in on a still)
def card(img, secs, out):
    n = int(secs * FPS)
    vf = (f"scale={round(W * 1.1)}:{round(H * 1.1)},zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},"
          f"fade=in:st=0:d=0.4,fade=out:st={secs - 0.5}:d=0.5,setsar=1")
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(n), *venc("inter"), out])
    return out


# ---------- final
ins, vparts = ["-i", body], []
if OPEN_S:
    ins = ["-i", card(card_path("open_card"), OPEN_S, os.path.join(WORK, "open.mp4"))] + ins
if END_S:
    ins += ["-i", card(card_path("end_card"), END_S, os.path.join(WORK, "end.mp4"))]
nv = len(ins) // 2
bi = 1 if OPEN_S else 0
final = os.path.join(OUT, NAME + ".mp4")
BODY = END - CUT
esc = lambda p: P(p).replace(":", "\\:")
tags = f",subtitles='{esc(labp)}':fontsdir='{esc(os.path.join(D, 'fonts'))}'" if labp else ""
fc = (f"[{bi}:v]{R['grade']},subtitles='{esc(subp)}':fontsdir='{esc(os.path.join(D, 'fonts'))}'{tags},fade=out:st={BODY - 0.8}:d=0.8[b];"
      + "".join("[b]" if j == bi else f"[{j}:v]" for j in range(nv)) + f"concat=n={nv}:v=1:a=0[v];"
      f"[{nv}:a]atrim={CUT}:{END},asetpts=PTS-STARTPTS,afade=in:d=0.02,adelay={int(OPEN_S * 1000)}|{int(OPEN_S * 1000)},"
      f"apad=whole_dur={OPEN_S + BODY + END_S},afade=out:st={OPEN_S + BODY - 1.2}:d=1.2[a]")
run(["ffmpeg", "-v", "error", "-y", *ins, "-i", SONG, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
     *venc("final"), "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-t", str(OPEN_S + BODY + END_S), final])
print("FINAL", final, dur_of(final))

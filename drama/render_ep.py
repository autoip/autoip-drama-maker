"""Assemble an episode: edit -> picture segments -> dialogue track + ducked music + effects -> subtitles -> mp4 + srt.

usage: python drama/render_ep.py PROJECT_DIR [MODE]        MODE = a key of project.EDITS (default "main")
env:   REUSE_BODY=1      keep render_<MODE>/body_raw.mp4 (subtitle / music / sound changes only)
       VENC=x264         encode on the CPU (by default the NVIDIA GPU encodes whenever ffmpeg can: common.nvenc_on)
       JOBS=4            segments encoded in parallel (default 4 on the GPU, else 2)
       SUBST="S1_05:S1_02" stand-ins for clips that are not made yet
out:   PROJECT_DIR/out/<NAME><suffix>.mp4 and .<lang>.srt

Sound: every base row brings its own clip's audio (the dialogue and effects AutoIP generated); cutaways are silent,
so a reaction shot plays over the line it reacts to. project.MUSIC cues are ducked under that track, row `sfx=` hits
are laid on top, and the mix is normalised to RENDER["lufs"] (default -16, what phone platforms play at).
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import endcard, subs, timeline
from common import P, load_project, run, dur_of, has_audio, venc, nvenc_on, find_media, hd_path

proj = load_project(sys.argv[1])
MODE = sys.argv[2] if len(sys.argv) > 2 else "main"
D = proj.DIR
tl = timeline.resolve(proj, MODE)
for w in tl["warn"]:
    print("WARN", w)
E, R, FPS, TOTAL = tl["edit"], tl["settings"], tl["fps"], tl["total"]
R = dict(dict(grade="eq=contrast=1.03:saturation=1.05", lang="zh-TW", crop={}, lufs=-16, sfx_gain=-4, end_card="", end_s=0), **R)
R.update({k: E[k] for k in ("end_card", "end_s") if k in E})
W, H = E["size"]
FOCUS = E.get("focus", {})
NAME = proj.NAME + E.get("suffix", "")
WORK, OUT = os.path.join(D, f"render_{MODE}"), os.path.join(D, "out")
os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
if not tl["base"]:
    sys.exit("nothing to render: no rows with clips")
frames = lambda a, b: round(b * FPS) - round(a * FPS)
HD_MISSING = set()


def picture(path):
    """enhance=True: the clip's clips_hd/ copy (enhance.py) when there is one newer than the clip, and how many times
    larger it is; otherwise the clip itself."""
    hd = hd_path(path)
    if not R.get("enhance") or not path.lower().endswith(".mp4"):
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
    import re
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


# ---------- picture
body = os.path.join(WORK, "body_raw.mp4")
jobs, segs = [], []
for n, p in enumerate([] if os.environ.get("REUSE_BODY") and os.path.exists(body) else tl["pictures"]):
    nf = frames(p["t0"], p["t1"])
    if nf <= 0:
        continue
    f, vf = p["flags"], []
    path, k = picture(p["path"])
    avail = dur_of(path) - p["off"]
    if p["kind"] == "freeze":  # one frame, held (the clip may well go on after it)
        vf += ["trim=end_frame=1", "setpts=PTS-STARTPTS", f"tpad=stop_mode=clone:stop_duration={nf / FPS + 0.2:.2f}"]
    elif avail < nf / FPS:
        vf.append(f"tpad=stop_mode=clone:stop_duration={nf / FPS - avail + 0.2:.2f}")
    if p["src"] in R["crop"]:
        vf.append(at_scale(R["crop"][p["src"]], k))
    fx = FOCUS.get(p["src"], 0.5)
    vf += [f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})/2",
           f"fps={FPS}", "setsar=1"]
    if f.get("zoom"):  # punch-in: 1.0 -> Z in 0.25 s, held for the rest of the row (also after a cutaway)
        Z = float(f["zoom"]) if f["zoom"] is not True else 1.15
        rt = p["t0"] - p["row_t0"]
        vf.append(f"zoompan=z='min({Z},1+{Z - 1}*(on/{FPS}+{rt:.3f})/0.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")
    if p["kind"] == "freeze":
        vf.append("eq=saturation=0.7:brightness=-0.03")
    starts_row = p["kind"] == "clip" and abs(p["t0"] - p["row_t0"]) < 1e-6
    if starts_row and f.get("flash"):
        vf.append("fade=in:st=0:d=0.16:color=white")
    if starts_row and f.get("black"):
        vf.append("fade=in:st=0:d=0.35")
    vf.append("setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709")  # same tags on every segment
    out = os.path.join(WORK, f"seg_{n:03d}.mp4")
    jobs.append(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, p['off']):.3f}", "-i", path, "-vf", ",".join(vf),
                 "-frames:v", str(nf), "-an", *venc("inter"), out])
    segs.append(out)
    print(f"{n:3d} {p['t0']:7.2f} {p['t1'] - p['t0']:5.2f}s {p['src']:10} {p['kind']:6} off={p['off']:.2f} "
          f"{' '.join(k if v is True else f'{k}={v}' for k, v in f.items())}", flush=True)
if HD_MISSING:
    print(f"WARN enhance: no current clips_hd copy for {', '.join(sorted(HD_MISSING))} (python drama/enhance.py {D})")
with ThreadPoolExecutor(int(os.environ.get("JOBS", 4 if nvenc_on() else 2))) as ex:
    list(ex.map(run, jobs))
if segs:
    lst = os.path.join(WORK, "segs.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{P(s)}'\n" for s in segs))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", body])

# ---------- sound: dialogue track (each base row's own audio, silence under freezes), music, effects
CARD = R["end_card"]  # a picture, or a dict: a text card over the body's last frame (endcard.py)
END_S = (R["end_s"] or 3.0) if isinstance(CARD, dict) else R["end_s"] if CARD and os.path.exists(os.path.join(D, CARD)) else 0
LEN = TOTAL + END_S
AF = "aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo"
pieces = []
for n, b in enumerate(tl["base"]):
    out = os.path.join(WORK, f"aud_{n:03d}.wav")
    d = b["t1"] - b["t0"]
    if has_audio(b["path"]) and not b["flags"].get("mute"):
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{b['inn']:.3f}", "-i", b["path"], "-vn", "-af",
             f"{AF},afade=in:d=0.012,apad=whole_dur={d:.3f},atrim=0:{d:.3f},afade=out:st={max(0, d - 0.012):.3f}:d=0.012", out])
    else:
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{d:.3f}", "-af", AF, out])
    pieces.append(out)
    if b["freeze"]:
        fz = os.path.join(WORK, f"aud_{n:03d}_fz.wav")
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{b['freeze']:.3f}", "-af", AF, fz])
        pieces.append(fz)
lst = os.path.join(WORK, "aud.txt")
open(lst, "w", encoding="utf-8").write("".join(f"file '{P(s)}'\n" for s in pieces))
dlg = os.path.join(WORK, "dialogue.wav")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", dlg])


def at(v, default):
    """Music cue position: a row id (its first appearance), seconds, "end" (the end card) or None."""
    if v is None:
        return default
    if v == "end":
        return TOTAL
    if isinstance(v, (int, float)):
        return float(v)
    for b in tl["base"] + tl["over"]:
        if b["src"] == v:
            return b["t0"]
    print(f"WARN music cue at {v}: no such row, using {default:.2f}")
    return default


# padded to the end card: sidechaincompress stops at the shorter input, which cut the end card's music off
ins, fc, mus, fx_ = ["-i", dlg], [f"[0:a]{AF},apad=whole_dur={LEN:.3f},asplit=2[dl][sc]"], [], []
for cue in E.get("music", getattr(proj, "MUSIC", [])):  # (file, from, to, gain dB, start s in the file): from / to =
    f, a, z, gain, ss = (list(cue) + [None, None, -14, 0])[:5]                          # row id, seconds or None
    src = find_media(proj, "music", f)
    if not src:
        print(f"WARN music {f}: not found in music/"); continue
    a, z = at(a, 0.0), at(z, LEN)
    L = max(0.5, z - a)
    k = ins.count("-i")
    ins += ["-stream_loop", "-1", "-i", src]
    fc.append(f"[{k}:a]{AF},atrim={ss:.3f}:{ss + L:.3f},asetpts=PTS-STARTPTS,afade=in:d={min(1.0, L / 4):.2f},"
              f"afade=out:st={max(0, L - 1.5):.2f}:d={min(1.5, L):.2f},volume={gain}dB,adelay={int(a * 1000)}|{int(a * 1000)}[m{k}]")
    mus.append(f"[m{k}]")
for b in tl["base"] + tl["over"]:
    name = b["flags"].get("sfx")
    if not name:
        continue
    src = find_media(proj, "sfx", name)
    if not src:
        print(f"WARN sfx {name}: not found in sfx/"); continue
    k = ins.count("-i")
    ins += ["-i", src]
    fc.append(f"[{k}:a]{AF},volume={R['sfx_gain']}dB,adelay={int(b['t0'] * 1000)}|{int(b['t0'] * 1000)}[x{k}]")
    fx_.append(f"[x{k}]")
mix = ["[dl]"]
if mus:
    fc.append(f"{''.join(mus)}amix=inputs={len(mus)}:normalize=0,{AF}[mus]")
    fc.append("[mus][sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[duck]")
    mix.append("[duck]")
else:
    fc.append("[sc]anullsink")
mix += fx_
fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0,apad=whole_dur={LEN:.3f},atrim=0:{LEN:.3f}[a]")
rawp, mixp = os.path.join(WORK, "mix_raw.wav"), os.path.join(WORK, "mix.wav")
run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[a]", "-ac", "2", "-c:a", "pcm_f32le", rawp])
# two-pass loudness: measure, then one linear gain. Single-pass loudnorm missed by up to 4 LU (a 5 s NG reel came out
# at -11.7 LUFS, episodes anywhere from -15.7 to -17.1)
LN = f"loudnorm=I={R['lufs']}:TP=-1.5:LRA=11"
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", rawp, "-af", LN + ":print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
run(["ffmpeg", "-v", "error", "-y", "-i", rawp, "-af",
     f"{LN}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
     f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000", "-ac", "2", mixp])

# ---------- subtitles
ass, cues = subs.build(proj, tl, W, H)
subp = os.path.join(WORK, "subs.ass")
open(subp, "w", encoding="utf-8-sig").write(ass)
open(os.path.join(OUT, f"{NAME}.{R['lang']}.srt"), "w", encoding="utf-8-sig").write(subs.srt(cues))

# ---------- final
fonts = next((p for p in (os.path.join(D, "fonts"), os.path.join(os.path.dirname(D), "fonts")) if os.path.isdir(p)), os.path.join(D, "fonts"))
esc = lambda p: P(p).replace(":", "\\:")
vins, nv = ["-i", body], 1
if END_S:
    card = os.path.join(WORK, "end.mp4")
    nfc = int(END_S * FPS)
    pic, Z = os.path.join(D, CARD) if not isinstance(CARD, dict) else "", 0.06
    if isinstance(CARD, dict):  # the text card sits on the cliffhanger's last frame, blurred
        last = os.path.join(WORK, "end_bg.png")
        run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i", body, "-frames:v", "1", "-update", "1", last])
        pic, Z = endcard.make(proj, D, CARD, last, os.path.join(WORK, "end_card.png"), W, H), 0.02
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", pic, "-vf",
         f"scale={round(W * 1.1)}:{round(H * 1.1)},zoompan=z='1+{Z}*on/{nfc}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={nfc}:"
         f"s={W}x{H}:fps={FPS},fade=in:st=0:d=0.4,setsar=1", "-frames:v", str(nfc), *venc("inter"), card])
    vins += ["-i", card]; nv = 2
fcv = f"[0:v]{R['grade']},subtitles='{esc(subp)}':fontsdir='{esc(fonts)}',fade=out:st={TOTAL - 0.5:.2f}:d=0.5[b]"
fcv += ";[b][1:v]concat=n=2:v=1:a=0[v]" if nv == 2 else ";[b]null[v]"
final = os.path.join(OUT, NAME + ".mp4")
run(["ffmpeg", "-v", "error", "-y", *vins, "-i", mixp, "-filter_complex", fcv, "-map", "[v]", "-map", f"{nv}:a",
     *venc("final"), "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-t", f"{LEN:.3f}", final])
print("FINAL", final, round(dur_of(final), 2), "s,", len(cues), "subtitle cues")

"""Assemble the MV: EDL -> beat-snapped segments -> body + kinetic ASS + optional promo cards + song audio.

usage: python mvkit/render_mv.py PROJECT_DIR MODE        MODE = a key of project.EDITS ("full", "short", ...)
env:   REUSE_BODY=1   keep render_<MODE>/body_raw.mp4 (subtitle / card changes only)
       SUBST="B17:B05" temporary stand-ins for clips that are not ready yet
edit:  size=(1080, 1920) renders a portrait cut: focus={src: 0..1} picks the horizontal crop centre per clip
       ("src@row_time": 0..1 for one shot, when the subject moves across the clip),
       zones={...} replaces epic.ZONES, open_card / end_card override RENDER's cards,
       crop={src: filter} is merged over RENDER's crop (e.g. a crop only the landscape cut needs)
out:   PROJECT_DIR/out/<NAME><suffix>.mp4 and .<lang>.srt

The EDL is resolved from project.EDITS here, at render time: there is no intermediate edl.json that could belong
to a different cut.
"""
import os, sys
import epic
from common import P, load_project, jload, audio_path, run, dur_of, edit

proj = load_project(sys.argv[1])
MODE = sys.argv[2]
D = proj.DIR
R = dict(fps=25, crop={}, grade="eq=contrast=1.07:saturation=1.06,vignette=PI/5,noise=alls=4:allf=t", lang="zh-TW",
         open_card="", end_card="", tail_guard=0.35)
R.update(getattr(proj, "RENDER", {}))
E = edit(proj, MODE)
R.update({k: E[k] for k in ("open_card", "end_card") if k in E})
R["crop"] = {**R["crop"], **E.get("crop", {})}
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


def snap(t):
    b = min(beats, key=lambda x: abs(x - t))
    return b if abs(b - t) <= 0.08 else t


# ---------- segments
shots = E["shots"]
CUT, END = E["cut"], E["end"]
starts = [CUT] + [snap(s[0]) for s in shots[1:]] + [END]
fr = [round((t - CUT) * FPS) for t in starts]
seglist = []
body = os.path.join(WORK, "body_raw.mp4")
for i, s in enumerate([] if os.environ.get("REUSE_BODY") and os.path.exists(body) else shots):
    src = SUBST.get(s[1], s[1]); off = s[2] if len(s) > 2 else 0; flags = s[3] if len(s) > 3 else ""
    n = fr[i + 1] - fr[i]
    d = n / FPS
    p = os.path.join(CLIPS, src + ".mp4")
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
        vf.append(R["crop"][src])
    fx = FOCUS.get(f"{src}@{s[0]:g}", FOCUS.get(src, 0.5))  # "LS06@133.2": one shot of a clip whose subject drifts
    vf += [f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})/2",
           f"fps={FPS}", "setsar=1",
           # same colour tags on every segment: when body_raw switches from untagged (e.g. matte_video.py output) to bt709/tv
           # mid-stream, the final ffmpeg re-inits the whole filtergraph and the song's atrim restarts -> ~2 s of audio squeezed out
           "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"]
    if "flash" in flags:
        vf.append("fade=in:st=0:d=0.16:color=white")
    out = os.path.join(WORK, f"seg_{i:03d}.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{off:.3f}", "-i", p, "-vf", ",".join(vf), "-frames:v", str(n),
         "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p", out])
    seglist.append(out)
    print(f"{i:3d} {starts[i]:7.2f} {d:5.2f}s {src} off={off:.2f}", flush=True)

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


# ---------- promo cards (slow push-in on a still)
def card(img, secs, out):
    n = int(secs * FPS)
    vf = (f"scale={round(W * 1.1)}:{round(H * 1.1)},zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},"
          f"fade=in:st=0:d=0.4,fade=out:st={secs - 0.5}:d=0.5,setsar=1")
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(n),
         "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p", out])
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
fc = (f"[{bi}:v]{R['grade']},subtitles='{esc(subp)}':fontsdir='{esc(os.path.join(D, 'fonts'))}',fade=out:st={BODY - 0.8}:d=0.8[b];"
      + "".join("[b]" if j == bi else f"[{j}:v]" for j in range(nv)) + f"concat=n={nv}:v=1:a=0[v];"
      f"[{nv}:a]atrim={CUT}:{END},asetpts=PTS-STARTPTS,afade=in:d=0.02,adelay={int(OPEN_S * 1000)}|{int(OPEN_S * 1000)},"
      f"apad=whole_dur={OPEN_S + BODY + END_S},afade=out:st={OPEN_S + BODY - 1.2}:d=1.2[a]")
run(["ffmpeg", "-v", "error", "-y", *ins, "-i", SONG, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
     "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-t", str(OPEN_S + BODY + END_S), final])
print("FINAL", final, dur_of(final))

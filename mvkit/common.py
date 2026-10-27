"""Shared helpers: load a project folder, json io, ffmpeg wrappers, EDL parsing."""
import importlib.util, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_project(pdir):
    """Import <pdir>/project.py as a module (the storyboard source of truth)."""
    path = os.path.join(pdir, "project.py")
    if not os.path.exists(path):
        sys.exit(f"no project.py in {pdir}")
    spec = importlib.util.spec_from_file_location("project", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.DIR = os.path.abspath(pdir)
    return m


def P(*parts):
    """Forward-slash path (ffmpeg filters and curl are happier with it on Windows)."""
    return os.path.join(*parts).replace("\\", "/")


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jdump(obj, p, indent=1):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print(" ".join(cmd)); print(r.stderr[-2000:]); sys.exit(1)
    return r.stdout


_NVENC = None


def nvenc_ok():
    """True when this ffmpeg can encode on an NVIDIA GPU (needs a recent enough driver for the ffmpeg build)."""
    return subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.2", "-c:v", "h264_nvenc",
                           "-f", "null", "-"], capture_output=True).returncode == 0


def venc(kind="final", crf=15):
    """ffmpeg video-encoder args. x264 by default; VENC=nvenc encodes on the NVIDIA GPU (h264_nvenc). Without VENC a
    working NVENC is only suggested (python mvkit/gpu_check.py lists every GPU option).
    kind "final" = the upload file (16 Mbit/s cap; on an RTX 5060 Ti NVENC is 4x faster at VMAF 99.2 vs x264 slow 99.3),
    "inter" = intermediates that are encoded again (x264 at crf; NVENC needs -maxrate or it caps at the level 4.0 bitrate)."""
    global _NVENC
    if _NVENC is None:
        want = os.environ.get("VENC", "")
        ok = want != "x264" and nvenc_ok()
        _NVENC = want == "nvenc" and ok
        if want == "nvenc" and not ok:
            print("  VENC=nvenc: this ffmpeg cannot encode on the GPU here, using x264")
        elif not want and ok:
            print("  tip: an NVIDIA encoder is available; VENC=nvenc encodes about 4x faster at the same quality")
    if _NVENC and kind == "final":
        return ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "19", "-b:v", "0", "-maxrate", "16M",
                "-bufsize", "32M", "-spatial-aq", "1", "-temporal-aq", "1", "-rc-lookahead", "32", "-bf", "3", "-b_ref_mode", "middle",
                "-pix_fmt", "yuv420p"]
    if _NVENC:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "15", "-b:v", "0", "-maxrate", "60M",
                "-bufsize", "120M", "-spatial-aq", "1", "-bf", "3", "-pix_fmt", "yuv420p"]
    if kind == "final":
        return ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", str(crf), "-pix_fmt", "yuv420p"]


def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def audio_path(proj, key):
    """Project-relative audio asset from project.AUDIO (song.wav, beats, vocals, voices, words)."""
    v = proj.AUDIO[key]
    if isinstance(v, dict):
        return {k: os.path.join(proj.DIR, x) for k, x in v.items()}
    return os.path.join(proj.DIR, v)


def parse_edl(text):
    """'start src [offset] [flags]' rows separated by '|' or newlines -> [[t, src, off?, flags?], ...]."""
    shots = []
    for tok in text.replace("\n", "|").split("|"):
        p = tok.split("#")[0].split()
        if not p:
            continue
        row = [float(p[0]), p[1]]
        if len(p) > 2:
            row.append(float(p[2]))
        if len(p) > 3:
            row.append(p[3])
        shots.append(row)
    bad = [(a[0], b[0]) for a, b in zip(shots, shots[1:]) if a[0] >= b[0]]
    assert not bad, f"EDL rows out of order: {bad}"
    return shots


def edit(proj, mode):
    """Resolve project.EDITS[mode] (shots may reference other modes with '@name')."""
    e = dict(proj.EDITS[mode])
    text = e["shots"]
    for k in sorted(proj.EDITS, key=len, reverse=True):  # "@shorts" before "@short"
        text = text.replace("@" + k, proj.EDITS[k]["shots"] if k != mode else "")
    e["shots"] = parse_edl(text)
    return e


def label_font(size):
    """A bold UI font for labelling review sheets, whatever the OS."""
    from PIL import ImageFont
    for f in ("DejaVuSans-Bold.ttf", "consolab.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default(size)

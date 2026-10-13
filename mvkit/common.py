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
    for k in proj.EDITS:
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

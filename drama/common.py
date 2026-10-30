"""Drama helpers: the canvas, where an EDL source lives, sfx / music lookup, the drama EDL format.
The helpers every line shares (project loading, json io, ffmpeg, encoder, credits) come from dreamfab.util."""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # the repo root: the shared core is the dreamfab package
from dreamfab.util import (load_project, P, jload, jdump, run, nvenc_ok, nvenc_on, venc, dur_of, has_audio, hd_path,
                          fingerprint, PRICE, estimate, off_peak, label_font)  # re-exported: scripts import them from common


def canvas(proj):
    """Output size from project.ASPECT: "9:16" (default, vertical short drama) or "16:9"."""
    return (1920, 1080) if getattr(proj, "ASPECT", "9:16") == "16:9" else (1080, 1920)


def clip_path(proj, src):
    """EDL source -> video file. A bare id is clips/<id>.mp4; a path (e.g. ../s1e01/clips/S3_05 for a recap) is
    relative to the project folder."""
    if "/" in src or "\\" in src:
        p = os.path.join(proj.DIR, src)
        return p if os.path.splitext(p)[1] else p + ".mp4"
    return os.path.join(proj.DIR, "clips", src + ".mp4")


def find_media(proj, sub, name):
    """sfx/<name>.wav, music/<name>.mp3 ...: looks in the episode folder, then in the series folder above it."""
    if os.path.splitext(name)[1]:
        for base in (proj.DIR, os.path.dirname(proj.DIR)):
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
    for base in (proj.DIR, os.path.dirname(proj.DIR)):
        for ext in ("", ".wav", ".mp3", ".m4a", ".flac", ".ogg"):
            p = os.path.join(base, sub, name + ext)
            if os.path.isfile(p):
                return p
    return None


# ---------------------------------------------------------------- EDL
NUM = re.compile(r"^-?\d+(\.\d+)?$")


def parse_edl(text):
    """Drama EDL rows, one per line (or separated by '|'); '#' starts a comment.

        src [in|auto] [dur] [flag ...]      base row: picture + sound of src, laid end to end
        ^src [in] [dur] @at [flag ...]      cutaway: picture only, over the previous base row, starting `at` s after its
                                            start (at < 0: before its end); may run on into the next rows
    flags: flash, black, zoom, mute, title, end[=text], freeze=S, sfx=name, intro=KEY, label=text
    -> [dict(src, inn (None = auto), dur (None = to the end / auto), flags {}, over, at)]
    """
    rows = []
    for tok in text.replace("|", "\n").split("\n"):
        p = tok.split("#")[0].split()
        if not p:
            continue
        over = p[0].startswith("^")
        r = dict(src=p[0].lstrip("^"), inn=None if not over else 0.0, dur=None, flags={}, over=over, at=0.0)
        nums = []
        for x in p[1:]:
            if x == "auto":
                nums.append(None)
            elif NUM.match(x):
                nums.append(float(x))
            elif x.startswith("@") and NUM.match(x[1:]):
                r["at"] = float(x[1:])
            else:
                k, _, v = x.partition("=")
                r["flags"][k] = v or True
        if nums:
            r["inn"] = nums[0] if nums[0] is not None or not over else 0.0
        if len(nums) > 1:
            r["dur"] = nums[1]
        assert not over or rows, f"cutaway {p[0]} needs a base row before it"
        rows.append(r)
    return rows


def edit(proj, mode):
    """Resolve project.EDITS[mode]: '@name' on a line of its own pastes another edit's rows (e.g. a recap)."""
    e = dict(proj.EDITS[mode])
    lines = []
    for ln in e["shots"].split("\n"):
        k = ln.split("#")[0].strip()
        if k.startswith("@") and k[1:] in proj.EDITS and k[1:] != mode:
            lines.append(proj.EDITS[k[1:]]["shots"])
        else:
            lines.append(ln)
    e["rows"] = parse_edl("\n".join(lines))
    e.setdefault("size", canvas(proj))
    return e


# ---------------------------------------------------------------- credits
# GET /api/v1/pricing on 2026-10-27: an estimate to show before a batch, not an invoice (credits.py audits what was
# charged). Multi-reference video is not linear in seconds (768p: 5 s 80, 6 s 115, 10 s 265; 2k 10 s is 195).



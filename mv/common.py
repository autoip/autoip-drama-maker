"""MV helpers: audio assets from project.AUDIO and the MV EDL format.
The helpers every line shares (project loading, json io, ffmpeg, encoder, credits) come from dreamfab.util."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # the repo root: the shared core is the dreamfab package
from dreamfab.util import (load_project, P, jload, jdump, run, nvenc_ok, nvenc_on, venc, dur_of, has_audio, hd_path,
                          fingerprint, PRICE, estimate, off_peak, label_font)  # re-exported: scripts import them from common


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


# ---------------------------------------------------------------- credits
# GET /api/v1/pricing on 2026-10-28: an estimate to show before a batch, not an invoice (credits.py audits what was
# charged). Multi-reference video is not linear in seconds (768p: 5 s 80, 6 s 115, 10 s 265). From 2026-10-30 tasks
# submitted with an API key in the off-peak window (03:00-09:00 Asia/Taipei, aip_runner.py AIP_OFFPEAK=1) cost half,
# rounded up, at least 1.



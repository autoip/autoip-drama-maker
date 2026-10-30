"""Where does each lip-sync clip's audio sit in the song? -> align.json {LS id: {start, dur, corr, req}}.

usage: python mv/qc/align.py PROJECT_DIR
Lip-sync services may trim or pad the audio you send, so the requested a0 is not always clip t=0. This
cross-correlates onset envelopes (10 ms resolution, +-3 s around a0). render_mv.py uses `start` to pick the clip
offset that keeps the mouth in sync with the song, and `dur` to avoid running past the end.
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import librosa, numpy as np
from common import load_project, jload, jdump, audio_path, dur_of

proj = load_project(sys.argv[1])
D = proj.DIR
SR, HOP = 8000, 80
voices = audio_path(proj, "voices")
env_of = {}
res = {}
for l in jload(os.path.join(D, "shots.json"))["lipsync"]:
    p = os.path.join(D, "clips", l["id"] + ".mp4")
    if not os.path.exists(p):
        print(l["id"], "missing"); continue
    if l["voice"] not in env_of:
        s, _ = librosa.load(voices[l["voice"]], sr=SR, mono=True)
        env_of[l["voice"]] = librosa.onset.onset_strength(y=s, sr=SR, hop_length=HOP)
    env_s = env_of[l["voice"]]
    w = os.path.join(D, "jobs", "aud", l["id"] + "_clip.wav")
    os.makedirs(os.path.dirname(w), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vn", "-ac", "1", "-ar", str(SR), w], check=True)
    y, _ = librosa.load(w, sr=SR, mono=True)
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    best, bl = -1, 0
    c0 = int(l["a0"] * 100)
    for lag in range(max(0, c0 - 300), c0 + 300):
        seg = env_s[lag:lag + len(env)]
        if len(seg) < len(env):
            break
        v = np.corrcoef(seg, env)[0, 1]
        if v > best:
            best, bl = v, lag
    res[l["id"]] = dict(start=bl / 100, dur=dur_of(p), corr=round(float(best), 3), req=l["a0"])
    print(l["id"], res[l["id"]], "" if best > 0.5 else "  <- low correlation, check by eye")
jdump(res, os.path.join(D, "align.json"))

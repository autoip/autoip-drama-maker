"""Split one vocal stem into per-singer tracks with soft gain masks, so each lip-sync mouth only moves on its own lines.

usage: python mvkit/audio/split_voices.py PROJECT_DIR
project.VOICE_SPANS = {"F": [(16.5, 22.4), ...]}  spans of the first voice; every other voice in AUDIO["voices"]
gets the complement. Masks have 50 ms ramps and a -36 dB floor (silence, but no hard clicks).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, soundfile as sf
from common import load_project, audio_path

proj = load_project(sys.argv[1])
y, sr = sf.read(audio_path(proj, "vocals"))
out = audio_path(proj, "voices")
(key, spans), = proj.VOICE_SPANS.items()
m = np.zeros(len(y))
for a, b in spans:
    m[int(a * sr):int(b * sr)] = 1
k = int(0.05 * sr)
m = np.convolve(m, np.ones(k) / k, "same")
floor = 10 ** (-36 / 20)
for v, path in out.items():
    g = floor + (1 - floor) * (m if v == key else 1 - m)
    sf.write(path, y * (g[:, None] if y.ndim == 2 else g), sr)
    print(v, path)

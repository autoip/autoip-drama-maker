"""Beat grid and song structure -> beats.json {tempo, beats, onsets, strong, rms, segments}.

usage: python mv/audio/analyze.py song.wav beats.json
Cut points are snapped to `beats` (render_mv.py), `strong` hits are flash candidates, `segments` hint at sections.
"""
import json, sys
import librosa, numpy as np

p, out = sys.argv[1], sys.argv[2]
y, sr = librosa.load(p, sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
onset_env = librosa.onset.onset_strength(y=y, sr=sr)
onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units="time")
rms = librosa.feature.rms(y=y, hop_length=sr // 2)[0]  # per 0.5 s
times = librosa.times_like(onset_env, sr=sr)
strong = []
for i in np.argsort(onset_env)[::-1]:  # strongest onsets at least 1.5 s apart
    t = float(times[i])
    if all(abs(t - s) > 1.5 for s in strong):
        strong.append(t)
    if len(strong) >= 60:
        break
mf = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
bt = librosa.frames_to_time(librosa.segment.agglomerative(mf, 14), sr=sr)
json.dump(dict(tempo=float(np.atleast_1d(tempo)[0]), beats=[round(float(b), 3) for b in beats],
               onsets=[round(float(o), 3) for o in onsets], strong=sorted(round(s, 2) for s in strong),
               rms=[round(float(r), 4) for r in rms], segments=[round(float(b), 2) for b in bt]), open(out, "w"))
print("tempo", tempo, "beats", len(beats))
print("segments", [round(float(b), 1) for b in bt])
print("rms/0.5s:", " ".join(f"{r:.2f}" for r in rms))

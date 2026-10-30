"""Who is singing when: per-window activity and pitch of the isolated vocal stem.

usage: python mv/audio/voice_probe.py vocals.wav [window_s=1.0]
Prints one row per window: activity, voiced ratio, median f0. In a duet of growl + soprano the soprano windows are
clearly voiced with a high f0 (> ~350 Hz); growls are active but barely voiced. Read the table, write the spans of one
voice into project.VOICE_SPANS and run split_voices.py.
"""
import sys
import librosa, numpy as np

y, sr = librosa.load(sys.argv[1], sr=16000)
win = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
hop = 320
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
f0, vf, _ = librosa.pyin(y, fmin=70, fmax=1100, sr=sr, hop_length=hop)
step = int(win * sr / hop)
thr = np.percentile(rms, 60) * 0.6
print("   t    act  voiced    f0   rms   guess")
for i in range(0, len(rms), step):
    r, f, v = rms[i:i + step], f0[i:i + step], vf[i:i + step]
    act, vr = (r > thr).mean(), v.mean()
    med = np.nanmedian(f[v]) if v.sum() > 3 else float("nan")
    guess = "" if act < 0.2 else ("HIGH/clean" if vr > 0.4 and med > 350 else ("low/rough" if vr < 0.25 else "mid"))
    print(f"{i * hop / sr:6.1f}  {act:.2f}  {vr:.2f}  {med:6.0f}  {r.mean():.3f}  {guess}")

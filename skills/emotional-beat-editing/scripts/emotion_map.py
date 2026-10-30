"""Emotion map of a song for emotional-beat editing.

usage: python mv/audio/emotion_map.py song.wav beats.json [vocals.wav]
  beats.json: {"beats": [seconds...]}  (from librosa beat tracking)
prints one row per bar: time, energy, stage (low/build/peak/drop), suggested cut density,
plus vocal breath points, energy drops and the strongest hits.
"""
import json, sys
import numpy as np
import librosa

song, beats_p = sys.argv[1], sys.argv[2]
vocals = sys.argv[3] if len(sys.argv) > 3 else None
SR, HOP = 22050, 512
y, _ = librosa.load(song, sr=SR, mono=True)
rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
onset = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
t_of = lambda i: i * HOP / SR
fr = lambda t: int(t * SR / HOP)
beats = json.load(open(beats_p))["beats"]
bars = beats[::4]
if not bars or bars[0] > 0.5:
    bars = [0.0] + bars
bars.append(len(y) / SR)

e = np.array([rms[fr(a):max(fr(a) + 1, fr(b))].mean() for a, b in zip(bars, bars[1:])])
lo, hi = np.percentile(e, 3), np.percentile(e, 90)
en = np.clip((e - lo) / max(1e-6, hi - lo), 0, 1)
sm = np.convolve(en, np.ones(3) / 3, "same")

print("bar   time   energy  stage  cuts       bar")
stages = []
for i, (a, v) in enumerate(zip(bars, en)):
    d = sm[i] - (sm[i - 2] if i >= 2 else sm[i])
    prev = en[i - 1] if i else v
    if prev - v > 0.35:
        st = "drop"
    elif v > 0.7:
        st = "peak"
    elif d > 0.12:
        st = "build"
    else:
        st = "low" if v < 0.45 else "mid"
    stages.append(st)
    cuts = {"peak": "1-2 拍一切", "build": "每小節一切", "mid": "每 1-2 小節", "low": "2 小節以上/特寫長鏡頭", "drop": "不要切（留白）"}[st]
    print(f"{i:3d} {a:7.2f}  {v:5.2f}   {st:5s}  {cuts:14s} " + "█" * int(v * 30))

# energy drops: the moment after which the music suddenly thins out -> breathing room
print("\nDROPS (留白候選，切點不要放在這之後的 1-2 秒):")
for i in range(1, len(en)):
    if en[i - 1] - en[i] > 0.35:
        print(f"  {bars[i]:7.2f}  {en[i - 1]:.2f} -> {en[i]:.2f}")

# strongest hits: onset peaks on beats
print("\nHITS (最強重拍，適合 flash / 變速卡點):")
bstr = [(onset[max(0, fr(b) - 2):fr(b) + 3].max(), b) for b in beats if fr(b) + 3 < len(onset)]
for s, b in sorted(bstr, reverse=True)[:12]:
    print(f"  {b:7.2f}  strength {s:.1f}")

if vocals:
    v, _ = librosa.load(vocals, sr=SR, mono=True)
    vr = librosa.feature.rms(y=v, hop_length=HOP)[0]
    vr = np.convolve(vr, np.ones(5) / 5, "same")
    on = vr > np.percentile(vr, 55) * 0.5
    print("\nBREATHS (人聲換氣/句尾停頓 >= 0.35s，不要在停頓中間切；切在停頓結束、下一句開口的瞬間):")
    i = 0
    while i < len(on):
        if not on[i]:
            j = i
            while j < len(on) and not on[j]:
                j += 1
            g = t_of(j) - t_of(i)
            if 0.35 <= g <= 4 and i > 0 and j < len(on):
                print(f"  {t_of(i):7.2f} - {t_of(j):7.2f}  ({g:.2f}s)")
            i = j
        else:
            i += 1

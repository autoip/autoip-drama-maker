"""Is the mouth actually moving? MediaPipe jawOpen per lip-sync clip.

usage: python mv/qc/mouth.py PROJECT_DIR timeline LS01 LS02 ...   jawOpen std per 1 s window every 0.5 s ('.' = no face)
       python mv/qc/mouth.py PROJECT_DIR edl MODE                 one row per lip-sync shot of the edit, verdict OK / IDLE?

Lip-sync clips can stay idle for the first seconds, or zoom out until the face is too small to read. Use the
timeline to choose offsets, and the edl check before every render.
The edl check also correlates the jaw with the loudness of the clip's own audio (the voice track it was made from,
best of -0.2..+0.2 s lag): a mouth that moves but not with the words (stuck open, chewing at random) gets OFF?.
Sustained notes can score low too: look at those shots before replacing them.
"""
import os, statistics as st, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, librosa, numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from common import HERE, load_project, jload, audio_path, edit

proj = load_project(sys.argv[1])
D, MODE = proj.DIR, sys.argv[2]
model = os.environ.get("FACE_MODEL", os.path.join(os.path.dirname(HERE), "models", "face_landmarker.task"))
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model), output_face_blendshapes=True, num_faces=1))
align = jload(os.path.join(D, "align.json"))
cache = {}


def jaw_series(k):
    """[(t, jawOpen or None)] at ~10 fps; small faces get a second try on an upscaled upper-centre crop."""
    if k in cache:
        return cache[k]
    cap = cv2.VideoCapture(os.path.join(D, "clips", k + ".mp4"))
    fps = cap.get(cv2.CAP_PROP_FPS); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ser = []
    for i in range(0, n, max(1, round(fps / 10))):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, fr = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not r.face_blendshapes:
            h, w = rgb.shape[:2]
            c = cv2.resize(rgb[0:int(h * .6), int(w * .25):int(w * .75)], None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=c.copy()))
        jaw = next((b.score for b in r.face_blendshapes[0] if b.category_name == "jawOpen"), None) if r.face_blendshapes else None
        ser.append((i / fps, jaw))
    cache[k] = ser
    return ser


acache = {}


def clip_rms(k):
    """Loudness of the clip's own audio at 10 fps (the lip-sync audio, so it is frame-aligned with jaw_series)."""
    if k not in acache:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(D, "clips", k + ".mp4"), "-f", "s16le", "-ac", "1",
                              "-ar", "16000", "-"], capture_output=True).stdout
        y = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        acache[k] = librosa.feature.rms(y=y, hop_length=1600)[0] if y.size else np.zeros(1)
    return acache[k]


def sync(k, off0, off1):
    """Best Pearson r between jawOpen and clip loudness over the window, lags -0.2..+0.2 s; None if too little face."""
    ser = [(t, j) for t, j in jaw_series(k) if off0 <= t < off1 and j is not None]
    if len(ser) < 8:
        return None
    a = clip_rms(k); best = -1.0
    for lag in (-2, -1, 0, 1, 2):
        idx = [int(round(t * 10)) + lag for t, _ in ser]
        pairs = [(j, a[i]) for (_, j), i in zip(ser, idx) if 0 <= i < len(a)]
        if len(pairs) < 8:
            continue
        x, y = np.array(pairs).T
        if x.std() < 1e-4 or y.std() < 1e-4:
            continue
        best = max(best, float(np.corrcoef(x, y)[0, 1]))
    return best


if MODE == "timeline":
    for k in sys.argv[3:]:
        ser = jaw_series(k); row = []; t = 0
        while t < align[k]["dur"] - 0.5:
            w = [j for tt, j in ser if t <= tt < t + 1]; s = [j for j in w if j is not None]
            row.append("  . " if len(s) < max(3, len(w) * .5) else f"{st.pstdev(s) * 100:3.0f} "); t += 0.5
        print(k, f"{align[k]['start']:6.1f}", "".join(row), flush=True)
else:
    e = edit(proj, sys.argv[3])
    voc, sr = librosa.load(audio_path(proj, "vocals"), sr=16000, mono=True)
    rms = librosa.feature.rms(y=voc, hop_length=1600)[0]  # 10 fps
    shots = e["shots"]
    print("song_t  src   off   dur  vocal  face%  jaw_mean jaw_std  sync   verdict")
    for i, s in enumerate(shots):
        nxt = shots[i + 1][0] if i + 1 < len(shots) else e["end"]
        if not s[1].startswith("LS"):
            continue
        off0, off1 = s[0] - align[s[1]]["start"], nxt - align[s[1]]["start"]
        pts = [j for t, j in jaw_series(s[1]) if off0 <= t < off1]
        seen = [j for j in pts if j is not None]
        v = float(rms[int(s[0] * 10):int(nxt * 10)].mean())
        face = len(seen) / max(1, len(pts))
        jm, js = (float(np.mean(seen)), float(np.std(seen))) if seen else (0, 0)
        r = sync(s[1], off0, off1)
        verdict = "IDLE?" if v > 0.03 and (face < 0.5 or js < 0.06) else ("OFF?" if v > 0.03 and r is not None and r < 0.25 else "OK")
        rs = "  -  " if r is None else f"{r:+.2f}"
        print(f"{s[0]:6.1f} {s[1]:5s} {off0:5.1f} {nxt - s[0]:4.1f}  {v:.3f}  {face:4.0%}   {jm:.2f}    {js:.3f}   {rs}  {verdict}", flush=True)

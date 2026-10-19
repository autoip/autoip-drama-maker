"""Push-in check for lip-sync clips: how big the face gets, and when (lip-sync 3.0 often zooms to an extreme close-up).

usage: python mvkit/qc/zoom.py PROJECT_DIR [clip.mp4 ...]     (no clips: every PROJECT_DIR/clips/LS*.mp4)

Every STEP seconds (env, default 2) finds the face (MediaPipe) and prints its width as a % of the frame width, then
  ratio  = the largest width / the first one
  push@  = the first sample above 1.3x the first width
  verdict: ok (< 1.3x) · LATE (pushes only after 10 s) · PUSH (a gradual zoom) · JUMP (> 2x within 2 s)
A clip that pushes is still usable up to push@; compare takes of the same lyric and keep the steady one.
"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from common import HERE, load_project

proj = load_project(sys.argv[1])
clips = sys.argv[2:] or sorted(glob.glob(os.path.join(proj.DIR, "clips", "LS*.mp4")))
STEP = float(os.environ.get("STEP", 2))
model = os.environ.get("FACE_MODEL", os.path.join(os.path.dirname(HERE), "models", "face_landmarker.task"))
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model), num_faces=1))


def face_width(cap, t):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    if not ok:
        return None
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))))
    if not r.face_landmarks:
        return None
    xs = [p.x for p in r.face_landmarks[0]]
    return (max(xs) - min(xs)) * 100


print(f"{'clip':<28} {'sec':>5}  face width % every {STEP:g} s{'':<26} ratio  push@  verdict")
for path in clips:
    cap = cv2.VideoCapture(path)
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)
    ts = list(np.arange(0, max(dur - 0.3, 0.1), STEP))
    ws = [face_width(cap, t) for t in ts]
    w0 = next((w for w in ws if w), None)
    if not w0:
        print(f"{os.path.basename(path):<28} {dur:5.1f}  no face found")
        continue
    ratio = max(w for w in ws if w) / w0
    push = next((t for t, w in zip(ts, ws) if w and w > 1.3 * w0), None)
    jump = any(w and w > 2 * w0 for t, w in zip(ts, ws) if t <= 2.0)
    verdict = "JUMP" if jump else "ok" if push is None else "LATE" if push >= 10 else "PUSH"
    row = " ".join("  . " if w is None else f"{w:4.0f}" for w in ws)
    print(f"{os.path.basename(path):<28} {dur:5.1f}  {row:<50} {ratio:4.2f}  {'' if push is None else f'{push:4.0f}':>5}  {verdict}")

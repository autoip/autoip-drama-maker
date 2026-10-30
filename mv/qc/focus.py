"""Portrait crop centres: where is the face in each clip of an edit? -> focus={...} for a portrait cut.

usage: python mvkit/qc/focus.py PROJECT_DIR MODE

MODE is an EDITS entry with size=(1080, 1920) (or any size). For every clip the edit uses, samples frames across the
span it plays, finds the face (MediaPipe) and prints the crop centre (0 = left edge, 1 = right edge) that puts the
face in the middle of the narrow window. Clips without a face print '?': leave them at 0.5 or pick a centre by eye
from a frame sheet of the first render. RENDER["crop"] (burned-in caption crops) is applied first, like the renderer.
"""
import os, re, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from common import HERE, load_project, jload, edit

proj = load_project(sys.argv[1])
D, MODE = proj.DIR, sys.argv[2]
E = edit(proj, MODE)
TW, TH = E.get("size", (1080, 1920))
model = os.environ.get("FACE_MODEL", os.path.join(os.path.dirname(HERE), "models", "face_landmarker.task"))
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model), num_faces=1))
ap = os.path.join(D, "align.json")
align = jload(ap) if os.path.exists(ap) else {}
crops = getattr(proj, "RENDER", {}).get("crop", {})

shots = E["shots"]
starts = [E["cut"]] + [s[0] for s in shots[1:]] + [E["end"]]
spans = {}  # src -> [clip seconds to sample]
for i, s in enumerate(shots):
    src, d = s[1], starts[i + 1] - starts[i]
    off = starts[i] - align[src]["start"] if src in align else (s[2] if len(s) > 2 else 0)
    spans.setdefault(src, []).extend(off + d * k for k in (0.1, 0.5, 0.9))

found = {}
print(f"{'clip':6} {'face':>5} {'focus':>6}  samples")
for src, ts in spans.items():
    cap = cv2.VideoCapture(os.path.join(D, "clips", src + ".mp4"))
    xs, size = [], None
    for t in ts:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000); ok, fr = cap.read()
        if not ok:
            continue
        m = re.match(r"crop=(\d+):(\d+):(\d+):(\d+)", crops.get(src, ""))
        if m:
            w, h, x, y = map(int, m.groups()); fr = fr[y:y + h, x:x + w]
        size = fr.shape[:2]
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
        if r.face_landmarks:
            lx = [p.x for p in r.face_landmarks[0]]
            xs.append((min(lx) + max(lx)) / 2)
    if not xs:
        print(f"{src:6} {'-':>5} {'?':>6}  0/{len(ts)}")
        continue
    fx = st.median(xs)
    win = min(1.0, size[0] * TW / TH / size[1])  # width of the portrait window as a fraction of the clip
    found[src] = round(min(1.0, max(0.0, (fx - win / 2) / (1 - win))), 2) if win < 1 else 0.5
    print(f"{src:6} {fx:5.2f} {found[src]:6.2f}  {len(xs)}/{len(ts)}")
print("\nfocus=" + repr({k: v for k, v in found.items() if abs(v - 0.5) >= 0.03}))

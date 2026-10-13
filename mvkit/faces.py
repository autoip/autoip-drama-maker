"""Face box for every character image -> faces.json {file: [cx, cy, width]} (MediaPipe FaceLandmarker).

usage: python mvkit/faces.py PROJECT_DIR
Needs models/face_landmarker.task (see docs/SETUP.md). Existing entries are kept, so a box you add by hand for a
stylised face the detector misses ([centre x, centre y, face width] in pixels) survives re-runs.
"""
import os, sys
import mediapipe as mp, numpy as np
from PIL import Image
from mediapipe.tasks.python import vision, BaseOptions
from common import HERE, load_project, jload, jdump

proj = load_project(sys.argv[1])
model = os.environ.get("FACE_MODEL", os.path.join(os.path.dirname(HERE), "models", "face_landmarker.task"))
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model), num_faces=1))
fp = os.path.join(proj.DIR, "faces.json")
out = jload(fp) if os.path.exists(fp) else {}
for c in proj.CHARS.values():
    f = c["file"]
    im = Image.open(os.path.join(proj.DIR, f)).convert("RGB")
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(im)))
    if not r.face_landmarks:
        print("no face", f, "(kept)" if f in out else "-> add [cx, cy, width] by hand if needed"); continue
    xs = [p.x * im.width for p in r.face_landmarks[0]]; ys = [p.y * im.height for p in r.face_landmarks[0]]
    out[f] = [int(np.mean(xs)), int(np.mean(ys)), int(max(xs) - min(xs))]
    print(f, im.size, out[f])
jdump(out, fp, indent=0)

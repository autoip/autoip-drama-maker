"""Put the person of a lip-sync clip onto a still background picture, frame by frame (MediaPipe selfie segmentation).

usage: python mvkit/matte_video.py IN.mp4 BG.png OUT.mp4      env BLUR (default 3), EMA (default 0.5)

Why: the lip-sync model can repaint a painted background as a photograph (lip-sync 3.0 did it within 0.8 s in a test
whose still stood the singer in an ink-wash painting). Re-compositing every frame keeps the painted world; the person
and the mouth come from the clip. The mask is smoothed over time (EMA = weight of the new frame) so the edge does not
flicker, holes inside the person (pale cloth reads as background) are filled, and the edge is pulled in 2 px and
feathered. Thin hair ornaments can be clipped in the first frames. CPU only: a 20 s 1344x768 clip takes ~40 s.
Needs models/selfie_multiclass_256x256.tflite (see models/README.md); SEG_MODEL overrides the path. Audio is copied.
"""
import json, os, subprocess, sys
import cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

HERE = os.path.dirname(os.path.abspath(__file__))
src, bgp, out = sys.argv[1:4]
BLUR, EMA = float(os.environ.get("BLUR", 3)), float(os.environ.get("EMA", 0.5))
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                  "-of", "json", src], capture_output=True, text=True).stdout)["streams"][0]
w, h, fps = info["width"], info["height"], info["r_frame_rate"]
seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=BaseOptions(model_asset_path=os.environ.get("SEG_MODEL", os.path.join(os.path.dirname(HERE), "models",
                                                                                         "selfie_multiclass_256x256.tflite"))),
    running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True))

b = cv2.cvtColor(cv2.imdecode(np.fromfile(bgp, np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
sc = max(w / b.shape[1], h / b.shape[0])
b = cv2.resize(b, (round(b.shape[1] * sc), round(b.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
y0, x0 = (b.shape[0] - h) // 2, (b.shape[1] - w) // 2
bg = b[y0:y0 + h, x0:x0 + w].astype(np.float32)
if BLUR > 0:
    bg = cv2.GaussianBlur(bg, (int(BLUR * 3) | 1, int(BLUR * 3) | 1), BLUR)

dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", fps, "-i", "-",
                        "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", "-shortest", out], stdin=subprocess.PIPE)
num, den = (int(x) for x in fps.split("/"))
prev, n = None, 0
while True:
    raw = dec.stdout.read(w * h * 3)
    if len(raw) < w * h * 3:
        break
    a = np.frombuffer(raw, np.uint8).reshape(h, w, 3)
    m = 1 - np.squeeze(seg.segment_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(a)),
                                             int(n * 1000 * den / num)).confidence_masks[0].numpy_view())
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
    prev = m if prev is None else EMA * m + (1 - EMA) * prev
    hard = (prev > 0.5).astype(np.uint8)
    ff = cv2.copyMakeBorder(1 - hard, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=1)
    cv2.floodFill(ff, None, (0, 0), 0)  # what the person encloses (pale cloth, the gap under the chin) is person
    hard = np.maximum(hard, ff[1:-1, 1:-1])
    k, lab, stats, _ = cv2.connectedComponentsWithStats(hard, connectivity=8)
    if k > 2:  # one person: drop islands of background the segmenter mistook for a person
        hard = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    alpha = cv2.GaussianBlur(cv2.erode(hard, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 2.0)[..., None]
    enc.stdin.write((a.astype(np.float32) * alpha + bg * (1 - alpha)).clip(0, 255).astype(np.uint8).tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print(out, n, "frames")

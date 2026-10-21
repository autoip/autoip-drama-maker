"""Lip-sync still with the background turned into a shallow depth of field; the person is untouched.
usage: python mvkit/bokeh_still.py OUT_DIR P/kf/L_*.png      env BLUR (default 22), DARK (0 = no darkening, 0.25 = night tint),
       SOLID_TORSO=1 for a bare half-body with nothing in the hands (fills notches the segmenter bites out of fur or pale cloth)
       BG=picture.png puts that picture behind the person instead of the blurred original (cover-fit, still blurred by BLUR)

Why: on a sharp, detailed background (painted skies, scenery) the lip-sync model tends to write the lyrics as vertical
calligraphy or signage in the scene, which /videos/restore cannot remove. On a blurred background it falls back to a
bottom-line subtitle, which restore `operations[]=subtitle` does remove.

No halo: the person is first painted out of the background (inpaint), so the blur does not smear the clothes outward,
and the body mask is pulled in, never grown, so no ring of sharp background is left around the shoulders. The selfie
segmenter misses a topknot or hat sticking out above the head, so dark pixels over the crown are added to the head mask.
Needs models/face_landmarker.task and models/selfie_multiclass_256x256.tflite (see models/README.md);
FACE_MODEL / SEG_MODEL override the paths.
"""
import os, sys
import cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(os.path.dirname(HERE), "models")
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
BLUR, DARK = float(os.environ.get("BLUR", 22)), float(os.environ.get("DARK", 0))
BG = os.environ.get("BG", "")
SOLID = os.environ.get("SOLID_TORSO", "0") == "1"
seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=BaseOptions(model_asset_path=os.environ.get("SEG_MODEL", os.path.join(MODELS, "selfie_multiclass_256x256.tflite"))),
    output_confidence_masks=True))
fl = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=os.environ.get("FACE_MODEL", os.path.join(MODELS, "face_landmarker.task"))), num_faces=1))
for p in sys.argv[2:]:
    a = cv2.cvtColor(cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB); h, w = a.shape[:2]  # imread can't open non-ASCII paths on Windows
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(a))
    m = 1 - np.squeeze(seg.segment(img).confidence_masks[0].numpy_view())
    hard = (m > 0.5).astype(np.uint8)
    head = np.zeros((h, w), np.uint8)
    L = fl.detect(img).face_landmarks
    if L:  # hair, topknot, hat or crown: lenient mask, holes closed, not pulled in (thin ornaments would be eaten)
        xs = [q.x * w for q in L[0]]; ys = [q.y * h for q in L[0]]
        fw = max(xs) - min(xs); cx = (max(xs) + min(xs)) / 2; top = min(ys)
        yy, xx = np.mgrid[0:h, 0:w]
        ell = ((xx - cx) / (0.42 * fw)) ** 2 + ((yy - (top - 0.55 * fw)) / (0.75 * fw)) ** 2 <= 1
        lum = a.astype(np.float32) @ [0.299, 0.587, 0.114]
        head = (((xx - cx) / (1.25 * fw)) ** 2 + ((yy - (top - 0.1 * fw)) / (1.3 * fw)) ** 2 <= 1) & (yy < top + 0.35 * fw)
        hm = ((m > 0.3) | (ell & (lum < 48))).astype(np.uint8)
        kk = max(9, int(fw * 0.12)) | 1
        hm = cv2.morphologyEx(hm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk)))
        head = head.astype(np.uint8)
        hard = np.where(head > 0, np.maximum(hard, hm), hard).astype(np.uint8)
        if SOLID:  # bare torso (no props): every row below the chin is solid from its leftmost to its rightmost person pixel
            chin = int(max(ys) + 0.15 * fw)
            for y in range(min(chin, h), h):
                xs_row = np.flatnonzero(hard[y])
                if len(xs_row):
                    hard[y, xs_row[0]:xs_row[-1] + 1] = 1
    # white fur or pale cloth reads as background: fill holes the person encloses, and drop islands cut off from the
    # person (a prop's head left sharp while its neck is blurred looks pasted on)
    ff = cv2.copyMakeBorder((1 - hard).astype(np.uint8), 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=1)
    cv2.floodFill(ff, None, (0, 0), 0)  # background reachable from the frame edge -> 0; what is left is enclosed
    hard = np.maximum(hard, ff[1:-1, 1:-1])
    n, lab, stats, _ = cv2.connectedComponentsWithStats(hard, connectivity=8)
    if n > 2:
        keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        hard = (lab == keep).astype(np.uint8)
    # background without the person: inpaint a generously grown mask at 1/4 size, then blur
    s = 4
    grow = cv2.dilate(hard, np.ones((41, 41), np.uint8))
    small = cv2.resize(a, (w // s, h // s), interpolation=cv2.INTER_AREA)
    hole = cv2.resize(grow, (w // s, h // s), interpolation=cv2.INTER_NEAREST)
    bg = cv2.inpaint(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), hole, 9, cv2.INPAINT_TELEA)
    bg = cv2.cvtColor(cv2.resize(bg, (w, h), interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB).astype(np.float32)
    if BG:  # another picture behind the person (cover-fit), e.g. a painted world around a realistic face
        b = cv2.cvtColor(cv2.imdecode(np.fromfile(BG, np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        sc = max(w / b.shape[1], h / b.shape[0])
        b = cv2.resize(b, (round(b.shape[1] * sc), round(b.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
        y0, x0 = (b.shape[0] - h) // 2, (b.shape[1] - w) // 2
        bg = b[y0:y0 + h, x0:x0 + w].astype(np.float32)
    k = int(BLUR * 3) | 1
    bg = cv2.GaussianBlur(bg, (k, k), BLUR)
    bg = bg * (1 - DARK) + np.array([8, 12, 24], np.float32) * DARK
    # person mask pulled in by 3 px, soft 2 px edge
    body = cv2.erode(hard, np.ones((7, 7), np.uint8))
    alpha = cv2.GaussianBlur(np.where(head > 0, hard, body).astype(np.float32), (0, 0), 2.0)[..., None]
    comp = a.astype(np.float32) * alpha + bg * (1 - alpha)
    o = os.path.join(out, os.path.basename(p))
    cv2.imencode(os.path.splitext(o)[1] or ".png", cv2.cvtColor(comp.clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))[1].tofile(o); print(o)

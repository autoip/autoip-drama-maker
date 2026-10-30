"""Put a character sheet's person into a set: the reference a multi-reference shot drifts into is then the set itself.

usage: python drama/restage.py PROJECT_DIR      every missing CAST[k]["by_set"] picture: CAST[k]["file"] put into that
                                                  set (keep = CAST[k]["restage_keep"], default 0)
       python drama/restage.py CAST.png SET.png OUT.png [blur] [keep]
       blur = set softness in px (default 3); keep = px of the sheet's own background kept around the person, fading
       into the set (default 0; ~70 keeps what segmentation drops: hair loops, hanging tassels, a veil)
env:   SEG_MODEL  person segmentation model (.tflite); default: MediaPipe's selfie_multiclass_256x256, downloaded once
                  to ~/.cache/dreamfab/
needs: pip install mediapipe   (0.10.x or later: the Tasks API)

Multi-reference video often dissolves into the background of a character's sheet (episode 1: 4 of 17 shots ended up in
the alley behind two sheets). The person is cut out with the face pixels untouched and laid over the set, cropped to the
sheet's size; list it in that character's `by_set` (e.g. by_set={"ROOM": "../cast/A_room.png"}) and multi-reference
shots in that set use it instead of `file`.
"""
import os, sys, urllib.request
import numpy as np
from PIL import Image, ImageFilter

URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/"
       "selfie_multiclass_256x256.tflite")


def model_path():
    p = os.environ.get("SEG_MODEL") or os.path.join(os.path.expanduser("~"), ".cache", "dreamfab", "selfie_multiclass_256x256.tflite")
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        print(f"downloading the segmentation model -> {p}")
        urllib.request.urlretrieve(URL, p)
    return p


def person_mask(rgb):
    """0..1 person coverage (hair, clothes and accessories count as person)."""
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=model_path()), output_confidence_masks=True))
    bg = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)).confidence_masks[0].numpy_view()  # class 0
    m = np.clip(1.0 - np.squeeze(bg), 0, 1)
    m = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    return np.clip((m - 0.12) / 0.8, 0, 1)  # the model leaves ~8 % of the old background everywhere


def restage(cast, set_, out, blur=3.0, keep=0):
    person = Image.open(cast).convert("RGB")
    W, H = person.size
    rgb = np.array(person)
    m = person_mask(rgb)
    if keep:  # a period headdress's hair loops and pearl tassels came out as background: keep a fading ring of the old background
        grow = Image.fromarray(((m > 0.5) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(keep / 2))
        ring = np.clip(np.array(grow).astype(np.float32) / 255 * 8, 0, 1)  # ~keep px of dilation
        ring = np.array(Image.fromarray((ring * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(keep / 2.5))) / 255
        m = np.maximum(m, ring.astype(np.float32))
    m = m[..., None]
    room = Image.open(set_).convert("RGB")
    s = max(W / room.width, H / room.height)  # cover the sheet's canvas, centred
    r = room.resize((round(room.width * s), round(room.height * s)), Image.LANCZOS)
    x0, y0 = (r.width - W) // 2, (r.height - H) // 2
    bg = np.array(r.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(blur))).astype(np.float32)
    Image.fromarray((rgb * m + bg * (1 - m)).astype(np.uint8)).save(out)
    print(f"{out}  {W}x{H}, person {float(m.mean()) * 100:.0f} % of the picture")


def restage_project(d):
    from common import load_project
    proj = load_project(d)
    sets = getattr(proj, "SETS", {})
    for k, v in proj.CAST.items():
        for sk, f in v.get("by_set", {}).items():
            out = os.path.join(proj.DIR, f)
            if os.path.exists(out):
                continue
            src, bg = os.path.join(proj.DIR, v["file"]), os.path.join(proj.DIR, sets[sk]["file"])
            if not (os.path.exists(src) and os.path.exists(bg)):
                print(f"{k} in {sk}: needs {v['file']} and {sets[sk]['file']} first")
                continue
            restage(src, bg, out, keep=v.get("restage_keep", 0))


if __name__ == "__main__":
    if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        restage_project(sys.argv[1])
        sys.exit()
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    restage(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 3.0,
            float(sys.argv[5]) if len(sys.argv) > 5 else 0)

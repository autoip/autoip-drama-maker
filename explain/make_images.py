"""Text-to-image jobs for an explainer's pictures (16:9 stills that render.py moves with pans and zooms).

usage: python explain/make_images.py PROJECT_DIR [ID ...]   jobs/images_jobs.json for the given ids, or every image
                                                            in proj.IMAGES that has no images/<id>.png yet
AutoIP text-to-image v4 is MOSS-Image. Write prompts the way its prompt enhancer does
(github.com/OpenMOSS/MOSS-Image, skills/moss-image-prompt-enhancer; docs/en/explain/OVERVIEW.md):
  * a caption: cohesive English prose - subject and action, appearance, setting, camera and framing, medium,
    lighting, palette, mood; no strings of quality tags ("8k, masterpiece"); visible words quoted exactly;
  * a Layout draft (a dict) when text or objects must sit in given places, e.g. a cover with its title: canvas
    width/height in pixels (multiples of 16, the size the job comes out at: 1312x736 for size 960x540 in v4),
    "bbox_coord_space": "abs", "bbox_format": "xyxy", a "summary" with a "caption", and flat "items" of
    {"label": object|character|text, "caption", "bbox": [x1, y1, x2, y2], "text" for text}. It is compiled here
    to the one-line JSON MOSS-Image reads (boxes centred on the canvas, y-x order).
project.py:
  IMAGES = [(id, chapter, note, prompt, look), ...]   prompt: a caption string or a Layout dict
  LOOKS  = {"S": "a paragraph on the medium and palette, appended to captions", ...}   (look None: nothing added)
  NEG    = "negative prompt"                          (v4 reads it: lettering you did not ask for, watermarks ...)
  IMAGE_FIELDS = dict(size="960x540", mode="v4")      (default)
Submit with: python dreamfab/aip_runner.py PROJECT_DIR/jobs/images_jobs.json [--off-peak]
"""
import json, math, os, sys
from common import load_project, P, jdump, estimate, off_peak

LAYOUT_KEYS = {"width", "height", "bbox_coord_space", "bbox_format", "summary", "items"}


def compile_layout(d, where):
    """A pixel Layout draft -> MOSS-Image's prompt: same content, boxes as [y1, x1, y2, x2] relative to the canvas
    centre (left/top floored, right/bottom ceiled), as compact JSON. Refuses what the model would not understand."""
    def need(ok, msg):
        if not ok:
            sys.exit(f"{where}: {msg}")
    need(set(d) == LAYOUT_KEYS, f"a Layout needs exactly {sorted(LAYOUT_KEYS)}")
    w, h = d["width"], d["height"]
    need(type(w) is int and type(h) is int and w > 0 and h > 0 and w % 16 == 0 and h % 16 == 0,
         "width and height must be positive multiples of 16")
    need(d["bbox_coord_space"] == "abs" and d["bbox_format"] == "xyxy", 'use "abs" and "xyxy" in the draft')
    need(isinstance(d["summary"], dict) and str(d["summary"].get("caption", "")).strip()
         and set(d["summary"]) <= {"caption", "meta", "canvas", "palette"}, "summary needs a caption (and only meta/canvas/palette)")
    need(isinstance(d["items"], list) and d["items"], "items must be a non-empty list")
    items = []
    for k, it in enumerate(d["items"]):
        need(set(it) <= {"label", "caption", "bbox", "text", "tags", "palette"} and {"label", "caption", "bbox"} <= set(it),
             f"items[{k}] needs label, caption, bbox (and only text/tags/palette besides)")
        need(it["label"] in ("object", "character", "text"), f"items[{k}].label must be object, character or text")
        need(it["label"] != "text" or str(it.get("text", "")).strip(), f"items[{k}] is text: give its exact words in 'text'")
        x1, y1, x2, y2 = it["bbox"]
        need(0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h, f"items[{k}].bbox is outside the {w}x{h} canvas")
        box = [math.floor(round(y1, 9)) - h // 2, math.floor(round(x1, 9)) - w // 2,
               math.ceil(round(y2, 9)) - h // 2, math.ceil(round(x2, 9)) - w // 2]
        items.append({key: box if key == "bbox" else v for key, v in it.items()})
    return json.dumps(dict(summary=d["summary"], items=items, bbox_coord_space="abs_centralized", bbox_format="yxyx"),
                      ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    proj = load_project(sys.argv[1])
    D, want = proj.DIR, set(sys.argv[2:])
    fields = dict(dict(size="960x540", mode="v4"), **getattr(proj, "IMAGE_FIELDS", {}))
    jobs = []
    for i, chapter, note, prompt, look in proj.IMAGES:
        out = P(D, "images", f"{i}.png")
        if (want and i not in want) or (not want and os.path.exists(out)):
            continue
        if isinstance(prompt, dict):
            text = compile_layout(prompt, f"IMAGES {i}")
        else:
            text = prompt.strip() + (f"\n\n{proj.LOOKS[look]}" if look else "")
        f = dict(fields, prompt=text)
        if getattr(proj, "NEG", ""):
            f["negative_prompt"] = proj.NEG
        if len(text) > 2000:
            sys.exit(f"IMAGES {i}: the prompt is {len(text)} characters (the API takes 2,000)")
        jobs.append(dict(id=i, endpoint="/images/text-to-image", fields=f, out=out))
    os.makedirs(os.path.join(D, "images"), exist_ok=True)
    jdump(jobs, os.path.join(D, "jobs", "images_jobs.json"))
    full = sum(estimate(j) for j in jobs)
    print(f"{len(jobs)} images -> jobs/images_jobs.json  ({full} credits now, {sum(off_peak(estimate(j)) for j in jobs)} off-peak)")

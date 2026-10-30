"""Group shot as an approved still first: member crops -> collage -> image-to-image candidates.

Multi-subject video often shrinks a band into short, childlike figures. Building the frame ourselves (waist-up
crops side by side) and letting image-to-image unify it keeps the members tall and recognisable; the approved
still then goes through plain image-to-video (make_jobs.py picks kf/<id>.png up automatically).

usage: python mv/group_still.py PROJECT_DIR SHOT_ID [WORK]
  -> WORK/<id>_collage.jpg + WORK/<id>_stills.json (i2i at several strengths, outputs kf_candidates/<id>_<strength>.png)
  run aip_runner.py on the json, look at the candidates, copy the chosen one to kf/<id>.png.
env GROUP_STRENGTHS="0.85,0.92"  (below ~0.8 the collage seams stay visible)
"""
import os, sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from common import P, load_project, jload, jdump

proj = load_project(sys.argv[1])
D, SID = proj.DIR, sys.argv[2]
WORK = sys.argv[3] if len(sys.argv) > 3 else os.path.join(D, "jobs")
os.makedirs(WORK, exist_ok=True)
sb = jload(os.path.join(D, "storyboard.json"))
shot = next(b for b in sb["band"] if b["id"] == SID)
members = [sb["chars"][k] for k in shot["chars"]]
W, H = 1920, 1080
STRENGTHS = os.environ.get("GROUP_STRENGTHS", "0.85,0.92").split(",")
MATURE = getattr(proj, "GROUP_PROMPT_SUFFIX",
                 "mature adults around thirty, tall slender model-like proportions, sharp jawlines, confident rock star presence, "
                 "slightly low angle, waist-up medium shot, faces large and clear")
NEG = ("text, letters, watermark, extra fingers, deformed hands, childlike, child, kid, teenager, baby face, chibi, "
       "big head, short people, full body, legs, feet, wide shot, visible seams, split screen, collage borders")


def member_crop(c, h):
    """Head-and-torso crop around the face box (or the top 60% of the image), scaled to height h."""
    im = Image.open(os.path.join(D, c["file"])).convert("RGB")
    if c.get("face"):
        fx, fy, fw = c["face"]
        w = min(im.width, int(fw * 3.6)); hh = min(im.height, int(w * 1.5))
        x0 = min(max(0, fx - w // 2), im.width - w); y0 = min(max(0, fy - int(hh * 0.22)), im.height - hh)
        im = im.crop((x0, y0, x0 + w, y0 + hh))
    else:
        im = im.crop((0, 0, im.width, int(im.height * 0.6)))
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)


# backdrop: the first member's image, blurred and darkened
bg = Image.open(os.path.join(D, members[0]["file"])).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(30))
bg = ImageEnhance.Brightness(bg).enhance(0.5)
n = len(members)
slot = W / n
for i, c in enumerate(members):
    im = member_crop(c, H)
    if im.width > slot * 1.25:  # trim the sides so neighbours overlap a little, not a lot
        k = int((im.width - slot * 1.25) / 2); im = im.crop((k, 0, im.width - k, im.height))
    mk = Image.new("L", im.size, 0)
    ImageDraw.Draw(mk).rectangle((40, 0, im.width - 40, im.height), fill=255)
    bg.paste(im, (int(slot * (i + 0.5) - im.width / 2), H - im.height), mk.filter(ImageFilter.GaussianBlur(28)))
col = os.path.join(WORK, f"{SID}_collage.jpg")
bg.save(col, quality=92)

who = "; ".join(f"from left {i + 1}: {c['desc']}" for i, c in enumerate(members))
prompt = f"group photo of {n} band members standing shoulder to shoulder, {MATURE}, {who}, {shot['prompt'] or sb['band_stage']}, {sb['style']}"
jobs = [dict(id=f"{SID}_{s}", endpoint="/images/image-to-image",
             fields=dict(prompt=prompt[:3900], negative_prompt=NEG, strength=s, size="960x540"),
             files=dict(image=P(col)), out=P(D, "kf_candidates", f"{SID}_{s}.png")) for s in STRENGTHS]
jdump(jobs, os.path.join(WORK, f"{SID}_stills.json"))
print(col, len(jobs), "jobs ->", os.path.join(WORK, f"{SID}_stills.json"))

"""Build AutoIP job files (consumed by aip_runner.py) from storyboard.json / shots.json.

usage: python mv/make_jobs.py PROJECT_DIR kf    [WORK]  -> keyframe stills: lip-sync scenes, band shots, B-roll
       python mv/make_jobs.py PROJECT_DIR video [WORK]  -> lip-sync audio cuts + lip-sync / image-to-video / multi-subject jobs
env ONLY="LS01,D1,B10" limits jobs to those ids (lip-sync takes pull in their keyframe scene).

Group band shots (more than one member): if kf/<id>.png exists (an approved still from group_still.py) the video is a
plain image-to-video from it; otherwise a multi-subject-reference job from the member images.
"""
import os, subprocess, sys
from PIL import Image, ImageFilter, ImageEnhance
from common import P, load_project, jload, jdump, audio_path

proj = load_project(sys.argv[1])
D = proj.DIR
KIND = sys.argv[2]
WORK = sys.argv[3] if len(sys.argv) > 3 else os.path.join(D, "jobs")
KF, CLIPS = os.path.join(D, "kf"), os.path.join(D, "clips")
for d in (WORK, KF, CLIPS, os.path.join(WORK, "img"), os.path.join(WORK, "aud")):
    os.makedirs(d, exist_ok=True)
sb = jload(os.path.join(D, "storyboard.json"))
shots = jload(os.path.join(D, "shots.json"))
ONLY = set(x for x in os.environ.get("ONLY", "").split(",") if x)
take = lambda i: not ONLY or i in ONLY
LS = [l for l in shots["lipsync"] if take(l["id"])]
SCENES = {l["scene"] for l in LS}
BAND = [b for b in sb["band"] if take(b["id"])]
BROLL = [b for b in sb["broll"] if take(b["id"])]
NEG = getattr(proj, "NEG", "text, letters, words, logo, watermark, subtitles, extra fingers, deformed hands")
# multi-subject video tends to shrink people into short, childlike figures in a wide shot: push hard against it
MULTI_NEG = getattr(proj, "MULTI_NEG", "dialogue, talking, short people, stubby body, chibi, big head, short legs, dwarf, "
                                       "tiny figures in the distance, full body shot, legs, feet, wide shot")
MULTI_DESC_PREFIX = getattr(proj, "MULTI_DESC_PREFIX", "tall slender adult, ")
VIDEO = getattr(proj, "VIDEO", dict(duration_seconds="5", resolution="768p", aspect_ratio="16:9"))
LS_FIELDS = getattr(proj, "LS_FIELDS", {})  # extra lip-sync fields, e.g. dict(engine="h3", resolution="768p")


def pad(key, c, whole=False):
    """Character image -> (3:4 crop around the face | whole image) -> 1920x1080 with a blurred side fill."""
    im = Image.open(os.path.join(D, c["file"])).convert("RGB")
    if not whole and c.get("face"):
        fx, fy, fw = c["face"]
        w = min(im.width, int(fw * 4.2)); h = min(im.height, w * 4 // 3)
        x0 = min(max(0, fx - w // 2), im.width - w); y0 = min(max(0, fy - h * 3 // 10), im.height - h)
        im = im.crop((x0, y0, x0 + w, y0 + h))
    fg = im.resize((int(im.width * 1080 / im.height), 1080), Image.LANCZOS)
    bg = ImageEnhance.Brightness(im.resize((1920, int(im.height * 1920 / im.width))).crop((0, 0, 1920, 1080))
                                 .filter(ImageFilter.GaussianBlur(40))).enhance(0.6)
    bg.paste(fg, ((1920 - fg.width) // 2, 0))
    out = os.path.join(WORK, "img", f"pad_{key}{'_w' if whole else ''}.jpg")
    bg.save(out, quality=92)
    return out


def kf_jobs():
    jobs = []
    for s in sb["lipsync_scenes"]:
        if ONLY and s["id"] not in SCENES:
            continue
        c = sb["chars"][s["char"]]
        jobs.append(dict(id=s["id"], endpoint="/images/image-to-image",
                         fields=dict(prompt=f"{c['desc']}, {s['scene']}, the only person in frame, front view facing the camera, "
                                            f"face large in frame, medium close-up, {sb['style']}",
                                     negative_prompt=NEG + ", second person, crowd faces", strength="0.95", size="960x540"),
                         files=dict(image=P(pad(s["char"], c))), out=P(KF, s["id"] + ".png")))
    for b in BAND:
        if len(b["chars"]) > 1:
            continue  # group shots: see group_still.py
        c = sb["chars"][b["chars"][0]]
        jobs.append(dict(id=b["id"], endpoint="/images/image-to-image",
                         fields=dict(prompt=f"{c['desc']}, {b['prompt']}, {sb['band_stage']}, {sb['style']}",
                                     negative_prompt=NEG + ", microphone in hand", strength="0.9", size="960x540"),
                         files=dict(image=P(pad(b["chars"][0], c, whole=True))), out=P(KF, b["id"] + ".png")))
    for b in BROLL:
        jobs.append(dict(id=b["id"], endpoint="/images/text-to-image",
                         fields=dict(prompt=f"{b['prompt']}, {sb['style']}, no text, no letters", size="960x540", mode="v3"),
                         out=P(KF, b["id"] + ".png")))
    return jobs


def i2v(id_, motion, extra=""):
    return dict(id=id_, endpoint="/videos/image-to-video",
                fields=dict(VIDEO, prompt=sb["motion_prefix"] + "SHOT 1: " + motion + "。" + extra),
                files=dict(first_frame=P(KF, id_ + ".png")), out=P(CLIPS, id_ + ".mp4"))


def video_jobs():
    voc = audio_path(proj, "voices")
    scene = {s["id"]: s for s in sb["lipsync_scenes"]}
    jobs = []
    for l in LS:
        a = os.path.join(WORK, "aud", l["id"] + ".mp3")
        if not os.path.exists(a):  # the mouth follows only this singer's isolated track
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(l["a0"]), "-t", str(l["dur"]), "-i", voc[l["voice"]],
                            "-ac", "2", "-b:a", "192k", a], check=True)
        img = os.path.join(KF, l["scene"] + ".png")
        if os.path.exists(img) and os.path.getsize(img) > 9_500_000:  # lip-sync takes images <= 10 MB (hd_4k stills are ~15 MB)
            small = os.path.join(WORK, "img", l["scene"] + ".jpg")
            if not os.path.exists(small):
                im = Image.open(img).convert("RGB")
                if im.width > 2560:
                    im = im.resize((2560, round(im.height * 2560 / im.width)), Image.LANCZOS)
                im.save(small, quality=95)
            img = small
        jobs.append(dict(id=l["id"], endpoint="/videos/lip-sync",
                         fields=dict(prompt=scene[l["scene"]]["motion"], aspect_ratio="16:9", **LS_FIELDS),
                         files=dict(image=P(img), audio=P(a)),
                         out=P(CLIPS, l["id"] + ".mp4")))
    for b in BAND:
        if len(b["chars"]) > 1 and not os.path.exists(os.path.join(KF, b["id"] + ".png")):
            members = [sb["chars"][k] for k in b["chars"]]
            jobs.append(dict(id=b["id"], endpoint="/videos/multi-subject-reference",
                             fields={**VIDEO, "prompt": b["multi"] or b["motion"], "negative_prompt": NEG + ", " + MULTI_NEG,
                                     "descriptions[]": [(MULTI_DESC_PREFIX + m["desc"])[:200] for m in members]},
                             files={"images[]": [P(D, m["file"]) for m in members]},
                             out=P(CLIPS, b["id"] + ".mp4")))
        else:
            jobs.append(i2v(b["id"], b["motion"]))
    for b in BROLL:
        jobs.append(i2v(b["id"], b["motion"], getattr(proj, "NO_TEXT_ZH", "畫面中不要出現任何文字。")))
    return jobs


if __name__ == "__main__":
    jobs = kf_jobs() if KIND == "kf" else video_jobs()
    p = os.path.join(WORK, f"{KIND}_jobs.json")
    jdump(jobs, p)
    print(p, len(jobs), [j["id"] for j in jobs])

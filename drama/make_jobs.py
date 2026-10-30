"""Build AutoIP job files (consumed by aip_runner.py) from project.py.

usage: python dramakit/make_jobs.py PROJECT_DIR refs   -> cast looks, set plates, props that have no file yet: from
                                                         `prompt` / `desc`, or from a `base` picture (see refs_jobs)
       python dramakit/make_jobs.py PROJECT_DIR voices -> voice clips for the cast: the character says `voice_line`
                                                         (image-to-video with sound from their picture), written to
                                                         `voice_src`; voices.py then cuts the sample from it
       python dramakit/make_jobs.py PROJECT_DIR kf     -> first-frame stills kf/<id>.png for LS / I2V / K shots
       python dramakit/make_jobs.py PROJECT_DIR video  -> M (multi-reference + dialogue + voice), LS (lip-sync),
                                                         I2V (image-to-video), K (keyframe) clips/<id>.mp4
env ONLY="S1_02,S1_05" limits jobs to those ids (shot ids, or CAST / SETS / PROPS keys for refs).
Prints the job count and a credit estimate; inputs that are missing are listed and their jobs left out.
Job files store absolute paths: name the episode folder before the first job.
"""
import os, sys
from PIL import Image, ImageFilter, ImageEnhance
from common import P, load_project, jload, jdump, canvas, estimate, off_peak, fingerprint
from storyboard import build, chars

proj = load_project(sys.argv[1])
D = proj.DIR
KIND = sys.argv[2]
WORK = os.path.join(D, "jobs")
for d in (WORK, os.path.join(D, "kf"), os.path.join(D, "clips"), os.path.join(WORK, "img")):
    os.makedirs(d, exist_ok=True)
ONLY = set(x for x in os.environ.get("ONLY", "").split(",") if x)
take = lambda i: not ONLY or i in ONLY
ASPECT = getattr(proj, "ASPECT", "9:16")
CW, CH = canvas(proj)
SIZES = dict(dict(frame="540x960" if ASPECT == "9:16" else "960x540", portrait="768x1024", square="1024x1024"),
             **getattr(proj, "SIZES", {}))
T2I = dict(dict(mode="standard"), **getattr(proj, "T2I", {}))   # v3 / v4 only where the account has them (else 422)
STYLE = proj.STYLE
NEG = getattr(proj, "NEG", "text, letters, words, logo, watermark, subtitles, extra fingers, deformed hands, nude, nsfw")
VIDEO = dict(dict(resolution="768p", aspect_ratio=ASPECT), **getattr(proj, "VIDEO", {}))
LS_FIELDS = getattr(proj, "LS_FIELDS", {})   # e.g. dict(engine="h3") for lip-sync 3.0
sb, warn = build(proj)
missing = []


def need(*paths):
    """True when every input exists; otherwise remember what is missing (the job is left out)."""
    gone = [p for p in paths if p and not os.path.exists(p)]
    missing.extend(gone)
    return not gone


def fill(im, w, h, name, bottom=True, box=None):
    """Picture -> w x h with a blurred, darkened fill around it, as the base of an image-to-image job.
    box = (x, y, width) as fractions of the canvas puts the picture there instead (a face crop where a head goes)."""
    s = box[2] * w / im.width if box else min(w / im.width, h / im.height)
    fg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    if box:  # a plain ground in the crop's edge colour: a blown-up blurred copy would put a giant ghost face behind it
        edge = [im.getpixel((x, y)) for x in range(0, im.width, max(1, im.width // 40)) for y in (0, im.height - 1)]
        bg = Image.new("RGB", (w, h), tuple(int(sum(p[i] for p in edge) / len(edge) * 0.6) for i in range(3)))
    else:
        c = max(w / im.width, h / im.height)
        bg = im.resize((round(im.width * c), round(im.height * c)))
        bg = bg.crop(((bg.width - w) // 2, (bg.height - h) // 2, (bg.width - w) // 2 + w, (bg.height - h) // 2 + h))
        bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(40))).enhance(0.6)
    xy = (round(box[0] * w), round(box[1] * h)) if box else ((w - fg.width) // 2, h - fg.height if bottom else (h - fg.height) // 2)
    bg.paste(fg, xy)
    out = os.path.join(WORK, "img", f"{name}.jpg")
    bg.save(out, quality=92)
    return P(out)


def pad(key):
    """Cast image -> the frame's aspect, standing on the bottom edge (the head keeps its place in the frame)."""
    return fill(Image.open(os.path.join(D, proj.CAST[key]["file"])).convert("RGB"), CW, CH, f"pad_{key}_{CW}x{CH}")


def t2i(id_, prompt, size, out):
    neg = dict(negative_prompt=NEG[:500]) if T2I["mode"] in ("standard", "hd_4k", "v4") else {}  # v2 / v3 ignore it
    return dict(id=id_, endpoint="/images/text-to-image", fields=dict(T2I, prompt=prompt, size=size, **neg), out=P(out))


def refs_jobs():
    """Text-to-image from `desc` / `prompt`, or, with `base`, image-to-image from a picture you have (a photo you may
    use, art, a still of an earlier project): `base_crop` = (x0, y0, x1, y1) as fractions keeps only that part (crop
    away costume and props you don't want carried over), `base_box` = (x, y, width) as fractions of the canvas places
    that part (a face crop where the head of a waist-up portrait goes; default: fitted, standing on the bottom edge),
    `base_strength` = 0.8 or a list of strengths, one candidate each in <file folder>/candidates/ (copy the one you
    pick to `file`). Whatever the base shows tends to stay (costume, props, a painted look): crop it away."""
    jobs = []
    # props do not get STYLE: "a still from a drama" makes the model stage a scene with actors around the object
    prop_style = getattr(proj, "PROP_STYLE", "studio product photograph of the object alone, nobody in the picture, photorealistic")
    groups = (("cast", proj.CAST, "portrait", "character reference portrait, waist-up, facing the camera, softly lit simple backdrop", STYLE),
              ("set", getattr(proj, "SETS", {}), "frame", "empty location with nobody in it, establishing view", STYLE),
              ("prop", getattr(proj, "PROPS", {}), "square", "a single object on a plain background", prop_style))
    for kind, table, size, how, style in groups:
        for k, v in table.items():
            if not v.get("file"):
                continue  # a character with no picture (file=None, see storyboard: `unseen`)
            out = os.path.join(D, v["file"])
            if not take(k) or os.path.exists(out) or not (v.get("prompt") or v.get("base") or kind != "cast"):
                continue  # cast without a prompt or base: you supply the picture (a photo you may use, or art)
            body = f"{v['desc']}, {v['prompt']}" if kind == "cast" and v.get("prompt") else v.get("prompt") or v["desc"]
            if not v.get("base"):
                jobs.append(t2i(k, f"{body}, {how}, {style}", SIZES[size], out))
                continue
            src = os.path.join(D, v["base"])
            if not need(src):
                continue
            im = Image.open(src).convert("RGB")
            if v.get("base_crop"):
                x0, y0, x1, y1 = v["base_crop"]
                im = im.crop((round(x0 * im.width), round(y0 * im.height), round(x1 * im.width), round(y1 * im.height)))
            w, h = (int(x) for x in SIZES[size].split("x"))
            base = fill(im, w * 2, h * 2, f"base_{k}", bottom=kind == "cast", box=v.get("base_box"))
            strengths = v.get("base_strength", 0.8)
            strengths = strengths if isinstance(strengths, (list, tuple)) else [strengths]
            stem = os.path.splitext(os.path.basename(out))[0]   # named after the target file: a second look of the
            for s in strengths:                                 # same key (A_PARTY after A_CASUAL) gets its own names
                o = out if len(strengths) == 1 else os.path.join(os.path.dirname(out), "candidates", f"{stem}_s{s:.2f}.png")
                if os.path.exists(o):
                    continue
                jobs.append(dict(id=k if len(strengths) == 1 else f"{stem}_s{s:.2f}", endpoint="/images/image-to-image",
                                 fields=dict(prompt=f"{body}, {how}, {style}", negative_prompt=NEG, strength=str(s), size="original"),
                                 files=dict(image=base), out=P(o)))
    return jobs


def voices_jobs():
    """A voice for each character that has `voice_line` and no sample yet, made by AutoIP instead of recorded:
    image-to-video with sound from the cast picture (text-to-video for a character with file=None, shown as
    `voice_who` or `unseen`), the character saying the line. The model gives the face a voice that fits it; voices.py
    takes the voice out of the clip, and every multi-reference shot clones that same voice from then on."""
    jobs = []
    vv = dict(dict(resolution="480p", aspect_ratio=ASPECT), **getattr(proj, "VOICE_VIDEO", {}))  # the sound is the same at 480p
    quiet = "單一連續鏡頭，鏡頭固定不動，背景安靜，沒有配樂、沒有音效、沒有其他人的聲音。"
    for k, c in proj.CAST.items():
        if not take(k) or not c.get("voice_line"):
            continue
        if os.path.exists(os.path.join(D, c.get("voice") or f"voices/{k}.wav")):
            continue  # the sample is already there
        if not c.get("voice_src", "").endswith(".mp4"):
            print(f"WARN {k}: voice_line needs voice_src = '.../voices/raw/{k}.mp4' (the clip is written there)")
            continue
        line, how = c["voice_line"], c.get("voice_how", "語氣自然")
        secs = c.get("voice_secs") or min(15, max(5, -(-chars(line) // 4) + 2))
        fields = dict(vv, duration_seconds=str(secs))
        out = P(D, c["voice_src"])
        if c.get("file"):
            if not need(os.path.join(D, c["file"])):
                continue
            prompt = f"{quiet}同一個人、同一張臉。\nSHOT 1: 畫面中的人物看著鏡頭，{how}地說：「{line}」嘴型清楚，說完停住。"
            jobs.append(dict(id=k, endpoint="/videos/image-to-video", fields=dict(fields, prompt=prompt),
                             files=dict(first_frame=pad(k)), out=out))
        else:
            who = c.get("voice_who") or c.get("unseen") or "畫面中背對鏡頭的人"
            prompt = f"{quiet}\nSHOT 1: {who}，只有這個人說話，{how}地說：「{line}」說完停住。"
            jobs.append(dict(id=k, endpoint="/videos/text-to-video", fields=dict(fields, prompt=prompt), out=out))
    return jobs


def kf_jobs():
    jobs = []
    for r in sb["shots"]:
        if r["kind"] not in ("LS", "I2V", "K") or not take(r["id"]) or not r["still"]:
            continue
        place = f", setting: {r['set_desc']}" if r['set_desc'] else ""
        if r["still_from"]:
            c = proj.CAST[r["still_from"]]
            talk = ", talking with the mouth open mid-sentence, face clearly visible, medium close-up" if r["kind"] == "LS" else ""
            if not need(os.path.join(D, c["file"])):
                continue
            jobs.append(dict(id=r["id"], endpoint="/images/image-to-image",
                             fields=dict(prompt=f"{c['desc']}, {r['still']}{place}{talk}, the only person in frame, {STYLE}",
                                         negative_prompt=NEG + ", second person, crowd faces", strength="0.9", size="original"),
                             files=dict(image=pad(r["still_from"])), out=r["still_file"]))
        else:
            jobs.append(t2i(r["id"], f"{r['still']}{place}, {STYLE}", SIZES["frame"], r["still_file"]))
    return jobs


def video_jobs():
    jobs = []
    clip = lambda i: P(D, "clips", i + ".mp4")
    for r in sb["shots"]:
        i = r["id"]
        if not take(i):
            continue
        if r["kind"] == "M":
            if not need(*r["images"], r["voice"]):
                continue
            fields = {**VIDEO, "prompt": r["prompt"], "duration_seconds": str(r["secs"]), "negative_prompt": NEG,
                      "descriptions[]": r["descs"]}
            files = {"images[]": r["images"]}
            if r["dialogue"]:
                fields["dialogue_text"] = r["dialogue"]
                if r["voice"]:
                    files["voice_sample"] = r["voice"]
            jobs.append(dict(id=i, endpoint="/videos/multi-subject-reference", fields=fields, files=files, out=clip(i)))
        elif r["kind"] == "LS":
            if not need(r["still_file"], r["audio"]):
                continue
            jobs.append(dict(id=i, endpoint="/videos/lip-sync", fields=dict(prompt=r["prompt"], aspect_ratio=ASPECT, **LS_FIELDS),
                             files=dict(image=r["still_file"], audio=r["audio"]), out=clip(i)))
        elif r["kind"] == "I2V":
            if not need(r["still_file"]):
                continue
            jobs.append(dict(id=i, endpoint="/videos/image-to-video", fields=dict(VIDEO, prompt=r["prompt"], duration_seconds=str(r["secs"])),
                             files=dict(first_frame=r["still_file"]), out=clip(i)))
        elif r["kind"] == "K":
            last = P(D, "kf", (r["to"] or "?") + ".png")
            if not need(r["still_file"], last):
                continue
            jobs.append(dict(id=i, endpoint="/videos/keyframe",
                             fields=dict(mode="2frame", prompt=r["prompt"], duration_seconds=str(r["secs"]),
                                         aspect_ratio=ASPECT, negative_prompt=NEG),
                             files=dict(first_frame=r["still_file"], last_frame=last), out=clip(i)))
    return jobs


if __name__ == "__main__":
    jobs = dict(refs=refs_jobs, voices=voices_jobs, kf=kf_jobs, video=video_jobs)[KIND]()
    for w in warn:
        print("WARN", w)
    for m in sorted(set(missing)):
        print("MISSING", os.path.relpath(m, D))
    p = os.path.join(WORK, f"{KIND}_jobs.json")
    jdump(jobs, p)
    sp = p + ".state"  # a job that failed for good goes again only if what it sends has changed since
    blocked = []
    if os.path.exists(sp):
        state = jload(sp)
        failed = {j["id"]: j for j in jobs if state.get(j["id"], {}).get("status") == "failed_final"}
        cleared = [i for i, j in failed.items() if state[i].get("sent") != fingerprint(j)]
        blocked = [f"{i} ({state[i].get('error') or 'failed'})" for i in failed if i not in cleared]
        for i in cleared:
            del state[i]
        if cleared:
            jdump(state, sp)
            print("changed since they failed, will be sent again:", cleared)
        if blocked:
            print("NOT sent again (unchanged since it was rejected or failed; change the prompt first):", blocked)
    todo = [j for j in jobs if not os.path.exists(j["out"]) and not any(b.startswith(j["id"] + " ") for b in blocked)]
    print(p, len(jobs), "jobs,", len(jobs) - len(todo), "already done")
    print(f"to submit: {len(todo)} jobs, about {sum(map(estimate, todo))} credits, {sum(off_peak(estimate(j)) for j in todo)} "
          f"off-peak (aip_runner.py --off-peak; estimate, GET /api/v1/pricing has live prices)")
    print(" ", [j["id"] for j in todo])

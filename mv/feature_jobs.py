"""project.I2V / KEYFRAME / MULTI -> PROJECT_DIR/jobs/feature_jobs.json (for aip_runner.py): AutoIP video features beyond
make_jobs.py's lip-sync, image-to-video and group shots, for MVs that show several features side by side.

usage: [ONLY=M02,K03] python mv/feature_jobs.py PROJECT_DIR [OUT.json]
  I2V      = ["B05", ...]                                   image-to-video 3.0: first frame kf/<id>.png, motion from BROLL
  KEYFRAME = {"K01": ("B01", "B03", "motion", 6)}           keyframe video 2frame: first / last frame kf/<id>.png; 6, 10 or 15 s
  MULTI    = {"M01": ([("R_HERO", None), ("plate_gate", "a stone fortress gate")], "prompt with @圖片 N", 10)}
             multi-subject reference 3.0: 1-6 reference images in order, each with a description (None -> REFS[key]["desc"],
             then REF_DESC[key]); a key is found as refs/<key>.png, refs/angles/<key>.png (multi-angle) or kf/<key>.png
  FEATURE_VIDEO (optional) = dict(resolution="768p", aspect_ratio="16:9") for all three
Outputs clips/<id>.mp4; the runner skips files that exist. Run the lip-sync jobs from make_jobs.py with their own runner
call, one after the other (the account's concurrency limit counts every runner):
  python dreamfab/aip_runner.py P/jobs/video_jobs.json && python dreamfab/aip_runner.py P/jobs/feature_jobs.json
Multi-reference: write the location into every SHOT. A shot that names only characters gets the plain backdrop of the
reference pictures (grey studio) instead of the scene. project.FEATURE labels the clips on screen (render_mv.py).
"""
import os, sys
from PIL import Image
from common import load_project, jdump, P

proj = load_project(sys.argv[1])
D = proj.DIR
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "jobs", "feature_jobs.json")
ONLY = set(x for x in os.environ.get("ONLY", "").split(",") if x)
take = lambda i: not ONLY or i in ONLY
V = dict(dict(resolution="768p", aspect_ratio="16:9"), **getattr(proj, "FEATURE_VIDEO", {}))
NEG = getattr(proj, "NEG", "text, letters, words, logo, watermark, subtitles, extra fingers, deformed hands")
PREFIX = getattr(proj, "MOTION_PREFIX", "")
motion = {b[0]: b[3] for b in getattr(proj, "BROLL", [])}
REFS, REF_DESC = getattr(proj, "REFS", {}), getattr(proj, "REF_DESC", {})
kf = lambda i: P(D, "kf", i + ".png")
clip = lambda i: P(D, "clips", i + ".mp4")


def ref_path(key):
    for p in (P(D, "refs", key + ".png"), P(D, "refs", "angles", key + ".png"), kf(key)):
        if os.path.exists(p):
            return p
    sys.exit(f"reference {key}: no refs/{key}.png, refs/angles/{key}.png or kf/{key}.png")


def under_10mb(p):
    """Multi-reference takes images <= 10 MB each (hd_4k stills are ~17 MB): send a JPEG copy from jobs/img/ instead."""
    if os.path.getsize(p) <= 9_500_000:
        return p
    small = P(D, "jobs", "img", os.path.splitext(os.path.basename(p))[0] + ".jpg")
    if not os.path.exists(small) or os.path.getmtime(small) < os.path.getmtime(p):
        im = Image.open(p).convert("RGB")
        if im.width > 2560:
            im = im.resize((2560, round(im.height * 2560 / im.width)), Image.LANCZOS)
        os.makedirs(os.path.dirname(small), exist_ok=True)
        im.save(small, quality=95)
    return small


def ref_desc(key, desc):
    d = desc or REFS.get(key, {}).get("desc") or REF_DESC.get(key)
    if not d:
        sys.exit(f"reference {key}: give a description in MULTI, REFS[{key!r}]['desc'] or REF_DESC")
    return d[:200]   # the endpoint reads 200 characters per description


jobs = []
for i in getattr(proj, "I2V", []):
    if take(i):
        jobs.append(dict(id=i, endpoint="/videos/image-to-video",
                         fields=dict(V, prompt=PREFIX + "SHOT 1: " + motion[i] + "。", duration_seconds="5"),
                         files=dict(first_frame=kf(i)), out=clip(i)))
for i, (a, b, m, s) in getattr(proj, "KEYFRAME", {}).items():
    if take(i):
        assert s in (6, 10, 15), f"{i}: keyframe video takes 6, 10 or 15 seconds"
        jobs.append(dict(id=i, endpoint="/videos/keyframe",
                         fields=dict(mode="2frame", prompt=PREFIX + m + "。", duration_seconds=str(s),
                                     aspect_ratio=V["aspect_ratio"], negative_prompt=NEG),
                         files=dict(first_frame=kf(a), last_frame=kf(b)), out=clip(i)))
for i, (refs, prompt, s) in getattr(proj, "MULTI", {}).items():
    if take(i):
        assert 1 <= len(refs) <= 6, f"{i}: multi-reference video takes 1-6 images"
        jobs.append(dict(id=i, endpoint="/videos/multi-subject-reference",
                         fields={**V, "prompt": prompt, "duration_seconds": str(s), "negative_prompt": NEG,
                                 "descriptions[]": [ref_desc(k, d) for k, d in refs]},
                         files={"images[]": [under_10mb(ref_path(k)) for k, _ in refs]}, out=clip(i)))
for j in jobs:
    for f in j["files"].values():
        for p in [f] if isinstance(f, str) else f:
            assert os.path.exists(p), (j["id"], p)
jdump(jobs, OUT)
print(OUT, len(jobs), [j["id"] for j in jobs])

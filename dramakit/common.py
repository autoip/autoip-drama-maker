"""Shared helpers: load a project folder, json io, ffmpeg wrappers, EDL parsing, credit estimates."""
import importlib.util, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _s in (sys.stdout, sys.stderr):  # Chinese lines and captions print intact through pipes on Windows too
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def load_project(pdir):
    """Import <pdir>/project.py as a module (the single source of truth for one episode)."""
    path = os.path.join(pdir, "project.py")
    if not os.path.exists(path):
        sys.exit(f"no project.py in {pdir}")
    spec = importlib.util.spec_from_file_location("project", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.DIR = os.path.abspath(pdir)
    return m


def P(*parts):
    """Forward-slash absolute path (ffmpeg filters and curl are happier with it on Windows)."""
    return os.path.normpath(os.path.join(*parts)).replace("\\", "/")


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jdump(obj, p, indent=1):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print(" ".join(cmd)); print(r.stderr[-2000:]); sys.exit(1)
    return r.stdout


_NVENC = None


def nvenc_ok():
    """True when this ffmpeg can encode on an NVIDIA GPU (needs a recent enough driver for the ffmpeg build)."""
    return subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.2", "-c:v", "h264_nvenc",
                           "-f", "null", "-"], capture_output=True).returncode == 0


def nvenc_on():
    """Encode on the NVIDIA GPU? Yes whenever this ffmpeg can (about 4x faster at the same quality); VENC=x264 forces the CPU."""
    global _NVENC
    if _NVENC is None:
        want = os.environ.get("VENC", "")
        _NVENC = want != "x264" and nvenc_ok()
        if want == "nvenc" and not _NVENC:
            print("  VENC=nvenc: this ffmpeg cannot encode on the GPU here, using x264")
        print(f"  video encoder: {'h264_nvenc (GPU)' if _NVENC else 'libx264 (CPU)'}")
    return _NVENC


def venc(kind="final", crf=15):
    """ffmpeg video-encoder args: h264_nvenc when the GPU can encode (nvenc_on), else x264.
    kind "final" = the upload file (16 Mbit/s cap), "inter" = intermediates that are encoded again."""
    nvenc_on()
    if _NVENC and kind == "final":
        return ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "19", "-b:v", "0", "-maxrate", "16M",
                "-bufsize", "32M", "-spatial-aq", "1", "-temporal-aq", "1", "-rc-lookahead", "32", "-bf", "3", "-b_ref_mode", "middle",
                "-pix_fmt", "yuv420p"]
    if _NVENC:  # NVENC needs -maxrate or cq is capped at the H.264 level 4.0 bitrate
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "15", "-b:v", "0", "-maxrate", "60M",
                "-bufsize", "120M", "-spatial-aq", "1", "-bf", "3", "-pix_fmt", "yuv420p"]
    if kind == "final":
        return ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", str(crf), "-pix_fmt", "yuv420p"]


def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def has_audio(p):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p],
                               capture_output=True, text=True).stdout.strip())


def canvas(proj):
    """Output size from project.ASPECT: "9:16" (default, vertical short drama) or "16:9"."""
    return (1920, 1080) if getattr(proj, "ASPECT", "9:16") == "16:9" else (1080, 1920)


def clip_path(proj, src):
    """EDL source -> video file. A bare id is clips/<id>.mp4; a path (e.g. ../s1e01/clips/S3_05 for a recap) is
    relative to the project folder."""
    if "/" in src or "\\" in src:
        p = os.path.join(proj.DIR, src)
        return p if os.path.splitext(p)[1] else p + ".mp4"
    return os.path.join(proj.DIR, "clips", src + ".mp4")


def find_media(proj, sub, name):
    """sfx/<name>.wav, music/<name>.mp3 ...: looks in the episode folder, then in the series folder above it."""
    if os.path.splitext(name)[1]:
        for base in (proj.DIR, os.path.dirname(proj.DIR)):
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
    for base in (proj.DIR, os.path.dirname(proj.DIR)):
        for ext in ("", ".wav", ".mp3", ".m4a", ".flac", ".ogg"):
            p = os.path.join(base, sub, name + ext)
            if os.path.isfile(p):
                return p
    return None


# ---------------------------------------------------------------- EDL
NUM = re.compile(r"^-?\d+(\.\d+)?$")


def parse_edl(text):
    """Drama EDL rows, one per line (or separated by '|'); '#' starts a comment.

        src [in|auto] [dur] [flag ...]      base row: picture + sound of src, laid end to end
        ^src [in] [dur] @at [flag ...]      cutaway: picture only, over the previous base row, starting `at` s after its
                                            start (at < 0: before its end); may run on into the next rows
    flags: flash, black, zoom, mute, title, end[=text], freeze=S, sfx=name, intro=KEY, label=text
    -> [dict(src, inn (None = auto), dur (None = to the end / auto), flags {}, over, at)]
    """
    rows = []
    for tok in text.replace("|", "\n").split("\n"):
        p = tok.split("#")[0].split()
        if not p:
            continue
        over = p[0].startswith("^")
        r = dict(src=p[0].lstrip("^"), inn=None if not over else 0.0, dur=None, flags={}, over=over, at=0.0)
        nums = []
        for x in p[1:]:
            if x == "auto":
                nums.append(None)
            elif NUM.match(x):
                nums.append(float(x))
            elif x.startswith("@") and NUM.match(x[1:]):
                r["at"] = float(x[1:])
            else:
                k, _, v = x.partition("=")
                r["flags"][k] = v or True
        if nums:
            r["inn"] = nums[0] if nums[0] is not None or not over else 0.0
        if len(nums) > 1:
            r["dur"] = nums[1]
        assert not over or rows, f"cutaway {p[0]} needs a base row before it"
        rows.append(r)
    return rows


def edit(proj, mode):
    """Resolve project.EDITS[mode]: '@name' on a line of its own pastes another edit's rows (e.g. a recap)."""
    e = dict(proj.EDITS[mode])
    lines = []
    for ln in e["shots"].split("\n"):
        k = ln.split("#")[0].strip()
        if k.startswith("@") and k[1:] in proj.EDITS and k[1:] != mode:
            lines.append(proj.EDITS[k[1:]]["shots"])
        else:
            lines.append(ln)
    e["rows"] = parse_edl("\n".join(lines))
    e.setdefault("size", canvas(proj))
    return e


# ---------------------------------------------------------------- credits
# GET /api/v1/pricing on 2026-10-27: an estimate to show before a batch, not an invoice (credits.py audits what was
# charged). Multi-reference video is not linear in seconds (768p: 5 s 80, 6 s 115, 10 s 265; 2k 10 s is 195).
PRICE = {
    "/images/text-to-image": dict(standard=10, hd_4k=20, anime=15, v2=15, v3=10, v4=20),
    "/images/image-to-image": dict(standard=15, hd_4k=30, v3=15),
    "/videos/multi-subject-reference": {"480p": {s: 6 * s for s in range(5, 16)},
                                        "768p": {5: 80, 6: 115, 7: 145, 8: 170, 9: 225, 10: 265},
                                        "2k": {5: 95, 6: 115, 7: 135, 8: 150, 9: 165, 10: 195}},
    "/videos/image-to-video": {"480p": 6, "768p": 15, "2k": 36},     # per second
    "/videos/text-to-video": {"480p": 6, "768p": 15, "2k": 36},      # per second
    "/videos/keyframe": 8,                                          # per second
    "/videos/lip-sync": dict(ltx2=50, h3_480p=50, h3_768p=75),
    "/videos/restore": 30,                                          # per 8 s segment
    "/voice/clone": 50,
}


def fingerprint(job):
    """Short hash of what a job sends (endpoint, fields, file paths): tells a rebuilt job from the one that failed."""
    import hashlib
    blob = json.dumps([job["endpoint"], job.get("fields", {}), job.get("files", {})], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def estimate(job):
    ep, f = job["endpoint"], job.get("fields", {})
    p, secs = PRICE.get(ep), int(f.get("duration_seconds", 5))
    if isinstance(p, int):
        return p * secs if ep == "/videos/keyframe" else p
    if ep in ("/images/text-to-image", "/images/image-to-image"):
        return p.get(f.get("mode", "standard"), p["standard"])
    if ep == "/videos/multi-subject-reference":
        return p.get(f.get("resolution", "768p"), p["768p"]).get(secs, 0)
    if ep in ("/videos/image-to-video", "/videos/text-to-video"):
        return p.get(f.get("resolution", "768p"), 15) * secs
    if ep == "/videos/lip-sync":
        return p["ltx2"] if f.get("engine", "ltx2") == "ltx2" else p["h3_" + f.get("resolution", "480p")]
    return 0


def label_font(size, cjk=False):
    """A bold UI font for labelling review sheets, whatever the OS; cjk=True prefers one with Chinese glyphs."""
    from PIL import ImageFont
    names = ("msjhbd.ttc", "msjh.ttc", "NotoSansTC-VF.ttf", "NotoSansCJK-Bold.ttc", "NotoSansCJK-Regular.ttc",
             "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc") if cjk else ()
    for f in names + ("DejaVuSans-Bold.ttf", "consolab.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default(size)

"""Helpers every Dreamfab line uses (drama, mv, explainer): load a project folder, json io, ffmpeg wrappers, the
NVIDIA encoder switch, where enhanced clip copies live, job fingerprints and credit estimates.

Each line's own common.py imports these and adds what only it needs (its EDL format, its media lookups).
"""
import importlib.util, json, os, subprocess, sys

for _s in (sys.stdout, sys.stderr):  # Chinese lines and captions print intact through pipes on Windows too
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def load_project(pdir):
    """Import <pdir>/project.py as a module (the single source of truth for one episode or one MV)."""
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


def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def has_audio(p):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p],
                               capture_output=True, text=True).stdout.strip())


# ---------------------------------------------------------------- video encoder
_NVENC = None


def nvenc_ok():
    """True when this ffmpeg can encode on an NVIDIA GPU (needs a recent enough driver for the ffmpeg build)."""
    return subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.2", "-c:v", "h264_nvenc",
                           "-f", "null", "-"], capture_output=True).returncode == 0


def nvenc_on():
    """Encode on the NVIDIA GPU? Yes whenever this ffmpeg can (about 4x faster: VMAF 99.2 vs x264 slow 99.3 on an
    RTX 5060 Ti); VENC=x264 forces the CPU."""
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


def hd_path(clip):
    """Where enhance.py keeps a clip's enhanced copy: clips/x.mp4 -> clips_hd/x.mp4, clips/_takes/x.mp4 ->
    clips_hd/_takes/x.mp4 (the renders look there too)."""
    parts = os.path.normpath(clip).split(os.sep)
    if "clips" in parts:
        i = len(parts) - 1 - parts[::-1].index("clips")
        return os.sep.join(parts[:i] + ["clips_hd"] + parts[i + 1:])
    return os.path.join(os.path.dirname(clip), "clips_hd", os.path.basename(clip))


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


# ---------------------------------------------------------------- AutoIP jobs and credits
def fingerprint(job):
    """Short hash of what a job sends (endpoint, fields, file paths): tells a rebuilt job from the one that failed."""
    import hashlib
    blob = json.dumps([job["endpoint"], job.get("fields", {}), job.get("files", {})], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


# list prices (GET /api/v1/pricing has the live ones; aip_runner.py records what each submit actually charged)
PRICE = {
    "/images/text-to-image": dict(standard=10, hd_4k=20, anime=15, v2=15, v3=10, v4=20),
    "/images/image-to-image": dict(standard=15, hd_4k=30, v3=15),
    "/images/multi-angle": {"8": 35, "17": 70},
    "/images/image-mix": 27,
    "/videos/multi-subject-reference": {"480p": {s: 6 * s for s in range(5, 16)},
                                        "768p": {5: 80, 6: 115, 7: 145, 8: 170, 9: 225, 10: 265},
                                        "2k": {5: 95, 6: 115, 7: 135, 8: 150, 9: 165, 10: 195}},
    "/videos/image-to-video": {"480p": 6, "768p": 15, "2k": 36},     # per second
    "/videos/text-to-video": {"480p": 6, "768p": 15, "2k": 36},      # per second
    "/videos/keyframe": 8,                                          # per second
    "/videos/lip-sync": dict(ltx2=50, h3_480p=50, h3_768p=75),
    "/videos/restore": 30,                                          # per 8 s segment of the source video
    "/videos/dance": 99,
    "/voice/clone": 50,
    "/voice/song": 30,
}


def off_peak(credits):
    """What a job costs when submitted through the API in the off-peak window (GET /pricing "off_peak": 03:00-09:00
    Asia/Taipei): half, rounded up, at least 1. aip_runner.py --off-peak submits only then."""
    return max(1, -(-credits // 2)) if credits else 0


def estimate(job, src_dur=None, off_peak_price=False):
    """Credits one job costs at PRICE; src_dur = the source video's seconds for /videos/restore; off_peak_price = half."""
    c = _list_price(job, src_dur)
    return off_peak(c) if off_peak_price else c


def _list_price(job, src_dur):
    ep, f = job["endpoint"], job.get("fields", {})
    p, secs = PRICE.get(ep), int(f.get("duration_seconds", 5))
    if ep == "/videos/restore":
        return p * max(1, int(-(-(src_dur or 8) // 8)))
    if isinstance(p, int):
        return p * secs if ep == "/videos/keyframe" else p
    if ep in ("/images/text-to-image", "/images/image-to-image"):
        return p.get(f.get("mode", "standard"), p["standard"])
    if ep == "/images/multi-angle":
        return p.get(str(f.get("angle_count", "8")), p["8"])
    if ep == "/videos/multi-subject-reference":
        return p.get(f.get("resolution", "768p"), p["768p"]).get(secs, 0)
    if ep in ("/videos/image-to-video", "/videos/text-to-video"):
        return p.get(f.get("resolution", "768p"), 15) * secs
    if ep == "/videos/lip-sync":
        return p["ltx2"] if f.get("engine", "ltx2") == "ltx2" else p["h3_" + f.get("resolution", "480p")]
    return 0

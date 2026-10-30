"""Local NVIDIA GPU pass over the clips, e.g. while AutoIP is still rendering the rest: Video Super Resolution (2x) and
Video Frame Generation (24 -> 60 fps) -> clips_hd/<id>.mp4, picture only. render_mv.py uses those copies when the render
settings say enhance=True (RENDER, or an edit's render=dict(...)); pixel values in RENDER["crop"] are scaled.

usage: python mvkit/enhance.py PROJECT_DIR [--fps 60] [--scale 2] [--quality ULTRA] [--watch]
env:   ONLY=B05,M02   just these clips
needs: an NVIDIA RTX GPU (frame generation: RTX 40 / 50 series), torch with CUDA, PyAV, and nvidia-vfx (the wheel comes
       from pypi.nvidia.com: pip install nvidia-vfx)
--watch   keep going while aip_runner.py downloads: stops once every job in jobs/*.json that writes into clips/ has its
          clip (or failed for good) and each clip the edits use has its copy
Every clip that project.EDITS uses is done (clips not downloaded yet are skipped). A copy is made again when its clip is
newer (a redone clip), or when --fps / --scale / --quality changed. Measured on an RTX 5060 Ti 16 GB: a 5 s 1344x768 clip
takes about 7.5 s, so a batch is done while AutoIP is still busy.
"""
import glob, json, math, os, sys, time
from fractions import Fraction
from common import load_project, jload, edit, hd_path

A = sys.argv[1:]
opt = lambda k, d: A[A.index(k) + 1] if k in A else d
FPS, SCALE, QUALITY = float(opt("--fps", 60)), int(opt("--scale", 2)), opt("--quality", "ULTRA")
D = os.path.abspath(A[0])
CLIPS = os.path.join(D, "clips")


def current(clip):
    """Its copy exists, is newer than the clip and was made with these settings."""
    hd, meta = hd_path(clip), hd_path(clip) + ".json"
    return (os.path.exists(hd) and os.path.exists(meta) and os.path.getmtime(hd) >= os.path.getmtime(clip)
            and jload(meta) == dict(fps=FPS, scale=SCALE, quality=QUALITY))


def clips_used(proj):
    srcs = {s[1] for mode in getattr(proj, "EDITS", {}) for s in edit(proj, mode)["shots"]}
    only = [s for s in os.environ.get("ONLY", "").split(",") if s]
    paths = [os.path.join(CLIPS, s + ".mp4") for s in srcs if not only or s in only]
    return sorted((p for p in paths if os.path.exists(p)), key=lambda p: (size_of(p), p))   # fewer effect reloads


def size_of(p):
    import av
    with av.open(p) as c:
        return c.streams.video[0].codec_context.width, c.streams.video[0].codec_context.height


LOADED = {}


def enhance(clip, sr, fg):
    """Decode -> super-resolve every source frame -> generate the frames between them on the output grid -> encode."""
    import av, torch
    hd = hd_path(clip)
    os.makedirs(os.path.dirname(hd), exist_ok=True)
    tmp = hd + ".part.mp4"
    src = av.open(clip)
    vs = src.streams.video[0]
    fin = float(vs.average_rate)
    w, h = vs.codec_context.width, vs.codec_context.height
    W, H = w * SCALE, h * SCALE
    n_in = vs.frames or round(float(vs.duration * vs.time_base) * fin)
    n_out = round(n_in * FPS / fin)
    if LOADED.get("size") != (w, h):   # load the effects again only when the clip size changes
        sr.output_width, sr.output_height = W, H
        sr.load()
        fg.input_width, fg.input_height = W, H
        fg.load()
        LOADED["size"] = (w, h)
    dst = av.open(tmp, mode="w")
    rate = Fraction(FPS).limit_denominator(1000)
    vo = dst.add_stream("hevc_nvenc", rate=rate)
    vo.width, vo.height, vo.pix_fmt = W, H, "yuv420p"
    vo.options = dict(preset="p6", rc="vbr", cq="16", b="0")
    for k in ("color_range", "colorspace", "color_trc", "color_primaries"):   # same colour tags as the clip
        if getattr(vs.codec_context, k, None) is not None:
            setattr(vo.codec_context, k, getattr(vs.codec_context, k))
    k_out = 0

    def emit(t):
        nonlocal k_out
        a = (t.clamp(0, 1) * 255).round().byte().permute(1, 2, 0).contiguous().cpu().numpy()
        f = av.VideoFrame.from_ndarray(a, format="rgb24").reformat(format="yuv420p")
        f.pts, f.time_base = k_out, Fraction(1) / rate
        for pkt in vo.encode(f):
            dst.mux(pkt)
        k_out += 1

    prev, j = None, -1
    for frame in src.decode(vs):
        x = torch.from_numpy(frame.to_ndarray(format="rgb24")).cuda().permute(2, 0, 1).float().div(255).contiguous()
        cur = torch.from_dlpack(sr.run(x).image).clone()   # the output points at the SDK's memory: copy it now
        j += 1
        if prev is not None:   # output frames whose time falls in [j-1, j) of the source (24 -> 60 is 2.5x, not whole)
            while k_out < n_out and k_out * fin / FPS < j - 1e-6:
                p = k_out * fin / FPS - (j - 1)
                emit(prev if p < 1e-3 else torch.from_dlpack(fg.run_at_timestep(prev, cur, p).image).clone())
        prev = cur
    while k_out < n_out:   # the tail: hold the last frame so the copy runs as long as the clip
        emit(prev)
    for pkt in vo.encode(None):
        dst.mux(pkt)
    dst.close(); src.close()
    os.replace(tmp, hd)
    json.dump(dict(fps=FPS, scale=SCALE, quality=QUALITY), open(hd + ".json", "w"))
    return n_in, k_out, W, H


def video_jobs_done():
    """Every job in jobs/*.json that writes into clips/ has its clip or failed for good."""
    for jp in glob.glob(os.path.join(D, "jobs", "*.json")):
        try:
            jobs = [j for j in jload(jp) if isinstance(j, dict) and os.path.normpath(os.path.dirname(j.get("out", ""))) == os.path.normpath(CLIPS)]
        except (ValueError, TypeError):
            continue
        st = jload(jp + ".state") if os.path.exists(jp + ".state") else {}
        if not all(os.path.exists(j["out"]) or st.get(j["id"], {}).get("status") == "failed_final" for j in jobs):
            return False
    return True


def main():
    import torch
    from nvvfx import VideoSuperRes, VideoFrameGeneration
    if not torch.cuda.is_available():
        sys.exit("no CUDA GPU")
    proj = load_project(D)
    sr = VideoSuperRes(quality=VideoSuperRes.QualityLevel[QUALITY])
    fg = VideoFrameGeneration(mode=VideoFrameGeneration.Mode.HIGH)
    fg.frame_multiplier = max(2, math.ceil(FPS / 24))
    done, t_all = 0, time.time()
    while True:
        todo = [c for c in clips_used(proj) if not current(c)]
        for c in todo:
            if time.time() - os.path.getmtime(c) < 20:   # aip_runner may still be writing it: next round
                continue
            t = time.time()
            try:
                n_in, n_out, W, H = enhance(c, sr, fg)
            except Exception as e:   # a broken or half-written download: left for the next round
                print(f"[hd] {os.path.basename(c)}: {e}", flush=True)
                if "--watch" not in A:
                    raise
                continue
            done += 1
            print(f"[hd] {os.path.basename(c)}: {n_in} -> {n_out} frames, {W}x{H} @ {FPS:g} fps, {time.time() - t:.1f}s", flush=True)
        if "--watch" not in A or (not todo and video_jobs_done()):
            break
        time.sleep(15)
    sr.close(); fg.close()
    print(f"enhance: {done} clips done in {time.time() - t_all:.0f}s")


if __name__ == "__main__":
    main()

# Local GPU super resolution + frame generation (NVIDIA)

[中文](../zh-TW/GPU_ENHANCE.md) | English

While AutoIP is still generating, the local NVIDIA GPU prepares the clips:

- **Super resolution**: 2x.
- **Frame generation**: 24 → 60 fps.

It started in [autoip-drama-maker](https://github.com/autoip/autoip-drama-maker) (`dramakit/enhance.py`), and mv-maker has it from 0.7.2 as `mvkit/enhance.py`. **It is optional and off by default**: without it, renders use the original clips as before, and a CPU-only setup needs no `nvidia-vfx`. This document covers how it works, the measured numbers, and what to watch for in MVs.

## What it uses

| Feature | Tool | Speed (measured, RTX 5060 Ti 16 GB) | Result |
|---|---|---|---|
| 2x super resolution | NVIDIA Video Super Resolution (`VideoSuperRes` in `nvidia-vfx`, quality `ULTRA`) | 6.4 ms a frame | Compression blocks and sign edges come out clean; skin gets smoother, with a little less pore and grain detail; once scaled back down to 1080 the picture is not much sharper |
| Frame generation 24 → 60 fps | NVIDIA Video Frame Generation (`VideoFrameGeneration.run_at_timestep`, mode `HIGH`) | about 13 ms per generated frame | Movement and camera pushes are clearly smoother; fast hand waving showed no extra fingers or ghosting |
| Decode, colour conversion, encode | PyAV + `hevc_nvenc` | about 4.3 s a clip (2.8 s of it is the RGB → YUV conversion on the CPU) | — |
| **One 5 s clip in total** | | **about 7.5 s** | AutoIP takes about 3 minutes per clip, so it is done within the wait |

## Installing

- **Hardware and driver**: an RTX GPU; frame generation needs the RTX 40 or 50 series. Windows driver 570.65 or later.
- **Python packages**: PyTorch with CUDA and PyAV (`pip install av`) in the environment.
- **`nvidia-vfx`**:
  - Run `pip install nvidia-vfx`. The PyPI package is a wheel stub; the real one comes from `pypi.nvidia.com`, about 436 MB on Windows, with the NVIDIA libraries it needs (NPP, NGX) included.
  - The wheel declares no dependencies, so `--no-deps` installs it into an existing environment and reuses the PyTorch already there instead of downloading another copy.
- **Licence**: NVIDIA proprietary; the models are marked on NGC as fit for commercial use. NVIDIA's sample code ([nvidia-vfx-python-samples](https://github.com/NVIDIA-Maxine/nvidia-vfx-python-samples)) is MIT.

```python
import torch
from nvvfx import VideoSuperRes, VideoFrameGeneration
sr = VideoSuperRes(quality=VideoSuperRes.QualityLevel.ULTRA)
sr.output_width, sr.output_height = 2688, 1536; sr.load()           # input (3, H, W) float32 0-1 on CUDA
fg = VideoFrameGeneration(mode=VideoFrameGeneration.Mode.HIGH)
fg.input_width, fg.input_height = 2688, 1536; fg.frame_multiplier = 3; fg.load()
mid = torch.from_dlpack(fg.run_at_timestep(prev, cur, 0.4).image).clone()   # the output points at SDK memory: clone it now
```

## How autoip-drama-maker does it

1. **Clips → `clips_hd/`**:
   - `enhance.py P` super-resolves each clip 2x and generates frames up to 60 fps into `clips_hd/<id>.mp4`. Only the picture is stored; the sound still comes from the original clip.
   - Old versions of reshot clips kept in `clips/_takes/` are done too, into `clips_hd/_takes/`.
2. **Exactly 2x**:
   - The pixel values of `crop=` and `delogo=` in `RENDER["crop"]` are doubled at render time; expressions such as `iw*0.8` are left alone.
   - The copy is not scaled to an arbitrary size, because those pixel values only convert exactly at a whole multiple.
3. **Frames by time position, not by multiplier**:
   - Output frame k sits at source frame `k × 24 / 60`. When that falls between two frames, `run_at_timestep(previous, next, fraction)` generates it. 24 → 60 is 2.5x, so a whole-number multiplier won't do.
   - The last frames hold the final picture, so the copy runs exactly as long as the clip.
   - Cuts inside a clip are handled: `automatic_shot_change_detection_enabled` is on by default.
4. **When it redoes a copy**: `clips_hd/<id>.mp4.json` records the settings used (fps, scale, quality). A copy is made again when its clip is newer (a reshoot) or the settings changed.
5. **`--watch`**: runs next to the runner. Each round it skips files changed in the last 20 s (the runner may still be writing them) and retries unreadable ones on the next round. It stops by itself once every job has its clip and every clip has its copy.
6. **Render**:
   - `fps=60, enhance=True` in `RENDER` takes the picture from `clips_hd/`; a clip without a copy is used as it is, with a warning.
   - An edit can carry its own `render=dict(...)` over `RENDER`, e.g. a 60 fps version of the same edit to compare.
7. **What is already published stays**: episodes uploaded at 25 fps are not uploaded again. For a compilation that should be 60 fps throughout, each episode gets a second `_hd60` render, and the compilation sets `episode_suffix="_hd60"`.

## Using it in mv-maker (optional)

```bash
python mvkit/enhance.py P               # clips used by project.EDITS -> clips_hd/<id>.mp4; --watch runs next to the runner
python mvkit/render_mv.py P full_hd60   # a comparison cut from the enhanced copies
```

In `project.py`, add comparison edits that reuse the same edit list and only change the render settings:

```python
HD60 = dict(fps=60, enhance=True)
EDITS["full_hd60"] = dict(EDITS["full"], suffix="_hd60", render=HD60)
EDITS["shorts_hd60"] = dict(EDITS["shorts"], suffix="_1min_shorts_hd60", render=HD60)
```

- **`enhance.py`** works like drama-maker's: 2x super resolution, frames generated by time position, and the last frames holding the final picture.
  - **When it redoes a copy**: the settings are kept in `clips_hd/<id>.mp4.json`; a copy is made again when its clip is newer (redone) or the settings changed.
  - **`--watch`**: stops once every job in `jobs/*.json` that writes into `clips/` has its clip and every copy is done.
  - **Model loading**: the effects reload only when the clip size changes (keyframe clips are 1280×704, the rest 1344×768), so clips are sorted by size first.
  - `ONLY=B05,M02` does just those.
- **`render_mv.py`**: an edit's `render=dict(...)` overrides `RENDER`.
  - With `enhance=True`, each row reads the clip's `clips_hd/` copy when it is newer than the clip; a clip without one is used as it is, with a warning.
  - The `crop=` / `delogo=` pixel values in `crop` filters are scaled to the copy.
  - Lip-sync rows are aligned in seconds through `align.json`, so they are unaffected.
  - Beats are converted from seconds to frames, so 60 fps only makes the snapping finer; the beats stay where they are.
- **`gpu_check.py`** prints an `hd` line: whether it can run and what is missing.

### Measured on one MV

A gold-leaf gongbi-style MV, 70 clips, RTX 5060 Ti 16 GB:

| Item | Result |
|---|---|
| Super resolution + frame generation, 70 clips | 16 minutes, 1.1 GB. A 5 s clip took 11 s on average, slower than the drama's 7.5 s; 8–10 s clips 14–29 s; the first clip, with model loading, about 20 s |
| 60 fps render | the 1-minute portrait cut 40 s, the 3-minute full cut 2 minutes |
| Portrait cut | clearly cleaner: compression blocks gone, lashes, lip lines, wrinkles and embroidery lines sharper; skin smoother |
| Landscape cut | almost no visible difference once scaled back down to 1080 |
| Frame generation | stepping through fight and sabre shots showed no extra fingers or ghosting, only the motion blur already in the clips |
| Decision-maker's call | "too sharp, it loses the artistry" → the finished MV stays at 25 fps from the original clips; enhancement stays an option |

In an MV with a painterly look aiming for a cinematic feel, the extra sharpness and the 60 fps smoothness can wash out the painting. Make a side-by-side on one song and let the decision-maker see it first; don't turn it on by default.

### What to watch for

- **Portrait cuts gain the most**: a portrait cut (`size=(1080, 1920)` + `focus`) from a landscape clip scales its height 2.5x (768 → 1920), so super resolution makes a much clearer difference there. Compare a portrait cut first.
- **Grade**: the MV `grade` adds `noise=alls=4:allf=t` (film grain) by default. Super resolution smooths skin, and that grain puts some texture back, but not the painterly feel.
- **Dance and lip-sync shots**: fast movement shows frame-generation flaws first (hands, hair, skirts). Step through a few of these clips frame by frame before switching.
- **Disk space**: the copies are 2x HEVC, about 1 GB per MV. `clips_hd/` stays out of git like `clips/`.
- **Don't redo published MVs**: YouTube can't replace a video file; a new version means a new upload, which loses the views and comments.

## Making it faster

- **Colour conversion on the GPU**: RGB → YUV runs on the CPU now and takes 2.8 s. On the GPU, a clip would drop from about 7.5 s to an estimated 4 s, and half as much data would come back from the GPU.
- **Frame generation in `MEDIUM` mode**: faster; the quality needs its own comparison.

## References

- [nvidia-vfx Python API](https://docs.nvidia.com/maxine/vfx-python/latest/api.html)
- [NVIDIA Video Frame Generation](https://docs.nvidia.com/maxine/vfx/latest/Filters/VideoFrameGeneration.html)
- [NGC: Video Super Resolution](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/collections/nvvfxvideosuperres)
- mv-maker: `mvkit/enhance.py`, `picture()` and `at_scale()` in `render_mv.py`, `common.hd_path()`
- autoip-drama-maker: [`dramakit/enhance.py`](https://github.com/autoip/autoip-drama-maker/blob/main/dramakit/enhance.py), `picture()` and `at_scale()` in `render_ep.py`, `common.hd_path()`

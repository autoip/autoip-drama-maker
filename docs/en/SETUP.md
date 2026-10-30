# Setup

[中文](../zh-TW/SETUP.md) | English

Every line of Dreamfab 造夢廠 (short drama `drama/`, MV `mv/` …) shares one setup: one repo, one Python environment, one set of AutoIP and YouTube settings. What a single line needs on top (fonts, model files) is in the [drama setup notes](drama/SETUP.md) and the [MV setup notes](mv/SETUP.md).

## 0. One-line install (Claude Code / Codex)

**macOS / Linux / Git Bash:**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/dreamfab/main/install.sh | bash
```

**Windows PowerShell:**

```powershell
irm https://raw.githubusercontent.com/autoip/dreamfab/main/install.ps1 | iex
```

The installer:
1. Clones the repo into `~/.dreamfab` (or updates it).
2. Creates `~/.dreamfab/.venv` and installs the Python packages.
3. Downloads the MediaPipe face model when the MV line is included.
4. Installs the skills into Claude Code (`~/.claude/skills/`) and Codex (`~/.codex/skills/`). An existing skill of the same name is backed up as `<name>.bak` first.

ffmpeg, fonts and the API key are not installed for you: see sections 1 and 4 below and each line's setup notes.

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `DREAMFAB_HOME` | `~/.dreamfab` | Install location |
| `DREAMFAB_LINES` | `drama,mv,explain` | Which lines' Python packages to install. The MV line needs PyTorch (vocal separation), MediaPipe and OpenCV, which are large; the explain line adds OpenCV and pypinyin; set `drama` for short dramas only |
| `DREAMFAB_AGENTS` | `claude,codex` | Where to install the skills; `none` installs none |
| `DREAMFAB_SKIP_DEPS` | — | `1` skips the Python packages |

E.g. `curl -fsSL .../install.sh | DREAMFAB_LINES=drama bash`; in PowerShell run `$env:DREAMFAB_LINES='drama'` first.

**Or install as a plugin** (skills only; on first use the skill runs the installer above to set up the tools):

```bash
claude plugin marketplace add autoip/dreamfab && claude plugin install dreamfab@dreamfab
codex plugin marketplace add autoip/dreamfab && codex plugin add dreamfab@dreamfab
```

**Then**, in Claude Code or Codex, just say one sentence:

> Use dreamfab-drama to turn script.md into a short drama
>
> Use dreamfab-mv to turn song.mp3 into a music video

The agent follows that line's WORKFLOW.md and shows you a review sheet with the credit estimate before every batch of jobs.

The rest of this page is the manual install.

## 1. System tools

- **Python 3.10+** (tested on 3.13)
- **ffmpeg / ffprobe** with libass: `ffmpeg -filters | grep subtitles` must print something. The drama line also uses `sidechaincompress`, `loudnorm`, `silencedetect`, `scdet` and `zoompan`, which any full build has.
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: your distribution's package.
- **curl**: `dreamfab/aip_runner.py` uploads multipart forms with it.
- **git**: for the one-line install.

## 2. Python packages

```bash
python -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt       # the shared core + the drama line
pip install -r requirements-mv.txt    # + the MV line (includes the line above)
```

For MVs on a CPU-only machine, the CPU build of PyTorch is enough: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`.

## 3. Optional: an NVIDIA GPU

Everything runs without a GPU. To see what the GPU on this machine can take over:

```bash
python dreamfab/gpu_check.py
```

| Step | How to switch it on | Measured (RTX 5060 Ti 16 GB vs a 16-thread CPU) |
|---|---|---|
| Video encoding (every line's render, `mv/matte_video.py`) | Automatic whenever ffmpeg can use NVENC; `VENC=x264` forces the CPU | 6.6 s vs 26.2 s per 60 s of output, VMAF 99.2 vs 99.3; a drama episode renders in 16 s instead of 31 |
| Speech recognition (`drama/speech.py`, `mv/audio/asr_words.py`) | Drama: automatic when CTranslate2 sees CUDA; MV: `ASR_DEVICE=cuda`. Both need cuBLAS 12 and cuDNN 9 (below) | 60 s of vocals in 1.0 s vs 10.9 s; 15 drama clips in 10 s instead of 48 |
| Vocal separation, Demucs (MV) | Install a CUDA build of PyTorch; demucs uses the GPU by itself | A 3-minute song in 21 s vs 32 s (model load included) |
| 2x super resolution + 60 fps frame generation | Optional, see [GPU_ENHANCE.md](GPU_ENHANCE.md) | About 7.5 s per 5 s clip |
| Faces, person mattes, lip-sync QC (MediaPipe) | — | The pip build on Windows has no GPU: CPU only |

faster-whisper (CTranslate2) on Windows needs the cuBLAS 12 and cuDNN 9 DLLs; pip is the easiest way:

```bash
pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"
```

A CUDA build of PyTorch: `cu130` for a driver with CUDA 13 or later, `cu128` for older ones (`gpu_check.py` prints the full command):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu130
```

- NVENC: ffmpeg 9 needs a driver of version 610 or later. GTX 10-series drivers stop at the 580 series, so it can't be used there; `gpu_check.py` says so.
- If the GPU fails to load, the tools fall back to the CPU; each one prints which it uses.

## 4. AutoIP API key

- Create an API key in the AutoIP dashboard (Starter plan or above).
- Keep it only in the `AUTOIP_API_KEY` environment variable, **never in a project file or in git**.
- `AUTOIP_BASE_URL` points the tools at a different API address.

```bash
export AUTOIP_API_KEY=aip_xxx           # PowerShell: $env:AUTOIP_API_KEY = "aip_xxx"
```

A normal account runs one task at a time, so `dreamfab/aip_runner.py` defaults to `AIP_MAX=1`. Keep one at a time in the daytime, even when `/me` reports `max_concurrent_tasks: null` (no limit). Accounts with a higher limit raise it off-peak only: add `AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1` and the runner drops back to 1 at that time (tasks already running finish).

**Off-peak is half price**: generation tasks submitted with an API key between 03:00 and 09:00 Taiwan time (weekends too) cost half (rounded up, at least 1 credit); the submit time counts (`GET /api/v1/pricing` → `off_peak` has the window and `active_now`). With `--off-peak` (or `AIP_OFF_PEAK=1`, `AIP_OFFPEAK=1`) the runner submits only in that window:

```bash
python dreamfab/aip_runner.py P/jobs/video_jobs.json --off-peak
```

- Start it in the evening (the computer must not sleep): it waits until 03:00 and stops submitting 2 minutes before 09:00 (`AIP_OFF_PEAK_MARGIN=120` seconds, in case this clock runs behind the server's).
- Running tasks are still polled and downloaded; what is left goes out the next morning, as long as the runner keeps running.
- Discounted tasks are marked `(off-peak)` in the log, the `.state` records what was actually charged, and the library counts that.
- Each line's `make_jobs.py` and `storyboard.py` print both estimates; outside the window without `--off-peak`, the runner prints a one-line hint.
- With a higher task limit, raise both: `AIP_MAX=N ... --off-peak`. No new task goes out after 09:00 anyway, so `AIP_MAX_UNTIL` is not needed.

## 5. YouTube upload (optional)

Both lines' uploaders (`drama/youtube_upload.py`, `mv/youtube_upload.py`) and the playlist tool (`dreamfab/youtube_playlists.py`) share one login:

- In Google Cloud Console create an OAuth client of type "Desktop app", download its JSON to `~/.config/dreamfab/youtube_client_secret.json` (or point `YT_CLIENT_SECRET` at it). One kept in `~/.config/autoip-mv-maker/` from before the merge is still read.
- The first run opens a browser to log in; the login is cached next to it as `youtube_token.json`. Keep both outside the repo.
- When one Google account owns several channels, pick the right one at login; with `YT_CHANNEL_ID` or an upload plan's `channel` set, the tools act on that channel only.
- Details: [drama publishing](drama/PUBLISHING.md) and [MV publishing](mv/PUBLISHING.md).

## 6. Rights to your material

- **Character art**: photos or art you may use, or images generated by AutoIP. No real public figure's face.
- **Voice samples**: your own voice, actors who agreed, or synthetic voices whose licence allows it. Never clone someone else's voice.
- **Songs, music, sound effects**: your own, generated by AutoIP, or from a licensed library.
- **Fonts**: a licence that allows redistribution (e.g. SIL OFL), and never committed to the repo.

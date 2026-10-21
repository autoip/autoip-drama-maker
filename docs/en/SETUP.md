# Setup

[中文](../zh-TW/SETUP.md) | English

## 0. One-line install (Claude Code / Codex)

**macOS / Linux / Git Bash:**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.sh | bash
```

**Windows PowerShell:**

```powershell
irm https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.ps1 | iex
```

The installer:
1. Clones the repo into `~/.autoip-mv-maker`, or updates it if it is already there.
2. Creates `~/.autoip-mv-maker/.venv` and installs the Python packages.
3. Downloads the MediaPipe face model.
4. Installs the skills into Claude Code (`~/.claude/skills/`) and Codex (`~/.codex/skills/`). An existing skill with the same name is first backed up as `<name>.bak`.

ffmpeg, fonts and the API key are not installed for you. See sections 1, 4 and 5 below.

Environment variables you can set:

| Variable | Default | Description |
|---|---|---|
| `AUTOIP_MV_HOME` | `~/.autoip-mv-maker` | Install location |
| `AUTOIP_MV_AGENTS` | `claude,codex` | Which agents get the skills. `none` installs no skills |
| `AUTOIP_MV_SKIP_DEPS` | — | Set to `1` to skip the Python packages (PyTorch is large) |

Examples:
- bash: `curl -fsSL .../install.sh | AUTOIP_MV_AGENTS=codex bash`
- PowerShell: run `$env:AUTOIP_MV_AGENTS='codex'` first, then the installer.

**Installing as a plugin instead.** This installs only the skills. The first time you use the skill, it runs the installer above to set up the toolkit.

```bash
claude plugin marketplace add autoip/autoip-mv-maker && claude plugin install autoip-mv-maker@autoip-mv-maker
codex plugin marketplace add autoip/autoip-mv-maker && codex plugin add autoip-mv-maker@autoip-mv-maker
```

**Once installed**, just tell Claude Code or Codex:

> Use autoip-mv-maker to turn song.mp3 into a music video

The agent follows the steps in [WORKFLOW.md](WORKFLOW.md). Before each batch of video jobs, it shows you the stills and the credit estimate.

The rest of this page covers manual installation.

## 1. System tools

- **Python 3.10+** (tested on 3.13)
- **ffmpeg / ffprobe**, a build with libass. `ffmpeg -filters | grep subtitles` must print something.
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: your distribution's package is fine.
- **curl**: `aip_runner.py` uses it for multipart uploads.
- **git**: needed for the one-line install.

## 2. Python packages

```bash
python -m venv venv
venv/Scripts/activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

- Vocal separation uses Demucs, which needs PyTorch.
- On CPU-only machines, install the CPU build first: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`.
- Separating a song of just over 2 minutes takes a few minutes on CPU.

**Optional: speech recognition on an NVIDIA GPU.** Run `asr_words.py` with `ASR_DEVICE=cuda`. On Windows faster-whisper (ctranslate2) needs the cuBLAS 12 and cuDNN 9 DLLs; installing them with pip is easiest, and `asr_words.py` finds them:

```bash
pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"
```

Measured on a GTX 1060: 32 s of vocals in 5.0 s, versus 11.6 s on a 16-thread CPU. Other steps gain little from the GPU:
- Decoding video: in this pipeline the CPU decodes faster than the GPU (60 s of 1080p: CPU 1.9 s, cuda 2.7 s).
- NVENC encoding: ffmpeg 9 needs driver 610 or newer, and GTX 10-series drivers stop at the 580 branch, so it won't open there; newer cards can use it.
- Per-frame matting of lip-sync clips (`matte_video.py`) uses MediaPipe, which runs on CPU only on Windows.

## 3. Model files

**MediaPipe face model**: used by `faces.py` and `qc/mouth.py`.

```bash
curl -L -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

You can also set the location with the environment variable `FACE_MODEL=/path/to/face_landmarker.task`.

**Demucs (htdemucs) and faster-whisper (medium)** are downloaded to your user cache automatically on first run.

## 4. Fonts

Fonts are not shipped with the project. Download them yourself and put them in each project's `fonts/`.

| Use | Recommended | License |
|---|---|---|
| Chinese titles / lyrics | Noto Serif TC, Black weight | SIL OFL |
| Latin text (ACT titles, name plates, readings) | Noto Serif (Regular / Bold / Italic) | SIL OFL |

**libass only renders the default weight of a variable font.** For a bold serif, extract a static weight first and give it a new family name:

```bash
python mvkit/make_static_font.py NotoSerifTC-VF.ttf 900 "PS Serif Black" projects/my_song/fonts/PSSerifBlack.ttf
```

Then set `TYPO = dict(font="PS Serif Black", font_file="fonts/PSSerifBlack.ttf", ...)` in `project.py`.

- `font_scale` converts PIL sizes to libass sizes. For Noto Serif TC it is about 1.45.
- After changing fonts, check the size with `qc/subprev.py`.

## 5. AutoIP API key

- Create an API key in the AutoIP dashboard. You need a Starter plan or higher.
- Keep it only in the `AUTOIP_API_KEY` environment variable. **Never write it into project files or commit it to git.**
- To use a different API host, set `AUTOIP_BASE_URL`.

```bash
export AUTOIP_API_KEY=aip_xxx           # PowerShell: $env:AUTOIP_API_KEY = "aip_xxx"
```

Regular accounts can run only one job at a time, so `aip_runner.py` defaults to `AIP_MAX=1`. If your account allows more, raise it.

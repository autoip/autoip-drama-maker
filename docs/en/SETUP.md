# Setup

[中文](../zh-TW/SETUP.md) | English

## 0. One-line install (Claude Code / Codex)

**macOS / Linux / Git Bash:**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.sh | bash
```

**Windows PowerShell:**

```powershell
irm https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.ps1 | iex
```

The installer:
1. Clones the repo into `~/.autoip-drama-maker`, or updates it if it is already there.
2. Creates `~/.autoip-drama-maker/.venv` and installs the Python packages.
3. Installs the skill into Claude Code (`~/.claude/skills/`) and Codex (`~/.codex/skills/`). An existing skill with the same name is first backed up as `<name>.bak`.

ffmpeg, fonts and the API key are not installed for you. See sections 1, 3 and 4 below.

Environment variables you can set:

| Variable | Default | Description |
|---|---|---|
| `AUTOIP_DRAMA_HOME` | `~/.autoip-drama-maker` | Install location |
| `AUTOIP_DRAMA_AGENTS` | `claude,codex` | Which agents get the skill. `none` installs no skill |
| `AUTOIP_DRAMA_SKIP_DEPS` | — | Set to `1` to skip the Python packages |

**Installing as a plugin instead.** This installs only the skill. The first time you use the skill, it runs the installer above to set up the toolkit.

```bash
claude plugin marketplace add autoip/autoip-drama-maker && claude plugin install autoip-drama-maker@autoip-drama-maker
codex plugin marketplace add autoip/autoip-drama-maker && codex plugin add autoip-drama-maker@autoip-drama-maker
```

**Once installed**, just tell Claude Code or Codex:

> Use autoip-drama-maker to turn script.md into a short drama

## 1. System tools

- **Python 3.10+** (tested on 3.13)
- **ffmpeg / ffprobe**, a build with libass. `ffmpeg -filters | grep subtitles` must print something. The pipeline also uses `sidechaincompress`, `loudnorm`, `silencedetect`, `scdet` and `zoompan`; any ordinary full build has them.
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

- `faster-whisper` is used by `speech.py`: per-character timings for the dialogue, and checking that each line was spoken in full. The first run downloads the `medium` model to your user cache. Without it, `speech.py` falls back to silence detection and finds only where each line starts and ends.
- **Optional: NVIDIA GPU.** Used automatically when present: speech recognition (`speech.py`) runs on the GPU whenever CTranslate2 sees CUDA (on Windows, first `pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"`; if the GPU fails to load it falls back to the CPU), and renders (`render_ep.py`) encode on the GPU whenever ffmpeg can use NVENC. Both print whether they use the GPU or the CPU. To force the CPU: `ASR_DEVICE=cpu`, `VENC=x264`. Measured on an RTX 5060 Ti: recognising 15 clips 48 → 10 s, rendering a 54 s episode 31 → 16 s (subtitle, scaling and similar filters still run on the CPU).

## 3. Fonts

Fonts are not shipped with the project. Download them yourself and put them in the episode's or the series' `fonts/` (the renderer looks in the episode folder first, then one level up).

| Use | Recommended | License |
|---|---|---|
| Dialogue, character intro cards, title card | Noto Sans TC, Black or Bold weight | SIL OFL |

**libass only renders the default weight of a variable font.** For bold, extract a static weight first and give it a new family name:

```bash
python dramakit/make_static_font.py NotoSansTC-VF.ttf 900 "DK Sans Black" projects/<series>/fonts/DKSansBlack.ttf
```

Then set `TYPO = dict(font="DK Sans Black", ...)` in `project.py`. Covers (`thumbkit.py`) use the same font file.

## 4. AutoIP API key

- Create an API key in the AutoIP dashboard. You need a Starter plan or higher.
- Keep it only in the `AUTOIP_API_KEY` environment variable. **Never write it into project files or commit it to git.**
- To use a different API host, set `AUTOIP_BASE_URL`.

```bash
export AUTOIP_API_KEY=aip_xxx           # PowerShell: $env:AUTOIP_API_KEY = "aip_xxx"
```

Regular accounts can run only one job at a time, so `aip_runner.py` defaults to `AIP_MAX=1`. In the daytime keep it at one, even when `/me` reports `max_concurrent_tasks: null` (no limit). If your account allows more, raise it off-peak only: add `AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1` and the runner drops back to 1 at that time by itself (tasks already running finish normally).

**Off-peak half price**: generation jobs submitted with an API key between 03:00 and 09:00 Taiwan time (every day) cost half, judged by when they are *submitted* (`GET /api/v1/pricing` → `off_peak` has the window and `active_now`). Add `--off-peak` to the runner (or set `AIP_OFF_PEAK=1`) and it submits only then:

```bash
python dramakit/aip_runner.py P/jobs/video_jobs.json --off-peak
```

- Start it in the evening (don't let the computer sleep): it waits for 03:00 and stops submitting new jobs 2 minutes before 09:00 (`AIP_OFF_PEAK_MARGIN=120` seconds, in case your clock runs behind the server's).
- Jobs already running are still polled and downloaded; anything not yet submitted waits for the next night, and a runner left open picks it up by itself.
- Jobs the API confirms with `off_peak_discount: true` are marked `(off-peak)` in the log, and the `.state` file records what was actually charged, which the library then shows.
- `make_jobs.py` and `storyboard.py` print both the full and the off-peak estimate.
- If your account allows more concurrent jobs, raise it at the same time: `AIP_MAX=N ... --off-peak`. No new jobs go out after 09:00 anyway, so `AIP_MAX_UNTIL` isn't needed.

## 5. Rights to your material

- **Character images**: photos or art you have the rights to use, or generated by AutoIP. Don't use the faces of real public figures.
- **Voice samples**: your own voice, actors who have agreed, or synthetic voices whose license allows it. Don't clone someone else's voice.
- **Music and sound effects**: from a licensed library, or made by you.

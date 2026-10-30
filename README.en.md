# Dreamfab 造夢廠

**An automated AI media workstation: say one sentence and you are the director and producer of the film you dream of.**

[中文](README.md) | English

Dreamfab makes pictures, voices and lip-sync with the public [AutoIP](https://autoip.ai) API, and edits, subtitles, mixes and renders everything locally with ffmpeg + libass. Each kind of media is a production line, and every line shares one core: submitting jobs, credits, half-price off-peak runs, local GPU super resolution and frame generation, the library, YouTube publishing.

## Lines: 戲・曲・說・影・聞

| Line | Tell the agent | Status | Docs |
|---|---|---|---|
| **戲** short drama `drama/` | Use dreamfab-drama to turn script.md into a short drama | Ready | [Drama overview](docs/en/drama/OVERVIEW.md) |
| **曲** music video `mv/` | Use dreamfab-mv to turn song.mp3 into a music video | Ready | [MV overview](docs/en/mv/OVERVIEW.md) |
| **說** explainer videos | Static or moving B-roll, few credits, made for reach | Planned | — |
| **影**, **聞** film, news | — | Later | — |

**Before every batch of jobs the agent shows you a review sheet and the credit estimate**; nothing goes out until you say so.

## Showcase

**Short drama 《我的室友是楊貴妃》** (My Roommate Is Yang Guifei), made with the drama line: Yang Guifei falls from Mawei into the flat of a talent agent three million in debt. Season one, 10 episodes of about 50 seconds, is all out. <!-- public-ok -->

- ▶ Episode 1: https://youtu.be/kA4J9kLOVVo <!-- public-ok -->
- ▶ The whole season: https://www.youtube.com/playlist?list=PLFDknh7mplug
- 🎵 The same character's MV 《馬嵬》: https://youtu.be/C6aGMU8mKdw (made with the MV line; the drama and the MV link to each other in their descriptions) <!-- public-ok -->

**Music videos**: one MV line, four genres and looks. Click a thumbnail to watch on YouTube.

| **Dark metal epic** | **Wong Kar-wai-style Cantopop ballad** | **Chinese-style duet** | **Cyberpunk female rap** |
|:---:|:---:|:---:|:---:|
| [![《黑日聖殿》](https://img.youtube.com/vi/ErQCd04OGA8/mqdefault.jpg)](https://youtu.be/ErQCd04OGA8) | [![《過期的那一分鐘》](https://img.youtube.com/vi/fMTLkI7qDq8/mqdefault.jpg)](https://youtu.be/fMTLkI7qDq8) | [![《洛川》](https://img.youtube.com/vi/OlIQYvfwZhA/mqdefault.jpg)](https://youtu.be/OlIQYvfwZhA) | [![《科技睪丸》](https://img.youtube.com/vi/fZ9SlclC9ng/mqdefault.jpg)](https://youtu.be/fZ9SlclC9ng) |

A whole season of MVs: the [《國風淒美對唱》 playlist](https://www.youtube.com/playlist?list=PLfoBI7oPycHg), 6 episodes with one look and packaging, a different genre each.

## One-line install (Claude Code / Codex)

**macOS / Linux / Git Bash:**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/dreamfab/main/install.sh | bash
```

**Windows PowerShell:**

```powershell
irm https://raw.githubusercontent.com/autoip/dreamfab/main/install.ps1 | iex
```

The tools go into `~/.dreamfab` (with a Python virtual environment) and the skills into both Claude Code and Codex. For short dramas only, set `DREAMFAB_LINES=drama` and skip the MV line's large packages. Or install as a plugin:

```bash
claude plugin marketplace add autoip/dreamfab && claude plugin install dreamfab@dreamfab
codex plugin marketplace add autoip/dreamfab && codex plugin add dreamfab@dreamfab
```

ffmpeg (with libass), fonts and `AUTOIP_API_KEY` are up to you: see [SETUP.md](docs/en/SETUP.md).

## A virtual troupe and parallel universes

- **Parallel universes**: each series is a world of its own in `projects/<series>/`, one folder and one `project.py` per episode or song.
- **A virtual troupe**: `projects/<series>/cast/` and `voices/` are that world's actors and voices, cast again across episodes and seasons with the same face and voice.
- **The library**: one web page for every episode, shot, character, credit and upload of every world:

```bash
python dreamfab/library.py serve projects     # http://127.0.0.1:8765
```

## The shared core `dreamfab/`

| File | What it does |
|---|---|
| `aip_runner.py` | Submits AutoIP jobs, polls, downloads; resumable, one at a time, `--off-peak` submits only in the half-price window |
| `util.py` | Project loading, ffmpeg, the NVIDIA encoder (used whenever available), credit estimates |
| `enhance.py` | The engine for local NVIDIA 2x super resolution + 60 fps frame generation (each line's `enhance.py` calls it): [GPU_ENHANCE.md](docs/en/GPU_ENHANCE.md) |
| `library.py` | The library page for every series |
| `youtube_api.py`, `youtube_playlists.py` | YouTube login (with a channel lock), playlist tidying |
| `credits.py` | Audit: what each job folder actually cost |
| `check_public.py` | The de-identification check before you send: keys, personal data, the words of your own work |
| `gpu_check.py`, `make_static_font.py` | What this machine's GPU can take over; static font weights for libass |

## Docs

| Doc | Contents |
|---|---|
| [SETUP.md](docs/en/SETUP.md) | Install, GPU, API key, off-peak pricing, YouTube login, rights to your material |
| [Drama overview](docs/en/drama/OVERVIEW.md) | The drama line: workflow, format, editing, publishing, lessons |
| [MV overview](docs/en/mv/OVERVIEW.md) | The MV line: workflow, format, emotional beat editing, publishing, lessons |
| [GPU_ENHANCE.md](docs/en/GPU_ENHANCE.md) | Local super resolution + frame generation: tools, measured speed and results |
| [CONTRIBUTING.en.md](CONTRIBUTING.en.md) | Contributing: what belongs in the repo, de-identification, the check before you send |

## Coming from autoip-drama-maker / autoip-mv-maker

Dreamfab is those two repos merged, with both histories kept. The old GitHub addresses redirect here.

| Before | Now |
|---|---|
| `dramakit/<x>.py` | `drama/<x>.py` |
| `mvkit/<x>.py` | `mv/<x>.py` |
| `dramakit/aip_runner.py`, `mvkit/aip_runner.py`, and `credits.py`, `check_public.py`, `gpu_check.py`, `make_static_font.py`, `youtube_playlists.py` | `dreamfab/<x>.py` |
| `~/.autoip-drama-maker`, `~/.autoip-mv-maker` | `~/.dreamfab` |
| `AUTOIP_DRAMA_*`, `AUTOIP_MV_*` | `DREAMFAB_*` |
| skills `autoip-drama-maker`, `autoip-mv-maker` | `dreamfab-drama`, `dreamfab-mv` |
| `~/.config/autoip-mv-maker/` (YouTube credentials) | `~/.config/dreamfab/` (the old place is still read) |

The `project.py` format is unchanged: existing projects work as they are.

## Licence

[MIT](LICENSE). What you make with Dreamfab is yours; use only material you have the rights to (see the last section of [SETUP.md](docs/en/SETUP.md)).

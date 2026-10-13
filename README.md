# autoip-mv-maker: an AI music-video pipeline

[中文](README.zh-TW.md) | English

A semi-automatic pipeline that turns a song into a finished music video. It outputs a full version and a 1-minute short:

- lip-synced singers, a band with a fixed line-up, story B-roll
- an edit cut to the song's emotional beats
- kinetic typography subtitles with rhyme readings and per-keyword effects
- promo cards, thumbnails and publishing copy

Image and video generation uses the [AutoIP](https://autoip.app) public API: text-to-image, image-to-image, image-to-video, lip-sync and multi-subject reference video. Editing, subtitles and rendering all run locally with ffmpeg + libass.

## Example

[![【科技睪丸】賽博龐克女聲 Rap MV｜駭進父權系統・Cyberpunk Hitpop Rap](https://img.youtube.com/vi/fZ9SlclC9ng/maxresdefault.jpg)](https://youtu.be/fZ9SlclC9ng)

*Made with this pipeline — click to watch on YouTube.*

## One-line install (Claude Code / Codex)

**macOS / Linux / Git Bash:**

```bash
curl -fsSL https://raw.githubusercontent.com/jsleetw/autoip-mv-maker/main/install.sh | bash
```

**Windows PowerShell:**

```powershell
irm https://raw.githubusercontent.com/jsleetw/autoip-mv-maker/main/install.ps1 | iex
```

The installer puts the toolkit in `~/.autoip-mv-maker`, including a Python venv and the face model. It installs the skills into both Claude Code and Codex.

Or install as a plugin:

```bash
claude plugin marketplace add jsleetw/autoip-mv-maker && claude plugin install autoip-mv-maker@autoip-mv-maker
codex plugin marketplace add jsleetw/autoip-mv-maker && codex plugin add autoip-mv-maker@autoip-mv-maker
```

You still need to provide three things yourself:
- **ffmpeg**, a build with libass
- **fonts**
- **an AutoIP API key**, in the `AUTOIP_API_KEY` environment variable. Never write it into a file.

See [docs/en/SETUP.md](docs/en/SETUP.md).

Once installed, tell Claude Code or Codex:

> Use autoip-mv-maker to turn song.mp3 into a music video

The agent works through the pipeline step by step. Before each batch of video jobs, it shows you the stills and the credit estimate.

## Features

- **One `project.py` is one MV.** It holds the cast, storyboard, lip-sync segments, lyric timings, edit lists, subtitle theme and effect keywords. Every other file is generated from it.
- **Look before you spend credits.** Every video job starts from a still keyframe. The stills go on a review sheet for a human to approve before anything is submitted.
- **Split-track duet lip-sync.** The vocals are separated, then split into two tracks by section (e.g. scream vs. soprano), so each singer's mouth moves only on their own lines.
- **Group shots that don't shrink people into kids.** Collage first, then image-to-image to an approved still, then image-to-video (`group_still.py`).
- **Emotional beat editing.** An energy map with breath and drop points guides the edit list, and cuts snap to the beat.
- **"Epic theatre" subtitle engine** (`epic.py`):
  - each voice part enters differently (slide in, or slam in with shake), and old lines burn to ash
  - act titles, musician name plates, title cards
  - romanized readings under rhyme words
  - keyword effects: coins, tears, a glass clink, CLAP, a spinning wheel, explosions, scurrying and floating words
- **QC tools.** Lip-sync alignment, mouth-movement checks (MediaPipe jawOpen), review sheets, subtitle-only fast previews, credit audits.

## Manual use

```bash
git clone https://github.com/jsleetw/autoip-mv-maker && cd autoip-mv-maker
python -m venv venv && venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
export AUTOIP_API_KEY=aip_xxx                       # from your AutoIP dashboard; never write it into a file
cp -r examples/demo projects/my_song                # projects/ is git-ignored
# add song.mp3, chars/*.png, fonts/, then edit projects/my_song/project.py
```

Then follow [docs/en/WORKFLOW.md](docs/en/WORKFLOW.md). It covers 10 steps from song analysis to publishing, each with commands and a review gate.

## Docs

| Doc | Contents |
|---|---|
| [SETUP.md](docs/en/SETUP.md) | Install: one-liner, Python packages, ffmpeg, models, fonts |
| [WORKFLOW.md](docs/en/WORKFLOW.md) | The full pipeline: audio → storyboard → generation → QC → edit → subtitles → render → thumbnails → publish |
| [PROJECT_FORMAT.md](docs/en/PROJECT_FORMAT.md) | Every `project.py` field |
| [LESSONS.md](docs/en/LESSONS.md) | Pitfalls and fixes: generation quirks, libass, ASR, cost |
| [EMOTIONAL_BEAT_EDITING.md](docs/en/EMOTIONAL_BEAT_EDITING.md) | Emotional beat editing |
| [PUBLISHING.md](docs/en/PUBLISHING.md) | Thumbnails, YouTube SEO, social post templates |

Chinese versions are in [docs/zh-TW/](docs/zh-TW/).

## Skills

| Skill | Purpose |
|---|---|
| `autoip-mv-maker` | The main workflow. It locates the toolkit, checks the environment, and walks the agent through the 10 steps while keeping the review gates |
| `emotional-beat-editing` | Applied when planning the edit list |

Both skills live in `skills/` and work in Claude Code and Codex. The one-line installer and the plugin install both include them.

## Layout

```
mvkit/
  common.py            project loading, EDL parsing, ffmpeg helpers
  storyboard.py        project.py -> storyboard.json + shots.json
  faces.py             character face boxes (MediaPipe)
  make_jobs.py         AutoIP job files (keyframes / video)
  group_still.py       group shots: collage -> image-to-image candidates
  aip_runner.py        submit, poll, download (resumable, one at a time by default)
  credits.py           credits spent per job folder
  render_mv.py         EDL -> segments -> subtitles -> promo cards -> final mp4 + srt
  epic.py              "epic theatre" kinetic subtitle engine (ASS)
  thumbkit.py          YouTube thumbnail toolkit
  make_static_font.py  variable font -> static weight (for libass)
  audio/               analyze / voice_probe / split_voices / asr_words / emotion_map
  qc/                  align / mouth / sheets / subprev
skills/                Claude Code / Codex skills
examples/demo/         fictional demo project (project.py, thumbs.py)
docs/en/, docs/zh-TW/  docs (English / Chinese)
install.sh, install.ps1                    one-line installers
.claude-plugin/, .codex-plugin/            plugin and marketplace manifests
```

## Notes

- Generation spends AutoIP credits. They are charged on submit, and there is no cancel API. Always review the stills before submitting video jobs.
- This repo ships no songs, character art, fonts or generated media. Use material you have the rights to, and follow each platform's AI-content disclosure rules.
- The demo project's lyrics and characters are fictional.

## License

[MIT](LICENSE)

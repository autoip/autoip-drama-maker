# autoip-mv-maker: an AI music-video pipeline

[中文](README.md) | English

A semi-automatic pipeline that turns a song into a finished music video. It outputs a full version, a 1-minute short and vertical Shorts:

- lip-synced singers, a band with a fixed line-up, story B-roll
- an edit cut to the song's emotional beats
- kinetic typography subtitles with rhyme readings and per-keyword effects
- promo cards, thumbnails and publishing copy

Image and video generation uses the [AutoIP](https://autoip.ai) public API: text-to-image, image-to-image, image-to-video, lip-sync and multi-subject reference video. Editing, subtitles and rendering all run locally with ffmpeg + libass.

## Make an MV with one sentence

Once installed (see below), tell Claude Code or Codex:

```text
Use autoip-mv-maker to turn song.mp3 into a music video
```

The agent works through the pipeline step by step. **Before each batch of video jobs, it shows you the stills and the credit estimate**, and only submits after you agree.

For a whole series:

```text
Use autoip-mv-maker to plan a 6-episode MV series about <subject>
```

The agent first asks about the subject, the axis and the anchors you want fixed, writes the season plan and a series style bible for your approval, then makes the episodes one by one. The framework gives the formula; the subject and style are yours. See [SERIES_PLANNING.md](docs/en/SERIES_PLANNING.md), and a [finished season](https://www.youtube.com/playlist?list=PLfoBI7oPycHg).

## Examples

One pipeline, four genres and visual styles. Click a thumbnail to watch on YouTube.

| **Dark metal epic** | **Wong Kar-wai ballad** | **Chinese guofeng duet** | **Cyberpunk hitpop rap** |
|:---:|:---:|:---:|:---:|
| [![Black Sun Temple](https://img.youtube.com/vi/ErQCd04OGA8/mqdefault.jpg)](https://youtu.be/ErQCd04OGA8) | [![The Expired Minute](https://img.youtube.com/vi/fMTLkI7qDq8/mqdefault.jpg)](https://youtu.be/fMTLkI7qDq8) | [![Luo River](https://img.youtube.com/vi/OlIQYvfwZhA/mqdefault.jpg)](https://youtu.be/OlIQYvfwZhA) | [![Tech Balls](https://img.youtube.com/vi/fZ9SlclC9ng/mqdefault.jpg)](https://youtu.be/fZ9SlclC9ng) |
| *Shadow Island, Island of Flames*<br>Death growls × ethereal soprano; typhoons, temples, a black sun | *The Expired Minute*<br>Step-printed blur, neon green and amber, rainy nights | *Luo River*<br>Cao Zhi × the river goddess; blue-green shanshui, gold leaf, scroll transitions | *Tech Balls*<br>A neon cyber-girl crew hacks the patriarchy OS; lyrics explode on the beat |

**A whole season as an example**: [the 《國風淒美對唱》 playlist](https://www.youtube.com/playlist?list=PLfoBI7oPycHg), 6 episodes with one look and one package, a different genre each episode.

## One-line install (Claude Code / Codex)

**macOS / Linux / Git Bash:**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.sh | bash
```

**Windows PowerShell:**

```powershell
irm https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.ps1 | iex
```

The installer puts the toolkit in `~/.autoip-mv-maker`, including a Python venv and the face model. It installs the skills into both Claude Code and Codex.

Or install as a plugin:

```bash
claude plugin marketplace add autoip/autoip-mv-maker && claude plugin install autoip-mv-maker@autoip-mv-maker
codex plugin marketplace add autoip/autoip-mv-maker && codex plugin add autoip-mv-maker@autoip-mv-maker
```

You still need to provide three things yourself:
- **ffmpeg**, a build with libass
- **fonts**
- **an AutoIP API key**, in the `AUTOIP_API_KEY` environment variable. Never write it into a file.

See [docs/en/SETUP.md](docs/en/SETUP.md).

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
- **Library page.** Every episode, shot (stills, clips, old takes and candidates), character, lyric, edit list, render, job with its credits and YouTube upload of a series in one SQLite file, browsed, played and searched on a local page (see "Library page" below).

## Manual use

```bash
git clone https://github.com/autoip/autoip-mv-maker && cd autoip-mv-maker
python -m venv venv && venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
export AUTOIP_API_KEY=aip_xxx                       # from your AutoIP dashboard; never write it into a file
cp -r examples/demo projects/my_song                # projects/ is git-ignored
# add song.mp3, chars/*.png, fonts/, then edit projects/my_song/project.py
```

Then follow [docs/en/WORKFLOW.md](docs/en/WORKFLOW.md). It covers 10 steps from song analysis to publishing, each with commands and a review gate.

## Library page

Once you have a series, its material is spread over every episode's `project.py`, `kf/`, `clips/`, `jobs/`, `out/` and `thumbnails/`. The library indexes all of it into one SQLite file and serves a local page to browse it:

```bash
python mvkit/library.py serve projects/my_series      # rebuild the index, open http://127.0.0.1:8770
python mvkit/library.py index projects/my_series      # only rebuild projects/my_series/library.db
python mvkit/library.py serve projects/my_series --no-index --port 8800   # keep the index, another port
```

| Page | What it shows |
|---|---|
| Overview | One section per season: each episode's cover, genre, full / short / Shorts lengths, shot count, lip-sync share, estimated credits and YouTube links; totals for clips, full-MV length, credits and disk use |
| Episode | The full MV, short cut, Shorts and song; links to the lyrics, notes, SEO copy and `project.py`; characters and reference images; every shot with its caption, the lyrics it covers, its still (first and last frame for keyframe video), its clip, which cuts use it and how often, and how many old versions it has; lyric timings; each cut's edit list (reused clips in red); thumbnails and review sheets |
| Shot | One shot's clip, still or every multi-reference image, prompts, the edit rows that use it, the jobs that made it, and every old take and candidate |
| Characters | Each episode's `CHARS` sheets and `REFS` images, with descriptions |
| Files | By kind (clips, old takes, candidates, keyframes, characters, thumbnails, renders, subtitles, review sheets, job files…) with size, length, dimensions and date |
| Jobs and credits | Every AutoIP job per episode, its status, estimated credits (and how much of it was video) and prompt |
| YouTube | Title, upload time, video and Studio links for each cut; finished episodes with no upload record |
| Search | Lyrics, shot captions and prompts, characters, titles, genres, file names |

- Standard library plus ffprobe / ffmpeg only; nothing extra to install.
- Every sub-folder with a `project.py` or named `s<season>e<episode>_<title>` is an episode (one without a `project.py` shows as planning); folders starting with `_` are skipped. Pointing it at a single project folder works too.
- Covers: the newest `thumbnails/thumb_*.jpg`, else a frame of the full MV.
- While `serve` runs it checks the series folder every 15 s and re-indexes in the background when files are added or changed; reload the page to see them. No need to re-run it by hand.
- Media lengths and posters are cached in `library.db` and `.library/`, so a rebuild takes seconds (the first one probes every video). Both are in `.gitignore`.
- It listens on `127.0.0.1` only and serves files from inside the series folder only; OAuth secrets and tokens are never indexed or served. Videos support seeking (Range). If the port is taken it moves to the next one.
- Credits are what the submit charged, kept in `.state` (so off-peak half price counts right); older `.state` files without it fall back to an estimate from the job file (`common.estimate`): failed tasks are refunded and not counted, a job run again counts only its last run, and a job with no `.state` whose output exists counts once. Audit real spend with `credits.py`.
- You can also query `library.db` with any SQLite tool (`episodes`, `shots`, `versions`, `lyrics`, `edit_rows`, `chars`, `files`, `jobs`, `youtube`).

## Docs

| Doc | Contents |
|---|---|
| [SETUP.md](docs/en/SETUP.md) | Install: one-liner, Python packages, ffmpeg, models, fonts |
| [WORKFLOW.md](docs/en/WORKFLOW.md) | The full pipeline: audio → storyboard → generation → QC → edit → subtitles → render → thumbnails → publish → library |
| [PROJECT_FORMAT.md](docs/en/PROJECT_FORMAT.md) | Every `project.py` field |
| [LESSONS.md](docs/en/LESSONS.md) | Pitfalls and fixes: generation quirks, libass, ASR, cost |
| [RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md) | Release notes |
| [EMOTIONAL_BEAT_EDITING.md](docs/en/EMOTIONAL_BEAT_EDITING.md) | Emotional beat editing |
| [PUBLISHING.md](docs/en/PUBLISHING.md) | Thumbnails, YouTube SEO, automatic YouTube upload, social post templates |
| [SERIES_PLANNING.md](docs/en/SERIES_PLANNING.md) | Planning a series: pitch, axis, fixed anchors, song structure, package, folder naming, per-episode steps |
| [CONTRIBUTING.md](docs/en/CONTRIBUTING.md) | Contributing code and docs: conventions, pull requests, bug reports and the de-identification check before you send |

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
  feature_jobs.py      multi-reference, keyframe and image-to-video job files (MVs that show several features)
  group_still.py       group shots: collage -> image-to-image candidates
  bokeh_still.py       blur a lip-sync still's background (person untouched, no halo); BG= swaps in a painted plate
  matte_video.py       re-composite a lip-sync clip onto a still painted plate, frame by frame; KEEP= saves head ornaments
  aip_runner.py        submit, poll, download (resumable, one at a time by default; AIP_OFFPEAK=1 submits only at off-peak half price)
  credits.py           credits spent per job folder
  render_mv.py         EDL -> segments -> subtitles -> promo cards -> final mp4 + srt
  epic.py              "epic theatre" kinetic subtitle engine (ASS)
  thumbkit.py          YouTube thumbnail toolkit
  youtube_upload.py    upload the video, thumbnail and subtitles with the copy in YouTube_SEO.txt (YouTube Data API, private by default)
  youtube_playlists.py tidy playlists (sort, add / remove, rename and describe, delete empty ones), fix text in many descriptions
  library.py           index of a whole series (SQLite library.db) + a local page to browse it
  make_static_font.py  variable font -> static weight (for libass)
  audio/               analyze / voice_probe / split_voices / asr_words / emotion_map
  qc/                  align / mouth / zoom (lip-sync push-in) / sheets / subprev / focus (portrait crop centres)
skills/                Claude Code / Codex skills
examples/demo/         fictional demo project (project.py, thumbs.py)
examples/series_template/  blank series template (research.md, style.md, episode skeleton)
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

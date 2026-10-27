# autoip-drama-maker: an AI short-drama pipeline

[中文](README.md) | English

A semi-automatic pipeline that turns a script into a vertical short drama, 1–2 minutes per episode:

- fixed character looks and voices: each character speaks their lines in their own voice sample, and the mouth is generated with them
- an edit driven by the dialogue: shot/reverse shot, reaction shots, L/J cuts, a push-in with a sound effect on the payoff (爽點), a freeze-frame cliffhanger (卡點) with 「未完待續」 ("To be continued")
- dialogue subtitles, character intro cards, a title card; music ducked under the dialogue automatically
- vertical covers, titles, descriptions; a planning framework for the whole series

Image, video and voice generation uses the [AutoIP](https://autoip.ai) public API: multi-subject reference video (character, set and prop reference images + the line + a voice sample), lip-sync, image-to-video, keyframe video, text-to-image and image-to-image. Editing, subtitles, mixing and rendering all run locally with ffmpeg + libass.

The architecture follows [autoip-mv-maker](https://github.com/autoip/autoip-mv-maker): one `project.py` per episode, a review sheet before every batch of jobs, a resumable runner.

## Make an episode with one sentence

Once installed (see below), tell Claude Code or Codex:

```text
Use autoip-drama-maker to turn script.md into a short drama
```

The agent works through the pipeline step by step. **Before each batch of jobs, it shows you the review sheet and the credit estimate**, and only submits after you agree.

For a whole series:

```text
Use autoip-drama-maker to plan a 30-episode short drama: <premise>
```

The agent first asks about the subject, the payoff engine, the arcs and the anchors you want fixed, writes the series plan (`plan.md`), the character profiles (`characters.md`) and the style bible (`style.md`) for your approval, then makes the episodes one by one. The framework gives the formula; the story and style are yours. See [SERIES_PLANNING.md](docs/en/SERIES_PLANNING.md).

## One-line install (Claude Code / Codex)

**macOS / Linux / Git Bash:**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.sh | bash
```

**Windows PowerShell:**

```powershell
irm https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.ps1 | iex
```

The installer puts the toolkit in `~/.autoip-drama-maker`, including a Python venv. It installs the skill into both Claude Code and Codex.

Or install as a plugin:

```bash
claude plugin marketplace add autoip/autoip-drama-maker && claude plugin install autoip-drama-maker@autoip-drama-maker
codex plugin marketplace add autoip/autoip-drama-maker && codex plugin add autoip-drama-maker@autoip-drama-maker
```

You still need to provide these yourself:
- **ffmpeg**, a build with libass
- **fonts**
- **an AutoIP API key**, in the `AUTOIP_API_KEY` environment variable. Never write it into a file.
- **voice samples**: 5–15 s per character, of a voice you have the rights to use.

See [docs/en/SETUP.md](docs/en/SETUP.md).

## Features

- **One `project.py` is one episode.** It holds the characters, sets, props, scenes, shots, lines, edit lists, music and subtitle theme. Every other file is generated from it.
- **Look before you spend credits.** Character sheets, sets and first frames come out as stills for review first; video jobs get a job review sheet first (each job's references, line, prompt and credits); each character gets one test shot, and the batch is sent only after you've heard the voice.
- **One speaker per shot.** A multi-reference video carries the speaker's voice sample, so the line and the mouth are generated together; dialogue is cut shot/reverse shot.
- **Prompts are put together for you.** References are combined automatically (speaker, `@KEY`, props, set), `@KEY` becomes `@圖片 N`, every SHOT names the location (so it doesn't fall into a grey studio), gender words that would override the voice's timbre are taken out of the descriptions when there is a voice sample, and a warning appears when a line goes over 4 characters per second.
- **Dialogue QC.** Speech recognition checks that every line is finished and is the line in the script; broken files, cuts inside clips, and whether there is sound are listed in one go.
- **An edit driven by the dialogue.** One row per shot in the edit list, and `auto` trims the silence before and after the line; cutaway rows change only the picture, not the sound, so a reaction shot or an L/J cut takes one line; `zoom`, `sfx=hit`, `flash`, `freeze`, `end`; clips from other episodes work directly as a recap.
- **Mixing.** Each shot uses its own dialogue and sound effects, the music ducks under the dialogue automatically, −16 LUFS overall.
- **Subtitles and cards.** Lines are split at punctuation and timed to per-character timings; character intro cards, title card, top-left label, cliffhanger text.

## Manual use

```bash
git clone https://github.com/autoip/autoip-drama-maker && cd autoip-drama-maker
python -m venv venv && venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
export AUTOIP_API_KEY=aip_xxx                       # from your AutoIP dashboard; never write it into a file
mkdir -p projects/my_drama && cp -r examples/demo projects/my_drama/s1e01_pilot   # projects/ is git-ignored
# add character images or prompts, voice samples, music, sound effects, fonts/, then edit project.py
```

Then follow [docs/en/WORKFLOW.md](docs/en/WORKFLOW.md). It covers 12 steps from script to publishing, each with commands and a review gate.

## Docs

| Doc | Contents |
|---|---|
| [SETUP.md](docs/en/SETUP.md) | Install: one-liner, Python packages, ffmpeg, fonts, API key, rights to your material |
| [WORKFLOW.md](docs/en/WORKFLOW.md) | The full pipeline: script → character sheets → voices → storyboard → first frames → test shots → video → QC → edit → subtitles and sound → render → publish |
| [PROJECT_FORMAT.md](docs/en/PROJECT_FORMAT.md) | Every `project.py` field, and how to write the edit list |
| [EDITING.md](docs/en/EDITING.md) | Short-drama editing principles: hook, shot/reverse shot, reaction shots, pacing, payoff, cliffhanger |
| [SERIES_PLANNING.md](docs/en/SERIES_PLANNING.md) | Planning a whole series: pitch, payoff engine, episode structure, arcs and big reveals, characters and voices, package |
| [PUBLISHING.md](docs/en/PUBLISHING.md) | Covers, titles, descriptions, the series playlist, platform specs |
| [LESSONS.md](docs/en/LESSONS.md) | Pitfalls and fixes (carried over from the MV project), and what is not yet tested in drama |
| [RELEASE_NOTES.md](docs/en/RELEASE_NOTES.md) | Release notes |

Chinese versions are in [docs/zh-TW/](docs/zh-TW/).

## Layout

```
dramakit/
  common.py            project loading, EDL parsing, ffmpeg helpers, credit estimates
  storyboard.py        project.py -> what each shot sends to AutoIP (references, prompt, line, voice) + warnings
  make_jobs.py         AutoIP job files: refs (character sheets, sets, props) / kf (first frames) / video (M, LS, I2V, K)
  aip_runner.py        submit, poll, download (resumable, one at a time by default)
  credits.py           credits actually spent per job folder
  voices.py            recordings -> voice samples
  speech.py            where each line sits in its clip, and whether it is finished (faster-whisper)
  timeline.py          edit list -> where each row sits in the episode (shared by render, preview and rough cut)
  edl_draft.py         rough cut in script order, trimmed to before and after each line
  render_ep.py         edit list -> picture -> dialogue + music ducking + sound effects -> subtitles -> final mp4 + srt
  subs.py              dialogue subtitles, character intro cards, title card, labels, cliffhanger text (ASS)
  thumbkit.py          vertical cover toolkit
  endcard.py           text end card (lines + a button over the last frame, blurred and darkened)
  compile.py           compilation: episodes (end cards cut) + bridge cards + other videos -> one mp4, merged subtitles, YouTube chapters
  youtube_upload.py    scheduled YouTube uploads from an upload plan, the playlist, links between episodes
  library.py           the whole series indexed (SQLite library.db) + a local page to browse it
  make_static_font.py  variable font -> static weight (for libass)
  qc/                  sheets (review sheets, job review sheets) / clips (broken files, cuts) / subprev (subtitle preview)
skills/                Claude Code / Codex skill
examples/demo/         de-identified demo episode: structure only, no story (project.py, covers.py)
examples/series_template/  blank series template (plan.md, style.md, characters.md, episode skeleton)
docs/en/, docs/zh-TW/  docs (English / Chinese)
install.sh, install.ps1                    one-line installers
.claude-plugin/, .codex-plugin/            plugin and marketplace manifests
```

## Notes

- Generation spends AutoIP credits. They are charged on submit, and there is no cancel API. Always look at the review sheet and shoot test shots before submitting video jobs.
- This repo ships no character art, voices, music, fonts or generated media. Use material you have the rights to (voice samples above all), don't use the faces or voices of real public figures, and follow each platform's AI-content disclosure rules.
- The examples in this repo hold structure only, no story; your scripts, characters and material all go in `projects/` (kept out of git).

## License

[MIT](LICENSE)

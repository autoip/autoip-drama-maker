---
name: dreamfab-explain
description: >
  Make a 3-6 minute landscape YouTube explainer (history and legend behind an MV or a topic) with Dreamfab's explain
  line (`explain/`): script, one cloned narrator voice, AutoIP text-to-image v4 (MOSS-Image) paintings with pans and
  zooms, the MV's instrumental as the music bed, subtitles timed to the voice, MV clip, cover and YouTube upload.
  Low credits (stills only). Use when the user wants an explainer / 解說影片 / 歷史解說 / MV 背後的故事 / 靜態 B-roll
  解說, or mentions dreamfab-explain, 造夢廠 解說, 說.
---

# Dreamfab · explain (說・解說影片)

One folder and one `project.py` per episode; the scripts read it. You write the script and the prompts, run the
scripts, and show the user every result before money is spent on the next step.

## 0. Locate the toolkit

1. `ROOT` = `$DREAMFAB_HOME`, else `~/.dreamfab`. If this skill's base directory is `<repo>/skills/dreamfab-explain`
   and `<repo>/explain/render.py` exists, you may use `<repo>` instead.
2. If `ROOT/explain` is missing, install (skills are already installed, so pass `DREAMFAB_AGENTS=none`):
   - macOS / Linux / Git Bash:
     `curl -fsSL https://raw.githubusercontent.com/autoip/dreamfab/main/install.sh | DREAMFAB_AGENTS=none bash`
   - Windows PowerShell:
     `$env:DREAMFAB_AGENTS='none'; irm https://raw.githubusercontent.com/autoip/dreamfab/main/install.ps1 | iex`
3. `PY` = `ROOT/.venv/bin/python` (Windows: `ROOT/.venv/Scripts/python.exe`). Commands: `PY ROOT/explain/<script>.py`,
   `PY ROOT/dreamfab/aip_runner.py`, `PY ROOT/mv/youtube_upload.py`.
4. `ffmpeg -filters` must list `subtitles` (libass). `AUTOIP_API_KEY` must be set by the user; never read keys from
   elsewhere, write them into files or echo them.

## Hard rules

- **Credits are charged on submit and there is no cancel.** Before every batch, give the job count and the price now
  and off-peak (03:00-09:00 Taiwan time, half; `aip_runner.py --off-peak`), and wait for a yes. Jobs one at a time.
- Show the script before any job; a 30-second test cut (`render.py --until`) before the whole episode when the look
  is new; a review sheet of every picture before rendering (models add things that do not belong, e.g. a modern map).
- **Prompts for text-to-image v4 are MOSS-Image prompts** (its prompt enhancer:
  https://github.com/OpenMOSS/MOSS-Image/blob/main/skills/moss-image-prompt-enhancer/SKILL.md): a caption is cohesive
  English prose (subject and action, appearance, setting, framing, medium, light, palette, mood), no strings of quality
  tags, visible words quoted exactly; use a Layout dict in `IMAGES` when text or figures must sit in given places
  (`make_images.py` compiles it). If that skill is installed, you may draft with it.
- The voice-clone API has no accent setting: the accent comes from the sample. Make the narrator's sample with
  text-to-video (the person says one line in the wanted accent and manner), never ask the user to record.
- Misread words go in `SAY` as same-length, same-sounding substitutes; subtitles keep the original.
- Uploads are **private** (the uploader's default). Never make a video public or schedule it unless the user asks.
- Projects live in the user's `projects/`, never in `ROOT`; keep media, fonts and keys out of git.

## Workflow

Details: `ROOT/docs/en/explain/OVERVIEW.md` (中文：`ROOT/docs/zh-TW/explain/OVERVIEW.md`). Example with every field:
`ROOT/examples/explain/demo/`.

1. **Script**: `script.md` with `## 旁白` (or `## Narration`) and one `### chapter` each; about 1,400 Chinese
   characters for 5 minutes; legends named as legends; sources for the description. User approves.
2. **Voice** (once per series): text-to-video of a narrator saying one line → extract 5-15 s → `VOICE`.
3. **Narration**: `explain/narration.py P jobs` → `aip_runner.py P/jobs/voice_jobs.json` → `narration.py P check`.
   Act on its report: words to listen to (fix with `SAY` + a re-read), a missing ending, or a loop at the end
   (`narration.py P cut AUDIO SECONDS`, re-read the lost sentences as one short part, list the files in `NARRATION`).
4. **Pictures**: `IMAGES` + `LOOKS` + `NEG` → `explain/make_images.py P` → `aip_runner.py P/jobs/images_jobs.json`
   → review sheet → user.
5. **Music**: the MV's instrumental (`python -m demucs --two-stems=vocals -n htdemucs song.wav`), `CH_MUSIC` per chapter,
   `MV_CLIP` and an `"MV:<second>"` shot for the ending.
6. **Render**: `SHOTS` (picture, first words, move, focus) → `explain/render.py P --until <words>` (test) →
   `explain/render.py P` → `out/NAME.mp4` + `.srt`; it prints the chapter times for the description.
7. **Publish**: cover (`mv/thumbkit.py` or a Layout cover), `YouTube_SEO.txt` (MV link on line 1, chapters, sources,
   AI disclosure), `mv/youtube_upload.py P --title A --category 27 --dry-run`, then without `--dry-run` (private).
   A playlist just for explainers (`dreamfab/youtube_playlists.py`). After the user publishes: pinned comment with the
   MV link (the API cannot comment on private videos), end screen and a card to the MV in Studio ("Related video" is
   Shorts-only).

`dreamfab/library.py serve projects` lists explainer folders under "其他資料夾" and plays their files.

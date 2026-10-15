---
name: autoip-mv-maker
description: >
  Turn a song into a full AI music video with the autoip-mv-maker pipeline: audio analysis, cast and
  storyboard, AutoIP keyframes / lip-sync / image-to-video, QC, emotion-driven beat-synced edit,
  kinetic subtitles, final render, thumbnails and YouTube/social copy. Use when the user wants to make
  an MV / music video / lyric video from a song, or mentions autoip-mv-maker, mvkit, 做 MV、音樂影片、
  對嘴 MV、歌詞動態字幕、把歌做成影片.
---

# autoip-mv-maker

A semi-automatic pipeline: one `project.py` per song drives everything. You (the agent) fill in
`project.py`, run the scripts, and show review sheets to the user at every gate.

## 0. Locate the toolkit

1. `ROOT` = `$AUTOIP_MV_HOME`, else `~/.autoip-mv-maker`.
   If this skill's base directory is `<repo>/skills/autoip-mv-maker` and `<repo>/mvkit/common.py`
   exists, you may use `<repo>` instead.
2. If `ROOT/mvkit` is missing, install it (clones the repo, creates `ROOT/.venv`, installs Python
   packages, downloads the face model). Skills are already installed, so pass `AUTOIP_MV_AGENTS=none`:
   - macOS / Linux / Git Bash:
     `curl -fsSL https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.sh | AUTOIP_MV_AGENTS=none bash`
   - Windows PowerShell:
     `$env:AUTOIP_MV_AGENTS='none'; irm https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.ps1 | iex`
3. `PY` = `ROOT/.venv/bin/python` (Windows: `ROOT/.venv/Scripts/python.exe`); fall back to `python`.
   Every command below is `PY ROOT/mvkit/<script>.py ...`.
4. Check `ffmpeg -filters` lists `subtitles` (libass). If not, ask the user to install ffmpeg.
5. `AUTOIP_API_KEY` must be set in the environment. If it isn't, ask the user to set it themselves.
   Never read keys from other places, never write a key into any file, never echo it.

## Hard rules

- **Credits are charged on submit and there is no cancel.** Before every batch of video jobs,
  generate stills and show a review sheet (`qc/sheets.py`) to the user. New characters, group shots
  and changed prompts always go through a still → user approval → video.
- **Run jobs one at a time** (`AIP_MAX=1`, the default) unless the user says their account allows more.
- Before submitting, state the job count and estimated credits (see the cost table in WORKFLOW) and
  get the user's go-ahead.
- Projects live in the user's working directory (e.g. `./projects/<song>`), never inside `ROOT`.
- Don't add songs, character art, fonts or keys to git.

## Workflow

Full details, commands and review gates: `ROOT/docs/en/WORKFLOW.md` (中文：`ROOT/docs/zh-TW/WORKFLOW.md`).
Field reference: `ROOT/docs/en/PROJECT_FORMAT.md`. Known pitfalls: `ROOT/docs/en/LESSONS.md` —
read it before planning shots.

1. **Project**: `cp -r ROOT/examples/demo projects/<song>`; put in `song.mp3`, `chars/*.png`, `fonts/`.
2. **Audio**: `audio/analyze.py` (beats), Demucs vocals, `audio/voice_probe.py` + `audio/split_voices.py`
   for duets, `audio/asr_words.py` for word timings, `audio/emotion_map.py` for the emotion map.
3. **Storyboard**: write `CHARS`, `LS_SCENES`, `LIPSYNC`, `BAND`, `BROLL`, `SECTIONS` in `project.py`;
   run `faces.py`, `storyboard.py`.
4. **Keyframes**: `make_jobs.py P kf` → `aip_runner.py` → `qc/sheets.py stills` → **user review**.
   Group shots: `group_still.py P <id>` → pick a candidate with the user.
5. **Video**: `make_jobs.py P video` → `aip_runner.py` → `qc/sheets.py strips` → user review.
6. **QC**: `qc/align.py`, `qc/mouth.py timeline` (idle mouths, zoom-outs, tail smear, burned-in text).
7. **Edit**: write `EDITS` (short + full) following the `emotional-beat-editing` skill;
   check with `qc/mouth.py P edl <mode>`.
8. **Subtitles**: `TYPO` theme; preview with `qc/subprev.py` (seconds, not minutes).
9. **Render**: `render_mv.py P short|full` → `P/out/*.mp4 + .srt`; spot-check with `qc/sheets.py video`.
   Vertical Shorts: an edit with `size=(1080, 1920)`, `focus` from `qc/focus.py P <mode>`, portrait `zones`
   and `end_card` (WORKFLOW, "Vertical cut").
10. **Publish**: thumbnails (`thumbkit.py`, see `examples/demo/thumbs.py`), titles, description,
    chapters, tags, social posts — `ROOT/docs/en/PUBLISHING.md`.

`credits.py` audits what each job folder actually cost.

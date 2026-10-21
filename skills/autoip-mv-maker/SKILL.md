---
name: autoip-mv-maker
description: >
  Turn a song into a full AI music video with the autoip-mv-maker pipeline: audio analysis, cast and
  storyboard, AutoIP keyframes / lip-sync / image-to-video, QC, emotion-driven beat-synced edit,
  kinetic subtitles, final render, thumbnails and YouTube/social copy. Use when the user wants to make
  an MV / music video / lyric video from a song, or a whole series / season of MVs, or mentions
  autoip-mv-maker, mvkit, 做 MV、音樂影片、對嘴 MV、歌詞動態字幕、把歌做成影片、MV 系列、一季 MV.
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
- **Run jobs one at a time** (`AIP_MAX=1`, the default) unless the user says their account allows more. For an
  off-peak window add `AIP_MAX_UNTIL=HH:MM AIP_MAX_AFTER=1` so the runner drops back by itself.
- Before submitting, state the job count and estimated credits (see the cost table in WORKFLOW) and
  get the user's go-ahead.
- Projects live in the user's working directory (e.g. `./projects/<song>`), never inside `ROOT`.
- Don't add songs, character art, fonts or keys to git.
- Keep `MOTION_PREFIX` to the art style only. Characters or props named there get pushed into every clip.
- Treat render `WARN ... short by` / `WARN ... before clip start` as errors: fix the edit from `align.json`
  durations (lip-sync clips are often 0.2–0.6 s shorter than requested) before showing the cut.
- Lip-sync stills must already be singing (open mouth): a calm closed-mouth portrait idles for the first 3–5 s.
  Run `qc/mouth.py P edl full` before every render and cut away from `IDLE?` windows. Keep complete shoulders
  (a bust cut-out narrower than the shoulders ends the arms flat); text-to-image half bodies drift from the face.
- Lip-sync clips often carry burned-in garbled captions (any colour, any edge). Never write "no text" in the
  prompt (it gets worse); remove them with AutoIP `POST /videos/restore` (`source_video` + `operations[]=subtitle`,
  30 credits per 8 s). Don't crop or re-cut around captions. `engine=h3` (lip-sync 3.0) burns none and syncs
  better but outputs 864×480. On a sharp painted background the model writes the lyrics as vertical
  calligraphy restore can't remove: blur the still's background (`bokeh_still.py OUT_DIR P/kf/L_*.png`),
  generate several takes and pick each lyric line from a clean one.
- Painted looks (ink wash, woodcut…): story shots from text-to-image with the style first in the prompt (`v3` adds red
  seals unless told "unsigned, without seals"). Image-to-image keeps a photographic background, so open the mouth with
  image-to-image, then `BG=plate.png bokeh_still.py` puts the singer on a painted plate. Pilot one lip-sync take: it may
  repaint the plate as a photograph; `matte_video.py raw.mp4 plate.png out.mp4` puts every frame back on the plate.
- With lyrics as `initial_prompt`, ASR guesses the next lyric line; re-check doubtful section openings without a prompt.
  `ASR_DEVICE=cuda` runs it on an NVIDIA GPU. In Git Bash `ps` hides arguments: check for a running `aip_runner.py`
  through `Get-CimInstance Win32_Process` command lines, not `ps aux | grep`.

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
   `qc/zoom.py P` flags lip-sync 3.0 clips that zoom themselves into a close-up or pull back (it is random; a camera
   instruction in the prompt only delays it): make two takes of important lines and keep the steadier, edit before `push@`.
7. **Edit**: write `EDITS` (short + full) following the `emotional-beat-editing` skill;
   check with `qc/mouth.py P edl <mode>`.
8. **Subtitles**: `TYPO` theme; preview with `qc/subprev.py` (seconds, not minutes).
9. **Render**: `render_mv.py P short|full` → `P/out/*.mp4 + .srt`; spot-check with `qc/sheets.py video`.
   Vertical Shorts: an edit with `size=(1080, 1920)`, `focus` from `qc/focus.py P <mode>`, portrait `zones`
   and `end_card` (WORKFLOW, "Vertical cut").
10. **Publish**: thumbnails (`thumbkit.py`, see `examples/demo/thumbs.py`), Shorts thumbnails for the
    vertical cut (`tk.W, tk.H = 1080, 1920`, key text above y 1440, desktop Studio upload only, no
    Test & compare for Shorts), titles, description,
    chapters, tags, social posts — `ROOT/docs/en/PUBLISHING.md`.
    Upload: `mvkit/youtube_upload.py P --dry-run`, then without it (private by default; the user publishes in Studio).
    Never make a video public or schedule it unless the user asks. Read the channel name it prints; one Google account
    can own several channels. The API description limit is 5,000 bytes (about 1,600 CJK characters).
    Playlists: `mvkit/youtube_playlists.py list`, then sort / add / remove / edit / delete / replace: run each without
    `--apply` first (it prints the plan) and apply only what the user approved. Sorting needs the playlist's default
    ordering set to Manual on YouTube (the API cannot change it).

`credits.py` audits what each job folder actually cost.

## Series

When the user wants several MVs as a series or season, plan the season before episode 1, following
`ROOT/docs/en/SERIES_PLANNING.md` (中文：`ROOT/docs/zh-TW/SERIES_PLANNING.md`). Blank template:
`ROOT/examples/series_template/`.

- It is a framework, not a style. Ask the user for the subject, the axis and which anchors to fix; never
  borrow the look, genre, structure or wording of an existing series (including the README example videos).
  Offer options from the guide's menus and let the user choose.
- Formula, every season: a one-line pitch, one axis that orders the episodes, 3–5 fixed anchors in `style.md`,
  one song structure, one package (thumbnail layout, title format, description order), a card per episode in
  `research.md`. Everything else changes freely; if one layer is fixed, another should change a lot.
- Layout: `projects/<series>/` with `research.md`, `style.md` and `s<season>e<episode>_<title>/` folders. Name an
  episode folder before its first AutoIP job: job files store absolute paths.
- Have the user approve `research.md` and the draft `style.md` before writing the first lyrics; settle
  `style.md` after episode 1.
- Before each episode's lyrics, prompts and thumbnails, re-read `style.md`. Episode 1's `project.py` starts from
  the demo; later episodes copy the previous episode's.
- Keep lyric versions (`歌詞_v1.txt`, `v2`, …); after an episode, tick it in `style.md` with the final version.

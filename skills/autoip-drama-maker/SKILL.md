---
name: autoip-drama-maker
description: >
  Turn a script into a vertical AI short drama with the autoip-drama-maker pipeline: script, cast / set / prop
  references and voice samples, shot list, AutoIP multi-reference dialogue shots (each character speaks in their own
  voice), lip-sync / image-to-video / keyframe shots, QC, dialogue-driven edit with reaction shots and cliffhangers,
  subtitles and character cards, ducked music, covers and publishing copy. Use when the user wants to make a short
  drama / micro drama / vertical drama / web series episode, plan a whole series of episodes, or mentions
  autoip-drama-maker, dramakit, 短劇、微短劇、直式短劇、AI 短劇、做一集短劇、把劇本做成影片、短劇企劃、分集大綱.
---

# autoip-drama-maker

A semi-automatic pipeline: one `project.py` per episode drives everything. You (the agent) write the script with the
user, fill in `project.py`, run the scripts, and show review sheets to the user at every gate.

## 0. Locate the toolkit

1. `ROOT` = `$AUTOIP_DRAMA_HOME`, else `~/.autoip-drama-maker`.
   If this skill's base directory is `<repo>/skills/autoip-drama-maker` and `<repo>/dramakit/common.py`
   exists, you may use `<repo>` instead.
2. If `ROOT/dramakit` is missing, install it (clones the repo, creates `ROOT/.venv`, installs Python packages).
   Skills are already installed, so pass `AUTOIP_DRAMA_AGENTS=none`:
   - macOS / Linux / Git Bash:
     `curl -fsSL https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.sh | AUTOIP_DRAMA_AGENTS=none bash`
   - Windows PowerShell:
     `$env:AUTOIP_DRAMA_AGENTS='none'; irm https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.ps1 | iex`
3. `PY` = `ROOT/.venv/bin/python` (Windows: `ROOT/.venv/Scripts/python.exe`); fall back to `python`.
   Every command below is `PY ROOT/dramakit/<script>.py ...`.
4. Check `ffmpeg -filters` lists `subtitles` (libass). If not, ask the user to install ffmpeg.
5. `AUTOIP_API_KEY` must be set in the environment. If it isn't, ask the user to set it themselves.
   Never read keys from other places, never write a key into any file, never echo it.

## Hard rules

- **Credits are charged on submit and there is no cancel.** Before every batch: show the review sheet
  (`qc/sheets.py stills` for pictures, `qc/sheets.py jobs` for video jobs), state the job count and the estimate that
  `make_jobs.py` prints, and get the user's go-ahead. New characters, sets and changed prompts always go through
  a still → user approval first.
- **Pilot before the batch**: one multi-reference shot with dialogue per speaking character (`ONLY=...`). Listen to the
  voice and look at the face with the user before sending the rest.
- **Run jobs one at a time in the daytime** (`AIP_MAX=1`, the default), even when `/me` reports no concurrency limit
  (`max_concurrent_tasks: null`). More than one only off-peak, and only when the user says so:
  `AIP_MAX=N AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1`.
- Projects live in the user's working directory (`./projects/<series>/s1e01_<title>`), never inside `ROOT`. Name the
  episode folder before its first AutoIP job: job files store absolute paths.
- **The story stays in the project.** Scripts, characters, lines, plans and covers go in `projects/` (ignored by git);
  never write a story into the toolkit's examples, docs or code. Examples there are structure with `<…>` placeholders.
- **One speaker per shot.** A multi-reference job takes one voice sample; dialogue is cut shot / reverse shot. Keep a
  line within about 4 characters per second of the shot (≤ 40 characters in 10 s); longer lines are split or become
  `LS` shots with the user's own recording.
- Keep `MOTION_PREFIX` to the art style only, and `SFX` to "no music" (music is added in the edit). Characters or props
  named there get pushed into every clip.
- **Multi-reference prompts are English; only the line is Chinese.** AutoIP builds MiniMax H3's prompt and appends
  "<Subject 1> looks at the camera and says: <d>[Chinese]line</d>"; Chinese narration next to it gets spoken (a take
  read the prompt out, another had gibberish before the line). Write `act`, the delivery in `say` and `MOTION_PREFIX`
  in English, name people with `@KEY` (no he / she), keep the speaker's SHOT last. The Chinese script stays in
  `劇本_v1.md`.
- Write prompts as what should be seen; never "no text" / "nobody" / "不要出現…": restriction sentences get drawn.
- Voices, faces and music must be ones the user has the rights to; no real public figures. Ask where a recorded
  voice sample comes from before using it (voices made with `make_jobs.py P voices` need no asking).
- Never invent the user's story: ask for the premise, the engine and the characters, offer options, let them choose.
  Don't borrow the plot, characters or wording of an existing drama.
- Treat render `WARN` lines as errors to fix before showing a cut (`covers the start of`, `the last frame is held`).

## Workflow

Full details, commands and review gates: `ROOT/docs/en/WORKFLOW.md` (中文：`ROOT/docs/zh-TW/WORKFLOW.md`).
Field reference: `ROOT/docs/en/PROJECT_FORMAT.md`. Known pitfalls: `ROOT/docs/en/LESSONS.md` — read it before writing
shots. Editing craft: `ROOT/docs/en/EDITING.md` — read it before writing `EDITS`.

1. **Script**: `劇本_v1.md` with the user: a hook in the first 3 s, pressure, a payoff (reveal / comeback), a
   cliffhanger in the last 5 s. Keep versions (`v2`, `v3`). Then `SCENES` and `SHOTS` in `project.py`
   (episode 1 starts from `ROOT/examples/demo/project.py`; later episodes copy the previous one).
2. **References**: `CAST` / `SETS` / `PROPS` with English `desc`; `make_jobs.py P refs` → `aip_runner.py` →
   `qc/sheets.py stills` → **user review**. One look per character per arc.
3. **Voices**: made, not recorded. `voice_line` + `voice_how` per character, `voice_src="voices/raw/<KEY>.mp4"`;
   `make_jobs.py P voices` (image-to-video with sound from the character sheet; text-to-video for `file=None`) →
   `aip_runner.py` → `voices.py P` cuts `voices/<KEY>.wav` (5–15 s, one speaker, no music) → **user listens**. Don't
   ask the user for recordings; a recording they bring goes straight into `voice_src`.
4. **Shot list**: `storyboard.py P` → read every WARN (line too long, > 6 references, unknown key, speaker without
   voice, two people in one still). Kinds: `M` dialogue / reactions / anything with cast (default), `LS` long or exact
   lines with a recording, `I2V` inserts and exteriors, `K` doors and transitions.
5. **First frames** (LS / I2V / K): `make_jobs.py P kf` → runner → `qc/sheets.py stills P/review_kf.jpg P/kf` →
   **user review**. Lip-sync stills must already be mid-sentence (open mouth).
6. **Pilot**: `ONLY=<one M shot per speaker> make_jobs.py P video` → runner → listen and look with the user.
7. **Video**: `make_jobs.py P video` → `qc/sheets.py jobs P/review_jobs.jpg P/jobs/video_jobs.json` → **user approves
   jobs and credits** → `aip_runner.py P/jobs/video_jobs.json`.
8. **QC**: `qc/clips.py P` (BROKEN downloads, internal cuts, sound), `speech.py P` (CUT? / TEXT? / SILENT? lines:
   listen to every flagged one), `qc/sheets.py strips` (face swaps, extra people, grey backdrops, garbled text).
9. **Edit**: `edl_draft.py P` → paste into `EDITS["main"]` → cut following EDITING.md: cold open on the conflict,
   shot / reverse shot, `^` reaction cutaways on the key line, `zoom sfx=hit` on the payoff, `intro=KEY` on first
   appearance or reveal, `title` after the hook, `freeze=1.6 end` on the last frame. `edl_draft.py P main` shows the
   timing.
10. **Subtitles and sound**: `TYPO`, `MUSIC` cues (files in `music/`), `sfx=` hits (files in `sfx/`); preview with
    `qc/subprev.py P main out.jpg t1 t2 ...`.
11. **Render**: `render_ep.py P main` → `P/out/<NAME>.mp4 + .srt`; check frames with `qc/sheets.py video`.
    `REUSE_BODY=1` for subtitle / sound changes; `SUBST="A:B"` for a rough cut before every clip exists.
12. **Publish**: covers with `thumbkit.py` (see `ROOT/examples/demo/covers.py`), title `《劇名》第N集｜<hook>`,
    description, hashtags, AI disclosure — `ROOT/docs/en/PUBLISHING.md`. Write them into `YouTube_SEO.txt`.

`credits.py P/jobs` audits what each job folder actually cost.

**Library**: `python ROOT/dramakit/library.py serve <series folder>` indexes the whole series (episodes, shots, lines,
clips, takes, cast and looks, sets, renders, jobs and estimated credits, YouTube uploads) into
`<series folder>/library.db` and serves a page on http://127.0.0.1:8765. Point the user to it when they ask where
something is or want an overview, and query `library.db` with sqlite3 yourself instead of walking folders. Re-run
it after renders, reshoots or uploads (`index` rebuilds without serving; it takes seconds).

## Series

When the user wants a whole drama (many episodes), plan it before episode 1, following
`ROOT/docs/en/SERIES_PLANNING.md` (中文：`ROOT/docs/zh-TW/SERIES_PLANNING.md`). Blank template:
`ROOT/examples/series_template/`.

- It is a framework, not a story. Ask the user for the premise, the engine (what keeps getting pushed down and what
  rises), the arcs and which anchors to fix; offer options from the guide's menus and let the user choose.
- Formula: a one-line pitch, one 壓 → 揚 engine, the same episode structure (hook / pressure / payoff / cliffhanger),
  3–5 big reveals that cut the series into arcs, fixed character looks and voices, one package, a card per episode
  in `plan.md`.
- Layout: `projects/<series>/` with `plan.md`, `style.md`, `characters.md`, shared `cast/ sets/ props/ voices/ music/
  sfx/ fonts/`, and `s1e01_<title>/` episode folders (`project.py` refers to `../cast/A.png`).
- Have the user approve `plan.md` (at least the first arc's cards), `characters.md` and the draft `style.md` before the
  first script. Before each episode, re-read them; this episode's hook answers the last episode's cliffhanger.

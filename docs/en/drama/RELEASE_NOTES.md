# Release notes

[中文](../../zh-TW/drama/RELEASE_NOTES.md) | English

## Dreamfab 0.9.0 (2026-10-30): the third line, 說 explainers

- **Explain line `explain/`**: the history and legend behind an MV as a 3-6 minute landscape explainer, made of:
  - a cloned narrator
  - text-to-image paintings with smooth pans and zooms
  - the MV's instrumental as the bed, one section per chapter, ducked under the voice
  - subtitles timed to the voice
  - an MV clip in a gold frame at the end

  Stills only: about 1,000 credits for 5 minutes at full price. The scripts are `narration.py` (parts split between chapters, then a check of speed, words to listen to, a missing ending and loops), `make_images.py` and `render.py`. See the [explainer overview](../explain/OVERVIEW.md), the example in `examples/explain/demo` and the `dreamfab-explain` skill.
- **Text-to-image v4 is MOSS-Image**: prompts follow its prompt enhancer (English prose captions, no quality-tag strings); covers with lettering use a Layout, which `make_images.py` compiles.
- **Library**: folders that are not a series (explainers, single MVs) appear under "其他資料夾" at `/files/...`, with players for their narration and videos.
- **Install**: `DREAMFAB_LINES` defaults to `drama,mv,explain`; the explain line adds `requirements-explain.txt` (OpenCV, pypinyin).

## Dreamfab 0.8.0 (2026-10-30): short drama and MV merged into Dreamfab 造夢廠

autoip-drama-maker and autoip-mv-maker are merged into [Dreamfab](https://github.com/autoip/dreamfab), an automated AI media workstation, with both histories kept; the old addresses redirect. The `project.py` format is unchanged.

- **Folders**: `dramakit/` → `drama/`, `mvkit/` → `mv/`; what they share moves into the core `dreamfab/`: `aip_runner.py`, `credits.py`, `check_public.py`, `gpu_check.py`, `make_static_font.py`, `youtube_api.py`, `youtube_playlists.py`, the enhance engine `enhance.py`, and shared helpers in `util.py`. Old and new paths: see the [README](../../../README.en.md).
- **Video encoding**: one rule for both lines, NVENC whenever ffmpeg can use it, `VENC=x264` forces the CPU. The MV line used to default to the CPU; with a GPU it is now faster at the same quality (VMAF 99.2 vs 99.3).
- **Runner**: the drama one (asks the server whether off-peak is on; a rejected job is never resent unchanged); `AIP_OFFPEAK=1` still works, and a full-price run prints the off-peak window.
- **Library**: `python dreamfab/library.py serve projects` shows every series, drama and MV, on one page; each series still runs its own line's library.
- **YouTube**: one login for both lines; credentials default to `~/.config/dreamfab/` (the old `~/.config/autoip-mv-maker/` is still read).
- **Install**: `~/.dreamfab`, `DREAMFAB_*` variables; `DREAMFAB_LINES=drama` installs only what the drama line needs (the MV extras are in `requirements-mv.txt`). Skills renamed `dreamfab-drama` and `dreamfab-mv`, the plugin `dreamfab`.
- **Docs**: the shared [SETUP.md](../SETUP.md), [GPU_ENHANCE.md](../GPU_ENHANCE.md) and [CONTRIBUTING.en.md](../../../CONTRIBUTING.en.md); each line's docs are in `docs/en/drama/` and `docs/en/mv/`. Paths in the older entries below are as they were then.

## 0.1.0 (2026-10-27): first release

The architecture follows [autoip-mv-maker](https://github.com/autoip/autoip-mv-maker): one `project.py` per episode, a review sheet before every batch of jobs, a resumable runner, local rendering with ffmpeg, a Claude Code / Codex skill. It is reworked to centre on the script and the dialogue:

- **Shots** (`storyboard.py`, `make_jobs.py`): `M` multi-reference video (the speaker says the line with their own voice sample, and the mouth is generated with it), `LS` lip-sync (lines you recorded yourself), `I2V` image-to-video, `K` keyframe video. References are put together automatically (speaker, `@KEY`, props, set), `@KEY` becomes `@圖片 N`, every SHOT names the location, gender words are taken out of the descriptions when there is a voice sample, and line length and credits are estimated. `make_jobs.py` rebuilds straight from `project.py` every time, so there is no intermediate file to remember to regenerate.
- **Material**: `make_jobs.py P refs` generates character sheets, sets and props, or derives them from a picture you have (`base`, `base_crop`, `base_box`; several strengths make candidates in one go); `voices.py` turns recordings into voice samples. Material shared by the whole series goes in the folder one level up.
- **QC**: `qc/sheets.py jobs` (each job's references, line, prompt and credits), `qc/clips.py` (broken files, cuts inside clips, whether there is sound), `speech.py` (where each line sits, whether it is finished, whether it is the line in the script).
- **Edit** (`timeline.py`): one row per shot, each placed after the previous row; `auto` trims to the line; cutaway rows `^` change only the picture (reaction shots, L/J cuts); `zoom`, `flash`, `black`, `freeze`, `sfx`, `mute`; clips from other episodes as a recap; `@name` pastes in another edit. `edl_draft.py` generates a rough cut.
- **Render** (`render_ep.py`): each row uses its own clip's sound, music sits under the dialogue automatically, sound effects go on top, −16 LUFS overall; vertical 1080×1920 by default, with an optional landscape version; optional end card.
- **Subtitles and cards** (`subs.py`): lines split at punctuation and timed to per-character timings; character intro cards, title card, top-left label, the cliffhanger 「未完待續」 ("To be continued"), episode tag. `qc/subprev.py` previews the subtitles only.
- **Covers** (`thumbkit.py`): vertical 1080×1920, hook copy, top/bottom split, episode tag.
- **Docs**: WORKFLOW, PROJECT_FORMAT, EDITING (short-drama editing), SERIES_PLANNING (planning a whole series), PUBLISHING, LESSONS (lessons carried over from the MV project, plus a list of what is not yet tested in drama), SETUP.
- **De-identified story**: the repo's demo episode, templates and docs hold structure only (characters A / B / C; sets and lines are all `<…>` placeholders); the concrete script, characters and material go only in `projects/` (kept out of git).
- Carried over from autoip-mv-maker: `aip_runner.py`, `credits.py`, `make_static_font.py`.

**Not done yet**: automatic YouTube upload and playlist tidying (autoip-mv-maker's `youtube_upload.py` and `youtube_playlists.py` need a version that uploads episode by episode), mouth QC for lip-sync shots (`qc/mouth.py`), face-based positioning for cropping landscape footage to vertical (`qc/focus.py`).

# Release notes

[中文](../zh-TW/RELEASE_NOTES.md) | English

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

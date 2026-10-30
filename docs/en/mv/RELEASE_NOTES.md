# Release notes

[中文](../../zh-TW/mv/RELEASE_NOTES.md) | English

## Dreamfab 0.8.0 (2026-10-30): short drama and MV merged into Dreamfab 造夢廠

autoip-drama-maker and autoip-mv-maker are merged into [Dreamfab](https://github.com/autoip/dreamfab), an automated AI media workstation, with both histories kept; the old addresses redirect. The `project.py` format is unchanged.

- **Folders**: `dramakit/` → `drama/`, `mvkit/` → `mv/`; what they share moves into the core `dreamfab/`: `aip_runner.py`, `credits.py`, `check_public.py`, `gpu_check.py`, `make_static_font.py`, `youtube_api.py`, `youtube_playlists.py`, the enhance engine `enhance.py`, and shared helpers in `util.py`. Old and new paths: see the [README](../../../README.en.md).
- **Video encoding**: one rule for both lines, NVENC whenever ffmpeg can use it, `VENC=x264` forces the CPU. The MV line used to default to the CPU; with a GPU it is now faster at the same quality (VMAF 99.2 vs 99.3).
- **Runner**: the drama one (asks the server whether off-peak is on; a rejected job is never resent unchanged); `AIP_OFFPEAK=1` still works, and a full-price run prints the off-peak window.
- **Library**: `python dreamfab/library.py serve projects` shows every series, drama and MV, on one page; each series still runs its own line's library.
- **YouTube**: one login for both lines; credentials default to `~/.config/dreamfab/` (the old `~/.config/autoip-mv-maker/` is still read).
- **Install**: `~/.dreamfab`, `DREAMFAB_*` variables; `DREAMFAB_LINES=drama` installs only what the drama line needs (the MV extras are in `requirements-mv.txt`). Skills renamed `dreamfab-drama` and `dreamfab-mv`, the plugin `dreamfab`.
- **Docs**: the shared [SETUP.md](../SETUP.md), [GPU_ENHANCE.md](../GPU_ENHANCE.md) and [CONTRIBUTING.en.md](../../../CONTRIBUTING.en.md); each line's docs are in `docs/en/drama/` and `docs/en/mv/`. Paths in the older entries below are as they were then.

## 0.7.2 (2026-10-29): local GPU super resolution + frame generation (optional)

- **`enhance.py`** (new): as in autoip-drama-maker, NVIDIA Video Super Resolution (2x) and Video Frame Generation (to 60 fps) turn the clips the edits use into `clips_hd/<id>.mp4` (picture only). The settings are kept in a `.json`, and a copy is redone when its clip is newer or the settings changed; `--watch` runs next to the runner; `ONLY=` limits it to some clips. Needs an RTX 40 / 50 card, PyTorch with CUDA, PyAV and `nvidia-vfx`.
- **`render_mv.py`**: an edit can carry `render=dict(...)` over `RENDER`; with `enhance=True` rows read the `clips_hd/` copies (a clip without one is used as it is, with a warning), and `crop=` / `delogo=` pixel values are scaled. Without it nothing changes.
- **`common.hd_path()`**; **`gpu_check.py`** prints an `hd` line.
- **GPU_ENHANCE.md**: "bringing it to mv-maker" is now how to use it, with numbers from one gongbi-style MV: the portrait cut gets clearly cleaner and the landscape cut barely changes, but the decision-maker found it too sharp and short on painterly feel, so the finished MV uses the originals. It is optional and off by default.

## 0.7.1 (2026-10-29): submit in the off-peak half-price window

- **`aip_runner.py`**: `AIP_OFFPEAK=1` submits new tasks only in AutoIP's off-peak window (from 2026-10-30, tasks submitted with an API key between 03:00 and 09:00 Taiwan time cost half). The window and whether it is on come from `off_peak` in `GET /pricing`, else the announced 03:00–09:00 UTC+8; submitting stops 2 minutes before the end, since the submit time sets the price. Outside the window it keeps polling and downloading running tasks and waits for the next one. Without it, outside the window it prints a one-line tip. Each submit keeps the credits charged and whether it was off-peak in `.state`; discounted ones are marked `(off-peak)`.
- **`common.estimate`**: `off_peak=True` gives the off-peak price (half, rounded up, at least 1), matching `off_peak_credits` in `/pricing`.
- **`library.py`**: job credits use what `.state` says was charged first, so off-peak tasks are not counted at full price.
- **`feature_jobs.py`**: multi-reference video takes reference images up to 10 MB each, and hd_4k character sheets (about 17 MB) are rejected with a 422; anything over 9.5 MB is sent as a JPEG copy (at most 2560 wide) saved in `jobs/img/`.
- SETUP, WORKFLOW (off-peak column in the cost table), README and the skill updated.
- **CONTRIBUTING.md** (new, Chinese and English): code and doc conventions, pull requests, bug reports, and de-identification before you send: what must never be uploaded (keys, real people's images and voices, personal data, account identifiers, local paths, unpublished work), commands to mask the key, a grep self-check before pushing, and revoking the key first if something slips through. `.github/` gains a PR template (de-identification checklist) and a bug-report template (public-page warning).

## 0.7.0 (2026-10-28): library page

- **`library.py`** (new): indexes a whole series into `<series folder>/library.db` (SQLite): every episode (genre, each cut's render and length, cover, lip-sync share, estimated credits, stage), every shot (lip-sync, band, B-roll, keyframe, multi-reference: still or reference images, clip, prompts, the lyrics it covers, which cuts use it and how often, old takes and candidates), lyric timings, edit lists (row lengths, reused clips), characters and reference images, files by kind, AutoIP jobs with estimated credits, and the uploads in `youtube.json`. `serve` opens a page on 127.0.0.1 (overview, episode, shot, characters, files, jobs and credits, YouTube, search) with posters for every clip and videos that load on click and can seek; while it runs it checks every 15 s and re-indexes in the background into a copy that is swapped in. Standard library plus ffprobe / ffmpeg only; lengths and posters are cached, so a rebuild takes seconds. Default port 8770, the next one if taken (on Windows two servers can bind the same port without an error, so SO_REUSEADDR is off there). OAuth secrets and tokens are never indexed or served.
- **`common.estimate`**: credits for one job at the `GET /pricing` rates (text-to-image / image-to-image modes, multi-angle, image-to-video and multi-reference by resolution × seconds, keyframe per second, lip-sync engine and resolution, restore per 8 s segment).
- README, WORKFLOW and the skill describe the library; `.gitignore` adds `library.db`, `library.db.tmp` and `.library/`.

## 0.6.1 (2026-10-27): optional NVIDIA GPU speed-ups, CPU still the default

- **`gpu_check.py`** (new): shows which steps this machine's NVIDIA GPU can take over and prints the env flags or installs for each. Without a GPU it says everything runs on the CPU.
- **`common.venc`**: one set of video-encoder settings for every encode. x264 by default, as before; `VENC=nvenc` encodes on the GPU (h264_nvenc). When NVENC works but `VENC` is not set, it only prints a tip.
- **`render_mv.py`**: segments, cards and the final file all go through `venc`; with `VENC=nvenc` it encodes 4 segments at a time (`JOBS` changes it; 1 on the CPU by default). Measured on an RTX 5060 Ti: a 190 s MV in 50 s, 2 min 45 s on the CPU, with identical audio; final VMAF 99.2 vs 99.3. **`matte_video.py`** encodes through `venc` too.
- **`asr_words.py`**: `ASR_DEVICE=cuda` now uses int8_float16 (60 s of vocals in 1.0 s on an RTX 5060 Ti, 10.9 s on the CPU); `ASR_COMPUTE` overrides it. With a GPU present but no `ASR_DEVICE`, it only prints a tip.
- Docs: SETUP's GPU part is now a table (how to turn on each step, measured speed, a CUDA PyTorch build for Demucs); LESSONS adds that NVENC's cq needs `-maxrate`; WORKFLOW, the skill and requirements are updated to match.

## 0.6.0 (2026-10-25): multi-reference and keyframe job files, AutoIP features named on screen

- **`feature_jobs.py`** (new): turns `project.py`'s `I2V`, `KEYFRAME` and `MULTI` into image-to-video 3.0, keyframe video (2frame) and multi-subject reference 3.0 jobs, for an MV that shows several AutoIP features at once. Fights and scenes with several characters go to multi-reference, A→B moments and transitions to keyframe video, and image-to-video keeps a few atmosphere shots. Reference pictures are looked up in `refs/`, `refs/angles/` (multi-angle views) and `kf/`; descriptions come from `MULTI`, `REFS` or `REF_DESC`.
- **`render_mv.py`**: `project.FEATURE` (clip id prefix → feature name) fades an "AutoIP｜<feature>" tag in at the top right for about 2 s on the shot where the feature changes (AutoIP in orange, 46 px); `labels=False` on an edit turns it off.
- **`epic.py`**: `TYPO.rewrite` takes an optional third field, written above the struck part in the same colour.
- **`bokeh_still.py`**: `CROWN_KEY=1` keeps long ornaments above the head (feathers, tall hats), which person segmentation cuts off, by colour difference from a plain backdrop; `SAVE_CROWN=1` saves that mask. **`matte_video.py`**: `KEEP=mask` adds it back on every frame, following the face.
- **`aip_runner.py`**: a task with several outputs (multi-angle views) downloads them all: `out`, `out_1`, `out_2`, …
- **`storyboard.py`**: `project.EXTRA_CAPS` lets clips outside `BROLL` / `BAND` / `LS_SCENES` (keyframe, multi-reference) be listed in section shots.
- LESSONS gets "Multi-reference and keyframe video": a SHOT with no location gets the references' grey studio background (4 of 11 clips; retaken with a location in every shot, 3 of 3 stayed on set); precise prop business (cutting a rope, throwing a spear) doesn't happen; an 8–10 s clip cuts 2–4 times by itself; keyframe video between two different scenes cuts or dissolves at about 65% (8 of 10). Also: theatre-style image-to-video walks a new character in after 2–3 s (4 of 14); with "do not push in" in the prompt 1 of 3 lip-sync takes still jumped to a close-up at 1 s; portrait `focus` is a fraction of the crop window's travel, not a frame position; `qc/focus.py` doesn't find puppet faces; tags must be big enough for phones; the outro title covers faces in the last shot. PROJECT_FORMAT, WORKFLOW, README and the skill are updated to match.

## 0.5.3 (2026-10-24): per-shot portrait focus, numbers from a woodblock-print MV

- **`render_mv.py`**: `focus` also takes `"clip id@row time"` keys, so one shot of a clip gets its own portrait crop centre. A lip-sync singer walked from the middle of the frame to the left third and back within one clip; a single centre cut her face in some shots of the Shorts cut.
- LESSONS: halving a doubled tempo on the wrong phase puts every snapped cut on the off-beat (pick the half the strong snare onsets land on); a shared prefix ending in "… animation MV" gets burned in as subtitles (5 of 67 clips); "keep the whole frame in ___ colours" stopped a palette drift in the pilot but 2 of 42 still drifted; the same still as first and last frame fixes pull-backs but made 3 of 5 other repairs insert a passing object (slow push-ins on the keyframe instead); a lip-sync take can break with a giant copy of the face behind the singer; `mouth.py` OFF? is unreliable on breathy songs; decode every downloaded clip, since one came down half-written. PROJECT_FORMAT documents the per-shot `focus` key.

## 0.5.2 (2026-10-23): harmony splits, a render audio fix, camera wording for image-to-video

- **`split_voices.py`**: `project.VOICE_BOTH` marks spans where both sing together; both voice tracks keep them, so both lip-sync singers open their mouths in a harmony chorus.
- **`render_mv.py`**: every segment gets the same colour tags (bt709/tv). When some clips are tagged and others are not (e.g. `matte_video.py` output), the final ffmpeg re-initialises the whole filtergraph at the switch, the song's `atrim` restarts, and about 2 s of audio drop out of the result.
- LESSONS: a motion prompt that moves the camera or names something outside the frame makes the model invent a new scene (4 of 66 clips); write "static camera" plus how things already in the picture move. For a clip that keeps pulling back, send the same still as both `first_frame` and `last_frame` to pin the framing. PROJECT_FORMAT documents `VOICE_BOTH`.

## 0.5.1 (2026-10-22): numbers from a full batch, off-peak windows

- **`aip_runner.py`**: `AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1` runs several tasks at once only during an off-peak window and drops back to 1 at that time by itself; tasks already running finish normally.
- LESSONS gets the numbers from a whole ink-wash MV: 4 of 12 lip-sync takes had the background repainted as a photograph and 1 grew a photographic pillar; `matte_video.py` cuts silver hair ornaments away on a pale paper background (all 3 such takes), so use the other take there; ink-wash image-to-video writes a lyric-like motion prompt into the picture (text both times); of 60 clips 2 turned photographic and 6 grew colour late; rerun `storyboard.py` after changing a `BROLL` prompt. SETUP and the skill describe the off-peak window.

## 0.5.0 (2026-10-22): painted looks, GPU speech recognition

- **`matte_video.py`** (new): re-composites a lip-sync clip onto a still plate, frame by frame. In an ink-wash test, lip-sync 3.0 repainted the background as a photographic garden within 0.8 s; put back on the plate, the whole clip stays inside the painting with the clip's own mouth. The mask is smoothed across frames so the edge doesn't flicker; about 40 s for a 20 s clip, CPU only.
- **`bokeh_still.py`**: `BG=picture` puts the person on another picture (cover-fit, still blurred by `BLUR`). For "a real person standing inside the painting" lip-sync stills: image-to-image from a semi-realistic character sheet can't paint an ink-wash background.
- **`asr_words.py`**: `ASR_DEVICE=cuda` runs on an NVIDIA GPU (int8), about 2.3× a 16-thread CPU on a GTX 1060. On Windows it finds the pip-installed cuBLAS and cuDNN DLLs.
- **`epic.py`**: `TYPO.rewrite`, a "rewrite" card before the title: an old line, a vermilion stroke crossing out part of it, then the title burns in.
- Docs: LESSONS (ink wash needs text-to-image, v3 stamps seals, image-to-image keeps a photographic background, lip-sync may repaint a painted background, lyric prompts make ASR guess the next line, GPU ASR, Git Bash `ps` can't see runners), SETUP (optional GPU ASR; measured decode and NVENC), WORKFLOW (painted plates, pilots, re-compositing), PROJECT_FORMAT (`rewrite`), README, skill.

## 0.4.3 (2026-10-20): tidy YouTube playlists

- **`youtube_playlists.py`**: lists every playlist and the uploads in none; sorts by a given order, upload date or title; adds and removes videos (`--dead` also drops deleted-video placeholders); renames and describes playlists; deletes empty ones; `replace` changes the same text in many video descriptions (the whole snippet goes back, so tags survive). Commands that write print a plan and need `--apply`; `YT_CHANNEL_ID` locks the channel; after writing it waits until a re-read shows the change.
- **`youtube_upload.py`**: reads the playlist back after adding a video. The login moved to `youtube_api.py`, shared by both tools.
- Docs: PUBLISHING (tidying playlists), LESSONS (publishing: Manual ordering, read lag, send the whole snippet), README, WORKFLOW, skill.

## 0.4.2 (2026-10-19): the full push-in test

- **Correction to 0.4.1**: with the 20-clip A/B test done, "a concrete camera instruction reduces push-in" does not hold. It removed the early jumps (0/16) but also cut fully steady takes from 14/29 to 2/16, and usable seconds averaged lower than with the old prompt; push-in is largely random. LESSONS "Lip-sync", PROJECT_FORMAT, WORKFLOW and the skill now say: keep the usual prompt, make two takes of important lines, pick with `zoom.py`.
- **`qc/zoom.py`** also flags pull-backs (face below 0.75x or not found: `OUT`, `out@`).

## 0.4.1 (2026-10-19): lip-sync push-in check

- **`qc/zoom.py`**: measures the face size in lip-sync clips every 2 s and flags clips that zoom themselves into a close-up (`ok` / `LATE` / `PUSH` / `JUMP`), and from which second.
- LESSONS "Lip-sync": 29 measured clips and first A/B results: a concrete camera instruction reduces push-in, dramatic emotion words after it undo that, shorter audio does not help, a wider still is a safety net. WORKFLOW QC and PROJECT_FORMAT's `motion_prompt` advice updated.

## 0.4.0 (2026-10-19): automatic YouTube upload

- **`youtube_upload.py`**: reads `YouTube_SEO.txt` and uploads the video, thumbnail and subtitles through the YouTube Data API, filling in the title, description, chapters, tags, category and languages, setting "not made for kids" and "altered or synthetic content", and optionally adding a playlist. Videos go up private by default, to be checked and published in Studio; `--publish-at` schedules a release, `--update` rewrites the copy after edits.
- **Checked before sending**: title ≤ 100 characters, description ≤ 5,000 bytes (about 1,600 CJK characters), tags ≤ 500 characters (commas and the quotes of tags with spaces count), chapter rules. `--dry-run` checks without uploading.
- **No wrong channel, no double uploads**: after login it prints the channel name, and `YT_CHANNEL_ID` locks the channel (one Google account can own several). Before uploading it compares the 《title》 of the channel's latest 50 uploads, which also catches copies uploaded by hand; uploaded ids are kept in `youtube.json`.
- **Shorts**: upload the full MV first; `{full}` in the Shorts description becomes its link. Shorts thumbnails skip the API (YouTube stores them as 16:9 and the Shorts shelf ignores them); the script reminds you to upload them in Studio.
- The `YouTube_SEO.txt` template gains three sections: an API description, a Shorts description and a pinned comment.
- **Lip-sync jobs**: `project.LS_FIELDS` adds lip-sync fields (e.g. `engine=h3`, `resolution=768p`); stills over 10 MB (hd_4k stills are about 15 MB and get rejected) are sent as a 2560-wide JPEG automatically.
- **`bokeh_still.py`**: white fur collars and pale cloth were often cut out as background. It now fills holes the person encloses and drops pieces cut off from the person; `SOLID_TORSO=1`, for a half-body with nothing in the hands, makes every row below the chin solid from its leftmost to its rightmost person pixel.
- Docs updated: PUBLISHING (one-time Google Cloud setup, usage, limits, what stays manual), LESSONS (publishing), WORKFLOW, README, skill. `requirements.txt` lists the optional `google-api-python-client` and `google-auth-oauthlib`.

## 0.3.0 (2026-10-17): plan a whole season at once

- **Series planning framework** (`docs/en/SERIES_PLANNING.md`): the formula every series needs (a one-line pitch, an axis, 3–5 fixed anchors, one song structure, one package, a card per episode), with everything else left free. Each step comes with options to pick from: seven axes, four song structures, five layers of anchors. Plus folder naming (`s{season}e{episode}_{title}`), per-episode steps and a pre-publish checklist.
- **Blank series template** (`examples/series_template/`): `research.md`, `style.md`, and per-episode skeletons for lyrics, cast notes and publishing copy.
- **`bokeh_still.py`**: blurs a lip-sync still's background. On a sharp painted background the model writes the lyrics into the scene as vertical text restore can't remove; on a blurred one the text drops to the bottom, where restore can clear it. The person is inpainted out before blurring, so there is no halo. Needs one extra segmentation model (see `models/README.md`).
- **Subtitles**: two vertical lines in a row no longer stack on the same side; in the vertical cut the columns sit closer to the edge, off the face (`epic.py`).
- Docs updated: LESSONS (background vs. garbled text, emotion-only lip-sync prompts, constraint sentences get drawn, `before clip start` from beat snapping), README, WORKFLOW, skill (new series section).

## 0.2.0 (2026-10-17): burned-in lip-sync captions, solved

On episode 5 《馬嵬》 every one of the 15 lip-sync clips came back with garbled captions burned in (white or gold; bottom, sides, vertical). Until now the only answers were cropping the frame or cutting away to another shot, and both hurt the picture or the performance. This release changes the workflow: <!-- public-ok -->

- **Captions are removed with AutoIP's video restore API.** `POST /videos/restore` with `source_video` + `operations[]=subtitle` (also `watermark` and `upscale`), 30 credits per 8-second segment. In practice a full line across the collar came out clean with the collar edge rebuilt; face and resolution untouched. Lip-sync clips are no longer cropped or re-cut around captions.
- **Lip-sync 3.0 (`engine=h3`).** No captions, tighter mouth and expression (a scream really opens the mouth), but 864×480 output. The docs say when it is worth it.
- **Lip-sync stills, settled: crop the portrait.** The semi-realistic portrait cropped straight to 16:9 at a different zoom per scene; no cut-out, no scene plate, no image-to-image. The detours (cut-outs with flat-cut arms and white halos, text-to-image half bodies with the wrong face, face swaps) are recorded in LESSONS.
- **Subtitles: `TYPO.hold`.** Clear a given line a set number of seconds after its last word, for a shout followed by silence.
- **Render: `EDITS[mode]["crop"]`.** The portrait and landscape cuts can crop differently.
- Docs updated: LESSONS (captions, stills, confirm voice attribution by ear, spell out the mouth in scream prompts), PROJECT_FORMAT, WORKFLOW, skill.

Series status: 《國風淒美對唱》 episode 1 《洛川》 is live, episodes 2–4 are finished, episode 5 《馬嵬》 (Emperor Xuanzong × Yang Guifei, dark K-pop ballad × metalcore) is in production. <!-- public-ok -->

## 0.1.0 (2026-10-15)

First public release: one `project.py` is one music video. Storyboard, AutoIP lip-sync and image-to-video, emotion-driven beat-synced editing, kinetic subtitles, render, thumbnails and publishing copy.

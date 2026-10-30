# Full workflow: from a script to a published episode

[中文](../../zh-TW/drama/WORKFLOW.md) | English

This page uses `projects/<series>/s1e01_<title>` as the example and writes `P` for that path. Run every command from the repo root. For a whole series (many episodes), read [SERIES_PLANNING.md](SERIES_PLANNING.md) first.

```
script ─┬─ 1 Script ───────────── 劇本_v1.md: opening hook, conflict, payoff, cliffhanger
        ├─ 2 Cast & sets ──────── character, set and prop stills → [review sheet: human approval]
        ├─ 3 Voice samples ────── one 5–15 s voice per character
        ├─ 4 Storyboard ───────── project.py SHOTS → storyboard.py (line length, references, credit estimate)
        ├─ 5 First-frame stills ─ first frames for lip-sync / image-to-video / keyframe shots → [review sheet: human approval]
        ├─ 6 Test shots ───────── one shot per character first: listen to the voice, check the look → [human approval]
        ├─ 7 Video ────────────── job review sheet → [credit estimate, human approval] → runner
        ├─ 8 QC ───────────────── broken files, cuts inside clips, is every line finished, frame checks
        ├─ 9 Edit ─────────────── EDITS: shot/reverse shot, reaction shots, L/J cuts, payoff, cliffhanger
        ├─ 10 Subtitles & sound ─ subtitle theme, character intro cards, music, sound effects
        ├─ 11 Render ──────────── render_ep.py → mp4 + srt
        └─ 12 Cover & publish ─── cover, title, description, hashtags
```

**Rule: AutoIP charges credits when a job is submitted, and there is no cancel API. Before every batch of jobs, show the review sheet and the credit estimate to whoever signs off.**

---

## 0. Project folder

```bash
mkdir -p projects/<series>
cp -r examples/drama/series_template/* projects/<series>/          # plan.md, style.md, characters.md, episode skeleton
mv projects/<series>/s1e01_title projects/<series>/s1e01_<title>
cp examples/drama/demo/project.py projects/<series>/s1e01_<title>/   # episode 1 starts from the demo; later episodes copy the previous one
```

- **Name the folder before the first AutoIP job.** Job files (`jobs/*.json`) store absolute paths, so renaming after submitting breaks resuming.
- The demo project keeps all its material inside the episode folder. For a whole series, put characters, sets, props and voice samples in the series folder instead (`projects/<series>/cast/` and so on) and write `../cast/A.png` in `project.py`, so every episode shares the same character sheet and the same voice. `sfx/`, `music/` and `fonts/` need no path changes: they are looked up in the episode folder first, then one level up.

## 1. Script

The story goes only in your own project (`projects/` stays out of git); the repo's examples and docs hold structure only. Write `劇本_v1.md` (format: `examples/drama/series_template/s1e01_title/劇本_v1.md`). Save revisions as `v2`, `v3`; never overwrite.

- An episode runs 1–2 minutes. **The first 3 seconds are the conflict**: don't open on the title, an empty shot or a self-introduction.
- Every episode has at least one payoff (爽點): a comeback, a reveal, a face-slap (打臉). The last 3–5 seconds stop on a cliffhanger (卡點): a question only the next episode answers.
- One line, one speaker. A multi-reference video can carry only one voice sample at a time, so **only one person speaks in each shot**; dialogue is built by cutting shot/reverse shot.
- Estimate each line at 4 characters per second: a 10 s shot holds at most 40 characters. Split a longer line in two, or use lip-sync (your own recording) instead.

Once the script is final, put the scenes in `project.SCENES` and the shots in `project.SHOTS`. The fields are in [PROJECT_FORMAT.md](PROJECT_FORMAT.md).

## 2. Character sheets, sets, props

Write the appearance descriptions in `CAST`, `SETS` and `PROPS` (in English; every generation reuses them). You can supply character images yourself (photos or art you have the rights to use), or write a `prompt` and let AutoIP draw them:

```bash
python drama/make_jobs.py P refs                    # characters without a file yet (those with a prompt or a base), sets, props
python dreamfab/aip_runner.py P/jobs/refs_jobs.json    # one at a time; can be interrupted and resumed
python drama/qc/sheets.py stills P/review_cast.jpg P/cast     # material shared by the whole series is in P/../cast
python drama/qc/sheets.py stills P/review_sets.jpg P/sets
```

Show the review sheets to whoever signs off. For any image they reject:
1. Move it to `rejected/` (don't delete it, so you can look up later why it was rejected).
2. Change `desc` or `prompt`.
3. Run `ONLY=A python drama/make_jobs.py P refs` to redo just that one.

- **One look per character**, and the whole arc uses the same character sheet. A costume change is a new image with a new key (e.g. `A_ARC2`).
- Set plates have no people in them: `make_jobs.py` adds "nobody in it" automatically.
- Character sheets: plain background, waist up, facing the camera.
- Multi-reference video often dissolves into the background of a character sheet. When a character plays a whole episode in one set, `python drama/restage.py cast/A.png sets/ROOM.png cast/A_room.png` cuts the person out and puts them into that set (face untouched, no credits), and that episode's `file` uses it. For headdresses, tassels and the like that the cut drops, a fifth argument keeps a ring of the old background: `... 3 70`. Needs `pip install mediapipe`; the segmentation model downloads on first use.

## 3. Voice samples

One clean voice per character (5–15 s, one person, no music).

**Let AutoIP voice them (default)**: in `CAST`, write `voice_line` (one line the character says, about 20–30 characters), `voice_how` (the tone), and set `voice_src` to `voices/raw/<KEY>.mp4`. `make_jobs.py P voices` runs image-to-video with sound from the character sheet as the first frame, and the character says the line; the model gives the face a voice that fits it. A character with no face (`file=None`) gets text-to-video instead, shown as `voice_who` (or `unseen`).

```bash
python drama/make_jobs.py P voices    # -> jobs/voices_jobs.json (480p, about 6 credits/s, 40-55 per character)
python dreamfab/aip_runner.py P/jobs/voices_jobs.json
python drama/voices.py P              # -> voices/<KEY>.wav: trim leading/trailing silence, cut low end, normalize level
```

Listen first: is it one person talking, is there music or effects under it, does the voice suit the face? If not, delete `voices/raw/<KEY>.mp4` and `voices/<KEY>.wav`, change `voice_how` and run it again. Once settled, the whole series uses that sample.

**Recording your own**: point `voice_src` at the recording (any format ffmpeg reads), with `voice_span` if needed, and run `voices.py P`. Use only voices you have the rights to: your own, actors who have agreed, or synthetic voices whose license allows it.
- A character without a voice sample may sound different in every shot.

## 4. Storyboard

```bash
python drama/storyboard.py P       # prints the shot list, warnings and a credit estimate for the video; writes storyboard.json
```

`storyboard.py` takes care of:
- References: the speaker, every `@KEY` in `act`, `cast`, `props`, and always the scene's set last; 6 at most.
- `@KEY` becomes `@圖片 N`, in the same order as the `images[]` sent.
- Every `SHOT` names the location (a multi-reference SHOT without one gets a grey studio background).
- In shots with a voice sample, gender words are taken out of the reference descriptions (the gender in a description overrides the sample's timbre).

Warnings to always read: a line too long (more than 4 characters per second), more than 6 references, a key that can't be found, a speaking character without a voice sample, two people in one still.

**Which shot type to use:**

| Shot | Use | Notes |
|---|---|---|
| Dialogue, reactions, several people in frame | `M` multi-reference video | The default. Generated straight from the character, prop and set references; the speaker says the line in their own voice, and the mouth is generated with it |
| Long lines, exact wording needed | `LS` lip-sync | First-frame still + your own recording of the line (`lines/<id>.wav`) |
| Empty shots, exteriors, cutaways | `I2V` image-to-video | The first-frame still comes to life, no speech |
| A door opening, transitions, A→B moments | `K` keyframe video | First frame to last frame, 6 / 10 / 15 s |

## 5. First-frame stills (LS, I2V, K shots)

```bash
python drama/make_jobs.py P kf
python dreamfab/aip_runner.py P/jobs/kf_jobs.json
python drama/qc/sheets.py stills P/review_kf.jpg P/kf
```

- First frames with a character are made with image-to-image from the character sheet; those without one use text-to-image.
- A lip-sync first frame must **already be talking** (mouth open): a still with a closed mouth and a calm face stares for 3–5 s before the mouth starts moving. The expression must also match the line's emotion.
- One person per still. Stills with two people in frame are hard to keep stable; use a multi-reference video instead.

## 6. Test shots

Before the full batch, shoot one `M` shot with a line for each character:

```bash
ONLY=S2_01,S2_02,S2_08 python drama/make_jobs.py P video
python dreamfab/aip_runner.py P/jobs/video_jobs.json
```

Listen: does the voice sound like the sample, did the description pull it to the other gender, is the line finished? Look: does the face match the character sheet, is the set right, did extra people appear? Fix any problem in `desc`, the voice sample or the line first, then send the batch.

## 7. Video generation

```bash
python drama/make_jobs.py P video                                   # prints the job count and credit estimate
python drama/qc/sheets.py jobs P/review_jobs.jpg P/jobs/video_jobs.json   # each job's references, line and prompt
python dreamfab/aip_runner.py P/jobs/video_jobs.json
```

Show `review_jobs.jpg` and the credits to whoever signs off, and run the runner only after they agree.

- The runner runs one job at a time (`AIP_MAX=1`). On a 429 it waits instead of resubmitting in a loop. Raise it if your account allows more; to raise it only off-peak, use `AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1`.
- For a batch that can wait, add `--off-peak`: the runner submits only in the half-price window (03:00–09:00 Taiwan time, every day) and waits the rest of the time (see SETUP.md).
- Files already downloaded are skipped. To redo one, move that file away (to `clips_rejected/`).
- Failed jobs are refunded automatically, and the runner retries up to 3 times.

**Optional: local super resolution + frame generation.** Off by default; whether to use it is your call. With an NVIDIA RTX GPU it can run while you wait for the clips:
- What you gain: 60 fps makes movement clearly smoother, and compression blocks are cleaned up.
- What it costs: 60 fps can look like TV or a live stream rather than film, and skin comes out smoother.

Compare one episode side by side before deciding. To use it, run this in a second window while the runner runs:

```bash
python drama/enhance.py P --watch      # each clip as soon as it is downloaded: NVIDIA 2x super resolution + 60 fps -> clips_hd/
```

- Add `fps=60, enhance=True` to `RENDER` in `project.py` and the render takes its picture from `clips_hd/`; the sound still comes from the original clip.
- Measured on an RTX 5060 Ti: a 5 s clip takes about 7.5 s (AutoIP takes about 3 minutes per clip), so an episode is ready about 20 s later than before; a 60 fps render takes 26 s (15 s at 25 fps).
- What it does: 60 fps makes movement clearly smoother; super resolution cleans up compression blocks and smooths skin, and after scaling back down to 1080 the picture is not much sharper.
- A reshot clip is newer than its `clips_hd/` copy and is redone on the next run. Installation: see SETUP.md.

## 8. QC

```bash
python drama/qc/clips.py P          # does each clip decode in full, its length, does it have sound, cuts inside the clip
python drama/speech.py P            # where each line sits in its clip, is it finished, is it the line in the script
python drama/qc/sheets.py strips P/review_clips.jpg P/clips/*.mp4
```

Always check for:
- `BROKEN`: only half downloaded. Delete the file and rerun the same job file; it downloads again from the same job, with no new generation.
- `CUT?`: the line runs right to the end of the clip and may be cut off. `TEXT?`: what was heard differs from the script (a missing or extra line). `SILENT?`: no sound. Listen to every one of these.
- A face changing, extra people appearing, the background turning into a grey studio, garbled text in the picture: check frames every second of every clip, and use only the clean seconds in the edit.
- `cuts`: a multi-reference video often cuts 2–4 times by itself within 8–10 s, so one clip can serve as several shots.

For fixes, see [LESSONS.md](LESSONS.md).

## 9. Edit

First generate a rough cut in script order, with each shot trimmed to just before and after its line:

```bash
python drama/edl_draft.py P            # prints EDITS; paste it into project.py and start editing
python drama/edl_draft.py P main       # shows the current edit expanded into seconds, and the total length
```

How to write the edit list:

```python
EDITS = {"main": dict(shots="""
    S2_01 auto flash intro=B         # src [in|auto] [dur] [flags]: one row per shot, placed after the previous one
    S2_03 auto zoom
    ^S2_04 0.8 1.0 @-1.0             # cutaway: picture only, the sound stays (reaction shots, L/J cuts)
    S2_08 auto zoom sfx=hit          # payoff: push in + sound effect
    S2_10 auto freeze=1.6 end        # cliffhanger: freeze frame + 「未完待續」
""")}
```

- `auto` (or just the id): trims to 0.15 s before and 0.35 s after the line, from `speech.json` (`RENDER.pad`); a shot without a line takes its first 2 s (`RENDER.hold`).
- All times are **the clip's own seconds**. The episode timeline is built by joining the rows' lengths.
- Editing principles (hook, shot/reverse shot, reaction shots, pacing, payoff, cliffhanger) are in [EDITING.md](EDITING.md).
- **NG reel**: before a reshoot, move the old take to `clips/_takes/<id>_v1.mp4` instead of deleting it. `speech.py` also transcribes what is in `_takes`. The NG reel is a video of its own: add a second edit `"ng": dict(suffix="_NG", music=[("theme", None, None, -20)], shots="""clips/_takes/S4_03_v1 0.4 4.2 black label=第3集NG花絮""")` to `EDITS` and `render_ep.py P ng` writes `<NAME>_NG.mp4`. The episode itself still ends on 「未完待續」. When the joke is what got said (the stage directions read out, say), add `heard` and the subtitle shows what was actually heard.

## 10. Subtitles, character intro cards, music, sound effects

- Subtitles: each line is split at punctuation into chunks of ≤14 characters (vertical) and timed to the per-character timings in `speech.json`. Font, size and position are in `TYPO`.
- Character intro cards: `intro=KEY` shows "title + name" at the start of that row (`CAST[k]["title"]`, `name`).
- Title card: `title` shows the drama's name + the episode number on that row. `label=前情提要` ("Previously on") puts a label in the top-left corner.
- Music: `MUSIC = [("tension", "S2_01", "S2_05", -18), ...]`, with the files in `music/`. The music drops automatically whenever there is dialogue (ducking). Start and end are a row id (its first appearance) or seconds. AutoIP can compose the music (`/voice/song`, 30 credits a piece, an empty `lyrics` gives an instrumental, 30–240 s); songs share the task slots with video.
- Sound effects: `sfx=hit` plays `sfx/hit.wav` at the start of that row.

While tuning subtitles, render the subtitles only, without video. You see the result in seconds:

```bash
python drama/qc/subprev.py P main P/subprev.jpg 0.9 2.5 9.0 21.0
```

Check: does any text cover a face, where the intro cards sit, does the title card block the opening conflict, when the cliffhanger text appears.

## 11. Render

```bash
python drama/render_ep.py P main
REUSE_BODY=1 python drama/render_ep.py P main        # only subtitles, music or sound effects changed: reuse the rendered picture
SUBST="S2_05:S2_02" python drama/render_ep.py P main # stand in another clip for a shot not generated yet, to check the pacing
```

- Outputs `P/out/<NAME>.mp4` and `.zh-TW.srt`.
- Sound: each row uses its own clip's sound (the dialogue and effects AutoIP generated); cutaways don't change the sound. Music sits under the dialogue, sound effects go on top, and the whole mix is normalized to −16 LUFS (`RENDER.lufs`).
- Deal with every `WARN` the render prints: `covers the start of` (a cutaway covers the next row's card or payoff), `asks for ... -> the last frame is held` (the clip is too short and will freeze).
- After rendering, spot-check frames: `python drama/qc/sheets.py video P/review_final.jpg P/out/<NAME>.mp4 1 5 10 20 30`

### Landscape version (16:9)

If the whole series is landscape, set `ASPECT = "16:9"`. For a landscape version of a vertical series, add `size` to an edit:

```python
EDITS["wide"] = dict(EDITS["main"], size=(1920, 1080), suffix="_wide", focus={"S2_08": 0.4})
```

`focus` is each clip's horizontal crop centre (0 = left edge, 1 = right edge, default 0.5). Vertical footage in a landscape frame gets enlarged and cropped, so use this mainly when the whole series is landscape to begin with.

## 12. Cover and publishing

See [PUBLISHING.md](PUBLISHING.md): vertical covers (`drama/thumbkit.py`, example in `examples/drama/demo/covers.py`), title, description, hashtags, the series playlist and AI disclosure.

## 13. Index and browse the series

As a series grows, its material spreads over every episode's `project.py`, `clips/`, `jobs/`, `speech.json` and `out/`, and the series folder's `cast/`, `covers/` and `youtube/`. `python drama/library.py serve <series folder>` indexes all of it into `<series folder>/library.db` (SQLite) and opens a page for this computer only (http://127.0.0.1:8765):

- Overview: one section per series title (season), every episode's cover, length, shot count, estimated credits and YouTube release time (covers in `covers/out/s2/ep01.jpg` or `covers/out/<episode folder>.jpg`; without one, the render's poster)
- Episode: the render and NG reel, each shot's line / what was heard / match / clip, the edit, replaced takes
- Cast (every look and every per-set version, voice samples), sets, files (by kind), jobs and credits, YouTube details
- Search over lines, characters, titles and file names

Standard library plus ffprobe / ffmpeg only. While `serve` runs it checks every 15 s and re-indexes in the background when files change (`index` builds without serving, `--no-index` skips the first build); durations and thumbnails are cached, so later runs take seconds. Credits are estimated from the job files, and a reshot clip counts only its last run. `library.db` also opens in any SQLite tool.

---

## Cost reference

These are the prices from `GET /api/v1/pricing` on 2026-10-27; current prices may differ. `make_jobs.py`, `storyboard.py` and `qc/sheets.py jobs` all estimate from this table (`PRICE` in `drama/common.py`).

| Job | Credits |
|---|---|
| Text-to-image | 10 (`v3`, standard); `v4` 20 |
| Image-to-image | 15 |
| Lip-sync 2.0 (≤31 s) | 50; lip-sync 3.0 480p 50, 768p 75 (audio ≤20 s) |
| Image-to-video 768p | 15 per second (5 s 75) |
| Multi-subject reference video 768p | 5 s 80, 6 s 115, 7 s 145, 8 s 170, 9 s 225, 10 s 265 |
| Multi-subject reference video 2k | 5 s 95, 6 s 115, 8 s 150, 10 s 195 |
| Keyframe video | 8 per second (6 s 48) |
| Video restore (caption removal) | 30 per 8 s |
| Voice clone | 50 |

- Multi-reference 768p is not priced in proportion to length: every second past 5 costs much more. Keep a line within 5 s when it fits.
- This is an estimate before submitting; audit what was actually spent with `dreamfab/credits.py P/jobs`.

The demo project (1 minute, 11 shots): about 870 credits of video and about 50 of first frames; character sheets and sets are shared by the whole series, about 60. Retakes are extra. To save credits:
- Shoot test shots first, and send the batch only once the voices and looks are settled.
- 5 s is enough for reaction shots and cutaways; one multi-reference video can often be cut into several shots.
- For a recap, use clips from the previous episode directly (`../s1e01_x/clips/S2_08`) instead of generating new ones.

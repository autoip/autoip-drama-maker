# Lessons learned

[中文](../zh-TW/LESSONS.md) | English

Every item here is a problem hit while making real MVs. Each one is handled in code or in the workflow; the file responsible is in parentheses.

## Generation: general

- **Credits are charged on submit, and there is no cancel API.** Once a job is submitted it can't be stopped, so gate before submitting:
  - Generate stills first and build a review sheet (`qc/sheets.py`).
  - Group shots, new characters and changed prompts always get a still review before the video job.
- **Failed jobs are refunded automatically.** The runner retries failed jobs, up to 3 times (`aip_runner.py`).
- **Concurrent job limit.** A regular account can run only 1 job at a time; going over returns 429 `concurrency_limit`.
  - The runner defaults to `AIP_MAX=1`. On a 429 it waits for the running job to finish instead of resubmitting in a loop.
- **The "2k" video option is actually worse.** In testing, 2k produced only 864×480 for 288 credits. 768p produces 1344×768 for 75 credits.
- **Whatever is in the image-to-image source ends up in the result.** For example, if the source has a piano, the organist keeps playing a piano no matter how you change the prompt.
  - Fix: redo that still with text-to-image, describe concrete parts in the prompt ("four manuals, rows of stops, giant pipes behind") and add `no piano`.

## Lip-sync

- **The last ~0.2 s often has a white smear.** The render never uses the last 0.35 s (`RENDER.tail_guard`).
- **The mouth may be idle for the first few seconds, and the shot may zoom out to full body mid-clip.**
  - Use `qc/mouth.py timeline` to find the usable span.
  - In the edit, use only the seconds where the mouth moves and the face is large enough; fill the rest with a lip-sync of the same passage from another scene.
- **Captions are occasionally burned into the picture.** Crop them out with `RENDER.crop`, e.g. `crop=1024:576:180:0`.
- **The output audio doesn't always start where you asked.** `qc/align.py` cross-correlates onsets to find the actual start. The render computes offsets from it so the mouth stays in sync with the song.
- **With two lead singers, never send the full vocal track.** If you do, both singers' mouths move on every line.
  - First mark each voice's spans with `voice_probe.py`, then split into two tracks with `split_voices.py` (50 ms fades, −36 dB floor on each track).
  - Each lip-sync job only gets its own track.
- **Each job is limited to about 30 seconds.** Split long passages into several jobs; generate 2–3 different scenes for the same audio and alternate between them in the edit.

## Image-to-video (I2V)

- **Parchment, documents and signs often sprout garbled text.**
  - In the image prompt write "completely blank ... with no writing".
  - In the video prompt add "no text anywhere in the frame".
  - If text still appears, use only the clean early part of the clip.
- **Characters can swap faces mid-clip.** For example, the drummer turns into someone else after 1.5 s.
  - Check with frame grabs from `qc/sheets.py video`.
  - In the edit, use only the seconds before the swap (`start src offset`, keep the segment short).

## Group shots

- **Multi-subject reference video tends to make people shorter, childlike, or shrink them into a wide shot.** Prompting "tall, waist-up" doesn't help much.
- **Fix: compose the frame yourself.** The `group_still.py` flow:
  1. Crop each member's head and chest and lay them out side by side as a collage.
  2. Run image-to-image at strengths 0.85 / 0.92, adding "mature adults around thirty, sharp jawlines, low angle, waist-up" to the prompt and "childlike, baby face, chibi, full body" to the negative.
  3. Pick the final still by hand, then run regular image-to-video.
- Below a strength of about 0.8 the collage seams remain visible.
- During review, specifically check whether anyone looks like a child.

## Subtitles (libass / ASS)

- **Within one event, the first `\pos` or `\move` wins; later ones are ignored.** To move a shape:
  - Don't put a `\pos` before the `\move`.
  - `epic.shape()` omits `\pos` automatically when it sees `\move`.
- **Variable fonts render only the default weight.** Asking for Black still gives Regular or Light.
  - Fix: cut a static weight with `make_static_font.py` and use a new family name.
- **libass font sizes differ from what PIL measures.** Multiply by `font_scale` (about 1.45 for Noto Serif TC); after changing fonts, calibrate with `subprev.py`.
- **ffmpeg `drawtext` crashes on some Windows builds because of fontconfig.** Review sheet labels are drawn with PIL instead (`qc/sheets.py`).
- **The title card must not cover the lead singer's face.** After slamming in on the climax downbeat, the title should shrink to the top edge within about 1.4 s; if the singer is in the upper part of the frame, change the shot.
- **Rhyme readings must follow the lyricist's own annotation.** Don't derive dictionary readings yourself. For example, the lyricist marks 乾杯 ("cheers") as "(pe)", while the dictionary reading is kan-pue.
- **Preview subtitles separately from the final render.** A subtitle-only preview takes a few seconds; a full render takes several minutes.

## Speech recognition

- **For Taiwanese Hokkien, screamed vocals and dense mixes, ASR text is nearly useless, but the timings are usable.** Approach:
  1. Use the full lyrics as `initial_prompt`.
  2. Recognize only the spans that have vocals, with `condition_on_previous_text` turned off.
  3. The subtitle engine uses difflib to match lyric characters to ASR characters; unmatched characters are spread evenly between line start times.
- Line start times must be checked by hand.

## Editing and rendering

- **The full and short EDLs were once mixed up.** The short EDL produced a 70-second "full version".
  - The edit list is now resolved from `project.EDITS[mode]` at render time; there is no intermediate file.
- **When a clip is too short:**
  - Regular clips can be slowed down with `setpts`; up to 1.8× still looks natural.
  - Lip-sync clips must not change speed or the mouth goes out of sync; freeze with `tpad` instead.
- **Cut points snap to beats within 0.08 s.** Beyond that the original time is kept — it's usually a deliberate off-beat cut.
- **Photorealistic AI people require platform disclosure.** Keep real people and party names out of thumbnails, titles and tags — especially for political satire.

## Tooling

- On Windows, Python strings containing `\\` or `\n` written via a bash heredoc are easily mangled. Write patch scripts to a file and run that instead.
- Each job folder's `*.state` files record the task uuids; `credits.py` uses them to total how many credits each project actually spent.

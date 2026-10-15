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
  - Or use only a face close-up as the source so the model draws the instrument itself; or start from a still of the same kind that already worked in another project and run it at low strength (about 0.6) to change only the background.
- **Image-to-image inherits the source's art style.** To switch a whole episode to another style (e.g. semi-realistic to gongbi painting), first redo the character sheets in the new style, then build every character shot from them.
  - Image-to-image only offers standard / hd_4k; style modes such as text-to-image `v3` aren't available, so the style has to come from the character sheet.
- **Padding a portrait character sheet to 16:9:**
  - With blurred side fill, strengths below 0.8 give back "portrait + blurred bars" and the scene never changes.
  - Fix: crop head to chest only, fill the sides with a mirrored copy, and run image-to-image at about 0.9.
  - **Never mirror-pad a full-body figure**: the mirrored copies get painted as two more people. For full-body shots use a blurred empty plate of the same scene as the background, or go text-to-image.
- **Extending a head-to-waist crop into a full body gives a big head and short legs.** The head size is locked by the source.
  - Full-body shots need a full-body reference; write "tall, long legs, heroic proportions" and add "short legs, stubby body, big head, chibi" to the negative.
  - `muscular` often comes out shirtless or bare-armed; write "powerfully built, fully covered in armor" and add "bare arms, bare chest" to the negative.
- **Text-to-image gets the composition right but drifts the character's look.** E.g. the Peking-opera Hegemon grows a long black beard and the white face paint turns red; `beard` in the negative doesn't stop it.
  - Fix: paste the locked character's head (face paint plus helmet) over the head in the frame with a feathered ellipse mask, then blend with image-to-image at about 0.45.
  - When the original beard is much larger than the face, pasting can't hide it; blurring it or cloning nearby texture over it leaves marks. Pick a composition that has no long beard to begin with, then paste the head.
- **Two characters in one still is hard.** A two-sheet collage run through image-to-image keeps its seam; text-to-image drifts both faces. Use multi-subject reference video with the character sheets and skip the still.
- **Mirrors grow a second face.** A "rouge in front of a mirror" shot often paints another frontal face in the reflection. Angle the mirror away so it only reflects candlelight, and add "face in the mirror, two faces" to the negative.
- **Fine hand poses can't be done in a still.** "Reverse grip, blade against her neck" came out as a forehand grip four times. Shoot the still holding the sword with eyes closed, and put the reverse-grip move into the image-to-video prompt.
- **With NSFW enabled on the account, text-to-image can produce nudity.** "The Hegemon cradling the lifeless Consort Yu" produced a nude figure. Add `nude, nsfw` to the negative of every character prompt, and look at every image before moving on.

## Lip-sync

- **The last ~0.2 s often has a white smear.** The render never uses the last 0.35 s (`RENDER.tail_guard`).
- **The mouth may be idle for the first few seconds, and the shot may zoom out to full body mid-clip.**
  - Use `qc/mouth.py timeline` to find the usable span.
  - In the edit, use only the seconds where the mouth moves and the face is large enough; fill the rest with a lip-sync of the same passage from another scene.
- **Garbled captions are often burned into the bottom of the picture.** Crop them out with `RENDER.crop`, e.g. `crop=1024:576:180:0`. They don't always cover the whole clip, so check the bottom of every lip-sync clip in frame grabs.
- **The output is often 0.2–0.6 s shorter than requested.** E.g. 22 s requested, 21.8 s delivered; 29.5 s requested, 28.9 s delivered.
  - Lay out the edit from `dur` in `align.json`, not from the length you submitted.
  - `WARN ... short by ... -> freeze tail` in the render log means that shot freezes, which looks like a glitch. Always fix the edit, e.g. let the previous B-roll shot run longer.
  - `WARN ... before clip start` means the lip-sync starts from the wrong point and the mouth won't match. Fix that too.
- **The source still's expression carries through the whole lip-sync.** A still with an open-mouthed grin, sung over a sad passage, looks like laughing the entire time. Pick a still whose expression already fits the passage; "smiling, grin" can go in the negative.
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
- **If the shared `MOTION_PREFIX` names characters or props, the model puts them into every clip.** With "the Hegemon and Consort Yu, Chu banners" in the prefix, an empty warhorse shot sprouted banners and people after 2 s, and Yu Ji putting on armor turned into a different woman after 1 s.
  - Keep the prefix to the art style only — no characters, no props.
  - Start each clip's prompt with "one continuous shot, no cuts, the same person and the same face throughout".

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
- **Screamed passages may not yield even timings.** Use the nearest recognized line starts before and after as anchors, spread the lines in between evenly, and fine-tune after watching the render.

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

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
  - A very different style (e.g. an ancient handscroll in the manner of Gu Kaizhi's "Nymph of the Luo River") can't be reached even by image-to-image: at strength 0.75 it was still the original gongbi. Redo those shots with text-to-image and describe the characters very concretely (which half of the face the mask covers, the shape of the crown).
- **Padding a portrait character sheet to 16:9:**
  - With blurred side fill, strengths below 0.8 give back "portrait + blurred bars" and the scene never changes.
  - Fix: crop head to chest only, fill the sides with a mirrored copy, and run image-to-image at about 0.9.
  - **Never mirror-pad a full-body figure**: the mirrored copies get painted as two more people. For full-body shots use a blurred empty plate of the same scene as the background, or go text-to-image.
- **The still's expression decides whether the first seconds are sung.** A calm, closed-mouth portrait cropped straight to 16:9 gives 3–5 s of that calm face staring (MediaPipe jawOpen near 0) before the mouth starts moving; a still that already sings (image-to-image with "singing with mouth open") sings from the first frame. On 《馬嵬》 every female lip-sync went back to the open-mouth stills.
  - Always run `qc/mouth.py P edl full` before rendering; cut away from `IDLE?` windows to B-roll, or start the shot where the mouth really starts (`qc/mouth.py P timeline LS04` shows the opening every 0.5 s).
  - The old problem with open-mouth stills is framing: a bust cut out onto a plate is narrower than the shoulders, so the arms end in a straight line. You need both the singing expression and complete shoulders.
  - Rejected on 《馬嵬》: a full-body cut-out on a plate (white halo), text-to-image half bodies (wrong face), pasting the old face onto a new body.
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
- **Garbled captions are burned in often: bottom, sides, vertical, white or gold to match the scene.** Remove them with AutoIP's video restore API: `POST /videos/restore` with `source_video` + `operations[]=subtitle` (30 credits per 8 s segment). Resolution is kept and the face is untouched; on 《馬嵬》 a full line across the collar came out clean with the collar edge rebuilt.
  - Don't crop or re-cut around captions: cropping costs resolution and swapping shots breaks the performance. Keep `RENDER.crop` for a small line in a corner when you don't want to spend credits.
  - Never write "no text / no subtitles" in the prompt: those batches had captions in 15 of 15 clips; prompts that only describe the performance and camera, about half.
  - Captions often last only a few seconds: grab one frame a second per clip, not just head / middle / tail.
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
- **The portrait image must be under 10 MB.** Image-to-image hd_4k output often isn't, and the job is rejected (no credits charged). Resize to 1920×1080 before submitting and keep the original.
- **Garbled text isn't always at the bottom; it can sit right next to the face.** Those can't be cropped out and used to mean a regeneration; now they go to restore like the rest.
- **Lip-sync 3.0 (`engine=h3`) burns no captions and syncs mouth and expression better** (a scream really opens the mouth and bares teeth), but outputs 864×480; restore's `upscale` only sharpens, it doesn't raise the resolution. Use 2.0 (1280×704) + subtitle removal for the picture, and consider 3.0 for shots where the performance matters more than resolution.
- **The background decides where the garbled text goes.** On a sharp gongbi landscape the model writes the lyrics as vertical brush calligraphy in the sky. Restore's `subtitle` only clears text in the lower part of the frame, and `watermark` doesn't clear vertical text at the sides either. In one MV painted in gongbi style, 13 of the first 15 clips came out like that.
  - Fix: keep the person and expression, and blur only the still's background into a shallow depth of field. The text then drops to a bottom line, which restore removes. Only about a third of the takes have bottom text or none, so generate several rounds per clip and pick, for each lyric line, the take that is clean and has a moving mouth. Blur with `bokeh_still.py`.
  - Inpaint the person out before blurring the background, or a sharp ring of background stays around them and looks like a cut-out halo. Erode the body mask by a few pixels, and use a looser mask for the head (topknot, crown) or it gets eaten.
- **Write only the emotion in the prompt, plus 「鏡頭穩定」 (steady camera).** Takes whose prompt described the scene ("singing under the tree…") kept zooming out to full body and grew props (a microphone appeared in a hand). In quiet passages the mouth barely moves; add 「清楚咬字，每個字嘴巴明顯張合」 (articulate clearly, mouth visibly opening on every word).
- **Spell out what the mouth does for screams and wails.** "screaming in despair" produced a frown with the mouth shut; "mouth wide open, screaming hard, teeth showing" opened it.
- **Confirm voice attribution by ear.** On 《馬嵬》 the timbre classifier called the second half of chorus 2 (2:40–2:53) female; it was male. When two singers trade the same melody, pitch can't tell them apart: ask the user instead of guessing.

- **Lip-sync 3.0 zooms in on its own, and the API has no camera parameter** (only image, audio, prompt, aspect ratio, audio start/duration, engine, resolution). Measured with `qc/zoom.py` over 29 clips from 3 projects: 14 stay framed, 5 jump to an extreme close-up within 2 s (the face goes from 16% of the frame width to 50–72%), 7 push in gradually from 2–6 s (1.7–2.9×), 3 push only in the last seconds. The same still and the same prompt can give either outcome.
  - **A concrete camera instruction in the prompt helps**: "a locked-off medium close-up, the person framed from the chest up the whole time, singing steadily" instead of "steady camera". On one 20 s line the old prompt pushed to 2.94× and a re-roll to 1.96×; the new prompt stayed at 1.10×. On the other lines of that song, 3 of 4 stayed within 1.35×. It is not a guarantee: one line that was steady before pushed to 1.9×.
  - **Don't follow the camera instruction with dramatic emotion words**: same audio, same still: "locked-off… singing steadily" 1.00×, "locked-off… singing powerfully, fierce eyes" 1.82×.
  - **Shorter audio does not help**: a 20 s line cut into two 10 s takes; the second pushed to 1.73× from 4 s.
  - **A wider still is a safety net**: a still with the face at ~11% of the frame width still pushed 1.5×, but it ended at a normal medium close-up instead of a face filling the frame. The cost is a smaller mouth.
  - A take that pushes is still usable up to `push@`; for an important line, make two takes and keep the steady one. (Testing in progress in 2026-10 with few samples; the numbers will be updated.)

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
- **Even with a clean prefix, extra people often appear in the second half of a clip.** In one batch of 27 for 《帷影》, 7 did: another emperor after 1–3 s, an unmasked woman beside a screen, a mask turning into Peking opera face paint. Check every clip second by second (not just start, middle and end), note the usable seconds in the EDL comments, and use only the front part.
- **A shadow counts as a person.** Viewers read a figure on a paper screen or a shadow on the wall as a second person. When the story calls for one person only, don't ask for screens or cast shadows, and add `shadow, silhouette on screen` to the negative.
- **Constraint sentences in the description get drawn.** Story clips whose prompt said things like 「沒有任何人」 ("nobody at all") got a giant hand reaching into frame, or those very words burned in at the bottom. Describe only what should be seen.

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
- **Clear a shout early when silence follows.** A line normally stays until the next line arrives, so 「賊本尚在」 hung on for 9 s into the female wail. `TYPO.hold={"賊本尚在": 1.4}` burns that line away 1.4 s after its last word.
- **Five seconds is enough for the prologue title.** By default it stays until the prologue ends, which with a 40-second prologue felt far too long to the user. Set `TYPO.intro_title_s=5` and `title_step=1` (one character per beat). Don't add an episode card unless the user asks for one.
- **Rhyme readings must follow the lyricist's own annotation.** Don't derive dictionary readings yourself. For example, the lyricist marks 乾杯 ("cheers") as "(pe)", while the dictionary reading is kan-pue.
- **Two vertical lines in a row stacked on the same side.** The next line was laid out on the edge where the previous one was still burning away. `epic.py` now moves a consecutive vertical line to the other side; in a portrait frame, which is mostly face, the columns sit 120 px from the edge (190 px in landscape).
- **Preview subtitles separately from the final render.** A subtitle-only preview takes a few seconds; a full render takes several minutes.

## Speech recognition

- **For Taiwanese Hokkien, screamed vocals and dense mixes, ASR text is nearly useless, but the timings are usable.** Approach:
  1. Use the full lyrics as `initial_prompt`.
  2. Recognize only the spans that have vocals, with `condition_on_previous_text` turned off.
  3. The subtitle engine uses difflib to match lyric characters to ASR characters; unmatched characters are spread evenly between line start times.
- Line start times must be checked by hand.
- **Screamed passages may not yield even timings.** Use the nearest recognized line starts before and after as anchors, spread the lines in between evenly, and fine-tune after watching the render.
- **In slow chanted passages with long notes, ASR word times can be half a second to over a second off.** The user felt the lyrics "couldn't keep up". Find each phrase onset from the vocal track's RMS in 0.25 s steps and rewrite that stretch of `words.json` directly (back it up first).

## Editing and rendering

- **The full and short EDLs were once mixed up.** The short EDL produced a 70-second "full version".
  - The edit list is now resolved from `project.EDITS[mode]` at render time; there is no intermediate file.
- **When a clip is too short:**
  - Regular clips can be slowed down with `setpts`; up to 1.8× still looks natural.
  - Lip-sync clips must not change speed or the mouth goes out of sync; freeze with `tpad` instead.
- **The portrait and landscape cuts can crop differently.** `EDITS[mode]["crop"]` is merged over `RENDER["crop"]`; the narrow portrait window never reaches text at the sides, so it need not share the landscape crop.
- **Cut points snap to beats within 0.08 s.** Beyond that the original time is kept — it's usually a deliberate off-beat cut.
  - A lip-sync shot's cut point snapped earlier can land before the clip starts, and the render prints `WARN ... before clip start`. Move that cut point slightly later so it doesn't snap.
- **Photorealistic AI people require platform disclosure.** Keep real people and party names out of thumbnails, titles and tags — especially for political satire.

## Publishing (YouTube API)

- **The API's description limit is 5,000 bytes, not 5,000 characters.** A CJK character takes 3 bytes, so a description with lyrics, sourcing and an English paragraph easily reaches 7,000+ bytes and is rejected. Write an API version: keep the lyrics and chapters, shorten the sourcing, and put the full notes in a pinned comment.
- **One Google account can own several channels.** The first login picked the wrong one without anyone noticing, and the videos went to another channel. After logging in, read the channel name the script prints, then lock it with `YT_CHANNEL_ID`.
- **Check what the channel already has before uploading.** Some videos had already been uploaded by hand in Studio; uploading from the SEO file again would have duplicated them. The script now compares the 《title》 of the latest 50 uploads.
- **A Short's thumbnail set through the API is accepted but stored as 16:9 (blurred sides), and the Shorts shelf does not use it.** Upload Shorts thumbnails in Studio on a computer, as before.
- **"Altered or synthetic content" (`containsSyntheticMedia`) can be sent but not read back**: `videos.list` never returns the field. Confirm it in Studio.
- **Run in the background, the login flow may not open a browser.** Give the printed URL to the user to open on the same computer; it is only valid for that run.

## Tooling

- On Windows, Python strings containing `\\` or `\n` written via a bash heredoc are easily mangled. Write patch scripts to a file and run that instead.
- Each job folder's `*.state` files record the task uuids; `credits.py` uses them to total how many credits each project actually spent.
- After changing `project.SECTIONS`, rerun `storyboard.py`. Rendering reads `storyboard.json`; without a rerun the old section times stay and the title card lands on a face.
- When a job file's `files` use relative paths, start `aip_runner.py` from inside the project folder. Started from the repo root it cannot find the images and every submit fails; don't grep-filter the runner's output, or you won't see the error.

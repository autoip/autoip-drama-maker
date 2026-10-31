# Explainers `explain/` (說)

Turn the history and legend behind a music video into a 3–6 minute landscape YouTube explainer: one narrator, thirty-odd paintings, the MV's instrumental as the bed, subtitles that follow the voice. The pictures are stills (static B-roll) with smooth pans and zooms, no video jobs, so it is cheap: about 1,000 credits for a 5-minute episode at full price, about half off-peak.

**Every episode ships in two versions**: wide (the 16:9 episode) and vertical (a 9:16 Short under 60 seconds). The Short is cut from the same narration, pictures and music at no extra credits, and its "Related video" sends viewers on to the episode.

[中文](../../zh-TW/explain/OVERVIEW.md) | English

## One episode's folder

```
projects/<series>/
  voices/NARRATOR.wav        the narrator's voice sample (shared by the series)
  music/<song>_inst.flac     the MV without vocals (optional)
  fonts/ExplainerSerif.ttf   subtitle font (a static weight, see below)
  e01_<topic>/
    project.py               every setting of the episode
    script.md                the script: one ### per chapter under ## Narration
    jobs/  voice/  images/
    out/NAME.mp4             wide (16:9) + NAME.zh-TW.srt
    out/NAME_shorts.mp4      vertical (9:16 Short) + NAME_shorts.zh-TW.srt
```

Example: [examples/explain/demo](../../../examples/explain/demo/) (every field commented).

## Steps

Every batch that costs credits is quoted at full and off-peak price first and waits for a yes.

1. **Script** `script.md`: under `## Narration` (or `## 旁白`), one `### heading` per chapter. The first chapter is the opening; the title (`TITLE`) comes up after it. Five minutes is about 1,400 Chinese characters.
2. **The narrator's voice** (once per series): make a narrator say one line with text-to-video (put accent and manner in the line's direction, e.g. Taiwanese Mandarin, soft, like late-night radio), then take the voice out as a 5–15 s sample. Nobody has to record anything. The voice-clone API has no accent setting: the accent comes entirely from the sample.
3. **Narration**:
   ```bash
   python explain/narration.py P jobs          # parts of <= 1,100 characters split between chapters (the API takes 1,200), 50 credits each
   python dreamfab/aip_runner.py P/jobs/voice_jobs.json [--off-peak]
   python explain/narration.py P check         # speed, words to listen to, a missing ending, a voice that loops
   ```
   - Words the voice tends to misread go in `SAY`: replaced by common characters of **the same length and sound** (宓妃→伏妃, 曹叡→曹銳, 二二〇→二二零). The subtitles keep the original.
   - `check` compares script and transcript by pinyin, so homophones never raise an alarm. What it lists sounds different; your ears have the last word.
   - Long parts sometimes **loop at the end**, repeating the last sentences. `check` says from which second. Cut it with `narration.py P cut voice/part2.flac SECONDS`, have the missing sentences read as a short extra part, and list both in `NARRATION`.
4. **Pictures**:
   ```bash
   python explain/make_images.py P            # every picture without a file yet -> jobs/images_jobs.json, 20 credits each in v4
   python dreamfab/aip_runner.py P/jobs/images_jobs.json [--off-peak]
   ```
   AutoIP text-to-image v4 is **MOSS-Image**. Write prompts the way its [prompt enhancer](https://github.com/OpenMOSS/MOSS-Image/blob/main/skills/moss-image-prompt-enhancer/SKILL.md) does:
   - **Caption**: cohesive English prose covering subject and action, appearance, setting, camera and framing, medium, lighting, palette and mood. No strings of tags like "8k, masterpiece, highly detailed". Quote any words that must appear in the picture exactly. Write `LOOKS` as a prose paragraph too; it is appended to each caption.
   - **Layout** (a cover with its title, panels, objects in given places): put a dict straight into `IMAGES`, with:
     - the canvas `width`/`height`: multiples of 16 and the size the job comes out at (v4's 960x540 returns 1312x736)
     - a `summary.caption`
     - flat `items`, each with a `label`, a `caption`, a pixel `bbox` [x1,y1,x2,y2] and, for text, its `text`

     `make_images.py` compiles it to the one-line JSON MOSS-Image reads, identical to the official compile_prompt.py.
   - Always look at a review sheet before submitting. Models draw things that do not belong, such as a modern map in a Three Kingdoms war tent. Check both before submitting and before the final render.
5. **Music and an MV clip**: take the vocals out of the MV with demucs (`python -m demucs --two-stems=vocals -n htdemucs ...`). `CH_MUSIC` gives the second each chapter starts from: the intro for the opening, the chorus for the story's climax, the quiet verse for a sad chapter. Each section is levelled automatically and ducked under the voice. To end on the MV, point `MV_CLIP` at the MV file and add `("MV:8.5", "first words", None, None)` to `SHOTS`; it plays in a gold frame with room for subtitles below.
6. **Render** (no credits):
   ```bash
   python explain/sub_styles.py P                                  # subtitle looks side by side for the user to pick
   python explain/render.py P --until "first words of chapter 1"   # a 30-second test cut first
   python explain/render.py P                                      # out/NAME.mp4 + .srt, then the Short out/NAME_shorts.mp4 (step 9)
   ```
   Each `SHOTS` item is (picture, the words it comes in on, move, focus). The moves:
   - `in`/`out`: zoom towards or away from the focus
   - `left`/`right`: pan
   - `frame`: the whole picture in a gold frame, for covers with lettering
   - `scroll`: a handscroll drawn on white, cut out and panned right to left

   Subtitles, picture changes and chapter labels all follow the narration's timing.

   **The user picks the subtitle look**: `sub_styles.py` sets the 4 looks (white with a thin dark edge, ivory with a thick dark-brown edge, plus a gold rim, a soft dark band) in every font in `FONT`'s folder on the episode's lightest and darkest pictures, one sheet (`out/subtitle_styles.jpg`). Show it, then write the pick into `project.py`, e.g. `SUBS = dict(style="band", font="DFKai-SB", size=66)` (the band with DFKai-SB, Windows' `kaiu.ttf`, which you copy into fonts/ yourself). Without `SUBS` it is white with a thin dark edge. On light paintings (gongbi, ink) the band reads best.
7. **Cover**: use `mv/thumbkit.py` with pictures from the episode and big lettering (see `examples/mv/demo/thumbs.py`), or have v4 paint the cover with its title through a Layout in `IMAGES`.
8. **Publish**:
   ```bash
   python mv/youtube_upload.py P --title A --category 27 --dry-run   # 27 = Education; reads YouTube_SEO.txt and project.py's NAME/EDITS/RENDER
   python mv/youtube_upload.py P --title A --category 27             # private by default: check it in Studio, then publish
   python mv/youtube_upload.py P --shorts --category 27              # the Short, private too; {full} in its description becomes the episode's link
   ```
   - Put the MV link on the first line of the description. Copy the chapter times render.py prints; each chapter must be at least 10 s.
   - Manage playlists with `dreamfab/youtube_playlists.py`.
   - The API cannot comment on a private video: post the pinned comment after publishing, then pin it from the comment's ⋮ menu.
   - Studio's "Related video" exists only for Shorts. A long video links to the MV through its end screen and cards, which become available once processing is done.
   - Every step after the upload goes into the publishing log: the uploader records the upload, captions, thumbnail, playlist and updates; what is done by hand in Studio is added right after, e.g. `python dreamfab/youtube_log.py add VIDEO end_screen "MV + subscribe"`, `... card "4:40 watch the MV"`, `... pin`, `... publish`. The episode page lists the log, and its card shows publish, end screen, card and pin.
9. **The vertical Short: every episode** (no credits): once the wide cut is final, write `SHORTS` in `project.py`; from then on `render.py P` renders both (vertical 1080x1920; `--full-only` renders the episode alone, `--shorts` the Short alone).
   ```bash
   # a series' first episode: one of each layout side by side for the user; the pick goes in SHORTS["layout"] and later episodes copy it
   python explain/render.py P --shorts --layout band   --out out/_layout_band.mp4
   python explain/render.py P --shorts --layout square --out out/_layout_square.mp4
   python explain/render.py P                          # wide + vertical
   python mv/youtube_upload.py P --shorts --dry-run    # reads the Shorts title line and the Shorts description in YouTube_SEO.txt
   ```
   - `SHORTS = dict(clips=[("from these words", "up to these words"), ...], head=("line at the top",), end="closing line", layout="square")`. A cut that works: the opening's hook, the most dramatic passage or two, and the MV's line or the closing question. Each clip runs from its first words up to (not including) the second ones (`None`: to the end of that audio file); the picture that is up where a clip starts comes in with it, and the closing MV clip meets the music where the full cut does.
   - Length: YouTube treats any vertical or square video up to 3 minutes as a Short, but a Short over 1 minute with any copyright claim (Content ID included) is blocked everywhere. Stay under 60 seconds, about 240 characters of narration.
   - The user picks the layout: `band` puts the whole 16:9 picture across the middle on a blurred copy of itself; `square` takes the middle square of each picture, much larger on a phone, with the subtitles over its lower edge (keep the head to one line). Both keep clear of the Shorts title and buttons at the bottom.
   - Every `YouTube_SEO.txt` carries the Short's copy too: a line "1 分鐘直式版（Shorts）標題：" with its title (ending in `#shorts`) in the titles block, and a "Shorts 說明欄" section: one hook line, `完整解說：{full}`, the MV link, tags.
   - After the upload, set the episode as the Short's "Related video" in Studio (a Shorts-only field) and log it: `youtube_log.py add SHORT link "related video -> EPISODE_ID"`. Shorts stay out of the episodes' playlist.
10. **Library**: after `python dreamfab/library.py serve projects`, an explainer series is at `http://127.0.0.1:8765/files/<series>/`: one card per episode showing how far it is along, and an episode page with the cut and its chapters, the covers, every picture with its note, the narration, the script and the YouTube copy. Add `?raw` for the plain file listing.

## project.py

| Field | Meaning |
|---|---|
| `LINE = "explain"` | the library serves the folder as plain files |
| `NAME`, `RENDER`, `EDITS` | output name, subtitle language; `EDITS` is for the uploader |
| `SCRIPT`, `VOICE` | the script, the narrator's sample |
| `SAY` | (written, spoken) pairs of the same length |
| `NARRATION` | optional: which audio files play (after a cut or a re-read) |
| `TITLE`, `ENDCARD` | the title after the opening (title, subtitle); the closing AI-made card |
| `FONT` | (font family, folder): `python dreamfab/make_static_font.py NotoSerifTC-VF.ttf 600 "Explainer Serif" fonts/ExplainerSerif.ttf` |
| `SUBS` | the subtitle look: `dict(style=..., font=family, size=58)`, picked by the user from `sub_styles.py`'s sheet (step 6). `style`: `outline` white with a thin dark edge (default), `heavy` ivory with a thick dark-brown edge, `gold` that plus a thin gold rim, `band` a soft dark strip along the bottom. The font file goes in `FONT`'s folder |
| `MUSIC`, `MUSIC_DB`, `CH_MUSIC` | the instrumental, each section's level, each chapter's start second |
| `MV_CLIP` | the video `"MV:<second>"` shots play |
| `GAPS` | seconds of lead-in, between chapters, for the title, between parts, at the end, and of cross-fades |
| `LOOKS`, `NEG`, `IMAGES`, `IMAGE_FIELDS` | pictures (step 4) |
| `SHOTS` | the timeline (step 6) |
| `SHORTS` | the vertical Short's clips, head line, closing line and layout, in every episode (step 9); add `"shorts": {"suffix": "_shorts"}` to `EDITS` |

## Lessons

- Pace: a cloned voice reads about 5 Chinese characters a second (punctuation not counted). A 1.4 s breath between chapters and 3.4 s for the title after the opening make it feel unhurried.
- A narration job costs 50 credits even for one sentence: collect re-reads and do them in one job.
- A long part can be cut off before its end (once at 68 s, 492 characters in). `narration.py check` reports "the last N characters were not heard": `cut` the file before that sentence, re-read only the rest, and list the pieces in `NARRATION`.
- Keep history and legend apart: say so in the script when something is a legend, and cite sources in the description.
- One topic seen from another angle makes another episode. A playlist just for explainers lets the MVs and explainers feed each other.

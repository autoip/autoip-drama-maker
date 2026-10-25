# project.py reference

[中文](../zh-TW/PROJECT_FORMAT.md) | English

`project.py` is an ordinary Python module, loaded by `mvkit/common.load_project()`.

- All times are **song seconds**.
- All paths are **relative to the project folder**.
- For a complete example, see [`examples/demo/project.py`](../../examples/demo/project.py).

## Basics

| Field | Description |
|---|---|
| `NAME` | Base name of the output files, e.g. `my_song_MV` |
| `SONG` | The song file, e.g. `song.mp3` |
| `STYLE` | Shared style sentence appended to every still prompt (English) |
| `MOTION_PREFIX` | Shared sentence prepended to every image-to-video prompt (can be Chinese) |
| `BAND_STAGE` | Stage description for musicians' solo shots |
| `NEG` *(optional)* | Shared negative prompt |
| `MULTI_NEG`, `MULTI_DESC_PREFIX` *(optional)* | For multi-subject reference videos: a negative prompt that stops members being shrunk, and a prefix for each member's description |
| `GROUP_PROMPT_SUFFIX` *(optional)* | "Mature, tall" description added to group still prompts |
| `VIDEO` *(optional)* | Video parameters. Default: `dict(duration_seconds="5", resolution="768p", aspect_ratio="16:9")` |
| `LS_FIELDS` *(optional)* | Extra lip-sync fields, e.g. `dict(engine="h3", resolution="768p")` (h3 768p takes ≤ 20 s of audio per job). Stills over 10 MB are saved as a 2560-wide JPEG for the job automatically |
| `FEATURE_VIDEO` *(optional)* | Resolution and aspect ratio for `feature_jobs.py`, default `dict(resolution="768p", aspect_ratio="16:9")` |

## Cast: `CHARS`

```python
CHARS = {"FV": dict(file="chars/soprano.png", name="主唱・女高音", kind="vocal",
                    role=("SOPRANO", "女高音"), desc="female singer with very long silver-white hair, ...")}
```

| Field | Description |
|---|---|
| `kind` | `vocal`: cropped to a 3:4 base image centered on the face, used for lip-sync. `band`: the whole image is used as the reference |
| `role` | Musician name plate shown during the instrumental break (English, local language) |
| `desc` | Stable appearance description reused by every generation. Multi-subject reference videos use only its first 200 characters |

## Shots

```python
LS_SCENES = [(id, char, scene_prompt, motion_prompt, caption)]           # lip-sync scenes (keyframes); motion_prompt = a mood + "steady camera". Lip-sync 3.0 pushes in at random: make two takes of an important line and pick with `qc/zoom.py` (LESSONS "Lip-sync")
LIPSYNC   = [(LS_id, scene_id, a0, dur, voice)]                          # lip-sync jobs: dur seconds (≤30) from song time a0, and which voice
BAND      = [(id, char | [chars], caption, prompt, motion)]               # musicians; a list = group shot
MULTI_PROMPT = {id: "multi-subject reference prompt; @圖片 N = member N"} # used only when a group shot has no approved still
BROLL     = [(id, caption, prompt, motion)]                              # story footage: text-to-image → image-to-video
```

An MV that shows several AutoIP video features makes a second job file with `mvkit/feature_jobs.py` (WORKFLOW, "Video generation"):

```python
I2V       = [B_id, ...]                                                 # these BROLL shots go through image-to-video 3.0, first frame kf/<id>.png
KEYFRAME  = {id: (first kf id, last kf id, motion, seconds)}             # keyframe video 2frame, 6 / 10 / 15 s
MULTI     = {id: ([(ref key, description | None), ...], prompt, seconds)} # multi-subject reference 3.0, 1–6 images in @圖片 N order; name the location in every SHOT
REFS      = {key: dict(desc="...")}                                     # descriptions for MULTI entries given as None, then REF_DESC = {key: "..."} (200 characters are sent)
FEATURE   = {"LS": "Lip-sync", "M": "Multi-reference 3.0", "K": "Keyframe"}  # clip id prefix → feature name; the render tags "AutoIP｜<feature>" top right when the feature changes
EXTRA_CAPS = {id: "caption"}                                             # clips outside BROLL / BAND / LS_SCENES (K*, M*) can be listed in SECTIONS shots
```

A reference key is looked up as `refs/<key>.png`, `refs/angles/<key>.png` (multi-angle character views), then `kf/<key>.png`.

## Sections: `SECTIONS`

```python
SECTIONS = [("副歌：夜之劇場", (40.0, 56.0), "subtitle design notes", [(40.0, "歌詞一句", "F"), ...], ["LS03", "B04", ...])]
```

- Section names have the form `"<key>：<subtitle>"`. The `key` is matched against `TYPO.acts` and `TYPO.specials`; the subtitle is shown under the act title.
- A section written as `(None, seconds)` is a promo card, and the subtitle engine skips it.
- Each lyric line is `(start seconds, text, voice)`. The voice is a key of `AUDIO["voices"]`.

## Audio: `AUDIO` / `VOICE_SPANS`

```python
AUDIO = dict(beats="audio/beats.json", vocals="audio/vocals.wav", words="audio/words.json",
             voices={"F": "audio/vocals_F.wav", "M": "audio/vocals_M.wav"})
VOICE_SPANS = {"F": [(16.5, 22.4), ...]}    # spans for one voice; the other voice gets the rest
VOICE_BOTH = [(163.3, 181.5), ...]          # optional: spans both sing together (a harmony chorus); every track keeps them
```

## Edits: `EDITS`

```python
EDITS = {"short": dict(cut=57.4, end=118.3, open_s=2, end_s=3, suffix="_1min", shots="""..."""),
         "full":  dict(cut=6.3, end=132.0, open_s=4, end_s=6, shots="""... @short ...""")}
```

| Field | Description |
|---|---|
| `cut` / `end` | Which part of the song to use |
| `open_s` / `end_s` | Length of the opening and end cards in seconds. Automatically 0 if the card file doesn't exist |
| `size` | Canvas size, default `(1920, 1080)`; `(1080, 1920)` renders in portrait (see WORKFLOW, "Vertical cut") |
| `focus` | `{clip id: 0–1}`, the horizontal crop centre when cropping to portrait, default 0.5; generate it with `qc/focus.py`. A key `"clip id@row time"` (e.g. `"LS06@133.2"`) sets one shot only, for a subject that moves across the clip. The value is a fraction of the crop window's travel, not a frame position: for a 16:9 clip in a 9:16 crop the window centre ≈ 0.16 + 0.68 × focus (a subject at x 0.75 needs 0.87) |
| `zones` | Replaces the subtitle engine's lyric-row positions `{"TL": (x, y), ...}`, for the portrait canvas |
| `open_card` / `end_card` | Card images for this edit only (e.g. portrait cards), overriding `RENDER` |
| `crop` | Crops for this edit only, `{clip id: "crop=w:h:x:y"}`, merged over `RENDER["crop"]` |
| `labels` | `False` drops the `FEATURE` corner tags; by default they are drawn whenever `project.FEATURE` is set |
| `shots` | The edit list; rules below |

How to write `shots`:
- Each row is `start src [offset] [flash]`. Rows are separated by `|` or newlines; everything after `#` is a comment.
- `@name` pastes in the rows of another edit.
- The first row's `start` is replaced by `cut`.
- For lip-sync rows the offset comes from `align.json`; any offset you write is ignored.

## Render: `RENDER`

| Field | Default | Description |
|---|---|---|
| `fps` | 25 | |
| `crop` | `{}` | `{clip_id: "crop=w:h:x:y"}`, crops out burned-in captions. For lip-sync captions prefer AutoIP `/videos/restore` (`operations[]=subtitle`), which keeps the resolution |
| `grade` | contrast 1.07, saturation 1.06, vignette, animated grain | ffmpeg color-grading filter chain |
| `open_card` / `end_card` | — | Promo card images (1920×1080) |
| `lang` | `zh-TW` | Language in the SRT file name |
| `tail_guard` | 0.35 | Seconds at the end of each lip-sync clip that are never used |

<a id="typo"></a>
## Kinetic subtitles: `TYPO`

| Field | Description |
|---|---|
| `font` / `font_file` / `font_scale` / `latin` | Font family name (as libass sees it), the file used to measure text width, the size factor, and the Latin font |
| `title` / `title_en` / `tagline` / `genre` | Used for the title card. In the prologue the title burns in one character per bar (4 beats) by default |
| `intro_title_s` | How many seconds the prologue title stays; by default until the prologue ends. Set it short (e.g. 5) when the prologue is long |
| `hold` | `{line text: seconds}`: clear that line this long after its last word instead of waiting for the next line. For a shout followed by silence |
| `title_step` | Beats between title characters in the prologue, default 4. Set 1 to burn them in one per beat |
| `ep_card` / `ep_card_s` | Episode card before the prologue title, e.g. `("其三", "不見")`, shown for `ep_card_s` seconds (default 4). Off unless set |
| `rewrite` / `rewrite_s` / `rewrite_color` | "Rewrite" card before the title: an old line appears, then a brush stroke (default vermilion `C8281E`) crosses out part of it, e.g. `("the old ending in full", "the part to cross out")`; an optional third field is written above the struck part in the same colour, e.g. `("the old line", "the old label", "her name")`. Shown for `rewrite_s` seconds (default 5). For songs that retell a legend. Off unless set |
| `acts` | `{section key: "ACT I"}`: act title in the top-left corner |
| `specials` | `{section key: "intro" \| "plates" \| "finale" \| "outro"}`; see the table below |
| `band_plate` | Name plate shown with group shots, e.g. `("THE BAND", "樂團")` |
| `readings` | `{rhyme word: "reading"}`: small gold text under line-end rhymes. A single syllable goes under the last character; a hyphenated reading spans the whole word |
| `readings_anywhere` | Words that get a reading even when not at the end of a line (they must still be within the last 4 characters) |
| `vertical` | `{voice: 0–1}`: share of each voice's lines set as vertical columns; default `{"F": 0.5}` (male lines all horizontal). Vertical columns sit at the left and right edges, so raise it (e.g. `{"F": 0.9, "M": 0.9}`) when faces are centred, to keep text off them |
| `gags` | List of keyword effects; see the table below |

The four special sections in `specials`:

| Value | Effect |
|---|---|
| `intro` | The title burns in one character at a time |
| `plates` | Musician name plates |
| `finale` | The title card slams in on a downbeat, then shrinks to the top of the screen |
| `outro` | The title fades out in silver |

Each `gags` entry has the form `dict(type=..., match="word" or ["word", ...], ...)`. It fires only when the line contains `match`:

| type | Parameters | Effect |
|---|---|---|
| `title_line` | — | For lines containing the title: the title fills the center in giant type, a red curtain opens, a spotlight |
| `color` | `chars`, `color` | Recolors the given characters (RRGGBB) |
| `enlarge` | `chars`, `scale` | Enlarges them (a roar) |
| `scurry` | `chars` | Shrinks them, then they scurry off the right edge |
| `float_away` | `chars` | Float upward and away |
| `tear` | `char` | A tear runs down from that character |
| `zone` | `zones=[a, b]` | Pins the line to zone a, or zone b if the previous line was in the same row |
| `coins` | — | Rain of gold coins |
| `clink` | `char` | A toast: two beams of light collide with a white flash |
| `clap` | `char`, `word` | Full-screen CLAP |
| `wheel` | `words`, `highlight` | Words rotate around a ring (loops) |
| `explode` | — | White flash; the whole line blows apart |

Voice styles:
- Voice `F`: silver-white, slides in, and is set vertically half the time.
- Voice `M`: white with a blood-red edge, slams in and shakes, with a random tilt.
- When the next line appears, the previous one burns to ash and drifts upward.

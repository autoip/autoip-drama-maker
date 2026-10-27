# project.py reference

[中文](../zh-TW/PROJECT_FORMAT.md) | English

`project.py` is an ordinary Python module, loaded by `dramakit/common.load_project()`. One `project.py` per episode.

- All paths are **relative to the episode folder**; material shared by the whole series is written `../cast/A.png`.
- Times in the edit list are **each clip's own seconds**. The episode timeline is built by joining the rows.
- For a complete example, see [`examples/demo/project.py`](../../examples/demo/project.py).

## Basics

| Field | Description |
|---|---|
| `NAME` | Base name of the output files, e.g. `board_s1e01` |
| `TITLE` | The drama's name (title card) |
| `EPISODE` | Episode number (the title card shows 「第 N 集」, "Episode N") |
| `ASPECT` | `"9:16"` (default, vertical short drama) or `"16:9"`; sets the generation aspect ratio and the output canvas |
| `STYLE` | Shared style sentence appended to every still prompt (English). **Look and light only, no place**: a place written here is carried into every still, props included |
| `MOTION_PREFIX` | Shared sentence prepended to every video prompt (**English**: multi-reference video reads Chinese narration out with the line). **Describe only the visual style**: characters or props written here get pushed into every clip |
| `SFX` | Default `MUSIC & SFX:` sentence for image-to-video and keyframe prompts, e.g. "No music, only ambience and the sounds of the action." (music is added in the edit for the whole episode). Not sent with multi-reference shots: AutoIP's default there is clear dialogue with room ambience and no music, and a `MUSIC & SFX:` line switches the music track on |
| `PROP_STYLE` *(optional)* | Style sentence for prop references, in place of `STYLE`; default "a studio product photograph of the object alone, nobody in the picture". With the drama-still style a prop comes back as a scene with actors |
| `NEG` *(optional)* | Shared negative prompt (the default includes `nude, nsfw`) |
| `VIDEO` *(optional)* | Video parameters. Default: `dict(resolution="768p", aspect_ratio=ASPECT)` |
| `LS_FIELDS` *(optional)* | Extra lip-sync fields, e.g. `dict(engine="h3")` (lip-sync 3.0: more accurate mouths, smaller output) |
| `T2I` *(optional)* | Extra text-to-image fields. Default: `dict(mode="v3")` |
| `SIZES` *(optional)* | Still sizes: `frame` (shot first frames and sets, default `540x960` / landscape `960x540`), `portrait` (character sheets, `768x1024`), `square` (props, `1024x1024`) |

## Characters, sets, props

The three tables share one set of keys (no duplicates). Shots name them with `@KEY`.

```python
CAST = {"A": dict(name="<A 的名字>", file="cast/A.png", title="<A 揭露後的身分>",
                  desc="<A's look in English: age, hair, face, one outfit>",
                  prompt="neutral expression", voice="voices/A.wav", voice_src="voices/raw/a.m4a")}
SETS  = {"ROOM": dict(name="<室內場景>", file="sets/ROOM.png", desc="<the main interior in English>")}
PROPS = {"ITEM": dict(file="props/ITEM.png", desc="<the object, in English, with no writing on it>")}
```

| Field | Description |
|---|---|
| `file` | The reference image. Supply it yourself, or generate it with `make_jobs.py P refs` (characters need a `prompt`; sets and props use `prompt` or `desc`) |
| `desc` | Stable appearance description (English) reused by every generation. Multi-reference videos read only its first 200 characters |
| `ref_desc` *(optional)* | Description used instead in multi-reference videos (e.g. a shorter version) |
| `prompt` *(optional)* | Sentence added after `desc` when generating the reference image (characters: expression, pose) |
| `base` *(optional)* | Start from a picture you have (a photo you may use, art, a character sheet of an earlier project) with image-to-image instead. Costume, props and painted looks in it tend to stay: crop them away with `base_crop` |
| `base_crop` / `base_box` *(optional)* | `base_crop = (x0, y0, x1, y1)`: keep only this part (fractions); `base_box = (x, y, width)`: where it goes on the canvas (fractions), e.g. a face crop where the head of a waist-up portrait goes, on a plain ground. Without it the picture is fitted, standing on the bottom edge |
| `base_strength` *(optional)* | Image-to-image strength, default 0.8. A list (e.g. `[0.6, 0.75]`) makes one candidate per strength in `candidates/`; copy the one you pick to `file` |
| `name` | Characters: the name next to the subtitles and on the character intro card. Sets: what the prompt calls this location |
| `title` *(characters)* | Job title / identity shown above the name on the character intro card |
| `color` *(characters, optional)* | Subtitle colour for this character's lines (RRGGBB) |
| `file=None` / `unseen` *(characters)* | A character who is not shown (a villain kept faceless, a voice off): no reference picture, and their lines still use their voice sample; `unseen` says how the shot shows them, e.g. "the man sitting behind the desk with his back to the camera" (a note, and the picture of their voice clip when they have no character sheet); the prompt gets no "only ___ speaks" sentence (in a test shot it was read out as part of the line). Don't `@` them in `act`: describe them in words. A close-up of hands or an object is safest: a person with their back to the camera often turns round with a stranger's face. A character with a picture can have `unseen` alone: still not shown in this episode, the picture gives them their voice (`make_jobs.py P voices`), and a later episode drops `unseen` to show the face |
| `voice` *(characters)* | Voice sample, sent with every one of this character's lines |
| `voice_src` / `voice_span` *(characters)* | The raw recording (or the `voices/raw/<KEY>.mp4` that `make_jobs.py P voices` made) and the seconds to use, `(a, b)`; `voices.py` cuts `voice` from it |
| `voice_line` / `voice_how` *(characters)* | Let AutoIP voice the character: one line they say (about 20–30 characters) and the tone; `make_jobs.py P voices` runs image-to-video with sound from the character sheet and writes it to `voice_src` |
| `voice_secs` / `voice_who` *(characters, optional)* | Length of that clip (default from the line, 5–15); for a character with no face, how the text-to-video shows them (default `unseen`) |

## Scenes: `SCENES`

```python
SCENES = [("S2", "ROOM", "<日／夜>，<室內場景>")]       # (scene id, set key, scene heading)
```

The set goes into the references of every multi-reference video in the scene (as the last image), and every `SHOT` names the location.

## Shots: `SHOTS`

In script order. One `dict` per shot:

```python
dict(id="S2_08", scene="S2", cast=["B", "A"], say=("C", "<C 揭露 A 身分的那一句>", "<語氣>"),
     act="@C <walks past @B toward @A>, @B frozen in the background, medium shot.")
```

| Field | Description |
|---|---|
| `id` | Shot id; also the file name of `clips/<id>.mp4` and `kf/<id>.png` |
| `scene` | Scene id |
| `kind` | `M` (default) multi-reference video, `LS` lip-sync, `I2V` image-to-video, `K` keyframe video; see the table below |
| `say` | `(speaking character, line, tone)`. The line in Chinese, the tone in **English**. One speaker per shot; length is estimated at 4 characters per second |
| `act` | Action and camera (**English**: H3 reads Chinese narration out with the line). `@KEY` names a character, prop or set and becomes `@圖片 N`; name people with `@KEY`, not he / she (gender words override the voice sample). To get several shots in one clip, write `SHOT 1:`, `SHOT 2:` on separate lines; the line is attached after the last SHOT, so put the speaking shot last |
| `cast` / `props` | Extra characters / props to put in the references that `act` doesn't `@` |
| `set` *(optional)* | Use a different set for this shot (default: the scene's set) |
| `secs` | Clip length. `M`: 5–10 (default from the line length); `I2V`: default 5; `K`: 6 / 10 / 15 |
| `sfx` *(optional)* | This shot's `MUSIC & SFX:` (English), replacing `project.SFX`; on a multi-reference shot it switches the music track on too |
| `still` | First-frame still description for `LS` / `I2V` / `K` (English); generates `kf/<id>.png` |
| `to` | `K`: which shot's still is the last frame (`kf/<to>.png`) |
| `audio` | `LS`: the recording of this line, default `lines/<id>.wav` |
| `cap` *(optional)* | Caption on the review sheet; defaults to the line or the action |

| `kind` | AutoIP feature | What is sent |
|---|---|---|
| `M` | Multi-subject reference 3.0 `/videos/multi-subject-reference` | References (speaker, `@KEY`, `cast`, `props`, set; ≤6 images), a description for each, prompt, `dialogue_text`, `voice_sample` |
| `LS` | Lip-sync `/videos/lip-sync` | `kf/<id>.png` + `lines/<id>.wav`; the prompt gives only the tone and "steady camera" |
| `I2V` | Image-to-video 3.0 `/videos/image-to-video` | `kf/<id>.png` + action |
| `K` | Keyframe video `/videos/keyframe` (2frame) | `kf/<id>.png` → `kf/<to>.png` + action |

## Edit list: `EDITS`

```python
EDITS = {"main": dict(shots="""
    S2_01 auto flash intro=B
    ^S2_04 0.8 1.0 @-1.0
"""), "wide": dict(..., size=(1920, 1080), suffix="_wide")}
```

| Field | Description |
|---|---|
| `shots` | The edit list; rules below |
| `size` | Canvas. Default from `ASPECT`: `(1080, 1920)` or `(1920, 1080)` |
| `suffix` | Output file name suffix |
| `focus` | `{clip id: 0–1}`: horizontal crop centre when a clip's aspect ratio differs from the canvas, default 0.5 |
| `music` | Different music for this edit only (same format as `MUSIC`) |
| `end_card` / `end_s` | End card image and seconds (optional; by default there is no end card and the episode ends on the cliffhanger) |

How to write `shots`:
- **Base row** `src [in|auto] [dur] [flags]`: placed after the previous row; picture and sound both come from this clip. `in` and `dur` are clip seconds; with just the id or `auto`, it is trimmed to the line using `speech.json`.
- **Cutaway row** `^src [in] [dur] @at [flags]`: picture only, the sound doesn't change. It goes over the previous base row, starting `at` seconds after that row's start (a negative `at` counts back from its end). It can run on into the next row (J cut).
- A path as `src` (e.g. `../s1e01_x/clips/S2_08`) takes a clip from another episode, for a recap; the subtitles read that episode's lines.
- A line on its own with `@name` pastes in another edit (e.g. `@recap`).
- Separate rows with newlines or `|`; everything after `#` is a comment.

| flag | Effect |
|---|---|
| `flash` | White flash in |
| `black` | Fade in from black |
| `zoom` / `zoom=1.2` | Push in to 1.15× (or the given factor) within 0.25 s, held for the whole row |
| `freeze=S` | Freeze frame for S seconds after the row ends (picture desaturated, sound muted, music continues) |
| `end` / `end=下集見` | Cliffhanger text (default `TYPO.end_text`; 下集見 = "See you next episode"), shown over the freeze frame or in the row's last 1.6 s |
| `mute` | Don't use this clip's sound |
| `sfx=name` | Plays `sfx/name.wav` (or .mp3, .m4a) at the start of the row |
| `intro=KEY` | Character intro card: title + name |
| `title` | Title card: the drama's name + episode number |
| `label=前情提要` | Label in the top-left corner, for the whole row |
| `heard` | Subtitle what `speech.py` actually heard instead of the script line (an NG reel take that read the stage directions out) |
| `chat=NAME` | Livestream comments: the comments in `CHAT[NAME]` scroll up one by one from the bottom left over this row (intro cards sit on the left too: not on the same row) |

Livestream comments go in `CHAT = {"hate": [("夜貓子", "這身材也敢跳？"), ...], ...}`: they are laid on as subtitles, not generated (phone screens always face away from the camera).

## Music: `MUSIC`

```python
MUSIC = [("tension", "S2_01", "S2_05", -18), ("reveal", "S2_08", None, -15)]
```

`(file name, from row, to row, volume dB)`: files are in `music/` (or one level up if not found). Start and end are a shot id (the time that row first appears), seconds, or `None` (the beginning / the end). The music loops to the length needed, fades in and out, and drops automatically whenever there is dialogue.

## Render: `RENDER`

| Field | Default | Description |
|---|---|---|
| `fps` | 25 | |
| `pad` | `(0.15, 0.35)` | Seconds kept before and after the line in `auto` rows |
| `hold` | 2.0 | Seconds taken from an `auto` row with no line |
| `tail_guard` | 0.3 | Seconds at the end of each clip that are never used |
| `crop` | `{}` | `{clip id: "crop=w:h:x:y"}`, to crop away small text in a corner |
| `grade` | contrast 1.03, saturation 1.05 | ffmpeg colour-grading filter chain |
| `lufs` | −16 | Overall loudness |
| `sfx_gain` | −4 | Sound effect volume dB |
| `lang` | `zh-TW` | Language in the SRT file name |

## Subtitles and cards: `TYPO`

| Field | Default | Description |
|---|---|---|
| `font` | `Noto Sans TC` | Font family name (as libass sees it); extract a static weight from a variable font with `make_static_font.py` first |
| `font_scale` | 1.45 | libass size conversion factor (about 1.45 for Noto CJK) |
| `size` | 54 | Dialogue text size (px at 1080 wide) |
| `max_chars` | 14 (vertical) / 22 (landscape) | Longest subtitle chunk in characters, split at punctuation |
| `sub_y` | 0.74 (vertical) / 0.92 (landscape) | Height of the subtitle baseline as a fraction; in vertical it stays clear of the app's title and buttons at the bottom |
| `intro_y` | 0.56 (vertical) / 0.6 (landscape) | Height of the character intro card as a fraction |
| `intro_s` / `title_s` | 2.4 / 2.6 | Seconds the character intro card / title card stays |
| `end_text` | 未完待續 | Used when `end` has no text ("To be continued") |
| `badge` | — | e.g. `"第1集"`: small tag in the top-right corner for the whole episode |
| `accent` | `F2C55C` | Colour of the character intro card's bar and title, and the episode number on the title card (also the user names of livestream comments) |
| `chat_y` / `chat_rows` | 0.66 (vertical) / 0.8 (landscape) / 5 | Height of the lowest livestream comment as a fraction / comments on screen at once |

Subtitle rules:
- Lines are split at punctuation; a trailing 「，。」 is removed, 「！？…」 are kept.
- One clip split over two rows (say `S4_02 1.3 2.45` then `S4_02 3.9 1.25 zoom sfx=hit`) subtitles each row with only the words said in it: 「錢都進了他的帳」 on the first, 「簽名是他」 on the second, so the punchline does not show early.
- With per-character timings in `speech.json`, chunks are matched character by character (difflib); without them, they are spread evenly over the line's seconds.
- Subtitles never run past their row (freeze included); when the next chunk appears, the previous one goes.

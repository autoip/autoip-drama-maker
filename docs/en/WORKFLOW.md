# Full workflow: from a song to a published video

[中文](../zh-TW/WORKFLOW.md) | English

This page uses `projects/my_song` as the example and writes `P` for that path. Run every command from the repo root. For a whole series, read [SERIES_PLANNING.md](SERIES_PLANNING.md) first.

```
song ─┬─ 1 Audio analysis ─ beats / structure / vocal separation / voice split / lyric timing / emotion map
      │
      ├─ 2 Cast & storyboard ─ project.py → storyboard.json + shots.json
      ├─ 3 Keyframes ───────── text-to-image / image-to-image → [review sheet: human approval]
      ├─ 4 Video ───────────── lip-sync / image-to-video / group shots → [review sheet: human approval]
      ├─ 5 QC ──────────────── lip-sync alignment / is the mouth moving / tail smear
      ├─ 6 Edit (EDL) ──────── emotional beat edit (full + short)
      ├─ 7 Subtitles ───────── kinetic typography theme, quick preview
      ├─ 8 Render ──────────── render_mv.py → mp4 + srt
      ├─ 9 Thumbnails ──────── A/B/C from frames of the finished video, plus Shorts covers for the vertical cut
      └─ 10 Publish ────────── title / description / chapters / tags / social posts
```

**Rule: AutoIP charges credits when a job is submitted, and there is no cancel API. Before every batch of video jobs, show still review sheets to whoever signs off.**

---

## 1. Audio analysis

```bash
mkdir -p P/audio
ffmpeg -i P/song.mp3 -ar 44100 -ac 2 P/audio/song.wav
python mvkit/audio/analyze.py P/audio/song.wav P/audio/beats.json          # beats, downbeats, section boundaries
python -m demucs --two-stems=vocals -n htdemucs -o P/audio/sep P/audio/song.wav
cp P/audio/sep/htdemucs/song/vocals.wav P/audio/vocals.wav
```

**Who is singing.** For a duet (for example a screamer and a soprano), first look at the pitch and the voiced ratio per second:

```bash
python mvkit/audio/voice_probe.py P/audio/vocals.wav
```

- Soprano windows have a high voiced ratio and f0 > 350 Hz.
- Scream windows have energy but are almost entirely unvoiced.
- Put one voice's time spans into `project.VOICE_SPANS`, then split the tracks:

```bash
python mvkit/audio/split_voices.py P          # -> audio/vocals_F.wav, audio/vocals_M.wav
```

Each lip-sync clip is fed only its own voice's track, so a singer's mouth stays still while the other one sings.

**Lyric timing:**
1. Fill in each line's start time in `project.SECTIONS`. Listen to the song and check against `beats.json` and the waveform.
2. Then run ASR per section to get per-character timings:

```bash
python mvkit/audio/asr_words.py P 15.5,46.5 58.5,74 74.5,103      # spans that contain vocals
```

- ASR text for Taiwanese, screaming or a dense mix is almost useless. With the lyrics as the prompt and short spans, though, the **timings** are mostly usable.
- Lines that can't be matched are spread evenly between line start times, so the line start times must be accurate.

**Emotion map.** The edit is based on it. See [EMOTIONAL_BEAT_EDITING.md](EMOTIONAL_BEAT_EDITING.md).

```bash
python mvkit/audio/emotion_map.py P/audio/song.wav P/audio/beats.json P/audio/vocals.wav > P/audio/emotion.txt
```

## 2. Cast and storyboard

1. Put the character images in `P/chars/`.
2. Fill in these fields in `project.py` (see [PROJECT_FORMAT.md](PROJECT_FORMAT.md) for each one):
   - `CHARS`: the fixed cast. Each character gets one stable English appearance description that every prompt reuses.
   - `LS_SCENES`, `LIPSYNC`: the singers' lip-sync scenes, and which ≤30 s of the song each lip-sync uses.
   - `BAND`: solo shots of the musicians, and group shots.
   - `BROLL`: story footage.
   - `SECTIONS`: sections, lyrics, voices, and which shots each section uses.

```bash
python mvkit/faces.py P          # character face boxes; add any it can't detect by hand
python mvkit/storyboard.py P     # -> storyboard.json, shots.json; lists shots no section uses
```

**Storyboard tips:**
- Match shot scale to the section's mood: close-ups for the build-up, medium and group shots for the chorus, big set pieces for the climax.
- Give each key image in the lyrics its own B-roll, for example red-wine glasses clinking for "a toast", or a weeping mask for "tears".
- Keep extras in B-roll `NO_FACES` (masks or shadows) so faces from outside the cast don't appear.
- Once the band line-up is set, don't change it. The same people must be recognizable in every shot.

## 3. Keyframes (stills)

```bash
python mvkit/make_jobs.py P kf                       # -> P/jobs/kf_jobs.json
python mvkit/aip_runner.py P/jobs/kf_jobs.json       # one at a time; can be interrupted and resumed
python mvkit/qc/sheets.py stills P/review_kf.jpg P/kf
```

Show `review_kf.jpg` to whoever signs off. For any still they reject:
1. Move it to `kf_rejected/`.
2. Edit the prompt in `project.py`.
3. Rerun just those stills with `ONLY=ID1,ID2`.

```bash
ONLY=O1,B05 python mvkit/make_jobs.py P kf && python mvkit/aip_runner.py P/jobs/kf_jobs.json
```

**Group shots** (a `BAND` entry with several members):

```bash
python mvkit/group_still.py P W1                     # collage + image-to-image jobs at 2 strengths
python mvkit/aip_runner.py P/jobs/W1_stills.json
# look at P/kf_candidates/W1_*.png, pick one and copy it to P/kf/W1.png
```

## 4. Video generation

```bash
python mvkit/make_jobs.py P video                    # lip-sync audio is cut from the voice tracks automatically
python mvkit/aip_runner.py P/jobs/video_jobs.json
python mvkit/qc/sheets.py strips P/review_clips.jpg P/clips/*.mp4
```

- Lip-sync: keyframe + that voice's track.
- Solo musicians and B-roll: image-to-video.
- Group shots: image-to-video when an approved still exists; multi-subject reference only otherwise.

**New characters, group shots and changed shots always get a still review before any video is submitted.**

## 5. QC

```bash
python mvkit/qc/align.py P                    # where each lip-sync clip's audio actually lands in the song -> align.json
python mvkit/qc/mouth.py P timeline LS01 LS02  # mouth movement every 0.5 s; '.' = no face found (zoomed out)
```

Always check for:
- A lip-sync clip whose mouth doesn't move for the first few seconds.
- A lip-sync clip that zooms out to full body midway.
- A white smear in the last 0.2 s of a lip-sync clip. By default, renders skip the last 0.35 s.
- Captions burned into a lip-sync clip: remove them with AutoIP `/videos/restore` (`source_video` + `operations[]=subtitle`); don't crop or re-cut around them.
- Garbled text appearing in image-to-video clips. Use only the clean seconds.
- A person's face changing midway through a clip. Use only the part before the change.

For fixes, see [LESSONS.md](LESSONS.md).

## 6. Edit list (EDL)

Edits go in `project.EDITS`, one entry per cut, for example `full` and `short`. Each row is `start src [offset] [flash]`, where `start` is in song seconds:

```python
EDITS = {
    "short": dict(cut=57.4, end=118.3, open_s=2, end_s=3, suffix="_1min", shots="""
        57.4 W1 0 flash | 58.2 D1 | 59.0 LS01 | 60.3 B10 ...
    """),
    "full": dict(cut=6.3, end=132.0, open_s=4, end_s=6, shots="""
        6.3 B01 | 8.4 B02 ...
        @short                          # reuse the short cut as-is
        119.1 B28 0 flash ...
    """),
}
```

- Leave the offset off lip-sync rows. The renderer aligns the mouths from `align.json`.
- Cut points snap to any beat within 0.08 s.
- Follow the emotion map:
  - Peak sections: cut every 1–2 beats, but keep one anchor long take.
  - Low sections: hold for at least 2 bars before cutting.
  - Never put a cut on a breath or a drop.
  - Add `flash` on the strongest downbeats.
- Check the mouths: `python mvkit/qc/mouth.py P edl short`. Replace any shot flagged `IDLE?`.

## 7. Subtitles

Set the font, title, act names, rhyme readings and keyword effects in `project.TYPO` (see [PROJECT_FORMAT.md](PROJECT_FORMAT.md#typo)). While tuning, render the subtitles only, without video. You see the result in seconds:

```bash
python mvkit/qc/subprev.py P 74 90 P/subprev.jpg 75.6 79.5 82.5 86.0
```

Check:
- Does any text cover a singer's face?
- Does any text run off screen? The script prints `offscreen`.
- Do the readings match the lyricist's notes?
- Does the title card get out of the way in time at the climax?

## 8. Render

```bash
python mvkit/render_mv.py P short
python mvkit/render_mv.py P full
REUSE_BODY=1 python mvkit/render_mv.py P full        # only subtitles or cards changed: reuse the rendered picture
```

- Outputs `P/out/<NAME><suffix>.mp4` and `.zh-TW.srt`.
- The EDL is resolved from `project.EDITS` at render time, so the short cut's EDL can never be rendered as the full version by mistake.
- After rendering, spot-check frames: `python mvkit/qc/sheets.py video P/review_final.jpg P/out/xxx.mp4 5 20 35 ...`

### Vertical cut (Shorts / Reels)

Add `size=(1080, 1920)` to an edit and it renders in portrait. Reuse an existing cut and change only the canvas:

```python
V = dict(open_s=0, end_s=4, size=(1080, 1920), end_card="cards/end_v.jpg",
         focus={"S12": 0.64, "B16": 0.2},   # crop centre per clip: 0 = left edge, 1 = right edge, default 0.5
         zones={"TL": (400, 300), "TR": (680, 300), "TC": (540, 260), "BL": (420, 1480), "BR": (660, 1480),
                "BC": (540, 1560), "ML": (420, 1250), "MR": (660, 1250), "C": (540, 960)})
EDITS["shorts"] = dict(EDITS["short"], suffix="_shorts", **V)
```

```bash
python mvkit/qc/focus.py P shorts       # face detection -> focus for every shot with a person in it
python mvkit/render_mv.py P shorts
```

- Each shot is cropped from its own 16:9 clip to 9:16. The finished landscape video is not cut down the middle, so the subtitles are laid out again for the portrait canvas and nothing gets cut off.
- `focus`: `qc/focus.py` prints a `focus={...}` line to paste into the edit. B-roll without a face prints `?`: render once, look at a frame sheet, and pick the subject's position by eye.
- `zones`: where horizontal lyric rows land. In portrait the face sits in the middle band, so put lyrics above the head and below the chest. Vertical lyric columns stick to the left and right edges on their own.
- No opening card: the first second or two decide whether a Shorts viewer swipes away, so start on the first line of the chorus. Use a portrait image for the end card; `end_card` in the edit overrides the one in `RENDER`.
- English lyrics: a run of space-separated English words is one token and never wraps. The portrait frame is only 1080 wide, so split English lines in `SECTIONS` into chunks of about 15 letters or fewer.
- Most clips are 1280 wide, so a portrait crop is enlarged about 2.7×. Prefer half-body or close-up shots of people, and B-roll with one clear subject.
- After that enlargement every lip-sync shot is a huge face and the subtitles look big too: lower `TYPO.font_scale` for the vertical cut (e.g. 1.45 → 1.0), keep long-note lip-sync close-ups under about 2 s, and intercut story shots densely even early in the song (see "Narrative editing techniques" in [EMOTIONAL_BEAT_EDITING.md](EMOTIONAL_BEAT_EDITING.md)).

## 9. Thumbnails

Grab 3–5 candidate frames from the finished video. Use `thumbkit` to make three variants, A, B and C; see `examples/demo/thumbs.py`:

| Variant | Angle |
|---|---|
| A | Music: the singers' face-off, the band |
| B | Hook: the punchiest lyric |
| C | World: the setting, the title |

If there is a vertical cut, also make 1080×1920 Shorts thumbnails; see [PUBLISHING.md](PUBLISHING.md), "Shorts thumbnails", for the layout and how to upload them.

## 10. Publish

See [PUBLISHING.md](PUBLISHING.md): title formulas, description layout, chapters, tags, AI disclosure, satire disclaimer and social posts.

Once `YouTube_SEO.txt` is written, `mvkit/youtube_upload.py` can upload directly (private by default; check with `--dry-run` first). Setup: PUBLISHING.md, "Automatic upload".

---

## Cost reference

These are the credit prices at the time of writing; check `GET /api/v1/pricing` for current prices.

| Job | Credits |
|---|---|
| Text-to-image | 10 |
| Image-to-image | 15 |
| Lip-sync (≤30 s) | 50 |
| Image-to-video 768p 5 s | 75 |
| Multi-subject reference video 768p 5 s | 80 |

A 2-minute full version with about 100 shots costs roughly 4,000–4,700 credits, including redos. To save credits:
- Make the short version first; the full version reuses its footage.
- Generate 2–3 scenes per lip-sync segment and rotate between them.
- Make group stills first.

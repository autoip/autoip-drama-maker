# Full workflow: from a song to a published video

[中文](../../zh-TW/mv/WORKFLOW.md) | English

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
python mv/audio/analyze.py P/audio/song.wav P/audio/beats.json          # beats, downbeats, section boundaries
python -m demucs --two-stems=vocals -n htdemucs -o P/audio/sep P/audio/song.wav
cp P/audio/sep/htdemucs/song/vocals.wav P/audio/vocals.wav
```

**Who is singing.** For a duet (for example a screamer and a soprano), first look at the pitch and the voiced ratio per second:

```bash
python mv/audio/voice_probe.py P/audio/vocals.wav
```

- Soprano windows have a high voiced ratio and f0 > 350 Hz.
- Scream windows have energy but are almost entirely unvoiced.
- Put one voice's time spans into `project.VOICE_SPANS`, then split the tracks:

```bash
python mv/audio/split_voices.py P          # -> audio/vocals_F.wav, audio/vocals_M.wav
```

Each lip-sync clip is fed only its own voice's track, so a singer's mouth stays still while the other one sings.

**Lyric timing:**
1. Fill in each line's start time in `project.SECTIONS`. Listen to the song and check against `beats.json` and the waveform.
2. Then run ASR per section to get per-character timings:

```bash
python mv/audio/asr_words.py P 15.5,46.5 58.5,74 74.5,103      # spans that contain vocals
```

- ASR text for Taiwanese, screaming or a dense mix is almost useless. With the lyrics as the prompt and short spans, though, the **timings** are mostly usable.
- Lines that can't be matched are spread evenly between line start times, so the line start times must be accurate.
- With the lyrics as prompt, ASR guesses the next line in lyric order. When a section's opening is in doubt, recognize those seconds again without a prompt (LESSONS, "Speech recognition").
- With an NVIDIA GPU: run `python dreamfab/gpu_check.py` first, then add what it suggests, `ASR_DEVICE=cuda` here and `VENC=nvenc` for renders (SETUP, "Optional").

**Emotion map.** The edit is based on it. See [EMOTIONAL_BEAT_EDITING.md](EMOTIONAL_BEAT_EDITING.md).

```bash
python mv/audio/emotion_map.py P/audio/song.wav P/audio/beats.json P/audio/vocals.wav > P/audio/emotion.txt
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
python mv/faces.py P          # character face boxes; add any it can't detect by hand
python mv/storyboard.py P     # -> storyboard.json, shots.json; lists shots no section uses
```

**Storyboard tips:**
- Match shot scale to the section's mood: close-ups for the build-up, medium and group shots for the chorus, big set pieces for the climax.
- Give each key image in the lyrics its own B-roll, for example red-wine glasses clinking for "a toast", or a weeping mask for "tears".
- Keep extras in B-roll `NO_FACES` (masks or shadows) so faces from outside the cast don't appear.
- Once the band line-up is set, don't change it. The same people must be recognizable in every shot.

## 3. Keyframes (stills)

```bash
python mv/make_jobs.py P kf                       # -> P/jobs/kf_jobs.json
python dreamfab/aip_runner.py P/jobs/kf_jobs.json       # one at a time; can be interrupted and resumed
python mv/qc/sheets.py stills P/review_kf.jpg P/kf
```

Show `review_kf.jpg` to whoever signs off. For any still they reject:
1. Move it to `kf_rejected/`.
2. Edit the prompt in `project.py`.
3. Rerun just those stills with `ONLY=ID1,ID2`.

```bash
ONLY=O1,B05 python mv/make_jobs.py P kf && python dreamfab/aip_runner.py P/jobs/kf_jobs.json
```

**Painted looks (ink wash, woodcut…)**: make the story shots with text-to-image, the style first in the prompt. Make the lip-sync stills with image-to-image as usual so the mouth sings; the background comes out photographic, so put the person on a painted plate made with text-to-image (paint out seals and inscriptions first):

```bash
BG=P/kf/plate_L01.png BLUR=3 python mv/bokeh_still.py P/kf/ls_ink P/kf/L01.png    # once approved, ls_ink/L01.png replaces kf/L01.png
```

**Group shots** (a `BAND` entry with several members):

```bash
python mv/group_still.py P W1                     # collage + image-to-image jobs at 2 strengths
python dreamfab/aip_runner.py P/jobs/W1_stills.json
# look at P/kf_candidates/W1_*.png, pick one and copy it to P/kf/W1.png
```

## 4. Video generation

```bash
python mv/make_jobs.py P video                    # lip-sync audio is cut from the voice tracks automatically
python dreamfab/aip_runner.py P/jobs/video_jobs.json
python mv/qc/sheets.py strips P/review_clips.jpg P/clips/*.mp4
```

- Lip-sync: keyframe + that voice's track.
- Solo musicians and B-roll: image-to-video.
- Group shots: image-to-video when an approved still exists; multi-subject reference only otherwise.

**An MV that shows several AutoIP features**: fill in `I2V`, `KEYFRAME` and `MULTI` in `project.py` (PROJECT_FORMAT, "Shots"), make a second job file and run it after the lip-sync one (the concurrency limit counts every runner):

```bash
python mv/feature_jobs.py P                      # -> P/jobs/feature_jobs.json
python dreamfab/aip_runner.py P/jobs/video_jobs.json && python dreamfab/aip_runner.py P/jobs/feature_jobs.json
```

A batch that can wait can go in the half-price off-peak window (03:00–09:00 Taiwan time, see SETUP): prefix `AIP_OFFPEAK=1` and the runner waits until the window opens. A reference image over 10 MB (hd_4k character sheets are about 17 MB) is sent as a JPEG copy that `feature_jobs.py` saves in `jobs/img/`.

- Fights and scenes with two or more characters: multi-subject reference. Character and scene pictures go in `images[]`, the prompt choreographs `SHOT N:` by `SHOT N:`, and **every SHOT names the location** (a shot that doesn't gets the reference pictures' grey backdrop). One 8–10 s clip cuts into several shots.
- A→B moments and transitions (bow drawn → arrow hits, stage → story world, night → dawn, formation whole → collapsed): keyframe video.
- Image-to-video only for a few atmosphere shots; lip-sync is optional, two or three takes as a demo are enough.
- `FEATURE` makes the render tag "AutoIP｜<feature>" top right whenever the feature changes; the end card lists every feature used.
- Multi-reference and keyframe clips often contain cuts or dissolves; find them before editing: `ffmpeg -i clip.mp4 -vf scdet=threshold=12 -f null - 2>&1 | grep scd.time`.

**New characters, group shots and changed shots always get a still review before any video is submitted.**

**Pilot a new look first.** Send one or two clips of each kind (`ONLY=LS01,B05 python mv/make_jobs.py P video`) and check that the style holds before the batch. Lip-sync on a painted background may come back with the background repainted as a photograph; if so, put the person back on the plate frame by frame and keep the raw clip:

```bash
python mv/matte_video.py P/clips_raw/LS01.mp4 P/kf/plate_L01.png P/clips/LS01.mp4
```

For a character with a long ornament on the head (feathers, a tall hat) the person segmenter cuts it off: make the still with `CROWN_KEY=1 SAVE_CROWN=1 python mv/bokeh_still.py ...` (on a plain backdrop, whatever differs in colour above the head is kept, and the mask is saved as `<name>_crown.png`), then re-composite with `KEEP=P/kf/ls_ink/L01_crown.png`; the mask follows the face.

## 5. QC

```bash
python mv/qc/align.py P                    # where each lip-sync clip's audio actually lands in the song -> align.json
python mv/qc/mouth.py P timeline LS01 LS02  # mouth movement every 0.5 s; '.' = no face found (zoomed out)
python mv/qc/zoom.py P                     # face size every 2 s: did the lip-sync push in or pull back, and from when
```

Always check for:
- A lip-sync clip whose mouth doesn't move for the first few seconds.
- A lip-sync clip that zooms out to full body midway, or zooms itself into a close-up (`zoom.py` says `PUSH` / `JUMP` / `OUT`): use only the part before `push@` / `out@`, or make another take and keep the steadier one (LESSONS, "Lip-sync").
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
- Check the mouths: `python mv/qc/mouth.py P edl short`. Replace any shot flagged `IDLE?`.

## 7. Subtitles

Set the font, title, act names, rhyme readings and keyword effects in `project.TYPO` (see [PROJECT_FORMAT.md](PROJECT_FORMAT.md#typo)). While tuning, render the subtitles only, without video. You see the result in seconds:

```bash
python mv/qc/subprev.py P 74 90 P/subprev.jpg 75.6 79.5 82.5 86.0
```

Check:
- Does any text cover a singer's face?
- Does any text run off screen? The script prints `offscreen`.
- Do the readings match the lyricist's notes?
- Does the title card get out of the way in time at the climax?

## 8. Render

```bash
python mv/render_mv.py P short
python mv/render_mv.py P full
REUSE_BODY=1 python mv/render_mv.py P full        # only subtitles or cards changed: reuse the rendered picture
```

- Outputs `P/out/<NAME><suffix>.mp4` and `.zh-TW.srt`.
- The EDL is resolved from `project.EDITS` at render time, so the short cut's EDL can never be rendered as the full version by mistake.
- After rendering, spot-check frames: `python mv/qc/sheets.py video P/review_final.jpg P/out/xxx.mp4 5 20 35 ...`

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
python mv/qc/focus.py P shorts       # face detection -> focus for every shot with a person in it
python mv/render_mv.py P shorts
```

- Each shot is cropped from its own 16:9 clip to 9:16. The finished landscape video is not cut down the middle, so the subtitles are laid out again for the portrait canvas and nothing gets cut off.
- `focus`: `qc/focus.py` prints a `focus={...}` line to paste into the edit. B-roll without a face prints `?`: render once, look at a frame sheet, and pick the subject's position by eye.
- `zones`: where horizontal lyric rows land. In portrait the face sits in the middle band, so put lyrics above the head and below the chest. Vertical lyric columns stick to the left and right edges on their own.
- No opening card: the first second or two decide whether a Shorts viewer swipes away, so start on the first line of the chorus. Use a portrait image for the end card; `end_card` in the edit overrides the one in `RENDER`.
- English lyrics: a run of space-separated English words is one token and never wraps. The portrait frame is only 1080 wide, so split English lines in `SECTIONS` into chunks of about 15 letters or fewer.
- Most clips are 1280 wide, so a portrait crop is enlarged about 2.7×. Prefer half-body or close-up shots of people, and B-roll with one clear subject.
- After that enlargement every lip-sync shot is a huge face and the subtitles look big too: lower `TYPO.font_scale` for the vertical cut (e.g. 1.45 → 1.0), keep long-note lip-sync close-ups under about 2 s, and intercut story shots densely even early in the song (see "Narrative editing techniques" in [EMOTIONAL_BEAT_EDITING.md](EMOTIONAL_BEAT_EDITING.md)).

## 9. Thumbnails

Grab 3–5 candidate frames from the finished video. Use `thumbkit` to make three variants, A, B and C; see `examples/mv/demo/thumbs.py`:

| Variant | Angle |
|---|---|
| A | Music: the singers' face-off, the band |
| B | Hook: the punchiest lyric |
| C | World: the setting, the title |

If there is a vertical cut, also make 1080×1920 Shorts thumbnails; see [PUBLISHING.md](PUBLISHING.md), "Shorts thumbnails", for the layout and how to upload them.

## 10. Publish

See [PUBLISHING.md](PUBLISHING.md): title formulas, description layout, chapters, tags, AI disclosure, satire disclaimer and social posts.

Once `YouTube_SEO.txt` is written, `mv/youtube_upload.py` can upload directly (private by default; check with `--dry-run` first). Setup: PUBLISHING.md, "Automatic upload". To sort, add to, rename or describe playlists, use `dreamfab/youtube_playlists.py` (PUBLISHING.md, "Tidying playlists").

## Library page

Once you have a series, `python mv/library.py serve <series folder>` reads every episode's `project.py`, `kf/`, `clips/`, `jobs/`, `out/`, `thumbnails/` and `youtube.json` into the shared database `~/.config/dreamfab/dreamfab.db` (SQLite, one file for every series) and serves a local-only page (http://127.0.0.1:8770):

- Overview: one section per season, each episode's cover, cut lengths, shot count, lip-sync share, estimated credits and YouTube links
- Episode: the renders and the song; every shot's still, clip, the lyrics it covers and the cuts that use it; each cut's edit list (reused clips in red); thumbnails and review sheets
- Shot page: prompts, reference images, the jobs that made it, every old take and candidate
- Characters, files by kind, jobs and credits, YouTube uploads; search lyrics, prompts, characters, titles and file names

Standard library plus ffprobe / ffmpeg only. A running `serve` checks every 15 s and re-indexes in the background when files change (`index` builds without serving, `--no-index` skips the build at start); media lengths and posters are cached, so a rebuild takes seconds. Credits are what the submit charged as kept in `.state` (off-peak half price included), else an estimate from the job file: refunded failures are not counted and a job run again counts once; audit real spend with `credits.py`. The edit-list summary shows how many clips each cut uses and how many rows reuse one, the place to look when you want fewer repeats. `dreamfab.db` can also be queried with any SQLite tool (`python dreamfab/db.py show`).

---

## Cost reference

These are the credit prices at the time of writing; check `GET /api/v1/pricing` for current prices. The off-peak column is the price for tasks submitted with an API key between 03:00 and 09:00 Taiwan time (from 2026-10-30: half, rounded up); `common.estimate(job, off_peak=True)` uses it.

| Job | Credits | Off-peak |
|---|---|---|
| Text-to-image | 10 | 5 |
| Image-to-image | 15 | 8 |
| Lip-sync (≤30 s) | 50 | 25 |
| Image-to-video 768p 5 s | 75 | 38 |
| Multi-subject reference video 768p 5 s | 80 | 40 |

A 2-minute full version with about 100 shots costs roughly 4,000–4,700 credits, including redos. To save credits:
- Send batches that can wait in the off-peak window with `AIP_OFFPEAK=1`; video jobs cost half.
- Make the short version first; the full version reuses its footage.
- Generate 2–3 scenes per lip-sync segment and rotate between them.
- Make group stills first.

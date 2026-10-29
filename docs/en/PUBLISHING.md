# Publishing: covers, titles, descriptions, the series playlist

[中文](../zh-TW/PUBLISHING.md) | English

A short drama is followed episode by episode: each episode's cover, title and description must let people **recognise the series at a glance and know which episode it is**. Write the package format into `style.md` and follow it every episode.

## Covers

**Source frames:**
- Grab frames from the clips, not from the finished video (the finished video has the subtitles burned in): `ffmpeg -ss <seconds> -i clips/<id>.mp4 -frames:v 1 thumb_src/<id>_<seconds>.png`
- Lay them out with `dramakit/thumbkit.py`; see `examples/demo/covers.py` for an example. The default is 1080×1920 vertical; for a landscape YouTube thumbnail, first set `tk.W, tk.H = 1280, 720`.

**Make one per direction and pick one:**

| Version | Direction | Layout |
|---|---|---|
| A | Reveal | The person who says the reveal line, with the hook copy above (`tk.hook`) and the drama's name below |
| B | Reversal | Split top and bottom (`tk.split`): the moment of being pushed down / the moment of the face-slap (打臉), each with one line |
| C | Lead | The lead alone, with the drama's name and a genre tag (`tk.banner`) |

**Rules:**
- One cover says one thing: one face, one hook.
- Text must not cover a face, and must still be readable when shrunk to 180 px wide (the size in a phone's list).
- On vertical covers, keep key text at y < 1440: apps lay the title over the bottom edge.
- Put the episode number in a fixed place (`tk.badge`), with one layout for the whole series.
- The hook can spoil "what happened", but not "why".

## Titles

**Formula**: `S1E3 this episode's hook｜Drama name` (in Chinese: `S1E3 這一集的鉤子｜劇名`)

- **Season and episode go first.** When a phone pushes one episode to someone, the end of the title is cut off; the viewer needs the start to tell which season and episode this is, so they can find episode 1 or the next one. Keep the label short: `S1E3` plus a half-width space takes 5 characters, while `【第一季 第3集】` takes 9 full-width ones and pushes the hook off the screen. The same for compilations: `S1完全版 …`. After changing titles of videos already uploaded, `youtube_upload.py PLAN --refresh` updates them all at once.
- For the hook, use the episode's harshest line or biggest reversal: the line that reveals an identity, the moment of the face-slap.
- Add genre keywords to episode 1's title: comeback, rebirth, hidden identity, sweet romance…
- YouTube Shorts and Reels titles can add `#短劇`; keep the length within what a phone shows in full (about 30–40 characters).

## Description layout

1. One line about the series (the pitch from `plan.md`)
2. What happens in this episode (two or three sentences; don't spoil the cliffhanger)
3. A link to the series (the playlist), plus links to the previous and next episodes
4. Character list (name + one line of identity)
5. Disclaimers:
   - This video uses AI-generated images and voices (AutoIP); the characters and plot are fictional
   - Where the voice samples come from and how they are licensed (your own voice, actors you work with, synthetic voices)
   - Credits for the music and sound effects
6. Hashtags: `#短劇 #劇名 #類型`, 3–5 of them

- Tick the platform's disclosure for modified or synthetic content (in YouTube Studio: "Altered or synthetic content").
- The YouTube API's description limit is 5,000 bytes, not 5,000 characters: one Chinese character is 3 bytes.

Write the title, description and hashtags in each episode's `YouTube_SEO.txt` (template: `examples/series_template/s1e01_title/YouTube_SEO.txt`).

## The series playlist and release schedule

- One playlist per series, **sorted by episode** (a YouTube playlist must be set to "Manual" sorting first).
- Release at a fixed time (e.g. one episode every evening at 8 pm), and state the schedule in the description and a pinned comment.
- Put the full episode index in a pinned comment (links from episode 1 to the latest one), and update it with every release.
- Episode 1's cover and title matter most: it is the entry point to the whole series, so it's worth testing two or three versions.
- **Upload a whole-season compilation as well**: `python dramakit/compile.py <compilation folder>`, whose `project.py` lists in `PARTS` every episode (`end_card=False` drops an episode's end card, keep only the last one), bridge cards (`card=`) other videos (say the same character's MV), and a hook up front (`clips=[(episode folder, from, to), ...]`: the most gripping lines cut from the finished episodes, joined with a white flash; the subtitles are burned in, so a cut must not land inside the line before or after, and it warns when one does). Each part is levelled to the same loudness on its own; out come merged subtitles and `<NAME>_chapters.txt`, ready to paste into the description.

## Platform specs

| Platform | Aspect ratio | Length | Notes |
|---|---|---|---|
| YouTube Shorts | 9:16 | Up to 3 minutes | Custom thumbnails can only be uploaded in Studio on a computer |
| Instagram Reels | 9:16 | Per platform rules | The cover can be uploaded separately |
| TikTok | 9:16 | Per platform rules | |
| YouTube regular video | 16:9 | No limit | For multi-episode compilations, use `ASPECT="16:9"` or make a separate landscape version |

The subtitles are already burned into the picture; also upload the `.srt` as closed captions, which help hard-of-hearing viewers and search.

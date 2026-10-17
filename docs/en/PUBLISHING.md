# Publishing: thumbnails, Shorts thumbnails, YouTube SEO, social posts

[中文](../zh-TW/PUBLISHING.md) | English

## Thumbnails (A/B/C test)

**Source frames:**
- Grab frames straight from the finished video — no need to spend credits generating them: `ffmpeg -ss <seconds> -i out/xxx.mp4 -frames:v 1 thumb_src/<id>_<seconds>.png`
- Lay them out with `mvkit/thumbkit.py`; see `examples/demo/thumbs.py` for an example.

**Make one per direction and upload all three to YouTube Studio's "Test & compare":**

| Version | Direction | Layout |
|---|---|---|
| A | Musicality | The two lead singers face off across a diagonal blood seam (`thumbkit.split`), title at the bottom, small English text below |
| B | Hook | The most savage lyric line: first half struck through, second half delivers the twist |
| C | Ensemble / world | The band in the setting, title at the bottom, a slanted genre tag in the top-left corner |

**Rules:**
- The title must not cover a face.
- It must still be readable when shrunk to 320 px wide.
- One thumbnail says one thing.
- Use the same fonts as the video's subtitles.

## Shorts thumbnails

In the Shorts feed the video plays straight away, so viewers never see the thumbnail there. The thumbnail shows on the Shorts shelf on the home page, in search results and on the channel's Shorts tab.

**Source frames and size:**
- Export a 1080×1920 (9:16) JPG.
- Grab frames from `clips/<id>.mp4`, not from the vertical render, because the render has the lyrics burned in: `ffmpeg -ss <seconds> -i clips/<id>.mp4 -frames:v 1 thumb_src/<id>_<seconds>.png`
- Most sources are 16:9, so a portrait crop is upscaled about 2.5×. Pick close-ups, or a shot with the two leads close together. Faces in full-body wide shots are unreadable at shelf size.

**Layout:** `thumbkit` reads the canvas size at call time, so set the size first and the same helpers work. For `frame`, reuse the horizontal crop centre from the vertical edit's `focus`.

```python
tk.W, tk.H = 1080, 1920
im = tk.shade(tk.frame(src("<id>_<seconds>.png"), 1.0, 0.5, 0.5), "top", strength=150, width=0.22)
tk.title(im, (540, 150), "TITLE", 200, 0.12)
tk.badge(im)
tk.grain(im).save(os.path.join(out, "shorts_A_duet.jpg"), quality=95)
```

**Keep the three landscape directions, stacked vertically:**

| Version | Portrait layout |
|---|---|
| A | One shot with both leads close together, since a portrait frame is too narrow for a left/right split. The title goes in the empty space above their heads. |
| B | The face sits in the middle band, the hook line above the head, the title under the chin. |
| C | The setting or a painted scroll. The title can run vertically, with a seal for period pieces. |

**Rules (the landscape rules still apply):**
- Keep key text in the top three quarters, above y = 1440. The Shorts shelf on mobile lays the video title over the bottom edge of the thumbnail.
- It must still be readable at 180 px wide, the size of a card on the mobile Shorts shelf.
- The thumbnail and the Shorts title use the same hook. A hook-line title goes with B.

**Upload:**
- Custom Shorts thumbnails can only be uploaded in YouTube Studio on a computer: Content → Shorts → the Short's edit icon → Thumbnail → Upload file → Save. The account must be verified.
- The mobile app only lets you pick a frame from the video.
- "Test & compare" does not support Shorts. Compare the three side by side at shelf size and upload one.

## Titles

Offer 2–3 candidates, plus a separate Shorts title.

| Direction | Formula |
|---|---|
| Musicality | 【Title】Language + genre MV｜Band/characters selling point × selling point・English Genre (e.g. `【片名】語言＋曲風 MV｜樂團/角色 賣點 × 賣點・English Genre`) |
| Hook | The most savage lyric line! 《Title》genre Official MV (e.g. `最狠的一句歌詞！《片名》曲風 Official MV`) |
| Emotion | A lyric line that paints a picture｜《Title》English Genre MV (e.g. `一句有畫面的歌詞｜《片名》English Genre MV`) |
| Shorts | First line of the chorus! genre #shorts (e.g. `副歌第一句！曲風 #shorts`) |

## Description structure

1. Two or three lines of introduction in the main language (world + selling points) + an English paragraph
2. Viewing tips (headphones, highest quality), subscribe reminder
3. **Chapters**: `0:00 Overture｜…`. Times come from the full version's section starts, minus `cut`, plus the opening card's duration. The first chapter must be 0:00.
4. Band line-up / characters
5. Full lyrics (keep the lyricist's reading annotations)
6. Disclaimers:
   - Satire should add "All characters and settings are fictional and do not refer to any specific political party or individual."
   - If AI-generated imagery is used, name the production tools.
7. 5–8 hashtags

## Tags

- Mix the main language and English, about 300–400 characters.
- In this order: title → language + genre → English genre → characters → themes → technique (AI MV, kinetic typography).

## Upload settings checklist

- [ ] Upload the `.srt` subtitles: the picture already has kinetic subtitles, so leaving CC off by default is fine.
- [ ] "Altered or synthetic content": choose "Yes" for photorealistic AI people.
- [ ] Audience: not made for kids.
- [ ] Thumbnail A/B/C test.
- [ ] Upload the vertical cut as the Short (WORKFLOW.md, "Vertical cut"): a landscape video is not treated as a Short.
- [ ] Shorts thumbnail: upload one 9:16 `thumbnails/shorts_*.jpg` in YouTube Studio on a computer (see "Shorts thumbnails" above).
- [ ] End screen: subscribe + playlist (the end card's duration is reserved for this).
- [ ] No real people or party names in the title, thumbnail or tags.

## Social posts (X / Threads)

| Post | Content |
|---|---|
| Main post | One hook line + one line of introduction + link + 3 hashtags, with thumbnail B attached |
| Short-video post | Upload the short version directly (native video usually reaches more people than links; X free accounts are limited to about 2 min 20 s) + two chorus lines |
| English version | Post the next morning, aimed at US Eastern evening |
| Thread | 3 posts: introduction → a stretch of lyrics → link and previous works |

- 3–4 hashtags per post.
- Don't tag real political parties or politicians.

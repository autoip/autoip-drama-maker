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

When you upload with `mvkit/youtube_upload.py`, the subtitles, "altered or synthetic content", audience and the full MV's thumbnail are set for you (next section).

## Automatic upload (YouTube Data API)

`mvkit/youtube_upload.py` reads `YouTube_SEO.txt` and uploads the finished video, thumbnail and subtitles, filling in the title, description, tags, category (Music), languages and upload settings. Videos go up **private** by default: check them in Studio, then publish there.

**One-time setup**
1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/) and enable **YouTube Data API v3** under "APIs & Services" → "Library".
2. "OAuth consent screen": user type "External", an app name and a contact email, and add your own Google account as a test user. Then press "Publish app" to move it to **In production**. Left in "Testing", the login expires every 7 days. An unreviewed production app still works for yourself; at login Google warns that the app is unverified: "Advanced" → "Go to …".
3. "Credentials" → "Create credentials" → "OAuth client ID", application type "Desktop app". Download the JSON and save it as `~/.config/autoip-mv-maker/youtube_client_secret.json` (or point `YT_CLIENT_SECRET` elsewhere). Keep it out of the repo.
4. Install the libraries: `pip install google-api-python-client google-auth-oauthlib`.
5. Log in first with `python mvkit/youtube_upload.py --whoami`: sign in with the channel's Google account and allow access; it ends by printing the channel name. The login is cached next to the client file as `youtube_token.json`.
   - **If the Google account owns several channels (brand accounts), the login asks which one: pick the right one.** If it is wrong, delete `youtube_token.json` and log in again.
   - Once confirmed, set the channel id as `YT_CHANNEL_ID`; the script then refuses to upload to any other channel.
   - Run in the background, the browser may not open by itself: copy the URL the script prints and open it in a browser **on the same computer**, until the page says "The authentication flow has completed".
6. The channel must be phone-verified before custom thumbnails can be set.

**Usage**
```
python mvkit/youtube_upload.py PROJECT_DIR --dry-run                 # check and print what would be sent; no login, no upload
python mvkit/youtube_upload.py PROJECT_DIR --title A --playlist "Playlist title"
python mvkit/youtube_upload.py PROJECT_DIR --shorts --title B        # after the full MV
python mvkit/youtube_upload.py PROJECT_DIR --update                  # SEO file changed: rewrite title, description, tags, settings, thumbnail
```
- Scheduled release: `--publish-at 2026-10-25T20:00:00+08:00`; the video stays private until then.
- Uploaded video ids and the channel are kept in `PROJECT_DIR/youtube.json`, so a rerun never uploads twice or to another channel.
- Before uploading, the script checks the channel's latest 50 uploads: one whose title has the same 《title》 and is (or is not) a Short in the same way stops it. That also catches copies uploaded by hand in Studio: record that id in `youtube.json`, or pass `--allow-duplicate`.
- `--title` picks the title and the thumbnail: `thumbnails/thumb_<letter>_*.jpg`.

**Sections of `YouTube_SEO.txt` the script reads** (split on `==== header ====`, matched by words in the header)

| Header contains | Content |
|---|---|
| 標題 / Title | `A. …`, `B. …`; the line that mentions Shorts or 直式 (after its colon, or the next line) is the Shorts title |
| 說明欄 / Description + API | the description for the API; falls back to the plain description |
| Shorts + 說明欄 / Description | the Shorts description; `{full}` becomes the link to the full MV |
| 標籤 / Tags | comma separated |

**API limits** (the script checks them before sending)
- Title ≤ 100 characters, no `<` or `>`.
- Description ≤ **5,000 bytes**, not characters. A CJK character takes 3 bytes, so about 1,600 of them fill it. Keep the lyrics and chapters, shorten the sourcing, and put the full notes in a pinned comment.
- Tags ≤ 500 characters in total: commas count, and a tag with a space counts two quotation marks.
- Chapters: the first is 0:00, at least 3, each ≥ 10 seconds.
- Quota: 10,000 units a day, plus up to 100 uploads a day. One video with thumbnail, subtitles and playlist is about 500 units (the subtitles alone are 400). The API itself is free.

**Still by hand in Studio**
- End screen, cards, pinned comment, thumbnail "Test & compare".
- A custom thumbnail for a Short: YouTube keeps an API thumbnail as a 16:9 image (the 9:16 picture in the middle, blurred sides) and the Shorts shelf does not use it. So the script sets no thumbnail on a Short and reminds you to upload `thumbnails/shorts_<letter>_*.jpg` in Studio on a computer (see "Shorts thumbnails" above).

## Tidying playlists (YouTube Data API)

`mvkit/youtube_playlists.py` uses the same login (previous section) to tidy a channel's playlists, and can change the descriptions of many videos at once. Every command that writes prints its plan and changes nothing until you add `--apply`; it prints the channel first, and with `YT_CHANNEL_ID` set it touches no other channel.

```
python mvkit/youtube_playlists.py list                                    # every playlist and its videos, plus uploads in no playlist (read-only)
python mvkit/youtube_playlists.py sort "Season 1" ID1 ID2 ID3 --apply      # exactly this order (name every video in the playlist)
python mvkit/youtube_playlists.py sort "Season 1" --by oldest --apply       # or by upload date (oldest / newest) or title
python mvkit/youtube_playlists.py add "Shorts" ID --apply
python mvkit/youtube_playlists.py remove "All MVs" ID --dead --apply        # --dead: also drop "Deleted video" / "Private video" placeholders
python mvkit/youtube_playlists.py edit "Season 1" --title "New title" --description-file about.txt --apply
python mvkit/youtube_playlists.py delete "Old list" --apply                 # empty playlists only (or ones holding only deleted videos), else --force
python mvkit/youtube_playlists.py replace "Old series name" "New series name" --playlist "Season 2" --apply   # the same text in many descriptions
```
- A playlist is its id (`PL…`) or exact title; a video is its id or a link (`youtu.be/…`, `watch?v=…`, `shorts/…`).
- **Before sorting, set the playlist's default ordering to Manual** (open the playlist on YouTube → ⋮ → Playlist settings). Otherwise the API rejects positions, and it cannot change that setting itself.
- After a write, a re-read takes a few seconds to show it. The script waits until it does (up to 45 s) before reporting, so it never acts on stale data and adds a video twice.
- `replace` sends the whole snippet (title, tags, category, languages) back and changes only the description: `videos.update` clears every field it is not given, tags included.
- Quota: a read costs 1 unit, each write 50 (sorting writes once per video).
- `youtube_upload.py` also reads a playlist back after adding a video, and tells you to check in Studio if it is not there.

## Social posts (X / Threads)

| Post | Content |
|---|---|
| Main post | One hook line + one line of introduction + link + 3 hashtags, with thumbnail B attached |
| Short-video post | Upload the short version directly (native video usually reaches more people than links; X free accounts are limited to about 2 min 20 s) + two chorus lines |
| English version | Post the next morning, aimed at US Eastern evening |
| Thread | 3 posts: introduction → a stretch of lyrics → link and previous works |

- 3–4 hashtags per post.
- Don't tag real political parties or politicians.

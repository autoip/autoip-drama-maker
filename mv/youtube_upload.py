"""Upload a finished MV (or its Shorts cut) to YouTube with the copy in YouTube_SEO.txt (YouTube Data API v3).

usage: python mv/youtube_upload.py PROJECT_DIR [--shorts] [--title A] [--dry-run] [options]
       python mv/youtube_upload.py --whoami     log in (or reuse the login) and print which channel it uploads to
  --shorts               the vertical cut (EDITS["shorts"]) with the Shorts title, instead of the full MV
  --title A|B|C          which candidate title from the 標題 section (default A); also picks the thumbnail letter
  --privacy P            private (default: check it in YouTube Studio, publish there) | unlisted | public
  --publish-at ISO       scheduled release, e.g. 2026-10-25T20:00:00+08:00 (the video stays private until then)
  --playlist NAME|ID     add to the channel playlist with this exact title (it must exist already) or this id
  --thumb PATH           default thumbnails/thumb_<letter>_*.jpg. Shorts get no thumbnail unless --thumb is given: YouTube
                         keeps an API thumbnail as a letterboxed 16:9 image and the Shorts shelf ignores it, so upload
                         thumbnails/shorts_<letter>_*.jpg in YouTube Studio on a computer
  --no-captions          skip the .srt (captions.insert costs 400 of the default 10,000 daily units)
  --update               already uploaded (see youtube.json): rewrite title, description, tags, settings, thumbnail
  --dry-run              validate and print what would be sent; no login, nothing uploaded
  --allow-duplicate      upload even if a recent upload on the channel already carries the same 《title》 (same kind)
Copy comes from PROJECT_DIR/YouTube_SEO.txt, split on "==== header ====" lines:
  標題 / Title        "A. …" lines; the Shorts title is the line after the one that mentions Shorts or 直式
  說明欄 / Description a header that also says API wins (the API takes 5,000 *bytes*: about 1,600 CJK characters);
                       a header that also says Shorts is the Shorts description (falls back to the main one);
                       {full} is replaced with the link of the full MV once it is uploaded (upload the full MV first)
  標籤 / Tags          comma separated
Credentials: YT_CLIENT_SECRET = an OAuth client of type "Desktop app" (default
~/.config/dreamfab/youtube_client_secret.json; dreamfab/youtube_api.py); the login is cached next to it as youtube_token.json.
Keep both outside the repo. One Google account can own several channels (brand accounts): the login asks which one,
and every upload prints the channel; set YT_CHANNEL_ID to refuse any other. To switch, delete youtube_token.json.
Uploaded ids (and the channel) go to PROJECT_DIR/youtube.json, so a rerun never uploads twice or to another channel.
"""
import argparse, glob, json, os, re, subprocess, sys, time
from datetime import datetime
from common import load_project

from dreamfab.youtube_api import SECRET, youtube, wait_until, in_playlist
from dreamfab.youtube_log import record

ap = argparse.ArgumentParser()
ap.add_argument("project", nargs="?")
ap.add_argument("--whoami", action="store_true")
ap.add_argument("--shorts", action="store_true")
ap.add_argument("--title", default="A")
ap.add_argument("--privacy", choices=["private", "unlisted", "public"])
ap.add_argument("--publish-at")
ap.add_argument("--playlist")
ap.add_argument("--thumb")
ap.add_argument("--no-captions", action="store_true")
ap.add_argument("--update", action="store_true")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--allow-duplicate", action="store_true")
ap.add_argument("--category", default="10")   # Music
ap.add_argument("--audio-lang")                # default: the subtitle language (RENDER["lang"])
A = ap.parse_args()


def channel(yt):
    ch = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
    print(f"  channel     {ch['snippet']['title']} ({ch['id']})")
    return ch["id"]


if A.whoami or not A.project:
    if not A.whoami:
        ap.error("PROJECT_DIR is required")
    channel(youtube())
    sys.exit(0)

proj = load_project(A.project)
D = proj.DIR
KIND = "shorts" if A.shorts else "full"
LANG = proj.RENDER.get("lang", "zh-TW")
problems = []


# ---------------------------------------------------------------- copy
def sections(text):
    parts = re.split(r"^=+\s*(.+?)\s*=+\s*$", text, flags=re.M)
    return [(h, b.strip("\n")) for h, b in zip(parts[1::2], parts[2::2])]


seo = os.path.join(D, "YouTube_SEO.txt")
S = sections(open(seo, encoding="utf-8").read())
pick = lambda *keys: [(h, b) for h, b in S if any(k in h for k in keys)]

tsec = "\n".join(b for _, b in pick("標題", "Title"))
titles = dict(re.findall(r"^([A-Z])\.\s*(.+?)\s*$", tsec, flags=re.M))
lines, short_title = tsec.splitlines(), ""
for i, l in enumerate(lines):
    m = re.search(r"(?:Shorts|直式).*?[：:]\s*(.*)$", l)
    if m:   # "1 分鐘直式版（Shorts）標題：" with the title on the same line or the next one
        short_title = m[1].strip() or next((n.strip() for n in lines[i + 1:] if n.strip()), "")
        break
title = short_title if A.shorts else titles.get(A.title.upper(), "")

descs = pick("說明欄", "Description")
main = [b for h, b in descs if "Shorts" not in h]
api = [b for h, b in descs if "API" in h and "Shorts" not in h]
desc = ((api or main or [""])[0] if not A.shorts else
        next((b for h, b in descs if "Shorts" in h), (api or main or [""])[0])).strip()

tags = [t.strip() for t in re.split(r"[,，\n]", "\n".join(b for _, b in pick("標籤", "Tags"))) if t.strip()]
tag_cost = sum(len(t) + (2 if " " in t else 0) for t in tags) + max(len(tags) - 1, 0)   # spaces -> counted with quotes

state_p = os.path.join(D, "youtube.json")
state = json.load(open(state_p, encoding="utf-8")) if os.path.exists(state_p) else {}
done = state.get(KIND)
if "{full}" in desc:
    if state.get("full"):
        desc = desc.replace("{full}", "https://youtu.be/" + state["full"]["id"])
    else:
        problems.append("the description links {full}: upload the full MV first")

# ---------------------------------------------------------------- files
E = proj.EDITS[KIND]
base = os.path.join(D, "out", proj.NAME + E.get("suffix", ""))
video, srt = base + ".mp4", f"{base}.{LANG}.srt"
letter = A.title.upper()
thumb = A.thumb or ("" if A.shorts else next(iter(sorted(glob.glob(os.path.join(D, "thumbnails", f"thumb_{letter}_*.jpg")))), ""))
studio_thumb = "" if thumb else next(iter(sorted(glob.glob(os.path.join(D, "thumbnails", f"shorts_{letter}_*.jpg")))), "")
dur = 0.0
if os.path.exists(video):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout or 0)
else:
    problems.append(f"no video {video} (render it first)")

# ---------------------------------------------------------------- checks (limits from developers.google.com/youtube/v3/docs/videos)
if not title:
    problems.append(f"no {'Shorts' if A.shorts else letter} title in {seo}")
if len(title) > 100:
    problems.append(f"title is {len(title)} characters (max 100)")
for name, s in (("title", title), ("description", desc)):
    if re.search("[<>]", s):
        problems.append(f"{name} contains < or > (not allowed)")
nbytes = len(desc.encode("utf-8"))
if nbytes > 5000:
    blocks = sorted(((len(b.encode("utf-8")), b.strip().splitlines()[0][:30]) for b in re.split(r"\n\s*\n", desc) if b.strip()), reverse=True)
    problems.append(f"description is {nbytes} bytes (max 5,000 bytes; CJK = 3 bytes each). Add a '說明欄（API）' section. "
                    "Biggest blocks: " + "; ".join(f"{n} B {h}" for n, h in blocks[:5]))
if tag_cost > 500:
    problems.append(f"tags count as {tag_cost} characters (max 500; commas count, a tag with spaces counts its quotes)")
chap = [(int(m[0] or 0) * 3600 + int(m[1]) * 60 + int(m[2]), m[3]) for m in
        re.findall(r"^(?:(\d+):)?(\d{1,2}):(\d{2})\s+(.+)$", desc, flags=re.M)]
if chap and not A.shorts:
    gaps = [b[0] - a[0] for a, b in zip(chap, chap[1:])] + ([dur - chap[-1][0]] if dur else [])
    if chap[0][0] != 0 or len(chap) < 3 or min(gaps, default=0) < 10:
        problems.append("chapters need a first 0:00, at least 3 timestamps and >= 10 s each "
                        f"(shortest {min(gaps, default=0):.0f} s)")
if A.shorts and dur > 180:
    problems.append(f"Shorts cut is {dur:.0f} s (max 180)")
if thumb and os.path.getsize(thumb) > 2_000_000:
    problems.append(f"thumbnail {os.path.basename(thumb)} is {os.path.getsize(thumb) / 1e6:.1f} MB (YouTube takes <= 2 MB)")
captions = os.path.exists(srt) and not A.no_captions

privacy = "private" if A.publish_at else (A.privacy or "private")
status = dict(privacyStatus=privacy, selfDeclaredMadeForKids=False, containsSyntheticMedia=True, embeddable=True, license="youtube")
if A.publish_at:
    status["publishAt"] = A.publish_at
snippet = dict(title=title, description=desc, tags=tags, categoryId=A.category,
               defaultLanguage=LANG, defaultAudioLanguage=A.audio_lang or LANG)

print(f"{KIND}: {os.path.relpath(video, D)} ({dur:.1f} s)")
print(f"  title       {title}")
print(f"  description {len(desc)} characters = {nbytes} bytes, {len(chap)} chapters")
print(f"  tags        {len(tags)} tags, {tag_cost}/500")
print(f"  thumbnail   {os.path.relpath(thumb, D) if thumb else '-'}"
      + (f"  (Shorts: upload {os.path.relpath(studio_thumb, D)} in Studio)" if studio_thumb else ""))
print(f"  captions    {os.path.relpath(srt, D) if captions else '-'} ({LANG})")
print(f"  status      {privacy}{' until ' + A.publish_at if A.publish_at else ''}, not made for kids, altered/synthetic content: yes, category {A.category}")
print(f"  playlist    {A.playlist or '-'}")
print(f"  quota       ~{50 * A.update + 50 * bool(thumb) + 400 * (captions and not A.update) + 51 * bool(A.playlist and not done)}"
      f" of 10,000 units/day{'' if A.update else ' + 1 of 100 uploads/day'}")
if done:
    print(f"  already uploaded: https://youtu.be/{done['id']}" + ("" if A.update else "  -> nothing to do (use --update to rewrite the copy)"))
for p in problems:
    print("  !!", p)
if problems or A.dry_run or (done and not A.update):
    sys.exit(1 if problems else 0)


# ---------------------------------------------------------------- upload
def media(path, mimetype, resumable=False):
    from googleapiclient.http import MediaFileUpload
    return MediaFileUpload(path, mimetype=mimetype, chunksize=16 * 1024 * 1024 if resumable else -1, resumable=resumable)


def save(vid, updated=False):
    """The upload record; an --update keeps the first upload time and notes when it was updated."""
    now = datetime.now().isoformat(timespec="seconds")
    state["channel"] = cid
    first = (state.get(KIND) or {}).get("at") if updated else None
    state[KIND] = dict(id=vid, title=title, at=first or now, **({"updated": now} if updated else {}))
    json.dump(state, open(state_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


from googleapiclient.errors import HttpError

yt = youtube()
cid = channel(yt)
want = os.environ.get("YT_CHANNEL_ID") or state.get("channel")
if want and cid != want:
    sys.exit(f"  !! logged in to channel {cid}, expected {want} (YT_CHANNEL_ID / youtube.json): delete "
             f"{os.path.join(os.path.dirname(SECRET), 'youtube_token.json')} and log in again, picking the right channel")
if not done and not A.allow_duplicate:   # also catches copies uploaded by hand in Studio
    key = (re.findall(r"《(.+?)》", title) or [title])[0]
    r = yt.playlistItems().list(part="snippet", playlistId="UU" + cid[2:], maxResults=50).execute()
    dup = [(i["snippet"]["resourceId"]["videoId"], i["snippet"]["title"]) for i in r["items"]
           if key in i["snippet"]["title"] and ("#shorts" in i["snippet"]["title"].lower()) == A.shorts]
    if dup:
        sys.exit("  !! already on the channel: " + "; ".join(f"https://youtu.be/{v} {t}" for v, t in dup)
                 + f" -> record it in {state_p} as {KIND!r}, or pass --allow-duplicate")
if done:
    vid = done["id"]
    cur = yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]
    keep = {k: cur[k] for k in ("privacyStatus", "publishAt") if k in cur and not (A.privacy or A.publish_at)}
    yt.videos().update(part="snippet,status", body=dict(id=vid, snippet=snippet, status={**status, **keep})).execute()
    save(vid, updated=True)
    record(vid, "update", title, D, KIND)
    print("  updated", vid)
else:
    req = yt.videos().insert(part="snippet,status", body=dict(snippet=snippet, status=status),
                             media_body=media(video, "video/mp4", resumable=True))
    resp, tries = None, 0
    while resp is None:
        try:
            st, resp = req.next_chunk()
            if st:
                print(f"  {st.progress() * 100:.0f}%", flush=True)
        except HttpError as e:
            if e.resp.status not in (500, 502, 503, 504) or tries >= 8:
                raise
            tries += 1
            time.sleep(2 ** tries)
        except OSError:
            if tries >= 8:
                raise
            tries += 1
            time.sleep(2 ** tries)
    vid = resp["id"]
    save(vid)
    record(vid, "upload", title, D, KIND)
    print("  uploaded", vid)
    if captions:
        yt.captions().insert(part="snippet", body=dict(snippet=dict(videoId=vid, language=LANG, name="", isDraft=False)),
                             media_body=media(srt, "application/octet-stream")).execute()
        record(vid, "captions", os.path.basename(srt), D, KIND)
        print("  captions", os.path.basename(srt))
if thumb:
    try:
        yt.thumbnails().set(videoId=vid, media_body=media(thumb, "image/png" if thumb.lower().endswith(".png") else "image/jpeg")).execute()
        record(vid, "thumbnail", os.path.basename(thumb), D, KIND)
        print("  thumbnail", os.path.basename(thumb))
    except HttpError as e:   # e.g. the channel is not verified for custom thumbnails, or a Shorts cut
        print("  !! thumbnail not set:", getattr(e, "reason", e), "-> upload it in YouTube Studio")
if A.playlist and not done:
    pid = A.playlist if re.fullmatch(r"(PL|OL)[\w-]{10,}", A.playlist) else None
    page = None
    while not pid:
        r = yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=page).execute()
        pid = next((p["id"] for p in r["items"] if p["snippet"]["title"] == A.playlist), None)
        page = r.get("nextPageToken")
        if not pid and not page:
            sys.exit(f"  !! no playlist titled {A.playlist!r} (create it in YouTube Studio); the video itself is uploaded")
    yt.playlistItems().insert(part="snippet", body=dict(snippet=dict(
        playlistId=pid, resourceId=dict(kind="youtube#video", videoId=vid)))).execute()
    # read it back: once a Short reported as added showed up in a different playlist of the channel
    if wait_until(lambda: in_playlist(yt, pid, vid), f"video {vid} in playlist {pid}"):
        record(vid, "playlist", pid, D, KIND)
        print("  playlist", pid)
print(f"https://studio.youtube.com/video/{vid}/edit  -> still by hand: end screen, cards, pinned comment"
      + (f", the Shorts thumbnail ({os.path.basename(studio_thumb) or 'thumbnails/shorts_*.jpg'})" if A.shorts else ", thumbnail Test & compare")
      + f"; log each: python dreamfab/youtube_log.py add {vid} end_screen|card|pin TEXT")

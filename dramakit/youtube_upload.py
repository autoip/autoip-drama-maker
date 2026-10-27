"""Upload a series to YouTube from an upload plan (YouTube Data API v3): scheduled episodes, a playlist, cross links.

usage: python dramakit/youtube_upload.py PLAN.json [--dry-run] [--whoami] [--max N] [--refresh] [--mv-side]
  (default)   upload the next videos in plan order that are not uploaded yet (at most --max, default 5: one upload is
              ~1,600 of the 10,000 daily quota units), each private until its publish_at, added to the playlist
  --refresh   rewrite every uploaded video's description now that more links are known (50 units each)
  --mv-side   put the plan's mv_side lines on top of those (already public) videos' descriptions (MV -> drama)
  --dry-run   check everything and print the plan; no login, nothing sent
  --whoami    log in (or reuse the login) and print the channel
PLAN.json: {"channel": "UC...", "playlist": {"title", "description"},
            "videos": [{"key": "EP1", "title", "description", "tags", "video", "thumbnail", "publish_at", "short"}],
            "mv_side": {"<video id>": "a line with {EP1} ..."}}
Paths are relative to the plan's folder's parent (the series folder). In descriptions {PLAYLIST}, {COMP} and {<key>}
become links once known; a line whose link is not known yet is left out (run --refresh after the last upload).
Shorts get no API thumbnail (YouTube letterboxes it and the Shorts shelf ignores it): set those in YouTube Studio.
Login: YT_CLIENT_SECRET = an OAuth client of type "Desktop app" (default ~/.config/autoip-mv-maker/youtube_client_secret.json),
cached next to it as youtube_token.json; keep both outside the repo. The plan's "channel" is the only channel it acts on.
Uploaded ids go to youtube.json next to the plan, so a rerun never uploads twice.
"""
import json, os, re, subprocess, sys, time
from datetime import datetime

A = sys.argv[1:]
flag = lambda f: f in A
PLAN = next(a for a in A if a.endswith(".json"))
MAX = int(A[A.index("--max") + 1]) if "--max" in A else 5
plan = json.load(open(PLAN, encoding="utf-8"))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(PLAN)))
STATE = os.path.join(os.path.dirname(os.path.abspath(PLAN)), "youtube.json")
state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"videos": {}}
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
SECRET = os.environ.get("YT_CLIENT_SECRET", os.path.expanduser("~/.config/autoip-mv-maker/youtube_client_secret.json"))
TOKEN = os.path.join(os.path.dirname(SECRET), "youtube_token.json")


def save():
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def links():
    out = {k: f"https://youtu.be/{v['id']}" for k, v in state["videos"].items()}
    if state.get("playlist"):
        out["PLAYLIST"] = f"https://www.youtube.com/playlist?list={state['playlist']}"
    return out


def fill(text):
    """{KEY} -> link; a line that still needs an unknown link is dropped."""
    known, keep = links(), []
    for line in text.split("\n"):
        keys = re.findall(r"\{(\w+)\}", line)
        if all(k in known for k in keys):
            keep.append(re.sub(r"\{(\w+)\}", lambda m: known[m.group(1)], line))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep))


def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout or 0)


# ---------------------------------------------------------------- checks
problems = []
for v in plan["videos"]:
    p = os.path.join(BASE, v["video"])
    v["path"], v["dur"] = p, dur_of(p) if os.path.exists(p) else 0
    v["short"] = v.get("short", v["dur"] <= 180)
    if not os.path.exists(p):
        problems.append(f"{v['key']}: no video {v['video']}")
    if len(v["title"]) > 100 or re.search("[<>]", v["title"] + v["description"]):
        problems.append(f"{v['key']}: title over 100 characters, or < > in the copy")
    if len(v["description"].encode("utf-8")) > 5000:
        problems.append(f"{v['key']}: description over 5,000 bytes")
    if sum(len(t) + 2 * (" " in t) for t in v["tags"]) + len(v["tags"]) - 1 > 500:
        problems.append(f"{v['key']}: tags over 500 characters")
    if v.get("publish_at") and datetime.fromisoformat(v["publish_at"]).timestamp() < time.time() + 600 \
            and v["key"] not in state["videos"]:
        problems.append(f"{v['key']}: publish_at {v['publish_at']} is not at least 10 minutes ahead")
todo = [v for v in plan["videos"] if v["key"] not in state["videos"]][:MAX]
mode = "refresh" if flag("--refresh") else "mv-side" if flag("--mv-side") else "upload"
print(f"plan {os.path.relpath(PLAN)}: {len(plan['videos'])} videos, {len(state['videos'])} uploaded, channel {plan.get('channel')}")
if mode == "upload":
    for v in todo:
        thumb = "" if v["short"] else v.get("thumbnail", "")
        print(f"  {v['key']:5} {v['dur']:6.1f}s {'Short' if v['short'] else 'video'}  {v.get('publish_at', 'private')}  {v['title']}"
              + (f"  [+thumbnail {thumb}]" if thumb else ""))
    units = 1600 * len(todo) + 50 * len(todo) + 50 * sum(1 for v in todo if not v["short"]) + 50 * (not state.get("playlist"))
    print(f"  ~{units} of 10,000 quota units today")
for p in problems:
    print("  !!", p)
if problems or flag("--dry-run"):
    sys.exit(1 if problems else 0)


# ---------------------------------------------------------------- login
def youtube():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    if not os.path.exists(SECRET):
        sys.exit(f"no OAuth client at {SECRET} (set YT_CLIENT_SECRET)")
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES) if os.path.exists(TOKEN) else None
    if creds and not creds.valid and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print("  login expired:", e); creds = None
    if not creds or not creds.valid:
        print("  log in with the channel's Google account in the browser (pick the right channel)")
        creds = InstalledAppFlow.from_client_secrets_file(SECRET, SCOPES).run_local_server(port=0, prompt="consent")
        open(TOKEN, "w").write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

yt = youtube()
ch = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
print(f"  logged in   {ch['snippet']['title']} ({ch['id']})")
if plan.get("channel") and ch["id"] != plan["channel"]:
    sys.exit(f"  !! this login is channel {ch['id']}, the plan is for {plan['channel']}: delete {TOKEN} and log in again")
if flag("--whoami"):
    sys.exit(0)


def body(v):
    status = dict(privacyStatus="private", selfDeclaredMadeForKids=False, containsSyntheticMedia=True, embeddable=True,
                  license="youtube")
    if v.get("publish_at"):
        status["publishAt"] = v["publish_at"]
    snippet = dict(title=v["title"], description=fill(v["description"]), tags=v["tags"], categoryId=plan.get("category", "1"),
                   defaultLanguage=plan.get("lang", "zh-TW"), defaultAudioLanguage=plan.get("lang", "zh-TW"))
    return dict(snippet=snippet, status=status)


def playlist():
    if not state.get("playlist"):
        p = plan["playlist"]
        r = yt.playlists().insert(part="snippet,status", body=dict(
            snippet=dict(title=p["title"], description=p.get("description", ""), defaultLanguage=plan.get("lang", "zh-TW")),
            status=dict(privacyStatus="public"))).execute()
        state["playlist"] = r["id"]; save()
        print("  playlist created", r["id"])
    return state["playlist"]


if mode == "upload":
    pid = playlist()
    for v in todo:
        req = yt.videos().insert(part="snippet,status", body=body(v),
                                 media_body=MediaFileUpload(v["path"], mimetype="video/mp4", chunksize=16 * 1024 * 1024, resumable=True))
        resp, tries = None, 0
        while resp is None:
            try:
                _, resp = req.next_chunk()
            except (HttpError, OSError) as e:
                if isinstance(e, HttpError) and e.resp.status not in (500, 502, 503, 504) or tries >= 8:
                    raise
                tries += 1; time.sleep(2 ** tries)
        vid = resp["id"]
        state["videos"][v["key"]] = dict(id=vid, title=v["title"], publish_at=v.get("publish_at"),
                                         at=datetime.now().isoformat(timespec="seconds"))
        save()
        print(f"  {v['key']:5} uploaded https://youtu.be/{vid}  ({v.get('publish_at', 'private')})", flush=True)
        if not v["short"] and v.get("thumbnail"):
            try:
                yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(os.path.join(BASE, v["thumbnail"]), mimetype="image/jpeg")).execute()
                print("        thumbnail", v["thumbnail"])
            except HttpError as e:
                print("        !! thumbnail not set:", e, "-> set it in YouTube Studio")
        yt.playlistItems().insert(part="snippet", body=dict(snippet=dict(
            playlistId=pid, position=sorted(state["videos"], key=lambda k: [x["key"] for x in plan["videos"]].index(k)).index(v["key"]),
            resourceId=dict(kind="youtube#video", videoId=vid)))).execute()
    left = [v["key"] for v in plan["videos"] if v["key"] not in state["videos"]]
    print("  still to upload:", ", ".join(left) or "nothing (run --refresh to fill in every link)")
elif mode == "refresh":
    for v in plan["videos"]:
        if v["key"] in state["videos"]:
            vid = state["videos"][v["key"]]["id"]
            cur = yt.videos().list(part="snippet", id=vid).execute()["items"][0]["snippet"]
            new = fill(v["description"])
            if cur.get("description") != new:
                b = body(v)
                yt.videos().update(part="snippet", body=dict(id=vid, snippet=b["snippet"])).execute()
                print(f"  {v['key']:5} description updated")
else:
    for vid, text in plan.get("mv_side", {}).items():
        sn = yt.videos().list(part="snippet", id=vid).execute()["items"][0]["snippet"]
        desc = sn.get("description", "")
        new = [l for l in fill(text).split("\n") if l and l not in desc]   # lines whose links are known, not there yet
        if not new:
            print(f"  {vid}: nothing new (already there, or the links are not known yet)"); continue
        # our block (lines starting 🎬) stays one block on top; later lines join it
        head, _, rest = desc.partition("\n\n") if desc.startswith("🎬") else ("", "", desc)
        sn["description"] = "\n".join(([head] if head else []) + new) + "\n\n" + rest
        keep = {k: sn[k] for k in ("title", "description", "categoryId", "tags", "defaultLanguage", "defaultAudioLanguage") if k in sn}
        try:
            yt.videos().update(part="snippet", body=dict(id=vid, snippet=keep)).execute()
            print(f"  {vid}: added on top of the description:", " / ".join(new))
        except HttpError as e:
            print(f"  !! {vid}: {e}")

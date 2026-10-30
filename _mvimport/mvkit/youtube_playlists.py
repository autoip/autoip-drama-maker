"""Tidy a channel's playlists, and fix text in many video descriptions at once (YouTube Data API v3).

usage: python mvkit/youtube_playlists.py list [--json OUT]
       python mvkit/youtube_playlists.py sort PLAYLIST VIDEO ... [--apply]           exactly this order
       python mvkit/youtube_playlists.py sort PLAYLIST --by oldest|newest|title [--apply]
       python mvkit/youtube_playlists.py add PLAYLIST VIDEO ... [--apply]
       python mvkit/youtube_playlists.py remove PLAYLIST [VIDEO ...] [--dead] [--apply]
       python mvkit/youtube_playlists.py edit PLAYLIST [--title T] [--description-file F] [--apply]
       python mvkit/youtube_playlists.py delete PLAYLIST [--force] [--apply]
       python mvkit/youtube_playlists.py replace OLD NEW (VIDEO ... | --playlist PLAYLIST) [--apply]
PLAYLIST = a playlist id (PL…) or its exact title. VIDEO = a video id or a youtu.be / watch?v= / shorts/ link.
Commands that write print their plan and change nothing unless --apply is given. The channel is printed first;
set YT_CHANNEL_ID to refuse any other (one Google account can own several channels).
  list      every playlist with its videos (position, privacy, length, upload date), then the channel's uploads
            that are in no playlist. Read-only; --json saves the same data.
  sort      YouTube only takes a position when the playlist's default ordering is Manual (YouTube: the playlist ->
            ⋮ -> Playlist settings); the API cannot change that setting. A VIDEO list must name every video in the
            playlist once; --by sorts by upload date or title instead (deleted/private placeholders go last).
  remove    --dead also removes "Deleted video" / "Private video" placeholders.
  edit      a playlist's title and/or description; whatever is not given is kept.
  delete    only a playlist that is empty or holds nothing but deleted/private placeholders, unless --force.
            Cannot be undone.
  replace   replace text in video descriptions (a renamed series or playlist, a dead link). The whole snippet is
            sent back with only the description changed: videos.update clears every snippet field it is not given,
            tags included.
Reads lag a few seconds behind writes, so after writing the script re-reads until the change shows (up to 45 s).
Quota: a read costs 1 unit, a write 50 (10,000 a day by default). Credentials: as youtube_upload.py.
"""
import argparse, json, re, sys
from youtube_api import youtube, channel, wait_until

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("cmd", choices=["list", "sort", "add", "remove", "edit", "delete", "replace"])
ap.add_argument("args", nargs="*")
ap.add_argument("--apply", action="store_true")
ap.add_argument("--by", choices=["oldest", "newest", "title"])
ap.add_argument("--dead", action="store_true")
ap.add_argument("--title")
ap.add_argument("--description-file")
ap.add_argument("--force", action="store_true")
ap.add_argument("--playlist")
ap.add_argument("--json")
A = ap.parse_args()
DEAD = ("Deleted video", "Private video")


def video_id(s):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", s)
    return m.group(1) if m else s


def playlist_id(s):
    if re.fullmatch(r"(PL|OL|UU|FL|LL)[\w-]{10,}", s):
        return s
    hits = [p["id"] for p in playlists() if p["snippet"]["title"] == s]
    if len(hits) != 1:
        sys.exit(f"  !! {len(hits)} playlists titled {s!r}: pass the id instead (see `list`)")
    return hits[0]


def pages(call, **kw):
    out, page = [], None
    while True:
        r = call(**kw, maxResults=50, pageToken=page).execute()
        out += r["items"]; page = r.get("nextPageToken")
        if not page:
            return out


def playlists():
    return pages(yt.playlists().list, part="snippet,status,contentDetails", mine=True)


def items(pid):
    return sorted(pages(yt.playlistItems().list, part="snippet,contentDetails", playlistId=pid),
                  key=lambda i: i["snippet"]["position"])


def vid(it):
    return it["snippet"]["resourceId"]["videoId"]


def dead(it):
    return it["snippet"]["title"] in DEAD


def videos(ids, part="snippet,status,contentDetails"):
    out = {}
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 50):
        for v in yt.videos().list(part=part, id=",".join(ids[i:i + 50])).execute()["items"]:
            out[v["id"]] = v
    return out


def plan(lines, writes):
    for l in lines:
        print(("  [plan] " if not A.apply else "  ") + l)
    print(f"  {writes} write(s), ~{50 * writes} quota units" + ("" if A.apply else "  (dry run: add --apply to write)"))
    return A.apply and writes > 0


def need(n, what):
    if len(A.args) < n:
        ap.error(f"{A.cmd} needs {what}")


yt = youtube()
ch = channel(yt, lock=True)

if A.cmd == "list":
    dump, seen = dict(channel=ch["id"], playlists=[], loose=[]), set()
    pls = playlists()
    its = {p["id"]: items(p["id"]) for p in pls}
    uploads = pages(yt.playlistItems().list, part="contentDetails", playlistId=ch["contentDetails"]["relatedPlaylists"]["uploads"])
    info = videos([vid(i) for l in its.values() for i in l] + [u["contentDetails"]["videoId"] for u in uploads])
    for p in pls:
        print(f"\n== {p['snippet']['title']}  [{p['status']['privacyStatus']}]  {p['id']}  ({len(its[p['id']])})")
        rows = []
        for it in its[p["id"]]:
            v = vid(it); seen.add(v); d = info.get(v)
            priv, dur, at = (d["status"]["privacyStatus"], d["contentDetails"]["duration"], d["snippet"]["publishedAt"][:10]) if d else ("-", "", "")
            print(f"  {it['snippet']['position']:3d}. {v}  {priv:8s} {dur:9s} {at}  {it['snippet']['title']}")
            rows.append(dict(position=it["snippet"]["position"], video=v, title=it["snippet"]["title"], privacy=priv, duration=dur, published=at))
        dump["playlists"].append(dict(id=p["id"], title=p["snippet"]["title"], privacy=p["status"]["privacyStatus"],
                                      description=p["snippet"].get("description", ""), items=rows))
    print("\n== uploads in no playlist")
    for u in uploads:
        v = u["contentDetails"]["videoId"]; d = info.get(v)
        if v not in seen and d:
            print(f"  {v}  {d['status']['privacyStatus']:8s} {d['contentDetails']['duration']:9s} {d['snippet']['publishedAt'][:10]}  {d['snippet']['title']}")
            dump["loose"].append(dict(video=v, title=d["snippet"]["title"], privacy=d["status"]["privacyStatus"]))
    if A.json:
        json.dump(dump, open(A.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n  saved", A.json)

elif A.cmd == "sort":
    need(1, "PLAYLIST")
    pid = playlist_id(A.args[0]); its = items(pid); cur = [vid(i) for i in its]
    if len(set(cur)) != len(cur):
        sys.exit("  !! the playlist holds the same video twice: remove the extra copy first")
    if A.by:
        info = videos([v for i, v in zip(its, cur) if not dead(i)], part="snippet")
        live = [v for v in cur if v in info]
        key = (lambda v: info[v]["snippet"]["title"]) if A.by == "title" else (lambda v: info[v]["snippet"]["publishedAt"])
        order = sorted(live, key=key, reverse=A.by == "newest") + [v for v in cur if v not in info]
    else:
        need(2, "PLAYLIST and the videos in their new order (or --by)")
        order = [video_id(a) for a in A.args[1:]]
        if sorted(order) != sorted(cur):
            sys.exit(f"  !! the list must name every video in the playlist once\n     missing: {sorted(set(cur) - set(order))}"
                     f"\n     not in the playlist: {sorted(set(order) - set(cur))}")
    title = {vid(i): i["snippet"]["title"] for i in its}
    moves = sum(a != b for a, b in zip(cur, order))
    if plan([f"{pos:3d}. {v}  {title[v][:60]}" for pos, v in enumerate(order)], moves and len(order)):
        from googleapiclient.errors import HttpError
        by = {vid(i): i for i in its}
        for pos, v in enumerate(order):
            try:
                yt.playlistItems().update(part="snippet", body=dict(id=by[v]["id"], snippet=dict(
                    playlistId=pid, resourceId=by[v]["snippet"]["resourceId"], position=pos))).execute()
            except HttpError as e:
                if "manualSortRequired" in str(e):
                    sys.exit("  !! YouTube only takes positions when the playlist's default ordering is Manual: open the "
                             "playlist on YouTube -> ⋮ -> Playlist settings -> Default video ordering: Manual, then rerun")
                raise
        if wait_until(lambda: [vid(i) for i in items(pid)] == order, f"new order of {pid}"):
            print("  sorted", pid)

elif A.cmd == "add":
    need(2, "PLAYLIST and VIDEO ids")
    pid = playlist_id(A.args[0]); have = {vid(i) for i in items(pid)}
    new = [v for v in dict.fromkeys(video_id(a) for a in A.args[1:]) if v not in have]
    info = videos(new, part="snippet")
    for v in new:
        if v not in info:
            sys.exit(f"  !! no video {v} (or not visible to this login)")
    if plan([f"add {v}  {info[v]['snippet']['title'][:60]}" for v in new] +
            [f"already there: {v}" for v in dict.fromkeys(video_id(a) for a in A.args[1:]) if v in have], len(new)):
        for v in new:
            yt.playlistItems().insert(part="snippet", body=dict(snippet=dict(playlistId=pid, resourceId=dict(kind="youtube#video", videoId=v)))).execute()
        if wait_until(lambda: set(new) <= {vid(i) for i in items(pid)}, f"added videos in {pid}"):
            print("  added", len(new))

elif A.cmd == "remove":
    need(1, "PLAYLIST")
    pid = playlist_id(A.args[0]); want = {video_id(a) for a in A.args[1:]}
    gone = [i for i in items(pid) if vid(i) in want or (A.dead and dead(i))]
    if not gone:
        sys.exit("  nothing to remove")
    if plan([f"remove {vid(i)}  {i['snippet']['title'][:60]}" for i in gone], len(gone)):
        for i in gone:
            yt.playlistItems().delete(id=i["id"]).execute()
        ids = {i["id"] for i in gone}
        if wait_until(lambda: not ids & {i["id"] for i in items(pid)}, f"removals in {pid}"):
            print("  removed", len(gone))

elif A.cmd == "edit":
    need(1, "PLAYLIST")
    pid = playlist_id(A.args[0])
    sn = yt.playlists().list(part="snippet", id=pid).execute()["items"][0]["snippet"]
    title = A.title or sn["title"]
    desc = open(A.description_file, encoding="utf-8").read().strip() if A.description_file else sn.get("description", "")
    if len(title) > 150 or len(desc) > 5000:
        sys.exit("  !! a playlist title takes at most 150 characters and a description 5,000")
    changes = [f"title {sn['title']!r} -> {title!r}"] if title != sn["title"] else []
    if desc != sn.get("description", ""):
        changes.append(f"description {len(sn.get('description', ''))} -> {len(desc)} characters")
    if plan(changes or ["no change"], 1 if changes else 0):
        body = dict(title=title, description=desc)
        if sn.get("defaultLanguage"):
            body["defaultLanguage"] = sn["defaultLanguage"]
        yt.playlists().update(part="snippet", body=dict(id=pid, snippet=body)).execute()
        now = lambda: yt.playlists().list(part="snippet", id=pid).execute()["items"][0]["snippet"]
        if wait_until(lambda: (now()["title"], now().get("description", "")) == (title, desc), f"edit of {pid}"):
            print("  edited", pid)

elif A.cmd == "delete":
    need(1, "PLAYLIST")
    pid = playlist_id(A.args[0]); its = items(pid)
    p = yt.playlists().list(part="snippet", id=pid).execute()["items"][0]["snippet"]
    live = [i for i in its if not dead(i)]
    if live and not A.force:
        sys.exit(f"  !! {p['title']!r} still holds {len(live)} live video(s); remove them first, or pass --force")
    if plan([f"delete playlist {pid} {p['title']!r} ({len(its)} item(s), {len(live)} live)"], 1):
        yt.playlists().delete(id=pid).execute()
        if wait_until(lambda: not yt.playlists().list(part="id", id=pid).execute()["items"], f"deletion of {pid}"):
            print("  deleted", pid)

elif A.cmd == "replace":
    need(2, "OLD and NEW text")
    old, new = A.args[0], A.args[1]
    ids = [video_id(a) for a in A.args[2:]]
    if A.playlist:
        ids += [vid(i) for i in items(playlist_id(A.playlist)) if not dead(i)]
    if not ids:
        ap.error("replace needs VIDEO ids or --playlist")
    info = videos(ids, part="snippet")
    todo, lines = [], []
    for v in dict.fromkeys(ids):
        sn = info.get(v, {}).get("snippet")
        if not sn:
            lines.append(f"{v}: not found"); continue
        d = sn.get("description", ""); n = d.count(old)
        if not n:
            lines.append(f"{v}: no match  {sn['title'][:50]}"); continue
        nd = d.replace(old, new)
        lines.append(f"{v}: {n} replacement(s), {len(d)} -> {len(nd)} characters  {sn['title'][:50]}")
        lines += [f"      | {l.strip()[:90]}" for l in d.splitlines() if old in l][:3]
        todo.append((v, sn, nd))
    if plan(lines, len(todo)):
        keep = ("title", "description", "tags", "categoryId", "defaultLanguage", "defaultAudioLanguage")
        for v, sn, nd in todo:
            body = {k: sn[k] for k in keep if k in sn}; body["description"] = nd
            yt.videos().update(part="snippet", body=dict(id=v, snippet=body)).execute()
        want = {v: nd for v, _, nd in todo}
        check = lambda: all(x["snippet"].get("description") == want[x["id"]] for x in videos(list(want), part="snippet").values())
        if wait_until(check, "description changes"):
            print("  updated", len(todo))

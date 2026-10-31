"""A log of everything done to the channel's videos after the render: upload, copy updates, captions, thumbnail,
playlist, publish, comments and pins, end screens, cards, links between episodes, for every line and project: the
youtube_log table of the shared Dreamfab database (dreamfab/db.py; $DREAMFAB_DB, default ~/.config/dreamfab/dreamfab.db).
The libraries' indexes are rebuilt from files; this table is never rebuilt, so the pages can show what was done and when.

The uploaders (drama/youtube_upload.py, mv/youtube_upload.py) record their own steps. What is done by hand or in a
browser (YouTube Studio: end screen, cards, pinning a comment) is recorded with the CLI right after:

Publishing by hand in Studio is caught by sync: it asks YouTube (read only) where every logged video stands, keeps that
in the youtube_status table, and logs the publish of each video that went public, at the time YouTube gives.

How much goes out a day: the workflow switch youtube.daily_max (default 6; 0 = no limit) caps the videos a channel
uploads or publishes on one day, Shorts included, so it is not throttled. The uploaders stop at the cap (their
--over-limit goes past it); stats shows today's count and what is in stock.

usage: python dreamfab/youtube_log.py add VIDEO ACTION [TEXT] [--project DIR] [--kind full|shorts|EP1...]
           ACTION: upload update captions thumbnail playlist publish comment pin end_screen card link (or any word)
       python dreamfab/youtube_log.py show [VIDEO ...]          the log, newest first (all videos, or these)
       python dreamfab/youtube_log.py import ROOT [ROOT ...]    record the uploads already in youtube.json files
                                                              (each once; safe to run again)
       python dreamfab/youtube_log.py sync [ROOT ...]           import, then ask YouTube where each video stands
       python dreamfab/youtube_log.py stats [--days N]          per channel: out per day against the cap, in stock
"""
import glob, json, os, sys
from collections import defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run as a script: the repo root
from dreamfab import db as shared
from dreamfab.workflow import get as workflow

LABELS = {"upload": "上傳", "update": "更新標題與說明欄", "captions": "字幕", "thumbnail": "封面", "playlist": "加入播放清單",
          "publish": "公開", "comment": "留言", "pin": "置頂留言", "end_screen": "片尾", "card": "資訊卡", "link": "說明欄連結"}


def connect(path=None):
    """The shared database, with its youtube_log table."""
    return shared.connect(path)


def record(video, action, text="", project=None, kind=None, at=None, force=False):
    """Add one entry; never lets a logging problem stop an upload. The uploaders' entries follow the workflow switch
    youtube.log; force (the add command) writes regardless."""
    try:
        if not force and not workflow("youtube.log", project):
            return
        db = connect()
        with db:
            db.execute("INSERT INTO youtube_log VALUES (?,?,?,?,?,?)", (at or datetime.now().isoformat(timespec="seconds"),
                                                                       video, action, text or "", project and os.path.abspath(project), kind))
        db.close()
    except Exception as e:   # pragma: no cover - a locked or unwritable file
        print(f"  (youtube log not written: {e})")


def history(videos=None, limit=None):
    """[dict(at, video, action, label, text, project, kind)] newest first; [] when there is no log yet."""
    if not os.path.exists(shared.PATH):
        return []
    db = connect()
    q, args = "SELECT at, video, action, text, project, kind FROM youtube_log", []
    if videos is not None:
        videos = [v for v in videos if v]
        if not videos:
            return []
        q += f" WHERE video IN ({','.join('?' * len(videos))})"; args = videos
    q += " ORDER BY at DESC, rowid DESC" + (f" LIMIT {int(limit)}" if limit else "")
    rows = [dict(zip(("at", "video", "action", "text", "project", "kind"), r)) for r in db.execute(q, args)]
    db.close()
    for r in rows:
        r["label"] = LABELS.get(r["action"], r["action"])
    return rows


def done(video):
    """{action} already recorded for a video (what the library pages tick off)."""
    return {r["action"] for r in history([video])}


def import_uploads(roots):
    """Each upload in youtube.json files under the roots (MV and explainer projects, drama youtube*/ folders) once."""
    db, n = connect(), 0
    have = {(v, a) for v, a in db.execute("SELECT video, action FROM youtube_log")}
    for root in roots:
        for p in glob.glob(os.path.join(root, "**", "youtube.json"), recursive=True):
            st = json.load(open(p, encoding="utf-8"))
            proj = os.path.dirname(p)
            entries = [(k, v) for k, v in st.items() if isinstance(v, dict) and v.get("id")] + \
                      [(k, v) for k, v in (st.get("videos") or {}).items() if v.get("id")]
            for kind, v in entries:
                if (v["id"], "upload") not in have:
                    at = str(v.get("at") or "")[:19] or None
                    db.execute("INSERT INTO youtube_log VALUES (?,?,?,?,?,?)", (at, v["id"], "upload", v.get("title", ""), proj, kind))
                    have.add((v["id"], "upload")); n += 1
                if v.get("published") and (v["id"], "publish") not in have:
                    db.execute("INSERT INTO youtube_log VALUES (?,?,?,?,?,?)", (v["published"], v["id"], "publish", "", proj, kind))
                    have.add((v["id"], "publish")); n += 1
    db.commit(); db.close()
    return n


STATUS = ("CREATE TABLE IF NOT EXISTS youtube_status (video TEXT PRIMARY KEY, channel TEXT, privacy TEXT, publish_at TEXT, "
          "published_at TEXT, title TEXT, checked TEXT)")


def local(ts):
    """A YouTube UTC time (2026-10-31T01:34:00Z) as local time without a zone, like the log's own entries."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().replace(tzinfo=None).isoformat(timespec="seconds")


def sync(roots=("projects",)):
    """Import the youtube.json uploads, then ask YouTube (read only) about every logged video: its channel, privacy and
    publish times go into youtube_status, and a video that is public without a publish entry gets one."""
    import_uploads(roots)
    from dreamfab.youtube_api import youtube
    db, yt = connect(), youtube()
    db.execute(STATUS)
    logged = {v for (v,) in db.execute("SELECT video FROM youtube_log WHERE action = 'upload'")}
    for ch in yt.channels().list(part="contentDetails", mine=True).execute()["items"]:   # uploads made by hand in Studio
        tok = None
        while True:
            r = yt.playlistItems().list(part="snippet", playlistId=ch["contentDetails"]["relatedPlaylists"]["uploads"],
                                        maxResults=50, pageToken=tok).execute()
            for i in r["items"]:
                v, title = i["snippet"]["resourceId"]["videoId"], i["snippet"]["title"]
                if v not in logged:
                    db.execute("INSERT INTO youtube_log VALUES (?,?,?,?,?,?)", (local(i["snippet"]["publishedAt"]), v, "upload",
                                                                               title, None, "shorts" if "#shorts" in title.lower() else "full"))
                    logged.add(v)
            tok = r.get("nextPageToken")
            if not tok:
                break
    vids = sorted({v for (v,) in db.execute("SELECT video FROM youtube_log") if v and len(v) == 11})
    published = {v for (v,) in db.execute("SELECT video FROM youtube_log WHERE action = 'publish'")}
    where = dict(db.execute("SELECT video, MAX(project) FROM youtube_log GROUP BY video"))
    kinds = dict(db.execute("SELECT video, MAX(kind) FROM youtube_log GROUP BY video"))
    now, seen, added = datetime.now().isoformat(timespec="seconds"), set(), 0
    for i in range(0, len(vids), 50):
        for it in yt.videos().list(part="status,snippet", id=",".join(vids[i:i + 50]), maxResults=50).execute()["items"]:
            st, sn = it["status"], it["snippet"]
            pub = local(sn["publishedAt"]) if st["privacyStatus"] == "public" and sn.get("publishedAt") else None
            db.execute("INSERT OR REPLACE INTO youtube_status VALUES (?,?,?,?,?,?,?)",
                       (it["id"], sn["channelId"], st["privacyStatus"], st.get("publishAt") and local(st["publishAt"]), pub,
                        sn["title"], now))
            seen.add(it["id"])
            if pub and it["id"] not in published:
                db.execute("INSERT INTO youtube_log VALUES (?,?,?,?,?,?)",
                           (pub, it["id"], "publish", "(sync: the time YouTube gives)", where.get(it["id"]), kinds.get(it["id"])))
                added += 1
    for v in set(vids) - seen:   # deleted, or on a channel this login cannot see
        db.execute("INSERT OR REPLACE INTO youtube_status (video, privacy, checked) VALUES (?, 'gone', ?)", (v, now))
    db.commit(); db.close()
    return len(seen), added


def line_of(project, kind, title=""):
    """(line, format) of a logged video: drama plans live in youtube*/ folders; an explainer's project.py says
    LINE = "explain"; the rest are MV projects. Without a project (uploaded in Studio) the title tells: 短劇, 解說, else
    MV. format: Shorts or 長片 (a drama episode or compilation: 短劇)."""
    p = os.path.normpath(project or "")
    if os.path.basename(p).startswith("youtube") or not project and "短劇" in (title or ""):
        return "短劇", "短劇"
    if not project and "解說" in (title or ""):
        return "解說", "Shorts" if kind == "shorts" else "長片"
    try:
        explain = 'LINE = "explain"' in open(os.path.join(p, "project.py"), encoding="utf-8").read()
    except OSError:
        explain = False
    return ("解說" if explain else "MV"), ("Shorts" if kind == "shorts" else "長片")


def channel_of(project):
    """The channel a project uploads to: its youtube.json, or the upload plan next to it."""
    for name in ("youtube.json", "upload_plan.json"):
        try:
            ch = json.load(open(os.path.join(project, name), encoding="utf-8")).get("channel")
        except (OSError, ValueError):
            continue
        if ch:
            return ch
    return None


def videos():
    """[dict(video, project, channel, line, fmt, privacy, publish_at)] for every logged video, with what sync last saw."""
    if not os.path.exists(shared.PATH):
        return []
    db = connect()
    db.execute(STATUS)
    status = {r[0]: r for r in db.execute("SELECT video, channel, privacy, publish_at, title FROM youtube_status")}
    rows = db.execute("SELECT video, MAX(project), MAX(kind) FROM youtube_log GROUP BY video").fetchall()
    db.close()
    out, chans = [], {}
    for v, project, kind in rows:
        st = status.get(v, (v, None, None, None, ""))
        if project not in chans:
            chans[project] = channel_of(project) if project else None
        line, fmt = line_of(project, kind, st[4])
        out.append(dict(video=v, project=project, channel=st[1] or chans[project] or "?", line=line, fmt=fmt,
                        privacy=st[2], publish_at=st[3]))
    return out


def day_counts(days=7):
    """{channel: {day: (uploaded, published, out)}} for the last days; out counts a video once however many of its
    steps fell on that day (what the daily cap counts)."""
    ch = {v["video"]: v["channel"] for v in videos()}
    if not ch:
        return {}
    first = (date.today() - timedelta(days=days - 1)).isoformat()
    db = connect()
    got = defaultdict(lambda: defaultdict(lambda: (set(), set())))
    for at, v, action in db.execute("SELECT at, video, action FROM youtube_log WHERE action IN ('upload', 'publish') "
                                    "AND at >= ?", (first,)):
        got[ch.get(v, "?")][at[:10]][action == "publish"].add(v)
    db.close()
    return {c: {d: (len(u), len(p), len(u | p)) for d, (u, p) in per.items()} for c, per in got.items()}


def out_today(channel):
    """Videos the channel has uploaded or published today."""
    return day_counts(1).get(channel, {}).get(date.today().isoformat(), (0, 0, 0))[2]


def quota(channel, project=None):
    """How many more videos the channel may put out today under youtube.daily_max, or None without a cap."""
    cap = workflow("youtube.daily_max", project)
    return max(0, cap - out_today(channel)) if cap else None


def stock():
    """{channel: {(line, format): {privacy: n}}} for the logged videos (privacy as sync last saw it: public, scheduled,
    private, unlisted, gone; never synced: unknown)."""
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for v in videos():
        out[v["channel"]][(v["line"], v["fmt"])]["scheduled" if v["publish_at"] else v["privacy"] or "unknown"] += 1
    return out


def print_stats(days=7):
    cap = workflow("youtube.daily_max")
    counts, st = day_counts(days), stock()
    today = date.today().isoformat()
    for ch in sorted(set(counts) | set(st)):
        per = counts.get(ch, {})
        n = per.get(today, (0, 0, 0))[2]
        print(f"channel {ch}: today {n} out" + (f" of {cap} (room for {max(0, cap - n)})" if cap else " (no daily cap)"))
        for d in sorted(per, reverse=True):
            print(f"  {d}  uploaded {per[d][0]:>2}  published {per[d][1]:>2}  out {per[d][2]:>2}")
        for (line, fmt), by in sorted(st.get(ch, {}).items()):
            print(f"  {line} {fmt}: " + ", ".join(f"{k} {by[k]}" for k in ("public", "scheduled", "private", "unlisted",
                                                                              "unknown", "gone") if by.get(k)))


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("add", "show", "import", "sync", "stats"):
        sys.exit(__doc__)

    def opt(name):
        return a[a.index(name) + 1] if name in a else None
    plain = [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and a[i - 1] not in ("--project", "--kind")]
    if a[0] == "add":
        if len(plain) < 2:
            sys.exit(__doc__)
        record(plain[0], plain[1], " ".join(plain[2:]), opt("--project"), opt("--kind"), force=True)
        print(f"logged {plain[0]} {plain[1]}  ({shared.PATH})")
    elif a[0] == "import":
        print(f"{import_uploads(plain or ['projects'])} entries added  ({shared.PATH})")
    elif a[0] == "sync":
        n, added = sync(plain or ["projects"])
        print(f"{n} videos checked, {added} publishes logged  ({shared.PATH})")
    elif a[0] == "stats":
        print_stats(int(opt("--days") or 7))
    else:
        for r in history(plain or None):
            print(f"{r['at']}  {r['video']}  {r['label']}  {r['text'][:80]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

"""A log of everything done to the channel's videos after the render: upload, copy updates, captions, thumbnail,
playlist, publish, comments and pins, end screens, cards, links between episodes. One SQLite file for every line and
project, next to the YouTube login (YT_LOG_DB, default ~/.config/dreamfab/youtube_log.db), so it outlives each
series' library.db (which is rebuilt from files) and the library pages can show what was done and when.

The uploaders (drama/youtube_upload.py, mv/youtube_upload.py) record their own steps. What is done by hand or in a
browser (YouTube Studio: end screen, cards, pinning a comment) is recorded with the CLI right after:

usage: python dreamfab/youtube_log.py add VIDEO ACTION [TEXT] [--project DIR] [--kind full|shorts|EP1...]
           ACTION: upload update captions thumbnail playlist publish comment pin end_screen card link (or any word)
       python dreamfab/youtube_log.py show [VIDEO ...]          the log, newest first (all videos, or these)
       python dreamfab/youtube_log.py import ROOT [ROOT ...]    record the uploads already in youtube.json files
                                                              (each once; safe to run again)
"""
import glob, json, os, sqlite3, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run as a script: the repo root
from dreamfab.youtube_api import SECRET
from dreamfab.workflow import get as workflow

DB = os.environ.get("YT_LOG_DB") or os.path.join(os.path.dirname(SECRET), "youtube_log.db")
LABELS = {"upload": "上傳", "update": "更新標題與說明欄", "captions": "字幕", "thumbnail": "封面", "playlist": "加入播放清單",
          "publish": "公開", "comment": "留言", "pin": "置頂留言", "end_screen": "片尾", "card": "資訊卡", "link": "說明欄連結"}


def connect(path=None):
    path = path or DB
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS actions (at TEXT, video TEXT, action TEXT, text TEXT, project TEXT, kind TEXT)")
    db.execute("CREATE INDEX IF NOT EXISTS actions_video ON actions (video)")
    return db


def record(video, action, text="", project=None, kind=None, at=None, force=False):
    """Add one entry; never lets a logging problem stop an upload. The uploaders' entries follow the workflow switch
    youtube.log; force (the add command) writes regardless."""
    try:
        if not force and not workflow("youtube.log", project):
            return
        db = connect()
        with db:
            db.execute("INSERT INTO actions VALUES (?,?,?,?,?,?)", (at or datetime.now().isoformat(timespec="seconds"), video,
                                                                   action, text or "", project and os.path.abspath(project), kind))
        db.close()
    except Exception as e:   # pragma: no cover - a locked or unwritable file
        print(f"  (youtube log not written: {e})")


def history(videos=None, limit=None):
    """[dict(at, video, action, label, text, project, kind)] newest first; [] when there is no log yet."""
    if not os.path.exists(DB):
        return []
    db = sqlite3.connect(DB)
    q, args = "SELECT at, video, action, text, project, kind FROM actions", []
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
    have = {(v, a) for v, a in db.execute("SELECT video, action FROM actions")}
    for root in roots:
        for p in glob.glob(os.path.join(root, "**", "youtube.json"), recursive=True):
            st = json.load(open(p, encoding="utf-8"))
            proj = os.path.dirname(p)
            entries = [(k, v) for k, v in st.items() if isinstance(v, dict) and v.get("id")] + \
                      [(k, v) for k, v in (st.get("videos") or {}).items() if v.get("id")]
            for kind, v in entries:
                if (v["id"], "upload") not in have:
                    at = str(v.get("at") or "")[:19] or None
                    db.execute("INSERT INTO actions VALUES (?,?,?,?,?,?)", (at, v["id"], "upload", v.get("title", ""), proj, kind))
                    have.add((v["id"], "upload")); n += 1
                if v.get("published") and (v["id"], "publish") not in have:
                    db.execute("INSERT INTO actions VALUES (?,?,?,?,?,?)", (v["published"], v["id"], "publish", "", proj, kind))
                    have.add((v["id"], "publish")); n += 1
    db.commit(); db.close()
    return n


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("add", "show", "import"):
        sys.exit(__doc__)

    def opt(name):
        return a[a.index(name) + 1] if name in a else None
    plain = [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and a[i - 1] not in ("--project", "--kind")]
    if a[0] == "add":
        if len(plain) < 2:
            sys.exit(__doc__)
        record(plain[0], plain[1], " ".join(plain[2:]), opt("--project"), opt("--kind"), force=True)
        print(f"logged {plain[0]} {plain[1]}  ({DB})")
    elif a[0] == "import":
        print(f"{import_uploads(plain or ['projects'])} entries added  ({DB})")
    else:
        for r in history(plain or None):
            print(f"{r['at']}  {r['video']}  {r['label']}  {r['text'][:80]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

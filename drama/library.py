"""A browsable index of one series: every episode, shot, clip, character, set, render, job and upload in one SQLite
file, and a small local web page to look through it (standard library only).

usage: python dramakit/library.py index SERIES_DIR                     -> SERIES_DIR/library.db (rebuilt each time)
       python dramakit/library.py serve SERIES_DIR [--port 8765]       index, then http://127.0.0.1:8765; re-indexes by
                                                                       itself when files change (checked every 15 s)
       python dramakit/library.py serve SERIES_DIR --no-index          serve the existing library.db as it is
SERIES_DIR is the folder above the episodes (cast/, sets/, voices/, music/, s1e01_x/, s1e02_x/ ...). Episodes are its
sub-folders with a project.py; a compilation folder (compile.py, PARTS) is listed with them. The overview groups them
by TITLE (one section per season, e.g. s1e01_x and s2e01_y with different titles). Covers: covers/out/<folder>.jpg or
covers/out/s<season>/ep01.jpg (season 1 may use covers/out/ep01.jpg); without one, the render's poster is shown. Media are probed with
ffprobe once and cached by size and date in the same file. Credits are what aip_runner.py recorded as charged, else
estimated from the job files (common.estimate): a reshot clip only counts its last run. YouTube details come from SERIES_DIR/youtube*/upload_plan.json and youtube.json
(youtube_upload.py; one folder per plan, e.g. youtube/ and youtube_s2/ for two seasons). The server listens on 127.0.0.1 only and serves files from inside SERIES_DIR only.
"""
import glob, html, json, mimetypes, os, re, shutil, sqlite3, subprocess, sys, threading, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from common import load_project, parse_edl, estimate

SCHEMA = """
CREATE TABLE IF NOT EXISTS probe (path TEXT PRIMARY KEY, size INT, mtime REAL, dur REAL, w INT, h INT);
DROP TABLE IF EXISTS episodes; DROP TABLE IF EXISTS shots; DROP TABLE IF EXISTS edit_rows; DROP TABLE IF EXISTS cast;
DROP TABLE IF EXISTS sets; DROP TABLE IF EXISTS files; DROP TABLE IF EXISTS jobs; DROP TABLE IF EXISTS youtube;
DROP TABLE IF EXISTS meta;
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE episodes (folder TEXT PRIMARY KEY, kind TEXT, number INT, label TEXT, name TEXT, title TEXT,
  n_shots INT, script TEXT, main_video TEXT, main_dur REAL, ng_video TEXT, cover TEXT, credits INT);
CREATE TABLE shots (folder TEXT, id TEXT, scene TEXT, set_key TEXT, kind TEXT, speaker TEXT, line TEXT, delivery TEXT,
  act TEXT, cast_keys TEXT, clip TEXT, clip_dur REAL, speech TEXT, heard TEXT, match REAL, takes INT, in_main INT,
  PRIMARY KEY (folder, id));
CREATE TABLE edit_rows (folder TEXT, mode TEXT, n INT, src TEXT, inn REAL, dur REAL, flags TEXT, over INT, note TEXT);
CREATE TABLE cast (key TEXT PRIMARY KEY, name TEXT, title TEXT, descr TEXT, sheet TEXT, voice TEXT, variants TEXT,
  episodes TEXT);
CREATE TABLE sets (key TEXT PRIMARY KEY, name TEXT, descr TEXT, file TEXT, episodes TEXT);
CREATE TABLE files (path TEXT PRIMARY KEY, kind TEXT, folder TEXT, size INT, mtime REAL, dur REAL, w INT, h INT, thumb TEXT);
CREATE TABLE jobs (folder TEXT, file TEXT, id TEXT, endpoint TEXT, status TEXT, uuid TEXT, credits INT, out TEXT,
  prompt TEXT, line TEXT);
CREATE TABLE youtube (key TEXT, folder TEXT PRIMARY KEY, video_id TEXT, title TEXT, publish_at TEXT, uploaded_at TEXT,
  thumbnail TEXT, description TEXT, tags TEXT, pinned TEXT);
"""
MEDIA = {".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".png", ".jpg", ".jpeg", ".webp"}
TEXT = {".md", ".txt", ".srt", ".json", ".py"}
SKIP_DIRS = {"__pycache__", "img", ".library"}
WATCH_S = 15   # serve: how often to look for changed files
THUMB_KINDS = {"clip", "take", "raw", "output", "ng_video", "voice_raw", "keyframe"}


def kind_of(rel):
    """What a file is, from where it sits."""
    p, ext = rel.replace("\\", "/"), os.path.splitext(rel)[1].lower()
    parts = p.split("/")
    rules = [("/clips/_takes/", "take"), ("/clips/_raw/", "raw"), ("/clips/", "clip"), ("/kf/", "keyframe"),
             ("cast/candidates/", "cast_candidate"), ("cast/", "cast"), ("sets/", "set"), ("voices/raw/", "voice_raw"),
             ("voices/", "voice"), ("music/", "music"), ("sfx/", "sfx"), ("covers/out/", "cover"), ("covers/", "cover_source"),
             ("rejected/", "rejected"), ("fonts/", "font")]
    for key, k in rules:
        if ("/" + p).find("/" + key.strip("/") + "/") >= 0 or p.startswith(key):
            return k
    if "/out/" in "/" + p:
        return "subtitle" if ext == ".srt" else "ng_video" if "_NG" in parts[-1] else "output" if ext == ".mp4" else "output_other"
    if ext == ".md":
        return "doc"
    if ext == ".json":
        return "data"
    if parts[-1].lower().startswith("youtube_seo"):
        return "seo"
    if ext in (".jpg", ".png") and re.match(r"(qc_|review|cands|sheet)", parts[-1]):
        return "review"
    if parts[-1] == "project.py":
        return "project"
    return "other"


def probe(paths, db):
    """ffprobe duration / size for media, cached by (size, mtime)."""
    cached = {r[0]: r for r in db.execute("SELECT path, size, mtime, dur, w, h FROM probe")}
    need = [p for p in paths if p not in cached or (cached[p][1], cached[p][2]) != (os.path.getsize(p), os.path.getmtime(p))]

    def one(p):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "json", p],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            j = json.loads(r.stdout or "{}")
        except ValueError:
            j = {}
        st = next((s for s in j.get("streams", []) if s.get("width")), {})
        d = float(j.get("format", {}).get("duration") or 0)
        return p, os.path.getsize(p), os.path.getmtime(p), d if d < 36000 else 0, st.get("width"), st.get("height")

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, need))
    db.executemany("INSERT OR REPLACE INTO probe VALUES (?,?,?,?,?,?)", rows)
    return {r[0]: r for r in db.execute("SELECT path, size, mtime, dur, w, h FROM probe")}


def make_thumbs(series, items):
    """A small still per video (cached in SERIES_DIR/.library/thumbs by path and date) for the page's posters."""
    out_dir = os.path.join(series, ".library", "thumbs")
    os.makedirs(out_dir, exist_ok=True)

    def one(item):
        p, d = item
        key = re.sub(r"[^\w.-]", "_", os.path.relpath(p, series)) + f"_{int(os.path.getmtime(p))}.jpg"
        t = os.path.join(out_dir, key)
        if not os.path.exists(t):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(1.0, (d or 2) / 2):.2f}", "-i", p, "-frames:v", "1",
                            "-vf", "scale=-2:360", t], capture_output=True)
        return p, os.path.relpath(t, series).replace("\\", "/") if os.path.exists(t) else None

    with ThreadPoolExecutor(8) as ex:
        return dict(ex.map(one, items))


def index(series):
    """Rebuild SERIES_DIR/library.db: built in a copy (it keeps the probe cache) and swapped in when done."""
    series = os.path.abspath(series)
    final, tmp = os.path.join(series, "library.db"), os.path.join(series, "library.db.tmp")
    if os.path.exists(final):
        shutil.copyfile(final, tmp)
    elif os.path.exists(tmp):
        os.remove(tmp)
    db = build(series, sqlite3.connect(tmp))
    db.close()
    for _ in range(20):   # a reader may hold the old file for a moment (Windows)
        try:
            os.replace(tmp, final)
            break
        except PermissionError:
            time.sleep(0.25)
    return sqlite3.connect(final)


def build(series, db):
    rel = lambda p: os.path.relpath(p, series).replace("\\", "/") if p else None
    db.executescript(SCHEMA)
    # ---------- files
    found = []
    for root, dirs, names in os.walk(series):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("render")]
        for n in names:
            if os.path.splitext(n)[1].lower() in MEDIA | TEXT and n != "library.db":
                found.append(os.path.join(root, n))
    pr = probe([p for p in found if os.path.splitext(p)[1].lower() in MEDIA], db)
    thumbs = make_thumbs(series, [(p, pr[p][3]) for p in found if p in pr and kind_of(rel(p)) in THUMB_KINDS and p.endswith(".mp4")])
    for p in found:
        r = rel(p)
        folder = r.split("/")[0] if os.path.exists(os.path.join(series, r.split("/")[0], "project.py")) else ""
        q = pr.get(p) or (p, os.path.getsize(p), os.path.getmtime(p), None, None, None)
        db.execute("INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?)", (r, kind_of(r), folder, q[1], q[2], q[3], q[4], q[5], thumbs.get(p)))
    dur = lambda r: (db.execute("SELECT dur FROM files WHERE path=?", (r,)).fetchone() or [None])[0]
    # ---------- episodes, shots, edits, cast, sets, jobs
    cast, sets = {}, {}
    folders = sorted(d for d in os.listdir(series) if os.path.exists(os.path.join(series, d, "project.py")))
    for folder in folders:
        D = os.path.join(series, folder)
        try:
            proj = load_project(D)
        except Exception as e:   # one broken project.py should not stop the index
            print(f"  !! {folder}: {e}"); continue
        number = getattr(proj, "EPISODE", None)
        kind = "compilation" if hasattr(proj, "PARTS") else "episode"
        name = getattr(proj, "NAME", folder)
        main = rel(os.path.join(D, "out", name + ".mp4")) if os.path.exists(os.path.join(D, "out", name + ".mp4")) else None
        ng = rel(os.path.join(D, "out", name + "_NG.mp4")) if os.path.exists(os.path.join(D, "out", name + "_NG.mp4")) else None
        scripts = sorted(glob.glob(os.path.join(D, "劇本_v*.md")) + glob.glob(os.path.join(D, "script*.md")))
        season = (re.match(r"s(\d+)", folder) or [None, "1"])[1]
        # covers/out/<folder>.jpg, or covers/out/s2/ep01.jpg; the first season may keep covers/out/ep01.jpg
        tries = [f"covers/out/{folder}.jpg"] + ([f"covers/out/s{season}/ep{number:02d}.jpg"] if number else [])             + ([f"covers/out/ep{number:02d}.jpg"] if number and season == "1" else [])             + ([f"covers/out/s{season}/compilation_vertical.jpg"] + (["covers/out/compilation_vertical.jpg"] if season == "1" else [])
               if kind == "compilation" else [])
        cover = next((c for c in tries if os.path.exists(os.path.join(series, c))), None)
        speech = json.load(open(os.path.join(D, "speech.json"), encoding="utf-8")) if os.path.exists(os.path.join(D, "speech.json")) else {}
        scene_set = {s[0]: s[1] for s in getattr(proj, "SCENES", [])}
        edits = getattr(proj, "EDITS", {})
        main_srcs = set()
        for mode, e in edits.items():
            text = e.get("shots", "") if isinstance(e, dict) else str(e)
            notes = [ln.split("#", 1)[1].strip() if "#" in ln else "" for ln in text.split("\n") if ln.split("#")[0].strip()]
            for n, (r, note) in enumerate(zip(parse_edl(text), notes)):
                db.execute("INSERT INTO edit_rows VALUES (?,?,?,?,?,?,?,?,?)", (folder, mode, n, r["src"], r["inn"], r["dur"],
                           json.dumps(r["flags"], ensure_ascii=False), int(r["over"]), note))
                if mode == "main":
                    main_srcs.add(r["src"])
        for s in getattr(proj, "SHOTS", []):
            say = s.get("say") or (None, None, None)
            clip = os.path.join(D, "clips", s["id"] + ".mp4")
            takes = len(glob.glob(os.path.join(D, "clips", "_takes", s["id"] + "_v*.mp4")))
            sp = speech.get(s["id"], {})
            db.execute("INSERT INTO shots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                folder, s["id"], s.get("scene"), scene_set.get(s.get("scene")), s.get("kind", "M"), say[0], say[1],
                say[2] if len(say) > 2 else None, s.get("act"), ",".join(s.get("cast", [])),
                rel(clip) if os.path.exists(clip) else None, dur(rel(clip)) if os.path.exists(clip) else None,
                json.dumps(sp.get("speech")) if sp.get("speech") else None, sp.get("heard"), sp.get("match"), takes,
                int(s["id"] in main_srcs)))
        for k, c in getattr(proj, "CAST", {}).items():
            e = cast.setdefault(k, dict(name=c.get("name"), title=c.get("title"), descr=c.get("desc"), sheet=None, voice=None,
                                        variants={}, episodes=[]))
            e.update({x: c[y] for x, y in (("name", "name"), ("title", "title"), ("descr", "desc")) if c.get(y)})
            stem = lambda p: os.path.splitext(os.path.basename(p))[0]
            for x, y in (("sheet", "file"), ("voice", "voice")):
                if c.get(y) and os.path.exists(os.path.join(D, c[y])):
                    p = rel(os.path.normpath(os.path.join(D, c[y])))
                    if x == "sheet" and e["sheet"] and e["sheet"] != p:   # a later look (another costume): keep both
                        e["variants"][stem(p)] = p
                    else:
                        e[x] = e[x] or p
            for f in (c.get("by_set") or {}).values():   # the sheet put into each set (restage.py), every look
                if os.path.exists(os.path.join(D, f)):
                    e["variants"][stem(f)] = rel(os.path.normpath(os.path.join(D, f)))
            e["episodes"].append(folder)
        for k, s in getattr(proj, "SETS", {}).items():
            e = sets.setdefault(k, dict(name=s.get("name"), descr=s.get("desc"), file=None, episodes=[]))
            if s.get("file") and os.path.exists(os.path.join(D, s["file"])):
                e["file"] = rel(os.path.normpath(os.path.join(D, s["file"])))
            e["episodes"].append(folder)
        credits = 0
        for jf in glob.glob(os.path.join(D, "jobs", "*_jobs.json")):
            st = json.load(open(jf + ".state", encoding="utf-8")) if os.path.exists(jf + ".state") else {}
            for j in json.load(open(jf, encoding="utf-8")):
                s = st.get(j["id"], {})
                c = (s["credits"] if s.get("credits") is not None else estimate(j)) if s.get("uuid") else 0  # runner records the charge
                credits += c
                f, out = j.get("fields", {}), j.get("out", "")
                db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)", (folder, os.path.basename(jf), j["id"], j["endpoint"],
                           s.get("status"), s.get("uuid"), c, rel(out) if os.path.isabs(out) else out, f.get("prompt"),
                           f.get("dialogue_text")))
        db.execute("INSERT INTO episodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            folder, kind, number, folder.split("_", 1)[-1], name, getattr(proj, "TITLE", ""), len(getattr(proj, "SHOTS", [])),
            rel(scripts[-1]) if scripts else None, main, dur(main) if main else None, ng, cover, credits))
    for k, c in cast.items():
        db.execute("INSERT INTO cast VALUES (?,?,?,?,?,?,?,?)", (k, c["name"], c["title"], c["descr"], c["sheet"], c["voice"],
                   json.dumps(c["variants"], ensure_ascii=False), ",".join(c["episodes"])))
    for k, s in sets.items():
        db.execute("INSERT INTO sets VALUES (?,?,?,?,?)", (k, s["name"], s["descr"], s["file"], ",".join(s["episodes"])))
    # ---------- YouTube
    playlists = []   # one upload plan per folder (a season each): its keys (EP1...) repeat, its episode folders do not
    for plan_p in sorted(glob.glob(os.path.join(series, "youtube*", "upload_plan.json"))):
        plan, sp = json.load(open(plan_p, encoding="utf-8")), os.path.join(os.path.dirname(plan_p), "youtube.json")
        st = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
        if st.get("playlist"):
            playlists.append((plan.get("playlist", {}).get("title", ""), st["playlist"]))
        db.execute("INSERT OR IGNORE INTO meta VALUES ('channel', ?)", (plan.get("channel"),))
        for v in plan["videos"]:
            up = st.get("videos", {}).get(v["key"], {})
            db.execute("INSERT OR REPLACE INTO youtube VALUES (?,?,?,?,?,?,?,?,?,?)", (
                v["key"], v["video"].split("/")[0], up.get("id"), v["title"], up.get("published") or v.get("publish_at"), up.get("at"),
                v.get("thumbnail"), v["description"], ", ".join(v.get("tags", [])), v.get("pinned_comment")))
    db.execute("INSERT INTO meta VALUES ('playlists', ?)", (json.dumps(playlists, ensure_ascii=False),))
    titles = [r[0] for r in db.execute("SELECT title FROM episodes WHERE title != '' ORDER BY folder")]
    db.execute("INSERT INTO meta VALUES ('series', ?)", (" · ".join(dict.fromkeys(titles)) or os.path.basename(series),))
    db.execute("INSERT INTO meta VALUES ('indexed', ?)", (datetime.now().isoformat(timespec="seconds"),))
    db.commit()
    n = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("episodes", "shots", "cast", "sets", "files", "jobs", "youtube")}
    print("library.db:", ", ".join(f"{v} {k}" for k, v in n.items()))
    return db


# ---------------------------------------------------------------- web
CSS = """
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1b19;--sub:#6b6560;--line:#e2ddd6;--accent:#b3202f;--chip:#efe9e1}
@media (prefers-color-scheme:dark){:root{--bg:#141312;--card:#1e1c1b;--ink:#ece8e3;--sub:#a59e97;--line:#34302d;--accent:#e2505d;--chip:#2a2725}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,"Microsoft JhengHei","PingFang TC",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
header b{color:var(--accent)}header a{color:var(--ink);text-decoration:none}header form{margin-left:auto}
input{padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);min-width:220px}
main{max-width:1280px;margin:0 auto;padding:16px}a{color:var(--accent)}h1{font-size:22px;margin:6px 0 14px}h2{font-size:17px;margin:22px 0 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}.card .b{padding:8px 10px}
.card img{width:100%;aspect-ratio:9/16;object-fit:cover;display:block;background:var(--chip)}.sub{color:var(--sub);font-size:13px}
.stats{display:flex;gap:10px;flex-wrap:wrap}.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px}
.stat b{display:block;font-size:20px}table{border-collapse:collapse;width:100%;background:var(--card);font-size:14px}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{color:var(--sub);font-weight:600}
video{max-width:100%;border-radius:8px;background:#000}td video{width:150px}.chip{display:inline-block;background:var(--chip);border-radius:20px;padding:1px 9px;margin:2px;font-size:13px;color:var(--ink);text-decoration:none}
.bad{color:var(--accent);font-weight:600}.wrap{overflow-x:auto}pre{white-space:pre-wrap;background:var(--card);border:1px solid var(--line);padding:12px;border-radius:10px}
.row{display:flex;gap:16px;flex-wrap:wrap}.row>div{flex:1;min-width:260px}.thumbs img{width:56px;display:inline-block;aspect-ratio:3/4;border-radius:6px;margin:2px}
[id]{scroll-margin-top:72px}.card:target,tr:target{outline:3px solid var(--accent);outline-offset:-3px}
.thumbs img,a.zoom img{cursor:zoom-in}
#lb{position:fixed;inset:0;z-index:20;background:rgba(0,0,0,.88);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:16px}
#lb[hidden]{display:none}#lb img{max-width:100%;max-height:calc(100vh - 72px);object-fit:contain;border-radius:8px}
#lb .cap{color:#eee;margin-top:8px;font-size:14px}#lb button{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;
border:0;border-radius:50%;background:rgba(255,255,255,.18);color:#fff;font-size:24px;cursor:pointer}#lb .prev{left:12px}#lb .next{right:12px}
"""
# click a character's sheet or one of its small per-set pictures (a set's picture too): it opens full size over the
# page; ‹ › or the arrow keys step through that card's pictures, a click outside or Esc closes it
LIGHTBOX = """<div id="lb" hidden><button class="prev" aria-label="上一張">‹</button><img alt=""><div class="cap"></div>
<button class="next" aria-label="下一張">›</button></div><script>
const lb=document.getElementById('lb'),li=lb.querySelector('img'),lc=lb.querySelector('.cap');let grp=[],gi=0;
function show(i){gi=(i+grp.length)%grp.length;li.src=grp[gi].src;lc.textContent=grp[gi].dataset.cap||grp[gi].title||'';
lb.querySelectorAll('button').forEach(b=>b.hidden=grp.length<2)}
document.addEventListener('click',e=>{const im=e.target.closest('.thumbs img,a.zoom img');if(!im||lb.contains(im))return;e.preventDefault();
grp=[...(im.closest('.card')||document).querySelectorAll('a.zoom img,.thumbs img')];show(grp.indexOf(im));lb.hidden=false});
lb.addEventListener('click',e=>{if(e.target.matches('.prev'))show(gi-1);else if(e.target.matches('.next'))show(gi+1);else lb.hidden=true});
document.addEventListener('keydown',e=>{if(lb.hidden)return;if(e.key==='Escape')lb.hidden=true;
else if(e.key==='ArrowLeft')show(gi-1);else if(e.key==='ArrowRight')show(gi+1)});
</script>"""


def serve(series, port):
    series = os.path.abspath(series)
    dbp = os.path.join(series, "library.db")
    E = html.escape
    url = lambda r: "/f/" + urllib.parse.quote(r) if r else ""
    fmt_d = lambda d: f"{int(d // 60)}:{int(d % 60):02d}" if d else "–"

    def q(sql, *a):
        db = sqlite3.connect(dbp); db.row_factory = sqlite3.Row
        try:
            return db.execute(sql, a).fetchall()
        finally:
            db.close()

    def page(title, body):
        meta = {r["k"]: r["v"] for r in q("SELECT k, v FROM meta")}
        nav = "".join(f'<a href="{h}">{t}</a>' for h, t in (("/", "總覽"), ("/cast", "角色"), ("/sets", "場景"), ("/files", "檔案"),
                                                           ("/jobs", "任務與點數"), ("/youtube", "YouTube")))
        return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{E(title)}</title><style>{CSS}</style></head><body><header><b>{E(meta.get("series", ""))}</b>{nav}'
                f'<form action="/search"><input name="q" placeholder="搜尋台詞、角色、標題…"></form></header><main>{body}'
                f'<p class="sub">索引時間 {E(meta.get("indexed", ""))}　重新索引：python dramakit/library.py index</p></main>{LIGHTBOX}</body></html>')

    def thumbs():
        return {r["path"]: r["thumb"] for r in q("SELECT path, thumb FROM files WHERE thumb IS NOT NULL")}

    def media(r, w=None, cap=None):
        """cap: a picture opens in the page's lightbox with this caption instead of as a file"""
        if not r:
            return '<span class="sub">–</span>'
        ext = os.path.splitext(r)[1].lower()
        if ext in (".mp4", ".mov", ".webm"):
            poster = thumbs().get(r)
            attrs = (f' poster="{url(poster)}"' if poster else "") + (f" width={w}" if w else "")
            return f'<video src="{url(r)}" controls preload="none"{attrs}></video>'
        if ext in (".wav", ".mp3", ".m4a"):
            return f'<audio src="{url(r)}" controls preload="none"></audio>'
        if ext in (".png", ".jpg", ".jpeg", ".webp"):
            zoom, dcap = (' class="zoom"', f' data-cap="{E(cap)}"') if cap else ("", "")
            return f'<a href="{url(r)}"{zoom}><img src="{url(r)}" loading="lazy" alt=""{f" width={w}" if w else ""}{dcap}></a>'
        return f'<a href="{url(r)}">{E(r)}</a>'

    def home():
        eps = q("SELECT * FROM episodes ORDER BY folder")
        yt = {r["folder"]: r for r in q("SELECT * FROM youtube")}
        tot = q("SELECT (SELECT COUNT(*) FROM shots) s, (SELECT COUNT(*) FROM shots WHERE clip IS NOT NULL) c, (SELECT COUNT(*) FROM cast) k,"
                " (SELECT SUM(credits) FROM episodes) cr, (SELECT SUM(main_dur) FROM episodes WHERE kind='episode') d,"
                " (SELECT COUNT(*) FROM files) f")[0]
        stats = "".join(f'<div class="stat"><b>{v}</b><span class="sub">{t}</span></div>' for t, v in (
            ("集", sum(e["kind"] == "episode" for e in eps)), ("鏡頭", tot["s"]), ("片段", tot["c"]), ("角色", tot["k"]),
            ("正片總長", fmt_d(tot["d"])), ("估計點數", f'{tot["cr"] or 0:,}'), ("檔案", tot["f"])))
        posters = thumbs()

        def card(e):
            y = yt.get(e["folder"])
            ys = (f'<a href="https://youtu.be/{y["video_id"]}">YouTube</a> {E((y["publish_at"] or "")[:16].replace("T", " "))}'
                  if y and y["video_id"] else "未上傳" if y else "")
            pic = e["cover"] or posters.get(e["main_video"])   # no cover yet: the render's poster
            href = "/ep/" + urllib.parse.quote(e["folder"])
            return (f'<div class="card"><a href="{href}">{media(pic) if pic else "<img alt>"}</a>'
                    f'<div class="b"><a href="{href}"><b>{"第" + str(e["number"]) + "集 " if e["number"] else ""}{E(e["label"])}</b></a>'
                    f'<div class="sub">{fmt_d(e["main_dur"])}・{e["n_shots"]} 鏡・{e["credits"] or 0:,} 點</div><div class="sub">{ys}</div></div></div>')

        seasons = {}   # one section per series title (a season), in folder order; episodes first, the compilation last
        for e in eps:
            seasons.setdefault(e["title"] or "", []).append(e)
        body = ""
        for title, items in seasons.items():
            items.sort(key=lambda x: (x["kind"] != "episode", x["number"] or 0))
            n = sum(x["kind"] == "episode" for x in items)
            d = sum(x["main_dur"] or 0 for x in items if x["kind"] == "episode")
            body += (f'<h2>{E(title) or "（未命名）"}</h2><p class="sub">{n} 集・正片 {fmt_d(d)}・估計 {sum(x["credits"] or 0 for x in items):,} 點</p>'
                     f'<div class="grid">{"".join(card(x) for x in items)}</div>')
        return page("總覽", f'<h1>總覽</h1><div class="stats">{stats}</div>{body}')

    def episode(folder):
        e = q("SELECT * FROM episodes WHERE folder=?", folder)
        if not e:
            return None
        e = e[0]
        y = q("SELECT * FROM youtube WHERE folder=?", folder)
        top = f'<div class="row"><div><h2>正片</h2>{media(e["main_video"], 300)}</div>'
        if e["ng_video"]:
            top += f'<div><h2>NG 花絮</h2>{media(e["ng_video"], 300)}</div>'
        info = f'<p>{e["n_shots"]} 鏡・{fmt_d(e["main_dur"])}・估計 {e["credits"] or 0:,} 點'
        info += f'・<a href="{url(e["script"])}">劇本</a>' if e["script"] else ""
        info += f'・<a href="{url(folder + "/project.py")}">project.py</a></p>'
        if y:
            y = y[0]
            info += (f'<h2>YouTube</h2><p><b>{E(y["title"])}</b><br>' + (f'<a href="https://youtu.be/{y["video_id"]}">https://youtu.be/{y["video_id"]}</a>　'
                     f'<a href="https://studio.youtube.com/video/{y["video_id"]}/edit">Studio</a><br>' if y["video_id"] else "未上傳<br>")
                     + f'公開時間 {E(y["publish_at"] or "–")}</p><details><summary>說明欄、標籤、置頂留言</summary><pre>{E(y["description"] or "")}</pre>'
                     f'<p class="sub">{E(y["tags"] or "")}</p><pre>{E(y["pinned"] or "")}</pre></details>')
        top += f'<div>{info}</div></div>'
        def shot_row(s):
            match = "" if s["match"] is None else f'<div class="{"bad" if s["match"] < 0.9 else "sub"}">吻合 {s["match"]:.2f}</div>'
            note = fmt_d(s["clip_dur"]) + (f'・重拍 {s["takes"]}' if s["takes"] else "") + ("" if s["in_main"] else "・未進正片")
            return (f'<tr id="{E(s["id"])}"><td><b>{E(s["id"])}</b><div class="sub">{E(s["set_key"] or "")}</div></td><td>{E(s["speaker"] or "")}</td>'
                    f'<td>{E(s["line"] or "")}<div class="sub">{E(s["delivery"] or "")}</div></td><td>{E(s["heard"] or "")}{match}</td>'
                    f'<td>{media(s["clip"])}<div class="sub">{note}</div></td><td class="sub">{E(s["act"] or "")}</td></tr>')

        rows = "".join(shot_row(s) for s in q("SELECT * FROM shots WHERE folder=? ORDER BY id", folder))
        shots = f'<h2>鏡頭</h2><div class="wrap"><table><tr><th>鏡頭</th><th>說話</th><th>台詞</th><th>辨識</th><th>片段</th><th>動作</th></tr>{rows}</table></div>'
        er = q("SELECT * FROM edit_rows WHERE folder=? ORDER BY mode, n", folder)
        edits = "".join(f'<tr><td>{E(r["mode"])}</td><td>{"^" if r["over"] else ""}{E(r["src"])}</td><td>{"" if r["inn"] is None else r["inn"]}</td>'
                        f'<td>{"" if r["dur"] is None else r["dur"]}</td><td>{E(r["flags"])}</td><td class="sub">{E(r["note"])}</td></tr>' for r in er)
        takes = q("SELECT path FROM files WHERE folder=? AND kind IN ('take','raw') ORDER BY path", folder)
        extra = (f'<h2>舊版與原片</h2><div class="grid">' + "".join(f'<div class="card">{media(t["path"])}<div class="b sub">{E(t["path"].split("/")[-1])}</div></div>' for t in takes)
                 + '</div>') if takes else ""
        return page(e["label"], f'<p class="sub">{E(e["title"])}</p><h1>{"第" + str(e["number"]) + "集 " if e["number"] else ""}{E(e["label"])}</h1>{top}{shots}'
                    f'<details><summary>剪輯表（{len(er)} 列）</summary><table><tr><th>版本</th><th>來源</th><th>入點</th><th>長度</th><th>旗標</th><th>註解</th></tr>{edits}</table></details>{extra}')

    def cast_page():
        cards = ""
        for c in q("SELECT * FROM cast ORDER BY LENGTH(episodes) - LENGTH(REPLACE(episodes, ',', '')) DESC, key"):
            eps = c["episodes"].split(",")
            who = c["name"] or c["key"]
            thumbs = "".join(f'<img src="{url(p)}" title="{E(k)}" data-cap="{E(who)}・{E(k)}" loading="lazy">'
                             for k, p in json.loads(c["variants"] or "{}").items())
            chips = "".join(f'<a class="chip" href="/ep/{urllib.parse.quote(x)}">{E(x.split("_", 1)[-1])}</a>' for x in eps)
            cards += (f'<div class="card" id="{E(c["key"])}">{media(c["sheet"], cap=f"{who}・定裝")}<div class="b"><b>{E(c["name"] or c["key"])}</b> <span class="sub">{E(c["key"])}</span>'
                      f'<div class="sub">{E(c["title"] or "")}</div>{media(c["voice"]) if c["voice"] else ""}'
                      f'<div class="thumbs">{thumbs}</div><div class="sub">{len(eps)} 集：{chips}</div>'
                      f'<details><summary class="sub">描述</summary><p class="sub">{E(c["descr"] or "")}</p></details></div></div>')
        return page("角色", f'<h1>角色</h1><div class="grid">{cards}</div>')

    def sets_page():
        cards = "".join(f'<div class="card" id="{E(s["key"])}">{media(s["file"], cap=s["name"] or s["key"])}<div class="b"><b>{E(s["name"] or s["key"])}</b> <span class="sub">{E(s["key"])}</span>'
                        f'<div class="sub">{len(s["episodes"].split(","))} 集</div><p class="sub">{E(s["descr"] or "")}</p></div></div>'
                        for s in q("SELECT * FROM sets ORDER BY key"))
        return page("場景", f'<h1>場景</h1><div class="grid">{cards}</div>')

    def files_page(kind):
        kinds = q("SELECT kind, COUNT(*) n, SUM(size) s FROM files GROUP BY kind ORDER BY n DESC")
        chips = "".join(f'<a class="chip" href="/files?kind={k["kind"]}">{k["kind"]} {k["n"]}・{(k["s"] or 0) / 1e6:.0f} MB</a>' for k in kinds)
        def file_row(f):
            wh = f'{f["w"]}×{f["h"]}' if f["w"] else ""
            return (f'<tr><td><a href="{url(f["path"])}">{E(f["path"])}</a></td><td>{f["kind"]}</td><td>{(f["size"] or 0) / 1e6:.1f} MB</td>'
                    f'<td>{fmt_d(f["dur"]) if f["dur"] else ""}</td><td>{wh}</td>'
                    f'<td class="sub">{datetime.fromtimestamp(f["mtime"]).strftime("%m-%d %H:%M")}</td></tr>')

        rows = "".join(file_row(f) for f in q("SELECT * FROM files WHERE kind=? ORDER BY path" if kind else
                                               "SELECT * FROM files ORDER BY mtime DESC LIMIT 200", *([kind] if kind else [])))
        return page("檔案", f'<h1>檔案{(" ・ " + E(kind)) if kind else "（最近 200 個）"}</h1><p>{chips}</p><div class="wrap"><table>'
                    f'<tr><th>路徑</th><th>類別</th><th>大小</th><th>長度</th><th>尺寸</th><th>修改</th></tr>{rows}</table></div>')

    def jobs_page(folder):
        summ = "".join(f'<tr><td><a href="/jobs?ep={urllib.parse.quote(r["folder"])}">{E(r["folder"])}</a></td><td>{r["n"]}</td><td>{r["c"] or 0:,}</td>'
                       f'<td>{r["bad"]}</td></tr>' for r in q("SELECT folder, COUNT(*) n, SUM(credits) c, SUM(status NOT IN ('completed') OR status IS NULL) bad "
                                                              "FROM jobs GROUP BY folder ORDER BY folder"))
        body = f'<h1>任務與點數</h1><table><tr><th>集</th><th>任務</th><th>估計點數</th><th>未完成</th></tr>{summ}</table>'
        if folder:
            rows = "".join(f'<tr><td>{E(j["file"])}</td><td>{E(j["id"])}</td><td>{E(j["endpoint"])}</td><td class="{"" if j["status"] == "completed" else "bad"}">{E(j["status"] or "未送")}</td>'
                           f'<td>{j["credits"]}</td><td>{E(j["line"] or "")}</td><td class="sub">{E((j["prompt"] or "")[:160])}</td></tr>'
                           for j in q("SELECT * FROM jobs WHERE folder=? ORDER BY file, id", folder))
            body += f'<h2>{E(folder)}</h2><div class="wrap"><table><tr><th>檔</th><th>id</th><th>端點</th><th>狀態</th><th>點數</th><th>台詞</th><th>提示詞</th></tr>{rows}</table></div>'
        return page("任務", body)

    def youtube_page():
        meta = {r["k"]: r["v"] for r in q("SELECT k, v FROM meta")}
        def yt_row(y):
            vid = y["video_id"]
            link = f'<a href="https://youtu.be/{vid}">{vid}</a>' if vid else '<span class="bad">未上傳</span>'
            return (f'<tr><td>{E(y["key"])}</td><td>{E(y["title"])}</td><td>{E((y["publish_at"] or "")[:16].replace("T", " "))}</td>'
                    f'<td>{link}</td><td>{media(y["thumbnail"], 60) if y["thumbnail"] else ""}</td></tr>')

        rows = "".join(yt_row(y) for y in q("SELECT * FROM youtube ORDER BY folder"))
        pls = "　".join(f'<a href="https://www.youtube.com/playlist?list={i}">{E(t or "播放清單")}</a>'
                       for t, i in json.loads(meta.get("playlists") or "[]"))
        head = f'<p>頻道 {E(meta.get("channel") or "–")}　{pls}</p>'
        return page("YouTube", f'<h1>YouTube</h1>{head}<div class="wrap"><table><tr><th>鍵</th><th>標題</th><th>公開時間</th><th>影片</th><th>封面</th></tr>{rows}</table></div>')

    def search_page(s):
        like = f"%{s}%"
        shots = q("SELECT folder, id, speaker, line, heard, clip FROM shots WHERE line LIKE ? OR heard LIKE ? OR act LIKE ? OR id LIKE ?", like, like, like, like)
        cast_ = q("SELECT key, name, title FROM cast WHERE key LIKE ? OR name LIKE ? OR title LIKE ? OR descr LIKE ?", like, like, like, like)
        yts = q("SELECT key, folder, title FROM youtube WHERE title LIKE ? OR description LIKE ?", like, like)
        files_ = q("SELECT path, kind FROM files WHERE path LIKE ? LIMIT 100", like)
        body = f'<h1>搜尋「{E(s)}」</h1><h2>台詞與鏡頭（{len(shots)}）</h2><table>' + "".join(
            f'<tr><td><a href="/ep/{urllib.parse.quote(r["folder"])}">{E(r["folder"])}</a> {E(r["id"])}</td><td>{E(r["speaker"] or "")}</td>'
            f'<td>{E(r["line"] or "")}</td><td>{media(r["clip"])}</td></tr>' for r in shots) + "</table>"
        body += f'<h2>角色（{len(cast_)}）</h2>' + "".join(f'<a class="chip" href="/cast">{E(c["name"] or c["key"])}・{E(c["title"] or "")}</a>' for c in cast_)
        body += f'<h2>YouTube（{len(yts)}）</h2>' + "".join(f'<p><a href="/ep/{urllib.parse.quote(y["folder"])}">{E(y["key"])}</a> {E(y["title"])}</p>' for y in yts)
        body += f'<h2>檔案（{len(files_)}）</h2>' + "".join(f'<div><a href="{url(f["path"])}">{E(f["path"])}</a> <span class="sub">{f["kind"]}</span></div>' for f in files_)
        return page("搜尋", body)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, body, code=200, ctype="text/html; charset=utf-8"):
            b = body.encode("utf-8")
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b)

        def file(self, rel):
            p = os.path.abspath(os.path.join(series, rel))
            if not p.startswith(series + os.sep) or not os.path.isfile(p):
                return self.send("not found", 404, "text/plain; charset=utf-8")
            size = os.path.getsize(p)
            ext = os.path.splitext(p)[1].lower()
            ctype = "text/plain; charset=utf-8" if ext in TEXT else (mimetypes.guess_type(p)[0] or "application/octet-stream")
            a, b = 0, size - 1
            m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            if m and (m[1] or m[2]):
                a, b = (int(m[1]), int(m[2]) if m[2] else size - 1) if m[1] else (max(0, size - int(m[2])), size - 1)
                b = min(b, size - 1)
                self.send_response(206); self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
            else:
                self.send_response(200)
            self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(b - a + 1)); self.end_headers()
            with open(p, "rb") as f:
                f.seek(a); left = b - a + 1
                while left > 0:
                    chunk = f.read(min(1 << 16, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk); left -= len(chunk)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            path, qs = urllib.parse.unquote(u.path), urllib.parse.parse_qs(u.query)
            try:
                if path.startswith("/f/"):
                    return self.file(path[3:])
                if path == "/":
                    return self.send(home())
                if path.startswith("/ep/"):
                    body = episode(path[4:])
                    return self.send(body) if body else self.send("not found", 404, "text/plain; charset=utf-8")
                routes = {"/cast": cast_page, "/sets": sets_page, "/youtube": youtube_page}
                if path in routes:
                    return self.send(routes[path]())
                if path == "/files":
                    return self.send(files_page(qs.get("kind", [""])[0]))
                if path == "/jobs":
                    return self.send(jobs_page(qs.get("ep", [""])[0]))
                if path == "/search":
                    return self.send(search_page(qs.get("q", [""])[0].strip()))
                self.send("not found", 404, "text/plain; charset=utf-8")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass   # the browser dropped a video request it no longer needs

    def watch():
        """Re-index in the background whenever a file under SERIES_DIR is added, removed or changed."""
        def stamp():
            n, newest = 0, 0.0
            for root, dirs, names in os.walk(series):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("render")]
                for f in names:
                    if os.path.splitext(f)[1].lower() in MEDIA | TEXT | {".state"} and not f.startswith("library.db"):
                        n += 1
                        try:
                            newest = max(newest, os.path.getmtime(os.path.join(root, f)))
                        except OSError:
                            pass
            return n, newest
        last = stamp()
        while True:
            time.sleep(WATCH_S)
            now = stamp()
            if now != last:
                time.sleep(3)   # let a render or a download finish writing
                try:
                    index(series).close()
                    print(f"  re-indexed at {datetime.now():%H:%M:%S}", flush=True)
                except Exception as e:
                    print("  !! re-index failed:", e, flush=True)
                last = stamp()

    threading.Thread(target=watch, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"library: http://127.0.0.1:{port}  (Ctrl+C to stop; re-indexes by itself when files change)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("index", "serve"):
        sys.exit(__doc__)
    cmd, series = sys.argv[1], sys.argv[2]
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765
    if cmd == "index" or "--no-index" not in sys.argv:
        index(series).close()
    if cmd == "serve":
        serve(series, port)

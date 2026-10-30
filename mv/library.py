"""A browsable index of one MV series: every episode, shot, clip, still, character, lyric, render, job and upload in one
SQLite file, and a small local web page to look through it (standard library only).

usage: python mvkit/library.py index SERIES_DIR                     -> SERIES_DIR/library.db (rebuilt each time)
       python mvkit/library.py serve SERIES_DIR [--port 8770]       index, then http://127.0.0.1:8770 (the next free
                                                                    port if it is taken); re-indexes by itself when
                                                                    files change (checked every 15 s)
       python mvkit/library.py serve SERIES_DIR --no-index          serve the existing library.db as it is
SERIES_DIR is the folder above the episodes (research.md, style.md, s1e1_x/, s1e2_y/ ...). Episodes are its sub-folders
with a project.py or named s<season>e<episode>_<title> (one still being planned has lyrics and notes only); a folder
starting with "_" is parked, not an episode. A single project folder works too (a series of one). The overview has one
section per season (the s<N> of the folder). Covers: the newest thumbnails/thumb_*.jpg, else the full MV's poster.
Media are probed with ffprobe once and cached by size and date in the same file. Credits come from the job
files and their .state: what the submit charged when the .state keeps it (off-peak tasks cost half), else common.estimate;
failed tasks are refunded, and a job run again only counts its last run.
YouTube details come from each episode's youtube.json (youtube_upload.py). The server listens on 127.0.0.1 only and
serves files from inside SERIES_DIR only; OAuth secrets and tokens are never indexed or served.
"""
import html, json, mimetypes, os, re, shutil, sqlite3, subprocess, sys, threading, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from common import load_project, estimate

SCHEMA = """
CREATE TABLE IF NOT EXISTS probe (path TEXT PRIMARY KEY, size INT, mtime REAL, dur REAL, w INT, h INT);
DROP TABLE IF EXISTS episodes; DROP TABLE IF EXISTS shots; DROP TABLE IF EXISTS lyrics; DROP TABLE IF EXISTS edit_rows;
DROP TABLE IF EXISTS chars; DROP TABLE IF EXISTS files; DROP TABLE IF EXISTS jobs; DROP TABLE IF EXISTS youtube;
DROP TABLE IF EXISTS meta; DROP TABLE IF EXISTS versions;
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE episodes (folder TEXT PRIMARY KEY, season INT, number INT, label TEXT, name TEXT, title TEXT, genre TEXT,
  tagline TEXT, stage TEXT, song TEXT, song_dur REAL, lyrics TEXT, notes TEXT, seo TEXT, n_shots INT, n_clips INT,
  renders TEXT, full TEXT, full_dur REAL, cover TEXT, shorts_cover TEXT, ls_share REAL, credits INT);
CREATE TABLE shots (folder TEXT, id TEXT, kind TEXT, feature TEXT, caption TEXT, chars TEXT, prompt TEXT, motion TEXT,
  still TEXT, still_end TEXT, refs TEXT, clip TEXT, clip_dur REAL, clip_thumb TEXT, a0 REAL, a_dur REAL, voice TEXT,
  lyric TEXT, edits TEXT, versions INT, PRIMARY KEY (folder, id));
CREATE TABLE versions (folder TEXT, id TEXT, path TEXT);
CREATE TABLE lyrics (folder TEXT, section TEXT, t REAL, text TEXT, voice TEXT);
CREATE TABLE edit_rows (folder TEXT, mode TEXT, n INT, t REAL, src TEXT, off REAL, flags TEXT, dur REAL, rep INT, note TEXT);
CREATE TABLE chars (folder TEXT, key TEXT, kind TEXT, name TEXT, file TEXT, descr TEXT, PRIMARY KEY (folder, key));
CREATE TABLE files (path TEXT PRIMARY KEY, kind TEXT, folder TEXT, size INT, mtime REAL, dur REAL, w INT, h INT, thumb TEXT);
CREATE TABLE jobs (folder TEXT, file TEXT, id TEXT, endpoint TEXT, status TEXT, uuid TEXT, credits INT, out TEXT, prompt TEXT);
CREATE TABLE youtube (folder TEXT, kind TEXT, video_id TEXT, title TEXT, at TEXT, channel TEXT, PRIMARY KEY (folder, kind));
"""
MEDIA = {".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".flac", ".png", ".jpg", ".jpeg", ".webp"}
TEXT = {".md", ".txt", ".srt", ".json", ".py", ".tsv"}
SKIP_DIRS = {"__pycache__", ".library", "img", "aud", "sep", "tmp"}   # job inputs (padded stills, audio cuts), stems
SECRET = re.compile(r"client_secret|token|\.env$|api_?key", re.I)   # file names never indexed or served
WATCH_S = 15   # serve: how often to look for changed files
THUMB_KINDS = {"clip", "clip_raw", "clip_candidate", "clip_rejected", "output"}
VERSION_KINDS = ("clip_raw", "clip_candidate", "clip_rejected", "still_candidate", "still_rejected")
EPISODE = re.compile(r"s(\d+)e(\d+)(?:_(.+))?$", re.I)
FEATURE = {"/videos/lip-sync": "對嘴影片", "/videos/image-to-video": "AI圖生影片", "/videos/keyframe": "關鍵幀影片",
           "/videos/multi-subject-reference": "多參考影片", "/videos/text-to-video": "文字生成動畫", "/videos/dance": "舞蹈影片"}
FEATURE_BY_KIND = {"對嘴": "對嘴影片", "樂手": "AI圖生影片", "B-roll": "AI圖生影片", "關鍵幀": "關鍵幀影片", "多參考": "多參考影片"}
REFUNDED = {"failed", "failed_final", "timeout", "cancelled"}
NO_PROJECT = ("企劃中", "沒有 project.py")   # episode stages without a project.py


def kind_of(rel):
    """What a file is, from where it sits."""
    p, ext = rel.replace("\\", "/"), os.path.splitext(rel)[1].lower()
    name, dirs = p.split("/")[-1], [d.lower() for d in p.split("/")[:-1]]
    video = ext in (".mp4", ".mov", ".webm")
    if any("rejected" in d for d in dirs):   # clips_rejected/, kf_rejected/, rejected/<attempt>/ ...
        return "clip_rejected" if video else "still_rejected"
    if "clips_raw" in dirs:
        return "clip_raw"
    if any(d.startswith("clips_") for d in dirs):   # clips_cand/, clips_test/
        return "clip_candidate"
    if any(d.startswith("kf_") for d in dirs) or "cand" in dirs and "kf" in dirs:   # kf_candidates/, kf_hd/, kf/cand/
        return "still_candidate"
    rules = [("clips/", "clip"), ("kf/", "keyframe"),
             ("chars/candidates/", "char_candidate"), ("chars/", "char"), ("refs/", "ref"), ("ref/", "ref"),
             ("cards/", "card"), ("thumbnails/", "thumbnail"), ("thumb_src/", "thumb_source"), ("audio/", "audio"),
             ("jobs/", "job"), ("qc/", "review"), ("fonts/", "font")]
    for key, k in rules:
        if ("/" + p).find("/" + key) >= 0:
            return k
    if "/out/" in "/" + p:
        return "subtitle" if ext == ".srt" else "output" if ext == ".mp4" else "output_other"
    if ext in (".wav", ".mp3", ".m4a", ".flac"):
        return "song"
    if name.startswith("歌詞"):
        return "lyrics"
    if name.lower().startswith("youtube_seo"):
        return "seo"
    if ext in (".jpg", ".png") and re.match(r"(review|qc_|sheet|cands|contact)", name):
        return "review"
    if name == "project.py":
        return "project"
    return {".md": "doc", ".txt": "doc", ".json": "data", ".tsv": "data", ".py": "script"}.get(ext, "other")


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
        try:
            d = float(j.get("format", {}).get("duration") or 0)
        except ValueError:
            d = 0
        return p, os.path.getsize(p), os.path.getmtime(p), d if d < 36000 else 0, st.get("width"), st.get("height")

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, need))
    db.executemany("INSERT OR REPLACE INTO probe VALUES (?,?,?,?,?,?)", rows)
    db.commit()   # keep the cache even if the rest of the index fails
    return {r[0]: r for r in db.execute("SELECT path, size, mtime, dur, w, h FROM probe")}


def make_thumbs(series, items):
    """A small still per video (cached in SERIES_DIR/.library/thumbs by path and date) for the page's posters: a clip at
    1 s, a render at 30 % (past the opening card). Stills no video uses any more are deleted."""
    out_dir = os.path.join(series, ".library", "thumbs")
    os.makedirs(out_dir, exist_ok=True)

    def one(item):
        p, d, render = item
        at = (d or 2) * 0.3 if render else min(1.0, (d or 2) / 2)
        key = re.sub(r"[^\w.-]", "_", os.path.relpath(p, series)) + f"_{int(os.path.getmtime(p))}{'_r' if render else ''}.jpg"
        t = os.path.join(out_dir, key)
        if not os.path.exists(t):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", p, "-frames:v", "1",
                            "-vf", "scale=-2:360", t], capture_output=True)
        return p, t if os.path.exists(t) else None

    with ThreadPoolExecutor(8) as ex:
        made = dict(ex.map(one, items))
    keep = {os.path.basename(t) for t in made.values() if t}
    for f in os.listdir(out_dir):
        if f not in keep:
            os.remove(os.path.join(out_dir, f))
    return {p: os.path.relpath(t, series).replace("\\", "/") for p, t in made.items() if t}


def episode_dirs(series):
    """Episode folders in season / episode order: a project.py, or named s<N>e<N>_...; "_" folders are parked."""
    if os.path.exists(os.path.join(series, "project.py")):
        return [""]

    def order(d):
        m = EPISODE.match(d)
        return (int(m[1]), int(m[2]), d) if m else (999, 999, d)
    return sorted((d for d in os.listdir(series) if not d.startswith((".", "_")) and os.path.isdir(os.path.join(series, d))
                   and (os.path.exists(os.path.join(series, d, "project.py")) or EPISODE.match(d))), key=order)


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
    g = lambda t, i: t[i] if isinstance(t, (list, tuple)) and len(t) > i else None
    db.executescript(SCHEMA)
    eps = episode_dirs(series)
    # ---------- files
    found = []
    for root, dirs, names in os.walk(series):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("render")]
        found += [os.path.join(root, n) for n in names if os.path.splitext(n)[1].lower() in MEDIA | TEXT and not SECRET.search(n)]
    pr = probe([p for p in found if os.path.splitext(p)[1].lower() in MEDIA], db)
    thumbs = make_thumbs(series, [(p, pr[p][3], kind_of(rel(p)) == "output") for p in found
                                  if p in pr and p.lower().endswith(".mp4") and kind_of(rel(p)) in THUMB_KINDS])
    info, by_folder = {}, {}
    for p in found:
        r = rel(p)
        folder = "" if eps == [""] else r.split("/")[0] if "/" in r and r.split("/")[0] in eps else ""
        q = pr.get(p) or (p, os.path.getsize(p), os.path.getmtime(p), None, None, None)
        info[r] = dict(kind=kind_of(r), size=q[1], mtime=q[2], dur=q[3], thumb=thumbs.get(p))
        by_folder.setdefault(folder, []).append(r)
        db.execute("INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?)", (r, info[r]["kind"], folder, q[1], q[2], q[3], q[4], q[5], thumbs.get(p)))
    dur = lambda r: (info.get(r) or {}).get("dur")
    # ---------- episodes
    for folder in eps:
        D = os.path.join(series, folder) if folder else series
        R = lambda *a: rel(os.path.join(D, *a))
        ex = lambda *a: os.path.exists(os.path.join(D, *a))
        ls = lambda sub, pat: sorted(f for f in (os.listdir(os.path.join(D, sub)) if os.path.isdir(os.path.join(D, sub)) else [])
                                     if re.match(pat, f, re.I))
        newest = lambda sub, pat: max(ls(sub, pat), key=lambda f: os.path.getmtime(os.path.join(D, sub, f)), default=None)
        m = EPISODE.match(folder)
        season, number = (int(m[1]), int(m[2])) if m else (None, None)
        label = (m[3] if m and m[3] else folder) or os.path.basename(series)
        lyr = sorted(ls(".", r"歌詞.*\.txt$"), key=lambda f: [int(x) for x in re.findall(r"\d+", f)] or [0])
        cover, shorts_cover = newest("thumbnails", r"thumb_.*\.jpe?g$"), newest("thumbnails", r"shorts_.*\.jpe?g$")
        cover, shorts_cover = cover and R("thumbnails", cover), shorts_cover and R("thumbnails", shorts_cover)
        cover = cover or next((r for r in by_folder.get(folder, []) if re.match(r"thumbnail.*\.jpe?g$", r.split("/")[-1], re.I)), None)
        try:
            yt = json.load(open(os.path.join(D, "youtube.json"), encoding="utf-8")) if ex("youtube.json") else {}
        except ValueError:
            yt = {}
        for k, v in yt.items():
            if isinstance(v, dict) and v.get("id"):
                db.execute("INSERT OR REPLACE INTO youtube VALUES (?,?,?,?,?,?)", (folder, k, v["id"], v.get("title"), v.get("at"), yt.get("channel")))
        proj = None
        if ex("project.py"):
            try:
                proj = load_project(D)
            except BaseException as e:   # one broken project.py (or a sys.exit in it) should not stop the index
                print(f"  !! {folder}: {e!r}"[:300])
        if not proj:
            song = next((f for f in ls(".", r".*\.(wav|mp3|m4a|flac)$")), None)
            db.execute("INSERT INTO episodes (folder, season, number, label, name, title, stage, song, song_dur, lyrics, notes, seo,"
                       " n_shots, n_clips, credits, cover) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,0,0,?)", (
                folder, season, number, label, label, label, "企劃中" if lyr or ex("狀態.md") else "沒有 project.py", song and R(song), song and dur(R(song)),
                R(lyr[-1]) if lyr else None, R("狀態.md") if ex("狀態.md") else None,
                R("YouTube_SEO.txt") if ex("YouTube_SEO.txt") else None, cover))
            continue
        T = getattr(proj, "TYPO", {}) or {}
        # ---------- jobs: estimated credits, and which endpoint made each output
        made, paid, jrows = {}, set(), []
        job_files = [os.path.join(root, f) for root, _, names in os.walk(os.path.join(D, "jobs")) for f in names if f.endswith(".json")]
        for jf in sorted(job_files, key=os.path.getmtime):   # oldest first: a later redo of the same output wins in `made`
            try:
                J = json.load(open(jf, encoding="utf-8"))
                st = json.load(open(jf + ".state", encoding="utf-8")) if os.path.exists(jf + ".state") else {}
            except ValueError:
                continue
            if not isinstance(J, list):
                continue
            for j in J:
                if not isinstance(j, dict) or "endpoint" not in j:
                    continue
                s = st.get(j.get("id"), {})
                src = (j.get("files") or {}).get("source_video")
                src_dur = dur(rel(os.path.normpath(src if os.path.isabs(src) else os.path.join(D, src)))) if isinstance(src, str) else None
                try:   # aip_runner.py keeps what the submit charged (off-peak tasks cost half); older .state files do not
                    c = s["credits"] if isinstance(s.get("credits"), int) else estimate(j, src_dur)
                except (KeyError, TypeError, ValueError):
                    c = 0
                out = j.get("out", "")
                outp = os.path.normpath(out if os.path.isabs(out) else os.path.join(D, out))
                ro = rel(outp) if outp.startswith(series + os.sep) else out
                if j["endpoint"] != "/videos/restore":
                    made[ro] = j["endpoint"]
                status = s.get("status") or ("output_only" if os.path.exists(outp) else None)
                charged = s.get("uuid") and status not in REFUNDED
                paid |= {ro} if charged else set()
                jrows.append([folder, os.path.relpath(jf, os.path.join(D, "jobs")).replace("\\", "/"), j.get("id"), j["endpoint"],
                              status, s.get("uuid"), c if charged else 0, ro, (j.get("fields") or {}).get("prompt"), c])
        for r in reversed(jrows):   # no .state (renamed or lost) but the output is there: count the newest such job once
            if r[4] == "output_only" and r[7] not in paid:
                r[6] = r[9]
                paid.add(r[7])
        db.executemany("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)", [r[:9] for r in jrows])
        credits = sum(r[6] for r in jrows)
        # ---------- lyrics
        lines = []
        for sec in getattr(proj, "SECTIONS", []):
            for ln in (g(sec, 3) or []):
                if g(ln, 1):
                    lines.append((g(sec, 0), g(ln, 0), g(ln, 1), g(ln, 2)))
                    db.execute("INSERT INTO lyrics VALUES (?,?,?,?,?)", (folder,) + lines[-1])
        # ---------- edits
        uses, renders, ls_share = {}, [], None
        lip_ids = {g(l, 0) for l in getattr(proj, "LIPSYNC", [])}
        edits = getattr(proj, "EDITS", {}) or {}
        for mode, e in edits.items():
            text = e.get("shots", "")
            for k in sorted(edits, key=len, reverse=True):   # "@shorts" before "@short"
                text = text.replace("@" + k, edits[k].get("shots", "") if k != mode else "")
            rows = []
            for tok in text.replace("\n", "|").split("|"):
                p = tok.split("#")[0].split()
                if not p:
                    continue
                try:
                    off = float(p[2]) if len(p) > 2 else None
                    rows.append([float(p[0]), p[1], off, p[3] if len(p) > 3 else "", tok.split("#", 1)[1].strip() if "#" in tok else ""])
                except ValueError:
                    continue
            if rows and e.get("cut") is not None:
                rows[0][0] = e["cut"]
            seen, total, lip = set(), 0.0, 0.0
            for n, r in enumerate(rows):
                end = rows[n + 1][0] if n + 1 < len(rows) else e.get("end", r[0])
                d = max(0.0, end - r[0])
                db.execute("INSERT INTO edit_rows VALUES (?,?,?,?,?,?,?,?,?,?)", (folder, mode, n, r[0], r[1], r[2], r[3], round(d, 2),
                           int(r[1] in seen), r[4]))
                seen.add(r[1])
                uses.setdefault(r[1], {}).setdefault(mode, 0)
                uses[r[1]][mode] += 1
                total += d
                lip += d if r[1] in lip_ids else 0
            if mode == "full" and total:
                ls_share = lip / total
            out = R("out", getattr(proj, "NAME", label) + e.get("suffix", "") + ".mp4")
            if out in info:
                size = e.get("size", (1920, 1080))
                renders.append(dict(mode=mode, path=out, dur=dur(out), vertical=size[0] < size[1], thumb=info[out]["thumb"]))
        renders.sort(key=lambda r: (["full", "short", "shorts"] + [r["mode"]]).index(r["mode"]))
        full = next((r for r in renders if r["mode"] == "full"), None) or max((r for r in renders if not r["vertical"]),
                                                                           key=lambda r: r["dur"] or 0, default=None)
        # ---------- shots: lip-sync takes, band, B-roll, keyframe and multi-reference videos
        kf = lambda k: R("kf", k + ".png") if k and ex("kf", k + ".png") else None
        ref = lambda k: next((R(d, k + ".png") for d in ("refs", "refs/angles", "kf") if ex(d, k + ".png")), None)   # feature_jobs order
        scenes = {s[0]: s for s in getattr(proj, "LS_SCENES", [])}
        caps = getattr(proj, "EXTRA_CAPS", {}) or {}
        shots = {}
        for l in getattr(proj, "LIPSYNC", []):
            sc, a0, ad = scenes.get(g(l, 1), ()), g(l, 2), g(l, 3)
            said = " / ".join(x[2] for x in lines if a0 is not None and x[1] is not None and a0 - 0.3 <= x[1] < a0 + (ad or 0))
            shots[l[0]] = dict(kind="對嘴", caption=g(sc, 4), chars=g(sc, 1), prompt=g(sc, 2), motion=g(sc, 3), still=kf(g(l, 1)),
                               a0=a0, a_dur=ad, voice=g(l, 4), lyric=said)
        for b in getattr(proj, "BAND", []):
            who = b[1] if isinstance(b[1], (list, tuple)) else [b[1]]
            shots[b[0]] = dict(kind="樂手", caption=g(b, 2), chars=",".join(map(str, who)), prompt=g(b, 3), motion=g(b, 4), still=kf(b[0]))
        for b in getattr(proj, "BROLL", []):
            shots[b[0]] = dict(kind="B-roll", caption=g(b, 1), prompt=g(b, 2), motion=g(b, 3), still=kf(b[0]))
        for k, v in (getattr(proj, "KEYFRAME", {}) or {}).items():
            shots[k] = dict(kind="關鍵幀", caption=caps.get(k), motion=g(v, 2), still=kf(g(v, 0)), still_end=kf(g(v, 1)))
        for k, v in (getattr(proj, "MULTI", {}) or {}).items():
            keys = [g(r, 0) if isinstance(r, (list, tuple)) else r for r in (g(v, 0) or [])]
            refs = [x for x in map(ref, keys) if x]
            shots[k] = dict(kind="多參考", caption=caps.get(k), prompt=g(v, 1), refs=json.dumps(refs, ensure_ascii=False),
                            still=refs[0] if refs else None)
        versions = {}   # each old take or candidate goes to the longest shot id it starts with: LS01b_r2 -> LS01b, B07a -> B07
        longest = sorted(shots, key=len, reverse=True)
        for r in by_folder.get(folder, []):
            if info[r]["kind"] in VERSION_KINDS:
                sid = next((i for i in longest if re.match(re.escape(i) + r"(?![0-9])", r.split("/")[-1], re.I)), None)
                if sid:
                    versions.setdefault(sid, []).append(r)
                    db.execute("INSERT INTO versions VALUES (?,?,?)", (folder, sid, r))
        for sid, s in shots.items():
            clip = R("clips", sid + ".mp4") if ex("clips", sid + ".mp4") else None
            nv = len(versions.get(sid, []))
            feature = FEATURE.get(made.get(clip)) or FEATURE_BY_KIND.get(s["kind"])
            db.execute("INSERT OR REPLACE INTO shots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                folder, sid, s["kind"], feature, s.get("caption"), s.get("chars"), s.get("prompt"), s.get("motion"), s.get("still"),
                s.get("still_end"), s.get("refs"), clip, dur(clip), clip and info.get(clip, {}).get("thumb"), s.get("a0"),
                s.get("a_dur"), s.get("voice"), s.get("lyric"), json.dumps(uses.get(sid, {})), nv))
        # ---------- characters (singers, band) and multi-reference images
        for k, c in (getattr(proj, "CHARS", {}) or {}).items():
            f = c.get("file")
            db.execute("INSERT OR REPLACE INTO chars VALUES (?,?,?,?,?,?)", (folder, k, c.get("kind", "vocal"), c.get("name"),
                       R(f) if f and ex(f) else None, c.get("desc")))
        for k, c in (getattr(proj, "REFS", {}) or {}).items():
            db.execute("INSERT OR REPLACE INTO chars VALUES (?,?,?,?,?,?)", (folder, k, "ref", c.get("name") if isinstance(c, dict) else None,
                       ref(k), c.get("desc") if isinstance(c, dict) else str(c)))
        n_clips = sum(1 for sid in shots if ex("clips", sid + ".mp4"))
        song = getattr(proj, "SONG", None)
        song = R(song) if song and ex(song) else None
        stage = "已上傳" if (yt.get("full") or {}).get("id") else "已完成" if full else "製作中"
        first_still = next((s["still"] for s in shots.values() if s.get("still")), None)
        db.execute("INSERT INTO episodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            folder, season, number, label, getattr(proj, "NAME", label), T.get("title") or label, T.get("genre"), T.get("tagline"),
            stage, song, dur(song) if song else None, R(lyr[-1]) if lyr else None, R("狀態.md") if ex("狀態.md") else None,
            R("YouTube_SEO.txt") if ex("YouTube_SEO.txt") else None, len(shots), n_clips, json.dumps(renders, ensure_ascii=False),
            full and full["path"], full and full["dur"], cover or (full and full["thumb"]) or first_still, shorts_cover, ls_share, credits))
    db.execute("INSERT INTO meta VALUES ('series', ?)", (os.path.basename(series),))
    db.execute("INSERT INTO meta VALUES ('indexed', ?)", (datetime.now().isoformat(timespec="seconds"),))
    db.commit()
    n = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("episodes", "shots", "lyrics", "chars", "files", "jobs", "youtube")}
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
main{max-width:1320px;margin:0 auto;padding:16px}a{color:var(--accent)}h1{font-size:22px;margin:6px 0 14px}h2{font-size:17px;margin:22px 0 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}.grid.small{grid-template-columns:repeat(auto-fill,minmax(160px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}.card .b{padding:8px 10px}
.card img,.card video{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:var(--chip);border-radius:0}
.portrait img{aspect-ratio:3/4}.sub{color:var(--sub);font-size:13px}
.stats{display:flex;gap:10px;flex-wrap:wrap}.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px}
.stat b{display:block;font-size:20px}table{border-collapse:collapse;width:100%;background:var(--card);font-size:14px}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{color:var(--sub);font-weight:600}
video{max-width:100%;border-radius:8px;background:#000}td video{width:200px}td img{width:120px;border-radius:6px}
.chip{display:inline-block;background:var(--chip);border-radius:20px;padding:1px 9px;margin:2px;font-size:13px;color:var(--ink);text-decoration:none}
.chip.on{background:var(--accent);color:#fff}.bad{color:var(--accent);font-weight:600}.wrap{overflow-x:auto}
pre{white-space:pre-wrap;background:var(--card);border:1px solid var(--line);padding:12px;border-radius:10px;font-size:13px}
.row{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}.row>div{min-width:200px}.row .grow{flex:1;min-width:280px}
audio{width:100%;max-width:420px}details{margin:10px 0}summary{cursor:pointer}
"""


def serve(series, port):
    series = os.path.abspath(series)
    dbp = os.path.join(series, "library.db")
    E = html.escape
    url = lambda r: "/f/" + urllib.parse.quote(r) if r else ""
    ep_url = lambda f: "/ep/" + urllib.parse.quote(f)
    shot_url = lambda f, i: "/shot/" + urllib.parse.quote(f) + "/" + urllib.parse.quote(i)
    fmt_d = lambda d: f"{int(d // 60)}:{int(d % 60):02d}" if d else "–"
    yt_link = lambda v: f'<a href="https://youtu.be/{E(v)}">youtu.be/{E(v)}</a> <a class="sub" href="https://studio.youtube.com/video/{E(v)}/edit">Studio</a>'
    MODE = {"full": "完整版", "short": "短版", "shorts": "Shorts"}
    status = lambda j: '<span class="sub">有輸出、沒有 .state</span>' if j["status"] == "output_only" else         E(j["status"]) if j["status"] == "completed" else f'<span class="bad">{E(j["status"] or "未送")}</span>'

    def q(sql, *a):
        db = sqlite3.connect(dbp); db.row_factory = sqlite3.Row
        try:
            return db.execute(sql, a).fetchall()
        finally:
            db.close()

    def page(title, body):
        meta = {r["k"]: r["v"] for r in q("SELECT k, v FROM meta")}
        nav = "".join(f'<a href="{h}">{t}</a>' for h, t in (("/", "總覽"), ("/chars", "角色"), ("/files", "檔案"),
                                                           ("/jobs", "任務與點數"), ("/youtube", "YouTube")))
        return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{E(title)}</title><style>{CSS}</style></head><body><header><b>{E(meta.get("series", ""))}</b>{nav}'
                f'<form action="/search"><input name="q" placeholder="搜尋歌詞、鏡頭、提示詞、角色、標題…"></form></header><main>{body}'
                f'<p class="sub">索引時間 {E(meta.get("indexed", ""))}　重新索引：python mvkit/library.py index</p></main></body></html>')

    def media(r, w=None, poster=None):
        if not r:
            return '<span class="sub">–</span>'
        ext = os.path.splitext(r)[1].lower()
        if ext in (".mp4", ".mov", ".webm"):
            if poster is None:
                poster = (q("SELECT thumb FROM files WHERE path=?", r) or [{"thumb": None}])[0]["thumb"]
            attrs = (f' poster="{url(poster)}"' if poster else "") + (f" width={w}" if w else "")
            return f'<video src="{url(r)}" controls preload="none"{attrs}></video>'
        if ext in (".wav", ".mp3", ".m4a", ".flac"):
            return f'<audio src="{url(r)}" controls preload="none"></audio>'
        if ext in (".png", ".jpg", ".jpeg", ".webp"):
            return f'<a href="{url(r)}"><img src="{url(r)}" loading="lazy" alt=""{f" width={w}" if w else ""}></a>'
        return f'<a href="{url(r)}">{E(r)}</a>'

    def ep_name(e):
        return (f'第{e["number"]}集 ' if e["number"] else "") + E(e["label"])

    def season_of(rows):
        out = {}
        for e in rows:
            out.setdefault(e["season"], []).append(e)
        return sorted(out.items(), key=lambda x: (x[0] is None, x[0] or 0))

    def home():
        eps = q("SELECT * FROM episodes")
        yt = {}
        for r in q("SELECT * FROM youtube"):
            yt.setdefault(r["folder"], {})[r["kind"]] = r
        tot = q("SELECT (SELECT COUNT(*) FROM shots WHERE clip IS NOT NULL) c, (SELECT COUNT(*) FROM shots WHERE clip IS NOT NULL AND kind='對嘴') l,"
                " (SELECT SUM(credits) FROM episodes) cr, (SELECT SUM(full_dur) FROM episodes) d, (SELECT COUNT(*) FROM files) f,"
                " (SELECT SUM(size) FROM files) s, (SELECT COUNT(DISTINCT folder) FROM youtube) y")[0]
        stats = "".join(f'<div class="stat"><b>{v}</b><span class="sub">{t}</span></div>' for t, v in (
            ("集", sum(e["stage"] not in NO_PROJECT for e in eps)), ("完成", sum(e["full"] is not None for e in eps)), ("有上傳紀錄", tot["y"]),
            ("影片片段", tot["c"]), ("對嘴片段", tot["l"]), ("完整版總長", fmt_d(tot["d"])), ("估計點數", f'{tot["cr"] or 0:,}'),
            ("檔案", f'{tot["f"]:,}'), ("容量", f'{(tot["s"] or 0) / 1e9:.1f} GB')))

        def card(e):
            y = yt.get(e["folder"], {})
            links = "　".join(f'<a href="https://youtu.be/{E(v["video_id"])}">{MODE.get(k, k)} ▶</a>' for k, v in y.items())
            renders = json.loads(e["renders"] or "[]")
            lens = "・".join(f'{MODE.get(r["mode"], r["mode"])} {fmt_d(r["dur"])}' for r in renders)
            nums = (f'{e["n_clips"]}/{e["n_shots"]} 段素材' + (f'・對嘴 {e["ls_share"]:.0%}' if e["ls_share"] is not None else "")
                    + f'・{e["credits"] or 0:,} 點') if e["stage"] not in NO_PROJECT else ""
            pic = f'<img src="{url(e["cover"])}" loading="lazy" alt="">' if e["cover"] else "<img alt>"
            return (f'<div class="card"><a href="{ep_url(e["folder"])}">{pic}</a><div class="b">'
                    f'<a href="{ep_url(e["folder"])}"><b>{ep_name(e)}</b></a> <span class="chip{" on" if e["stage"] == "已上傳" else ""}">{e["stage"]}</span>'
                    f'<div class="sub">{E(e["genre"] or "")}</div><div class="sub">{lens}</div><div class="sub">{nums}</div>'
                    f'<div class="sub">{links or ("沒有上傳紀錄" if e["full"] else "")}</div></div></div>')

        body = ""
        for s, items in season_of(eps):
            done = [x for x in items if x["full_dur"]]
            body += (f'<h2>{f"第 {s} 季" if s else "其他"}</h2><p class="sub">{len(items)} 集・完成 {len(done)}・完整版共 '
                     f'{fmt_d(sum(x["full_dur"] for x in done))}・估計 {sum(x["credits"] or 0 for x in items):,} 點</p>'
                     f'<div class="grid">{"".join(card(x) for x in items)}</div>')
        return page("總覽", f'<h1>總覽</h1><div class="stats">{stats}</div>{body}')

    def episode(folder):
        e = q("SELECT * FROM episodes WHERE folder=?", folder)
        if not e:
            return None
        e = e[0]
        renders = json.loads(e["renders"] or "[]")
        top = "".join(f'<div><h2>{MODE.get(r["mode"], r["mode"])} {fmt_d(r["dur"])}</h2>{media(r["path"], 220 if r["vertical"] else 520, r["thumb"] or "")}</div>'
                      for r in renders)
        links = [(t, e[k]) for t, k in (("歌詞", "lyrics"), ("狀態", "notes"), ("YouTube_SEO", "seo")) if e[k]]
        links += [("project.py", (folder + "/" if folder else "") + "project.py")] if e["stage"] not in NO_PROJECT else []
        info = (f'<h2>資料</h2><p>{E(e["genre"] or "")}{"・" + E(e["tagline"]) if e["tagline"] else ""}</p>'
                + (f'<p>歌曲 {fmt_d(e["song_dur"])}<br>{media(e["song"])}</p>' if e["song"] else "")
                + "<p>" + "・".join(f'<a href="{url(p)}">{t}</a>' for t, p in links) + "</p>")
        if e["stage"] not in NO_PROJECT:
            info += (f'<p>{e["n_clips"]}/{e["n_shots"]} 段素材有影片' + (f'・完整版對嘴佔 {e["ls_share"]:.0%}' if e["ls_share"] is not None else "")
                     + f'・估計 {e["credits"] or 0:,} 點（<a href="/jobs?ep={urllib.parse.quote(folder)}">任務</a>）</p>')
        for y in q("SELECT * FROM youtube WHERE folder=?", folder):
            info += f'<p><b>{MODE.get(y["kind"], y["kind"])}</b> {E(y["title"] or "")}<br>{yt_link(y["video_id"])} <span class="sub">{E((y["at"] or "")[:16].replace("T", " "))}</span></p>'
        top = f'<div class="row">{top}<div class="grow">{info}</div></div>'
        chars = q("SELECT * FROM chars WHERE folder=? ORDER BY kind='ref', key", folder)
        cast = (f'<h2>角色與參考圖</h2><div class="grid small portrait">' + "".join(
            f'<div class="card">{media(c["file"])}<div class="b"><b>{E(c["name"] or c["key"])}</b> <span class="sub">{E(c["key"])}</span></div></div>'
            for c in chars) + "</div>") if chars else ""

        def shot_row(s):
            u = json.loads(s["edits"] or "{}")
            chips = "".join(f'<span class="chip">{MODE.get(k, k)}{f" ×{n}" if n > 1 else ""}</span>' for k, n in u.items()) or '<span class="sub">沒用到</span>'
            text = E(s["caption"] or "") + (f'<div>{E(s["lyric"])}</div>' if s["lyric"] else "")
            still = media(s["still"]) + (f'<div class="sub">→</div>{media(s["still_end"])}' if s["still_end"] else "")
            spans = f'{fmt_d(s["a0"])} 起 {s["a_dur"]:.1f} 秒・{E(s["voice"] or "")}' if s["a0"] is not None and s["a_dur"] else ""
            under = (fmt_d(s["clip_dur"]) if s["clip_dur"] else "") + (f'・舊版與候選 {s["versions"]}' if s["versions"] else "")
            return (f'<tr><td><a href="{shot_url(folder, s["id"])}"><b>{E(s["id"])}</b></a><div class="sub">{E(s["feature"] or s["kind"])}</div></td>'
                    f'<td>{text}<div class="sub">{spans}</div></td>'
                    f'<td>{still}</td><td>{media(s["clip"], None, s["clip_thumb"] or "") if s["clip"] else "<span class=sub>沒有影片</span>"}'
                    f'<div class="sub">{under}</div></td>'
                    f'<td>{chips}</td></tr>')

        rows = "".join(shot_row(s) for s in q("SELECT * FROM shots WHERE folder=? ORDER BY kind!='對嘴', id", folder))
        shots = (f'<h2>素材</h2><div class="wrap"><table><tr><th>素材</th><th>說明／歌詞</th><th>靜圖</th><th>影片</th><th>用在</th></tr>{rows}</table></div>'
                 if rows else "")
        lyr = q("SELECT * FROM lyrics WHERE folder=? ORDER BY t", folder)
        lyrics = (f'<details><summary>歌詞時間（{len(lyr)} 句）</summary><table><tr><th>時間</th><th>段落</th><th>聲部</th><th>歌詞</th></tr>' + "".join(
            f'<tr><td>{fmt_d(r["t"]) if r["t"] is not None else ""}</td><td class="sub">{E(r["section"] or "")}</td><td>{E(r["voice"] or "")}</td><td>{E(r["text"])}</td></tr>'
            for r in lyr) + "</table></details>") if lyr else ""
        edits = ""
        for m in q("SELECT mode, COUNT(*) n, COUNT(DISTINCT src) u, SUM(rep) r, SUM(dur) d FROM edit_rows WHERE folder=? GROUP BY mode", folder):
            er = q("SELECT * FROM edit_rows WHERE folder=? AND mode=? ORDER BY n", folder, m["mode"])
            edits += (f'<details><summary>剪輯表 {MODE.get(m["mode"], m["mode"])}：{m["n"]} 列、{fmt_d(m["d"])}、用了 {m["u"]} 段素材、'
                      f'<span class="{"bad" if m["r"] else ""}">重複 {m["r"]} 列</span></summary><table><tr><th>開始</th><th>素材</th><th>入點</th><th>長度</th><th>旗標</th><th>註解</th></tr>'
                      + "".join(f'<tr><td>{fmt_d(r["t"])} <span class="sub">{r["t"]:.2f}</span></td><td><a href="{shot_url(folder, r["src"])}"'
                                f'{" class=bad" if r["rep"] else ""}>{E(r["src"])}</a></td><td>{"" if r["off"] is None else r["off"]}</td>'
                                f'<td>{r["dur"]:.2f}</td><td>{E(r["flags"] or "")}</td><td class="sub">{E(r["note"] or "")}</td></tr>' for r in er)
                      + "</table></details>")
        thumbs = q("SELECT path FROM files WHERE folder=? AND kind='thumbnail' ORDER BY mtime DESC", folder)
        gallery = (f'<h2>縮圖（{len(thumbs)}）</h2><div class="grid small">' + "".join(
            f'<div class="card">{media(t["path"])}<div class="b sub">{E(t["path"].split("/")[-1])}</div></div>' for t in thumbs) + "</div>") if thumbs else ""
        reviews = q("SELECT path FROM files WHERE folder=? AND kind='review' AND path NOT LIKE '%.json' ORDER BY mtime DESC", folder)
        gallery += (f'<details><summary>審核圖（{len(reviews)}）</summary><div class="grid small">' + "".join(
            f'<div class="card">{media(t["path"])}<div class="b sub">{E(t["path"].split("/")[-1])}</div></div>' for t in reviews) + "</div></details>") if reviews else ""
        season = f'第 {e["season"]} 季・' if e["season"] else ""
        head = f'<p class="sub">{season}{E(e["stage"])}{"・" + E(folder) if folder else ""}</p><h1>{ep_name(e)}</h1>'
        return page(e["label"], head + top + cast + shots + lyrics + edits + gallery)

    def shot(folder, sid):
        s = q("SELECT * FROM shots WHERE folder=? AND id=?", folder, sid)
        if not s:
            return None
        s = s[0]
        e = q("SELECT * FROM episodes WHERE folder=?", folder)[0]
        refs = json.loads(s["refs"] or "[]")
        pics = [(f"@圖片 {n}", r) for n, r in enumerate(refs, 1)] if refs else             [("首幀" if s["still_end"] else "靜圖", s["still"])] + ([("尾幀", s["still_end"])] if s["still_end"] else [])
        stills = "".join(f'<div><h2>{t}</h2>{media(r, 300)}</div>' for t, r in pics if r)
        top = f'<div class="row"><div><h2>影片 {fmt_d(s["clip_dur"])}</h2>{media(s["clip"], 520, s["clip_thumb"] or "") if s["clip"] else "沒有影片"}</div>{stills}</div>'
        text = "".join(f'<h2>{t}</h2><pre>{E(v)}</pre>' for t, v in (("說明", s["caption"]), ("歌詞", s["lyric"]),
                                                                       ("影片提示詞" if refs else "靜圖提示詞", s["prompt"]), ("動作提示詞", s["motion"])) if v)
        if s["a0"] is not None:
            text += f'<p class="sub">對嘴音檔：歌曲 {s["a0"]:.2f} 起 {s["a_dur"] or 0:.2f} 秒，聲部 {E(s["voice"] or "")}，角色 {E(s["chars"] or "")}</p>'
        er = q("SELECT * FROM edit_rows WHERE folder=? AND src=? ORDER BY mode, n", folder, sid)
        text += (f'<h2>剪輯表（{len(er)} 列）</h2><table><tr><th>版本</th><th>開始</th><th>入點</th><th>長度</th><th>旗標</th><th>註解</th></tr>' + "".join(
            f'<tr><td>{MODE.get(r["mode"], r["mode"])}</td><td>{fmt_d(r["t"])} <span class="sub">{r["t"]:.2f}</span></td><td>{"" if r["off"] is None else r["off"]}</td>'
            f'<td>{r["dur"]:.2f}</td><td>{E(r["flags"] or "")}</td><td class="sub">{E(r["note"] or "")}</td></tr>' for r in er) + "</table>") if er else '<p class="sub">剪輯表沒用到</p>'
        stem = "%/" + sid
        jobs = q("SELECT * FROM jobs WHERE folder=? AND (out LIKE ? OR out LIKE ? OR out LIKE ?) ORDER BY file", folder, stem + ".mp4", stem + ".png", stem + "_%")
        text += (f'<h2>任務（{len(jobs)}）</h2><div class="wrap"><table><tr><th>任務檔</th><th>端點</th><th>狀態</th><th>點數</th><th>輸出</th><th>提示詞</th></tr>' + "".join(
            f'<tr><td>{E(j["file"])}</td><td>{E(j["endpoint"])}</td><td>{status(j)}</td>'
            f'<td>{j["credits"]}</td><td class="sub">{E(j["out"] or "")}</td><td class="sub">{E((j["prompt"] or "")[:300])}</td></tr>' for j in jobs) + "</table></div>") if jobs else ""
        vs = q("SELECT f.path, f.thumb FROM versions v JOIN files f USING (path) WHERE v.folder=? AND v.id=? ORDER BY f.mtime DESC", folder, sid)
        text += (f'<h2>舊版與候選（{len(vs)}）</h2><div class="grid small">' + "".join(
            f'<div class="card">{media(v["path"], None, v["thumb"] or "")}<div class="b sub">{E(v["path"].split("/", 1)[-1])}</div></div>' for v in vs) + "</div>") if vs else ""
        return page(sid, f'<p class="sub"><a href="{ep_url(folder)}">{ep_name(e)}</a>・{E(s["feature"] or s["kind"])}</p><h1>{E(sid)} {E(s["caption"] or "")}</h1>{top}{text}')

    def chars_page():
        eps = {e["folder"]: e for e in q("SELECT * FROM episodes")}
        body = ""
        for s, items in season_of(eps.values()):
            for e in items:
                cs = q("SELECT * FROM chars WHERE folder=? ORDER BY kind='ref', key", e["folder"])
                if not cs:
                    continue
                body += f'<h2><a href="{ep_url(e["folder"])}">{f"S{s} " if s else ""}{ep_name(e)}</a></h2><div class="grid small portrait">' + "".join(
                    f'<div class="card">{media(c["file"])}<div class="b"><b>{E(c["name"] or c["key"])}</b> <span class="sub">{E(c["key"])}・{E(c["kind"] or "")}</span>'
                    f'<details><summary class="sub">描述</summary><p class="sub">{E(c["descr"] or "")}</p></details></div></div>' for c in cs) + "</div>"
        return page("角色", f'<h1>角色與參考圖</h1>{body}')

    def files_page(kind):
        kinds = q("SELECT kind, COUNT(*) n, SUM(size) s FROM files GROUP BY kind ORDER BY n DESC")
        chips = "".join(f'<a class="chip{" on" if k["kind"] == kind else ""}" href="/files?kind={k["kind"]}">{k["kind"]} {k["n"]}・{(k["s"] or 0) / 1e6:,.0f} MB</a>' for k in kinds)

        def file_row(f):
            wh = f'{f["w"]}×{f["h"]}' if f["w"] else ""
            return (f'<tr><td><a href="{url(f["path"])}">{E(f["path"])}</a></td><td>{f["kind"]}</td><td>{(f["size"] or 0) / 1e6:.1f} MB</td>'
                    f'<td>{fmt_d(f["dur"]) if f["dur"] else ""}</td><td>{wh}</td>'
                    f'<td class="sub">{datetime.fromtimestamp(f["mtime"]).strftime("%m-%d %H:%M")}</td></tr>')

        rows = "".join(file_row(f) for f in q("SELECT * FROM files WHERE kind=? ORDER BY path LIMIT 2000" if kind else
                                               "SELECT * FROM files ORDER BY mtime DESC LIMIT 200", *([kind] if kind else [])))
        return page("檔案", f'<h1>檔案{(" ・ " + E(kind)) if kind else "（最近 200 個）"}</h1><p>{chips}</p><div class="wrap"><table>'
                    f'<tr><th>路徑</th><th>類別</th><th>大小</th><th>長度</th><th>尺寸</th><th>修改</th></tr>{rows}</table></div>')

    def jobs_page(folder):
        summ = "".join(f'<tr><td><a href="/jobs?ep={urllib.parse.quote(r["folder"])}">{E(r["folder"] or "（系列）")}</a></td><td>{r["n"]}</td><td>{r["c"] or 0:,}</td>'
                       f'<td>{r["v"]:,}</td><td>{r["bad"]}</td></tr>' for r in q(
                           "SELECT folder, COUNT(*) n, SUM(credits) c, SUM(CASE WHEN endpoint LIKE '/videos/%' THEN credits ELSE 0 END) v,"
                           " SUM(status IS NULL OR status NOT IN ('completed', 'output_only')) bad FROM jobs GROUP BY folder ORDER BY folder"))
        body = f'<h1>任務與點數</h1><table><tr><th>集</th><th>任務</th><th>估計點數</th><th>其中影片</th><th>沒完成</th></tr>{summ}</table>'
        if folder:
            by = "".join(f'<tr><td>{E(r["endpoint"])}</td><td>{r["n"]}</td><td>{r["c"] or 0:,}</td></tr>' for r in q(
                "SELECT endpoint, COUNT(*) n, SUM(credits) c FROM jobs WHERE folder=? GROUP BY endpoint ORDER BY c DESC", folder))
            rows = "".join(f'<tr><td>{E(j["file"])}</td><td>{E(j["id"] or "")}</td><td>{E(j["endpoint"])}</td><td>{status(j)}</td>'
                           f'<td>{j["credits"]}</td><td class="sub">{E((j["prompt"] or "")[:160])}</td></tr>'
                           for j in q("SELECT * FROM jobs WHERE folder=? ORDER BY file, id", folder))
            body += (f'<h2><a href="{ep_url(folder)}">{E(folder)}</a></h2><table><tr><th>端點</th><th>任務</th><th>估計點數</th></tr>{by}</table>'
                     f'<div class="wrap"><table><tr><th>任務檔</th><th>id</th><th>端點</th><th>狀態</th><th>點數</th><th>提示詞</th></tr>{rows}</table></div>')
        return page("任務", body + '<p class="sub">點數照任務檔和 .state 估算：失敗會退點，不算；同一個任務重送只算最後一次；'
                    '沒有 .state 但輸出還在的，算一次。要對帳用 mvkit/credits.py。</p>')

    def youtube_page():
        eps = {e["folder"]: e for e in q("SELECT * FROM episodes")}
        rows = ""
        for y in q("SELECT * FROM youtube"):
            e = eps.get(y["folder"])
            rows += (f'<tr><td><a href="{ep_url(y["folder"])}">{ep_name(e) if e else E(y["folder"])}</a></td><td>{MODE.get(y["kind"], y["kind"])}</td>'
                     f'<td>{E(y["title"] or "")}</td><td>{E((y["at"] or "")[:16].replace("T", " "))}</td><td>{yt_link(y["video_id"])}</td></tr>')
        missing = [e for e in eps.values() if e["full"] and not q("SELECT 1 FROM youtube WHERE folder=?", e["folder"])]
        note = ('<p class="sub">完成但沒有 youtube.json 上傳紀錄：' + "、".join(f'<a href="{ep_url(e["folder"])}">{ep_name(e)}</a>' for e in missing) + "</p>") if missing else ""
        return page("YouTube", f'<h1>YouTube</h1><div class="wrap"><table><tr><th>集</th><th>版本</th><th>標題</th><th>上傳時間</th><th>影片</th></tr>{rows}</table></div>{note}')

    def search_page(s):
        like = f"%{s}%"
        lyr = q("SELECT l.folder, l.t, l.text, l.voice, e.label FROM lyrics l JOIN episodes e USING (folder) WHERE l.text LIKE ? ORDER BY l.folder, l.t", like)
        shots = q("SELECT folder, id, kind, caption, lyric, still, clip, clip_thumb FROM shots WHERE id LIKE ? OR caption LIKE ? OR lyric LIKE ? OR prompt LIKE ? OR motion LIKE ?"
                  " ORDER BY folder, id LIMIT 300", like, like, like, like, like)
        eps = q("SELECT * FROM episodes WHERE label LIKE ? OR title LIKE ? OR genre LIKE ? OR tagline LIKE ?", like, like, like, like)
        chars = q("SELECT * FROM chars WHERE key LIKE ? OR name LIKE ? OR descr LIKE ?", like, like, like)
        yts = q("SELECT * FROM youtube WHERE title LIKE ? OR video_id LIKE ?", like, like)
        files = q("SELECT path, kind FROM files WHERE path LIKE ? LIMIT 100", like)
        body = f'<h1>搜尋「{E(s)}」</h1><h2>集（{len(eps)}）</h2>' + "".join(f'<a class="chip" href="{ep_url(e["folder"])}">{ep_name(e)}・{E(e["genre"] or "")}</a>' for e in eps)
        body += f'<h2>歌詞（{len(lyr)}）</h2><table>' + "".join(
            f'<tr><td><a href="{ep_url(r["folder"])}">{E(r["label"])}</a></td><td>{fmt_d(r["t"]) if r["t"] is not None else ""}</td><td>{E(r["voice"] or "")}</td><td>{E(r["text"])}</td></tr>' for r in lyr) + "</table>"
        body += f'<h2>素材（{len(shots)}）</h2><table>' + "".join(
            f'<tr><td><a href="{shot_url(r["folder"], r["id"])}">{E(r["folder"])} {E(r["id"])}</a><div class="sub">{E(r["kind"])}</div></td><td>{E(r["caption"] or "")}'
            f'<div class="sub">{E(r["lyric"] or "")}</div></td><td>{media(r["still"])}</td><td>{media(r["clip"], None, r["clip_thumb"] or "") if r["clip"] else ""}</td></tr>' for r in shots) + "</table>"
        body += f'<h2>角色（{len(chars)}）</h2>' + "".join(f'<a class="chip" href="{ep_url(c["folder"])}">{E(c["name"] or c["key"])}・{E(c["folder"])}</a>' for c in chars)
        body += f'<h2>YouTube（{len(yts)}）</h2>' + "".join(f'<p><a href="{ep_url(y["folder"])}">{E(y["folder"])}</a> {E(y["title"] or "")} {yt_link(y["video_id"])}</p>' for y in yts)
        body += f'<h2>檔案（{len(files)}）</h2>' + "".join(f'<div><a href="{url(f["path"])}">{E(f["path"])}</a> <span class="sub">{f["kind"]}</span></div>' for f in files)
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
            if not p.startswith(series + os.sep) or not os.path.isfile(p) or SECRET.search(os.path.basename(p)):
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
            nf = lambda: self.send("not found", 404, "text/plain; charset=utf-8")
            try:
                if path.startswith("/f/"):
                    return self.file(path[3:])
                if path == "/":
                    return self.send(home())
                if path.startswith("/ep/"):
                    body = episode(path[4:])
                    return self.send(body) if body else nf()
                if path.startswith("/shot/") and "/" in path[6:]:
                    body = shot(*path[6:].rsplit("/", 1))
                    return self.send(body) if body else nf()
                routes = {"/chars": chars_page, "/youtube": youtube_page}
                if path in routes:
                    return self.send(routes[path]())
                if path == "/files":
                    return self.send(files_page(qs.get("kind", [""])[0]))
                if path == "/jobs":
                    return self.send(jobs_page(qs.get("ep", [""])[0]))
                if path == "/search":
                    return self.send(search_page(qs.get("q", [""])[0].strip()))
                nf()
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

    class Server(ThreadingHTTPServer):
        allow_reuse_address = os.name != "nt"   # on Windows SO_REUSEADDR lets a second server bind a busy port silently

    for p in range(port, port + 20):
        try:
            srv = Server(("127.0.0.1", p), H)
            break
        except OSError:
            print(f"  port {p} is in use, trying {p + 1}", flush=True)
    else:
        sys.exit(f"no free port in {port}-{port + 19}: pass --port")
    threading.Thread(target=watch, daemon=True).start()
    print(f"library: http://127.0.0.1:{p}  (Ctrl+C to stop; re-indexes by itself when files change)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("index", "serve"):
        sys.exit(__doc__)
    cmd, series = sys.argv[1], sys.argv[2]
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8770
    if cmd == "index" or "--no-index" not in sys.argv:
        index(series).close()
    if cmd == "serve":
        serve(series, port)

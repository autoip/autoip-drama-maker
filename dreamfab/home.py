"""The library's front page (dreamfab/library.py serves it at /): Dreamfab as a factory floor.

產線: one conveyor per production line (戲 短劇, 曲 MV, 說 解說; 影 and 聞 are still to come) with its stations up to
the cover; an episode still being made sits at the first station it has not passed, and leaves the line for the
warehouse once it has a cut and a cover. A line with work on it runs (rollers turn, parcels ride into the warehouse,
busy stations blink); an idle one only turns slowly. 倉庫: a rack per series and a shelf per season, every episode standing on it
by its cover, marked uploaded (▶) or waiting to go up (待上架); one still on a line keeps an empty slot. 散件區: the
folders that are not a series yet. 庫存與出貨: per line, what is made but not uploaded, uploaded but not public, and
public (as youtube_log.py sync last saw it), and per channel what went out each day against the youtube.daily_max cap.
出貨紀錄: the latest entries of the YouTube log (dreamfab/youtube_log.py: uploads, publishing, comments, end screens,
cards). Everything else is read from what the lines already keep, so the page follows the work
as the files appear: drama and MV from their series' index in the shared database (dreamfab/db.py; their own
libraries build it), explainers from the
episode folders (explain/pages.py).
"""
import html, json, os, re, sqlite3, urllib.parse
from datetime import date, timedelta

import pages as explain_pages   # explain/pages.py; dreamfab/library.py puts explain/ on the path
from dreamfab import youtube_log   # pages.py puts the repo root on the path
from dreamfab.db import has_index, open_index
from dreamfab.workflow import get as workflow

E, Q = html.escape, urllib.parse.quote

LINES = (   # key, plate, name, stations, how to start one
    ("drama", "戲", "短劇", ("劇本", "分鏡", "生成", "剪輯", "封面"), "用 dreamfab-drama 把 劇本.md 做成短劇"),
    ("mv", "曲", "MV", ("歌曲", "分鏡", "生成", "剪輯", "封面"), "用 dreamfab-mv 把 song.mp3 做成 MV"),
    ("explain", "說", "解說", ("文案", "旁白", "畫面", "剪輯", "封面"), "用 dreamfab-explain 把一支 MV 背後的歷史做成解說"),
)
SOON = (("影", "電影"), ("聞", "新聞"))
RACK = {"drama": "A", "mv": "B", "explain": "C"}   # rack codes, one letter per line
TALL = {"drama"}                                    # lines whose covers are vertical (9:16)

CSS = """
:root{--bg:#f4f2ee;--card:#fff;--ink:#1d1b19;--sub:#6b6560;--line:#e2ddd6;--accent:#b3202f;--chip:#efe9e1;
--ok:#2f7d4f;--ok-bg:#e3f1e8;--doing:#9a6412;--doing-bg:#f8ecd6;--grid:rgba(60,50,40,.06);
--rack:#cdbfac;--track:#5b5650;--roll:#86807a;--drama:#b3202f;--mv:#2c5f8d;--explain:#9a6b12;--on:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#121110;--card:#1d1b1a;--ink:#ece8e3;--sub:#a59e97;--line:#34302d;
--accent:#e2505d;--chip:#2a2725;--ok:#7cc79a;--ok-bg:#1f3328;--doing:#e2b45e;--doing-bg:#3a2e1a;--grid:rgba(255,255,255,.04);
--rack:#4d453d;--track:#3a3632;--roll:#5c5650;--drama:#e2505d;--mv:#6aa5d8;--explain:#e0b45a;--on:#161412}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,"Microsoft JhengHei","PingFang TC",sans-serif}
a{color:var(--accent)}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:16px;align-items:center}
header b{color:var(--accent)}header nav{margin-left:auto;display:flex;gap:14px}header nav a{color:var(--ink);text-decoration:none}
main{max-width:1180px;margin:0 auto;padding:18px 16px 60px}
.sub{color:var(--sub);font-size:14px}
.l-drama{--lc:var(--drama)}.l-mv{--lc:var(--mv)}.l-explain{--lc:var(--explain)}
.hero{border:1px solid var(--line);border-radius:16px;padding:22px 20px 20px;background-color:var(--card);
background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);background-size:24px 24px}
.hero h1{margin:0;font-size:28px;letter-spacing:.02em}.hero p{margin:4px 0 0}
.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px;margin-top:18px}
.node{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px;color:var(--ink);text-decoration:none;min-width:100px}
.node b{display:block;font-size:15px}.node span{font-size:12.5px;color:var(--sub)}a.node:hover{border-color:var(--accent)}
.node.key{border-color:var(--ink)}.arr{align-self:center;color:var(--sub);font-size:18px;animation:nudge 3s ease-in-out infinite}
@keyframes nudge{0%,60%,100%{transform:none;color:var(--sub)}30%{transform:translateX(3px);color:var(--accent)}}
h2{font-size:20px;margin:34px 0 12px;display:flex;align-items:baseline;gap:10px}h2 .sub{font-weight:400}
.line{display:grid;grid-template-columns:72px minmax(0,1fr);gap:14px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}
.plate{display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:10px;background:var(--lc);color:var(--on);min-height:72px}
.plate b{font:700 32px/1 "Noto Serif TC","PMingLiU",serif}.plate span{font-size:12px;margin-top:4px}
.floor{min-width:0}.scroll{overflow-x:auto;padding-bottom:2px}
.belt{display:grid;grid-template-columns:repeat(5,minmax(112px,1fr)) 58px;grid-template-rows:auto 1fr 24px;column-gap:14px;row-gap:8px;min-width:680px}
.st{grid-row:1/3;display:flex;flex-direction:column;gap:8px;min-width:0}
.mach{position:relative;display:flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:8px;padding:5px 8px;font-weight:600;font-size:14px;background:var(--bg)}
.mach::after{content:"";position:absolute;right:-15px;top:50%;width:14px;height:2px;opacity:.5;background:linear-gradient(90deg,var(--sub) 0 2px,transparent 2px) 0 0/5px 100%}
.line.run .mach::after{opacity:.9;animation:march .8s linear infinite}@keyframes march{to{background-position:5px 0}}
.mach .no{font:11px ui-monospace,Consolas,monospace;color:var(--sub)}
.st.busy .mach{border-color:var(--lc);color:var(--lc)}.st.busy .mach b{animation:ping 1.6s ease-out infinite}
@keyframes ping{from{box-shadow:0 0 0 0 color-mix(in srgb,var(--lc) 70%,transparent)}to{box-shadow:0 0 0 7px transparent}}.mach b{margin-left:auto;background:var(--lc);color:var(--on);border-radius:10px;font-size:12px;padding:0 7px}
.bay{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:6px;min-height:20px}
.track{position:relative;overflow:hidden;grid-column:1/6;grid-row:3}
.track::after{content:"";position:absolute;left:0;right:0;bottom:0;height:12px;border-radius:6px;background:linear-gradient(90deg,var(--roll) 0 3px,var(--track) 3px) 0 0/14px 100%;box-shadow:inset 0 1px 3px rgba(0,0,0,.35)}
.track.run::after{animation:roll .6s linear infinite}.track.idle::after{animation:roll 3s linear infinite}@keyframes roll{to{background-position:14px 0}}
.track i{position:absolute;left:0;right:0;bottom:12px;height:11px;pointer-events:none;animation:ship 10s linear infinite}
.track i::before{content:"";position:absolute;left:0;bottom:1px;width:16px;height:10px;border-radius:2px;background:var(--lc);box-shadow:inset 0 -3px 0 rgba(0,0,0,.25),inset 0 2px 0 rgba(255,255,255,.25)}
.track i:nth-child(2){animation-delay:-3.4s}.track i:nth-child(3){animation-delay:-6.7s}
@keyframes ship{0%{transform:translateX(0);opacity:0}5%,92%{opacity:1}100%{transform:translateX(calc(100% - 16px));opacity:0}}
.gate{grid-column:6;grid-row:1/4;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;border-left:2px dashed var(--line);color:var(--sub);font-size:13px;text-decoration:none}
.gate span{font-size:20px;line-height:1}.line.run .gate span{animation:drop 1.6s ease-in infinite}
@keyframes drop{0%{transform:translateY(-5px);opacity:.2}60%{transform:translateY(2px);opacity:1}100%{transform:translateY(5px);opacity:0}}a.gate:hover{color:var(--accent)}
.crate{display:block;background:var(--card);border:1px solid var(--line);border-top:3px solid var(--lc);border-radius:6px;overflow:hidden;color:var(--ink);text-decoration:none;font-size:12.5px;box-shadow:0 2px 0 rgba(0,0,0,.08)}
a.crate:hover{border-color:var(--lc)}
.crate img,.crate .noimg{display:block;width:100%;height:58px;object-fit:cover;background:var(--chip)}
.crate .noimg{background:repeating-linear-gradient(45deg,var(--chip) 0 6px,transparent 6px 12px)}
.crate .cl{display:block;padding:4px 7px 0;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.crate .cs{display:block;padding:0 7px 6px;color:var(--sub);font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pg{display:block;margin:-2px 7px 7px;height:4px;background:var(--chip);border-radius:2px;overflow:hidden}
.pg i{display:block;height:100%;background:linear-gradient(90deg,rgba(255,255,255,.35) 0 3px,transparent 3px) 0 0/8px 100%,var(--lc);animation:stripe .7s linear infinite}
@keyframes stripe{to{background-position:8px 0,0 0}}
.more{font-size:12px;color:var(--sub);text-align:center;border:1px dashed var(--line);border-radius:6px;padding:3px}
.feed{margin-top:10px;font-size:13px;color:var(--sub)}.feed code{background:var(--chip);border-radius:6px;padding:1px 6px;color:var(--ink)}
.soon{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.soon .line{background:transparent;border-style:dashed;margin:0;align-items:center}.soon .plate{background:var(--chip);color:var(--sub)}
.racks{display:grid;gap:16px}
.rack{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px 16px}
.rack-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;margin-bottom:10px}
.code{font:600 12px ui-monospace,Consolas,monospace;background:var(--lc);color:var(--on);border-radius:4px;padding:1px 7px}
.rack-head h3{margin:0;font-size:17px}.rack-head h3 a{color:var(--ink);text-decoration:none}.rack-head h3 a:hover{color:var(--accent)}
.rack-head .go{margin-left:auto;font-size:13.5px;text-decoration:none}
.frame{border-left:6px solid var(--rack);border-right:6px solid var(--rack);padding:0 10px}
.tier{padding-top:10px}.tier-label{display:inline-block;font-size:12px;color:var(--sub);border:1px solid var(--line);border-radius:4px;padding:0 6px;margin-bottom:6px;background:var(--bg)}
.shelf{display:flex;gap:10px;align-items:flex-end;overflow-x:auto;padding:5px 2px 0;border-bottom:7px solid var(--rack)}
.rack{--w:164px;--ar:16/9}.rack.tall{--w:78px;--ar:9/16}
.box{flex:none;width:var(--w);position:relative;color:var(--ink);text-decoration:none;font-size:12px;padding-bottom:5px}
.box img,.box .ph{display:block;width:100%;aspect-ratio:var(--ar);object-fit:cover;border-radius:4px;background:var(--chip);box-shadow:0 1px 4px rgba(0,0,0,.25);transition:transform .15s}
a.box:hover img{transform:translateY(-4px)}
.box .ph{border:2px dashed var(--lc);box-shadow:none;background:transparent;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;color:var(--lc);font-size:11.5px;text-align:center;line-height:1.3;padding:4px}
.box .cap{display:block;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tag{position:absolute;top:4px;right:4px;font-size:10.5px;font-weight:600;border-radius:10px;padding:0 6px;background:var(--doing-bg);color:var(--doing)}
.tag.ok{background:var(--ok);color:#fff}.tag.old{background:var(--chip);color:var(--sub)}
.loose{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}
.loose a{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;color:var(--ink);text-decoration:none;font-size:13px}
.loose a:hover{border-color:var(--accent)}.loose img,.loose .noimg{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:var(--chip)}
.loose b{display:block;padding:6px 10px 0}.loose span{display:block;padding:0 10px 8px;color:var(--sub);font-size:12px}
.stock{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:14px}
.stock>div{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px;overflow-x:auto}
.stock h3{margin:0 0 8px;font-size:15px}.stock table{border-collapse:collapse;width:100%;font-size:14px}
.stock th{font-weight:500;color:var(--sub);text-align:right;padding:4px 8px;white-space:nowrap}.stock th:first-child{text-align:left}
.stock td{text-align:right;padding:5px 8px;border-top:1px solid var(--line);font-variant-numeric:tabular-nums;white-space:nowrap}
.stock td:first-child{text-align:left}.stock tr.sum td{font-weight:600}.stock td i{font-style:normal;color:var(--sub);font-size:12px}
.today{font-size:22px;font-weight:700}.today.over{color:var(--accent)}.today span{font-size:13px;font-weight:400;color:var(--sub)}
.day{display:grid;grid-template-columns:52px minmax(0,1fr) 30px;gap:8px;align-items:center;font-size:13px;margin:4px 0}
.day .b{height:10px;border-radius:5px;background:var(--chip);position:relative;overflow:hidden}
.day .b i{position:absolute;left:0;top:0;bottom:0;background:var(--ok);border-radius:5px}.day.over .b i{background:var(--accent)}
.day .n{text-align:right;font-variant-numeric:tabular-nums}.day .d{color:var(--sub);font-variant-numeric:tabular-nums}
.stock .cap{position:absolute;top:0;bottom:0;border-left:2px dashed var(--ink);opacity:.45}
@media (max-width:760px){.stock{grid-template-columns:minmax(0,1fr)}}
.ship{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:6px 14px;overflow-x:auto}
.ship table{border-collapse:collapse;width:100%;font-size:13.5px}.ship td{border-bottom:1px solid var(--line);padding:7px 6px;vertical-align:top}
.ship tr:last-child td{border-bottom:0}.ship .t{color:var(--sub);white-space:nowrap;font-variant-numeric:tabular-nums}
.ship .a{white-space:nowrap}.ship .a span{background:var(--ok-bg);color:var(--ok);border-radius:10px;padding:1px 8px;font-size:12px}
.ship .w{white-space:nowrap;color:var(--sub)}.ship .x{max-width:520px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media (max-width:640px){.line{grid-template-columns:46px minmax(0,1fr);gap:10px;padding:12px}.plate b{font-size:24px}.plate span{font-size:11px}
.hero h1{font-size:24px}.rack{--w:140px}.rack.tall{--w:70px}header nav{gap:10px}}
"""


def rows(line, series, sql):
    """Rows from the series' index (line: drama or mv), or [] before its library has indexed it."""
    if not has_index(line, series):
        return []
    try:
        c = open_index(line, series)
        try:
            c.row_factory = sqlite3.Row
            return c.execute(sql).fetchall()
        finally:
            c.close()
    except sqlite3.Error:
        return []


def item(tier, order, short, long, href, cover, done, progress=None, dur=None, uploaded=False, old=False):
    """One episode: done is a flag per station; progress {station: (have, of)}; it is on a line until it has a cut and
    a cover (old: made before its line kept project folders, never on a line). It stands at the station after the last
    one it has passed (shots without a script file are still at 生成), or else at the first one it has not."""
    at = max((i + 1 for i, d in enumerate(done) if d), default=0)
    if at >= len(done):
        at = next((i for i, d in enumerate(done) if not d), len(done))
    return dict(tier=tier, order=order, short=short, long=long, href=href, cover=cover, done=done, progress=progress or {},
                dur=dur, uploaded=uploaded, old=old, wip=not old and not (done[3] and done[4]), at=at)


def drama(path, base):
    """base: the series' library address (/u/<name>/)."""
    out = []
    for r in rows("drama", path, "SELECT e.*, y.video_id, (SELECT thumb FROM files f WHERE f.path = e.main_video) AS poster, "
                                 "(SELECT count(*) FROM shots s WHERE s.folder = e.folder AND s.clip IS NOT NULL) AS clips "
                                 "FROM episodes e LEFT JOIN youtube y ON y.folder = e.folder"):
        season = int((re.match(r"s(\d+)", r["folder"]) or [0, 1])[1])
        comp, n, shots = r["kind"] == "compilation", r["number"] or 0, r["n_shots"] or 0
        cut = bool(r["main_video"])
        done = [comp or bool(r["script"]), comp or shots > 0, comp or cut or 0 < shots <= r["clips"], cut, bool(r["cover"])]
        pic = r["cover"] or r["poster"]
        out.append(item(f'S{season}・{r["title"]}', (season, comp, n), "合集" if comp else f'{n:02d} {r["label"]}',
                        f"S{season} 合集" if comp else f'S{season}E{n:02d} {r["label"]}', base + "ep/" + Q(r["folder"]),
                        os.path.join(path, pic) if pic else None, done, {2: (r["clips"], shots)} if shots else {},
                        r["main_dur"], bool(r["video_id"])))
    return out


def mv(path, base):
    out = []
    for r in rows("mv", path, "SELECT e.*, y.video_id FROM episodes e LEFT JOIN youtube y ON y.folder = e.folder "
                              "AND y.kind = 'full'"):
        old = r["stage"] == "沒有 project.py"
        if old and not r["cover"]:
            continue
        shots, clips, full = r["n_shots"] or 0, r["n_clips"] or 0, bool(r["full"])
        done = [bool(r["song"]), shots > 0, full or 0 < shots <= clips, full, bool(r["cover"])]
        s, n = r["season"] or 0, r["number"] or 0
        out.append(item(f"第 {s} 季" if s else "其他", (s or 99, n, r["folder"]), r["label"].replace("_", "・"),
                        f'S{s}E{n} {r["label"].replace("_", "・")}', base + "ep/" + Q(r["folder"]),
                        os.path.join(path, r["cover"]) if r["cover"] else None, done, {2: (clips, shots)} if shots else {},
                        r["full_dur"], bool(r["video_id"]), old))
    return out


def explain(path, base):
    """base: the series' /files/ address."""
    out = []
    for d in sorted(os.listdir(path)):
        p = os.path.join(path, d)
        if not explain_pages.is_episode(p):
            continue
        ep = explain_pages.episode(p)
        nv, ni = len(ep["parts"]), len(ep["images"])
        dv = sum(1 for x in ep["parts"] if any(v.startswith(x) for v in ep["voice"]))
        di = sum(1 for x in ep["images"] if x[3])
        thumb = next((t for t in ep["thumbs"] if t.startswith("thumb_A")), ep["thumbs"][0] if ep["thumbs"] else None)
        pic = os.path.join(p, "thumbnails", thumb) if thumb else next((os.path.join(p, x[3]) for x in ep["images"] if x[3]), None)
        name = ep["mv"] or d.split("_", 1)[-1]
        out.append(item("每一集", (ep["num"],), f'#{ep["num"]:02d} {name}', f'#{ep["num"]:02d} {name}', base + Q(d) + "/", pic,
                        [bool(ep["script"]), nv > 0 and dv == nv, ni > 0 and di == ni, bool(ep["cut"]), bool(ep["thumbs"])],
                        {1: (dv, nv), 2: (di, ni)}, ep["length"], bool(ep["yt"].get("id"))))
    return out


def shorts_waiting(line, path):
    """Shorts cut but not uploaded: an episode folder with an out/*shorts*.mp4 and no shorts id in its youtube.json
    (explainers and MVs; a drama episode is its own short)."""
    n = 0
    if line not in ("explain", "mv") or not os.path.isdir(path):
        return 0
    for d in os.listdir(path):
        out = os.path.join(path, d, "out")
        if d.startswith(("_", ".")) or not os.path.isdir(out) or not any(f.endswith(".mp4") and "shorts" in f for f in os.listdir(out)):
            continue
        try:
            yt = json.load(open(os.path.join(path, d, "youtube.json"), encoding="utf-8"))
        except (OSError, ValueError):
            yt = {}
        n += not (yt.get("shorts") or {}).get("id")
    return n


def stock_panel(racks, paths):
    """庫存與出貨: made but not uploaded (from the racks), uploaded but not public and public (the YouTube log as sync
    last saw it), and per channel the last week's output against the daily cap."""
    names = {"drama": "短劇", "mv": "MV", "explain": "解說"}
    rows = {n: {"made": [0, 0], "private": [0, 0], "public": [0, 0]} for n in names.values()}   # [長片 or 短劇, Shorts]
    for line, name, href, items in racks:
        r = rows.get(names.get(line))
        if r:
            r["made"][0] += sum(1 for it in items if it["done"][3] and not (it["uploaded"] or it["old"] or it["wip"]))
    for line, path in paths:
        if names.get(line) in rows:
            rows[names[line]]["made"][1] += shorts_waiting(line, path)
    unsynced = 0
    for ch, per in youtube_log.stock().items():
        for (line, fmt), by in per.items():
            r = rows.setdefault(line, {"made": [0, 0], "private": [0, 0], "public": [0, 0]})
            k = fmt == "Shorts"
            r["private"][k] += by.get("private", 0) + by.get("unlisted", 0) + by.get("scheduled", 0)
            r["public"][k] += by.get("public", 0)
            unsynced += by.get("unknown", 0)

    def cell(pair, line):
        if line == "短劇":
            return str(pair[0]) if pair[0] else "–"
        a, b = pair
        return (f"{a + b}<i> 長片 {a}・Shorts {b}</i>" if a and b else str(a + b)) if a + b else "–"
    body = "".join(f'<tr><td>{E(n)}</td><td>{cell(r["made"], n)}</td><td>{cell(r["private"], n)}</td><td>{cell(r["public"], n)}</td></tr>'
                   for n, r in rows.items())
    tot = {k: sum(sum(r[k]) for r in rows.values()) for k in ("made", "private", "public")}
    body += f'<tr class="sum"><td>合計</td><td>{tot["made"]}</td><td>{tot["private"]}</td><td>{tot["public"]}</td></tr>'
    left = (f'<div><h3>庫存</h3><table><tr><th>產線</th><th>做好沒上傳</th><th>已上傳沒公開</th><th>已公開</th></tr>{body}</table>'
            + (f'<p class="sub">有 {unsynced} 支還沒跟 YouTube 對過：<code>python dreamfab/youtube_log.py sync</code></p>' if unsynced else
               '<p class="sub">「已上傳沒公開」含排程；跟 YouTube 對帳：<code>python dreamfab/youtube_log.py sync</code></p>') + "</div>")
    cap, today = workflow("youtube.daily_max"), date.today()
    days = [(today - timedelta(days=i)).isoformat() for i in range(7)]
    right = []
    for ch, per in sorted(youtube_log.day_counts(7).items()):
        n = per.get(days[0], (0, 0, 0))[2]
        top = max([cap or 0] + [v[2] for v in per.values()]) or 1
        head = (f'<div class="today{" over" if cap and n > cap else ""}">今天出貨 {n}' + (f'<span>／上限 {cap}・'
                + (f'還能出 {cap - n} 支' if n < cap else "已到上限" if n == cap else f"超過 {n - cap} 支") + "</span>" if cap else
                "<span>（沒有設上限）</span>") + "</div>")
        bars = "".join(
            f'<div class="day{" over" if cap and per.get(d, (0, 0, 0))[2] > cap else ""}"><span class="d">{d[5:].replace("-", "/")}</span>'
            f'<span class="b" title="上傳 {per.get(d, (0, 0, 0))[0]}・公開 {per.get(d, (0, 0, 0))[1]}"><i style="width:{per.get(d, (0, 0, 0))[2] / top:.0%}"></i>'
            + (f'<span class="cap" style="left:{cap / top:.0%}"></span>' if cap else "") + f'</span>'
            f'<span class="n">{per.get(d, (0, 0, 0))[2]}</span></div>' for d in days)
        right.append(f'<div><h3>出貨・頻道 {E(ch[-6:])}</h3>{head}{bars}<p class="sub">一支影片當天上傳或公開都算一次，Shorts 也算；'
                     f'上限是工作流程開關 <code>youtube.daily_max</code></p></div>')
    return f'<div class="stock">{left}{"".join(right) or "<div class=sub>還沒有上架紀錄</div>"}</div>'


def hours(sec):
    m = round(sec / 60)
    return f"{m // 60} 小時 {m % 60} 分" if m >= 60 else f"{m} 分"


def page(series, explainers, loose, files_url):
    """series: [(name, path, line)] that their own libraries serve at /u/<name>/; explainers and loose: [(name, path)]
    served as files; files_url(path): the /files/ address of a file under the roots."""
    order = [l[0] for l in LINES]
    racks = [(line, name, "/u/" + Q(name) + "/", path) for name, path, line in series] + \
            [("explain", name, files_url(path) + "/", path) for name, path in explainers]
    paths = [(line, path) for line, _, _, path in racks]
    racks = [(line, name, href, {"drama": drama, "mv": mv, "explain": explain}.get(line, drama)(path, href))
             for line, name, href, path in sorted(racks, key=lambda r: (order.index(r[0]) if r[0] in order else 9, r[1]))]

    def img(path, w):
        return f'<img loading="lazy" decoding="async" src="{files_url(path)}?w={w}" alt="">'

    def crate(name, it):
        have, of = it["progress"].get(it["at"], (0, 0))
        bar = f'<span class="pg"><i style="width:{have / of:.0%}"></i></span>' if of else ""
        note = f"・{have}/{of}" if of else ""
        return (f'<a class="crate" href="{it["href"]}" title="{E(name)} {E(it["long"])}">'
                f'{img(it["cover"], 240) if it["cover"] else "<span class=noimg></span>"}'
                f'<span class="cl">{E(it["long"])}{E(note)}</span><span class="cs">{E(name)}</span>{bar}</a>')

    lines, wip_all = [], 0
    for key, plate, title, stations, hint in LINES:
        mine = [r for r in racks if r[0] == key]
        wip = [(name, it) for _, name, _, items in mine for it in items if it["wip"]]
        wip_all += len(wip)
        cols = []
        for i, st in enumerate(stations):
            here = [(n, it) for n, it in wip if it["at"] == i]
            crates = "".join(crate(n, it) for n, it in here[:3]) + (f'<div class="more">還有 {len(here) - 3} 件</div>' if len(here) > 3 else "")
            cols.append(f'<div class="st{" busy" if here else ""}"><div class="mach"><span class="no">{i + 1:02d}</span>{E(st)}'
                        f'{f"<b>{len(here)}</b>" if here else ""}</div><div class="bay">{crates}</div></div>')
        names = "、".join(f'<a href="#rack-{Q(n)}">{E(n)}</a>' for _, n, _, _ in mine)
        feed = (f"在製 {len(wip)} 件" if wip else "閒置中") + (f"・系列：{names}" if names else "") + \
            ("" if wip else f"・開新的一集，跟 agent 說 <code>{E(hint)}</code>")
        lines.append(f'<div class="line l-{key}{" run" if wip else ""}"><div class="plate"><b>{plate}</b><span>{E(title)}</span></div>'
                     f'<div class="floor"><div class="scroll"><div class="belt">{"".join(cols)}'
                     f'<a class="gate" href="#store"><span>⤵</span>入庫</a><div class="track {"run" if wip else "idle"}">{"<i></i>" * 3 if wip else ""}</div>'
                     f'</div></div><div class="feed">{feed}</div></div></div>')
    lines.append('<div class="soon">' + "".join(
        f'<div class="line"><div class="plate"><b>{p}</b><span>{t}</span></div><div class="sub">規劃中・新產線只要寫自己的流程和 skill，'
        f'生成引擎和共用核心直接用</div></div>' for p, t in SOON) + "</div>")

    shelves, made, up, total = [], 0, 0, 0.0
    codes = {}
    for line, name, href, items in racks:
        codes[line] = codes.get(line, 0) + 1
        tiers = {}
        for it in sorted(items, key=lambda it: it["order"]):
            tiers.setdefault(it["tier"], []).append(it)
        boxes = []
        for tier, its in tiers.items():
            tiles = []
            for it in its:
                if it["wip"]:
                    st = dict((l[0], l[3]) for l in LINES).get(line, LINES[0][3])[it["at"]]
                    tiles.append(f'<a class="box" href="{it["href"]}" title="{E(it["long"])}・製作中"><span class="ph">製作中<b>{E(st)}</b></span>'
                                 f'<span class="cap">{E(it["short"])}</span></a>')
                    continue
                tag = ('<span class="tag ok" title="已上架">▶</span>' if it["uploaded"] else
                       '<span class="tag old">舊作</span>' if it["old"] else '<span class="tag">待上架</span>')
                pic = img(it["cover"], 160 if line in TALL else 340) if it["cover"] else '<span class="ph"></span>'
                tiles.append(f'<a class="box" href="{it["href"]}" title="{E(it["long"])}">{pic}{tag}<span class="cap">{E(it["short"])}</span></a>')
            boxes.append(f'<div class="tier"><span class="tier-label">{E(tier)}・{len(its)} 件</span><div class="shelf">{"".join(tiles)}</div></div>')
        done = [it for it in items if it["done"][3]]
        n_up, n_wip = sum(1 for it in items if it["uploaded"]), sum(1 for it in items if it["wip"])
        n_wait = sum(1 for it in done if not (it["uploaded"] or it["old"] or it["wip"]))
        dur = sum(it["dur"] or 0 for it in done)
        made, up, total = made + len(done), up + n_up, total + dur
        facts = [f"{len(items)} 件"] + [f"{label} {n}" for label, n in (("已上架", n_up), ("待上架", n_wait), ("在製", n_wip)) if n] + \
            ([f"片長 {hours(dur)}"] if dur else [])
        title = dict((l[0], f"{l[1]}・{l[2]}") for l in LINES).get(line, line)
        shelves.append(f'<section class="rack l-{line}{" tall" if line in TALL else ""}" id="rack-{E(Q(name))}"><div class="rack-head">'
                       f'<span class="code">{RACK.get(line, "Z")}-{codes[line]:02d}</span><h3><a href="{href}">{E(name)}</a></h3>'
                       f'<span class="sub">{E(title)}・{"・".join(facts)}</span><a class="go" href="{href}">進入系列 →</a></div>'
                       f'<div class="frame">{"".join(boxes) or "<div class=sub>還在建索引，稍後重新整理</div>"}</div></section>')

    def first_pic(path):
        for d in ("thumbnails", ""):
            p = os.path.join(path, d)
            pics = sorted(f for f in os.listdir(p) if f.lower().endswith((".jpg", ".png"))) if os.path.isdir(p) else []
            if pics:
                return os.path.join(p, pics[0])
    loose_cards = []
    for name, path in loose:
        pic, vids = first_pic(path), sum(1 for f in os.listdir(path) if f.endswith(".mp4"))
        loose_cards.append(f'<a href="{files_url(path)}/">{img(pic, 380) if pic else "<span class=noimg></span>"}<b>{E(name)}</b>'
                           f'<span>{f"{vids} 支影片" if vids else "檔案"}</span></a>')

    log = youtube_log.history(limit=15)
    ship = "".join(
        f'<tr><td class="t">{E(r["at"][:16].replace("T", " "))}</td><td class="a"><span>{E(r["label"])}</span></td>'
        f'<td class="w">{E(os.path.basename(r["project"] or ""))}{E("・" + r["kind"]) if r["kind"] and r["kind"] != "full" else ""}</td>'
        f'<td class="x" title="{E(r["text"])}">{E(r["text"].splitlines()[0] if r["text"] else "")}</td>'
        f'<td><a href="https://youtu.be/{E(r["video"])}" target="_blank">▶</a></td></tr>' for r in log)
    hero = (f'<section class="hero"><h1>Dreamfab 造夢廠</h1><p class="sub">AI Agent 影音製作框架：你跟 agent 說一句話，'
            f'產線把它做成影片，成品入庫，再上架到 YouTube。每個系列是一個平行時空。</p><div class="flow">'
            f'<div class="node"><b>一句話</b><span>你跟 agent 說</span></div><span class="arr" style="animation-delay:0.00s">→</span>'
            f'<div class="node"><b>AI Agent</b><span>Claude Code・Codex</span></div><span class="arr" style="animation-delay:0.35s">→</span>'
            f'<a class="node key" href="#lines"><b>產線</b><span>戲・曲・說・在製 {wip_all} 件</span></a><span class="arr" style="animation-delay:0.70s">⇄</span>'
            f'<div class="node"><b>生成引擎</b><span>AutoIP：圖・影片・聲音・作曲</span></div><span class="arr" style="animation-delay:1.05s">→</span>'
            f'<a class="node key" href="#store"><b>倉庫</b><span>成品 {made} 件・{hours(total)}</span></a><span class="arr" style="animation-delay:1.40s">→</span>'
            f'<a class="node" href="#ship"><b>YouTube</b><span>已上架 {up} 件</span></a></div></section>')
    body = (hero + f'<h2 id="lines">產線<span class="sub">每一集停在它還沒過的那一站；有成片、有封面就入庫</span></h2>{"".join(lines)}'
            f'<h2 id="store">倉庫<span class="sub">一個系列一座貨架、一季一層；▶ 已上架、待上架、虛線是還在產線上的</span></h2>'
            f'<div class="racks">{"".join(shelves)}</div>'
            f'<h2 id="stock">庫存與出貨<span class="sub">做好沒上傳、已上傳沒公開、已公開；每天出貨不要超過上限，以免被限流</span></h2>'
            f'{stock_panel(racks, paths)}'
            + (f'<h2 id="ship">出貨紀錄<span class="sub">最近在 YouTube 上做的事：上傳、公開、留言、片尾、資訊卡…'
               f'（dreamfab/youtube_log.py）</span></h2><div class="ship"><table>{ship}</table></div>' if ship else "")
            + (f'<h2 id="loose">散件區<span class="sub">還不是系列的資料夾，直接看檔案</span></h2><div class="loose">{"".join(loose_cards)}</div>'
               if loose_cards else ""))
    nav = '<nav><a href="#lines">產線</a><a href="#store">倉庫</a><a href="#stock">庫存與出貨</a>' + ('<a href="#ship">出貨紀錄</a>' if ship else "") + ('<a href="#loose">散件區</a>' if loose_cards else "") + "</nav>"
    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>Dreamfab 造夢廠</title><style>{CSS}</style></head>'
            f'<body><header><b>Dreamfab</b><span class="sub">造夢廠</span>{nav}</header><main>{body}</main></body></html>')

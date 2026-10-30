"""The explain line's pages in the Dreamfab library (dreamfab/library.py serves them under /files/<series>/).

A series page: one card per episode with its cover, title and where it stands (script, narration, pictures, cut,
YouTube), then the shared voices and music. An episode page: the cut with its chapters (click one to jump there), the
covers, every picture with its note, the narration parts, the script and the YouTube copy. Both are read from the
episode folders as they are (project.py, 文案, voice/, images/, out/, thumbnails/, YouTube_SEO.txt, youtube.json), so a
step shows up as soon as its files exist. "所有檔案" (?raw) is the plain folder listing. After the upload, what was
done on YouTube (end screen, card, pinned comment, links...) comes from the YouTube log (dreamfab/youtube_log.py).
"""
import html, json, os, re, runpy, subprocess, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo root
from dreamfab import youtube_log

E, Q = html.escape, urllib.parse.quote

CSS = """
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1b19;--sub:#6b6560;--line:#e2ddd6;--accent:#b3202f;--chip:#efe9e1;
--ok:#2f7d4f;--ok-bg:#e3f1e8;--doing:#9a6412;--doing-bg:#f8ecd6}
@media (prefers-color-scheme:dark){:root{--bg:#141312;--card:#1e1c1b;--ink:#ece8e3;--sub:#a59e97;--line:#34302d;
--accent:#e2505d;--chip:#2a2725;--ok:#7cc79a;--ok-bg:#1f3328;--doing:#e2b45e;--doing-bg:#3a2e1a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,"Microsoft JhengHei","PingFang TC",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;
display:flex;gap:14px;align-items:center;flex-wrap:wrap}header b{color:var(--accent)}header a{color:var(--ink);text-decoration:none}
header .right{margin-left:auto;display:flex;gap:14px}
main{max-width:1180px;margin:0 auto;padding:18px 16px 60px}a{color:var(--accent)}
h1{font-size:24px;line-height:1.35;margin:4px 0 6px}h2{font-size:18px;margin:34px 0 12px}.sub{color:var(--sub);font-size:14px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0 0}.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 16px}
.stat b{display:block;font-size:22px}
.eps{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.ep{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;color:var(--ink);text-decoration:none}
a.ep:hover{border-color:var(--accent)}.ep img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:var(--chip)}
.ep .noimg{aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;background:var(--chip);color:var(--sub);font-size:40px}
.ep .b{padding:12px 14px 14px}.ep .n{font-size:13px;color:var(--accent);font-weight:600}.ep h3{font-size:16px;line-height:1.4;margin:2px 0 6px}
.steps{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
.st{font-size:12.5px;border-radius:20px;padding:1px 9px;background:var(--chip);color:var(--sub)}
.st.ok{background:var(--ok-bg);color:var(--ok)}.st.doing{background:var(--doing-bg);color:var(--doing)}
.chip{display:inline-block;background:var(--chip);border-radius:20px;padding:2px 10px;margin:2px 4px 2px 0;font-size:13px;color:var(--ink);text-decoration:none}
.top{display:grid;grid-template-columns:minmax(0,2fr) minmax(240px,1fr);gap:16px;margin-top:14px}
@media (max-width:820px){.top{grid-template-columns:1fr}}
video{width:100%;border-radius:10px;background:#000;display:block}
.chaps{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px}
.chaps button{display:flex;gap:10px;width:100%;text-align:left;background:none;border:0;border-radius:8px;padding:6px 8px;color:var(--ink);font:inherit;cursor:pointer}
.chaps button:hover{background:var(--chip)}.chaps .t{color:var(--accent);font-variant-numeric:tabular-nums;min-width:38px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}.grid.covers{grid-template-columns:repeat(auto-fill,minmax(280px,1fr))}
.pic{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;color:var(--ink);text-decoration:none}a.pic:hover{border-color:var(--accent)}.pic img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.pic .b{padding:6px 10px;font-size:13px}.pic .b b{color:var(--accent);margin-right:4px}
.missing{aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;background:var(--chip);color:var(--sub);font-size:13px}
.list{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}.item{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px}
audio{width:100%;margin-top:6px}details{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;margin:10px 0}
summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;font:inherit;font-size:14px;margin:10px 0 0}
.md h2{font-size:17px;margin:22px 0 8px}.md h3,.md h4{font-size:15px;margin:18px 0 6px;color:var(--accent)}.md p{margin:6px 0}
.md blockquote{margin:8px 0;padding:4px 12px;border-left:3px solid var(--line);color:var(--sub)}
.log{border-collapse:collapse;width:100%;font-size:14px}.log td{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top}
.log td.t{color:var(--sub);white-space:nowrap;font-variant-numeric:tabular-nums}.log b{white-space:nowrap}
.md table{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}.md td,.md th{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
"""


def is_episode(path):
    p = os.path.join(path, "project.py")
    return os.path.isfile(p) and re.search(r"^LINE\s*=\s*[\"']explain", open(p, encoding="utf-8", errors="replace").read(), re.M)


def is_series(path):
    return os.path.isdir(path) and any(is_episode(os.path.join(path, d)) for d in os.listdir(path)
                                       if os.path.isdir(os.path.join(path, d)))


def doc(title, header, body):
    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{E(title)}</title><style>{CSS}</style></head>'
            f'<body><header>{header}</header><main>{body}</main></body></html>')


def read(path):
    return open(path, encoding="utf-8", errors="replace").read() if os.path.isfile(path) else ""


_LENGTH = {}


def length(path):
    """The cut's length in seconds (ffprobe, remembered until the file changes)."""
    key = (path, os.path.getmtime(path))
    if key not in _LENGTH:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        _LENGTH[key] = float(r.stdout.strip() or 0) or None
    return _LENGTH[key]


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def episode(path):
    """Everything the pages show about one episode folder."""
    try:
        proj = runpy.run_path(os.path.join(path, "project.py"))
    except Exception:   # a half-written project.py still gets a card
        proj = {}
    head = read(os.path.join(path, "project.py")).split("\n", 1)[0]
    seo = read(os.path.join(path, "YouTube_SEO.txt"))
    folder = os.path.basename(path)
    m = re.match(r"#\s*解說\s*#(\d+)：(.+?)（", head)
    num = int(m[1]) if m else int((re.match(r"e(\d+)", folder) or [0, 0])[1])
    question = m[2] if m else ""
    title = (re.search(r"^A\.\s*(.+)$", seo, re.M) or [None, ""])[1]
    mv = re.search(r"MV《(.+?)》[^\n]*?(https://youtu\.be/[\w-]+)", seo) or re.search(r"MV《(.+?)》\s*(https://\S+?)(?=\s|）|$)", head)
    mv_name = mv[1] if mv else (re.search(r"s\d+e\d+_([^/]+)/", proj.get("MV_CLIP", "")) or [None, ""])[1]
    chapters = []
    sec = seo.split("⏱ 章節", 1)[1] if "⏱ 章節" in seo else ""
    for line in sec.strip().splitlines():
        cm = re.match(r"(\d+):(\d\d)\s+(.+)", line.strip())
        if not cm:
            break
        chapters.append((int(cm[1]) * 60 + int(cm[2]), cm[3]))
    name = proj.get("NAME", folder)
    cut = os.path.join(path, "out", name + ".mp4")
    srt = os.path.isfile(os.path.join(path, "out", name + ".zh-TW.srt"))
    images = proj.get("IMAGES", [])
    have = lambda i: next((f"images/{i}{x}" for x in (".png", ".jpg") if os.path.exists(os.path.join(path, "images", i + x))), None)
    jobs = os.path.join(path, "jobs", "voice_jobs.json")
    parts = [j["id"] for j in json.loads(read(jobs))] if os.path.isfile(jobs) else []
    voice = sorted(f for f in os.listdir(os.path.join(path, "voice")) if f.endswith((".flac", ".mp3", ".wav"))) \
        if os.path.isdir(os.path.join(path, "voice")) else []
    thumbs = sorted(f for f in os.listdir(os.path.join(path, "thumbnails")) if f.endswith((".jpg", ".png"))) \
        if os.path.isdir(os.path.join(path, "thumbnails")) else []
    yt = (json.loads(read(os.path.join(path, "youtube.json")) or "{}").get("full") or {})
    return dict(folder=folder, num=num, question=question, title=title or question or (proj.get("TITLE") or [folder])[0],
                lines=proj.get("TITLE") or (), mv=mv_name, mv_url=mv[2] if mv else "", music=os.path.basename(proj.get("MUSIC", "")),
                chapters=chapters, cut=f"out/{name}.mp4" if os.path.isfile(cut) else None,
                length=length(cut) if os.path.isfile(cut) else None,
                srt=f"out/{name}.zh-TW.srt" if srt else None, script=proj.get("SCRIPT") if os.path.isfile(os.path.join(path, proj.get("SCRIPT") or "-")) else None,
                images=[(i, ch, note, have(i)) for i, ch, note, *_ in images], parts=parts,
                voice=[v for v in voice if os.path.splitext(v)[0] + "_cut" not in {os.path.splitext(x)[0] for x in voice}],
                thumbs=thumbs, seo=seo, yt=yt, log=youtube_log.history([yt.get("id")]) if yt.get("id") else [])


def steps(ep):
    """The pipeline as small chips: done, under way, not yet."""
    def chip(label, state):
        return f'<span class="st {state}">{E(label)}</span>'
    n_img, done_img = len(ep["images"]), sum(1 for x in ep["images"] if x[3])
    n_voice = len(ep["parts"])
    done = {r["action"] for r in ep["log"]}
    done_voice = sum(1 for p in ep["parts"] if any(v.startswith(p) for v in ep["voice"]))
    return "".join([
        chip("文案 ✓" if ep["script"] else "文案", "ok" if ep["script"] else ""),
        chip(f"旁白 {done_voice}/{n_voice}" if n_voice else "旁白", "ok" if n_voice and done_voice == n_voice else "doing" if done_voice else ""),
        chip(f"畫面 {done_img}/{n_img}" if n_img else "畫面", "ok" if n_img and done_img == n_img else "doing" if done_img else ""),
        chip(f"剪輯 {mmss(ep['length'])}" if ep["cut"] and ep["length"] else "剪輯 ✓" if ep["cut"] else "剪輯", "ok" if ep["cut"] else ""),
        chip("封面 ✓" if ep["thumbs"] else "封面", "ok" if ep["thumbs"] else ""),
        chip("已上傳 ✓" if ep["yt"].get("id") else "上架", "ok" if ep["yt"].get("id") else ""),
    ] + ([chip(label + (" ✓" if a in done else ""), "ok" if a in done else "")   # after the upload: from the YouTube log
          for a, label in (("publish", "公開"), ("end_screen", "片尾"), ("card", "資訊卡"), ("pin", "置頂"))]
         if ep["yt"].get("id") else []))


def series_page(path, url):
    """url: this folder's /files/... address, ending in /."""
    name = os.path.basename(path)
    eps = sorted((episode(os.path.join(path, d)) for d in os.listdir(path) if is_episode(os.path.join(path, d))),
                 key=lambda e: e["num"])
    cards = []
    for ep in eps:
        u = url + Q(ep["folder"]) + "/"
        thumb = next((t for t in ep["thumbs"] if t.startswith("thumb_A")), ep["thumbs"][0] if ep["thumbs"] else None)
        pic = (f'<img loading="lazy" src="{u}thumbnails/{Q(thumb)}" alt="">' if thumb else
               next((f'<img loading="lazy" src="{u}{Q(x[3])}" alt="">' for x in ep["images"] if x[3]), '<div class="noimg">🎬</div>'))
        mv = f'MV《{E(ep["mv"])}》' if ep["mv"] else ""
        cards.append(f'<a class="ep" href="{u}">{pic}<div class="b"><div class="n">第 {ep["num"]} 集 · {mv}</div>'
                     f'<h3>{E(ep["title"])}</h3><div class="sub">{E(ep["question"])}</div>'
                     f'<div class="steps">{steps(ep)}</div></div></a>')
    done = sum(1 for e in eps if e["cut"])
    up = sum(1 for e in eps if e["yt"].get("id"))
    stats = (f'<div class="stats"><div class="stat"><b>{len(eps)}</b><span class="sub">集</span></div>'
             f'<div class="stat"><b>{done}</b><span class="sub">已剪好</span></div>'
             f'<div class="stat"><b>{up}</b><span class="sub">已上傳</span></div>'
             f'<div class="stat"><b>{len(eps) - done}</b><span class="sub">製作中</span></div></div>')
    # shared material: the narrator's voice and each MV's instrumental, named after the MV that uses it
    music_mv = {e["music"]: (e["num"], f'第 {e["num"]} 集 MV《{e["mv"]}》') for e in eps if e["music"]}
    voices = {}
    for e in eps:   # which voice file each episode reads with (VOICE in project.py)
        try:
            v = os.path.basename(runpy.run_path(os.path.join(path, e["folder"], "project.py")).get("VOICE", ""))
        except Exception:
            v = ""
        if v:
            voices.setdefault(v, []).append(e["num"])
    shared = []
    for sub, label in (("voices", "旁白員的聲音（每一集都用它唸）"), ("music", "配樂：每支 MV 的伴奏（原曲去人聲）")):
        d = os.path.join(path, sub)
        files = [f for f in os.listdir(d) if f.endswith((".wav", ".flac", ".mp3"))] if os.path.isdir(d) else []
        files.sort(key=lambda f: (music_mv.get(f, (99,))[0], f))
        if files:
            def label_of(f):
                if f in music_mv:
                    return music_mv[f][1]
                if f in voices:
                    return f'旁白員（第 {"、".join(map(str, voices[f]))} 集）'
                return f
            shared.append(f'<h3 class="sub">{E(label)}</h3><div class="list">' + "".join(
                f'<div class="item"><b>{E(label_of(f))}</b> <span class="sub">{E(f)}</span>'
                f'<audio controls preload="none" src="{url}{sub}/{Q(f)}"></audio></div>' for f in files) + "</div>")
    body = (f'<h1>{E(name)}</h1><div class="sub">每一集解說一支國風 MV 背後的歷史與傳說：台灣腔旁白、金箔工筆畫面、'
            f'結尾放 MV 片段。點一集看影片、章節、畫面和文案。</div>{stats}'
            f'<h2>每一集</h2><div class="eps">{"".join(cards)}</div>'
            + (f'<h2>共用素材</h2>{"".join(shared)}' if shared else ""))
    header = (f'<a href="/">⇦ Dreamfab</a><b>{E(name)}</b><span class="sub">解說</span>'
              f'<span class="right"><a href="{url}?raw">所有檔案</a></span>')
    return doc(name, header, body)


def linkify(s):
    return re.sub(r"(https?://[^\s<）]+)", r'<a href="\1" target="_blank">\1</a>', E(s)).replace("\n", "<br>")


def markdown(text):
    """Just enough Markdown for a script: headings, quotes, lists, tables, bold, links."""
    def inline(s):
        s = E(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        return re.sub(r"(https?://[^\s<）]+)", r'<a href="\1" target="_blank">\1</a>', s)
    out, table, lst = [], [], []

    def flush():
        if table:
            rows = [r for r in table if not re.match(r"^\|[\s\-|:]+\|$", r)]
            out.append("<table>" + "".join("<tr>" + "".join(f"<td>{inline(c.strip())}</td>" for c in r.strip("|").split("|"))
                                           + "</tr>" for r in rows) + "</table>")
            table.clear()
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in lst) + "</ul>")
            lst.clear()
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|"):
            table.append(s); continue
        if s.startswith("- "):
            lst.append(s[2:]); continue
        flush()
        if not s:
            continue
        h = re.match(r"(#+)\s+(.*)", s)
        if h:
            lvl = min(len(h[1]) + 1, 4)
            out.append(f"<h{lvl}>{inline(h[2])}</h{lvl}>")
        elif s.startswith(">"):
            out.append(f"<blockquote>{inline(s.lstrip('> '))}</blockquote>")
        else:
            out.append(f"<p>{inline(s)}</p>")
    flush()
    return '<div class="md">' + "".join(out) + "</div>"


def episode_page(path, url):
    ep = episode(path)
    series_url = url.rstrip("/").rsplit("/", 1)[0] + "/"
    series = os.path.basename(os.path.dirname(path))
    links = []
    if ep["yt"].get("id"):
        links.append(f'<a class="chip" href="https://youtu.be/{E(ep["yt"]["id"])}" target="_blank">▶ YouTube（{E(ep["yt"].get("at", "")[:10])} 上傳）</a>')
    if ep["mv_url"]:
        links.append(f'<a class="chip" href="{E(ep["mv_url"])}" target="_blank">♪ MV《{E(ep["mv"])}》</a>')
    if ep["srt"]:
        links.append(f'<a class="chip" href="{url}{Q(ep["srt"])}">字幕 .srt</a>')
    thumb = next((t for t in ep["thumbs"] if t.startswith("thumb_A")), None)
    poster = f' poster="{url}thumbnails/{Q(thumb)}"' if thumb else ""
    if ep["cut"]:
        chaps = "".join(f'<button onclick="go({t})"><span class="t">{mmss(t)}</span><span>{E(n)}</span></button>'
                        for t, n in ep["chapters"]) or '<div class="sub" style="padding:6px 8px">章節在說明欄寫好後會出現在這裡</div>'
        top = (f'<div class="top"><video id="cut" controls preload="metadata" src="{url}{Q(ep["cut"])}"{poster}></video>'
               f'<div class="chaps"><div class="sub" style="padding:2px 8px 6px">章節（點一下跳過去）</div>{chaps}</div></div>'
               '<script>function go(t){const v=document.getElementById("cut");v.currentTime=t;v.play()}</script>')
    else:
        top = '<div class="item sub" style="margin-top:14px">還沒剪好：旁白和畫面都齊了之後跑 render.py，影片會出現在這裡。</div>'
    body = [f'<div class="n sub">第 {ep["num"]} 集 · {E("／".join(ep["lines"]))}</div><h1>{E(ep["title"])}</h1>'
            f'<div class="sub">{E(ep["question"])}</div><div class="steps">{steps(ep)}</div>'
            f'<div style="margin-top:10px">{"".join(links)}</div>{top}']
    if ep["thumbs"]:
        body.append('<h2>封面</h2><div class="grid covers">' + "".join(
            f'<a class="pic" href="{url}thumbnails/{Q(t)}" target="_blank"><img loading="lazy" src="{url}thumbnails/{Q(t)}" alt="">'
            f'<div class="b"><b>{E(t[6:7])}</b>{E(t[8:].rsplit(".", 1)[0])}{"（上傳用這張）" if t.startswith("thumb_A") else ""}</div></a>'
            for t in ep["thumbs"]) + "</div>")
    if ep["images"]:
        done = sum(1 for x in ep["images"] if x[3])
        body.append(f'<h2>畫面 <span class="sub">{done}/{len(ep["images"])} 張</span></h2><div class="grid">' + "".join(
            (f'<a class="pic" href="{url}{Q(f)}" target="_blank"><img loading="lazy" src="{url}{Q(f)}" alt="">' if f else
             '<div class="pic"><div class="missing">還在生成</div>')
            + f'<div class="b"><b>{E(i)}</b>{E(note)}<div class="sub">{E(ch)}</div></div>' + ("</a>" if f else "</div>")
            for i, ch, note, f in ep["images"]) + "</div>")
    if ep["voice"] or ep["parts"]:
        body.append('<h2>旁白</h2><div class="list">' + "".join(
            f'<div class="item"><b>{E(v)}</b><audio controls preload="none" src="{url}voice/{Q(v)}"></audio></div>'
            for v in ep["voice"]) + ("" if ep["voice"] else '<div class="item sub">還在生成</div>') + "</div>")
    if ep["script"]:
        body.append(f'<h2>文案</h2><details><summary>{E(ep["script"])}（點開看全文：標題候選、旁白、畫面表、考據）</summary>'
                    f'{markdown(read(os.path.join(path, ep["script"])))}</details>')
    if ep["log"]:
        body.append('<h2>上架紀錄 <span class="sub">YouTube 上做過的事，新的在上面（dreamfab/youtube_log.py）</span></h2>'
                    '<div class="item"><table class="log">' + "".join(
                        f'<tr><td class="t">{E(r["at"][:16].replace("T", " "))}</td><td><b>{E(r["label"])}</b></td>'
                        f'<td>{linkify(r["text"])}</td></tr>' for r in ep["log"]) + "</table></div>")
    if ep["seo"]:
        body.append(f'<h2>YouTube 標題與說明欄</h2><details><summary>YouTube_SEO.txt</summary><pre>{E(ep["seo"])}</pre></details>')
    header = (f'<a href="{series_url}">⇦ {E(series)}</a><b>第 {ep["num"]} 集</b><span class="sub">{E(ep["folder"])}</span>'
              f'<span class="right"><a href="{url}?raw">所有檔案</a></span>')
    return doc(f'#{ep["num"]} {ep["title"]}', header, "".join(body))

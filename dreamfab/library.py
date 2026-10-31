"""One library page for everything Dreamfab made: every series (a parallel universe) of every line, side by side.

usage: python dreamfab/library.py serve ROOT [ROOT ...] [--port 8765]
       python dreamfab/library.py list ROOT [ROOT ...]          which series it finds, and their line
ROOT is a series folder or a folder of series (e.g. projects/). A series is a folder whose sub-folders have a
project.py (an MV project folder on its own counts too); its line is mv when a project.py there has AUDIO (the song),
else drama. Each series is served by its own line's library (drama/library.py, mv/library.py: they index into the
shared Dreamfab database, dreamfab/db.py, and re-index by themselves) on a port of its own, and this page puts them
under one address:
http://127.0.0.1:8765/ is the factory floor (dreamfab/home.py: each line's stations with what is being made there, and a
rack per series in the warehouse), /u/<series>/ is that series' library. Folders that are not a series yet (an
explainer's script and narration, say) are listed too and served as plain files: /files/<path under ROOT>; a folder
there is a page with players for its audio, video and images. An explainer series (project.py says LINE = "explain")
gets the explain line's own pages there instead (explain/pages.py: episode cards, then each episode's cut, chapters,
pictures and script); ?raw shows its plain listing, and ?w=<px> on an image sends it scaled down. Listens on 127.0.0.1
only.
"""
import html, http.client, io, mimetypes, os, re, subprocess, sys, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "explain"))
import pages as explain_pages
import home


def line_of(series):
    """explain when a project.py says LINE = "explain" (no library of its own yet: served as plain files), mv when
    one has AUDIO, else drama."""
    for d in [series] + [os.path.join(series, x) for x in sorted(os.listdir(series))]:
        p = os.path.join(d, "project.py")
        src = open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""
        if re.search(r"^LINE\s*=\s*[\"']explain", src, re.M):
            return "explain"
        if re.search(r"^AUDIO\s*=", src, re.M):
            return "mv"
    return "drama"


def find_series(roots):
    """[(name, path, line)] for every series under the roots, in folder order; names are made unique."""
    out, seen = [], set()
    for root in roots:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            sys.exit(f"no folder {root}")
        kids = [os.path.join(root, d) for d in sorted(os.listdir(root)) if os.path.isdir(os.path.join(root, d))]
        is_series = os.path.isfile(os.path.join(root, "project.py")) or any(
            os.path.isfile(os.path.join(k, "project.py")) for k in kids)
        for s in [root] if is_series else [k for k in kids if not os.path.basename(k).startswith(("_", "."))
                                           and any(os.path.isfile(os.path.join(k, d, "project.py")) for d in os.listdir(k))]:
            name = os.path.basename(s)
            while name in seen:
                name += "_"
            seen.add(name)
            out.append((name, s, line_of(s)))
    return out


def other_folders(roots, series):
    """[(name, path)] for the folders under the roots that are not a series (served as plain files)."""
    taken = {os.path.normcase(p) for _, p, _ in series}
    out = []
    for root in roots:
        root = os.path.abspath(root)
        for d in sorted(os.listdir(root)):
            p = os.path.join(root, d)
            if os.path.isdir(p) and not d.startswith(("_", ".")) and os.path.normcase(p) not in taken \
                    and not any(s.startswith(os.path.normcase(p) + os.sep) for s in taken):
                out.append((d, p))
    return out


def sniff(path):
    """Content type from the bytes first (a narration saved as .mp3 may really be FLAC), then the extension."""
    with open(path, "rb") as f:
        head = f.read(12)
    for magic, t in ((b"fLaC", "audio/flac"), (b"ID3", "audio/mpeg"), (b"OggS", "audio/ogg")):
        if head.startswith(magic):
            return t
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    t = mimetypes.guess_type(path)[0] or ("text/plain" if path.endswith((".md", ".srt")) else "application/octet-stream")
    return t + "; charset=utf-8" if t.startswith("text/") or t.endswith("json") else t


_SMALL = {}


def small(path, width):
    """The image scaled down to width as a JPEG (kept in memory until the file changes), for the front page's covers;
    None without Pillow, and the whole file goes out instead."""
    key = (path, os.path.getmtime(path), width)
    if key not in _SMALL:
        try:
            from PIL import Image
        except ImportError:
            return None
        with Image.open(path) as im:
            im.draft("RGB", (width, width * 4))   # JPEGs decode straight to a smaller size
            im.thumbnail((width, width * 4))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=84)
        _SMALL[key] = buf.getvalue()
    return _SMALL[key]


def start(series, port):
    """Run the series' own line library on a free port; returns (process, port)."""
    name, path, line = series
    p = subprocess.Popen([sys.executable, "-u", os.path.join(REPO, line, "library.py"), "serve", path, "--port", str(port)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                         env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    for l in p.stdout:   # wait for "library: http://127.0.0.1:<port>" (it indexes first)
        m = re.search(r"library: http://127\.0\.0\.1:(\d+)", l)
        if m:
            threading.Thread(target=lambda: [print(f"  [{name}] {x}", end="", flush=True) for x in p.stdout], daemon=True).start()
            return p, int(m[1])
        if "Traceback" in l or "Error" in l:
            print(f"  [{name}] {l}", end="")
    sys.exit(f"{name}: its library did not start")


CSS = """
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1b19;--sub:#6b6560;--line:#e2ddd6;--accent:#b3202f}
@media (prefers-color-scheme:dark){:root{--bg:#141312;--card:#1e1c1b;--ink:#ece8e3;--sub:#a59e97;--line:#34302d;--accent:#e2505d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,"Microsoft JhengHei","PingFang TC",sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px}h1{font-size:24px;margin:0 0 4px}.sub{color:var(--sub);font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;margin-top:18px}
a.card{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;color:var(--ink);text-decoration:none}
a.card:hover{border-color:var(--accent)}h2{font-size:17px;margin:28px 0 0}
ul.files{list-style:none;padding:0;margin:18px 0 0}ul.files li{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-bottom:10px}
ul.files a{color:var(--ink)}ul.files audio,ul.files video{display:block;width:100%;margin-top:8px}ul.files img{display:block;max-width:100%;max-height:420px;margin-top:8px;border-radius:6px}
pre{white-space:pre-wrap;font:inherit;margin:8px 0 0}.tag{display:inline-block;font-size:12px;color:var(--accent);border:1px solid var(--accent);border-radius:20px;padding:0 8px;margin-bottom:6px}
"""


def serve(roots, port):
    found = find_series(roots)
    series = [s for s in found if s[2] != "explain"]
    explain = {os.path.normcase(p) for _, p, l in found if l == "explain"}
    if not series:
        sys.exit("no series found (a series is a folder whose sub-folders have a project.py)")
    others = other_folders(roots, series)
    roots = [os.path.abspath(r) for r in roots]
    procs, ports = [], {}
    for i, s in enumerate(series):
        p, sp = start(s, port + 10 + i * 3)
        procs.append(p); ports[s[0]] = sp
        print(f"  {s[0]} ({s[2]}) -> /u/{urllib.parse.quote(s[0])}/")
    E = html.escape

    def files_url(path):
        """The /files/ address of a file or folder under one of the roots."""
        for root in roots:
            rel = os.path.relpath(path, root)
            if not rel.startswith(".."):
                return "/files" + "".join("/" + urllib.parse.quote(x) for x in rel.split(os.sep) if x != ".")

    def front():
        return home.page(series, [(n, p) for n, p in others if os.path.normcase(p) in explain],
                         [(n, p) for n, p in others if os.path.normcase(p) not in explain], files_url)

    def page(title, body):
        return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" '
                f'content="width=device-width,initial-scale=1"><title>{E(title)}</title><style>{CSS}</style></head><body><main>'
                f'{body}</main></body></html>')

    def local(rel):
        """The file or folder under one of the roots that /files/<rel> names, or None."""
        parts = [x for x in rel.replace("\\", "/").split("/") if x]
        if any(x in (".", "..") or ":" in x for x in parts):
            return None
        for root in roots:
            p = os.path.join(root, *parts)
            if os.path.exists(p):
                return p
        return None

    def folder(rel, path):
        """A folder as a page: sub-folders as links, media with players, Markdown inline."""
        parts = [x for x in rel.split("/") if x]
        url = "/files/" + "/".join(urllib.parse.quote(x) for x in parts)
        items = []
        for d in sorted(os.listdir(path), key=lambda d: (not os.path.isdir(os.path.join(path, d)), d)):
            p, u = os.path.join(path, d), f"{url}/{urllib.parse.quote(d)}"
            if d.startswith(".") or d.endswith(".state"):
                continue
            if os.path.isdir(p):
                items.append(f'<li id="{E(d)}"><a href="{u}/">📁 {E(d)}/</a></li>')
                continue
            t, size = sniff(p), os.path.getsize(p)
            tag = (f'<audio controls preload="metadata" src="{u}"></audio>' if t.startswith("audio/") else
                   f'<video controls preload="metadata" src="{u}"></video>' if t.startswith("video/") else
                   f'<img loading="lazy" src="{u}" alt="">' if t.startswith("image/") else
                   f'<pre>{E(open(p, encoding="utf-8", errors="replace").read())}</pre>' if d.endswith(".md") and size < 200_000 else "")
            items.append(f'<li id="{E(d)}"><a href="{u}">{E(d)}</a> <span class="sub">{size / 1e6:.1f} MB</span>{tag}</li>')
        nav = '<a href="/">⇦ Dreamfab</a>' + (f' · <a href="{url.rsplit("/", 1)[0]}/">⇧ 上一層</a>' if len(parts) > 1 else "")
        return page(parts[-1], f'<div class="sub">{nav}</div><h1>{E("/".join(parts))}</h1><ul class="files">{"".join(items)}</ul>')

    def send_file(h, path):
        """One file, with Range so audio and video can seek."""
        size, t = os.path.getsize(path), sniff(path)
        m = re.match(r"bytes=(\d*)-(\d*)", h.headers.get("Range", ""))
        a, b = 0, size - 1
        if m and (m[1] or m[2]):
            a, b = (int(m[1]), int(m[2]) if m[2] else size - 1) if m[1] else (max(0, size - int(m[2])), size - 1)
            b = min(b, size - 1)
            h.send_response(206); h.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        else:
            h.send_response(200)
        h.send_header("Content-Type", t); h.send_header("Accept-Ranges", "bytes")
        h.send_header("Content-Length", str(b - a + 1)); h.end_headers()
        with open(path, "rb") as f:
            f.seek(a)
            left = b - a + 1
            while left > 0 and (chunk := f.read(min(1 << 16, left))):
                h.wfile.write(chunk); left -= len(chunk)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            m = re.match(r"^/u/([^/]+)(/.*)?$", self.path)
            try:
                if self.path in ("/", "/index.html"):
                    b = front().encode("utf-8")
                    self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(b))); self.end_headers(); return self.wfile.write(b)
                if self.path.startswith("/files/"):
                    path, _, query = self.path.split("#")[0].partition("?")
                    rel = urllib.parse.unquote(path[len("/files/"):])
                    p = local(rel)
                    if not p:
                        self.send_response(404); self.end_headers(); return
                    if os.path.isfile(p):
                        w = urllib.parse.parse_qs(query).get("w", [""])[0]
                        b = small(p, min(max(int(w), 64), 1280)) if w.isdigit() and sniff(p).startswith("image/") else None
                        if not b:
                            return send_file(self, p)
                        self.send_response(200); self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Content-Length", str(len(b))); self.end_headers(); return self.wfile.write(b)
                    if not path.endswith("/"):
                        self.send_response(301); self.send_header("Location", path + "/"); self.end_headers(); return
                    raw = "raw" in urllib.parse.parse_qs(query, keep_blank_values=True)
                    b = (explain_pages.series_page(p, path) if not raw and explain_pages.is_series(p) else
                         explain_pages.episode_page(p, path) if not raw and explain_pages.is_episode(p) else
                         folder(rel, p)).encode("utf-8")
                    self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(b))); self.end_headers(); return self.wfile.write(b)
                name = urllib.parse.unquote(m[1]) if m else None
                if name not in ports:
                    self.send_response(404); self.end_headers(); return
                self.proxy(name, m[2] or "/")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass   # the browser dropped a video request it no longer needs

        def proxy(self, name, path):
            """Forward to the series' own library; its pages link from / so their links get the /u/<name> prefix."""
            c = http.client.HTTPConnection("127.0.0.1", ports[name], timeout=120)
            c.request("GET", path, headers={k: v for k, v in self.headers.items() if k.lower() in ("range", "accept")})
            r = c.getresponse()
            ctype = r.getheader("Content-Type", "")
            if ctype.startswith("text/html"):
                pre = "/u/" + urllib.parse.quote(name)
                b = re.sub(r'((?:href|src|action|poster)=")/', rf"\1{pre}/", r.read().decode("utf-8"))
                b = b.replace("</header>", f'<a href="/">⇦ Dreamfab</a></header>', 1).encode("utf-8")
                self.send_response(r.status); self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            else:
                self.send_response(r.status)
                for k in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                    if r.getheader(k):
                        self.send_header(k, r.getheader(k))
                self.end_headers()
                while chunk := r.read(1 << 16):
                    self.wfile.write(chunk)
            c.close()

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    for n, _ in others:
        print(f"  {n} (files) -> /files/{urllib.parse.quote(n)}/")
    print(f"library: http://127.0.0.1:{port}  ({len(series)} series; Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("serve", "list"):
        sys.exit(__doc__)
    args = sys.argv[2:]
    port = int(args[args.index("--port") + 1]) if "--port" in args else 8765
    roots = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--port")]
    if sys.argv[1] == "list":
        for n, p, l in find_series(roots):
            print(f"{l:6} {n}  {p}")
    else:
        serve(roots, port)

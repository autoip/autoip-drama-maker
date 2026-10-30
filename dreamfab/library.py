"""One library page for everything Dreamfab made: every series (a parallel universe) of every line, side by side.

usage: python dreamfab/library.py serve ROOT [ROOT ...] [--port 8765]
       python dreamfab/library.py list ROOT [ROOT ...]          which series it finds, and their line
ROOT is a series folder or a folder of series (e.g. projects/). A series is a folder whose sub-folders have a
project.py (an MV project folder on its own counts too); its line is mv when a project.py there has AUDIO (the song),
else drama. Each series is served by its own line's library (drama/library.py, mv/library.py: they keep their own
library.db and re-index by themselves) on a port of its own, and this page puts them under one address:
http://127.0.0.1:8765/ lists the series, /u/<series>/ is that series' library. Listens on 127.0.0.1 only.
"""
import html, http.client, os, re, subprocess, sys, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LINES = {"drama": "戲・短劇", "mv": "曲・MV"}


def line_of(series):
    """mv when a project.py in the series (or the series itself) has AUDIO, else drama."""
    for d in [series] + [os.path.join(series, x) for x in sorted(os.listdir(series))]:
        p = os.path.join(d, "project.py")
        if os.path.isfile(p) and re.search(r"^AUDIO\s*=", open(p, encoding="utf-8", errors="replace").read(), re.M):
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
a.card:hover{border-color:var(--accent)}.tag{display:inline-block;font-size:12px;color:var(--accent);border:1px solid var(--accent);border-radius:20px;padding:0 8px;margin-bottom:6px}
"""


def serve(roots, port):
    series = find_series(roots)
    if not series:
        sys.exit("no series found (a series is a folder whose sub-folders have a project.py)")
    procs, ports = [], {}
    for i, s in enumerate(series):
        p, sp = start(s, port + 10 + i * 3)
        procs.append(p); ports[s[0]] = sp
        print(f"  {s[0]} ({s[2]}) -> /u/{urllib.parse.quote(s[0])}/")
    E = html.escape

    def home():
        cards = "".join(f'<a class="card" href="/u/{urllib.parse.quote(n)}/"><span class="tag">{E(LINES.get(l, l))}</span>'
                        f'<div><b>{E(n)}</b></div><div class="sub">{E(os.path.relpath(p, REPO) if p.startswith(REPO) else p)}</div></a>'
                        for n, p, l in series)
        return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" '
                f'content="width=device-width,initial-scale=1"><title>Dreamfab 造夢廠</title><style>{CSS}</style></head><body><main>'
                f'<h1>Dreamfab 造夢廠</h1><div class="sub">AI 自動化媒體工作站・每個系列是一個平行時空</div>'
                f'<div class="grid">{cards}</div></main></body></html>')

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            m = re.match(r"^/u/([^/]+)(/.*)?$", self.path)
            try:
                if self.path in ("/", "/index.html"):
                    b = home().encode("utf-8")
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

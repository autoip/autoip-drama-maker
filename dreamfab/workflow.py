"""Workflow switches: which steps Dreamfab takes on its own. Everyone works differently, so each automatic step is a
switch in a small settings file rather than a fixed habit of the code.

Where the switches come from (a later one wins):
  1. the defaults below: what Dreamfab does with no settings file at all
  2. ~/.config/dreamfab/workflow.ini   your choices for everything ($DREAMFAB_WORKFLOW names another file)
  3. <series>/workflow.ini             one series' choices, only what it does differently (read for the episode folder
                                       a script works on: the folder above it, then the folder itself)
project.py and the command line still win over all of them (RENDER["enhance"], SHORTS["layout"], --off-peak, --privacy).

usage: python dreamfab/workflow.py show [DIR]            every switch, its value and the file that set it; DIR (an
                                                         episode or series folder) brings in that series' file
       python dreamfab/workflow.py init [DIR]            start a commented file: yours, or DIR/workflow.ini
       python dreamfab/workflow.py set KEY VALUE [DIR]   change one switch in your file (or DIR's), e.g.
                                                         python dreamfab/workflow.py set explain.shorts off
In code: from dreamfab.workflow import get; get("explain.shorts", episode_dir)
"""
import configparser, os, sys

USER = os.environ.get("DREAMFAB_WORKFLOW") or os.path.join(os.path.expanduser("~"), ".config", "dreamfab", "workflow.ini")
NAME = "workflow.ini"

# (key, default, choices or None, what it does: 中文 / English). The defaults are what the code did before the switch.
SWITCHES = [
    ("credits.off_peak", False, None,
     "只在離峰半價時段（03:00–09:00 台灣時間）送出要花點數的任務；要馬上送就加 --now",
     "submit credit jobs only in the half-price window (03:00-09:00 Taiwan time); --now submits anyway"),
    ("credits.max_parallel", 1, None,
     "同時跑幾個 AutoIP 任務（多數帳號白天只能 1 個）；環境變數 AIP_MAX 優先",
     "AutoIP tasks in flight at once (most accounts allow 1 by day); AIP_MAX wins"),
    ("explain.shorts", True, None,
     "解說：render.py 剪完寬版，接著剪直版 Shorts（project.py 要有 SHORTS）",
     "explainers: render.py cuts the vertical Short after the episode (when project.py has SHORTS)"),
    ("explain.shorts_layout", "band", ("band", "square"),
     "解說直版的版面（SHORTS 沒寫 layout 時）：band 整張畫在中間、square 取中間的正方形",
     "the Short's layout when SHORTS has none: band (the whole picture) or square (its middle square)"),
    ("video.enhance", False, None,
     "短劇和 MV：成片用 GPU 超分補幀的 clips_hd（先跑 drama/enhance.py 或 mv/enhance.py；RENDER[\"enhance\"] 優先）",
     "drama and MV: render from the GPU-enhanced clips_hd copies (run its enhance.py first; RENDER[\"enhance\"] wins)"),
    ("youtube.privacy", "private", ("private", "unlisted", "public"),
     "上傳後的狀態：private 私人（在 Studio 看過再公開）、unlisted 不公開、public 公開；--privacy 優先",
     "what an upload starts as: private (check it in Studio, publish there), unlisted or public; --privacy wins"),
    ("youtube.daily_max", 6, None,
     "每個頻道一天最多上傳或公開幾支（Shorts 也算），避免被限流；建議不要超過 6；0 不限制。上傳程式到了就停，--over-limit 硬上",
     "videos a channel uploads or publishes in one day, Shorts included, so it is not throttled (6 or fewer is wise; 0: "
     "no cap); the uploaders stop there, --over-limit goes past it"),
    ("youtube.log", True, None,
     "上架紀錄：上傳程式把每個動作記進共用資料庫的 youtube_log 表（資源庫的出貨紀錄讀它）",
     "the publishing log: the uploaders record every step in the shared database's youtube_log (the library reads it)"),
]
DEFAULTS = {k: d for k, d, *_ in SWITCHES}
TRUE, FALSE = ("1", "true", "yes", "on", "開"), ("0", "false", "no", "off", "關")


def parse(key, raw, where="?"):
    """A switch's value from its text, checked against the default's type and the choices."""
    default, choices = DEFAULTS[key], next(c for k, _, c, *_ in SWITCHES if k == key)
    s = str(raw).strip().lower()
    if isinstance(default, bool):
        if s in TRUE or s in FALSE:
            return s in TRUE
        raise ValueError(f"{where}: {key} = {raw!r}: use on or off")
    if isinstance(default, int):
        try:
            return int(s)
        except ValueError:
            raise ValueError(f"{where}: {key} = {raw!r}: use a whole number") from None
    if choices and s not in choices:
        raise ValueError(f"{where}: {key} = {raw!r}: use {' / '.join(choices)}")
    return s


def files(where=None):
    """The settings files that apply, weakest first: yours, then the series folder's, then the episode folder's."""
    out = [USER]
    if where:
        d = os.path.abspath(where if os.path.isdir(where) else os.path.dirname(where))
        out += [os.path.join(os.path.dirname(d), NAME), os.path.join(d, NAME)]
    found = []
    for p in out:
        if os.path.exists(p) and p not in found:
            found.append(p)
    return found


def settings(where=None):
    """{key: (value, source)} for every switch; source is "default" or the file that set it."""
    out = {k: (d, "default") for k, d in DEFAULTS.items()}
    for path in files(where):
        cp = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
        cp.read(path, encoding="utf-8")
        for sec in cp.sections():
            for opt, raw in cp.items(sec):
                key = f"{sec}.{opt}"
                if key not in DEFAULTS:
                    print(f"  (workflow: {path}: unknown switch {key})", file=sys.stderr)
                    continue
                out[key] = (parse(key, raw, path), path)
    return out


def get(key, where=None):
    """One switch's value for the episode (or series) folder `where`."""
    return settings(where)[key][0]


def shown(v):
    return ("on" if v else "off") if isinstance(v, bool) else str(v)


def template(series=False):
    """A commented settings file. Yours lists every switch; a series file lists them commented out, to uncomment only
    what that series does differently."""
    lines = ["# Dreamfab workflow switches: turn each automatic step on or off. Docs: docs/zh-TW/WORKFLOW.md (中文),",
             "# docs/en/WORKFLOW.md. Check what applies: python dreamfab/workflow.py show <episode folder>",
             "# 工作流程開關：每個自動步驟要不要做，自己決定。"
             + ("這是一個系列的設定，只把這個系列不一樣的地方取消註解。" if series else "這是你自己的設定，所有系列都套用。")]
    sec = None
    for key, default, choices, zh, en in SWITCHES:
        s, k = key.split(".")
        if s != sec:
            lines += ["", f"[{s}]"]; sec = s
        lines += [f"# {zh}", f"# {en}", f"{'# ' if series else ''}{k} = {shown(default)}"]
    return "\n".join(lines) + "\n"


def set_value(path, key, value):
    """Write key = value into an INI file, keeping its comments: replace the line (commented or not) or add it."""
    sec, opt = key.split(".")
    text = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []
    line, cur, at, end = f"{opt} = {value}", None, None, None
    for i, l in enumerate(text):
        t = l.strip()
        if t.startswith("[") and t.endswith("]"):
            cur = t[1:-1].strip()
            continue
        if cur == sec:
            end = i
            bare = t.lstrip("#; ").split("=")[0].strip().lower() if "=" in t else ""
            if bare == opt and (at is None or not t.startswith(("#", ";"))):
                at = i
    if at is not None:
        text[at] = line
    elif end is not None:
        text.insert(end + 1, line)
    else:
        text += ["", f"[{sec}]", line]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(text) + "\n")


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("show", "init", "set"):
        sys.exit(__doc__)
    if a[0] == "show":
        where = a[1] if len(a) > 1 else None
        rows = settings(where)
        width = max(len(k) for k in rows)
        for key, *_ in SWITCHES:
            v, src = rows[key]
            print(f"{key:<{width}}  {shown(v):<8}  {src}")
        print("files read: " + (", ".join(files(where)) or "none (all defaults)"))
    elif a[0] == "init":
        path = os.path.join(a[1], NAME) if len(a) > 1 else USER
        if os.path.exists(path):
            sys.exit(f"{path} is already there: edit it, or use set")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        open(path, "w", encoding="utf-8", newline="\n").write(template(series=len(a) > 1))
        print(f"wrote {path}")
    else:
        if len(a) < 3 or a[1] not in DEFAULTS:
            sys.exit("set KEY VALUE [DIR]; KEY is one of: " + ", ".join(DEFAULTS))
        try:
            value = shown(parse(a[1], a[2], "set"))
        except ValueError as e:
            sys.exit(str(e))
        path = os.path.join(a[3], NAME) if len(a) > 3 else USER
        set_value(path, a[1], value)
        print(f"{path}: {a[1]} = {value}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

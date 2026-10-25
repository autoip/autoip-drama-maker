"""Epic-theatre kinetic typography (ASS for libass): the song is staged as a play in acts.

Voice "F" lines glide in silver, voice "M" lines slam in with a blood-red edge and shake; finished lines burn into
rising ash. Everything song-specific comes from the project's TYPO dict (see examples/demo/project.py):
  title / title_en / tagline / genre      title cards (prologue, finale, epilogue)
  ep_card   ("其三", "不見")             episode card before the prologue title: small number over two big characters
  ep_card_s / intro_title_s              how long the episode card / the burning title stay (default: card 4 s, title to section end)
  rewrite   ("old line", "part"[, "new"]) card before the title: an old line, then a vermilion stroke crosses out "part"
                                         (and writes "new" above it in the same colour)
  rewrite_s / rewrite_color              how long it stays (default 5 s) / stroke colour (default C8281E)
  title_step                             beats between title characters in the prologue (default 4)
  acts      {section key: "ACT I", ...}  corner header at each section start ("key：subtitle" section names)
  specials  {section key: "intro" | "plates" | "finale" | "outro"}
  readings  {word: "romanization"}       small gold reading under rhyme words at the end of a line
  hold      {line text: seconds}         clear that line this long after its last word (a shout before a long silence)
  gags      [{"type": ..., "match": word or [words], ...}]  keyword effects, see GAGS below

build(sections, words, cut, a, b, beats, theme, plates=()) -> list of ASS lines; times are body time (song - cut).
"""
import difflib, math, os, random, re
from PIL import ImageFont

W, H = 1920, 1080
FONT, LATIN, FONT_FILE, FSK = "Noto Serif TC", "Noto Serif", None, 1.45
_pil = {}
OFFSCREEN = []  # (t, token, x, y, size) of glyphs that would leave the frame: check after build()
WHITE, SILVER, GOLD, BLOOD, EMBER, FIRE = "FFFFFF", "DCE6F5", "F2C55C", "B0101A", "FF7A1A", "FFB030"


def configure(theme, base_dir=""):
    """Fonts from TYPO: font (family name libass sees), font_file (for measuring), font_scale, latin."""
    global FONT, LATIN, FONT_FILE, FSK
    FONT, LATIN = theme.get("font", FONT), theme.get("latin", LATIN)
    FSK = theme.get("font_scale", FSK)
    FONT_FILE = os.path.join(base_dir, theme["font_file"])
    _pil.clear()


FS = lambda em: int(round(em * FSK))  # em -> ASS \fs (libass sizes by ascent+descent, so CJK fonts need a factor)


def col(h):
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&"


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def text_w(s, size):
    if size not in _pil:
        _pil[size] = ImageFont.truetype(FONT_FILE, size)
    return _pil[size].getlength(s)


def hits(g, text):
    m = g.get("match")
    return any(k in text for k in (m if isinstance(m, list) else [m]))


# ---------------------------------------------------------------- timing
def tokenize(text):
    toks = []
    for m in re.finditer(r"[A-Za-z0-9]+(?: [A-Za-z0-9]+)*|[^\sA-Za-z0-9]", text):
        s = m.group()
        if re.fullmatch(r"[，。！？、「」“”…,.!?：:；;—-]", s):
            continue
        toks.append(s)
    return toks


norm = lambda s: re.sub(r"[^\w]", "", s.lower())


def time_tokens(lines, words):
    """Per-token start times: align lyric characters to ASR word characters, interpolate the gaps.
    lines: [(line start, text)], words: [[start, end, word]] -> [(t_first, t_next_line, [(token, t)])]"""
    asr = []
    for s, e, w in words:
        cs = norm(w)
        for i, c in enumerate(cs):
            asr.append((c, s + (e - s) * i / max(1, len(cs))))
    lyr, toks = [], [tokenize(x) for _, x in lines]
    for li, tk in enumerate(toks):
        for ti, tok in enumerate(tk):
            for c in norm(tok):
                lyr.append((c, li, ti))
    sm = difflib.SequenceMatcher(None, "".join(c for c, *_ in lyr), "".join(c for c, _ in asr), autojunk=False)
    t_of = [None] * len(lyr)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            t_of[blk.a + k] = asr[blk.b + k][1]
    out = []
    for li, (t0, _) in enumerate(lines):
        t1 = lines[li + 1][0] if li + 1 < len(lines) else t0 + 3.2
        idx = [k for k, (_, l, _) in enumerate(lyr) if l == li]
        pts = [(k, t_of[k]) for k in idx if t_of[k] is not None and t0 - 0.3 <= t_of[k] <= t1 - 0.1]
        pts = [p for i, p in enumerate(pts) if i == 0 or p[1] >= pts[i - 1][1]]
        if not pts or pts[0][0] != idx[0]:
            pts.insert(0, (idx[0], t0))
        if pts[-1][0] != idx[-1]:
            pts.append((idx[-1], min(t1 - 0.25, pts[-1][1] + 0.2 * (idx[-1] - pts[-1][0]))))
        times = {}
        for (ka, ta), (kb, tb) in zip(pts, pts[1:]):
            for k in range(ka, kb + 1):
                times[k] = ta + (tb - ta) * (k - ka) / max(1, kb - ka)
        if len(pts) == 1:
            times[pts[0][0]] = pts[0][1]
        tt, last = [], -1
        for ti, tok in enumerate(toks[li]):
            ks = [k for k in idx if lyr[k][2] == ti]
            t = times.get(ks[0], t0) if ks else (tt[-1][1] + 0.1 if tt else t0)
            t = max(t, last + 0.05)
            tt.append((tok, t)); last = t
        out.append((tt[0][1], t1, tt))
    return out


# ---------------------------------------------------------------- events
class Ev:
    def __init__(self):
        self.rows = []

    def add(self, t0, t1, tags, text, layer=5):
        if t1 - t0 >= 0.02:
            self.rows.append(f"Dialogue: {layer},{ts(t0)},{ts(t1)},K,,0,0,0,,{{{tags}}}{text}")


def shape(ev, t0, t1, x, y, path, c, alpha="00", layer=2, extra=""):
    pos = "" if "\\move" in extra else f"\\pos({x:.0f},{y:.0f})"  # libass: the first \pos/\move wins
    ev.add(t0, t1, f"\\an7{pos}\\bord0\\shad0\\c{col(c)}\\alpha&H{alpha}&{extra}\\p1", path, layer)


rect = lambda w, h: f"m 0 0 l {w:.0f} 0 {w:.0f} {h:.0f} 0 {h:.0f}"


def circle(r):
    k = r * 0.5523
    return (f"m {r} 0 b {r + k} 0 {2 * r} {r - k} {2 * r} {r} b {2 * r} {r + k} {r + k} {2 * r} {r} {2 * r} "
            f"b {r - k} {2 * r} 0 {r + k} 0 {r} b 0 {r - k} {r - k} 0 {r} 0")


def base_tags(fs, voice, color, rot=0.0):
    if voice == "M":
        return f"\\an5\\fn{FONT}\\fs{FS(fs)}\\frz{rot:.1f}\\bord{max(5, fs // 13)}\\3c{col(BLOOD)}\\shad0\\blur1.2\\c{col(color)}"
    return f"\\an5\\fn{FONT}\\fs{FS(fs)}\\frz{rot:.1f}\\bord{max(4, fs // 18)}\\3c&H281810&\\shad0\\blur0.8\\c{col(color)}"


def glyph(ev, t0, t1, tok, x, y, fs, rot, voice, color, rnd, burn=None, L=5, entry=None):
    """One token: entry (slam | glide | extra tags), hold, then optionally burn to ash and rise."""
    hw, hh = text_w(tok, fs) / 2, fs * 0.6
    if x - hw < 8 or x + hw > W - 8 or y - hh < 8 or y + hh > H - 8:
        OFFSCREEN.append((round(t0, 2), tok, int(x), int(y), fs))
    b = base_tags(fs, voice, color, rot)
    t_hold_end = burn if burn else t1
    entry = entry or ("slam" if voice == "M" else "glide")
    if entry == "slam":
        ev.add(t0, t0 + 0.14, f"{b}\\pos({x:.0f},{y:.0f})\\fscx250\\fscy250\\blur10\\alpha&H50&\\t(0,140,\\fscx100\\fscy100\\blur1.2\\alpha&H00&)", tok, L)
        for k in range(4):  # impact shake
            a = t0 + 0.14 + k * 0.04
            ev.add(a, a + 0.04, f"{b}\\pos({x + rnd.uniform(-11, 11):.0f},{y + rnd.uniform(-8, 8):.0f})", tok, L)
        ev.add(t0 + 0.30, t_hold_end, f"{b}\\pos({x:.0f},{y:.0f})", tok, L)
        ev.add(t0, t0 + 0.35, f"\\an5\\fn{FONT}\\fs{FS(fs)}\\frz{rot:.1f}\\bord{fs // 7}\\3c{col(EMBER)}\\c{col(EMBER)}\\blur14\\alpha&H40&\\pos({x:.0f},{y:.0f})\\t(0,350,\\alpha&HFF&)", tok, L - 1)
    elif entry == "glide":
        ev.add(t0, t_hold_end, f"{b}\\move({x:.0f},{y + 34:.0f},{x:.0f},{y:.0f},0,260)\\blur9\\alpha&HFF&\\t(0,260,\\blur0.8\\alpha&H00&)", tok, L)
        ev.add(t0, t_hold_end, f"\\an5\\fn{FONT}\\fs{FS(fs)}\\frz{rot:.1f}\\bord{fs // 9}\\3c&HF0D8B0&\\c&HF0D8B0&\\blur16\\alpha&HA0&\\move({x:.0f},{y + 34:.0f},{x:.0f},{y:.0f},0,260)", tok, L - 1)
    else:  # plain pos + caller's animation tags
        ev.add(t0, t_hold_end, f"{b}\\pos({x:.0f},{y:.0f}){entry}", tok, L)
    if burn and burn < t1:  # ember -> ash, drifting up
        dx, dy = rnd.uniform(-40, 40), rnd.uniform(-140, -80)
        ev.add(burn, t1, f"{b}\\t(0,220,\\c{col(EMBER)}\\3c&H000000&)\\move({x:.0f},{y:.0f},{x + dx:.0f},{y + dy:.0f},120,{int((t1 - burn) * 1000)})"
                         f"\\t(120,{int((t1 - burn) * 1000)},\\blur6\\fscx70\\fscy70\\alpha&HFF&)", tok, 3)


# ---------------------------------------------------------------- layout
ZONES = {"TL": (620, 250), "TR": (1300, 250), "TC": (960, 210), "BL": (620, 840), "BR": (1300, 840), "BC": (960, 870),
         "ML": (560, 540), "MR": (1360, 540), "C": (960, 540)}


def layout(toks, zone, size, vertical, rnd, voice):
    """-> [(token, x, y, size, rotation)]; horizontal rows (split in two past 1500 px) or vertical columns at the edge."""
    items = [[t, size] for t, _ in toks]
    if vertical:
        room = H - 200
        total = sum(fs * 1.04 for _, fs in items)
        cols = [items]
        if total > room * 0.8:
            cut = len(items) // 2
            cols = [items[:cut], items[cut:]]
        tallest = max(sum(fs * 1.04 for _, fs in c) for c in cols)
        k = min(1.0, room / tallest)
        colw = size * k * 1.3
        left = zone in ("TL", "BL", "ML")
        edge = 190 if W >= 1600 else 120  # a portrait frame is mostly face: keep the columns tight to the edge
        x0 = edge + (len(cols) - 1) * colw if left else W - edge
        out = []
        for ci, c in enumerate(cols):
            x = x0 - ci * colw
            h = sum(fs * k * 1.04 for _, fs in c)
            y = max(100, min(H - 100 - h, H / 2 - h / 2 + ci * size * 0.5))
            for tok, fs in c:
                f = int(fs * k)
                out.append((tok, x, y + f / 2, f, 0.0)); y += f * 1.04
        return out
    cx, cy = ZONES[zone]
    widths = [text_w(t, fs) + fs * 0.04 for t, fs in items]
    total = sum(widths)
    rows = [list(range(len(items)))]
    if total > W - 420:  # 1500 px on a 1920 canvas
        acc, cut = 0, 0
        for i, w in enumerate(widths):
            acc += w
            if acc > total / 2:
                cut = i + 1; break
        rows = [list(range(cut)), list(range(cut, len(items)))]
    rot = rnd.uniform(-6, 6) if voice == "M" else rnd.uniform(-1.5, 1.5)
    rowh = size * 1.25
    out = []
    for r, row in enumerate(rows):
        rw = sum(widths[i] for i in row)
        indent = (r - (len(rows) - 1) / 2) * size * 0.9  # stagger the second row
        x0 = min(max(cx - rw / 2 + indent, 80), W - 80 - rw)
        y = min(max(cy + (r - (len(rows) - 1) / 2) * rowh, 120), H - 120)
        x = x0
        for i in row:
            px, py = x + widths[i] / 2, y
            a = math.radians(-rot)
            dx = px - (x0 + rw / 2)
            px, py = x0 + rw / 2 + dx * math.cos(a), y + dx * math.sin(a)
            out.append((items[i][0], px, py, items[i][1], rot))
            x += widths[i]
    return out


def title_xs(title, spacing, cx=960):
    n = len(title)
    return [cx + (i - (n - 1) / 2) * spacing for i in range(n)]


# ---------------------------------------------------------------- set pieces
def coins(ev, t0, t1, x, y, rnd, n=14):
    for _ in range(n):
        a = t0 + rnd.uniform(0, 0.6); r = rnd.choice([10, 13, 16])
        sx = x + rnd.uniform(-220, 220)
        shape(ev, a, min(t1, a + 1.1), sx, y - 160, circle(r), GOLD, "10", 4,
              f"\\3c{col('7A5310')}\\bord2\\move({sx:.0f},{y - 200:.0f},{sx + rnd.uniform(-30, 30):.0f},{y + 260:.0f})\\fad(0,200)")


def act_header(ev, T, s0, s1, sec_name, acts):
    key = sec_name.split("：")[0]
    act, title = acts.get(key, ""), sec_name.split("：")[-1]
    if not act:
        return
    t0, t1 = T(s0), min(T(s0) + 3.2, T(s1))
    shape(ev, t0, t1, 0, 22, rect(620, 150), "000000", "70", 5, "\\blur18\\fad(300,500)")
    ev.add(t0, t1, f"\\an7\\fn{LATIN}\\b1\\fs58\\fsp12\\bord3\\3c&H000000&\\c{col(GOLD)}\\pos(56,30)\\fad(300,500)", act, 6)
    shape(ev, t0, t1, 56, 104, rect(460, 3), GOLD, "10", 6, "\\fscx0\\t(0,400,\\fscx100)\\fad(0,500)")
    ev.add(t0 + 0.15, t1, f"\\an7\\fn{FONT}\\fs{FS(52)}\\bord4\\3c&H000000&\\c{col(SILVER)}\\pos(56,116)\\fad(300,500)", title, 6)


def title_card(ev, T, beats, t0, t1, rnd, th):
    """FINALE: the title slams in one character per downbeat at centre, then shrinks to the top so the singer stays
    visible; title_en and tagline under it, ember glow on every beat."""
    title = th["title"]; n = len(title)
    bs = [b for b in beats if t0 <= b < t1]
    hits_ = bs[0:2 * n:2][:n] if len(bs) >= 2 * n - 1 else [t0 + 0.6 * i for i in range(n)]
    xs = title_xs(title, 340)
    t_up = hits_[-1] + 1.4
    Y0, Y1, K = 470, 165, 0.55
    for ch, x, h in zip(title, xs, hits_):
        glyph(ev, T(h), T(t_up), ch, x, Y0, 250, 0, "M", WHITE, rnd, L=8)
        shape(ev, T(h), T(h + 0.12), 0, 0, rect(W, H), "FFFFFF", "90", 9)
        x1 = 960 + (x - 960) * K
        b = base_tags(250, "M", WHITE)
        ev.add(T(t_up), T(t1 - 1.2), f"{b}\\move({x:.0f},{Y0},{x1:.0f},{Y1},0,600)\\t(0,600,\\fscx{K * 100:.0f}\\fscy{K * 100:.0f})", ch, 8)
        ev.add(T(t1 - 1.2), T(t1), f"{b}\\fscx{K * 100:.0f}\\fscy{K * 100:.0f}\\t(0,250,\\c{col(EMBER)}\\3c&H000000&)"
                                   f"\\t(150,1200,\\blur6\\alpha&HFF&)\\move({x1:.0f},{Y1},{x1:.0f},{Y1 - 80},150,1200)", ch, 8)
    ts_ = hits_[-1] + 0.5
    sub = [(th.get("title_en", ""), f"\\fn{LATIN}\\b1\\fs76\\fsp26\\bord3\\3c&H000000&\\c{col(GOLD)}\\blur0.6", 690, 300),
           (th.get("tagline", ""), f"\\fn{LATIN}\\i1\\fs46\\fsp6\\bord2\\3c&H000000&\\c{col(SILVER)}", 790, 360)]
    for k, (txt, tags, ya, yb) in enumerate(sub):
        if not txt:
            continue
        a = ts_ + 0.4 * k
        ev.add(T(a), T(t_up), f"\\an5{tags}\\pos(960,{ya})\\fad(400,0)", txt, 8)
        ev.add(T(t_up), T(t1 - 0.6), f"\\an5{tags}\\move(960,{ya},960,{yb},0,600)\\t(0,600,\\fscx70\\fscy70)\\fad(0,600)", txt, 8)
    for b in bs:  # heartbeat glow behind the title
        if hits_[-1] + 0.3 < b < t1 - 1.3:
            up = b >= t_up + 0.6
            ev.add(T(b), T(b + 0.22), f"\\an5\\fn{FONT}\\fs{FS(250 * (K if up else 1)):.0f}\\fsp{60 * (K if up else 1):.0f}\\bord18\\3c{col(EMBER)}\\c{col(EMBER)}\\blur22\\alpha&H70&"
                                   f"\\pos(960,{Y1 if up else Y0})\\t(0,220,\\alpha&HFF&)", " ".join(title), 7)


def cycle_wheel(ev, T, t0, t1, rnd, words, highlight=None):
    """Words riding a slowly turning ring (centre right): A -> B -> C -> A ..."""
    cx, cy, r = 1420, 520, 230
    shape(ev, T(t0), T(t1), cx - r, cy - r, circle(r), GOLD, "FF", 2, f"\\3c{col(GOLD)}\\bord3\\3a&H60&\\fad(300,400)")
    steps = int((t1 - t0) / 0.12)
    for k in range(steps):
        a0 = T(t0 + k * 0.12)
        for i, w in enumerate(words):
            ang = math.radians(-90 + i * 360 / len(words) + k * 4)
            x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
            ev.add(a0, a0 + 0.12, f"\\an5\\fn{FONT}\\fs{FS(70)}\\bord5\\3c{col(BLOOD)}\\c{col(GOLD if w == highlight else WHITE)}\\pos({x:.0f},{y:.0f})"
                   + ("\\fad(300,0)" if k == 0 else ("\\fad(0,400)" if k == steps - 1 else "")), w, 4)
        ang = math.radians(-30 + k * 4)
        ev.add(a0, a0 + 0.12, f"\\an5\\fn{LATIN}\\b1\\fs60\\bord0\\c{col(GOLD)}\\alpha&H40&\\frz{-math.degrees(ang) - 90:.0f}\\pos({cx + r * math.cos(ang):.0f},{cy + r * math.sin(ang):.0f})", "➤", 3)


def intro_title(ev, T, beats, t0, t1, rnd, th):
    """PROLOGUE: the title burns out of the dark one character per bar, then crumbles to ash before the vocals."""
    title = th["title"]
    bs = [x for x in beats if t0 <= x < t1]
    step = th.get("title_step", 4)  # beats between characters
    hits_ = [bs[i] for i in range(0, step * len(title), step) if i < len(bs)] or [t0 + i for i in range(len(title))]
    t_end = t1 - 0.3
    for ch, x, h in zip(title, title_xs(title, 340), hits_):
        x = round(x)
        b = base_tags(230, "M", WHITE)
        ev.add(T(h), T(h + 0.9), f"\\an5\\fn{FONT}\\fs{FS(230)}\\bord14\\3c{col(EMBER)}\\c{col(FIRE)}\\blur18\\pos({x},500)\\alpha&H20&\\t(0,900,\\alpha&HFF&)", ch, 7)
        ev.add(T(h), T(t_end - 1.0), f"{b}\\pos({x},500)\\c{col(FIRE)}\\alpha&HFF&\\t(0,700,\\alpha&H00&)\\t(300,1400,\\c{col(WHITE)})", ch, 8)
        dx = rnd.uniform(-60, 60)
        ev.add(T(t_end - 1.0), T(t_end), f"{b}\\move({x},500,{x + dx:.0f},380,0,1000)\\t(0,250,\\c{col(EMBER)}\\3c&H000000&)\\t(150,1000,\\blur8\\fscx70\\fscy70\\alpha&HFF&)", ch, 8)
        shape(ev, T(h), T(h + 0.1), 0, 0, rect(W, H), "FFF0D0", "A0", 9)
    ts_ = hits_[-1] + 0.6
    if th.get("title_en"):
        ev.add(T(ts_), T(t_end - 0.8), f"\\an5\\fn{LATIN}\\b1\\fs76\\fsp26\\bord3\\3c&H000000&\\c{col(GOLD)}\\pos(960,710)\\fad(500,600)", th["title_en"], 8)
    if th.get("genre"):
        ev.add(T(ts_ + 0.4), T(t_end - 0.8), f"\\an5\\fn{FONT}\\fs{FS(44)}\\bord3\\3c&H000000&\\c{col(SILVER)}\\pos(960,800)\\fad(500,600)", th["genre"], 8)


def ep_card(ev, T, t0, t1, th):
    """Episode card (series format: prop close-up + episode number + the two-character theme), e.g. 其三・不見."""
    num, word = th["ep_card"]
    ev.add(T(t0), T(t1), f"\\an5\\fn{FONT}\\fs{FS(110)}\\fsp30\\bord5\\3c&H000000&\\c{col(GOLD)}\\pos(960,360)\\fad(600,700)", num, 8)
    shape(ev, T(t0 + 0.3), T(t1), 710, 452, rect(500, 4), GOLD, "20", 8, "\\fscx0\\t(0,600,\\fscx100)\\fad(0,700)")
    for ch, x in zip(word, title_xs(word, 300)):
        ev.add(T(t0 + 0.5), T(t1), f"{base_tags(240, 'M', WHITE)}\\pos({x:.0f},600)\\blur3\\fad(800,700)", ch, 8)


def rewrite_card(ev, T, t0, t1, th):
    """Card before the title: an old line of the legend, then a vermilion stroke crosses out the part the song rewrites."""
    old, struck, *fix = th["rewrite"]
    sp = 130 if len(old) <= 8 else 110
    xs = title_xs(old, sp)
    for ch, x in zip(old, xs):
        ev.add(T(t0), T(t1), f"{base_tags(110, 'F', SILVER)}\\pos({x:.0f},500)\\fad(700,600)", ch, 8)
    i = old.find(struck)
    if i >= 0:  # the stroke grows left to right from 1.4 s, over the struck characters only
        color = th.get("rewrite_color", "C8281E")
        shape(ev, T(t0 + 1.4), T(t1), xs[i] - sp / 2, 488, rect(sp * len(struck), 26), color, "10", 9,
              "\\blur2\\fscx0\\t(0,450,\\fscx100)\\fad(0,600)")
        if fix:  # ("old line", "part", "new"): the new words are written in the stroke's colour above the struck part
            cx = (xs[i] + xs[i + len(struck) - 1]) / 2
            for ch, x in zip(fix[0], title_xs(fix[0], sp, cx)):
                ev.add(T(t0 + 2.1), T(t1), f"{base_tags(96, 'F', color)}\\pos({x:.0f},360)\\fad(500,600)", ch, 9)


def band_plates(ev, T, plates):
    """INTERMISSION: name plate (english / native role) for each player as the cut lands on them."""
    for t0, t1, en, zh in plates:
        a, b = T(t0) + 0.08, T(t1) - 0.05
        shape(ev, a, b, 0, 860, rect(760, 150), "000000", "60", 5, "\\blur20\\fad(120,150)")
        ev.add(a, b, f"\\an7\\fn{LATIN}\\b1\\fs64\\fsp14\\bord3\\3c&H000000&\\c{col(GOLD)}\\move(-200,880,70,880,0,220)\\fad(0,150)", en, 6)
        shape(ev, a + 0.1, b, 70, 960, rect(420, 3), GOLD, "10", 6, "\\fscx0\\t(0,300,\\fscx100)\\fad(0,150)")
        ev.add(a + 0.12, b, f"\\an7\\fn{FONT}\\fs{FS(50)}\\bord4\\3c{col(BLOOD)}\\c{col(WHITE)}\\pos(70,972)\\fad(150,150)", zh, 6)


def epilogue(ev, T, t0, t1, th):
    """EPILOGUE: the title returns quietly in silver and fades with the music."""
    for i, (ch, x) in enumerate(zip(th["title"], title_xs(th["title"], 200))):
        ev.add(T(t0 + i * 0.5), T(t1), f"\\an5\\fn{FONT}\\fs{FS(150)}\\bord5\\3c&H101010&\\c{col(SILVER)}\\blur1\\move({x:.0f},520,{x:.0f},490,0,1500)\\fad(900,1400)", ch, 7)
    if th.get("title_en"):
        ev.add(T(t0 + 1.8), T(t1), f"\\an5\\fn{LATIN}\\b1\\fs60\\fsp24\\bord2\\3c&H000000&\\c{col(GOLD)}\\pos(960,640)\\fad(900,1400)", th["title_en"], 7)
    if th.get("genre"):
        ev.add(T(t0 + 2.6), T(t1), f"\\an5\\fn{FONT}\\fs{FS(40)}\\bord3\\3c&H000000&\\c{col(SILVER)}\\pos(960,720)\\fad(900,1400)", th["genre"], 7)


# ---------------------------------------------------------------- keyword gags
# glyph-level (change how matching tokens of a matching line behave):
#   color      chars, color          recolour tokens
#   title_line                       line containing the title: title chars huge at centre + curtains + spotlight
#   scurry     chars                 tokens shrink, then run off-screen to the right
#   float_away chars                 tokens float up and away
#   tear       char                  a drop runs down from that token
#   enlarge    chars, scale          oversized
# line-level:
#   zone       zones [a, b]          pin the line to zone a (or b if the previous line was in a's row)
#   coins                            gold coins rain from the line
#   clink      char                  two flashes collide on that token + white flash
#   clap       char, word            the word ("CLAP") pops all over the screen on beats after that token
#   wheel      words, highlight      words ride a turning ring while the line holds
#   explode                          white flash, every token flies outwards
def gags_of(theme, kind, text):
    return [g for g in theme.get("gags", []) if g["type"] == kind and hits(g, text)]


def build(sections, words, cut, a, b, beats, theme, seed=7, plates=()):
    rnd = random.Random(seed)
    ev = Ev()
    T = lambda t: t - cut
    title = theme.get("title", "")
    acts, specials = theme.get("acts", {}), theme.get("specials", {})
    readings, anywhere = theme.get("readings", {}), set(theme.get("readings_anywhere", []))
    for s in sections:
        if s["span"][0] is None:
            continue
        s0, s1 = s["span"]
        if s1 <= a or s0 >= b:
            continue
        s0c, s1c = max(s0, a), min(s1, b)
        key = s["name"].split("：")[0]
        sp = specials.get(key)
        if s0 >= a - 0.01:
            act_header(ev, T, s0c, s1c, s["name"], acts)
        if sp == "outro":
            epilogue(ev, T, s0c + theme.get("outro_delay", 5.5), s1c - 0.2, theme)
        if sp == "intro":
            t0 = max(s0, a) + 1.0
            if theme.get("ep_card"):
                cs = theme.get("ep_card_s", 4.0)
                ep_card(ev, T, t0 - 0.6, t0 - 0.6 + cs, theme)
                t0 += cs
            if theme.get("rewrite"):
                rs = theme.get("rewrite_s", 5.0)
                rewrite_card(ev, T, t0 - 0.6, t0 - 0.6 + rs, theme)
                t0 += rs
            ts = theme.get("intro_title_s")
            intro_title(ev, T, beats, t0, min(s1c, t0 + ts) if ts else s1c, rnd, theme)
        if sp == "plates":
            band_plates(ev, T, plates)
        if sp == "finale":
            title_card(ev, T, beats, max(s0, a) + 0.6, s1c, rnd, theme)
        if not s.get("lines"):
            continue
        timed = time_tokens([tuple(x) for x in s["lines"]], words)
        voices = s["voices"]
        prev_zone, prev_vside = None, None
        for li, (t0, t1, toks) in enumerate(timed):
            if t0 < a or t0 >= b:
                continue
            voice = voices[li]
            text = "".join(k for k, _ in toks)
            t_next = timed[li + 1][2][0][1] if li + 1 < len(timed) else min(s1c, toks[-1][1] + 1.6)
            if text in theme.get("hold", {}):
                t_next = min(t_next, toks[-1][1] + theme["hold"][text])
            t_end = min(t_next + 0.9, s1c)  # the old line burns away while the next one arrives
            burn = t_next - 0.05
            is_title = bool(title) and title in text and any(g["type"] == "title_line" for g in theme.get("gags", []))
            # ------ placement
            pool = [z for z in ZONES if z != "C" and (prev_zone is None or z[0] != prev_zone[0])]
            zone = rnd.choice(pool)
            p_vert = theme.get("vertical", {"F": 0.5}).get(voice, 0)  # share of lines set as vertical columns at the frame edge
            vertical = p_vert > 0 and rnd.random() < p_vert and not is_title
            size = rnd.choice([96, 104, 112]) if voice == "F" else rnd.choice([110, 120, 130])
            color = SILVER if voice == "F" else WHITE
            if is_title:
                zone, vertical = "C", False
            for g in gags_of(theme, "zone", text):
                za, zb = g["zones"]
                zone, vertical = (zb if prev_zone and prev_zone[0] == za[0] else za), False
            side = "L" if zone in ("TL", "BL", "ML") else "R"
            if vertical and side == prev_vside:  # the previous column is still burning away on this edge
                zone, side = zone[0] + ("R" if side == "L" else "L"), ("R" if side == "L" else "L")
            pos = layout(toks, zone, size, vertical, rnd, voice)
            if is_title:  # the title as a theatre marquee, the rest of the line smaller underneath
                head = [p for p in pos if p[0] in title][:len(title)]
                rest = [p for p in pos if p not in head]
                sp_ = min(320, 1500 / max(1, len(head)))
                pos = [(k, x, 430, int(min(210, sp_ * 0.66)), 0.0) for (k, *_r), x in zip(head, title_xs(head, sp_))]
                rl = layout([(k, 0) for k, *_r in rest], "BC", 92, False, rnd, voice)
                pos += [(k, x, y - 70, f, r) for k, x, y, f, r in rl]
                for x0 in (0, W / 2):  # curtains swing open
                    shape(ev, T(t0 - 0.12), T(t0 + 0.3), x0, 0, rect(W / 2, H), BLOOD, "00", 9,
                          f"\\move({x0:.0f},0,{x0 - W / 2 if x0 == 0 else W:.0f},0,0,400)")
                ev.add(T(t0), T(t_end), f"\\an8\\pos(960,0)\\bord0\\c&HE0F0FF&\\alpha&HC8&\\blur30\\p1", "m 0 0 l 260 0 700 1080 -440 1080", 1)
            # ------ glyphs
            for (tok, tt), (_, x, y, fs, rot) in zip(toks, pos):
                c = color
                for g in gags_of(theme, "color", text):
                    if tok in g["chars"]:
                        c = g["color"]
                entry, L = None, 5
                if is_title and tok in title:
                    entry, L = "slam", 7
                special = None
                for kind in ("scurry", "float_away", "tear"):
                    for g in gags_of(theme, kind, text):
                        if tok in g.get("chars", g.get("char", "")):
                            special = kind
                if special == "scurry":
                    glyph(ev, T(tt), T(t_next), tok, x, y, fs, rot, voice, c, rnd, None, L, None)
                    ev.add(T(t_next), T(t_next + 0.6), f"{base_tags(int(fs * .6), voice, c)}\\move({x:.0f},{y:.0f},{W + 200:.0f},{y + rnd.uniform(-40, 40):.0f},{int(rnd.uniform(0, 200))},600)", tok, 5)
                    continue
                if special == "float_away":
                    glyph(ev, T(tt), T(t_next), tok, x, y, fs, rot, voice, c, rnd, None, L, None)
                    ev.add(T(t_next), T(t_next + 1.0), f"{base_tags(fs, voice, c)}\\move({x:.0f},{y:.0f},{x + rnd.uniform(-60, 60):.0f},-150,0,1000)\\t(0,1000,\\fscx70\\fscy70)", tok, 5)
                    continue
                if special == "tear":
                    glyph(ev, T(tt), T(t_next), tok, x, y, fs, rot, voice, c, rnd, T(burn), L, None)
                    shape(ev, T(tt + 0.3), T(tt + 1.4), x - 9, y + fs * 0.5, circle(9), "BFE6FF", "20", 6,
                          f"\\move({x - 9:.0f},{y + fs * 0.5:.0f},{x - 9:.0f},{y + fs * 2.4:.0f},0,1100)\\fscy160\\fad(0,300)")
                    continue
                for g in gags_of(theme, "enlarge", text):
                    if tok in g["chars"]:
                        fs = int(fs * g.get("scale", 1.35))
                glyph(ev, T(tt), T(t_end), tok, x, y, fs, rot, voice, c, rnd, T(burn), L, entry)
            # ------ line-level
            lx = sum(p[1] for p in pos) / len(pos); ly = sum(p[2] for p in pos) / len(pos)
            for word, rom in readings.items():  # romanized reading under the rhyme word
                if text.endswith(word) or (word in text and word in anywhere):
                    ps = [p for p in pos if p[0] in word][-len(word):]
                    if "-" not in rom:  # one-syllable reading sits under the last character
                        ps = ps[-1:]
                    if ps and text.rfind(word) >= len(text) - 4:
                        kx = sum(p[1] for p in ps) / len(ps); ky = max(p[2] for p in ps) + ps[-1][3] * 0.82
                        if vertical:
                            kx, ky = ps[-1][1], ps[-1][2] + ps[-1][3] * 0.9
                        ky = min(ky, H - 40)
                        tk = [t for k_, t in toks if k_ in word][-1]
                        ev.add(T(tk + 0.15), T(burn), f"\\an5\\fn{LATIN}\\i1\\b1\\fs70\\bord3\\3c&H000000&\\c{col(GOLD)}\\pos({kx:.0f},{ky:.0f})\\fad(200,200)", rom, 6)
                        break
            if gags_of(theme, "coins", text):
                coins(ev, T(toks[-1][1]), T(t_end), lx, ly, rnd)
            for g in gags_of(theme, "clink", text):
                tk = next((t for k_, t in toks if k_ == g["char"]), toks[-1][1])
                for sx in (-1, 1):
                    ev.add(T(tk), T(tk + 0.35), f"\\an5\\fn{FONT}\\fs{FS(150)}\\bord0\\c&H3020E0&\\alpha&H40&\\move({lx + sx * 420:.0f},{ly:.0f},{lx + sx * 30:.0f},{ly:.0f},0,180)\\t(180,350,\\alpha&HFF&)", "◆", 4)
                shape(ev, T(tk + 0.18), T(tk + 0.3), 0, 0, rect(W, H), "FFFFFF", "C0", 9)
            for g in gags_of(theme, "clap", text):
                tk = next((t for k_, t in toks if k_ == g["char"]), toks[-1][1])
                for k in range(10):
                    a0 = tk + k * 0.28
                    ev.add(T(a0), T(a0 + 0.3), f"\\an5\\fn{LATIN}\\b1\\fs{rnd.choice([64, 80, 96])}\\bord2\\3c&H000000&\\c{col(SILVER)}\\alpha&H50&\\frz{rnd.uniform(-15, 15):.0f}"
                           f"\\pos({rnd.uniform(200, W - 200):.0f},{rnd.uniform(150, H - 150):.0f})\\fscx140\\fscy140\\t(0,120,\\fscx100\\fscy100)", g.get("word", "CLAP"), 3)
            for g in gags_of(theme, "wheel", text):
                cycle_wheel(ev, T, toks[0][1], t_end, rnd, g["words"], g.get("highlight"))
            if gags_of(theme, "explode", text):
                tb = toks[-1][1] + 0.2
                shape(ev, T(tb), T(tb + 0.4), 0, 0, rect(W, H), "FFF2D0", "00", 9, "\\t(0,400,\\alpha&HFF&)")
                for (tok, _), (_, x, y, fs, rot) in zip(toks, pos):
                    ang = math.atan2(y - ly, x - lx + 0.01)
                    ev.add(T(tb), T(tb + 0.7), f"{base_tags(fs, voice, FIRE, rot)}\\move({x:.0f},{y:.0f},{x + math.cos(ang) * 900:.0f},{y + math.sin(ang) * 700 + 200:.0f},0,700)"
                           f"\\t(0,700,\\frz{rnd.uniform(-180, 180):.0f}\\fscx180\\fscy180\\alpha&HFF&)", tok, 8)
            prev_zone, prev_vside = zone, (side if vertical else None)
    for i, bt in enumerate(beats):  # drifting embers on every other beat
        if a <= bt < b and i % 2 == 0:
            for _ in range(rnd.randint(1, 3)):
                x = rnd.uniform(0, W); r = rnd.choice([3, 4, 6])
                shape(ev, T(bt), T(bt + 1.6), x, H, circle(r), rnd.choice([EMBER, FIRE, "FFD27A"]), "30", 1,
                      f"\\blur2\\move({x:.0f},{rnd.uniform(H * .6, H):.0f},{x + rnd.uniform(-120, 120):.0f},{rnd.uniform(100, 500):.0f})\\fad(200,600)")
    head = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: K,{FONT},96,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,5,0,5,0,0,0,1",
            "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    return head + ev.rows

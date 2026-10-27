"""Short-drama subtitles (ASS for libass): dialogue, character intro cards, title card, labels, cliffhanger text.

Everything comes from the edit (timeline.resolve) and project.TYPO:
  font / font_scale          family name libass sees (see make_static_font.py) / libass size factor (Noto CJK ~1.45)
  size                       dialogue glyph size in px at 1080 wide (default 54)
  max_chars                  longest subtitle chunk (default 14 vertical, 22 landscape); lines are split at punctuation
  sub_y                      dialogue baseline as a fraction of the height (default 0.74 vertical: above the app's
                             caption / button area; 0.92 landscape)
  intro_y                    character intro card position, fraction of the height (default 0.56 / 0.6)
  intro_s / title_s          seconds an intro card / the title card stays (2.4 / 2.6)
  end_text                   text of a bare `end` flag (default 未完待續)
  badge                      e.g. "第1集": small corner tag for the whole episode (default none)
  accent                     RRGGBB of the intro bar, role line and title rule (default F2C55C)
  chat_y / chat_rows         livestream comments: bottom of the stack as a fraction of the height (default 0.66 / 0.8),
                             comments on screen at once (default 5)
Per character: CAST[k]["color"] colours that speaker's lines, CAST[k]["title"] is the role line of the intro card.
Row flags used here: intro=KEY, title, label=text, end[=text], chat=NAME, heard (subtitle what speech.py heard, not the
script line: an NG take that read the stage directions out).
chat=NAME: project.CHAT[NAME] = [("user", "comment"), ...] scroll up over that row like a livestream's comments,
bottom left (keep intro cards off those rows: both sit on the left).
"""
import difflib, os, re
from common import load_project, jload
from storyboard import PUNCT

STRONG = "。！？!?…"
SOFT_TAIL = "，。、；：,.;:"


def col(hexrgb, alpha="00"):
    h = hexrgb.lstrip("#")
    return f"&H{alpha}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ts(v):
    v = max(0.0, v)
    return f"{int(v // 3600)}:{int(v % 3600 // 60):02d}:{v % 60:05.2f}"


def srt_ts(v):
    v = max(0.0, v)
    return f"{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round(v % 1 * 1000)) % 1000:03d}"


def chunks(text, maxc):
    """Split a line into subtitle chunks at punctuation, merging short phrases up to maxc characters.
    -> [(display text, number of spoken characters)]"""
    phrases = [p for p in re.findall(r"[^，。！？；、,.!?;…—~～\s]+[，。！？；、,.!?;…—~～\s]*", text) if p.strip()]
    out = []
    for p in phrases:
        n = len(PUNCT.sub("", p))
        while n > maxc:  # a long phrase: cut it into even pieces
            k = -(-n // maxc)
            cut = -(-n // k)
            head, seen, j = "", 0, 0
            while seen < cut:
                head += p[j]; seen += bool(PUNCT.sub("", p[j])); j += 1
            out.append([head, seen, True])
            p, n = p[j:], n - seen
        if out and not out[-1][2] and out[-1][1] + n <= maxc and out[-1][0].rstrip()[-1:] not in STRONG:
            out[-1][0] += p; out[-1][1] += n
        else:
            out.append([p, n, False])
        out[-1][2] = out[-1][0].rstrip()[-1:] in STRONG
    return [(c.strip().rstrip(SOFT_TAIL).strip(), n) for c, n, _ in out if n]


def part(disp, i0, i1):
    """The piece of a chunk from its i0-th to its i1-th spoken character, with the punctuation inside it."""
    out, j = "", -1
    for c in disp:
        j += bool(PUNCT.sub("", c))
        if i0 <= j <= i1:
            out += c
    return out.strip().rstrip(SOFT_TAIL).strip()


def char_times(text, words, span):
    """Start / end time (clip seconds) of each spoken character of the line: ASR words matched with difflib, the rest
    spread evenly between known neighbours or across the speech span."""
    script = PUNCT.sub("", text)
    n = len(script)
    st, en = [None] * n, [None] * n
    asr = []
    for a, b, w in words:
        w = PUNCT.sub("", w)
        for k, c in enumerate(w):
            asr.append((c, a + (b - a) * k / len(w), a + (b - a) * (k + 1) / len(w)))
    if asr:
        sm = difflib.SequenceMatcher(None, script, "".join(c for c, _, _ in asr), autojunk=False)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                st[blk.a + k], en[blk.a + k] = asr[blk.b + k][1], asr[blk.b + k][2]
    a0, b0 = span
    known = [k for k in range(n) if st[k] is not None]
    for k in range(n):
        if st[k] is not None:
            continue
        lo = max((j for j in known if j < k), default=None)
        hi = min((j for j in known if j > k), default=None)
        ta, ka = (en[lo], lo) if lo is not None else (a0, -1)
        tb, kb = (st[hi], hi) if hi is not None else (b0, n)
        m = kb - ka - 1  # unknown characters between the two anchors share the time between them
        st[k] = ta + (tb - ta) * (k - ka - 1) / m
        en[k] = ta + (tb - ta) * (k - ka) / m
    return st, en


def build(proj, tl, W, H):
    """-> (ASS text, [(start, end, text)] dialogue cues for the SRT)"""
    T = dict(getattr(proj, "TYPO", {}))
    vert = H > W
    u = min(W, H) / 1080
    fsk = T.get("font_scale", 1.45)
    FS = lambda px: round(px * u * fsk)
    font = T.get("font", "Noto Sans TC")
    accent = T.get("accent", "F2C55C")
    maxc = T.get("max_chars", 14 if vert else 22)
    sub_y = T.get("sub_y", 0.74 if vert else 0.92)
    shots = {s["id"]: s for s in proj.SHOTS}
    cast = proj.CAST
    speech = tl["speech"]

    styles = [
        f"Style: Dlg,{font},{FS(T.get('size', 54))},&H00FFFFFF,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,{u:.1f},0,1,"
        f"{3.4 * u:.1f},{1.2 * u:.1f},2,{round(60 * u)},{round(60 * u)},{round(H * (1 - sub_y))},1",
        f"Style: Name,{font},{FS(86)},&H00FFFFFF,&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,{4 * u:.1f},0,1,{3 * u:.1f},{2 * u:.1f},7,0,0,0,1",
        f"Style: Role,{font},{FS(34)},{col(accent)},&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,{3 * u:.1f},0,1,{2.4 * u:.1f},{1.5 * u:.1f},7,0,0,0,1",
        f"Style: Title,{font},{FS(128 if vert else 112)},&H00FFFFFF,&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,{10 * u:.1f},0,1,{4 * u:.1f},{3 * u:.1f},5,0,0,0,1",
        f"Style: Ep,{font},{FS(44)},{col(accent)},&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,{8 * u:.1f},0,1,{2.5 * u:.1f},{1.5 * u:.1f},5,0,0,0,1",
        f"Style: Label,{font},{FS(34)},&H00FFFFFF,&H000000FF,&H60000000,&H60000000,0,0,0,0,100,100,{2 * u:.1f},0,3,{10 * u:.1f},0,7,0,0,0,1",
        f"Style: Chat,{font},{FS(34)},&H00FFFFFF,&H000000FF,&H70000000,&H70000000,0,0,0,0,100,100,{u:.1f},0,3,{8 * u:.1f},0,1,0,0,0,1",
        f"Style: End,{font},{FS(104 if vert else 96)},&H00FFFFFF,&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,{14 * u:.1f},0,1,{4 * u:.1f},{3 * u:.1f},5,0,0,0,1",
        f"Style: Box,{font},10,&H00000000,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
    ]
    ev, cues = [], []
    rect = lambda w, h: f"m 0 0 l {w:.0f} 0 {w:.0f} {h:.0f} 0 {h:.0f}"

    episodes = {}

    def line_of(src):
        """(shot, speech entry) for a row: this episode's shot, for a recap row (../s1e01_x/clips/S2_08) that episode's,
        for an earlier take (clips/_takes/S4_03_v1, an NG reel) shot S4_03 with the take's own timing."""
        if "/" not in src and "\\" not in src:
            return shots.get(src), speech.get(src, {})
        full = os.path.normpath(os.path.join(proj.DIR, src))
        name, folder = os.path.splitext(os.path.basename(full))[0], os.path.dirname(full)
        take = os.path.basename(folder) == "_takes"
        ep = os.path.dirname(os.path.dirname(folder) if take else folder)
        if ep not in episodes:
            ok = os.path.exists(os.path.join(ep, "project.py"))
            other = load_project(ep) if ok else None
            sp_p = os.path.join(ep, "speech.json")
            episodes[ep] = ({s["id"]: s for s in other.SHOTS} if other else {}, jload(sp_p) if os.path.exists(sp_p) else {})
        sid = re.sub(r"_v\d+$", "", name) if take else name
        return episodes[ep][0].get(sid), episodes[ep][1].get(f"_takes/{name}" if take else name, {})

    # dialogue: each base row carries its own clip's line
    for b in tl["base"]:
        s, sp = line_of(b["src"])
        if not s or not s.get("say"):
            continue
        spk, text = s["say"][0], s["say"][1]
        if b["flags"].get("heard") and sp.get("heard"):  # an NG take: subtitle what was actually said (the joke)
            text = re.sub(r"[,;﹐﹑﹔；]+", "，", sp["heard"]).strip("＀ ")  # ASR commas -> full width, so chunks() splits there
        span = sp.get("speech") or [b["inn"], b["inn"] + b["dur"]]
        st, en = char_times(text, sp.get("words") or [], span)
        # a row cut from part of the clip (one line split over two rows) subtitles only the words said in it
        lo, hi = b["inn"] + 0.05, b["inn"] + b["dur"] - 0.05
        k = 0
        for disp, n in chunks(text, maxc):
            keep = [j for j in range(k, k + n) if en[j] > lo and st[j] < hi]
            if keep and len(keep) < n:
                disp = part(disp, keep[0] - k, keep[-1] - k)
            k += n
            if not keep:
                continue
            a, z = st[keep[0]], en[keep[-1]]
            a, z = b["t0"] + a - b["inn"], b["t0"] + z - b["inn"]
            if z <= b["t0"] or a >= b["t2"]:
                continue
            cues.append([max(a, b["t0"]), min(max(z + 0.25, a + 0.7), b["t2"]), disp, spk])
    cues.sort()
    for n in range(len(cues) - 1):
        cues[n][1] = min(cues[n][1], cues[n + 1][0] - 0.02)
    for a, z, disp, spk in cues:
        c = cast.get(spk, {}).get("color")
        tint = "{\\c" + col(c) + "&}" if c else ""
        ev.append(f"Dialogue: 2,{ts(a)},{ts(z)},Dlg,{spk},0,0,0,,{tint}{disp}")

    for b in tl["base"] + tl["over"]:
        f, t0 = b["flags"], b["t0"]
        t_end = b.get("t2", b["t1"])
        if f.get("intro") in cast:  # character intro: accent bar, role line, name sliding in
            c = cast[f["intro"]]
            d = min(T.get("intro_s", 2.4), max(1.5, t_end - t0 - 0.1))
            a, z = t0 + 0.15, t0 + 0.15 + d
            x, y = 70 * u, H * T.get("intro_y", 0.56 if vert else 0.6)
            fad = "\\fad(200,350)"
            ev.append(f"Dialogue: 3,{ts(a)},{ts(z)},Box,,0,0,0,,{{\\an7\\pos({x:.0f},{y:.0f})\\c{col(accent)}{fad}\\p1}}{rect(8 * u, 150 * u)}{{\\p0}}")
            if c.get("title"):
                ev.append(f"Dialogue: 3,{ts(a + 0.1)},{ts(z)},Role,,0,0,0,,{{\\move({x + 40 * u:.0f},{y + 4 * u:.0f},{x + 26 * u:.0f},{y + 4 * u:.0f},0,300){fad}}}{c['title']}")
            ev.append(f"Dialogue: 3,{ts(a)},{ts(z)},Name,,0,0,0,,{{\\move({x - 10 * u:.0f},{y + 46 * u:.0f},{x + 22 * u:.0f},{y + 46 * u:.0f},0,300){fad}}}{c['name']}")
        if f.get("title"):  # series title and episode number over a dark band
            d = min(T.get("title_s", 2.6), t_end - t0)
            y = H * 0.40
            title = getattr(proj, "TITLE", "")
            # a long title shrinks to 90 % of the width (9 CJK characters ran off both sides of a vertical frame)
            em = (128 if vert else 112) + 10
            k = min(100, 100 * 0.9 * W / max(1.0, sum(1 if ord(c) > 0x2E80 else 0.55 for c in title) * em * u))
            ev.append(f"Dialogue: 1,{ts(t0)},{ts(t0 + d)},Box,,0,0,0,,{{\\an7\\pos(0,{y - 140 * u:.0f})\\1a&H70&\\fad(250,400)\\p1}}{rect(W, 300 * u)}{{\\p0}}")
            ev.append(f"Dialogue: 3,{ts(t0)},{ts(t0 + d)},Title,,0,0,0,,{{\\pos({W / 2:.0f},{y - 20 * u:.0f})\\fad(250,400)"
                      f"\\fscx{1.12 * k:.0f}\\fscy{1.12 * k:.0f}\\t(0,400,\\fscx{k:.0f}\\fscy{k:.0f})}}{title}")
            if getattr(proj, "EPISODE", None):
                ev.append(f"Dialogue: 3,{ts(t0 + 0.2)},{ts(t0 + d)},Ep,,0,0,0,,{{\\pos({W / 2:.0f},{y + 95 * u:.0f})\\fad(250,400)}}第 {proj.EPISODE} 集")
        if f.get("label"):
            ev.append(f"Dialogue: 3,{ts(t0)},{ts(b['t1'])},Label,,0,0,0,,{{\\pos({50 * u:.0f},{(150 if vert else 50) * u:.0f})\\fad(150,150)}}{f['label']}")
        if f.get("end"):  # cliffhanger: over the freeze (or the last 1.6 s of the row)
            txt = f["end"] if isinstance(f["end"], str) else T.get("end_text", "未完待續")
            a = b["t1"] if b.get("freeze") else max(t0, b["t1"] - 1.6)
            ev.append(f"Dialogue: 4,{ts(a)},{ts(t_end)},End,,0,0,0,,{{\\pos({W / 2:.0f},{H * 0.42:.0f})\\fad(300,0)\\fscx125\\fscy125\\t(0,350,\\fscx100\\fscy100)}}{txt}")
    chats, keep = getattr(proj, "CHAT", {}), T.get("chat_rows", 5)
    for b in tl["base"]:  # livestream comments: one by one from the bottom, older ones pushed up and out
        lst = chats.get(b["flags"].get("chat"), [])
        t0, t_end = b["t0"], b.get("t2", b["t1"])
        gap = min(0.9, max(0.35, (t_end - t0 - 0.4) / max(1, len(lst))))
        times = [t for t in (t0 + 0.1 + i * gap for i in range(len(lst))) if t < t_end - 0.2]
        x, y0, step = 40 * u, H * T.get("chat_y", 0.66 if vert else 0.8), 64 * u
        for i, t in enumerate(times):
            who, text = lst[i]
            for k in range(min(keep, len(times) - i)):  # k = comments that arrived after this one
                z = times[i + k + 1] if i + k + 1 < len(times) else t_end
                y = y0 - k * step
                # the new one slides up a whole step too, fading in: the stack moves together and never overlaps
                at = f"\\move({x:.0f},{y + step:.0f},{x:.0f},{y:.0f},0,150)" + ("\\fad(150,0)" if k == 0 else "")
                ev.append(f"Dialogue: 2,{ts(times[i + k])},{ts(z)},Chat,,0,0,0,,{{\\an1{at}}}{{\\c{col(accent)}}}{who}：{{\\c&HFFFFFF&}}{text}")
    if T.get("badge"):
        ev.append(f"Dialogue: 1,{ts(0)},{ts(tl['total'])},Label,,0,0,0,,{{\\pos({(W - 50 * u):.0f},{(150 if vert else 50) * u:.0f})\\an9}}{T['badge']}")

    head = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
            "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            *styles, "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    return "\n".join(head + ev) + "\n", [(a, z, d) for a, z, d, _ in cues]


def srt(cues):
    return "\n".join(f"{n}\n{srt_ts(a)} --> {srt_ts(z)}\n{d}\n" for n, (a, z, d) in enumerate(cues, 1))

"""Render an explainer: still pictures with smooth pans and zooms and cross-fades, the narration, subtitles timed to
the voice (pinyin alignment), a music bed from the series' MV (one section per chapter, ducked under the voice),
an MV clip and other covers in a gold frame, a title after the opening and an AI-made end card. No credits.

usage: python explain/render.py PROJECT_DIR [--until TEXT] [--out out/NAME.mp4] [--full-only]
       python explain/render.py PROJECT_DIR --shorts [--layout band|square] [--out out/NAME_shorts.mp4]
  --until TEXT   stop before this sentence (a short test cut); the title and a few seconds of music close it
  (a project with SHORTS gets both cuts from one command: the 16:9 episode, then its vertical Short; the
   workflow switch explain.shorts turns that off (dreamfab/workflow.py), --full-only skips it once)
  --shorts       a vertical 1080x1920 Short cut from the same narration, pictures and music (no credits):
                 SHORTS = dict(clips=[(from words, up to words or None), ...], head=("line", ...), music=second in
                 MUSIC (default: the bed meets the MV clip where the full cut's 結尾 section does), end="closing
                 line", layout="band"). Each clip plays the narration from its first words up to
                 (not including) the second (None: to the end of that part); keep the sum under 60 s (YouTube takes up
                 to 3 minutes, but a Short over 1 minute with any copyright claim is blocked everywhere). head stays at
                 the top, the pictures sit in the middle, subtitles below them, the end line over the last seconds.
  --layout       band: the whole 16:9 picture across the middle on a blurred copy of itself (default);
                 square: a 1:1 cut from the middle of each picture, larger on the phone (keep head to one line).
                 Render both (--layout ... --out ...) and let the user choose before setting SHORTS["layout"]
Needs images/<id>.png|jpg (voice/*.words.json are made on the first run, or by narration.py check), and in project.py:
  NAME, SCRIPT, SHOTS; optional SAY, NARRATION, TITLE, ENDCARD, MUSIC, CH_MUSIC, MUSIC_DB, MV_CLIP, FONT, SUBS, GAPS
SUBS = dict(style=outline | heavy | gold | band, font=a family in FONT's folder, size=58): the subtitle look the user
picked from explain/sub_styles.py (default: outline, FONT's family, 58).
Writes out/NAME.mp4 and out/NAME.<lang>.srt (YouTube indexes uploaded captions for search).
SHOTS = [(image, first words, move, focus)]: the picture comes in when the narration reaches those words (searched in
order). move: in / out (zoom towards / away from focus=(x, y) in 0..1), left / right (pan), frame (whole picture in a
gold frame: covers with lettering), scroll (a long handscroll on a white ground: cut out and panned right to left).
image "MV:12.5" plays MV_CLIP from 12.5 s in the gold frame.
"""
import os, subprocess, sys
import numpy as np
from common import load_project, jload, venc, chapters, written, narration, words_path, transcribe, align, lines, \
    ass_time, sub_styles, sub_events
from dreamfab.workflow import get as workflow

W, H, FPS = 1920, 1080, 30
GOLD_BGR, GOLD_ASS = (96, 200, 232), "&H0060C8E8"


def srt_time(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t % 1 * 1000):03d}"


def music_track(proj, chaps, total, work, start=None):
    """One section of the music per chapter (CH_MUSIC: chapter heading prefix -> second in the file), each levelled to
    MUSIC_DB (RMS, dBFS) and cross-faded into the next a second before the chapter starts. start: one section from
    that second for the whole video (a Short)."""
    src_file = os.path.join(proj.DIR, proj.MUSIC)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src_file, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    mono = np.frombuffer(raw, np.float32)
    starts, target = getattr(proj, "CH_MUSIC", {}), getattr(proj, "MUSIC_DB", -27)
    segs = []
    for k, (t, name) in enumerate(chaps or [(0.0, "")]):
        a = 0.0 if k == 0 else t - 1.0
        b = total if k + 1 >= len(chaps) else chaps[k + 1][0] - 1.0
        src = start if start is not None else next((s for key, s in starts.items() if name.startswith(key)), 0.0)
        dur = b - a + 2.0
        x = mono[int(src * 8000): int((src + dur) * 8000)]
        rms = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else target
        segs.append((src, dur, float(np.clip(target - rms, -12, 10))))
    cmd, fl = ["ffmpeg", "-v", "error", "-y"], []
    for k, (src, dur, g) in enumerate(segs):
        cmd += ["-ss", f"{src:.3f}", "-t", f"{dur:.3f}", "-i", src_file]
        fl.append(f"[{k}:a]aresample=48000,volume={g:.1f}dB[s{k}]")
    cur = "[s0]"
    for k in range(1, len(segs)):
        fl.append(f"{cur}[s{k}]acrossfade=d=2.0:c1=tri:c2=tri[x{k}]"); cur = f"[x{k}]"
    fl.append(f"{cur}apad,atrim=0:{total:.3f},afade=t=in:d=1.2,afade=t=out:st={total - 3:.3f}:d=3[m]")
    out = os.path.join(work, "music.wav")
    subprocess.run(cmd + ["-filter_complex", ";".join(fl), "-map", "[m]", out], check=True)
    return out


def build():
    import cv2
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    proj = load_project(sys.argv[1])
    D, args = proj.DIR, sys.argv[2:]
    until = args[args.index("--until") + 1] if "--until" in args else None
    S = getattr(proj, "SHORTS", None) if "--shorts" in args else None
    if "--shorts" in args and not S:
        sys.exit("--shorts needs SHORTS = dict(clips=[...], ...) in project.py")
    suffix = getattr(proj, "EDITS", {}).get("shorts", {}).get("suffix", "_shorts") if S else ""
    out = os.path.join(D, args[args.index("--out") + 1] if "--out" in args else f"out/{proj.NAME}{suffix}.mp4")
    work = os.path.join(D, "out", "_work_shorts" if S else "_work"); os.makedirs(work, exist_ok=True)
    gaps = dict(dict(lead=1.6, chapter=1.4, title=3.4, part=0.4, end=5.5, xfade=0.9), **getattr(proj, "GAPS", {}))
    if S:   # a Short starts on the first word, cuts tight and ends on its closing line
        gaps.update(lead=0.3, part=0.45, end=3.0, xfade=0.6)
    LEAD, XF = gaps["lead"], gaps["xfade"]
    title, endcard = getattr(proj, "TITLE", None), getattr(proj, "ENDCARD", "")
    font, fonts = getattr(proj, "FONT", ("Explainer Serif", "fonts"))
    fonts = next((p for p in (os.path.join(D, fonts), os.path.join(D, "..", fonts)) if os.path.isdir(p)), os.path.join(D, fonts))
    lang = getattr(proj, "RENDER", {}).get("lang", "zh-TW")
    sub = dict(dict(style="outline", font=font, size=58), **getattr(proj, "SUBS", {}))
    OW, OH = (1080, 1920) if S else (W, H)   # the output; pictures are still drawn 16:9 (W x H) and set into it
    if S:
        layout = args[args.index("--layout") + 1] if "--layout" in args else \
            S.get("layout") or workflow("explain.shorts_layout", D)
        if layout not in ("band", "square"):
            sys.exit("--layout is band or square")
        pic_h = OW if layout == "square" else OW * H // W        # the picture across the middle of the phone
        pic_y = 380 if layout == "square" else 520
        # subtitles under the picture (band) or over its lower edge (square), above the Shorts title and buttons that
        # cover the bottom fifth of the screen; heavy edges keep them readable on either
        sub = dict(sub, style="heavy", size=S.get("sub_size", 68), side=70, margin=OH - (1430 if layout == "square" else 1330))

    # narration: each part's spoken text -> subtitle text and a time for every character; cut into one piece per
    # chapter and laid on the timeline with a breath between chapters (and the title after the first one)
    heads = [(h, t[:8]) for h, t in chapters(proj)]
    parts, items = [], narration(proj)
    missing = [it["audio"] for it in items if not os.path.exists(words_path(it["audio"]))]
    if missing:   # a freshly cut or re-read file: time its words first
        transcribe(missing)
    for it in items:
        w = jload(words_path(it["audio"]))
        ct, _ = align(it["text"], w["words"])
        parts.append(dict(path=it["audio"], text=written(it["text"], proj), ct=ct, dur=w["duration"]))
    pieces = []   # (part, first char, end char, from s in the file, to s in the file, chapter heading or None)
    nh = 0        # chapters come in order: look only for the next heading, after the last one (an opening quote can recur)
    for pi, p in enumerate(parts):
        text, ct = p["text"], p["ct"]
        starts, at = [], 0
        while nh < len(heads) and heads[nh][1] in text[at:]:
            at = text.index(heads[nh][1], at)
            starts.append((at, heads[nh][0])); nh += 1; at += 1
        if not starts or starts[0][0] > 0:
            starts = [(0, None)] + starts
        stop = text.index(until) if until and until in text else len(text)
        for k, (a, name) in enumerate(starts):
            b = starts[k + 1][0] if k + 1 < len(starts) else len(text)
            if a >= stop:
                break
            b = min(b, stop)
            first = next(ct[i] for i in range(a, b) if ct[i])[0]
            last = next(ct[i] for i in range(b - 1, a - 1, -1) if ct[i])[1]
            fa = 0.0 if a == 0 else (first + next(ct[i] for i in range(a - 1, -1, -1) if ct[i])[1]) / 2
            fb = p["dur"] if b == len(text) else (last + next(ct[i] for i in range(b, len(text)) if ct[i])[0]) / 2
            pieces.append((pi, a, b, fa, fb, name))
        if stop < len(text):
            break
    if S:   # a Short plays the clips, not whole chapters
        pieces = []
        for frm, to in S["clips"]:
            pi = next((k for k, p in enumerate(parts) if frm in p["text"]), None)
            if pi is None:
                sys.exit(f"SHORTS clip {frm!r} is not in the narration")
            text, ct = parts[pi]["text"], parts[pi]["ct"]
            a = text.index(frm)
            if to and to not in text[a:]:
                sys.exit(f"SHORTS clip {frm!r}: {to!r} does not come after it in the same part")
            b = text.index(to, a) if to else len(text)
            first = next(ct[i] for i in range(a, b) if ct[i])[0]
            last = next(ct[i] for i in range(b - 1, a - 1, -1) if ct[i])[1]
            prev = next((ct[i][1] for i in range(a - 1, -1, -1) if ct[i]), None)
            nxt = next((ct[i][0] for i in range(b, len(text)) if ct[i]), None)
            fa = 0.0 if prev is None else (first + prev) / 2
            fb = parts[pi]["dur"] if nxt is None else (last + nxt) / 2
            pieces.append((pi, a, b, fa, fb, None))
    first_head = heads[0][0] if heads else None
    t, place, chaps = LEAD, [], []
    for k, (pi, a, b, fa, fb, name) in enumerate(pieces):
        if name:
            chaps.append((t + parts[pi]["ct"][next(i for i in range(a, b) if parts[pi]["ct"][i])][0] - fa, name))
        place.append(t - fa)
        t += fb - fa
        if k + 1 < len(pieces):
            nxt = pieces[k + 1][5]
            t += (gaps["title"] if title and name == first_head else gaps["chapter"]) if nxt else gaps["part"]
    narr_end = t
    total = narr_end + (3.2 if until else gaps["end"])

    def when(pi, i):   # seconds into the video of character i of part pi
        k = next(k for k, pc in enumerate(pieces) if pc[0] == pi and pc[1] <= i < pc[2])
        return place[k] + parts[pi]["ct"][i][0], place[k] + parts[pi]["ct"][i][1]

    subs = []
    if S:   # each clip on its own, in lines narrow enough for a phone
        for pi, a, b, *_ in pieces:
            for x, y, shown in lines(parts[pi]["text"][a:b], width=12):
                ts = [when(pi, i) for i in range(a + x, a + y) if parts[pi]["ct"][i]]
                subs.append((ts[0][0], ts[-1][1], shown))
    for pi, p in enumerate(parts if not S else []):
        lim = max([pc[2] for pc in pieces if pc[0] == pi], default=0)
        for a, b, shown in lines(p["text"][:lim]):
            ts = [when(pi, i) for i in range(a, b) if p["ct"][i]]
            subs.append((ts[0][0], ts[-1][1], shown))
    for i, (a, b, s) in enumerate(subs):   # hold each line a little, never into the next one
        nxt = subs[i + 1][0] if i + 1 < len(subs) else total
        subs[i] = (a - 0.05, min(max(b + 0.35, a + 1.0), nxt - 0.02), s)

    # pictures: each comes in where the narration reaches its first words
    gtext = "".join(p["text"] + "\u0000" for p in parts)
    offs = np.cumsum([0] + [len(p["text"]) + 1 for p in parts])
    shots, starts, pos = [], [], 0
    for img, phrase, mv, focus in proj.SHOTS:
        if phrase is None:
            shots.append((img, mv, focus)); starts.append(0.0); continue
        g = gtext.find(phrase, pos)
        if g < 0:
            print(f"  shot {img}: {phrase!r} is not in the narration (or comes before the previous shot's words)"); continue
        pi = int(np.searchsorted(offs, g, side="right") - 1); i = g - offs[pi]
        if not any(pc[0] == pi and pc[1] <= i < pc[2] for pc in pieces):
            continue
        i = next(j for j in range(i, len(parts[pi]["text"])) if parts[pi]["ct"][j])
        shots.append((img, mv, focus)); starts.append(when(pi, i)[0] - 0.15); pos = g + len(phrase)
    if S:   # a clip can start in the middle of a shot: the picture that is up there comes in with the clip
        found, pos = [], 0
        for img, phrase, mv, focus in proj.SHOTS:
            g = 0 if phrase is None else gtext.find(phrase, pos)
            if g >= 0:
                found.append((g, img, mv, focus)); pos = g + len(phrase or "")
        shots, starts = [], []
        for k, (pi, a, b, fa, fb, _) in enumerate(pieces):
            ga, gb = offs[pi] + a, offs[pi] + b
            inside = [s for s in found if ga <= s[0] < gb]
            before = [s for s in found if s[0] < ga]
            if before and not (inside and inside[0][0] - ga < 4) and (not shots or shots[-1][0] != before[-1][1]):
                shots.append(before[-1][1:]); starts.append(place[k] + fa)
            for g, img, mv, focus in inside:
                i = next(j for j in range(g - offs[pi], b) if parts[pi]["ct"][j])
                shots.append((img, mv, focus)); starts.append(max(place[k] + fa, when(pi, i)[0] - 0.15))
        if shots:
            starts[0] = 0.0
    if not shots:
        sys.exit("no SHOTS")

    # subtitles, chapter labels, title, end card
    ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {OW}", f"PlayResY: {OH}", "WrapStyle: 2", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
           "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           *sub_styles(sub),
           f"Style: Chap,{font},36,{GOLD_ASS},&H000000FF,&H60101010,&H90000000,0,0,0,0,100,100,4,0,1,1.6,1.2,7,90,90,64,1",
           f"Style: Title,{font},120,{GOLD_ASS},&H000000FF,&H40101010,&HA0000000,0,0,0,0,100,100,12,0,1,3.2,2.5,5,0,0,0,1",
           f"Style: TitleSub,{font},46,&H00FFFFFF,&H000000FF,&H50101010,&H90000000,0,0,0,0,100,100,6,0,1,2,1.5,5,0,0,0,1",
           f"Style: Head,{font},84,{GOLD_ASS},&H000000FF,&H30101010,&H90000000,0,0,0,0,100,100,6,0,1,3.4,2.4,8,60,60,0,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    if S:   # a line too wide for the phone breaks in two, at a comma near its middle if there is one
        def fit(s, n=13):
            if len(s) <= n:
                return s
            cut = min((k + 1 for k, c in enumerate(s) if c in "，、：" and 3 < k < len(s) - 3),
                      key=lambda k: abs(k - len(s) / 2), default=(len(s) + 1) // 2)
            return s[:cut] + "\\N" + s[cut:]
        ass += sub_events(sub, [(a, b, fit(s)) for a, b, s in subs], OW, OH)
        head = "\\N".join(S.get("head", title or ()))
        if head:
            ass.append(f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Head,,0,0,0,,{{\\fad(300,600)\\an8\\pos({OW // 2},"
                       f"{230 if layout == 'square' else 250})}}{head}")
    else:
        ass += sub_events(sub, subs, W, H)
    for t0, name in chaps:
        st = 0.5 if t0 < LEAD + 1 else t0 - 0.2
        ass.append(f"Dialogue: 0,{ass_time(st)},{ass_time(st + 4.5)},Chap,,0,0,0,,{{\\fad(400,500)}}{name}")
    op = next((k for k, pc in enumerate(pieces) if pc[5] and pc[5] == first_head), None)
    if title and op is not None:   # the opening is over: the title comes up
        ts = place[op] + pieces[op][4] + 0.2
        te = (narr_end + 3.0) if op + 1 == len(pieces) else ts + gaps["title"] + 0.6
        ass.append(f"Dialogue: 1,{ass_time(ts)},{ass_time(te)},Title,,0,0,0,,{{\\fad(500,400)\\pos(960,500)}}{title[0]}")
        if len(title) > 1:
            ass.append(f"Dialogue: 1,{ass_time(ts + 0.3)},{ass_time(te)},TitleSub,,0,0,0,,{{\\fad(500,400)\\pos(960,620)}}{title[1]}")
    if S and S.get("end"):   # the closing line over the picture, then the AI note under it
        y = pic_y + pic_h // 2
        ass.append(f"Dialogue: 3,{ass_time(narr_end + 0.2)},{ass_time(total - 0.1)},Head,,0,0,0,,{{\\fad(400,300)\\an5"
                   f"\\fs74\\pos({OW // 2},{y})}}{S['end']}")
        if endcard:
            ass.append(f"Dialogue: 3,{ass_time(narr_end + 0.5)},{ass_time(total - 0.1)},TitleSub,,0,0,0,,{{\\fad(400,300)"
                       f"\\an5\\fs36\\pos({OW // 2},{y + 90})}}{endcard}")
    elif endcard and not until:
        ass.append(f"Dialogue: 1,{ass_time(narr_end + 1.3)},{ass_time(total - 0.2)},TitleSub,,0,0,0,,{{\\fad(600,400)\\fs54\\pos(960,1000)}}{endcard}")
    subp = os.path.join(work, "subs.ass")
    open(subp, "w", encoding="utf-8-sig").write("\n".join(ass) + "\n")

    # sound: the narration pieces in place, the music ducked under them (sidechain)
    cmd, fl, labels = ["ffmpeg", "-v", "error", "-y"], [], []
    for k, (pi, a, b, fa, fb, name) in enumerate(pieces):
        cmd += ["-ss", f"{fa:.3f}", "-t", f"{fb - fa:.3f}", "-i", parts[pi]["path"]]
        fl.append(f"[{k}:a]aresample=48000,afade=t=in:d=0.03,afade=t=out:st={fb - fa - 0.06:.3f}:d=0.06,"
                  f"adelay={int((place[k] + fa) * 1000)}:all=1[n{k}]")
        labels.append(f"[n{k}]")
    n = len(pieces)
    fl.append(f"{''.join(labels)}amix=inputs={n}:normalize=0,apad=whole_dur={total:.3f},atrim=0:{total:.3f},"
              f"loudnorm=I=-16:TP=-2:LRA=9" + (",asplit[v][key]" if getattr(proj, "MUSIC", None) else ",alimiter=limit=0.93[a]"))
    if getattr(proj, "MUSIC", None):
        start = None
        if S:   # by default the bed reaches the MV clip where the full cut's 結尾 section does (in time with the MV)
            mv = next((k for k, s in enumerate(shots) if s[0].startswith("MV:")), None)
            end_src = next((s for key, s in getattr(proj, "CH_MUSIC", {}).items() if key == "結尾"), None)
            auto = end_src + 0.85 - starts[mv] if mv is not None and end_src is not None else 0.0
            start = S.get("music", max(0.0, auto))
        cmd += ["-i", music_track(proj, chaps, total, work, start=start)]
        fl.append(f"[{n}:a]anull[m]")
        fl.append("[m][key]sidechaincompress=threshold=0.03:ratio=5:attack=60:release=700:makeup=1[md]")
        fl.append("[v][md]amix=inputs=2:normalize=0,alimiter=limit=0.93[a]")
    wav = os.path.join(work, "mix.wav")
    subprocess.run(cmd + ["-filter_complex", ";".join(fl), "-map", "[a]", "-ac", "2", wav], check=True)

    # pictures: sub-pixel pans and zooms (no jitter), cross-fades, fade in from and out to black
    ends = starts[1:] + [total]
    xf = [min(XF, 0.45 * (ends[i - 1] - starts[i - 1]), 0.45 * (ends[i] - starts[i])) if i else 0 for i in range(len(starts))]
    spans = [(max(0, starts[i] - xf[i] / 2), (starts[i + 1] + xf[i + 1] / 2) if i + 1 < len(starts) else total)
             for i in range(len(starts))]
    cache, clips, strips = {}, {}, {}
    yy, xx = np.mgrid[0:H, 0:W]
    vign = 1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    navy = (np.dstack([np.full((H, W), 40.0), np.full((H, W), 24.0), np.full((H, W), 14.0)]) * vign[..., None]).astype(np.uint8)

    def img(name):
        if name not in cache:
            p = next((os.path.join(D, "images", name + e) for e in (".png", ".jpg", ".jpeg", ".webp")
                      if os.path.exists(os.path.join(D, "images", name + e))), None)
            if not p:
                sys.exit(f"no images/{name}.png")
            cache[name] = cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)
        return cache[name]

    def framed(f):
        """A frame inside a gold border (room for subtitles below) on a blurred, darkened copy of itself. A Short sets
        every picture into its own frame (vertical below), so a cover or the MV fills it there."""
        if S:
            return f
        bg = cv2.GaussianBlur(cv2.resize(f, (W // 8, H // 8)), (0, 0), 3)
        bg = (cv2.resize(bg, (W, H)).astype(np.float32) * 0.35).astype(np.uint8)
        s = 0.74; w, h = int(W * s), int(H * s); x, y = (W - w) // 2, int(H * 0.06)
        cv2.rectangle(bg, (x - 4, y - 4), (x + w + 3, y + h + 3), GOLD_BGR, 2, cv2.LINE_AA)
        bg[y:y + h, x:x + w] = cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA)
        return bg

    class Clip:
        """MV_CLIP decoded in order from a start second."""
        def __init__(self, src, dur):
            self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{src:.3f}", "-t", f"{dur + 1:.3f}",
                                       "-i", os.path.join(D, proj.MV_CLIP), "-vf", f"fps={FPS},scale={W}:{H}",
                                       "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
            self.n, self.last = -1, np.zeros((H, W, 3), np.uint8)

        def frame(self, k):
            while self.n < k:
                b = self.p.stdout.read(W * H * 3)
                if len(b) < W * H * 3:
                    break
                self.last = np.frombuffer(b, np.uint8).reshape(H, W, 3); self.n += 1
            return framed(self.last)

    def strip(name):
        """A handscroll drawn as a thin strip on white: cut it out, 430 px high, for the scroll move."""
        if name not in strips:
            im = img(name); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) < 200
            rows = np.where(g.mean(1) > 0.5)[0]; cols = np.where(g[rows[0]:rows[-1] + 1].mean(0) > 0.5)[0]
            cut = im[rows[0] + 3:rows[-1] - 2, cols[0] + 3:cols[-1] - 2]
            strips[name] = cv2.resize(cut, (int(cut.shape[1] * 430 / cut.shape[0]), 430), interpolation=cv2.INTER_LANCZOS4)
        return strips[name]

    def view(i, t):
        name, mv, focus = shots[i]
        a, b = spans[i]
        if name.startswith("MV:"):
            if i not in clips:
                clips[i] = Clip(float(name[3:]), b - a)
            return clips[i].frame(int((t - a) * FPS))
        u = min(1, max(0, (t - a) / (b - a)))
        u = 0.75 * u + 0.25 * (0.5 - 0.5 * np.cos(np.pi * u))   # mostly linear: the camera never stops
        fx, fy = focus or (0.5, 0.5)
        if mv == "frame":
            return framed(cv2.resize(img(name), (W, H), interpolation=cv2.INTER_LANCZOS4))
        if mv == "scroll":   # read right to left, the way a Chinese handscroll unrolls
            st = strip(name); vw = int(W * 0.88)
            x0 = (1 - u) * max(0, st.shape[1] - vw)
            win = cv2.warpAffine(st, np.float32([[1, 0, -x0], [0, 1, 0]]), (vw, st.shape[0]), flags=cv2.INTER_LINEAR)
            fr = navy.copy(); y = (H - st.shape[0]) // 2 - 50; x = (W - vw) // 2
            cv2.rectangle(fr, (x - 3, y - 3), (x + vw + 2, y + st.shape[0] + 2), GOLD_BGR, 1, cv2.LINE_AA)
            fr[y:y + st.shape[0], x:x + vw] = win
            return fr
        if mv == "in":
            z = 1.0 + 0.16 * u; cx, cy = 0.5 + (fx - 0.5) * u, 0.5 + (fy - 0.5) * u
        elif mv == "out":
            z = 1.16 - 0.16 * u; cx, cy = fx + (0.5 - fx) * u, fy + (0.5 - fy) * u
        else:
            z = 1.14; d = (1 - 1 / z) / 2 * 0.9; sgn = 1 if mv == "right" else -1
            cx, cy = 0.5 + sgn * d * (2 * u - 1), 0.5
        h = 0.5 / z; cx = min(max(cx, h), 1 - h); cy = min(max(cy, h), 1 - h)
        im = img(name); sh, sw = im.shape[:2]
        sx = W / (sw / z); sy = H / (sh / z)
        M = np.float32([[sx, 0, W / 2 - sx * cx * sw], [0, sy, H / 2 - sy * cy * sh]])
        return cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)

    def vertical(fr):
        """A Short's frame: the 16:9 picture (or its middle square) across the phone, gold rules above and below, on a
        blurred, darkened copy of itself that fills the rest."""
        bw = OH * W // H
        bg = cv2.GaussianBlur(cv2.resize(fr, (W // 12, H // 12), interpolation=cv2.INTER_AREA), (0, 0), 2.5)
        bg = cv2.resize(bg, (bw, OH))[:, (bw - OW) // 2:(bw - OW) // 2 + OW] * 0.38
        pic = fr[:, (W - H) // 2:(W + H) // 2] if layout == "square" else fr
        bg[pic_y:pic_y + pic_h] = cv2.resize(pic, (OW, pic_h), interpolation=cv2.INTER_AREA)
        bg[pic_y - 3:pic_y - 1] = GOLD_BGR
        bg[pic_y + pic_h + 1:pic_y + pic_h + 3] = GOLD_BGR
        return bg

    card = (S.get("end") if S else endcard) and not until
    esc = lambda p: os.path.abspath(p).replace("\\", "/").replace(":", "\\:")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS),
                            "-i", "-", "-i", wav, "-vf", f"subtitles='{esc(subp)}':fontsdir='{esc(fonts)}'",
                            *venc("final"), "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    for f in range(int(round(total * FPS))):
        t = f / FPS
        live = [i for i, (a, b) in enumerate(spans) if a <= t < b] or [len(spans) - 1]
        fr = view(live[0], t).astype(np.float32)
        if len(live) > 1:
            a = min(1, max(0, (t - spans[live[1]][0]) / max(xf[live[1]], 1e-3)))
            fr = fr * (1 - a) + view(live[1], t).astype(np.float32) * a
        if S:
            fr = vertical(fr)
        g = min(1, t / 0.8, (total - t) / 1.2) if not S else min(1, t / 0.25, (total - t) / 0.8)
        if card:
            g *= 1 - 0.6 * min(1, max(0, (t - narr_end - (0.0 if S else 0.8)) / (0.5 if S else 1.0)))   # darken under the end card
        enc.stdin.write(np.clip(fr * g, 0, 255).astype(np.uint8).tobytes())
        if f % (FPS * 30) == 0:
            print(f"  {t:.0f}/{total:.0f} s", flush=True)
    enc.stdin.close(); enc.wait()
    for c in clips.values():
        c.p.kill()
    srt = os.path.splitext(out)[0] + f".{lang}.srt"
    open(srt, "w", encoding="utf-8").write("".join(f"{k + 1}\n{srt_time(a)} --> {srt_time(b)}\n{s}\n\n" for k, (a, b, s) in enumerate(subs)))
    print(f"{os.path.relpath(out, D)}  {total:.1f} s, {len(subs)} subtitle lines, {len(shots)} pictures, chapters at "
          + ", ".join(f"{int(t0 // 60)}:{int(t0 % 60):02d}" if k else "0:00" for k, (t0, _) in enumerate(chaps)))   # YouTube wants 0:00 first


if __name__ == "__main__":
    build()
    a = sys.argv[2:]
    if not any(x in a for x in ("--shorts", "--until", "--out", "--full-only")) \
            and getattr(load_project(sys.argv[1]), "SHORTS", None) and workflow("explain.shorts", sys.argv[1]):
        sys.argv.append("--shorts")
        build()

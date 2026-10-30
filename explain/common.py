"""Shared bits of the explain line (說・解說影片): the script, spoken vs written text, and pinyin alignment.

An explainer is one folder with a project.py (see docs/en/explain/OVERVIEW.md) and a script in Markdown whose
narration section holds one "### chapter" heading per chapter:

    ## Narration            (or: ## 旁白)
    ### Opening | A line
    First paragraph...
    ### 1. Next chapter
    ...
    ## Images               (any next "## " heading ends the narration)
"""
import glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run as a script: the repo root
from dreamfab.util import load_project, P, jload, jdump, run, venc, estimate, off_peak  # noqa: F401

PUNCT = "，。、：；？！「」『』〈〉《》（）—…·,.:;?!()\"' \n"


def chapters(proj):
    """[(heading, text)] of the narration in proj.SCRIPT; paragraphs joined by a blank line."""
    md = open(os.path.join(proj.DIR, getattr(proj, "SCRIPT", "script.md")), encoding="utf-8").read()
    m = re.search(r"^## *(?:旁白|Narration)\b.*$", md, flags=re.M)
    if not m:
        sys.exit(f"{proj.SCRIPT}: no '## Narration' (or '## 旁白') section")
    body = md[m.end():]
    body = body[:re.search(r"^## ", body, flags=re.M).start()] if re.search(r"^## ", body, flags=re.M) else body
    parts = re.split(r"^### *(.+?)\s*$", body, flags=re.M)[1:]
    return [(h, "\n\n".join(p.strip() for p in s.strip().split("\n\n") if p.strip())) for h, s in zip(parts[::2], parts[1::2])]


def spoken(text, proj):
    """What the voice reads: SAY swaps rare characters for same-sounding common ones (宓妃 -> 伏妃) so the voice model
    does not misread them. Each pair has the same length, so subtitles and timings map one to one."""
    for written, said in getattr(proj, "SAY", []):
        assert len(written) == len(said), f"SAY {written}->{said}: both sides must be the same length"
        text = text.replace(written, said)
    return text


def written(text, proj):
    """The subtitle text for spoken text (SAY undone)."""
    for w, said in getattr(proj, "SAY", []):
        text = text.replace(said, w)
    return text


def find_job(proj, jid):
    """The job with this id in any jobs/*.json of the project."""
    for f in sorted(glob.glob(os.path.join(proj.DIR, "jobs", "*.json"))):
        for j in jload(f):
            if j.get("id") == jid:
                return j
    sys.exit(f"no job {jid!r} in {proj.DIR}/jobs/*.json")


def narration(proj):
    """What render.py plays, in order: [dict(audio, text, stop_at)]. proj.NARRATION lists them when a part was cut
    or patched; otherwise every /voice/clone job in jobs/voice_jobs.json, in order."""
    items = getattr(proj, "NARRATION", None)
    if items is None:
        jobs = [j for j in jload(os.path.join(proj.DIR, "jobs", "voice_jobs.json")) if j["endpoint"] == "/voice/clone"]
        items = [dict(audio=os.path.relpath(j["out"], proj.DIR), job=j["id"]) for j in jobs]
    out = []
    for it in items:
        text = it.get("text") or find_job(proj, it["job"])["fields"]["text"]
        if it.get("stop_at"):
            text = text[:text.index(it["stop_at"])].rstrip()
        out.append(dict(audio=os.path.join(proj.DIR, it["audio"]), text=text))
    return out


def words_path(audio):
    return os.path.splitext(audio)[0] + ".words.json"


def transcribe(paths, model="medium"):
    """Word timings from faster-whisper, cached next to each audio file as <name>.words.json."""
    import numpy as np, site, subprocess
    for d in glob.glob(os.path.join(site.getsitepackages()[-1], "nvidia", "*", "bin")):   # CUDA DLLs on Windows
        os.add_dll_directory(d); os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
    from faster_whisper import WhisperModel
    try:
        m = WhisperModel(model, device="cuda", compute_type="int8_float16")
    except Exception:
        m = WhisperModel(model, device="cpu", compute_type="int8")
    for path in paths:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        segs, _ = m.transcribe(a, language="zh", word_timestamps=True, condition_on_previous_text=False)
        words = [(w.word.strip(), round(w.start, 3), round(w.end, 3)) for s in segs for w in s.words if w.word.strip()]
        jdump(dict(duration=len(a) / 16000, words=words), words_path(path))
        print(f"  {os.path.basename(words_path(path))}: {len(words)} words, {len(a) / 16000:.1f} s")


def key(ch):
    from pypinyin import lazy_pinyin
    return lazy_pinyin(ch)[0] if "一" <= ch <= "鿿" or ch == "〇" else ch.lower()


def align(text, words):
    """(start, end) seconds for every character of the spoken text (None for punctuation), and the matching blocks.
    Text and transcript are compared by pinyin, so homophones the recogniser wrote differently (and the SAY swaps)
    still line up; characters it missed are interpolated between their neighbours."""
    from difflib import SequenceMatcher
    digits = dict(zip("0123456789", "零一二三四五六七八九"))
    au, at, ac = [], [], []
    for w, s, e in words:
        cs = [digits.get(c, c) for c in w if c not in PUNCT and not c.isspace()]
        for k, c in enumerate(cs):
            au.append(key(c)); ac.append(c); at.append((s + (e - s) * k / len(cs), s + (e - s) * (k + 1) / len(cs)))
    idx = [i for i, c in enumerate(text) if c not in PUNCT]
    t = [None] * len(idx)
    blocks = SequenceMatcher(None, [key(text[i]) for i in idx], au, autojunk=False).get_matching_blocks()
    for a, b, n in blocks:
        for j in range(n):
            t[a + j] = at[b + j]
    known = [j for j, v in enumerate(t) if v]
    if not known:
        sys.exit("the transcript does not match the text at all (wrong audio file?)")
    for j in range(len(t)):
        if t[j] is None:
            p = max([k for k in known if k < j], default=None); q = min([k for k in known if k > j], default=None)
            if p is None or q is None:
                t[j] = t[p if p is not None else q]
            else:
                x = t[p][1] + (t[q][0] - t[p][1]) * (j - p) / (q - p); t[j] = (x, x)
    out = [None] * len(text)
    for j, i in enumerate(idx):
        out[i] = t[j]
    return out, dict(idx=idx, asr=ac, asr_t=at, blocks=blocks)


def lines(text, width=20):
    """Subtitle lines as (first char, end char, shown text): a line per sentence, a long one split at the comma
    nearest its middle; trailing punctuation is dropped and a short tail after a colon stays on its line."""
    out, a, i = [], 0, 0
    while i < len(text):
        if text[i] in "。？！；：\n":
            while i + 1 < len(text) and text[i + 1] in "」』〉》":
                i += 1
            out.append((a, i + 1)); a = i + 1
        i += 1
    if a < len(text):
        out.append((a, len(text)))
    res = []
    for a, b in out:
        s = text[a:b]
        if not s.strip():
            continue
        segs = [(a, b)]
        if len(s.strip()) > width:
            cuts = [a + k + 1 for k, c in enumerate(s) if c in "，、" and 6 < k < len(s) - 5]
            if cuts:
                m = min(cuts, key=lambda x: abs(x - (a + b) / 2)); segs = [(a, m), (m, b)]
        for x, y in segs:
            shown = text[x:y].strip().rstrip("，。、；：").strip()
            if not shown:
                continue
            if res and len(shown) <= 4 and len(res[-1][2]) + len(shown) <= width + 4 and text[res[-1][1] - 1] == "：":
                res[-1] = (res[-1][0], y, res[-1][2] + "：" + shown)
            else:
                res.append((x, y, shown))
    return res

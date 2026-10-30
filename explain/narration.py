"""Narration for an explainer: voice-clone jobs from the script, then a check of what came back.

usage: python explain/narration.py PROJECT_DIR jobs [--max 1100]   jobs/voice_jobs.json: the narration in parts of at most
                                                                  --max characters, split between chapters (the API takes
                                                                  1,200), SAY applied, read in proj.VOICE
       python explain/narration.py PROJECT_DIR check [AUDIO ...]  transcribe (cached in voice/*.words.json) and report
                                                                  speed, words to listen to, a missing ending, or a voice
                                                                  that runs on and repeats itself after the text ends
       python explain/narration.py PROJECT_DIR cut AUDIO SECONDS  keep the first SECONDS (short fade) -> <name>_cut.flac
Submit with: python dreamfab/aip_runner.py PROJECT_DIR/jobs/voice_jobs.json [--off-peak]
"""
import os, subprocess, sys
from common import load_project, P, jload, jdump, estimate, off_peak, chapters, spoken, narration, words_path, transcribe, align, PUNCT

if len(sys.argv) < 3 or sys.argv[2] not in ("jobs", "check", "cut"):
    sys.exit(__doc__)
proj = load_project(sys.argv[1])
D, cmd, args = proj.DIR, sys.argv[2], sys.argv[3:]


def alike(said, heard):
    """Same length and every character shares a reading (著/着, 長/常): a polyphone, not a misread."""
    from pypinyin import pinyin, Style
    reads = lambda c: set(pinyin(c, style=Style.NORMAL, heteronym=True)[0])
    return len(said) == len(heard) and all(reads(x) & reads(y) for x, y in zip(said, heard))


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


if cmd == "jobs":
    limit = int(args[args.index("--max") + 1]) if "--max" in args else 1100
    voice = os.path.join(D, proj.VOICE)
    if not os.path.exists(voice):
        sys.exit(f"no voice sample {voice} (proj.VOICE)")
    parts, cur = [], []
    for head, text in chapters(proj):
        if cur and len("\n\n".join(cur + [text])) > limit:
            parts.append(cur); cur = []
        if len(text) > limit:
            sys.exit(f"chapter {head!r} is {len(text)} characters: split it (the voice API takes {limit} here)")
        cur.append(text)
    parts.append(cur)
    jobs = [dict(id=f"part{k + 1}", endpoint="/voice/clone", fields=dict(text=spoken("\n\n".join(p), proj)),
                 files=dict(reference_audio=P(voice)), out=P(D, "voice", f"part{k + 1}.flac")) for k, p in enumerate(parts)]
    jdump(jobs, os.path.join(D, "jobs", "voice_jobs.json"))
    full = sum(estimate(j) for j in jobs)
    for j in jobs:
        print(f"  {j['id']}: {len(j['fields']['text'])} characters")
    print(f"{len(jobs)} parts -> jobs/voice_jobs.json  ({full} credits now, {sum(off_peak(estimate(j)) for j in jobs)} off-peak)")

elif cmd == "check":
    items = narration(proj)
    if args:
        want = {os.path.abspath(os.path.join(D, a)) for a in args}
        items = [it for it in items if os.path.abspath(it["audio"]) in want]
    todo = [it["audio"] for it in items if os.path.exists(it["audio"]) and not os.path.exists(words_path(it["audio"]))]
    if todo:
        transcribe(todo)
    for it in items:
        if not os.path.exists(it["audio"]):
            print(f"{os.path.relpath(it['audio'], D)}: not there yet"); continue
        w = jload(words_path(it["audio"]))
        text, words, dur = it["text"], w["words"], w["duration"]
        ct, info = align(text, words)
        n = len(info["idx"])
        hit = sum(b[2] for b in info["blocks"])
        print(f"{os.path.relpath(it['audio'], D)}: {dur:.1f} s, {n / dur:.1f} characters/s, {hit / n:.0%} heard as written")
        last_a = max((a + k for a, b, k in info["blocks"] if k), default=0)   # last text character the transcript matched
        last_b = max((b + k for a, b, k in info["blocks"] if k), default=0)
        if n - last_a > 6:
            print(f"  !! the last {n - last_a} characters were not heard: the voice stopped early (re-read the ending)")
        extra = len(info["asr"]) - last_b
        if extra > 8:
            t = info["asr_t"][last_b][0]
            print(f"  !! {extra} more characters after the text ends, from {mmss(t)}: the voice repeats itself."
                  f" Keep what is before it: narration.py {sys.argv[1]} cut {os.path.relpath(it['audio'], D)} SECONDS")
        prev = (0, 0)
        for a, b, k in info["blocks"]:   # gaps between matches: words to listen to
            ta, tb = prev
            if a - ta >= 1 and (b - tb) >= 1 and a - ta <= 8:
                said = "".join(text[info["idx"][i]] for i in range(ta, a))
                heard = "".join(info["asr"][tb:b])
                if not alike(said, heard):
                    print(f"  listen at {mmss(ct[info['idx'][ta]][0])}: 「{said}」 (heard as {heard})")
            prev = (a + k, b + k)
    print("Pinyin is compared, so same-sounding words pass; what is listed sounds different. Fix a misread with SAY"
          " (same-length, same-sounding characters) and re-read just those lines.")

else:
    src, secs = os.path.join(D, args[0]), float(args[1])
    out = os.path.splitext(src)[0] + "_cut.flac"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-t", f"{secs:.3f}", "-af", f"afade=t=out:st={secs - 0.1:.3f}:d=0.1",
                    "-c:a", "flac", out], check=True)
    print(f"{os.path.relpath(out, D)}: first {secs:.2f} s. In project.py NARRATION, play it with stop_at = the first words"
          " that were cut off, and add the re-read ending as its own part")

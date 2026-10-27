"""project.py -> storyboard.json: every shot resolved into what AutoIP will get (references, prompt, dialogue, voice).

usage: python dramakit/storyboard.py PROJECT_DIR
Prints the shot list, warnings and a credit estimate for the video jobs. make_jobs.py calls build() itself, so the
jobs always follow the current project.py (there is no stale storyboard to forget to regenerate); storyboard.json is
for reading and review.

What build() takes care of, so project.py stays a script:
  - references: the speaker, every @KEY in `act`, `cast`, `props`, and the scene's set (always, last); 6 at most
  - @KEY in `act` -> @圖片 N in the order of images[]
  - every SHOT line names the location (a multi-reference SHOT without one falls back to a grey studio backdrop)
  - with a voice sample, gender words are taken out of the descriptions (they override the voice's timbre)
  - multi-reference prompts are English: the model (MiniMax H3) speaks Chinese narration along with the line;
    `act` and the delivery in `say` are written in English, only the line itself is Chinese
"""
import math, os, re, sys
from common import load_project, jdump, P

KEY = re.compile(r"@([A-Z][A-Z0-9_]*)")
PUNCT = re.compile(r"[\s，。！？、；：,.!?;:…—\-「」『』（）()《》〈〉“”\"'~～]")
GENDER = [(r"\b(business)(wo)?m[ae]n\b", r"\1 person"), (r"\b(wo)?m[ae]n\b", "person"), (r"\b(girl|boy|lady|gentleman|guy)s?\b", "person"),
          (r"\b(fe)?male\s+", ""), (r"\b(he|she)\b", "they"), (r"\b(his|her)\b", "their"),
          (r"(男|女)(人|子|孩|生|士)", r"人"), (r"(少女|少年|先生|小姐)", "人物")]
SAY_RATE = 4.0  # characters per second the multi-reference voice can fit without squeezing
CJK = re.compile(r"[㐀-鿿]")


def neutral(desc):
    out = desc
    for pat, rep in GENDER:
        out = re.sub(pat, rep, out, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip()


def chars(text):
    return len(PUNCT.sub("", text))


def build(proj):
    """-> (storyboard dict, [warnings])"""
    warn = []
    CAST, SETS, PROPS = proj.CAST, getattr(proj, "SETS", {}), getattr(proj, "PROPS", {})
    # a character with file=None or `unseen` is not shown in this episode: never a reference, `unseen` says how the
    # shot shows them instead (with a picture it still gives them their voice, and is there for later episodes)
    unseen = {k: v.get("unseen") or "畫面中背對鏡頭的人" for k, v in CAST.items() if not v.get("file") or v.get("unseen")}
    lib = {**{k: ("cast", v) for k, v in CAST.items() if k not in unseen}, **{k: ("set", v) for k, v in SETS.items()},
           **{k: ("prop", v) for k, v in PROPS.items()}}
    if len(lib) + len(unseen) < len(CAST) + len(SETS) + len(PROPS):
        warn.append("CAST, SETS and PROPS share one key space: a key is used twice")
    scenes = {s[0]: dict(set=s[1], head=s[2]) for s in proj.SCENES}
    prefix, sfx0 = getattr(proj, "MOTION_PREFIX", ""), getattr(proj, "SFX", "")
    shots, seen, long_desc = [], set(), set()
    if CJK.search(prefix) and any(s.get("kind", "M") == "M" for s in proj.SHOTS):
        warn.append("MOTION_PREFIX is Chinese: multi-reference prompts are English (H3 may speak Chinese narration)")
    for s in proj.SHOTS:
        i, kind = s["id"], s.get("kind", "M")
        assert i not in seen, f"shot id {i} used twice"
        seen.add(i)
        sc = scenes[s["scene"]]
        set_key = s.get("set", sc["set"])
        say = s.get("say")
        spk, text, how = (list(say) + [""])[:3] if say else (None, "", "")
        act = s.get("act", "")
        keys = ([spk] if spk else []) + list(s.get("cast", []))
        keys += KEY.findall(act) + list(s.get("props", []))
        keys = [k for n, k in enumerate(keys) if k not in keys[:n] and k != set_key] + [set_key]
        for k in keys:
            if k in unseen and k in KEY.findall(act):
                warn.append(f"{i}: @{k} is not shown in this episode (file=None / unseen): describe them in words instead")
            elif k not in lib and k not in unseen:
                warn.append(f"{i}: unknown key {k} (not in CAST / SETS / PROPS)")
        keys = [k for k in keys if k in lib]
        idx = {k: n + 1 for n, k in enumerate(keys)}
        at = lambda t: KEY.sub(lambda m: f"@圖片 {idx[m.group(1)]}" if m.group(1) in idx else m.group(0), t)
        cast_in = [k for k in keys if lib[k][0] == "cast"]
        voice = CAST[spk].get("voice") if spk in CAST else None
        sfx = s.get("sfx", sfx0)
        row = dict(id=i, kind=kind, scene=s["scene"], head=sc["head"], set=set_key, cast=cast_in, speaker=spk, dialogue=text,
                   how=how, cap=s.get("cap") or (f"{CAST[spk]['name']}：{text}" if spk in CAST else act)[:40])

        if kind == "M":
            n = len(keys)
            if n > 6:
                warn.append(f"{i}: {n} references, multi-reference takes 6 at most")
            secs = s.get("secs") or (min(10, max(5, math.ceil(chars(text) / SAY_RATE + 1.5))) if text else 5)
            if not 5 <= secs <= 10:
                warn.append(f"{i}: secs={secs}, multi-reference video is 5-10 s")
            if text and chars(text) > SAY_RATE * secs:
                warn.append(f"{i}: {chars(text)} characters in {secs} s (> {SAY_RATE:g}/s): the voice gets squeezed or cut; "
                            f"split the line or make it an LS shot")
            if spk and not voice:
                warn.append(f"{i}: {spk} has no voice sample: the model picks a voice, it will differ from shot to shot")
            # AutoIP turns this into MiniMax H3's six sections and appends, at the very end, "<Subject 1> looks at the
            # camera and says: <d>[Chinese]line</d>". So: narration in English (Chinese next to the <d> gets spoken
            # with the line), the speaker is picture 1 (speaker first, above), the line belongs to the last SHOT, the
            # first paragraph is the summary, and no MUSIC & SFX (it switches the music track on, even for "no music")
            for f, t in (("act", act), ("how", how)):
                if CJK.search(t):
                    warn.append(f"{i}: Chinese in `{f}`: H3 may speak it with the line; write it in English (only the line stays Chinese)")
            if spk in unseen:
                warn.append(f"{i}: {spk} speaks but is not shown: AutoIP gives the line to the first reference ({keys[0]})")
            loc = f"@圖片 {idx[set_key]}"
            # one SHOT: say so, or the model cuts by itself (to a reference picture's own background, e.g. an alley)
            body = at(act) if "SHOT" in act else "SHOT 1: One continuous shot, no cuts. " + at(act)
            out = [ln.strip() for ln in body.split("\n") if ln.strip()]
            shot_rows = [n for n, ln in enumerate(out) if ln.startswith(("SHOT", "CUT"))]
            for n in shot_rows:
                if loc not in out[n]:
                    out[n] += f" Location: {loc}."
            if spk and spk not in unseen and shot_rows:
                out[shot_rows[-1]] += f" Only @圖片 1 speaks{', ' + how if how else ''}."
            head = f"{prefix} The whole video takes place in {loc}.".strip()
            sfx = s.get("sfx", "")  # project SFX is for I2V / K shots; a shot's own `sfx` (English) also turns music on
            prompt = head + "\n\n" + (f"MUSIC & SFX: {sfx}\n" if sfx else "") + "\n".join(out)
            descs = []
            for k in keys:
                d = lib[k][1].get("ref_desc") or lib[k][1]["desc"]
                if voice:
                    d2 = neutral(d)
                    if d2 != d and k in CAST:
                        row.setdefault("neutralized", []).append(k)
                    d = d2
                if len(d) > 200 and k not in long_desc:
                    long_desc.add(k)
                    warn.append(f"{k}: description is {len(d)} characters, multi-reference reads 200 (give a shorter ref_desc)")
                descs.append(d[:200])
            # a character can have one picture per set (`by_set`, made by restage.py): what a shot drifts into is then that set
            pic = lambda k: lib[k][1].get("by_set", {}).get(set_key) or lib[k][1]["file"]
            row.update(refs=keys, images=[P(proj.DIR, pic(k)) for k in keys], descs=descs, prompt=prompt,
                       secs=secs, voice=P(proj.DIR, voice) if voice else None)
        elif kind in ("LS", "I2V", "K"):
            still = s.get("still")
            if not still:
                warn.append(f"{i}: kind {kind} needs `still` (English prompt for its first-frame still kf/{i}.png)")
            if len(cast_in) > 1:
                warn.append(f"{i}: {len(cast_in)} people in one still drift and merge; use a multi-reference (M) shot")
            base = cast_in[0] if cast_in else None
            sd = lib[set_key][1]["desc"] if set_key in lib else ""
            row.update(still=still or "", still_from=base, set_desc=sd, still_file=P(proj.DIR, "kf", i + ".png"))
            if kind == "LS":
                audio = s.get("audio", f"lines/{i}.wav")
                row.update(audio=P(proj.DIR, audio), prompt=f"{how or '平靜'}地說話，咬字清楚，每個字嘴巴明顯張合，鏡頭穩定。")
                if not spk:
                    warn.append(f"{i}: an LS shot needs `say` (who speaks, the subtitle text)")
            elif kind == "I2V":
                secs = s.get("secs", 5)
                lead = "單一連續鏡頭，不要切換畫面，同一個人、同一張臉。" if cast_in else "單一連續鏡頭。"
                row.update(secs=secs, prompt=(prefix + "\n" if prefix else "") + (f"MUSIC & SFX: {sfx}\n" if sfx else "") + "SHOT 1: " + lead + at(act))
                if text:
                    warn.append(f"{i}: image-to-video does not speak `say`; use M or LS for dialogue")
            else:
                secs = s.get("secs", 6)
                if secs not in (6, 10, 15):
                    warn.append(f"{i}: keyframe video is 6, 10 or 15 s, not {secs}")
                if not s.get("to"):
                    warn.append(f"{i}: a K shot needs `to` (the shot id whose still kf/<to>.png is the last frame)")
                row.update(secs=secs, to=s.get("to"), prompt=prefix + at(act))
        else:
            warn.append(f"{i}: unknown kind {kind} (M, LS, I2V, K)")
        shots.append(row)

    used = {k for r in shots for k in r.get("refs", []) + r.get("cast", []) + [r["set"]]}
    unused = sorted(set(lib) - used)
    if unused:
        warn.append(f"never used: {unused}")
    for k, (t, v) in lib.items():
        if not os.path.exists(os.path.join(proj.DIR, v["file"])):
            warn.append(f"{t} {k}: {v['file']} does not exist yet" + (" (make_jobs.py P refs)" if v.get("prompt") or v.get("base") or t != "cast" else ""))
    for k, v in CAST.items():
        for sk, f in v.get("by_set", {}).items():
            if sk in used and not os.path.exists(os.path.join(proj.DIR, f)):
                warn.append(f"cast {k}: {f} (in {sk}) does not exist yet (restage.py P)")
        if v.get("voice") and not os.path.exists(os.path.join(proj.DIR, v["voice"])):
            warn.append(f"cast {k}: voice sample {v['voice']} does not exist yet ("
                        + ("make_jobs.py P voices, then " if v.get("voice_line") else "") + "voices.py)")
    return dict(name=proj.NAME, shots=shots), warn


if __name__ == "__main__":
    from common import estimate
    proj = load_project(sys.argv[1])
    sb, warn = build(proj)
    jdump(sb, os.path.join(proj.DIR, "storyboard.json"))
    ep = {"M": "/videos/multi-subject-reference", "LS": "/videos/lip-sync", "I2V": "/videos/image-to-video", "K": "/videos/keyframe"}
    total, video = 0, dict(dict(resolution="768p"), **getattr(proj, "VIDEO", {}))
    for r in sb["shots"]:
        extra = getattr(proj, "LS_FIELDS", {}) if r["kind"] == "LS" else video
        c = estimate(dict(endpoint=ep.get(r["kind"], ""), fields=dict(extra, duration_seconds=r.get("secs", 5))))
        total += c
        who = f"{r['speaker']}：{r['dialogue']}" if r["speaker"] else "—"
        print(f"{r['id']:8} {r['kind']:3} {str(r.get('secs', '')):>3}s {c:4} {'+'.join(r.get('refs') or r['cast'] or [r['set']]):24} {who}")
    for k in sorted({k for r in sb["shots"] for k in r.get("neutralized", [])}):
        print(f"note: {k}'s description loses its gender words in voiced multi-reference jobs (the voice sample decides)")
    for w in warn:
        print("WARN", w)
    print(f"{len(sb['shots'])} shots, video about {total} credits (estimate at 768p; GET /api/v1/pricing has live prices)")

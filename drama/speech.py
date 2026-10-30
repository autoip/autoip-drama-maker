"""Where is the speech in each dialogue clip, and was the line said? -> speech.json (used by the edit and subtitles).

usage: python dramakit/speech.py PROJECT_DIR [id ...]        (default: every shot with `say` whose clip exists, and its
                                                             earlier takes clips/_takes/<id>_v1.mp4 as "_takes/<id>_v1")
env:   NO_ASR=1           speech span from silence detection only (no faster-whisper)
       SIL_DB=-32         silence threshold for the span (clip audio also carries ambience and effects)
       ASR_DEVICE=cpu     recognise on the CPU (default: the NVIDIA GPU when CTranslate2 sees one, else the CPU);
                          WHISPER_MODEL (default medium), ASR_LANG (default zh)

speech.json {id: {dur, speech: [a, b], words: [[a, b, "字"], ...], heard, match}}, all in clip seconds.
Flags in the table:
  SILENT?  no speech found                       TEXT?  what was heard differs from the line (match < 0.5)
  CUT?     speech runs into the end of the clip (the line may be cut off: multi-reference squeezes or drops long lines)
The line itself is the ASR prompt, so `heard` leans towards the script: TEXT? catches missing or extra sentences,
not single wrong syllables. Listen to anything flagged.
"""
import difflib, os, re, subprocess, sys, tempfile
from common import load_project, jload, jdump, dur_of, has_audio, clip_path
from storyboard import PUNCT

proj = load_project(sys.argv[1])
D = proj.DIR
SIL_DB = os.environ.get("SIL_DB", "-32")
out_p = os.path.join(D, "speech.json")
out = jload(out_p) if os.path.exists(out_p) else {}
said = {s["id"]: s for s in proj.SHOTS if s.get("say")}
shots = [(i, s, clip_path(proj, i)) for i, s in said.items()]
takes = os.path.join(D, "clips", "_takes")  # earlier takes (clips/_takes/<id>_v1.mp4) for an NG reel: key "_takes/<id>_v1"
for f in sorted(os.listdir(takes)) if os.path.isdir(takes) else []:
    m = re.match(r"^(.+)_v\d+\.mp4$", f)
    if m and m.group(1) in said:
        shots.append(("_takes/" + f[:-4], said[m.group(1)], os.path.join(takes, f)))
shots = [x for x in shots if os.path.exists(x[2]) and (not sys.argv[2:] or x[0] in sys.argv[2:])]

model = None
if not os.environ.get("NO_ASR"):
    try:
        DEVICE = os.environ.get("ASR_DEVICE", "")
        if not DEVICE:  # the GPU whenever CTranslate2 (faster-whisper's engine) sees one
            try:
                import ctranslate2
                DEVICE = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:
                DEVICE = "cpu"
        if DEVICE == "cuda" and os.name == "nt":  # the pip wheels keep their DLLs in site-packages/nvidia/*/bin
            import importlib.util
            for mod in ("nvidia.cublas", "nvidia.cudnn"):
                spec = importlib.util.find_spec(mod)
                for d in (spec.submodule_search_locations or []) if spec else []:
                    if os.path.isdir(os.path.join(d, "bin")):
                        os.add_dll_directory(os.path.join(d, "bin"))
                        os.environ["PATH"] = os.path.join(d, "bin") + os.pathsep + os.environ["PATH"]
        from faster_whisper import WhisperModel
        load = lambda dev: WhisperModel(os.environ.get("WHISPER_MODEL", "medium"), device=dev,
                                        compute_type=os.environ.get("ASR_COMPUTE", "int8_float16" if dev == "cuda" else "int8"))
        try:
            model = load(DEVICE)
        except Exception as e:  # e.g. cuBLAS / cuDNN missing (SETUP): recognise on the CPU instead of stopping
            if DEVICE != "cuda":
                raise
            print(f"speech recognition on the GPU failed ({str(e)[:120]}), using the CPU")
            DEVICE, model = "cpu", load("cpu")
        print(f"speech recognition: faster-whisper on the {'GPU' if DEVICE == 'cuda' else 'CPU'}")
    except ImportError:
        print("faster-whisper not installed: speech spans from silence detection only (pip install faster-whisper)")


def spans(wav, dur):
    """Non-silent stretches from ffmpeg silencedetect."""
    err = subprocess.run(["ffmpeg", "-v", "info", "-i", wav, "-af", f"silencedetect=noise={SIL_DB}dB:d=0.3", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    edges, t = [], 0.0
    for a, b in zip(st, en + [dur] * (len(st) - len(en))):
        if a - t > 0.08:
            edges.append([round(max(0, t), 2), round(a, 2)])
        t = b
    if dur - t > 0.08:
        edges.append([round(t, 2), round(dur, 2)])
    return edges


tmp = tempfile.mkdtemp()
print(f"{'id':8} {'dur':>5} {'speech':>12}  {'match':>5}  flags  heard")
for i, s, p in shots:
    text = s["say"][1]
    dur = dur_of(p)
    r = dict(dur=round(dur, 2), speech=None, words=[], heard="", match=None)
    if has_audio(p):
        wav = os.path.join(tmp, i.replace("/", "_") + ".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
        sp = spans(wav, dur)
        if model:
            segs, _ = model.transcribe(wav, language=os.environ.get("ASR_LANG", "zh"), initial_prompt=text, word_timestamps=True,
                                       vad_filter=True, condition_on_previous_text=False, temperature=0)
            r["words"] = [[round(w.start, 2), round(w.end, 2), w.word.strip()] for g in segs for w in g.words if w.word.strip()]
            r["heard"] = "".join(w[2] for w in r["words"])
            want, got = PUNCT.sub("", text), PUNCT.sub("", r["heard"])
            r["match"] = round(difflib.SequenceMatcher(None, want, got).ratio(), 2) if want else None
        if r["words"]:  # whisper starts the first word early (~0.3 s): take the sound onset / offset next to it if there is one
            w = r["words"]
            on = [a for a, b in sp if w[0][0] - 0.15 <= a <= w[0][1]]
            off = [b for a, b in sp if w[-1][0] <= b <= w[-1][1] + 0.6]
            r["speech"] = [on[0] if on else w[0][0], off[-1] if off else w[-1][1]]
        elif sp:
            r["speech"] = [sp[0][0], sp[-1][1]]
    flags = []
    if not r["speech"]:
        flags.append("SILENT?")
    elif r["speech"][1] > dur - 0.25:
        flags.append("CUT?")
    if r["match"] is not None and r["match"] < 0.5:
        flags.append("TEXT?")
    out[i] = r
    sp_s = f"{r['speech'][0]:.2f}-{r['speech'][1]:.2f}" if r["speech"] else "-"
    print(f"{i:8} {dur:5.2f} {sp_s:>12}  {'' if r['match'] is None else r['match']:>5}  {' '.join(flags):6} {r['heard'][:40]}", flush=True)
jdump(out, out_p)
print(out_p, len(shots), "clips")

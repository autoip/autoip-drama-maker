"""Word timestamps for the sung lyrics (faster-whisper), prompted with the lyric text, region by region.

usage: python mvkit/audio/asr_words.py PROJECT_DIR a,b [a,b ...]   (song seconds of the regions with vocals)
-> AUDIO["words"] = [[start, end, word], ...]

ASR on sung dialects (Taiwanese Hokkien, growls, heavy mixes) is unreliable as text, but with the lyrics as
initial_prompt and short regions its *timings* are usable. epic.time_tokens() aligns the lyric characters to
these words; lines it cannot match fall back to even spacing between the line start times in project.SECTIONS,
so regions that fail completely are fine as long as the line start times are right.

ASR_DEVICE=cuda runs on an NVIDIA GPU (int8_float16: 60 s of vocals in 1.0 s on an RTX 5060 Ti, 10.9 s on 16 CPU
threads; the first GPU run compiles kernels, ~20 s once). The CPU is the default; a GPU that ctranslate2 sees is only
suggested. ASR_COMPUTE overrides the compute type. ctranslate2 needs cuBLAS 12 and cuDNN 9:
`pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"`; their DLL folders are added here.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ctranslate2, librosa
from common import load_project, audio_path

DEVICE = os.environ.get("ASR_DEVICE", "cpu")
if "ASR_DEVICE" not in os.environ and ctranslate2.get_cuda_device_count():
    print("  tip: an NVIDIA GPU is available; ASR_DEVICE=cuda transcribes about 10x faster")
COMPUTE = os.environ.get("ASR_COMPUTE", "int8_float16" if DEVICE == "cuda" else "int8")
if DEVICE == "cuda" and os.name == "nt":  # the pip wheels keep their DLLs in site-packages/nvidia/*/bin
    import importlib.util
    for mod in ("nvidia.cublas", "nvidia.cudnn"):
        spec = importlib.util.find_spec(mod)
        for d in (spec.submodule_search_locations or []) if spec else []:
            if os.path.isdir(os.path.join(d, "bin")):
                os.add_dll_directory(os.path.join(d, "bin"))
                os.environ["PATH"] = os.path.join(d, "bin") + os.pathsep + os.environ["PATH"]
from faster_whisper import WhisperModel

proj = load_project(sys.argv[1])
m = WhisperModel(os.environ.get("WHISPER_MODEL", "medium"), device=DEVICE, compute_type=COMPUTE)
print("asr on", DEVICE, COMPUTE)
y, sr = librosa.load(audio_path(proj, "vocals"), sr=16000)
prompt = "".join(x for s in proj.SECTIONS for _, x, _ in s[3])
out = []
for spec in sys.argv[2:]:
    a, b = (float(v) for v in spec.split(","))
    segs, _ = m.transcribe(y[int(a * sr):int(b * sr)], language=os.environ.get("ASR_LANG", "zh"), initial_prompt=prompt,
                           word_timestamps=True, vad_filter=False, condition_on_previous_text=False, temperature=0)
    for s in segs:
        print(f"{s.start + a:7.2f}-{s.end + a:7.2f}", " ".join(f"{w.word.strip()}@{w.start + a:.1f}" for w in s.words), flush=True)
        out += [[round(w.start + a, 2), round(w.end + a, 2), w.word.strip()] for w in s.words]
json.dump(out, open(audio_path(proj, "words"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(out), "words")

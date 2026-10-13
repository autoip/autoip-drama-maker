"""Word timestamps for the sung lyrics (faster-whisper), prompted with the lyric text, region by region.

usage: python mvkit/audio/asr_words.py PROJECT_DIR a,b [a,b ...]   (song seconds of the regions with vocals)
-> AUDIO["words"] = [[start, end, word], ...]

ASR on sung dialects (Taiwanese Hokkien, growls, heavy mixes) is unreliable as text, but with the lyrics as
initial_prompt and short regions its *timings* are usable. epic.time_tokens() aligns the lyric characters to
these words; lines it cannot match fall back to even spacing between the line start times in project.SECTIONS,
so regions that fail completely are fine as long as the line start times are right.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import librosa
from faster_whisper import WhisperModel
from common import load_project, audio_path

proj = load_project(sys.argv[1])
m = WhisperModel(os.environ.get("WHISPER_MODEL", "medium"), device="cpu", compute_type="int8")
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

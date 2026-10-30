"""Voice samples for the cast: cut, clean and level a recording into CAST[k]["voice"] (sent as voice_sample).

usage: python drama/voices.py PROJECT_DIR [KEY ...]
CAST[k] fields:
  voice_src   "voices/raw/lin.m4a": a recording of this character's voice (any format ffmpeg reads), or the clip
              `make_jobs.py P voices` made from `voice_line` ("voices/raw/LIN.mp4": the character saying it)
  voice_span  (a, b): the seconds of voice_src to use (default: all of it, edge silence trimmed)
  voice       "voices/LIN.wav": the sample that is written and sent (default voices/<KEY>.wav)
A good sample: one speaker, 5-15 s, no music or effects under it, in the tone the character uses most. Use a voice
you have the rights to (your own, an actor's with consent, or a synthetic voice whose licence allows it).
"""
import os, sys
from common import load_project, run, dur_of

proj = load_project(sys.argv[1])
keys = sys.argv[2:] or [k for k, c in proj.CAST.items() if c.get("voice_src")]
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.2,areverse")
for k in keys:
    c = proj.CAST[k]
    if not c.get("voice_src"):
        print(f"{k}: no voice_src"); continue
    src = os.path.join(proj.DIR, c["voice_src"])
    out = os.path.join(proj.DIR, c.get("voice", f"voices/{k}.wav"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cut = []
    if c.get("voice_span"):
        a, b = c["voice_span"]
        cut = ["-ss", str(a), "-t", str(b - a)]
    run(["ffmpeg", "-v", "error", "-y", *cut, "-i", src, "-vn", "-af",
         f"highpass=f=70,{TRIM},loudnorm=I=-18:TP=-2:LRA=7", "-ac", "1", "-ar", "44100", out])
    d = dur_of(out)
    note = " (short: give 5 s or more)" if d < 5 else " (long: 15 s or less is enough)" if d > 20 else ""
    print(f"{k}: {os.path.relpath(out, proj.DIR)} {d:.1f} s{note}")
    if not c.get("voice"):
        print(f"   set CAST['{k}']['voice'] = 'voices/{k}.wav'")

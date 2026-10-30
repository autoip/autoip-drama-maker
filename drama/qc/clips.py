"""Check downloaded clips: does each decode to the end, how long is it, does it have sound, where does it cut inside?

usage: python dramakit/qc/clips.py PROJECT_DIR [id ...]        (default: every clips/*.mp4)
env:   SCD=12  scene-change threshold (ffmpeg scdet)

A finished download is not always a whole file (a clip can stop decoding half way): BROKEN ones are downloaded again
from the same task (delete the file and rerun aip_runner.py with the same job file, no new credits). Multi-reference
clips cut by themselves 2-4 times in 8-10 s: `cuts` are those seconds, so an edit row can take one shot out of a clip
(`S1_03 4.20 2.10`). -> PROJECT_DIR/clips.json {id: {dur, size, audio, cuts, ok}}
"""
import glob, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import load_project, jdump

proj = load_project(sys.argv[1])
D = proj.DIR
ids = sys.argv[2:] or sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(D, "clips", "*.mp4")))
info = {}
print(f"{'id':10} {'dur':>6} {'size':>10} audio  cuts")
for i in ids:
    p = os.path.join(D, "clips", i + ".mp4")
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                                    "-of", "json", p], capture_output=True, text=True).stdout or "{}")
    st = pr.get("streams", [])
    v = next((s for s in st if s.get("codec_type") == "video"), {})
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", p, "-vf", f"scdet=threshold={os.environ.get('SCD', '12')}", "-an",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    errs = [ln for ln in r.stderr.splitlines() if re.search(r"error|invalid|corrupt", ln, re.I) and "scd" not in ln]
    cuts = [round(float(x), 2) for x in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", r.stderr)]
    info[i] = dict(dur=round(float(pr.get("format", {}).get("duration", 0)), 2), size=f"{v.get('width')}x{v.get('height')}",
                   audio=any(s.get("codec_type") == "audio" for s in st), cuts=cuts, ok=r.returncode == 0 and not errs)
    c = info[i]
    print(f"{i:10} {c['dur']:6.2f} {c['size']:>10} {'yes' if c['audio'] else 'NO ':5}  {cuts}{'' if c['ok'] else '  BROKEN: ' + (errs[:1] or ['exit'])[0][:60]}")
jdump(info, os.path.join(D, "clips.json"))

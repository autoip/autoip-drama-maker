"""First-pass edit: every shot in story order, trimmed to its line -> paste into project.EDITS and start cutting.

usage: python drama/edl_draft.py PROJECT_DIR [MODE]
Without MODE: one row per shot that has a clip, `in` and `dur` taken from speech.json (run speech.py first), the line
as a comment. With MODE: the rows of that edit as they resolve now (auto rows with numbers), and the running time.
"""
import os, sys
import timeline
from common import load_project, jload, dur_of, clip_path

proj = load_project(sys.argv[1])
if len(sys.argv) > 2:
    tl = timeline.resolve(proj, sys.argv[2])
    for w in tl["warn"]:
        print("WARN", w)
    for b in tl["base"]:
        fl = " ".join(k if v is True else f"{k}={v}" for k, v in b["flags"].items())
        print(f"{b['t0']:7.2f}  {b['src']:10} {b['inn']:5.2f} {b['dur']:5.2f} {fl}")
        for o in tl["over"]:
            if tl["base"][o["row"]] is b:
                print(f"{o['t0']:7.2f}    ^{o['src']:8} {o['inn']:5.2f} {o['dur']:5.2f}")
    print(f"total {tl['total']:.2f} s")
    sys.exit()

R = timeline.settings(proj)
sp_p = os.path.join(proj.DIR, "speech.json")
speech = jload(sp_p) if os.path.exists(sp_p) else {}
t, rows = 0.0, []
for s in proj.SHOTS:
    p = clip_path(proj, s["id"])
    if not os.path.exists(p):
        rows.append(f"# {s['id']}: no clip yet")
        continue
    cd = dur_of(p)
    sp = speech.get(s["id"], {}).get("speech")
    if sp:
        a = max(0.0, sp[0] - R["pad"][0])
        d = min(cd - R["tail_guard"], sp[1] + R["pad"][1]) - a
    else:
        a, d = 0.0, min(cd - R["tail_guard"], R["hold"])
    say = s.get("say")
    note = f"{proj.CAST[say[0]]['name']}：{say[1]}" if say and say[0] in proj.CAST else (s.get("cap") or s.get("act", ""))[:30]
    rows.append(f"{s['id']:10} {a:5.2f} {d:5.2f}    # {t:6.2f}  {note}")
    t += d
print('EDITS = {\n    "main": dict(shots="""')
for r in rows:
    print("        " + r)
print('    """),\n}')
print(f"# total {t:.2f} s")

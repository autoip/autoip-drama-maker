"""project.py -> storyboard.json (what to generate) + shots.json (lip-sync takes, sections, lyric lines).

usage: python mv/storyboard.py PROJECT_DIR
Run faces.py first so vocal characters carry a face box (used to crop the lip-sync pads).
"""
import os, sys
from common import load_project, jload, jdump

proj = load_project(sys.argv[1])
D = proj.DIR
fp = os.path.join(D, "faces.json")
FACES = jload(fp) if os.path.exists(fp) else {}
MULTI = getattr(proj, "MULTI_PROMPT", {})


def label(t):
    a, b = t
    if a is None:
        return f"{b:g} s"
    mm = lambda x: f"{int(x // 60)}:{int(x % 60):02d}"
    return f"{mm(a)}–{mm(b)} ({a:.1f}–{b:.1f}s)"


sb = dict(name=proj.NAME, song=proj.SONG, style=proj.STYLE, motion_prefix=proj.MOTION_PREFIX,
          band_stage=getattr(proj, "BAND_STAGE", ""),
          chars={k: dict(c, face=FACES.get(c["file"])) for k, c in proj.CHARS.items()},
          lipsync_scenes=[dict(id=i, char=c, scene=s, motion=m, cap=cap) for i, c, s, m, cap in proj.LS_SCENES],
          band=[dict(id=i, chars=c if isinstance(c, list) else [c], cap=cap, prompt=p, motion=m, multi=MULTI.get(i))
                for i, c, cap, p, m in proj.BAND],
          broll=[dict(id=i, cap=cap, prompt=p, motion=m) for i, cap, p, m in proj.BROLL])
caps = {b[0]: b[1] for b in proj.BROLL} | {b[0]: b[2] for b in proj.BAND} | {s[0]: s[4] for s in proj.LS_SCENES} | {"CARD": "promo card"}
caps |= {l[0]: caps[l[1]] for l in proj.LIPSYNC}  # sections may list lip-sync takes or their scenes
caps |= getattr(proj, "EXTRA_CAPS", {})  # clips made outside this storyboard (keyframe / multi-reference jobs of the project)
shots = dict(lipsync=[dict(id=i, scene=s, a0=a, dur=d, voice=v) for i, s, a, d, v in proj.LIPSYNC],
             sections=[dict(name=n, t=label(t), span=list(t), typo=ty, lines=[[a, x] for a, x, _ in ln], voices=[v for *_, v in ln],
                            shots=[[k, caps[k]] for k in sh]) for n, t, ty, ln, sh in proj.SECTIONS])
for c in sb["chars"].values():
    if c.get("kind") == "vocal" and not c["face"]:
        print("WARN no face box for", c["file"], "-> run faces.py")
jdump(sb, os.path.join(D, "storyboard.json"))
jdump(shots, os.path.join(D, "shots.json"))
used = {k for s in proj.SECTIONS for k in s[4]}
used |= {l[1] for l in proj.LIPSYNC if l[0] in used}
print("chars", len(proj.CHARS), "LS scenes", len(proj.LS_SCENES), "band", len(proj.BAND), "B-roll", len(proj.BROLL),
      "sections", len(proj.SECTIONS), "unused", sorted(set(caps) - used - {"CARD"}))

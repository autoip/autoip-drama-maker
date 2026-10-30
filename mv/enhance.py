"""Local GPU super resolution (2x) + frame generation (60 fps) for an MV's clips -> clips_hd/, picture only;
render_mv.py uses the copies when the render settings say enhance=True (RENDER, or an edit's render=dict(...)).
The engine is dreamfab/enhance.py.

usage: python mv/enhance.py PROJECT_DIR [--fps 60] [--scale 2] [--quality ULTRA] [--watch]
env:   ONLY=B05,M02   just these clips
Every clip that project.EDITS uses is done (clips not downloaded yet are skipped).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import edit
from dreamfab import enhance


def clips_used(proj):
    srcs = {s[1] for mode in getattr(proj, "EDITS", {}) for s in edit(proj, mode)["shots"]}
    keep = enhance.only()
    return [os.path.join(proj.DIR, "clips", s + ".mp4") for s in srcs if not keep or s in keep]


if __name__ == "__main__":
    enhance.main(sys.argv[1:], clips_used)

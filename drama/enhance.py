"""Local GPU super resolution (2x) + frame generation (60 fps) for an episode's clips -> clips_hd/, picture only;
render_ep.py uses the copies when the render settings say enhance=True. The engine is dreamfab/enhance.py.

usage: python drama/enhance.py PROJECT_DIR [--fps 60] [--scale 2] [--quality ULTRA] [--watch]
env:   ONLY=S1_01,S2_03   just these clips
Every clip the episode's edits use is done, also clips borrowed from another episode (into that episode's clips_hd/)
and old takes in clips/_takes/ that an NG edit uses.
"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: F401  (puts the repo root on sys.path for dreamfab)
import timeline
from dreamfab import enhance


def clips_used(proj):
    out = {os.path.normpath(p) for p in glob.glob(os.path.join(proj.DIR, "clips", "*.mp4"))}
    for mode in getattr(proj, "EDITS", {}):
        try:
            tl = timeline.resolve(proj, mode)
        except Exception as e:   # an edit that does not resolve yet (clips still missing) is skipped
            print(f"  ({mode}: {e})"); continue
        out |= {os.path.normpath(p["path"]) for p in tl["pictures"] if p["path"].lower().endswith(".mp4")}
    keep = enhance.only()
    return [p for p in out if not keep or os.path.splitext(os.path.basename(p))[0] in keep]


if __name__ == "__main__":
    enhance.main(sys.argv[1:], clips_used)

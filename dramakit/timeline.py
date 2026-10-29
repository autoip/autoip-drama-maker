"""An edit (project.EDITS[mode]) -> timed rows: the one place that decides where every shot sits.

Base rows play one after another with their own sound. A row without `in` (or with `auto`) uses speech.json: from just
before the line starts to just after it ends (RENDER pad), or the first `hold` seconds of a clip without a line.
Cutaways (^rows) put another clip's picture over the base track; the sound stays the base row's (an L / J cut).
Everything is rounded to whole frames, so picture and sound cannot drift apart.
"""
import os
from common import jload, dur_of, clip_path, edit

DEFAULTS = dict(fps=25, pad=(0.15, 0.35), hold=2.0, tail_guard=0.3)


def settings(proj):
    return dict(DEFAULTS, **getattr(proj, "RENDER", {}))


def resolve(proj, mode):
    """-> dict(edit, base, over, pictures, total, warn)

    base     [dict(src, path, inn, dur, freeze, flags, t0, t1, t2)]   t1 = end of the clip, t2 = end of the freeze
    over     [dict(src, path, inn, dur, flags, t0, t1, row)]          row = index of the base row it was placed on
    pictures [dict(t0, t1, src, path, off, kind, flags, row_t0)]      kind "clip" | "freeze"; off = clip seconds at t0
    """
    E = edit(proj, mode)
    R = dict(settings(proj), **E.get("render", {}))   # an edit may change render settings, e.g. render=dict(fps=60)
    FPS = R["fps"]
    q = lambda t: round(t * FPS) / FPS
    sp_p = os.path.join(proj.DIR, "speech.json")
    speech = jload(sp_p) if os.path.exists(sp_p) else {}
    durs, warn = {}, []

    def clip_dur(p):
        if p not in durs:
            durs[p] = dur_of(p) if os.path.exists(p) else 0.0
        return durs[p]

    subst = dict(x.split(":") for x in os.environ.get("SUBST", "").split(",") if x)  # stand-ins for clips not made yet
    base, over, t = [], [], 0.0
    for r in E["rows"]:
        p = clip_path(proj, subst.get(r["src"], r["src"]))
        cd = clip_dur(p)
        if not cd:
            warn.append(f"{r['src']}: no clip at {os.path.relpath(p, proj.DIR)}")
            continue
        usable = cd - R["tail_guard"]
        if r["over"]:
            inn, dur = r["inn"] or 0.0, r["dur"] or 1.0
        elif r["inn"] is None:
            s = speech.get(r["src"], {}).get("speech")
            if s:
                inn = max(0.0, s[0] - R["pad"][0])
                dur = r["dur"] or min(usable, s[1] + R["pad"][1]) - inn
                if not r["dur"] and s[1] > usable:  # multi-reference lines often end ~0.2 s before the clip does
                    warn.append(f"{r['src']}: the line runs to {s[1]:.2f} s, auto stops at {usable:.2f} (tail_guard): "
                                f"give in / dur by hand")
            else:
                inn, dur = 0.0, r["dur"] or min(usable, R["hold"])
        else:
            inn, dur = r["inn"], r["dur"] or usable - r["inn"]
        dur = q(dur)
        if dur <= 0:
            warn.append(f"{r['src']}: nothing left to play (in {inn:.2f}, clip {cd:.2f} s)")
            continue
        if inn + dur > cd + 0.01:
            warn.append(f"{r['src']}: asks for {inn:.2f}+{dur:.2f} s of a {cd:.2f} s clip -> the last frame is held")
        row = dict(src=r["src"], path=p, inn=inn, dur=dur, flags=r["flags"])
        if r["over"]:
            b = base[-1]
            t0 = q(b["t0"] + r["at"] if r["at"] >= 0 else b["t1"] + r["at"])
            over.append(dict(row, t0=t0, t1=q(t0 + dur), row=len(base) - 1))
        else:
            fz = q(float(r["flags"].get("freeze", 0) or 0))
            base.append(dict(row, freeze=fz, t0=q(t), t1=q(t + dur), t2=q(t + dur + fz)))
            t = t + dur + fz
    total = q(t)

    pics = []
    for b in base:
        pics.append(dict(t0=b["t0"], t1=b["t1"], src=b["src"], path=b["path"], off=b["inn"], kind="clip", flags=b["flags"], row_t0=b["t0"]))
        if b["freeze"]:
            pics.append(dict(t0=b["t1"], t1=b["t2"], src=b["src"], path=b["path"], off=b["inn"] + b["dur"] - 1 / FPS, kind="freeze",
                             flags={}, row_t0=b["t0"]))
    for o in over:  # punch each cutaway into the picture track
        a, z = o["t0"], min(o["t1"], total)
        for b in base:
            if a <= b["t0"] < z and any(k in b["flags"] for k in ("intro", "title", "flash", "zoom")):
                warn.append(f"^{o['src']} ({a:.2f}-{z:.2f}) covers the start of {b['src']} and its "
                            f"{'/'.join(k for k in ('intro', 'title', 'flash', 'zoom') if k in b['flags'])}")
        nxt = []
        for p in pics:
            if p["t1"] <= a or p["t0"] >= z:
                nxt.append(p)
                continue
            if p["t0"] < a:
                nxt.append(dict(p, t1=a))
            if p["t1"] > z:  # the rest of the interrupted shot carries on where it would have been
                nxt.append(dict(p, t0=z, off=p["off"] + (z - p["t0"]) * (p["kind"] == "clip"), flags={k: v for k, v in p["flags"].items() if k == "zoom"}))
        nxt.append(dict(t0=a, t1=z, src=o["src"], path=o["path"], off=o["inn"], kind="clip", flags=o["flags"], row_t0=a))
        pics = sorted(nxt, key=lambda p: p["t0"])
    pics = [p for p in pics if p["t1"] - p["t0"] >= 0.5 / FPS]
    return dict(edit=E, base=base, over=over, pictures=pics, total=total, warn=warn, fps=FPS, settings=R, speech=speech)

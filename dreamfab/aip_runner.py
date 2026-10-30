"""AutoIP job runner: keeps <= AIP_MAX tasks in flight, polls, downloads. Resumable.

usage: python dreamfab/aip_runner.py jobs.json [--off-peak]
env:   AUTOIP_API_KEY (required), AUTOIP_BASE_URL (default https://autoip.app), AIP_MAX (default 1)
       AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1: allow AIP_MAX tasks only until that local time (off-peak), then AIP_MAX_AFTER
       AIP_OFF_PEAK=1 or AIP_OFFPEAK=1 (same as --off-peak): submit only inside the half-price window that GET /pricing reports
       (03:00-09:00 Asia/Taipei; a task is billed by when it is submitted). Outside it the runner waits, and tasks
       already running are still polled and downloaded. AIP_OFF_PEAK_MARGIN=120: stop submitting that many seconds
       before the window ends, in case this clock runs behind the server's

jobs.json: [{"id": "...", "endpoint": "/videos/lip-sync", "fields": {...},
             "files": {"image": "path", "images[]": ["p1", "p2"]}, "out": "path.mp4"}]
State lives in jobs.json.state; a job whose `out` file exists is skipped, so delete the output to redo it.
Credits are charged at submit and there is no cancel endpoint: review stills before submitting video jobs.
"""
import json, os, subprocess, sys, time
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run as a script: the repo root
from dreamfab.util import fingerprint

BASE = os.environ.get("AUTOIP_BASE_URL", "https://autoip.app").rstrip("/") + "/api/v1"
KEY = os.environ.get("AUTOIP_API_KEY", "")
MAX_INFLIGHT = int(os.environ.get("AIP_MAX", "1"))  # most accounts allow one running task
UNTIL = os.environ.get("AIP_MAX_UNTIL", "")  # "09:00": AIP_MAX only until then (local time), AIP_MAX_AFTER afterwards
AFTER = int(os.environ.get("AIP_MAX_AFTER", "1"))
DEADLINE = None
if UNTIL:
    _now = time.localtime()
    DEADLINE = time.mktime(_now[:3] + tuple(int(x) for x in UNTIL.split(":")) + (0,) + _now[6:])
    if DEADLINE <= time.time():
        DEADLINE += 86400


def cap():
    return MAX_INFLIGHT if DEADLINE is None or time.time() < DEADLINE else AFTER


OFF_PEAK = "--off-peak" in sys.argv or any(os.environ.get(k, "") not in ("", "0") for k in ("AIP_OFF_PEAK", "AIP_OFFPEAK"))
MARGIN = int(os.environ.get("AIP_OFF_PEAK_MARGIN", "120"))
OFF = dict(enabled=True, timezone="Asia/Taipei", start="03:00", end="09:00")  # GET /pricing "off_peak" replaces it
_checked = [0.0, False]  # last time the server was asked, its active_now


def off_peak_wait():
    """Seconds until a task submitted now would be billed off-peak; 0 inside the window (which ends MARGIN s early)."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(OFF["timezone"]))
    except Exception:  # Windows without the tzdata package: Asia/Taipei is UTC+8 all year
        now = datetime.now(timezone(timedelta(hours=8)))
    sec = lambda hm: int(hm[:2]) * 3600 + int(hm[3:5]) * 60
    t, a, b = now.hour * 3600 + now.minute * 60 + now.second, sec(OFF["start"]), sec(OFF["end"]) - MARGIN
    if (a <= t < b) if a < b else (t >= a or t < b):
        if time.time() - _checked[0] > 60:  # the server has the last word (clock skew at the start of the window)
            try:
                _checked[:] = time.time(), json.loads(curl([BASE + "/pricing"]))["off_peak"]["active_now"]
            except Exception:
                _checked[:] = time.time(), False
        return 0 if _checked[1] else 60
    return (a - t) % 86400
TERMINAL = {"completed", "failed", "timeout", "cancelled"}
if not KEY:
    sys.exit("set AUTOIP_API_KEY")


def curl(args):
    r = subprocess.run(["curl", "-s", "-H", f"Authorization: Bearer {KEY}"] + args, capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def submit(job):
    args = ["-X", "POST", BASE + job["endpoint"]]
    for k, v in job.get("fields", {}).items():
        for item in (v if isinstance(v, list) else [v]):
            args += ["--form-string", f"{k}={item}"]
    for k, v in job.get("files", {}).items():
        for p in (v if isinstance(v, list) else [v]):
            args += ["-F", f"{k}=@{p}"]
    return json.loads(curl(args))


def main(path):
    jobs = json.load(open(path, encoding="utf-8"))
    spath = path + ".state"
    state = json.load(open(spath, encoding="utf-8")) if os.path.exists(spath) else {}
    save = lambda: json.dump(state, open(spath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    live = lambda j: state.get(j["id"], {}).get("uuid") and state[j["id"]].get("status") not in TERMINAL
    if OFF_PEAK:
        try:
            OFF.update(json.loads(curl([BASE + "/pricing"]))["off_peak"])
        except Exception as e:
            print(f"[off-peak] GET /pricing failed ({e}); assuming {OFF['start']}-{OFF['end']} {OFF['timezone']}", flush=True)
        if not OFF.get("enabled"):
            sys.exit("[off-peak] GET /pricing says off-peak pricing is not enabled; run without --off-peak")
    elif any(not live(j) and not os.path.exists(j["out"]) for j in jobs):  # something to submit, at full price
        try:
            o = json.loads(curl([BASE + "/pricing"])).get("off_peak") or {}
            if o.get("enabled") and not o.get("active_now"):
                print(f"  tip: --off-peak submits only {o.get('start')}-{o.get('end')} {o.get('timezone')}, when API tasks "
                      f"cost half", flush=True)
        except Exception:
            pass
    waiting = None
    while True:
        pending = [j for j in jobs if not os.path.exists(j["out"]) and state.get(j["id"], {}).get("status") != "failed_final"]
        if not pending:
            break
        for j in [j for j in pending if live(j)]:  # poll
            st = state[j["id"]]
            try:
                t = json.loads(curl([f"{BASE}/tasks/{st['uuid']}"]))
            except Exception:
                continue
            st["status"] = t.get("status", st.get("status"))
            if st["status"] == "completed":
                os.makedirs(os.path.dirname(j["out"]) or ".", exist_ok=True)
                base, ext = os.path.splitext(j["out"])
                for k, o in reversed(list(enumerate(t["outputs"]))):  # several outputs (multi-angle): out_1, out_2, …; out last
                    subprocess.run(["curl", "-s", "-L", "-H", f"Authorization: Bearer {KEY}", "-o",
                                    j["out"] if k == 0 else f"{base}_{k}{ext}", o["download_url"]])
                print(f"[done] {j['id']} -> {j['out']}", flush=True)
            elif st["status"] in TERMINAL:  # failed tasks are refunded automatically; retry up to 3 times
                st["fails"] = st.get("fails", 0) + 1
                print(f"[{st['status']}] {j['id']} {t.get('error') or t.get('message') or ''}", flush=True)
                if st["fails"] >= 3:
                    st.update(status="failed_final", sent=fingerprint(j))
                else:
                    st.pop("uuid")
            save()
        inflight = [j for j in pending if live(j)]
        wait = off_peak_wait() if OFF_PEAK else 0
        if OFF_PEAK and (waiting is None or bool(wait) != bool(waiting)):
            print(f"[off-peak] waiting {wait // 3600}h{wait % 3600 // 60:02d}m for {OFF['start']}-{OFF['end']} {OFF['timezone']}"
                  if wait else "[off-peak] window open, submitting", flush=True)
        waiting = wait
        for j in [] if wait else pending:  # submit
            if len(inflight) >= cap():  # tasks already running past AIP_MAX_UNTIL finish; no new ones until below the cap
                break
            st = state.setdefault(j["id"], {})
            if live(j) or os.path.exists(j["out"]) or st.get("status") == "failed_final":
                continue
            try:
                r = submit(j)
            except Exception as e:
                print(f"[submit-err] {j['id']} {e}", flush=True)
                break
            if "task_uuid" in r:
                st.update(uuid=r["task_uuid"], status="submitted", credits=r.get("credits_charged"))
                if r.get("off_peak_discount"):
                    st["off_peak"] = True
                inflight.append(j)
                print(f"[submit] {j['id']} {r['task_uuid']} credits={r.get('credits_charged')}"
                      f"{' (off-peak)' if r.get('off_peak_discount') else ''} left={r.get('remaining_credits')}", flush=True)
            else:
                print(f"[reject] {j['id']} {r}", flush=True)
                if r.get("error_code") in ("concurrency_limit", "rate_limited", "too_many_requests"):
                    break  # wait for the running task, do not hammer
                # what was sent is remembered: make_jobs.py lets the job go again only once its fields have changed,
                # so a prompt that content review rejected is never resent as it is
                st.update(status="failed_final", error=r.get("error_code"), sent=fingerprint(j))
            save()
        time.sleep(10 if inflight or not wait else min(wait, 600))
    print("ALL DONE", flush=True)
    for j in jobs:
        print(j["id"], "OK" if os.path.exists(j["out"]) else "MISSING")


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")][0])

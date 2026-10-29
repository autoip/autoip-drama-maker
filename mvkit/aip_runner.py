"""AutoIP job runner: keeps <= AIP_MAX tasks in flight, polls, downloads. Resumable.

usage: python mvkit/aip_runner.py jobs.json
env:   AUTOIP_API_KEY (required), AUTOIP_BASE_URL (default https://autoip.app), AIP_MAX (default 1)
       AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1: allow AIP_MAX tasks only until that local time, then AIP_MAX_AFTER
       AIP_OFFPEAK=1: submit only inside AutoIP's off-peak window (GET /pricing: 03:00-09:00 Asia/Taipei from 2026-10-30),
       where API tasks cost half. Outside it the runner keeps polling running tasks and waits for the next window.

jobs.json: [{"id": "...", "endpoint": "/videos/lip-sync", "fields": {...},
             "files": {"image": "path", "images[]": ["p1", "p2"]}, "out": "path.mp4"}]
State lives in jobs.json.state; a job whose `out` file exists is skipped, so delete the output to redo it.
Credits are charged at submit and there is no cancel endpoint: review stills before submitting video jobs.
"""
import datetime, json, os, subprocess, sys, time

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


OFFPEAK = os.environ.get("AIP_OFFPEAK", "") not in ("", "0")
MARGIN = 2  # minutes: stop submitting this long before the window ends (the submit time decides the price)


def cap():
    return MAX_INFLIGHT if DEADLINE is None or time.time() < DEADLINE else AFTER
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


def offpeak_window():
    """AutoIP's off-peak window from GET /pricing: (on, start, end, timezone); the announced 03:00-09:00 UTC+8 if missing."""
    try:
        o = json.loads(curl([BASE + "/pricing"])).get("off_peak") or {}
    except ValueError:
        o = {}
    return o.get("enabled", True), o.get("start", "03:00"), o.get("end", "09:00"), o.get("timezone", "Asia/Taipei")


def offpeak_wait(win):
    """Seconds until tasks can be submitted at the off-peak price; 0 = now (or no off-peak pricing to wait for)."""
    on, start, end, tz = win
    if not on:
        return 0
    try:
        from zoneinfo import ZoneInfo
        now = datetime.datetime.now(ZoneInfo(tz))
    except Exception:  # no time zone database (Windows without tzdata): the window is announced in UTC+8
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    m = now.hour * 60 + now.minute + now.second / 60
    s, e = (int(x[:2]) * 60 + int(x[3:5]) for x in (start, end))
    e -= MARGIN
    inside = s <= m < e if s < e else (m >= s or m < e)
    return 0 if inside else ((s - m) % 1440) * 60


def main(path):
    jobs = json.load(open(path, encoding="utf-8"))
    spath = path + ".state"
    state = json.load(open(spath, encoding="utf-8")) if os.path.exists(spath) else {}
    save = lambda: json.dump(state, open(spath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    live = lambda j: state.get(j["id"], {}).get("uuid") and state[j["id"]].get("status") not in TERMINAL
    win, waiting = offpeak_window(), False
    if not OFFPEAK and win[0] and offpeak_wait(win):
        print(f"  tip: AIP_OFFPEAK=1 submits only {win[1]}-{win[2]} {win[3]}, when API tasks cost half", flush=True)
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
                    st["status"] = "failed_final"
                else:
                    st.pop("uuid")
            save()
        inflight = [j for j in pending if live(j)]
        wait = OFFPEAK and offpeak_wait(win)
        if wait and not waiting:
            print(f"[off-peak] waiting {wait / 3600:.1f} h for {win[1]}-{win[2]} {win[3]}; running tasks still finish", flush=True)
        waiting = bool(wait)
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
                st.update(uuid=r["task_uuid"], status="submitted", credits=r.get("credits_charged"),
                          off_peak=bool(r.get("off_peak_discount")))
                inflight.append(j)
                print(f"[submit] {j['id']} {r['task_uuid']} credits={r.get('credits_charged')}{' (off-peak)' if st['off_peak'] else ''}"
                      f" left={r.get('remaining_credits')}", flush=True)
            else:
                print(f"[reject] {j['id']} {r}", flush=True)
                if r.get("error_code") in ("concurrency_limit", "rate_limited", "too_many_requests"):
                    break  # wait for the running task, do not hammer
                st["status"] = "failed_final"
            save()
        time.sleep(10)
    print("ALL DONE", flush=True)
    for j in jobs:
        print(j["id"], "OK" if os.path.exists(j["out"]) else "MISSING")


if __name__ == "__main__":
    main(sys.argv[1])

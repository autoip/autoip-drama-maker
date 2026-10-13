"""AutoIP job runner: keeps <= AIP_MAX tasks in flight, polls, downloads. Resumable.

usage: python mvkit/aip_runner.py jobs.json
env:   AUTOIP_API_KEY (required), AUTOIP_BASE_URL (default https://autoip.app), AIP_MAX (default 1)

jobs.json: [{"id": "...", "endpoint": "/videos/lip-sync", "fields": {...},
             "files": {"image": "path", "images[]": ["p1", "p2"]}, "out": "path.mp4"}]
State lives in jobs.json.state; a job whose `out` file exists is skipped, so delete the output to redo it.
Credits are charged at submit and there is no cancel endpoint: review stills before submitting video jobs.
"""
import json, os, subprocess, sys, time

BASE = os.environ.get("AUTOIP_BASE_URL", "https://autoip.app").rstrip("/") + "/api/v1"
KEY = os.environ.get("AUTOIP_API_KEY", "")
MAX_INFLIGHT = int(os.environ.get("AIP_MAX", "1"))  # most accounts allow one running task
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
                subprocess.run(["curl", "-s", "-L", "-H", f"Authorization: Bearer {KEY}", "-o", j["out"],
                                t["outputs"][0]["download_url"]])
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
        for j in pending:  # submit
            if len(inflight) >= MAX_INFLIGHT:
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
                st.update(uuid=r["task_uuid"], status="submitted")
                inflight.append(j)
                print(f"[submit] {j['id']} {r['task_uuid']} credits={r.get('credits_charged')} left={r.get('remaining_credits')}", flush=True)
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

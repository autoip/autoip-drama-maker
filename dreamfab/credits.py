"""Credits spent per job folder: lists your AutoIP tasks and attributes each to the *.state files that reference it.

usage: python dreamfab/credits.py JOBDIR [JOBDIR ...]
env:   AUTOIP_API_KEY, AUTOIP_BASE_URL
"""
import glob, json, os, re, sys, urllib.request
from collections import defaultdict

BASE = os.environ.get("AUTOIP_BASE_URL", "https://autoip.app").rstrip("/") + "/api/v1"
KEY = os.environ.get("AUTOIP_API_KEY") or sys.exit("set AUTOIP_API_KEY")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + KEY})
    return json.load(urllib.request.urlopen(req, timeout=60))


owner = {}
for d in sys.argv[1:]:
    for f in glob.glob(os.path.join(d, "**", "*.state"), recursive=True):
        for u in UUID.findall(open(f, encoding="utf-8", errors="replace").read()):
            owner[u] = d

tasks, page = [], 1
while True:
    r = get(f"/tasks?per_page=100&page={page}")
    items = r.get("data") or r.get("tasks") or r.get("items") or []
    tasks += items
    meta = r.get("meta") or r.get("pagination") or {}
    last = meta.get("last_page") or meta.get("total_pages")
    if not items or (last and page >= last):
        break
    page += 1

tot = defaultdict(lambda: [0, 0])
for t in tasks:
    u = t.get("task_uuid") or t.get("uuid")
    if u in owner:
        net = (t.get("credits_charged") or 0) - (t.get("credits_refunded") or 0)
        tot[owner[u]][0] += 1; tot[owner[u]][1] += net
for d, (n, c) in sorted(tot.items()):
    print(f"{d}: {n} tasks, {c} credits")
print("total", sum(c for _, c in tot.values()))

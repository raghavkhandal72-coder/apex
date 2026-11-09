import os
import urllib.request
import json

TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "raghavkhandal72-coder/apex"
req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/actions/runs?per_page=4",
    headers={"Authorization": f"token {TOKEN}", "User-Agent": "Apex-Agent"}
)
runs = json.loads(urllib.request.urlopen(req).read())["workflow_runs"]
for r in runs:
    print(f"{r['id']} | {r['name']} | branch={r['head_branch']} | status={r['status']} | conclusion={r['conclusion']} | commit={r['head_sha'][:7]}")
    j_req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/runs/{r['id']}/jobs",
        headers={"Authorization": f"token {TOKEN}", "User-Agent": "Apex-Agent"}
    )
    try:
        jobs = json.loads(urllib.request.urlopen(j_req).read()).get("jobs", [])
        for j in jobs:
            print(f"   └─ {j['name']} | status={j['status']} | conclusion={j['conclusion']}")
    except Exception:
        pass


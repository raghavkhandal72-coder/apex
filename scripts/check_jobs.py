import os
import urllib.request
import json

TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "raghavkhandal72-coder/apex"
for run_id in [42616697943, 42616697940]:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs",
        headers={"Authorization": f"token {TOKEN}", "User-Agent": "Apex-Agent"}
    )
    jobs = json.loads(urllib.request.urlopen(req).read())["jobs"]
    for j in jobs:
        print(f"{run_id} | {j['name']} | status={j['status']} | conclusion={j['conclusion']}")


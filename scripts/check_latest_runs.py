import os
import urllib.request
import json

TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "raghavkhandal72-coder/apex"
req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/actions/runs?per_page=6",
    headers={"Authorization": f"token {TOKEN}", "User-Agent": "Apex-Agent"}
)
runs = json.loads(urllib.request.urlopen(req).read())["workflow_runs"]
for r in runs:
    print(f"{r['id']} | {r['name']} | branch={r['head_branch']} | status={r['status']} | conclusion={r['conclusion']} | commit={r['head_sha'][:7]}")

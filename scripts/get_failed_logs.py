#!/usr/bin/env python3
"""
Fetch failure logs from GitHub Actions.
"""

import json
import os
import sys
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "raghavkhandal72-coder/apex"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Apex-Agent",
}

RUNS = [42408124893, 42408124864]

for run_id in RUNS:
    url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        jobs = json.loads(resp.read().decode("utf-8"))["jobs"]

    for j in jobs:
        print("=" * 60)
        print(f"Run {run_id} | Job {j['id']}: {j['name']} | Conclusion: {j['conclusion']}")
        print("=" * 60)
        log_url = f"https://api.github.com/repos/{REPO}/actions/jobs/{j['id']}/logs"
        log_req = urllib.request.Request(log_url, headers=HEADERS)
        try:
            # Custom opener that drops Authorization header on redirect to storage
            class NoAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    m = req.get_method()
                    new_req = urllib.request.Request(newurl, method=m)
                    # Do not pass Authorization header to external redirect (Azure Blob)
                    for k, v in req.headers.items():
                        if k.lower() != "authorization":
                            new_req.add_header(k, v)
                    return new_req

            opener = urllib.request.build_opener(NoAuthRedirectHandler)
            with opener.open(log_req, timeout=15) as lresp:
                text = lresp.read().decode("utf-8", errors="replace")
                lines = text.splitlines()
                print("Last 25 lines of log:")
                for l in lines[-25:]:
                    print("  ", l)
        except Exception as e:
            print("Could not fetch log:", e)

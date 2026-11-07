#!/usr/bin/env python3
"""
Inspect GitHub Actions runs and identify why PR or workflow run failed.
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


def main():
    try:
        url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=10"
        req = urllib.request.Request(url, headers=HEADERS)

        with urllib.request.urlopen(req, timeout=15) as resp:
            runs = json.loads(resp.read().decode("utf-8"))["workflow_runs"]

        print(f"Total runs fetched: {len(runs)}")
        for r in runs:
            print(f"ID: {r['id']} | Workflow: {r['name']} | Event: {r['event']} | Status: {r['status']} | Conclusion: {r['conclusion']}")
            print(f"   Commit: {r['head_commit']['message'][:50] if r.get('head_commit') else 'N/A'}")
            print(f"   URL: {r['html_url']}")

            if r.get("conclusion") == "failure":
                # Fetch jobs for this failed run
                jobs_url = r["jobs_url"]
                jreq = urllib.request.Request(jobs_url, headers=HEADERS)
                try:
                    with urllib.request.urlopen(jreq, timeout=15) as jresp:
                        jobs = json.loads(jresp.read().decode("utf-8"))["jobs"]
                        for job in jobs:
                            if job.get("conclusion") == "failure":
                                print(f"   --> FAILED JOB: {job['name']}")
                                for step in job.get("steps", []):
                                    if step.get("conclusion") == "failure":
                                        print(f"       --> FAILED STEP: {step['name']}")
                except Exception as je:
                    print(f"   --> Could not fetch jobs: {je}")
    except Exception as e:
        print(f"Error in check_pr_runs: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

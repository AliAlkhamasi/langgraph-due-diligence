"""End-to-end test of the FastAPI + SSE pipeline.

Starts an analysis, streams events to stdout, fetches the final report.
Assumes the API is running on http://127.0.0.1:8000.
"""
from __future__ import annotations

import json
import sys
import time

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API = "http://127.0.0.1:8000"


def main(repo_url: str = "https://github.com/pallets/flask") -> None:
    print(f"--- POST {API}/analyze ---")
    r = requests.post(f"{API}/analyze", json={"repo_url": repo_url}, timeout=10)
    r.raise_for_status()
    aid = r.json()["analysis_id"]
    print(f"  analysis_id: {aid}")

    print(f"\n--- GET {API}/analyze/{aid}/stream ---")
    t0 = time.perf_counter()
    saw_complete = False
    saw_error = False
    with requests.get(f"{API}/analyze/{aid}/stream", stream=True, timeout=300) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            if not raw.startswith("data:"):
                continue
            try:
                ev = json.loads(raw[5:].lstrip())
            except json.JSONDecodeError:
                print(f"  [bad event] {raw}")
                continue
            kind = ev.get("type")
            elapsed = time.perf_counter() - t0
            if kind == "node_start":
                team = f" ({ev['team']})" if ev.get("team") else ""
                print(f"  +{elapsed:5.1f}s  start    {ev['node']}{team}")
            elif kind == "node_complete":
                team = f" ({ev['team']})" if ev.get("team") else ""
                print(f"  +{elapsed:5.1f}s  done     {ev['node']}{team}  -> {ev.get('summary', '')}")
            elif kind == "team_complete":
                print(f"  +{elapsed:5.1f}s  TEAM     {ev['team']}  overall={ev.get('overall_score')}/10  scores={ev.get('scores')}")
            elif kind == "report_ready":
                rep = ev.get("report") or {}
                print(f"  +{elapsed:5.1f}s  REPORT   {rep.get('recommendation')}  overall={rep.get('overall_score')}/10")
            elif kind == "complete":
                usage = ev.get("usage") or {}
                print(f"  +{elapsed:5.1f}s  COMPLETE calls={usage.get('calls')} cost=${usage.get('cost_usd')}")
                saw_complete = True
            elif kind == "error":
                print(f"  +{elapsed:5.1f}s  ERROR    {ev.get('message')}")
                saw_error = True
            else:
                print(f"  +{elapsed:5.1f}s  ?        {ev}")

    if saw_error:
        print("\nrun ended with error")
        sys.exit(1)
    if not saw_complete:
        print("\nrun ended without 'complete' event")
        sys.exit(2)

    print(f"\n--- GET {API}/analyze/{aid} ---")
    r = requests.get(f"{API}/analyze/{aid}", timeout=10)
    r.raise_for_status()
    data = r.json()
    print(f"  status: {data['status']}")
    final = data.get("final") or {}
    print(f"  recommendation: {final.get('recommendation')}")
    print(f"  overall_score:  {final.get('overall_score')}")
    print(f"  veto: {final.get('veto')}")
    md = final.get("report_markdown", "")
    print(f"  report_markdown: {len(md)} chars")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask"
    main(url)

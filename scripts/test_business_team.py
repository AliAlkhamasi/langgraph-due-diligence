"""Standalone test for the Business team subgraph."""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm import print_usage_summary, reset_usage  # noqa: E402
from src.teams.business_team import build_business_team_graph  # noqa: E402
from src.tools.repo import cleanup_repo, clone_repo  # noqa: E402


def main(repo_url: str = "https://github.com/pallets/flask") -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reset_usage()
    print(f"--- business team subgraph: {repo_url} ---\n")
    path = clone_repo(repo_url)
    try:
        graph = build_business_team_graph()
        input_state = {"repo_url": repo_url, "repo_path": path}

        print("streaming node updates:")
        t0 = time.perf_counter()
        final = None
        for event in graph.stream(input_state, stream_mode="updates"):
            for node, update in event.items():
                keys = list(update.keys()) if isinstance(update, dict) else []
                print(f"  [{node}] -> {keys}")
                if isinstance(update, dict) and "business_team_report" in update:
                    final = update
        elapsed = time.perf_counter() - t0
        print(f"\nelapsed: {elapsed:.2f}s\n")

        report = (final or {}).get("business_team_report") or {}
        print(f"overall_score: {report.get('overall_score')}/10")
        print(f"scores:        {report.get('scores')}")
        print(f"\nreadme:        {report.get('readme_analysis', {}).get('summary')}")
        print(f"\ncontributors:  {report.get('contributor_activity', {}).get('summary')}")
        print(f"\nissues:        {report.get('issue_health', {}).get('summary')}")
    finally:
        cleanup_repo(path)
        print_usage_summary()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask"
    main(url)

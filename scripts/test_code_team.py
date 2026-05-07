"""Standalone test for the Code team subgraph."""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm import print_usage_summary, reset_usage  # noqa: E402
from src.teams.code_team import build_code_team_graph  # noqa: E402
from src.tools.repo import cleanup_repo, clone_repo  # noqa: E402


def main(repo_url: str = "https://github.com/pallets/flask") -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reset_usage()
    print(f"--- code team subgraph: {repo_url} ---\n")
    path = clone_repo(repo_url)
    try:
        graph = build_code_team_graph()
        input_state = {"repo_url": repo_url, "repo_path": path}

        print("streaming node updates:")
        for event in graph.stream(input_state, stream_mode="updates"):
            for node, update in event.items():
                keys = list(update.keys()) if isinstance(update, dict) else []
                print(f"  [{node}] -> {keys}")

        t0 = time.perf_counter()
        final = graph.invoke(input_state)
        elapsed = time.perf_counter() - t0
        print(f"\nelapsed (full second pass, mostly cached): {elapsed:.2f}s\n")

        report = final.get("code_team_report") or {}
        print(f"overall_score: {report.get('overall_score')}/10")
        print(f"scores:        {report.get('scores')}")
        print(f"\nsummary:\n{report.get('summary')}")
    finally:
        cleanup_repo(path)
        print_usage_summary()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask"
    main(url)

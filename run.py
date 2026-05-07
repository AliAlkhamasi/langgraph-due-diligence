"""End-to-end run of the top-level due-diligence graph."""
from __future__ import annotations

import logging
import sys
import time

from src.graph import build_graph
from src.llm import print_usage_summary, reset_usage


def main(repo_url: str = "https://github.com/pallets/flask") -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reset_usage()

    graph = build_graph()
    print(f"--- analyzing {repo_url} ---\n")

    t0 = time.perf_counter()
    final = None
    for event in graph.stream({"repo_url": repo_url}, stream_mode="updates"):
        for node, update in event.items():
            keys = list(update.keys()) if isinstance(update, dict) else []
            print(f"  [{node}] -> {keys}")
            if isinstance(update, dict) and "final_report_markdown" in update:
                final = update
    elapsed = time.perf_counter() - t0

    print(f"\nelapsed: {elapsed:.2f}s")
    if final:
        print(f"\nrecommendation: {final.get('final_recommendation')}\n")
        print(final.get("final_report_markdown", "(no report)"))
    print_usage_summary()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask"
    main(url)

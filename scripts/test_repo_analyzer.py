"""Standalone test for src/agents/repo_analyzer.py.

Clones the given repo, runs the analyzer, prints the result, cleans up.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging  # noqa: E402

from src.agents.repo_analyzer import analyze_repo  # noqa: E402
from src.llm import print_usage_summary, reset_usage  # noqa: E402
from src.tools.repo import cleanup_repo, clone_repo  # noqa: E402


def main(repo_url: str = "https://github.com/pallets/flask") -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reset_usage()
    print(f"--- repo analyzer: {repo_url} ---\n")
    path = clone_repo(repo_url)
    try:
        t0 = time.perf_counter()
        result = analyze_repo(repo_url, path)
        elapsed = time.perf_counter() - t0
        print(f"\nelapsed: {elapsed:.2f}s")
        compact = {k: v for k, v in result.items() if k not in ("structure", "languages", "file_breakdown")}
        print(json.dumps(compact, indent=2))
        print(f"\nlanguages: {result['languages']}")
        print(f"top file types: {dict(list(result['file_breakdown'].items())[:6])}")
        print(f"\nLLM summary: {result['summary']}")
        print(f"LLM score:   {result['score']}/10")
    finally:
        cleanup_repo(path)
        print_usage_summary()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask"
    main(url)

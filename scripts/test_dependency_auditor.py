"""Standalone test for src/agents/dependency_auditor.py."""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.dependency_auditor import audit_dependencies  # noqa: E402
from src.llm import print_usage_summary, reset_usage  # noqa: E402
from src.tools.repo import cleanup_repo, clone_repo  # noqa: E402


def main(repo_url: str = "https://github.com/pallets/flask") -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reset_usage()
    print(f"--- dependency auditor: {repo_url} ---\n")
    path = clone_repo(repo_url)
    try:
        t0 = time.perf_counter()
        result = audit_dependencies(path)
        elapsed = time.perf_counter() - t0
        print(f"\nelapsed: {elapsed:.2f}s\n")
        print(f"ecosystem:        {result['ecosystem']}")
        print(f"manifests:        {result['manifests_found']}")
        print(f"runtime ({len(result['runtime_deps'])}):  {result['runtime_deps'][:10]}")
        print(f"dev ({len(result['dev_deps'])}):      {result['dev_deps'][:10]}")
        print(f"total:            {result['total_count']}")
        print(f"\nLLM summary: {result['summary']}")
        print(f"LLM score:   {result['score']}/10")
    finally:
        cleanup_repo(path)
        print_usage_summary()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask"
    main(url)

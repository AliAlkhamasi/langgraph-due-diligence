"""Standalone test for src/agents/security_scanner.py."""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.security_scanner import scan_security  # noqa: E402
from src.llm import print_usage_summary, reset_usage  # noqa: E402
from src.tools.repo import cleanup_repo, clone_repo  # noqa: E402


def main(repo_url: str = "https://github.com/pallets/flask") -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reset_usage()
    print(f"--- security scanner: {repo_url} ---\n")
    path = clone_repo(repo_url)
    try:
        t0 = time.perf_counter()
        result = scan_security(repo_url, path)
        elapsed = time.perf_counter() - t0
        print(f"\nelapsed: {elapsed:.2f}s\n")
        print(f"default branch:    {result['default_branch']}")
        print(f"branch protection: {result['branch_protection']}")
        print(f"secrets found:     {len(result['secrets_found'])}")
        if result['secrets_found']:
            print(f"  by type:         {result['secret_count_by_type']}")
            for s in result['secrets_found'][:5]:
                print(f"  - {s['file']}:{s['line']}  [{s['type']}]  {s['snippet']!r}")
        print(f"sensitive files:   {result['sensitive_files']}")
        print(f"\nLLM summary: {result['summary']}")
        print(f"LLM score:   {result['score']}/10")
    finally:
        cleanup_repo(path)
        print_usage_summary()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask"
    main(url)

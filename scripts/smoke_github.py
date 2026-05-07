"""Standalone smoke test for src/tools/github.py.

Usage:
    python scripts/smoke_github.py [owner/repo]

Hits a handful of endpoints against the given (or default) repo, exercising
auth, caching, and rate-limit logging.
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools import github  # noqa: E402


def fmt_count(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, list):
        return str(len(value))
    return str(value)


def main(slug: str = "pallets/flask") -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    owner, repo = github.parse_repo_url(f"https://github.com/{slug}")
    print(f"--- testing against {owner}/{repo} ---\n")

    user = github.verify_token()
    print(f"auth ok, token belongs to: {user.get('login')}")

    print("\nfirst pass (cache cold):")
    t0 = time.perf_counter()
    meta = github.get_repo(owner, repo)
    langs = github.get_languages(owner, repo)
    contributors = github.get_contributors(owner, repo, per_page=10)
    commits = github.get_commits(owner, repo, per_page=5)
    issues = github.get_issues(owner, repo, state="open", per_page=5)
    pulls = github.get_pulls(owner, repo, state="open", per_page=5)
    readme = github.get_readme(owner, repo)
    cold = time.perf_counter() - t0
    print(f"  elapsed: {cold:.2f}s")

    print("\nsecond pass (cache warm):")
    t0 = time.perf_counter()
    github.get_repo(owner, repo)
    github.get_languages(owner, repo)
    github.get_contributors(owner, repo, per_page=10)
    github.get_commits(owner, repo, per_page=5)
    github.get_issues(owner, repo, state="open", per_page=5)
    github.get_pulls(owner, repo, state="open", per_page=5)
    github.get_readme(owner, repo)
    warm = time.perf_counter() - t0
    print(f"  elapsed: {warm:.2f}s  (speedup: {cold / max(warm, 1e-6):.0f}x)")

    print("\n--- summary ---")
    print(f"  stars:               {meta.get('stargazers_count') if meta else 'n/a'}")
    print(f"  forks:               {meta.get('forks_count') if meta else 'n/a'}")
    print(f"  language:            {meta.get('language') if meta else 'n/a'}")
    print(f"  license:             {(meta.get('license') or {}).get('spdx_id') if meta else 'n/a'}")
    print(f"  default_branch:      {meta.get('default_branch') if meta else 'n/a'}")
    print(f"  pushed_at:           {meta.get('pushed_at') if meta else 'n/a'}")
    print(f"  language breakdown:  {len(langs) if langs else 0} languages")
    print(f"  contributors (top):  {fmt_count(contributors)}")
    print(f"  recent commits:      {fmt_count(commits)}")
    print(f"  open issues:         {fmt_count(issues)}")
    print(f"  open pulls:          {fmt_count(pulls)}")
    print(f"  readme present:      {readme is not None}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "pallets/flask"
    main(arg)

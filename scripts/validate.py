"""Validation harness — runs the full pipeline on a fixed set of repos and
prints a side-by-side comparison. No code changes; pure observation.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph import build_graph  # noqa: E402
from src.llm import get_usage, print_usage_summary, reset_usage  # noqa: E402

REPOS: list[tuple[str, str, str]] = [
    ("flask", "https://github.com/pallets/flask", "healthy mature"),
    ("requests-oauthlib", "https://github.com/requests/requests-oauthlib", "abandoned"),
    ("fastapi", "https://github.com/tiangolo/fastapi", "single-maintainer"),
    ("autoresearch", "https://github.com/karpathy/autoresearch", "young trending"),
]


def run_one(url: str) -> tuple[dict, float, float]:
    pre = get_usage().cost_usd
    t0 = time.perf_counter()
    graph = build_graph()
    final = graph.invoke({"repo_url": url})
    elapsed = time.perf_counter() - t0
    return final, elapsed, get_usage().cost_usd - pre


def extract(final: dict) -> dict:
    code = final.get("code_team_report") or {}
    biz = final.get("business_team_report") or {}
    contrib = biz.get("contributor_activity") or {}
    issues = biz.get("issue_health") or {}
    sec = code.get("security_scan") or {}
    deps = code.get("dependency_audit") or {}
    repo_a = code.get("repo_analysis") or {}

    md = final.get("final_report_markdown", "")
    risks = []
    if "## Risks" in md:
        chunk = md.split("## Risks", 1)[1].split("\n##", 1)[0]
        for line in chunk.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                risks.append(stripped[2:])

    return {
        "recommendation": final.get("final_recommendation"),
        "overall_score": final.get("overall_score"),
        "code_scores": code.get("scores") or {},
        "biz_scores": biz.get("scores") or {},
        "bus_factor": contrib.get("bus_factor"),
        "active_contributors": contrib.get("active_contributors"),
        "days_since_last_commit": contrib.get("days_since_last_commit"),
        "activity_bucket": contrib.get("activity_bucket"),
        "median_close_days": issues.get("median_close_days"),
        "stale_open": issues.get("stale_open_count"),
        "merge_ratio": issues.get("merge_ratio"),
        "secrets_found": len(sec.get("secrets_found") or []),
        "loc": repo_a.get("loc"),
        "deps_count": deps.get("total_count"),
        "top_risks": risks[:3],
    }


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    reset_usage()

    Path("reports").mkdir(exist_ok=True)
    rows: list[dict] = []

    for name, url, profile in REPOS:
        print(f"\n{'=' * 70}")
        print(f"running {url}  ({profile})")
        print("=" * 70)
        try:
            final, elapsed, cost = run_one(url)
            Path(f"reports/{name}.md").write_text(
                final.get("final_report_markdown", ""), encoding="utf-8"
            )
            data = extract(final)
            data["name"] = name
            data["repo"] = url.split("github.com/")[-1]
            data["profile"] = profile
            data["elapsed"] = elapsed
            data["cost"] = cost
            rows.append(data)
            print(
                f"  -> {data['recommendation']:<20}  overall={data['overall_score']}/10  "
                f"({elapsed:.1f}s, ${cost:.4f})"
            )
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            rows.append({"name": name, "repo": url.split("github.com/")[-1], "profile": profile, "error": str(e)})

    print("\n\n" + "=" * 70)
    print("COMPARISON TABLE")
    print("=" * 70)
    print()
    print(f"| {'repo':<32} | {'profile':<18} | {'rec':<20} | {'overall':<7} | {'bus':<4} | {'days':<5} | {'stale':<5} | {'secrets':<7} |")
    print(f"|{'-' * 34}|{'-' * 20}|{'-' * 22}|{'-' * 9}|{'-' * 6}|{'-' * 7}|{'-' * 7}|{'-' * 9}|")
    for r in rows:
        if "error" in r:
            print(f"| {r['repo']:<32} | {r['profile']:<18} | ERROR: {r['error'][:30]}")
            continue
        print(
            f"| {r['repo']:<32} | {r['profile']:<18} | {str(r['recommendation']):<20} | "
            f"{str(r['overall_score']):<7} | {str(r['bus_factor']):<4} | "
            f"{str(r['days_since_last_commit']):<5} | {str(r['stale_open']):<5} | "
            f"{str(r['secrets_found']):<7} |"
        )

    print("\n\nDETAILED SCORES PER DIMENSION:\n")
    print(f"| {'repo':<32} | {'repo':<5} | {'deps':<5} | {'sec':<5} | {'docs':<5} | {'contrib':<7} | {'issues':<6} |")
    print(f"|{'-' * 34}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 9}|{'-' * 8}|")
    for r in rows:
        if "error" in r:
            continue
        cs = r.get("code_scores") or {}
        bs = r.get("biz_scores") or {}
        print(
            f"| {r['repo']:<32} | {str(cs.get('repo', '-')):<5} | "
            f"{str(cs.get('dependencies', '-')):<5} | {str(cs.get('security', '-')):<5} | "
            f"{str(bs.get('documentation', '-')):<5} | {str(bs.get('contributors', '-')):<7} | "
            f"{str(bs.get('issues', '-')):<6} |"
        )

    print("\n\nTOP 3 RISKS PER REPO:\n")
    for r in rows:
        if "error" in r:
            continue
        print(f"\n{r['repo']} ({r['profile']}, rec={r['recommendation']}):")
        for risk in r.get("top_risks", []):
            print(f"  - {risk}")

    print_usage_summary("\n")


if __name__ == "__main__":
    main()

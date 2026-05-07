"""Issue Health — pipeline node.

Samples open + recently-closed issues, derives:
  - open / closed counts
  - median time-to-close (days) on the recent sample
  - stale issue count (open + no update for 90+ days)
  - PR merge ratio (merged / closed)

GitHub's /issues endpoint mixes issues and PRs; we filter pure issues by
checking for the ``pull_request`` key, which is only present on PR rows.
"""
from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.llm import get_llm
from src.tools import github

logger = logging.getLogger(__name__)

STALE_DAYS = 90
MAX_OPEN_PAGES = 3


class _IssueAssessment(BaseModel):
    summary: str = Field(description="2-3 sentence assessment of issue/PR responsiveness")
    score: int = Field(ge=1, le=10, description="1=neglected, 5=mediocre, 10=exemplary")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def analyze_issues(repo_url: str) -> dict[str, Any]:
    owner, repo = github.parse_repo_url(repo_url)
    logger.info("issue_health: %s/%s", owner, repo)
    now = datetime.now(timezone.utc)

    open_items = github.github_get_paginated(
        f"/repos/{owner}/{repo}/issues",
        params={"state": "open", "per_page": 100},
        max_pages=MAX_OPEN_PAGES,
    )
    open_issues = [i for i in open_items if not i.get("pull_request")]
    open_capped = len(open_items) >= MAX_OPEN_PAGES * 100

    closed_sample = github.github_get(
        f"/repos/{owner}/{repo}/issues",
        params={"state": "closed", "per_page": 100, "sort": "updated", "direction": "desc"},
    ) or []
    closed_issues = [i for i in closed_sample if not i.get("pull_request")]

    close_days: list[float] = []
    for i in closed_issues:
        created = _parse_iso(i.get("created_at"))
        closed = _parse_iso(i.get("closed_at"))
        if created and closed:
            close_days.append((closed - created).total_seconds() / 86400.0)

    median_days = round(statistics.median(close_days), 1) if close_days else None

    stale_count = 0
    for i in open_issues:
        updated = _parse_iso(i.get("updated_at"))
        if updated and (now - updated).days >= STALE_DAYS:
            stale_count += 1

    closed_pr_sample = github.github_get(
        f"/repos/{owner}/{repo}/pulls",
        params={"state": "closed", "per_page": 100, "sort": "updated", "direction": "desc"},
    ) or []
    closed_prs = len(closed_pr_sample)
    merged_prs = sum(1 for p in closed_pr_sample if p.get("merged_at"))
    merge_ratio = round(merged_prs / closed_prs, 2) if closed_prs else None

    open_pulls_sample = github.github_get(
        f"/repos/{owner}/{repo}/pulls",
        params={"state": "open", "per_page": 100},
    ) or []
    open_prs = len(open_pulls_sample)

    prompt = f"""You are evaluating issue/PR responsiveness for an open-source repository.

Open issues sample:    {len(open_issues)}{' (capped at 300)' if open_capped else ''}
Closed-issues sample:  {len(closed_issues)} (most recently updated)
Median time-to-close (days, sample): {median_days}
Stale open issues (no update {STALE_DAYS}+ days): {stale_count}

Pull requests:
  open PRs sampled:    {open_prs}
  closed PRs sampled:  {closed_prs}
  merged of closed:    {merged_prs}
  merge ratio:         {merge_ratio}

Score 1-10:
  1-3  = neglected (huge stale backlog, no closes, abandoned PRs)
  4-6  = mediocre (slow time-to-close, growing staleness)
  7-8  = healthy (reasonable time-to-close, low staleness, active PR merging)
  9-10 = exemplary (fast time-to-close, very low staleness, strong PR throughput)"""

    llm = get_llm().with_structured_output(_IssueAssessment)
    assessment: _IssueAssessment = llm.invoke(prompt)  # type: ignore[assignment]

    return {
        "open_issues_sampled": len(open_issues),
        "open_issues_capped": open_capped,
        "closed_issues_sampled": len(closed_issues),
        "median_close_days": median_days,
        "stale_open_count": stale_count,
        "stale_threshold_days": STALE_DAYS,
        "open_prs_sampled": open_prs,
        "closed_prs_sampled": closed_prs,
        "merged_prs": merged_prs,
        "merge_ratio": merge_ratio,
        "summary": assessment.summary,
        "score": assessment.score,
    }


def issue_health_node(state: dict) -> dict:
    return {"issue_health": analyze_issues(state["repo_url"])}

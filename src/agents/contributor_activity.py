"""Contributor Activity — pipeline node.

Pulls last-year commits via GitHub API (paginated), buckets by author, derives:
  - active contributor count (>=3 commits/year)
  - bus factor (min N committers covering >= 50% of last year's commits)
  - activity bucket: <90d healthy / 90-365d warning / >365d stale

LLM scores the result.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.llm import get_llm
from src.tools import github

logger = logging.getLogger(__name__)


class _ContribAssessment(BaseModel):
    summary: str = Field(description="2-3 sentence assessment of maintainer activity")
    score: int = Field(ge=1, le=10, description="1=abandoned, 5=warning, 10=thriving")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _author_label(commit: dict) -> str | None:
    author = commit.get("author")
    if isinstance(author, dict) and author.get("login"):
        return author["login"]
    git_author = (commit.get("commit") or {}).get("author") or {}
    if git_author.get("name"):
        return git_author["name"]
    return None


def analyze_contributors(repo_url: str) -> dict[str, Any]:
    owner, repo = github.parse_repo_url(repo_url)
    logger.info("contributor_activity: %s/%s", owner, repo)

    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)
    since_iso = one_year_ago.strftime("%Y-%m-%dT%H:%M:%SZ")

    commits = github.github_get_paginated(
        f"/repos/{owner}/{repo}/commits",
        params={"since": since_iso, "per_page": 100},
        max_pages=10,
    )

    counter: Counter[str] = Counter()
    last_commit: datetime | None = None
    for c in commits:
        label = _author_label(c)
        if label:
            counter[label] += 1
        date = _parse_iso(((c.get("commit") or {}).get("author") or {}).get("date"))
        if date and (last_commit is None or date > last_commit):
            last_commit = date

    total = sum(counter.values())
    unique = len(counter)
    active = [a for a, n in counter.items() if n >= 3]

    sorted_authors = counter.most_common()
    bus_factor = 0
    cumulative = 0
    threshold = total * 0.5
    for _, count in sorted_authors:
        bus_factor += 1
        cumulative += count
        if cumulative >= threshold:
            break

    if last_commit:
        days_since = (now - last_commit).days
        if days_since < 90:
            bucket = "healthy (<90d)"
        elif days_since < 365:
            bucket = "warning (90-365d)"
        else:
            bucket = "stale (>365d)"
    else:
        days_since = None
        bucket = "no commits in window"

    sample_truncated = len(commits) >= 1000

    prompt = f"""You are evaluating maintainer activity for an open-source repository.

Last 365 days (since {one_year_ago.date().isoformat()}):
  total commits sampled: {total}{' (sample truncated at 1000)' if sample_truncated else ''}
  unique committers:     {unique}
  active contributors (>=3 commits/year): {len(active)}
  bus factor (committers needed for 50% of commits): {bus_factor}
  top 10 contributors:   {sorted_authors[:10]}

Recency:
  days since last commit: {days_since}
  activity bucket:        {bucket}

Score 1-10:
  1-3  = abandoned (>365d stale, near-zero contributors)
  4-6  = warning (slowing pace, single-contributor risk, bus factor 1)
  7-8  = healthy (active, multiple contributors)
  9-10 = thriving (very active, strong bus factor)"""

    llm = get_llm().with_structured_output(_ContribAssessment)
    assessment: _ContribAssessment = llm.invoke(prompt)  # type: ignore[assignment]

    return {
        "total_commits_last_year": total,
        "unique_committers_last_year": unique,
        "active_contributors": len(active),
        "bus_factor": bus_factor,
        "top_contributors": sorted_authors[:10],
        "days_since_last_commit": days_since,
        "activity_bucket": bucket,
        "sample_truncated": sample_truncated,
        "summary": assessment.summary,
        "score": assessment.score,
    }


def contributor_activity_node(state: dict) -> dict:
    return {"contributor_activity": analyze_contributors(state["repo_url"])}

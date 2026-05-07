"""Repo Analyzer — pipeline node.

Deterministic data collection (GitHub /languages + filesystem walk) followed by
a single LLM call that produces a 2-3 sentence summary and an integer score.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.llm import get_llm
from src.tools import filesystem as fs
from src.tools import github

logger = logging.getLogger(__name__)


class _RepoAssessment(BaseModel):
    summary: str = Field(description="2-3 sentence assessment of code maturity")
    score: int = Field(ge=1, le=10, description="1=alarming, 5=mediocre, 10=exemplary")


def _scan(path: Path) -> dict[str, Any]:
    file_count = 0
    total_loc = 0
    by_ext: dict[str, int] = {}
    largest: list[tuple[int, Path]] = []
    for f in fs.walk_files(path):
        file_count += 1
        ext = f.suffix.lower() or "<noext>"
        by_ext[ext] = by_ext.get(ext, 0) + 1
        try:
            total_loc += fs.count_lines(f)
            largest.append((f.stat().st_size, f))
        except OSError:
            pass
    largest.sort(reverse=True)
    return {
        "file_count": file_count,
        "loc": total_loc,
        "by_ext": dict(sorted(by_ext.items(), key=lambda kv: -kv[1])),
    }


def _detect_tests(path: Path) -> tuple[bool, str | None]:
    for candidate in ("tests", "test", "__tests__", "spec", "specs"):
        p = path / candidate
        if p.is_dir():
            return True, candidate
    return False, None


def _detect_ci(path: Path) -> tuple[bool, list[str]]:
    found: list[str] = []
    workflows = path / ".github" / "workflows"
    if workflows.is_dir():
        for f in workflows.iterdir():
            if f.is_file() and f.suffix.lower() in {".yml", ".yaml"}:
                found.append(f".github/workflows/{f.name}")
    for ci_file in (
        ".gitlab-ci.yml",
        ".circleci/config.yml",
        "azure-pipelines.yml",
        ".travis.yml",
        "Jenkinsfile",
    ):
        if (path / ci_file).exists():
            found.append(ci_file)
    return bool(found), found


def _structure(path: Path) -> list[dict[str, Any]]:
    return [
        {"name": e["name"], "is_dir": e["is_dir"]}
        for e in fs.list_directory(path)
        if not e["name"].startswith(".") or e["name"] in {".github"}
    ]


def analyze_repo(repo_url: str, repo_path: str) -> dict[str, Any]:
    """Run the Repo Analyzer pipeline. Returns the analysis dict."""
    owner, repo = github.parse_repo_url(repo_url)
    logger.info("repo_analyzer: %s/%s", owner, repo)

    languages = github.get_languages(owner, repo) or {}
    primary = max(languages.items(), key=lambda kv: kv[1])[0] if languages else "unknown"

    path = Path(repo_path)
    scan = _scan(path)
    has_tests, tests_path = _detect_tests(path)
    has_ci, ci_files = _detect_ci(path)
    structure = _structure(path)

    top_exts = dict(list(scan["by_ext"].items())[:8])

    prompt = f"""You are evaluating an open-source repository's code-level maturity.

Repository: {owner}/{repo}
Primary language: {primary}
Language byte breakdown: {languages}
Total non-binary files: {scan['file_count']}
Approximate lines of code: {scan['loc']:,}
Top file extensions: {top_exts}
Tests directory present: {has_tests} ({tests_path or "n/a"})
CI configured: {has_ci} ({ci_files or "n/a"})
Top-level layout: {[s['name'] for s in structure]}

Based ONLY on these structural signals, give a 2-3 sentence assessment of the
codebase's maturity (testing discipline, CI hygiene, project organization,
size). Then assign an integer score 1-10:
  1-3  = alarming gaps (no tests, no CI, chaotic layout)
  4-6  = functional but with notable gaps
  7-8  = solid, professional project
  9-10 = exemplary, best-in-class
Do not penalize for things you can't see in the signals above."""

    llm = get_llm().with_structured_output(_RepoAssessment)
    assessment: _RepoAssessment = llm.invoke(prompt)  # type: ignore[assignment]

    return {
        "languages": languages,
        "primary_language": primary,
        "loc": scan["loc"],
        "file_count": scan["file_count"],
        "file_breakdown": scan["by_ext"],
        "has_tests": has_tests,
        "tests_path": tests_path,
        "has_ci": has_ci,
        "ci_files": ci_files,
        "structure": structure,
        "summary": assessment.summary,
        "score": assessment.score,
    }


def repo_analyzer_node(state: dict) -> dict:
    """LangGraph node wrapper — reads repo_url + repo_path from state."""
    return {"repo_analysis": analyze_repo(state["repo_url"], state["repo_path"])}

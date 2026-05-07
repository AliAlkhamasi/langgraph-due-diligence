"""Final Report Writer.

Two deterministic policies wrap the LLM:
  - **Veto:** any single dimension <=2 caps the verdict at AVOID; <=3 caps it at
    ADOPT WITH CAUTION. The LLM is told about the veto so its prose reflects
    the cap, and the cap is enforced server-side regardless.
  - **Young project (<180d):** maturity signals (CI, dev deps, contributor
    diversity) are weighted lower in the verdict prompt and a "Young Project"
    note is rendered into the markdown.

The structured LLM output is intentionally narrow (recommendation, prose,
bullets); veto and age sections are formatted from deterministic state, so
the markdown is consistent across runs.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.llm import get_llm

logger = logging.getLogger(__name__)


_DIMENSION_LABELS: dict[tuple[str, str], str] = {
    ("code", "repo"): "Repo structure",
    ("code", "dependencies"): "Dependencies",
    ("code", "security"): "Security",
    ("biz", "documentation"): "Documentation",
    ("biz", "contributors"): "Contributor activity",
    ("biz", "issues"): "Issue health",
}

_VERDICT_SEVERITY: dict[str, int] = {"ADOPT": 0, "ADOPT WITH CAUTION": 1, "AVOID": 2}
_YOUNG_PROJECT_DAYS = 180


class _FinalReport(BaseModel):
    recommendation: Literal["ADOPT", "ADOPT WITH CAUTION", "AVOID"] = Field(
        description="One verdict only"
    )
    executive_summary: str = Field(
        description="STRICT: 3-4 sentences max, ~80 words total. Justify the verdict."
    )
    strengths: list[str] = Field(
        min_length=2,
        max_length=5,
        description="3-5 short bullets, max one sentence each",
    )
    risks: list[str] = Field(
        min_length=1,
        max_length=5,
        description="2-5 short bullets, max one sentence each",
    )
    code_findings: str = Field(description="STRICT: 2-3 sentences max, ~50 words")
    business_findings: str = Field(description="STRICT: 2-3 sentences max, ~50 words")


def _collect_dimensions(code: dict, biz: dict) -> dict[str, int | None]:
    cs = code.get("scores") or {}
    bs = biz.get("scores") or {}
    return {
        "Repo structure": cs.get("repo"),
        "Dependencies": cs.get("dependencies"),
        "Security": cs.get("security"),
        "Documentation": bs.get("documentation"),
        "Contributor activity": bs.get("contributors"),
        "Issue health": bs.get("issues"),
    }


def _compute_veto(dimensions: dict[str, int | None]) -> dict | None:
    """Return veto info if any dimension scored <=3, else None.

    Veto cap rule:
      score <= 2  -> recommendation must be AVOID
      score <= 3  -> recommendation must be ADOPT WITH CAUTION or AVOID
    """
    worst_dim: str | None = None
    worst_score = 11
    for dim, score in dimensions.items():
        if score is None:
            continue
        if score < worst_score:
            worst_score = score
            worst_dim = dim
    if worst_dim is None or worst_score > 3:
        return None
    cap = "AVOID" if worst_score <= 2 else "ADOPT WITH CAUTION"
    return {"dimension": worst_dim, "score": worst_score, "verdict_cap": cap}


def _apply_cap(
    llm_recommendation: str, veto: dict | None
) -> tuple[str, bool]:
    """Server-side cap: returns (final_recommendation, was_capped)."""
    if not veto:
        return llm_recommendation, False
    cap = veto["verdict_cap"]
    if _VERDICT_SEVERITY[llm_recommendation] < _VERDICT_SEVERITY[cap]:
        return cap, True
    return llm_recommendation, False


def _score_row(label: str, score: Any) -> str:
    if score is None:
        return f"| {label} | — |"
    try:
        n = float(score)
    except (TypeError, ValueError):
        return f"| {label} | {score} |"
    bars = "#" * int(round(n)) + "-" * max(0, 10 - int(round(n)))
    return f"| {label} | {n:.1f}/10  `{bars}` |"


def _build_score_table(code: dict, biz: dict) -> str:
    rows = ["| Dimension | Score |", "|---|---|"]
    cs = code.get("scores") or {}
    bs = biz.get("scores") or {}
    rows.append(_score_row("Repo structure", cs.get("repo")))
    rows.append(_score_row("Dependencies", cs.get("dependencies")))
    rows.append(_score_row("Security", cs.get("security")))
    rows.append(_score_row("Documentation", bs.get("documentation")))
    rows.append(_score_row("Contributor activity", bs.get("contributors")))
    rows.append(_score_row("Issue health", bs.get("issues")))
    rows.append("|---|---|")
    rows.append(_score_row("**Code team avg**", code.get("overall_score")))
    rows.append(_score_row("**Business team avg**", biz.get("overall_score")))
    return "\n".join(rows)


def _fmt_int(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return default


def _summarize_repo_meta(meta: dict, age_days: int | None) -> str:
    license_obj = meta.get("license") or {}
    license_id = license_obj.get("spdx_id") if isinstance(license_obj, dict) else license_obj
    age_line = f"- **Age:** {age_days} days" if age_days is not None else ""
    return "\n".join(
        line for line in [
            f"- **Stars:** {_fmt_int(meta.get('stargazers_count', meta.get('stars')))}",
            f"- **Forks:** {_fmt_int(meta.get('forks_count', meta.get('forks')))}",
            f"- **License:** {license_id or '—'}",
            f"- **Primary language:** {meta.get('language') or '—'}",
            f"- **Default branch:** {meta.get('default_branch') or '—'}",
            f"- **Last push:** {meta.get('pushed_at') or '—'}",
            age_line,
        ]
        if line
    )


def _veto_block(veto: dict, was_capped: bool, llm_recommendation: str) -> str:
    head = f"## Veto Triggered\n\nThis repository scored **{veto['score']}/10** on **{veto['dimension']}**."
    rule = (
        f" Per policy, any single dimension at or below "
        f"{'2/10 forces AVOID' if veto['score'] <= 2 else '3/10 caps the verdict at ADOPT WITH CAUTION'}, "
        "regardless of how strong the other dimensions are."
    )
    cap_note = ""
    if was_capped:
        cap_note = (
            f"\n\nThe LLM-suggested verdict (`{llm_recommendation}`) was overridden to "
            f"**{veto['verdict_cap']}** by this rule. Strong scores in other dimensions do not "
            "compensate for a single failing one — a working OAuth library with abandoned "
            "issue triage is still a liability."
        )
    return head + rule + cap_note


def _young_project_block(age_days: int) -> str:
    return (
        f"> **Young Project ({age_days} days old).** Maturity signals (CI, dev "
        f"dependencies, contributor diversity, PR throughput) were weighted "
        f"lower than for an established repo, since these are naturally weak "
        f"early on. Scores below {_YOUNG_PROJECT_DAYS}-day age threshold should "
        f"be read with that context."
    )


def write_report(
    repo_url: str,
    repo_metadata: dict,
    repo_age_days: int | None,
    code_team_report: dict,
    business_team_report: dict,
) -> dict[str, Any]:
    code = code_team_report or {}
    biz = business_team_report or {}

    code_overall = code.get("overall_score", 0) or 0
    biz_overall = biz.get("overall_score", 0) or 0
    overall = round((code_overall + biz_overall) / 2, 1) if (code_overall or biz_overall) else 0

    dimensions = _collect_dimensions(code, biz)
    veto = _compute_veto(dimensions)
    is_young = repo_age_days is not None and repo_age_days < _YOUNG_PROJECT_DAYS

    veto_section = ""
    if veto:
        veto_section = (
            f"\nVETO IN EFFECT (deterministic, will be enforced server-side):\n"
            f"  Dimension '{veto['dimension']}' scored {veto['score']}/10\n"
            f"  Cap: recommendation must be {veto['verdict_cap']} or stricter\n"
            f"\nIMPORTANT: a separate structured callout will explain the veto rule\n"
            f"and restate the dimension/score. Your executive_summary must NOT\n"
            f"restate the policy mechanics ('Per policy, any single dimension at\n"
            f"or below X/10 forces AVOID...') — that text is rendered elsewhere.\n"
            f"Instead, justify the verdict using the repo's actual situation: what\n"
            f"goes wrong for an adopter when {veto['dimension']} is at {veto['score']}/10.\n"
            f"End the executive_summary BEFORE any sentence that restates the rule.\n"
        )
    else:
        veto_section = "\nNo veto in effect (no dimension scored <=3).\n"

    age_section = ""
    if repo_age_days is not None:
        age_section = f"\nREPO AGE: {repo_age_days} days."
        if is_young:
            age_section += (
                "\n  This is a YOUNG project (<180 days). Naturally weak signals at this age:\n"
                "    - Limited contributor diversity / single primary author\n"
                "    - Sparse CI and dev deps (still being set up)\n"
                "    - Low PR merge ratios (short history)\n"
                "  Weigh these less heavily. Weight code quality, dependency hygiene, and\n"
                "  documentation MORE for young repos. A young project that already lacks\n"
                "  fundamentals (no tests at all, no README) still warrants concern; one\n"
                "  that's just light on CI/contributors does not.\n"
            )

    prompt = f"""You are writing a due-diligence verdict for a tech lead deciding
whether to adopt this open-source library.

Repository: {repo_url}
Code team scores: {code.get('scores')} (avg {code_overall}/10)
Business team scores: {biz.get('scores')} (avg {biz_overall}/10)
Combined overall: {overall}/10
{age_section}{veto_section}

CODE TEAM FINDINGS
  Repo analysis:
    {code.get('repo_analysis', {}).get('summary', '(none)')}
  Dependency audit:
    {code.get('dependency_audit', {}).get('summary', '(none)')}
  Security scan:
    {code.get('security_scan', {}).get('summary', '(none)')}

BUSINESS TEAM FINDINGS
  README/docs:
    {biz.get('readme_analysis', {}).get('summary', '(none)')}
  Contributor activity:
    {biz.get('contributor_activity', {}).get('summary', '(none)')}
  Issue health:
    {biz.get('issue_health', {}).get('summary', '(none)')}

Key data points:
  bus factor: {biz.get('contributor_activity', {}).get('bus_factor')}
  active contributors: {biz.get('contributor_activity', {}).get('active_contributors')}
  days since last commit: {biz.get('contributor_activity', {}).get('days_since_last_commit')}
  median issue close days: {biz.get('issue_health', {}).get('median_close_days')}
  stale open issues: {biz.get('issue_health', {}).get('stale_open_count')}
  secrets found: {len(code.get('security_scan', {}).get('secrets_found') or [])}

Recommendation rules (subject to veto and age policy above):
  ADOPT                 — overall ~7.5+ AND no severe risks
  ADOPT WITH CAUTION    — overall 5-7.4 OR a notable but manageable concern
  AVOID                 — overall <5 OR a severe risk (committed secrets,
                          stale >365d, abandoned, security red flag)

Strengths and risks must be concrete, grounded in the data above (e.g.,
"Bus factor of 1 (davidism = 89% of commits)" not "Maintainer concentration").
Aim for 3-5 of each."""

    llm = get_llm(max_tokens=8192).with_structured_output(_FinalReport, method="json_schema")
    fr: _FinalReport = llm.invoke(prompt)  # type: ignore[assignment]

    final_recommendation, was_capped = _apply_cap(fr.recommendation, veto)

    score_table = _build_score_table(code, biz)
    meta_block = _summarize_repo_meta(repo_metadata or {}, repo_age_days)
    strengths_md = "\n".join(f"- {s}" for s in fr.strengths)
    risks_md = "\n".join(f"- {r}" for r in fr.risks)
    young_md = (_young_project_block(repo_age_days) + "\n\n") if is_young and repo_age_days is not None else ""
    veto_md = ("\n\n" + _veto_block(veto, was_capped, fr.recommendation)) if veto else ""

    cap_suffix = f"  (capped from `{fr.recommendation}` by veto)" if was_capped else ""

    md = f"""# Due Diligence Report

**Repository:** {repo_url}

{young_md}{meta_block}

## Recommendation: {final_recommendation}{cap_suffix}

**Overall score: {overall}/10**

{fr.executive_summary}{veto_md}

## Score breakdown

{score_table}

## Strengths

{strengths_md}

## Risks

{risks_md}

## Code team findings

{fr.code_findings}

## Business team findings

{fr.business_findings}
"""

    logger.info(
        "report_writer: %s%s (overall=%.1f, veto=%s, young=%s)",
        final_recommendation,
        " (capped)" if was_capped else "",
        overall,
        veto["dimension"] if veto else "none",
        is_young,
    )
    return {
        "final_recommendation": final_recommendation,
        "final_report_markdown": md,
        "overall_score": overall,
        "veto": veto,
    }


def report_writer_node(state: dict) -> dict:
    return write_report(
        repo_url=state["repo_url"],
        repo_metadata=state.get("repo_metadata") or {},
        repo_age_days=state.get("repo_age_days"),
        code_team_report=state.get("code_team_report") or {},
        business_team_report=state.get("business_team_report") or {},
    )

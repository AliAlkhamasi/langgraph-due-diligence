from __future__ import annotations

from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class TopState(TypedDict, total=False):
    repo_url: str
    repo_path: Optional[str]
    repo_metadata: Optional[dict]
    repo_age_days: Optional[int]
    code_team_report: Optional[dict]
    business_team_report: Optional[dict]
    final_recommendation: Optional[str]
    final_report_markdown: Optional[str]
    overall_score: Optional[float]
    veto: Optional[dict]
    messages: Annotated[list, add_messages]


class CodeTeamState(TypedDict, total=False):
    repo_url: str
    repo_path: Optional[str]
    repo_metadata: dict
    repo_analysis: Optional[dict]
    dependency_audit: Optional[dict]
    security_scan: Optional[dict]
    code_team_report: Optional[dict]
    messages: Annotated[list, add_messages]


class BusinessTeamState(TypedDict, total=False):
    repo_url: str
    repo_path: Optional[str]
    repo_metadata: dict
    readme_analysis: Optional[dict]
    contributor_activity: Optional[dict]
    issue_health: Optional[dict]
    business_team_report: Optional[dict]
    messages: Annotated[list, add_messages]

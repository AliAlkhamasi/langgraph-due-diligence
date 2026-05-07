"""Business team subgraph — mirrors code_team structure."""
from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.agents.contributor_activity import contributor_activity_node
from src.agents.issue_health import issue_health_node
from src.agents.readme_analyzer import readme_analyzer_node
from src.state import BusinessTeamState

logger = logging.getLogger(__name__)


def business_supervisor(state: BusinessTeamState) -> dict:
    return {}


def route_business_supervisor(
    state: BusinessTeamState,
) -> Literal["readme_analyzer", "contributor_activity", "issue_health", "compiler", "__end__"]:
    if state.get("readme_analysis") is None:
        return "readme_analyzer"
    if state.get("contributor_activity") is None:
        return "contributor_activity"
    if state.get("issue_health") is None:
        return "issue_health"
    if state.get("business_team_report") is None:
        return "compiler"
    return END


def compile_business_report(state: BusinessTeamState) -> dict:
    readme = state.get("readme_analysis") or {}
    contrib = state.get("contributor_activity") or {}
    issues = state.get("issue_health") or {}

    scores = {
        "documentation": readme.get("score", 0),
        "contributors": contrib.get("score", 0),
        "issues": issues.get("score", 0),
    }
    avg = sum(scores.values()) / len(scores) if scores else 0.0

    summary_parts = [
        s.strip()
        for s in (readme.get("summary"), contrib.get("summary"), issues.get("summary"))
        if s
    ]

    report = {
        "scores": scores,
        "overall_score": round(avg, 1),
        "readme_analysis": readme,
        "contributor_activity": contrib,
        "issue_health": issues,
        "summary": " ".join(summary_parts),
    }
    logger.info("business_team report: avg=%.1f scores=%s", avg, scores)
    return {"business_team_report": report}


def build_business_team_graph():
    g = StateGraph(BusinessTeamState)
    g.add_node("business_supervisor", business_supervisor)
    g.add_node("readme_analyzer", readme_analyzer_node)
    g.add_node("contributor_activity", contributor_activity_node)
    g.add_node("issue_health", issue_health_node)
    g.add_node("compiler", compile_business_report)

    g.add_edge(START, "business_supervisor")
    g.add_conditional_edges(
        "business_supervisor",
        route_business_supervisor,
        {
            "readme_analyzer": "readme_analyzer",
            "contributor_activity": "contributor_activity",
            "issue_health": "issue_health",
            "compiler": "compiler",
            END: END,
        },
    )
    g.add_edge("readme_analyzer", "business_supervisor")
    g.add_edge("contributor_activity", "business_supervisor")
    g.add_edge("issue_health", "business_supervisor")
    g.add_edge("compiler", "business_supervisor")

    return g.compile()


business_team_graph = build_business_team_graph()

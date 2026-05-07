"""Code team subgraph.

Mirrors the top-level supervisor pattern: a no-op ``code_supervisor`` node
hosts the conditional edges, and a ``compiler`` node assembles the three
specialist outputs into a single ``code_team_report`` that flows back into
the parent state via shared key naming.

Routing is currently sequential (Repo Analyzer → Dependency Auditor →
Security Scanner → Compiler). This shape leaves room to switch to parallel
fan-out via ``Send`` later without changing the public output shape.
"""
from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.agents.dependency_auditor import dependency_auditor_node
from src.agents.repo_analyzer import repo_analyzer_node
from src.agents.security_scanner import security_scanner_node
from src.state import CodeTeamState

logger = logging.getLogger(__name__)


def code_supervisor(state: CodeTeamState) -> dict:
    return {}


def route_code_supervisor(
    state: CodeTeamState,
) -> Literal["repo_analyzer", "dependency_auditor", "security_scanner", "compiler", "__end__"]:
    if state.get("repo_analysis") is None:
        return "repo_analyzer"
    if state.get("dependency_audit") is None:
        return "dependency_auditor"
    if state.get("security_scan") is None:
        return "security_scanner"
    if state.get("code_team_report") is None:
        return "compiler"
    return END


def compile_code_report(state: CodeTeamState) -> dict:
    repo = state.get("repo_analysis") or {}
    deps = state.get("dependency_audit") or {}
    sec = state.get("security_scan") or {}

    scores = {
        "repo": repo.get("score", 0),
        "dependencies": deps.get("score", 0),
        "security": sec.get("score", 0),
    }
    avg = sum(scores.values()) / len(scores) if scores else 0.0

    summary_parts = [
        s.strip()
        for s in (repo.get("summary"), deps.get("summary"), sec.get("summary"))
        if s
    ]

    report = {
        "scores": scores,
        "overall_score": round(avg, 1),
        "repo_analysis": repo,
        "dependency_audit": deps,
        "security_scan": sec,
        "summary": " ".join(summary_parts),
    }
    logger.info("code_team report: avg=%.1f scores=%s", avg, scores)
    return {"code_team_report": report}


def build_code_team_graph():
    g = StateGraph(CodeTeamState)
    g.add_node("code_supervisor", code_supervisor)
    g.add_node("repo_analyzer", repo_analyzer_node)
    g.add_node("dependency_auditor", dependency_auditor_node)
    g.add_node("security_scanner", security_scanner_node)
    g.add_node("compiler", compile_code_report)

    g.add_edge(START, "code_supervisor")
    g.add_conditional_edges(
        "code_supervisor",
        route_code_supervisor,
        {
            "repo_analyzer": "repo_analyzer",
            "dependency_auditor": "dependency_auditor",
            "security_scanner": "security_scanner",
            "compiler": "compiler",
            END: END,
        },
    )
    g.add_edge("repo_analyzer", "code_supervisor")
    g.add_edge("dependency_auditor", "code_supervisor")
    g.add_edge("security_scanner", "code_supervisor")
    g.add_edge("compiler", "code_supervisor")

    return g.compile()


code_team_graph = build_code_team_graph()

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.report_writer import report_writer_node
from src.state import TopState
from src.teams.business_team import business_team_graph
from src.teams.code_team import code_team_graph
from src.tools import github
from src.tools.repo import cleanup_repo as _cleanup_repo
from src.tools.repo import clone_repo as _clone_repo


def fetch_metadata(state: TopState) -> dict:
    from datetime import datetime, timezone

    owner, repo = github.parse_repo_url(state["repo_url"])
    meta = github.get_repo(owner, repo) or {}
    age_days: int | None = None
    created = meta.get("created_at")
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created_dt).days
        except ValueError:
            pass
    return {"repo_metadata": meta, "repo_age_days": age_days}


def clone_repo_node(state: TopState) -> dict:
    path = _clone_repo(state["repo_url"])
    return {"repo_path": path}


def cleanup_repo_node(state: TopState) -> dict:
    _cleanup_repo(state.get("repo_path"))
    return {"repo_path": None}


def top_supervisor(state: TopState) -> dict:
    return {}


def route_from_supervisor(
    state: TopState,
) -> Literal["code_team", "business_team", "report_writer", "__end__"]:
    if state.get("repo_metadata") is None:
        return "code_team"
    if state.get("code_team_report") is None:
        return "code_team"
    if state.get("business_team_report") is None:
        return "business_team"
    if state.get("final_report_markdown") is None:
        return "report_writer"
    return END


def code_team(state: TopState) -> dict:
    """Invoke the code team subgraph with a narrow slice of TopState."""
    sub_input = {
        "repo_url": state["repo_url"],
        "repo_path": state.get("repo_path"),
        "repo_metadata": state.get("repo_metadata") or {},
    }
    result = code_team_graph.invoke(sub_input)
    return {"code_team_report": result.get("code_team_report")}


def business_team(state: TopState) -> dict:
    """Invoke the business team subgraph with a narrow slice of TopState."""
    sub_input = {
        "repo_url": state["repo_url"],
        "repo_path": state.get("repo_path"),
        "repo_metadata": state.get("repo_metadata") or {},
    }
    result = business_team_graph.invoke(sub_input)
    return {"business_team_report": result.get("business_team_report")}


def report_writer(state: TopState) -> dict:
    return report_writer_node(state)


def build_graph():
    g = StateGraph(TopState)

    g.add_node("fetch_metadata", fetch_metadata)
    g.add_node("clone_repo", clone_repo_node)
    g.add_node("top_supervisor", top_supervisor)
    g.add_node("code_team", code_team)
    g.add_node("business_team", business_team)
    g.add_node("report_writer", report_writer)
    g.add_node("cleanup_repo", cleanup_repo_node)

    g.add_edge(START, "fetch_metadata")
    g.add_edge("fetch_metadata", "clone_repo")
    g.add_edge("clone_repo", "top_supervisor")
    g.add_conditional_edges(
        "top_supervisor",
        route_from_supervisor,
        {
            "code_team": "code_team",
            "business_team": "business_team",
            "report_writer": "report_writer",
            END: END,
        },
    )
    g.add_edge("code_team", "top_supervisor")
    g.add_edge("business_team", "top_supervisor")
    g.add_edge("report_writer", "cleanup_repo")
    g.add_edge("cleanup_repo", END)

    return g.compile()


graph = build_graph()

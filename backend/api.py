"""FastAPI wrapper around the LangGraph due-diligence pipeline.

Endpoints:
  POST /analyze              -> { analysis_id }
  GET  /analyze/{id}/stream  -> Server-Sent Events
  GET  /analyze/{id}         -> final report (404 until complete)
  GET  /health

SSE event types:
  node_start       { node, team? }
  node_complete    { node, team?, summary }
  team_complete    { team, scores, overall_score }
  report_ready     { report }
  complete         { usage }
  error            { message }

In-memory store only — restart wipes runs. Suitable for v1.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

CODE_SPECIALISTS = ["repo_analyzer", "dependency_auditor", "security_scanner"]
BUSINESS_SPECIALISTS = ["readme_analyzer", "contributor_activity", "issue_health"]

app = FastAPI(title="Tech Due Diligence API", version="0.1.0")

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

runs: dict[str, dict] = {}


class AnalyzeRequest(BaseModel):
    repo_url: str


class AnalyzeResponse(BaseModel):
    analysis_id: str


def _next_pending(seq: list[str], done: list[str]) -> str | None:
    for s in seq:
        if s not in done:
            return s
    return None


def _specialist_summary(node: str, update: dict) -> str:
    keys = {
        "repo_analyzer": "repo_analysis",
        "dependency_auditor": "dependency_audit",
        "security_scanner": "security_scan",
        "readme_analyzer": "readme_analysis",
        "contributor_activity": "contributor_activity",
        "issue_health": "issue_health",
    }
    data = update.get(keys.get(node, ""), {}) or {}
    score = data.get("score")
    summary = (data.get("summary") or "").strip()
    first = summary.split(". ")[0] if summary else ""
    if len(first) > 120:
        first = first[:120].rstrip() + "…"
    return f"{score}/10 — {first}" if score is not None and first else (first or f"{score}/10" if score else "")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def start_analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    analysis_id = uuid.uuid4().hex
    runs[analysis_id] = {
        "id": analysis_id,
        "repo_url": req.repo_url,
        "status": "running",
        "queue": asyncio.Queue(),
        "final": None,
        "error": None,
    }
    asyncio.create_task(_run(analysis_id, req.repo_url))
    logger.info("started analysis %s for %s", analysis_id, req.repo_url)
    return AnalyzeResponse(analysis_id=analysis_id)


@app.get("/analyze/{analysis_id}/stream")
async def stream_analyze(analysis_id: str) -> StreamingResponse:
    if analysis_id not in runs:
        raise HTTPException(404, "analysis_id not found")

    async def gen():
        queue: asyncio.Queue = runs[analysis_id]["queue"]
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/analyze/{analysis_id}")
async def get_analysis(analysis_id: str) -> dict:
    if analysis_id not in runs:
        raise HTTPException(404, "analysis_id not found")
    run = runs[analysis_id]
    return {
        "id": run["id"],
        "repo_url": run["repo_url"],
        "status": run["status"],
        "final": run["final"],
        "error": run["error"],
    }


async def _run(analysis_id: str, repo_url: str) -> None:
    from src.graph import build_graph
    from src.llm import get_usage, reset_usage

    run = runs[analysis_id]
    queue: asyncio.Queue = run["queue"]
    code_done: list[str] = []
    biz_done: list[str] = []

    async def emit(event: dict | None) -> None:
        await queue.put(event)

    try:
        reset_usage()
        graph = build_graph()
        await emit({"type": "node_start", "node": "fetch_metadata"})

        async for event_tuple in graph.astream(
            {"repo_url": repo_url},
            stream_mode="updates",
            subgraphs=True,
        ):
            namespace, payload = event_tuple
            for node, update in payload.items():
                if not isinstance(update, dict):
                    continue

                if not namespace:
                    if node == "fetch_metadata" and update.get("repo_metadata"):
                        meta = update["repo_metadata"]
                        stars = meta.get("stargazers_count") or 0
                        summary = (
                            f"{meta.get('full_name', repo_url)} · "
                            f"{meta.get('language', '?')} · {stars:,}★"
                        )
                        await emit({"type": "node_complete", "node": "fetch_metadata", "summary": summary})
                        await emit({"type": "node_start", "node": "clone_repo"})

                    elif node == "clone_repo" and update.get("repo_path"):
                        await emit({"type": "node_complete", "node": "clone_repo", "summary": "shallow clone done"})
                        await emit({"type": "node_start", "node": "code_team"})
                        await emit({"type": "node_start", "node": CODE_SPECIALISTS[0], "team": "code"})

                    elif node == "code_team" and update.get("code_team_report"):
                        report = update["code_team_report"]
                        await emit({
                            "type": "team_complete",
                            "team": "code",
                            "scores": report.get("scores"),
                            "overall_score": report.get("overall_score"),
                        })
                        await emit({"type": "node_start", "node": "business_team"})
                        await emit({"type": "node_start", "node": BUSINESS_SPECIALISTS[0], "team": "business"})

                    elif node == "business_team" and update.get("business_team_report"):
                        report = update["business_team_report"]
                        await emit({
                            "type": "team_complete",
                            "team": "business",
                            "scores": report.get("scores"),
                            "overall_score": report.get("overall_score"),
                        })
                        await emit({"type": "node_start", "node": "report_writer"})

                    elif node == "report_writer" and update.get("final_report_markdown"):
                        final = {
                            "recommendation": update.get("final_recommendation"),
                            "report_markdown": update.get("final_report_markdown"),
                            "overall_score": update.get("overall_score"),
                            "veto": update.get("veto"),
                        }
                        run["final"] = final
                        await emit({"type": "node_complete", "node": "report_writer", "summary": "report ready"})
                        await emit({"type": "report_ready", "report": final})

                else:
                    ns = namespace[0]
                    is_code = ns.startswith("code_team")
                    is_biz = ns.startswith("business_team")
                    if is_code and node in CODE_SPECIALISTS:
                        await emit({
                            "type": "node_complete",
                            "node": node,
                            "team": "code",
                            "summary": _specialist_summary(node, update),
                        })
                        code_done.append(node)
                        nxt = _next_pending(CODE_SPECIALISTS, code_done)
                        if nxt:
                            await emit({"type": "node_start", "node": nxt, "team": "code"})
                    elif is_biz and node in BUSINESS_SPECIALISTS:
                        await emit({
                            "type": "node_complete",
                            "node": node,
                            "team": "business",
                            "summary": _specialist_summary(node, update),
                        })
                        biz_done.append(node)
                        nxt = _next_pending(BUSINESS_SPECIALISTS, biz_done)
                        if nxt:
                            await emit({"type": "node_start", "node": nxt, "team": "business"})

        run["status"] = "complete"
        usage = get_usage()
        await emit({
            "type": "complete",
            "usage": {
                "calls": usage.calls,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost_usd": round(usage.cost_usd, 4),
            },
        })
        logger.info("analysis %s complete", analysis_id)
    except Exception as e:
        logger.exception("analysis %s failed", analysis_id)
        run["status"] = "error"
        run["error"] = f"{type(e).__name__}: {e}"
        await emit({"type": "error", "message": run["error"]})
    finally:
        await emit(None)  # sentinel

"""Security Scanner — pipeline node.

Three deterministic checks, then an LLM verdict:
  1. Regex-based scan for committed secrets across non-binary files.
  2. Sensitive filename detection (.env, *.pem, id_rsa, ...).
  3. Branch-protection lookup on the default branch (best-effort, requires
     admin access on the token to return data; 404 means unknown, not absent).

Note: shallow clone means we only see HEAD, not history. Adding history scan
would require a full clone — punted to a future iteration.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.llm import get_llm
from src.tools import filesystem as fs
from src.tools import github

logger = logging.getLogger(__name__)


_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_pat", re.compile(r"\b(?:ghp|ghs|gho|ghr|ghu)_[A-Za-z0-9_]{30,}\b")),
    ("github_fine_grained_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{40,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{40,}\b")),
    ("private_key_header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("stripe_key", re.compile(r"\b(?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,}\b")),
]

_NOISE_SUFFIXES: frozenset[str] = frozenset({".lock", ".map", ".min.js", ".min.css"})
_SENSITIVE_SUFFIXES: frozenset[str] = frozenset({".pem", ".key", ".p12", ".pfx", ".pkcs12"})
_SENSITIVE_NAMES: frozenset[str] = frozenset(
    {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".pgpass", ".htpasswd", ".npmrc", ".pypirc"}
)


class _SecAssessment(BaseModel):
    summary: str = Field(description="2-3 sentence security-hygiene assessment")
    score: int = Field(ge=1, le=10, description="1=alarming, 5=mediocre, 10=exemplary")


def _scan_secrets(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for f in fs.walk_files(path):
        if f.suffix.lower() in _NOISE_SUFFIXES:
            continue
        try:
            text = fs.read_file(f, max_bytes=500_000)
        except (ValueError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for kind, regex in _SECRET_PATTERNS:
                if regex.search(line):
                    findings.append(
                        {
                            "file": str(f.relative_to(path)).replace("\\", "/"),
                            "type": kind,
                            "line": line_no,
                            "snippet": line.strip()[:120],
                        }
                    )
                    break
    return findings


def _detect_sensitive_files(path: Path) -> list[str]:
    found: list[str] = []
    for f in fs.walk_files(path, skip_binary=False):
        name = f.name.lower()
        if name.startswith(".env") and not name.endswith(".example") and not name.endswith(".sample"):
            found.append(str(f.relative_to(path)).replace("\\", "/"))
        elif name in _SENSITIVE_NAMES:
            found.append(str(f.relative_to(path)).replace("\\", "/"))
        elif f.suffix.lower() in _SENSITIVE_SUFFIXES:
            found.append(str(f.relative_to(path)).replace("\\", "/"))
    return found


def _branch_protection_summary(owner: str, repo: str, branch: str) -> dict[str, Any]:
    bp = github.get_branch_protection(owner, repo, branch)
    if bp is None:
        return {"status": "unknown", "reason": "404 (no admin access on token, or no protection set)"}
    return {
        "status": "enabled",
        "required_approving_reviews": (bp.get("required_pull_request_reviews") or {}).get(
            "required_approving_review_count"
        ),
        "enforce_admins": (bp.get("enforce_admins") or {}).get("enabled"),
        "required_status_checks": bool(bp.get("required_status_checks")),
        "require_signed_commits": (bp.get("required_signatures") or {}).get("enabled"),
    }


def scan_security(repo_url: str, repo_path: str) -> dict[str, Any]:
    """Run the Security Scanner pipeline. Returns the scan dict."""
    owner, repo = github.parse_repo_url(repo_url)
    logger.info("security_scanner: %s/%s", owner, repo)

    repo_meta = github.get_repo(owner, repo) or {}
    default_branch = repo_meta.get("default_branch", "main")
    branch_protection = _branch_protection_summary(owner, repo, default_branch)

    path = Path(repo_path)
    secrets = _scan_secrets(path)
    secret_count_by_type: dict[str, int] = {}
    for s in secrets:
        secret_count_by_type[s["type"]] = secret_count_by_type.get(s["type"], 0) + 1

    sensitive_files = _detect_sensitive_files(path)

    prompt = f"""You are evaluating the security hygiene of an open-source repository.

Repository: {owner}/{repo}
Default branch: {default_branch}
Branch protection: {branch_protection}

Filesystem scan (HEAD only, not git history):
  Suspected secrets matching common patterns: {len(secrets)}
  Counts by type: {secret_count_by_type}
  First 5 hits: {secrets[:5]}
  Sensitive filenames present (.env / .pem / id_rsa / ...): {sensitive_files[:10]}

Important context for scoring:
- Many open-source repos legitimately commit ".env.example" / sample files
  with placeholder values; these aren't real leaks. Real leaks usually show
  long high-entropy strings.
- Branch protection of "unknown" usually means the token lacks admin scope —
  do NOT penalize the repo for that, treat it as unobserved.
- Score ONLY based on what's clearly visible.

Provide a 2-3 sentence assessment and an integer score 1-10:
  1-3  = real secrets committed, or visible serious exposure
  4-6  = ambiguous matches; deserves manual review
  7-8  = clean working tree, no obvious red flags
  9-10 = clean + visible defensive practices (signed commits, strict reviews)"""

    llm = get_llm().with_structured_output(_SecAssessment)
    assessment: _SecAssessment = llm.invoke(prompt)  # type: ignore[assignment]

    return {
        "default_branch": default_branch,
        "branch_protection": branch_protection,
        "secrets_found": secrets,
        "secret_count_by_type": secret_count_by_type,
        "sensitive_files": sensitive_files,
        "summary": assessment.summary,
        "score": assessment.score,
    }


def security_scanner_node(state: dict) -> dict:
    return {"security_scan": scan_security(state["repo_url"], state["repo_path"])}

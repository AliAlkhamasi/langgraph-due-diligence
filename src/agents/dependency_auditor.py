"""Dependency Auditor — pipeline node.

Detects manifests (pyproject.toml, requirements*.txt, package.json, Cargo.toml,
go.mod), parses them, then asks the LLM to score dependency hygiene.

OSV-database vulnerability lookup is intentionally deferred — see the project
spec; can be layered in later without changing the output shape.
"""
from __future__ import annotations

import json
import logging
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.llm import get_llm
from src.tools import filesystem as fs

logger = logging.getLogger(__name__)


class _DepAssessment(BaseModel):
    summary: str = Field(description="2-3 sentence assessment of dependency health")
    score: int = Field(ge=1, le=10, description="1=unhealthy, 5=average, 10=exemplary")


def _parse_pyproject(path: Path) -> dict[str, list[str]]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    runtime: list[str] = []
    dev: list[str] = []

    proj = data.get("project") or {}
    runtime.extend(proj.get("dependencies") or [])

    for group, deps in (proj.get("optional-dependencies") or {}).items():
        target = dev if any(k in group.lower() for k in ("dev", "test", "lint", "doc")) else runtime
        target.extend(deps or [])

    # PEP 735 dependency groups (used by Flask and many newer projects)
    for group, deps in (data.get("dependency-groups") or {}).items():
        target = dev if any(k in group.lower() for k in ("dev", "test", "lint", "doc")) else runtime
        for d in deps or []:
            if isinstance(d, str):
                target.append(d)

    poetry = (data.get("tool") or {}).get("poetry") or {}
    if poetry:
        for name, val in (poetry.get("dependencies") or {}).items():
            if name == "python":
                continue
            spec = val if isinstance(val, str) else (val.get("version", "") if isinstance(val, dict) else "")
            runtime.append(f"{name}{spec}")
        for name, val in (poetry.get("dev-dependencies") or {}).items():
            spec = val if isinstance(val, str) else ""
            dev.append(f"{name}{spec}")

    return {"runtime": runtime, "dev": dev}


def _parse_requirements(path: Path) -> list[str]:
    out: list[str] = []
    for raw in fs.read_file(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        out.append(line)
    return out


def _parse_package_json(path: Path) -> dict[str, list[str]]:
    data = json.loads(fs.read_file(path))
    runtime = [f"{n}@{v}" for n, v in (data.get("dependencies") or {}).items()]
    peer = [f"{n}@{v}" for n, v in (data.get("peerDependencies") or {}).items()]
    dev = [f"{n}@{v}" for n, v in (data.get("devDependencies") or {}).items()]
    return {"runtime": runtime + peer, "dev": dev}


def _parse_cargo(path: Path) -> dict[str, list[str]]:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    def fmt(name: str, val: Any) -> str:
        if isinstance(val, str):
            return f"{name} = {val}"
        if isinstance(val, dict):
            return f"{name} = {val.get('version', '*')}"
        return f"{name} = *"

    runtime = [fmt(n, v) for n, v in (data.get("dependencies") or {}).items()]
    dev = [fmt(n, v) for n, v in (data.get("dev-dependencies") or {}).items()]
    return {"runtime": runtime, "dev": dev}


def _parse_go_mod(path: Path) -> list[str]:
    out: list[str] = []
    in_block = False
    for raw in fs.read_file(path).splitlines():
        line = raw.strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block:
            if line == ")":
                in_block = False
                continue
            if line and not line.startswith("//"):
                out.append(line)
        elif line.startswith("require "):
            out.append(line[len("require "):].strip())
    return out


def audit_dependencies(repo_path: str) -> dict[str, Any]:
    """Run the Dependency Auditor pipeline. Returns the audit dict."""
    path = Path(repo_path)
    manifests: list[str] = []
    runtime: list[str] = []
    dev: list[str] = []
    ecosystems: set[str] = set()

    pyproject = path / "pyproject.toml"
    if pyproject.is_file():
        manifests.append("pyproject.toml")
        ecosystems.add("python")
        parsed = _parse_pyproject(pyproject)
        runtime.extend(parsed["runtime"])
        dev.extend(parsed["dev"])

    for name in ("requirements.txt", "requirements/base.txt", "requirements/prod.txt"):
        req = path / name
        if req.is_file():
            manifests.append(name)
            ecosystems.add("python")
            runtime.extend(_parse_requirements(req))

    for name in ("requirements-dev.txt", "requirements/dev.txt", "requirements/test.txt"):
        req = path / name
        if req.is_file():
            manifests.append(name)
            ecosystems.add("python")
            dev.extend(_parse_requirements(req))

    pkg = path / "package.json"
    if pkg.is_file():
        manifests.append("package.json")
        ecosystems.add("node")
        parsed = _parse_package_json(pkg)
        runtime.extend(parsed["runtime"])
        dev.extend(parsed["dev"])

    cargo = path / "Cargo.toml"
    if cargo.is_file():
        manifests.append("Cargo.toml")
        ecosystems.add("rust")
        parsed = _parse_cargo(cargo)
        runtime.extend(parsed["runtime"])
        dev.extend(parsed["dev"])

    go_mod = path / "go.mod"
    if go_mod.is_file():
        manifests.append("go.mod")
        ecosystems.add("go")
        runtime.extend(_parse_go_mod(go_mod))

    if not ecosystems:
        ecosystem = "unknown"
    elif len(ecosystems) == 1:
        ecosystem = next(iter(ecosystems))
    else:
        ecosystem = "mixed:" + ",".join(sorted(ecosystems))

    runtime = sorted(set(runtime))
    dev = sorted(set(dev))

    if not manifests:
        return {
            "ecosystem": "unknown",
            "manifests_found": [],
            "runtime_deps": [],
            "dev_deps": [],
            "total_count": 0,
            "summary": "No recognized dependency manifests were found in the repository.",
            "score": 5,
        }

    prompt = f"""You are evaluating dependency hygiene for an open-source repository.

Ecosystem: {ecosystem}
Manifests detected: {manifests}
Runtime dependencies ({len(runtime)}): {runtime[:50]}
Dev / test / lint dependencies ({len(dev)}): {dev[:30]}

Consider:
- Total count: very few may indicate immaturity; hundreds may indicate bloat
- Pinned vs unpinned versions
- Presence of testing / linting / type-checking tools in dev deps
- Obviously outdated or risky packages
- Whether the dependency set matches the project's apparent scope

Provide a 2-3 sentence assessment and an integer score 1-10:
  1-3  = unhealthy (no manifests, dependency hell, abandoned packages)
  4-6  = average / unclear
  7-8  = solid hygiene
  9-10 = exemplary"""

    llm = get_llm().with_structured_output(_DepAssessment)
    assessment: _DepAssessment = llm.invoke(prompt)  # type: ignore[assignment]

    return {
        "ecosystem": ecosystem,
        "manifests_found": manifests,
        "runtime_deps": runtime,
        "dev_deps": dev,
        "total_count": len(runtime) + len(dev),
        "summary": assessment.summary,
        "score": assessment.score,
    }


def dependency_auditor_node(state: dict) -> dict:
    return {"dependency_audit": audit_dependencies(state["repo_path"])}

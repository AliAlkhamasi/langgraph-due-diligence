"""README/Docs Analyzer — pipeline node.

Globs standard documentation files, reads README + a couple of supporting docs,
detects badges that indicate a hosted documentation site, then asks the LLM
for a quality verdict.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.llm import get_llm
from src.tools import filesystem as fs

logger = logging.getLogger(__name__)


_DOC_HOST_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("readthedocs", re.compile(r"https?://[\w.-]*readthedocs\.(?:io|org)[\w./?#=&:%-]*", re.I)),
    ("github_pages", re.compile(r"https?://[\w.-]+\.github\.io/[\w./?#=&:%-]*", re.I)),
    ("docs_rs", re.compile(r"https?://docs\.rs/[\w./?#=&:%-]+", re.I)),
    ("gitbook", re.compile(r"https?://[\w.-]+\.gitbook\.io/[\w./?#=&:%-]*", re.I)),
    ("mkdocs", re.compile(r"\bmkdocs\b", re.I)),
]

_DOC_CANDIDATES: dict[str, list[str]] = {
    "README": ["README.md", "README.rst", "README.txt", "README"],
    "CONTRIBUTING": ["CONTRIBUTING.md", "CONTRIBUTING.rst", ".github/CONTRIBUTING.md"],
    "CODE_OF_CONDUCT": ["CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md"],
    "CHANGELOG": ["CHANGELOG.md", "CHANGELOG.rst", "CHANGES.md", "CHANGES.rst", "HISTORY.md"],
    "LICENSE": ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENSE.rst"],
    "SECURITY": ["SECURITY.md", ".github/SECURITY.md"],
}


class _DocsAssessment(BaseModel):
    summary: str = Field(description="2-3 sentence assessment of documentation quality")
    score: int = Field(ge=1, le=10, description="1=cryptic, 5=basic, 10=professional")


def _find_doc(path: Path, candidates: list[str]) -> Path | None:
    for cand in candidates:
        target = path / cand
        if target.is_file():
            return target
        for child in path.iterdir():
            if child.name.lower() == cand.lower() and child.is_file():
                return child
    return None


def _detect_hosted_docs(text: str) -> list[dict[str, str]]:
    if not text:
        return []
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for kind, regex in _DOC_HOST_PATTERNS:
        m = regex.search(text)
        if m:
            url = m.group(0)
            if url not in seen:
                seen.add(url)
                out.append({"kind": kind, "match": url})
    return out


def _docs_dir_summary(path: Path) -> dict[str, Any] | None:
    docs = path / "docs"
    if not docs.is_dir():
        return None
    files = list(fs.walk_files(docs))
    return {
        "exists": True,
        "file_count": len(files),
        "extensions": sorted({f.suffix.lower() for f in files if f.suffix}),
    }


def analyze_readme(repo_url: str, repo_path: str) -> dict[str, Any]:
    path = Path(repo_path)
    docs_present: dict[str, str] = {}
    docs_content: dict[str, str] = {}
    for name, candidates in _DOC_CANDIDATES.items():
        found = _find_doc(path, candidates)
        if not found:
            continue
        docs_present[name] = str(found.relative_to(path)).replace("\\", "/")
        try:
            docs_content[name] = fs.read_file(found, max_bytes=300_000)
        except (ValueError, OSError):
            pass

    readme_text = docs_content.get("README", "")
    hosted_docs = _detect_hosted_docs(readme_text)
    docs_dir = _docs_dir_summary(path)

    snippets = {n: docs_content[n][:2000] for n in ("README", "CONTRIBUTING", "CHANGELOG") if n in docs_content}

    prompt = f"""You are evaluating documentation quality of an open-source repository.

Documentation files present: {sorted(docs_present.keys())}
Hosted docs site detected: {hosted_docs or 'none detected'}
docs/ directory: {docs_dir or 'absent'}
README length: {len(readme_text):,} chars

README excerpt (first 2000 chars):
---
{snippets.get('README', '(no README)')}
---

CONTRIBUTING excerpt (first 2000 chars):
---
{snippets.get('CONTRIBUTING', '(no CONTRIBUTING)')}
---

Provide a 2-3 sentence assessment focusing on:
- Does the README cover purpose, install, and usage?
- Are there contributor-friendly supporting docs (CONTRIBUTING, CODE_OF_CONDUCT)?
- Is there a hosted docs site or a substantial docs/ directory?

Score 1-10:
  1-3 = barely any docs, unclear
  4-6 = README only, basic
  7-8 = solid README plus supporting docs
  9-10 = professional, hosted site, comprehensive coverage"""

    llm = get_llm().with_structured_output(_DocsAssessment)
    assessment: _DocsAssessment = llm.invoke(prompt)  # type: ignore[assignment]

    return {
        "docs_present": docs_present,
        "hosted_docs_sites": hosted_docs,
        "docs_directory": docs_dir,
        "readme_length_chars": len(readme_text),
        "summary": assessment.summary,
        "score": assessment.score,
    }


def readme_analyzer_node(state: dict) -> dict:
    return {"readme_analysis": analyze_readme(state["repo_url"], state["repo_path"])}

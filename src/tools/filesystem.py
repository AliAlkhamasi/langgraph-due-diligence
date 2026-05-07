"""Filesystem helpers for reading/walking a cloned repo.

All functions take ``str | Path`` and return native Python types so they're
trivial to use from agent pipelines. Default ignore-set excludes common build
artifacts and VCS dirs to avoid wasting time on generated content.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Iterator

DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "env",
        "__pycache__",
        "dist",
        "build",
        "target",
        ".cache",
        ".idea",
        ".vscode",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".next",
        "coverage",
        ".gradle",
    }
)

BINARY_EXTS: frozenset[str] = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff",
        ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".xz",
        ".so", ".dll", ".dylib", ".exe", ".bin", ".o", ".a",
        ".pyc", ".pyo", ".class", ".jar",
        ".woff", ".woff2", ".ttf", ".eot", ".otf",
        ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    }
)


def read_file(path: str | Path, *, max_bytes: int = 1_000_000) -> str:
    """Read a text file with a size cap. Errors are replaced (lossy)."""
    p = Path(path)
    size = p.stat().st_size
    if size > max_bytes:
        raise ValueError(f"{p} is {size} bytes; exceeds max_bytes={max_bytes}")
    return p.read_text(encoding="utf-8", errors="replace")


def list_directory(path: str | Path) -> list[dict]:
    """List immediate children. Returns dicts with name, is_dir, size."""
    p = Path(path)
    out: list[dict] = []
    for child in sorted(p.iterdir()):
        try:
            is_dir = child.is_dir()
            size = None if is_dir else child.stat().st_size
        except OSError:
            continue
        out.append({"name": child.name, "is_dir": is_dir, "size": size})
    return out


def walk_files(
    root: str | Path,
    *,
    ignore_dirs: Iterable[str] = DEFAULT_IGNORE_DIRS,
    skip_binary: bool = True,
) -> Iterator[Path]:
    """Walk all files under root, pruning ignore_dirs in-place for speed."""
    ignore = set(ignore_dirs)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore]
        for fn in filenames:
            if skip_binary and Path(fn).suffix.lower() in BINARY_EXTS:
                continue
            yield Path(dirpath) / fn


def glob_files(
    root: str | Path,
    pattern: str,
    *,
    ignore_dirs: Iterable[str] = DEFAULT_IGNORE_DIRS,
) -> list[Path]:
    """Recursive glob; results outside ignore_dirs and limited to files."""
    root_path = Path(root)
    ignore = set(ignore_dirs)
    results: list[Path] = []
    for path in root_path.rglob(pattern):
        if any(part in ignore for part in path.relative_to(root_path).parts):
            continue
        if path.is_file():
            results.append(path)
    return results


def count_lines(path: str | Path) -> int:
    """Count newline-terminated lines in a file (binary-safe)."""
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def find_first(
    root: str | Path,
    candidates: Iterable[str],
    *,
    case_insensitive: bool = True,
) -> Path | None:
    """Return the first candidate path that exists at any depth, or None.

    candidates may be filenames ("README.md") or relative subpaths
    (".github/workflows"). Used for locating manifests and config files.
    """
    root_path = Path(root)
    for cand in candidates:
        direct = root_path / cand
        if direct.exists():
            return direct
        if case_insensitive and "/" not in cand and os.sep not in cand:
            target = cand.lower()
            for child in root_path.iterdir():
                if child.name.lower() == target:
                    return child
    return None

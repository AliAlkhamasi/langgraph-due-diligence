"""Shallow git clone + cleanup helpers for ephemeral repo analysis."""
from __future__ import annotations

import logging
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def clone_repo(repo_url: str, *, depth: int = 1, timeout: int = 180) -> str:
    """Shallow-clone a public GitHub repo into a fresh temp directory.

    Returns the absolute path to the cloned working tree. The caller owns the
    directory and must invoke ``cleanup_repo`` when finished.
    """
    target = tempfile.mkdtemp(prefix="tdd_clone_")
    cmd = ["git", "clone", "--depth", str(depth), "--quiet", repo_url, target]
    logger.info("cloning %s -> %s", repo_url, target)
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        cleanup_repo(target)
        raise RuntimeError(
            "git executable not found on PATH. Install git and retry."
        ) from e
    except subprocess.TimeoutExpired:
        cleanup_repo(target)
        raise RuntimeError(f"git clone timed out after {timeout}s for {repo_url}")
    except subprocess.CalledProcessError as e:
        cleanup_repo(target)
        msg = (e.stderr or e.stdout or "").strip()
        raise RuntimeError(f"git clone failed for {repo_url}: {msg}") from e
    return target


def _on_rm_error(func, path, exc_info):
    """rmtree handler that fixes Windows read-only files inside .git/."""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except Exception:
        pass


def cleanup_repo(path: str | None) -> None:
    """Remove a cloned repo directory; safe to call on missing/None paths."""
    if not path:
        return
    p = Path(path)
    if not p.exists():
        return
    logger.info("cleaning up %s", path)
    try:
        shutil.rmtree(p, onerror=_on_rm_error)
    except Exception:  # pragma: no cover
        logger.exception("failed to cleanup %s", path)

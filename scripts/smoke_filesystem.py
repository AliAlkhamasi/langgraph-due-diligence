"""Standalone smoke test for src/tools/filesystem.py.

Clones pallets/flask, exercises every helper, prints a summary, cleans up.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools import filesystem as fs  # noqa: E402
from src.tools.repo import cleanup_repo, clone_repo  # noqa: E402


def main(repo_url: str = "https://github.com/pallets/flask") -> None:
    print(f"--- cloning {repo_url} ---")
    t0 = time.perf_counter()
    path = clone_repo(repo_url)
    print(f"  clone: {time.perf_counter() - t0:.2f}s -> {path}")

    try:
        print("\nlist_directory(root):")
        for entry in fs.list_directory(path)[:15]:
            kind = "d" if entry["is_dir"] else "f"
            size = "" if entry["size"] is None else f"  ({entry['size']:,} bytes)"
            print(f"  {kind} {entry['name']}{size}")

        print("\nfind_first(README candidates):")
        readme = fs.find_first(path, ["README.md", "README.rst", "README"])
        print(f"  -> {readme}")
        if readme:
            content = fs.read_file(readme, max_bytes=2_000_000)
            print(f"  read {len(content):,} chars; first line: {content.splitlines()[0][:80]}")

        print("\nfind_first(workflows):")
        wf = fs.find_first(path, [".github/workflows"])
        print(f"  -> {wf}")

        print("\nglob_files('**/*.py'):")
        t0 = time.perf_counter()
        py_files = fs.glob_files(path, "**/*.py")
        print(f"  found {len(py_files)} python files in {time.perf_counter() - t0:.2f}s")

        print("\nwalk_files() summary:")
        t0 = time.perf_counter()
        total = 0
        by_ext: dict[str, int] = {}
        for f in fs.walk_files(path):
            total += 1
            ext = f.suffix.lower() or "<noext>"
            by_ext[ext] = by_ext.get(ext, 0) + 1
        print(f"  {total} non-binary files in {time.perf_counter() - t0:.2f}s")
        top = sorted(by_ext.items(), key=lambda kv: -kv[1])[:10]
        for ext, n in top:
            print(f"    {ext:>10}: {n}")

        print("\ncount_lines(top 3 .py by size):")
        with_size = sorted(py_files, key=lambda p: p.stat().st_size, reverse=True)[:3]
        for f in with_size:
            print(f"  {f.relative_to(path)}: {fs.count_lines(f):,} lines")

    finally:
        cleanup_repo(path)
        print(f"\ncleaned up {path}")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask"
    main(url)

#!/usr/bin/env python3
"""Thin launcher for LongMarching/cnki-search-skill without vendoring its code.

V2.4.1+ also normalizes path-valued CLI arguments that belong to the current
course-paper project before handing them to the upstream backend.  In
particular, a relative ``--dir papers/cnki`` is converted to an absolute path
under the current project root so the upstream backend cannot reinterpret it
relative to its own repository.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def backend_root() -> Path:
    override = os.environ.get("CNKI_SKILL_BACKEND")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".agents" / "tools" / "cnki-search-skill-backend"


def project_root() -> Path:
    """Return the project root used to resolve project-relative output paths.

    Agents normally launch the wrapper with the paper project as their current
    working directory.  CNKI_PROJECT_ROOT is an explicit override for hosts
    whose command runner cannot guarantee that behavior.
    """
    override = os.environ.get("CNKI_PROJECT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path.cwd().resolve()


def _absolute_project_path(raw: str, root: Path) -> str:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return str(path.resolve())
    return str((root / path).resolve())


def normalize_args(args: Iterable[str], root: Path) -> list[str]:
    """Normalize project-relative output directories before backend handoff.

    Supports both ``--dir VALUE`` and ``--dir=VALUE``.  Absolute paths are
    preserved semantically; relative paths are anchored to *root*.
    """
    src = list(args)
    out: list[str] = []
    i = 0
    while i < len(src):
        arg = src[i]
        if arg == "--dir":
            out.append(arg)
            if i + 1 >= len(src):
                # Leave malformed input for the upstream parser to report.
                i += 1
                continue
            out.append(_absolute_project_path(src[i + 1], root))
            i += 2
            continue
        if arg.startswith("--dir="):
            _, value = arg.split("=", 1)
            out.append(f"--dir={_absolute_project_path(value, root)}")
            i += 1
            continue
        out.append(arg)
        i += 1
    return out


def main() -> int:
    root = backend_root()
    run_py = root / ".claude" / "skills" / "cnki-search" / "run.py"
    if not run_py.is_file():
        print(
            "CNKI backend not found. Run the installer, or set CNKI_SKILL_BACKEND "
            "to a clone of LongMarching/cnki-search-skill.",
            file=sys.stderr,
        )
        print(f"Expected: {run_py}", file=sys.stderr)
        return 2

    project = project_root()
    forwarded = normalize_args(sys.argv[1:], project)

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # Expose the resolved project root to child processes and diagnostics.
    env.setdefault("CNKI_PROJECT_ROOT", str(project))
    cmd = [sys.executable, str(run_py), *forwarded]
    try:
        return subprocess.call(cmd, cwd=str(project), env=env)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

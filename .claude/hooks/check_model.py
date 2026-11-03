#!/usr/bin/env python3
"""PostToolUse hook for Write and Edit on dbt models: every model needs tests, marts list their columns.

The edit has already happened, so exit 2 does not undo it. It shows stderr to Claude, which then fixes the
problem in its next step. Standard library only.
"""

import json
import os
import re
import sys
from pathlib import Path

FEEDBACK = 2


def _model_name(file_path: Path, root: Path) -> str | None:
    try:
        relative = file_path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return file_path.stem if relative.parts[:1] == ("models",) and file_path.suffix == ".sql" else None


def _has_tests(model: str, root: Path) -> bool:
    pattern = re.compile(rf"^\s*-\s*name:\s*{re.escape(model)}\s*$", re.MULTILINE)
    return any(pattern.search(yml.read_text(encoding="utf-8")) for yml in (root / "models").rglob("*.yml"))


def problems(file_path: Path, root: Path) -> list[str]:
    model = _model_name(file_path, root)
    if model is None or not file_path.exists():
        return []
    found = []
    if not _has_tests(model, root):
        found.append(f"Model {model} has no entry in a schema .yml. Add it with unique + not_null on its key.")
    sql = file_path.read_text(encoding="utf-8")
    if "marts" in file_path.parts and re.search(r"select\s+\*", sql, re.IGNORECASE):
        found.append(f"{model} is a mart: list its columns instead of SELECT *, so upstream changes can't leak in.")
    return found


def main() -> int:
    event = json.load(sys.stdin)
    if event.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".")
    found = problems(Path(event.get("tool_input", {}).get("file_path", "")), root)
    if found:
        print("check_model:\n- " + "\n- ".join(found), file=sys.stderr)
        return FEEDBACK
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""PreToolUse hook for Bash: stop destructive SQL, production targets and force pushes before they run.

Claude Code sends the tool call as JSON on stdin. Exit 2 blocks the command and shows stderr to Claude,
which then explains the block to the user instead of retrying. Standard library only.
"""

import json
import re
import sys

BLOCK = 2

RULES: tuple[tuple[str, str], ...] = (
    (r"\bdrop\s+(table|schema|database|view)\b", "DROP is blocked. Ask the user to run it themselves."),
    (r"\btruncate\s+(table\s+)?[\w.\"]+", "TRUNCATE is blocked. Ask the user to run it themselves."),
    (r"\bdbt\b.*\s(--target|-t)[\s=]+prod\w*", "dbt against production is blocked. Use the dev target."),
    (r"\bdbt\b.*--full-refresh", "--full-refresh rebuilds tables from scratch. Ask the user first."),
    (r"\bgit\s+push\b.*(--force\b|-f\b)", "Force push is blocked."),
)


def _delete_without_where(command: str) -> bool:
    statements = re.split(r";", command, flags=re.IGNORECASE)
    return any(
        re.search(r"\bdelete\s+from\b", s, re.IGNORECASE) and not re.search(r"\bwhere\b", s, re.IGNORECASE)
        for s in statements
    )


def reason_to_block(command: str) -> str | None:
    for pattern, reason in RULES:
        if re.search(pattern, command, re.IGNORECASE):
            return reason
    if _delete_without_where(command):
        return "DELETE without WHERE is blocked: it would empty the whole table."
    return None


def main() -> int:
    event = json.load(sys.stdin)
    if event.get("tool_name") != "Bash":
        return 0
    reason = reason_to_block(event.get("tool_input", {}).get("command", ""))
    if reason:
        print(f"Blocked by guard_bash: {reason}", file=sys.stderr)
        return BLOCK
    return 0


if __name__ == "__main__":
    sys.exit(main())

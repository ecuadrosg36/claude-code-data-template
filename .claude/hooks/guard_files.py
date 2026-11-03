#!/usr/bin/env python3
"""PreToolUse hook for Write and Edit: keep secrets out of files and protected files untouched.

Blocks edits to secret files (.env, keys) and blocks writing anything that looks like a credential.
Exit 2 blocks the edit and tells Claude why. Standard library only.
"""

import json
import re
import sys
from pathlib import PurePath

BLOCK = 2

PROTECTED_NAMES = re.compile(r"^(\.env(\..+)?|.*\.pem|.*\.key|id_rsa.*|credentials\.json)$")
SECRET_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"AKIA[0-9A-Z]{16}", "an AWS access key"),
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "an Anthropic API key"),
    (r"AIza[0-9A-Za-z_-]{35}", "a Google API key"),
    (r"gh[pousr]_[A-Za-z0-9]{36,}", "a GitHub token"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "a private key"),
    (r"(password|passwd|secret)\s*[:=]\s*['\"](?!\{\{)[^'\"\s$]{6,}['\"]", "a hard-coded password"),
)


def reason_to_block(file_path: str, new_text: str) -> str | None:
    if PROTECTED_NAMES.match(PurePath(file_path).name):
        return f"{file_path} holds secrets and is protected. Ask the user to edit it."
    for pattern, what in SECRET_PATTERNS:
        if re.search(pattern, new_text, re.IGNORECASE):
            return f"the new text contains {what}. Read it from an environment variable (env_var() in dbt) instead."
    return None


def main() -> int:
    event = json.load(sys.stdin)
    if event.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    tool_input = event.get("tool_input", {})
    new_text = tool_input.get("content") or tool_input.get("new_string") or ""
    reason = reason_to_block(tool_input.get("file_path", ""), new_text)
    if reason:
        print(f"Blocked by guard_files: {reason}", file=sys.stderr)
        return BLOCK
    return 0


if __name__ == "__main__":
    sys.exit(main())

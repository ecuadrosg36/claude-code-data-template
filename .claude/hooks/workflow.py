"""Local workflow checks, not a security sandbox. JSON stdin/stdout hook protocol."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[2]


def variants(command: str) -> list[str]:
    """Inspect literal shell wrappers without executing any submitted command."""
    found = [command]
    frontier = [command]
    for _ in range(3):
        next_level = []
        for value in frontier:
            try:
                next_level.extend(shlex.split(value, comments=False))
            except ValueError:
                pass
        found.extend(next_level)
        frontier = [x for x in next_level if ' ' in x]
    return found


def guard(command: str, environment: dict[str, str] | None = None) -> str | None:
    environment = os.environ if environment is None else environment
    # Remove SQL comments before detecting keyword boundaries, including DR/**/OP.
    candidates = [re.sub(r'/\*.*?\*/', replacement, x, flags=re.S)
                  for x in variants(command) for replacement in ('', ' ')]
    candidates = [re.sub(r'--[^\n]*', '', x) for x in candidates]
    # Targets are deliberately restricted to this repository's only output: dev.
    # Inspect original text too: SQL comment removal must not hide --target.
    for text in variants(command):
        if re.search(r'(?i)\bdbt\b', command):
            targets = re.findall(r'(?:--target(?:=|\s+)|(?<![\w-])-t\s*=?\s*)[\'\"]?([\w-]+)', text)
            targets += re.findall(r'(?i)DBT_TARGET\s*=\s*[\'"]?([\w-]+)', text)
            if any(t.lower() != 'dev' for t in targets) or environment.get('DBT_TARGET', 'dev').lower() != 'dev':
                return 'Only the dev target is permitted. Remove the target override and use profiles.yml.'
        if re.search(r'(?i)\b(?:prod|production)[\"`]?\s*\.', text):
            if re.search(r'(?i)\b(insert|merge|create|alter|copy|update|delete|drop|truncate)\b', command):
                return 'Writes naming a prod/production schema are blocked. Use the local dev database.'
    for text in candidates:
        if re.search(r'(?i)\b(drop|truncate)\b', text):
            return 'DROP/TRUNCATE blocked. Use a reviewed migration outside this demo workflow.'
        for match in re.finditer(r'(?i)\b(delete\s+from|update)\s+(?=\S)', text):
            sql = text[match.start():].split(';', 1)[0].strip().rstrip("\"'")
            try:
                tree = sqlglot.parse_one(sql, read='duckdb')
            except sqlglot.errors.SqlglotError:
                return 'Cannot verify SQL mutation. Use one literal SQL statement with an explicit WHERE.'
            if not isinstance(tree, (exp.Delete, exp.Update)) or tree.args.get('where') is None:
                return 'DELETE/UPDATE requires a top-level WHERE in every statement. Scope the affected rows.'
    return None


def run_dbt(arguments: list[str]) -> tuple[bool, str]:
    """Fixed executable, project, target and argv; never shell-evaluate tool input."""
    executable = ROOT / '.venv/bin/dbt'
    env = dict(os.environ, DBT_SEND_ANONYMOUS_USAGE_STATS='false', DBT_TARGET='dev')
    try:
        result = subprocess.run(
            [str(executable), *arguments, '--project-dir', str(ROOT),
             '--profiles-dir', str(ROOT), '--target', 'dev'],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, 'dbt unavailable or timed out. Run uv sync --frozen, then rerun dbt locally.'
    # Do not echo arbitrary dbt output: SQL, profiles, or errors can contain secrets.
    return result.returncode == 0, f'dbt {arguments[0]} exited {result.returncode}. Inspect local logs/dbt.log and target/run_results.json; fix the cause and rerun.'


def handle(event: dict) -> dict:
    name = event.get('hook_event_name')
    if name == 'PreToolUse' and event.get('tool_name') == 'Bash':
        command = event.get('tool_input', {}).get('command')
        reason = guard(command) if isinstance(command, str) else 'Missing Bash command; cannot inspect it.'
        if reason:
            return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}
    elif name == 'PostToolUse' and event.get('tool_name') in ('Edit', 'Write'):
        raw = event.get('tool_input', {}).get('file_path')
        if not isinstance(raw, str):
            return {'decision': 'block', 'reason': 'Missing file_path; model validation could not run.'}
        path = Path(raw)
        path = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(ROOT / 'models') or path.suffix != '.sql':
            return {}
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', path.stem):
            return {'decision': 'block', 'reason': 'Rename model to an identifier: letters, digits, underscores; no selector syntax.'}
        ok, reason = run_dbt(['build', '--select', path.stem + '+'])
        if not ok:
            return {'decision': 'block', 'reason': reason}
    elif name == 'Stop':
        if event.get('stop_hook_active') is True:
            # Explicit loop escape, never a green status or a completion certification.
            return {'systemMessage': 'Stop loop escape: validation NOT certified. Report outstanding failures; do not claim completion.'}
        ok, reason = run_dbt(['test'])
        if not ok:
            return {'decision': 'block', 'reason': reason + ' Do not claim completion. If unable to fix, report the blocker on the next stop attempt.'}
    return {}


def main() -> None:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError('Expected JSON object')
        output = handle(event)
    except (ValueError, TypeError, KeyError, AttributeError):
        # exit 2 is documented blocking feedback for all configured events.
        print('Invalid hook input. Send a JSON object with documented event and tool_input fields.', file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(output))


if __name__ == '__main__':
    main()

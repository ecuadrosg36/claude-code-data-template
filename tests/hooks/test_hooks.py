"""Each hook is run the way Claude Code runs it: a JSON event on stdin, then check the exit code and stderr."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
BLOCKED = 2


def run_hook(name: str, event: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", **(env or {})},
        check=False,
    )


def bash(command: str) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}


@pytest.mark.parametrize(
    "command",
    [
        "duckdb shop.duckdb -c 'DROP TABLE fct_orders'",
        "duckdb shop.duckdb -c 'drop schema main cascade'",
        "duckdb shop.duckdb -c 'TRUNCATE fct_orders'",
        "duckdb shop.duckdb -c 'DELETE FROM fct_orders'",
        "duckdb shop.duckdb -c 'delete from a where id = 1; delete from b'",
        "uv run dbt build --target prod",
        "uv run dbt run -t production",
        "uv run dbt run --target=prod --select fct_orders",
        "uv run dbt run --full-refresh",
        "git push --force origin main",
        "git push -f",
    ],
)
def test_risky_commands_are_blocked(command: str) -> None:
    result = run_hook("guard_bash.py", bash(command))

    assert result.returncode == BLOCKED
    assert result.stderr.startswith("Blocked by guard_bash:")


@pytest.mark.parametrize(
    "command",
    [
        "uv run dbt build",
        "uv run dbt run --target dev --select fct_orders",
        "duckdb shop.duckdb -c 'DELETE FROM fct_orders WHERE order_id = 1'",
        "duckdb shop.duckdb -c 'select * from dropped_items'",
        "ls -t production/",
        "git push origin feature/new-model",
    ],
)
def test_normal_work_is_allowed(command: str) -> None:
    result = run_hook("guard_bash.py", bash(command))

    assert result.returncode == 0, result.stderr


def test_other_tools_are_ignored_by_the_bash_guard() -> None:
    assert run_hook("guard_bash.py", {"tool_name": "Read", "tool_input": {"file_path": "x"}}).returncode == 0


def write(path: str, content: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": path, "content": content},
    }


@pytest.mark.parametrize(
    ("path", "content"),
    [
        (".env", "DUCKDB_PATH=shop.duckdb"),
        ("config/.env.prod", "X=1"),
        ("keys/service.pem", "..."),
        ("profiles.yml", "password: 'SuperSecret123'"),
        ("scripts/load.py", 'KEY = "AKIAABCDEFGHIJKLMNOP"'),
        ("scripts/llm.py", 'client = Anthropic(api_key="sk-ant-api03-abcdefghijklmnopqrstuvwxyz")'),
        ("notes.md", "-----BEGIN RSA PRIVATE KEY-----"),
    ],
)
def test_secrets_are_blocked(path: str, content: str) -> None:
    result = run_hook("guard_files.py", write(path, content))

    assert result.returncode == BLOCKED
    assert "Blocked by guard_files:" in result.stderr


@pytest.mark.parametrize(
    "content",
    [
        "password: \"{{ env_var('DB_PASSWORD') }}\"",
        "select order_id from {{ ref('stg_orders') }}",
        "api_key = os.environ['ANTHROPIC_API_KEY']",
    ],
)
def test_safe_content_is_allowed(content: str) -> None:
    assert run_hook("guard_files.py", write("models/x.sql", content)).returncode == 0


def test_edit_new_string_is_checked() -> None:
    event = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "a.py", "old_string": "x", "new_string": "AKIAABCDEFGHIJKLMNOP"},
    }

    assert run_hook("guard_files.py", event).returncode == BLOCKED


def edited(path: Path) -> dict:
    return {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(path)}}


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "models" / "marts").mkdir(parents=True)
    (tmp_path / "models" / "marts" / "_marts.yml").write_text("models:\n  - name: fct_sales\n")
    return tmp_path


def test_model_with_tests_and_columns_passes(project: Path) -> None:
    model = project / "models" / "marts" / "fct_sales.sql"
    model.write_text("select order_id, amount from {{ ref('stg_orders') }}")

    assert run_hook("check_model.py", edited(model), {"CLAUDE_PROJECT_DIR": str(project)}).returncode == 0


def test_model_without_tests_gets_feedback(project: Path) -> None:
    model = project / "models" / "marts" / "fct_refunds.sql"
    model.write_text("select order_id from {{ ref('stg_orders') }}")

    result = run_hook("check_model.py", edited(model), {"CLAUDE_PROJECT_DIR": str(project)})

    assert result.returncode == BLOCKED
    assert "fct_refunds has no entry in a schema .yml" in result.stderr


def test_select_star_in_a_mart_gets_feedback(project: Path) -> None:
    model = project / "models" / "marts" / "fct_sales.sql"
    model.write_text("SELECT * FROM {{ ref('stg_orders') }}")

    result = run_hook("check_model.py", edited(model), {"CLAUDE_PROJECT_DIR": str(project)})

    assert result.returncode == BLOCKED
    assert "list its columns" in result.stderr


def test_files_outside_models_are_ignored(project: Path) -> None:
    script = project / "scripts" / "x.sql"
    script.parent.mkdir()
    script.write_text("select *")

    assert run_hook("check_model.py", edited(script), {"CLAUDE_PROJECT_DIR": str(project)}).returncode == 0


def test_settings_point_at_every_hook() -> None:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
    commands = [h["command"] for groups in settings["hooks"].values() for g in groups for h in g["hooks"]]

    for hook in HOOKS.glob("*.py"):
        assert any(hook.name in c for c in commands), f"{hook.name} is not wired in settings.json"

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/hooks/workflow.py'
spec = importlib.util.spec_from_file_location('workflow', SCRIPT)
hooks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hooks)


@pytest.mark.parametrize('command', [
    'duckdb x -c "DROP TABLE orders"',
    "bash -lc 'duckdb x -c \"tRuNcAtE orders\"'",
    'duckdb x -c "DR/**/OP TABLE orders"',
    'duckdb x -c "delete/**/from orders"',
    'duckdb x -c "update/**/orders set amount=0"',
    'dbt build --target "prod"',
    "duckdb x -c 'insert into \"prod\".orders values (1)'",
    'duckdb x -c "select 1; delete from orders"',
    'duckdb x -c "update orders set amount=0"',
    'duckdb x -c "delete from orders -- WHERE id=1"',
    'duckdb x -c "update orders set x=(select x from t where id=1)"',
    'duckdb x -c "delete from orders where id=1; update orders set x=1"',
    'uv run dbt build --target prod', 'dbt run -tproduction',
    "bash -c 'DBT_TARGET=prod dbt seed'", 'dbt build --target=staging',
    'duckdb x -c "insert into production.orders values (1)"',
    'duckdb x -c "update orders set note=\'WHERE\'"',
])
def test_denied(command):
    assert hooks.guard(command, {})


@pytest.mark.parametrize('command', [
    'uv run dbt build --target dev', 'uv run pytest',
    'duckdb x -c "select * from orders"',
    'duckdb x -c "delete from orders where order_id=1"',
    'duckdb x -c "update orders set amount=1 where order_id=2"',
    'echo dropdown', 'dbt build -t dev',
])
def test_allowed(command):
    assert hooks.guard(command, {}) is None


def test_inherited_prod():
    assert hooks.guard('dbt build', {'DBT_TARGET': 'prod'})


def test_pre_protocol():
    result = hooks.handle({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': 'DROP TABLE x'}})
    assert result['hookSpecificOutput']['permissionDecision'] == 'deny'


@pytest.mark.parametrize('name', ['staging/stg_orders.sql', 'marts/fct_customer_orders.sql'])
def test_model_select(monkeypatch, name):
    calls = []
    monkeypatch.setattr(hooks, 'run_dbt', lambda args: (calls.append(args) or True, ''))
    assert hooks.handle({'hook_event_name': 'PostToolUse', 'tool_name': 'Edit', 'tool_input': {'file_path': str(ROOT / 'models' / name)}}) == {}
    assert calls == [['build', '--select', Path(name).stem + '+']]


@pytest.mark.parametrize('path', ['README.md', 'models_extra/x.sql', '../outside.sql', 'models/stg_orders.yml'])
def test_path_boundary(monkeypatch, path):
    monkeypatch.setattr(hooks, 'run_dbt', lambda _: pytest.fail('must not run dbt'))
    assert hooks.handle({'hook_event_name': 'PostToolUse', 'tool_name': 'Write', 'tool_input': {'file_path': str(ROOT / path)}}) == {}


def test_selector_injection(monkeypatch):
    monkeypatch.setattr(hooks, 'run_dbt', lambda _: pytest.fail('must not run dbt'))
    result = hooks.handle({'hook_event_name': 'PostToolUse', 'tool_name': 'Write', 'tool_input': {'file_path': str(ROOT / 'models/evil;touch secret.sql')}})
    assert result['decision'] == 'block'


def test_symlink_boundary(monkeypatch, tmp_path):
    monkeypatch.setattr(hooks, 'ROOT', tmp_path)
    (tmp_path / 'models').mkdir()
    (tmp_path / 'models/external.sql').symlink_to('/tmp/external.sql')
    monkeypatch.setattr(hooks, 'run_dbt', lambda _: pytest.fail('must not run dbt'))
    assert hooks.handle({'hook_event_name': 'PostToolUse', 'tool_name': 'Edit', 'tool_input': {'file_path': str(tmp_path / 'models/external.sql')}}) == {}


@pytest.mark.parametrize('event', ['PostToolUse', 'Stop'])
def test_failure_protocol(monkeypatch, event):
    monkeypatch.setattr(hooks, 'run_dbt', lambda _: (False, 'dbt failed: inspect target/run_results.json'))
    result = hooks.handle({'hook_event_name': event, 'tool_name': 'Edit', 'tool_input': {'file_path': str(ROOT / 'models/staging/stg_orders.sql')}, 'stop_hook_active': False})
    assert result['decision'] == 'block'
    assert 'run_results' in result['reason']


def test_stop_loop_escape(monkeypatch):
    monkeypatch.setattr(hooks, 'run_dbt', lambda _: pytest.fail('must not loop'))
    result = hooks.handle({'hook_event_name': 'Stop', 'stop_hook_active': True})
    assert 'decision' not in result
    assert 'NOT certified' in result['systemMessage']


def test_stop_success(monkeypatch):
    monkeypatch.setattr(hooks, 'run_dbt', lambda args: (args == ['test'], ''))
    assert hooks.handle({'hook_event_name': 'Stop'}) == {}


def test_runner_argv_and_failure(monkeypatch):
    def fake_run(argv, **kwargs):
        assert argv[1:4] == ['build', '--select', 'stg_orders+']
        assert argv[-2:] == ['--target', 'dev']
        assert kwargs.get('shell', False) is False
        assert kwargs['env']['DBT_SEND_ANONYMOUS_USAGE_STATS'] == 'false'
        return subprocess.CompletedProcess(argv, 1, 'sensitive SQL', 'secret')
    monkeypatch.setattr(hooks.subprocess, 'run', fake_run)
    ok, message = hooks.run_dbt(['build', '--select', 'stg_orders+'])
    assert not ok and 'exited 1' in message
    assert 'secret' not in message and 'sensitive' not in message


@pytest.mark.parametrize('error', [FileNotFoundError(), subprocess.TimeoutExpired('dbt', 90)])
def test_runner_unavailable(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(hooks.subprocess, 'run', fail)
    assert hooks.run_dbt(['test'])[0] is False


def test_malformed_input():
    run = subprocess.run([sys.executable, str(SCRIPT)], input='[]', capture_output=True, text=True)
    assert run.returncode == 2 and 'Invalid hook input' in run.stderr


def test_cli_json_denial():
    event = {'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': 'DROP TABLE x'}}
    run = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(event), capture_output=True, text=True)
    assert run.returncode == 0
    assert json.loads(run.stdout)['hookSpecificOutput']['permissionDecision'] == 'deny'

"""Reproduce hook feedback with real local dbt; never execute submitted Bash SQL.

Run after uv sync and dbt build. Intentionally injects a duplicate synthetic
seed row into the dev database and restores via a full build in finally.
"""
import importlib.util
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workflow', ROOT / '.claude/hooks/workflow.py')
hooks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hooks)


def show(label, event):
    result = hooks.handle(event)
    print(label)
    print(json.dumps(result, sort_keys=True))
    return result


def main():
    print('Offline hook demo: real hook handlers and local dbt; no Claude/model/API session.')
    denied = show('PreToolUse Bash: duckdb -c "DROP TABLE raw_orders" (submitted text only)', {
        'hook_event_name': 'PreToolUse', 'tool_name': 'Bash',
        'tool_input': {'command': 'duckdb -c "DROP TABLE raw_orders"'},
    })
    assert denied['hookSpecificOutput']['permissionDecision'] == 'deny'
    post = {'hook_event_name': 'PostToolUse', 'tool_name': 'Edit',
            'tool_input': {'file_path': str(ROOT / 'models/staging/stg_orders.sql')}}
    assert show('PostToolUse stg_orders.sql: build --select stg_orders+ (healthy)', post) == {}
    try:
        with duckdb.connect(str(ROOT / 'target/portfolio.duckdb')) as connection:
            connection.execute('insert into raw_orders select * from raw_orders where order_id = 1')
        print('Injected one duplicate synthetic order into local dev seed table.')
        assert show('PostToolUse stg_orders.sql: downstream build detects duplicate', post)['decision'] == 'block'
        assert show('Stop: real dbt test detects duplicate', {'hook_event_name': 'Stop', 'stop_hook_active': False})['decision'] == 'block'
        escape = show('Stop retry: explicit loop escape, NOT a passing result', {'hook_event_name': 'Stop', 'stop_hook_active': True})
        assert 'decision' not in escape
    finally:
        ok, reason = hooks.run_dbt(['build'])
        if not ok:
            raise RuntimeError('Restore failed: ' + reason)
        print('Restored seed and rebuilt all models/tests successfully.')
    assert show('Stop after repair: real dbt test passes', {'hook_event_name': 'Stop', 'stop_hook_active': False}) == {}
    with duckdb.connect(str(ROOT / 'target/portfolio.duckdb'), read_only=True) as connection:
        rows = connection.execute('select * from fct_customer_orders order by customer_id').fetchall()
    print('Verified mart rows (customer_id, completed_order_count, revenue_cents): ' + repr(rows))


if __name__ == '__main__':
    main()

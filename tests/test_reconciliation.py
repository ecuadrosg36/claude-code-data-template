"""Execute the shipped reconciliation SQL against isolated synthetic relations."""
from pathlib import Path

import duckdb
from jinja2 import Environment, StrictUndefined
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(('mart_rows', 'violations'), [
    ([(101, 2, 15000)], []),
    ([(101, None, 15000)], [(101,)]),
    ([(101, 2, None)], [(101,)]),
    ([(101, 1, 15000)], [(101,)]),
    ([(101, 2, 1)], [(101,)]),
    ([], [(101,)]),
    ([(101, 2, 15000), (999, 1, 100)], [(999,)]),
])
def test_customer_revenue_reconciliation(mart_rows, violations):
    sql = Environment(undefined=StrictUndefined).from_string(
        (ROOT / 'data_tests/customer_revenue_reconciles.sql').read_text()
    ).render(ref=lambda name: {'stg_orders': 'stg_orders',
                              'fct_customer_orders': 'fct_customer_orders'}[name])
    with duckdb.connect(':memory:') as connection:
        connection.execute('create table stg_orders(customer_id integer, status varchar, amount_cents bigint)')
        connection.execute("insert into stg_orders values (101, 'completed', 12000), (101, 'completed', 3000), (101, 'cancelled', 5000)")
        connection.execute('create table fct_customer_orders(customer_id integer, completed_order_count bigint, revenue_cents bigint)')
        if mart_rows:
            connection.executemany('insert into fct_customer_orders values (?, ?, ?)', mart_rows)
        assert sorted(connection.execute(sql).fetchall()) == violations

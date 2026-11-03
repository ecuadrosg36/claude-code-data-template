---
name: reconcile
description: Compare row counts and totals between two dbt models, overall and per day, to prove a change did not lose or duplicate data. Use before calling a model change done, or when numbers look off.
---

# Reconcile two models

Compare an upstream model with a downstream one. Pick the date column on each side (names can differ, e.g.
`ordered_at` upstream and `order_date` downstream) and a measure such as `amount` if there is one.

```bash
uv run dbt show --profiles-dir . --inline "
with up as (
    select cast(<upstream_date> as date) as day, count(*) as n, sum(<measure>) as total
    from {{ ref('<upstream>') }} group by 1
), down as (
    select cast(<downstream_date> as date) as day, count(*) as n, sum(<measure>) as total
    from {{ ref('<downstream>') }} group by 1
)
select coalesce(up.day, down.day) as day, up.n as rows_up, down.n as rows_down,
       up.total as total_up, down.total as total_down
from up full outer join down using (day)
where up.n is distinct from down.n or up.total is distinct from down.total
order by day"
```

- **No rows returned:** the two models agree day by day.
- **rows_down < rows_up:** the downstream model lost rows. Look for inner joins and `where` filters.
- **rows_down > rows_up:** fan-out from a join on a non-unique key, or duplicates.
- **Same rows, different total:** a value changed: casting, rounding or a wrong column.

Report the result as a short table. If the counts are meant to differ (a filter by design), say why.

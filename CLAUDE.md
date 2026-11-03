# Project rules for Claude Code

This is a dbt project on DuckDB. Data correctness matters more than speed: a wrong number in a report is
worse than a slow change.

## Commands

- Build and test everything: `uv run dbt build --profiles-dir .`
- One model and its children: `uv run dbt build --profiles-dir . --select fct_orders+`
- Look at data: `uv run dbt show --profiles-dir . --inline "select ..."`
- Hook tests: `uv run pytest`

Only the `dev` target exists here. Never add or use a production target; the user runs production.

## Layers

- `models/staging/`: one model per source table. Rename, cast and clean only. No joins. Views.
- `models/marts/`: business tables built from staging. Joins and metrics go here. Tables.
- Name models `stg_<source>`, `fct_<event>` (one row per event) and `dim_<thing>` (one row per thing).

## Every model

- Write the grain in the model's description: "one row per ...".
- Add it to the folder's `.yml` with `unique` and `not_null` on the key. The `check_model` hook reminds you.
- Marts list their columns. No `select *` outside staging.
- Prefer `left join` and label missing matches (`'UNKNOWN'`). An inner join silently drops rows; only use it
  when dropping is the point, and say so in a comment.

## Before you say a change is done

1. `uv run dbt build --profiles-dir .` passes.
2. Compare row counts before and after for every model you touched (the `reconcile` skill does this).
   Explain any change in counts. "It builds" is not enough.
3. If a number in a mart changed, show one example row before and after.

## Things you must not do

Hooks block these, but don't try them in the first place: `DROP`, `TRUNCATE`, `DELETE` without `WHERE`,
`--full-refresh`, any production target, force push, editing `.env` or writing credentials into files. If one
of them is really needed, explain why and let the user run it.

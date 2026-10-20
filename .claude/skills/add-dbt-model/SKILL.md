---
name: add-dbt-model
description: Add a dbt model with declared grain, schema tests, and downstream validation in this DuckDB project.
---
Read CLAUDE.md, dbt_project.yml, and nearby models before adding a model.
Establish its business purpose, one-row grain, key, and upstream refs. Clarify
ambiguous grain before implementation. Use stg_ for typed staging or fct_ for
business facts, explicit columns, ref(), and integer cents for money.
Add a models/schema.yml entry with description, key unique/not_null tests,
and relevant accepted-values or reconciliation tests. Use synthetic fixtures.
Run `uv run dbt build --profiles-dir . --target dev --select <model>+` using the
actual validated identifier. If upstream tables are absent, run the full build.
Inspect real test results, fix root causes, and report commands and counts.
Do not call a failed or unexecuted validation successful.

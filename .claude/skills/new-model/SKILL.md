---
name: new-model
description: Add a new dbt model the way this project expects - right layer, grain written down, tests, and a row-count check. Use when the user asks for a new staging model, fact or dimension.
---

# Add a dbt model

1. **Pick the layer.** One source table, cleaning only: `models/staging/stg_<source>.sql`.
   Joins or metrics: `models/marts/fct_<event>.sql` or `dim_<thing>.sql`.
2. **Write the grain first**, as the model's description: "One row per order."
3. **Write the SQL.** Reference inputs with `{{ ref() }}`. List columns explicitly in marts. Use `left join`
   and label missing matches unless dropping rows is the goal.
4. **Add tests** in the folder's `.yml`:
   ```yaml
   - name: fct_example
     description: One row per ...
     columns:
       - name: example_id
         data_tests: [unique, not_null]
   ```
5. **Build it and its children:** `uv run dbt build --profiles-dir . --select <model>+`
6. **Check the counts** with the `reconcile` skill: the new model against its main input. Explain any
   difference before saying the model is done.

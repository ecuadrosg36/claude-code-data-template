# Engineering contract

Use Python 3.12 and `uv sync --frozen`. All data here is synthetic. Never access
production, copy personal data, print credentials, or commit profiles containing
secrets. Only the committed dev DuckDB target is permitted. The hooks are local
workflow feedback, not a security sandbox or a substitute for database permissions.

Declare each model's grain in SQL and YAML. Use `stg_` for typed staging and
`fct_` for business facts. Use explicit columns, `ref()`, integer cents, and tests
for keys, nullability, categories, and business reconciliation. Diagnose failing
tests before changing expectations. Review downstream effects and avoid fanout.

Definition of done: pytest passes; a fresh `uv run dbt build --profiles-dir .
--target dev` passes; results and limitations are accurately documented; no
secrets or generated databases are tracked. Post-edit validation assumes parents
were built. Hooks do not run for Bash edits or arbitrary external tools. A Stop
loop escape is not a passing result: report outstanding blockers explicitly.

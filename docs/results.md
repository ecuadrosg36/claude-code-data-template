# Verified results

Local verification on 2026-10-20, macOS arm64. These are synthetic example
results, not production performance measurements. [demo.txt](demo.txt) is actual
captured stdout from `scripts/demo.py`, not a reconstructed conversation.

| Check | Observed result |
| --- | --- |
| `uv sync` | Resolved and installed dependencies; lockfile committed |
| `.venv/bin/pytest -q` | 46 passed |
| Fresh dbt clean then `dbt build --profiles-dir . --target dev` | PASS=14, WARN=0, ERROR=0, SKIP=0; 1 seed, 2 models, 11 tests |
| Published settings schema validation | Passed with jsonschema; fetched schema SHA-256 below |
| Skill frontmatter validator | `Skill is valid!` |
| Real downstream build via PostToolUse | Passed healthy; exited 1 and returned documented block feedback after duplicate injection |
| Real Stop via dbt test | Exited 1 on duplicate, returned block feedback; retry escaped with NOT certified message; passed after full rebuild |
| Verified mart query | `(101, 2, 15000)`, `(103, 1, 2500)` — customer, completed orders, cents |

The demo inserts a duplicate of order 1 into the local seed table, provoking
unique-key failure. It restores seeds and all derived relations in a `finally`
block, then verifies tests pass. Hook subprocess tests also cover missing dbt,
timeouts, nonzero return codes, argv boundaries, and secret-safe error messages.
Command cases include case changes, literal shell wrappers, SQL comments,
statement batches, a nested WHERE that must not count as an outer WHERE,
non-dev targets (including inherited DBT_TARGET), and quoted production schemas.
Path cases include siblings, outside paths, symlink escapes, and selector syntax.

Versions actually observed: Python **3.12.13**, uv **0.11.1**, dbt-core **1.12.6**,
dbt-duckdb **1.11.0**, DuckDB **1.5.6**, pytest **9.1.1**, sqlglot **29.0.1**,
jsonschema **4.26.0**. Installed Claude Code reports **2.1.304**; only its version
was queried. No authenticated Claude/model/API session was used.

Official docs were read before configuration on 2026-10-20: [settings](https://code.claude.com/docs/en/settings),
[hooks](https://code.claude.com/docs/en/hooks),
[subagents](https://code.claude.com/docs/en/sub-agents), and
[skills](https://code.claude.com/docs/en/skills). See [compatibility](compatibility.md)
for field-level provenance and limits. The fetched
[published settings schema](https://json.schemastore.org/claude-code-settings.json)
had SHA-256 `f26f028ad94a1e2a28e9dad1f80832ab196a8e080bd3a7d7a32e6428a15e0611`.
Schema validation used `scripts/validate_settings.py` with that local file.
To repeat independently:

```sh
curl --fail --location https://json.schemastore.org/claude-code-settings.json -o /tmp/claude-settings-schema.json
uv run python scripts/validate_settings.py /tmp/claude-settings-schema.json
uv run pytest -q
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run dbt clean --profiles-dir .
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run dbt build --profiles-dir . --target dev
uv run python scripts/demo.py > docs/demo.txt
```

The schema and CLI can change after this date. No minimum CLI version or
interactive hook loading is certified. Hooks can be bypassed and Stop's loop
escape does not certify completion; [README](../README.md) details those limits.
Hosted CI evidence is available on the pull request; local results above stand
independently of hosted execution.

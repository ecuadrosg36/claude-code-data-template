# dbt changes with evidence before completion

This portfolio demonstrates a local review loop for data engineers: reject obvious
destructive commands, build a changed model and its descendants, and return
failing tests to the agent before it claims completion. It combines a runnable
DuckDB pipeline with Claude Code configuration and deterministic hook tests.
It uses synthetic data and makes no claims about production impact or hiring outcomes.

A real offline run submitted a destructive command to the hook without executing
that command. The generated [full transcript](docs/demo.txt) also shows a genuine
duplicate-key failure, Stop feedback, repair, and passing tests:

```text
PreToolUse Bash: duckdb -c "DROP TABLE raw_orders" (submitted text only)
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "DROP/TRUNCATE blocked. Use a reviewed migration outside this demo workflow."}}
```

To reproduce with Python 3.12 and [uv](https://docs.astral.sh/uv/):

```sh
uv sync --frozen
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run dbt build --profiles-dir . --target dev
uv run pytest -q
uv run python scripts/demo.py
```

The demo intentionally duplicates one synthetic row in the local dev database,
then restores it in `finally` with a full build. Run it without concurrent dbt
processes. No Claude account, model, or API call is needed. CI installs locked
dependencies and runs pytest/dbt locally; dbt telemetry is disabled.

The graph is `raw_orders → stg_orders → fct_customer_orders`. Four synthetic
orders yield two customer rows; cancelled orders are excluded and money remains
integer cents. Key, category, and reconciliation tests check the declared grains.
See [validated versions and outcomes](docs/results.md).

| Piece | Purpose |
| --- | --- |
| [CLAUDE.md](CLAUDE.md) | Data safety, grain, naming, tests, definition of done |
| [.claude/settings.json](.claude/settings.json) | Documented command hooks, 120-second outer timeout |
| [.claude/hooks/workflow.py](.claude/hooks/workflow.py) | Literal command inspection; fixed local dbt argv and 90-second timeout |
| [.claude/agents](.claude/agents) | Read-only model reviewer and evidence-first quality investigator definitions |
| [.claude/skills/add-dbt-model](.claude/skills/add-dbt-model/SKILL.md) | Add a model with grain, tests, and downstream build |
| [tests](tests) | Allow/deny boundaries, paths, protocol, failures, and loop escape |
| [.github/workflows/verify.yml](.github/workflows/verify.yml) | pytest and full dbt build without model/API calls |

For adoption, clone, sync, build the parents once, and start Claude Code from the
repo root. Review and trust the hook scripts before enabling project settings.
Use `/status` to check loaded settings, `/agents` to inspect definitions, and
`/add-dbt-model` for the skill. Review organization and personal overrides.
The two agent definitions ship as examples; no subagents were used to build or
validate this project. See [compatibility and official sources](docs/compatibility.md).

These hooks are workflow checks, **not a security sandbox**. They inspect literal
Bash text, not arbitrary program behavior. Dynamic SQL, variable expansion,
encoded payloads, external SQL files, alternate tools, modified profiles, and
changed hooks can bypass them. Conservative matching can reject harmless strings
such as a comment containing `DROP`. A top-level WHERE is checked structurally;
`WHERE true` still passes and can affect every row. Use database permissions,
isolation, and human review for real protection. Never supply production credentials.

PostToolUse covers Edit/Write SQL files under the resolved `models/` path, not
Bash edits, YAML, seeds, or external tools. It requires parents already built;
run a full build on a fresh checkout. Model basenames must be unique identifiers.
Stop runs tests against existing dev relations, not a fresh rebuild; CI/full build
is the source-change check. Stop initially blocks a failing test, but deliberately
allows a repeated stop via `stop_hook_active` to avoid an infinite loop. That
escape explicitly reports validation as uncertified, and must never be presented
as success. Neither hooks nor CI authorize deployment or merging.

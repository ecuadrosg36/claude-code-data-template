# claude-code-data-template

[![CI](https://github.com/ecuadrosg36/claude-code-data-template/actions/workflows/ci.yml/badge.svg)](https://github.com/ecuadrosg36/claude-code-data-template/actions/workflows/ci.yml)

**A dbt + DuckDB starter where Claude Code follows your data rules and can't do the dangerous things.**

AI coding agents are fast at writing SQL. They are also fast at running `DROP TABLE`, pointing dbt at
production, or "fixing" a failing test by changing an inner join. This template puts guardrails in the
repository itself, so every session on the project gets them:

| Layer | What it does | File |
|---|---|---|
| **Rules** | Layers, naming, grain, tests, and what "done" means for a data change | [`CLAUDE.md`](CLAUDE.md) |
| **Hooks** | Code that blocks risky actions before they run, and checks models after edits | [`.claude/hooks/`](.claude/hooks) |
| **Permissions** | dbt and test commands run without prompts; `.env` can't be read | [`.claude/settings.json`](.claude/settings.json) |
| **Subagents** | `data-reviewer` checks grain, joins and nulls; `incident-investigator` finds where a number broke | [`.claude/agents/`](.claude/agents) |
| **Skills** | `new-model` adds a model the project's way; `reconcile` proves no rows were lost | [`.claude/skills/`](.claude/skills) |

Rules in `CLAUDE.md` are guidance the model reads. Hooks are code that runs on every tool call, so they hold
even when the model gets something wrong.

## What the hooks block

| Hook | When | Blocks or flags |
|---|---|---|
| `guard_bash.py` | Before any shell command | `DROP`, `TRUNCATE`, `DELETE` without `WHERE`, dbt with a `prod` target, `--full-refresh`, force push |
| `guard_files.py` | Before any file write or edit | Edits to `.env`, `*.pem`, key files; AWS, Anthropic, Google and GitHub keys; private keys; hard-coded passwords |
| `check_model.py` | After a model is written | A model with no tests in a `.yml`; `select *` in a mart |

A blocked action exits with code 2, and Claude Code shows Claude the reason. Claude then explains the block or
changes course instead of retrying. Allowed on purpose: `DELETE ... WHERE`, the `dev` target, normal pushes,
and `env_var()` in dbt profiles.

The hooks are plain Python with no dependencies. **34 tests** run each one exactly as Claude Code does,
with a JSON event on stdin, and check the exit code and message.

## The demo project

A small shop: customers and orders as seeds, two staging views, `fct_orders` and `dim_customers`. It shows the
habits the rules ask for:

- Order 1009 belongs to a customer who isn't loaded yet. `fct_orders` uses a `LEFT JOIN` and labels it
  `UNKNOWN`, so revenue stays complete.
- [`tests/dbt/assert_orders_not_lost.sql`](tests/dbt/assert_orders_not_lost.sql) reconciles staging and the
  mart. Changing the join to `INNER JOIN` makes `dbt build` fail on this test. That was checked by doing it.
- `dbt build` runs 2 seeds, 4 models and 12 data tests in CI.

## Use it

Click **Use this template** on GitHub, or:

```bash
git clone https://github.com/ecuadrosg36/claude-code-data-template my-project
cd my-project
uv sync
uv run dbt build --profiles-dir .
uv run pytest
claude      # start Claude Code; the rules, hooks, agents and skills load automatically
```

Then replace the seeds and models with your own. Keep `.claude/` and `CLAUDE.md`, and extend the hook rules
as your project finds new ways to break.

## Adapting it

- **Another warehouse:** swap `dbt-duckdb` for your adapter and add targets to `profiles.yml` with
  credentials from `env_var()`. `guard_bash.py` already blocks any target named `prod*`.
- **More rules:** add a pattern and a reason to `RULES` in `guard_bash.py` or `SECRET_PATTERNS` in
  `guard_files.py`, then add a test case.
- **Personal settings** go in `.claude/settings.local.json`, which is git-ignored.

MIT License.

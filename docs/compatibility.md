# Claude Code compatibility and provenance

Official documentation was browsed on 2026-10-20 **before configuration was
written**. This repo uses only command hooks; there are no prompt/model hooks.

- [Settings](https://code.claude.com/docs/en/settings): shared project JSON,
  project-root startup, and the documented
  [published JSON Schema](https://json.schemastore.org/claude-code-settings.json).
- [Hooks reference](https://code.claude.com/docs/en/hooks): `PreToolUse` matcher
  `Bash`, `PostToolUse` matcher `Edit|Write`, and unfiltered `Stop`. Input comes
  from stdin. PreToolUse denials use `hookSpecificOutput.permissionDecision`;
  PostToolUse and Stop failure feedback uses top-level `decision: block` and
  `reason`. Valid JSON decisions exit 0; malformed input exits 2 with stderr.
  PostToolUse cannot undo an edit. `stop_hook_active` provides this project's
  single-retry loop escape; the CLI also has its own continuation controls.
- [Subagents](https://code.claude.com/docs/en/sub-agents): Markdown files with
  YAML `name`, `description`, and `tools` under `.claude/agents/`. Read/Grep/Glob
  are deliberately the only tools configured. These are definitions, not evidence
  that a model executed a review.
- [Skills](https://code.claude.com/docs/en/skills): `.claude/skills/<name>/SKILL.md`
  with `name` and `description` frontmatter. No forked context is configured.

Start Claude Code from the repo root so `CLAUDE_PROJECT_DIR` resolves here.
Run `uv sync --frozen` first: hooks use the project venv directly and will not
install dependencies during an event. Paths in the configured shell command
are quoted; tool-supplied paths are resolved and checked before invoking dbt
with an argv list, never `shell=True`. Unix/macOS/Linux are the supported runtime
for this example (`.venv/bin`); Windows needs adjusted executable paths.

The offline tests validate the documented subset and hook wire responses. Full
settings JSON Schema validation was separately run against the published schema
(see results). Agent/skill frontmatter has local structural checks against the
fields above; no official machine-readable schema is claimed for those files.
No authenticated interactive Claude session was exercised. A precise minimum
Claude Code version is not claimed; use a current CLI, inspect loaded settings,
and rerun the local contract tests after upgrades. Settings schema publication
can lag the CLI, as the official settings page explains.

To repeat full schema validation, fetch the public schema into a local temporary
file, then run `uv run python scripts/validate_settings.py /path/to/schema.json`.
This network retrieval is an explicit developer step, not a CI operation.

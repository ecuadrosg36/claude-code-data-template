"""Offline structural checks of the documented configuration subset we use.

Full published JSON Schema validation is separately recorded in docs/results.md.
These checks do not pretend to be the full Claude Code settings schema.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_hook_configuration():
    settings = json.loads((ROOT / '.claude/settings.json').read_text())
    assert set(settings['hooks']) == {'PreToolUse', 'PostToolUse', 'Stop'}
    for event, entries in settings['hooks'].items():
        assert len(entries) == 1
        entry = entries[0]
        if event == 'Stop':
            assert 'matcher' not in entry
        else:
            assert entry['matcher'] == {'PreToolUse': 'Bash', 'PostToolUse': 'Edit|Write'}[event]
        hook = entry['hooks'][0]
        assert hook['type'] == 'command' and hook['timeout'] == 120
        assert hook['command'] == '"$CLAUDE_PROJECT_DIR"/.venv/bin/python "$CLAUDE_PROJECT_DIR"/.claude/hooks/workflow.py'


def frontmatter(path):
    return yaml.safe_load(path.read_text().split('---', 2)[1])


def test_documented_agent_and_skill_fields():
    for path in (ROOT / '.claude/agents').glob('*.md'):
        data = frontmatter(path)
        assert set(data) == {'name', 'description', 'tools'}
        assert data['name'] == path.stem
        assert data['tools'] == 'Read, Grep, Glob'
    path = ROOT / '.claude/skills/add-dbt-model/SKILL.md'
    data = frontmatter(path)
    assert set(data) == {'name', 'description'}
    assert data['name'] == path.parent.name

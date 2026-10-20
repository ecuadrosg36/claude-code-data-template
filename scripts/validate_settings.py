"""Validate with a local copy of the documented published JSON Schema. No network."""
import json
from pathlib import Path
import sys

import jsonschema

root = Path(__file__).resolve().parents[1]
schema = json.loads(Path(sys.argv[1]).read_text())
jsonschema.validators.validator_for(schema).check_schema(schema)
jsonschema.validate(json.loads((root / '.claude/settings.json').read_text()), schema)
print('Settings validate against supplied published JSON Schema.')

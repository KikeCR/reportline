"""CI regenerates openapi.json and fails if it differs from the committed
file - this is the same check, runnable locally via ``make test``. See
docs/adr/0002-api-contract.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from app import create_app

OPENAPI_JSON_PATH = Path(__file__).parent.parent.parent / "openapi.json"


def test_openapi_json_matches_the_generated_spec():
    app = create_app()
    regenerated = json.dumps(app.api_doc, indent=2, sort_keys=True) + "\n"

    committed = OPENAPI_JSON_PATH.read_text()

    assert regenerated == committed, (
        "api/openapi.json is out of date - run `make openapi` and commit the result"
    )

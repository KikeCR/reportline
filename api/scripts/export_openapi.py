"""Writes api/openapi.json deterministically (sorted keys, stable
indentation) so it can be diffed in CI - see docs/adr/0002-api-contract.md.

CLAUDE.md: "Generated files are never hand-edited" and "Changing an API
model requires regenerating OpenAPI and TS types in the same PR." This
script, run via ``make openapi``, is the only thing that writes
``api/openapi.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

from app import create_app

OUTPUT_PATH = Path(__file__).parent.parent / "openapi.json"


def export(output_path: Path = OUTPUT_PATH) -> None:
    app = create_app()
    spec = app.api_doc
    output_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")


def main() -> int:
    export()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

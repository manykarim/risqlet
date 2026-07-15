"""Generate the published JSON Schema files from the pydantic models.

Run via ``python -m risqlet.model.schema_gen``. The output is deterministic
(sorted keys, fixed indent) and committed under ``src/risqlet/schemas/`` so
non-Python consumers can validate register files without this package.
"""

from __future__ import annotations

import json
from pathlib import Path

from risqlet.catalog.models import CatalogPack
from risqlet.model.models import PUBLISHED_SCHEMAS

EXTRA_SCHEMAS = {"catalog": CatalogPack}

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


def generate() -> dict[str, str]:
    """Render each published schema; returns {filename: json_text}."""
    out: dict[str, str] = {}
    for name, model in sorted({**PUBLISHED_SCHEMAS, **EXTRA_SCHEMAS}.items()):
        schema = model.model_json_schema()
        schema["$id"] = f"https://risqlet.dev/schemas/v1/{name}.schema.json"
        out[f"{name}.schema.json"] = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    return out


def write(directory: Path = SCHEMAS_DIR) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, text in generate().items():
        path = directory / filename
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


if __name__ == "__main__":
    for p in write():
        print(p)

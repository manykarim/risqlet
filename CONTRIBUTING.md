# Contributing to risqlet

Thanks for your interest. risqlet is an agent-facing risk-analysis and
test-strategy toolkit; contributions of code, catalog entries, guardrail
templates, and docs are welcome.

## Development setup

```bash
uv sync                 # install deps (Python 3.12+)
uv run pytest           # run the test suite
uv run ruff check .     # lint (must be clean)
uv run risqlet --help   # try the CLI
```

Regenerate the committed JSON Schemas after changing any model:

```bash
uv run python -m risqlet.model.schema_gen
```

## Pull request checklist

- [ ] `uv run ruff check .` is clean and `uv run pytest` passes.
- [ ] New behavior has tests; determinism-sensitive code (scoring, dedupe,
      exports, diff) has a "runs twice → identical" test.
- [ ] Public CLI/format changes update the README and, if a capability
      changes, the relevant `openspec/specs/` and a change under
      `openspec/changes/`.
- [ ] JSON Schemas regenerated if models changed.

## Clean-room affirmation (required for catalog and NOTICE-bearing content)

Catalog packs (`src/risqlet/catalog/packs/`) and any content that references a
third-party taxonomy are authored under the clean-room protocol in
`CLEAN-ROOM.md`: established concept names and originator citations may be used
as facts, but **no source card, standard, or licensed document text may be
consulted or reproduced while writing entry text**, and every entry carries a
provenance line.

Any PR that adds or edits catalog/guardrail/NOTICE content must state in its
description:

> Entry text authored without consulting licensed source text (CLEAN-ROOM.md).

## Licensing of contributions

By contributing you agree that your code contributions are licensed under
Apache-2.0 and your catalog-content contributions under CC BY 4.0, matching the
project's dual license.

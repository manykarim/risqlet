"""Filesystem store for the .risqlet/ register.

The register is plain files co-edited by humans and agents; every write here
round-trips through ruamel.yaml so comments and key order survive CLI touches.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from risqlet.model import RISK_ID_PATTERN, Event  # noqa: F401  (pattern re-exported for callers)

RISQLET_DIR = ".risqlet"
REGISTER_DIR = "register"
CONFIG_FILE = "config.yaml"
EVENTS_FILE = "events.jsonl"
POLICIES_DIR = "policies"

_STARTER_CONFIG = """\
# risqlet register configuration — see schemas/config.schema.json
schema_version: 1
project: {project}
# catalog packs powering soft reference checks (unknown aspect/technique slugs
# warn) and elicitation/mitigation lookups; remove entries to disable
catalogs: [iso25010, techniques, heuristics, guidewords]
# active scoring policy pack: sod-ap-v1 (Severity x Occurrence x Detection with
# Action-Priority lookup) or li-v1 (3x3 likelihood x impact), or a pack id from
# .risqlet/policies/
scoring_policy: sod-ap-v1
# workflow phase: context | aspects | elicit | score | mitigate | emit
# phase changes require a human-principal event in events.jsonl
phase: context
constraints:
  max_aspects: 6      # forced prioritization — resist the urge to raise this
  max_top_risks: 10
# selected quality aspects (phase >= aspects), each: {{id, rank, rationale}}
aspects: []
"""


class StoreError(Exception):
    """Raised for store-level failures (missing register, refusal to overwrite)."""


def _yaml() -> YAML:
    y = YAML(typ="rt")
    y.preserve_quotes = True
    y.width = 100
    return y


def find_register(start: Path | None = None, explicit: Path | None = None) -> Path:
    """Locate the .risqlet directory: explicit --dir wins, else walk up from cwd."""
    if explicit is not None:
        root = explicit.expanduser().resolve()
        candidate = root if root.name == RISQLET_DIR else root / RISQLET_DIR
        if not candidate.is_dir():
            raise StoreError(f"no {RISQLET_DIR}/ register at {root}")
        return candidate
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / RISQLET_DIR
        if candidate.is_dir():
            return candidate
    raise StoreError(
        f"no {RISQLET_DIR}/ register found from {current} upwards — run `risqlet init`"
    )


def init_register(project_dir: Path, project_name: str | None = None) -> Path:
    """Scaffold .risqlet/ in project_dir. Refuses to overwrite a non-empty register."""
    risqlet = project_dir.resolve() / RISQLET_DIR
    register = risqlet / REGISTER_DIR
    if risqlet.exists() and (
        (register.exists() and any(register.iterdir()))
        or (risqlet / CONFIG_FILE).exists()
        or (risqlet / EVENTS_FILE).exists()
    ):
        raise StoreError(f"{risqlet} already contains a register — refusing to overwrite")
    register.mkdir(parents=True, exist_ok=True)
    name = project_name or project_dir.resolve().name
    (risqlet / CONFIG_FILE).write_text(_STARTER_CONFIG.format(project=name))
    (risqlet / EVENTS_FILE).touch()
    return risqlet


@dataclass
class RiskFile:
    """A register file paired with its round-trip-preserving parsed data."""

    path: Path
    data: dict  # ruamel CommentedMap; mutate in place, then Store.save_risk()


class Store:
    def __init__(self, risqlet_dir: Path):
        self.root = risqlet_dir
        self._yaml = _yaml()

    # -- config ------------------------------------------------------------
    @property
    def config_path(self) -> Path:
        return self.root / CONFIG_FILE

    def load_config_raw(self) -> dict:
        with self.config_path.open() as f:
            return self._yaml.load(f) or {}

    def save_config_raw(self, data: dict) -> None:
        buf = io.StringIO()
        self._yaml.dump(data, buf)
        self.config_path.write_text(buf.getvalue())

    # -- risks ---------------------------------------------------------------
    @property
    def register_dir(self) -> Path:
        return self.root / REGISTER_DIR

    def risk_paths(self) -> list[Path]:
        if not self.register_dir.is_dir():
            return []
        return sorted(self.register_dir.glob("*.yaml"))

    def load_risk_files(self) -> list[RiskFile]:
        out = []
        for path in self.risk_paths():
            with path.open() as f:
                data = self._yaml.load(f)
            out.append(RiskFile(path=path, data=data or {}))
        return out

    def save_risk(self, risk_file: RiskFile) -> None:
        buf = io.StringIO()
        self._yaml.dump(risk_file.data, buf)
        risk_file.path.write_text(buf.getvalue())

    def next_risk_id(self) -> str:
        return f"R-{self._next_number('R'):04d}"

    def next_mitigation_id(self) -> str:
        return f"M-{self._next_number('M'):04d}"

    def _next_number(self, prefix: str) -> int:
        highest = 0
        for rf in self.load_risk_files():
            ids = [rf.data.get("id", "")] if prefix == "R" else [
                m.get("id", "") for m in rf.data.get("mitigations", []) or []
            ]
            for candidate in ids:
                if isinstance(candidate, str) and candidate.startswith(f"{prefix}-"):
                    try:
                        highest = max(highest, int(candidate.split("-", 1)[1]))
                    except ValueError:
                        pass
        return highest + 1

    # -- events --------------------------------------------------------------
    @property
    def events_path(self) -> Path:
        return self.root / EVENTS_FILE

    def append_event(self, event: Event) -> None:
        line = json.dumps(event.model_dump(by_alias=True, exclude_none=True), sort_keys=True)
        with self.events_path.open("a") as f:
            f.write(line + "\n")

    def read_events(self) -> list[tuple[int, dict]]:
        """Return (line_number, raw_dict) pairs; malformed lines raise with context."""
        if not self.events_path.exists():
            return []
        out = []
        for lineno, line in enumerate(self.events_path.read_text().splitlines(), start=1):
            if not line.strip():
                continue
            try:
                out.append((lineno, json.loads(line)))
            except json.JSONDecodeError as exc:
                raise StoreError(f"{self.events_path}:{lineno}: malformed event line") from exc
        return out

    # -- policies -----------------------------------------------------------
    @property
    def user_policies_dir(self) -> Path:
        return self.root / POLICIES_DIR

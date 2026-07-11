"""Pydantic models for the .risqlet/ register file formats.

Open-world stance: unknown extra fields are preserved (``extra="allow"``) and
surfaced as validation *warnings* by the validate pipeline, never errors, so
later layers (catalogs, skills, MCP adapter) can annotate documents without
breaking older CLIs. See design.md D2/Risks.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

RISK_ID_PATTERN = r"^R-\d{4}$"
MITIGATION_ID_PATTERN = r"^M-\d{4}$"
# namespaced catalog.slug, e.g. "iso25010.security"; free-form but format-checked in v1
ASPECT_ID_PATTERN = r"^[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9._-]*$"
PRINCIPAL_PATTERN = r"^(human|agent):.+$"

SCHEMA_VERSION = 1


class Method(StrEnum):
    RISKSTORMING = "riskstorming"
    HAZOP = "hazop"
    STRIDE = "stride"
    PREMORTEM = "premortem"
    FMEA = "fmea"
    INSIDE_OUT = "inside-out"
    MANUAL = "manual"


class Status(StrEnum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    MITIGATING = "mitigating"
    CLOSED = "closed"
    REJECTED = "rejected"


class Treatment(StrEnum):
    AVOID = "avoid"
    REDUCE = "reduce"
    TRANSFER = "transfer"
    ACCEPT = "accept"


class Lever(StrEnum):
    SEVERITY = "severity"
    OCCURRENCE = "occurrence"
    DETECTION = "detection"


class Barrier(StrEnum):
    PREVENT = "prevent"
    DETECT = "detect"
    RECOVER = "recover"


class Phase(StrEnum):
    CONTEXT = "context"
    ASPECTS = "aspects"
    ELICIT = "elicit"
    SCORE = "score"
    MITIGATE = "mitigate"
    EMIT = "emit"


class EventType(StrEnum):
    STATUS_CHANGE = "status_change"
    PHASE_CHANGE = "phase_change"


class _OpenModel(BaseModel):
    model_config = ConfigDict(extra="allow", use_enum_values=True)

    def extra_fields(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


class ElicitedBy(_OpenModel):
    method: Method
    prompt_ref: str = ""
    evidence: list[str] = Field(default_factory=list)


class ScoreSet(_OpenModel):
    policy: str = Field(min_length=1)
    values: dict[str, int]
    rubric_anchors: list[str] = Field(default_factory=list)
    scored_by: list[str] = Field(default_factory=list)
    derived: dict[str, Any] = Field(default_factory=dict)


class Mitigation(_OpenModel):
    id: str = Field(pattern=MITIGATION_ID_PATTERN)
    risk_ids: list[str] = Field(min_length=1)
    treatment: Treatment
    lever: Lever
    barrier: Barrier
    technique_ref: str = ""
    concrete: str = Field(min_length=1)
    residual_note: str = Field(min_length=1)
    tests: list[str] = Field(default_factory=list)


class Risk(_OpenModel):
    schema_version: int = SCHEMA_VERSION
    id: str = Field(pattern=RISK_ID_PATTERN)
    statement: str = Field(min_length=1)
    aspects: list[str] = Field(default_factory=list)
    elicited_by: ElicitedBy
    scores: list[ScoreSet] = Field(default_factory=list)
    status: Status = Status.PROPOSED
    mitigations: list[Mitigation] = Field(default_factory=list)
    # engine-owned: ensemble scoring spread, written by `risqlet score` (>=2 sets)
    disagreement: dict[str, Any] | None = None
    # provenance of risks merged into this one via `risqlet merge`
    merged_from: list[dict[str, Any]] = Field(default_factory=list)


class SelectedAspect(_OpenModel):
    id: str = Field(pattern=ASPECT_ID_PATTERN)
    rank: int = Field(ge=1)
    rationale: str = Field(min_length=1)


class Constraints(_OpenModel):
    max_aspects: int = Field(default=6, ge=1)
    max_top_risks: int = Field(default=10, ge=1)


class Config(_OpenModel):
    schema_version: int = SCHEMA_VERSION
    project: str = Field(min_length=1)
    catalogs: list[str] = Field(default_factory=list)
    scoring_policy: str = "sod-ap-v1"
    phase: Phase = Phase.CONTEXT
    constraints: Constraints = Field(default_factory=Constraints)
    aspects: list[SelectedAspect] = Field(default_factory=list)


class Event(_OpenModel):
    ts: str = Field(min_length=1)  # ISO 8601; kept as string to stay round-trip-exact
    type: EventType
    risk: str | None = None
    from_: str = Field(alias="from")
    to: str
    principal: str = Field(pattern=PRINCIPAL_PATTERN)
    note: str = ""

    model_config = ConfigDict(extra="allow", use_enum_values=True, populate_by_name=True)


#: Models whose JSON Schemas are published for non-Python consumers.
PUBLISHED_SCHEMAS: dict[str, type[BaseModel]] = {
    "risk": Risk,
    "config": Config,
    "event": Event,
}

"""Guardrail template descriptors and rendered guardrails.

Templates are vetted, fixed-body snippets. Only declared ``params`` are ever
interpolated from the register — a guardrail body is never free-form model
output, because a generated hook runs arbitrary commands.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Surface(StrEnum):
    AGENTS_MD = "agents-md"
    CLAUDE_HOOK = "claude-hook"
    CLAUDE_PERMISSION = "claude-permission"
    PRE_COMMIT = "pre-commit"
    CI = "ci"


class Enforcement(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class Selectors(BaseModel):
    model_config = ConfigDict(extra="allow")
    aspects: list[str] = Field(default_factory=list)
    catalog_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    match_any: bool = False


class GuardrailTemplate(BaseModel):
    model_config = ConfigDict(extra="allow", use_enum_values=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    surface: Surface
    enforcement: Enforcement
    barriers: list[str] = Field(min_length=1)  # prevent|detect|recover
    selectors: Selectors = Field(default_factory=Selectors)
    params: list[str] = Field(default_factory=list)
    body: str = Field(min_length=1)
    # executable truth for hook/pre-commit surfaces (verifiable, agent-independent)
    command: str = ""
    verify: VerifySpec | None = None


class VerifySpec(BaseModel):
    model_config = ConfigDict(extra="allow")
    tools: list[str] = Field(default_factory=list)   # must resolve on PATH
    blocking: bool = False                           # exits nonzero on a violation
    input: str = "none"                              # file | none | git-staged
    benign: str = ""                                 # fixture that MUST pass (exit 0)
    violation: str = ""                              # fixture that MUST be caught


class RenderedGuardrail(BaseModel):
    """A template rendered for one or more risks; deduped by (template, params)."""

    template_id: str
    surface: str
    enforcement: str
    params: dict[str, list[str]] = Field(default_factory=dict)
    content: str
    markers: list[str] = Field(default_factory=list)  # risqlet:<risk>:<barrier>:<template>
    risks: list[str] = Field(default_factory=list)
    command: str = ""                                 # rendered executable command
    verify: VerifySpec | None = None

    def dedupe_key(self) -> tuple:
        param_items = tuple(sorted((k, tuple(v)) for k, v in self.params.items()))
        return (self.template_id, self.surface, param_items)

"""Agent adapter descriptors and the setup manifest.

Adapters are data (one YAML per agent): a schema change for any agent is a data
edit, not code. Setup installs the intersection of requested components and each
adapter's declared capability, and records every write in a manifest so removal
is exact.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Component(StrEnum):
    SKILLS = "skills"
    MCP = "mcp"
    INSTRUCTIONS = "instructions"
    HOOKS = "hooks"
    COMMANDS = "commands"


class Scope(StrEnum):
    PROJECT = "project"
    GLOBAL = "global"


ALL_COMPONENTS = [c.value for c in Component]


class ComponentSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")
    scopes: list[str] = Field(default_factory=list)  # project|global
    project: str = ""   # path template, project scope
    global_: str = Field(default="", alias="global")  # path template, global scope
    # copy-skills | json-merge | jsonc-merge | toml-merge | md-section | json-hooks | copy-commands
    method: str = ""
    key: str = ""       # top-level merge key (mcpServers|servers|mcp|mcp_servers)
    note: str = ""      # honest capability note shown to the user

    def path_for(self, scope: str) -> str:
        return self.project if scope == Scope.PROJECT else self.global_

    def supports(self, scope: str) -> bool:
        return scope in self.scopes and bool(self.path_for(scope))


class Detect(BaseModel):
    model_config = ConfigDict(extra="allow")
    binary: str = ""
    dirs: list[str] = Field(default_factory=list)


class AgentAdapter(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    detect: Detect = Field(default_factory=Detect)
    components: dict[str, ComponentSpec] = Field(default_factory=dict)

    def supported_components(self, scope: str) -> list[str]:
        return [c for c, spec in self.components.items() if spec.supports(scope)]


class PlannedAction(BaseModel):
    agent: str
    component: str
    scope: str
    target: str          # resolved path (absolute)
    method: str
    key: str = ""
    marker: str = ""     # for md-section / merge-key removal
    creates_file: bool = False


class SkippedItem(BaseModel):
    agent: str
    component: str
    reason: str


class Plan(BaseModel):
    scope: str
    actions: list[PlannedAction] = Field(default_factory=list)
    skipped: list[SkippedItem] = Field(default_factory=list)

    def by_agent(self) -> dict[str, list[PlannedAction]]:
        out: dict[str, list[PlannedAction]] = {}
        for a in self.actions:
            out.setdefault(a.agent, []).append(a)
        return out


class ManifestEntry(BaseModel):
    agent: str
    component: str
    scope: str
    target: str
    method: str
    key: str = ""
    marker: str = ""
    created_file: bool = False


class Manifest(BaseModel):
    risqlet_version: str = ""
    entries: list[ManifestEntry] = Field(default_factory=list)

"""Pydantic models for catalog packs (knowledge layer as data)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]*$"
ENTRY_ID_PATTERN = r"^[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9-]*$"


class EntryKind(StrEnum):
    ASPECT = "aspect"
    TECHNIQUE = "technique"
    HEURISTIC = "heuristic"
    GUIDEWORD_SET = "guideword-set"


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="allow", use_enum_values=True)

    slug: str = Field(pattern=SLUG_PATTERN)
    name: str = Field(min_length=1)
    kind: EntryKind
    summary: str = Field(min_length=1)
    prompts: list[str] = Field(min_length=1, max_length=3)
    tags: list[str] = Field(default_factory=list)
    provenance: str = Field(min_length=1)
    related: list[str] = Field(default_factory=list)
    words: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _guideword_sets_need_words(self):
        if self.kind == EntryKind.GUIDEWORD_SET and not self.words:
            raise ValueError(f"entry {self.slug!r}: guideword-set requires a non-empty words list")
        return self


class CatalogPack(BaseModel):
    model_config = ConfigDict(extra="allow", use_enum_values=True)

    id: str = Field(pattern=SLUG_PATTERN)
    title: str = Field(min_length=1)
    version: int = 1
    license: str = Field(min_length=1)
    attribution: str = Field(min_length=1)
    # optional required-reproduction notice (e.g. a rights-holder permission statement)
    notice: str = ""
    entries: list[CatalogEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_slugs(self):
        seen: set[str] = set()
        for entry in self.entries:
            if entry.slug in seen:
                raise ValueError(f"pack {self.id!r}: duplicate slug {entry.slug!r}")
            seen.add(entry.slug)
        return self

    def entry_ids(self) -> list[str]:
        return [f"{self.id}.{e.slug}" for e in self.entries]

    def get(self, slug: str) -> CatalogEntry | None:
        for entry in self.entries:
            if entry.slug == slug:
                return entry
        return None

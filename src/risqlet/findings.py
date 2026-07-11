"""Shared finding type for validation results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Finding:
    severity: Severity
    file: str
    field: str
    message: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = str(self.severity)
        return d


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity == Severity.ERROR for f in findings)

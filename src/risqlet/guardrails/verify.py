"""Verify guardrail hooks in the environment they are added to.

A hook that has not been proven to work is a liability, not a safeguard. We run
static checks (required tools on PATH, `bash -n` syntax) and behavioral checks
(benign fixture must pass; a blocking hook must catch a violation) for the *vetted
rendered command only*, in a temp working directory, with a timeout that kills a
hanging command's process group.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from risqlet.guardrails.models import RenderedGuardrail, VerifySpec

TIMEOUT_S = 10
HOOK_FILE_ENV = "RISQLET_HOOK_FILE"


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class VerifyResult:
    template_id: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)

    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        return {"template_id": self.template_id, "ok": self.ok,
                "checks": [vars(c) for c in self.checks]}


def _run(command: str, cwd: Path, env_file: Path | None) -> tuple[int, str]:
    env = dict(os.environ)
    if env_file is not None:
        env[HOOK_FILE_ENV] = str(env_file)
    try:
        proc = subprocess.Popen(
            ["bash", "-c", command], cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=TIMEOUT_S)
            return proc.returncode, out
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
            return 124, "timed out"
    except OSError as exc:
        return 127, str(exc)


def _fixture_path(scratch: Path, guardrail: RenderedGuardrail, spec: VerifySpec) -> Path:
    name = getattr(spec, "fixture", "") or "probe.txt"
    dirs = guardrail.params.get("paths") or ["."]
    d = dirs[0]
    base = scratch if d == "." else scratch / d
    base.mkdir(parents=True, exist_ok=True)
    return base / name


def verify_guardrail(guardrail: RenderedGuardrail, cwd: Path) -> VerifyResult:
    result = VerifyResult(template_id=guardrail.template_id)
    spec = guardrail.verify
    if spec is None:  # advisory guardrail — nothing executable to verify
        result.checks.append(Check("no-op", True, "advisory guardrail, not executed"))
        return result

    # preflight: tools on PATH
    for tool in spec.tools:
        result.checks.append(Check(
            f"tool:{tool}", shutil.which(tool) is not None,
            "" if shutil.which(tool) else f"{tool} not on PATH"))

    # git-staged hooks (pre-commit) verify by tool presence only in v1
    if spec.input == "git-staged" or not guardrail.command:
        return result

    # preflight: syntax
    rc, out = _run(f"set -e; : ; true; {{ :; }}; bash -n <<'RISQLET_EOF'\n"
                   f"{guardrail.command}\nRISQLET_EOF", cwd, None)
    result.checks.append(Check("syntax", rc == 0, "" if rc == 0 else out.strip()[:200]))
    if rc != 0:
        return result

    with tempfile.TemporaryDirectory(dir=cwd) as tmp:
        scratch = Path(tmp)
        if spec.input == "file":
            fx = _fixture_path(scratch, guardrail, spec)
            fx.write_text(spec.benign)
            rc, out = _run(guardrail.command, scratch, fx)
            result.checks.append(Check(
                "benign-passes", rc == 0,
                "" if rc == 0 else f"benign fixture blocked (exit {rc}): {out.strip()[:120]}"))
            if spec.blocking:
                fx.write_text(spec.violation)
                rc, out = _run(guardrail.command, scratch, fx)
                result.checks.append(Check(
                    "violation-caught", rc != 0 and rc != 124,
                    "" if (rc != 0 and rc != 124)
                    else f"violation not caught (exit {rc})"))
        else:  # input: none (e.g. Stop hook) — just prove it runs and exits 0
            rc, out = _run(guardrail.command, scratch, None)
            result.checks.append(Check(
                "runs", rc == 0,
                "" if rc == 0 else f"exited {rc}: {out.strip()[:120]}"))
    return result

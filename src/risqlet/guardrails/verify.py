"""Verify guardrail hooks in the environment they are added to.

A hook that has not been proven to work is a liability, not a safeguard. We run
static checks (required tools on PATH, and — for shell commands — a `bash -n`
syntax check) and behavioral checks (benign fixture must pass; a blocking hook must
catch a violation) for the *vetted rendered command only*, in a temp working
directory, with a timeout that kills a hanging command's process group.

The static check follows the command's form: a shell command needs a shell (and is
syntax-checked with one), while a shell-free command — a single executable with
literal arguments — is run directly and must not be failed for a shell it never
uses. Note this module's process handling is POSIX-only; guardrail hooks are not
supported on Windows.
"""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from risqlet.guardrails.models import RenderedGuardrail, VerifySpec

TIMEOUT_S = 10
HOOK_FILE_ENV = "RISQLET_HOOK_FILE"

UNSUPPORTED_ON_WINDOWS = (
    "guardrail shell hooks are not supported on Windows: the templates are POSIX "
    "shell and this verifier uses POSIX process handling. Use risqlet setup's check "
    "hook, which is shell-free and runs everywhere."
)

# Characters that only mean something to a shell. A command containing none of
# them is a plain argv line and can be executed without one.
_SHELL_METACHARS = set("$`\"'|;&><(){}[]*?~!#\n\\")


def _is_windows() -> bool:
    """Indirection so tests can simulate Windows.

    Patching `os.name` directly is not an option: `os` is a shared module, and
    pathlib reads `os.name` to choose PosixPath vs WindowsPath — so faking it
    globally breaks every path in the process.
    """
    return os.name == "nt"


def is_shell_free(command: str) -> bool:
    """True if the command is a single executable with literal arguments.

    Requires the leading token to resolve on PATH: without a shell there is
    nothing to interpret a builtin like `exit`, so a bare builtin is a shell
    command however few metacharacters it has.
    """
    if not command or not command.strip():
        return False
    if any(c in _SHELL_METACHARS for c in command):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    return bool(tokens) and shutil.which(tokens[0]) is not None


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
    argv = shlex.split(command) if is_shell_free(command) else ["bash", "-c", command]
    try:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=TIMEOUT_S)
            return proc.returncode, out
        except subprocess.TimeoutExpired:
            _kill(proc)
            proc.wait()
            return 124, "timed out"
    except OSError as exc:
        return 127, str(exc)


def _kill(proc: subprocess.Popen) -> None:
    """Kill a hung hook and the children it spawned.

    Killing the process group matters: a shell hook's `grep` outlives a kill aimed
    only at the shell. os.killpg/os.getpgid do not exist on Windows, so fall back to
    killing the process alone rather than dying in an AttributeError — guardrails are
    POSIX-only (see module docstring), and an unsupported platform should say so, not
    crash.
    """
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (AttributeError, OSError):
        proc.kill()


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

    # a shell command needs a shell; a shell-free one must not be failed for
    # lacking one, so bash is required only when the command actually uses it
    shell_free = is_shell_free(guardrail.command)

    # A shell hook is unsupported on Windows by policy, not by whether a shell
    # happens to be present: Windows runners ship Git Bash, so the template might
    # limp along and then behave differently from POSIX. Refuse with a reason and
    # let the install gate skip it, rather than install something unproven.
    if guardrail.command and not shell_free and _is_windows():
        result.checks.append(Check("platform", False, UNSUPPORTED_ON_WINDOWS))
        return result

    tools = list(spec.tools)
    if guardrail.command and not shell_free and "bash" not in tools:
        tools.append("bash")

    # preflight: tools on PATH
    for tool in tools:
        result.checks.append(Check(
            f"tool:{tool}", shutil.which(tool) is not None,
            "" if shutil.which(tool) else f"{tool} not on PATH"))

    # git-staged hooks (pre-commit) verify by tool presence only in v1
    if spec.input == "git-staged" or not guardrail.command:
        return result

    # preflight: syntax — only meaningful for a shell command. A shell-free
    # command has no shell syntax; executing it below proves more than bash -n.
    if not shell_free:
        if shutil.which("bash") is None:
            return result  # already reported as a missing tool
        rc, out = _run(f"set -e; : ; true; {{ :; }}; bash -n <<'RISQLET_EOF'\n"
                       f"{guardrail.command}\nRISQLET_EOF", cwd, None)
        result.checks.append(Check("syntax", rc == 0,
                                   "" if rc == 0 else out.strip()[:200]))
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

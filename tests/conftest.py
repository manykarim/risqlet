"""Shared fixtures: a populated register used across validate/score/export/CLI tests."""

import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from risqlet.store import Store, init_register

SRC = str(Path(__file__).resolve().parent.parent / "src")

POSIX_ONLY_REASON = (
    "risqlet guardrails is POSIX-only: its hook templates are shell one-liners and "
    "its verifier uses POSIX process handling. This is a stated support boundary, "
    "not an accident of the runner image — Windows runners do ship Git Bash."
)


def pytest_collection_modifyitems(config, items):
    """Skip POSIX-only tests on Windows, visibly and with a reason.

    A skip shows up in the run; a test omitted from a hand-picked per-OS selection
    does not, and absence reads as green. Platform gaps belong here, where they are
    stated, rather than in the workflow's test selection.
    """
    if os.name != "nt":
        return
    skip = pytest.mark.skip(reason=POSIX_ONLY_REASON)
    for item in items:
        if "posix_only" in item.keywords:
            item.add_marker(skip)


def _path_risqlet_runs_hook() -> bool:
    """Does the `risqlet` on PATH understand the hook command we install?"""
    try:
        proc = subprocess.run(["risqlet", "check", "--hook-input", "claude", "--json"],
                              input="{}", capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


@pytest.fixture
def risqlet_on_path(tmp_path_factory, monkeypatch):
    """Guarantee the `risqlet` on PATH is this working tree's.

    Hook verification runs the real `risqlet` executable, so an editable install
    (`uv sync` / `uv run pytest`) already satisfies this. Bare `python -m pytest`
    may instead resolve a stale global install (e.g. `uv tool install risqlet`),
    which would let whatever is installed decide the result rather than the code
    under test — so shim the working tree in front of it.
    """
    if _path_risqlet_runs_hook():
        return  # editable install already on PATH — nothing to do
    if os.name == "nt":  # subprocess cannot exec a .bat shim via CreateProcess
        pytest.skip("no working risqlet on PATH — install the package first (uv sync)")
    shim_dir = tmp_path_factory.mktemp("shim")
    launcher = shim_dir / "risqlet"
    launcher.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import sys
        sys.path.insert(0, {SRC!r})
        from risqlet.cli import main
        sys.exit(main())
        """))
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    monkeypatch.setenv("PATH", str(shim_dir) + os.pathsep + os.environ["PATH"])
    # fail loudly here rather than as a confusing verification skip downstream
    assert _path_risqlet_runs_hook(), "risqlet shim is broken"

RISK_1 = """\
schema_version: 1
id: R-0001
statement: Because the payment terminal acknowledges asynchronously, late confirmations
  may be recorded as failed while the cardholder was charged, causing double-charge complaints
aspects: [iso25010.reliability]
elicited_by:
  method: hazop
  prompt_ref: "guideword:LATE"
  evidence: ["docs/payment-flow.md"]
scores:
  - policy: sod-ap-v1
    values: {severity: 7, occurrence: 5, detection: 8}
    rubric_anchors: ["sev7: revenue + reputation", "occ5: weekly at peak",
      "det8: no reconciliation check"]
    scored_by: ["agent:ops-persona"]
status: proposed
mitigations:
  - id: M-0001
    risk_ids: [R-0001]
    treatment: reduce
    lever: detection
    barrier: detect
    technique_ref: ""
    concrete: nightly reconciliation of PSP settlement file against transaction journal
    residual_note: chargebacks initiated at the issuer remain undetected until settlement +2d
    tests: ["rf:suites/reconciliation.robot::Nightly Settlement Match"]
"""

RISK_2 = """\
schema_version: 1
id: R-0002
statement: Because session tokens are logged at debug level, an attacker with log access
  may replay sessions, causing account takeover
aspects: [iso25010.security]
elicited_by:
  method: stride
  prompt_ref: "stride:information-disclosure"
  evidence: []
scores:
  - policy: sod-ap-v1
    values: {severity: 9, occurrence: 3, detection: 6}
    rubric_anchors: ["sev9: account takeover", "occ3: requires log access", "det6: no log scanning"]
status: proposed
mitigations: []
"""


@pytest.fixture
def populated_register(tmp_path):
    risqlet = init_register(tmp_path, "demo")
    store = Store(risqlet)
    (store.register_dir / "R-0001.yaml").write_text(RISK_1)
    (store.register_dir / "R-0002.yaml").write_text(RISK_2)
    return store


def append_raw_event(store: Store, **kw):
    """Append an event dict without model validation (for negative tests)."""
    with store.events_path.open("a") as f:
        f.write(json.dumps(kw) + "\n")

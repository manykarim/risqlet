"""Shared fixtures: a populated register used across validate/score/export/CLI tests."""

import json

import pytest

from risqlet.store import Store, init_register

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

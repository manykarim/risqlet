"""Unit tests for the lifecycle state machine and human-principal gates."""

from risqlet.findings import Severity, has_errors
from risqlet.lifecycle import (
    check_events,
    check_phase_consistency,
    check_risk_consistency,
    replay_status,
)


def ev(lineno, **kw):
    base = {
        "ts": "2026-07-10T12:00:00Z",
        "type": "status_change",
        "risk": "R-0001",
        "principal": "human:many",
    }
    base.update(kw)
    return (lineno, base)


class TestCheckEvents:
    def test_legal_chain_clean(self):
        events = [
            ev(1, **{"from": "proposed", "to": "reviewed"}),
            ev(2, **{"from": "reviewed", "to": "accepted"}),
        ]
        assert check_events(events) == []

    def test_agent_principal_rejected(self):
        events = [ev(1, principal="agent:security-persona",
                     **{"from": "proposed", "to": "reviewed"})]
        findings = check_events(events)
        assert has_errors(findings)
        assert "human principal" in findings[0].message

    def test_illegal_transition_rejected(self):
        events = [ev(1, **{"from": "proposed", "to": "closed"})]
        findings = check_events(events)
        assert any("illegal status transition" in f.message for f in findings)

    def test_rejected_branch_legal(self):
        assert check_events([ev(1, **{"from": "reviewed", "to": "rejected"})]) == []

    def test_terminal_states_frozen(self):
        findings = check_events([ev(1, **{"from": "closed", "to": "proposed"})])
        assert has_errors(findings)

    def test_phase_event_checked(self):
        events = [
            (1, {"ts": "t", "type": "phase_change", "from": "context",
                 "to": "warp", "principal": "human:many"})
        ]
        findings = check_events(events)
        assert any(f.field == "to" for f in findings)


class TestReplayConsistency:
    def test_replay_matches_file(self):
        events = [
            ev(1, **{"from": "proposed", "to": "reviewed"}),
            ev(2, **{"from": "reviewed", "to": "accepted"}),
        ]
        assert replay_status("R-0001", events) == "accepted"
        assert check_risk_consistency("R-0001", "accepted", "R-0001.yaml", events) == []

    def test_skipped_state_detected(self):
        # file says accepted but no proposed->reviewed event exists
        findings = check_risk_consistency("R-0001", "accepted", "R-0001.yaml", [])
        assert has_errors(findings)
        assert "does not match event replay" in findings[0].message

    def test_mismatched_from_detected(self):
        events = [ev(1, **{"from": "reviewed", "to": "accepted"})]  # never left proposed
        findings = check_risk_consistency("R-0001", "accepted", "R-0001.yaml", events)
        assert any("replayed status is 'proposed'" in f.message for f in findings)

    def test_events_for_other_risks_ignored(self):
        events = [ev(1, risk="R-0002", **{"from": "proposed", "to": "reviewed"})]
        assert replay_status("R-0001", events) == "proposed"


class TestPhaseGate:
    def test_phase_advance_needs_event(self):
        findings = check_phase_consistency("elicit", [])
        assert has_errors(findings)
        assert "phase changes require" in findings[0].message

    def test_phase_chain_replays(self):
        events = [
            (1, {"ts": "t", "type": "phase_change", "from": "context",
                 "to": "aspects", "principal": "human:many"}),
            (2, {"ts": "t", "type": "phase_change", "from": "aspects",
                 "to": "elicit", "principal": "human:many"}),
        ]
        assert check_phase_consistency("elicit", events) == []

    def test_backward_phase_move_allowed(self):
        events = [
            (1, {"ts": "t", "type": "phase_change", "from": "context",
                 "to": "elicit", "principal": "human:many"}),
            (2, {"ts": "t", "type": "phase_change", "from": "elicit",
                 "to": "aspects", "principal": "human:many"}),
        ]
        assert check_phase_consistency("aspects", events) == []

    def test_context_phase_needs_no_events(self):
        assert check_phase_consistency("context", []) == []


class TestSeverityModel:
    def test_findings_serialize(self):
        findings = check_phase_consistency("elicit", [])
        d = findings[0].to_dict()
        assert d["severity"] == str(Severity.ERROR) == "error"
        assert set(d) == {"severity", "file", "field", "message"}

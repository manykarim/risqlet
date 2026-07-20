"""Tests for risqlet diff, check gate, and ci init."""

import io
import json
import shlex

import pytest

from risqlet.changeset import build_diff, parse_claude_hook_payload, run_check
from risqlet.ci import CIError, init, template_text
from risqlet.cli import build_parser, main
from risqlet.store import Store, init_register
from risqlet.validate import validate_register
from tests.conftest import read_utf8

RISK = """\
schema_version: 1
id: {id}
statement: {statement}
aspects: [{aspect}]
elicited_by: {{method: inside-out, evidence: [{evidence}]}}
scores: {scores}
status: {status}
mitigations: {mitigations}
"""


def write_risk(store, id, statement="Because the order flow reverts without "
               "compensation, divergence may occur, causing split projections",
               aspect="iso25010.reliability", evidence='"src/orders/saga.py"',
               scores="[]", status="proposed", mitigations="[]"):
    (store.register_dir / f"{id}.yaml").write_text(RISK.format(
        id=id, statement=statement, aspect=aspect, evidence=evidence,
        scores=scores, status=status, mitigations=mitigations), encoding="utf-8")


SCORED = """
  - policy: sod-ap-v1
    values: {severity: 8, occurrence: 5, detection: 4}
    rubric_anchors: ["s", "o", "d"]
    derived: {rpn: 160, action_priority: HIGH}
"""


@pytest.fixture
def store(tmp_path):
    return Store(init_register(tmp_path, "demo"))


class TestDiff:
    def test_evidence_match(self, store):
        write_risk(store, "R-0001", evidence='"src/orders/saga.py"')
        report = build_diff(store, files=["src/orders/saga.py"])
        assert report["touched"][0]["risk"] == "R-0001"
        assert report["touched"][0]["confidence"] == "high"
        assert "evidence:" in report["touched"][0]["reasons"][0]["reason"]

    def test_evidence_annotation_stripped(self, store):
        write_risk(store, "R-0001", evidence='"src/orders/saga.py (the revert path)"')
        report = build_diff(store, files=["src/orders/saga.py"])
        assert report["touched"] and report["touched"][0]["risk"] == "R-0001"

    def test_basename_collision_not_matched(self, store):
        """A ubiquitous basename must not false-match across directories.

        Bug: `_path_match` used bare-basename equality, so evidence
        `src/connection/mod.rs` HIGH-matched any changed `mod.rs`
        (`locator/mod.rs`, `python/mod.rs`) — false HIGH-confidence flags in the CI
        gate, worst on the polyglot repos (Rust mod.rs, Python __init__.py) risqlet
        targets. Now the parent directory must match too.
        """
        write_risk(store, "R-0001", evidence='"src/connection/mod.rs"')
        report = build_diff(store, files=["src/locator/mod.rs", "src/python/mod.rs"])
        assert report["touched"] == []  # neither shares connection/'s parent dir

    def test_init_py_collision_not_matched(self, store):
        write_risk(store, "R-0001", evidence='"pkg/auth/__init__.py"')
        report = build_diff(store, files=["pkg/billing/__init__.py"])
        assert report["touched"] == []

    def test_same_file_different_root_still_matches(self, store):
        """The legitimate reason basename matching existed — evidence and git
        reporting the same file at different roots — must still match at HIGH."""
        write_risk(store, "R-0001", evidence='"connection/mod.rs"')
        report = build_diff(store, files=["src/connection/mod.rs"])
        assert report["touched"] and report["touched"][0]["risk"] == "R-0001"
        assert report["touched"][0]["confidence"] == "high"

    def test_collision_still_matches_the_real_file(self, store):
        """Fixing the collision must not lose the true positive: the actual
        connection/mod.rs change is still flagged even amid decoy mod.rs files."""
        write_risk(store, "R-0001", evidence='"src/connection/mod.rs"')
        report = build_diff(store, files=["src/locator/mod.rs", "src/connection/mod.rs"])
        assert [t["risk"] for t in report["touched"]] == ["R-0001"]
        assert report["touched"][0]["confidence"] == "high"

    def test_test_ref_match(self, store):
        write_risk(store, "R-0001", evidence='"docs/x.md"',
                   mitigations='[{id: M-0001, risk_ids: [R-0001], treatment: reduce, '
                   'lever: detection, barrier: detect, concrete: c, residual_note: r, '
                   'tests: ["pytest:tests/test_saga.py::test_revert"]}]')
        report = build_diff(store, files=["tests/test_saga.py"])
        assert report["touched"] and "test:" in report["touched"][0]["reasons"][0]["reason"]

    def test_statement_token_low_confidence(self, store):
        write_risk(store, "R-0001", evidence='"unrelated/file.md"',
                   statement="Because the approval saga hardcodes tenant, "
                             "misfiling may occur, causing invisible approvals")
        report = build_diff(store, files=["src/approval/saga.py"])
        # 'approval' + 'saga' tokens appear in the path -> low-confidence touch
        assert report["touched"] and report["touched"][0]["confidence"] == "low"

    def test_no_match(self, store):
        write_risk(store, "R-0001", evidence='"src/orders/saga.py"')
        assert build_diff(store, files=["README.md"])["touched"] == []

    def test_untouched_high_priority_reminder(self, store):
        write_risk(store, "R-0001", evidence='"src/orders/saga.py"', scores=SCORED,
                   status="accepted")
        write_risk(store, "R-0002", evidence='"src/billing/pay.py"', scores=SCORED,
                   status="accepted")
        report = build_diff(store, files=["src/orders/saga.py"])
        touched = {t["risk"] for t in report["touched"]}
        assert touched == {"R-0001"}
        assert any(u["risk"] == "R-0002" for u in report["untouched_high_priority"])

    def test_read_only(self, store):
        write_risk(store, "R-0001")
        before = {p.name: p.read_text(encoding="utf-8") for p in store.register_dir.iterdir()}
        build_diff(store, files=["src/orders/saga.py"])
        assert {p.name: read_utf8(p) for p in store.register_dir.iterdir()} == before

    def test_files_via_stdin(self, store):
        write_risk(store, "R-0001", evidence='"src/orders/saga.py"')
        report = build_diff(store, stdin_text="src/orders/saga.py\nREADME.md\n")
        assert [t["risk"] for t in report["touched"]] == ["R-0001"]


class TestCheckGate:
    def _accepted_untested(self, store):
        write_risk(store, "R-0001", evidence='"src/orders/saga.py"', scores=SCORED,
                   status="accepted",
                   mitigations='[{id: M-0001, risk_ids: [R-0001], treatment: reduce, '
                   'lever: detection, barrier: detect, concrete: c, residual_note: r, '
                   'tests: []}]')

    def _set_mode(self, store, mode):
        cfg = store.load_config_raw()
        cfg.setdefault("constraints", {})["ci_gate"] = mode
        store.save_config_raw(cfg)

    def test_warn_mode_exits_zero(self, store):
        self._accepted_untested(store)
        self._set_mode(store, "warn")
        report = run_check(store, files=["src/orders/saga.py"])
        assert report["flagged"] and report["exit"] == 0

    def test_block_mode_exits_nonzero(self, store):
        self._accepted_untested(store)
        self._set_mode(store, "block")
        report = run_check(store, files=["src/orders/saga.py"])
        assert report["flagged"] and report["exit"] == 1

    def test_off_mode_silent(self, store):
        self._accepted_untested(store)
        self._set_mode(store, "off")
        # off still computes but never blocks; flagged may exist, exit 0
        report = run_check(store, files=["src/orders/saga.py"])
        assert report["exit"] == 0

    def test_ci_paths_filter(self, store):
        self._accepted_untested(store)
        self._set_mode(store, "block")
        cfg = store.load_config_raw()
        cfg["constraints"]["ci_paths"] = ["app/**"]
        store.save_config_raw(cfg)
        report = run_check(store, files=["src/orders/saga.py"])
        assert report["excluded_paths"] == 1
        assert report["flagged"] == [] and report["exit"] == 0

    def test_no_flag_when_covered(self, store, tmp_path):
        from risqlet.trace import ingest

        write_risk(store, "R-0001", evidence='"src/orders/saga.py"', scores=SCORED,
                   status="accepted",
                   mitigations='[{id: M-0001, risk_ids: [R-0001], treatment: reduce, '
                   'lever: detection, barrier: detect, concrete: c, residual_note: r, '
                   'tests: ["pytest:tests/test_saga.py::test_ok"]}]')
        junit = tmp_path / "j.xml"
        junit.write_text('<testsuite><testcase classname="tests.test_saga" '
                         'name="test_ok"/></testsuite>', encoding="utf-8")
        ingest(store, [junit], ts="t")
        self._set_mode(store, "block")
        report = run_check(store, files=["src/orders/saga.py"])
        assert report["flagged"] == [] and report["exit"] == 0


class TestParseClaudeHookPayload:
    """spec: change-reassessment — check accepts an agent hook payload."""

    def test_real_payload_shape(self):
        payload = json.dumps({
            "session_id": "abc", "hook_event_name": "PostToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": "src/orders/saga.py", "old_string": "a"},
        })
        assert parse_claude_hook_payload(payload) == ["src/orders/saga.py"]

    @pytest.mark.parametrize("text", [
        None, "", "   ", "not json at all", "{oops", "null", "[]", '"a string"', "42",
        "{}", '{"tool_input": null}', '{"tool_input": {}}', '{"tool_input": "nope"}',
        '{"tool_input": {"file_path": ""}}', '{"tool_input": {"file_path": "   "}}',
        '{"tool_input": {"file_path": null}}', '{"tool_input": {"file_path": 7}}',
    ])
    def test_unusable_payload_is_empty_never_raises(self, text):
        assert parse_claude_hook_payload(text) == []

    def test_path_is_stripped(self):
        assert parse_claude_hook_payload(
            '{"tool_input": {"file_path": "  src/a.py \\n"}}') == ["src/a.py"]


class TestCheckHookMode:
    """spec: change-reassessment — hook mode reports but never blocks."""

    def _accepted_untested(self, store):
        write_risk(store, "R-0001", evidence='"src/orders/saga.py"', scores=SCORED,
                   status="accepted",
                   mitigations='[{id: M-0001, risk_ids: [R-0001], treatment: reduce, '
                   'lever: detection, barrier: detect, concrete: c, residual_note: r, '
                   'tests: ["pytest:tests/test_saga.py::test_ok"]}]')

    def _set_mode(self, store, mode):
        cfg = store.load_config_raw()
        cfg.setdefault("constraints", {})["ci_gate"] = mode
        store.save_config_raw(cfg)

    def _run(self, store, monkeypatch, payload, extra=()):
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        root = str(store.root.parent)
        return main(["check", "--hook-input", "claude", "--dir", root, *extra])

    def test_payload_resolves_edited_file(self, store, monkeypatch, capsys):
        self._accepted_untested(store)
        payload = json.dumps({"tool_input": {"file_path": "src/orders/saga.py"}})
        assert self._run(store, monkeypatch, payload, ["--json"]) == 0
        assert "R-0001" in capsys.readouterr().out

    def test_block_mode_still_exits_zero(self, store, monkeypatch, capsys):
        self._accepted_untested(store)
        self._set_mode(store, "block")
        payload = json.dumps({"tool_input": {"file_path": "src/orders/saga.py"}})
        # same register + file exits 1 via --files; hook mode must not break the loop
        assert self._run(store, monkeypatch, payload, ["--json"]) == 0
        assert json.loads(capsys.readouterr().out)["flagged"]
        assert main(["check", "--files", "src/orders/saga.py",
                     "--dir", str(store.root.parent)]) == 1

    @pytest.mark.parametrize("payload", ["", "not json", "{}", '{"tool_input": {}}'])
    def test_malformed_payload_is_silent_noop(self, store, monkeypatch, capsys,
                                              payload):
        self._accepted_untested(store)
        self._set_mode(store, "block")
        assert self._run(store, monkeypatch, payload) == 0
        out = capsys.readouterr()
        assert out.out == "" and "Traceback" not in out.err

    def test_internal_error_never_escapes(self, store, monkeypatch, capsys):
        self._accepted_untested(store)

        def boom(*a, **k):
            raise RuntimeError("register exploded")

        monkeypatch.setattr("risqlet.changeset.run_check", boom)
        payload = json.dumps({"tool_input": {"file_path": "src/orders/saga.py"}})
        assert self._run(store, monkeypatch, payload) == 0
        assert "Traceback" not in capsys.readouterr().err

    def test_stdin_mode_semantics_unchanged(self, store, monkeypatch):
        self._accepted_untested(store)
        self._set_mode(store, "block")
        monkeypatch.setattr("sys.stdin", io.StringIO("src/orders/saga.py\n"))
        assert main(["check", "--stdin", "--dir", str(store.root.parent)]) == 1


class TestCiInit:
    def test_github(self, tmp_path):
        result = init("github", tmp_path)
        dest = tmp_path / ".github/workflows/risqlet.yml"
        assert dest.exists() and result["written"] == str(dest)
        assert "risqlet validate" in read_utf8(dest) and "risqlet check" in read_utf8(dest)

    def test_gitlab(self, tmp_path):
        init("gitlab", tmp_path)
        assert (tmp_path / ".gitlab-ci.risqlet.yml").exists()

    def test_claude_hooks_prints(self, tmp_path):
        result = init("claude-hooks", tmp_path)
        assert result["printed"]
        assert json.loads(result["content"])["hooks"]["PostToolUse"]

    def _template_commands(self):
        payload = json.loads(template_text("claude-hooks"))
        return [h["command"] for e in payload["hooks"]["PostToolUse"] for h in e["hooks"]]

    def test_claude_hooks_matches_installed_command(self):
        """spec: change-reassessment — the two hook surfaces cannot drift."""
        from risqlet.setup import render

        assert self._template_commands() == [render.SETUP_HOOK_COMMAND]

    def test_claude_hooks_reads_no_unset_env_var(self):
        # regression: the template used to read $CLAUDE_TOOL_FILE_PATH, which Claude
        # Code never sets — it silently checked an empty path on every platform
        assert not any("$" in c for c in self._template_commands())

    def test_claude_hooks_resolves_the_edited_file(self, store, monkeypatch, capsys):
        """The emitted command actually checks the payload's file."""
        write_risk(store, "R-0001", evidence='"src/orders/saga.py"', scores=SCORED,
                   status="accepted", mitigations='[{id: M-0001, risk_ids: [R-0001], '
                   'treatment: reduce, lever: detection, barrier: detect, concrete: c, '
                   'residual_note: r, tests: ["pytest:tests/test_saga.py::test_ok"]}]')
        argv = shlex.split(self._template_commands()[0])
        assert argv[0] == "risqlet"
        payload = json.dumps({"tool_input": {"file_path": "src/orders/saga.py"}})
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        assert main([*argv[1:], "--dir", str(store.root.parent)]) == 0
        assert "R-0001" in capsys.readouterr().out

    def test_arbitrary_path(self, tmp_path):
        dest = tmp_path / "custom" / "flow.yml"
        init(str(dest), tmp_path)
        assert dest.exists()

    def test_overwrite_protection(self, tmp_path):
        init("github", tmp_path)
        with pytest.raises(CIError, match="already exists"):
            init("github", tmp_path)
        init("github", tmp_path, force=True)  # ok with force

    def test_unknown_target(self, tmp_path):
        with pytest.raises(CIError, match="unknown target"):
            init("jenkins", tmp_path)  # no path-like suffix, not a known target


class TestTemplatesValid:
    def test_yaml_templates_parse(self):
        yaml = pytest.importorskip("yaml", reason="pyyaml not installed")
        for target in ("github", "gitlab"):
            yaml.safe_load(template_text(target))

    def test_hooks_json_valid(self):
        json.loads(template_text("claude-hooks"))

    def test_templates_reference_real_commands(self):
        import re

        parser = build_parser()
        subcommands = set()
        for action in parser._subparsers._group_actions:  # noqa: SLF001
            subcommands.update(action.choices.keys())
        for target in ("github", "gitlab", "claude-hooks"):
            for cmd in set(re.findall(r"\brisqlet[ \t]+([a-z-]+)", template_text(target))):
                assert cmd in subcommands, f"{target}: unknown risqlet {cmd}"


class TestIntegration:
    def test_validate_unaffected(self, store):
        write_risk(store, "R-0001", evidence='"src/orders/saga.py"')
        before = validate_register(store).to_dict()
        cfg = store.load_config_raw()
        cfg.setdefault("constraints", {})["ci_gate"] = "block"
        cfg["constraints"]["ci_paths"] = ["src/**"]
        store.save_config_raw(cfg)
        after = validate_register(store).to_dict()
        assert before["pass"] == after["pass"] == True  # noqa: E712

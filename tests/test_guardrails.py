"""Tests for risk-driven guardrail generation, diff, and install."""

import json

import pytest

from risqlet.guardrails import (
    GuardrailError,
    build_plan,
    diff_target,
    install_plan,
    load_templates,
)
from risqlet.guardrails.engine import _install_claude
from risqlet.store import Store, init_register
from risqlet.validate import validate_register

CONF_RISK = """\
schema_version: 1
id: {id}
statement: Because tokens are logged, replay may occur, causing account takeover
aspects: [iso25010.confidentiality, iso25010.security]
elicited_by:
  method: stride
  prompt_ref: "owasp-web.cryptographic-failures"
  evidence: ["src/auth/logging.py", "src/auth/session.py"]
scores:
  - policy: sod-ap-v1
    values: {{severity: {sev}, occurrence: 3, detection: 6}}
    rubric_anchors: [s, o, d]
status: {status}
mitigations:
  - id: M-{n}
    risk_ids: [{id}]
    treatment: reduce
    lever: detection
    barrier: {barrier}
    technique_ref: "owasp-web.cryptographic-failures"
    concrete: redact tokens in logs
    residual_note: legacy logs remain
    tests: []
"""


@pytest.fixture
def store(tmp_path):
    return Store(init_register(tmp_path, "demo"))


def add_risk(store, id="R-0001", sev=9, status="accepted", barrier="prevent", n="0001"):
    (store.register_dir / f"{id}.yaml").write_text(
        CONF_RISK.format(id=id, sev=sev, status=status, barrier=barrier, n=n), encoding="utf-8")


class TestTemplates:
    def test_load(self):
        templates = load_templates()
        assert len(templates) >= 10
        ids = {t.id for t in templates}
        assert {"secret-scan-posttool", "env-read-deny", "agents-no-secret-logging"} <= ids

    def test_only_declared_params_interpolated(self, store):
        # a template without params must render byte-identical to its body
        add_risk(store, barrier="prevent")
        plan = build_plan(store)
        env = next(g for g in plan.guardrails if g.template_id == "env-read-deny")
        template = next(t for t in load_templates() if t.id == "env-read-deny")
        assert env.content == template.body.rstrip("\n")  # no free-form drift

    def test_path_param_scoped_to_evidence(self, store):
        add_risk(store, barrier="prevent")
        plan = build_plan(store)
        secret = next(g for g in plan.guardrails if g.template_id == "secret-scan-posttool")
        # scoping now lives in the executable command (*dir/* matches absolute paths)
        assert "*src/auth/*" in secret.command
        assert secret.params["paths"] == ["src/auth"]


class TestSelection:
    def test_barrier_and_aspect_select(self, store):
        add_risk(store, barrier="prevent")
        ids = {g.template_id for g in build_plan(store).guardrails}
        assert "secret-scan-posttool" in ids  # confidentiality + prevent barrier

    def test_proposed_excluded(self, store):
        add_risk(store, status="proposed")
        assert build_plan(store).guardrails == []

    def test_reviewed_excluded(self, store):
        add_risk(store, status="reviewed")
        assert build_plan(store).guardrails == []

    def test_mitigating_included(self, store):
        add_risk(store, status="mitigating")
        assert build_plan(store).guardrails

    def test_barrier_mismatch_filters(self, store):
        # recover-barrier mitigation should match no prevent/detect templates
        add_risk(store, barrier="recover")
        assert build_plan(store).guardrails == []

    def test_deterministic_and_read_only(self, store, tmp_path):
        add_risk(store)
        snap = {p.name: p.read_text(encoding="utf-8") for p in store.register_dir.iterdir()}
        first = build_plan(store).to_dict()
        second = build_plan(store).to_dict()
        assert first == second
        assert {p.name: p.read_text(encoding="utf-8") for p in store.register_dir.iterdir()} == snap

    def test_dedupe_across_risks(self, store):
        add_risk(store, id="R-0001", n="0001")
        add_risk(store, id="R-0002", n="0002")
        plan = build_plan(store)
        secret = [g for g in plan.guardrails if g.template_id == "secret-scan-posttool"]
        assert len(secret) == 1  # deduped by (template, params)
        assert set(secret[0].risks) == {"R-0001", "R-0002"}


class TestHonesty:
    def test_hard_and_soft_labels(self, store):
        add_risk(store, barrier="prevent")
        plan = build_plan(store)
        by_id = {g.template_id: g.enforcement for g in plan.guardrails}
        assert by_id["secret-scan-posttool"] == "hard"
        assert by_id["agents-no-secret-logging"] == "soft"

    def test_advisory_warning_when_soft_only(self, store):
        # a high-sev risk whose only match is the soft injection AGENTS.md rule
        (store.register_dir / "R-0009.yaml").write_text(
            CONF_RISK.format(id="R-0009", sev=9, status="accepted", barrier="prevent", n="0009")
            .replace("[iso25010.confidentiality, iso25010.security]", "[companyx.thing]")
            .replace("owasp-web.cryptographic-failures", "owasp-web.injection"), encoding="utf-8")
        plan = build_plan(store)
        assert all(g.enforcement == "soft" for g in plan.guardrails)
        assert any("advisory" in a and "R-0009" in a for a in plan.advisories)

    def test_no_advisory_when_hard_present(self, store):
        add_risk(store, sev=9, barrier="prevent")  # includes hard secret-scan
        assert build_plan(store).advisories == []

    def test_low_severity_no_advisory(self, store):
        # soft-only but low severity -> no advisory
        (store.register_dir / "R-0005.yaml").write_text(
            CONF_RISK.format(id="R-0005", sev=3, status="accepted", barrier="prevent", n="0005")
            .replace("[iso25010.confidentiality, iso25010.security]", "[companyx.thing]")
            .replace("owasp-web.cryptographic-failures", "owasp-web.injection"), encoding="utf-8")
        assert build_plan(store).advisories == []


class TestInstallAndDiff:
    def test_install_path_bundle(self, store, tmp_path):
        add_risk(store)
        out = tmp_path / "out"
        result = install_plan(store, build_plan(store), "path", out)
        bundle = (out / "guardrails.md").read_text(encoding="utf-8")
        assert "risqlet:R-0001:prevent:secret-scan-posttool" in bundle
        assert (out / ".risqlet-guardrails.lock.json").exists()
        assert result["guardrails"] >= 4

    def test_install_agents_md_section(self, store, tmp_path):
        add_risk(store)
        install_plan(store, build_plan(store), "agents-md", tmp_path)
        agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "risqlet:guardrails:begin" in agents
        assert "agents-no-secret-logging" in agents

    def test_agents_md_section_replaced_not_duplicated(self, store, tmp_path):
        add_risk(store)
        install_plan(store, build_plan(store), "agents-md", tmp_path)
        install_plan(store, build_plan(store), "agents-md", tmp_path)  # again
        agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert agents.count("risqlet:guardrails:begin") == 1  # idempotent

    def test_agents_md_preserves_existing_content(self, store, tmp_path):
        add_risk(store)
        (tmp_path / "AGENTS.md").write_text("# My project rules\n\nDo the thing.\n",
                                            encoding="utf-8")
        install_plan(store, build_plan(store), "agents-md", tmp_path)
        agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "# My project rules" in agents and "Do the thing." in agents
        assert "risqlet:guardrails:begin" in agents

    def test_claude_settings_writes_permission_deny(self, store, tmp_path):
        # cross-platform: the permission guardrail is written on every OS
        add_risk(store)
        _install_claude(tmp_path, build_plan(store), force=False)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
        assert any(str(d).startswith("Read(**/.env") for d in settings["permissions"]["deny"])

    @pytest.mark.posix_only  # the bundled hooks are POSIX shell; refused on Windows
    def test_claude_settings_writes_shell_hook(self, store, tmp_path):
        add_risk(store)
        _install_claude(tmp_path, build_plan(store), force=False)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
        assert "hooks" in settings
        assert any("# risqlet:" in h["command"]
                   for e in settings["hooks"]["PostToolUse"] for h in e["hooks"])

    def test_claude_reinstall_preserves_user_hook(self, store, tmp_path):
        # cross-platform: a user's own hook is never touched, however many installs
        add_risk(store)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write",
                      "hooks": [{"type": "command", "command": "my-own-hook"}]}]}}),
                          encoding="utf-8")
        _install_claude(tmp_path, build_plan(store), force=False)
        _install_claude(tmp_path, build_plan(store), force=False)  # twice
        settings = json.loads((settings_dir / "settings.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for e in settings["hooks"]["PostToolUse"] for h in e["hooks"]]
        assert "my-own-hook" in cmds  # user hook preserved

    @pytest.mark.posix_only  # the managed shell hook is not written on Windows
    def test_claude_reinstall_does_not_duplicate_managed_hook(self, store, tmp_path):
        add_risk(store)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write",
                      "hooks": [{"type": "command", "command": "my-own-hook"}]}]}}),
                          encoding="utf-8")
        _install_claude(tmp_path, build_plan(store), force=False)
        _install_claude(tmp_path, build_plan(store), force=False)  # twice
        settings = json.loads((settings_dir / "settings.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for e in settings["hooks"]["PostToolUse"] for h in e["hooks"]]
        assert sum("# risqlet:" in c for c in cmds) == 1  # managed hook not duplicated

    def test_windows_no_verify_does_not_write_shell_hook(self, store, tmp_path, monkeypatch):
        """The behavior change (user-approved): --no-verify used to slip a POSIX shell
        hook — which shells out to bash/python3, absent on Windows — into Windows
        settings.json with no warning. The write-time guard in _install_claude closes
        that escape hatch. Simulated Windows so it runs on every OS; the real-Windows
        counterpart is test_hook_verification.py::TestWindowsRefusal."""
        add_risk(store)
        monkeypatch.setattr("risqlet.guardrails.engine._is_windows", lambda: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        res = install_plan(store, build_plan(store), "claude-project", proj, verify=False)
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for e in settings.get("hooks", {}).get("PostToolUse", [])
                for h in e["hooks"]]
        assert not any("# risqlet:" in c for c in cmds)  # no non-runnable hook landed
        assert any(s["failed"] == ["platform"] for s in res["verify_skipped"])  # and reported
        assert any(str(d).startswith("Read(**/.env")  # permissions still degrade honestly
                   for d in settings["permissions"]["deny"])
        # the lock is written from the same filtered plan, so `diff` must report the
        # dropped hook as missing — not falsely in-sync (the reviewer's finding)
        d = diff_target(store, proj)
        assert any("secret-scan-posttool" in m for m in d["missing"])

    def test_windows_force_cannot_override_platform(self, store, tmp_path, monkeypatch):
        """--force overrides a verification failure, but not platform impossibility:
        a shell hook still cannot run on Windows, so force must not write it."""
        add_risk(store)
        monkeypatch.setattr("risqlet.guardrails.engine._is_windows", lambda: True)
        monkeypatch.setattr("risqlet.guardrails.verify._is_windows", lambda: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        res = install_plan(store, build_plan(store), "claude-project", proj, force=True)
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for e in settings.get("hooks", {}).get("PostToolUse", [])
                for h in e["hooks"]]
        assert not any("# risqlet:" in c for c in cmds)  # force did NOT write it
        # the platform skip must NOT be marked forced — force didn't override it
        plat = [s for s in res["verify_skipped"] if s["failed"] == ["platform"]]
        assert plat and plat[0]["forced"] is False

    def test_overwrite_protection_path_target(self, store, tmp_path):
        # a standalone bundle file (path target) with foreign content is protected
        add_risk(store)
        dest = tmp_path / "bundle.md"
        dest.write_text("hand-written, no markers\n", encoding="utf-8")
        with pytest.raises(GuardrailError, match="--force"):
            install_plan(store, build_plan(store), "path", dest)
        install_plan(store, build_plan(store), "path", dest, force=True)  # ok
        assert "risqlet:guardrails:begin" in dest.read_text(encoding="utf-8")

    def test_refuses_install_inside_register(self, store):
        add_risk(store)
        with pytest.raises(GuardrailError, match="must not be installed inside"):
            install_plan(store, build_plan(store), "path", store.root / "sub")

    def test_diff_in_sync_then_stale(self, store, tmp_path):
        add_risk(store)
        install_plan(store, build_plan(store), "agents-md", tmp_path)
        assert diff_target(store, tmp_path) == {"stale": [], "missing": [], "drift": []}
        # reject the risk -> plan drops it -> installed markers go stale
        path = store.register_dir / "R-0001.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("status: accepted",
                                                                 "status: rejected"),
                                                                 encoding="utf-8")
        report = diff_target(store, tmp_path)
        assert report["stale"] and not report["missing"]

    def test_diff_missing_for_uninstalled(self, store, tmp_path):
        add_risk(store)
        report = diff_target(store, tmp_path)  # nothing installed
        assert report["missing"] and not report["stale"]

    def test_register_untouched_and_validate_unaffected(self, populated_register, tmp_path):
        # accept R-0001 with a matching event so validate passes, then guardrails
        from tests.conftest import append_raw_event, read_utf8
        for frm, to in [("proposed", "reviewed"), ("reviewed", "accepted")]:
            append_raw_event(populated_register, ts="t", type="status_change", risk="R-0001",
                             principal="human:many", note="", to=to, **{"from": frm})
        p = populated_register.register_dir / "R-0001.yaml"
        p.write_text(p.read_text(encoding="utf-8").replace("status: proposed", "status: accepted"),
                                                           encoding="utf-8")
        before = validate_register(populated_register).to_dict()
        snap = {x.name: read_utf8(x) for x in populated_register.register_dir.iterdir()}
        install_plan(populated_register, build_plan(populated_register), "agents-md", tmp_path)
        after = validate_register(populated_register).to_dict()
        assert before == after
        assert {x.name: read_utf8(x) for x in populated_register.register_dir.iterdir()} == snap

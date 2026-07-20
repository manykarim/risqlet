"""Tests for guardrail hook verification and the verify-by-default install gate."""

import json
import os
import shutil

import pytest

from risqlet.guardrails.engine import _render_text, build_plan, install_plan, load_templates
from risqlet.guardrails.models import RenderedGuardrail, VerifySpec
from risqlet.guardrails.verify import verify_guardrail

TEMPLATES = {t.id: t for t in load_templates()}


def rendered(template_id, dirs=("."), test_command=None):
    t = TEMPLATES[template_id]
    cmd = _render_text(t.command, list(dirs), test_command).strip() if t.command else ""
    return RenderedGuardrail(
        template_id=t.id, surface=str(t.surface), enforcement=str(t.enforcement),
        params={"paths": list(dirs)} if "paths" in t.params else {},
        content="x", command=cmd, verify=t.verify)


class TestVerify:
    @pytest.mark.posix_only
    def test_good_secret_hook_passes(self, tmp_path):
        r = verify_guardrail(rendered("secret-scan-posttool", ["src/auth"]), tmp_path)
        assert r.ok
        names = {c.name for c in r.checks}
        assert {"benign-passes", "violation-caught"} <= names

    @pytest.mark.posix_only
    def test_good_lint_hook_passes(self, tmp_path):
        assert verify_guardrail(rendered("lint-format-posttool"), tmp_path).ok

    @pytest.mark.posix_only  # on Windows the shell hook is refused before tool preflight
    def test_missing_tool_fails(self, tmp_path):
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command='nope_tool_xyz "$RISQLET_HOOK_FILE"',
            verify=VerifySpec(tools=["nope_tool_xyz"], blocking=True, input="file",
                              benign="ok\n", violation="bad\n"))
        r = verify_guardrail(g, tmp_path)
        assert not r.ok and any(c.name == "tool:nope_tool_xyz" for c in r.failed())

    @pytest.mark.posix_only
    def test_syntax_error_fails(self, tmp_path):
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command='if [ ; then echo bad',  # broken shell
            verify=VerifySpec(tools=["bash"], blocking=False, input="none"))
        r = verify_guardrail(g, tmp_path)
        assert not r.ok and any(c.name == "syntax" for c in r.failed())

    @pytest.mark.posix_only
    def test_false_block_fails(self, tmp_path):
        # a hook that blocks even the benign fixture must fail verification
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command='exit 2',
            verify=VerifySpec(tools=["bash"], blocking=True, input="file",
                              benign="fine\n", violation="bad\n"))
        r = verify_guardrail(g, tmp_path)
        assert not r.ok and any(c.name == "benign-passes" for c in r.failed())

    @pytest.mark.posix_only
    def test_hang_times_out(self, tmp_path, monkeypatch):
        monkeypatch.setattr("risqlet.guardrails.verify.TIMEOUT_S", 2)
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command='sleep 30',
            verify=VerifySpec(tools=["bash"], blocking=False, input="none"))
        r = verify_guardrail(g, tmp_path)
        assert not r.ok and any(c.name == "runs" for c in r.failed())

    def test_shell_free_hook_verifies_without_a_shell(self, tmp_path, monkeypatch,
                                                      risqlet_on_path):
        """spec: hook-verification — a shell-free hook needs no shell.

        Deliberately not marked posix_only: this is the cross-platform property
        itself, so it must run on Windows. The command is `risqlet` rather than
        `true` because `true` is not an executable on Windows — using it would
        make this test skip on the one platform it exists to cover.
        """
        real_which = shutil.which
        monkeypatch.setattr("risqlet.guardrails.verify.shutil.which",
                            lambda t, *a, **k: None if t == "bash" else real_which(t))
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command="risqlet --help",
            verify=VerifySpec(tools=[], blocking=False, input="none"))
        r = verify_guardrail(g, tmp_path)
        assert r.ok, r.failed()
        assert not any(c.name == "tool:bash" for c in r.checks)
        assert not any(c.name == "syntax" for c in r.checks)

    @pytest.mark.posix_only  # on Windows the answer is "unsupported", not "no bash"
    def test_shell_hook_still_requires_its_shell(self, tmp_path, monkeypatch):
        """spec: hook-verification — a shell hook without bash still fails.

        POSIX-only: on Windows a shell hook is refused wholesale by policy before
        the tool preflight runs, so "bash is missing" is never the reason reported.
        test_shell_hook_reports_unsupported_on_windows covers that path instead.
        """
        real_which = shutil.which
        monkeypatch.setattr("risqlet.guardrails.verify.shutil.which",
                            lambda t, *a, **k: None if t == "bash" else real_which(t))
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command='echo "$RISQLET_HOOK_FILE" | grep -q x',
            verify=VerifySpec(tools=[], blocking=False, input="none"))
        r = verify_guardrail(g, tmp_path)
        assert not r.ok
        assert any(c.name == "tool:bash" for c in r.failed())

    def test_shell_hook_reports_unsupported_on_windows(self, tmp_path, monkeypatch):
        """spec: cross-platform-support — unsupported is stated, not crashed into."""
        monkeypatch.setattr("risqlet.guardrails.verify._is_windows", lambda: True)
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command='grep -q x "$RISQLET_HOOK_FILE"',
            verify=VerifySpec(tools=["grep"], blocking=True, input="file",
                              benign="ok\n", violation="x\n"))
        r = verify_guardrail(g, tmp_path)
        assert not r.ok
        platform_check = [c for c in r.failed() if c.name == "platform"]
        assert platform_check and "not supported on Windows" in platform_check[0].detail

    def test_shell_free_hook_still_supported_on_windows(self, tmp_path, monkeypatch,
                                                        risqlet_on_path):
        # the Windows refusal must be scoped to shell hooks — the shell-free check
        # hook is exactly what does work there
        monkeypatch.setattr("risqlet.guardrails.verify._is_windows", lambda: True)
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command="risqlet --help",
            verify=VerifySpec(tools=[], blocking=False, input="none"))
        assert verify_guardrail(g, tmp_path).ok

    def test_kill_falls_back_when_killpg_missing(self, tmp_path, monkeypatch):
        """os.killpg does not exist on Windows — must not die in AttributeError."""
        monkeypatch.setattr("risqlet.guardrails.verify.TIMEOUT_S", 2)
        monkeypatch.delattr("risqlet.guardrails.verify.os.killpg", raising=False)
        g = RenderedGuardrail(
            template_id="x", surface="claude-hook", enforcement="hard", params={},
            content="x", command="sleep 30",
            verify=VerifySpec(tools=[], blocking=False, input="none"))
        r = verify_guardrail(g, tmp_path)  # must time out cleanly, not raise
        assert not r.ok and any(c.name == "runs" for c in r.failed())

    def test_advisory_guardrail_is_noop(self, tmp_path):
        g = RenderedGuardrail(template_id="agents-x", surface="agents-md",
                              enforcement="soft", content="advice", verify=None)
        assert verify_guardrail(g, tmp_path).ok


ACCEPTED_SECRET_RISK = """\
schema_version: 1
id: R-0001
statement: Because tokens are logged, replay may occur, causing takeover
aspects: [iso25010.confidentiality, iso25010.security]
elicited_by:
  method: stride
  prompt_ref: "owasp-web.cryptographic-failures"
  evidence: ["src/auth/x.py"]
scores:
  - policy: sod-ap-v1
    values: {severity: 8, occurrence: 3, detection: 6}
    rubric_anchors: [s, o, d]
status: accepted
mitigations:
  - id: M-0001
    risk_ids: [R-0001]
    treatment: reduce
    lever: detection
    barrier: prevent
    technique_ref: "owasp-web.cryptographic-failures"
    concrete: redact
    residual_note: legacy logs
    tests: []
"""


@pytest.fixture
def store_with_secret_risk(tmp_path):
    from risqlet.store import Store, init_register

    store = Store(init_register(tmp_path, "demo"))
    (store.register_dir / "R-0001.yaml").write_text(ACCEPTED_SECRET_RISK, encoding="utf-8")
    return store


@pytest.mark.skipif(os.name != "nt", reason="asserts the Windows-native refusal path")
class TestWindowsRefusal:
    """Proof, on a REAL Windows runner, that guardrails install degrades honestly.

    The product deliberately refuses POSIX shell hooks on Windows — there is nothing
    to execute, so this asserts the refusal, not execution. Not posix_only (it must
    RUN on the windows-latest leg); skipped with a reason on Linux/macOS. Drives the
    `--no-verify` path deliberately: the default path was already honest before the
    write-time refusal, so only --no-verify (and the lock/diff consistency) actually
    exercises the new code. Real os.name=='nt' closes what the simulated-Windows
    tests in test_guardrails.py cannot: WindowsPath and PATHEXT through the flow."""

    def test_no_verify_still_refuses_and_stays_consistent(self, store_with_secret_risk,
                                                          tmp_path):
        from risqlet.guardrails import diff_target

        proj = tmp_path / "proj"
        proj.mkdir()
        # --no-verify bypasses the gate; the shell hook must STILL be refused here
        res = install_plan(store_with_secret_risk, build_plan(store_with_secret_risk),
                           "claude-project", proj, verify=False)  # must not raise
        skipped = {s["template_id"]: s for s in res["verify_skipped"]}
        assert "secret-scan-posttool" in skipped
        assert skipped["secret-scan-posttool"]["failed"] == ["platform"]
        assert "not supported on Windows" in skipped["secret-scan-posttool"]["detail"]

        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for e in settings.get("hooks", {}).get("PostToolUse", [])
                for h in e["hooks"]]
        assert not any("# risqlet:" in c for c in cmds)  # no non-runnable hook written
        assert settings["permissions"]["deny"]  # degrades to permissions-only

        # the lock must match reality: `diff` reports the dropped hook as missing,
        # not falsely "in sync" (the regression the reviewer found)
        d = diff_target(store_with_secret_risk, proj)
        assert any("secret-scan-posttool" in m for m in d["missing"])


@pytest.mark.posix_only
class TestInstallGate:
    def test_claude_install_writes_real_command(self, store_with_secret_risk, tmp_path):
        proj = tmp_path / "proj"
        proj.mkdir()
        # tools (grep/bash) are present, so the hook verifies and installs for real
        install_plan(store_with_secret_risk, build_plan(store_with_secret_risk),
                     "claude-project", proj)
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for e in settings["hooks"]["PostToolUse"] for h in e["hooks"]]
        assert any("grep" in c and "true #" not in c for c in cmds)  # real, not placeholder
        assert not any(c.strip().startswith("true #") for c in cmds)

    def test_failing_hook_skipped_by_default(self, store_with_secret_risk, tmp_path, monkeypatch):
        # make verification fail (pretend grep missing)
        import risqlet.guardrails.verify as v
        real_which = v.shutil.which
        monkeypatch.setattr(v.shutil, "which",
                            lambda t: None if t == "grep" else real_which(t))
        proj = tmp_path / "proj"
        proj.mkdir()
        result = install_plan(store_with_secret_risk, build_plan(store_with_secret_risk),
                              "claude-project", proj)
        assert any(s["template_id"] == "secret-scan-posttool" and not s["forced"]
                   for s in result["verify_skipped"])
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for e in settings.get("hooks", {}).get("PostToolUse", [])
                for h in e["hooks"]]
        assert not any("grep" in c for c in cmds)  # the failing hook was not installed

    def test_force_installs_failing_with_flag(self, store_with_secret_risk, tmp_path, monkeypatch):
        import risqlet.guardrails.verify as v
        real_which = v.shutil.which
        monkeypatch.setattr(v.shutil, "which",
                            lambda t: None if t == "grep" else real_which(t))
        proj = tmp_path / "proj"
        proj.mkdir()
        result = install_plan(store_with_secret_risk, build_plan(store_with_secret_risk),
                              "claude-project", proj, force=True)
        assert any(s["template_id"] == "secret-scan-posttool" and s["forced"]
                   for s in result["verify_skipped"])

    def test_no_verify_skips_gate(self, store_with_secret_risk, tmp_path, monkeypatch):
        import risqlet.guardrails.verify as v
        monkeypatch.setattr(v.shutil, "which", lambda t: None)  # everything "missing"
        proj = tmp_path / "proj"
        proj.mkdir()
        result = install_plan(store_with_secret_risk, build_plan(store_with_secret_risk),
                              "claude-project", proj, verify=False)
        assert result["verify_skipped"] == []  # gate skipped entirely


class TestCoverageStopDetection:
    def test_parked_without_test_command(self, tmp_path):
        from risqlet.store import Store, init_register

        store = Store(init_register(tmp_path, "demo"))
        # a risk that would select coverage-check-stop (testability + detect barrier)
        (store.register_dir / "R-0002.yaml").write_text(
            ACCEPTED_SECRET_RISK.replace("R-0001", "R-0002")
            .replace("[iso25010.confidentiality, iso25010.security]", "[iso25010.testability]")
            .replace("barrier: prevent", "barrier: detect")
            .replace("owasp-web.cryptographic-failures", "iso25010.testability"), encoding="utf-8")
        # tmp_path has no pyproject/package.json/Makefile-test -> parked
        plan = build_plan(store)
        assert not any(g.template_id == "coverage-check-stop" for g in plan.guardrails)
        assert any("coverage-check-stop" in n for n in plan.notes)

    def test_detects_pytest(self, tmp_path):
        from risqlet.store import Store, init_register

        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        store = Store(init_register(tmp_path, "demo"))
        (store.register_dir / "R-0002.yaml").write_text(
            ACCEPTED_SECRET_RISK.replace("R-0001", "R-0002")
            .replace("[iso25010.confidentiality, iso25010.security]", "[iso25010.testability]")
            .replace("barrier: prevent", "barrier: detect")
            .replace("owasp-web.cryptographic-failures", "iso25010.testability"), encoding="utf-8")
        plan = build_plan(store)
        g = next((g for g in plan.guardrails if g.template_id == "coverage-check-stop"), None)
        assert g is not None and "pytest -q" in g.command


@pytest.mark.posix_only
class TestInstalledClaudeStdinContract:
    """Regression: the installed Claude hook must read the file path from the
    stdin JSON payload Claude actually sends — not an env var (caught by live
    dogfooding, 2026-07-11)."""

    def test_installed_hook_fires_on_claude_stdin(self, store_with_secret_risk, tmp_path):
        import subprocess

        proj = tmp_path / "proj"
        (proj / "src" / "auth").mkdir(parents=True)
        install_plan(store_with_secret_risk, build_plan(store_with_secret_risk),
                     "claude-project", proj)
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmd = [h["command"] for e in settings["hooks"]["PostToolUse"]
               for h in e["hooks"]][0]
        target = proj / "src" / "auth" / "fixtures.py"

        def run(stdin_json: str) -> int:
            return subprocess.run(["bash", "-c", cmd], input=stdin_json,
                                  capture_output=True, text=True, encoding="utf-8").returncode

        payload = json.dumps({"tool_name": "Write",
                              "tool_input": {"file_path": str(target)}})
        target.write_text("port = 8080\n", encoding="utf-8")
        assert run(payload) == 0                    # benign: allowed
        target.write_text("token = 'abc123'\n", encoding="utf-8")
        assert run(payload) == 2                    # secret: blocked via stdin JSON
        # a file outside the scoped path is ignored
        outside = proj / "other.py"
        outside.write_text("token = 'abc123'\n", encoding="utf-8")
        assert run(json.dumps({"tool_input": {"file_path": str(outside)}})) == 0

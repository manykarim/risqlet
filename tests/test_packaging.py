"""Release-readiness checks: packaging metadata, governance files, shipped assets."""

import glob
import json
import os
import shlex
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.conftest import read_utf8

ROOT = Path(__file__).resolve().parents[1]

# every agent risqlet ships an adapter for — read from the adapter data so a new
# adapter is smoke-tested automatically rather than silently uncovered
ADAPTER_IDS = [p.stem for p in (ROOT / "src/risqlet/setup/adapters").glob("*.yaml")]


def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


class TestMetadata:
    def test_core_fields_present(self):
        proj = pyproject()["project"]
        assert proj["name"] == "risqlet"
        for field in ("description", "readme", "license", "authors", "keywords",
                      "classifiers"):
            assert proj.get(field), f"missing {field}"
        assert any("Apache" in c for c in proj["classifiers"])
        assert any("3.12" in c for c in proj["classifiers"])

    def test_urls_present(self):
        urls = pyproject()["project"]["urls"]
        assert "Repository" in urls and "Issues" in urls

    def test_os_claims_match_what_ci_runs(self):
        """spec: cross-platform-support — don't claim a platform CI doesn't run.

        A classifier is a promise to users browsing PyPI. Tying it to the matrix
        means dropping a platform from CI is a failing test, not a silent lie.
        """
        from ruamel.yaml import YAML

        wf = YAML(typ="safe").load(read_utf8(ROOT / ".github/workflows/test.yml"))
        runners = wf["jobs"]["test"]["strategy"]["matrix"]["os"]
        claimed = {c for c in pyproject()["project"]["classifiers"]
                   if c.startswith("Operating System")}
        assert claimed, "no Operating System classifier — say what is supported"
        assert "Operating System :: OS Independent" not in claimed, (
            "over-claims: risqlet guardrails is POSIX-only")
        for runner, classifier in (
            ("ubuntu", "Operating System :: POSIX :: Linux"),
            ("macos", "Operating System :: MacOS"),
            ("windows", "Operating System :: Microsoft :: Windows"),
        ):
            in_ci = any(r.startswith(runner) for r in runners)
            assert in_ci == (classifier in claimed), (
                f"{classifier!r} claimed={classifier in claimed} but CI runs "
                f"{runner}={in_ci} — the claim and the evidence disagree")

    def test_author_has_contact(self):
        author = pyproject()["project"]["authors"][0]
        assert author.get("name") and author.get("email")


class TestGovernanceFiles:
    @pytest.mark.parametrize("name", [
        "LICENSE", "LICENSE-CATALOG", "NOTICE", "CONTRIBUTING.md",
        "SECURITY.md", "CHANGELOG.md", "RELEASING.md", "CLEAN-ROOM.md",
        "docs/release-checklist.md", "src/risqlet/py.typed",
        ".github/workflows/release.yml",
    ])
    def test_file_exists(self, name):
        assert (ROOT / name).exists(), f"{name} is missing"

    def test_notice_has_mitre_and_runtime_pointer(self):
        notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        assert "MITRE" in notice
        assert "risqlet catalog licenses" in notice

    def test_contributing_has_clean_room_affirmation(self):
        assert "CLEAN-ROOM.md" in (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        assert "without consulting licensed source text" in read_utf8(ROOT / "CONTRIBUTING.md")

    def test_changelog_has_010(self):
        assert "[0.1.0]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    def test_release_workflow_is_manual_multimode_token(self):
        wf = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        # manual dispatch only — a tag push must not publish
        assert "workflow_dispatch:" in wf
        assert "on:\n  push:" not in wf
        # three selectable modes
        for mode in ("gh-draft", "gh-release", "pypi"):
            assert mode in wf, f"missing mode {mode}"
        # token-based PyPI auth, OIDC removed
        assert "PYPI_API_TOKEN" in wf
        assert "id-token: write" not in wf
        # artifacts attached to the GitHub release
        assert "gh release create" in wf and "dist/*" in wf

    def test_release_workflow_is_valid_yaml(self):
        from ruamel.yaml import YAML

        YAML(typ="safe").load((ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))


class CleanInstall(NamedTuple):
    exe: str      # the installed `risqlet` console script
    py: str       # the venv's python, for asserting where imports resolve
    work: Path    # a cwd outside the repo
    bin_dir: Path # prepended to PATH so bare `risqlet` means *this* install


def build_wheel(out_dir: Path) -> str:
    result = subprocess.run(
        ["uv", "build", "--wheel", "-o", str(out_dir)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    return sorted(glob.glob(str(out_dir / "*.whl")))[-1]


@pytest.fixture(scope="module")
def clean_install(tmp_path_factory):
    """The wheel, installed into a fresh venv with no dev deps and no source tree.

    Every other test runs against an editable install of `src/` — the one
    configuration no user has. This is the artifact users actually get: it catches a
    broken console script or package data that never made it into the wheel, neither
    of which any source-tree test can see.

    Returns (risqlet_exe, workdir) where workdir is *outside* the repo, so an import
    the wheel is missing cannot be satisfied by the checkout.
    """
    base = tmp_path_factory.mktemp("cleaninstall")
    wheel = build_wheel(base / "dist")
    venv = base / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                   capture_output=True)
    bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
    py = bin_dir / ("python.exe" if os.name == "nt" else "python")
    r = subprocess.run([str(py), "-m", "pip", "install", "--quiet", wheel],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    exe = bin_dir / ("risqlet.exe" if os.name == "nt" else "risqlet")
    assert exe.exists(), f"console script missing from the wheel install: {exe}"
    work = base / "work"
    work.mkdir()
    return CleanInstall(exe=str(exe), py=str(py), work=work, bin_dir=bin_dir)


def run_installed(inst: "CleanInstall", *args: str) -> subprocess.CompletedProcess:
    """Run the installed CLI the way a user's shell would.

    The venv's bin dir goes first on PATH deliberately. risqlet shells out to a bare
    `risqlet` when it verifies the setup hook, so without this the hook would be
    verified against whatever risqlet the *developer* has installed — an editable
    checkout, or a stale `uv tool install` — and this fixture would silently stop
    testing the wheel. A user who pip-installs gets this install on PATH; so does
    this test.
    """
    env = dict(os.environ)
    env["PATH"] = str(inst.bin_dir) + os.pathsep + env["PATH"]
    return subprocess.run([inst.exe, *args], cwd=inst.work, env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


@pytest.mark.slow
class TestCleanInstall:
    """spec: release-readiness / cross-platform-support — the wheel must run.

    Inspecting a wheel's namelist proves it contains paths, not that it works.
    """

    def test_console_script_runs(self, clean_install):
        r = run_installed(clean_install, "--help")
        assert r.returncode == 0, r.stderr
        assert "risqlet" in r.stdout

    def test_imports_from_the_wheel_not_the_source_tree(self, clean_install):
        """The thing under test must be the wheel, not the checkout beside it."""
        r = subprocess.run(
            [clean_install.py, "-c", "import risqlet; print(risqlet.__file__)"],
            cwd=clean_install.work, capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert r.returncode == 0, r.stderr
        resolved = Path(r.stdout.strip()).resolve()
        assert not resolved.is_relative_to(ROOT / "src"), (
            f"imported risqlet from the source tree ({resolved}) — this fixture "
            f"would not catch package-data or entry-point bugs")

    def test_agent_adapters_ship(self, clean_install):
        """setup reads setup/adapters/*.yaml — force-included package data."""
        proj = clean_install.work / "adapters"
        proj.mkdir(exist_ok=True)
        r = run_installed(clean_install, "setup", "--agents", "claude", "--dry-run",
                          "--json", "--dir", str(proj))
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["actions"], "no adapter actions planned"

    def test_cli_emits_utf8_not_the_console_code_page(self, clean_install):
        """spec: cross-platform-support — stdout is a machine interface.

        Caught by the Windows CI leg, not by reasoning: risqlet's own stdout was
        encoded in the host locale, so on Windows an em-dash in `--help` went out as
        cp1252 byte 0x97 and any UTF-8 consumer — an agent parsing `--json`, or the
        MCP stdio transport — failed to decode it. Asserts raw bytes, because
        `text=True` would decode them and hide exactly what is being tested.
        """
        env = dict(os.environ)
        env["PATH"] = str(clean_install.bin_dir) + os.pathsep + env["PATH"]
        r = subprocess.run([clean_install.exe, "--help"], cwd=clean_install.work,
                           env=env, capture_output=True, timeout=120)  # bytes, not text
        assert r.returncode == 0
        r.stdout.decode("utf-8")  # raises UnicodeDecodeError if we emitted cp1252
        assert b"\x97" not in r.stdout  # cp1252's em-dash byte

    def test_ci_templates_ship(self, clean_install):
        """ci init reads ci/templates/*.json — force-included package data."""
        r = run_installed(clean_install, "ci", "init", "--target", "claude-hooks")
        assert r.returncode == 0, r.stderr
        assert "risqlet check --hook-input claude" in r.stdout

    def test_catalog_packs_ship(self, clean_install):
        r = run_installed(clean_install, "catalog", "list", "--json")
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout), "no catalog entries from the installed wheel"

    def test_bundled_skills_ship(self, clean_install):
        target = clean_install.work / "skills-out"
        r = run_installed(clean_install, "skills", "install", "--target", str(target))
        assert r.returncode == 0, r.stderr
        assert (target / "risk-analysis").exists()

    def test_register_lifecycle_works_from_the_wheel(self, clean_install):
        proj = clean_install.work / "reg"
        proj.mkdir(exist_ok=True)
        assert run_installed(clean_install, "init", "--dir", str(proj)).returncode == 0
        r = run_installed(clean_install, "validate", "--dir", str(proj))
        assert r.returncode == 0, r.stderr

    @pytest.mark.parametrize("agent", sorted(ADAPTER_IDS))
    def test_every_adapter_sets_up_from_the_wheel(self, clean_install, agent):
        """spec: cross-platform-support — agent setup is smoke-tested per platform.

        The Windows hook bug lived here: setup reported success while silently
        skipping the hook. A legitimate skip (Codex's MCP is global-only, Copilot
        has no hooks) is fine; a skip because something failed verification is the
        bug, so this asserts on the *reason*, not on skips being empty.
        """
        proj = clean_install.work / f"agent-{agent}"
        proj.mkdir(exist_ok=True)
        r = run_installed(clean_install, "setup", "--agents", agent, "--yes", "--json",
                          "--dir", str(proj))
        assert r.returncode == 0, f"setup failed for {agent}: {r.stderr}"
        payload = json.loads(r.stdout)
        bad = [s for s in payload["skipped"] if "verification" in s.get("reason", "")]
        assert not bad, f"{agent}: component skipped by a failed verification: {bad}"
        assert payload["installed"] > 0, f"{agent}: setup installed nothing"

    def test_installed_hook_command_runs_from_the_wheel(self, clean_install):
        """The setup hook must work from the shipped artifact, on this platform."""
        proj = clean_install.work / "hookproj"
        proj.mkdir(exist_ok=True)
        assert run_installed(clean_install, "init", "--dir", str(proj)).returncode == 0
        r = run_installed(clean_install, "setup", "--agents", "claude", "--components", "hooks",
                          "--yes", "--json", "--dir", str(proj))
        assert r.returncode == 0, r.stderr
        payload = json.loads(r.stdout)
        assert payload["skipped"] == [], f"hook was skipped: {payload['skipped']}"
        settings = json.loads((proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmd = [h["command"] for e in settings["hooks"]["PostToolUse"]
               for h in e["hooks"]][0]
        # run the command exactly as written into settings.json, resolving `risqlet`
        # off PATH the way the agent's hook runner will
        argv = shlex.split(cmd)
        assert argv[0] == "risqlet"
        env = dict(os.environ)
        env["PATH"] = str(clean_install.bin_dir) + os.pathsep + env["PATH"]
        proc = subprocess.run([*argv, "--dir", str(proj)], env=env,
                              cwd=clean_install.work,
                              input='{"tool_input": {"file_path": "src/x.py"}}',
                              capture_output=True, text=True, encoding="utf-8", timeout=120)
        assert proc.returncode == 0, proc.stderr


class TestWheelContents:
    def test_wheel_ships_license_notice_and_data(self, tmp_path):
        wheel = build_wheel(tmp_path / "dist")
        names = zipfile.ZipFile(wheel).namelist()
        assert any(n.endswith("py.typed") for n in names)
        assert any("catalog/packs/" in n for n in names)
        assert any("guardrails/templates/" in n for n in names)
        assert any("data/skills/" in n for n in names)
        # LICENSE, LICENSE-CATALOG, and NOTICE ship in the wheel metadata dir
        assert any(n.endswith("licenses/LICENSE") for n in names)
        assert any(n.endswith("LICENSE-CATALOG") for n in names)
        assert any(n.endswith("NOTICE") for n in names)

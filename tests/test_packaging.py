"""Release-readiness checks: packaging metadata, governance files, shipped assets."""

import glob
import subprocess
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


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
        notice = (ROOT / "NOTICE").read_text()
        assert "MITRE" in notice
        assert "risqlet catalog licenses" in notice

    def test_contributing_has_clean_room_affirmation(self):
        assert "CLEAN-ROOM.md" in (ROOT / "CONTRIBUTING.md").read_text()
        assert "without consulting licensed source text" in (ROOT / "CONTRIBUTING.md").read_text()

    def test_changelog_has_010(self):
        assert "[0.1.0]" in (ROOT / "CHANGELOG.md").read_text()

    def test_release_workflow_is_tag_triggered_trusted_publishing(self):
        wf = (ROOT / ".github/workflows/release.yml").read_text()
        assert "tags:" in wf and 'v*' in wf
        assert "id-token: write" in wf  # OIDC trusted publishing, no stored token


class TestWheelContents:
    def test_wheel_ships_license_notice_and_data(self, tmp_path):
        out = tmp_path / "dist"
        result = subprocess.run(
            ["uv", "build", "--wheel", "-o", str(out)],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        wheel = sorted(glob.glob(str(out / "*.whl")))[-1]
        names = zipfile.ZipFile(wheel).namelist()
        assert any(n.endswith("py.typed") for n in names)
        assert any("catalog/packs/" in n for n in names)
        assert any("guardrails/templates/" in n for n in names)
        assert any("data/skills/" in n for n in names)
        # LICENSE, LICENSE-CATALOG, and NOTICE ship in the wheel metadata dir
        assert any(n.endswith("licenses/LICENSE") for n in names)
        assert any(n.endswith("LICENSE-CATALOG") for n in names)
        assert any(n.endswith("NOTICE") for n in names)

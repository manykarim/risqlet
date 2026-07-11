"""CLI behavior tests (spec: risqlet-cli)."""

import json

from risqlet.cli import main


class TestInit:
    def test_fresh_init_validates_clean(self, tmp_path, capsys):
        assert main(["init", "--dir", str(tmp_path)]) == 0
        assert main(["validate", "--dir", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "PASS" in out

    def test_init_refuses_existing(self, tmp_path, capsys):
        assert main(["init", "--dir", str(tmp_path)]) == 0
        (tmp_path / ".risqlet" / "register" / "R-0001.yaml").write_text("id: R-0001\n")
        assert main(["init", "--dir", str(tmp_path)]) == 1
        assert "refusing to overwrite" in capsys.readouterr().err

    def test_init_json(self, tmp_path, capsys):
        assert main(["init", "--dir", str(tmp_path), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["created"].endswith(".risqlet")


class TestValidate:
    def test_json_report(self, populated_register, capsys):
        root = str(populated_register.root)
        assert main(["validate", "--dir", root, "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["pass"] is True
        assert isinstance(payload["findings"], list)

    def test_failure_exit_code(self, populated_register, capsys):
        (populated_register.register_dir / "R-0003.yaml").write_text("id: nope\n")
        assert main(["validate", "--dir", str(populated_register.root)]) == 1
        assert "FAIL" in capsys.readouterr().out

    def test_missing_register(self, tmp_path, capsys):
        assert main(["validate", "--dir", str(tmp_path)]) == 1
        assert "no .risqlet" in capsys.readouterr().err


class TestScore:
    def test_requires_target(self, populated_register, capsys):
        assert main(["score", "--dir", str(populated_register.root)]) == 1
        assert "R-0001" in capsys.readouterr().err  # usage hint

    def test_score_all(self, populated_register, capsys):
        assert main(["score", "--all", "--dir", str(populated_register.root), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload == {"updated": 2, "findings": []}

    def test_score_single(self, populated_register, capsys):
        assert main(["score", "R-0002", "--dir", str(populated_register.root)]) == 0
        assert "updated 1 file(s)" in capsys.readouterr().out


class TestExport:
    def test_stdout_default(self, populated_register, capsys):
        assert main(["export", "--fmt", "strategy-md",
                     "--dir", str(populated_register.root)]) == 0
        assert "# Test Strategy: demo" in capsys.readouterr().out

    def test_output_file(self, populated_register, tmp_path, capsys):
        target = tmp_path / "out" / "strategy.md"
        assert main(["export", "--fmt", "strategy-md", "-o", str(target),
                     "--dir", str(populated_register.root)]) == 0
        assert target.read_text().startswith("# Test Strategy")

    def test_all_formats(self, populated_register, capsys):
        for fmt in ("register-yaml", "strategy-md", "trace-matrix-csv"):
            assert main(["export", "--fmt", fmt, "--dir", str(populated_register.root)]) == 0

    def test_byte_identical_repeat(self, populated_register, capsys):
        main(["export", "--fmt", "strategy-md", "--dir", str(populated_register.root)])
        first = capsys.readouterr().out
        main(["export", "--fmt", "strategy-md", "--dir", str(populated_register.root)])
        assert capsys.readouterr().out == first

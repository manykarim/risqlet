"""End-to-end smoke test: the canonical workflow later changes build on.

init -> author risks + scores + mitigation -> score --all -> human decisions
-> validate -> all three exports. Everything via the CLI entry point.
"""

import json

from risqlet.cli import main
from risqlet.store import Store
from tests.conftest import RISK_1, RISK_2, append_raw_event


def test_full_workflow(tmp_path, capsys):
    root = str(tmp_path)

    # 1. init
    assert main(["init", "--dir", root, "--project", "pos-terminal"]) == 0
    capsys.readouterr()  # drain init output

    # 2. an agent authors two risks (proposed) with scores and one mitigation
    store = Store(tmp_path / ".risqlet")
    (store.register_dir / "R-0001.yaml").write_text(RISK_1)
    (store.register_dir / "R-0002.yaml").write_text(RISK_2)

    # 3. deterministic scoring
    assert main(["score", "--all", "--dir", root, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["updated"] == 2

    # 4. humans select aspects, advance the phase, and review R-0001
    cfg = store.load_config_raw()
    cfg["aspects"] = [
        {"id": "iso25010.reliability", "rank": 1,
         "rationale": "payment flow correctness is existential"},
        {"id": "iso25010.security", "rank": 2, "rationale": "PCI scope"},
    ]
    cfg["phase"] = "score"
    store.save_config_raw(cfg)
    for from_phase, to_phase in [("context", "aspects"), ("aspects", "elicit"),
                                 ("elicit", "score")]:
        append_raw_event(store, ts="2026-07-10T12:00:00Z", type="phase_change",
                         principal="human:many", note="", to=to_phase,
                         **{"from": from_phase})
    append_raw_event(store, ts="2026-07-10T12:30:00Z", type="status_change",
                     risk="R-0001", principal="human:many",
                     note="confirmed in review", to="reviewed", **{"from": "proposed"})
    path = store.register_dir / "R-0001.yaml"
    path.write_text(path.read_text().replace("status: proposed", "status: reviewed"))

    # 5. the gate command passes with warnings only (R-0002 is speculative)
    assert main(["validate", "--dir", root, "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["pass"] is True and report["errors"] == 0

    # 6. all exports render
    out_dir = tmp_path / "exports"
    for fmt, name in [("register-yaml", "register.yaml"),
                      ("strategy-md", "strategy.md"),
                      ("trace-matrix-csv", "trace.csv")]:
        assert main(["export", "--fmt", fmt, "-o", str(out_dir / name),
                     "--dir", root]) == 0

    strategy = (out_dir / "strategy.md").read_text()
    assert "# Test Strategy: pos-terminal" in strategy
    assert "iso25010.reliability" in strategy
    assert "M-0001" in strategy
    assert "What this does not cover" in strategy

    # 7. an agent trying to self-advance a risk is caught by the gate
    append_raw_event(store, ts="2026-07-10T13:00:00Z", type="status_change",
                     risk="R-0002", principal="agent:eager-helper",
                     note="", to="reviewed", **{"from": "proposed"})
    path2 = store.register_dir / "R-0002.yaml"
    path2.write_text(path2.read_text().replace("status: proposed", "status: reviewed"))
    assert main(["validate", "--dir", root]) == 1
    assert "human principal" in capsys.readouterr().out

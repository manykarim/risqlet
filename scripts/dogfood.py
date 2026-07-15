#!/usr/bin/env python3
"""Dogfooding experiment harness.

Runs risqlet skills against real target repos via headless Claude Code and
captures the results as experiment artifacts. Never commits to targets;
`cleanup` restores them to their recorded baseline.

Usage:
  python scripts/dogfood.py prepare  <target-dir>
  python scripts/dogfood.py run      <target-dir> <experiment> [--timeout SECS]
  python scripts/dogfood.py collect  <target-dir> <experiment>
  python scripts/dogfood.py cleanup  <target-dir>
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = REPO_ROOT / "scripts" / "prompts"
EXPERIMENTS_DIR = REPO_ROOT / "docs" / "experiments"

STATEMENT_RE = re.compile(r"because\s.{15,}?\bcaus(?:e|ing)\b", re.I | re.S)

ALLOWED_TOOLS = [
    "Read", "Grep", "Glob", "LS",
    "Bash(risqlet:*)",
    "Bash(git log:*)", "Bash(git diff:*)", "Bash(git status:*)", "Bash(git show:*)",
    "Write", "Edit",
]


def sh(
    cmd: list[str], cwd: Path | None = None, timeout: int | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def target_slug(target: Path) -> str:
    return target.resolve().name


def baseline_path(target: Path) -> Path:
    directory = EXPERIMENTS_DIR / target_slug(target)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "git-baseline.txt"


def git_porcelain(target: Path) -> str:
    result = sh(["git", "status", "--porcelain"], cwd=target)
    if result.returncode != 0:
        raise SystemExit(f"{target} is not a git repo: {result.stderr}")
    return result.stdout


# -- prepare -----------------------------------------------------------------

def cmd_prepare(args) -> int:
    target = Path(args.target).resolve()
    baseline_path(target).write_text(git_porcelain(target))

    install = sh(["uv", "tool", "install", "--force", "--reinstall", "--no-cache",
                  str(REPO_ROOT)])
    if install.returncode != 0:
        raise SystemExit(f"uv tool install failed:\n{install.stderr}")
    probe = sh(["risqlet", "skills", "list"])
    if probe.returncode != 0:
        raise SystemExit(f"risqlet not invocable after install:\n{probe.stderr}")

    skills = sh(["risqlet", "skills", "install", "--force",
                 "--target", str(target / ".claude" / "skills")])
    if skills.returncode != 0:
        raise SystemExit(f"skills install failed:\n{skills.stderr}")
    print(f"prepared {target}\n{skills.stdout}")
    return 0


# -- run -----------------------------------------------------------------------

def cmd_run(args) -> int:
    target = Path(args.target).resolve()
    prompt_file = PROMPTS_DIR / f"{args.experiment}.md"
    if not prompt_file.exists():
        raise SystemExit(f"no prompt file {prompt_file}")
    out_dir = EXPERIMENTS_DIR / target_slug(target) / args.experiment
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "claude", "-p", prompt_file.read_text(),
        "--permission-mode", "acceptEdits",
        "--output-format", "json",
        "--allowedTools", *ALLOWED_TOOLS,
    ]
    started = time.time()
    timed_out = False
    try:
        result = sh(cmd, cwd=target, timeout=args.timeout)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        def _text(v):
            return v.decode() if isinstance(v, bytes) else (v or "")

        stdout, stderr = _text(exc.stdout), _text(exc.stderr)
        code = -1
    elapsed = round(time.time() - started, 1)

    (out_dir / "raw-output.json").write_text(stdout or "")
    (out_dir / "stderr.txt").write_text(stderr or "")
    meta = {"experiment": args.experiment, "target": str(target),
            "elapsed_seconds": elapsed, "exit_code": code, "timed_out": timed_out}
    try:
        payload = json.loads(stdout)
        meta["result_preview"] = (payload.get("result") or "")[:2000]
        for key in ("total_cost_usd", "num_turns", "duration_ms", "is_error"):
            if key in payload:
                meta[key] = payload[key]
        (out_dir / "result.md").write_text(payload.get("result") or "")
    except (json.JSONDecodeError, AttributeError):
        meta["parse_error"] = True
    (out_dir / "run-meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return 0 if code == 0 else 1


# -- collect ---------------------------------------------------------------------

def _load_yaml(path: Path):
    from ruamel.yaml import YAML

    with path.open(encoding="utf-8") as f:
        return YAML(typ="safe").load(f)


def cmd_collect(args) -> int:
    target = Path(args.target).resolve()
    out_dir = EXPERIMENTS_DIR / target_slug(target) / args.experiment
    out_dir.mkdir(parents=True, exist_ok=True)
    risqlet_dir = target / ".risqlet"
    copy_root = out_dir / "register-copy"
    register_copy = copy_root / ".risqlet"
    if copy_root.exists():
        shutil.rmtree(copy_root)
    if not risqlet_dir.exists():
        (out_dir / "metrics.json").write_text(json.dumps({"register": False}))
        print("no .risqlet/ produced")
        return 1
    copy_root.mkdir(parents=True)
    shutil.copytree(risqlet_dir, register_copy)

    validate = sh(["risqlet", "validate", "--json", "--dir", str(copy_root)])
    try:
        report = json.loads(validate.stdout)
    except json.JSONDecodeError:
        report = {"pass": False, "unparseable": validate.stdout[-500:]}

    risks = []
    for risk_file in sorted((register_copy / "register").glob("*.yaml")):
        data = _load_yaml(risk_file) or {}
        risks.append(data)

    evidence_checks = []
    for risk in risks:
        for ev in (risk.get("elicited_by") or {}).get("evidence") or []:
            # evidence items may carry annotations: "path (note)" or "path:123"
            candidate = re.sub(r"\s*\(.*\)$", "", str(ev)).strip()
            candidate = re.split(r"[:#\s]", candidate, maxsplit=1)[0]
            looks_like_path = "/" in candidate or candidate.endswith(
                (".py", ".rs", ".md", ".toml", ".robot", ".java", ".yaml"))
            exists = (target / candidate).exists() if looks_like_path else None
            evidence_checks.append({"risk": risk.get("id"), "evidence": ev,
                                    "checked": looks_like_path, "exists": exists})
    missing = [e for e in evidence_checks if e["checked"] and e["exists"] is False]

    speculative = [r.get("id") for r in risks
                   if not ((r.get("elicited_by") or {}).get("evidence"))]
    bad_statements = [r.get("id") for r in risks
                      if not STATEMENT_RE.search(str(r.get("statement", "")))]
    with_prompt_ref = [r.get("id") for r in risks
                       if (r.get("elicited_by") or {}).get("prompt_ref")]

    metrics = {
        "register": True,
        "risk_count": len(risks),
        "validate_pass": report.get("pass"),
        "validate_errors": report.get("errors"),
        "validate_warnings": report.get("warnings"),
        "speculative": speculative,
        "speculative_ratio": round(len(speculative) / len(risks), 2) if risks else None,
        "statement_format_misses": bad_statements,
        "prompt_ref_coverage": round(len(with_prompt_ref) / len(risks), 2) if risks else None,
        "evidence_items": len(evidence_checks),
        "evidence_missing_paths": missing,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (out_dir / "validate-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(metrics, indent=2))
    return 0


# -- cleanup ----------------------------------------------------------------------

def cmd_cleanup(args) -> int:
    target = Path(args.target).resolve()
    for path in [target / ".risqlet",
                 target / ".claude" / "skills" / "risk-analysis",
                 target / ".claude" / "skills" / "risk-quickscan"]:
        if path.exists():
            shutil.rmtree(path)
            print(f"removed {path}")
    skills_dir = target / ".claude" / "skills"
    if skills_dir.exists() and not any(skills_dir.iterdir()):
        skills_dir.rmdir()
        claude_dir = target / ".claude"
        if claude_dir.exists() and not any(claude_dir.iterdir()):
            claude_dir.rmdir()

    baseline = baseline_path(target)
    before = baseline.read_text() if baseline.exists() else ""
    after = git_porcelain(target)
    if after != before:
        print("RESIDUE DETECTED — target differs from baseline:")
        before_set, after_set = set(before.splitlines()), set(after.splitlines())
        for line in sorted(after_set - before_set):
            print(f"  + {line}")
        for line in sorted(before_set - after_set):
            print(f"  - {line}")
        return 1
    print("target clean (matches baseline)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("prepare", cmd_prepare), ("cleanup", cmd_cleanup)]:
        p = sub.add_parser(name)
        p.add_argument("target")
        p.set_defaults(func=fn)
    for name, fn in [("run", cmd_run), ("collect", cmd_collect)]:
        p = sub.add_parser(name)
        p.add_argument("target")
        p.add_argument("experiment")
        if name == "run":
            p.add_argument("--timeout", type=int, default=900)
        p.set_defaults(func=fn)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

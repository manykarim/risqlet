"""risqlet command-line interface — thin argparse wiring over the core layers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from risqlet.exports.renderers import FORMATS, ExportError, render
from risqlet.findings import Finding
from risqlet.scoring import score_risks
from risqlet.store import Store, StoreError, find_register, init_register
from risqlet.validate import validate_register


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dir", type=Path, default=None,
                        help="project or .risqlet directory (default: walk up from cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")


def _store(args) -> Store:
    return Store(find_register(explicit=args.dir))


def _print_findings(findings: list[Finding]) -> None:
    for f in findings:
        print(f"{f.severity}: {f.file} [{f.field}] {f.message}")


def cmd_init(args) -> int:
    target = args.dir or Path.cwd()
    try:
        risqlet = init_register(target, args.project)
    except StoreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"created": str(risqlet)}))
    else:
        print(f"initialized register at {risqlet}")
    return 0


def cmd_validate(args) -> int:
    report = validate_register(_store(args))
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_findings(report.findings)
        summary = report.to_dict()
        print(f"{'PASS' if report.passed else 'FAIL'} "
              f"({summary['errors']} errors, {summary['warnings']} warnings)")
    return 0 if report.passed else 1


def cmd_status(args) -> int:
    from risqlet.status import build_status, format_status

    report = build_status(_store(args))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_status(report))
    return 0


def cmd_score(args) -> int:
    if not args.risk_id and not args.all:
        print("error: give a risk id (e.g. R-0001) or --all", file=sys.stderr)
        return 1
    updated, findings = score_risks(_store(args), args.risk_id)
    if args.json:
        print(json.dumps({
            "updated": updated,
            "findings": [f.to_dict() for f in findings],
        }, indent=2))
    else:
        _print_findings(findings)
        print(f"updated {updated} file(s)")
    return 0 if not findings else 1


def cmd_export(args) -> int:
    try:
        output = render(_store(args), args.fmt)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8", newline="\n")
        if args.json:
            print(json.dumps({"format": args.fmt, "written": str(args.output)}))
        else:
            print(f"wrote {args.output}")
    elif args.json:
        print(json.dumps({"format": args.fmt, "content": output}))
    else:
        sys.stdout.write(output)
    return 0


def _catalog_packs(args):
    """Load packs with register context when available (user packs), else packaged only."""
    from risqlet.catalog import load_available

    try:
        store = _store(args)
    except StoreError:
        store = None
    return load_available(store)


def cmd_catalog_list(args) -> int:
    packs = _catalog_packs(args)
    if args.pack:
        if args.pack not in packs:
            print(f"error: no catalog pack named {args.pack!r}", file=sys.stderr)
            return 1
        packs = {args.pack: packs[args.pack]}
    entries = [
        {"id": f"{pack.id}.{e.slug}", "kind": str(e.kind), "summary": e.summary}
        for pack in packs.values()
        for e in pack.entries
    ]
    if args.json:
        print(json.dumps({"entries": entries}, indent=2))
    else:
        for e in entries:
            print(f"{e['id']}  [{e['kind']}]  {e['summary']}")
    return 0


def cmd_catalog_show(args) -> int:
    from risqlet.catalog import resolve_entry

    packs = _catalog_packs(args)
    entry = resolve_entry(args.entry_id, packs)
    if entry is None:
        print(f"error: no catalog entry {args.entry_id!r}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(entry.model_dump(mode="json"), indent=2))
        return 0
    print(f"{args.entry_id} — {entry.name} [{entry.kind}]")
    print(f"\n{entry.summary}\n")
    for prompt in entry.prompts:
        print(f"  ? {prompt}")
    if entry.words:
        print(f"\n  words: {', '.join(entry.words)}")
    if entry.tags:
        print(f"\n  tags: {', '.join(entry.tags)}")
    if entry.related:
        print(f"  related: {', '.join(entry.related)}")
    print(f"  provenance: {entry.provenance}")
    pack_id = args.entry_id.split(".", 1)[0]
    pack = packs.get(pack_id)
    if pack is not None and getattr(pack, "notice", ""):
        print(f"  notice: {pack.notice}")
    return 0


def cmd_catalog_licenses(args) -> int:
    packs = _catalog_packs(args)
    rows = [
        {"id": p.id, "title": p.title, "license": p.license,
         "attribution": " ".join(p.attribution.split()),
         "notice": " ".join((getattr(p, "notice", "") or "").split())}
        for p in sorted(packs.values(), key=lambda p: p.id)
    ]
    if args.json:
        print(json.dumps({"packs": rows}, indent=2))
    else:
        for r in rows:
            print(f"{r['id']}  [{r['license']}]  {r['title']}")
            print(f"    attribution: {r['attribution']}")
            if r["notice"]:
                print(f"    notice: {r['notice']}")
    return 0


def cmd_catalog_search(args) -> int:
    from risqlet.catalog import search

    packs = _catalog_packs(args)
    results = search(packs, args.terms)
    if args.json:
        print(json.dumps({
            "results": [{"id": rid, "summary": e.summary, "hits": hits}
                        for rid, e, hits in results]
        }, indent=2))
    else:
        for rid, e, _hits in results:
            print(f"{rid}  {e.summary}")
    return 0


def cmd_skills_list(args) -> int:
    from risqlet.skills import SkillsError, list_skills

    try:
        skills = list_skills()
    except SkillsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({
            "skills": [{"name": s.name, "description": s.description} for s in skills]
        }, indent=2))
    else:
        for s in skills:
            print(f"{s.name}  —  {s.description}")
    return 0


def cmd_skills_install(args) -> int:
    from risqlet.skills import SkillsError, install

    try:
        installed = install(args.skills or None, args.target, force=args.force)
    except SkillsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({
            "installed": [{"name": n, "path": str(p)} for n, p in installed]
        }, indent=2))
    else:
        for name, path in installed:
            print(f"installed {name} -> {path}")
    return 0


def cmd_trace_ingest(args) -> int:
    import datetime

    from risqlet.trace import TraceError, ingest

    ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        result = ingest(_store(args), [Path(p) for p in args.paths], ts)
    except TraceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"ingested {result['ingested']} result(s): " +
              ", ".join(f"{k}={v}" for k, v in result["per_source"].items()))
    return 0


def cmd_trace_status(args) -> int:
    from risqlet.trace import trace_report

    report = trace_report(_store(args))
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    if not report["results_present"]:
        print("no test results ingested yet (risqlet trace ingest <report.xml>)")
    for risk in report["risks"]:
        states = (", ".join(f"{m['id']}:{m['state']}" for m in risk["mitigations"])
                  or "no mitigations")
        print(f"{risk['risk']} [{risk['status']}] {risk['rollup']} — {states}")
    if report["detection_notes"]:
        print("\ndetection evidence:")
        for note in report["detection_notes"]:
            print(f"  ! {note}")
    return 0


def cmd_dedupe(args) -> int:
    from risqlet.ensemble import find_clusters

    clusters = find_clusters(_store(args))
    if args.json:
        print(json.dumps({"clusters": [c.to_dict() for c in clusters]}, indent=2))
    elif not clusters:
        print("no near-duplicate clusters found")
    else:
        for cluster in clusters:
            print(f"cluster: {', '.join(cluster.members)}  "
                  f"(suggested survivor: {cluster.suggested_survivor})")
            for pair, score in cluster.pairs.items():
                print(f"  {pair}: {score}")
        print("\nreview each cluster; merge true duplicates with: "
              "risqlet merge <survivor> <duplicate...>")
    return 0


def cmd_merge(args) -> int:
    from risqlet.ensemble import EnsembleError, merge

    try:
        result = merge(_store(args), args.survivor, args.duplicates)
    except EnsembleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"merged {', '.join(result['merged'])} into {result['survivor']} "
              f"({result['moved_mitigations']} mitigation(s) moved) — run risqlet validate")
    return 0


def cmd_diff(args) -> int:
    from risqlet.changeset import ChangesetError, build_diff

    stdin_text = None
    if not args.files and args.stdin:
        stdin_text = sys.stdin.read()
    try:
        report = build_diff(_store(args), base=args.base, files=args.files,
                            stdin_text=stdin_text)
    except ChangesetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"changed files: {report['changed_files']} "
              f"(considered {report['considered_files']}, "
              f"excluded {report['excluded_paths']})")
        if not report["touched"]:
            print("no tracked risks touched by this change")
        for t in report["touched"]:
            reasons = "; ".join(r["reason"] for r in t["reasons"])
            print(f"  {t['risk']} [{t['status']}] {t['priority']} ({t['confidence']}) "
                  f"— {reasons}")
            print(f"    -> {t['suggested_action']}")
        if report["untouched_high_priority"]:
            print("still worth attention (untouched, high priority): " +
                  ", ".join(u["risk"] for u in report["untouched_high_priority"]))
    return 0


def cmd_check(args) -> int:
    if args.hook_input:
        return _cmd_check_hook(args)

    from risqlet.changeset import ChangesetError, run_check

    stdin_text = None
    if not args.files and args.stdin:
        stdin_text = sys.stdin.read()
    try:
        report = run_check(_store(args), base=args.base, files=args.files,
                          stdin_text=stdin_text)
    except ChangesetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _print_check_report(report, args.json)
    return report["exit"]


def _print_check_report(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print(f"gate mode: {report['mode']} — {len(report['flagged'])} flagged")
        for f in report["flagged"]:
            print(f"  {f['risk']} [{f['status']}]: {f['flag']} -> {f['suggested_action']}")


def _cmd_check_hook(args) -> int:
    """Hook mode: report what the edit touched, never break the agent's loop.

    Always exits 0 — the gate's block/warn contract governs CI, not an editor
    hook. Replaces the old shell hook's `2>/dev/null || true`, which is why any
    failure here is swallowed rather than surfaced.
    """
    try:
        from risqlet.changeset import parse_claude_hook_payload, run_check

        files = parse_claude_hook_payload(sys.stdin.read())
        if not files:  # no edited path in the payload — nothing to check
            return 0
        report = run_check(_store(args), base=args.base, files=files)
        _print_check_report(report, args.json)
    except Exception:
        pass
    return 0


def cmd_ci_init(args) -> int:
    from risqlet.ci import CIError, init

    target = args.dir or Path.cwd()
    try:
        result = init(args.target, target, force=args.force)
    except CIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if result.get("printed"):
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"# {args.target}: merge the following into your Claude Code settings.json\n")
            print(result["content"])
    elif args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"wrote {result['written']}")
    return 0


def cmd_guardrails_generate(args) -> int:
    from risqlet.guardrails import GuardrailError, build_plan

    try:
        plan = build_plan(_store(args))
    except GuardrailError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(plan.to_dict(), indent=2))
        return 0
    summary = plan.to_dict()["summary"]
    print(f"{summary['count']} guardrail(s): {summary['hard']} hard, {summary['soft']} soft "
          f"across {', '.join(summary['surfaces']) or 'no surfaces'}")
    for surface, items in sorted(plan.by_surface().items()):
        print(f"\n[{surface}]")
        for g in items:
            print(f"  {g.template_id} ({g.enforcement}) — risks {', '.join(g.risks)}")
    for note in plan.advisories:
        print(f"\n! {note}")
    print("\ninstall a surface with: risqlet guardrails install --target "
          "agents-md|claude-project|pre-commit|<path>")
    return 0


def cmd_guardrails_diff(args) -> int:
    from risqlet.guardrails import diff_target

    store = _store(args)
    root = Path(args.target) if args.target else store.root.parent
    report = diff_target(store, root)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for kind in ("stale", "missing", "drift"):
            for marker in report[kind]:
                print(f"{kind}: {marker}")
        if not any(report.values()):
            print("installed guardrails are in sync with the register")
    return 0


def cmd_guardrails_install(args) -> int:
    from risqlet.guardrails import GuardrailError, build_plan, install_plan

    store = _store(args)
    known = ("agents-md", "claude-project", "pre-commit")
    if args.target in known:
        target, root = args.target, (args.dir or Path.cwd())
    else:
        target, root = "path", Path(args.target)
    try:
        result = install_plan(store, build_plan(store), target, root,
                              force=args.force, verify=not args.no_verify)
    except GuardrailError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"installed {result['guardrails']} guardrail(s) -> {result['written']}")
        for sk in result.get("verify_skipped", []):
            if sk.get("forced"):
                print(f"  ! WARNING forced despite failed verification: "
                      f"{sk['template_id']} ({', '.join(sk['failed'])})")
            else:
                print(f"  skipped (failed verification): {sk['template_id']} — "
                      f"{', '.join(sk['failed'])}: {sk.get('detail', '')}")
    return 0


def cmd_guardrails_verify(args) -> int:
    from risqlet.guardrails import build_plan
    from risqlet.guardrails.engine import verify_plan

    store = _store(args)
    root = args.dir or Path.cwd()
    results = verify_plan(build_plan(store), Path(root))
    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        if not results:
            print("no executable (hook/pre-commit) guardrails to verify")
        for r in results:
            status = "OK" if r.ok else "FAIL"
            print(f"{status}  {r.template_id}")
            for c in r.checks:
                if not c.passed:
                    print(f"    ✗ {c.name}: {c.detail}")
    return 0 if all(r.ok for r in results) else 1


def _setup_print_plan(plan) -> None:
    for agent, actions in sorted(plan.by_agent().items()):
        comps = ", ".join(f"{a.component}" for a in actions)
        print(f"  {agent}: {comps}")
        for a in actions:
            print(f"      {a.component} -> {a.target}")
    for sk in plan.skipped:
        print(f"  skip {sk.agent}/{sk.component}: {sk.reason}")


def cmd_setup(args) -> int:
    import sys as _sys

    from risqlet.setup import (
        DETECT_LABELS,
        SetupError,
        apply_plan,
        build_plan,
        detect_sources,
        load_adapters,
        remove,
        status,
    )
    from risqlet.setup import interactive as _tui

    project_root = (args.dir or Path.cwd())
    adapters = load_adapters()

    if args.status:
        report = status(args.scope, project_root)
        print(json.dumps(report, indent=2) if args.json else _format_status(report))
        return 0
    if args.remove:
        agents = args.agents.split(",") if args.agents else None
        result = remove(args.scope, project_root, agents)
        print(json.dumps(result, indent=2) if args.json
              else f"removed {result['removed']} entrie(s); {result['remaining']} remain")
        return 0

    sources = detect_sources(adapters)
    detected = list(sources)
    interactive = (not args.agents and not args.all_detected
                   and not args.update and _sys.stdin.isatty())

    if interactive:
        # say *how* each was detected — a project dir is not an installed agent
        opts = [(aid, f"{adapters[aid].name}"
                 + (f"  ({DETECT_LABELS[sources[aid]]})" if aid in sources else ""))
                for aid in adapters]
        agent_ids = _tui.multiselect("Configure which agents?", opts, set(detected))
        if not agent_ids:
            print("nothing selected")
            return 0
        scope = _tui.choose("Scope?", ["project", "global"], args.scope)
        components = None
    else:
        if args.all_detected:
            agent_ids = detected
        elif args.agents:
            agent_ids = args.agents.split(",")
        elif args.update:
            agent_ids = sorted({e.agent for e in
                                __import__("risqlet.setup", fromlist=["read_manifest"])
                                .read_manifest(args.scope, project_root).entries})
        else:
            print("error: specify --agents, --all-detected, or run in a TTY for "
                  "interactive setup", file=_sys.stderr)
            return 1
        scope = args.scope
        components = args.components.split(",") if args.components else None

    if not agent_ids:
        print("no agents to configure" + (" (none detected)" if args.all_detected else ""))
        return 0
    try:
        plan = build_plan(adapters, agent_ids, scope, components, project_root)
    except SetupError as exc:
        print(f"error: {exc}", file=_sys.stderr)
        return 1

    if args.dry_run:
        if args.json:
            print(json.dumps({"scope": plan.scope,
                              "actions": [a.model_dump() for a in plan.actions],
                              "skipped": [s.model_dump() for s in plan.skipped]}, indent=2))
        else:
            print(f"plan ({plan.scope} scope) — dry run, nothing written:")
            _setup_print_plan(plan)
        return 0

    if interactive:
        print(f"\nplan ({scope} scope):")
        _setup_print_plan(plan)
        if not _tui.confirm("apply?"):
            print("aborted")
            return 0
    elif not args.yes:
        print("error: refusing to write without --yes (non-interactive); plan:",
              file=_sys.stderr)
        _setup_print_plan(plan)
        return 1

    result = apply_plan(plan, project_root, force=args.force, verify=not args.no_verify)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"configured {', '.join(result['agents'])} ({result['scope']} scope): "
              f"{result['installed']} item(s)")
        for sk in result["skipped"]:
            print(f"  skip {sk['agent']}/{sk['component']}: {sk['reason']}")
    return 0


def _format_status(report: dict) -> str:
    lines = [f"scope: {report['scope']}  (risqlet {report['risqlet_version'] or '?'})"]
    if not report["agents"]:
        lines.append("  nothing installed")
    for agent, items in sorted(report["agents"].items()):
        lines.append(f"  {agent}: " + ", ".join(i["component"] for i in items))
    return "\n".join(lines)


def cmd_mcp(args) -> int:
    from risqlet.mcp.server import main as mcp_main

    return mcp_main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="risqlet",
        description="Repo-native risk register with a deterministic core. "
                    "State lives in .risqlet/; semantic analysis stays with your agent.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="scaffold a .risqlet/ register")
    p_init.add_argument("--project", default=None, help="project name (default: directory name)")
    _add_common(p_init)
    p_init.set_defaults(func=cmd_init)

    p_validate = sub.add_parser(
        "validate", help="schema, integrity, lifecycle and gate checks"
    )
    _add_common(p_validate)
    p_validate.set_defaults(func=cmd_validate)

    p_status = sub.add_parser(
        "status", help="read-only session overview: phase, counts, top risks, pending gates"
    )
    _add_common(p_status)
    p_status.set_defaults(func=cmd_status)

    p_score = sub.add_parser("score", help="compute derived priorities from the policy pack")
    p_score.add_argument("risk_id", nargs="?", default=None, metavar="R-NNNN")
    p_score.add_argument("--all", action="store_true", help="score every risk")
    _add_common(p_score)
    p_score.set_defaults(func=cmd_score)

    p_export = sub.add_parser("export", help="render deterministic outputs")
    p_export.add_argument("--fmt", required=True, choices=FORMATS)
    p_export.add_argument("-o", "--output", type=Path, default=None,
                          help="write to file instead of stdout")
    _add_common(p_export)
    p_export.set_defaults(func=cmd_export)

    p_catalog = sub.add_parser(
        "catalog", help="browse the knowledge catalogs (packs of aspects, "
                        "techniques, heuristics, guidewords)"
    )
    catalog_sub = p_catalog.add_subparsers(dest="catalog_command", required=True)

    p_cat_list = catalog_sub.add_parser("list", help="list entries of loaded packs")
    p_cat_list.add_argument("--pack", default=None, help="restrict to one pack id")
    _add_common(p_cat_list)
    p_cat_list.set_defaults(func=cmd_catalog_list)

    p_cat_show = catalog_sub.add_parser("show", help="show one entry in full")
    p_cat_show.add_argument("entry_id", metavar="PACK.SLUG")
    _add_common(p_cat_show)
    p_cat_show.set_defaults(func=cmd_catalog_show)

    p_cat_licenses = catalog_sub.add_parser(
        "licenses", help="list each loaded pack's license, attribution and notice"
    )
    _add_common(p_cat_licenses)
    p_cat_licenses.set_defaults(func=cmd_catalog_licenses)

    p_cat_search = catalog_sub.add_parser(
        "search",
        help="keyword search over entries (a convenience lookup only — "
             "judging which technique fits a risk is the calling agent's job)",
    )
    p_cat_search.add_argument("terms", nargs="+")
    _add_common(p_cat_search)
    p_cat_search.set_defaults(func=cmd_catalog_search)

    p_skills = sub.add_parser(
        "skills", help="list or install the bundled agent skills (portable "
                       "SKILL.md playbooks for coding agents)"
    )
    skills_sub = p_skills.add_subparsers(dest="skills_command", required=True)

    p_sk_list = skills_sub.add_parser("list", help="show bundled skills")
    _add_common(p_sk_list)
    p_sk_list.set_defaults(func=cmd_skills_list)

    p_sk_install = skills_sub.add_parser(
        "install", help="copy skills to an agent platform's skill directory"
    )
    p_sk_install.add_argument("skills", nargs="*", metavar="SKILL",
                              help="skill names (default: all)")
    p_sk_install.add_argument(
        "--target", default="claude-project",
        help="claude-project (./.claude/skills), claude-user (~/.claude/skills), "
             "or any directory path for other agent platforms",
    )
    p_sk_install.add_argument("--force", action="store_true",
                              help="overwrite existing skill directories")
    _add_common(p_sk_install)
    p_sk_install.set_defaults(func=cmd_skills_install)

    p_diff = sub.add_parser(
        "diff", help="report which register risks a code change touches (read-only)"
    )
    p_diff.add_argument("--base", default=None, help="git base ref (default HEAD~1)")
    p_diff.add_argument("--files", nargs="*", default=None, help="explicit changed paths")
    p_diff.add_argument("--stdin", action="store_true", help="read changed paths from stdin")
    _add_common(p_diff)
    p_diff.set_defaults(func=cmd_diff)

    p_check = sub.add_parser(
        "check", help="CI gate: flag changes touching under-covered tracked risks"
    )
    p_check.add_argument("--base", default=None, help="git base ref (default HEAD~1)")
    p_check.add_argument("--files", nargs="*", default=None)
    p_check.add_argument("--stdin", action="store_true",
                         help="read newline-separated changed paths from stdin")
    p_check.add_argument("--hook-input", choices=["claude"], default=None,
                         help="read an agent hook payload (JSON) from stdin instead; "
                              "reports only, always exits 0")
    _add_common(p_check)
    p_check.set_defaults(func=cmd_check)

    p_ci = sub.add_parser("ci", help="emit CI / hooks templates for continuous re-assessment")
    ci_sub = p_ci.add_subparsers(dest="ci_command", required=True)
    p_ci_init = ci_sub.add_parser("init", help="write a CI template")
    p_ci_init.add_argument("--target", default="github",
                           help="github | gitlab | claude-hooks | a file path")
    p_ci_init.add_argument("--force", action="store_true")
    _add_common(p_ci_init)
    p_ci_init.set_defaults(func=cmd_ci_init)

    p_guard = sub.add_parser(
        "guardrails", help="generate risk-driven coding-agent guardrails "
                           "(hooks, AGENTS.md rules, permissions) from the register"
    )
    guard_sub = p_guard.add_subparsers(dest="guardrails_command", required=True)
    p_g_gen = guard_sub.add_parser("generate", help="propose a guardrail plan (read-only)")
    _add_common(p_g_gen)
    p_g_gen.set_defaults(func=cmd_guardrails_generate)
    p_g_diff = guard_sub.add_parser("diff", help="stale/missing/drift vs installed guardrails")
    p_g_diff.add_argument("--target", default=None,
                          help="install root to compare (default: the register's project dir)")
    _add_common(p_g_diff)
    p_g_diff.set_defaults(func=cmd_guardrails_diff)
    p_g_inst = guard_sub.add_parser("install", help="write guardrails for a surface (human-gated)")
    p_g_inst.add_argument("--target", default="agents-md",
                          help="agents-md | claude-project | pre-commit | a file/dir path")
    p_g_inst.add_argument("--force", action="store_true",
                          help="install even hooks that fail verification (warns)")
    p_g_inst.add_argument("--no-verify", action="store_true",
                          help="skip hook verification (CI-only; the runtime env may differ)")
    _add_common(p_g_inst)
    p_g_inst.set_defaults(func=cmd_guardrails_install)
    p_g_ver = guard_sub.add_parser(
        "verify", help="verify installed hooks in this environment (tools, syntax, behavior)")
    _add_common(p_g_ver)
    p_g_ver.set_defaults(func=cmd_guardrails_verify)

    p_trace = sub.add_parser(
        "trace", help="ingest test results and report mitigation coverage / detection evidence"
    )
    trace_sub = p_trace.add_subparsers(dest="trace_command", required=True)
    p_tr_ingest = trace_sub.add_parser("ingest", help="ingest RF output.xml or JUnit XML")
    p_tr_ingest.add_argument("paths", nargs="+", metavar="REPORT.xml")
    _add_common(p_tr_ingest)
    p_tr_ingest.set_defaults(func=cmd_trace_ingest)
    p_tr_status = trace_sub.add_parser("status", help="per-mitigation coverage + detection notes")
    _add_common(p_tr_status)
    p_tr_status.set_defaults(func=cmd_trace_status)

    p_dedupe = sub.add_parser(
        "dedupe", help="report near-duplicate risk clusters (proposes, never merges)"
    )
    _add_common(p_dedupe)
    p_dedupe.set_defaults(func=cmd_dedupe)

    p_merge = sub.add_parser(
        "merge", help="mechanically merge proposed duplicate risks into a survivor"
    )
    p_merge.add_argument("survivor", metavar="R-NNNN")
    p_merge.add_argument("duplicates", nargs="+", metavar="R-NNNN")
    _add_common(p_merge)
    p_merge.set_defaults(func=cmd_merge)

    p_setup = sub.add_parser(
        "setup", help="configure coding agents to use risqlet (skills, MCP, "
                      "instructions, hooks) — install/remove/update, project or global"
    )
    p_setup.add_argument("--agents", default=None,
                         help="comma-separated agent ids (claude,cursor,opencode,codex,"
                              "copilot,kilo,pi)")
    p_setup.add_argument("--all-detected", action="store_true",
                         help="configure every detected agent")
    p_setup.add_argument("--scope", choices=["project", "global"], default="project")
    p_setup.add_argument("--components", default=None,
                         help="comma-separated: skills,mcp,instructions,hooks,commands")
    p_setup.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    p_setup.add_argument("--yes", action="store_true", help="apply without confirmation")
    p_setup.add_argument("--force", action="store_true")
    p_setup.add_argument("--no-verify", action="store_true",
                         help="skip hook verification (CI-only)")
    p_setup.add_argument("--remove", action="store_true", help="uninstall (reverse the manifest)")
    p_setup.add_argument("--update", action="store_true", help="refresh installed agents")
    p_setup.add_argument("--status", action="store_true", help="show what is installed")
    _add_common(p_setup)
    p_setup.set_defaults(func=cmd_setup)

    p_mcp = sub.add_parser(
        "mcp", help="run the stdio MCP server (requires the risqlet[mcp] extra)"
    )
    p_mcp.set_defaults(func=cmd_mcp)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except StoreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

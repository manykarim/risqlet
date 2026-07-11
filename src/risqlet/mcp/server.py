"""Thin FastMCP wiring over the tool functions (stdio transport, stateless)."""

from __future__ import annotations

from risqlet.mcp import tools as t

INSTRUCTIONS = (
    "risqlet: repo-native risk analysis and test-strategy toolkit. All state "
    "lives in the project's .risqlet/ directory; every tool takes project_dir. "
    "Start with get_guidance(topic='overview'). You (the client) do the "
    "semantic analysis; this server only validates, computes, and stores. "
    "Decisions (record_decision) may only be recorded after an explicit "
    "human confirmation."
)


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("risqlet", instructions=INSTRUCTIONS)

    def wrap(fn):
        def inner(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except t.ToolError as exc:
                raise ValueError(str(exc)) from exc

        inner.__name__ = fn.__name__
        inner.__doc__ = fn.__doc__
        return inner

    mcp.tool(name="init_register", description=(
        "Scaffold a .risqlet/ risk register in project_dir. Refuses to overwrite "
        "an existing register."))(wrap(t.tool_init_register))
    mcp.tool(name="validate_register", description=(
        "Validate the register: schemas, referential integrity, lifecycle/gate "
        "consistency, derived-score recomputation. Run after every mutation."))(
        wrap(t.tool_validate_register))
    mcp.tool(name="score_risks", description=(
        "Deterministically compute derived priorities (e.g. RPN, action priority) "
        "for scored risks from the active policy pack. Never compute priorities "
        "yourself — factor values + rubric anchors in, priorities out."))(
        wrap(t.tool_score_risks))
    mcp.tool(name="export_register", description=(
        "Render deterministic outputs: fmt is one of register-yaml, strategy-md, "
        "trace-matrix-csv. Returns the content."))(wrap(t.tool_export_register))
    mcp.tool(name="browse_catalog", description=(
        "Browse knowledge packs (quality aspects, techniques, heuristics, "
        "guidewords). action=list (optional pack), show (entry_id), search "
        "(terms). Search is keyword lookup only — judging fit is your job."))(
        wrap(t.tool_browse_catalog))
    mcp.tool(name="get_guidance", description=(
        "Get the risk-analysis playbooks as markdown. Topics: overview, phases, "
        "elicitation, scoring, risk-writing, mitigation, quickscan. Read "
        "'overview' before starting a session."))(wrap(t.tool_get_guidance))
    mcp.tool(name="upsert_risk", description=(
        "Create or update a risk in 'proposed' status with full provenance "
        "(elicited_by.method/prompt_ref/evidence — cite real files only). "
        "Cannot change status or derived scores; those go through "
        "record_decision / score_risks."))(wrap(t.tool_upsert_risk))
    mcp.tool(name="add_mitigation", description=(
        "Add a mitigation to a risk: treatment (avoid|reduce|transfer|accept), "
        "lever (severity|occurrence|detection), barrier (prevent|detect|recover), "
        "concrete action, MANDATORY honest residual_note, optional technique_ref "
        "and tests[]."))(wrap(t.tool_add_mitigation))
    mcp.tool(name="record_decision", description=(
        "Append a human decision to the audit log and sync register state: "
        "type=status_change (risk_id, from_state, to_state) or phase_change. "
        "ONLY call after the human explicitly confirmed in conversation; "
        "principal must be 'human:<name>'. Returns a fresh validation report."))(
        wrap(t.tool_record_decision))

    return mcp


def main() -> int:
    try:
        server = build_server()
    except ImportError:
        import sys

        print(
            "error: the MCP extra is not installed — run: pip install 'risqlet[mcp]' "
            "(or: uv sync --extra mcp)",
            file=sys.stderr,
        )
        return 1
    server.run(transport="stdio")
    return 0

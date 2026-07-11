Use the risk-analysis skill's guardrails guidance
(.claude/skills/risk-analysis/references/guardrails.md — read it).

A risk register already exists in `.risqlet/` (from an earlier security-focused
session, with several access-control, tenant-isolation, and approval-integrity
risks). This is a guardrail-generation demo. Make NO code changes to the repo.

Steps:

1. `risqlet status --json` to see the register. The risks are currently
   `reviewed`. Guardrails are only generated for `accepted`/`mitigating` risks,
   so first ACCEPT the top security risks: for each, append a
   `reviewed -> accepted` status_change event to `.risqlet/events.jsonl` with
   principal `human:many` and note `"guardrails demo: scripted acceptance"`, and
   set the risk file's `status: accepted`. (This is a scripted simulated gate,
   clearly labeled — I, human:many, pre-authorize accepting the top risks.)
   Then `risqlet validate --json` must pass.

2. Each accepted security risk needs at least one mitigation whose `barrier`
   drives a guardrail — add a `prevent` or `detect` mitigation to each (real
   `residual_note`, treatment/lever/barrier), if not already present.

3. `risqlet guardrails generate --json` — report the plan: which guardrails,
   for which risks, hard vs soft, across which surfaces, and any advisory-only
   warnings for high-severity risks covered only by soft rules.

4. `risqlet guardrails install --target <a TEMP directory you create, e.g.
   ./guardrails-out>` — do NOT install into the repo's real `.claude/` or
   `AGENTS.md`. Show that the written bundle carries `risqlet:<risk>:...`
   provenance markers.

5. `risqlet guardrails diff --dir . --target ./guardrails-out` (should be in
   sync). Then reject or close ONE risk (append a status event + set status),
   and re-run diff to show that risk's guardrails reported as `stale`.

Rules: `risqlet` on PATH; only `.risqlet/` and your temp `./guardrails-out`
directory may be written; no repo source changes. Finish with the generate
plan JSON, the markers from the installed bundle, and the before/after diff
output in your final answer.

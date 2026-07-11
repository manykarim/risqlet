# Research Appendix — Agentic QA Orchestrator

**Date:** 25 June 2026 · **Purpose:** Backing evidence for `agentic-qa-proposal.md`. Records (a) experiments run against the real installed packages, (b) the 2026 commercial/OSS landscape, and (c) a claim-by-claim fact-check. Where a claim could not be confirmed, this document says so.

> **Independence disclosure.** Four building blocks the proposal depends on — `rf-mcp`, `robotframework-heal`, `robotframework-agentskills`, `robotframework-agenteval` — are repositories authored by the proposal owner (GitHub `manykarim`). They are real and under our control, but they are not neutral third-party assets and should not be presented as such. `-agentskills` and `-agenteval` are **not yet on PyPI** (GitHub-only), so the repo strategy must use git dependencies or vendoring until they publish.

---

## 1. Experiments — installed reality, not documentation claims

All experiments below were run against packages actually installed from PyPI on 25 Jun 2026, using `TestModel` (no API keys, deterministic). They re-verify the claims in `pydantic-ai-2.0-analysis.md` against the shipped artifact rather than trusting the prior write-up.

### 1.1 Package existence (PyPI)

| Package | Latest | Note |
|---|---|---|
| `pydantic-ai` | **2.0.0** | Preceded by betas `2.0.0b1…b7`; v1 lineage runs `1.0.0 … 1.107.0`. The "7 betas + mature v1" framing is accurate. MIT. |
| `robotframework-heal` | **0.4.0** | Summary verbatim: *"A Robot Framework Listener for library agnostic self-healing, failure triage and root cause analysis of tests."* |
| `rf-mcp` | **0.31.2** | *"Robot Framework MCP Server — Natural Language Test Automation Bridge."* |
| `robotframework-browser` | **20.0.0** | Playwright-powered Browser library (the default RF browser backend). |
| `robotframework-agentskills` | **— not on PyPI —** | Exists on GitHub (`manykarim`); PyPI publication pending. |
| `robotframework-agenteval` | **— not on PyPI —** | Exists on GitHub (`manykarim`); Apache-2.0, v0.0.1; not yet on PyPI. |

### 1.2 Pydantic AI 2.0.0 API surface (introspection)

| What was tested | Result |
|---|---|
| Root exports: `Agent`, `ApprovalRequired`, `DeferredToolRequests`, `DeferredToolResults`, `ToolApproved`, `ToolDenied`, `RunContext`, `UsageLimits`, `AgentSpec` | ✅ All present |
| `ApprovalRequired(metadata=…)` signature | ✅ `__init__(self, metadata)` |
| MCP: `MCPToolset`, `StreamableHttpTransport`, `StdioTransport`, `ElicitationHandler`, `SamplingHandler` | ✅ All present under `pydantic_ai.mcp` |
| Capabilities: `AgentCapability`, `CapabilityFunc`, `capabilities`, `_deferred_capabilities` | ✅ Present (deferred-loading machinery is real) |
| `durable_exec.temporal` / `dbos` / `prefect` | ⚠️ Submodules exist but require optional deps (`temporalio`, `dbos`, `prefect`) — pin as extras |
| `ui.vercel_ai` | ✅ Imports; `ui.ag_ui` needs the `ag-ui-protocol` package |

### 1.3 The decisive experiment — HITL approval round-trip

A tool `apply_fix` raises `ApprovalRequired(metadata={"urgency":2,"blast_radius":"shared","event_id":…})` when the blast radius is `shared` and the call is not yet approved.

```
1) Run paused?  -> True
   approvals pending: ['apply_fix']
2) out.metadata = {'pyd_ai_tool_call_id__apply_fix':
                     {'urgency': 2, 'blast_radius': 'shared', 'event_id': 'evt-1'}}
3) Resumed via ToolApproved() -> {"apply_fix":"applied fix to evt-1"}
```

**Confirmed end-to-end:** the run pauses and returns a serializable `DeferredToolRequests` (the checkpoint); urgency/blast-radius are readable at `output.metadata[tool_call_id]` (a field on `DeferredToolRequests`, **not** on the individual `ToolCallPart` — note the access path); the human resumes with `ToolApproved()` and the run **continues from the pause**, not from scratch. This is the Escalation gate and the urgency-ranked inbox, built-in.

### 1.4 Other confirmed mechanisms

- **AgentSpec round-trip:** `AgentSpec.from_file/to_file` and `Agent.from_spec` exist. Fields: `model, name, description, instructions, deps_schema, output_schema, model_settings, retries, end_strategy, tool_timeout, metadata, capabilities, json_schema_path`. Agents can live in-repo as version-controlled YAML with a `$schema`.
- **Pydantic Evals:** `Dataset`, `Case`, `Evaluator`, `LLMJudge` importable from `pydantic_evals`.

**Net:** every load-bearing Pydantic AI v2 mechanism the proposal relies on is real in the shipped 2.0.0 package. The bet is sound.

---

## 2. Claim-by-claim fact-check (external)

| # | Claim | Verdict | Source |
|---|---|---|---|
| 1 | heise article "Agentic QA: Wie KI-Agenten…" (18 Jun 2026, Adam Auerbach) | **PARTIAL** — article, date, author, "Expert-in-the-Loop", tester→coordinator shift confirmed; **six-agent taxonomy + confidence-pausing are behind heise+ and unconfirmed** | heise.de/hintergrund/…-11312179.html |
| 2 | EPAM publishes the six-agent / MCP-Playwright + LangGraph + OmniParser reference architecture | **CONTRADICTED as stated** — EPAM Agentic QA is real (launched 28 Oct 2025, AI/Run™), but EPAM describes it as scriptless / "Adaptive Regression" / human-AI synergy. The specific stack appears only in third-party blogs, not EPAM material | epam.com newsroom; solutionshub.epam.com |
| 3 | Playwright ships built-in Planner/Generator/Healer; TS-only, no Python loop | **VERIFIED** — v1.56 (Oct 2025), MCP-based; `--loop=python` is an open P3 request (issue #38610) | playwright.dev/docs/test-agents |
| 4 | Playwright MCP — ~34k★, Apache-2.0, accessibility-tree (not screenshots) | **VERIFIED** | github.com/microsoft/playwright-mcp |
| 5 | OmniParser v2 — YOLOv8+Florence-2, ~0.6–0.8 s/frame; `icon_detect` AGPL, `icon_caption` MIT | **VERIFIED** | github.com/microsoft/OmniParser |
| 6 | robotframework-heal — ~7 failure classes, library-agnostic, tiered cost model, heal MCP (`list_failures`/`get_fix_proposals`/`apply_fix`/`healing_history`), "test outdated vs application changed", current API `Library Heal`/`HEAL_*` | **VERIFIED** — classes: locator-drift, timing, viewport, overlay, form-state, assertion-drift, + unknown (≈7); `Library SelfHealing`/`LLM_*` is the deprecated 0.3 shim | github.com/manykarim/robotframework-heal |
| 7 | rf-mcp — NL → Robot Framework tests, discover-then-act, multi-library | **VERIFIED** | github.com/manykarim/rf-mcp |
| 8 | `-agentskills` / `-agenteval` not on PyPI | **VERIFIED** — both exist on GitHub (`manykarim`), neither on PyPI | github.com/manykarim |
| 9 | Langfuse acquired by ClickHouse (~Jan 2026); MIT, self-hostable, OTel-native | **VERIFIED** — announced 16 Jan 2026 | clickhouse.com/blog; langfuse.com/blog |

**Action required:** stop attributing the six-agent architecture to EPAM (claim 2). Present it as our synthesis informed by the heise article's direction. Cite the heise six-agent taxonomy carefully (claim 1) given it's paywalled.

---

## 3. The 2026 commercial / OSS landscape

### 3.1 Category is now analyst-formalized

- **Forrester** renamed the category to **"Autonomous Testing Platforms"** (Wave Q4 2025, 31 vendors).
- **Gartner** has an **"AI-Augmented Software Testing Tools"** Magic Quadrant (2025: Tricentis a Leader, Katalon a Visionary).
- Consensus definition of **agentic QA**: *autonomous agents plan/execute/adapt testing from **goals, not scripts**, with human **oversight**, not human **control**.*

### 3.2 Most marquee features have commoditized

| Capability | 2026 status |
|---|---|
| NL / requirements → test generation | **Table-stakes** |
| Self-healing | **Table-stakes** — *intent-based* (vs DOM-selector) healing is the differentiator |
| Visual validation / visual AI | **Table-stakes** — noise-handling differentiates |
| CI/CD integration | **Baseline** — MCP / coding-agent integration is the new edge |
| Flakiness detection & quarantine | **Table-stakes** for CI platforms |
| Root-cause analysis / triage | **Becoming table-stakes** |
| Human-in-the-loop review/approval | **Differentiator → governance requirement** (EU AI Act, Aug 2026) |
| Coverage & risk mapping | **Differentiator** |
| Autonomous app exploration | **Emerging differentiator** |
| **Multi-agent orchestration (planner/executor/critic)** | **Leading-edge** — the *independent critic* is key |

### 3.3 Competitor snapshot (verified facts)

- **EPAM Agentic QA** — services-delivered, scriptless, "Adaptive Regression" (mechanism undisclosed). EPAM–Anthropic partnership.
- **testRigor** — plain-English specs; multi-attribute → semantic → Vision-AI healing; "fixed-by-ai" tag + human rollback.
- **mabl** — agentic platform positioning as *independent reviewer of AI-generated code*; "Adaptive Multi-Layer Auto-Healing" heals on preserved **intent**; fails the step on low-confidence rather than mis-healing. Cloud-only.
- **Functionize** — most aggressively "fully autonomous"; ~200 attributes/element, "adjoint model" fails loudly on uncertainty.
- **Katalon** — TrueTest generates from production telemetry; two-tier healing (deterministic fallback → LLM) with Approve/Discard UI; pluggable models (OpenAI/Gemini/Bedrock-Claude).
- **Tricentis** (Tosca/Testim) — model-based + Vision AI (works where there's no DOM); Testim Smart Locators with 70% confidence threshold; remote MCP servers + BYO-AI.
- **Playwright agents** (Microsoft) — Planner/Generator/Healer on MCP + accessibility tree; Healer reports >75% on selector failures [vendor]; **TS-only**.
- **QA.tech** — autonomous agents build an app knowledge graph; fully autonomous PR workflow; built on Claude (Haiku 4.5 default, Sonnet 4.5 for complex).
- **Diffblue** — Java unit tests via RL + symbolic execution (no LLM → deterministic, on-prem).
- **Antithesis** — deterministic-simulation testing; $105M Series A (Jane Street, Dec 2025).
- **Octomind** — ⚠️ **shutting down June 2026** despite pioneering source-level healing (cautionary tale).

### 3.4 Self-healing reality (design-relevant)

Three generations: (1) multi-locator fallback, (2) weighted-attribute scoring (Testim 70%, Healenium 0.6 score-cap), (3) **semantic ML/LLM re-ID by step intent** (mabl advanced, Functionize, testRigor, Katalon AI tier, Playwright Healer, **robotframework-heal**). Gen-3 is the differentiated tier.

**The central risk is the silent heal / false positive:** when an element is genuinely gone (a real bug), a scorer picks the closest surviving node, the test goes green, and a defect ships. **Only ~28% of real failures are selector-related** (timing ~30%, test data ~14%, visual ~10%, interaction ~10%, runtime ~8%, per QA Wolf) — so selector-only "self-healing" addresses barely a quarter of failures. This is the strongest argument for the full six-agent RCA loop and heal's "test outdated vs application changed" distinction, rather than healing in isolation.

### 3.5 Market gaps = the proposal's openings

1. **Cross-framework agentic orchestration — almost nobody does it.** OSS agents (browser-use, Stagehand, Skyvern, Midscene, LaVague) are single-paradigm walled gardens; commercial "unified" platforms only aggregate results. No OSS orchestrator drives Robot Framework + Playwright + Selenium/Cypress under one planner with shared reporting.
2. **Robot Framework + AI is nascent.** The one RF self-healing agent lib (`robotframework-selfhealing-agents`, MarketSquare) is v0.1.1, ~26★, locator-only. RF's regulated/European enterprise base aligns with a self-host thesis — arguably the strongest single wedge.
3. **Privacy structurally disqualifies cloud leaders.** 67% cite data-privacy as the top GenAI-in-QE barrier (WQR 2025). Browser agents ingest the whole DOM; research (AgentDAM) shows tool inputs/logs leak up to ~85% even when final output is sanitized. A genuinely air-gappable, BYO/local-LLM, open-source orchestrator with compliance scaffolding has almost no direct competition.
4. **Regulation creates a mandate.** **EU AI Act (effective Aug 2026)** makes demonstrable human oversight a legal requirement — the autonomy ladder + HITL approval is a compliance feature, not just good UX.
5. **Practitioner consensus: keep AI out of the deterministic runtime.** AI belongs in authoring/maintenance; regression suites must be deterministic and cost-predictable. The most dangerous failure mode is AI silently rewriting assertions to make failing tests pass.

### 3.6 Synthesized positioning

A defensible, under-served position combines five things no incumbent offers together:

1. Cross-framework orchestration (RF + Playwright/MCP + Selenium/Cypress) under one agentic planner with shared reporting.
2. Self-hostable + BYO/local-LLM by default — turning the regulated-industry blocker into the headline feature.
3. A governance layer OSS agents lack — audit trails, DOM/prompt redaction, RBAC/SSO, deterministic replay, HITL gates (answers EU AI Act + the privacy/reliability barriers).
4. AI in authoring/healing, deterministic at runtime — generate/repair with LLMs, compile to deterministic Playwright/RF/Selenium specs.
5. Independent-critic multi-agent pattern (planner/executor/critic) — avoids the "agent grading its own work" bias.

---

## 4. What could NOT be verified

- heise six-agent taxonomy & confidence-pausing (paywalled).
- EPAM's internal self-healing mechanism and exact architecture (press-release-level only).
- LLM identity for mabl, Functionize, EPAM, Katalon TrueTest, Autify.
- Gated analyst rankings (Forrester Wave leaders, Gartner Peer Insights) — 403.
- Vendor performance metrics (Functionize accuracy, Playwright Healer >75%, maintenance-reduction %) — vendor-reported, not independently audited.
</invoke>

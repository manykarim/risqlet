# Prior Art, Architecture Practice, IP Boundaries & Usage Patterns

**Deep research report #2 — gap-filling companion to `ai-augmented-risk-analysis-framework.md`**

*Compiled: July 2026. Method: multi-agent research harness (5 search angles, 26 sources fetched, 129 claims extracted, top 25 adversarially verified 3-vote, 0 refuted). Claims marked ⚠ were extracted from primary sources but not adversarially verified.*

This report deliberately does **not** re-cover standards, techniques, or game mechanics (see report #1). It answers four questions: what already exists, how to build it, what we may legally ship, and how it gets used.

---

## Part 1 — Prior Art Landscape (2024–2026)

The space is **no longer greenfield**. At least three threat-modeling MCP servers ship today, plus agentic security review products and one repo-metrics MCP server. None covers quality-risk breadth (ISO 25010-wide risks, RBT, FMEA levers, test strategy) — that is the open niche.

### Comparison table

| Tool | What it is | License | Adoption | Key lessons for us |
|---|---|---|---|---|
| **AWS Labs threat-modeling-mcp-server** (Dec 2025) | Stateful, sequential 9-phase STRIDE workflow (business context → residual risk); persists to a `.threatmodel/` dir in Markdown+JSON; validates identified threats against actual code; **no external inference** — steers the host agent's own LLM | Apache-2.0 (forkable) | experimental, first-party | ✔ `.threatmodel/` = de-facto risk-register-as-code. ✔ "steer the host LLM, keep data client-side" answers the privacy question. ✘ **100+ tools** (13 business-context, 18 trust-boundary, 7 mitigation…) — a direct anti-pattern vs. minimalism evidence below |
| **mcp-stride-gpt** (mrwadams, STRIDE-GPT author) | Serverless HTTP MCP on Vercel: STRIDE, DREAD scoring, Mermaid attack trees, **security-test generation** (Gherkin/checklist), coverage validation, threat reports | "same as STRIDE GPT" (parent MIT) — verify before reuse | ~3 stars | ✔ Documented **"framework-provider" pattern**: server returns structured frameworks/guidance; the client LLM does the semantic analysis. This is the strongest architectural precedent for our skill-vs-tool split |
| **IriusRisk CLI** (v0.6.0, Feb 2026) | MCP stdio server, **29 tools in 7 categories** with `--include-tags`/`--exclude-tools` filtering; since v0.6.0 also ships **portable Agent Skills** tiered by LLM capability (reasoning/general/code-focused); repo-grounded loop: agent reads code → answers security questionnaires → rules engine regenerates threat model | CLI is MIT; the 200+ threat library stays server-side proprietary | commercial, most complete | ✔ First-party validation of the **hybrid Skills+MCP** architecture. ✔ The questionnaire→rules-engine loop is a proven repo-grounding pattern. ✘ Its moat is the proprietary catalog — confirming the catalog is the scarce asset |
| **Semgrep Claude Code plugin** | MCP server (SAST/SCA/secrets) + **hooks**: post-tool hook scans every file write/edit; session-start & per-prompt context injection of secure-coding defaults | plugin free; hosted service, tier-gated features | 18,127 installs | ✔ The **MCP + hooks + context-injection composite** is the shipping template for continuous, event-driven re-assessment inside an agent session |
| **Claude Code /security-review** (Aug 2025) & **Claude Code Security** (research preview Feb 2026) | Agentic scan (SQLi, XSS, auth, data handling, deps); GitHub Action posts inline PR comments (open source); the 2026 product adds adversarial self-triage of findings | GH Action open source | paid-plan feature | ✔ Adversarial self-triage of findings is now table stakes. ⚠ 500+ validated high-sev vulns claimed, but **no published false-positive stats**; static-only and non-deterministic — auditability gap we can differentiate on |
| **pytm / Threagile / Threat Dragon / MS TMT** (pre-LLM) | Code/YAML/diagram threat modeling | pytm & Threagile OSS | mature | ✔ IEEE S&P survey: **text-based models (pytm Python, Threagile YAML) are distinctly better for automation, scripting, versioning**. Threat library sizes span an order of magnitude: Threat Dragon generic → OVVL ~30 → Threagile ~42 → TMT ~50 → pytm ~114 (CAPEC/CWE) → IriusRisk 200+ |
| **omen** (panbanda) ⚠ | Rust CLI + MCP server, 20+ code-analysis tools: **churn×complexity hotspots** (Tornhill's *Code as a Crime Scene*), JIT defect prediction (Kamei 2013, Nagappan & Ball 2005), SATD, ownership, repo-health; commit/PR diff risk, GitHub Actions risk labels & quality gates; ships as MCP **plus** `omen-skills` plugin | Apache-2.0 (forkable) | ~15 stars | ✔ The repo-telemetry layer we need already exists permissively licensed. ✔ Its hybrid MCP+skills packaging mirrors our design. Its obscurity confirms the niche is open |

**Strategic conclusion:** STRIDE mechanics are commoditized and legally forkable (Apache-2.0/MIT prior art). Differentiation must come from (a) **quality/test-strategy breadth** — the whole ISO 25010 spectrum, RBT, FMEA levers, mitigation→test-charter generation — and (b) a **rich, permissively licensed quality-risk catalog**, which no one ships openly today.

---

## Part 2 — Agent-Facing Architecture Practice (verified evidence)

### 2.1 Skills vs MCP: hybrid, with the catalog in Skills

- Anthropic explicitly positions **Skills as complementary to MCP** — skills teach workflows involving external tools. A skill = directory + `SKILL.md` + YAML frontmatter; **three-level progressive disclosure** (metadata always in context → SKILL.md on relevance → bundled files on demand) makes bundled catalog content *effectively unbounded* at near-zero idle token cost. Skills can also bundle **executable scripts the agent runs without loading them into context** — the right home for deterministic scoring code. [Anthropic engineering, 3-0 verified]
- AWS MCP Design Guidelines formalize resources-for-data vs tools-for-functionality, **but** verifiers flagged that MCP resources have uneven client support in practice — so ship reference data via **Skills bundled files**, not `resource://` URIs. [3-0 verified, with caveat]
- IriusRisk shipping MCP tools *and* portable Agent Skills simultaneously (v0.6.0) is independent practitioner validation of the hybrid.

### 2.2 Tool-count minimalism is quantitatively supported

- Anthropic: replacing direct many-tool MCP calls with code execution cut an example workflow from **150,000 → 2,000 tokens (98.7%)**; loading all tool definitions up-front degrades performance; intermediate results should not transit the model's context. [vendor figure, illustrative]
- GitHub Copilot: the full ~40-tool built-in set caused a **2–5 pp resolution-rate drop** on SWE-Lancer/SWE-bench-class evals; consolidating to **13 core tools** improved success 2–5 pp and cut latency ~400 ms (GPT-5 and Claude Sonnet 4.5). [GitHub reports, bundle of changes]
- AWS Labs' 100+-tool threat-modeling server is the concrete anti-pattern.

**Target: ≤ ~10 MCP tools.** Consistent with report #1's ~6-tool surface.

### 2.3 Statelessness is where MCP is heading — persist state to files

- A 2026-07-28 MCP **spec release candidate moves the protocol stateless-first**: connection-level sessions (`Mcp-Session-Id`) and the initialize handshake are eliminated; **elicitation is replaced** by an `InputRequiredResult` multi-round-trip flow; rationale is load-balancer-friendly scaling. ⚠ [single source, RC not final]
- Anthropic independently recommends agents keep workflow state via **filesystem persistence** rather than stateful server-side tools. [3-0 verified]
- AWS Labs' `.threatmodel/` directory and Atlassian's `.known-risks.yaml` show risk-state-in-repo is already the working convention.

**Implication:** do NOT build around server-held sessions (a revision of both report #1's `create_session` sketch and agentic-riskstorming's design). The **risk register lives in the repo** (e.g. `.qrisk/` — YAML/Markdown, git-versioned, diffable, PR-reviewable). Server tools operate on those files deterministically. Event-sourced audit trails (agentic-riskstorming ADR-002) can be kept as append-only JSONL *in the same directory*.

### 2.4 Multi-persona elicitation: evidence now exists, with a critical caveat

- **Separate-Then-Together wins**: independent ideation per persona agent followed by a collaborative merge phase outperformed both purely-independent and purely-joint multi-agent brainstorming. **Dissimilar personas measurably increase semantic diversity** (k-means cluster purity 0.80 for distant persona pairs vs 0.53 generalist baseline); replicated across GPT-4.1, Llama 4, Claude Sonnet 4.5, Gemini 2.5 Pro. ⚠ [arXiv 2512.04488; LLM-graded, not human-graded]
- **Domain-specificity collapse**: on domain-specific topics, persona-agent effectiveness drops sharply — experts judge many agent contributions irrelevant because agents lack tacit organizational knowledge. ⚠ [counter-balanced human study]
- Zalando's postmortem-mining pipeline: multi-stage LLM pipeline over thousands of incident postmortems; **up to 40% hallucination probability** in summarization; dominant failure = "surface attribution error" (causes assigned from textual clues, not causality); mitigated by staged pipeline + **100% human curation**; still a ~3× reviewer productivity gain. ⚠

**Implication:** report #1's Phase 0 (context ingestion) is not a nice-to-have — it is **the** determinant of elicitation quality. Persona ensembles without deep repo/product grounding will produce plausible irrelevance. Budget accordingly: grounding > generation.

### 2.5 Repo-grounding signals (validated research)

- **Relative churn** (normalized by size & temporal extent) discriminates fault-prone binaries at **89% accuracy**; absolute churn is a poor predictor — normalize. [Nagappan & Ball, ICSE 2005] ⚠
- **Change entropy** (Shannon entropy of change distribution across files per period) beats prior-modifications predictors by **13–42% error reduction** and matches/beats prior-faults predictors; computable from VCS data alone. [Hassan, ICSE 2009] ⚠
- omen implements churn×complexity hotspots + JIT defect prediction over MCP under Apache-2.0 — fork or depend rather than rebuild.

### 2.6 Security of state-changing tools

AWS guidelines for tools that execute/accept code: dedicated namespace execution, explicit operation/module allowlists, timeouts, AST validation + scanner in depth. [3-0 verified] Plus report #1's own guardrails: human principal required for state transitions, read-only defaults.

---

## Part 3 — IP & Licensing Boundaries

*⚠ Extracted from primary sources (statute-adjacent commentary, official terms pages) but not adversarially verified; not legal advice.*

### 3.1 Card decks: mechanics free, expression protected

- US copyright: **the idea of a game and its method of play are not copyrightable** — only expressive elements (rule text as literary work, artwork). [ABA Landslide]
- *Affiliated Hospital v. Merdel*: rulebook copyright protects only arrangement/presentation; **a restatement of the same rules did not infringe**.
- **Merger doctrine** (*Freedman v. Grolier*): where an idea admits only one expression, that expression is unprotectable. Card games are treated as having "limited opportunity for expression".
- BUT: sufficiently **creative card text is protectable** — TestSphere's specific descriptions and example prompts qualify. Mechanics (3 phases, pick-six, card categories as concepts) do not.

### 3.2 Specific properties

| Source | Status | What we may do |
|---|---|---|
| **TestSphere / RiskStorming (MoT)** | Proprietary, **seat-licensed** (Single/Team-10/Unlimited); no tier grants software-embedding or redistribution; riskstormingonline.com: "© 2026 … All rights reserved" | Reimplement the *mechanics* and *established concepts* with **original text and original examples**; do not ship card text; avoid the trademarks ("RiskStorming", "TestSphere") in product naming. The `docs/testsphere-data/*.json` files in this repo are verbatim card content — **treat as internal reference only, never ship** |
| **HTSM (Satisfice)** | Plain proprietary copyright (v6.3, 2024); Bach *encourages customization* in context — an informal invitation, **not** a republication license | Category labels (SFDIPOT words etc.) are short functional phrases — unprotectable as such. Write our own definitions/prompts around the concept structure, with attribution |
| **ISO standards** | Strict: no verbatim, no modification/translation without permission; extracts require authorization; **explicit prohibition on any AI/LLM use of ISO content** (site terms, 2026); actively enforced (Swiss law) | Characteristic *names* and the taxonomy-as-fact are usable; **write fully original definitions**. Never ingest ISO text into the product or its build pipeline |
| **OWASP Testing Guide** | Legacy repo is **GFDL 1.3** (copyleft; derived works must stay GFDL); newer WSTG is CC BY-SA (also share-alike) | Avoid deriving catalog text from these directly, or quarantine such content in a clearly-licensed separate pack. Check each OWASP project individually — licenses vary (Top-10 lists are typically CC BY-SA 4.0) |
| **MITRE ATT&CK / ATLAS / CWE / CAPEC** | Royalty-free license incl. **commercial use**, with mandatory attribution statement ("© … The MITRE Corporation … reproduced and distributed with the permission of…"); ATT&CK is a registered trademark | Embed content with the required notice; don't brand with MITRE marks |

### 3.3 Safe catalog strategy (clean-room pattern)

1. **Concept layer** (free): established technique/heuristic/quality-aspect *names and ideas* — stress testing, boundary analysis, CRUD, personas, pick-six constraint, S×O×D — with citations to their originators.
2. **Expression layer** (ours): every definition, description, and example prompt written from scratch; a contributor rule that no source card/standard text is open while writing (clean-room discipline); provenance note per entry ("concept popularized by X; text original").
3. **Open packs** (imported under their terms): MITRE (attribution notice), OWASP per-project (share-alike quarantined), CWE/CAPEC.
4. **Licensed packs** (bring-your-own): a slot for teams that own TestSphere/RiskStorming decks or IriusRisk libraries to mount them locally — we never distribute.

---

## Part 4 — Usage & Adoption Patterns

- **Risk-register-as-code is converging**: AWS `.threatmodel/` (Markdown+JSON), Atlassian `.known-risks.yaml` (service owners define their own risk checks in-repo), omen's CI risk labels. Our register format should live in-repo and be PR-diffable.
- **PR-time gating works at scale with near-zero friction**: Atlassian ran Known-Risks merge checks over **355,000+ PRs, flagging 0.075%** (~7 per 10k); 41% of PRs auto-excluded by path filtering; ~3% of flags overridden by humans ("HOT approval"). Change-related causes account for **50–60% of service disruptions** — the PR boundary is the right re-assessment trigger. ⚠
- **In-session continuity**: Semgrep's post-tool-hook (scan after every write) + session-start context injection is the template for keeping the risk register live *during* agent coding sessions, not just in CI.
- **Repo-grounded model regeneration**: IriusRisk's loop (agent answers questionnaires from code → rules engine regenerates threat model) shows how to keep analysis synchronized with code without re-running full elicitation.
- **Human-in-the-loop is evidence-mandated**, not just principled: Zalando's 40% hallucination rate and "surface attribution error" mode; Claude Code Security's absent FP statistics. Verification layers and human curation gates are what make LLM elicitation usable.

---

## Part 5 — Consolidated Architecture Decisions

Updating report #1's design with the verified evidence:

| # | Decision | Basis |
|---|---|---|
| D1 | **Hybrid: Agent Skills (knowledge) + small MCP server (determinism)** — catalog, playbooks, personas, rubrics as skills with progressive disclosure; ≤ ~10 MCP tools | Anthropic guidance 3-0; GitHub 40→13 evidence; IriusRisk precedent |
| D2 | **Framework-provider pattern**: tools return structures/frameworks/validation; the *host* LLM does semantic analysis; server makes no inference calls (privacy: data stays client-side) | mcp-stride-gpt + AWS Labs precedent |
| D3 | **Register-in-repo, stateless server**: `.qrisk/` directory (YAML register + append-only JSONL event log + Markdown strategy), no server-held sessions | MCP stateless-first RC; Anthropic filesystem-state guidance; `.threatmodel`/`.known-risks.yaml` convention |
| D4 | **Deterministic scoring/dedup/traceability as bundled executable scripts** (skills) callable without context load; arithmetic never in the model | Anthropic scripts pattern; report #1 principle 1 |
| D5 | **Separate-then-together persona ensemble** with deliberately *dissimilar* personas; merge is deterministic; disagreement surfaced | arXiv 2512.04488 (with LLM-graded caveat) |
| D6 | **Grounding before generation**: Phase 0 ingests relative-churn + change-entropy hotspots (fork/depend on omen, Apache-2.0), coverage, postmortems via multi-stage pipeline with human curation | Nagappan/Ball, Hassan, Zalando; domain-collapse evidence |
| D7 | **Three re-assessment triggers**: in-session (post-tool hooks), PR-time (merge-check pattern with path filtering + human override), scheduled/event (incident ingestion) | Semgrep, Atlassian patterns |
| D8 | **Clean-room catalog + open packs + BYO licensed packs**; never ship TestSphere/RiskStorming/HTSM/ISO text; MITRE with attribution; share-alike content quarantined | Part 3 |
| D9 | **Differentiate on quality breadth + traceability loop** (aspect→risk→mitigation→test→result), not on STRIDE — security-only analysis is commoditized | Part 1 landscape |
| D10 | **Verification layer on elicited risks** (evidence-linking, adversarial self-triage, speculative flags) before anything enters the register | Zalando 40% hallucination; Claude Code Security precedent |

### Open questions carried forward

1. MCP stateless-first RC is not yet final — track it; design as if final (file-backed state loses nothing either way).
2. Which MCP features (resources, prompts, elicitation, sampling) are dependable across Claude Code / Cursor / Copilot / Codex in 2026? Current answer: assume **tools only**; everything else via Skills.
3. No published recall/precision study of LLM *risk* elicitation (vs. security vuln detection) exists yet — backtesting on historical incidents (report #1 §6.1) would be genuinely novel, publishable evidence.
4. EU jurisdiction nuance on the idea/expression analysis (US case law cited); worth a legal read before public release.

---

## Sources (verified findings)

- https://github.com/awslabs/threat-modeling-mcp-server (Apache-2.0; 9-phase; `.threatmodel`; 100+ tools)
- https://github.com/mrwadams/mcp-stride-gpt (framework-provider pattern; security-test generation)
- https://github.com/iriusrisk/iriusrisk-cli (MIT; 29 tools; Agent Skills v0.6.0; questionnaire loop)
- https://claude.com/plugins/semgrep + https://github.com/semgrep/mcp-marketplace (hooks.json)
- https://people.bu.edu/staro/Threat_Modeling_Tools_Survey.pdf (IEEE S&P 20(4), 2022)
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://www.anthropic.com/engineering/code-execution-with-mcp (98.7% figure)
- https://github.blog/ai-and-ml/github-copilot/how-were-making-github-copilot-smarter-with-fewer-tools/ (40→13)
- https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md

**Sources (extracted, unverified ⚠):** ABA Landslide (playing-card copyright); MITRE terms of use; ISO copyright guide/site terms; MoT Digital RiskStorming store page; Satisfice HTSM v6.3; OWASP Testing Guide Licence.md; arXiv 2512.04488 (separate-then-together); arXiv 2505.04101 / 2411.17058; Nagappan & Ball ICSE 2005; Hassan ICSE 2009; Zalando engineering (postmortem pipeline); Atlassian engineering (Known Risks merge checks); StackHawk (Claude Code security review analysis); azukiazusa.dev (MCP stateless RC); https://github.com/panbanda/omen.

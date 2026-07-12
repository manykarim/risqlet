# AI-Augmented Risk Analysis & Mitigation for Software Quality

**Deep research report: standards, models, games — and a framework design for agents (MCP server / tool / Agent Skill)**

*Compiled: July 2026*

---

## Executive Summary

Software risk analysis sits on three bodies of knowledge that rarely talk to each other:

1. **Formal standards** — ISO/IEC 25010 (quality characteristics), ISO/IEC/IEEE 29119 (risk-based testing), ISO 31000 (generic risk management), plus domain regimes (ISO 26262, ISO 14971, IEC 62443, DO-178C) and the new AI-specific layer (EU AI Act, NIST AI RMF, ISO/IEC 42001, OWASP LLM/Agentic Top 10).
2. **Engineering techniques** — FMEA/RPN, FTA, HAZOP guidewords, STRIDE, risk matrices, pre-mortems, bow-tie analysis.
3. **Community practice & serious games** — RiskStorming with TestSphere, Would Heu-Risk It?, the Heuristic Test Strategy Model (HTSM), FEW HICCUPPS, the Test Heuristics Cheat Sheet, architecture risk-storming (Simon Brown).

The central finding of this report: **the games are not toys — they are executable protocols.** RiskStorming's three phases *are* a pipeline (`prioritize_quality_aspects → elicit_risks → map_mitigations`). Card decks *are* curated, chunked knowledge bases with stable IDs. Guideword methods (HAZOP, SFDIPOT, FEW HICCUPPS) *are* structured prompt libraries. What workshop facilitators do with humans, an orchestrator can do with agents — provided the framework separates **divergent ideation (LLM-suitable)** from **scoring, aggregation and traceability (deterministic-code-suitable)**, and keeps humans in the decision loop.

The proposed framework, working name **QRisk** (Quality Risk Intelligence), is a hybrid:

- A **knowledge layer** shipped as Agent Skills (quality models, card decks as data, guideword catalogs, scoring rubrics) — cheap, auditable, versioned text.
- A **state & determinism layer** shipped as a small MCP server (risk register CRUD, scoring engine, traceability graph, exports) — few stateful tools, structured and loggable.
- An **orchestration layer** of persona subagents (security, performance, UX, compliance, operations) running divergent elicitation in parallel, converging through deterministic de-duplication and human review gates.
- **Outputs** that are first-class artifacts: a machine-readable risk register (YAML/JSON), a one-page test strategy, and traceable links from quality aspect → risk → mitigation → test case → execution result, closing the loop with rf-mcp, robotframework-heal and robotframework-agenteval.

---

## Table of Contents

1. [Part I — Standards Landscape](#part-i--standards-landscape)
2. [Part II — Risk Analysis Techniques](#part-ii--risk-analysis-techniques)
3. [Part III — Community Concepts, Card Decks & Serious Games](#part-iii--community-concepts-card-decks--serious-games)
4. [Part IV — Why Games Translate to Agents](#part-iv--why-games-translate-to-agents)
5. [Part V — Framework Design: QRisk](#part-v--framework-design-qrisk)
6. [Part VI — Evaluation, Limitations & Honest Caveats](#part-vi--evaluation-limitations--honest-caveats)
7. [Part VII — Roadmap](#part-vii--roadmap)
8. [References](#references)

---

# Part I — Standards Landscape

## 1.1 ISO/IEC 25010:2023 — The Product Quality Model (SQuaRE)

The anchor standard for "what does quality even mean." The 2023 revision (replacing 2011) restructured the SQuaRE family: the product quality model stays in 25010, the quality-in-use model moved to **ISO/IEC 25019:2023**, and model usage guidance moved to **ISO/IEC 25002:2024**. Data quality remains in **ISO/IEC 25012**.

**Nine characteristics in 25010:2023** (was eight in 2011):

| # | Characteristic | Key sub-characteristics | Notes vs. 2011 |
|---|----------------|-------------------------|----------------|
| 1 | Functional Suitability | completeness, correctness, appropriateness | unchanged |
| 2 | Performance Efficiency | time behaviour, resource utilization, capacity | unchanged |
| 3 | Compatibility | co-existence, interoperability | unchanged |
| 4 | Interaction Capability | appropriateness recognizability, learnability, operability, user error protection, user engagement, **inclusivity**, user assistance, **self-descriptiveness** | renamed from *Usability*; "user interface aesthetics" → "user engagement" |
| 5 | Reliability | **faultlessness**, availability, fault tolerance, recoverability | "maturity" → "faultlessness" |
| 6 | Security | confidentiality, integrity, non-repudiation, accountability, authenticity, **resistance** | *resistance* (to attack) added |
| 7 | Maintainability | modularity, reusability, analysability, modifiability, testability | unchanged |
| 8 | Flexibility | adaptability, **scalability**, installability, replaceability | renamed from *Portability*; scalability added |
| 9 | **Safety** (NEW) | operational constraint, risk identification, fail safe, hazard warning, safe integration | entirely new top-level characteristic |

Why this matters for a risk framework: 25010 is the **canonical taxonomy for Phase 1 of any risk analysis** ("which quality aspects matter?"). The 2023 additions — Safety, resistance, inclusivity, scalability — map remarkably well onto modern AI-era concerns. Notably, the *Safety* sub-characteristic **risk identification** makes risk analysis itself a product quality attribute.

Related SQuaRE members worth encoding in the framework:

- **ISO/IEC 25019:2023** — quality in use (beneficialness, freedom from risk, acceptability).
- **ISO/IEC 25012** — data quality model (15 characteristics; critical for data-heavy and ML systems).
- **ISO/IEC 25059:2023** — quality model extension for AI systems (adds e.g. functional adaptability, robustness, transparency, controllability for ML-based systems).

## 1.2 ISO/IEC/IEEE 29119 — Software Testing (Risk-Based by Mandate)

The 29119 series (Part 1 Concepts, Part 2 Test Processes, Part 3 Documentation, Part 4 Techniques, Part 5 Keyword-Driven) explicitly positions **testing as the primary approach to risk treatment in software development** and mandates a risk-based approach to test strategy. Part 2's test planning process embeds risk identification, risk assessment, and risk treatment selection directly in the flow that produces the test plan.

Consequence for the framework: a standards-aligned pipeline should produce 29119-3-compatible artifacts (test plan sections: risks, mitigation approach, prioritization rationale) *as a serialization target*, not as the working format.

## 1.3 ISO 31000 — Generic Risk Management Vocabulary & Process

ISO 31000 defines risk as *"the effect of uncertainty on objectives"* and standardizes the loop:

```
Scope & Context → Risk Identification → Risk Analysis → Risk Evaluation → Risk Treatment
        ↑______________ Monitoring & Review / Communication ______________↓
```

Treatment options (worth encoding as an enum): **avoid, reduce (mitigate), transfer/share, accept**. Every mitigation an agent proposes should be classifiable into one of these — it forces honesty about residual risk instead of implying everything is testable away.

## 1.4 ISTQB Definitions — The De-Facto Practitioner Vocabulary

ISTQB frames risk as a potential event/hazard/situation whose occurrence would have adverse consequences, characterized by **likelihood × impact**, and distinguishes:

- **Product (quality) risk** — a problem in the work product (defect-prone areas, failures in the field).
- **Project risk** — threats to the project's ability to deliver (staffing, environments, schedule).

**Risk-based testing (RBT)** per ISTQB: use product-risk levels to select, prioritize and scope test activities from the earliest stage. Despite ~25 years of RBT being mainstream, practitioner application is famously shallow — usually a one-off spreadsheet at project start. This is precisely the gap an agentic framework can close: *continuous, cheap re-assessment* instead of a stale artifact.

## 1.5 Domain & Safety Regimes (Encode as Optional Profiles)

| Standard | Domain | Risk concept worth stealing |
|----------|--------|------------------------------|
| ISO 26262 | Automotive | **ASIL (A–D)** determined by Severity × Exposure × Controllability; risk classes drive required rigor of methods |
| ISO 14971 | Medical devices | Risk = harm-centric; mandates benefit-risk analysis and post-market surveillance loop; RPN usage with explicit caveats |
| IEC 62443 | Industrial/OT security | Security Levels (SL 1–4) per zone/conduit; target vs. achieved SL gap analysis |
| DO-178C | Avionics | Design Assurance Levels (DAL A–E) tied to failure condition severity; objectives scale with level |
| EN 50128 | Rail | SIL-driven technique selection tables (technique X is M/HR/R per SIL) |

The generalizable pattern across all of them: **a discrete criticality level, derived from a small formula over 2–3 ordinal factors, that then *selects the required rigor of methods*.** That "criticality → method selection table" pattern is exactly what Phase 3 of RiskStorming does informally, and exactly what an agent can automate.

## 1.6 The AI-System Risk Layer (2024–2026)

For systems that *contain* AI — and for the risk-analysis agent itself:

- **EU AI Act** — risk-tiered regulation (unacceptable / high / limited / minimal); high-risk systems require risk management systems, logging, human oversight. Relevant for any German/EU enterprise deployment (fiscal-compliance-style thinking applied to AI).
- **NIST AI RMF 1.0** (+ Generative AI Profile) — four functions: **Govern, Map, Measure, Manage**; deliberately compatible with ISO 31000 vocabulary.
- **ISO/IEC 42001:2023** — AI management systems (the "ISO 27001 of AI").
- **ISO/IEC 23894:2023** — AI risk management guidance (ISO 31000 applied to AI).
- **OWASP Top 10 for LLM Applications (2025)** and **OWASP Top 10 for Agentic Applications (Dec 2025)** — community-driven risk catalogs with per-risk explanations, examples, and mitigations; the agentic list covers memory poisoning, tool misuse, privilege compromise, cascading hallucinations, etc. These are ready-made "risk card decks" in all but name.
- **MITRE ATLAS** — adversarial ML threat matrix (ATT&CK-style).

These belong in the framework as **pluggable risk catalogs**, same shape as a card deck.

---

# Part II — Risk Analysis Techniques

## 2.1 FMEA / RPN — The Workhorse (and Its Known Failure Modes)

Failure Mode and Effects Analysis rates each potential failure mode on three ordinal scales (typically 1–10):

```
RPN = Severity × Occurrence × Detection        (range 1–1000; higher = worse)
```

- **Severity** — how bad the effect is if it happens.
- **Occurrence** — how likely the cause is to occur.
- **Detection** — how likely existing controls are to catch it *before* it reaches the user (high score = poor detectability).

Mitigation levers map cleanly: reduce Severity via design changes/fail-safes, reduce Occurrence via prevention/error-proofing, improve Detection via added testing/monitoring. The **Detection dimension is FMEA's gift to testers** — it is literally "how good is our testing here?", which neither the ISTQB 2-factor model (likelihood × impact) nor most risk matrices capture.

**Known problems to encode as guardrails, not repeat:**

1. **RPN is not a valid interval scale.** S9×O2×D5 = 90 and S2×O9×D5 = 90 are *not* equally urgent — a severity-9 issue deserves attention regardless of the product. Modern practice (AIAG-VDA FMEA 2019) replaced raw RPN thresholds with **Action Priority (AP) tables** (High/Medium/Low lookups over S/O/D combinations), and reliability practitioners advise against fixed RPN thresholds because teams game the numbers.
2. **Score-gaming** — teams tweak ratings downward to duck the action threshold. An agent-maintained audit trail (who/what changed a rating, with justification) is a direct countermeasure.
3. **Ordinal-scale multiplication** is mathematically dubious; treat RPN/AP as a *sorting heuristic*, never as a measurement.

**Framework takeaway:** support both classic Likelihood×Impact and S×O×D, but implement prioritization as a **configurable policy** (raw product, AP-style lookup table, severity-first lexicographic) in deterministic code — never let the LLM do the arithmetic or the ranking.

## 2.2 The Rest of the Toolbox

| Technique | Core move | Agent-translation value |
|-----------|-----------|--------------------------|
| **FTA** (Fault Tree Analysis) | Top-down: start from an undesired top event, decompose via AND/OR gates to basic causes | LLMs are good at proposing decompositions; the tree is a verifiable structure a human can prune |
| **HAZOP** | Apply **guidewords** (No/Not, More, Less, As Well As, Part Of, Reverse, Other Than, Early, Late, Before, After) to each parameter/flow | *The* proto-prompt-library. Guideword × element cross-product = systematic elicitation an agent can exhaustively enumerate (humans can't, agents can — cheaply) |
| **STRIDE** | Per-element threat categories: Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation of privilege | Same shape as HAZOP for security; pairs with data-flow diagrams |
| **Risk matrix** (L×I grid) | 3×3 / 5×5 grid, color zones | Simple; suffers "risk matrix pathologies" (range compression, arbitrary bucketing) — keep, but as a *view*, not the model |
| **Pre-mortem** (Klein) | "It's 6 months later and the project failed spectacularly. What happened?" — prospective hindsight | Excellent single-prompt technique; measurably increases risk idea diversity; trivially agent-runnable with multiple personas |
| **Bow-tie analysis** | Hazard in the middle; preventive barriers left, recovery barriers right | Great visual for mitigation *placement* (prevent vs. detect vs. recover) — maps to Detection-vs-Occurrence levers |
| **Risk poker** | Planning-poker-style estimation of risk per story | The consensus mechanic (independent estimates, reveal, discuss outliers) is directly portable to multi-agent estimation — have N persona agents score independently, surface disagreement to humans |
| **Monte Carlo / quantitative (FAIR etc.)** | Distributions instead of point scores | Out of scope for v1; note as a future policy plug-in |

**Cross-cutting insight:** almost every classic technique is (a) a **decomposition structure** plus (b) a **prompt catalog** plus (c) an **aggregation rule**. Agents excel at (a) proposals and (b) exhaustive application; (c) must stay deterministic.

---

# Part III — Community Concepts, Card Decks & Serious Games

## 3.1 RiskStorming with TestSphere (Beren Van Daele / Ministry of Testing)

The most widely adopted collaborative test-strategy format in the testing community. A whole-team workshop (testers, devs, PO, UX, business) in **three phases**:

| Phase | Question | Mechanic | Output |
|-------|----------|----------|--------|
| **1** | *Which quality aspects matter most for this product?* ("Why we test") | From the 20 blue **Quality Aspect** TestSphere cards, the team negotiates down to **exactly six** | 6 prioritized quality aspects |
| **2** | *What risks endanger those aspects?* | Timeboxed brainstorm; sticky notes per aspect; then prioritize the most important risks | Concrete, product-specific risk statements |
| **3** | *How do we mitigate those risks?* ("How we test") | Map remaining TestSphere cards (Techniques, Heuristics, Patterns, Feelings) onto each top risk; teams may invent new cards for uncovered mitigations | Mitigation/test-strategy mapping, often condensed into a **one-page test plan** |

The full TestSphere deck is **100 cards in 5 suits**: Quality Aspects (blue), Patterns (orange), Techniques (green), Heuristics (pink), Feelings (purple) — each card carrying a title, a one-liner, and three example prompts. A 2019+ **Quality Aspects expansion** added modern aspects (e.g. inclusivity-adjacent concerns that emerged *from* RiskStorming sessions themselves, presaging ISO 25010:2023's additions).

**Constraint design worth preserving:** the forced choice of *six* aspects is not arbitrary — limiting options is what makes prioritization real (João Proença's observation via Lisa Crispin). An AI framework that returns 40 "important" aspects has failed Phase 1 by definition.

**Ecosystem notes:**
- **riskstormingonline.com** — Beren's SaaS for remote sessions (born of COVID-era Miro workarounds); now positions RiskStorming as "risk-based testing for agile teams," turning QA into business strategy.
- **MoT relaunch (Oct 2024)** — RiskStorming as a standalone product: dedicated card decks (no longer strictly TestSphere-bound), a facilitation guide, print + digital.
- **RiskStorming + AI** — MoT/Beren have publicly experimented with AI-assisted RiskStorming sessions (MoTaverse, 2025), i.e. the community itself is moving this direction.
- Documented weak spot (Scott Logic practitioner guide, field reports): **Phase 3 is where teams struggle** — non-testers don't know the technique vocabulary, sessions run long, mitigation mapping gets cut short. *This is the highest-leverage point for AI augmentation:* the agent knows all 100 cards and every technique's applicability conditions; humans keep the context and the decision.

## 3.2 Would Heu-Risk It? (Lena Pejgan Wiberg/Nyström)

Born from a risk workshop Lena planned with Lisa Crispin; became a 30-card deck (illustrated by Trish Khoo, RPG-trading-card style, each card with a title, artwork and a rhyme) plus a 2021 book. Three categories:

| Category | Meaning | Risk-framework role |
|----------|---------|---------------------|
| **Traps** (purple) | Mistakes/antipatterns testers fall into — *risks to the quality of testing itself* | Meta-risk checklist: audit the *risk analysis and test process*, not the product |
| **Tools** | Heuristics/techniques/patterns good testers use, often unconsciously | Mitigation catalog for process-level risks |
| **Weapons** | Common weak spots in how software is built — where to aim testing | Product-risk elicitation prompts |

Its distinctive contribution vs. RiskStorming: **second-order risk**. RiskStorming asks "what can go wrong with the product?"; Would Heu-Risk It also asks "what can go wrong with *our testing and our thinking*?" (bias, over-trust in automation, coverage illusions). Lisa Crispin's blurb nails the intent: overcoming unconscious bias, thinking laterally, surfacing "unknown unknown" risks. An honest AI framework needs exactly this layer pointed at itself (see Part VI).

Format detail worth copying: documented **game modes** (Lightning mode for solo reflection, matching/connection games, workshop formats with trap-card constraints injected into a risk analysis) — i.e. the deck ships with *multiple protocols over the same knowledge base*. That's a skill with several entry-point workflows.

## 3.3 Heuristic Test Strategy Model — HTSM (James Bach / Michael Bolton, Satisfice)

The intellectual backbone of context-driven test strategy; current version **6.3 (Dec 2024)**. Four guideword areas:

1. **Project Environment** — customers, information, developer relations, test team, equipment & tools, schedule, test items, deliverables.
2. **Product Elements** — the **SFDIPOT** mnemonic: **S**tructure, **F**unction, **D**ata, **I**nterfaces, **P**latform, **O**perations, **T**ime (Time was added after Michael Bolton's field experience; Interfaces likewise a later refinement of the original SFDPO).
3. **Quality Criteria Categories** — capability, reliability, usability, charisma, security, scalability, performance, installability, compatibility, supportability, testability, maintainability, portability, localizability — a practitioner's alternative to ISO 25010, plus **development criteria** (CRUSSPIC STMPL family).
4. **General Test Techniques** — nine families: Function, Domain, Stress, Flow, Claims, User, Risk, Sequence/State, Automatic Checking.

Output concept: the **Testing & Quality Story** — you can never verify "actual" quality; testing produces an *informed assessment narrated as a story* (risks, coverage, techniques, caveats). This is the right epistemology for an AI framework's report generator: assessments with stated uncertainty, not verdicts.

Companion heuristics from the same school:

- **FEW HICCUPPS** (Bolton) — consistency **oracles**: Familiarity, Explainability, World, History, Image, Comparable products, Claims, User expectations, Product (internal consistency), Purpose, Statutes & Standards. Answers "how would we even *recognize* this risk materializing?" — i.e. the Detection dimension, from the exploratory side.
- **Heuristics of Software Testability** (Bach, v2.8) — five testability kinds (epistemic, value-related, project-related, subjective, intrinsic). Low testability is itself a first-class risk amplifier: it inflates FMEA's Detection score across the board.
- **Heuristic Risk-Based Testing** (Bach's classic paper) — inside-out (start from product internals, ask what can fail) vs. outside-in (start from risk catalogs/quality criteria, ask where the product is exposed). A complete framework runs **both directions and diffs the results**.

## 3.4 Test Heuristics Cheat Sheet (Hendrickson, Lyndsay, Emery — 2006; MoT expanded edition 2022)

The classic one-pager of concrete test-idea generators: Data Type Attacks (long names, special characters, boundary dates like Feb 30), Variable Analysis, Touch Points, Boundaries, Goldilocks (too big/too small/just right), CRUD, Configurations, Interruptions, Starvation, Position, Count (0/1/many), Multi-user, Flood, Dependencies, Constraints, Input Method, Sequences, Sorting, State Analysis, Map Making. Required reading in BBST Test Design; expanded by Simon Tomes & MoT contributors in 2022.

Framework role: this is the **leaf level** — once a risk and mitigation direction are chosen, these heuristics generate the *concrete test ideas*, i.e. the natural hand-off point to rf-mcp / test-generation agents.

## 3.5 Risk-Storming for Architecture (Simon Brown, riskstorming.com)

Not the MoT product — a same-named, independent technique from the C4-model author: visualize the architecture (C4 diagrams), have participants **individually and silently** annotate perceived risks on stickies (color-coded low/med/high), converge, then prioritize. Key mechanics to steal: **diagram-anchored elicitation** (risks attach to concrete architecture elements, not the void) and **silent individual ideation before group convergence** (anchoring-bias control — directly implementable as parallel agent runs with no shared context, merged afterwards).

## 3.6 Other Notable Formats (Brief)

- **TestSphere base game** — storytelling over drawn cards; the knowledge-sharing mechanic more than a risk protocol.
- **Oblique Testing** (Mike Talks) — Brian-Eno-style oblique strategy cards for lateral test ideas; useful randomness injector.
- **Exploratory Testing Tours** (Whittaker et al.) — themed tours (Landmark, Money, Antisocial, Back Alley…) = persona/lens catalog for exploratory charters.
- **RiskStorming variants in the field** — remote (Miro), agile-team-embedded (Gem Hill/BBC: quality-aspect subset without testing jargon), risk poker hybrids. The consistent empirical claims across experience reports: sessions surface risks teams wouldn't have found, create shared vocabulary, and are inclusive across roles; the consistent costs: time (2–3h), facilitation skill, Phase-3 vocabulary gap, remote overhead.

## 3.7 Comparative Summary

| Framework | Primary question | Structure | Knowledge encoding | Weakness an agent can fix |
|-----------|-----------------|-----------|--------------------|---------------------------|
| ISO 25010:2023 | What is quality? | 9×~35 taxonomy | Standard text | Abstract; no elicitation protocol |
| ISO 29119 / ISTQB RBT | How does risk drive testing? | Process | Standard text | Heavyweight; done once, goes stale |
| FMEA | What fails, how bad, do we catch it? | Table + S·O·D | Rating rubrics | Tedious; score-gaming; needs audit trail |
| HAZOP / STRIDE | What deviations/threats per element? | Guideword × element grid | Guideword catalog | Combinatorial explosion for humans |
| RiskStorming/TestSphere | Aspects → risks → mitigations | 3-phase workshop | 100-card deck | Phase-3 expertise gap; 2–3h ceremony |
| Would Heu-Risk It? | What's wrong with our *testing*? | 30 cards, 3 suits | Card deck + book | Reflection depends on experience present |
| HTSM 6.3 | What should the strategy consider? | 4 guideword areas | Guideword doc | Requires deep skill to apply well |
| FEW HICCUPPS | How do we recognize problems? | Oracle list | Mnemonic | Recall under pressure |
| Cheat Sheet | Which concrete test ideas? | Flat catalog | One-pager | Breadth without prioritization |
| Brown's risk-storming | Where is the architecture risky? | Diagram + silent stickies | C4 + process | Needs the diagram; scheduling |

---

# Part IV — Why Games Translate to Agents

Four structural properties make these formats unusually good raw material for agentic systems:

**1. Phases are protocols.** RiskStorming's three phases have typed inputs/outputs and completion criteria (exactly 6 aspects; top-N risks; every top risk has ≥1 mitigation). That is a state machine, and state machines are what MCP servers and hook-gated workflows enforce well. The facilitation guide is, functionally, a system prompt.

**2. Cards are chunked, addressable knowledge.** A card = stable ID + title + definition + example prompts + suit/category. That is precisely the granularity RAG and Agent Skills want: small, self-contained, composable, citable ("risk R-014 was elicited via card QA-07 *Security* × guideword *Late*"). Traceability to card IDs is what separates auditable elicitation from vibes.

**3. Constraints are the product.** Pick-exactly-six, timeboxes, one-page test plans — the games encode *forcing functions against completeness theater*. LLMs default to exhaustive, hedged, 40-item lists; the game rules are ready-made output contracts that fight exactly that failure mode.

**4. Multi-perspective mechanics map to multi-agent orchestration.** Silent individual ideation → group merge (Brown) is embarrassingly parallel persona agents + deterministic merge. Risk poker's independent-estimate-then-discuss is ensemble scoring + disagreement surfacing. The workshop's cross-role diversity (dev, PO, UX, ops) becomes a persona catalog.

What does **not** translate — and must be explicitly preserved for humans:

- **Shared understanding as the real output.** Every experience report says the artifact matters less than the conversation. An agent that produces a perfect risk register nobody discussed has delivered a smaller fraction of the value than it appears. The framework must be designed as a *facilitation amplifier* (prepare, expand, challenge, remember), not a workshop replacement.
- **Tacit context.** "The payment team is short-staffed and the last two incidents were config-related" lives in humans. Elicitation quality is bounded by context ingestion; the framework needs explicit context-gathering steps (docs, ADRs, incident history, code hotspots) before ideation.
- **Accountability.** Risk acceptance is a business decision. The framework records decisions and who made them; it never "accepts" a risk itself.

---

# Part V — Framework Design: QRisk

> Working name: **QRisk** — Quality Risk Intelligence. An AI-augmented risk analysis & mitigation framework packaged for agents as (a) Agent Skills, (b) a small MCP server, (c) persona subagents, with human review gates.

## 5.1 Design Principles

1. **Divergence to the LLM, convergence to code.** Risk *elicitation*, risk *phrasing*, mitigation *suggestion* = LLM tasks. Scoring arithmetic, ranking policy, de-duplication thresholds, register state, traceability graph = deterministic code. Never let the model compute or silently mutate priorities.
2. **Every claim traceable.** Each risk links to: the quality aspect(s) it threatens, the elicitation source (card ID / guideword / persona / document evidence), its scores with rubric citations, its mitigations, and eventually its tests and their latest results.
3. **Constraint-first outputs.** Default output contracts mirror the games: max 6 quality aspects, max 10 top risks, one-page strategy. Exhaustive mode exists but is opt-in.
4. **Human gates at decisions, not at ideation.** Agents may generate freely; nothing enters the *accepted* register, and no risk is *closed or accepted*, without a named human.
5. **Standards as profiles, not as the core.** The core ontology is minimal; ISO 25010:2023, HTSM quality criteria, TestSphere aspects, OWASP LLM/Agentic, ISO 26262 ASIL etc. are swappable **catalog packs** and **scoring policy packs**.
6. **Living register.** Risk analysis is an event-driven loop (new feature, incident, dependency bump, failed test pattern from robotframework-heal), not a ceremony. Re-assessment is cheap, so run it continuously and diff.
7. **Second-order honesty.** The framework applies a "Traps" check (Would-Heu-Risk-It style) to *its own output*: bias audit, coverage-illusion check, hallucinated-risk screening, and an explicit "what did we probably miss" section in every report.

## 5.2 Core Ontology (Minimal Data Model)

```yaml
QualityAspect:
  id: qa.security            # namespaced: catalog.slug
  catalog: iso25010-2023     # or testsphere, htsm, owasp-agentic…
  rank: 1..6                 # only for the selected six
  rationale: str             # why it matters HERE (product-specific)

Risk:
  id: R-0014
  statement: str             # "Because <condition>, <event> may occur, causing <consequence>"
  aspects: [qa.security, qa.data-integrity]
  elicited_by:               # full provenance
    method: riskstorming|hazop|stride|premortem|fmea|manual
    prompt_ref: card:TS-QA-07 | guideword:LATE | persona:ops
    evidence: [doc refs, incident IDs, code hotspots]
  scores:
    - policy: sod-v1         # or li-v1 (likelihood/impact), asil-v1…
      severity: 8            # each with rubric anchor citation
      occurrence: 4
      detection: 7
      derived: {rpn: 224, action_priority: HIGH}   # computed by server, never by LLM
      scored_by: [agent:security-persona, agent:ops-persona, human:many]
      disagreement: 0.31     # ensemble spread — surfaced, not averaged away
  status: proposed|reviewed|accepted|mitigating|closed|rejected
  decisions: [{who, when, action, note}]           # append-only audit log

Mitigation:
  id: M-0042
  risk_ids: [R-0014]
  treatment: reduce          # avoid|reduce|transfer|accept  (ISO 31000)
  lever: detection           # severity|occurrence|detection (FMEA)
  barrier: prevent           # prevent|detect|recover        (bow-tie)
  technique_ref: card:TS-TE-31 | htsm:stress | cheatsheet:interruptions
  concrete: str              # the actual proposed action / test charter
  tests: [rf:suite/path::TestName]                 # closes loop to Robot Framework
  residual_note: str         # what this does NOT cover — mandatory field
```

Two deliberate choices: `disagreement` is first-class (risk poker's insight — outlier discussion is where the value is), and `residual_note` is mandatory (anti-completeness-theater).

## 5.3 The Pipeline (RiskStorming, Generalized)

```
Phase 0  CONTEXT      ingest: product description, ADRs/C4 diagrams, requirements,
                      incident history, code hotspots (churn×complexity),
                      existing test coverage, robotframework-heal failure patterns
                          │
Phase 1  ASPECTS      propose ranked quality aspects from active catalog(s)
                      → HUMAN GATE: confirm/edit the six              [RiskStorming P1]
                          │
Phase 2  ELICIT       parallel divergent passes, merged deterministically:
                        a) persona subagents (security, perf, ux, ops,
                           compliance, data) — silent/independent      [Brown]
                        b) guideword sweep: HAZOP × interfaces,
                           STRIDE × dataflows, SFDIPOT × product map   [HAZOP/HTSM]
                        c) pre-mortem prompt per aspect                [Klein]
                        d) outside-in catalog match (OWASP, domain packs)
                        e) inside-out: code/architecture-anchored scan [Bach HRBT]
                      merge → embed-dedupe → cluster
                      → HUMAN GATE: select/edit top risks              [RiskStorming P2]
                          │
Phase 3  SCORE        ensemble scoring vs. rubric anchors; server computes
                      derived priority per active policy; disagreement report
                      → HUMAN GATE: contested scores resolved by humans
                          │
Phase 4  MITIGATE     per top risk: map techniques from decks/HTSM/cheat-sheet;
                      classify treatment/lever/barrier; draft test charters;
                      generate concrete RF test skeletons via rf-mcp   [RiskStorming P3]
                      → HUMAN GATE: accept mitigations, assign owners
                          │
Phase 5  EMIT         one-page test strategy (md), risk register (yaml/json),
                      29119-3-style plan section, traceability matrix,
                      board views (matrix, bow-tie, aspect heatmap)
                          │
Phase 6  LOOP         watch events (new PRs touching hot risks, incidents,
                      heal-events, coverage drift) → cheap re-assessment diff
                      → notify only on material change
```

Phase 2's five elicitation passes are the "ultimate" part: no single existing method runs persona diversity, guideword exhaustiveness, prospective hindsight, catalog matching, *and* code-anchored inside-out analysis together — humans can't afford to. Agents can, because marginal elicitation cost is near zero; the scarce resource shifts to **convergence quality**, which is why dedupe/cluster/gate design matters more than generation.

## 5.4 Packaging: Skill vs. MCP vs. Subagent — the Hybrid

Consistent with the rf-mcp architectural evaluation (knowledge → Skills, state/determinism → few MCP tools):

| Layer | Packaging | Contents | Why here |
|-------|-----------|----------|----------|
| Knowledge | **Agent Skills** (SKILL.md + resources) | Catalog packs (ISO 25010:2023, HTSM 6.3, TestSphere-style aspects*, OWASP LLM/Agentic, domain profiles), guideword sets, scoring rubric anchors, phase playbooks, output contracts, persona definitions | Versioned auditable text; zero runtime cost; progressive disclosure; distributable via plugin marketplaces |
| State & determinism | **MCP server** (FastMCP), ~6 tools | `session` (create/configure policy+catalogs) · `register` (CRUD risks/mitigations, append-only decisions) · `score` (rubric-anchored ensemble intake → deterministic derive) · `dedupe` (embedding cluster/merge proposals) · `trace` (link risks↔tests↔results; query matrix) · `export` (md/yaml/json/29119 profile) | Structured, loggable invocations; the audit trail lives where observability exists; arithmetic and ranking never in the model |
| Orchestration | **Subagents + hooks** | Persona agents (isolated context = "silent ideation"), a facilitator agent enforcing phase gates, hooks that block phase transitions without human sign-off | Parallelism, anchoring-bias control, gate enforcement |
| Integration | existing stack | rf-mcp (execute/generate tests from charters), robotframework-heal (failure patterns as Occurrence/Detection evidence feed), robotframework-agenteval (evaluate the framework itself), CI (re-assessment triggers) | Closes aspect→risk→mitigation→test→result loop |

\* Licensing note: TestSphere/RiskStorming and Would-Heu-Risk-It card *content* is commercial IP (Ministry of Testing / Lena Pejgan Wiberg). The framework should ship the *mechanics* plus open catalogs (ISO-derived aspect names, HTSM is freely published with attribution, OWASP is open), and support licensed deck packs as a bring-your-own option — or a collaboration with MoT, who are visibly experimenting with AI RiskStorming themselves.

## 5.5 Example Tool Surface (MCP)

```python
# qrisk-mcp — deliberately small, stateful core (FastMCP)

@mcp.tool()
def create_session(product: str, context_refs: list[str],
                   catalogs: list[str] = ["iso25010-2023"],
                   scoring_policy: str = "sod-ap-v1",
                   max_aspects: int = 6, max_top_risks: int = 10) -> SessionInfo: ...

@mcp.tool()
def upsert_risks(session_id: str, risks: list[RiskDraft],
                 elicited_by: Provenance) -> UpsertResult:
    """Drafts only enter as status=proposed. Dedupe candidates returned,
    never auto-merged. Decisions require a human principal."""

@mcp.tool()
def submit_scores(session_id: str, risk_id: str,
                  scores: ScoreVector, scored_by: Principal,
                  rubric_anchors: list[str]) -> ScoreState:
    """Server computes RPN/AP/priority per policy; returns ensemble
    disagreement. Rejects scores without rubric anchor citations."""

@mcp.tool()
def link_trace(session_id: str, edges: list[TraceEdge]) -> TraceState:
    """aspect→risk→mitigation→test→result graph; queryable both directions."""

@mcp.tool()
def export(session_id: str, fmt: Literal["register-yaml","strategy-md",
           "iso29119-plan-md","trace-matrix-csv"]) -> FileRef: ...
```

Everything else — phase playbooks, elicitation prompts, persona briefs, rubric texts, card catalogs — is skill content, not tools.

## 5.6 Worked Micro-Example (Phase 2b, guideword sweep)

Element: `POS checkout → payment terminal (card/EC terminal)` · Guideword: **Late**
Persona: ops · Catalog aspect under threat: `qa.reliability`, `qa.compliance`

> **R-0031** — *Because the card terminal acknowledges asynchronously, a late (>30s) confirmation may be recorded as failed while the cardholder was charged, causing double-charge complaints and a fiscal-journal export that disagrees with the PSP settlement file.*
> elicited_by: guideword:LATE × interface:card-terminal, persona:ops
> scores (sod-ap-v1): S7 O5 D8 → AP HIGH (D8: no current reconciliation test)
> mitigations: M-0102 *reduce/detection/detect* — nightly reconciliation check PSP-settlement ↔ fiscal journal (RF suite draft); M-0103 *reduce/occurrence/prevent* — idempotent booking on terminal retry. residual: chargebacks initiated at issuer remain undetected until settlement +2d.

This is the level of concreteness the framework must reach to be worth more than a workshop — note that it required Phase-0 context (the team's actual fiscal/payment reality), which is the point.

---

# Part VI — Evaluation, Limitations & Honest Caveats

## 6.1 How to Evaluate QRisk Itself (robotframework-agenteval territory)

| Dimension | Metric | Method |
|-----------|--------|--------|
| Elicitation recall | % of retrospectively known risks (from real incident post-mortems) the pipeline surfaces on the pre-incident snapshot | Backtesting on historical projects — the single most convincing eval |
| Precision / hallucination | % of proposed risks judged plausible-and-applicable by domain experts | Blind expert review; LLM-judge only after calibration against humans (LLM judges hallucinate, drift, and defer rhetorically — calibrate per system, per the multi-agent risk-analysis literature) |
| Diversity | Cluster count / semantic spread vs. single-pass baseline | Embedding-space dispersion; compare 5-pass ensemble vs. one generic prompt |
| Prioritization sanity | Rank correlation of framework priority vs. expert panel ranking | Kendall's τ on shared risk sets |
| Score stability | Variance of S/O/D across reruns and model versions | Repeated runs; rubric-anchor citations should reduce variance measurably |
| Process value | Do teams change decisions? Time-to-strategy vs. workshop? | Field pilots; honest comparison including facilitation value lost |

## 6.2 Failure Modes of AI-Augmented Risk Analysis (the framework's own Trap cards)

1. **Plausible-risk hallucination** — fluent risks that don't apply to this product. Countermeasure: evidence-linking requirement; risks with zero context evidence get flagged `speculative`.
2. **Completeness theater** — a 60-item register that *feels* thorough and anesthetizes vigilance. Countermeasure: hard output constraints; mandatory "what we probably missed" section; Would-Heu-Risk-It trap audit pass.
3. **Sycophantic scoring** — model mirrors the user's framing ("this is probably low risk, right?"). Countermeasure: scoring agents never see human hypotheses, only rubric + risk statement + evidence; independent-then-reveal protocol.
4. **Anchoring across personas** — shared context contaminates "independent" passes. Countermeasure: isolated subagent contexts (this is why subagents, not one chat).
5. **Stale confidence** — register decays silently. Countermeasure: TTL on scores; event-driven re-assessment; freshness shown in every export.
6. **Automation of the wrong thing** — replacing the conversation instead of feeding it. Countermeasure: default deliverable is a *workshop briefing pack* (pre-elicited candidates for humans to fight over), full-auto mode clearly labeled second-class.
7. **The framework as attack surface** — an MCP server with write access to quality decisions is itself a risky tool (state-changing capability is the most prevalent MCP risk category in 2026 analyses; skills add an observability gap since their effects play out inside model reasoning). Countermeasure: apply your 16-pattern secret-exposure catalog; read-only defaults; human principal required for state transitions; pinned versions.

## 6.3 What This Framework Deliberately Does Not Claim

- It does not compute "true" risk. Ordinal rubrics multiplied together remain a sorting heuristic; the standards themselves warn against threshold worship.
- It does not replace domain regimes. For ISO 26262/14971 contexts it is an assistant feeding the mandated process, never the process.
- It does not make acceptance decisions. ISO 31000's *accept* is a named human's signature, by design.

---

# Part VII — Roadmap

| Stage | Scope | Proof point |
|-------|-------|-------------|
| **0. Spike** (1–2 wks) | Skill-only: RiskStorming 3-phase playbook + ISO 25010:2023 catalog + S·O·D rubric as SKILL.md set; register as YAML in repo; no server | Run against one real product (e.g. a POS/payment evaluation — fiscal-compliance risks are a perfect testbed); compare to what the human analysis already found |
| **1. Determinism** | qrisk-mcp: session/register/score/export; append-only decisions; AP policy table | Backtest vs. one historical incident set |
| **2. Ensemble** | Persona subagents, isolated contexts, dedupe/cluster tool, disagreement surfacing | Diversity + recall metrics vs. Stage-0 single-pass |
| **3. Loop closure** | trace tool; rf-mcp charter→test generation; heal-events as Detection evidence; CI re-assessment diffs | One risk demonstrably re-scored by a production failure signal |
| **4. Community** | Open catalog packs; workshop-briefing mode; MoT/RiskStorming conversation re licensed deck packs; RoboCon 2027 material | External pilot team |

The Stage-0 spike is genuinely small: the entire Part-V knowledge layer is text, and you already have the extensibility scaffolding from the Claude-Code Riskstorming design and robotframework-agentskills distribution work.

---

# References

**Standards & official sources**
- ISO/IEC 25010:2023 — Product quality model. https://www.iso.org/standard/78176.html · online browsing: https://www.iso.org/obp/ui/en/#!iso:std:78176:en
- arc42 quality model — ISO 25010:2023 change analysis. https://quality.arc42.org/articles/iso-25010-update-2023 · https://quality.arc42.org/standards/iso-25010
- iso25000.com — sub-characteristic definitions. https://iso25000.com/index.php/en/iso-25000-standards/iso-25010
- ISO/IEC/IEEE 29119-1 — Concepts & definitions (risk-based testing mandate). https://wildart.github.io/MISG5020/standards/ISO-IEC-IEEE-29119-1.pdf
- Reid, S. — ISO/IEC/IEEE 29119: The New International Software Testing Standards. https://www.stureid.info/wp-content/uploads/2015/08/ISO-29119-The-New-International-Software-Testing-Standards.pdf
- ISTQB Glossary — risk-based testing. https://istqb-glossary.page/risk-based-testing/
- ISO 31000, ISO/IEC 42001, ISO/IEC 23894, ISO/IEC 25012/25019/25059, ISO 26262, ISO 14971, IEC 62443, DO-178C, EN 50128 — via iso.org / iec.ch (paywalled primary texts)
- NIST AI RMF 1.0. https://www.nist.gov/itl/ai-risk-management-framework
- OWASP Top 10 for LLM Applications / Agentic Applications. https://owasp.org/www-project-top-10-for-large-language-model-applications/ · https://genai.owasp.org

**Risk techniques**
- Felderer & Schieferdecker et al. — A Taxonomy of Risk-Based Testing. https://arxiv.org/pdf/1912.11519 · standards-tailoring follow-up: https://arxiv.org/pdf/1905.10676
- Integrating software quality models into risk-based testing, *Software Quality Journal*. https://link.springer.com/article/10.1007/s11219-016-9345-3
- FMEA/RPN mechanics & critiques: https://www.hbkworld.com/en/knowledge/resource-center/articles/examining-risk-priority-numbers-in-fmea · https://accendoreliability.com/prioritizing-risk-in-an-fmea/ · https://www.regulatorymedicaldevice.com/2025/04/risk-priority-number-rpn-ISO-14971.html
- Bach, J. — Heuristic Risk-Based Testing. https://www.satisfice.com/articles/hrbt.pdf

**Games & community practice**
- RiskStorming (MoT). https://www.ministryoftesting.com/testsphere/riskstorming · relaunch: https://www.ministryoftesting.com/news/riskstorming-is-here · AI experiments: https://www.ministryoftesting.com/moments/beren-van-daele-and-ai-riskstorming
- RiskStorming Online (Van Daele). https://riskstormingonline.com/
- Experience reports: https://www.ministryoftesting.com/articles/riskstorming-workshop-experience · https://www.ministryoftesting.com/articles/how-to-run-a-remote-risk-storming-workshop-with-testsphere · https://www.ministryoftesting.com/articles/riskstorming-in-agile-teams-with-testsphere · https://scottlogic.github.io/practitioners-guides/pages/risk-analysis-and-pre-mortems/ · https://lisacrispin.com/2022/03/20/quick-risk-strategizing/
- TestSphere expansion background (Van Daele). https://isleof.it/category/software-testing/testsphere/
- Would Heu-Risk It? (Wiberg/Pejgan). https://pejgan.se/wouldheu-riskit.html · deck: https://store.ministryoftesting.com/products/would-heu-risk-it-single-deck · book: ISBN 9798543871720
- HTSM v6.3 (Bach). https://www.satisfice.com/download/heuristic-test-strategy-model · annotated: https://www.developsense.com/resource/htsm.pdf
- FEW HICCUPPS (Bolton). https://developsense.com/blog/2012/07/few-hiccupps · SFDIPOT history: https://developsense.com/blog/2014/07/how-models-change
- Test Heuristics Cheat Sheet (Hendrickson/Lyndsay/Emery; MoT 2022 edition). https://www.ministryoftesting.com/articles/test-heuristics-cheat-sheet
- Risk-storming for architecture (Brown). https://riskstorming.com/

**AI & agent risk (for Part VI)**
- Reid et al. — Risk Analysis Techniques for Governed LLM-based Multi-Agent Systems. https://arxiv.org/abs/2508.05687
- MCP/Skills risk landscape 2026 (Noma Security via Help Net Security). https://www.helpnetsecurity.com/2026/05/05/ai-agent-security-skills-blind-spots/
- MCP-in-SoS risk assessment framework. https://arxiv.org/html/2603.10194v1

---

*Prepared as research input for an Agentic QA Orchestrator component. Card-deck contents referenced descriptively; TestSphere, RiskStorming and Would Heu-Risk It? are commercial products of Ministry of Testing Ltd. and Lena Pejgan Wiberg respectively — mechanics are discussed under fair-use analysis, card texts are not reproduced.*

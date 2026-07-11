Use the risk-quickscan skill (.claude/skills/risk-quickscan/SKILL.md), but with
a SECURITY focus and the opt-in security catalogs enabled.

Setup:
1. `risqlet init` (pre-authorized). Then edit `.risqlet/config.yaml` to enable the
   security packs: set `catalogs: [iso25010, techniques, heuristics, guidewords,
   mitre-attack, owasp-web]`.
2. `risqlet catalog licenses --json` — capture the output (you will report it;
   note that mitre-attack carries a required MITRE notice).

Task: a security-framed scan of this repository's exposure. Read the codebase —
its external interfaces, command/execution surfaces, authentication and default
configuration, and any automation that acts on the host — and elicit security
risks grounded in what you find.

Use the security catalog entries as your lenses and cite them in prompt_ref:
- adversary tactics via `mitre-attack.enterprise-tactics` (and
  `mitre-attack.initial-access-review` / `privilege-and-lateral` /
  `exfiltration-and-impact`);
- web/service risk categories via the `owasp-web.*` entries
  (e.g. `owasp-web.broken-access-control`, `owasp-web.security-misconfiguration`,
  `owasp-web.identification-and-authentication-failures`,
  `owasp-web.server-side-request-forgery`).

Write well-evidenced `proposed` risks (real file paths in evidence), each with a
`prompt_ref` pointing at the security catalog entry that surfaced it.

Rules: only `.risqlet/` may be written; no code changes, no events. Finish with:
- `risqlet validate --json` (MUST show 0 catalog warnings — the security refs
  must resolve, proving the packs loaded),
- `risqlet catalog licenses --json`,
- the list of risks with their security prompt_refs,
in your final answer.

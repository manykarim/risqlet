# Scoring rubrics

Scores are ordinal sorting heuristics, never measurements. Your job: propose
factor values with one **anchor** per factor — a short phrase tying the value
to observable reality. `risqlet score` refuses anchorless scores; validate
recomputes everything, so never write `derived` yourself.

Anchor discipline: cite evidence where any exists ("det 8: no automated check
— coverage gap noted in context brief"). Uncertain between two values? Present
both with anchors and let the human choose — disagreement is signal, not
noise. Do not let the human's hoped-for answer steer you; score first, then
discuss.

## sod-ap-v1 (default): Severity × Occurrence × Detection, 1–10

### Severity — how bad if it happens

| Value | Anchor pattern |
|---|---|
| 9–10 | safety/legal harm, irreversible data loss, existential money or trust damage |
| 7–8 | serious user harm or revenue impact, recoverable with real cost; compliance exposure |
| 5–6 | feature unusable or wrong for many users; workaround exists but hurts |
| 3–4 | annoyance, cosmetic-plus; degraded experience for some users |
| 1–2 | barely noticeable, internal only |

### Occurrence — how likely the cause occurs

| Value | Anchor pattern |
|---|---|
| 9–10 | happens routinely already / structurally guaranteed under normal load |
| 7–8 | expected within weeks; the trigger is a common user action or event |
| 5–6 | expected within a release cycle; trigger is uncommon but regular (month-scale) |
| 3–4 | needs an unusual combination; seen occasionally in the field (quarter/year) |
| 1–2 | needs a rare coincidence or a determined attacker with deep access |

### Detection — how likely we MISS it before users are hit (high = poor)

| Value | Anchor pattern |
|---|---|
| 9–10 | nothing would catch it — no test, no monitor, silent failure mode |
| 7–8 | only incidental discovery (a human happens to look); no automated signal |
| 5–6 | indirect signals exist (generic error rates) but nothing specific |
| 3–4 | a test or alert covers the area, with known gaps |
| 1–2 | specific automated check or alarm fires before or immediately at impact |

Detection is the tester's lever: it asks "how good is our net?" — score it
against checks that *exist*, not checks that are planned.

## li-v1 (lightweight): Likelihood × Impact, 1–3

Likelihood — 3: expected in normal use · 2: plausible this quarter ·
1: needs bad luck. Impact — 3: users/money/data hurt badly · 2: real but
recoverable pain · 1: minor annoyance. Same anchor discipline, one per factor.

## After scoring

```bash
risqlet score --all && risqlet validate --json
```

Read back the computed `action_priority`/`priority` per risk. If a computed
priority contradicts your intuition, say so explicitly — either the anchors
are wrong or the intuition is; the human decides which.

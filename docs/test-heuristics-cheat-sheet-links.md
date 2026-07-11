# Test Heuristics Cheat Sheet — Link Index

All hyperlinks embedded in the Ministry of Testing *Test Heuristics Cheat Sheet*, grouped by section with a short description of each.

> Source: Ministry of Testing — Test Heuristics Cheat Sheet (© 2006 Quality Tree Software, Inc.; © 2022 Ministry of Testing Ltd.)

---

## Web Tests — Syntax (page 2)

| Link | Description |
|------|-------------|
| [HTML Syntax Checker](https://validator.w3.org) | W3C Markup Validation Service — interactive tool to check HTML for syntax errors. |
| [CSS Syntax Checker](http://jigsaw.w3.org/css-validator/) | W3C CSS Validation Service (Jigsaw) — interactive tool to validate CSS. |

## API Tests (page 3)

| Mnemonic | Author | Link | Description |
|----------|--------|------|-------------|
| **BINMEN** | Gwen Diagram & Ash Winter | [MoT Dojo lesson](https://www.ministryoftesting.com/dojo/lessons/how-to-turn-a-403-into-a-202-at-the-api-party-gwen-diagram-ash-winter?s_id=10395318) | Ministry of Testing talk "How to Turn a 403 into a 202 at the API Party." Source of the BINMEN API heuristic (Boundary, Invalid entries, NULL, Method, Empty, Negative). *(May sit behind MoT membership.)* |
| **POISED** | Amber Race | [Twitter/X post](https://twitter.com/marianneduijst/status/965577461860896768?s=20) | Sketchnote by Marianne Duijst summarizing the POISED API heuristic (Parameters, Output, Interop, Security, Errors, Data). |
| **VADER** | Stuart Ashman | [qa-matters.com article](https://qa-matters.com/2016/07/30/vader-a-rest-api-test-heuristic/) | Blog post introducing the VADER REST API heuristic (Verbs, Authorization, Data, Errors, Responsiveness). |

## Mobile / Device / Tablet (page 3)

| Mnemonic | Author | Link | Description |
|----------|--------|------|-------------|
| **Mobile App Testing** | Daniel Knott | [MoT Dojo lesson](https://www.ministryoftesting.com/dojo/lessons/mobile-app-testing-mnemonic?s_id=10395137) | Ministry of Testing lesson on Daniel Knott's mobile app testing mnemonic. *(May sit behind MoT membership.)* |

## Heuristics (page 6)

| Mnemonic | Author | Link | Description |
|----------|--------|------|-------------|
| **RCRCRC** | Karen N. Johnson | [Heuristics & Mnemonics PDF](http://karennicolejohnson.com/wp-content/uploads/2012/11/KNJohnson-2012-heuristics-mnemonics.pdf) | PDF of regression heuristic (Recent, Core, Risky, Configuration-sensitive, Repaired, Chronic). **⚠ Currently unreachable — returns HTTP 403.** |
| **FAILURE** | Ben Simo | [questioningsoftware.com](https://www.questioningsoftware.com/2007/08/failure-usability.html) | Blog post on the FAILURE usability heuristic (Functional, Appropriate, Impact, Log, UI, Recovery, Emotions). |
| **WWWWWHKE** | Darren McMillan | [bettertesting.co.uk](http://www.bettertesting.co.uk/content/?p=857) | Blog post on the "wiki"-sounding questioning heuristic (Who/What/When/Where/Why/How + Knowledge & Experience). |
| **Diversity & Inclusion** | Callum Akehurst-Ryan | [WordPress blog](https://callumakehurstryansblog.wordpress.com/2019/02/06/how-diversity-inclusion-can-improve-testing/) | Blog post on how diversity & inclusion can improve testing. |
| **Combat Bias with Heuristics of Diversity** | Ash Coleman | [MoT Dojo lesson](https://www.ministryoftesting.com/dojo/lessons/combating-bias-with-heuristics-of-diversity-ash-coleman?s_id=10394959) | Ministry of Testing talk on combating bias (Does this work for me / them / someone I've never met?). *(May sit behind MoT membership.)* |
| **Seven Dwarfs** | Cassandra H. Leung | [MoT Dojo lesson](https://www.ministryoftesting.com/dojo/lessons/mis-using-personas-with-the-seven-dwarfs-cassandra-h-leung?s_id=10713757) | Ministry of Testing talk on (mis)using personas with the Seven Dwarfs. *(May sit behind MoT membership.)* |
| **Specs/Designs Watchlist** | Gerard McCann | [MoT Dojo lesson — Larvae Hunting](https://www.ministryoftesting.com/dojo/lessons/larvae-hunting-heuristics-and-cheat-sheet?s_id=10394959) | Ministry of Testing "Larvae Hunting" heuristics & cheat sheet — watch for ambiguity, weasel words, fudge, jargon, over/under-simplification. *(May sit behind MoT membership.)* |
| **TORCH** | Simon Tomes | [Google Doc](https://docs.google.com/document/d/1rKYmujVhUlNgfeYIBot12Z8E7S0Y_Z4pk5pefK7xO3g/edit) | Shared Google Doc describing TORCH (Timer, Oracles, Risks, Consider these questions, Heuristics). *(Requires Google sign-in.)* |
| **MCOASTER** | Michael Kelly | [InformIT article](https://www.informit.com/articles/printerfriendly/457506) | Article on Michael Kelly's MCOASTER test-management heuristic (Mission, Coverage, Obstacles, Audience, Status, Techniques, Environment, Risk). |

## Heuristics (page 7)

| Mnemonic | Author | Link | Description |
|----------|--------|------|-------------|
| **TuTTu and TaTTa** | Mark Winteringham | [Talk page](https://www.mwtestconsultancy.co.uk/say-tatta-to-your-tuttu-talk/index.html) · [YouTube](https://www.youtube.com/watch?v=uIDvGzQdoxc&t=285s) | "Say TaTTa to your TuTTu" — Testing the UI vs. Through the UI; Testing the API vs. Through the API. Talk page plus accompanying YouTube video. |
| **SACRED** | Richard Bradshaw | *(no working URL — see note)* | Automation design heuristic (State management, Actions, Codified oracle, Reporting, Execution, Deterministic). The cheat sheet links this entry, but no resolvable target URL is embedded in the PDF. |
| **TRIMS** | Richard Bradshaw | *(no working URL — see note)* | Automation quality heuristic (Targeted, Reliable, Informative, Maintainable, Speedy). Same as above — no resolvable target embedded. |

---

## Notes

- **PDF links:** Only one link in the cheat sheet is itself a PDF — Karen N. Johnson's *Heuristics & Mnemonics* (RCRCRC). It currently returns **HTTP 403** and could not be downloaded.
- **Walled / auth-required:** Ministry of Testing "Dojo" lessons (BINMEN, Mobile App Testing, Combat Bias, Seven Dwarfs, Larvae Hunting) may require MoT membership; the TORCH Google Doc requires Google sign-in.
- **No article body:** The W3C validators are interactive tools, the POISED link is a Twitter/X post, and TuTTu/TaTTa includes a YouTube video — none have substantial extractable text.
- **Duplicates removed:** Several links appeared twice in the PDF (Mobile App Testing, Diversity/Combat Bias, Larvae Hunting, TuTTu/TaTTa) and are listed once here.

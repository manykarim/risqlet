# Clean-Room Authoring Protocol for Catalog Content

The packaged catalogs express long-established software-testing and risk-analysis
concepts. Concepts, methods, and names are not copyrightable; specific expressive
text is. This protocol keeps our expression original so the packs can be licensed
CC BY 4.0 without infringing anyone's card decks, models, or standards.

## Rules

1. **Facts are fair game.** Concept names (e.g. "stress testing", "STRIDE",
   the ISO/IEC 25010:2023 characteristic names, the SFDIPOT mnemonic letters),
   originator names, and bibliographic citations may be used freely as facts.
2. **Source text is off limits.** While writing or editing entry text
   (`summary`, `prompts`, guideword annotations), do not have open, consult, or
   copy from: TestSphere or RiskStorming cards, Would Heu-Risk It? cards or book,
   the Heuristic Test Strategy Model document, ISO/IEC standards, the Test
   Heuristics Cheat Sheet, or any other licensed source. Write from your own
   understanding of the concept.
3. **Every entry carries provenance.** One line naming the concept's origin or
   noting that it is common professional practice with no single originator.
   Provenance credits ideas; it does not import text.
4. **Attribution is not affiliation.** Mentioning ISO, Ministry of Testing,
   Satisfice, or any originator never implies endorsement. The `iso25010` pack's
   definitions are original paraphrases of publicly known characteristic *names*
   and are not the standard's text; consult the actual standard for normative use.
5. **Contributions affirm compliance.** Every PR touching `src/risqlet/catalog/packs/`
   must state: *"Entry text authored without consulting licensed source text
   (CLEAN-ROOM.md rule 2)."*
6. **Slugs are stable public identifiers.** Risk registers cite entries by id
   (`techniques.stress-testing`). Do not rename or delete slugs; supersede with
   new entries and keep the old ones.
7. **Standard taxonomy names are facts.** The names of established taxonomies —
   ISO/IEC 25010 characteristics, MITRE ATT&CK tactics, OWASP risk categories,
   STRIDE letters — may be used as factual references and coverage checklists.
   Their *descriptive text* and identifiers (e.g. ATT&CK `Txxxx` technique IDs)
   may not be reproduced; write original definitions and prompts around the
   names.
8. **Reproduce required notices.** When a source's terms require an attribution
   or permission statement (e.g. MITRE ATT&CK), put it verbatim in the pack's
   `notice` field. `risqlet catalog licenses` surfaces every pack's license,
   attribution, and notice so redistributors can meet the obligations.

## Licensing

- Code: Apache-2.0 (`LICENSE`).
- Catalog pack content (`src/risqlet/catalog/packs/`): CC BY 4.0 (`LICENSE-CATALOG`).
  Reuse requires attribution to "the risqlet contributors".

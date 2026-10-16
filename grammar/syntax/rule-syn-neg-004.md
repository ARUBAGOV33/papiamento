---
id: RULE_SYN_NEG_004
title: Double negation - no together with other negation elements
status: draft
source: SIN2015
page: "90-91; 96-97"
severity: info
reviewed_by: ""
---

## Rule
Double negation is using the negation element no together with one or more other negation elements. The other elements can appear after the predicate, or before or after the sentence. Sintaxis calls it a phenomenon typical of creole languages such as Papiamento, though some non-creole languages have it too.

## Source
Manual di Gramatica di Papiamento: Sintaxis (2015), §5.3 "Elemento di negacion", pp. 90–91, and §5.5 "Negacion dobel", pp. 96–97.
"Negacion dobel ta e fenomeno linguistico den cua ta uza e elemento di negacion no hunto cu un of mas elemento di negacion."

## Correct
- Mi no a biaha nunca den avion.
- Nada (no) a sosode na e fiesta ayeranochi.
- Niun hende (no) a bay scucha e charla di e profesor na universidad.
- Mi no lo biaha pa Hulanda e aña aki tampoco.
- Mi tanta no a invita ningun hende/niun hende pa su hacimento di aña.

## Notes
- Severity is info. The old pack had "acceptable" (not a level in this repo); the point is the same: double negation is grammatical and a checker must not "fix" it by removing a negation element.
- The other negation elements are hamas, nunca, tampoco, ni, nada, ningun hende / niun hende and ningun caminda / niun caminda (§5.3, pp. 90–91). no is the basic one and the only one that can appear on its own in a sentence (p. 90).
- Whether no is required depends on where the other element stands: after the predicate, no is obligatory (RULE_SYN_NEG_005); before the predicate, no is optional (RULE_SYN_NEG_006). More than two elements: RULE_SYN_NEG_007.
- The book prints (no) in brackets where no is optional.
- hamas and nunca both mean "never" and are both correct (_meta/invariants.md).

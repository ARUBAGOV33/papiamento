---
id: RULE_SYN_NEG_005
title: When another negation element follows the predicate, no is required
status: draft
source: SIN2015
page: "90-91; 97"
severity: error
reviewed_by: ""
---

## Rule
When the other negation element or elements appear after the predicate, the negation element no is obligatory. In the book's examples these elements are hamas, nunca, tampoco, nada, ningun hende / niun hende and ningun caminda / niun caminda.

## Source
Manual di Gramatica di Papiamento: Sintaxis (2015), §5.3 "Elemento di negacion", pp. 90–91, and §5.5.1 "Otro elemento di negacion patras di e predicado", p. 97.
"Ora cu e otro elemento(nan) di negacion ta aparece patras di e predicado, e uzo di e elemento di negacion no ta obligatorio"

## Correct
- Mi lo no bishita e persona ey hamas.
- E mucha muhe no a duna su mucha homber un sunchi tampoco.
- Gabriel no a contesta su mama na un manera fresco nunca.
- Christopher no a bishita Jason nunca.
- Mi no lo biaha pa Hulanda e aña aki tampoco.
- Mi tanta no a invita ningun hende/niun hende pa su hacimento di aña.
- E carpinte no por a haya su martiu ningun caminda/niun caminda den su shop.

## Notes
- The old rule pack had this rule reversed: it said no is optional when the other negation element follows the predicate. Both p. 91 and p. 97 say the opposite ("obligatorio"), so this file follows the book. The old pack's RULE_SYN_NEG_006 was reversed the same way.
- Severity is error because the book says no is obligatory here. The book prints no sentence without it, so there is no Incorrect example; a checker flags a sentence where one of these elements follows the predicate and no is missing before the predicate.
- Scope for a checker: §5.5.3 (p. 97) prints sentences with negation elements on both sides of the predicate where no stays optional, e.g. Hamas y nunca Maria ni Hose (no) a duna mi nada. So no is required only when no negation element comes before the predicate. This reading is drawn from the book's examples; the page does not state it in words.
- ni is also a negation element. The examples of §5.3 and §5.5 have ni only before the predicate (RULE_SYN_NEG_006), so it is left out of the list above. §5.4.4 (p. 95) does print ni after the predicate, with no present: "E señora no a bari ni mop e cas."
- With the particle lo, no can stand before or after lo (Mi lo no …, Mi no lo …); see RULE_SYN_NEG_002.
- Related: RULE_SYN_NEG_004 (double negation), RULE_SYN_NEG_006 (element before the predicate), RULE_SYN_NEG_007.

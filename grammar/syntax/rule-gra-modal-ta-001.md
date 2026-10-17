---
id: RULE_GRA_MODAL_TA_001
title: Modal verbs do not take the particle ta
status: draft
source: MOR2010
page: "39"
severity: error
reviewed_by: ""
---

## Rule
The verbs ke/kier, mag (di), mester (di), por and sa(bi) do not take the particle ta. Following the maintainer ruling, gusta used as a modal verb does not take ta either.

## Source
Manual di Gramatica di Papiamento: Morfologia (2010), §6.2.3.1 "Verbo sin uzo di e particula ta", p. 39.
"E verbonan conoce, ke/kier, mag (di), mester (di), por, sa(bi), ta y tin(i) no ta uza e particula ta"

## Correct
- Semper bo kier haci loke bo ta haya ta bon.
- Mañan nos docente mester asisti na un conferencia.

## Notes
- gusta conflicts with the books. Morfologia §6.2.3.2 (same page, p. 39) and Sintaxis §2.2.4.1 II.1 (SIN2015 p. 31) list gusta among the verbs used both with and without ta, e.g. "Mucha (ta) gusta core den un espacio grandi." The maintainer ruling in `_meta/invariants.md` says "Modals (kier, mester, por, sa, gusta, mag) never take **ta**." This file follows the ruling. The conflict is open in `sources/errata.tsv` (err-0023, draft): on 2026-10-17 the maintainer had not yet decided whether gusta takes ta. Until then RULE_GRA_MODAL_TA_001 leaves gusta out.
- The invariants table gives the checker's pattern: mi ta kier bay is wrong, mi kier bay is right (`_meta/invariants.md`, Grammar). The book page itself prints no wrong sentence, so it is not listed under Incorrect.
- Only ta is excluded. These verbs do take other particles: Sintaxis p. 30 prints "Mi tata no tabata sa cu nos a bishita nos bisiña nobo.", "Semper bo tabata/lo kier e cas aki pa biba." and "Pa e les di matematica nos docente lo mester (di) un liniaal y un passer." kier, mester and por put the particle a after them, not before (Morfologia §6.2.3.3, p. 40).
- Ta enfatico is not the particle ta and must not be flagged: "Ta kier e kier bay e boda." (Sintaxis §1.5.2.1, Nota 3, p. 18) emphasises the predicate by putting ta and a copy of the verb first.
- Which verbs are modal: Morfologia §6.2.2.1 (p. 37) lists gusta, kier, mag (di), mester, por, sa and tin cu / tin di, and says sigui, cuminsa, caba di and others can also be used as modals (p. 38). The ruling, and this rule, cover kier, mester, por, sa, gusta and mag.
- Sintaxis §2.2.4.1 I (p. 29) gives the same no-ta list for ke/kier, (tin) mester (di) and sa(bi).
- Not a modal, but a related conflict: Morfologia p. 39 lists conoce among the verbs without ta, while Sintaxis p. 31 lists conoce among the verbs used with or without ta. Reviewers may want an errata row for it as well.
- Related rulings: por has no gerund (err-0010); lo and a never combine (`_meta/invariants.md`).

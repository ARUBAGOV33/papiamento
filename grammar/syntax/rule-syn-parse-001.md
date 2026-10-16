---
id: RULE_SYN_PARSE_001
title: In Sintaxis the predicate is only the verbal part, not everything after the subject
status: draft
source: SIN2015
page: "3"
severity: info
reviewed_by: ""
---

## Rule
Traditional analysis splits a sentence into subject and predicate, so everything that is not the subject counts as predicate. Sintaxis does not: it divides the sentence by the grammatical function of each part, and counts as predicate only the part that consists of a verb, or of a verb with another grammatical element. The other material after the subject is analysed as other sentence parts, such as complements.

## Source
Manual di Gramatica di Papiamento: Sintaxis (2015), "Sistema di analisis sintactico", p. 3.
"ta considera predicado solamente e parti di frase cu tin e funcion defini den Capitulo 2.2.1 y cu ta consisti solamente di verbo of di verbo cu otro elemento gramatical"

## Correct
- E mucha muhe tabata bula di un banda pa otro. (Traditional analysis: subject E mucha muhe; predicate tabata bula di un banda pa otro.)
- E mucha muhe tabata bula di un banda pa otro. (Sintaxis: subject E mucha muhe; predicate tabata bula; complement di un banda pa otro.)

## Notes
- Severity is info: this tells annotators and the checker how the book's terms are meant. It is nothing to flag in a text.
- The same page states the book's typographic convention: in its examples the main element is in italics and the related element is underlined.
- The function of the predicate is defined in §2.2.1 (RULE_SYN_PRED_001). Sentence parts other than subject and predicate: RULE_SYN_PART_001.

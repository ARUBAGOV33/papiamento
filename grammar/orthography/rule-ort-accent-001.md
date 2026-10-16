---
id: RULE_ORT_ACCENT_001
title: No accent marks in Aruban Papiamento
status: draft
source: ORT2009
page: "1; 6"
severity: error
reviewed_by: ""
---

## Rule

The orthography uses its alphabetic signs without accent marks. ñ is one of the letters of the alphabet.

## Source

Ortografia di Papiamento (version april 2009), Introduccion, printed page 1: "A mantene e sistema metodologico di e signonan alfabetico sin uzo di accent." §1 "Alfabet", printed page 6, lists the letters, ñ among them, and the digraphs ch, dj, sh, zj.

## Correct

- tera, bela
- barbulet, speki
- binager, sanger
- copa, bora
- sopi, scoter

## Exceptions

- Loans: words adopted from French are written by the current Dutch spelling rules, e.g. paté, and crèche keeps its accent (AB 2018 §12.2, gazette page 42; RULE_ORT_052). `_meta/allowlists/accented-loans.txt` lists the loanwords the AB 2018 word list prints with accents.

## Notes

- The examples are from §2 "Vocal" (page 6): e stands for [e], [ε] and [ə], and o for [o] and [ɔ], always without a mark.
- The AB 2018 gazette copy of the annex does not include the Introduccion, so ORT2009 is cited. AB 2018 prints the same alphabet on gazette page 6.
- Ruling (`_meta/invariants.md`): no accent marks, except ñ and the loanwords in the allowlist. The validator enforces the same in Aruban text columns (`_meta/conventions.md`, "Spelling checks on Aruban text").
- The old rule pack also had RULE_ORT_001 for the same statement; it was merged here. This id is the one the Skirbi checker uses.

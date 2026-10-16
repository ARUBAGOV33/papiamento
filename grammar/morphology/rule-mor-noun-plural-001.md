---
id: RULE_MOR_NOUN_PLURAL_001
title: When the plural suffix nan is used
status: draft
source: MOR2010
page: "10-11"
severity: info
reviewed_by: ""
---

## Rule

Morfologia says the suffix nan marks a plural reading only in specific cases: when the noun is determined by the definite article, when it is combined with a possessive pronoun, or when it is combined with a demonstrative pronoun. A noun used as a form of address with a plural meaning also takes nan.

## Source

Manual di Gramatica di Papiamento: Morfologia (2010), §2.3.2 "Uzo di e sufiho nan pa indica un interpretacion plural", pp. 10-11, and §2.3.3 "Sustantivo como apelativo", p. 11: "Ta uza e sufiho nan pa denota un interpretacion plural, solamente den algun caso specifico".

## Correct

- Definite article: Nos mester discuti e puntonan cu bo a trece padilanti.
- Definite article: Bo a mira e autonan nobo caba?
- Definite article: Unda e muchanan fastioso ta?
- Possessive: Mi no ta di acuerdo cu su insinuacionnan.
- Possessive: Trece mi cosnan aworaki mes!
- Possessive: Mi ta bay benta tur bo potoshinan afo.
- Demonstrative: Mi no ta gusta e cosnan ey.
- Demonstrative: Tur e teorianan ey falta algo
- Demonstrative: E tres edificionan aya ta di Gobierno.
- Form of address: Muchanan, boso bin tende!
- Form of address: Damanan, bonbini na e evento aki.
- Form of address: Ma shonnan, ta con boso por bay misa asina bisti?

## Notes

- Severity is info: the page describes when nan is used, and a checker cannot see a plural meaning that has no nan. What the checker does flag comes from the invariants: plural is -nan only, never -s, -os or -as, and no -nan after a bare numeral (_meta/invariants.md).
- The old rule pack called nan the common plural of count nouns. The book is narrower: nan is used only in the cases above. The cases without nan are in RULE_MOR_NOUN_PLURAL_002.
- "E tres edificionan aya ta di Gobierno." has a numeral and nan because the article and demonstrative are there; this matches the invariant (no -nan after a bare numeral, fine with an article or possessive) and RULE_GRA_PLURAL_001.
- "Tur e teorianan ey falta algo" has no full stop on the page; copied as printed.
- Where nan goes with adjectives and compound nouns: RULE_MOR_NOUN_PLURAL_003, _005, _006, _007.

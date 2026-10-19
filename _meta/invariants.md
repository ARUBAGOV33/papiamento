# Invariants

Aruban Papiamento rules that are not up for debate in this repo. Every AI agent and every contributor applies them. Each rule names its source.

- **Page references** are printed AB 2018 no. 68 page numbers taken from the text extraction. Each will be checked against the official PDF; until then the "Verified" column says `no`.
- **Rulings** were made by the project maintainer. The ones that can be checked automatically are also in [`known-facts.tsv`](known-facts.tsv), so the validator enforces them on every change.
- To change an invariant, open a pull request that cites a source page. The review board decides.

## Spelling

| Rule | Example | Source | Verified |
|---|---|---|---|
| The language name is **Papiamento** (capital P, ending in -o). | Papiamento, not Papiamentu | Ruling | — |
| **No accent marks**, except **ñ** and loanwords the AB list prints with accents (see `allowlists/accented-loans.txt`). | educacion, mas | AB 2018; ruling | no |
| The suffix pronounced /-shon/ is written **-cion**. Words where -shon is not that suffix keep it (cashon, shon are in the AB list). Exception: the nouns listed under AB §5 Sh, point 2 are written with **-sion** ("Ta skirbi e letternan si pa representa e zonido [ʃ] den e siguiente sustantivonan y nan derivacionnan"): expansion, conclusion, decision, division, posesion, comprension, depresion, confesion, television, admision … (p. 17) and comision, dimension, mision, version, vision … (p. 18). | educacion, nacion; decision, television | AB §5 Sh, pp. 17–18; AB list | no |
| **c** before a, o, u; **k** before e, i. Dutch loans keep their k (kabel, kantoor). | cas, cumpra, kere | Ruling; AB list | no |
| A word-final i-sound after a vowel is written **y** (ay, ey, oy, uy). Exceptions: rooi, trei, fei. | bay, ley | AB §3.2, p. 8 | no |
| Plural is **-nan** only, never -s, -os or -as. | casnan | Ruling | — |
| No **-nan** after a bare numeral. With an article or possessive it is fine. | cinco buki; e cinco bukinan | Ruling | — |
| Days and months are written in **lowercase**. | dialuna, januari | AB §9.6, p. 32 | no |
| Numbers 11–99 are written as **one word**. | trintidos (32), bintitres (23) | AB §11.8, p. 38 | no |
| Numbers above 100 are written **separately**. | dos shen y trintiseis (236) | AB §11.8, p. 38 | no |
| Clock times: numeral and **or** written separately. | 7 or, 12 or y mey | AB §11.8, p. 38 | no |
| Loanwords follow AB §12 (Spanish §12.1; Dutch, English and French §12.2; other languages §12.3). | | AB §12, pp. 41–44 | no |

## Words that must always be right

| Meaning | Aruban Papiamento | Never | Source |
|---|---|---|---|
| 1–10 | un, dos, tres, cuater, cinco, seis, shete, ocho, nuebe, dies | siete, cincu, sinku | Ruling; AB list |
| 4 | cuater (cuatro is also accepted) | | AB list `cuater [cuatro]` |
| 23 | bintitres | bintiseis (that is 26) | Ruling, 2026-10-15; AB §11.8 typo, see `sources/errata.tsv` |
| a lot, many, much | hopi | mucho | Ruling, 2026-10-15 |
| five | cinco | | Ruling, 2026-10-15 |
| never | nunca; hamas | | Ruling, 2026-10-16 |
| billion (10^9) | biyon | biljoen / billón (those are 10^12) | Ruling, 2026-10-16 |
| all | tur | todo, except in fixed expressions such as en todo caso | Ruling; err-0013 |
| family | famia | familia | Ruling |
| there is / there are | tin | hay | Ruling |
| Monday–Sunday | dialuna, diamars, diaranson, diahuebs, diabierna, diasabra, diadomingo | lunes, martes … domingo | Ruling; AB §9.6 |
| January–December | januari, februari, maart, april, mei, juni, juli, augustus, september, october, november, december | enero, febrero … | Ruling; AB §9.6 |
| fierce | feroz | feros | Ruling, 2026-10-19; AB §12.1, p. 41; Sintaxis p. 36 has a typo (err-0017) |
| little by little | pocopoco | poco poco | Ruling, 2026-10-19; AB §11.10, p. 39; Morfologia p. 25 has a typo (err-0018) |
| light (noun); to light | luz; lusa | lus | Ruling, 2026-10-19; AB 2018 word list, p. 41 |

`april` is written the same in Spanish and Dutch; it is correct.

## Grammar

| Rule | Correct | Wrong | Source |
|---|---|---|---|
| **lo** (future) and **a** (past) never combine. Use one or the other. | mi a bay | lo a bay | Ruling; kept on 2026-10-17 against Morfologia pp. 42, 44, 57 and Sintaxis p. 119 (err-0019 to err-0022) |
| Modals (kier, mester, por, sa, mag) never take **ta**. | mi kier bay | mi ta kier bay | Ruling; Morfologia §6.2.3.1, p. 39 |
| **conoce** never takes **ta**. | Mi tata conoce nos bisiña | Mi tata ta conoce nos bisiña | Ruling, 2026-10-19; Morfologia §6.2.3.1, p. 39; Sintaxis p. 31 differs (err-0024) |
| **gusta** is used with or without **ta**. | E mucha ta gusta core; E mucha gusta core | | Ruling, 2026-10-19; Morfologia §6.2.3.2, p. 39; Sintaxis §2.2.4.1 II.1, p. 31 (err-0023) |
| **por** and **prefera** have no gerund. | | porndo, podiendo, preferando, prefiriendo | Ruling; decided against Morfologia p. 48 (err-0010, err-0011) |
| Aruban irregular gerunds. | drumiendo, teniendo, keriendo, sabiendo | durmiendo, drumindo, tinindo, kierndo, sabindo | Ruling; AB 2018 word list; err-0009 |
| Spanish **de la / del / de los** becomes **di**, and the article is dropped. | cas di famia | cas di la familia | Ruling |
| Location **en** becomes **den** (inside a closed or limited place) or **na** (a place in general), depending on the meaning. | den cas; Francisco ta biba na Venezuela. | en cas | Ruling, 2026-10-17; Preposicion y Interheccion §1.3.4, p. 6 (den) and §1.3.7, p. 15 (na) |
| **usted / ustedes** become **bo / boso**. | | usted | Ruling |
| Collective nouns are singular, and so are the words that refer to them (**su**): "Palabra manera “club”, “gobierno”, “comision”, ta singular." | E comision di studiante a forma su directiva. | | Stilistica §2 point 11, PDF p. 4 |

## Variants

Curaçao spellings (`ku`, `kos`, `kome`, `kaba`, `-shon`) are a different standard, not mistakes in their own context. In this repo they appear only in `lexicon/variants/curacao-aruba.tsv`, mapped to the Aruban form (`kome → come`, `kaba → caba`).

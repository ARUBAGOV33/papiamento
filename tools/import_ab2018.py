#!/usr/bin/env python3
"""Rebuild the AB 2018 no. 68 word list from the law's PDF.

This is the script used for the initial import of lexicon/words/ (October 2026).
It is kept so anyone can check how the data was produced. Ids are now fixed in
the data files; re-running this script does not change them.

Steps:
  1. Read the text layer of the word-list annex (PDF pages 48-119, printed
     pages 1-72) and drop page headers.
  2. Join entries the layout split over two lines (hyphenated wraps, bracket
     or parenthesis parts on the next line) and restore missing spaces before
     "[" and "(". Hyphen joins are checked against the Papiamento.aw list.
  3. Compare every entry with the Papiamento.aw spell-checker list, if given.
  4. Split each entry into lemma, alt, tag and pos (see _meta/conventions.md).
  5. Apply reviewed corrections from tools/import_ab2018_overrides.tsv.

Usage:
  python3 tools/import_ab2018.py --pdf sources/pdf/AB2018.pdf \
      [--paw custom.txt] --out staged.json

Needs PyMuPDF (pip install pymupdf). The Papiamento.aw list (custom.txt from
papiamento.aw's spell-checker download) is not redistributed here.
"""

import argparse
import csv
import difflib
import json
import os
import re
import sys
import unicodedata

POS = {"s.", "v.", "adh.", "adv.", "num.", "pron.", "prep.", "conh.",
       "interh.", "art.", "expr.", "abr."}
FIRST_WORDLIST_PDF_PAGE = 48  # PDF page of printed word-list page 1
OVERRIDES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "import_ab2018_overrides.tsv")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def read_lines(pdf_path):
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    out = []
    for i in range(FIRST_WORDLIST_PDF_PAGE - 1, doc.page_count):
        text = doc[i].get_text()
        m = re.match(r"\s*Pagina\s+(\d+)", text)
        if not m:
            continue
        page = int(m.group(1))
        n = 0
        for raw in text.split("\n"):
            s = raw.strip()
            if not s or re.fullmatch(r"Pagina\s+\d+", s) or re.fullmatch(r"_+", s):
                continue
            if s.startswith("Afkondigingsblad van Aruba") or s == str(page):
                continue
            n += 1
            out.append({"page": page, "pdf_page": i + 1, "line": n, "text": nfc(s)})
    return out


def space_fix(s):
    s = re.sub(r"(?<=\S)\[", " [", s)
    if not s.startswith("("):
        s = re.sub(r"(?<=[^\s(])\((?!\s)", " (", s)
    s = re.sub(r"\)(?=\[)", ") ", s)
    return re.sub(r"\s+", " ", s).strip()


def join_entries(lines, paw):
    entries = []
    i = 0
    while i < len(lines):
        first = lines[i]
        text = first["text"]
        raw = [text]
        while i + 1 < len(lines):
            nxt = lines[i + 1]["text"]
            opens = text.count("[") > text.count("]") or text.count("(") > text.count(")")
            if text.endswith("-") and (opens or nxt[:1].islower()):
                a, b = text[:-1] + nxt, text + nxt
                text = a if (space_fix(a) in paw or space_fix(b) not in paw) else b
            elif nxt.startswith("[") and not opens:
                text = text + " " + nxt
            elif nxt.startswith("(") and "(" not in text:
                text = text + " " + nxt
            elif opens:
                text = text + " " + nxt
            else:
                break
            raw.append(nxt)
            i += 1
        entries.append({"page": first["page"], "pdf_page": first["pdf_page"],
                        "key": "p%02d-%03d" % (first["page"], first["line"]),
                        "printed": space_fix(text), "raw": raw})
        i += 1
    return entries


def parse(entry):
    t = entry["printed"].replace("’", "'").replace("‘", "'")
    tags = re.findall(r"\(([^)]*)\)", t)
    alts = re.findall(r"\[([^\]]*)\]", t)
    head = re.sub(r"\s*\([^)]*\)|\s*\[[^\]]*\]", "", t).strip()
    alt = [a.strip() for x in alts for a in x.split(",") if a.strip()]
    notes = ""
    if "/" in head:
        parts = [p.strip() for p in head.split("/")]
        head, alt, notes = parts[0], parts[1:] + alt, "printed as %s" % t
    tag = "; ".join(x.strip() for x in tags)
    first = next((c for c in head if c.isalpha()), "?")
    entry.update({
        "printed": t, "lemma": head, "alt": "; ".join(alt), "tag": tag,
        "pos": tag if tag in POS else "", "notes": notes, "status": "draft",
        "letter": unicodedata.normalize("NFD", first)[0].upper(),
    })
    return entry


def apply_overrides(entries):
    if not os.path.exists(OVERRIDES):
        return 0
    by_key = dict((e["key"], e) for e in entries)
    n = 0
    with open(OVERRIDES, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            e = by_key.get(row["key"])
            if e is None:
                sys.exit("override for unknown key %s" % row["key"])
            e[row["field"]] = row["value"]
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--paw", help="Papiamento.aw spell-checker list (custom.txt)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    paw = []
    if a.paw:
        with open(a.paw, encoding="utf-8-sig") as f:
            paw = [nfc(l.strip()) for l in f if l.strip()]
    entries = join_entries(read_lines(a.pdf), set(paw))
    if paw:
        printed = [e["printed"] for e in entries]
        sm = difflib.SequenceMatcher(None, paw, printed, autojunk=False)
        for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
            for j in range(j1, j2):
                entries[j]["papiamento_aw"] = "same" if tag == "equal" else "differs"
    entries = [parse(e) for e in entries]
    n = apply_overrides(entries)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    same = sum(1 for e in entries if e.get("papiamento_aw") == "same")
    print("%d entries, %d identical to Papiamento.aw, %d overrides applied"
          % (len(entries), same, n))


if __name__ == "__main__":
    main()

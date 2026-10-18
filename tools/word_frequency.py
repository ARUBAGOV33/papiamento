#!/usr/bin/env python3
"""Rank the AB 2018 headwords by how often they occur in text this repo publishes.

Two counts, both reproducible from files in the repository:

- pdf: words in the source PDFs in sources/pdf/ that the repo may share, except
  the ones in EXCLUDE (the word lists, which print every headword once, and
  text that is already counted).
- sentences: words in the Aruban Papiamento sentences of
  corpus/parallel/pairs.tsv. The held-out eval/parallel/ sentences are not used.

score is the rate per million words in the PDFs. Once there are contributed
sentences, it is the average of that rate and the rate in the sentences, so
the everyday words teachers use rise as sentences arrive. The maintainer chose
this on 2026-10-18 (tools/contribute/DESIGN.md, 5(e)); counts from private
text are never published.

A headword counts its lemma and its alt forms. Multi-word lemmas (a base di)
count as phrases. Rows that share a lemma (homographs) share its count.

Reading the PDFs needs PyMuPDF, like tools/import_ab2018.py
(pip install pymupdf). The output is not committed; the contribution tool's
sync job regenerates it to order the "Translate words" queue.

Usage:
    python3 tools/word_frequency.py                  # every headword, TSV on stdout
    python3 tools/word_frequency.py --untranslated   # only rows with no en, nl or es
    python3 tools/word_frequency.py --out word-frequency.tsv
    python3 tools/word_frequency.py --no-pdf         # sentences only (no PyMuPDF needed)
"""

import argparse
import collections
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Shareable PDFs that are not counted, and why.
EXCLUDE = {
    "AB2018": "its word list prints every headword once, and its orthography annex is the text of ORT2009, which is counted",
    "VOC2009": "the word list itself: it prints every headword once",
}
SENTENCES = "corpus/parallel/pairs.tsv"
LETTERS = "a-zà-ÿñ"
TOKEN = re.compile(r"[%s]+(?:'[%s]+)*" % (LETTERS, LETTERS))
COLUMNS = ["id", "lemma", "pdf_count", "sentence_count", "score", "translated"]


def tokenize(text):
    """Lowercase words; letters with accents and ñ count, apostrophes stay inside a word."""
    return TOKEN.findall(text.lower().replace("’", "'"))


def ngram_counts(tokens, sizes):
    """Counter of space-joined n-grams for every n in sizes (1 included)."""
    counts = collections.Counter(tokens)
    for n in sorted(s for s in sizes if s > 1):
        for i in range(len(tokens) - n + 1):
            counts[" ".join(tokens[i:i + n])] += 1
    return counts


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def load_words(root):
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "lexicon", "words", "*", "words.tsv"))):
        rows += read_tsv(path)
    return [r for r in rows if r.get("status") != "deprecated"]


def forms_of(row):
    """The lemma and its alt forms, lowercased and tokenized the same way as text."""
    forms = []
    for value in [row["lemma"]] + [a for a in row.get("alt", "").split("; ") if a]:
        joined = " ".join(tokenize(value))
        if joined and joined not in forms:
            forms.append(joined)
    return forms


def shareable_pdfs(root):
    """(source id, path) of every PDF in sources.tsv that may be shared and is not excluded."""
    with open(os.path.join(root, "_meta", "schema", "registry.json"), encoding="utf-8") as f:
        tiers = set(json.load(f).get("shareable_licence_tiers") or [])
    out = []
    for row in read_tsv(os.path.join(root, "sources", "sources.tsv")):
        if row.get("pdf") and row.get("licence_tier") in tiers and row["id"] not in EXCLUDE:
            out.append((row["id"], os.path.join(root, row["pdf"])))
    return sorted(out)


def pdf_tokens(pdfs):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise SystemExit("PyMuPDF is needed to read the PDFs: pip install pymupdf (or run with --no-pdf)")
    tokens = []
    for _sid, path in pdfs:
        doc = fitz.open(path)
        for page in doc:
            tokens += tokenize(page.get_text())
    return tokens


def sentence_tokens(root):
    path = os.path.join(root, SENTENCES)
    if not os.path.exists(path):
        return []
    tokens = []
    for row in read_tsv(path):
        if row.get("status") != "deprecated":
            tokens += tokenize(row.get("pap", ""))
    return tokens


def per_million(count, total):
    return 1e6 * count / total if total else 0.0


def score_rows(words, pdf_toks, sent_toks):
    """One output row per headword, best first."""
    sizes = set(len(f.split(" ")) for w in words for f in forms_of(w))
    pdf_counts = ngram_counts(pdf_toks, sizes)
    sent_counts = ngram_counts(sent_toks, sizes)
    out = []
    for w in words:
        forms = forms_of(w)
        pc = sum(pdf_counts[f] for f in forms)
        sc = sum(sent_counts[f] for f in forms)
        score = per_million(pc, len(pdf_toks))
        if sent_toks:
            score = (score + per_million(sc, len(sent_toks))) / 2 if pdf_toks else per_million(sc, len(sent_toks))
        translated = "yes" if (w.get("en") or w.get("nl") or w.get("es")) else "no"
        out.append({"id": w["id"], "lemma": w["lemma"], "pdf_count": pc, "sentence_count": sc,
                    "score": round(score, 2), "translated": translated})
    out.sort(key=lambda r: (-r["score"], r["lemma"].casefold(), r["id"]))
    return out


def write(rows, out):
    out.write("\t".join(COLUMNS) + "\n")
    for r in rows:
        out.write("\t".join("%.2f" % r[c] if c == "score" else str(r[c]) for c in COLUMNS) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--untranslated", action="store_true", help="only headwords with no en, nl or es")
    ap.add_argument("--out", help="write the TSV here instead of stdout")
    ap.add_argument("--no-pdf", action="store_true", help="count the contributed sentences only")
    ap.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    words = load_words(args.root)
    pdfs = [] if args.no_pdf else shareable_pdfs(args.root)
    rows = score_rows(words, pdf_tokens(pdfs) if pdfs else [], sentence_tokens(args.root))
    if args.untranslated:
        rows = [r for r in rows if r["translated"] == "no"]
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            write(rows, f)
    else:
        write(rows, sys.stdout)
    used = ", ".join(sid for sid, _ in pdfs) or "none"
    print("counted PDFs: %s; %d headwords written" % (used, len(rows)), file=sys.stderr)


if __name__ == "__main__":
    main()

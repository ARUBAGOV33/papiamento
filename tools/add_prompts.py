#!/usr/bin/env python3
"""Add a batch of English or Spanish prompts to the parallel-sentence tables.

Reads a text file with one prompt per line, "lang|topic|text" (lines starting
with # are comments), gives each new prompt the next free id, and writes it to
corpus/parallel/prompts.tsv or, for the held-out 15%, to
eval/parallel/prompts.tsv: a prompt is held out when
int(sha256(id), 16) % 100 < 15 (_meta/conventions.md, Parallel sentences).

It refuses a prompt that breaks the prompt rules (1 to 14 words, no digits,
no abbreviations, no characters Common Voice rejects) or that is already in
either table. Standard library only.

Usage:
    python3 tools/add_prompts.py BATCH_FILE --batch prompts-1 --author machine
    python3 tools/add_prompts.py BATCH_FILE --batch prompts-1 --author machine --check   # write nothing
"""

import argparse
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join("corpus", "parallel", "prompts.tsv")
EVAL = os.path.join("eval", "parallel", "prompts.tsv")
HOLD_OUT_PERCENT = 15
BAD_CHARS = re.compile(r"[0-9<>+*#@%^\[\]()/\\_=|{}~\"]")
ABBREVIATION = re.compile(r"\b(?:[A-Z]{2,}|(?:[A-Za-z]\.){2,})")
ID_RE = re.compile(r"^prm-([0-9]{6})$")


def held_out(prompt_id):
    return int(hashlib.sha256(prompt_id.encode("utf-8")).hexdigest(), 16) % 100 < HOLD_OUT_PERCENT


def problems(text):
    out = []
    words = text.split()
    if not 1 <= len(words) <= 14:
        out.append("has %d words (1 to 14)" % len(words))
    if BAD_CHARS.search(text):
        out.append("has a digit or a character Common Voice rejects")
    if ABBREVIATION.search(text):
        out.append("looks like an abbreviation")
    if text != text.strip() or "  " in text or "\t" in text:
        out.append("has extra spaces or a tab")
    if "’" in text:
        out.append("has a curly apostrophe")
    return out


def read_table(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    header = lines[0].split("\t")
    rows = [dict(zip(header, line.split("\t"))) for line in lines[1:] if line]
    return header, rows


def write_table(path, header, rows):
    rows = sorted(rows, key=lambda r: r["id"])
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(header) + "\n")
        for r in rows:
            f.write("\t".join(r.get(h, "") for h in header) + "\n")


def read_batch(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != 3 or parts[0] not in ("en", "es"):
                raise SystemExit("%s:%d: expected lang|topic|text with lang en or es" % (path, n))
            out.append((n, parts[0], parts[1].strip(), parts[2].strip()))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batch_file")
    ap.add_argument("--batch", required=True, help="batch name, e.g. prompts-1")
    ap.add_argument("--author", required=True, help="machine, or handles from _meta/contributors.tsv")
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    ap.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    corpus_path, eval_path = os.path.join(args.root, CORPUS), os.path.join(args.root, EVAL)
    header, corpus_rows = read_table(corpus_path)
    _, eval_rows = read_table(eval_path)
    taken = [int(ID_RE.match(r["id"]).group(1)) for r in corpus_rows + eval_rows if ID_RE.match(r["id"])]
    next_id = max(taken, default=0) + 1
    seen = set(r["text"].casefold() for r in corpus_rows + eval_rows)

    errors, added = [], {"corpus": 0, "eval": 0}
    for n, lang, topic, text in read_batch(args.batch_file):
        bad = problems(text)
        if text.casefold() in seen:
            bad.append("is already in the prompts")
        if bad:
            errors.append("%s:%d: %r %s" % (args.batch_file, n, text, "; ".join(bad)))
            continue
        seen.add(text.casefold())
        pid = "prm-%06d" % next_id
        next_id += 1
        row = {"id": pid, "lang": lang, "text": text, "topic": topic, "origin": "written", "origin_ref": "",
               "author": args.author, "batch": args.batch, "licence": "CC0-1.0", "status": "draft",
               "reviewed_by": "", "notes": ""}
        if held_out(pid):
            eval_rows.append(row)
            added["eval"] += 1
        else:
            corpus_rows.append(row)
            added["corpus"] += 1

    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        raise SystemExit("%d prompt(s) refused; nothing written" % len(errors))
    if not args.check:
        write_table(corpus_path, header, corpus_rows)
        write_table(eval_path, header, eval_rows)
    total = added["corpus"] + added["eval"]
    print("%s %d prompt(s): %d to corpus/parallel, %d held out in eval/parallel (%.1f%%)" % (
        "would add" if args.check else "added", total, added["corpus"], added["eval"],
        100.0 * added["eval"] / total if total else 0))


if __name__ == "__main__":
    main()

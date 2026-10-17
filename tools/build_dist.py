#!/usr/bin/env python3
"""Build the release files in dist/ from the source tables and rule files.

dist/ is never committed. It holds what a release ships: one JSONL file per
table, the grammar rules as JSONL, an auditor-ready rule_pack.json, the
Hugging Face dataset card (README.md), a manifest with counts and checksums,
and RELEASE_NOTES.md with the number of rows per status.

Multi-value cells ("house; home") become JSON lists. Empty cells stay "".

Usage:
  python3 tools/build_dist.py [--version 0.1.0] [--out dist]
  python3 tools/build_dist.py --check      build into a temporary folder (for CI)

Standard library only; Python 3.9+.
"""

import argparse
import collections
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import validate  # noqa: E402  (front matter and section parsing)

LIST_FIELDS = {"alt", "en", "nl", "es", "reviewed_by", "translated_by", "right", "authors"}
TABLES = [
    # (output name, registry table name)
    ("words", "words"),
    ("numbers", "numbers"),
    ("calendar", "calendar"),
    ("barbarismos", "barbarismos"),
    ("variants", "variants"),
    ("loanwords", "loanwords"),
    ("errata", "errata"),
    ("sources", "sources"),
    ("known_facts", "known-facts"),
]
CARD_TEMPLATE = os.path.join(ROOT, "release", "dataset-card.md")


def read_tsv(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if not line:
            continue
        rows.append(dict(zip(header, line.split("\t"))))
    return header, rows


def convert(row):
    out = {}
    for key, value in row.items():
        if key in LIST_FIELDS:
            out[key] = [v for v in value.split("; ") if v] if value else []
        else:
            out[key] = value
    return out


def citation_version():
    path = os.path.join(ROOT, "CITATION.cff")
    with open(path, encoding="utf-8") as f:
        m = re.search(r'^version:\s*"?([0-9][^"\s]*)"?', f.read(), re.M)
    return m.group(1) if m else None


def changelog_section(version):
    """The text under '## [version]' in CHANGELOG.md, or '' if there is none."""
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^## \[%s\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)" % re.escape(version), text, re.M | re.S)
    return m.group(1).strip() if m else ""


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n")


def grammar_rows():
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "grammar", "*", "rule-*.md"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        meta, body = validate.parse_front_matter(text)
        if not meta:
            continue
        rule = re.search(r"## Rule\n(.*?)(?=\n## |\Z)", body, re.S)
        source = re.search(r"## Source\n(.*?)(?=\n## |\Z)", body, re.S)
        rows.append({
            "id": meta.get("id", ""),
            "topic": os.path.basename(os.path.dirname(path)),
            "title": meta.get("title", ""),
            "status": meta.get("status", ""),
            "severity": meta.get("severity", ""),
            "source": meta.get("source", ""),
            "page": meta.get("page", ""),
            "reviewed_by": [v for v in meta.get("reviewed_by", "").split("; ") if v],
            "rule": re.sub(r"\s+", " ", rule.group(1)).strip() if rule else "",
            "source_text": source.group(1).strip() if source else "",
            "correct": validate.section_items(text, "Correct"),
            "incorrect": validate.section_items(text, "Incorrect"),
            "exceptions": validate.section_items(text, "Exceptions"),
            "notes": validate.section_items(text, "Notes"),
            "file": os.path.relpath(path, ROOT),
        })
    return rows


def machine_rules(grammar):
    by_id = dict((g["id"], g) for g in grammar)
    path = os.path.join(ROOT, "rules", "rules.jsonl")
    rules = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    g = by_id.get(r["rule_id"], {})
                    r["severity"] = g.get("severity", "")
                    r["status"] = g.get("status", "")
                    r["source"] = g.get("source", "")
                    r["page"] = g.get("page", "")
                    rules.append(r)
    return rules


def status_counts(rows):
    return dict(sorted(collections.Counter(r.get("status", "") or "-" for r in rows).items()))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build(out, version, hf_repo="ARUBAGOV33/papiamento"):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(ROOT, "_meta", "schema", "registry.json"), encoding="utf-8") as f:
        registry = json.load(f)
    globs = dict((t["name"], t["glob"]) for t in registry["tables"])
    data = {}
    for name, table in TABLES:
        rows = []
        for path in sorted(glob.glob(os.path.join(ROOT, globs[table]))):
            _, tsv_rows = read_tsv(path)
            for r in tsv_rows:
                c = convert(r)
                if name in ("numbers", "calendar"):
                    c["file"] = os.path.basename(path)[:-4]
                rows.append(c)
        if name == "words":
            for r in rows:
                first = next((ch for ch in r["lemma"] if ch.isalpha()), "")
                r["letter"] = validate.strip_accents(first).upper() if first else ""
        data[name] = rows
        write_jsonl(os.path.join(out, name + ".jsonl"), rows)
    grammar = grammar_rows()
    data["grammar"] = grammar
    write_jsonl(os.path.join(out, "grammar.jsonl"), grammar)
    rules = machine_rules(grammar)
    data["rules"] = rules
    write_jsonl(os.path.join(out, "rules.jsonl"), rules)
    pack = {
        "name": "papiamento-aruba-rule-pack",
        "version": version,
        "variant": "pap-AW",
        "about": "Rules for an Aruban Papiamento writing auditor: regex rules with tests, plus the word-level barbarismos and Curaçao-to-Aruba spelling pairs. See README.md.",
        "rules": rules,
        "barbarismos": data["barbarismos"],
        "variants": data["variants"],
    }
    with open(os.path.join(out, "rule_pack.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
        f.write("\n")

    counts = dict((k, len(v)) for k, v in data.items())
    statuses = dict((k, status_counts(v)) for k, v in data.items() if k not in ("sources", "known_facts", "rules"))
    machine_translated = sum(1 for r in data["words"] if "machine" in r.get("translated_by", []))
    translated = sum(1 for r in data["words"] if r.get("en") or r.get("nl") or r.get("es"))
    reviewed = sum(n.get("reviewed", 0) for k, n in statuses.items() if k != "errata")
    if reviewed:
        review_state = "In this version, {:,} data rows have been reviewed.".format(reviewed)
    else:
        review_state = "In this version no data row has been reviewed yet, so that filter returns nothing outside the `errata` table."
    with_en = sum(1 for r in data["words"] if r.get("en"))
    with_nl = sum(1 for r in data["words"] if r.get("nl"))
    with_es = sum(1 for r in data["words"] if r.get("es"))
    stats = {"rows": counts, "status": statuses, "words_with_en": with_en, "words_with_nl": with_nl,
             "words_with_es": with_es, "words_translated": translated, "words_machine_translated": machine_translated,
             "machine_rules_with_fix": sum(1 for r in rules if r.get("replacement"))}

    # dataset card
    with open(CARD_TEMPLATE, encoding="utf-8") as f:
        card = f.read()
    table = "\n".join("| `%s` | %s |" % (k, "{:,}".format(v)) for k, v in counts.items())
    card = (card.replace("{{VERSION}}", version)
                .replace("{{COUNTS_TABLE}}", table)
                .replace("{{WORDS}}", "{:,}".format(counts["words"]))
                .replace("{{WORDS_TRANSLATED}}", "{:,}".format(translated))
                .replace("{{REVIEW_STATE}}", review_state)
                .replace("{{WORDS_MACHINE}}", "{:,}".format(machine_translated))
                .replace("{{GRAMMAR}}", "{:,}".format(counts["grammar"]))
                .replace("{{RULES}}", "{:,}".format(counts["rules"]))
                .replace("{{HF_REPO}}", hf_repo))
    left = re.search(r"\{\{[A-Z_]+\}\}", card)
    if left:
        raise SystemExit("dataset card has an unfilled placeholder: " + left.group(0))
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(card)

    # release notes
    notes = ["# Papiamento open data %s" % version, "", "## Rows per table and status", "",
             "| Table | Rows | Status |", "|---|---:|---|"]
    for k, v in counts.items():
        st = statuses.get(k)
        notes.append("| %s | %s | %s |" % (k, "{:,}".format(v),
                                           ", ".join("%s %s" % (s, "{:,}".format(n)) for s, n in st.items()) if st else ""))
    notes += ["", "Words with English: {:,}; Dutch: {:,}; Spanish: {:,}. Words whose translations include machine drafts: {:,}."
              .format(with_en, with_nl, with_es, machine_translated),
              "Machine rules with an automatic fix: {:,}.".format(stats["machine_rules_with_fix"]),
              "", "Only `reviewed` rows have been checked against the source page. "
              + ("Data rows reviewed so far: {:,}.".format(reviewed) if reviewed else "Apart from the errata, no row has been reviewed yet."),
              ""]
    changes = changelog_section(version)
    if changes:
        notes += ["## Changes", "", changes]
    else:
        notes += ["See CHANGELOG.md for what changed."]
    with open(os.path.join(out, "RELEASE_NOTES.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(notes) + "\n")

    files = sorted(n for n in os.listdir(out) if n != "manifest.json")
    manifest = {"name": "papiamento", "version": version, "stats": stats,
                "files": dict((n, {"bytes": os.path.getsize(os.path.join(out, n)), "sha256": sha256(os.path.join(out, n))})
                              for n in files)}
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return counts, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--version", help="release version, default: version in CITATION.cff")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--hf-repo", default=os.environ.get("HF_DATASET_REPO") or "ARUBAGOV33/papiamento",
                    help="Hugging Face dataset id shown in the card (default: $HF_DATASET_REPO or ARUBAGOV33/papiamento)")
    ap.add_argument("--check", action="store_true", help="build into a temporary folder and discard it")
    a = ap.parse_args()
    version = a.version or citation_version() or "0.0.0-dev"
    out = tempfile.mkdtemp() if a.check else a.out
    try:
        if not a.check and os.path.isdir(out):
            if os.listdir(out) and not os.path.isfile(os.path.join(out, "manifest.json")):
                sys.exit("%s is not empty and has no manifest.json; refusing to delete it" % out)
            shutil.rmtree(out)
        counts, stats = build(out, version, a.hf_repo)
    finally:
        if a.check:
            shutil.rmtree(out, ignore_errors=True)
    print("Built version %s%s: %s" % (version, " (check only)" if a.check else " in " + os.path.relpath(out, ROOT),
                                       ", ".join("%s %d" % kv for kv in counts.items())))


if __name__ == "__main__":
    main()

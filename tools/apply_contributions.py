#!/usr/bin/env python3
"""Bring review-board decisions from the contribution tool into the repo.

The contribution tool (tools/contribute/) keeps answers, sentences, ratings and
board decisions in its Supabase database. This script reads the decisions not
yet exported and writes them into the data files:

- word decisions (review, translate): the en/nl/es cells, translated_by,
  status, reviewed_by and notes of the row in lexicon/words/<L>/words.tsv;
- sentence decisions: a new row in corpus/parallel/pairs.tsv, or in
  eval/parallel/pairs.tsv when the prompt is held out;
- every person it credits gets a row in _meta/contributors.tsv (no email).

A row becomes reviewed only when a board member or maintainer with a GitHub
username decided it; otherwise it stays draft. Disputed decisions set the row
to disputed. Nothing is ever merged: the workflow opens one pull request, and
the board member named in reviewed_by approves it on GitHub.

Rows it cannot write safely are skipped and listed, and their decisions stay
unexported:

- a word already reviewed in the repo;
- a translate decision on a word that has a translation by now;
- a sentence with characters Aruban spelling does not allow;
- a person whose handle belongs to someone else in contributors.tsv.

Usage:
    python3 tools/apply_contributions.py fetch --out snapshot.json            # needs SUPABASE_URL, SUPABASE_SECRET_KEY
    python3 tools/apply_contributions.py apply --snapshot snapshot.json --dry-run
    python3 tools/apply_contributions.py apply --snapshot snapshot.json --summary pr-body.md --ids ids.json
    python3 tools/apply_contributions.py mark-exported --ids ids.json --pr-url URL   # needs SUPABASE_URL, SUPABASE_SECRET_KEY

The secret key is read from the environment only, sent only to SUPABASE_URL,
and never printed. Standard library only.
"""

import argparse
import datetime
import glob
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS = ("en", "nl", "es")
CONTRIBUTORS = os.path.join("_meta", "contributors.tsv")
PAIRS = {"corpus": os.path.join("corpus", "parallel", "pairs.tsv"), "eval": os.path.join("eval", "parallel", "pairs.tsv")}
PROMPTS = {"corpus": os.path.join("corpus", "parallel", "prompts.tsv"), "eval": os.path.join("eval", "parallel", "prompts.tsv")}
ARUBAN_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ñÑ' -.")
SENTENCE_PUNCT = set(",;:!?¿¡\"")  # punctuation a sentence may also use


# --------------------------------------------------------------------------- TSV files

class Table(object):
    """A TSV file read as a header and rows of dicts; written back the same way."""

    def __init__(self, path):
        self.path = path
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        self.header = lines[0].split("\t")
        self.rows = [dict(zip(self.header, line.split("\t"))) for line in lines[1:] if line]
        self.changed = False

    def write(self):
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\t".join(self.header) + "\n")
            for r in self.rows:
                f.write("\t".join(r.get(h, "") for h in self.header) + "\n")


def clean(text):
    """NFC, straight apostrophes, no tabs or line breaks, single spaces."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("’", "'").replace("‘", "'").replace("ʼ", "'")
    text = re.sub(r"[\t\r\n  ]+", " ", text)
    return re.sub(r" {2,}", " ", text).strip()


def clean_gloss(text):
    return re.sub(r"\s*;\s*", "; ", clean(text)).strip("; ").strip()


def add_note(row, note):
    row["notes"] = "; ".join(n for n in (row.get("notes", ""), note) if n)


def accented_loans(root):
    path = os.path.join(root, "_meta", "allowlists", "accented-loans.txt")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return set(unicodedata.normalize("NFC", l.strip()) for l in f if l.strip() and not l.startswith("#"))


def spelling_problems(text, loans):
    """Characters the validator (G3) would refuse in Aruban text."""
    bad = []
    for word in re.split(r"\s+", text):
        core = word.strip("".join(SENTENCE_PUNCT) + ".")
        if any(ch not in ARUBAN_ALLOWED and ch not in SENTENCE_PUNCT for ch in core) and core not in loans:
            bad.append(word)
    return bad


# --------------------------------------------------------------------------- Supabase

def supabase(method, path, body=None):
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SECRET_KEY", "")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url + path, data=data, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=minimal")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        # Never echo request headers; the path and status are enough.
        raise SystemExit("Supabase %s %s failed: HTTP %d" % (method, path.split("?")[0], err.code))
    except urllib.error.URLError as err:
        raise SystemExit("Supabase %s %s failed: %s" % (method, path.split("?")[0], err.reason))


def in_list(values):
    return "in.(%s)" % ",".join(str(v) for v in values)


def fetch_snapshot():
    """Unexported decisions plus the profiles, sentences and ratings they need."""
    decisions = supabase("GET", "/rest/v1/decisions?select=*&exported_in=is.null&order=id") or []
    tids = set(d["translation_id"] for d in decisions if d.get("translation_id"))
    for d in decisions:
        v = d.get("value") or {}
        if isinstance(v, dict) and v.get("translation_id"):
            tids.add(v["translation_id"])
    translations = supabase("GET", "/rest/v1/translations?select=*&id=" + urllib.parse.quote(in_list(sorted(tids)))) if tids else []
    ratings = supabase("GET", "/rest/v1/ratings?select=*&translation_id=" + urllib.parse.quote(in_list(sorted(tids)))) if tids else []
    profiles = supabase("GET", "/rest/v1/profiles?select=id,handle,credit_name,credit,role,github,occupation,consent_version,created_at&order=handle") or []
    return {"profiles": profiles, "decisions": decisions, "translations": translations or [], "ratings": ratings or []}


# --------------------------------------------------------------------------- apply

class Run(object):
    def __init__(self, root, snapshot, batch_date):
        self.root = root
        self.snap = snapshot
        self.batch = "contrib-" + batch_date
        self.profiles = dict((p["id"], p) for p in snapshot.get("profiles", []))
        self.translations = dict((t["id"], t) for t in snapshot.get("translations", []))
        self.ratings = snapshot.get("ratings", [])
        self.loans = accented_loans(root)
        self.word_files = [Table(p) for p in sorted(glob.glob(os.path.join(root, "lexicon", "words", "*", "words.tsv")))]
        self.reindex()
        self.contributors = Table(os.path.join(root, CONTRIBUTORS))
        self.pairs = dict((k, Table(os.path.join(root, p))) for k, p in PAIRS.items())
        self.prompt_split = {}
        for split, path in PROMPTS.items():
            for r in Table(os.path.join(root, path)).rows:
                self.prompt_split[r["id"]] = split
        self.exported = []      # decision ids written
        self.done = []          # (decision, line for the summary)
        self.skipped = []       # (decision, reason)
        self.new_people = []
        self.reviewers = set()

    def reindex(self):
        self.word_tables = dict((r["id"], (t, r)) for t in self.word_files for r in t.rows)

    # people -------------------------------------------------------------

    def contributor_row(self, handle=None, github=None):
        for r in self.contributors.rows:
            if handle and r["handle"].casefold() == handle.casefold():
                return r
            if github and r.get("github") and r["github"].casefold() == github.casefold():
                return r
        return None

    def credit(self, person_id):
        """The handle to credit for a person, adding them to contributors.tsv if needed."""
        p = self.profiles.get(person_id)
        if p is None:
            raise ValueError("person %s is not in the tool's profiles" % person_id)
        existing = self.contributor_row(handle=p["handle"])
        if existing is not None:
            if p.get("github") and existing.get("github") and existing["github"].casefold() != p["github"].casefold():
                raise ValueError("handle %r is already used in _meta/contributors.tsv by GitHub user %s"
                                 % (p["handle"], existing["github"]))
            if not p.get("github") and existing.get("github"):
                raise ValueError("handle %r belongs to GitHub user %s in _meta/contributors.tsv, not to this person"
                                 % (p["handle"], existing["github"]))
            return existing["handle"]
        by_github = self.contributor_row(github=p.get("github")) if p.get("github") else None
        if by_github is not None:
            return by_github["handle"]
        row = {"handle": p["handle"], "credit_name": clean(p.get("credit_name", "")) if p.get("credit") else "",
               "github": p.get("github") or "", "role": p.get("role", "contributor"),
               "licence_words": "CC-BY-4.0", "licence_sentences": "CC0-1.0",
               "consent": p.get("consent_version", ""), "joined": (p.get("created_at") or "")[:10], "notes": ""}
        self.contributors.rows.append(row)
        self.contributors.rows.sort(key=lambda r: r["handle"])
        self.contributors.changed = True
        self.new_people.append(row)
        return row["handle"]

    def board(self, decision):
        """(handle, GitHub username or '') of the board member who decided."""
        handle = self.credit(decision["board_id"])
        p = self.profiles[decision["board_id"]]
        return handle, p.get("github") or ""

    # words --------------------------------------------------------------

    def apply_word(self, d):
        hit = self.word_tables.get(d.get("word_ref"))
        if hit is None:
            raise ValueError("%s is not a word in lexicon/words" % d.get("word_ref"))
        table, row = hit
        if row["status"] == "reviewed":
            raise ValueError("%s %s is already reviewed in the repo" % (row["id"], row["lemma"]))
        if d["kind"] == "translate" and any(row[l] for l in LANGS) and d["outcome"] == "reviewed":
            raise ValueError("%s %s has a translation in the repo by now" % (row["id"], row["lemma"]))
        board_handle, github = self.board(d)
        note = "contribution tool decision %s" % d["id"]
        if d["outcome"] == "disputed":
            row["status"] = "disputed"
            row["reviewed_by"] = ""
            add_note(row, note + ": the two answers differ")
            table.changed = True
            return "%s %s: disputed" % (row["id"], row["lemma"])

        value = d.get("value") or {}
        by, kept, changed = [], [], []
        for lang in LANGS:
            v = value.get(lang)
            if not isinstance(v, dict):
                continue
            text = clean_gloss(v.get("value", ""))
            source = v.get("from")
            if text != row[lang]:
                if source == "machine":
                    raise ValueError("%s: the %s value is marked as the machine draft but differs from it" % (row["id"], lang))
                row[lang] = text
            if not text:
                continue
            if source == "machine":
                kept.append(lang.upper())
                continue
            changed.append(lang.upper())
            people = [board_handle] if source == "board" else [self.credit(pid) for pid in (source or [])]
            for h in people:
                if h not in by:
                    by.append(h)
        if not any(row[l] for l in LANGS):
            row["translated_by"] = ""
        else:
            row["translated_by"] = "; ".join(by + (["machine"] if kept else []))
        if github:
            row["status"], row["reviewed_by"] = "reviewed", github
            self.reviewers.add(github)
        else:
            row["status"], row["reviewed_by"] = "draft", ""
            note += " (decided by %s, who has no GitHub username yet, so the row stays draft)" % board_handle
        if kept and changed:
            note += "; %s confirmed as machine draft, %s corrected" % (", ".join(kept), ", ".join(changed))
        add_note(row, note)
        table.changed = True
        return "%s %s: %s, %s" % (row["id"], row["lemma"], row["status"],
                                  " / ".join("%s %s" % (l.upper(), row[l]) for l in LANGS if row[l]))

    # sentences ----------------------------------------------------------

    def next_pair_id(self):
        taken = [int(r["id"][4:]) for t in self.pairs.values() for r in t.rows if re.match(r"^par-[0-9]{6}$", r["id"])]
        return "par-%06d" % (max(taken, default=0) + 1)

    def apply_sentence(self, d):
        tr = self.translations.get(d.get("translation_id"))
        if tr is None:
            raise ValueError("sentence %s is missing from the snapshot" % d.get("translation_id"))
        split = self.prompt_split.get(tr["prompt_ref"])
        if split is None:
            raise ValueError("prompt %s is not in corpus/ or eval/ prompts.tsv" % tr["prompt_ref"])
        value = d.get("value") or {}
        text = clean(value.get("text") or tr["text"])
        source = value.get("from", tr["person_id"])
        bad = spelling_problems(text, self.loans)
        if bad:
            raise ValueError("%s: Aruban spelling does not allow %s; the board should correct it in the tool"
                             % (tr["prompt_ref"], ", ".join(repr(b) for b in bad)))
        table = self.pairs[split]
        if any(r["prompt_id"] == tr["prompt_ref"] and r["pap"] == text for r in table.rows):
            self.exported.append(d["id"])  # already in the data: nothing to write, nothing to redo
            return "%s: already in %s" % (tr["prompt_ref"], PAIRS[split])
        board_handle, github = self.board(d)
        author = board_handle if source == "board" else self.credit(source)
        checked = []
        for r in sorted(self.ratings, key=lambda r: r["id"]):
            if r["translation_id"] == tr["id"] and r["verdict"] == "good" and r["person_id"] != tr["person_id"]:
                h = self.credit(r["person_id"])
                if h not in checked and h != author:
                    checked.append(h)
        flags = []
        for f in tr.get("flags_kept") or []:
            fid = (f.get("id") if isinstance(f, dict) else str(f)).split(":")[-1]
            if re.match(r"^(RULE_[A-Z0-9_]+|bar-[0-9]{4}|var-[0-9]{4})$", fid) and fid not in flags:
                flags.append(fid)
        note = "contribution tool decision %s" % d["id"]
        if d["outcome"] == "disputed":
            status, reviewed_by = "disputed", ""
            note += ": the board marked it disputed"
        elif github:
            status, reviewed_by = "reviewed", github
            self.reviewers.add(github)
        else:
            status, reviewed_by = "draft", ""
            note += " (decided by %s, who has no GitHub username yet, so the row stays draft)" % board_handle
        row = {"id": self.next_pair_id(), "prompt_id": tr["prompt_ref"], "pap": text, "translated_by": author,
               "checked_by": "; ".join(checked), "fix_of": "", "flags_kept": "; ".join(flags), "batch": self.batch,
               "licence": "CC0-1.0", "status": status, "reviewed_by": reviewed_by, "notes": note}
        table.rows.append(row)
        table.rows.sort(key=lambda r: (r["prompt_id"], r["id"]))
        table.changed = True
        return "%s %s in %s: %s, %s" % (row["id"], tr["prompt_ref"], PAIRS[split], status, text)

    # run ------------------------------------------------------------------

    def run(self):
        for d in sorted(self.snap.get("decisions", []), key=lambda d: d["id"]):
            if d.get("exported_in"):
                continue
            # Work on copies first, so a decision that fails halfway leaves no trace.
            backup = self.snapshot_state()
            try:
                line = self.apply_sentence(d) if d["kind"] == "sentence" else self.apply_word(d)
            except ValueError as err:
                self.restore_state(backup)
                self.skipped.append((d, str(err)))
                continue
            if d["id"] not in self.exported:
                self.exported.append(d["id"])
            self.done.append((d, line))

    def tables(self):
        return self.word_files + [self.contributors] + list(self.pairs.values())

    def snapshot_state(self):
        return ([(t, [dict(r) for r in t.rows], t.changed) for t in self.tables()],
                list(self.new_people), set(self.reviewers))

    def restore_state(self, backup):
        tables, people, reviewers = backup
        for t, rows, changed in tables:
            t.rows, t.changed = rows, changed
        self.reindex()
        self.new_people, self.reviewers = people, reviewers

    def write(self):
        for t in self.tables():
            if t.changed:
                t.write()

    def summary(self):
        lines = ["Decisions made by the review board in the contribution tool (`tools/contribute/`), exported by `tools/apply_contributions.py` (batch `%s`)." % self.batch, ""]
        if self.reviewers:
            lines += ["**Approval needed from:** %s. GOVERNANCE.md: the person named in `reviewed_by` must approve this pull request." % ", ".join("@" + g for g in sorted(self.reviewers)), ""]
        lines += ["## Written (%d)" % len(self.done), ""]
        lines += ["- %s (decision %s)" % (line, d["id"]) for d, line in self.done] or ["- nothing"]
        if self.new_people:
            lines += ["", "## New in `_meta/contributors.tsv` (%d)" % len(self.new_people), ""]
            lines += ["- `%s`%s, %s" % (r["handle"], " (%s)" % r["credit_name"] if r["credit_name"] else "", r["role"]) for r in self.new_people]
        if self.skipped:
            lines += ["", "## Not exported (%d): fix in the tool, then they come in the next sync" % len(self.skipped), ""]
            lines += ["- decision %s: %s" % (d["id"], why) for d, why in self.skipped]
        lines += ["", "Opened by the papiamento-sync GitHub App from the contribution tool's database. Rows stay `draft` unless a board member with a GitHub username decided them. Never merged automatically."]
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="read unexported decisions from Supabase into a JSON snapshot")
    f.add_argument("--out", required=True)
    a = sub.add_parser("apply", help="write a snapshot's decisions into the data files")
    a.add_argument("--snapshot", required=True)
    a.add_argument("--date", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
                   help="batch date, YYYY-MM-DD (default: today, UTC)")
    a.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    a.add_argument("--summary", help="write the pull request body (Markdown) here")
    a.add_argument("--ids", help="write the exported decision ids (JSON) here")
    a.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    m = sub.add_parser("mark-exported", help="record the pull request on the exported decisions")
    m.add_argument("--ids", required=True)
    m.add_argument("--pr-url", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "fetch":
        snap = fetch_snapshot()
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, ensure_ascii=False, indent=1)
        print("fetched %d unexported decision(s)" % len(snap["decisions"]))
        return 0

    if args.cmd == "mark-exported":
        with open(args.ids, encoding="utf-8") as fh:
            ids = json.load(fh)
        if not re.match(r"^https://github\.com/[^/]+/[^/]+/pull/[0-9]+$", args.pr_url):
            raise SystemExit("--pr-url must be a GitHub pull request URL")
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            supabase("PATCH", "/rest/v1/decisions?id=" + urllib.parse.quote(in_list(chunk)),
                     {"exported_in": args.pr_url, "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        print("marked %d decision(s) as exported in %s" % (len(ids), args.pr_url))
        return 0

    with open(args.snapshot, encoding="utf-8") as fh:
        snap = json.load(fh)
    run = Run(args.root, snap, args.date)
    run.run()
    if not args.dry_run:
        run.write()
    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as fh:
            fh.write(run.summary())
    if args.ids:
        with open(args.ids, "w", encoding="utf-8") as fh:
            json.dump(run.exported, fh)
    print("%s %d decision(s), skipped %d, %d new contributor(s)%s" % (
        "would write" if args.dry_run else "wrote", len(run.done), len(run.skipped), len(run.new_people),
        " (dry run: no file changed)" if args.dry_run else ""))
    for d, why in run.skipped:
        print("  skipped decision %s: %s" % (d["id"], why))
    return 0


if __name__ == "__main__":
    sys.exit(main())

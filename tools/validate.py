#!/usr/bin/env python3
"""The gauntlet: validates every data file in the papiamento repo.

Usage: python3 tools/validate.py [--root PATH] [--json] [--strict]

Gates
  G0 Source trace   every row cites a known source; PDFs are shareable
  G1 Format         UTF-8, NFC, LF, final newline, header, columns, cells, sort
  G2 Schema         required / enum / pattern / unique, reviewed_by
  G3 Orthography    accents, Curacao markers, letter folders
  G4 Integrity      ids unique repo-wide, unique_together, lexicon refs
  G5 Known facts    rulings in _meta/known-facts.tsv (extension point: G5_CHECKS)

Exit codes: 0 no errors, 1 errors found (or warnings with --strict),
2 bad command line.

Standard library only; Python 3.9 compatible. Bad data never crashes the
validator: every problem becomes a finding.
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

ERROR = "error"
WARNING = "warning"

GATES = ["G0", "G1", "G2", "G3", "G4", "G5"]
GATE_TITLES = {
    "G0": "Source trace",
    "G1": "Format",
    "G2": "Schema",
    "G3": "Orthography",
    "G4": "Integrity",
    "G5": "Known facts",
}

REGISTRY_PATH = "_meta/schema/registry.json"
MULTI_SEP = "; "
# Rows from this source are exempt from the Curacao-marker warning: the
# official AB list contains legitimate words such as cashon, shon, kabel.
AB_SOURCE_ID = "AB2018"
CURACAO_WORDS = {"ku", "kos", "kon", "ki"}
CURACAO_K_RE = re.compile(r"k[aou]")
CURLY_APOSTROPHES = ("’", "‘")
# Characters allowed in Aruban text without an allowlist entry.
ARUBAN_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "ñÑ' -."
)


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

class Finding(object):
    def __init__(self, gate, severity, path, line, message):
        # type: (str, str, str, Optional[int], str) -> None
        self.gate = gate
        self.severity = severity
        self.path = path
        self.line = line
        self.message = message

    def to_dict(self):
        return {
            "gate": self.gate,
            "severity": self.severity,
            "path": self.path,
            "line": self.line,
            "message": self.message,
        }

    def location(self):
        if self.line is None:
            return "%s:" % self.path
        return "%s:%d:" % (self.path, self.line)


class Table(object):
    def __init__(self, name, glob, schema_path, schema):
        self.name = name
        self.glob = glob
        self.schema_path = schema_path
        self.schema = schema  # type: dict
        fields = schema.get("fields") if isinstance(schema, dict) else None
        self.fields = []  # type: List[dict]
        if isinstance(fields, list):
            self.fields = [f for f in fields if isinstance(f, dict) and "name" in f]
        self.field_names = [str(f["name"]) for f in self.fields]
        x = schema.get("x-papiamento") if isinstance(schema, dict) else None
        self.x = x if isinstance(x, dict) else {}
        self.files = []  # type: List[TsvFile]

    def has(self, field):
        return field in self.field_names

    def rows(self):
        for f in self.files:
            for r in f.rows:
                yield r


class Row(object):
    def __init__(self, tsv, line, cells):
        self.file = tsv  # type: TsvFile
        self.line = line  # type: int
        self.cells = cells  # type: Dict[str, str]

    def get(self, field):
        return self.cells.get(field, "")


class TsvFile(object):
    def __init__(self, rel, table):
        self.rel = rel  # type: str
        self.table = table  # type: Table
        self.rows = []  # type: List[Row]
        self.header_ok = False


class Context(object):
    def __init__(self, root):
        self.root = root  # type: Path
        self.findings = []  # type: List[Finding]
        self.registry = {}  # type: dict
        self.tables = {}  # type: Dict[str, Table]
        self.files = []  # type: List[TsvFile]
        self.allowlist = set()  # type: Set[str]
        self.source_ids = None  # type: Optional[Set[str]]
        self.facts_total = 0
        self.facts_checked = 0
        self.facts_pending = 0

    def add(self, gate, severity, path, line, message):
        self.findings.append(Finding(gate, severity, path, line, message))

    @property
    def rows_checked(self):
        return sum(len(f.rows) for f in self.files)


def split_multi(value):
    # type: (str) -> List[str]
    return [v for v in value.split(MULTI_SEP) if v != ""]


def strip_accents(text):
    # type: (str) -> str
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


# --------------------------------------------------------------------------
# Loading: registry, schemas, allowlist
# --------------------------------------------------------------------------

def load_json(ctx, rel, gate="G2"):
    path = ctx.root / rel
    try:
        with open(str(path), "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except FileNotFoundError:
        ctx.add(gate, ERROR, rel, None, "file not found")
    except (ValueError, UnicodeDecodeError) as exc:
        ctx.add(gate, ERROR, rel, None, "invalid JSON: %s" % exc)
    except OSError as exc:
        ctx.add(gate, ERROR, rel, None, "cannot read: %s" % exc)
    return None


def load_registry(ctx):
    # type: (Context) -> bool
    registry = load_json(ctx, REGISTRY_PATH)
    if not isinstance(registry, dict):
        if registry is not None:
            ctx.add("G2", ERROR, REGISTRY_PATH, None, "registry must be a JSON object")
        return False
    ctx.registry = registry
    schema_dir = Path(REGISTRY_PATH).parent
    tables = registry.get("tables")
    if not isinstance(tables, list):
        ctx.add("G2", ERROR, REGISTRY_PATH, None, "registry has no 'tables' list")
        return False
    for entry in tables:
        if not isinstance(entry, dict) or not all(k in entry for k in ("name", "glob", "schema")):
            ctx.add("G2", ERROR, REGISTRY_PATH, None,
                    "registry table entry needs name, glob and schema: %r" % (entry,))
            continue
        schema_rel = (schema_dir / str(entry["schema"])).as_posix()
        schema = load_json(ctx, schema_rel)
        if not isinstance(schema, dict):
            continue
        table = Table(str(entry["name"]), str(entry["glob"]), schema_rel, schema)
        if not table.field_names:
            ctx.add("G2", ERROR, schema_rel, None, "schema has no fields")
            continue
        for fspec in table.fields:
            pattern = (fspec.get("constraints") or {}).get("pattern")
            if pattern is not None:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    ctx.add("G2", ERROR, schema_rel, None,
                            "field %s has an invalid pattern: %s" % (fspec["name"], exc))
        ctx.tables[table.name] = table
    return True


def load_allowlist(ctx):
    rel = (ctx.registry.get("allowlists") or {}).get("accented_loans")
    if not rel:
        return
    path = ctx.root / rel
    try:
        text = path.read_bytes().decode("utf-8")
    except FileNotFoundError:
        ctx.add("G3", WARNING, rel, None, "accented-loans allowlist not found")
        return
    except (OSError, UnicodeDecodeError) as exc:
        ctx.add("G3", ERROR, rel, None, "cannot read allowlist: %s" % exc)
        return
    for line in text.splitlines():
        word = line.strip()
        if word and not word.startswith("#"):
            ctx.allowlist.add(unicodedata.normalize("NFC", word))


# --------------------------------------------------------------------------
# G1 Format + G2 Schema (per file)
# --------------------------------------------------------------------------

def read_tsv(ctx, table, path):
    # type: (Context, Table, Path) -> TsvFile
    rel = path.relative_to(ctx.root).as_posix()
    tsv = TsvFile(rel, table)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        ctx.add("G1", ERROR, rel, None, "cannot read file: %s" % exc)
        return tsv
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        line = raw[:exc.start].count(b"\n") + 1
        ctx.add("G1", ERROR, rel, line, "not valid UTF-8 (byte offset %d)" % exc.start)
        return tsv
    if text.startswith("﻿"):
        ctx.add("G1", ERROR, rel, 1, "file starts with a byte-order mark (BOM)")
        text = text[1:]
    if text == "":
        ctx.add("G1", ERROR, rel, None, "file is empty (needs at least a header)")
        return tsv
    if "\r" in text:
        line = text[:text.index("\r")].count("\n") + 1
        ctx.add("G1", ERROR, rel, line, "carriage return (\\r) found; use LF line endings")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        ctx.add("G1", ERROR, rel, text.count("\n") + 1, "missing final newline")
    else:
        text = text[:-1]
    lines = text.split("\n")
    for i, line in enumerate(lines, start=1):
        if unicodedata.normalize("NFC", line) != line:
            ctx.add("G1", ERROR, rel, i, "text is not Unicode NFC (first such line)")
            break

    header = lines[0].split("\t")
    if header != table.field_names:
        ctx.add("G1", ERROR, rel, 1, header_diff(header, table.field_names))
        return tsv
    tsv.header_ok = True

    unique_seen = {}  # type: Dict[str, Dict[str, int]]
    for lineno, line in enumerate(lines[1:], start=2):
        if line == "":
            ctx.add("G1", ERROR, rel, lineno, "blank line")
            continue
        cells = line.split("\t")
        if len(cells) != len(table.field_names):
            ctx.add("G1", ERROR, rel, lineno,
                    "has %d cells, header has %d" % (len(cells), len(table.field_names)))
            continue
        row = Row(tsv, lineno, dict(zip(table.field_names, cells)))
        check_cells(ctx, row)
        check_schema(ctx, row, unique_seen)
        tsv.rows.append(row)

    check_sort(ctx, tsv)
    return tsv


def header_diff(got, want):
    # type: (List[str], List[str]) -> str
    for i in range(max(len(got), len(want))):
        g = got[i] if i < len(got) else "<missing>"
        w = want[i] if i < len(want) else "<extra>"
        if g != w:
            return ("header does not match schema: column %d is %r, expected %r "
                    "(expected header: %s)" % (i + 1, g, w, "\\t".join(want)))
    return "header does not match schema"


def check_cells(ctx, row):
    # type: (Context, Row) -> None
    rel = row.file.rel
    for field in row.file.table.field_names:
        value = row.cells[field]
        if value != value.strip():
            ctx.add("G1", ERROR, rel, row.line,
                    "%s: leading or trailing whitespace in %r" % (field, value))
        if "  " in value:
            ctx.add("G1", ERROR, rel, row.line, "%s: double space in %r" % (field, value))
        if any(c in value for c in CURLY_APOSTROPHES):
            ctx.add("G1", ERROR, rel, row.line,
                    "%s: curly apostrophe in %r; use a straight ' " % (field, value))
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            ctx.add("G1", WARNING, rel, row.line,
                    "%s: cell is wrapped in double quotes; TSV cells are never quoted" % field)


def check_sort(ctx, tsv):
    # type: (Context, TsvFile) -> None
    sort_by = tsv.table.x.get("sort_by")
    if not isinstance(sort_by, list) or not sort_by:
        return
    fields = [f for f in sort_by if tsv.table.has(f)]
    prev = None
    for row in tsv.rows:
        key = tuple(row.get(f).casefold() for f in fields)
        if prev is not None and key < prev:
            ctx.add("G1", ERROR, tsv.rel, row.line,
                    "rows not sorted by %s (case-insensitive); first out-of-order row"
                    % ", ".join(fields))
            return
        prev = key


def check_schema(ctx, row, unique_seen):
    # type: (Context, Row, Dict[str, Dict[str, int]]) -> None
    rel = row.file.rel
    table = row.file.table
    for fspec in table.fields:
        name = fspec["name"]
        value = row.cells.get(name, "")
        cons = fspec.get("constraints") or {}
        if not isinstance(cons, dict):
            continue
        if cons.get("required") and value == "":
            ctx.add("G2", ERROR, rel, row.line, "%s is required" % name)
            continue
        if value == "":
            continue
        enum = cons.get("enum")
        if isinstance(enum, list) and value not in enum:
            ctx.add("G2", ERROR, rel, row.line,
                    "%s: %r is not one of %s" % (name, value, ", ".join(map(str, enum))))
        pattern = cons.get("pattern")
        if pattern is not None:
            try:
                ok = re.fullmatch(pattern, value) is not None
            except re.error:
                ok = True  # already reported against the schema
            if not ok:
                ctx.add("G2", ERROR, rel, row.line,
                        "%s: %r does not match pattern %s" % (name, value, pattern))
        if cons.get("unique"):
            seen = unique_seen.setdefault(name, {})
            if value in seen:
                ctx.add("G2", ERROR, rel, row.line,
                        "%s: duplicate value %r (first on line %d)" % (name, value, seen[value]))
            else:
                seen[value] = row.line
    if table.has("status") and table.has("reviewed_by"):
        if row.get("status") == "reviewed" and row.get("reviewed_by") == "":
            ctx.add("G2", ERROR, rel, row.line, "status is reviewed but reviewed_by is empty")
    # x-papiamento required_if_any: {"translated_by": ["en", "nl", "es"]} means
    # translated_by must be filled whenever any of en, nl, es is.
    for name, triggers in (table.x.get("required_if_any") or {}).items():
        if not table.has(name) or row.get(name):
            continue
        filled = [t for t in triggers if table.has(t) and row.get(t)]
        if filled:
            ctx.add("G2", ERROR, rel, row.line,
                    "%s is required when %s is filled" % (name, ", ".join(filled)))


def load_files(ctx):
    seen = set()  # type: Set[Path]
    for table in ctx.tables.values():
        try:
            paths = sorted(p for p in ctx.root.glob(table.glob) if p.is_file())
        except (ValueError, OSError) as exc:
            ctx.add("G2", ERROR, REGISTRY_PATH, None,
                    "bad glob %r for table %s: %s" % (table.glob, table.name, exc))
            continue
        for path in paths:
            if path in seen:
                continue
            seen.add(path)
            tsv = read_tsv(ctx, table, path)
            table.files.append(tsv)
            ctx.files.append(tsv)


# --------------------------------------------------------------------------
# G0 Source trace
# --------------------------------------------------------------------------

def gate_g0(ctx):
    sources = ctx.tables.get("sources")
    sources_rel = sources.glob if sources else "sources/sources.tsv"
    if sources is None or not sources.files:
        ctx.add("G0", WARNING, sources_rel, None,
                "sources registry not found; source ids are not checked")
        ctx.source_ids = None
    elif not all(f.header_ok for f in sources.files):
        ctx.source_ids = None  # unreadable; G1 already reported it
    else:
        ctx.source_ids = set(r.get("id") for r in sources.rows())

    for tsv in ctx.files:
        table = tsv.table
        if not table.has("source") or table.name == "sources":
            continue
        has_status = table.has("status")
        has_page = table.has("page")
        for row in tsv.rows:
            src = row.get("source")
            page = row.get("page")
            if src and ctx.source_ids is not None and src not in ctx.source_ids:
                ctx.add("G0", ERROR, tsv.rel, row.line,
                        "source %r is not an id in sources/sources.tsv" % src)
            if has_status and row.get("status") == "reviewed":
                if not src or (has_page and not page):
                    ctx.add("G0", ERROR, tsv.rel, row.line,
                            "reviewed row must have both source and page")
            elif src and has_page and not page:
                ctx.add("G0", WARNING, tsv.rel, row.line,
                        "untraced: source %s but no page" % src)

    check_sources_registry(ctx, sources)
    check_pdfs(ctx, sources)


def check_sources_registry(ctx, sources):
    if sources is None:
        return
    shareable = set(ctx.registry.get("shareable_licence_tiers") or [])
    for row in sources.rows():
        rel = row.file.rel
        tier = row.get("licence_tier")
        if tier == "permission" and not row.get("permission_ref"):
            ctx.add("G0", ERROR, rel, row.line,
                    "%s: licence_tier permission needs a permission_ref" % row.get("id"))
        pdf = row.get("pdf")
        if pdf:
            if tier not in shareable:
                ctx.add("G0", ERROR, rel, row.line,
                        "%s: has a pdf but licence_tier %r is not shareable (allowed: %s)"
                        % (row.get("id"), tier, ", ".join(sorted(shareable))))
            if not (ctx.root / pdf).is_file():
                ctx.add("G0", ERROR, rel, row.line,
                        "%s: pdf %s does not exist" % (row.get("id"), pdf))
        card = row.get("card")
        if card and not (ctx.root / card).is_file():
            ctx.add("G0", ERROR, rel, row.line,
                    "%s: card %s does not exist" % (row.get("id"), card))


def check_pdfs(ctx, sources):
    pdf_dir_rel = ctx.registry.get("pdf_dir")
    if not pdf_dir_rel:
        return
    pdf_dir = ctx.root / pdf_dir_rel
    if not pdf_dir.is_dir():
        return
    refs = {}  # type: Dict[str, List[Row]]
    if sources is not None:
        for row in sources.rows():
            if row.get("pdf"):
                refs.setdefault(row.get("pdf"), []).append(row)
    for path in sorted(pdf_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        rel = path.relative_to(ctx.root).as_posix()
        rows = refs.get(rel, [])
        if not rows:
            ctx.add("G0", ERROR, rel, None,
                    "PDF is not referenced by any sources/sources.tsv row; "
                    "only shareable sources may be committed")
        elif len(rows) > 1:
            ctx.add("G0", ERROR, rel, None,
                    "PDF is referenced by %d sources rows (%s); expected exactly one"
                    % (len(rows), ", ".join(r.get("id") for r in rows)))


# --------------------------------------------------------------------------
# G3 Orthography
# --------------------------------------------------------------------------

def gate_g3(ctx):
    for tsv in ctx.files:
        table = tsv.table
        fields = [f for f in (table.x.get("aruban_text") or []) if table.has(f)]
        letter_field = table.x.get("letter_folder")
        for row in tsv.rows:
            exempt = row.get("source") == AB_SOURCE_ID
            for field in fields:
                for item in split_multi(row.get(field)):
                    for word in item.split(" "):
                        if word:
                            check_word(ctx, row, field, word, exempt)
            if letter_field and table.has(letter_field):
                check_letter_folder(ctx, row, letter_field)


def check_word(ctx, row, field, word, exempt_curacao):
    rel = row.file.rel
    bad = [c for c in word if c not in ARUBAN_ALLOWED]
    if bad:
        bare = word.strip(".'-")
        if word not in ctx.allowlist and bare not in ctx.allowlist:
            accented = [c for c in bad if strip_accents(c) != c]
            kind = "accented letter" if accented else "character not used in Aruban spelling"
            ctx.add("G3", ERROR, rel, row.line,
                    "%s: %r has %s %s; not in the accented-loans allowlist"
                    % (field, word, kind, " ".join(sorted(set(bad)))))
    if exempt_curacao:
        return
    lw = word.casefold().strip(".'-")
    reasons = []
    if lw.endswith("shon"):
        reasons.append("ends in -shon")
    if CURACAO_K_RE.search(lw):
        reasons.append("k before a/o/u")
    if lw in CURACAO_WORDS:
        reasons.append("Curacao function word")
    if reasons:
        ctx.add("G3", WARNING, rel, row.line,
                "%s: %r looks like Curacao spelling (%s)" % (field, word, ", ".join(reasons)))


def check_letter_folder(ctx, row, field):
    lemma = row.get(field)
    if not lemma:
        return
    folder = Path(row.file.rel).parent.name
    first = next((c for c in lemma if c.isalpha()), None)
    if first is None:
        ctx.add("G3", ERROR, row.file.rel, row.line,
                "%s %r has no letter to file it under" % (field, lemma))
        return
    expected = strip_accents(first).upper()
    if folder != expected:
        ctx.add("G3", ERROR, row.file.rel, row.line,
                "%s %r belongs in letter folder %s, not %s" % (field, lemma, expected, folder))


# --------------------------------------------------------------------------
# G4 Integrity
# --------------------------------------------------------------------------

def gate_g4(ctx):
    ids = {}  # type: Dict[str, Row]
    for tsv in ctx.files:
        if not tsv.table.has("id"):
            continue
        for row in tsv.rows:
            value = row.get("id")
            if not value:
                continue
            first = ids.get(value)
            if first is None:
                ids[value] = row
            elif first.file is not tsv:  # same-file duplicates are G2's job
                ctx.add("G4", ERROR, tsv.rel, row.line,
                        "id %r is already used at %s:%d" % (value, first.file.rel, first.line))

    for table in ctx.tables.values():
        for combo in table.x.get("unique_together") or []:
            if not isinstance(combo, list) or not all(table.has(f) for f in combo):
                ctx.add("G4", ERROR, table.schema_path, None,
                        "unique_together %r names unknown fields" % (combo,))
                continue
            seen = {}  # type: Dict[Tuple[str, ...], Row]
            for row in table.rows():
                key = tuple(row.get(f) for f in combo)
                first = seen.get(key)
                if first is None:
                    seen[key] = row
                else:
                    ctx.add("G4", ERROR, row.file.rel, row.line,
                            "%s %s duplicates %s:%d"
                            % ("+".join(combo), "|".join(key), first.file.rel, first.line))

    words = ctx.tables.get("words")
    if words is None or not words.files:
        return
    lemmas = set(r.get("lemma") for r in words.rows())
    for tsv in ctx.files:
        refs = [f for f in (tsv.table.x.get("lexicon_refs") or []) if tsv.table.has(f)]
        for row in tsv.rows:
            for field in refs:
                for value in split_multi(row.get(field)):
                    if value not in lemmas:
                        ctx.add("G4", WARNING, tsv.rel, row.line,
                                "%s: %r is not a lemma in lexicon/words" % (field, value))


# --------------------------------------------------------------------------
# G5 Known facts (and, later, rule tests)
# --------------------------------------------------------------------------

def parse_where(where):
    # type: (str) -> Optional[List[Tuple[str, str]]]
    pairs = []
    for part in where.split("&"):
        if "=" not in part:
            return None
        k, v = part.split("=", 1)
        if not k:
            return None
        pairs.append((k, v))
    return pairs or None


MATCH_VERBS = {"equals": "equal", "contains": "contain", "not-contains": "not contain"}


def fact_holds(match, cell, value):
    # type: (str, str, str) -> bool
    if match == "equals":
        return cell == value
    items = [i.casefold() for i in split_multi(cell)]
    if match == "contains":
        return value.casefold() in items
    if match == "not-contains":
        return value.casefold() not in items
    return True


def check_known_facts(ctx):
    facts = ctx.tables.get("known-facts")
    if facts is None:
        return
    for fact in facts.rows():
        ctx.facts_total += 1
        fid = fact.get("id")
        where = parse_where(fact.get("where"))
        field = fact.get("field")
        match = fact.get("match")
        value = fact.get("value")
        target = ctx.tables.get(fact.get("table"))
        if where is None or target is None or match not in ("equals", "contains", "not-contains"):
            continue  # G2 reports malformed fact rows
        unknown = [k for k, _ in where if not target.has(k)]
        if not target.has(field):
            unknown.append(field)
        if unknown:
            ctx.add("G5", ERROR, fact.file.rel, fact.line,
                    "%s: table %s has no column(s) %s" % (fid, target.name, ", ".join(unknown)))
            continue
        # An empty cell means "not known yet" (conventions), so a fact only
        # constrains rows where the field has been filled in.
        rows = [r for r in target.rows()
                if r.get("status") != "deprecated"
                and all(r.get(k) == v for k, v in where)
                and r.get(field)]
        if not rows:
            ctx.facts_pending += 1
            continue
        ctx.facts_checked += 1
        for row in rows:
            cell = row.get(field)
            if not fact_holds(match, cell, value):
                notes = fact.get("notes")
                ctx.add("G5", ERROR, row.file.rel, row.line,
                        "%s violated: %s where %s: %s must %s %r, found %r%s"
                        % (fid, target.name, fact.get("where"), field, MATCH_VERBS[match],
                           value, cell,
                           (" (ruling: %s)" % notes) if notes else ""))


# Each G5 check takes the Context and appends findings. Rule tests go here.
G5_CHECKS = [check_known_facts]  # type: List[Callable[[Context], None]]


def gate_g5(ctx):
    for check in G5_CHECKS:
        check(ctx)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def run(root, strict=False):
    # type: (Path, bool) -> Context
    ctx = Context(root)
    if not root.is_dir():
        ctx.add("G1", ERROR, str(root), None, "root is not a directory")
        return ctx
    try:
        ok = load_registry(ctx)
    except Exception as exc:  # never crash on bad data
        ctx.add("G2", ERROR, REGISTRY_PATH, None, "validator failed to load registry: %r" % exc)
        ok = False
    if ok:
        for gate, step in (("G3", load_allowlist), ("G1", load_files), ("G0", gate_g0),
                           ("G3", gate_g3), ("G4", gate_g4), ("G5", gate_g5)):
            try:
                step(ctx)
            except Exception as exc:
                ctx.add(gate, ERROR, "tools/validate.py", None,
                        "internal error in %s: %r (please report)" % (step.__name__, exc))
    if strict:
        for f in ctx.findings:
            f.severity = ERROR
    return ctx


def summarize(ctx):
    gates = {}
    for g in GATES:
        gates[g] = {"errors": 0, "warnings": 0}
    for f in ctx.findings:
        key = "errors" if f.severity == ERROR else "warnings"
        gates.setdefault(f.gate, {"errors": 0, "warnings": 0})[key] += 1
    return gates


def is_ok(ctx):
    return not any(f.severity == ERROR for f in ctx.findings)


def sorted_findings(ctx):
    order = dict((g, i) for i, g in enumerate(GATES))
    return sorted(ctx.findings, key=lambda f: (order.get(f.gate, 99), f.path,
                                              f.line if f.line is not None else 0))


def report_json(ctx):
    return {
        "ok": is_ok(ctx),
        "gates": summarize(ctx),
        "findings": [f.to_dict() for f in sorted_findings(ctx)],
        "files_checked": len(ctx.files),
        "rows_checked": ctx.rows_checked,
        "known_facts": {"total": ctx.facts_total, "checked": ctx.facts_checked,
                        "pending": ctx.facts_pending},
    }


def report_text(ctx):
    out = []
    current = None
    for f in sorted_findings(ctx):
        if f.gate != current:
            current = f.gate
            out.append("== %s %s" % (f.gate, GATE_TITLES.get(f.gate, "")))
        out.append("%s [%s] %s %s" % (f.location(), f.gate, f.severity.upper(), f.message))
    gates = summarize(ctx)
    parts = ["%s %d error(s) %d warning(s)" % (g, gates[g]["errors"], gates[g]["warnings"])
             for g in GATES]
    out.append("")
    out.append("Gauntlet: %d file(s), %d row(s) checked; known facts: %d checked, %d pending"
               % (len(ctx.files), ctx.rows_checked, ctx.facts_checked, ctx.facts_pending))
    out.append(" | ".join(parts))
    out.append("RESULT: %s" % ("PASS" if is_ok(ctx) else "FAIL"))
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the papiamento dataset (the gauntlet).")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent),
                        help="repo root (default: parent of tools/)")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args(argv)
    ctx = run(Path(args.root).resolve(), strict=args.strict)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass
    if args.json:
        print(json.dumps(report_json(ctx), ensure_ascii=False, indent=2))
    else:
        print(report_text(ctx))
    return 0 if is_ok(ctx) else 1


if __name__ == "__main__":
    sys.exit(main())

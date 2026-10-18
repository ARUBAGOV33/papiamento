#!/usr/bin/env python3
"""The gauntlet: validates every data file in the papiamento repo.

Usage: python3 tools/validate.py [--root PATH] [--json] [--strict]

Gates
  G0 Source trace   every row cites a known source; PDFs are shareable and only in sources/pdf/
  G1 Format         UTF-8, NFC, LF, final newline, header, columns, cells, sort;
                    every registry table and rules/rules.jsonl present
  G2 Schema         required / enum / pattern / unique, reviewed_by; grammar rule files;
                    the schemas themselves (x-papiamento and constraint keys)
  G3 Orthography    accents, Curacao markers, letter folders
  G4 Integrity      ids unique repo-wide, unique_together, lexicon refs, rule refs
  G5 Known facts    rulings in _meta/known-facts.tsv; machine rules in rules/rules.jsonl tested
                    against their grammar files' examples (extension point: G5_CHECKS)

Exit codes: 0 no errors, 1 errors found (or warnings with --strict),
2 bad command line.

Standard library only; Python 3.9 compatible. Bad data never crashes the
validator: every problem becomes a finding.
"""

import argparse
import json
import os
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
WHOLE_NUMBER_RE = re.compile(r"[0-9]+")
# Characters allowed in Aruban text without an allowlist entry.
ARUBAN_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "ñÑ' -."
)
# Word-level rules (barbarismos) have RULE_LEX_* ids: the row itself is the
# rule, so there is no grammar file for them (grammar/README.md).
LEX_RULE_PREFIX = "RULE_LEX_"

# What the validator reads from a schema. A key it does not know would
# silently switch a check off, so unknown keys are errors.
SCHEMA_KEYS = ("$comment", "title", "description", "fields", "primaryKey", "foreignKeys", "x-papiamento")
FIELD_KEYS = ("name", "title", "type", "format", "description", "constraints")
CONSTRAINT_KEYS = ("required", "enum", "pattern", "unique")
# x-papiamento keys and the shape of their value.
X_KEYS = {
    "sort_by": "fields",          # ["lemma", "pos"]
    "aruban_text": "fields",
    "lexicon_refs": "fields",
    "rule_refs": "fields",
    "letter_folder": "field",     # "lemma"
    "unique_together": "groups",  # [["lemma", "pos", "tag"]]
    "at_most": "pairs",           # [["errors", "sample_size"]]
    "required_if_any": "map",     # {"translated_by": ["en", "nl", "es"]}
    "contributor_refs": "fields", # ["translated_by", "reviewed_by"]: handles in _meta/contributors.tsv
    "folder_refs": "files",       # {"prompt_id": "prompts.tsv"}: an id in that file, same folder
}
X_SHAPES = {
    "field": "a field name",
    "fields": "a list of field names",
    "groups": "a list of non-empty lists of field names",
    "pairs": "a list of [field, field] pairs",
    "map": "an object mapping a field name to a list of field names",
    "files": "an object mapping a field name to a .tsv file name in the same folder",
}
# Folders that are not part of the dataset: build output and local tool
# folders. Hidden folders other than .github (.git, .claude worktrees, .venv)
# are skipped too.
SKIP_DIRS = {"dist", "node_modules", "__pycache__"}


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
    def __init__(self, name, glob, schema_path, schema, optional=False):
        self.name = name
        self.glob = glob
        self.optional = optional  # may match no file (registry "optional": true)
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
        self.facts_pending_ids = []  # type: List[str]
        self.grammar_ids = set()  # type: Set[str]
        self.grammar_checked = 0
        self.rules_checked = 0

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
        optional = entry.get("optional", False)
        if not isinstance(optional, bool):
            ctx.add("G2", ERROR, REGISTRY_PATH, None,
                    "table %s: optional must be true or false, not %r" % (entry["name"], optional))
            optional = False
        schema_rel = (schema_dir / str(entry["schema"])).as_posix()
        schema = load_json(ctx, schema_rel)
        if not isinstance(schema, dict):
            continue
        table = Table(str(entry["name"]), str(entry["glob"]), schema_rel, schema, optional)
        if not table.field_names:
            ctx.add("G2", ERROR, schema_rel, None, "schema has no fields")
            continue
        check_schema_keys(ctx, table)
        ctx.tables[table.name] = table
    return True


def check_schema_keys(ctx, table):
    # type: (Context, Table) -> None
    """Report schema keys the validator does not know or that name no field:
    a typo in them would silently switch a check off."""
    rel = table.schema_path
    unknown = sorted(set(table.schema) - set(SCHEMA_KEYS))
    if unknown:
        ctx.add("G2", ERROR, rel, None, "unknown schema key(s) %s (known: %s)"
                % (", ".join(unknown), ", ".join(SCHEMA_KEYS)))
    if "x-papiamento" in table.schema and not isinstance(table.schema["x-papiamento"], dict):
        ctx.add("G2", ERROR, rel, None, "x-papiamento must be an object")
    for fspec in table.fields:
        name = fspec["name"]
        unknown = sorted(set(fspec) - set(FIELD_KEYS))
        if unknown:
            ctx.add("G2", ERROR, rel, None, "field %s: unknown key(s) %s (known: %s)"
                    % (name, ", ".join(unknown), ", ".join(FIELD_KEYS)))
        cons = fspec.get("constraints") or {}
        if not isinstance(cons, dict):
            ctx.add("G2", ERROR, rel, None, "field %s: constraints must be an object" % name)
            continue
        unknown = sorted(set(cons) - set(CONSTRAINT_KEYS))
        if unknown:
            ctx.add("G2", ERROR, rel, None, "field %s: constraint(s) %s are not checked by the validator (known: %s)"
                    % (name, ", ".join(unknown), ", ".join(CONSTRAINT_KEYS)))
        pattern = cons.get("pattern")
        if pattern is not None:
            try:
                re.compile(pattern)
            except (re.error, TypeError) as exc:
                ctx.add("G2", ERROR, rel, None, "field %s has an invalid pattern: %s" % (name, exc))
    for key, value in sorted(table.x.items()):
        shape = X_KEYS.get(key)
        if shape is None:
            ctx.add("G2", ERROR, rel, None, "unknown x-papiamento key %r (known: %s)"
                    % (key, ", ".join(sorted(X_KEYS))))
        elif not x_value_ok(table, shape, value):
            ctx.add("G2", ERROR, rel, None, "x-papiamento %s must be %s of this table, got %s"
                    % (key, X_SHAPES[shape], json.dumps(value, ensure_ascii=False)))


def x_value_ok(table, shape, value):
    # type: (Table, str, object) -> bool
    def names(v, size=None):
        return (isinstance(v, list) and (size is None or len(v) == size)
                and all(isinstance(f, str) and table.has(f) for f in v))
    if shape == "field":
        return isinstance(value, str) and table.has(value)
    if shape == "fields":
        return names(value)
    if shape == "groups":
        return isinstance(value, list) and all(names(g) and g for g in value)
    if shape == "pairs":
        return isinstance(value, list) and all(names(g, 2) for g in value)
    if shape == "map":
        return isinstance(value, dict) and all(table.has(k) and names(v) for k, v in value.items())
    if shape == "files":
        return isinstance(value, dict) and all(
            table.has(k) and isinstance(v, str) and v.endswith(".tsv") and "/" not in v for k, v in value.items())
    return False


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
        if not value.isprintable():
            ctx.add("G1", ERROR, rel, row.line,
                    "%s: hidden or line-breaking character(s) %s in %r; cells hold only visible "
                    "characters and plain spaces" % (field, ", ".join(hidden_chars(value)), value))
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            ctx.add("G1", WARNING, rel, row.line,
                    "%s: cell is wrapped in double quotes; TSV cells are never quoted" % field)


def hidden_chars(value):
    # type: (str) -> List[str]
    """Characters str.isprintable() rejects: control and format characters,
    line and paragraph separators, and every space but U+0020 (such as the
    no-break space), as U+XXXX NAME."""
    out = []
    for c in sorted(set(c for c in value if not c.isprintable())):
        name = unicodedata.name(c, "")
        out.append("U+%04X%s" % (ord(c), " " + name if name else ""))
    return out


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
            except (re.error, TypeError):
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
        bots = machine_reviewers(row.get("reviewed_by"))
        if bots:
            ctx.add("G2", ERROR, rel, row.line,
                    "reviewed_by must name people, not %s: machine-made content stays draft" % ", ".join(bots))
    # x-papiamento required_if_any: {"translated_by": ["en", "nl", "es"]} means
    # translated_by must be filled whenever any of en, nl, es is.
    for name, triggers in (table.x.get("required_if_any") or {}).items():
        if not table.has(name) or row.get(name):
            continue
        filled = [t for t in triggers if table.has(t) and row.get(t)]
        if filled:
            ctx.add("G2", ERROR, rel, row.line,
                    "%s is required when %s is filled" % (name, ", ".join(filled)))
    # x-papiamento at_most: [["errors", "sample_size"]] means errors can never
    # be greater than sample_size. Cells that are not whole numbers are left
    # to the patterns.
    for pair in table.x.get("at_most") or []:
        if not (isinstance(pair, list) and len(pair) == 2 and all(table.has(f) for f in pair)):
            continue  # reported against the schema
        small, big = row.get(pair[0]), row.get(pair[1])
        if WHOLE_NUMBER_RE.fullmatch(small) and WHOLE_NUMBER_RE.fullmatch(big) and int(small) > int(big):
            ctx.add("G2", ERROR, rel, row.line,
                    "%s (%s) is greater than %s (%s)" % (pair[0], small, pair[1], big))


def load_files(ctx):
    seen = set()  # type: Set[Path]
    for table in ctx.tables.values():
        try:
            paths = sorted(p for p in ctx.root.glob(table.glob) if p.is_file())
        except (ValueError, OSError) as exc:
            ctx.add("G2", ERROR, REGISTRY_PATH, None,
                    "bad glob %r for table %s: %s" % (table.glob, table.name, exc))
            continue
        if not paths and not table.optional:
            # A typo in the glob, or a moved folder, would otherwise drop the
            # whole table from the gauntlet and the release.
            ctx.add("G1", ERROR, REGISTRY_PATH, None,
                    "table %s: glob %r matches no file; fix the glob or restore the files "
                    "(a table that may have no file yet needs \"optional\": true)" % (table.name, table.glob))
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
            elif not src:
                ctx.add("G0", WARNING, tsv.rel, row.line,
                        "untraced: no source%s" % (" for page %s" % page if page else ""))
            elif has_page and not page:
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


def repo_files(root, suffix):
    """Every file under root whose name ends in suffix (case-insensitive),
    skipping SKIP_DIRS and hidden folders other than .github."""
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and (not d.startswith(".") or d == ".github"))
        for name in sorted(filenames):
            if name.lower().endswith(suffix):
                yield Path(dirpath) / name


def check_pdfs(ctx, sources):
    pdf_dir_rel = str(ctx.registry.get("pdf_dir") or "").strip("/")
    refs = {}  # type: Dict[str, List[Row]]
    if sources is not None:
        for row in sources.rows():
            if row.get("pdf"):
                refs.setdefault(row.get("pdf"), []).append(row)
    for path in repo_files(ctx.root, ".pdf"):
        if not path.is_file():
            continue
        rel = path.relative_to(ctx.root).as_posix()
        if not pdf_dir_rel or not rel.startswith(pdf_dir_rel + "/"):
            ctx.add("G0", ERROR, rel, None,
                    "PDF outside %s/: source PDFs are committed only there, and only for "
                    "shareable sources" % (pdf_dir_rel or "the registry's pdf_dir"))
            continue
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
            if not isinstance(combo, list) or not combo or not all(table.has(f) for f in combo):
                continue  # reported against the schema
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

    # x-papiamento rule_refs: the cell names the grammar rule that catches the
    # row. RULE_LEX_* ids are row-level and have no grammar file.
    for tsv in ctx.files:
        refs = [f for f in (tsv.table.x.get("rule_refs") or []) if tsv.table.has(f)]
        for row in tsv.rows:
            for field in refs:
                value = row.get(field)
                if value and not value.startswith(LEX_RULE_PREFIX) and value not in ctx.grammar_ids:
                    ctx.add("G4", WARNING, tsv.rel, row.line,
                            "%s: %r is not the id of a grammar file in grammar/ (only %s* ids are "
                            "row-level and need none)" % (field, value, LEX_RULE_PREFIX))

    check_contributor_refs(ctx)
    check_folder_refs(ctx)

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


def check_contributor_refs(ctx):
    """x-papiamento contributor_refs: every name in those cells is machine or a
    handle (or GitHub username, any case) in _meta/contributors.tsv, so every
    person the data credits is in the contributors list."""
    table = ctx.tables.get("contributors")
    known = set()
    if table is not None:
        for row in table.rows():
            for field in ("handle", "github"):
                if row.get(field):
                    known.add(row.get(field).casefold())
    for tsv in ctx.files:
        refs = [f for f in (tsv.table.x.get("contributor_refs") or []) if tsv.table.has(f)]
        for row in tsv.rows:
            for field in refs:
                for name in split_multi(row.get(field)):
                    if name.casefold() != "machine" and name.casefold() not in known:
                        ctx.add("G4", ERROR, tsv.rel, row.line,
                                "%s: %r is not a handle in _meta/contributors.tsv (add a row there)" % (field, name))


def check_folder_refs(ctx):
    """x-papiamento folder_refs: {"prompt_id": "prompts.tsv"} means the cell is
    an id in prompts.tsv in the same folder. This keeps the held-out eval/
    pairs on eval/ prompts, and corpus/ pairs on corpus/ prompts."""
    by_rel = dict((f.rel, f) for f in ctx.files)
    for tsv in ctx.files:
        for field, name in sorted((tsv.table.x.get("folder_refs") or {}).items()):
            if not tsv.table.has(field) or not isinstance(name, str):
                continue  # reported against the schema
            target_rel = "/".join(tsv.rel.split("/")[:-1] + [name])
            target = by_rel.get(target_rel)
            ids = set(r.get("id") for r in target.rows) if target is not None else set()
            for row in tsv.rows:
                value = row.get(field)
                if value and value not in ids:
                    ctx.add("G4", ERROR, tsv.rel, row.line,
                            "%s: %r is not an id in %s" % (field, value, target_rel))


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
        matched = [r for r in target.rows() if all(r.get(k) == v for k, v in where)]
        # An empty cell means "not known yet" (conventions), so a fact only
        # constrains live rows where the field has been filled in.
        rows = [r for r in matched if r.get("status") != "deprecated" and r.get(field)]
        if not rows:
            ctx.facts_pending += 1
            ctx.facts_pending_ids.append(fid)
            if not matched:
                ctx.add("G5", WARNING, fact.file.rel, fact.line,
                        "%s: no row of %s matches %s (a typo, or the row is not in the data yet)"
                        % (fid, target.name, fact.get("where")))
            elif any(k == "id" for k, _ in where):
                # A ruling on one row (an errata correction) must not be
                # switched off by emptying its cell or deprecating the row.
                if all(r.get("status") == "deprecated" for r in matched):
                    state = "is deprecated"
                else:
                    state = "has an empty %s" % field
                ctx.add("G5", ERROR, fact.file.rel, fact.line,
                        "%s: the row %s %s, so the ruling is no longer checked; restore it, "
                        "or remove the fact if the ruling no longer applies"
                        % (fid, fact.get("where"), state))
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


# --------------------------------------------------------------------------
# Grammar rule files: grammar/<topic>/<rule-id>.md with front matter
# --------------------------------------------------------------------------

GRAMMAR_TOPICS = ("orthography", "morphology", "syntax", "prepositions", "style")
GRAMMAR_REQUIRED = ("id", "title", "status", "source", "page", "severity")
GRAMMAR_STATUS = ("draft", "reviewed", "disputed", "deprecated")
GRAMMAR_SEVERITY = ("error", "warning", "suggestion", "info")
RULING_SOURCE = "RUL2026"  # maintainer rulings have no page
RULE_ID_RE = re.compile(r"^RULE_[A-Z]+_[A-Z0-9_]+$")
GRAMMAR_PAGE_RE = re.compile(r"^([0-9]+(-[0-9]+)?|[ivxlc]+(-[ivxlc]+)?)(; ([0-9]+(-[0-9]+)?))*$")


def parse_front_matter(text):
    # type: (str) -> Tuple[Optional[Dict[str, str]], str]
    """Parse a simple `key: value` front matter block. None if absent or unterminated."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    meta = {}  # type: Dict[str, str]
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            return meta, "\n".join(lines[i + 1:])
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value
    return None, text



def machine_reviewers(cell):
    # type: (str) -> List[str]
    """Names in a reviewed_by cell that are not people: machine, or a [bot] account."""
    names = [v.strip() for v in cell.split(";")]
    return [v for v in names if v.lower() == "machine" or v.lower().endswith("[bot]")]


RULE_SECTION_RE = re.compile(r"^## Rule\n(.*?)(?=\n## |\Z)", re.S | re.M)


def check_grammar(ctx):
    # type: (Context) -> None
    base = ctx.root / "grammar"
    if not base.is_dir():
        return
    seen = {}  # type: Dict[str, str]
    for path in sorted(base.rglob("*.md")):
        if path.name == "README.md":
            continue
        rel = path.relative_to(ctx.root).as_posix()
        parts = path.relative_to(base).parts
        if len(parts) != 2 or parts[0] not in GRAMMAR_TOPICS:
            ctx.add("G2", ERROR, rel, None,
                    "grammar files go in grammar/<topic>/, topic one of: %s" % ", ".join(GRAMMAR_TOPICS))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            ctx.add("G1", ERROR, rel, None, "not valid UTF-8")
            continue
        ctx.grammar_checked += 1
        if "\r" in text:
            ctx.add("G1", ERROR, rel, None, "contains CR characters; use LF line endings")
        if unicodedata.normalize("NFC", text) != text:
            ctx.add("G1", ERROR, rel, None, "text is not Unicode NFC")
        meta, body = parse_front_matter(text)
        if meta is None:
            ctx.add("G2", ERROR, rel, 1, "missing or unterminated front matter (--- ... ---)")
            continue
        for key in GRAMMAR_REQUIRED:
            if not meta.get(key) and not (key == "page" and meta.get("source") == RULING_SOURCE):
                ctx.add("G2", ERROR, rel, None, "front matter: %s is required" % key)
        rid = meta.get("id", "")
        if rid:
            if not RULE_ID_RE.match(rid):
                ctx.add("G2", ERROR, rel, None, "id %r must look like RULE_<DOMAIN>_<NAME>" % rid)
            expected = rid.lower().replace("_", "-") + ".md"
            if path.name != expected:
                ctx.add("G2", ERROR, rel, None, "file name must be %s for id %s" % (expected, rid))
            if rid in seen:
                ctx.add("G4", ERROR, rel, None, "id %s is already used by %s" % (rid, seen[rid]))
            else:
                seen[rid] = rel
                ctx.grammar_ids.add(rid)
        status = meta.get("status", "")
        if status and status not in GRAMMAR_STATUS:
            ctx.add("G2", ERROR, rel, None, "status %r not in %s" % (status, ", ".join(GRAMMAR_STATUS)))
        if status == "reviewed" and not meta.get("reviewed_by"):
            ctx.add("G2", ERROR, rel, None, "status is reviewed but reviewed_by is empty")
        bots = machine_reviewers(meta.get("reviewed_by", ""))
        if bots:
            ctx.add("G2", ERROR, rel, None,
                    "reviewed_by must name people, not %s: machine-made content stays draft" % ", ".join(bots))
        severity = meta.get("severity", "")
        if severity and severity not in GRAMMAR_SEVERITY:
            ctx.add("G2", ERROR, rel, None, "severity %r not in %s" % (severity, ", ".join(GRAMMAR_SEVERITY)))
        source = meta.get("source", "")
        if source and ctx.source_ids is not None and source not in ctx.source_ids:
            ctx.add("G0", ERROR, rel, None, "source %r is not in sources/sources.tsv" % source)
        page = meta.get("page", "")
        if page and not GRAMMAR_PAGE_RE.match(page):
            ctx.add("G2", ERROR, rel, None, "page %r should be printed page number(s), e.g. 38 or 38-39" % page)
        # Same pattern as tools/build_dist.py, which ships the section text.
        rule = RULE_SECTION_RE.search(body)
        if not rule:
            ctx.add("G2", ERROR, rel, None, "missing a '## Rule' section")
        elif not rule.group(1).strip():
            ctx.add("G2", ERROR, rel, None, "the '## Rule' section is empty")


# --------------------------------------------------------------------------
# Machine rules: rules/rules.jsonl, tested against the grammar files' examples
# --------------------------------------------------------------------------

RULES_PATH = "rules/rules.jsonl"
RULE_KEYS = {"rule_id", "pattern", "flags", "replacement", "message", "tests", "derived", "notes",
             "allow_correct_hits"}
# Python-only or non-portable regex syntax. \b and \w are ASCII-only in JavaScript,
# so they misfire next to ñ and accented letters; spell boundaries out instead.
NON_PORTABLE = re.compile(r"\\[bBwW]|\(\?P|\(\?[aiLmsux-]+[):]|\\[AZz]|\(\?<[A-Za-z]")


def grammar_index(ctx):
    # type: (Context) -> Dict[str, Tuple[str, str, Dict[str, str]]]
    out = {}  # type: Dict[str, Tuple[str, str, Dict[str, str]]]
    base = ctx.root / "grammar"
    if not base.is_dir():
        return out
    for path in sorted(base.rglob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        meta, _ = parse_front_matter(text)
        if meta and meta.get("id"):
            out[meta["id"]] = (path.relative_to(ctx.root).as_posix(), text, meta)
    return out


def section_items(text, heading):
    # type: (str, str) -> List[str]
    """The '- item' lines under a '## heading' section of a grammar file."""
    items = []  # type: List[str]
    inside = False
    for line in text.split("\n"):
        if line.startswith("## "):
            inside = line.strip() == "## " + heading
            continue
        if inside and line.startswith("- "):
            items.append(line[2:].strip())
    return items


def py_replacement(repl):
    # type: (str) -> str
    return re.sub(r"\$(\d)", r"\\\1", repl.replace("\\", "\\\\"))


def check_rule_tests(ctx):
    # type: (Context) -> None
    path = ctx.root / RULES_PATH
    if not path.exists():
        ctx.add("G1", ERROR, RULES_PATH, None, "file not found; the machine rules are required")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        ctx.add("G1", ERROR, RULES_PATH, None, "not valid UTF-8")
        return
    index = grammar_index(ctx)
    correct_pool = [(rel, ex) for rel, gtext, _ in index.values() for ex in section_items(gtext, "Correct")]
    seen = set()  # type: Set[str]
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        try:
            rule = json.loads(line)
        except ValueError as exc:
            ctx.add("G2", ERROR, RULES_PATH, n, "not valid JSON: %s" % exc)
            continue
        if not isinstance(rule, dict):
            ctx.add("G2", ERROR, RULES_PATH, n, "each line must be a JSON object")
            continue
        ctx.rules_checked += 1
        rid = rule.get("rule_id", "")
        for key in ("rule_id", "pattern", "message", "tests"):
            if not rule.get(key):
                ctx.add("G2", ERROR, RULES_PATH, n, "%s is required" % key)
        extra = set(rule) - RULE_KEYS
        if extra:
            ctx.add("G2", ERROR, RULES_PATH, n, "unknown key(s): %s" % ", ".join(sorted(extra)))
        if rid in seen:
            ctx.add("G4", ERROR, RULES_PATH, n, "rule %s appears twice" % rid)
        seen.add(rid)
        entry = index.get(rid)
        if entry is None:
            ctx.add("G4", ERROR, RULES_PATH, n, "no grammar file has id %s" % rid)
            continue
        grel, gtext, gmeta = entry
        if gmeta.get("severity") == "info":
            ctx.add("G2", ERROR, RULES_PATH, n, "%s is an info rule (nothing to flag); it needs no machine rule" % rid)
        flags = rule.get("flags", "") or ""
        if any(f not in "i" for f in flags):
            ctx.add("G2", ERROR, RULES_PATH, n, "flags may only be 'i' (got %r)" % flags)
        pattern = rule.get("pattern", "") or ""
        if NON_PORTABLE.search(pattern):
            ctx.add("G2", ERROR, RULES_PATH, n,
                    "%s: pattern uses syntax that behaves differently in JavaScript (\\b, \\w, inline flags, named groups, \\A/\\Z)" % rid)
        try:
            rx = re.compile(pattern, re.IGNORECASE if "i" in flags else 0)
        except re.error as exc:
            ctx.add("G2", ERROR, RULES_PATH, n, "%s: pattern does not compile: %s" % (rid, exc))
            continue
        tests = rule.get("tests") or {}
        if not isinstance(tests, dict):
            ctx.add("G2", ERROR, RULES_PATH, n, "tests must be an object")
            continue
        positives = 0
        for kind in ("match", "no_match"):
            for ex in tests.get(kind) or []:
                if ex not in gtext:
                    ctx.add("G0", ERROR, RULES_PATH, n,
                            "%s: test %r is not printed in %s; tests come verbatim from the grammar file" % (rid, ex, grel))
                hit = rx.search(ex) is not None
                if kind == "match":
                    positives += 1
                    if not hit:
                        ctx.add("G5", ERROR, RULES_PATH, n, "%s: does not catch %r" % (rid, ex))
                elif hit:
                    ctx.add("G5", ERROR, RULES_PATH, n, "%s: wrongly flags the correct example %r" % (rid, ex))
        for d in rule.get("derived") or []:
            if not isinstance(d, dict) or not all(d.get(k) for k in ("text", "from", "change", "expect")):
                ctx.add("G2", ERROR, RULES_PATH, n, "%s: each derived test needs text, from, change and expect" % rid)
                continue
            if d["from"] not in gtext:
                ctx.add("G0", ERROR, RULES_PATH, n,
                        "%s: derived test is based on %r, which is not printed in %s" % (rid, d["from"], grel))
            hit = rx.search(d["text"]) is not None
            if d["expect"] == "match":
                positives += 1
                if not hit:
                    ctx.add("G5", ERROR, RULES_PATH, n, "%s: does not catch derived test %r" % (rid, d["text"]))
            elif d["expect"] == "no_match":
                if hit:
                    ctx.add("G5", ERROR, RULES_PATH, n, "%s: wrongly flags derived test %r" % (rid, d["text"]))
            else:
                ctx.add("G2", ERROR, RULES_PATH, n, "%s: derived expect must be match or no_match" % rid)
        for fx in tests.get("fix") or []:
            if not isinstance(fx, dict) or "text" not in fx or "expect" not in fx:
                ctx.add("G2", ERROR, RULES_PATH, n, "%s: each fix test needs text and expect" % rid)
                continue
            repl = rule.get("replacement")
            if repl is None:
                ctx.add("G2", ERROR, RULES_PATH, n, "%s: fix tests need a replacement" % rid)
                continue
            try:
                got = rx.sub(py_replacement(repl), fx["text"])
            except (re.error, IndexError) as exc:
                ctx.add("G2", ERROR, RULES_PATH, n, "%s: replacement %r cannot be applied: %s" % (rid, repl, exc))
                continue
            if got != fx["expect"]:
                ctx.add("G5", ERROR, RULES_PATH, n, "%s: fixing %r gives %r, expected %r" % (rid, fx["text"], got, fx["expect"]))
        if positives == 0:
            ctx.add("G5", ERROR, RULES_PATH, n, "%s: needs at least one test it must catch" % rid)
        # Every '## Correct' example of every grammar file, the rule's own
        # included, must pass the rule, unless the rule lists it in
        # allow_correct_hits (an example that really contains the flagged form).
        allow = rule.get("allow_correct_hits") or []
        if not (isinstance(allow, list) and all(isinstance(a, str) for a in allow)):
            ctx.add("G2", ERROR, RULES_PATH, n, "%s: allow_correct_hits must be a list of strings" % rid)
            allow = []
        no_match = tests.get("no_match") or []
        flagged = set()  # type: Set[str]
        for rel, ex in correct_pool:
            if not rx.search(ex):
                continue
            flagged.add(ex)
            if ex in allow or ex in no_match:  # no_match hits are reported above
                continue
            ctx.add("G5", ERROR, RULES_PATH, n,
                    "%s flags the correct example %r in %s; fix the pattern, or list the example in "
                    "allow_correct_hits if it really contains the flagged form" % (rid, ex, rel))
        for ex in allow:
            if ex not in flagged:
                ctx.add("G2", ERROR, RULES_PATH, n,
                        "%s: allow_correct_hits %r is not a correct example this rule flags; remove it" % (rid, ex))


# Each G5 check takes the Context and appends findings. Rule tests go here.
G5_CHECKS = [check_known_facts, check_rule_tests]  # type: List[Callable[[Context], None]]


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
        for gate, step in (("G3", load_allowlist), ("G1", load_files), ("G0", gate_g0), ("G2", check_grammar),
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
        "grammar_rules_checked": ctx.grammar_checked,
        "machine_rules_checked": ctx.rules_checked,
        "known_facts": {"total": ctx.facts_total, "checked": ctx.facts_checked,
                        "pending": ctx.facts_pending, "pending_ids": ctx.facts_pending_ids},
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
    out.append("Gauntlet: %d file(s), %d row(s), %d grammar rule(s), %d machine rule(s) checked; known facts: %d checked, %d pending%s"
               % (len(ctx.files), ctx.rows_checked, ctx.grammar_checked, ctx.rules_checked, ctx.facts_checked, ctx.facts_pending,
                  " (%s)" % ", ".join(ctx.facts_pending_ids) if ctx.facts_pending_ids else ""))
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

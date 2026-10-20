#!/usr/bin/env python3
"""Generate the progress pages for lexicon/words/.

Writes lexicon/words/<LETTER>/README.md for every letter folder, refreshes
the progress table in lexicon/words/README.md between the PROGRESS markers,
draws the progress chart in .github/assets/progress-light.svg and
progress-dark.svg, and refreshes the progress block in the top-level README.md
between the REPO-PROGRESS markers. The measured error rates come from the
audit log _meta/audits.tsv, the milestones line from _meta/milestones.tsv.
These files are generated: edit this script, not the pages.

Usage: python3 tools/build_pages.py [--check]
  --check  exit 1 if any page is out of date (for CI), write nothing.
"""

import argparse
import glob
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import validate  # noqa: E402  (front matter, parsed the same way as the gauntlet)

WORDS = os.path.join(ROOT, "lexicon", "words")
START, END = "<!-- PROGRESS:START -->", "<!-- PROGRESS:END -->"
REPO_START, REPO_END = "<!-- REPO-PROGRESS:START -->", "<!-- REPO-PROGRESS:END -->"
ASSETS = os.path.join(ROOT, ".github", "assets")
REGISTRY = os.path.join(ROOT, "_meta", "schema", "registry.json")
FLAGGABLE = ("error", "warning", "suggestion")
OTHER_TABLES = [
    # (table in _meta/schema/registry.json and _meta/audits.tsv, label in the README table)
    ("numbers", "Numbers"),
    ("calendar", "Calendar (days, months, public holidays)"),
    ("barbarismos", "Barbarismos"),
    ("variants", "Cura\u00e7ao \u2192 Aruba spelling pairs"),
    ("loanwords", "Loanwords"),
    ("closed-classes", "Closed word classes (articles, pronouns, particles, modals, conjunctions, prepositions)"),
    ("verb-forms", "Verb forms (gerunds and participles)"),
]
AUDIT_TABLES = [
    # (table in _meta/audits.tsv, label in the chart's Quality section), in
    # chart order. Must list the same values as the table enum in
    # _meta/schema/audits.schema.json.
    ("words", "Words"),
    ("translations", "Word translations"),
    ("numbers", "Numbers"),
    ("calendar", "Calendar"),
    ("barbarismos", "Barbarismos"),
    ("variants", "Cura\u00e7ao \u2192 Aruba pairs"),
    ("loanwords", "Loanwords"),
    ("closed-classes", "Closed word classes"),
    ("verb-forms", "Verb forms"),
    ("grammar", "Grammar rules"),
    ("rules", "Machine checker rules"),
]
MILESTONE_STATUS = {
    # status in _meta/milestones.tsv: how the README shows it. Must list the
    # same values as the status enum in _meta/schema/milestones.schema.json.
    "done": "\u2705 done",
    "in-progress": "\U0001f7e1 in progress",
    "next": "\u27a1\ufe0f next",
    "not-started": "\u2b1c not started",
}
QUALITY_SCALES = (0.25, 0.5, 1.0)  # the Quality bars run from 0% to the first that fits every range
WHOLE_NUMBER_RE = re.compile(r"[0-9]+")
EMPTY_CHECKS = [
    # (name in the "Still empty" line, globs whose rows count)
    ("names", ["lexicon/names/*.tsv"]),
    ("closed word classes", ["lexicon/closed-classes/*.tsv"]),
    ("public holidays", ["lexicon/calendar/holidays.tsv"]),
    ("the corpus", ["corpus/**/*.tsv"]),
    ("the test sets", ["eval/**/*.tsv", "eval/**/*.jsonl"]),
]
THEMES = {
    "light": {"bg": "#ffffff", "border": "#d0d7de", "text": "#1f2328", "muted": "#59636e",
              "track": "#eaeef2", "tile": "#f6f8fa", "added": "#1f6fb2", "reviewed": "#1a7f37",
              "error": "#bc4c00"},
    "dark": {"bg": "#0d1117", "border": "#30363d", "text": "#e6edf3", "muted": "#9198a1",
             "track": "#21262d", "tile": "#161b22", "added": "#4493f8", "reviewed": "#3fb950",
             "error": "#f0883e"},
}


def read_rows(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    header = lines[0].split("\t")
    return [dict(zip(header, l.split("\t"))) for l in lines[1:] if l]


def table_rows(name):
    """Every row of a registry table, from the files its glob in _meta/schema/registry.json matches."""
    with open(REGISTRY, encoding="utf-8") as f:
        globs = dict((t["name"], t["glob"]) for t in json.load(f)["tables"])
    if name not in globs:
        sys.exit("%s has no table %r" % (os.path.relpath(REGISTRY, ROOT), name))
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, globs[name]))):
        rows += read_rows(path)
    return rows


def stats(rows):
    def n(pred):
        return sum(1 for r in rows if pred(r))
    return {
        "words": len(rows),
        "en": n(lambda r: r.get("en")),
        "nl": n(lambda r: r.get("nl")),
        "es": n(lambda r: r.get("es")),
        "reviewed": n(lambda r: r.get("status") == "reviewed"),
        "disputed": n(lambda r: r.get("status") == "disputed"),
        "machine": n(lambda r: "machine" in r.get("translated_by", "").split("; ")),
    }


def pct(part, whole):
    return "0%" if not whole else "%d%%" % round(100.0 * part / whole)


def letter_page(letter, s):
    return "\n".join([
        "# Letter %s" % letter,
        "",
        "<!-- Generated by tools/build_pages.py. Do not edit by hand. -->",
        "",
        "Words from the official AB 2018 no. 68 word list that start with **%s**. "
        "The data is in [`words.tsv`](words.tsv); GitHub shows it as a searchable table." % letter,
        "",
        "| | Count | Share |",
        "|---|---:|---:|",
        "| Words | %d | |" % s["words"],
        "| With English | %d | %s |" % (s["en"], pct(s["en"], s["words"])),
        "| With Dutch | %d | %s |" % (s["nl"], pct(s["nl"], s["words"])),
        "| With Spanish | %d | %s |" % (s["es"], pct(s["es"], s["words"])),
        "| Rows with machine-drafted translations | %d | |" % s["machine"],
        "| Reviewed by the board | %d | %s |" % (s["reviewed"], pct(s["reviewed"], s["words"])),
        "| Disputed | %d | |" % s["disputed"],
        "",
        "## How to help with %s" % letter,
        "",
        "1. Open [`words.tsv`](words.tsv) and pick rows with an empty or doubtful translation.",
        "2. Suggest a translation with the **Add a translation** issue form, or edit the file in the browser "
        "(see [CONTRIBUTING.md](../../../CONTRIBUTING.md)).",
        "3. Leave `status` as `draft`; a review-board member marks rows `reviewed`.",
        "",
    ])


def progress_table(all_stats):
    lines = ["| Letter | Words | English | Dutch | Spanish | Reviewed |",
             "|---|---:|---:|---:|---:|---:|"]
    tot = dict((k, 0) for k in ("words", "en", "nl", "es", "reviewed"))
    for letter, s in all_stats:
        for k in tot:
            tot[k] += s[k]
        lines.append("| [%s](%s/) | %d | %s | %s | %s | %s |" % (
            letter, letter, s["words"], pct(s["en"], s["words"]), pct(s["nl"], s["words"]),
            pct(s["es"], s["words"]), pct(s["reviewed"], s["words"])))
    lines.append("| **All** | **%d** | **%s** | **%s** | **%s** | **%s** |" % (
        tot["words"], pct(tot["en"], tot["words"]), pct(tot["nl"], tot["words"]),
        pct(tot["es"], tot["words"]), pct(tot["reviewed"], tot["words"])))
    return "\n".join(lines)


def fmt(n):
    return "{:,}".format(n)


def front_matter(path):
    with open(path, encoding="utf-8") as f:
        meta, _ = validate.parse_front_matter(f.read())
    return meta or {}


# TODO(frequency-weighted coverage, board card P1-21): also show "of every 100
# words in real Aruban text, how many are reviewed entries", i.e. the corpus
# frequency of the reviewed words divided by the frequency of all word tokens.
# That needs a word-frequency list whose licence lets it be published in this
# repo. The maintainer has not chosen one yet: until then, do not add
# frequency data, and do not derive it from an unpublished corpus.


def repo_stats(words):
    """Counts for the top-level README: words, other tables, grammar and machine rules, audits."""
    other = []
    for key, label in OTHER_TABLES:
        rows = table_rows(key)
        other.append((key, label, len(rows), sum(1 for r in rows if r.get("status") == "reviewed")))
    grammar = [front_matter(p) for p in sorted(glob.glob(os.path.join(ROOT, "grammar", "*", "rule-*.md")))]
    rules_path = os.path.join(ROOT, "rules", "rules.jsonl")
    machine = 0
    if os.path.exists(rules_path):
        with open(rules_path, encoding="utf-8") as f:
            machine = sum(1 for line in f if line.strip())
    return {
        "words": words,
        "other": other,
        "grammar": len(grammar),
        "grammar_reviewed": sum(1 for m in grammar if m.get("status") == "reviewed"),
        "flaggable": sum(1 for m in grammar if m.get("severity") in FLAGGABLE),
        "machine": machine,
        "empty": [name for name, patterns in EMPTY_CHECKS if count_rows(patterns) == 0],
        "audits": latest_audits(table_rows("audits")),
        "milestones": table_rows("milestones"),
        "sentences": sentence_stats(),
    }


def sentence_stats():
    """Parallel sentences: English/Spanish prompts (corpus and held out) and
    the Aruban Papiamento translations teachers write for them."""
    prompts = table_rows("parallel-prompts") + table_rows("eval-parallel-prompts")
    pairs = table_rows("parallel-pairs") + table_rows("eval-parallel-pairs")
    return {
        "prompts": len(prompts),
        "prompts_reviewed": sum(1 for p in prompts if p.get("status") == "reviewed"),
        "held_out": len(table_rows("eval-parallel-prompts")),
        "translated": len(set(p.get("prompt_id") for p in pairs if p.get("prompt_id"))),
        "pairs": len(pairs),
        "pairs_reviewed": sum(1 for p in pairs if p.get("status") == "reviewed"),
    }


def latest_audits(rows):
    """The latest audit of each table, by date and then id. Rows the gauntlet
    rejects (sample_size or errors not a whole number, errors > sample_size)
    are skipped."""
    latest = {}
    for r in rows:
        n, e = r.get("sample_size", ""), r.get("errors", "")
        if not (WHOLE_NUMBER_RE.fullmatch(n) and WHOLE_NUMBER_RE.fullmatch(e)):
            continue
        if int(n) == 0 or int(e) > int(n):
            continue
        key, when = r.get("table", ""), (r.get("date", ""), r.get("id", ""))
        if key not in latest or when > (latest[key].get("date", ""), latest[key].get("id", "")):
            latest[key] = r
    return latest


def wilson(errors, n, z=1.96):
    """95% Wilson score interval for `errors` wrong out of `n`, as (low, high) shares."""
    p = float(errors) / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def pct1(part):
    """A share as a percentage with one decimal and no trailing .0: 0.0333 -> '3.3'."""
    s = "%.1f" % (100.0 * part)
    return s[:-2] if s.endswith(".0") else s


def audit_numbers(audit):
    n, e = int(audit["sample_size"]), int(audit["errors"])
    low, high = wilson(e, n)
    return n, e, float(e) / n, low, high


def machine_only(audit):
    return [a for a in audit.get("auditor", "").split("; ") if a] == ["machine"]


def error_rate(audit):
    """The README cell for one audit: the rate and the sample on one line, the
    interval and the date in small print under it (short lines for phones)."""
    n, e, p, low, high = audit_numbers(audit)
    return "%s%% (%s of %s)<br><sub>95%% CI %s\u2013%s%%, checked%s on %s</sub>" % (
        pct1(p), fmt(e), fmt(n), pct1(low), pct1(high),
        " by machine" if machine_only(audit) else "", audit.get("date", ""))


def milestones_line(rows):
    """'Milestones: **P0 Foundation** \u2705 done \u00b7 ...', or None when there are none."""
    if not rows:
        return None
    return "Milestones: %s. [What is left](_meta/milestones.tsv)" % " \u00b7 ".join(
        "**%s %s** %s" % (r.get("id", ""), r.get("title", ""), MILESTONE_STATUS.get(r.get("status", ""), ""))
        for r in rows)


def count_rows(patterns):
    n = 0
    for pattern in patterns:
        for path in glob.glob(os.path.join(ROOT, pattern), recursive=True):
            with open(path, encoding="utf-8") as f:
                lines = [l for l in f.read().split("\n") if l.strip()]
            n += max(0, len(lines) - 1) if path.endswith(".tsv") else len(lines)
    return n


def join_names(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def share(part, whole):
    return 0.0 if not whole else float(part) / whole


def chart_rows(rs):
    w = rs["words"]
    other_rows = sum(n for _, _, n, _ in rs["other"])
    other_reviewed = sum(r for _, _, _, r in rs["other"])
    return [
        ("Words", None, None, None),
        ("With English", w["en"], w["words"], "added"),
        ("With Dutch", w["nl"], w["words"], "added"),
        ("With Spanish", w["es"], w["words"], "added"),
        ("Reviewed by the board", w["reviewed"], w["words"], "reviewed"),
        ("Rules", None, None, None),
        ("Grammar rules reviewed", rs["grammar_reviewed"], rs["grammar"], "reviewed"),
        ("Flaggable rules with a machine check", rs["machine"], rs["flaggable"], "added"),
        ("Other tables", None, None, None),
        ("Rows reviewed", other_reviewed, other_rows, "reviewed"),
    ] + sentence_chart_rows(rs.get("sentences"))


def sentence_chart_rows(s):
    if not s or not s["prompts"]:
        return []
    return [
        ("Sentences", None, None, None),
        ("Prompts with a Papiamento translation", s["translated"], s["prompts"], "added"),
        ("Translations reviewed", s["pairs_reviewed"], s["pairs"], "reviewed"),
    ]


def progress_svg(rs, theme):
    t = THEMES[theme]
    w = rs["words"]
    width, left, right = 840, 28, 812
    bar_x, bar_w = 350, 270
    out = []
    # Tiles: the four headline numbers.
    tiles = [
        (fmt(w["words"]), "AB 2018 words", "added"),
        ("%d%%" % round(100 * share(w["en"], w["words"])), "with English", "added"),
        ("%d%%" % round(100 * share(w["reviewed"], w["words"])), "reviewed", "reviewed"),
        ("%s/%s" % (fmt(rs["machine"]), fmt(rs["flaggable"])), "rules machine-checked", "added"),
    ]
    gap = 12
    tile_w = (right - left - gap * (len(tiles) - 1)) // len(tiles)
    for i, (big, small, kind) in enumerate(tiles):
        x = left + i * (tile_w + gap)
        out.append('<rect x="%d" y="56" width="%d" height="86" rx="10" fill="%s"/>' % (x, tile_w, t["tile"]))
        out.append('<text x="%d" y="98" font-size="30" font-weight="700" fill="%s">%s</text>' % (x + 16, t[kind], big))
        out.append('<text x="%d" y="124" font-size="12" fill="%s">%s</text>' % (x + 16, t["muted"], small))
    y = 172
    for label, part, whole, kind in chart_rows(rs):
        if part is None:
            y += 8
            out.append('<text x="%d" y="%d" font-size="12" font-weight="600" fill="%s" letter-spacing="0.8">%s</text>'
                       % (left, y, t["muted"], label.upper()))
            y += 26
            continue
        frac = share(part, whole)
        fill_w = 0 if part == 0 else max(10, int(round(bar_w * frac)))
        out.append('<text x="%d" y="%d" font-size="15" fill="%s">%s</text>' % (left, y, t["text"], label))
        out.append('<rect x="%d" y="%d" width="%d" height="10" rx="5" fill="%s"/>' % (bar_x, y - 10, bar_w, t["track"]))
        if fill_w:
            out.append('<rect x="%d" y="%d" width="%d" height="10" rx="5" fill="%s"/>' % (bar_x, y - 10, fill_w, t[kind]))
        out.append('<text x="%d" y="%d" font-size="14" fill="%s" text-anchor="end">%s of %s'
                   '<tspan font-weight="600" fill="%s" dx="8">%d%%</tspan></text>'
                   % (right, y, t["muted"], fmt(part), fmt(whole), t["text"], int(round(100 * frac))))
        y += 30
    audited = [(label, rs["audits"][key]) for key, label in AUDIT_TABLES if key in rs.get("audits", {})]
    if audited:
        # Quality: the error rate of the latest audit of each table (the dot)
        # and its 95% interval (the band), on a scale from 0 to `scale`.
        top = max(audit_numbers(a)[4] for _, a in audited)
        scale = next(s for s in QUALITY_SCALES if top <= s)
        y += 8
        out.append('<text x="%d" y="%d" font-size="12" font-weight="600" fill="%s" letter-spacing="0.8">QUALITY</text>'
                   % (left, y, t["muted"]))
        out.append('<text x="%d" y="%d" font-size="12" fill="%s">0%%</text>' % (bar_x, y, t["muted"]))
        out.append('<text x="%d" y="%d" font-size="12" fill="%s" text-anchor="middle">error rate, 95%% range</text>'
                   % (bar_x + bar_w // 2, y, t["muted"]))
        out.append('<text x="%d" y="%d" font-size="12" fill="%s" text-anchor="end">%d%%</text>'
                   % (bar_x + bar_w, y, t["muted"], round(100 * scale)))
        y += 26

        def pos(part):
            return bar_x + 5 + int(round((bar_w - 10) * part / scale))

        for label, audit in audited:
            n, e, p, low, high = audit_numbers(audit)
            out.append('<text x="%d" y="%d" font-size="15" fill="%s">%s</text>' % (left, y, t["text"], label))
            out.append('<rect x="%d" y="%d" width="%d" height="10" rx="5" fill="%s"/>' % (bar_x, y - 10, bar_w, t["track"]))
            out.append('<rect x="%d" y="%d" width="%d" height="10" rx="5" fill="%s" fill-opacity="0.35"/>'
                       % (pos(low) - 5, y - 10, pos(high) - pos(low) + 10, t["error"]))
            out.append('<circle cx="%d" cy="%d" r="5" fill="%s"/>' % (pos(p), y - 5, t["error"]))
            out.append('<text x="%d" y="%d" font-size="14" fill="%s" text-anchor="end">%s of %s wrong'
                       '<tspan font-weight="600" fill="%s" dx="8">%s%%</tspan></text>'
                       % (right, y, t["muted"], fmt(e), fmt(n), t["text"], pct1(p)))
            y += 30
    height = y + 2
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
        'aria-label="Progress of the Papiamento open data">' % (width, height, width, height),
        "<!-- Generated by tools/build_pages.py. Do not edit by hand. -->",
        '<rect x="0.5" y="0.5" width="%d" height="%d" rx="14" fill="%s" stroke="%s"/>'
        % (width - 1, height - 1, t["bg"], t["border"]),
        "<g font-family=\"-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif\">",
        '<text x="%d" y="36" font-size="18" font-weight="700" fill="%s">Progress</text>' % (left, t["text"]),
        '<text x="%d" y="36" font-size="13" fill="%s" text-anchor="end">'
        '<tspan fill="%s">\u25cf</tspan> added    <tspan fill="%s">\u25cf</tspan> reviewed by the board</text>'
        % (right, t["muted"], t["added"], t["reviewed"]),
    ] + out + ["</g>", "</svg>", ""])


def readme_block(rs):
    w = rs["words"]
    alt = ("Progress: %s words; %d%% with English, %d%% with Dutch, %d%% with Spanish; %d%% reviewed by the board; "
           "%s of %s flaggable grammar rules have a machine check." % (
               fmt(w["words"]), round(100 * share(w["en"], w["words"])), round(100 * share(w["nl"], w["words"])),
               round(100 * share(w["es"], w["words"])), round(100 * share(w["reviewed"], w["words"])),
               fmt(rs["machine"]), fmt(rs["flaggable"])))
    audits = rs.get("audits", {})
    audited = []
    for key, label in AUDIT_TABLES:
        if key in audits:
            n, e, p, _, _ = audit_numbers(audits[key])
            audited.append("%s %s%% (%s of %s)" % (label, pct1(p), fmt(e), fmt(n)))
    if audited:
        alt += " Measured error rate in the latest random audit: %s." % "; ".join(audited)

    def rate(key):
        return error_rate(audits[key]) if key in audits else "not audited yet"

    words_rate = rate("words")
    if "translations" in audits:
        words_rate += "<br>Translations: " + rate("translations")
    lines = [
        REPO_START,
        "<!-- Generated by tools/build_pages.py from the data. Do not edit by hand. -->",
    ]
    milestones = milestones_line(rs.get("milestones"))
    if milestones:
        lines += [milestones, ""]
    lines += [
        "<picture>",
        '  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/progress-dark.svg">',
        '  <img alt="%s" src=".github/assets/progress-light.svg" width="100%%">' % alt,
        "</picture>",
        "",
        "| Table | Rows | Reviewed by the board | Measured error rate |",
        "|---|---:|---:|---|",
        "| [Words](lexicon/words/) (AB 2018 word list) | %s | %s | %s |" % (
            fmt(w["words"]), fmt(w["reviewed"]), words_rate),
    ]
    for key, label, n, reviewed in rs["other"]:
        lines.append("| %s | %s | %s | %s |" % (label, fmt(n), fmt(reviewed), rate(key)))
    s = rs.get("sentences")
    if s and s["prompts"]:
        lines.append("| [Sentence prompts](corpus/parallel/) (English and Spanish; %s held out for tests) | %s | %s | not audited yet |" % (
            fmt(s["held_out"]), fmt(s["prompts"]), fmt(s.get("prompts_reviewed", 0))))
        lines.append("| Aruban Papiamento sentence translations | %s | %s | not audited yet |" % (
            fmt(s["pairs"]), fmt(s["pairs_reviewed"])))
    lines += [
        "| [Grammar rules](grammar/) | %s | %s | %s |" % (fmt(rs["grammar"]), fmt(rs["grammar_reviewed"]), rate("grammar")),
        "| [Machine checker rules](rules/) | %s | | %s |" % (fmt(rs["machine"]), rate("rules")),
        "",
        "Measured error rate: the share of wrong rows in the latest random audit of the table against the source "
        "PDFs, with its 95% Wilson interval (CI). The audits are logged in [`_meta/audits.tsv`](_meta/audits.tsv)."
        + (" \"Checked by machine\" means software or an AI model did the checking, not yet a person."
           if any(machine_only(audits[k]) for k, _ in AUDIT_TABLES if k in audits) else ""),
    ]
    if rs.get("empty"):
        lines += ["", "Still empty: %s." % join_names(rs["empty"])]
    lines.append(REPO_END)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    outputs = {}
    all_stats = []
    for letter in sorted(os.listdir(WORDS)):
        tsv = os.path.join(WORDS, letter, "words.tsv")
        if not os.path.isfile(tsv):
            continue
        s = stats(read_rows(tsv))
        all_stats.append((letter, s))
        outputs[os.path.join(WORDS, letter, "README.md")] = letter_page(letter, s)
    index = os.path.join(WORDS, "README.md")
    with open(index, encoding="utf-8") as f:
        text = f.read()
    block = "%s\n%s\n%s" % (START, progress_table(all_stats), END)
    if START in text and END in text:
        text = text[:text.index(START)] + block + text[text.index(END) + len(END):]
    else:
        text = text.rstrip("\n") + "\n\n## Progress\n\n" + block + "\n"
    outputs[index] = text
    totals = dict((k, sum(st[k] for _, st in all_stats)) for k in ("words", "en", "nl", "es", "reviewed"))
    rs = repo_stats(totals)
    for theme in THEMES:
        outputs[os.path.join(ASSETS, "progress-%s.svg" % theme)] = progress_svg(rs, theme)
    readme = os.path.join(ROOT, "README.md")
    with open(readme, encoding="utf-8") as f:
        text = f.read()
    if REPO_START not in text or REPO_END not in text:
        sys.exit("README.md has no %s ... %s block" % (REPO_START, REPO_END))
    outputs[readme] = (text[:text.index(REPO_START)] + readme_block(rs)
                       + text[text.index(REPO_END) + len(REPO_END):])
    stale = []
    for path, content in sorted(outputs.items()):
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != content:
            stale.append(os.path.relpath(path, ROOT))
            if not a.check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
    if a.check and stale:
        print("Out of date (run python3 tools/build_pages.py):\n  " + "\n  ".join(stale))
        sys.exit(1)
    print("%d page(s) %s" % (len(stale), "out of date" if a.check else "written"))


if __name__ == "__main__":
    main()

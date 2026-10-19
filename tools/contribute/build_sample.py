#!/usr/bin/env python3
"""Build the data files of the contribution-tool prototype.

Reads the repo's own data and writes, next to this script:

- data/sample.js   the sample words (review and translate) and the prompts
- data/checks.js   the checks the sentence screen runs while a teacher types:
                   rules/rules.jsonl (with severity from grammar/), the
                   barbarismos, the Curacao-Aruba variants and the AB 2018 word
                   list
- data/strings.js  the interface text from ui-strings.tsv
- crops/<id>.png   a crop of the printed AB 2018 word-list page around each
                   sample word, with the entry highlighted, and <id>-column.png,
                   the entry's own column for narrow (phone) screens

It also checks the Papiamento interface text: every word must be in the AB 2018
word list (or in TOKEN_ALLOWLIST), and no rule, barbarismo or Curacao variant
may fire on it. Exit code 1 when that check fails.

Needs PyMuPDF and Pillow (the validator itself needs neither):
    python3 tools/contribute/build_sample.py
"""

import collections
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Word-list page N of AB 2018 is PDF page N + 47 (sources/cards/AB2018.md).
AB_WORDLIST_OFFSET = 47

# Machine-drafted rows to check (translated_by = machine). Picked by hand for
# variety: four carry the "uncertain" note, several have more than one sense.
REVIEW_IDS = [
    "pap-001573",  # bel
    "pap-011371",  # pica
    "pap-001947",  # bonbini
    "pap-002642",  # caya
    "pap-013160",  # robes
    "pap-009777",  # mesora
    "pap-001335",  # baki
    "pap-002563",  # cashi
]

# Rows with no translation, picked from the top of the frequency order below, skipping Dutch and English function words that the books quote (van,
# het, in, o) and the language name.
TRANSLATE_IDS = [
    "pap-009327",  # madushi
    "pap-013394",  # Santo
    "pap-002137",  # buchi
    "pap-010579",  # occidente
    "pap-005016",  # djaca
    "pap-005292",  # editor
    "pap-016009",  # weita
    "pap-000396",  # agricultura
]

# Frequency order, as the maintainer decided on 2026-10-18 (DESIGN.md 5(e)):
# token counts in the shareable PDFs in this repo, the same ones
# tools/word_frequency.py counts. AB2018 and VOC2009 are left out: their word
# lists print every headword once, and the AB annex is the text of ORT2009.
FREQ_PDFS = [("MOR2010", None), ("ORT2009", None), ("PRE2016", None), ("SIN2015", None)]
FREQ_LABEL = ("how often the word occurs in the repo's shareable PDFs (MOR2010, ORT2009, "
              "PRE2016, SIN2015); contributed sentences will be blended in")

# Words in the Papiamento interface text that are not AB 2018 headwords but are
# allowed: technical terms, names, licence codes and the past marker a.
TOKEN_ALLOWLIST = {
    "a": "past tense marker; not a headword in the AB list",
    "browser": "technical term",
    "server": "technical term",
    "email": "technical term",
    "json": "file format",
    "pdf": "file format",
    "cc": "licence name",
    "by": "licence name (CC BY)",
    "cc0": "licence name",
    "common": "name (Common Voice)",
    "voice": "name (Common Voice)",
    "ab": "law (AB 2018)",
    "to": "English word quoted in a hint",
    "go": "English word quoted in a hint",
    "github": "name (GitHub)",
    "pull": "technical term (pull request)",
    "request": "technical term (pull request)",
    "spam": "technical term (spam folder)",
}

LETTER = "A-Za-zÀ-ÿñÑ"

PRONOUN_E = re.compile(r"(?<![A-Za-zÀ-ÿñÑ'])([A-Za-zñ]*[aeiou]) e(?=\s*(?:$|[.,;:!?)]|\s(?:den|na|riba|bon|awor|tambe|y|of)(?![A-Za-zñ])))")
NOT_VERBS = {"di", "pa", "na", "cu", "ta", "manera", "aki", "riba", "loke", "tocante", "a", "e", "si", "y", "o", "no", "lo", "ya"}
TOKEN = re.compile(r"[%s]+(?:'[%s]+)?" % (LETTER, LETTER))


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))


def load_words():
    rows = []
    for path in sorted((ROOT / "lexicon" / "words").glob("*/words.tsv")):
        rows += read_tsv(path)
    return rows


def ab_forms(words):
    forms = set()
    for r in words:
        forms.add(r["lemma"].lower())
        for alt in r["alt"].split("; "):
            if alt:
                forms.add(alt.lower())
    return forms


def front_matter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    block = text[4:text.index("\n---", 4)]
    out = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip('"')
    return out


def load_rules():
    meta = {}
    for path in (ROOT / "grammar").rglob("*.md"):
        fm = front_matter(path)
        if fm.get("id"):
            meta[fm["id"]] = {"severity": fm.get("severity", ""),
                              "title": fm.get("title", ""),
                              "file": str(path.relative_to(ROOT))}
    rules = []
    with open(ROOT / "rules" / "rules.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            m = meta.get(r["rule_id"], {})
            rules.append({
                "rule_id": r["rule_id"],
                "pattern": r["pattern"],
                "flags": r["flags"],
                "replacement": r["replacement"],
                "message": r["message"],
                "severity": m.get("severity") or "warning",
                "title": m.get("title", ""),
                "file": m.get("file", ""),
            })
    return rules


def word_frequencies():
    tok = re.compile(r"[a-zñ]+(?:'[a-zñ]+)?")
    counts = collections.Counter()
    for sid, pages in FREQ_PDFS:
        doc = fitz.open(ROOT / "sources" / "pdf" / ("%s.pdf" % sid))
        for i in (pages if pages is not None else range(doc.page_count)):
            counts.update(tok.findall(doc[i].get_text().lower()))
    return counts


def find_entry(page, lemma):
    """Return the rectangle of the word-list line that prints `lemma`."""
    words = page.get_text("words")
    lines = collections.defaultdict(list)
    for w in words:
        lines[(w[5], w[6])].append(w)
    target = lemma.split()
    best = None
    for key, ws in lines.items():
        ws.sort(key=lambda w: w[7])
        texts = [w[4] for w in ws]
        if texts[:len(target)] != target:
            continue
        # The rest of the line may only be the AB list's [alt] or (tag).
        rest = " ".join(texts[len(target):])
        clean = rest == "" or rest.startswith("[") or rest.startswith("(") or rest.startswith("/")
        rect = fitz.Rect(ws[0][:4])
        for w in ws[1:]:
            rect |= fitz.Rect(w[:4])
        score = (1 if clean else 0, -len(rest))
        if best is None or score > best[0]:
            best = (score, rect)
    return best[1] if best else None


def render_crop(doc, row, out_path, column=False):
    """Crop the word-list page around the entry: the full width (four columns)
    or, for phones, only the entry's own column."""
    pdf_index = int(row["page"]) + AB_WORDLIST_OFFSET - 1
    page = doc[pdf_index]
    rect = find_entry(page, row["lemma"])
    if rect is None:
        raise SystemExit("could not find %s %r on PDF page %d" % (row["id"], row["lemma"], pdf_index + 1))
    line_h = 12.1
    if column:
        clip = fitz.Rect(rect.x0 - 6, max(78, rect.y0 - 3 * line_h - 0.8),
                         min(546, rect.x0 + 116), min(778, rect.y1 + 3 * line_h + 0.8))
    else:
        clip = fitz.Rect(50, max(78, rect.y0 - 3 * line_h - 0.8), 546, min(778, rect.y1 + 3 * line_h + 0.8))
    dpi = 200
    pix = page.get_pixmap(clip=clip, dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    scale = dpi / 72.0
    box = [(rect.x0 - 3 - clip.x0) * scale, (rect.y0 - 1 - clip.y0) * scale,
           (rect.x1 + 3 - clip.x0) * scale, (rect.y1 + 1 - clip.y0) * scale]
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(box, fill=(255, 214, 0, 90), outline=(200, 120, 0, 255), width=4)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img = img.quantize(colors=32, method=Image.Quantize.MEDIANCUT)
    img.save(out_path, optimize=True)
    return {"pdf_page": pdf_index + 1, "width": img.width, "height": img.height}


def check_pap_strings(strings, forms, rules, barbarismos, variants):
    problems = []
    bar_wrong = {b["wrong"].lower() for b in barbarismos}
    var_cw = {v["curacao"].lower() for v in variants}
    compiled = [(r["rule_id"], re.compile(r["pattern"], re.I if "i" in r["flags"] else 0)) for r in rules]
    multi = sorted((f for f in forms if " " in f), key=len, reverse=True)
    for s in strings:
        text = re.sub(r"\{[a-z_]+\}", " ", s["pap"])
        # Multi-word headwords (for di, por lo menos) count as known words.
        for phrase in multi:
            text = re.sub(r"(?<![%s])%s(?![%s])" % (LETTER, re.escape(phrase), LETTER), " ", text, flags=re.I)
        for tok in TOKEN.findall(text):
            low = tok.lower()
            if low in TOKEN_ALLOWLIST:
                continue
            if low in var_cw:
                problems.append("%s: Curacao form %r" % (s["key"], tok))
            if low in bar_wrong:
                problems.append("%s: barbarismo %r" % (s["key"], tok))
            if low in forms:
                continue
            if low.endswith("nan") and low[:-3] in forms:
                continue
            # Verb + pronoun e with the vowel dropped (uz'e from uza).
            if low.endswith("'e") and any(low[:-2] + v in forms for v in "aeiou"):
                continue
            problems.append("%s: %r is not in the AB 2018 word list" % (s["key"], tok))
        # A vowel-final verb + the pronoun e is written with an apostrophe
        # (uz'e, aprob'e; AB 2018 annex §10.1 point 1, p. 33), or the pronoun
        # is left out (controla). Heuristic: e at the end of a clause, or
        # before a word that cannot follow the article e.
        for m in PRONOUN_E.finditer(s["pap"]):
            if m.group(1).lower() not in NOT_VERBS:
                problems.append("%s: %r looks like verb + pronoun e; write %s'e or drop the e" % (
                    s["key"], m.group(0).strip(), m.group(1)[:-1]))
        for rule_id, rx in compiled:
            # Sentence-start capital rules do not apply to short labels.
            if rule_id in ("RULE_ORT_014",):
                continue
            m = rx.search(s["pap"])
            if m:
                problems.append("%s: %s fires on %r" % (s["key"], rule_id, m.group(0)))
    return problems


def js(name, obj):
    return "// Generated by tools/contribute/build_sample.py. Do not edit by hand.\nwindow.%s = %s;\n" % (
        name, json.dumps(obj, ensure_ascii=False, indent=1))


def main():
    words = load_words()
    by_id = {r["id"]: r for r in words}
    forms = ab_forms(words)
    rules = load_rules()
    barbarismos = read_tsv(ROOT / "lexicon" / "barbarismos" / "barbarismos.tsv")
    variants = read_tsv(ROOT / "lexicon" / "variants" / "curacao-aruba.tsv")
    loans = [line.strip() for line in (ROOT / "_meta" / "allowlists" / "accented-loans.txt").read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.startswith("#")]
    prompts = read_tsv(HERE / "prompts.tsv")
    strings = read_tsv(HERE / "ui-strings.tsv")
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()

    problems = check_pap_strings(strings, forms, rules, barbarismos, variants)
    for p in problems:
        print("pap text:", p)

    doc = fitz.open(ROOT / "sources" / "pdf" / "AB2018.pdf")
    (HERE / "crops").mkdir(exist_ok=True)
    counts = word_frequencies()

    def word_item(row, mode):
        if mode == "review" and row["translated_by"] != "machine":
            raise SystemExit("%s is not a machine draft" % row["id"])
        if mode == "translate" and (row["en"] or row["nl"] or row["es"]):
            raise SystemExit("%s already has a translation" % row["id"])
        crop = render_crop(doc, row, HERE / "crops" / ("%s.png" % row["id"]))
        col = render_crop(doc, row, HERE / "crops" / ("%s-column.png" % row["id"]), column=True)
        item = {k: row[k] for k in ("id", "lemma", "alt", "pos", "tag", "en", "nl", "es",
                                    "translated_by", "status", "source", "page", "notes")}
        item.update({"crop": "crops/%s.png" % row["id"], "pdf_page": crop["pdf_page"],
                     "crop_w": crop["width"], "crop_h": crop["height"],
                     "crop_column": "crops/%s-column.png" % row["id"],
                     "crop_column_w": col["width"], "crop_column_h": col["height"]})
        if mode == "translate":
            item["freq"] = counts[row["lemma"].lower()]
        return item

    review = [word_item(by_id[i], "review") for i in REVIEW_IDS]
    translate = sorted((word_item(by_id[i], "translate") for i in TRANSLATE_IDS),
                       key=lambda x: (-x["freq"], x["lemma"].lower()))

    sample = {
        "built_from_commit": commit,
        "review": review,
        "translate": translate,
        "translate_order": FREQ_LABEL,
        "prompts": prompts,
        "pdf_href": "../../sources/pdf/AB2018.pdf",
    }
    in_ab = lambda w: w.lower() in forms
    checks = {
        "built_from_commit": commit,
        "rules": rules,
        "barbarismos": [{"id": b["id"], "wrong": b["wrong"], "right": b["right"].split("; "),
                         "reason": b["reason"], "rule_id": b["rule_id"], "notes": b["notes"],
                         "is_ab_headword": in_ab(b["wrong"])} for b in barbarismos],
        "variants": [{"id": v["id"], "curacao": v["curacao"], "aruba": v["aruba"],
                      "pattern": v["pattern"]} for v in variants],
        "accented_loans": loans,
        "ab_words": "\n".join(sorted(forms)),
    }
    ui = {"en": {}, "pap": {}, "pap_status": {}}
    for s in strings:
        ui["en"][s["key"]] = s["en"]
        ui["pap"][s["key"]] = s["pap"]
        ui["pap_status"][s["key"]] = s["pap_status"]

    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "sample.js").write_text(js("CONTRIB_SAMPLE", sample), encoding="utf-8")
    (HERE / "data" / "checks.js").write_text(js("CONTRIB_CHECKS", checks), encoding="utf-8")
    (HERE / "data" / "strings.js").write_text(js("CONTRIB_STRINGS", ui), encoding="utf-8")
    print("built %d review words, %d translate words, %d prompts, %d rules, %d barbarismos, "
          "%d variants, %d AB forms, %d interface strings (from %s)" % (
              len(review), len(translate), len(prompts), len(rules), len(barbarismos),
              len(variants), len(forms), len(strings), commit))
    for w in translate:
        print("  translate %s %-12s count %d" % (w["id"], w["lemma"], w["freq"]))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

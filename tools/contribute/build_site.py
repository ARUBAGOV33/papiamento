#!/usr/bin/env python3
"""Build the contribution tool's website into one folder, for GitHub Pages.

The workflow "Contribution site" runs it on every push to main that changes
the tool or its data, and publishes the folder at
https://arubagov33.github.io/papiamento/:

    SUPABASE_URL=... SUPABASE_PUBLISHABLE_KEY=... \\
        python3 tools/contribute/build_site.py --out _site --live --vendor

Without --live it builds the demo (answers stay in the browser, as in the
prototype), which needs no database:

    python3 tools/contribute/build_site.py --out /tmp/site

What it writes:

- index.html, style.css, app.js, checker.js, assets/: copied from this folder;
  in live mode index.html gets a Content-Security-Policy that allows scripts
  from the site itself only and connections to the Supabase project only;
- config.js: live mode, the Supabase URL and the publishable key. Both are
  public by design: the database's access rules decide what they can reach
  (supabase/README.md). The script refuses a secret key;
- data/sample.js: every machine-drafted word to check, the words with no
  translation that occur in the repo's texts (ordered by tools/word_frequency.py,
  as the maintainer decided on 2026-10-18), and every prompt in
  corpus/parallel/ and eval/parallel/;
- data/checks.js, data/strings.js: the live checks and the interface text, as
  build_sample.py builds them (the Papiamento text check runs here too);
- crops/<id>.png: the entry's own column of the printed AB 2018 word-list page;
- pdf/AB2018.pdf: for "Open the whole page";
- vendor/supabase-js-<version>.js (--vendor): the pinned supabase-js browser
  build, downloaded from the npm registry and checked against its published
  checksum before it is used.

Needs PyMuPDF and Pillow (pip install pymupdf pillow), like build_sample.py.
"""

import argparse
import base64
import hashlib
import io
import json
import re
import shutil
import sys
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# The browser build of supabase-js, pinned to one version and its checksum
# (dist.integrity on https://registry.npmjs.org/@supabase/supabase-js/2.117.2).
SUPABASE_JS = {
    "version": "2.117.2",
    "tarball": "https://registry.npmjs.org/@supabase/supabase-js/-/supabase-js-2.117.2.tgz",
    "integrity": "sha512-eSG2VKnHR+Clp1PmidZ1/weJ8PJwoybjva3L2GgKqFG4YDS1Iqmc61psKGZP5xw6OMT2O7ZorPR42PY6q1BOXg==",
    "file": "package/dist/umd/supabase.js",
    "licence": "package/LICENSE",
}
VENDOR_PATH = "vendor/supabase-js-%s.js" % SUPABASE_JS["version"]

STATIC = ["index.html", "style.css", "app.js", "checker.js", "assets"]
REPO_URL = "https://github.com/ARUBAGOV33/papiamento"
FREQ_LABEL = ("how often the word occurs in the repo's shareable PDFs and contributed sentences "
              "(tools/word_frequency.py)")


# --------------------------------------------------------------------------- config

def check_url(url):
    """The Supabase project URL: https, a host, nothing else."""
    parts = urllib.parse.urlsplit(url or "")
    if parts.scheme != "https" or not parts.hostname or parts.path not in ("", "/") or parts.query or parts.fragment \
            or parts.username or parts.password:
        raise ValueError("SUPABASE_URL must look like https://<project>.supabase.co")
    return "https://" + parts.netloc


def check_publishable_key(key):
    """Refuse anything but a publishable (or legacy anon) key. Never echo the key."""
    key = (key or "").strip()
    if key.startswith("sb_publishable_") and re.match(r"^sb_publishable_[A-Za-z0-9_-]+$", key):
        return key
    if key.startswith("sb_secret_"):
        raise ValueError("SUPABASE_PUBLISHABLE_KEY holds a secret key. It must never be published: "
                         "put the publishable key (sb_publishable_...) in the repository variable instead")
    if key.count(".") == 2:  # a legacy JWT key: only the anon role is public
        try:
            payload = key.split(".")[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        except (ValueError, UnicodeDecodeError):
            claims = {}
        if claims.get("role") == "anon":
            return key
        raise ValueError("SUPABASE_PUBLISHABLE_KEY is not the anon key; it must never be published")
    raise ValueError("SUPABASE_PUBLISHABLE_KEY is not a publishable key (sb_publishable_...)")


def site_config(live, url, key):
    if not live:
        return {"mode": "demo", "repo": REPO_URL}
    origin = check_url(url)
    return {"mode": "live", "supabaseUrl": origin, "supabaseKey": check_publishable_key(key),
            "supabaseJs": VENDOR_PATH, "repo": REPO_URL}


def csp(config):
    """Content-Security-Policy for the live site: own scripts only, and only the
    Supabase project as a server."""
    connect = ["'self'"]
    if config.get("supabaseUrl"):
        host = urllib.parse.urlsplit(config["supabaseUrl"]).netloc
        connect += ["https://" + host, "wss://" + host]
    return "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "connect-src " + " ".join(connect),
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'none'",
    ])


def config_js(config):
    return ("// Generated by tools/contribute/build_site.py. The URL and key are public by design;\n"
            "// the database's access rules decide what they can reach (supabase/README.md).\n"
            "window.CONTRIB_CONFIG = %s;\n" % json.dumps(config, indent=1))


# --------------------------------------------------------------------------- catalog

def _import(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def catalog(out, bs, wf):
    """Words to check, words to translate, and the prompts, with a crop for each word."""
    import fitz  # PyMuPDF

    words = wf.load_words(str(ROOT))
    pdfs = wf.shareable_pdfs(str(ROOT))
    scores = dict((r["id"], r["score"]) for r in wf.score_rows(words, wf.pdf_tokens(pdfs), wf.sentence_tokens(str(ROOT))))
    review = [w for w in words if w["translated_by"] == "machine" and w["status"] == "draft"]
    review.sort(key=lambda w: (0 if "uncertain" in w["notes"] else 1, -scores.get(w["id"], 0), w["id"]))
    translate = [w for w in words if not (w["en"] or w["nl"] or w["es"]) and w["status"] == "draft"
                 and scores.get(w["id"], 0) > 0]
    translate.sort(key=lambda w: (-scores[w["id"]], w["lemma"].casefold(), w["id"]))

    doc = fitz.open(ROOT / "sources" / "pdf" / "AB2018.pdf")
    (out / "crops").mkdir(parents=True, exist_ok=True)
    missing = []

    def item(row, with_freq):
        it = {k: row[k] for k in ("id", "lemma", "alt", "pos", "tag", "en", "nl", "es", "page", "notes")}
        it["pdf_page"] = int(row["page"]) + bs.AB_WORDLIST_OFFSET
        try:
            crop = bs.render_crop(doc, row, out / "crops" / ("%s.png" % row["id"]), column=True)
        except SystemExit:  # the entry's line was not found on the page: the app links to the PDF instead
            missing.append(row["id"])
            crop = None
        if crop:
            path = "crops/%s.png" % row["id"]
            it.update({"crop": path, "crop_w": crop["width"], "crop_h": crop["height"],
                       "crop_column": path, "crop_column_w": crop["width"], "crop_column_h": crop["height"]})
        if with_freq:
            it["freq"] = scores[row["id"]]
        return it

    prompts = []
    for split in ("corpus", "eval"):
        for r in bs.read_tsv(ROOT / split / "parallel" / "prompts.tsv"):
            if r["status"] != "deprecated":
                prompts.append({"id": r["id"], "lang": r["lang"], "text": r["text"], "topic": r["topic"], "origin": r["origin"]})
    prompts.sort(key=lambda p: p["id"])

    sample = {
        "built_from_commit": "",
        "review": [item(w, False) for w in review],
        "translate": [item(w, True) for w in translate],
        "translate_order": FREQ_LABEL,
        "prompts": prompts,
        "pdf_href": "pdf/AB2018.pdf",
    }
    return sample, missing


# --------------------------------------------------------------------------- vendor

def vendor_supabase(out):
    """Download the pinned supabase-js tarball, check its checksum, keep the browser build."""
    with urllib.request.urlopen(SUPABASE_JS["tarball"], timeout=60) as res:
        blob = res.read()
    algo, want = SUPABASE_JS["integrity"].split("-", 1)
    got = base64.b64encode(hashlib.new(algo, blob).digest()).decode("ascii")
    if got != want:
        raise SystemExit("supabase-js %s: the download does not match its published checksum" % SUPABASE_JS["version"])
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        js = tar.extractfile(SUPABASE_JS["file"]).read()
        try:
            licence = tar.extractfile(SUPABASE_JS["licence"]).read()
        except KeyError:
            licence = b""
    dest = out / VENDOR_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(js)
    if licence:
        dest.with_suffix(".LICENSE.txt").write_bytes(licence)
    return len(js)


# --------------------------------------------------------------------------- main

def main(argv=None):
    import os
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="folder to write the site into (emptied first)")
    ap.add_argument("--live", action="store_true", help="connect to Supabase (needs SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY)")
    ap.add_argument("--vendor", action="store_true", help="download the pinned supabase-js into vendor/")
    args = ap.parse_args(argv)

    try:
        config = site_config(args.live, os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_PUBLISHABLE_KEY", ""))
    except ValueError as err:
        raise SystemExit("config: %s" % err)

    out = Path(args.out).resolve()
    if (out == ROOT or ROOT in out.parents) and not (out.parent == ROOT and out.name.startswith("_site")):
        raise SystemExit("--out must be a folder outside the repository, or _site at its top level: it is emptied first")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    bs = _import("build_sample", HERE / "build_sample.py")
    wf = _import("word_frequency", ROOT / "tools" / "word_frequency.py")

    for name in STATIC:
        src = HERE / name
        if src.is_dir():
            shutil.copytree(src, out / name)
        else:
            shutil.copy2(src, out / name)
    if config["mode"] == "live":
        html = (out / "index.html").read_text(encoding="utf-8")
        meta = '<meta http-equiv="Content-Security-Policy" content="%s">' % csp(config)
        html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + meta, 1)
        html = html.replace("<title>Papiamento contribution tool (prototype)</title>", "<title>Papiamento contribution tool</title>")
        (out / "index.html").write_text(html, encoding="utf-8")
    (out / "config.js").write_text(config_js(config), encoding="utf-8")

    # Interface text and checks: the same data and the same Papiamento check as the prototype.
    words = bs.load_words()
    forms = bs.ab_forms(words)
    rules = bs.load_rules()
    barbarismos = bs.read_tsv(ROOT / "lexicon" / "barbarismos" / "barbarismos.tsv")
    variants = bs.read_tsv(ROOT / "lexicon" / "variants" / "curacao-aruba.tsv")
    loans = [l.strip() for l in (ROOT / "_meta" / "allowlists" / "accented-loans.txt").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    strings = bs.read_tsv(HERE / "ui-strings.tsv")
    problems = bs.check_pap_strings(strings, forms, rules, barbarismos, variants)
    for p in problems:
        print("pap text:", p)
    if problems:
        return 1

    commit = os.environ.get("GITHUB_SHA", "")[:7]
    sample, missing = catalog(out, bs, wf)
    sample["built_from_commit"] = commit
    checks = {
        "built_from_commit": commit,
        "rules": rules,
        "barbarismos": [{"id": b["id"], "wrong": b["wrong"], "right": b["right"].split("; "), "reason": b["reason"],
                         "rule_id": b["rule_id"], "notes": b["notes"], "is_ab_headword": b["wrong"].lower() in forms}
                        for b in barbarismos],
        "variants": [{"id": v["id"], "curacao": v["curacao"], "aruba": v["aruba"], "pattern": v["pattern"]} for v in variants],
        "accented_loans": loans,
        "ab_words": "\n".join(sorted(forms)),
    }
    ui = {"en": {}, "pap": {}, "pap_status": {}}
    for s in strings:
        ui["en"][s["key"]] = s["en"]
        ui["pap"][s["key"]] = s["pap"]
        ui["pap_status"][s["key"]] = s["pap_status"]
    (out / "data").mkdir()
    compact = lambda name, obj: "// Generated by tools/contribute/build_site.py.\nwindow.%s = %s;\n" % (
        name, json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    (out / "data" / "sample.js").write_text(compact("CONTRIB_SAMPLE", sample), encoding="utf-8")
    (out / "data" / "checks.js").write_text(compact("CONTRIB_CHECKS", checks), encoding="utf-8")
    (out / "data" / "strings.js").write_text(compact("CONTRIB_STRINGS", ui), encoding="utf-8")

    (out / "pdf").mkdir()
    shutil.copy2(ROOT / "sources" / "pdf" / "AB2018.pdf", out / "pdf" / "AB2018.pdf")

    if args.vendor:
        size = vendor_supabase(out)
        print("vendored supabase-js %s (%d bytes, checksum verified)" % (SUPABASE_JS["version"], size))
    elif config["mode"] == "live":
        print("note: live mode without --vendor; %s is missing, so the site shows its error screen" % VENDOR_PATH)

    print("built the %s site in %s: %d words to check, %d to translate, %d prompts, %d crops (%d entries not found on "
          "their page; those link to the PDF)" % (config["mode"], out, len(sample["review"]), len(sample["translate"]),
                                                    len(sample["prompts"]), len(sample["review"]) + len(sample["translate"]) - len(missing),
                                                    len(missing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

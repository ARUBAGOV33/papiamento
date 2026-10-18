// Live checks for Aruban Papiamento text, run in the browser while a teacher
// types. Uses only the repo's own data (built into data/checks.js):
//
// - rules/rules.jsonl: the 49 machine rules (JavaScript-compatible patterns)
// - lexicon/barbarismos/: Spanish and other forms that are not Aruban
// - lexicon/variants/: Curacao spellings mapped to the Aruban form
// - lexicon/words/: the AB 2018 word list, for the optional "not in the list" hint
//
// No check blocks a teacher: findings are advice, and the teacher may keep
// what they wrote. Works in the browser (window.PapChecker) and in Node
// (module.exports) so it can be tested without a browser.

(function (root) {
  "use strict";

  var LETTERS = "A-Za-zÀ-ÿñÑ";
  var BEFORE = "(?<![" + LETTERS + "'])";
  var AFTER = "(?![" + LETTERS + "'])";
  var TOKEN = new RegExp("[" + LETTERS + "]+(?:'[" + LETTERS + "]+)*", "g");
  var SEVERITY_ORDER = { error: 0, warning: 1, check: 2, suggestion: 3, info: 4 };

  function escapeRx(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function matchCase(fix, original) {
    if (original && original[0] !== original[0].toLowerCase() && fix) {
      return fix[0].toUpperCase() + fix.slice(1);
    }
    return fix;
  }

  // Expand $1, $2, $& and $$ in a rule's replacement for one match.
  function expand(template, m) {
    return template.replace(/\$(\$|&|\d+)/g, function (all, g) {
      if (g === "$") return "$";
      if (g === "&") return m[0];
      var v = m[Number(g)];
      return v == null ? "" : v;
    });
  }

  function prepare(data) {
    var rules = [];
    data.rules.forEach(function (r) {
      try {
        rules.push({
          id: r.rule_id,
          rx: new RegExp(r.pattern, "g" + (r.flags || "")),
          replacement: r.replacement,
          message: r.message,
          severity: r.severity || "warning",
          title: r.title,
          file: r.file
        });
      } catch (err) {
        if (typeof console !== "undefined") console.warn("rule does not compile:", r.rule_id, err.message);
      }
    });
    var ab = new Set(data.ab_words.split("\n"));
    var barbarismos = data.barbarismos.map(function (b) {
      return {
        id: b.id,
        wrong: b.wrong,
        right: b.right,
        reason: b.reason,
        notes: b.notes,
        ruleId: b.rule_id,
        isHeadword: b.is_ab_headword,
        rx: new RegExp(BEFORE + escapeRx(b.wrong).replace(/ /g, "\\s+") + AFTER, "gi")
      };
    });
    var variants = new Map();
    data.variants.forEach(function (v) { variants.set(v.curacao.toLowerCase(), v); });
    var loans = new Set(data.accented_loans.map(function (s) { return s.toLowerCase(); }));
    var multi = [];
    ab.forEach(function (w) { if (w.indexOf(" ") >= 0) multi.push(w); });
    multi.sort(function (a, b) { return b.length - a.length; });
    var multiRx = multi.length
      ? new RegExp(BEFORE + "(?:" + multi.map(function (w) { return escapeRx(w).replace(/ /g, "\\s+"); }).join("|") + ")" + AFTER, "gi")
      : null;
    return { rules: rules, ab: ab, barbarismos: barbarismos, variants: variants, loans: loans, multiRx: multiRx };
  }

  function wordAt(text, start, end) {
    var a = start, b = end;
    var letter = new RegExp("[" + LETTERS + "]");
    while (a > 0 && letter.test(text[a - 1])) a--;
    while (b < text.length && letter.test(text[b])) b++;
    return text.slice(a, b);
  }

  function isKnown(P, low) {
    if (P.ab.has(low)) return true;
    // Plural -nan on a listed noun (casnan), and a contraction (cumpr'e).
    if (low.length > 4 && low.slice(-3) === "nan" && P.ab.has(low.slice(0, -3))) return true;
    if (low.indexOf("'") >= 0) return true;
    return false;
  }

  // Returns findings sorted by position:
  // {start, end, text, kind: rule|barbarismo|variant|unknown, id, severity, message, fixes[]}
  function check(text, P, opts) {
    opts = opts || {};
    var out = [];
    if (!text || !text.trim()) return out;

    P.rules.forEach(function (r) {
      r.rx.lastIndex = 0;
      var m;
      while ((m = r.rx.exec(text)) !== null) {
        if (m[0] === "") { r.rx.lastIndex++; continue; }
        var fixes = [];
        if (r.id === "RULE_ORT_ACCENT_001") {
          var word = wordAt(text, m.index, m.index + m[0].length);
          if (P.loans.has(word.toLowerCase())) continue;
          // Offer the unaccented form only when the AB 2018 list has it.
          var plain = word.normalize("NFD").replace(/[\u0300-\u036f]/g, "").normalize("NFC");
          if (word === m[0] && P.ab.has(plain.toLowerCase())) fixes.push(matchCase(plain.toLowerCase(), word));
        }
        if (r.replacement != null) {
          var fix = expand(r.replacement, m);
          if (fix !== m[0]) fixes.push(fix);
        }
        out.push({ start: m.index, end: m.index + m[0].length, text: m[0], kind: "rule", id: r.id,
                   severity: r.severity, message: r.message, fixes: fixes, title: r.title, file: r.file });
      }
    });

    P.barbarismos.forEach(function (b) {
      b.rx.lastIndex = 0;
      var m;
      while ((m = b.rx.exec(text)) !== null) {
        out.push({ start: m.index, end: m.index + m[0].length, text: m[0], kind: "barbarismo", id: b.id,
                   ruleId: b.ruleId, severity: b.isHeadword ? "check" : "warning", message: b.reason,
                   notes: b.notes, fixes: b.right.map(function (r) { return matchCase(r, m[0]); }) });
      }
    });

    var covered = [];
    if (P.multiRx) {
      P.multiRx.lastIndex = 0;
      var mm;
      while ((mm = P.multiRx.exec(text)) !== null) covered.push([mm.index, mm.index + mm[0].length]);
    }
    TOKEN.lastIndex = 0;
    var t;
    while ((t = TOKEN.exec(text)) !== null) {
      var word = t[0], low = word.toLowerCase(), start = t.index, end = t.index + word.length;
      var v = P.variants.get(low);
      if (v && !P.ab.has(low)) {
        out.push({ start: start, end: end, text: word, kind: "variant", id: v.id, severity: "warning",
                   message: "Curaçao spelling (" + v.pattern + ").", fixes: [matchCase(v.aruba, word)] });
        continue;
      }
      if (opts.unknownWords && !isKnown(P, low) && !covered.some(function (c) { return start >= c[0] && end <= c[1]; })) {
        out.push({ start: start, end: end, text: word, kind: "unknown", id: "AB2018-list", severity: "info",
                   message: "Not in the AB 2018 word list.", fixes: [] });
      }
    }

    // Drop findings that repeat another finding on the same span; keep the one
    // that offers a fix, then the more severe one.
    out.sort(function (a, b) {
      return a.start - b.start || b.end - a.end ||
        (b.fixes.length > 0) - (a.fixes.length > 0) ||
        SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
    });
    var kept = [];
    out.forEach(function (f) {
      var dup = kept.some(function (k) {
        var overlap = f.start < k.end && k.start < f.end;
        var sameRule = (f.ruleId && f.ruleId === k.id) || (k.ruleId && k.ruleId === f.id);
        return (f.start === k.start && f.end === k.end) || (overlap && sameRule) ||
          (overlap && f.kind === "unknown");
      });
      if (!dup) kept.push(f);
    });
    return kept;
  }

  function applyFix(text, finding, fix) {
    return text.slice(0, finding.start) + fix + text.slice(finding.end);
  }

  // Normalise a contributed text the way the repo's TSV conventions require:
  // NFC, straight apostrophes, no tabs or line breaks, single spaces, trimmed.
  function normalise(text) {
    return (text || "").normalize("NFC").replace(/[‘’ʼ]/g, "'")
      .replace(/[\t\r\n]+/g, " ").replace(/ {2,}/g, " ").trim();
  }

  var api = { prepare: prepare, check: check, applyFix: applyFix, normalise: normalise, severityOrder: SEVERITY_ORDER };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.PapChecker = api;
})(this);

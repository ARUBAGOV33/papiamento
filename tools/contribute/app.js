// Contribution tool prototype for ARUBAGOV33/papiamento.
//
// Three modes (check machine translations, translate words, translate
// sentences), a rating screen for sentences and a review-board screen.
// Everything is stored in this browser (localStorage) and can be exported as
// JSON. No network calls. See DESIGN.md for the design this prototypes.

(function () {
  "use strict";

  var STR = window.CONTRIB_STRINGS;
  var SAMPLE = window.CONTRIB_SAMPLE;
  var CHECKS = window.CONTRIB_CHECKS;
  var KEY = "pap-contrib-prototype-v1";
  var FORMAT = "pap-contrib-prototype/1";
  var LANGS = ["en", "nl", "es"];
  var P = window.PapChecker.prepare(CHECKS);

  var state = load();
  var session = {
    skipped: { review: new Set(), translate: new Set(), sentences: new Set(), rate: new Set() },
    stayOn: null,
    flash: null,
    draft: {}
  };

  // ---------------------------------------------------------------- storage

  function blank() {
    return { format: FORMAT, people: [], current: null, ui_lang: "en", show_unknown: true,
             answers: [], translations: [], ratings: [], decisions: [] };
  }

  function load() {
    try {
      var raw = window.localStorage.getItem(KEY);
      if (raw) {
        var s = JSON.parse(raw);
        if (s && s.format === FORMAT) return Object.assign(blank(), s);
      }
    } catch (e) { /* storage blocked: work in memory */ }
    return blank();
  }

  function save() {
    try { window.localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* in memory only */ }
  }

  function newId(prefix) {
    return prefix + "-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  }

  function now() { return new Date().toISOString(); }

  // ------------------------------------------------------------------- text

  function t(key, vars) {
    var lang = state.ui_lang === "pap" ? "pap" : "en";
    var s = (STR[lang] && STR[lang][key]) || STR.en[key] || key;
    if (vars) s = s.replace(/\{(\w+)\}/g, function (m, k) { return k in vars ? String(vars[k]) : m; });
    return s;
  }

  function langName(code) { return t("lang." + code + "_name"); }

  // ------------------------------------------------------------------- DOM

  function el(tag, attrs) {
    var n = document.createElement(tag);
    var props = {};
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        var v = attrs[k];
        if (v == null || v === false) return;
        if (k === "class") n.className = v;
        else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
        else if (k === "value" || k === "checked") props[k] = v;
        else if (v === true) n.setAttribute(k, "");
        else n.setAttribute(k, v);
      });
    }
    for (var i = 2; i < arguments.length; i++) append(n, arguments[i]);
    Object.keys(props).forEach(function (k) { n[k] = props[k]; });
    return n;
  }

  function append(n, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { append(n, x); }); return; }
    n.appendChild(c.nodeType ? c : document.createTextNode(String(c)));
  }

  function button(label, onclick, cls, extra) {
    return el("button", Object.assign({ type: "button", class: "btn " + (cls || ""), onclick: onclick }, extra || {}), label);
  }

  // ---------------------------------------------------------------- people

  function me() {
    for (var i = 0; i < state.people.length; i++) if (state.people[i].id === state.current) return state.people[i];
    return null;
  }

  function person(id) {
    for (var i = 0; i < state.people.length; i++) if (state.people[i].id === id) return state.people[i];
    return { id: id, name: "?", handle: "unknown" };
  }

  function makeHandle(name, id) {
    var slug = name.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    if (!slug) slug = "contributor-" + id.slice(-4);
    var taken = state.people.map(function (p) { return p.handle; });
    var h = slug, n = 2;
    while (taken.indexOf(h) >= 0) h = slug + "-" + n++;
    return h;
  }

  function creditName(p) { return p.credit ? p.name : p.handle; }

  // ----------------------------------------------------------------- queues

  function answersFor(kind, item) {
    return state.answers.filter(function (a) { return a.kind === kind && a.item === item; });
  }

  function decisionFor(kind, item) {
    for (var i = state.decisions.length - 1; i >= 0; i--) {
      var d = state.decisions[i];
      if (d.kind === kind && d.item === item) return d;
    }
    return null;
  }

  function openForMe(kind, item) {
    var ans = answersFor(kind, item);
    return ans.length < 2 && !decisionFor(kind, item) &&
      !ans.some(function (a) { return a.by === state.current; });
  }

  function reviewQueue() {
    return SAMPLE.review.filter(function (w) { return openForMe("review", w.id); });
  }

  function translateQueue() {
    return SAMPLE.translate.filter(function (w) { return openForMe("translate", w.id); });
  }

  function translationsOf(promptId) {
    return state.translations.filter(function (tr) { return tr.prompt === promptId; });
  }

  function sentenceQueue() {
    var mine = function (p) { return translationsOf(p.id).some(function (tr) { return tr.by === state.current; }); };
    return SAMPLE.prompts.filter(function (p) { return !mine(p); })
      .sort(function (a, b) { return translationsOf(a.id).length - translationsOf(b.id).length; });
  }

  function ratingsOf(trId) {
    return state.ratings.filter(function (r) { return r.translation === trId; });
  }

  function rateQueue() {
    return state.translations.filter(function (tr) {
      var rs = ratingsOf(tr.id);
      return tr.by !== state.current && rs.length < 2 && !decisionFor("sentence", tr.id) &&
        !rs.some(function (r) { return r.by === state.current; });
    });
  }

  function promptById(id) {
    for (var i = 0; i < SAMPLE.prompts.length; i++) if (SAMPLE.prompts[i].id === id) return SAMPLE.prompts[i];
    return null;
  }

  function wordById(id) {
    var all = SAMPLE.review.concat(SAMPLE.translate);
    for (var i = 0; i < all.length; i++) if (all[i].id === id) return all[i];
    return null;
  }

  // -------------------------------------------------------------- agreement

  function normGloss(s) {
    return window.PapChecker.normalise(s).replace(/\s*;\s*/g, "; ").replace(/;\s*$/, "");
  }

  function senseKey(s) {
    return normGloss(s).toLowerCase().split("; ").filter(Boolean).sort().join("|");
  }

  // Outcome per language for "check translations".
  function reviewOutcome(answers, lang, draft) {
    var decided = answers.map(function (a) { return a.verdicts[lang]; })
      .filter(function (v) { return v.verdict !== "unsure"; });
    if (decided.length < 2) return { status: "not_enough" };
    if (decided.every(function (v) { return v.verdict === "correct"; })) return { status: "agree", value: draft, from: "machine" };
    if (decided.every(function (v) { return v.verdict === "wrong"; })) {
      var keys = decided.map(function (v) { return senseKey(v.fix); });
      if (keys.every(function (k) { return k === keys[0]; })) return { status: "agree", value: decided[0].fix, from: "fix" };
    }
    return { status: "differ" };
  }

  // Outcome per language for "translate words".
  function translateOutcome(answers, lang) {
    var vals = answers.map(function (a) { return a.unknown ? "" : a.values[lang]; }).filter(Boolean);
    if (vals.length === 0) return { status: "agree", value: "" };
    if (vals.length < 2) return { status: "not_enough" };
    var keys = vals.map(senseKey);
    if (keys.every(function (k) { return k === keys[0]; })) return { status: "agree", value: vals[0] };
    return { status: "differ" };
  }

  // Outcome for one sentence translation: the author plus the raters.
  function sentenceOutcome(tr) {
    var rs = ratingsOf(tr.id);
    if (!rs.length) return { status: "not_enough" };
    if (rs.every(function (r) { return r.verdict === "good"; })) return { status: "agree" };
    return { status: "differ" };
  }

  // --------------------------------------------------------------- rendering

  var routes = {
    home: viewHome, review: viewReview, translate: viewTranslate, sentences: viewSentences,
    rate: viewRate, board: viewBoard, export: viewExport, about: viewAbout, person: viewConsent
  };

  function route() {
    var r = (window.location.hash || "#/home").replace(/^#\//, "");
    return routes[r] ? r : "home";
  }

  function go(r) {
    if (window.location.hash === "#/" + r) render();
    else window.location.hash = "#/" + r;
  }

  function render() {
    document.documentElement.lang = state.ui_lang === "pap" ? "pap" : "en";
    document.title = t("app.title") + " (prototype)";
    renderHeader();
    var main = document.getElementById("main");
    main.innerHTML = "";
    var r = me() ? route() : "person";
    renderNav(r);
    if (session.flash) {
      main.appendChild(el("div", { class: "flash", role: "status" }, session.flash));
      session.flash = null;
    }
    main.appendChild(routes[r]());
    var h = main.querySelector("h2");
    if (h) h.setAttribute("tabindex", "-1");
  }

  function renderHeader() {
    var head = document.getElementById("head");
    head.innerHTML = "";
    var p = me();
    var langSel = el("select", { id: "ui-lang", "aria-label": t("lang.label"), value: state.ui_lang,
      onchange: function (e) { state.ui_lang = e.target.value; save(); render(); } },
      el("option", { value: "en" }, "English"),
      el("option", { value: "pap" }, "Papiamento (draft)"));
    langSel.value = state.ui_lang;
    var who = null;
    if (p) {
      var sel = el("select", { id: "who", "aria-label": t("person.switch"),
        onchange: function (e) {
          if (e.target.value === "__new") { go("person"); return; }
          state.current = e.target.value; save(); render();
        } },
        state.people.map(function (x) {
          return el("option", { value: x.id }, x.name + (x.board ? " (" + t("person.board_badge") + ")" : ""));
        }),
        el("option", { value: "__new" }, "+ " + t("person.new")));
      sel.value = state.current;
      who = el("label", { class: "who" }, el("span", { class: "muted" }, t("person.as")), sel);
    }
    head.appendChild(el("div", { class: "brand" },
      el("h1", null, t("app.title")),
      el("p", { class: "muted" }, t("app.subtitle"))));
    head.appendChild(el("div", { class: "head-controls" },
      el("label", { class: "who" }, el("span", { class: "muted" }, t("lang.label")), langSel), who));

    var banner = document.getElementById("banner");
    banner.innerHTML = "";
    banner.appendChild(el("p", { class: "banner proto" }, t("banner.prototype")));
    if (state.ui_lang === "pap") banner.appendChild(el("p", { class: "banner draft" }, t("lang.pap_note")));
  }

  function renderNav(current) {
    var nav = document.getElementById("nav");
    nav.innerHTML = "";
    if (!me()) return;
    var items = [["home", "nav.home"], ["review", "nav.review", reviewQueue().length],
                 ["translate", "nav.translate", translateQueue().length],
                 ["sentences", "nav.sentences", sentenceQueue().length],
                 ["rate", "nav.rate", rateQueue().length]];
    if (me().board) items.push(["board", "nav.board", boardCount()]);
    items.push(["export", "nav.export"], ["about", "nav.about"]);
    nav.appendChild(el("ul", null, items.map(function (it) {
      return el("li", null, el("a", { href: "#/" + it[0], "aria-current": it[0] === current ? "page" : null },
        t(it[1]), it[2] ? el("span", { class: "count" }, it[2]) : null));
    })));
  }

  // ------------------------------------------------------------------ views

  function viewConsent() {
    var adding = !!me();
    var form = el("form", { class: "card stack", novalidate: true });
    var err = el("p", { class: "error", role: "alert", hidden: true });
    var name = el("input", { id: "c-name", type: "text", autocomplete: "name", required: true });
    var roles = ["teacher", "linguist", "other"].map(function (r, i) {
      return el("label", { class: "choice" }, el("input", { type: "radio", name: "role", value: r, checked: i === 0 }), t("role." + r));
    });
    var board = el("input", { id: "c-board", type: "checkbox" });
    var gh = el("input", { id: "c-gh", type: "text", autocomplete: "off", placeholder: "e.g. victorgomesrt-rgb" });
    var ghRow = el("div", { class: "field", hidden: true }, el("label", { for: "c-gh" }, t("consent.github")), gh);
    board.addEventListener("change", function () { ghRow.hidden = !board.checked; });
    var credit = el("input", { id: "c-credit", type: "checkbox", checked: true });
    var lw = el("input", { id: "c-lw", type: "checkbox" });
    var ls = el("input", { id: "c-ls", type: "checkbox" });

    form.appendChild(el("h2", null, t("consent.title")));
    form.appendChild(el("p", null, t("consent.intro")));
    form.appendChild(el("div", { class: "field" }, el("label", { for: "c-name" }, t("consent.name")), name));
    form.appendChild(el("fieldset", { class: "field" }, el("legend", null, t("consent.role")), el("div", { class: "choices" }, roles)));
    form.appendChild(el("label", { class: "check" }, board, t("consent.board")));
    form.appendChild(ghRow);
    form.appendChild(el("label", { class: "check" }, credit, t("consent.credit")));
    form.appendChild(el("fieldset", { class: "field licence" }, el("legend", null, "Licence"),
      el("label", { class: "check" }, lw, t("consent.words")),
      el("label", { class: "check" }, ls, t("consent.sentences")),
      el("p", { class: "note" }, t("consent.pending"))));
    form.appendChild(el("p", { class: "muted small" }, t("consent.privacy")));
    form.appendChild(err);
    form.appendChild(el("div", { class: "actions" },
      adding ? button(t("common.back"), function () { go("home"); }, "ghost") : null,
      el("button", { type: "submit", class: "btn primary" }, t("consent.start"))));
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var n = window.PapChecker.normalise(name.value);
      if (!n || !lw.checked || !ls.checked) { err.textContent = t("consent.need"); err.hidden = false; return; }
      var id = newId("person");
      var role = form.querySelector("input[name=role]:checked").value;
      state.people.push({
        id: id, name: n, handle: makeHandle(n, id), role: role, board: board.checked,
        github: board.checked ? window.PapChecker.normalise(gh.value) : "", credit: credit.checked,
        consent: { words: "CC-BY-4.0", sentences: "CC0-1.0 (proposed)", text_version: "prototype-1", at: now() },
        created_at: now()
      });
      state.current = id;
      save();
      go("home");
    });
    return form;
  }

  function viewHome() {
    var p = me();
    var tiles = [
      ["review", "nav.review", "home.review", reviewQueue().length],
      ["translate", "nav.translate", "home.translate", translateQueue().length],
      ["sentences", "nav.sentences", "home.sentences", sentenceQueue().length],
      ["rate", "nav.rate", "home.rate", rateQueue().length]
    ];
    if (p.board) tiles.push(["board", "nav.board", "home.board", boardCount()]);
    return el("section", null,
      el("h2", null, t("home.hello", { name: p.name })),
      el("div", { class: "tiles" }, tiles.map(function (x) {
        return el("a", { class: "tile", href: "#/" + x[0] },
          el("h3", null, t(x[1])),
          el("p", null, t(x[2])),
          el("span", { class: "pill" + (x[3] ? "" : " zero") }, t("home.waiting", { n: x[3] })));
      })));
  }

  function doneCard(kind, extra) {
    var skipped = session.skipped[kind];
    return el("section", { class: "card stack" },
      el("h2", null, t("common.done_title")),
      el("p", null, t("common.done")),
      extra || null,
      skipped && skipped.size ? button(t("common.show_skipped"), function () { skipped.clear(); render(); }, "ghost") : null,
      el("div", { class: "actions" }, button(t("nav.home"), function () { go("home"); }, "primary")));
  }

  function wordHeader(w) {
    var uncertain = /uncertain/.test(w.notes || "");
    return el("div", { class: "word" },
      el("div", { class: "word-title" },
        el("span", { class: "lemma", lang: "pap" }, w.lemma),
        w.alt ? el("span", { class: "alt", lang: "pap" }, "[" + w.alt + "]") : null,
        w.pos ? el("span", { class: "chip" }, w.pos) : null,
        w.tag ? el("span", { class: "chip" }, "(" + w.tag + ")") : null,
        el("span", { class: "chip muted" }, w.id)),
      el("figure", { class: "crop" },
        el("picture", null,
          el("source", { media: "(max-width: 560px)", srcset: w.crop_column, width: w.crop_column_w, height: w.crop_column_h }),
          el("img", { src: w.crop, width: w.crop_w, height: w.crop_h, loading: "lazy",
                      alt: "AB 2018 word list, page " + w.page + ", with " + w.lemma + " highlighted" })),
        el("figcaption", null, t("word.page", { page: w.page }), " · ",
          el("a", { href: SAMPLE.pdf_href + "#page=" + w.pdf_page, target: "_blank", rel: "noopener" }, t("word.open_pdf")))),
      uncertain ? el("p", { class: "note warn" }, t("word.uncertain")) :
        (w.notes ? el("p", { class: "note" }, el("strong", null, t("word.notes") + ": "), w.notes) : null));
  }

  function progressLine(kind, items) {
    var doneByMe = items.filter(function (w) {
      return answersFor(kind, w.id).some(function (a) { return a.by === state.current; });
    }).length;
    return el("p", { class: "muted small" }, t("common.progress", { i: Math.min(doneByMe + 1, items.length), n: items.length }));
  }

  function segmented(name, options, onchange) {
    return el("div", { class: "seg", role: "radiogroup" }, options.map(function (o) {
      return el("label", { class: "seg-opt " + o.value },
        el("input", { type: "radio", name: name, value: o.value, onchange: onchange }),
        el("span", null, o.label));
    }));
  }

  function viewReview() {
    var queue = reviewQueue().filter(function (w) { return !session.skipped.review.has(w.id); });
    if (!queue.length) return doneCard("review");
    var w = queue[0];
    var verdicts = {};
    var rows = LANGS.map(function (lang) {
      var fix = el("input", { type: "text", class: "fix", lang: lang, "aria-label": t("review.fix", { lang: langName(lang) }),
                              placeholder: t("review.fix", { lang: langName(lang) }), hidden: true });
      var seg = segmented("v-" + lang, [
        { value: "correct", label: t("review.correct") },
        { value: "wrong", label: t("review.wrong") },
        { value: "unsure", label: t("review.unsure") }
      ], function (e) { verdicts[lang] = e.target.value; fix.hidden = e.target.value !== "wrong"; if (!fix.hidden) fix.focus(); });
      return { lang: lang, fix: fix, node: el("fieldset", { class: "lang-row" },
        el("legend", null, langName(lang)),
        el("div", { class: "draft-line" }, el("span", { class: "muted small" }, t("review.draft") + ": "),
          el("span", { class: "draft-val", lang: lang }, w[lang] || "—")),
        seg, fix) };
    });
    var comment = el("textarea", { rows: 2, "aria-label": t("common.comment"), placeholder: t("common.comment") });
    var err = el("p", { class: "error", role: "alert", hidden: true });

    function submit() {
      var missing = LANGS.some(function (l) { return !verdicts[l]; });
      if (missing) { err.textContent = t("review.need_all"); err.hidden = false; return; }
      var out = {};
      var badFix = false;
      rows.forEach(function (r) {
        var v = verdicts[r.lang];
        var f = v === "wrong" ? normGloss(r.fix.value) : "";
        if (v === "wrong" && !f) badFix = true;
        out[r.lang] = { verdict: v, fix: f };
      });
      if (badFix) { err.textContent = t("review.need_fix"); err.hidden = false; return; }
      state.answers.push({ id: newId("ans"), kind: "review", item: w.id, by: state.current, at: now(),
                           verdicts: out, comment: window.PapChecker.normalise(comment.value) });
      save();
      session.flash = t("common.saved");
      render();
    }

    return el("section", { class: "card stack" },
      el("div", { class: "row-between" }, el("h2", null, t("nav.review")), progressLine("review", SAMPLE.review)),
      wordHeader(w),
      el("p", { class: "lead" }, t("review.intro")),
      rows.map(function (r) { return r.node; }),
      comment, err,
      el("p", { class: "muted small" }, t("common.answers_so_far", { n: answersFor("review", w.id).length })),
      el("div", { class: "actions" },
        button(t("common.skip"), function () { session.skipped.review.add(w.id); render(); }, "ghost"),
        button(t("common.save_next"), submit, "primary")));
  }

  function glossHints(lang, value, w) {
    var hints = [];
    var v = normGloss(value);
    if (!v) return hints;
    if (v.split("; ").length > 3) hints.push("At most three meanings.");
    if (lang === "en" && w.pos === "v." && v.split("; ").some(function (s) { return s.indexOf("to ") !== 0; })) {
      hints.push("English verbs start with \"to\".");
    }
    if (/[,]/.test(v) && v.indexOf(";") < 0) hints.push("Separate different meanings with ; not ,");
    return hints;
  }

  function viewTranslate() {
    var queue = translateQueue().filter(function (w) { return !session.skipped.translate.has(w.id); });
    if (!queue.length) return doneCard("translate");
    var w = queue[0];
    var inputs = {};
    var rows = LANGS.map(function (lang) {
      var hint = el("p", { class: "hint", "aria-live": "polite" });
      var inp = el("input", { type: "text", lang: lang, id: "tr-" + lang,
        oninput: function () { hint.textContent = glossHints(lang, inp.value, w).join(" "); } });
      inputs[lang] = inp;
      return el("div", { class: "field" }, el("label", { for: "tr-" + lang }, langName(lang)), inp, hint);
    });
    var unknown = el("input", { type: "checkbox", id: "tr-unknown" });
    var comment = el("textarea", { rows: 2, "aria-label": t("common.comment"), placeholder: t("common.comment") });
    var err = el("p", { class: "error", role: "alert", hidden: true });

    function submit() {
      var vals = {};
      LANGS.forEach(function (l) { vals[l] = normGloss(inputs[l].value); });
      var any = LANGS.some(function (l) { return vals[l]; });
      if (!any && !unknown.checked) { err.textContent = t("translate.need_one"); err.hidden = false; return; }
      state.answers.push({ id: newId("ans"), kind: "translate", item: w.id, by: state.current, at: now(),
                           values: unknown.checked ? { en: "", nl: "", es: "" } : vals, unknown: unknown.checked,
                           comment: window.PapChecker.normalise(comment.value) });
      save();
      session.flash = t("common.saved");
      render();
    }

    return el("section", { class: "card stack" },
      el("div", { class: "row-between" }, el("h2", null, t("nav.translate")), progressLine("translate", SAMPLE.translate)),
      wordHeader(w),
      el("p", { class: "lead" }, t("translate.intro")),
      el("p", { class: "muted small" }, t("translate.hint")),
      rows,
      el("label", { class: "check" }, unknown, t("translate.unknown")),
      comment, err,
      el("p", { class: "muted small" }, t("common.answers_so_far", { n: answersFor("translate", w.id).length }),
        " · ", t("translate.freq", { source: SAMPLE.translate_order + " (" + w.freq + ")" })),
      el("div", { class: "actions" },
        button(t("common.skip"), function () { session.skipped.translate.add(w.id); render(); }, "ghost"),
        button(t("common.save_next"), submit, "primary")));
  }

  // Live-check panel bound to a textarea. Returns {node, refresh, findings()}.
  function checkerPanel(textarea) {
    var preview = el("p", { class: "preview", lang: "pap" });
    var list = el("ul", { class: "findings" });
    var status = el("p", { class: "muted small" });
    var toggle = el("input", { type: "checkbox", checked: state.show_unknown,
      onchange: function () { state.show_unknown = toggle.checked; save(); refresh(); } });
    var current = [];

    function refresh() {
      var text = textarea.value;
      current = window.PapChecker.check(text, P, { unknownWords: state.show_unknown });
      preview.innerHTML = "";
      list.innerHTML = "";
      if (!text.trim()) { status.textContent = ""; preview.hidden = true; return; }
      preview.hidden = false;
      var pos = 0, n = 0;
      current.forEach(function (f) {
        if (f.start < pos) return;
        preview.appendChild(document.createTextNode(text.slice(pos, f.start)));
        n++;
        preview.appendChild(el("mark", { class: "sev-" + f.severity, title: f.message }, text.slice(f.start, f.end), el("sup", null, n)));
        pos = f.end;
      });
      preview.appendChild(document.createTextNode(text.slice(pos)));
      var major = current.filter(function (f) { return f.kind !== "unknown"; });
      var unknown = current.filter(function (f) { return f.kind === "unknown"; });
      status.textContent = major.length ? "" : t("sent.checks_none");
      var i = 0;
      current.forEach(function (f) {
        i++;
        if (f.kind === "unknown") return;
        var msg;
        if (f.kind === "variant") msg = t("sent.curacao", { right: f.fixes.join(" / ") });
        else if (f.kind === "barbarismo") msg = f.severity === "check" ? t("sent.barbarismo_check", { right: f.fixes.join(" / ") })
                                                                        : t("sent.barbarismo", { right: f.fixes.join(" / ") });
        else msg = f.message;
        list.appendChild(el("li", { class: "sev-" + f.severity },
          el("span", { class: "num" }, i),
          el("span", { class: "quote", lang: "pap" }, "“" + f.text + "”"), " ",
          el("span", null, msg), " ",
          f.kind === "barbarismo" && f.message ? el("span", { class: "muted small" }, "(" + f.message + ")") : null, " ",
          el("span", { class: "ref muted small" }, f.kind === "rule" ? f.id : f.kind === "variant" ? "lexicon/variants " + f.id : "lexicon/barbarismos " + f.id),
          f.fixes.map(function (fx) {
            return button(t("sent.use", { fix: fx }), function () {
              textarea.value = window.PapChecker.applyFix(textarea.value, f, fx);
              textarea.dispatchEvent(new Event("input"));
              textarea.focus();
            }, "small");
          })));
      });
      if (unknown.length) {
        list.appendChild(el("li", { class: "sev-info" }, el("span", { class: "num" }, "·"),
          el("span", { class: "quote", lang: "pap" }, unknown.map(function (f) { return f.text; }).join(", ")), " ",
          el("span", null, t("sent.unknown"))));
      }
    }

    textarea.addEventListener("input", refresh);
    var node = el("div", { class: "checker", "aria-live": "polite" },
      el("div", { class: "row-between" }, el("h3", null, t("sent.checks")),
        el("label", { class: "check small" }, toggle, t("sent.unknown_toggle"))),
      el("p", { class: "muted small" }, t("sent.preview") + ":"), preview, status, list,
      el("p", { class: "note small" }, t("sent.checks_note")));
    refresh();
    return { node: node, refresh: refresh, findings: function () { return current; } };
  }

  function summarise(findings) {
    return findings.filter(function (f) { return f.kind !== "unknown"; })
      .map(function (f) { return { id: f.kind === "rule" ? f.id : f.kind + ":" + f.id, text: f.text, fixes: f.fixes }; });
  }

  function promptCard(p) {
    return el("div", { class: "prompt" },
      el("div", { class: "chips" },
        el("span", { class: "chip lang" }, langName(p.lang)),
        p.origin === "written-for-prototype" ? el("span", { class: "chip warn" }, t("sent.written")) : null,
        el("span", { class: "chip muted" }, p.id)),
      el("p", { class: "prompt-text", lang: p.lang }, p.text));
  }

  function viewSentences() {
    var p = null;
    if (session.stayOn) p = promptById(session.stayOn);
    if (!p) {
      session.stayOn = null;
      var queue = sentenceQueue().filter(function (x) { return !session.skipped.sentences.has(x.id); });
      if (!queue.length) return doneCard("sentences");
      p = queue[0];
    }
    var mine = translationsOf(p.id).filter(function (tr) { return tr.by === state.current; });
    var others = new Set(translationsOf(p.id).filter(function (tr) { return tr.by !== state.current; })
      .map(function (tr) { return tr.by; })).size;
    var ta = el("textarea", { id: "pap-text", rows: 3, lang: "pap", spellcheck: "false", autocapitalize: "sentences",
                              autocomplete: "off", "aria-describedby": "no-draft", value: session.draft[p.id] || "" });
    ta.addEventListener("input", function () { session.draft[p.id] = ta.value; });
    var panel = checkerPanel(ta);
    var err = el("p", { class: "error", role: "alert", hidden: true });

    function store(stay) {
      var text = window.PapChecker.normalise(ta.value);
      if (!text) { err.textContent = t("sent.empty"); err.hidden = false; return; }
      var kept = summarise(window.PapChecker.check(text, P, { unknownWords: false }));
      state.translations.push({ id: newId("tr"), prompt: p.id, by: state.current, at: now(), text: text,
                                flags_kept: kept, fix_of: null });
      save();
      delete session.draft[p.id];
      session.stayOn = stay ? p.id : null;
      session.flash = t("common.saved") + (kept.length ? " " + t("sent.kept", { n: kept.length }) : "");
      render();
    }

    return el("section", { class: "card stack" },
      el("h2", null, t("nav.sentences")),
      promptCard(p),
      el("p", { class: "lead" }, t("sent.intro")),
      el("p", { class: "note", id: "no-draft" }, t("sent.no_draft")),
      mine.length ? el("div", { class: "mine" }, el("p", { class: "muted small" }, t("sent.yours")),
        el("ul", null, mine.map(function (tr) { return el("li", { lang: "pap" }, tr.text); }))) : null,
      others ? el("p", { class: "muted small" }, t("sent.others", { n: others })) : null,
      el("label", { for: "pap-text", class: "label-strong" }, t("sent.your")),
      ta, panel.node, err,
      el("div", { class: "actions" },
        button(t("common.skip"), function () { session.skipped.sentences.add(p.id); session.stayOn = null; render(); }, "ghost"),
        button(t("sent.another"), function () { store(true); }, ""),
        button(t("sent.save"), function () { store(false); }, "primary")));
  }

  function viewRate() {
    var queue = rateQueue().filter(function (tr) { return !session.skipped.rate.has(tr.id); });
    if (!queue.length) {
      var anyOthers = state.translations.some(function (tr) { return tr.by !== state.current; });
      return doneCard("rate", anyOthers ? null : el("p", { class: "note" }, t("rate.empty_hint")));
    }
    var tr = queue[0];
    var p = promptById(tr.prompt);
    var verdict = null;
    var fixTa = el("textarea", { rows: 3, lang: "pap", spellcheck: "false", "aria-label": t("rate.fix_box"), value: tr.text });
    var fixPanel = checkerPanel(fixTa);
    var fixBox = el("div", { class: "stack", hidden: true }, el("label", { class: "label-strong" }, t("rate.fix_box")), fixTa, fixPanel.node);
    var seg = segmented("rate", [{ value: "good", label: t("rate.good") }, { value: "fix", label: t("rate.fix") }],
      function (e) { verdict = e.target.value; fixBox.hidden = verdict !== "fix"; if (!fixBox.hidden) fixTa.focus(); });
    var comment = el("textarea", { rows: 2, "aria-label": t("common.comment"), placeholder: t("common.comment") });
    var err = el("p", { class: "error", role: "alert", hidden: true });
    var flags = window.PapChecker.check(tr.text, P, { unknownWords: false });

    function submit() {
      if (!verdict) { err.textContent = t("rate.need_choice"); err.hidden = false; return; }
      var fixId = null;
      if (verdict === "fix") {
        var text = window.PapChecker.normalise(fixTa.value);
        if (!text || text === tr.text) { err.textContent = t("rate.need_fix"); err.hidden = false; return; }
        fixId = newId("tr");
        state.translations.push({ id: fixId, prompt: tr.prompt, by: state.current, at: now(), text: text,
                                  flags_kept: summarise(window.PapChecker.check(text, P, {})), fix_of: tr.id });
      }
      state.ratings.push({ id: newId("rat"), translation: tr.id, by: state.current, at: now(), verdict: verdict,
                           fix_translation: fixId, comment: window.PapChecker.normalise(comment.value) });
      save();
      session.flash = t("common.saved");
      render();
    }

    return el("section", { class: "card stack" },
      el("h2", null, t("nav.rate")),
      promptCard(p),
      el("p", { class: "muted small" }, t("rate.by")),
      el("p", { class: "candidate", lang: "pap" }, tr.text),
      flags.length ? el("div", { class: "note warn" }, t("rate.flags") + " ",
        flags.map(function (f) { return el("span", { class: "flag" }, "“" + f.text + "” (" + (f.kind === "rule" ? f.id : f.kind) + ") "); })) : null,
      el("p", { class: "lead" }, t("rate.intro")),
      seg, fixBox, comment, err,
      el("div", { class: "actions" },
        button(t("common.skip"), function () { session.skipped.rate.add(tr.id); render(); }, "ghost"),
        button(t("common.save_next"), submit, "primary")));
  }

  // ------------------------------------------------------------------ board

  function boardItems() {
    var items = [];
    SAMPLE.review.forEach(function (w) {
      var a = answersFor("review", w.id);
      if (a.length >= 2) items.push({ kind: "review", item: w.id, word: w, answers: a });
    });
    SAMPLE.translate.forEach(function (w) {
      var a = answersFor("translate", w.id);
      if (a.length >= 2) items.push({ kind: "translate", item: w.id, word: w, answers: a });
    });
    state.translations.forEach(function (tr) {
      if (ratingsOf(tr.id).length >= 1) items.push({ kind: "sentence", item: tr.id, tr: tr });
    });
    return items;
  }

  function boardCount() {
    return boardItems().filter(function (x) { return !decisionFor(x.kind, x.item); }).length;
  }

  function involved(x) {
    var ids = [];
    if (x.answers) ids = x.answers.map(function (a) { return a.by; });
    if (x.tr) {
      ids = [x.tr.by].concat(ratingsOf(x.tr.id).map(function (r) { return r.by; }));
      ratingsOf(x.tr.id).forEach(function (r) { if (r.fix_translation) ids.push(r.by); });
    }
    return ids.indexOf(state.current) >= 0;
  }

  function badge(status) {
    var map = { agree: ["ok", t("board.agree")], differ: ["bad", t("board.differ")], not_enough: ["muted", t("board.not_enough")] };
    var m = map[status] || map.not_enough;
    return el("span", { class: "badge " + m[0] }, m[1]);
  }

  function verdictText(v) {
    if (!v) return "—";
    if (v.verdict === "correct") return t("review.correct");
    if (v.verdict === "unsure") return t("review.unsure");
    return t("review.wrong") + " → " + v.fix;
  }

  // Radio list of candidate values plus a free box; returns {node, value()}.
  function chooser(name, candidates, preset, lang) {
    var own = el("input", { type: "text", lang: lang || null, "aria-label": t("board.write_own"), placeholder: t("board.write_own") });
    var opts = candidates.map(function (c, i) {
      return el("label", { class: "choice" },
        el("input", { type: "radio", name: name, value: String(i), checked: preset === i }),
        el("span", { lang: lang || null }, c.label));
    });
    var ownRadio = el("input", { type: "radio", name: name, value: "own" });
    own.addEventListener("input", function () { ownRadio.checked = true; });
    return {
      node: el("div", { class: "chooser" }, opts, el("label", { class: "choice" }, ownRadio, own)),
      value: function (root) {
        var picked = root.querySelector("input[name='" + name + "']:checked");
        if (!picked) return null;
        if (picked.value === "own") return { value: normGloss(own.value), from: "board" };
        return candidates[Number(picked.value)];
      }
    };
  }

  function decide(x, outcome, values, note) {
    state.decisions.push({ id: newId("dec"), kind: x.kind, item: x.item, by: state.current, at: now(),
                           outcome: outcome, values: values || null, note: note || "",
                           based_on: (x.answers || []).map(function (a) { return a.id; })
                             .concat(x.tr ? ratingsOf(x.tr.id).map(function (r) { return r.id; }) : []) });
    save();
    session.flash = t("common.saved");
    render();
  }

  function boardWordCard(x) {
    var w = x.word;
    var done = decisionFor(x.kind, x.item);
    var mineToo = involved(x);
    var card = el("article", { class: "board-item" });
    var choosers = {};
    var table = el("table", { class: "cmp" },
      el("thead", null, el("tr", null, el("th", null, ""),
        x.kind === "review" ? el("th", null, t("review.draft")) : null,
        x.answers.map(function (a, i) { return el("th", null, t("board.answer", { i: i + 1 }), el("br"), el("span", { class: "muted small" }, person(a.by).name)); }),
        el("th", null, ""))),
      el("tbody", null, LANGS.map(function (lang) {
        var oc = x.kind === "review" ? reviewOutcome(x.answers, lang, w[lang]) : translateOutcome(x.answers, lang);
        var cands = [];
        if (x.kind === "review" && w[lang]) cands.push({ label: w[lang] + " (" + t("review.draft") + ")", value: w[lang], from: "machine" });
        x.answers.forEach(function (a) {
          var v = x.kind === "review" ? (a.verdicts[lang].verdict === "wrong" ? a.verdicts[lang].fix : "") : (a.unknown ? "" : a.values[lang]);
          if (!v) return;
          var same = cands.filter(function (c) { return senseKey(c.value) === senseKey(v); })[0];
          if (!same) cands.push({ label: v, value: v, from: [a.by] });
          else if (Array.isArray(same.from)) same.from.push(a.by);
        });
        var preset = -1;
        if (oc.status === "agree") {
          cands.forEach(function (c, i) { if (senseKey(c.value) === senseKey(oc.value || "")) preset = i; });
        }
        choosers[lang] = chooser(x.item + "-" + lang, cands, preset, lang);
        return el("tr", null,
          el("th", { scope: "row" }, langName(lang)),
          x.kind === "review" ? el("td", { lang: lang }, w[lang] || "—") : null,
          x.answers.map(function (a) {
            return el("td", { lang: lang }, x.kind === "review" ? verdictText(a.verdicts[lang]) : (a.unknown ? "(" + t("translate.unknown") + ")" : (a.values[lang] || "—")));
          }),
          el("td", null, badge(oc.status)));
      })));
    card.appendChild(el("div", { class: "row-between" },
      el("h3", null, el("span", { lang: "pap" }, w.lemma), " ", el("span", { class: "muted small" }, w.id)),
      done ? el("span", { class: "badge ok" }, t("board.decided") + " · " + person(done.by).name) : null));
    card.appendChild(el("picture", null,
      el("source", { media: "(max-width: 560px)", srcset: w.crop_column, width: w.crop_column_w, height: w.crop_column_h }),
      el("img", { class: "crop-small", src: w.crop, alt: "", width: w.crop_w, height: w.crop_h, loading: "lazy" })));
    card.appendChild(el("div", { class: "table-wrap" }, table));
    var comments = x.answers.filter(function (a) { return a.comment; });
    if (comments.length) card.appendChild(el("ul", { class: "comments" }, comments.map(function (a) { return el("li", null, person(a.by).name + ": " + a.comment); })));
    if (done) {
      card.appendChild(el("p", { class: "muted small" }, done.outcome === "disputed" ? t("board.dispute") : LANGS.map(function (l) {
        return langName(l) + ": " + ((done.values && done.values[l] && done.values[l].value) || "—");
      }).join(" · ")));
      card.appendChild(button(t("board.undo"), function () {
        state.decisions = state.decisions.filter(function (d) { return d.id !== done.id; }); save(); render();
      }, "ghost small"));
      return card;
    }
    if (mineToo) { card.appendChild(el("p", { class: "note" }, t("board.own"))); return card; }
    var decideBox = el("div", { class: "stack" },
      el("p", { class: "muted small" }, t("board.choose_each")),
      LANGS.map(function (lang) { return el("div", { class: "field" }, el("span", { class: "label-strong" }, langName(lang)), choosers[lang].node); }));
    var err = el("p", { class: "error", role: "alert", hidden: true });
    card.appendChild(decideBox);
    card.appendChild(err);
    card.appendChild(el("div", { class: "actions" },
      button(t("board.dispute"), function () { decide(x, "disputed", null, ""); }, "ghost"),
      button(t("board.decide"), function () {
        var values = {};
        var missing = false;
        LANGS.forEach(function (l) { values[l] = choosers[l].value(card); if (!values[l]) missing = true; });
        if (missing) { err.textContent = t("board.need_each"); err.hidden = false; return; }
        decide(x, "reviewed", values, "");
      }, "primary")));
    return card;
  }

  function boardSentenceCard(x) {
    var tr = x.tr;
    var p = promptById(tr.prompt);
    var rs = ratingsOf(tr.id);
    var oc = sentenceOutcome(tr);
    var done = decisionFor("sentence", tr.id);
    var cands = [{ label: tr.text, value: tr.text, translation: tr.id, from: tr.by }];
    rs.forEach(function (r) {
      if (!r.fix_translation) return;
      var f = state.translations.filter(function (z) { return z.id === r.fix_translation; })[0];
      if (f) cands.push({ label: f.text, value: f.text, translation: f.id, from: f.by });
    });
    var ch = chooser(tr.id, cands, oc.status === "agree" ? 0 : -1, "pap");
    var card = el("article", { class: "board-item" },
      el("div", { class: "row-between" }, el("h3", null, p ? p.text : tr.prompt), done ? el("span", { class: "badge ok" }, t("board.decided") + " · " + person(done.by).name) : badge(oc.status)),
      promptCard(p),
      el("p", { class: "candidate", lang: "pap" }, tr.text, " ", el("span", { class: "muted small" }, "— " + person(tr.by).name)),
      tr.flags_kept.length ? el("p", { class: "note warn small" }, t("sent.kept", { n: tr.flags_kept.length }) + " " +
        tr.flags_kept.map(function (f) { return "“" + f.text + "” (" + f.id + ")"; }).join(", ")) : null,
      el("ul", { class: "comments" }, rs.map(function (r) {
        return el("li", null, person(r.by).name + ": " + (r.verdict === "good" ? t("rate.good") : t("rate.fix")) + (r.comment ? " — " + r.comment : ""));
      })));
    if (done) {
      card.appendChild(el("p", { class: "muted small" }, done.outcome === "disputed" ? t("board.dispute") : (done.values && done.values.pap ? done.values.pap.value : "")));
      card.appendChild(button(t("board.undo"), function () {
        state.decisions = state.decisions.filter(function (d) { return d.id !== done.id; }); save(); render();
      }, "ghost small"));
      return card;
    }
    if (involved(x)) { card.appendChild(el("p", { class: "note" }, t("board.own"))); return card; }
    var err = el("p", { class: "error", role: "alert", hidden: true });
    card.appendChild(ch.node);
    card.appendChild(err);
    card.appendChild(el("div", { class: "actions" },
      button(t("board.dispute"), function () { decide(x, "disputed", null, ""); }, "ghost"),
      button(oc.status === "agree" ? t("board.confirm") : t("board.decide"), function () {
        var v = ch.value(card);
        if (!v || !v.value) { err.textContent = t("board.need_each"); err.hidden = false; return; }
        if (v.from === "board") {
          var lint = summarise(window.PapChecker.check(v.value, P, {}));
          v.flags = lint;
        }
        decide(x, "reviewed", { pap: v }, "");
      }, "primary")));
    return card;
  }

  function viewBoard() {
    if (!me().board) return el("section", { class: "card" }, el("p", null, t("board.not_member")));
    var items = boardItems();
    var open = items.filter(function (x) { return !decisionFor(x.kind, x.item); });
    var closed = items.filter(function (x) { return decisionFor(x.kind, x.item); });
    var section = function (kind, title) {
      var xs = open.filter(function (x) { return x.kind === kind; }).concat(closed.filter(function (x) { return x.kind === kind; }));
      if (!xs.length) return null;
      return el("section", { class: "stack" }, el("h3", { class: "section-title" }, title),
        xs.map(function (x) { return kind === "sentence" ? boardSentenceCard(x) : boardWordCard(x); }));
    };
    return el("div", { class: "stack" },
      el("section", { class: "card" }, el("h2", null, t("nav.board")), el("p", null, t("board.intro")),
        items.length ? null : el("p", { class: "muted" }, t("board.empty"))),
      section("review", t("board.words_review")),
      section("translate", t("board.words_translate")),
      section("sentence", t("board.sentences")));
  }

  // ----------------------------------------------------------------- export

  // What a sync bot would write to the repo for each board decision.
  function pullRequestPreview() {
    var words = [], pairs = [];
    state.decisions.forEach(function (d) {
      var board = person(d.by);
      var reviewer = board.github || ("NEEDS-GITHUB-USERNAME(" + board.handle + ")");
      if (d.kind === "review" || d.kind === "translate") {
        var w = wordById(d.item);
        if (!w) return;
        if (d.outcome === "disputed") {
          words.push({ id: w.id, lemma: w.lemma, en: w.en, nl: w.nl, es: w.es, translated_by: w.translated_by,
                       status: "disputed", reviewed_by: "", notes: "Contribution tool: the two answers differ; see decision " + d.id });
          return;
        }
        var by = [], machineKept = [], changed = [];
        LANGS.forEach(function (l) {
          var v = d.values[l];
          if (!v || !v.value) return;
          if (v.from === "machine") machineKept.push(l.toUpperCase());
          else {
            changed.push(l.toUpperCase());
            var hs = v.from === "board" ? [board.handle] : [].concat(v.from).map(function (id) { return person(id).handle; });
            hs.forEach(function (h) { if (by.indexOf(h) < 0) by.push(h); });
          }
        });
        if (machineKept.length) by.push("machine");
        var notes = [];
        if (machineKept.length && changed.length) notes.push(machineKept.join(", ") + " confirmed as machine draft; " + changed.join(", ") + " corrected");
        notes.push("contribution tool " + d.id);
        words.push({ id: w.id, lemma: w.lemma,
                     en: d.values.en ? d.values.en.value : "", nl: d.values.nl ? d.values.nl.value : "", es: d.values.es ? d.values.es.value : "",
                     translated_by: by.join("; "), status: "reviewed", reviewed_by: reviewer, notes: notes.join("; ") });
      } else if (d.kind === "sentence") {
        var tr = state.translations.filter(function (z) { return z.id === d.item; })[0];
        if (!tr) return;
        var p = promptById(tr.prompt);
        var v = d.values && d.values.pap;
        var authorId = v ? (v.from === "board" ? d.by : v.from) : tr.by;
        var checked = ratingsOf(tr.id).filter(function (r) { return r.verdict === "good"; }).map(function (r) { return person(r.by).handle; });
        pairs.push({ id: "par-NEW", prompt_id: tr.prompt, prompt_lang: p ? p.lang : "", pap: v ? v.value : tr.text,
                     translated_by: person(authorId).handle, checked_by: checked.join("; "),
                     status: d.outcome === "disputed" ? "disputed" : "reviewed", reviewed_by: d.outcome === "disputed" ? "" : reviewer,
                     licence: "CC0-1.0", split: "(assigned by prompt)", notes: "contribution tool " + d.id });
      }
    });
    return { words: words, pairs: pairs };
  }

  function exportObject() {
    return {
      format: FORMAT,
      exported_at: now(),
      tool: { kind: "prototype", data_built_from_commit: SAMPLE.built_from_commit },
      licences: { words: "CC-BY-4.0", sentences: "CC0-1.0 (proposed, not decided)" },
      people: state.people,
      answers: state.answers,
      translations: state.translations,
      ratings: state.ratings,
      decisions: state.decisions,
      pull_request_preview: pullRequestPreview()
    };
  }

  function download() {
    var blob = new Blob([JSON.stringify(exportObject(), null, 2) + "\n"], { type: "application/json" });
    var a = el("a", { href: URL.createObjectURL(blob), download: "papiamento-contributions-" + now().slice(0, 10) + ".json" });
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  function importFile(file) {
    var reader = new FileReader();
    reader.onload = function () {
      var added = 0;
      try {
        var data = JSON.parse(reader.result);
        if (!data || data.format !== FORMAT) throw new Error("not a prototype export");
        ["people", "answers", "translations", "ratings", "decisions"].forEach(function (k) {
          var have = new Set(state[k].map(function (x) { return x.id; }));
          (data[k] || []).forEach(function (x) { if (x && x.id && !have.has(x.id)) { state[k].push(x); added++; } });
        });
        save();
        session.flash = t("export.imported", { n: added });
      } catch (e) {
        session.flash = "Could not read that file: " + e.message;
      }
      render();
    };
    reader.readAsText(file);
  }

  function tsvTable(rows, cols) {
    if (!rows.length) return el("p", { class: "muted small" }, t("export.none"));
    return el("div", { class: "table-wrap" }, el("table", { class: "tsv" },
      el("thead", null, el("tr", null, cols.map(function (c) { return el("th", null, c); }))),
      el("tbody", null, rows.map(function (r) { return el("tr", null, cols.map(function (c) { return el("td", null, r[c] || ""); })); }))));
  }

  function viewExport() {
    var pr = pullRequestPreview();
    var file = el("input", { type: "file", accept: "application/json,.json", id: "imp",
      onchange: function (e) { if (e.target.files[0]) importFile(e.target.files[0]); } });
    return el("div", { class: "stack" },
      el("section", { class: "card stack" },
        el("h2", null, t("export.title")),
        el("p", null, t("export.intro")),
        el("p", { class: "muted" }, t("export.counts", { a: state.answers.length, t: state.translations.length, r: state.ratings.length, d: state.decisions.length })),
        el("div", { class: "actions left" },
          button(t("export.download"), download, "primary"),
          el("label", { class: "btn", for: "imp" }, t("export.import")), file),
        el("p", { class: "muted small" }, t("export.import_note"))),
      el("section", { class: "card stack" },
        el("h2", null, t("export.pr_title")),
        el("p", null, t("export.pr_note")),
        el("h3", null, "lexicon/words/<L>/words.tsv"),
        tsvTable(pr.words, ["id", "lemma", "en", "nl", "es", "translated_by", "status", "reviewed_by", "notes"]),
        el("h3", null, "corpus/parallel/pairs.tsv (proposed table)"),
        tsvTable(pr.pairs, ["id", "prompt_id", "pap", "translated_by", "checked_by", "status", "reviewed_by", "licence", "notes"]),
        el("h3", null, "Credits"),
        el("p", { class: "small" }, state.people.map(function (x) { return creditName(x) + " (" + x.handle + ")"; }).join(", ") || "—")),
      el("section", { class: "card stack danger" },
        button(t("export.clear"), function () {
          if (!window.confirm(t("export.clear_confirm"))) return;
          state = blank(); save();
          session.skipped = { review: new Set(), translate: new Set(), sentences: new Set(), rate: new Set() };
          go("person");
        }, "danger")));
  }

  function viewAbout() {
    return el("section", { class: "card stack prose" },
      el("h2", null, t("about.title")),
      el("p", null, "This is a clickable prototype of the contribution tool described in ", el("a", { href: "DESIGN.md" }, "DESIGN.md"),
        " (board card P2-09). It runs from a local file, sends nothing anywhere and stores answers only in this browser."),
      el("ul", null,
        el("li", null, "Check translations: " + SAMPLE.review.length + " machine-drafted rows from lexicon/words/, shown with a crop of the printed AB 2018 word-list page."),
        el("li", null, "Translate words: " + SAMPLE.translate.length + " rows with no translation. Order: " + SAMPLE.translate_order + "."),
        el("li", null, "Translate sentences: " + SAMPLE.prompts.length + " English and Spanish prompts written for this prototype only. No Papiamento is shown or prefilled."),
        el("li", null, "Live checks: " + CHECKS.rules.length + " rules from rules/rules.jsonl, " + CHECKS.barbarismos.length + " barbarismos, " +
          CHECKS.variants.length + " Curaçao-Aruba pairs and the AB 2018 word list."),
        el("li", null, "Data built from repository commit " + SAMPLE.built_from_commit + " by tools/contribute/build_sample.py.")),
      el("p", null, "Papiamento interface text is a machine draft (status draft in ui-strings.tsv). Every word in it is an AB 2018 headword, and no repo check fires on it, but a teacher must check its grammar and wording."),
      el("p", null, "Licences shown here are proposals: word translations CC BY 4.0 like the rest of the dataset; sentences CC0 1.0 so they can go to Common Voice. Victor decides."));
  }

  // ------------------------------------------------------------------- boot

  window.addEventListener("hashchange", render);
  render();
})();

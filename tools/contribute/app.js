// Contribution tool for ARUBAGOV33/papiamento (board card P2-09).
//
// Three modes (check machine translations, translate words, translate
// sentences), rating, a review-board queue, credits and an account page.
// Phone first: one item per screen with a progress bar, a full-width primary
// button and a feedback sheet (the Duolingo lesson pattern, without its
// cartoon look). On a laptop a sidebar replaces the tab bar and word tasks
// use two columns. See DESIGN.md.
//
// Two backends, chosen by config.js:
// - demo (the prototype): everything stays in this browser (localStorage) and
//   can be exported as JSON. No network calls.
// - live (the published site): sign-in by emailed code and the database in
//   Supabase, through supabase-js. The database's access rules
//   (supabase/001_contribute.sql) decide what each person may read or write;
//   this file only shows it.

(function () {
  "use strict";

  if (!window.CONTRIB_STRINGS || !window.CONTRIB_SAMPLE || !window.CONTRIB_CHECKS || !window.PapChecker) {
    var root = document.getElementById("app");
    if (root) root.innerHTML = '<div class="fatal"><h1>The sample data did not load</h1>' +
      '<p>Run <code>python3 tools/contribute/build_sample.py</code> from the repository root, then reload this page.</p></div>';
    return;
  }

  var STR = window.CONTRIB_STRINGS;
  var SAMPLE = window.CONTRIB_SAMPLE;
  var CHECKS = window.CONTRIB_CHECKS;
  var Checker = window.PapChecker;
  var KEY = "pap-contrib-prototype-v1";
  var FORMAT = "pap-contrib-prototype/1";
  var LANGS = ["en", "nl", "es"];
  var DAILY_GOAL = 10;
  var TASKS = { review: 1, translate: 1, sentences: 1, rate: 1 };
  var P = Checker.prepare(CHECKS);
  var SIM_DELAY = { normal: 450, slow: 1800, fail: 1000 };
  var CONFIG = window.CONTRIB_CONFIG || { mode: "demo" };
  var LIVE = CONFIG.mode === "live";
  var CONSENT_VERSION = "tool-2026-10";   // profiles.consent_version: the consent text people agree to
  var PREFS_KEY = "pap-contrib-prefs-v1"; // live: only the screen language and the checker switch stay in the browser
  var RESEND_SECONDS = 60;

  var storageBlocked = false;
  var state = load();
  var session = freshSession();

  // Live backend state. status: loading, error, signed_out, needs_profile, ready.
  var live = {
    status: "loading", error: null, client: null, user: null,
    qs: null,                       // queue_state(): ids and counts only
    closed: { review: new Set(), translate: new Set() },
    promptN: {},                    // prompt id -> number of sentences written for it
    rateList: [],                   // rate_queue(): sentences to rate, without authors
    credits: null, creditsError: false
  };

  function freshSession() {
    return {
      skipped: { review: new Set(), translate: new Set(), sentences: new Set(), rate: new Set() },
      stayOn: null,
      draft: {},
      onb: { step: 0, email: "", profile: null },
      boardTab: "open",
      boardSel: null
    };
  }

  // ---------------------------------------------------------------- storage

  function blank() {
    return { format: FORMAT, people: [], current: null, ui_lang: "en", show_unknown: true,
             answers: [], translations: [], ratings: [], decisions: [] };
  }

  function load() {
    try {
      window.localStorage.setItem(KEY + "-probe", "1");
      window.localStorage.removeItem(KEY + "-probe");
      if (LIVE) {
        var prefs = JSON.parse(window.localStorage.getItem(PREFS_KEY) || "{}") || {};
        return Object.assign(blank(), { ui_lang: prefs.ui_lang === "pap" ? "pap" : "en", show_unknown: prefs.show_unknown !== false });
      }
      var raw = window.localStorage.getItem(KEY);
      if (raw) {
        var s = JSON.parse(raw);
        if (s && s.format === FORMAT) return Object.assign(blank(), s);
      }
    } catch (e) { storageBlocked = true; }
    return blank();
  }

  // Storage can be blocked (private mode, full disk). Keep working in memory
  // and tell the person to export before closing the tab. Live, answers are
  // in the database: only the two preferences are stored here.
  function save() {
    try {
      if (LIVE) window.localStorage.setItem(PREFS_KEY, JSON.stringify({ ui_lang: state.ui_lang, show_unknown: state.show_unknown }));
      else window.localStorage.setItem(KEY, JSON.stringify(state));
      storageBlocked = false;
    } catch (e) { storageBlocked = true; }
  }

  function newId(prefix) {
    return prefix + "-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  }

  function now() { return new Date().toISOString(); }
  function day(iso) { return (iso || "").slice(0, 10); }
  function today() { return day(new Date().toISOString()); }

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
        else if (k === "value" || k === "checked" || k === "disabled") props[k] = v;
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

  var ICONS = {
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.6-2.4 2.1-2.4 3.6"/><path d="M12 17h.01"/>',
    chevron: '<path d="M9 6l6 6-6 6"/>',
    back: '<path d="M15 6l-6 6 6 6"/>',
    book: '<path d="M4 4h11a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3z"/><path d="M4 17a3 3 0 0 1 3-3h11"/>',
    languages: '<path d="M4 5h9M8.5 3v2M6 5c.5 3 2.5 5.5 5 7M11 5c-.8 3.5-3 6-6 7.5"/><path d="M13 21l4-9 4 9M14.5 18h5"/>',
    chat: '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>',
    star: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>',
    shield: '<path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 14.2a6.5 6.5 0 0 1 3 5.8"/>',
    home: '<path d="M4 10.5L12 4l8 6.5V20h-5.5v-6h-5v6H4z"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    upload: '<path d="M12 16V5M7 10l5-5 5 5M5 20h14"/>',
    trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    wifioff: '<path d="M3 3l18 18"/><path d="M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 5-2.7M14.5 10.4A10 10 0 0 1 19 13M2 9.5a15 15 0 0 1 4.5-2.8M10.7 6.1A15 15 0 0 1 22 9.5"/><path d="M12 20h.01"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    alert: '<path d="M12 3.5l9 16.5H3z"/><path d="M12 10v4M12 17h.01"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    school: '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2.5 9 2.5 12 0v-5"/>',
    pen: '<path d="M4 20l4-1L19 8l-3-3L5 16z"/><path d="M14 7l3 3"/>',
    calendar: '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9s-1.3 6.5-3.8 9c-2.5-2.5-3.8-5.5-3.8-9S9.5 5.5 12 3z"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    skip: '<path d="M5 6l7 6-7 6M13 6l7 6-7 6"/>',
    target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><path d="M12 12h.01"/>',
    more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'
  };

  function icon(name, cls) {
    var span = el("span", { class: "icon " + (cls || ""), "aria-hidden": "true" });
    span.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + ICONS[name] + "</svg>";
    return span;
  }

  function brandMark() {
    var span = el("span", { class: "brand-mark", "aria-hidden": "true" });
    span.innerHTML = '<svg viewBox="0 0 32 32"><rect width="32" height="32" rx="9" fill="#1663b8"/><rect x="6" y="19" width="20" height="2.6" rx="1.3" fill="#f9d616"/><rect x="6" y="23.6" width="20" height="2.6" rx="1.3" fill="#f9d616"/><path d="M11.5 16.5V7.5h5a3.5 3.5 0 0 1 0 7h-5" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    return span;
  }

  function initials(name) {
    var parts = (name || "?").trim().split(/\s+/);
    return ((parts[0] || "?")[0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
  }

  function avatar(p) { return el("span", { class: "avatar" + (p.board ? " board" : ""), "aria-hidden": "true" }, initials(p.name)); }

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

  // Live, a contributor cannot read other people's answers: queue_state()
  // lists the words closed to them (two answers, a decision, or their own).
  function openForMe(kind, item) {
    if (LIVE) return !live.closed[kind].has(item);
    var ans = answersFor(kind, item);
    return ans.length < 2 && !decisionFor(kind, item) &&
      !ans.some(function (a) { return a.by === state.current; });
  }

  function reviewQueue() { return SAMPLE.review.filter(function (w) { return openForMe("review", w.id); }); }
  function translateQueue() { return SAMPLE.translate.filter(function (w) { return openForMe("translate", w.id); }); }

  function translationsOf(promptId) {
    return state.translations.filter(function (tr) { return tr.prompt === promptId; });
  }

  function sentencesFor(promptId) {
    return LIVE ? live.promptN[promptId] || 0 : translationsOf(promptId).length;
  }

  function sentenceQueue() {
    var mine = new Set(state.translations.filter(function (tr) { return tr.by === state.current; }).map(function (tr) { return tr.prompt; }));
    return SAMPLE.prompts.filter(function (p) { return !mine.has(p.id); })
      .sort(function (a, b) { return sentencesFor(a.id) - sentencesFor(b.id); });
  }

  function ratingsOf(trId) {
    return state.ratings.filter(function (r) { return r.translation === trId; });
  }

  // Live: rate_queue() returns other people's sentences without their authors.
  function rateQueue() {
    if (LIVE) {
      var rated = new Set(state.ratings.filter(function (r) { return r.by === state.current; }).map(function (r) { return r.translation; }));
      return live.rateList.filter(function (tr) { return !rated.has(tr.id); });
    }
    return state.translations.filter(function (tr) {
      var rs = ratingsOf(tr.id);
      return tr.by !== state.current && rs.length < 2 && !decisionFor("sentence", tr.id) &&
        !rs.some(function (r) { return r.by === state.current; });
    });
  }

  function rateCount() { return LIVE ? Math.max(rateQueue().length, (live.qs && live.qs.rate_open) || 0) : rateQueue().length; }

  function promptById(id) {
    for (var i = 0; i < SAMPLE.prompts.length; i++) if (SAMPLE.prompts[i].id === id) return SAMPLE.prompts[i];
    return null;
  }

  var WORDS = {};
  SAMPLE.review.concat(SAMPLE.translate).forEach(function (w) { WORDS[w.id] = w; });
  function wordById(id) { return WORDS[id] || null; }

  function translationById(id) {
    for (var i = 0; i < state.translations.length; i++) if (state.translations[i].id === id) return state.translations[i];
    return null;
  }

  // ------------------------------------------------------------ live: reading
  // Rows come from the database through the access rules. Every value is
  // shaped here before a screen uses it, and screens only ever set text, never
  // HTML, so nothing in a row can change the page.

  function str(v) { return typeof v === "string" ? v : ""; }

  function fromAnswer(r) {
    var b = r.body && typeof r.body === "object" ? r.body : {};
    var a = { id: r.id, kind: r.kind, item: r.ref, by: r.person_id, at: r.created_at, comment: str(r.comment) };
    if (r.kind === "review") {
      a.verdicts = {};
      LANGS.forEach(function (l) {
        var v = (b.verdicts && b.verdicts[l]) || {};
        a.verdicts[l] = { verdict: ["correct", "wrong", "unsure"].indexOf(v.verdict) >= 0 ? v.verdict : "unsure", fix: str(v.fix) };
      });
    } else {
      a.unknown = b.unknown === true;
      a.values = {};
      LANGS.forEach(function (l) { a.values[l] = str(b.values && b.values[l]); });
    }
    return a;
  }

  function fromFlags(list) {
    return (Array.isArray(list) ? list : []).filter(function (f) { return f && typeof f === "object"; }).map(function (f) {
      return { id: str(f.id), text: str(f.text), fixes: Array.isArray(f.fixes) ? f.fixes.map(String) : [] };
    });
  }

  function fromTranslation(r) {
    return { id: r.id, prompt: r.prompt_ref, by: r.person_id, at: r.created_at, text: str(r.text), flags_kept: fromFlags(r.flags_kept), fix_of: r.fix_of };
  }

  function fromRating(r) {
    return { id: r.id, translation: r.translation_id, by: r.person_id, at: r.created_at, verdict: r.verdict,
             fix_translation: r.fix_translation_id, comment: str(r.comment) };
  }

  // Decision values as the sync job reads them (tools/apply_contributions.py):
  // words {en: {value, from}, ...}, from = "machine", "board" or person ids;
  // sentences {text, from, translation_id}.
  function fromDecision(r) {
    var v = r.value && typeof r.value === "object" ? r.value : null;
    var values = null;
    if (v && r.kind === "sentence") values = { pap: { value: str(v.text), from: v.from, translation: v.translation_id || null } };
    else if (v) {
      values = {};
      LANGS.forEach(function (l) { if (v[l] && typeof v[l] === "object") values[l] = { value: str(v[l].value), from: v[l].from }; });
    }
    return { id: r.id, kind: r.kind, item: r.kind === "sentence" ? r.translation_id : r.word_ref, by: r.board_id, at: r.created_at,
             outcome: r.outcome, values: values, note: str(r.note), exported_in: r.exported_in || null };
  }

  function toDecisionValue(kind, values) {
    if (!values) return null;
    if (kind === "sentence") {
      var v = values.pap;
      return { text: v.value, from: v.from, translation_id: v.translation || null, flags: v.flags || [] };
    }
    var out = {};
    LANGS.forEach(function (l) { if (values[l]) out[l] = { value: values[l].value, from: values[l].from }; });
    return out;
  }

  function fromProfile(r) {
    var mine = live.user && r.id === live.user.id;
    return { id: r.id, name: str(r.credit_name) || r.handle, handle: r.handle, role: r.occupation, school: str(r.school),
             credit: r.credit !== false, github: str(r.github), db_role: r.role, consent_version: r.consent_version,
             // Whether I do the board's work comes from the database (maintainers only while the board is small).
             board: mine ? !!(live.qs && live.qs.board) : r.role === "board" };
  }

  function db(query) {
    return Promise.resolve(query).then(function (res) { if (res.error) throw res.error; return res.data; });
  }

  // The API returns at most 1000 rows per request.
  function selectAll(table, filter) {
    var rows = [];
    function page(from) {
      var q = live.client.from(table).select("*").order(table === "profiles" ? "handle" : "id").range(from, from + 999);
      if (filter) q = filter(q);
      return db(q).then(function (data) { rows = rows.concat(data || []); return data && data.length === 1000 ? page(from + 1000) : rows; });
    }
    return page(0);
  }

  function loadQueue() {
    return db(live.client.rpc("queue_state")).then(function (qs) {
      qs = qs || {};
      live.qs = qs;
      live.closed = { review: new Set(qs.review_closed || []), translate: new Set(qs.translate_closed || []) };
      live.promptN = {};
      (qs.prompts || []).forEach(function (p) { live.promptN[p.ref] = p.n; });
    });
  }

  function loadRateList() {
    return db(live.client.rpc("rate_queue", { p_limit: 50 })).then(function (rows) {
      live.rateList = (rows || []).map(function (r) {
        return { id: r.id, prompt: r.prompt_ref, text: str(r.text), flags_kept: fromFlags(r.flags_kept), by: null };
      });
    });
  }

  // Everything the screens need. A contributor gets their own rows; the board
  // (as the database decides) gets everyone's, without emails.
  function loadData() {
    return loadQueue().then(function () {
      var uid = live.user.id;
      var all = !!live.qs.board;
      var mine = function (q) { return q.eq("person_id", uid); };
      return Promise.all([
        selectAll("profiles", all ? null : function (q) { return q.eq("id", uid); }),
        selectAll("answers", all ? null : mine),
        selectAll("translations", all ? null : mine),
        selectAll("ratings", all ? null : mine),
        all ? selectAll("decisions") : [],
        loadRateList()
      ]);
    }).then(function (r) {
      var people = r[0].map(fromProfile);
      if (!people.some(function (p) { return p.id === live.user.id; })) {
        live.status = "needs_profile";
        state.people = []; state.current = null;
        return;
      }
      state.people = people;
      state.current = live.user.id;
      state.answers = r[1].map(fromAnswer);
      state.translations = r[2].map(fromTranslation);
      state.ratings = r[3].map(fromRating);
      state.decisions = r[4].map(fromDecision);
      live.status = "ready";
    });
  }

  function loadCredits() {
    live.creditsError = false;
    live.creditsLoading = true;
    return db(live.client.rpc("credits")).then(function (rows) {
      live.credits = rows || []; live.creditsAt = Date.now();
    }, function () { live.creditsError = true; }).then(function () {
      live.creditsLoading = false;
      if (route().name === "credits") render();
    });
  }

  // After a write the database has accepted: reload, but a failed reload must
  // not turn the saved answer into an error.
  function refreshAfterWrite() {
    return loadData().catch(function () {});
  }

  function loadScript(src) {
    if (window.supabase && window.supabase.createClient) return Promise.resolve();
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.onload = function () { window.supabase && window.supabase.createClient ? resolve() : reject(new Error("supabase-js")); };
      s.onerror = function () { s.remove(); reject(new Error("supabase-js")); };
      document.head.appendChild(s);
    });
  }

  function startLive() {
    live.status = "loading"; live.error = null;
    render();
    if (!CONFIG.supabaseUrl || !CONFIG.supabaseKey || !CONFIG.supabaseJs) { live.status = "error"; live.error = "config"; render(); return; }
    loadScript(CONFIG.supabaseJs).then(function () {
      if (!live.client) {
        live.client = window.supabase.createClient(CONFIG.supabaseUrl, CONFIG.supabaseKey, {
          auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false, storageKey: "pap-contrib-auth" }
        });
        live.client.auth.onAuthStateChange(function (event) { if (event === "SIGNED_OUT") signedOut(); });
      }
      return live.client.auth.getSession();
    }).then(function (res) {
      var s = res && res.data && res.data.session;
      if (!s) { live.status = "signed_out"; render(); return; }
      live.user = s.user;
      return loadData().then(function () {
        if (live.status === "needs_profile") session.onb.step = 3;
        render();
      });
    }).catch(function () {
      live.status = "error";
      live.error = navigator.onLine ? "load" : "offline";
      render();
    });
  }

  function signedOut() {
    if (live.status === "signed_out" && !live.user) return;
    live.user = null; live.qs = null; live.rateList = []; live.credits = null;
    live.closed = { review: new Set(), translate: new Set() }; live.promptN = {};
    var keep = { ui_lang: state.ui_lang, show_unknown: state.show_unknown };
    state = Object.assign(blank(), keep);
    session = freshSession();
    live.status = "signed_out";
    go("onboarding");
  }

  function signOut(btn) {
    var restore = busy(btn, t("common.loading"));
    live.client.auth.signOut({ scope: "local" }).then(function () { restore(); signedOut(); }, function () { restore(); signedOut(); });
  }

  // --------------------------------------------------------------- writing
  // Demo: change the state in this browser. Live: write to the database
  // first; the screens change only once it has accepted (persist() reloads).

  // Someone else gave the second answer or rating first, or the board decided.
  function tooLate(e) { return !!e && (e.hint === "full" || e.hint === "decided" || e.code === "23505"); }

  function after(result, fn) { return result && typeof result.then === "function" ? result.then(fn) : fn(); }

  function saveAnswer(kind, item, body, comment) {
    if (!LIVE) {
      state.answers.push(Object.assign({ id: newId("ans"), kind: kind, item: item, by: state.current, at: now() }, body, { comment: comment }));
      return;
    }
    return db(live.client.from("answers").insert({ kind: kind, ref: item, body: body, comment: comment }).select().single())
      .then(function (row) { state.answers.push(fromAnswer(row)); live.closed[kind].add(item); },
            function (err) { if (tooLate(err)) live.closed[kind].add(item); throw err; });
  }

  function saveTranslation(promptId, text, kept) {
    if (!LIVE) {
      state.translations.push({ id: newId("tr"), prompt: promptId, by: state.current, at: now(), text: text, flags_kept: kept, fix_of: null });
      return;
    }
    return db(live.client.from("translations").insert({ prompt_ref: promptId, text: text, flags_kept: kept }).select().single())
      .then(function (row) { state.translations.push(fromTranslation(row)); live.promptN[promptId] = (live.promptN[promptId] || 0) + 1; });
  }

  // A rating and its corrected version are saved together (rate_sentence):
  // if the rating is refused, the correction is not kept either.
  function saveRating(tr, verdict, fixText, kept, comment) {
    if (!LIVE) {
      var fixId = null;
      if (verdict === "fix") {
        fixId = newId("tr");
        state.translations.push({ id: fixId, prompt: tr.prompt, by: state.current, at: now(), text: fixText, flags_kept: kept, fix_of: tr.id });
      }
      state.ratings.push({ id: newId("rat"), translation: tr.id, by: state.current, at: now(), verdict: verdict, fix_translation: fixId, comment: comment });
      return;
    }
    return db(live.client.rpc("rate_sentence", { p_translation: tr.id, p_verdict: verdict, p_fix_text: verdict === "fix" ? fixText : null,
                                                  p_fix_flags: kept || [], p_comment: comment }))
      .then(function (id) {
        state.ratings.push({ id: id, translation: tr.id, by: state.current, at: now(), verdict: verdict, fix_translation: null, comment: comment });
      }, function (err) {
        if (tooLate(err)) live.rateList = live.rateList.filter(function (x) { return x.id !== tr.id; });
        throw err;
      });
  }

  function saveDecision(x, outcome, values) {
    if (!LIVE) {
      state.decisions.push({ id: newId("dec"), kind: x.kind, item: x.item, by: state.current, at: now(),
                             outcome: outcome, values: values || null, note: "",
                             based_on: (x.answers || []).map(function (a) { return a.id; })
                               .concat(x.tr ? ratingsOf(x.tr.id).map(function (r) { return r.id; }) : []) });
      return;
    }
    var row = { kind: x.kind, outcome: outcome, value: toDecisionValue(x.kind, values), note: "" };
    if (x.kind === "sentence") row.translation_id = x.item; else row.word_ref = x.item;
    return db(live.client.from("decisions").insert(row).select().single())
      .then(function (r) { state.decisions.push(fromDecision(r)); });
  }

  function undoDecision(d) {
    if (!LIVE) {
      state.decisions = state.decisions.filter(function (x) { return x.id !== d.id; });
      save();
      return Promise.resolve();
    }
    // The access rules delete only the board member's own decision before it is exported.
    return db(live.client.from("decisions").delete().eq("id", d.id).select()).then(function (rows) {
      if (!rows || !rows.length) throw { code: "42501" };
      state.decisions = state.decisions.filter(function (x) { return x.id !== d.id; });
      return refreshAfterWrite();
    });
  }

  // My activity: every record I made, with its date.
  function myRecords(pid) {
    var id = pid || state.current;
    var mine = function (x) { return x.by === id; };
    return {
      review: state.answers.filter(function (a) { return a.kind === "review" && mine(a); }),
      translate: state.answers.filter(function (a) { return a.kind === "translate" && mine(a); }),
      sentences: state.translations.filter(mine),
      ratings: state.ratings.filter(mine),
      decisions: state.decisions.filter(mine)
    };
  }

  function myCount(pid) {
    var r = myRecords(pid);
    return r.review.length + r.translate.length + r.sentences.length + r.ratings.length + r.decisions.length;
  }

  function myDates() {
    var r = myRecords();
    return [].concat(r.review, r.translate, r.sentences, r.ratings, r.decisions).map(function (x) { return day(x.at); });
  }

  function daysInARow() {
    var set = new Set(myDates());
    var d = new Date(), n = 0;
    if (!set.has(today())) d.setDate(d.getDate() - 1);
    while (set.has(day(d.toISOString()))) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }

  // -------------------------------------------------------------- agreement

  function normGloss(s) {
    return Checker.normalise(s).replace(/\s*;\s*/g, "; ").replace(/;\s*$/, "");
  }

  function senseKey(s) {
    return normGloss(s).toLowerCase().split("; ").filter(Boolean).sort().join("|");
  }

  function reviewOutcome(answers, lang, draft) {
    var decided = answers.map(function (a) { return a.verdicts[lang]; })
      .filter(function (v) { return v.verdict !== "unsure"; });
    if (decided.length < 2) return { status: "not_enough" };
    if (decided.every(function (v) { return v.verdict === "correct"; })) return { status: "agree", value: draft };
    if (decided.every(function (v) { return v.verdict === "wrong"; })) {
      var keys = decided.map(function (v) { return senseKey(v.fix); });
      if (keys.every(function (k) { return k === keys[0]; })) return { status: "agree", value: decided[0].fix };
    }
    return { status: "differ" };
  }

  function translateOutcome(answers, lang) {
    var vals = answers.map(function (a) { return a.unknown ? "" : a.values[lang]; }).filter(Boolean);
    if (vals.length === 0) return { status: "agree", value: "" };
    if (vals.length < 2) return { status: "not_enough" };
    var keys = vals.map(senseKey);
    if (keys.every(function (k) { return k === keys[0]; })) return { status: "agree", value: vals[0] };
    return { status: "differ" };
  }

  function sentenceOutcome(tr) {
    var rs = ratingsOf(tr.id);
    if (!rs.length) return { status: "not_enough" };
    if (rs.every(function (r) { return r.verdict === "good"; })) return { status: "agree" };
    return { status: "differ" };
  }

  function itemOutcome(x) {
    if (x.kind === "sentence") return sentenceOutcome(x.tr).status;
    var st = LANGS.map(function (l) {
      return x.kind === "review" ? reviewOutcome(x.answers, l, x.word[l]).status : translateOutcome(x.answers, l).status;
    });
    if (st.indexOf("differ") >= 0) return "differ";
    if (st.indexOf("not_enough") >= 0) return "not_enough";
    return "agree";
  }

  // ---------------------------------------------------------------- routing

  function route() {
    var h = (window.location.hash || "#/home").replace(/^#\//, "");
    var parts = h.split("/");
    return { name: parts[0] || "home", args: parts.slice(1).map(decodeURIComponent) };
  }

  function go(path) {
    if (window.location.hash === "#/" + path) render();
    else window.location.hash = "#/" + path;
  }

  var VIEWS = {
    home: viewHome, review: viewReview, translate: viewTranslate, sentences: viewSentences, rate: viewRate,
    board: viewBoard, credits: viewCredits, account: viewAccount, onboarding: viewOnboarding
  };

  // ------------------------------------------------------------------ shell

  function render() {
    if (LIVE && (live.status === "loading" || live.status === "error")) { renderGate(); return; }
    var r = route();
    if (!me() && r.name !== "onboarding") { go("onboarding"); return; }
    if (LIVE && me() && r.name === "onboarding") { go("home"); return; }
    if (r.name === "export" || r.name === "about") r.name = "account";
    if (!VIEWS[r.name]) r.name = "home";
    document.documentElement.lang = state.ui_lang === "pap" ? "pap" : "en";
    document.title = LIVE ? t("app.title") : t("app.title") + " (prototype)";
    var app = document.getElementById("app");
    app.innerHTML = "";
    var mode = r.name === "onboarding" ? "onb" : TASKS[r.name] ? "task" : "page";
    document.body.className = "mode-" + mode;
    if (mode === "page") {
      app.appendChild(sidebar(r.name));
      var col = el("div", { class: "page-col" }, topbar(r.name), banners(),
        el("main", { id: "main", class: "page" }, VIEWS[r.name](r.args)));
      app.appendChild(col);
      app.appendChild(tabbar(r.name));
    } else if (mode === "task") {
      app.appendChild(el("div", { class: "task-col" }, banners(), VIEWS[r.name](r.args)));
    } else {
      app.appendChild(el("div", { class: "onb-col" }, banners(), VIEWS.onboarding()));
    }
    var focus = app.querySelector("[data-autofocus]");
    if (focus) focus.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  // Live: the whole screen while the tool connects, or when it cannot.
  function renderGate() {
    document.documentElement.lang = state.ui_lang === "pap" ? "pap" : "en";
    document.title = t("app.title");
    document.body.className = "mode-onb";
    var body;
    if (live.status === "loading") {
      body = el("div", { class: "gate", role: "status", "aria-live": "polite" },
        brandMark(), el("span", { class: "spinner big", "aria-hidden": "true" }), el("p", { class: "muted" }, t("common.loading")));
    } else {
      var kind = live.error === "config" ? "config" : live.error === "offline" ? "offline" : "load";
      body = el("div", { class: "gate" }, emptyState(kind === "offline" ? "wifioff" : "alert",
        t(kind === "config" ? "error.config_title" : "error.load_title"),
        t(kind === "config" ? "error.config" : kind === "offline" ? "offline.load" : "error.load_body"),
        kind === "config" ? null : [button(t("common.retry"), startLive, "primary")]));
    }
    document.getElementById("app").replaceChildren(el("div", { class: "onb-col" }, el("main", { id: "main" }, body)));
    var b = document.querySelector(".gate .btn");
    if (b) b.focus({ preventScroll: true });
  }

  function banners() {
    return el("div", { class: "banners" },
      storageBlocked ? el("p", { class: "banner offline", role: "alert" }, icon("alert"), el("span", null, t(LIVE ? "error.storage_live" : "error.storage"))) : null,
      !navigator.onLine ? el("p", { class: "banner offline", role: "status" }, icon("wifioff"), el("span", null, t(LIVE ? "offline.banner_live" : "offline.banner"))) : null,
      LIVE ? null : el("p", { class: "banner proto" }, icon("info"), el("span", null, t("banner.prototype"))),
      state.ui_lang === "pap" ? el("p", { class: "banner draft" }, icon("globe"), el("span", null, t("lang.pap_note"))) : null);
  }

  function navItems() {
    var p = me();
    var items = [
      { name: "home", icon: "home", label: t("nav.home") },
      { name: "review", icon: "book", label: t("nav.review"), count: reviewQueue().length, task: true },
      { name: "translate", icon: "languages", label: t("nav.translate"), count: translateQueue().length, task: true },
      { name: "sentences", icon: "chat", label: t("nav.sentences"), count: sentenceQueue().length, task: true },
      { name: "rate", icon: "star", label: t("nav.rate"), count: rateCount(), task: true }
    ];
    if (p && p.board) items.push({ name: "board", icon: "shield", label: t("nav.board"), count: boardCount() });
    items.push({ name: "credits", icon: "users", label: t("nav.credits") });
    items.push({ name: "account", icon: "user", label: t("nav.account") });
    return items;
  }

  function sidebar(current) {
    var p = me();
    return el("aside", { class: "sidebar", "aria-label": "Sections" },
      el("a", { class: "brand", href: "#/home" }, brandMark(), el("span", null, el("strong", null, t("app.short")), el("small", null, "pap-AW"))),
      el("nav", null, el("ul", null, navItems().map(function (it) {
        return el("li", null, el("a", { href: "#/" + it.name, "aria-current": it.name === current ? "page" : null },
          icon(it.icon), el("span", { class: "grow" }, it.label), it.count ? el("span", { class: "count" }, it.count) : null));
      }))),
      el("div", { class: "sidebar-foot" },
        el("a", { class: "me", href: "#/account" }, avatar(p), el("span", null, el("strong", null, p.name), el("small", null, t("role." + p.role) + (p.board ? " · " + t("person.board_badge") : ""))))));
  }

  function topbar(current) {
    var p = me();
    var titles = { home: t("nav.home"), board: t("nav.board"), credits: t("nav.credits"), account: t("nav.account") };
    return el("header", { class: "topbar" },
      current === "home" ? el("a", { class: "brand", href: "#/home" }, brandMark(), el("strong", null, t("app.short"))) :
        el("h1", { class: "topbar-title" }, titles[current] || ""),
      el("a", { class: "topbar-me", href: "#/account", "aria-label": t("nav.account") }, avatar(p)));
  }

  function tabbar(current) {
    var p = me();
    var tabs = [{ name: "home", icon: "home", label: t("nav.home") }];
    if (p.board) tabs.push({ name: "board", icon: "shield", label: t("tab.board"), count: boardCount() });
    tabs.push({ name: "credits", icon: "users", label: t("nav.credits") }, { name: "account", icon: "user", label: t("nav.account") });
    return el("nav", { class: "tabbar", "aria-label": "Sections" }, tabs.map(function (it) {
      return el("a", { href: "#/" + it.name, "aria-current": it.name === current ? "page" : null },
        el("span", { class: "tab-icon" }, icon(it.icon), it.count ? el("span", { class: "dot" }, it.count) : null), el("span", null, it.label));
    }));
  }

  // Focus-mode frame for a task: close, progress, skip; body; bottom action bar.
  function taskFrame(opts) {
    var pct = opts.total ? Math.round(100 * Math.min(opts.done, opts.total) / opts.total) : 0;
    return el("div", { class: "task" + (opts.wide ? " wide" : "") },
      el("header", { class: "taskbar" },
        el("a", { class: "icon-btn", href: "#/home", "aria-label": t("common.close") }, icon("close")),
        el("div", { class: "progress", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(opts.total || 0),
                    "aria-valuenow": String(opts.done || 0), "aria-label": opts.title },
          el("span", { style: "width:" + pct + "%" })),
        opts.onSkip ? el("button", { type: "button", class: "text-btn", onclick: opts.onSkip }, t("common.skip")) : el("span", { class: "spacer" })),
      el("main", { id: "main", class: "task-body" },
        el("p", { class: "eyebrow" }, icon(opts.icon), el("span", null, opts.title),
          opts.total ? el("span", { class: "muted" }, " · " + t("common.progress", { i: Math.min(opts.done + 1, opts.total), n: opts.total })) : null),
        opts.body),
      opts.actions ? el("footer", { class: "actionbar" }, el("div", { class: "actionbar-inner" }, opts.actions)) : null);
  }

  // Bottom feedback sheet, as in the Duolingo lesson flow. It slides up on the
  // iOS drawer curve and leaves faster than it came (Emil Kowalski).
  function showSheet(opts) {
    closeSheet(true);
    var scrim = el("div", { class: "scrim", onclick: opts.dismissable ? closeSheet : null });
    var sheet = el("section", { class: "sheet " + (opts.tone || "ok"), role: "dialog", "aria-modal": "true", "aria-labelledby": "sheet-title" },
      el("div", { class: "sheet-inner" },
        el("h2", { id: "sheet-title", class: "sheet-title" }, icon(opts.icon || "check"), el("span", null, opts.title)),
        opts.body ? el("div", { class: "sheet-body" }, opts.body) : null,
        el("div", { class: "sheet-actions" }, opts.actions)));
    document.body.appendChild(scrim);
    document.body.appendChild(sheet);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { scrim.setAttribute("data-open", "true"); sheet.setAttribute("data-open", "true"); });
    });
    var b = sheet.querySelector(".btn.primary") || sheet.querySelector(".btn");
    if (b) b.focus({ preventScroll: true });
  }

  function closeSheet(immediate) {
    document.querySelectorAll(".sheet, .scrim").forEach(function (n) {
      if (immediate === true || n.getAttribute("data-open") !== "true") { n.remove(); return; }
      n.setAttribute("data-open", "false");
      setTimeout(function () { n.remove(); }, 200);
    });
  }

  // Sonner-style toast for small confirmations (download, import, undo).
  function toast(message, tone) {
    var host = document.getElementById("toasts");
    if (!host) { host = el("div", { id: "toasts", class: "toasts", "aria-live": "polite" }); document.body.appendChild(host); }
    var node = el("div", { class: "toast " + (tone || "ok"), role: tone === "bad" ? "alert" : "status" },
      icon(tone === "bad" ? "alert" : tone === "info" ? "info" : "check"), el("span", null, message));
    host.appendChild(node);
    requestAnimationFrame(function () { requestAnimationFrame(function () { node.setAttribute("data-open", "true"); }); });
    var left = 3200, started = Date.now(), timer;
    function hide() { node.setAttribute("data-open", "false"); setTimeout(function () { node.remove(); }, 200); }
    function arm() { started = Date.now(); timer = setTimeout(hide, left); }
    // Pause while the tab is hidden, so a toast is never missed.
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) { clearTimeout(timer); left -= Date.now() - started; } else if (node.isConnected) arm();
    });
    arm();
  }

  // The prototype has no server. api() stands in for one, so the loading and
  // error states can be tried: Account > Prototype: connection.
  function api() {
    var mode = state.sim || "normal";
    return new Promise(function (resolve, reject) {
      setTimeout(function () { if (mode === "fail") reject(new Error("network")); else resolve(); }, SIM_DELAY[mode] || 450);
    });
  }

  // Put a button into its loading state; returns a function that restores it.
  function busy(btn, label) {
    if (!btn) return function () {};
    var kids = Array.prototype.slice.call(btn.childNodes);
    var wasDisabled = btn.disabled;
    btn.style.minWidth = btn.getBoundingClientRect().width + "px";
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    btn.classList.add("is-busy");
    btn.replaceChildren(el("span", { class: "spinner", "aria-hidden": "true" }), el("span", null, label || t("common.saving")));
    return function () {
      if (!btn.isConnected) return;
      btn.replaceChildren.apply(btn, kids);
      btn.disabled = wasDisabled;
      btn.removeAttribute("aria-busy");
      btn.classList.remove("is-busy");
      btn.style.minWidth = "";
    };
  }

  // Save: loading state on the button, then success or an error sheet.
  // Demo: commit() changes state once api() (the stand-in server) has accepted.
  // Live: commit() is the database write itself; then everything reloads.
  function persist(btn, commit, onDone, retry, label) {
    var restore = busy(btn, label);
    var work = LIVE ? Promise.resolve().then(commit).then(refreshAfterWrite)
                    : api().then(function () { commit(); save(); });
    work.then(function () {
      restore();
      onDone();
    }, function (err) {
      restore();
      failSheet(err, retry);
    });
  }

  // What the database said, in words a teacher can act on.
  function failSheet(err, retry) {
    var e = err || {};
    if (LIVE && tooLate(e)) {
      showSheet({ tone: "warn", icon: "info", title: t("error.quicker_title"), body: el("p", null, t("error.quicker_body")),
        actions: [button(t("common.continue"), function (ev) {
          var restore = busy(ev.currentTarget, t("common.loading"));
          refreshAfterWrite().then(function () { restore(); closeSheet(); session.stayOn = null; render(); });
        }, "primary block")] });
      return;
    }
    if (LIVE && (e.status === 401 || /^PGRST30/.test(e.code || "") || /JWT/i.test(e.message || ""))) {
      showSheet({ tone: "bad", icon: "user", title: t("error.session_title"), body: el("p", null, t("error.session_body")),
        actions: [button(t("onb.email_title"), function (ev) { closeSheet(true); signOut(ev.currentTarget); }, "primary block")] });
      return;
    }
    if (LIVE && e.code === "42501") {
      showSheet({ tone: "bad", icon: "alert", title: t("error.not_allowed_title"), dismissable: true, body: el("p", null, t("error.not_allowed")),
        actions: [button(t("common.close"), closeSheet, "primary block")] });
      return;
    }
    errorSheet(retry);
  }

  function errorSheet(retry) {
    showSheet({
      tone: "bad", icon: "alert", title: t("error.save_title"), dismissable: true,
      body: el("p", null, t("error.save_body")),
      actions: [button(t("common.retry"), function () { closeSheet(true); retry(); }, "primary block"),
                button(t("common.cancel"), closeSheet, "block")]
    });
  }

  // Inline error under a field: red border, icon, message, focus.
  function fieldError(input, message) {
    var field = input.closest(".field, .stack") || input.parentNode;
    var id = (input.id || newId("field")) + "-error";
    var msg = field.querySelector(".field-error[data-for='" + id + "']");
    if (!msg) { msg = el("p", { class: "field-error", id: id, "data-for": id, role: "alert" }); field.appendChild(msg); }
    msg.replaceChildren(icon("alert"), el("span", null, message));
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", id);
    input.focus();
    input.addEventListener("input", function clear() {
      input.removeAttribute("aria-invalid");
      if (msg.isConnected) msg.remove();
      input.removeEventListener("input", clear);
    });
  }

  function savedSheet(extra, next) {
    showSheet({
      tone: "ok", icon: "check", title: t("common.saved"),
      body: extra,
      actions: [button(t("common.continue"), function () { closeSheet(); next(); }, "primary block")]
    });
  }

  function emptyState(iconName, title, body, actions) {
    return el("div", { class: "empty" },
      el("span", { class: "empty-icon" }, icon(iconName)),
      el("h2", null, title),
      body ? el("p", { class: "muted" }, body) : null,
      actions ? el("div", { class: "empty-actions" }, actions) : null);
  }

  // End of a task queue: Mimo's "Lesson complete" with three stat tiles.
  function doneScreen(kind, title, iconName, extra) {
    var skipped = session.skipped[kind];
    var r = myRecords();
    var all = [].concat(r.review, r.translate, r.sentences, r.ratings);
    var todayN = all.filter(function (x) { return day(x.at) === today(); }).length;
    var waiting = LIVE ? live.qs.my_waiting || 0 : r.review.concat(r.translate).filter(function (a) {
      return answersFor(a.kind, a.item).length < 2 && !decisionFor(a.kind, a.item);
    }).length + r.sentences.filter(function (tr) { return !ratingsOf(tr.id).length; }).length;
    var confirmed = LIVE ? live.qs.my_confirmed || 0 : r.review.concat(r.translate).filter(function (a) {
      var d = decisionFor(a.kind, a.item); return d && d.outcome === "reviewed";
    }).length + r.sentences.filter(function (tr) { var d = decisionFor("sentence", tr.id); return d && d.outcome === "reviewed"; }).length;
    return taskFrame({
      title: title, icon: iconName, done: 0, total: 0,
      body: el("div", { class: "done" },
        el("span", { class: "done-icon" }, icon("check")),
        el("h2", { "data-autofocus": true, tabindex: "-1" }, t("summary.title")),
        el("p", { class: "muted" }, t("common.done")),
        extra || null,
        el("div", { class: "stats" },
          stat(todayN, t("summary.today")),
          stat(waiting, t("summary.waiting")),
          stat(confirmed, t("summary.confirmed"))),
        skipped && skipped.size ? button(t("common.show_skipped"), function () { skipped.clear(); render(); }, "ghost") : null),
      actions: [button(t("summary.home"), function () { go("home"); }, "primary block")]
    });
  }

  function stat(n, label) { return el("div", { class: "stat" }, el("strong", null, n), el("span", null, label)); }

  // -------------------------------------------------------------- onboarding

  function viewOnboarding() {
    var o = session.onb;
    var adding = !!me();
    var steps = [onbWelcome, onbEmail, onbCode, onbProfile, onbConsent];
    if (adding && o.step === 0) o.step = 1;
    return steps[o.step](o, adding);
  }

  function onbFrame(o, body, actions, backable) {
    var n = 4;
    return el("div", { class: "onb" },
      el("header", { class: "onb-head" },
        backable ? button(icon("back"), function () { o.step--; render(); }, "icon-btn", { "aria-label": t("common.back") }) :
          (me() ? el("a", { class: "icon-btn", href: "#/account", "aria-label": t("common.close") }, icon("close")) : el("span", { class: "spacer" })),
        o.step > 0 ? el("div", { class: "steps" }, el("span", { class: "muted small" }, t("onb.step", { i: o.step, n: n })),
          el("div", { class: "progress thin" }, el("span", { style: "width:" + Math.round(100 * o.step / n) + "%" }))) : el("span", { class: "spacer" }),
        langSwitch()),
      el("main", { id: "main", class: "onb-body" }, body),
      el("footer", { class: "actionbar" }, el("div", { class: "actionbar-inner" }, actions)));
  }

  function langSwitch() {
    return el("div", { class: "seg-mini", role: "group", "aria-label": t("lang.label") },
      ["en", "pap"].map(function (l) {
        return el("button", { type: "button", "aria-pressed": state.ui_lang === l ? "true" : "false",
          onclick: function () { state.ui_lang = l; save(); render(); } }, l === "en" ? "EN" : "PAP");
      }));
  }

  function onbWelcome(o) {
    return onbFrame(o, el("div", { class: "welcome" },
      el("div", { class: "hero-art" },
        el("img", { src: "assets/hero.webp", alt: "", width: "1048", height: "592", decoding: "async" }),
        el("div", { class: "hero-overlay" }, brandMark(), el("span", { class: "hero-tag" }, "Aruban Papiamento · pap-AW"))),
      el("h1", { "data-autofocus": true, tabindex: "-1" }, t("app.subtitle")),
      el("ul", { class: "points" },
        el("li", null, icon("book"), el("span", null, t("onb.point1"))),
        el("li", null, icon("chat"), el("span", null, t("onb.point2"))),
        el("li", null, icon("shield"), el("span", null, t("onb.point3"))))),
      [button(t("onb.get_started"), function () { o.step = 1; render(); }, "primary block")]);
  }

  // Live: Supabase emails a 6-digit code (supabase/email-template.html).
  function sendCode(email) {
    if (!LIVE) return api();
    return db(live.client.auth.signInWithOtp({ email: email, options: { shouldCreateUser: true } }));
  }

  function onbEmail(o, adding) {
    var input = el("input", { type: "email", id: "onb-email", autocomplete: "email", inputmode: "email", value: o.email, "data-autofocus": true,
                              placeholder: "name@example.com", spellcheck: "false", autocapitalize: "off" });
    var sendBtn = button(t("onb.send_code"), next, "primary block");
    function next() {
      var v = input.value.trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { fieldError(input, t("onb.email_need")); return; }
      var restore = busy(sendBtn, t("common.sending"));
      sendCode(v).then(function () { o.email = v; o.sentAt = Date.now(); o.step = 2; render(); },
                       function (err) { restore(); fieldError(input, t(err && err.status === 429 ? "error.code_wait" : "error.send_code")); });
    }
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") next(); });
    return onbFrame(o, el("div", { class: "stack" },
      el("span", { class: "hero-icon" }, icon("mail")),
      el("h1", null, t("onb.email_title")),
      el("p", { class: "muted" }, t("onb.email_note")),
      el("div", { class: "field" }, el("label", { for: "onb-email" }, t("onb.email_label")), input),
      el("p", { class: "note small" }, icon("info"), el("span", null, t(LIVE ? "onb.email_live" : "onb.proto_email")))),
      [sendBtn], !adding);
  }

  function onbCode(o) {
    var boxes = [];
    var row = el("div", { class: "code-row", role: "group", "aria-label": t("onb.code_title") });
    var okBtn = button(t("common.continue"), next, "primary block");
    for (var i = 0; i < 6; i++) {
      (function (i) {
        var b = el("input", { type: "text", inputmode: "numeric", autocomplete: i === 0 ? "one-time-code" : "off", maxlength: "1", class: "code-box",
                              "aria-label": "Digit " + (i + 1), "data-autofocus": i === 0 ? true : null });
        b.addEventListener("input", function () {
          b.value = b.value.replace(/\D/g, "").slice(0, 1);
          row.removeAttribute("aria-invalid");
          if (b.value && boxes[i + 1]) boxes[i + 1].focus();
          if (boxes.every(function (x) { return x.value; })) next();
        });
        b.addEventListener("keydown", function (e) { if (e.key === "Backspace" && !b.value && boxes[i - 1]) boxes[i - 1].focus(); });
        b.addEventListener("paste", function (e) {
          var d = (e.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, 6);
          if (!d) return;
          e.preventDefault();
          d.split("").forEach(function (c, k) { if (boxes[k]) boxes[k].value = c; });
          (boxes[d.length] || boxes[5]).focus();
          if (d.length === 6) next();
        });
        boxes.push(b);
      })(i);
    }
    append(row, [boxes.slice(0, 3), el("span", { class: "code-dash", "aria-hidden": "true" }, "–"), boxes.slice(3)]);
    var checking = false;
    function next() {
      if (checking) return;
      var code = boxes.map(function (b) { return b.value; }).join("");
      if (code.length < 6) {
        row.setAttribute("aria-invalid", "true");
        fieldError(boxes[code.length] || boxes[0], t("onb.code_need"));
        return;
      }
      checking = true;
      var restore = busy(okBtn, t("common.checking"));
      if (!LIVE) {
        api().then(function () { o.step = 3; render(); },
                   function () { checking = false; restore(); fieldError(boxes[5], t("error.save_body")); });
        return;
      }
      var verified = false;
      db(live.client.auth.verifyOtp({ email: o.email, token: code, type: "email" })).then(function (data) {
        verified = true;
        live.user = (data && data.user) || (data && data.session && data.session.user);
        return loadData();
      }).then(function () {
        if (live.status === "ready") {
          session.onb = { step: 0, email: "", profile: null };
          go("home");
          toast(t("toast.welcome_back"));
        } else { o.step = 3; render(); }
      }).catch(function (err) {
        if (verified) { live.status = "error"; live.error = navigator.onLine ? "load" : "offline"; render(); return; }
        checking = false; restore();
        row.setAttribute("aria-invalid", "true");
        var wrong = err && (err.status === 400 || err.status === 401 || err.status === 403 || /expired|invalid|otp/i.test(err.message || ""));
        fieldError(boxes[5], t(wrong ? "error.code_wrong" : err && err.status === 429 ? "error.code_wait" : "error.save_body"));
      });
    }

    // Live: a new code after a minute, with the seconds counting down.
    var resend = null;
    if (LIVE) {
      resend = button(t("onb.resend"), function () {
        var restore = busy(resend, t("common.sending"));
        sendCode(o.email).then(function () { o.sentAt = Date.now(); restore(); tick(); toast(t("onb.code_sent", { email: o.email }), "info"); },
                               function (err) { restore(); tick(); toast(t(err && err.status === 429 ? "error.code_wait" : "error.send_code"), "bad"); });
      }, "text-btn");
      var tick = function (first) {
        if (first !== true && !resend.isConnected) return;
        var left = Math.ceil((RESEND_SECONDS * 1000 - (Date.now() - (o.sentAt || 0))) / 1000);
        if (resend.getAttribute("aria-busy")) return;
        resend.disabled = left > 0;
        resend.textContent = left > 0 ? t("onb.resend_wait", { s: left }) : t("onb.resend");
        if (left > 0) setTimeout(tick, 1000);
      };
      tick(true);
    }
    return onbFrame(o, el("div", { class: "stack center" },
      el("span", { class: "hero-icon" }, icon("mail")),
      el("h1", null, t("onb.code_title")),
      el("p", { class: "muted" }, t("onb.code_sent", { email: o.email })),
      row,
      el("p", { class: "note small" }, icon("info"), el("span", null, t(LIVE ? "onb.code_live" : "onb.code_proto"))),
      el("div", { class: "row-actions center" }, resend,
        button(t("onb.change_email"), function () { o.step = 1; render(); }, "text-btn"))),
      [okBtn], true);
  }

  function onbProfile(o) {
    var pr = o.profile || (o.profile = { name: "", role: "teacher", school: "", board: false, github: "" });
    var name = el("input", { type: "text", id: "onb-name", autocomplete: "name", value: pr.name, "data-autofocus": true });
    var school = el("input", { type: "text", id: "onb-school", autocomplete: "organization", value: pr.school });
    var gh = el("input", { type: "text", id: "onb-gh", autocomplete: "off", value: pr.github, placeholder: "github-username", spellcheck: "false", autocapitalize: "off" });
    var ghRow = el("div", { class: "field", hidden: !pr.board }, el("label", { for: "onb-gh" }, t("consent.github")), gh);
    // Live, a maintainer makes someone a board member in the database (supabase/README.md).
    if (LIVE) pr.board = false;
    var board = el("input", { type: "checkbox", id: "onb-board", checked: pr.board,
      onchange: function () { ghRow.hidden = !board.checked; } });
    var roles = [["teacher", "school"], ["linguist", "pen"], ["other", "user"]];
    var roleTiles = el("div", { class: "tiles3", role: "radiogroup", "aria-label": t("consent.role") }, roles.map(function (r) {
      return el("label", { class: "tile-choice" },
        el("input", { type: "radio", name: "role", value: r[0], checked: pr.role === r[0], class: "sr-only" }),
        el("span", { class: "face" }, icon(r[1]), el("span", null, t("role." + r[0]))));
    }));
    function next() {
      pr.name = Checker.normalise(name.value);
      pr.school = Checker.normalise(school.value);
      pr.role = roleTiles.querySelector("input:checked").value;
      pr.board = board.checked;
      pr.github = Checker.normalise(gh.value);
      if (!pr.name) { fieldError(name, t("onb.name_need")); return; }
      if (pr.board && !/^[A-Za-z0-9-]+$/.test(pr.github)) { fieldError(gh, t("onb.github_need")); return; }
      o.step = 4; render();
    }
    return onbFrame(o, el("div", { class: "stack" },
      el("h1", null, t("onb.profile_title")),
      el("div", { class: "field" }, el("label", { for: "onb-name" }, t("consent.name")), name),
      el("fieldset", { class: "field" }, el("legend", null, t("consent.role")), roleTiles),
      el("div", { class: "field" }, el("label", { for: "onb-school" }, t("onb.school")), school),
      LIVE ? null : el("label", { class: "switch-row" }, board, el("span", { class: "switch", "aria-hidden": "true" }), el("span", null, t("consent.board"))),
      LIVE ? null : ghRow),
      [button(t("common.continue"), next, "primary block")], !LIVE);
  }

  function onbConsent(o) {
    var pr = o.profile;
    var lw = el("input", { type: "checkbox", id: "c-lw" });
    var ls = el("input", { type: "checkbox", id: "c-ls" });
    var credit = el("input", { type: "checkbox", id: "c-credit", checked: true });
    var cards = el("div", { class: "stack consent-group" },
      el("label", { class: "consent-card" }, lw, el("span", null, el("strong", null, "CC BY 4.0"), el("span", null, t("consent.words")))),
      el("label", { class: "consent-card" }, ls, el("span", null, el("strong", null, "CC0 1.0"), el("span", null, t("consent.sentences")))));
    var finishBtn = button(t("onb.finish"), finish, "primary block");
    function finish() {
      if (!lw.checked || !ls.checked) { fieldError(!lw.checked ? lw : ls, t("consent.need_boxes")); return; }
      persist(finishBtn, function () {
        if (LIVE) {
          return db(live.client.rpc("create_profile", { p_name: pr.name, p_credit: credit.checked, p_school: pr.school,
                                                         p_occupation: pr.role, p_consent_version: CONSENT_VERSION }));
        }
        var id = newId("person");
        state.people.push({
          id: id, name: pr.name, handle: makeHandle(pr.name, id), role: pr.role, school: pr.school, board: pr.board,
          github: pr.board ? pr.github : "", credit: credit.checked,
          consent: { words: "CC-BY-4.0", sentences: "CC0-1.0", text_version: "prototype-2", at: now() },
          created_at: now()
        });
        state.current = id;
      }, function () {
        session.onb = { step: 0, email: "", profile: null };
        if (LIVE && live.status !== "ready") { live.status = "error"; live.error = navigator.onLine ? "load" : "offline"; render(); return; }
        go("home");
        toast(t("toast.welcome"));
      }, finish);
    }
    return onbFrame(o, el("div", { class: "stack" },
      el("h1", null, t("onb.licence_title")),
      el("p", { class: "muted" }, t("consent.intro")),
      cards,
      el("label", { class: "switch-row" }, credit, el("span", { class: "switch", "aria-hidden": "true" }), el("span", null, t("consent.credit"))),
      el("p", { class: "muted small" }, t(LIVE ? "consent.privacy_live" : "consent.privacy"))),
      [finishBtn], true);
  }

  // ------------------------------------------------------------------- home

  function goalRing(n, goal) {
    var r = 26, c = 2 * Math.PI * r, f = Math.min(1, n / goal);
    var span = el("span", { class: "ring", "aria-hidden": "true" });
    span.innerHTML = '<svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="' + r + '" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="7"/>' +
      '<circle cx="32" cy="32" r="' + r + '" fill="none" stroke="#f9d616" stroke-width="7" stroke-linecap="round" stroke-dasharray="' + (c * f) + " " + c + '" transform="rotate(-90 32 32)"/></svg>';
    span.appendChild(el("strong", null, n));
    return span;
  }

  function viewHome() {
    var p = me();
    var dates = myDates();
    var todayN = dates.filter(function (d) { return d === today(); }).length;
    var weekAgo = new Date(); weekAgo.setDate(weekAgo.getDate() - 6);
    var weekN = dates.filter(function (d) { return d >= day(weekAgo.toISOString()); }).length;
    var modes = [
      ["review", "book", "nav.review", "home.review", reviewQueue().length, "blue"],
      ["translate", "languages", "nav.translate", "home.translate", translateQueue().length, "teal"],
      ["sentences", "chat", "nav.sentences", "home.sentences", sentenceQueue().length, "sun"],
      ["rate", "star", "nav.rate", "home.rate", rateCount(), "violet"]
    ];
    return el("div", { class: "home" },
      el("h1", { class: "hello", "data-autofocus": true, tabindex: "-1" }, t("home.hello", { name: p.name.split(" ")[0] })),
      el("section", { class: "goal", "aria-label": t("home.goal") },
        goalRing(todayN, DAILY_GOAL),
        el("div", { class: "goal-text" }, el("span", { class: "goal-label" }, t("home.goal")),
          el("strong", null, t("home.goal_progress", { n: todayN, goal: DAILY_GOAL }))),
        el("div", { class: "goal-stats" },
          el("div", null, el("strong", null, weekN), el("span", null, t("home.week"))),
          el("div", null, el("strong", null, daysInARow()), el("span", null, t("home.days"))))),
      p.board ? el("a", { class: "board-cta", href: "#/board" }, icon("shield"),
        el("span", { class: "grow" }, el("strong", null, t("nav.board")), el("span", null, t("home.board"))),
        el("span", { class: "pill" + (boardCount() ? "" : " zero"), "aria-label": t("home.waiting", { n: boardCount() }) },
          el("span", { class: "pill-long", "aria-hidden": "true" }, t("home.waiting", { n: boardCount() })),
          el("span", { class: "pill-short", "aria-hidden": "true" }, boardCount())), icon("chevron", "chev")) : null,
      el("h2", { class: "section-title" }, t("home.ways")),
      el("ul", { class: "mode-list" }, modes.map(function (m) {
        return el("li", null, el("a", { class: "mode-row", href: "#/" + m[0] },
          el("span", { class: "mode-icon " + m[5] }, icon(m[1])),
          el("span", { class: "grow" }, el("strong", null, t(m[2])), el("span", { class: "muted" }, t(m[3]))),
          el("span", { class: "pill" + (m[4] ? "" : " zero"), "aria-label": t("home.waiting", { n: m[4] }) },
            el("span", { class: "pill-long", "aria-hidden": "true" }, t("home.waiting", { n: m[4] })),
            el("span", { class: "pill-short", "aria-hidden": "true" }, m[4])),
          icon("chevron", "chev")));
      })),
      LIVE ? null : el("p", { class: "muted small foot-note" }, t("home.proto_note")));
  }

  // ------------------------------------------------------------------- word card

  function wordCard(w) {
    var uncertain = /uncertain/.test(w.notes || "");
    return el("article", { class: "word-card" },
      el("div", { class: "word-title" },
        el("h2", { class: "lemma", lang: "pap", "data-autofocus": true, tabindex: "-1" }, w.lemma),
        w.alt ? el("span", { class: "alt", lang: "pap" }, "[" + w.alt + "]") : null),
      el("div", { class: "chips" },
        w.pos ? el("span", { class: "chip" }, w.pos) : null,
        w.tag ? el("span", { class: "chip" }, "(" + w.tag + ")") : null,
        el("span", { class: "chip muted" }, w.id)),
      el("figure", { class: "crop" },
        pageCrop(w, "", "(max-width: 560px), (min-width: 900px)"),
        el("figcaption", null, el("span", null, t("word.page", { page: w.page })),
          el("a", { href: SAMPLE.pdf_href + "#page=" + w.pdf_page, target: "_blank", rel: "noopener" }, t("word.open_pdf"), icon("external")))),
      uncertain ? el("p", { class: "note warn" }, icon("alert"), el("span", null, t("word.uncertain"))) :
        (w.notes ? el("p", { class: "note" }, icon("info"), el("span", null, el("strong", null, t("word.notes") + ": "), w.notes)) : null));
  }

  // A crop of the printed page: shimmer while it loads, a plain fallback with
  // the PDF link if it fails. Phones and laptops get the one-column crop.
  function pageCrop(w, cls, media) {
    if (!w.crop) {
      return el("div", { class: "img-frame failed " + (cls || "") }, el("p", { class: "img-fallback" }, icon("alert"),
        el("span", null, t("error.image") + " "), el("a", { href: SAMPLE.pdf_href + "#page=" + w.pdf_page, target: "_blank", rel: "noopener" }, t("word.open_pdf"))));
    }
    var frame = el("div", { class: "img-frame " + (cls || "") });
    var img = el("img", { src: w.crop, width: w.crop_w, height: w.crop_h, decoding: "async",
                          alt: "AB 2018 word list, page " + w.page + ", with " + w.lemma + " highlighted" });
    img.addEventListener("load", function () { frame.classList.add("loaded"); });
    img.addEventListener("error", function () {
      frame.classList.add("failed");
      frame.replaceChildren(el("p", { class: "img-fallback" }, icon("alert"),
        el("span", null, t("error.image") + " "), el("a", { href: SAMPLE.pdf_href + "#page=" + w.pdf_page, target: "_blank", rel: "noopener" }, t("word.open_pdf"))));
    });
    frame.appendChild(el("picture", null,
      el("source", { media: media, srcset: w.crop_column, width: w.crop_column_w, height: w.crop_column_h }), img));
    if (img.complete && img.naturalWidth) frame.classList.add("loaded");
    return frame;
  }

  function progressOf(kind) {
    return state.answers.filter(function (a) { return a.kind === kind && a.by === state.current; }).length;
  }

  // After saving a word: live, a contributor cannot see whether theirs was the second answer.
  function wordFeedback(kind, item) {
    if (LIVE) return t("feedback.word_live");
    return t(answersFor(kind, item).length >= 2 ? "feedback.to_board" : "feedback.waiting");
  }

  // Big choice buttons: radio inputs styled as buttons.
  function choiceGroup(name, options, onchange) {
    return el("div", { class: "choices-big", role: "radiogroup" }, options.map(function (o) {
      return el("label", { class: "choice-big " + o.value },
        el("input", { type: "radio", name: name, value: o.value, class: "sr-only", onchange: onchange }),
        el("span", { class: "face" }, icon(o.icon), el("span", null, o.label)));
    }));
  }

  function viewReview() {
    var queue = reviewQueue().filter(function (w) { return !session.skipped.review.has(w.id); });
    if (!queue.length) return doneScreen("review", t("nav.review"), "book");
    var w = queue[0];
    var verdicts = {};
    var fixes = {};
    var saveBtn = button(t("common.save"), submit, "primary block", { disabled: true });
    var hint = el("p", { class: "action-hint muted small" }, t("review.need_all"));
    function update() {
      var complete = LANGS.every(function (l) { return verdicts[l] && (verdicts[l] !== "wrong" || normGloss(fixes[l].value)); });
      saveBtn.disabled = !complete;
      hint.hidden = complete;
    }
    var rows = LANGS.map(function (lang) {
      var fix = el("input", { type: "text", class: "fix", lang: lang, hidden: true, oninput: update,
                              "aria-label": t("review.fix", { lang: langName(lang) }), placeholder: t("review.fix", { lang: langName(lang) }) });
      fixes[lang] = fix;
      return el("fieldset", { class: "lang-block" },
        el("legend", null, el("span", { class: "lang-code" }, lang.toUpperCase()), langName(lang)),
        el("p", { class: "draft-row" }, el("span", { class: "draft-label" }, t("review.draft")), el("span", { lang: lang }, w[lang] || "—")),
        choiceGroup("v-" + lang, [
          { value: "correct", icon: "check", label: t("review.correct") },
          { value: "wrong", icon: "close", label: t("review.wrong") },
          { value: "unsure", icon: "help", label: t("review.unsure") }
        ], function (e) {
          verdicts[lang] = e.target.value;
          fix.hidden = e.target.value !== "wrong";
          if (!fix.hidden) fix.focus();
          update();
        }),
        fix);
    });
    var comment = el("textarea", { rows: 2, class: "comment", "aria-label": t("common.comment"), placeholder: t("common.comment") });

    function submit() {
      var out = {};
      LANGS.forEach(function (l) { out[l] = { verdict: verdicts[l], fix: verdicts[l] === "wrong" ? normGloss(fixes[l].value) : "" }; });
      persist(saveBtn, function () {
        return saveAnswer("review", w.id, { verdicts: out }, Checker.normalise(comment.value));
      }, function () {
        savedSheet(el("p", null, wordFeedback("review", w.id)), render);
      }, submit);
    }

    return taskFrame({
      title: t("nav.review"), icon: "book", done: progressOf("review"), total: progressOf("review") + queue.length, wide: true,
      onSkip: function () { session.skipped.review.add(w.id); render(); },
      body: el("div", { class: "split" },
        el("div", { class: "split-left" }, wordCard(w)),
        el("div", { class: "split-right" },
          el("p", { class: "lead" }, t("review.intro")),
          rows, comment)),
      actions: [hint, saveBtn]
    });
  }

  function glossHints(lang, value, w) {
    var hints = [];
    var v = normGloss(value);
    if (!v) return hints;
    if (v.split("; ").length > 3) hints.push(t("hint.three"));
    if (lang === "en" && w.pos === "v." && v.split("; ").some(function (s) { return s.indexOf("to ") !== 0; })) hints.push(t("hint.to"));
    if (/,/.test(v) && v.indexOf(";") < 0) hints.push(t("hint.semicolon"));
    return hints;
  }

  function viewTranslate() {
    var queue = translateQueue().filter(function (w) { return !session.skipped.translate.has(w.id); });
    if (!queue.length) return doneScreen("translate", t("nav.translate"), "languages");
    var w = queue[0];
    var inputs = {};
    var saveBtn = button(t("common.save"), submit, "primary block", { disabled: true });
    var unknown = el("input", { type: "checkbox", id: "tr-unknown", onchange: update });
    function update() {
      var any = LANGS.some(function (l) { return normGloss(inputs[l].value); });
      saveBtn.disabled = !(any || unknown.checked);
      LANGS.forEach(function (l) { inputs[l].disabled = unknown.checked; });
    }
    var rows = LANGS.map(function (lang) {
      var hint = el("p", { class: "hint", "aria-live": "polite" });
      var inp = el("input", { type: "text", lang: lang, id: "tr-" + lang, autocomplete: "off",
        oninput: function () { hint.textContent = glossHints(lang, inp.value, w).join(" "); update(); } });
      inputs[lang] = inp;
      return el("div", { class: "field lang-input" },
        el("label", { for: "tr-" + lang }, el("span", { class: "lang-code" }, lang.toUpperCase()), langName(lang)), inp, hint);
    });
    var comment = el("textarea", { rows: 2, class: "comment", "aria-label": t("common.comment"), placeholder: t("common.comment") });

    function submit() {
      var vals = {};
      LANGS.forEach(function (l) { vals[l] = normGloss(inputs[l].value); });
      persist(saveBtn, function () {
        return saveAnswer("translate", w.id, { values: unknown.checked ? { en: "", nl: "", es: "" } : vals, unknown: unknown.checked },
                          Checker.normalise(comment.value));
      }, function () {
        savedSheet(el("p", null, wordFeedback("translate", w.id)), render);
      }, submit);
    }

    return taskFrame({
      title: t("nav.translate"), icon: "languages", done: progressOf("translate"), total: progressOf("translate") + queue.length, wide: true,
      onSkip: function () { session.skipped.translate.add(w.id); render(); },
      body: el("div", { class: "split" },
        el("div", { class: "split-left" }, wordCard(w),
          el("p", { class: "muted small order" }, t("translate.freq", { source: SAMPLE.translate_order + " (" + w.freq + ")" }))),
        el("div", { class: "split-right" },
          el("p", { class: "lead" }, t("translate.intro")),
          el("p", { class: "note" }, icon("info"), el("span", null, t("translate.hint"))),
          rows,
          el("label", { class: "check-chip" }, unknown, el("span", null, t("translate.unknown"))),
          comment)),
      actions: [saveBtn]
    });
  }

  // ------------------------------------------------------------------- live checks

  function checkMessage(f) {
    if (f.kind === "variant") return t("sent.curacao", { right: f.fixes.join(" / ") });
    if (f.kind === "barbarismo") return f.severity === "check" ? t("sent.barbarismo_check", { right: f.fixes.join(" / ") })
                                                             : t("sent.barbarismo", { right: f.fixes.join(" / ") });
    return f.message;
  }

  function checkRef(f) {
    return f.kind === "rule" ? f.id : f.kind === "variant" ? "lexicon/variants " + f.id : "lexicon/barbarismos " + f.id;
  }

  // Wrong → right, as in Duolingo's correction sheet.
  function correction(f) {
    return el("span", { class: "correction", lang: "pap" },
      el("del", null, f.text),
      f.fixes.length ? [el("span", { class: "arrow", "aria-hidden": "true" }, "→"), el("ins", null, f.fixes.join(" / "))] : null);
  }

  // Live-check panel bound to a textarea. Returns {node, findings()}.
  function checkerPanel(textarea) {
    var list = el("ul", { class: "findings" });
    var status = el("p", { class: "check-ok" });
    var unknownLine = el("p", { class: "unknown-line muted small" });
    var toggle = el("input", { type: "checkbox", checked: state.show_unknown,
      onchange: function () { state.show_unknown = toggle.checked; save(); refresh(); } });
    var current = [];

    function refresh() {
      var text = textarea.value;
      current = Checker.check(text, P, { unknownWords: state.show_unknown });
      list.innerHTML = "";
      status.innerHTML = "";
      unknownLine.textContent = "";
      if (!text.trim()) { status.hidden = true; return; }
      var major = current.filter(function (f) { return f.kind !== "unknown"; });
      var unknown = current.filter(function (f) { return f.kind === "unknown"; });
      status.hidden = major.length > 0;
      append(status, [icon("check"), el("span", null, t("sent.checks_none"))]);
      major.forEach(function (f) {
        list.appendChild(el("li", { class: "finding sev-" + f.severity },
          el("div", { class: "finding-main" }, correction(f),
            el("p", { class: "finding-msg" }, checkMessage(f),
              f.kind === "barbarismo" && f.message ? el("span", { class: "muted" }, " (" + f.message + ")") : null),
            el("p", { class: "ref" }, checkRef(f))),
          f.fixes.map(function (fx) {
            return button(t("sent.use", { fix: fx }), function () {
              textarea.value = Checker.applyFix(textarea.value, f, fx);
              textarea.dispatchEvent(new Event("input"));
              textarea.focus();
            }, "small");
          })));
      });
      if (unknown.length) unknownLine.textContent = t("sent.unknown") + " " + unknown.map(function (f) { return f.text; }).join(", ");
    }

    textarea.addEventListener("input", refresh);
    var node = el("section", { class: "checker", "aria-live": "polite", "aria-label": t("sent.checks") },
      el("div", { class: "checker-head" }, el("h3", null, t("sent.checks")),
        el("label", { class: "mini-switch" }, toggle, el("span", null, t("sent.unknown_short")))),
      status, list, unknownLine);
    refresh();
    return { node: node, refresh: refresh, findings: function () { return current; } };
  }

  function summarise(findings) {
    return findings.filter(function (f) { return f.kind !== "unknown"; })
      .map(function (f) { return { id: f.kind === "rule" ? f.id : f.kind + ":" + f.id, text: f.text, fixes: f.fixes }; });
  }

  // "Check" first; if the checker has findings, show them in a sheet with
  // "Use the suggestions" and "Keep as written". Otherwise save directly.
  function checkThenSave(textarea, doSave) {
    var text = Checker.normalise(textarea.value);
    var major = Checker.check(text, P, {}).filter(function (f) { return f.kind !== "unknown"; });
    if (!major.length) { doSave(text, []); return; }
    var fixable = major.filter(function (f) { return f.fixes.length === 1; });
    showSheet({
      tone: "warn", icon: "alert", title: t("feedback.check_title"), dismissable: true,
      body: [el("p", null, t("feedback.check_body")),
             el("ul", { class: "sheet-list" }, major.map(function (f) { return el("li", null, correction(f), el("span", { class: "muted small" }, checkMessage(f))); })),
             el("p", { class: "muted small" }, t("sent.checks_note"))],
      actions: [
        fixable.length ? button(t("feedback.use_all"), function () {
          var v = textarea.value;
          fixable.slice().sort(function (a, b) { return b.start - a.start; }).forEach(function (f) {
            var hit = Checker.check(v, P, {}).filter(function (g) { return g.id === f.id && g.text === f.text && g.fixes.length === 1; })[0];
            if (hit) v = Checker.applyFix(v, hit, hit.fixes[0]);
          });
          textarea.value = v;
          textarea.dispatchEvent(new Event("input"));
          closeSheet();
          textarea.focus();
        }, "primary block") : null,
        button(t("feedback.keep"), function () { closeSheet(); doSave(text, summarise(major)); }, fixable.length ? "block" : "primary block")
      ]
    });
  }

  function promptCard(p) {
    return el("div", { class: "prompt-card" },
      el("div", { class: "chips" },
        el("span", { class: "chip lang" }, langName(p.lang)),
        p.origin === "written-for-prototype" ? el("span", { class: "chip sun" }, t("sent.written")) : null),
      el("p", { class: "prompt-text", lang: p.lang }, p.text));
  }

  function viewSentences() {
    var p = null;
    if (session.stayOn) p = promptById(session.stayOn);
    if (!p) {
      session.stayOn = null;
      var queue = sentenceQueue().filter(function (x) { return !session.skipped.sentences.has(x.id); });
      if (!queue.length) return doneScreen("sentences", t("nav.sentences"), "chat");
      p = queue[0];
    }
    var mine = translationsOf(p.id).filter(function (tr) { return tr.by === state.current; });
    var others = LIVE ? Math.max(0, sentencesFor(p.id) - mine.length) :
      new Set(translationsOf(p.id).filter(function (tr) { return tr.by !== state.current; }).map(function (tr) { return tr.by; })).size;
    var ta = el("textarea", { id: "pap-text", rows: 3, lang: "pap", spellcheck: "false", autocapitalize: "sentences",
                              autocomplete: "off", "aria-describedby": "no-draft", value: session.draft[p.id] || "", "data-autofocus": true,
                              placeholder: t("sent.placeholder") });
    var saveBtn = button(t("common.check"), function () { checkThenSave(ta, function (text, kept) { store(text, kept, false, saveBtn); }); }, "primary block", { disabled: !ta.value.trim() });
    var anotherBtn = button(t("sent.another_short"), function () { checkThenSave(ta, function (text, kept) { store(text, kept, true, anotherBtn); }); }, "block", { disabled: !ta.value.trim() });
    ta.addEventListener("input", function () {
      session.draft[p.id] = ta.value;
      saveBtn.disabled = anotherBtn.disabled = !ta.value.trim();
    });
    var panel = checkerPanel(ta);
    var doneN = new Set(state.translations.filter(function (tr) { return tr.by === state.current; }).map(function (tr) { return tr.prompt; })).size;

    function store(text, kept, stay, btn) {
      persist(btn, function () {
        return after(saveTranslation(p.id, text, kept), function () {
          delete session.draft[p.id];
          session.stayOn = stay ? p.id : null;
        });
      }, function () {
        savedSheet([el("p", null, t("feedback.sentence")),
                    kept.length ? el("p", { class: "muted small" }, t("sent.kept", { n: kept.length })) : null], render);
      }, function () { store(text, kept, stay, btn); });
    }

    return taskFrame({
      title: t("nav.sentences"), icon: "chat", done: doneN, total: doneN + sentenceQueue().length,
      onSkip: function () { session.skipped.sentences.add(p.id); session.stayOn = null; render(); },
      body: el("div", { class: "stack" },
        promptCard(p),
        el("p", { class: "lead" }, t("sent.intro")),
        el("p", { class: "note", id: "no-draft" }, icon("info"), el("span", null, t("sent.no_draft"))),
        mine.length ? el("div", { class: "mine" }, el("p", { class: "muted small" }, t("sent.yours")),
          el("ul", null, mine.map(function (tr) { return el("li", { lang: "pap" }, tr.text); }))) : null,
        others ? el("p", { class: "muted small" }, t("sent.others", { n: others })) : null,
        el("label", { for: "pap-text", class: "label-strong" }, t("sent.your")),
        ta, panel.node),
      actions: [anotherBtn, saveBtn]
    });
  }

  function viewRate() {
    var queue = rateQueue().filter(function (tr) { return !session.skipped.rate.has(tr.id); });
    var ratedByMe = state.ratings.filter(function (r) { return r.by === state.current; }).length;
    if (!queue.length) {
      var anyOthers = LIVE ? rateCount() > 0 : state.translations.some(function (tr) { return tr.by !== state.current; });
      if (!anyOthers && !ratedByMe) {
        return taskFrame({ title: t("nav.rate"), icon: "star", done: 0, total: 0,
          body: emptyState("star", t("rate.empty_title"), t(LIVE ? "rate.empty_hint_live" : "rate.empty_hint")),
          actions: [button(t("summary.home"), function () { go("home"); }, "primary block")] });
      }
      return doneScreen("rate", t("nav.rate"), "star");
    }
    var tr = queue[0];
    var p = promptById(tr.prompt) || { id: tr.prompt, lang: "en", text: tr.prompt, origin: "" };
    var verdict = null;
    var fixTa = el("textarea", { rows: 3, lang: "pap", spellcheck: "false", "aria-label": t("rate.fix_box"), value: tr.text });
    var fixPanel = checkerPanel(fixTa);
    var fixBox = el("div", { class: "stack", hidden: true }, el("label", { class: "label-strong" }, t("rate.fix_box")), fixTa, fixPanel.node);
    var saveBtn = button(t("common.save"), submit, "primary block", { disabled: true });
    function update() {
      saveBtn.disabled = !verdict || (verdict === "fix" && (!Checker.normalise(fixTa.value) || Checker.normalise(fixTa.value) === tr.text));
    }
    fixTa.addEventListener("input", update);
    var seg = choiceGroup("rate", [{ value: "good", icon: "check", label: t("rate.good") }, { value: "fix", icon: "pen", label: t("rate.fix") }],
      function (e) { verdict = e.target.value; fixBox.hidden = verdict !== "fix"; if (!fixBox.hidden) fixTa.focus(); update(); });
    var comment = el("textarea", { rows: 2, class: "comment", "aria-label": t("common.comment"), placeholder: t("common.comment") });
    var flags = Checker.check(tr.text, P, { unknownWords: false });

    function finish(fixText, kept) {
      persist(saveBtn, function () {
        return saveRating(tr, verdict, fixText, kept, Checker.normalise(comment.value));
      }, function () { savedSheet(el("p", null, t("feedback.rated")), render); },
      function () { finish(fixText, kept); });
    }
    function submit() {
      if (verdict === "fix") checkThenSave(fixTa, finish);
      else finish(null, []);
    }

    return taskFrame({
      title: t("nav.rate"), icon: "star", done: ratedByMe, total: ratedByMe + Math.max(queue.length, rateCount()),
      onSkip: function () { session.skipped.rate.add(tr.id); render(); },
      body: el("div", { class: "stack" },
        promptCard(p),
        el("div", { class: "candidate-card" },
          el("p", { class: "muted small" }, t("rate.by")),
          el("p", { class: "candidate", lang: "pap", "data-autofocus": true, tabindex: "-1" }, tr.text),
          flags.length ? el("div", { class: "flags" }, el("span", { class: "muted small" }, t("rate.flags")),
            flags.map(function (f) { return correction(f); })) : null),
        el("p", { class: "lead" }, t("rate.intro")),
        seg, fixBox, comment),
      actions: [saveBtn]
    });
  }

  // ------------------------------------------------------------------ board

  // Words with two answers, and sentences with at least one rating. Built from
  // the answers, not the word list, so it stays quick with thousands of words.
  function boardItems() {
    var groups = {}, keys = [];
    state.answers.forEach(function (a) {
      var k = a.kind + ":" + a.item;
      if (!groups[k]) { groups[k] = []; keys.push(k); }
      groups[k].push(a);
    });
    var words = [];
    keys.forEach(function (k) {
      var a = groups[k], w = wordById(a[0].item);
      if (a.length >= 2 && w) words.push({ kind: a[0].kind, item: a[0].item, word: w, answers: a });
    });
    words.sort(function (x, y) { return (x.kind === "review" ? 0 : 1) - (y.kind === "review" ? 0 : 1); });
    var rated = new Set(state.ratings.map(function (r) { return r.translation; }));
    return words.concat(state.translations.filter(function (tr) { return rated.has(tr.id); })
      .map(function (tr) { return { kind: "sentence", item: tr.id, tr: tr }; }));
  }

  function boardCount() {
    if (LIVE) return (live.qs && live.qs.board_open) || 0;
    return boardItems().filter(function (x) { return !decisionFor(x.kind, x.item); }).length;
  }

  function involved(x) {
    var ids = [];
    if (x.answers) ids = x.answers.map(function (a) { return a.by; });
    if (x.tr) ids = [x.tr.by].concat(ratingsOf(x.tr.id).map(function (r) { return r.by; }));
    return ids.indexOf(state.current) >= 0;
  }

  function badge(status) {
    var map = { agree: ["ok", t("board.agree")], differ: ["bad", t("board.differ")], not_enough: ["muted", t("board.not_enough")] };
    var m = map[status] || map.not_enough;
    return el("span", { class: "badge " + m[0] }, m[1]);
  }

  function verdictText(v) {
    if (!v) return "—";
    if (v.verdict === "correct") return el("span", { class: "v ok" }, icon("check"), t("review.correct"));
    if (v.verdict === "unsure") return el("span", { class: "v muted" }, icon("help"), t("review.unsure"));
    return el("span", { class: "v bad" }, icon("close"), el("span", null, v.fix));
  }

  function chooser(name, candidates, preset, lang) {
    var own = el("input", { type: "text", lang: lang || null, "aria-label": t("board.write_own"), placeholder: t("board.write_own") });
    var ownRadio = el("input", { type: "radio", name: name, value: "own" });
    own.addEventListener("input", function () { ownRadio.checked = true; });
    return {
      node: el("div", { class: "chooser" }, candidates.map(function (c, i) {
        return el("label", { class: "choice" },
          el("input", { type: "radio", name: name, value: String(i), checked: preset === i }),
          el("span", { lang: lang || null }, c.label));
      }), el("label", { class: "choice own" }, ownRadio, own)),
      value: function (root) {
        var picked = root.querySelector("input[name='" + name + "']:checked");
        if (!picked) return null;
        if (picked.value === "own") return { value: normGloss(own.value), from: "board" };
        return candidates[Number(picked.value)];
      }
    };
  }

  function decide(x, outcome, values, btn) {
    persist(btn, function () { return saveDecision(x, outcome, values); },
      function () { decidedSheet(outcome); }, function () { decide(x, outcome, values, btn); });
  }

  function decidedSheet(outcome) {
    showSheet({ tone: outcome === "disputed" ? "warn" : "ok", icon: outcome === "disputed" ? "alert" : "check",
      title: outcome === "disputed" ? t("board.disputed_saved") : t("board.decision_saved"),
      body: el("p", null, t("board.goes_to_pr")),
      actions: [button(t("common.continue"), function () { closeSheet(); session.boardSel = null; go("board"); }, "primary block")] });
  }

  function itemTitle(x) {
    if (x.kind === "sentence") { var p = promptById(x.tr.prompt); return x.tr.text + (p ? "" : ""); }
    return x.word.lemma;
  }

  function itemKey(x) { return x.kind + ":" + x.item; }

  function viewBoard(args) {
    if (!me().board) return emptyState("shield", t("board.not_member"), null, [button(t("summary.home"), function () { go("home"); }, "primary")]);
    var items = boardItems();
    var open = items.filter(function (x) { return !decisionFor(x.kind, x.item); });
    var closed = items.filter(function (x) { return decisionFor(x.kind, x.item); });
    var list = session.boardTab === "open" ? open : closed;
    var selKey = args && args.length >= 2 ? args[0] + ":" + args[1] : null;
    var sel = selKey ? items.filter(function (x) { return itemKey(x) === selKey; })[0] : null;
    var kindLabel = { review: t("board.words_review"), translate: t("board.words_translate"), sentence: t("board.sentences") };
    var kindIcon = { review: "book", translate: "languages", sentence: "chat" };

    var listPane = el("section", { class: "queue" + (sel ? " has-sel" : "") },
      el("div", { class: "queue-head" },
        el("p", { class: "muted small" }, t("board.intro")),
        el("div", { class: "seg-tabs", role: "tablist" },
          [["open", t("board.tab_open"), open.length], ["closed", t("board.decided"), closed.length]].map(function (tb) {
            return el("button", { type: "button", role: "tab", "aria-selected": session.boardTab === tb[0] ? "true" : "false",
              onclick: function () { session.boardTab = tb[0]; go("board"); } }, tb[1], el("span", { class: "count" }, tb[2]));
          }))),
      list.length ? el("ul", { class: "queue-list" }, list.map(function (x) {
        var d = decisionFor(x.kind, x.item);
        return el("li", null, el("a", { class: "queue-row" + (sel && itemKey(sel) === itemKey(x) ? " selected" : ""),
            href: "#/board/" + x.kind + "/" + encodeURIComponent(x.item) },
          el("span", { class: "mode-icon small " + (x.kind === "sentence" ? "sun" : x.kind === "review" ? "blue" : "teal") }, icon(kindIcon[x.kind])),
          el("span", { class: "grow" }, el("strong", { lang: "pap" }, itemTitle(x)),
            el("span", { class: "muted small" }, kindLabel[x.kind] + (involved(x) ? " · " + t("board.yours") : ""))),
          d ? el("span", { class: "badge " + (d.outcome === "disputed" ? "bad" : "ok") }, d.outcome === "disputed" ? t("board.dispute") : t("board.decided"))
            : itemOutcome(x) === "not_enough" ? el("span", { class: "badge muted" }, t("board.incomplete")) : badge(itemOutcome(x)),
          icon("chevron", "chev")));
      })) : emptyState("shield", t("board.empty_title"), t("board.empty")));

    var detail = sel ? el("section", { class: "detail" },
      el("a", { class: "back-link", href: "#/board" }, icon("back"), t("board.back")),
      sel.kind === "sentence" ? boardSentenceDetail(sel) : boardWordDetail(sel)) :
      el("section", { class: "detail placeholder" }, emptyState("shield", t("board.pick"), null));
    return el("div", { class: "board" + (sel ? " show-detail" : "") }, listPane, detail);
  }

  function decisionFooter(x, onSave, saveLabel) {
    var err = el("p", { class: "field-error", role: "alert", hidden: true });
    var disputeBtn = button(t("board.dispute"), function () { decide(x, "disputed", null, disputeBtn); }, "ghost");
    var saveBtn = button(saveLabel, function () {
      var msg = onSave(saveBtn);
      if (msg) { err.replaceChildren(icon("alert"), el("span", null, msg)); err.hidden = false; }
      else err.hidden = true;
    }, "primary");
    return el("div", { class: "decision-bar" }, err, el("div", { class: "decision-actions" }, disputeBtn, saveBtn));
  }

  function decidedNote(done, x) {
    return el("div", { class: "decided-box" },
      el("p", null, icon("check"), el("strong", null, t("board.decided") + " · " + person(done.by).name)),
      el("p", { class: "muted small" }, done.outcome === "disputed" ? t("board.dispute") :
        x.kind === "sentence" ? (done.values && done.values.pap ? done.values.pap.value : "") :
        LANGS.map(function (l) { return l.toUpperCase() + ": " + ((done.values && done.values[l] && done.values[l].value) || "—"); }).join(" · ")),
      done.exported_in ? el("p", { class: "muted small" }, t("board.exported")) :
      LIVE && done.by !== state.current ? null :
      button(t("board.undo"), function (ev) {
        var restore = busy(ev.currentTarget, t("common.saving"));
        undoDecision(done).then(function () { render(); toast(t("toast.undone"), "info"); },
                                function (err) { restore(); failSheet(err, render); });
      }, "ghost small"));
  }

  function boardWordDetail(x) {
    var w = x.word;
    var done = decisionFor(x.kind, x.item);
    var choosers = {};
    var table = el("table", { class: "cmp" },
      el("thead", null, el("tr", null, el("th", null, ""),
        x.kind === "review" ? el("th", null, t("review.draft")) : null,
        x.answers.map(function (a, i) { return el("th", null, t("board.answer", { i: i + 1 }), el("span", { class: "who" }, person(a.by).name)); }),
        el("th", null, ""))),
      el("tbody", null, LANGS.map(function (lang) {
        var oc = x.kind === "review" ? reviewOutcome(x.answers, lang, w[lang]) : translateOutcome(x.answers, lang);
        var cands = [];
        if (x.kind === "review" && w[lang]) cands.push({ label: w[lang] + " · " + t("review.draft"), value: w[lang], from: "machine" });
        x.answers.forEach(function (a) {
          var v = x.kind === "review" ? (a.verdicts[lang].verdict === "wrong" ? a.verdicts[lang].fix : "") : (a.unknown ? "" : a.values[lang]);
          if (!v) return;
          var same = cands.filter(function (c) { return senseKey(c.value) === senseKey(v); })[0];
          if (!same) cands.push({ label: v, value: v, from: [a.by] });
          else if (Array.isArray(same.from)) same.from.push(a.by);
        });
        var preset = -1;
        if (oc.status === "agree") cands.forEach(function (c, i) { if (senseKey(c.value) === senseKey(oc.value || "")) preset = i; });
        choosers[lang] = chooser(x.item + "-" + lang, cands, preset, lang);
        return el("tr", null,
          el("th", { scope: "row" }, lang.toUpperCase()),
          x.kind === "review" ? el("td", { lang: lang }, w[lang] || "—") : null,
          x.answers.map(function (a) {
            return el("td", { lang: lang }, x.kind === "review" ? verdictText(a.verdicts[lang]) : (a.unknown ? "(" + t("translate.unknown") + ")" : (a.values[lang] || "—")));
          }),
          el("td", null, badge(oc.status)));
      })));
    var card = el("article", { class: "detail-card" },
      el("div", { class: "word-title" }, el("h2", { class: "lemma", lang: "pap" }, w.lemma), el("span", { class: "chip muted" }, w.id)),
      pageCrop(w, "small", "(max-width: 560px)"),
      el("div", { class: "table-wrap" }, table));
    var comments = x.answers.filter(function (a) { return a.comment; });
    if (comments.length) card.appendChild(el("ul", { class: "comments" }, comments.map(function (a) { return el("li", null, person(a.by).name + ": " + a.comment); })));
    if (done) { card.appendChild(decidedNote(done, x)); return card; }
    if (involved(x)) { card.appendChild(el("p", { class: "note" }, icon("info"), el("span", null, t("board.own")))); return card; }
    card.appendChild(el("div", { class: "stack" },
      el("p", { class: "muted small" }, t("board.choose_each")),
      LANGS.map(function (lang) { return el("fieldset", { class: "field" }, el("legend", null, langName(lang)), choosers[lang].node); })));
    card.appendChild(decisionFooter(x, function (btn) {
      var values = {}, missing = false;
      LANGS.forEach(function (l) { values[l] = choosers[l].value(card); if (!values[l]) missing = true; });
      if (missing) return t("board.need_each");
      decide(x, "reviewed", values, btn);
      return null;
    }, t("board.decide")));
    return card;
  }

  function boardSentenceDetail(x) {
    var tr = x.tr;
    var p = promptById(tr.prompt);
    var rs = ratingsOf(tr.id);
    var oc = sentenceOutcome(tr);
    var done = decisionFor("sentence", tr.id);
    var cands = [{ label: tr.text, value: tr.text, translation: tr.id, from: tr.by }];
    rs.forEach(function (r) {
      var f = r.fix_translation ? translationById(r.fix_translation) : null;
      if (f) cands.push({ label: f.text, value: f.text, translation: f.id, from: f.by });
    });
    var ch = chooser(tr.id, cands, oc.status === "agree" ? 0 : -1, "pap");
    var card = el("article", { class: "detail-card" },
      p ? promptCard(p) : null,
      el("div", { class: "candidate-card" },
        el("p", { class: "muted small" }, person(tr.by).name, " · ", badge(oc.status)),
        el("p", { class: "candidate", lang: "pap" }, tr.text),
        tr.flags_kept.length ? el("p", { class: "note warn small" }, icon("alert"), el("span", null, t("sent.kept", { n: tr.flags_kept.length }) + " " +
          tr.flags_kept.map(function (f) { return "“" + f.text + "” (" + f.id + ")"; }).join(", "))) : null),
      el("h3", null, t("board.ratings")),
      el("ul", { class: "ratings" }, rs.map(function (r) {
        return el("li", null, avatar(person(r.by)), el("span", { class: "grow" }, el("strong", null, person(r.by).name),
          el("span", { class: "muted small" }, (r.verdict === "good" ? t("rate.good") : t("rate.fix")) + (r.comment ? " — " + r.comment : ""))),
          r.verdict === "good" ? el("span", { class: "badge ok" }, t("rate.good")) : el("span", { class: "badge bad" }, t("rate.fix")));
      })));
    if (done) { card.appendChild(decidedNote(done, x)); return card; }
    if (involved(x)) { card.appendChild(el("p", { class: "note" }, icon("info"), el("span", null, t("board.own")))); return card; }
    card.appendChild(el("fieldset", { class: "field" }, el("legend", null, t("board.choose_sentence")), ch.node));
    card.appendChild(decisionFooter(x, function (btn) {
      var v = ch.value(card);
      if (!v || !v.value) return t("board.need_each");
      if (v.from === "board") v.flags = summarise(Checker.check(v.value, P, {}));
      decide(x, "reviewed", { pap: v }, btn);
      return null;
    }, oc.status === "agree" ? t("board.confirm") : t("board.decide")));
    return card;
  }

  // ---------------------------------------------------------------- credits

  function creditRole(role) {
    return role === "board" ? t("nav.board") : role === "maintainer" ? t("role.maintainer") : "";
  }

  // Live: credits() returns names (or handles, for people who chose not to be
  // named) and counts. No email, no school.
  function liveCreditLists() {
    if (!live.creditsLoading && (!live.credits || Date.now() - (live.creditsAt || 0) > 60000) && !live.creditsError) loadCredits();
    if (!live.credits) {
      if (live.creditsError) {
        return [el("section", { class: "card" }, emptyState("alert", t("error.load_title"), t("error.load_body"),
          [button(t("common.retry"), function (ev) { busy(ev.currentTarget, t("common.loading")); loadCredits(); }, "primary")]))];
      }
      return [el("section", { class: "card", "aria-busy": "true" }, el("div", { class: "gate small", role: "status" },
        el("span", { class: "spinner big", "aria-hidden": "true" }), el("p", { class: "muted" }, t("common.loading"))))];
    }
    var row = function (c) {
      return el("li", { class: "person-row" }, avatar({ name: c.name, board: c.role === "board" }),
        el("span", { class: "grow" }, el("strong", null, c.name), creditRole(c.role) ? el("span", { class: "muted small" }, creditRole(c.role)) : null),
        el("span", { class: "muted small" }, t("credits.n", { n: c.contributions })));
    };
    var board = live.credits.filter(function (c) { return c.role === "board"; });
    var people = live.credits.filter(function (c) { return c.role !== "board"; });
    return [
      el("section", { class: "card" },
        el("h2", null, t("nav.board")),
        board.length ? el("ul", { class: "people" }, board.map(row)) : el("p", { class: "muted" }, t("credits.board_empty"))),
      el("section", { class: "card" },
        el("h2", null, t("credits.people")),
        el("p", { class: "muted small" }, t("credits.note")),
        people.length ? el("ul", { class: "people" }, people.map(row)) : el("p", { class: "muted" }, t("credits.empty")))
    ];
  }

  function viewCredits() {
    var r = myRecords();
    var rows = [
      ["book", t("count.review"), r.review.length], ["languages", t("count.translate"), r.translate.length],
      ["chat", t("count.sentences"), r.sentences.length], ["star", t("count.ratings"), r.ratings.length]
    ];
    if (me().board) rows.push(["shield", t("count.decisions"), r.decisions.length]);
    var byName = function (a, b) { return creditName(a).localeCompare(creditName(b)); };
    var board = state.people.filter(function (p) { return p.board; }).sort(byName);
    var people = state.people.filter(function (p) { return !p.board; }).sort(byName);
    var personRow = function (p) {
      return el("li", { class: "person-row" }, avatar(p),
        el("span", { class: "grow" }, el("strong", null, creditName(p)),
          el("span", { class: "muted small" }, t("role." + p.role) + (p.school ? " · " + p.school : ""))),
        el("span", { class: "muted small" }, t("credits.n", { n: myCount(p.id) })));
    };
    var yours = el("section", { class: "card" },
      el("h2", { "data-autofocus": true, tabindex: "-1" }, t("credits.yours")),
      el("ul", { class: "count-list" }, rows.map(function (x) {
        return el("li", null, icon(x[0]), el("span", { class: "grow" }, x[1]), el("strong", null, x[2]));
      })));
    if (LIVE) return el("div", { class: "stack-lg" }, yours, liveCreditLists());
    return el("div", { class: "stack-lg" },
      yours,
      el("section", { class: "card" },
        el("h2", null, t("nav.board")),
        board.length ? el("ul", { class: "people" }, board.map(personRow)) : el("p", { class: "muted" }, t("credits.board_empty"))),
      el("section", { class: "card" },
        el("h2", null, t("credits.people")),
        el("p", { class: "muted small" }, t("credits.note")),
        people.length ? el("ul", { class: "people" }, people.map(personRow)) : el("p", { class: "muted" }, t("credits.empty"))));
  }

  // ---------------------------------------------------------------- account

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
        var tr = translationById(d.item);
        if (!tr) return;
        var v = d.values && d.values.pap;
        var authorId = v ? (v.from === "board" ? d.by : v.from) : tr.by;
        var checked = ratingsOf(tr.id).filter(function (r) { return r.verdict === "good"; }).map(function (r) { return person(r.by).handle; });
        pairs.push({ id: "par-NEW", prompt_id: tr.prompt, pap: v ? v.value : tr.text,
                     translated_by: person(authorId).handle, checked_by: checked.join("; "),
                     status: d.outcome === "disputed" ? "disputed" : "reviewed", reviewed_by: d.outcome === "disputed" ? "" : reviewer,
                     licence: "CC0-1.0", notes: "contribution tool " + d.id });
      }
    });
    return { words: words, pairs: pairs };
  }

  function exportObject() {
    return {
      format: FORMAT,
      exported_at: now(),
      tool: { kind: "prototype", data_built_from_commit: SAMPLE.built_from_commit },
      licences: { words: "CC-BY-4.0", sentences: "CC0-1.0" },
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
    var a = el("a", { href: URL.createObjectURL(blob), download: "papiamento-contributions-" + today() + ".json" });
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    toast(t("toast.downloaded"));
  }

  function importFile(file) {
    var reader = new FileReader();
    reader.onload = function () {
      var added = 0, msg;
      try {
        var data = JSON.parse(reader.result);
        if (!data || data.format !== FORMAT) throw new Error("not a prototype export");
        ["people", "answers", "translations", "ratings", "decisions"].forEach(function (k) {
          var have = new Set(state[k].map(function (x) { return x.id; }));
          (data[k] || []).forEach(function (x) { if (x && x.id && !have.has(x.id)) { state[k].push(x); added++; } });
        });
        save();
        msg = t("export.imported", { n: added });
      } catch (e) {
        msg = t("error.import");
      }
      render();
      toast(msg, added ? "ok" : "bad");
    };
    reader.onerror = function () { toast(t("error.import"), "bad"); };
    reader.readAsText(file);
  }

  function tsvTable(rows, cols) {
    if (!rows.length) return el("p", { class: "muted small" }, t("export.none"));
    return el("div", { class: "table-wrap" }, el("table", { class: "tsv" },
      el("thead", null, el("tr", null, cols.map(function (c) { return el("th", null, c); }))),
      el("tbody", null, rows.map(function (r) { return el("tr", null, cols.map(function (c) { return el("td", null, r[c] || ""); })); }))));
  }

  // Live: my own records only, never anyone else's (a board member reads
  // everyone's answers, but this file holds only their own).
  function downloadMine() {
    var p = me(), mine = function (x) { return x.by === state.current; };
    var data = {
      format: "pap-contrib-mine/1",
      exported_at: now(),
      licences: { words: "CC-BY-4.0", sentences: "CC0-1.0" },
      profile: { handle: p.handle, name: p.name, credit: p.credit, occupation: p.role, school: p.school, role: p.db_role,
                 consent_version: p.consent_version },
      answers: state.answers.filter(mine),
      translations: state.translations.filter(mine),
      ratings: state.ratings.filter(mine),
      decisions: state.decisions.filter(mine)
    };
    var blob = new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" });
    var a = el("a", { href: URL.createObjectURL(blob), download: "my-papiamento-contributions-" + today() + ".json" });
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    toast(t("toast.downloaded"));
  }

  function languageCard() {
    return el("section", { class: "card stack" },
      el("h2", null, t("lang.label")),
      el("div", { class: "seg-tabs", role: "group" }, [["en", "English"], ["pap", "Papiamento (draft)"]].map(function (l) {
        return el("button", { type: "button", "aria-pressed": state.ui_lang === l[0] ? "true" : "false",
          onclick: function () { state.ui_lang = l[0]; save(); render(); } }, l[1]);
      })),
      state.ui_lang === "pap" ? el("p", { class: "muted small" }, t("lang.pap_note")) : null);
  }

  function viewAccountLive() {
    var p = me();
    var r = myRecords();
    var credit = el("input", { type: "checkbox", id: "acc-credit", checked: p.credit, onchange: function () {
      var want = credit.checked;
      credit.disabled = true;
      db(live.client.from("profiles").update({ credit: want }).eq("id", p.id)).then(function () {
        p.credit = want; credit.disabled = false; live.credits = null; toast(t("toast.saved"));
      }, function () {
        credit.checked = !want; credit.disabled = false; toast(t("error.save_title"), "bad");
      });
    } });
    return el("div", { class: "stack-lg" },
      el("section", { class: "card profile" },
        avatar(p),
        el("div", { class: "grow" }, el("h2", { "data-autofocus": true, tabindex: "-1" }, p.name),
          el("p", { class: "muted small" }, t("role." + p.role) + (p.school ? " · " + p.school : "") + " · " + p.handle),
          el("div", { class: "chips" }, el("span", { class: "chip" }, "Words: CC BY 4.0"), el("span", { class: "chip" }, "Sentences: CC0 1.0"),
            p.board ? el("span", { class: "chip lang" }, t("nav.board")) : null))),
      languageCard(),
      el("section", { class: "card stack" },
        el("h2", null, t("nav.credits")),
        el("label", { class: "switch-row" }, credit, el("span", { class: "switch", "aria-hidden": "true" }), el("span", null, t("consent.credit")))),
      el("section", { class: "card stack" },
        el("h2", null, t("account.data_title")),
        el("p", { class: "muted" }, t("account.mine_intro")),
        el("p", { class: "small" }, t("export.counts", { a: r.review.length + r.translate.length, t: r.sentences.length, r: r.ratings.length, d: r.decisions.length })),
        el("div", { class: "row-actions" }, button([icon("download"), t("account.download_mine")], downloadMine, "primary"))),
      el("section", { class: "card stack prose" },
        el("h2", null, t("about.live_title")),
        el("p", null, "Teachers and linguists check and add translations and write sentences here, without a GitHub account. " +
          "Two people answer each item on their own; a review-board member checks the answers. Each week a job turns the board's " +
          "decisions into one pull request on GitHub, which the board member approves there. Contributors are credited by name, " +
          "or by handle if they prefer."),
        el("p", null, "Your email address is used only to send you sign-in codes. It is never published, and other contributors never see it."),
        el("ul", null,
          el("li", null, "Check translations: " + SAMPLE.review.length + " machine-drafted rows from lexicon/words/, with a crop of the printed AB 2018 word-list page."),
          el("li", null, "Translate words: " + SAMPLE.translate.length + " rows with no translation. Order: " + SAMPLE.translate_order + "."),
          el("li", null, "Translate sentences: " + SAMPLE.prompts.length + " English and Spanish prompts (CC0). No Papiamento is shown or prefilled."),
          el("li", null, "Live checks: " + CHECKS.rules.length + " rules, " + CHECKS.barbarismos.length + " barbarismos, " +
            CHECKS.variants.length + " Curaçao-Aruba pairs and the AB 2018 word list.")),
        el("p", null, "Data built from repository commit " + (SAMPLE.built_from_commit || "?") + ". ",
          el("a", { href: CONFIG.repo + "/blob/main/tools/contribute/DESIGN.md", target: "_blank", rel: "noopener" }, "How the tool works"), " · ",
          el("a", { href: CONFIG.repo, target: "_blank", rel: "noopener" }, "The dataset on GitHub"))),
      el("section", { class: "card" },
        button([icon("close"), t("account.sign_out")], function (ev) { signOut(ev.currentTarget); }, "block")));
  }

  function viewAccount() {
    if (LIVE) return viewAccountLive();
    var p = me();
    var pr = pullRequestPreview();
    var file = el("input", { type: "file", accept: "application/json,.json", id: "imp", class: "sr-only",
      onchange: function (e) { if (e.target.files[0]) importFile(e.target.files[0]); } });
    var who = el("select", { id: "who", "aria-label": t("person.switch"),
      onchange: function (e) {
        if (e.target.value === "__new") { session.onb = { step: 1, email: "", profile: null }; go("onboarding"); return; }
        state.current = e.target.value; save(); go("home");
      } },
      state.people.map(function (x) { return el("option", { value: x.id }, x.name + (x.board ? " (" + t("person.board_badge") + ")" : "")); }),
      el("option", { value: "__new" }, "+ " + t("person.new")));
    who.value = state.current;
    return el("div", { class: "stack-lg" },
      el("section", { class: "card profile" },
        avatar(p),
        el("div", { class: "grow" }, el("h2", { "data-autofocus": true, tabindex: "-1" }, p.name),
          el("p", { class: "muted small" }, t("role." + p.role) + (p.school ? " · " + p.school : "") + " · " + p.handle),
          el("div", { class: "chips" }, el("span", { class: "chip" }, "Words: CC BY 4.0"), el("span", { class: "chip" }, "Sentences: CC0 1.0"),
            p.board ? el("span", { class: "chip lang" }, t("nav.board")) : null))),
      languageCard(),
      el("section", { class: "card stack proto-card" },
        el("h2", null, t("person.switch")),
        el("p", { class: "muted small" }, t("person.switch_note")), who),
      el("section", { class: "card stack proto-card" },
        el("h2", null, t("sim.title")),
        el("p", { class: "muted small" }, t("sim.note")),
        el("div", { class: "seg-tabs", role: "group", "aria-label": t("sim.title") }, [["normal", t("sim.normal")], ["slow", t("sim.slow")], ["fail", t("sim.fail")]].map(function (m) {
          return el("button", { type: "button", "aria-pressed": (state.sim || "normal") === m[0] ? "true" : "false",
            onclick: function () { state.sim = m[0]; save(); render(); toast(t("sim.set", { mode: m[1] }), "info"); } }, m[1]);
        }))),
      el("section", { class: "card stack" },
        el("h2", null, t("export.title")),
        el("p", { class: "muted" }, t("export.intro")),
        el("p", { class: "small" }, t("export.counts", { a: state.answers.length, t: state.translations.length, r: state.ratings.length, d: state.decisions.length })),
        el("div", { class: "row-actions" },
          button([icon("download"), t("export.download")], download, "primary"),
          el("label", { class: "btn", for: "imp" }, icon("upload"), t("export.import")), file),
        el("p", { class: "muted small" }, t("export.import_note")),
        el("details", { class: "pr" }, el("summary", null, t("export.pr_title")),
          el("p", { class: "small" }, t("export.pr_note")),
          el("h3", null, "lexicon/words/<L>/words.tsv"),
          tsvTable(pr.words, ["id", "lemma", "en", "nl", "es", "translated_by", "status", "reviewed_by", "notes"]),
          el("h3", null, "corpus/parallel/pairs.tsv"),
          tsvTable(pr.pairs, ["id", "prompt_id", "pap", "translated_by", "checked_by", "status", "reviewed_by", "licence", "notes"]))),
      el("section", { class: "card stack prose" },
        el("h2", null, t("about.title")),
        el("p", null, "This is a clickable prototype of the contribution tool described in ", el("a", { href: "DESIGN.md" }, "DESIGN.md"),
          " (board card P2-09). It runs from a local file, sends nothing anywhere and stores answers only in this browser."),
        el("ul", null,
          el("li", null, "Check translations: " + SAMPLE.review.length + " machine-drafted rows from lexicon/words/, with a crop of the printed AB 2018 word-list page."),
          el("li", null, "Translate words: " + SAMPLE.translate.length + " rows with no translation. Order: " + SAMPLE.translate_order + "."),
          el("li", null, "Translate sentences: " + SAMPLE.prompts.length + " English and Spanish prompts written for this prototype only. No Papiamento is shown or prefilled."),
          el("li", null, "Live checks: " + CHECKS.rules.length + " rules from rules/rules.jsonl, " + CHECKS.barbarismos.length + " barbarismos, " +
            CHECKS.variants.length + " Curaçao-Aruba pairs and the AB 2018 word list."),
          el("li", null, "Data built from repository commit " + SAMPLE.built_from_commit + " by tools/contribute/build_sample.py.")),
        el("p", null, "The Papiamento interface text is a machine draft (pap_status = draft in ui-strings.tsv). Every word in it is an AB 2018 headword and no repo check fires on it, but a teacher must check its grammar and wording."),
        el("p", null, "Licences, as the maintainer decided on 2026-10-18: word translations CC BY 4.0 like the rest of the dataset; sentences and prompts CC0 1.0, so they can go to Common Voice.")),
      el("section", { class: "card danger" },
        button([icon("trash"), t("export.clear")], function () {
          if (!window.confirm(t("export.clear_confirm"))) return;
          state = blank(); save(); session = freshSession(); go("onboarding");
        }, "danger")));
  }

  // ------------------------------------------------------------------- boot

  window.addEventListener("hashchange", function () { closeSheet(); render(); });
  window.addEventListener("online", function () {
    if (LIVE && live.status === "error" && live.error === "offline") { startLive(); return; }
    render(); toast(t("toast.online"));
  });
  window.addEventListener("offline", function () { render(); toast(t(LIVE ? "offline.banner_live" : "offline.banner"), "bad"); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && document.querySelector(".sheet")) closeSheet();
  });
  if (LIVE) startLive(); else render();
})();

// Apply the saved appearance before the first paint, so the page never
// flashes light before turning dark. Light is the default; app.js owns the
// setting (Account > Appearance) and keeps it in the same storage key.
(function () {
  var pref = "light";
  try { pref = window.localStorage.getItem("pap-contrib-theme") || "light"; } catch (e) { /* storage blocked */ }
  var dark = pref === "dark" ||
    (pref === "system" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
})();

// Run every machine rule in rules/rules.jsonl with JavaScript's RegExp,
// the engine the Skirbi checker uses, against the same tests the Python
// validator runs. Python and JavaScript regexes differ in small ways; this
// makes sure a rule behaves the same in both.
//
// Usage: node tools/test_rules.mjs [path/to/rules.jsonl]   (exit 1 on any failure)

import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const path = process.argv[2] || join(root, "rules", "rules.jsonl");
if (!existsSync(path)) {
  console.log(`${path} not found; the machine rules are required`);
  process.exit(1);
}

let rules = 0;
let checks = 0;
const failures = [];
const lines = readFileSync(path, "utf8").split("\n");
lines.forEach((line, i) => {
  if (!line.trim()) return;
  const rule = JSON.parse(line);
  rules += 1;
  const where = `rules.jsonl:${i + 1} ${rule.rule_id}`;
  let rx;
  try {
    rx = new RegExp(rule.pattern, rule.flags || "");
  } catch (err) {
    failures.push(`${where}: pattern does not compile in JavaScript: ${err.message}`);
    return;
  }
  const hit = (text) => new RegExp(rule.pattern, rule.flags || "").test(text);
  const tests = rule.tests || {};
  for (const text of tests.match || []) {
    checks += 1;
    if (!hit(text)) failures.push(`${where}: does not catch ${JSON.stringify(text)}`);
  }
  for (const text of tests.no_match || []) {
    checks += 1;
    if (hit(text)) failures.push(`${where}: wrongly flags ${JSON.stringify(text)}`);
  }
  for (const d of rule.derived || []) {
    checks += 1;
    if ((d.expect === "match") !== hit(d.text)) {
      failures.push(`${where}: derived test ${JSON.stringify(d.text)} expected ${d.expect}`);
    }
  }
  for (const fx of tests.fix || []) {
    checks += 1;
    const got = fx.text.replace(new RegExp(rule.pattern, (rule.flags || "") + "g"), rule.replacement);
    if (got !== fx.expect) {
      failures.push(`${where}: fixing ${JSON.stringify(fx.text)} gives ${JSON.stringify(got)}, expected ${JSON.stringify(fx.expect)}`);
    }
  }
  void rx;
});

for (const f of failures) console.log(f);
console.log(`JavaScript rule tests: ${rules} rule(s), ${checks} check(s), ${failures.length} failure(s)`);
process.exit(failures.length ? 1 : 0);

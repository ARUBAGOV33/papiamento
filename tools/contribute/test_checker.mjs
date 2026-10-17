// Test the prototype's live checker (checker.js) against the repo's own data:
// every rule's "match" and "no_match" tests from rules/rules.jsonl, every
// barbarismo and every Curacao-Aruba pair. No Papiamento is made up here.
//
// Usage: node tools/contribute/test_checker.mjs   (after build_sample.py; exit 1 on failure)

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const require = createRequire(import.meta.url);
const checker = require(join(here, "checker.js"));

const sandbox = { window: {} };
vm.runInNewContext(readFileSync(join(here, "data", "checks.js"), "utf8"), sandbox);
const data = sandbox.window.CONTRIB_CHECKS;
const P = checker.prepare(data);

const failures = [];
let checks = 0;
const ids = (text) => checker.check(text, P).map((f) => f.kind === "rule" ? f.id : f.kind + ":" + f.id);

for (const line of readFileSync(join(root, "rules", "rules.jsonl"), "utf8").split("\n")) {
  if (!line.trim()) continue;
  const rule = JSON.parse(line);
  for (const text of rule.tests.match || []) {
    checks++;
    if (!ids(text).includes(rule.rule_id)) failures.push(`${rule.rule_id} does not flag ${JSON.stringify(text)}`);
  }
  for (const text of rule.tests.no_match || []) {
    checks++;
    if (ids(text).includes(rule.rule_id)) failures.push(`${rule.rule_id} flags ${JSON.stringify(text)}`);
  }
  for (const fx of rule.tests.fix || []) {
    checks++;
    let text = fx.text;
    for (let i = 0; i < 5; i++) {
      const f = checker.check(text, P).find((x) => x.kind === "rule" && x.id === rule.rule_id && x.fixes.length);
      if (!f) break;
      text = checker.applyFix(text, f, f.fixes[0]);
    }
    if (text !== fx.expect) failures.push(`${rule.rule_id} fixes ${JSON.stringify(fx.text)} to ${JSON.stringify(text)}, expected ${JSON.stringify(fx.expect)}`);
  }
}

for (const b of data.barbarismos) {
  checks++;
  // A rule on the same word may win over the barbarismo row (durmiendo is
  // caught by RULE_MOR_GERUND_004); either way the right form must be offered.
  const f = checker.check(b.wrong, P).find((x) =>
    (x.kind === "barbarismo" && x.id === b.id) || (x.start === 0 && x.end === b.wrong.length && b.right.some((r) => x.fixes.includes(r))));
  if (!f) failures.push(`barbarismo ${b.id} ${JSON.stringify(b.wrong)} is not flagged`);
}

for (const v of data.variants) {
  checks++;
  const f = checker.check(v.curacao, P).find((x) => x.kind === "variant" && x.id === v.id);
  if (!f) failures.push(`variant ${v.id} ${JSON.stringify(v.curacao)} is not flagged`);
  else if (f.fixes[0] !== v.aruba) failures.push(`variant ${v.id} suggests ${f.fixes[0]}, expected ${v.aruba}`);
}

// A sample of AB 2018 headwords must never be marked "not in the list".
const words = data.ab_words.split("\n").filter((w) => !w.includes(" "));
for (let i = 0; i < words.length; i += 97) {
  checks++;
  const f = checker.check(words[i], P, { unknownWords: true }).find((x) => x.kind === "unknown");
  if (f) failures.push(`AB headword ${JSON.stringify(words[i])} is marked unknown`);
}

if (failures.length) {
  console.log(failures.join("\n"));
  console.log(`\n${failures.length} of ${checks} checks failed`);
  process.exit(1);
}
console.log(`checker: ${checks} checks passed`);

// Check that the contribution tool's database is up: the sign-in service answers
// and a table can be read. When a Supabase project is paused it loses its address,
// so the website still loads but nobody can sign in (found on 5 November 2026).
//
//   SUPABASE_URL=... SUPABASE_SECRET_KEY=... node tools/contribute/supabase/check_database_up.mjs
//
// The workflow "Contribution database check" runs it three times a week. It reads
// at most one row id, prints no row and never prints the key. A database that is
// waking up gets a few more tries. Exit code 1 if it still does not answer.

const url = (process.env.SUPABASE_URL || "").replace(/\/+$/, "");
const key = process.env.SUPABASE_SECRET_KEY || "";
if (!url || !key) {
  console.log("SUPABASE_URL and SUPABASE_SECRET_KEY are not set; nothing to check.");
  process.exit(process.env.CI ? 1 : 0);
}

const TRIES = 5;
const WAIT_SECONDS = Number(process.env.CHECK_WAIT_SECONDS ?? 30);
const headers = { apikey: key, Authorization: "Bearer " + key };

const PROBES = [
  { label: "sign-in service", path: "/auth/v1/health" },
  { label: "tables", path: "/rest/v1/decisions?select=id&limit=1" },
];

function stop(message) {
  console.log("\nFAIL  " + message);
  if (process.env.GITHUB_ACTIONS) console.log("::error::" + message);
  process.exit(1);
}

async function ask(path) {
  try {
    const res = await fetch(url + path, { headers, signal: AbortSignal.timeout(30000) });
    await res.text(); // Only the status matters; the row itself is never printed.
    return res.status;
  } catch (err) {
    return err.message;
  }
}

for (const { label, path } of PROBES) {
  let answer;
  for (let attempt = 1; attempt <= TRIES; attempt++) {
    answer = await ask(path);
    if (answer === 200 || answer === 401 || answer === 403) break;
    console.log(`wait  ${label}: no answer yet (${answer}), try ${attempt} of ${TRIES}`);
    if (attempt < TRIES) await new Promise((done) => setTimeout(done, WAIT_SECONDS * 1000));
  }
  if (answer === 401 || answer === 403) {
    stop(`${label} refused the key (HTTP ${answer}). The database is up, but check the SUPABASE_SECRET_KEY secret.`);
  }
  if (answer !== 200) {
    stop(`${label} did not answer after ${TRIES} tries (${answer}). Teachers cannot sign in or save answers while this lasts. The project may be paused: open the Supabase dashboard, restore it, then run this check again.`);
  }
  console.log(`ok    ${label} answered (200)`);
}
console.log("\nThe contribution tool's database is up.");

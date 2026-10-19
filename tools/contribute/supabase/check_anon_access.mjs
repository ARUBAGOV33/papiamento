// Prove that the public (publishable) key alone, without signing in, can read
// and write nothing: no answers, sentences, ratings, decisions or profiles, no
// email addresses, and none of the app's functions.
//
// It needs only the two public values the website itself uses:
//   SUPABASE_URL=... SUPABASE_PUBLISHABLE_KEY=... node tools/contribute/supabase/check_anon_access.mjs
// The workflow "Contribution security check" runs it with the repository
// variables. It never prints the key. Exit code 1 if anything is readable.

const url = (process.env.SUPABASE_URL || "").replace(/\/+$/, "");
const key = process.env.SUPABASE_PUBLISHABLE_KEY || "";
if (!url || !key) {
  console.log("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are not set; nothing to check.");
  process.exit(process.env.CI ? 1 : 0);
}

const headers = { apikey: key, "Content-Type": "application/json" };
const failures = [];
let checks = 0;

// A request is safe when it is refused (401/403/404) or returns no rows.
async function expectNothing(label, path, init = {}) {
  checks++;
  let res;
  try {
    res = await fetch(url + path, { ...init, headers: { ...headers, ...(init.headers || {}) } });
  } catch (err) {
    failures.push(`${label}: request failed (${err.message})`);
    return;
  }
  const text = await res.text();
  let body = null;
  try { body = JSON.parse(text); } catch (e) { /* not JSON */ }
  const refused = [401, 403, 404].includes(res.status) ||
    (body && typeof body === "object" && !Array.isArray(body) && (body.code === "42501" || body.code === "PGRST202" || body.code === "PGRST106"));
  const empty = Array.isArray(body) && body.length === 0;
  const graphqlEmpty = body && body.data && Object.values(body.data).every((v) => !v || (v.edges && v.edges.length === 0));
  if (refused || empty || (path.startsWith("/graphql") && (graphqlEmpty || body.errors))) {
    console.log(`PASS  ${label} (${res.status})`);
  } else {
    failures.push(`${label}: HTTP ${res.status}, ${text.slice(0, 120)}`);
  }
}

// First make sure this is the real project: a wrong URL would refuse
// everything and look like a pass.
{
  const res = await fetch(url + "/auth/v1/settings", { headers }).catch((err) => ({ ok: false, status: err.message }));
  if (!res.ok) {
    console.log(`FAIL  cannot reach the Supabase project's public auth settings (${res.status}); check SUPABASE_URL`);
    process.exit(1);
  }
  console.log("ok    reached the Supabase project");
}

for (const table of ["profiles", "answers", "translations", "ratings", "decisions", "reserved_handles"]) {
  await expectNothing(`read ${table}`, `/rest/v1/${table}?select=*&limit=5`);
}
await expectNothing("write an answer", "/rest/v1/answers", {
  method: "POST", headers: { Prefer: "return=representation" },
  body: JSON.stringify({ kind: "review", ref: "pap-000001", body: {} }),
});
for (const fn of ["queue_state", "rate_queue", "rate_sentence", "credits", "create_profile"]) {
  await expectNothing(`call ${fn}`, `/rest/v1/rpc/${fn}`, { method: "POST", body: "{}" });
}
await expectNothing("list users (emails) through the auth admin API", "/auth/v1/admin/users");
await expectNothing("read answers through GraphQL", "/graphql/v1", {
  method: "POST", body: JSON.stringify({ query: "{ answersCollection(first: 5) { edges { node { id } } } }" }),
});
await expectNothing("read profiles through GraphQL", "/graphql/v1", {
  method: "POST", body: JSON.stringify({ query: "{ profilesCollection(first: 5) { edges { node { handle } } } }" }),
});

if (failures.length) {
  console.log("\nFAIL\n" + failures.map((f) => "  " + f).join("\n"));
  console.log(`\n${failures.length} of ${checks} checks failed: the public key can reach data it must not.`);
  process.exit(1);
}
console.log(`\nAll ${checks} checks passed: the public key alone reads and writes nothing.`);

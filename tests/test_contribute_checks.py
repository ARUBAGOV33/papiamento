"""Tests for the contribution tool's two outside checks, against a stand-in server:
tools/contribute/supabase/check_anon_access.mjs and check_database_up.mjs.

Skipped when Node.js is not installed. Run from the repo root:
python3 -m unittest discover -s tests -v
"""

import json
import os
import shutil
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ANON_CHECK = REPO / "tools" / "contribute" / "supabase" / "check_anon_access.mjs"
UP_CHECK = REPO / "tools" / "contribute" / "supabase" / "check_database_up.mjs"
KEY = "test-key-that-must-never-be-printed"


class StandIn:
    """A local server: answer(method, path) returns (status, body) for each request."""

    def __init__(self, answer):
        self.calls = []
        self.headers = []
        stand_in = self

        class Handler(BaseHTTPRequestHandler):
            def respond(self):
                length = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(length)
                stand_in.calls.append(self.path)
                stand_in.headers.append(dict(self.headers))
                status, body = answer(self.command, self.path)
                data = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = respond

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d" % self.server.server_port
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def closed_port_url():
    # A port nobody listens on behaves like a project whose address is gone.
    server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    url = "http://127.0.0.1:%d" % server.server_port
    server.server_close()
    return url


def run_check(script, **env):
    full = {"PATH": os.environ["PATH"], "CHECK_WAIT_SECONDS": "0"}
    full.update(env)
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, env=full, timeout=60)
    return result.returncode, result.stdout + result.stderr


def anon_server(table=(401, {}), graphql=(200, {"data": {"answersCollection": None}})):
    def answer(method, path):
        if path == "/auth/v1/settings":
            return 200, {"external": {"email": True}}
        if path.startswith("/graphql"):
            return graphql
        return table
    return StandIn(answer)


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class AnonAccessCheckTest(unittest.TestCase):
    def run_against(self, server):
        self.addCleanup(server.close)
        return run_check(ANON_CHECK, SUPABASE_URL=server.url, SUPABASE_PUBLISHABLE_KEY=KEY)

    def test_everything_refused_passes(self):
        code, out = self.run_against(anon_server())
        self.assertEqual(code, 0, out)
        self.assertIn("All 15 checks passed", out)
        self.assertNotIn(KEY, out)

    def test_waking_database_is_not_called_a_leak(self):
        # What happened on 5 November 2026: REST 404, GraphQL 503 while waking up.
        code, out = self.run_against(anon_server(table=(404, {}), graphql=(503, {"code": "PGRST002"})))
        self.assertEqual(code, 1, out)
        self.assertIn("2 of 15 checks got no answer", out)
        self.assertNotIn("can reach data", out)

    def test_all_server_errors_do_not_pass(self):
        code, out = self.run_against(anon_server(table=(503, {}), graphql=(503, {})))
        self.assertEqual(code, 1, out)
        self.assertIn("15 of 15 checks got no answer", out)
        self.assertNotIn("checks passed", out)

    def test_readable_table_is_a_leak(self):
        code, out = self.run_against(anon_server(table=(200, [{"id": 1}])))
        self.assertEqual(code, 1, out)
        self.assertIn("can reach data", out)

    def test_leak_wins_over_no_answer(self):
        code, out = self.run_against(anon_server(table=(200, [{"id": 1}]), graphql=(503, {})))
        self.assertEqual(code, 1, out)
        self.assertIn("can reach data", out)

    def test_unreachable_project_mentions_a_pause(self):
        code, out = run_check(ANON_CHECK, SUPABASE_URL=closed_port_url(), SUPABASE_PUBLISHABLE_KEY=KEY)
        self.assertEqual(code, 1, out)
        self.assertIn("may be paused", out)
        self.assertNotIn(KEY, out)


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class DatabaseUpCheckTest(unittest.TestCase):
    def run_against(self, answer, **env):
        server = StandIn(answer)
        self.addCleanup(server.close)
        code, out = run_check(UP_CHECK, SUPABASE_URL=server.url, SUPABASE_SECRET_KEY=KEY, **env)
        return code, out, server

    def test_up_passes_and_prints_no_row_or_key(self):
        code, out, server = self.run_against(lambda m, p: (200, [{"id": "row-content"}]))
        self.assertEqual(code, 0, out)
        self.assertIn("database is up", out)
        self.assertNotIn("row-content", out)
        self.assertNotIn(KEY, out)
        self.assertEqual(server.headers[0].get("apikey"), KEY)
        self.assertEqual(server.headers[0].get("Authorization"), "Bearer " + KEY)
        self.assertEqual(server.calls, ["/auth/v1/health", "/rest/v1/decisions?select=id&limit=1"])

    def test_waking_database_gets_more_tries(self):
        seen = []

        def answer(method, path):
            seen.append(path)
            return (200, {}) if len(seen) > 3 else (503, {"code": "PGRST002"})

        code, out, _ = self.run_against(answer)
        self.assertEqual(code, 0, out)
        self.assertIn("try 3 of 5", out)

    def test_not_found_while_waking_gets_more_tries(self):
        code, out, server = self.run_against(lambda m, p: (404, {}))
        self.assertEqual(code, 1, out)
        self.assertEqual(len(server.calls), 5)

    def test_still_down_fails_and_mentions_a_pause(self):
        code, out, server = self.run_against(lambda m, p: (503, {}))
        self.assertEqual(code, 1, out)
        self.assertIn("may be paused", out)
        self.assertEqual(len(server.calls), 5)

    def test_no_address_fails_and_mentions_a_pause(self):
        code, out = run_check(UP_CHECK, SUPABASE_URL=closed_port_url(), SUPABASE_SECRET_KEY=KEY)
        self.assertEqual(code, 1, out)
        self.assertIn("may be paused", out)
        self.assertNotIn(KEY, out)

    def test_refused_key_is_reported_at_once(self):
        code, out, server = self.run_against(lambda m, p: (401, {}))
        self.assertEqual(code, 1, out)
        self.assertIn("SUPABASE_SECRET_KEY", out)
        self.assertEqual(len(server.calls), 1)

    def test_github_actions_gets_an_error_line(self):
        code, out, _ = self.run_against(lambda m, p: (503, {}), GITHUB_ACTIONS="true")
        self.assertEqual(code, 1, out)
        self.assertIn("::error::", out)

    def test_missing_settings(self):
        code, out = run_check(UP_CHECK)
        self.assertEqual(code, 0, out)
        code, out = run_check(UP_CHECK, CI="true")
        self.assertEqual(code, 1, out)


if __name__ == "__main__":
    unittest.main()

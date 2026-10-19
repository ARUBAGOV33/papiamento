"""Tests for tools/contribute/build_site.py: the parts that decide what the
published site may contain. They need neither PyMuPDF nor the network.

Run from the repo root: python3 -m unittest discover -s tests -v
"""

import base64
import importlib.util
import json
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "contribute" / "build_site.py"
_spec = importlib.util.spec_from_file_location("build_site", str(TOOL))
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)  # type: ignore[union-attr]


def jwt(claims):
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "eyJhbGciOiJIUzI1NiJ9." + body + ".signature"


class TestKeys(unittest.TestCase):
    def test_publishable_key_is_accepted(self):
        self.assertEqual(bs.check_publishable_key(" sb_publishable_abc-DEF_123 "), "sb_publishable_abc-DEF_123")

    def test_legacy_anon_key_is_accepted(self):
        key = jwt({"role": "anon"})
        self.assertEqual(bs.check_publishable_key(key), key)

    def test_secret_keys_are_refused_without_echoing_them(self):
        for key in ("sb_secret_abcdef123456", jwt({"role": "service_role"})):
            with self.assertRaises(ValueError) as ctx:
                bs.check_publishable_key(key)
            self.assertNotIn(key, str(ctx.exception))
            self.assertIn("never be published", str(ctx.exception))

    def test_anything_else_is_refused(self):
        for key in ("", "hello", "sb_publishable_", "sb_publishable_has space", "a.b.c"):
            with self.assertRaises(ValueError):
                bs.check_publishable_key(key)


class TestUrl(unittest.TestCase):
    def test_project_url(self):
        self.assertEqual(bs.check_url("https://abcdefghijklmnopqrst.supabase.co/"), "https://abcdefghijklmnopqrst.supabase.co")

    def test_refused_urls(self):
        for url in ("", "http://x.supabase.co", "https://x.supabase.co/rest/v1", "https://u:p@x.supabase.co",
                    "https://x.supabase.co?x=1", "javascript:alert(1)"):
            with self.assertRaises(ValueError):
                bs.check_url(url)


class TestConfig(unittest.TestCase):
    def test_demo_needs_nothing(self):
        self.assertEqual(bs.site_config(False, "", "")["mode"], "demo")

    def test_live_config_and_policy(self):
        cfg = bs.site_config(True, "https://abc.supabase.co", "sb_publishable_x1")
        self.assertEqual(cfg["mode"], "live")
        self.assertEqual(cfg["supabaseJs"], bs.VENDOR_PATH)
        js = bs.config_js(cfg)
        self.assertTrue(js.rstrip().endswith(";"))
        self.assertEqual(json.loads(js.split("window.CONTRIB_CONFIG = ", 1)[1].rstrip().rstrip(";")), cfg)
        policy = bs.csp(cfg)
        self.assertIn("script-src 'self';", policy)
        self.assertIn("connect-src 'self' https://abc.supabase.co wss://abc.supabase.co", policy)
        self.assertNotIn("unsafe-eval", policy)

    def test_live_without_values_fails(self):
        with self.assertRaises(ValueError):
            bs.site_config(True, "", "")

    def test_pinned_library(self):
        self.assertRegex(bs.SUPABASE_JS["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn(bs.SUPABASE_JS["version"], bs.SUPABASE_JS["tarball"])
        self.assertTrue(bs.SUPABASE_JS["integrity"].startswith("sha512-"))


if __name__ == "__main__":
    unittest.main()

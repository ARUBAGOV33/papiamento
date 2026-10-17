"""Tests for tools/test_rules.mjs, the JavaScript run of the machine rules.

Skipped when Node.js is not installed. Run from the repo root:
python3 -m unittest discover -s tests -v
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "tools" / "test_rules.mjs"


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class RulesJsTest(unittest.TestCase):
    def run_node(self, *args):
        return subprocess.run(["node", str(RUNNER)] + list(args), capture_output=True, text=True)

    def test_missing_rules_file_fails(self):
        # It used to print "nothing to test" and exit 0.
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_node(str(Path(tmp) / "rules.jsonl"))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("not found", result.stdout)

    def test_repository_rules_pass(self):
        result = self.run_node()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("0 failure(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()

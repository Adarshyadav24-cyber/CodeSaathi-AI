"""Focused checks for the safe analysis and history core."""

import os
import tempfile
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from codesaathi.ai import get_explanation
from codesaathi.analyzer import EXAMPLES, analyze_code
from codesaathi.history import list_recent, save


class AnalyzerTests(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(analyze_code("  ").status, "empty")

    def test_invalid_python(self):
        result = analyze_code("for x in range(2)\n    print(x)")
        self.assertEqual(result.status, "syntax_error")
        self.assertEqual(result.line, 1)

    def test_valid_example_and_static_result(self):
        result = analyze_code("def greet(name):\n    return 'Hi ' + name\n")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.test_results[0]["status"], "Passed")
        self.assertIn("function", " ".join(result.tests))

    def test_possible_undefined_name(self):
        result = analyze_code("print(nam)")
        self.assertTrue(any(f.title == "Possible undefined name" for f in result.findings))

    def test_demo_fix_is_narrow_and_reviewable(self):
        result = analyze_code("name = 'Asha'\nprint(nam)")
        explanation = get_explanation("name = 'Asha'\nprint(nam)", result)
        self.assertIn("print(name)", explanation["corrected_code"])
        self.assertIn("Line 2", explanation["text"])

    def test_wrong_index_has_line_and_guarded_correction(self):
        source = EXAMPLES["Wrong list index"]
        result = analyze_code(source)
        explanation = get_explanation(source, result)
        self.assertTrue(any(f.title == "List index is out of range" and f.line == 2 for f in result.findings))
        self.assertIn("if len(colors) > 2", explanation["corrected_code"])
        self.assertIn("Line 2", explanation["text"])

    def test_zero_divisor_has_line_and_guarded_correction(self):
        source = EXAMPLES["Divide by zero"]
        result = analyze_code(source)
        explanation = get_explanation(source, result)
        self.assertTrue(any(f.title == "Division by zero" and f.line == 3 for f in result.findings))
        self.assertIn("if count == 0:", explanation["corrected_code"])
        self.assertIn("assigned the value 0 on line 2", " ".join(f.detail for f in result.findings))

    def test_missing_colon_gets_corrected_code(self):
        source = EXAMPLES["Missing colon"]
        explanation = get_explanation(source, analyze_code(source))
        self.assertIn("range(3):", explanation["corrected_code"])
        self.assertIn("Line 1", explanation["text"])

    def test_empty_and_size_limit_are_not_executed(self):
        self.assertEqual(analyze_code("x = 1\n" * 4000).status, "invalid")

    def test_demo_fallback_without_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            self.assertEqual(get_explanation("print('hi')", analyze_code("print('hi')"))["mode"], "Demo")

    def test_api_failure_uses_fallback(self):
        fake_openai = SimpleNamespace(OpenAI=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}), patch.dict(sys.modules, {"openai": fake_openai}):
            result = get_explanation("print(nam)", analyze_code("print(nam)"))
            self.assertEqual(result["mode"], "Demo fallback")
            self.assertIn("unavailable", result["notice"])

    def test_history_save_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.db"
            save(path, "demo", "print(1)", {"analysis": {"status": "ok"}})
            entries = list_recent(path)
            self.assertEqual(entries[0]["code"], "print(1)")
            self.assertEqual(entries[0]["result"]["analysis"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()

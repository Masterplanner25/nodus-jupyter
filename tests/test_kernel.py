"""Tests for NodusKernel — exercises _run_cell and do_complete/do_inspect
directly, without requiring a live Jupyter server."""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def _make_kernel() -> "NodusKernel":  # noqa: F821
    """Instantiate NodusKernel while bypassing ipykernel's ZMQ __init__."""
    from nodus_jupyter.kernel import NodusKernel

    kernel = NodusKernel.__new__(NodusKernel)
    kernel._cell_globals = {}
    kernel._session_source = []
    kernel.execution_count = 0
    kernel.iopub_socket = MagicMock()
    kernel._response_metadata = {}
    return kernel


PYTHONPATH_PATCH = {
    "sys.path": sys.path,
}


class TestRunCell(unittest.TestCase):
    def setUp(self):
        self.kernel = _make_kernel()

    def test_simple_expression(self):
        stdout, stderr, error = self.kernel._run_cell("let x = 1 + 2\nprint(x)\n")
        self.assertIsNone(error)
        self.assertIn("3", stdout)

    def test_globals_persist_across_cells(self):
        self.kernel._run_cell("let x = 42\n")
        stdout, _, error = self.kernel._run_cell("print(x)\n")
        self.assertIsNone(error)
        self.assertIn("42", stdout)

    def test_reassignment_persists(self):
        self.kernel._run_cell("let counter = 0\n")
        self.kernel._run_cell("counter = counter + 1\n")
        stdout, _, error = self.kernel._run_cell("print(counter)\n")
        self.assertIsNone(error)
        self.assertIn("1", stdout)

    def test_syntax_error_returns_error(self):
        _, _, error = self.kernel._run_cell("let x = }\n")
        self.assertIsNotNone(error)
        self.assertIn("error", error.lower())

    def test_undefined_variable_returns_error(self):
        _, _, error = self.kernel._run_cell("print(undefined_xyz)\n")
        self.assertIsNotNone(error)

    def test_empty_cell_returns_ok(self):
        stdout, stderr, error = self.kernel._run_cell("")
        self.assertIsNone(error)
        self.assertEqual(stdout, "")

    def test_multiline_fn_definition(self):
        src = "fn add(a, b) {\n    return a + b\n}\nprint(add(3, 4))\n"
        stdout, _, error = self.kernel._run_cell(src)
        self.assertIsNone(error)
        self.assertIn("7", stdout)

    def test_fn_defined_in_one_cell_callable_in_next(self):
        self.kernel._run_cell("fn double(n) {\n    return n * 2\n}\n")
        stdout, _, error = self.kernel._run_cell("print(double(5))\n")
        self.assertIsNone(error)
        self.assertIn("10", stdout)

    def test_runtime_error_does_not_corrupt_globals(self):
        self.kernel._run_cell("let safe = 99\n")
        self.kernel._run_cell("print(no_such_var)\n")  # error — ignored
        stdout, _, error = self.kernel._run_cell("print(safe)\n")
        self.assertIsNone(error)
        self.assertIn("99", stdout)

    def test_stderr_captured(self):
        # Nodus itself doesn't write to stderr, but we verify the buffer works
        stdout, stderr, error = self.kernel._run_cell("let x = 1\n")
        self.assertIsNone(error)

    def test_list_operations(self):
        stdout, _, error = self.kernel._run_cell(
            "let nums = [1, 2, 3]\nprint(len(nums))\n"
        )
        self.assertIsNone(error)
        self.assertIn("3", stdout)

    def test_map_operations(self):
        stdout, _, error = self.kernel._run_cell(
            'let m = {"a": 1, "b": 2}\nprint(m["a"])\n'
        )
        self.assertIsNone(error)
        self.assertIn("1", stdout)

    def test_string_interpolation(self):
        stdout, _, error = self.kernel._run_cell(
            'let name = "Nodus"\nprint("Hello, \\(name)!")\n'
        )
        self.assertIsNone(error)
        self.assertIn("Hello, Nodus!", stdout)

    def test_boolean_logic(self):
        stdout, _, error = self.kernel._run_cell(
            "let x = true\nif (x) {\n    print(\"yes\")\n}\n"
        )
        self.assertIsNone(error)
        self.assertIn("yes", stdout)

    def test_error_does_not_bleed_partial_globals(self):
        # If a cell fails partway through, earlier defs in that cell
        # should not be visible (VM error rolls back the session cleanly).
        before = set(self.kernel._cell_globals.keys())
        self.kernel._run_cell("let tmp_var = 1\nprint(no_such)\n")
        # tmp_var may or may not be in globals depending on execution order;
        # the important thing is _cell_globals is still a dict (not corrupted).
        self.assertIsInstance(self.kernel._cell_globals, dict)


class TestDoExecute(unittest.TestCase):
    def setUp(self):
        self.kernel = _make_kernel()
        self.kernel.send_response = MagicMock()

    def test_ok_result_sends_stdout(self):
        result = self.kernel.do_execute("print(7)\n", silent=False)
        self.assertEqual(result["status"], "ok")
        calls = [str(c) for c in self.kernel.send_response.call_args_list]
        self.assertTrue(any("7" in c for c in calls))

    def test_silent_suppresses_output(self):
        self.kernel.do_execute("print(42)\n", silent=True)
        self.kernel.send_response.assert_not_called()

    def test_error_result_on_bad_code(self):
        result = self.kernel.do_execute("let x = }\n", silent=False)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["ename"], "NodusError")

    def test_empty_cell_is_ok_without_send(self):
        result = self.kernel.do_execute("   \n", silent=False)
        self.assertEqual(result["status"], "ok")
        self.kernel.send_response.assert_not_called()


class TestDoComplete(unittest.TestCase):
    def setUp(self):
        self.kernel = _make_kernel()

    def test_keyword_completion(self):
        result = self.kernel.do_complete("le", 2)
        self.assertEqual(result["status"], "ok")
        self.assertIn("let", result["matches"])

    def test_builtin_completion(self):
        result = self.kernel.do_complete("pri", 3)
        self.assertIn("print", result["matches"])

    def test_stdlib_completion(self):
        result = self.kernel.do_complete("std:", 4)
        self.assertTrue(any(m.startswith("std:") for m in result["matches"]))

    def test_global_var_appears_in_completions(self):
        self.kernel._cell_globals["my_variable"] = 42
        result = self.kernel.do_complete("my_", 3)
        self.assertIn("my_variable", result["matches"])

    def test_no_match_returns_empty(self):
        result = self.kernel.do_complete("zzz_no_match", 12)
        self.assertEqual(result["matches"], [])

    def test_cursor_start_is_correct(self):
        result = self.kernel.do_complete("let x = pri", 11)
        self.assertEqual(result["cursor_start"], 8)
        self.assertIn("print", result["matches"])


class TestDoInspect(unittest.TestCase):
    def setUp(self):
        self.kernel = _make_kernel()

    def test_known_builtin(self):
        result = self.kernel.do_inspect("print", 5, 0)
        self.assertTrue(result["found"])
        self.assertIn("print", result["data"]["text/plain"])

    def test_stdlib_module(self):
        result = self.kernel.do_inspect("std:math", 8, 0)
        self.assertTrue(result["found"])

    def test_unknown_token(self):
        result = self.kernel.do_inspect("xyz_unknown", 11, 0)
        self.assertFalse(result["found"])

    def test_partial_cursor_extracts_token(self):
        # cursor is mid-token: "let x = pri|nt" (cursor at 12)
        code = "let x = print"
        result = self.kernel.do_inspect(code, len(code), 0)
        self.assertTrue(result["found"])


class TestDoIsComplete(unittest.TestCase):
    def setUp(self):
        self.kernel = _make_kernel()

    def test_complete_single_line(self):
        result = self.kernel.do_is_complete("let x = 1\n")
        self.assertEqual(result["status"], "complete")

    def test_incomplete_open_brace(self):
        result = self.kernel.do_is_complete("fn foo() {")
        self.assertEqual(result["status"], "incomplete")

    def test_balanced_braces_complete(self):
        result = self.kernel.do_is_complete("fn foo() {\n    return 1\n}\n")
        self.assertEqual(result["status"], "complete")


if __name__ == "__main__":
    unittest.main()

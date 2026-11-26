import contextlib
import io
import os
import tempfile
import unittest
import unittest.mock

from rmcm import clean_source, main, remove_comments_and_docstrings


class DocstringRemovalTests(unittest.TestCase):
    def test_removes_docstrings_in_all_supported_scopes(self):
        source = '''"""module"""
class Example:
    r"""class"""

    def method(self):
        'method'
        return 1

async def other():
    """async"""
    return 2
'''
        self.assertEqual(
            remove_comments_and_docstrings(source),
            "class Example:\n\n    def method(self):\n\n        return 1\n\nasync def other():\n\n    return 2\n",
        )

    def test_preserves_non_docstring_strings(self):
        source = '''value = """assigned"""
"""not a docstring"""
items = [
    """item""",
]
def function():
    f"""not a docstring {1}"""
    if True:
        """not a docstring"""
'''
        self.assertEqual(
            remove_comments_and_docstrings(source),
            source,
        )

    def test_removes_multiline_and_parenthesized_docstrings(self):
        source = '''def function():
    (
        """first line
        second line"""
    )
    return 1
'''
        self.assertEqual(
            remove_comments_and_docstrings(source),
            "def function():\n\n    return 1\n",
        )

    def test_preserves_multiline_string_contents(self):
        source = 'x = """a\n\n\nb   \nc"""\n'
        self.assertEqual(remove_comments_and_docstrings(source), source)

    def test_inserts_pass_for_docstring_only_bodies(self):
        source = (
            'def f():\n    """doc"""\n\n'
            'class C:\n    """doc"""\n\n'
            'async def g():\n    """doc"""\n'
        )
        cleaned = remove_comments_and_docstrings(source)
        compile(cleaned, "<test>", "exec")
        self.assertNotIn("doc", cleaned)
        self.assertEqual(cleaned.count("pass"), 3)

    def test_inserts_pass_for_parenthesized_docstring_only_body(self):
        source = 'def f():\n    (\n        """doc"""\n    )\n'
        self.assertEqual(
            remove_comments_and_docstrings(source),
            "def f():\n    pass\n",
        )

    def test_preserves_inline_docstring_suite(self):
        source = 'def f(): """doc"""; return 1\n'
        cleaned = remove_comments_and_docstrings(source)
        compile(cleaned, "<test>", "exec")
        self.assertEqual(cleaned, "def f(): return 1\n")

    def test_preserves_shebang_and_encoding_cookie(self):
        source = (
            "#!/usr/bin/env python3\n"
            "# -*- coding: utf-8 -*-\n"
            "# gone\n"
            "print(1)\n"
        )
        self.assertEqual(
            remove_comments_and_docstrings(source),
            "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\nprint(1)\n",
        )

    def test_raises_on_invalid_syntax(self):
        with self.assertRaises(SyntaxError):
            remove_comments_and_docstrings("def (:\n")


class OtherLanguageTests(unittest.TestCase):
    def test_c_removes_both_comment_forms_and_preserves_string_markers(self):
        source = 'char *url = "https://example.test/a/*b*/"; // line\nint x; /* block\ncomment */\n'
        cleaned = clean_source(source, "c")
        self.assertIn('"https://example.test/a/*b*/"', cleaned)
        self.assertNotIn("line", cleaned)
        self.assertNotIn("block", cleaned)
        self.assertEqual(cleaned.count("\n"), source.count("\n"))

    def test_css_removes_block_comments_and_preserves_string_markers(self):
        source = 'a { content: "/* keep */"; /* remove */ color: red; }\n'
        cleaned = clean_source(source, "css")
        self.assertIn('"/* keep */"', cleaned)
        self.assertNotIn("remove", cleaned)
        self.assertIn("color: red", cleaned)


class CliTests(unittest.TestCase):
    def test_print_has_no_extra_blank_line(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("# c\nx = 1\n")
            path = f.name
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = main(["-i", path, "-p"])
        finally:
            os.unlink(path)
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue(), "x = 1\n")

    def test_reads_from_stdin(self):
        buf = io.StringIO()
        with unittest.mock.patch("sys.stdin", io.StringIO("# c\nx = 1\n")):
            with contextlib.redirect_stdout(buf):
                code = main(["-i", "-", "-p"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue(), "x = 1\n")

    def test_help_lists_all_options(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit) as result:
            main(["--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertIn("--input INPUT", buf.getvalue())
        self.assertIn("--output OUTPUT", buf.getvalue())
        self.assertIn("--overwrite", buf.getvalue())
        self.assertIn("--print", buf.getvalue())
        self.assertIn("--python", buf.getvalue())
        self.assertIn("-c", buf.getvalue())
        self.assertIn("--css", buf.getvalue())

    def test_c_cli_selector_writes_cleaned_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = os.path.join(directory, "input.c")
            output_path = os.path.join(directory, "output.c")
            with open(source_path, "w", encoding="utf-8") as f:
                f.write("int value = 1; // remove\n")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["-c", "-i", source_path, "-o", output_path])
            self.assertEqual(code, 0)
            with open(output_path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "int value = 1;          \n")

    def test_python_selector_and_implicit_default(self):
        for selector in ([], ["--python"], ["--lang", "python"]):
            with tempfile.TemporaryDirectory() as directory:
                source_path = os.path.join(directory, "input.py")
                output_path = os.path.join(directory, "output.py")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write("# remove\nx = 1\n")
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(selector + ["-i", source_path, "-o", output_path])
                self.assertEqual(code, 0)
                with open(output_path, encoding="utf-8") as f:
                    self.assertEqual(f.read(), "x = 1\n")


if __name__ == "__main__":
    unittest.main()

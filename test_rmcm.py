import unittest

from rmcm import remove_comments_and_docstrings


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


if __name__ == "__main__":
    unittest.main()

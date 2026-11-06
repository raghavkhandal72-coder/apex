import unittest

from apex_council.lint.rules import lint_source


def codes(src):
    return sorted(d["code"]["value"] for d in lint_source(src, "x.py"))


class LintTests(unittest.TestCase):
    def test_bare_except(self):
        self.assertEqual(codes("try:\n    pass\nexcept:\n    pass\n"), ["APX001"])

    def test_mutable_default(self):
        self.assertEqual(codes("def f(a=[]):\n    pass\n"), ["APX002"])
        self.assertEqual(codes("def f(a=None):\n    pass\n"), [])

    def test_secret_real_vs_placeholder(self):
        self.assertEqual(codes('API_KEY = "sk-abcdefghijklmnopqrstuvwxyz"\n'), ["APX003"])
        self.assertEqual(codes('password = "hunter2hunter2"\n'), ["APX003"])
        self.assertEqual(codes('api_key = "your_api_key_here"\n'), [])
        self.assertEqual(codes('token = ""\n'), [])

    def test_eval_and_shell(self):
        self.assertEqual(codes("eval(x)\n"), ["APX004"])
        self.assertEqual(codes("import os\nos.system('ls')\n"), ["APX005"])
        self.assertEqual(codes("import subprocess\nsubprocess.run('ls', shell=True)\n"), ["APX005"])
        self.assertEqual(codes("import subprocess\nsubprocess.run(['ls'])\n"), [])

    def test_assert_tuple(self):
        self.assertEqual(codes("assert (x, 'msg')\n"), ["APX006"])
        self.assertEqual(codes("assert x, 'msg'\n"), [])

    def test_syntax_error_reported_not_raised(self):
        self.assertEqual(codes("def (:\n"), ["APX000"])

    def test_clean_code_is_clean(self):
        self.assertEqual(codes("def add(a, b):\n    return a + b\n"), [])


if __name__ == "__main__":
    unittest.main()

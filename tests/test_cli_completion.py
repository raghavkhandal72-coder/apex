import unittest

from apex_council.cli_completion import generate_completion_script


class TestApexCompletion(unittest.TestCase):
    def test_bash_completion(self):
        script = generate_completion_script("bash", ["cegis", "sbfl", "lint", "fix"])
        self.assertIn("complete -F _apex_completions apex", script)
        self.assertIn("cegis fix lint sbfl", script)

    def test_powershell_completion(self):
        script = generate_completion_script("powershell", ["cegis", "sbfl"])
        self.assertIn("Register-ArgumentCompleter", script)
        self.assertIn("'cegis', 'sbfl'", script)


if __name__ == "__main__":
    unittest.main()

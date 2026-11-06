import subprocess
import tempfile
import unittest
from pathlib import Path

from apex_council.git.hook import install_hook, run_pre_commit_hook, uninstall_hook


class GitHookTests(unittest.TestCase):
    def test_install_and_uninstall_hook(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".git" / "hooks").mkdir(parents=True, exist_ok=True)

            self.assertTrue(install_hook(tmp))
            hook_file = tmp / ".git" / "hooks" / "pre-commit"
            self.assertTrue(hook_file.exists())
            self.assertIn("apex hook run", hook_file.read_text(encoding="utf-8"))

            self.assertTrue(uninstall_hook(tmp))
            self.assertFalse(hook_file.exists())

    def test_pre_commit_heals_staged_regression(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # Init git repo
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmp, check=True)
            subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=tmp, check=True)

            target = tmp / "search.py"
            target.write_text(
                "def binary_search(arr, target):\n"
                "    left, right = 0, len(arr) - 1\n"
                "    while left < right:\n"  # Buggy!
                "        mid = (left + right) // 2\n"
                "        if arr[mid] == target: return mid\n"
                "        elif arr[mid] < target: left = mid + 1\n"
                "        else: right = mid - 1\n"
                "    return -1\n",
                encoding="utf-8",
            )
            tests = tmp / "tests.txt"
            tests.write_text("assert binary_search([1, 2, 3], 3) == 2\n", encoding="utf-8")

            # Stage the buggy file
            subprocess.run(["git", "add", "search.py", "tests.txt"], cwd=tmp, check=True)

            # Run pre-commit hook
            ret = run_pre_commit_hook(tmp)
            self.assertEqual(ret, 0)

            # Verify that search.py was repaired to <=
            repaired = target.read_text(encoding="utf-8")
            self.assertIn("while left <= right:", repaired)


if __name__ == "__main__":
    unittest.main()

import os
import sys
import tempfile
import unittest

from apex_council.repair.watcher import scan_mtimes, detect_changes, run_watch_loop


class TestApexWatcher(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.test_file = os.path.join(self.tmp_dir.name, "sample.py")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

    def test_scan_mtimes_and_detect_changes(self):
        mtimes_initial = scan_mtimes(self.tmp_dir.name)
        self.assertIn(os.path.abspath(self.test_file), mtimes_initial)

        # No changes initially
        changed = detect_changes(mtimes_initial, mtimes_initial)
        self.assertEqual(changed, [])

        # Touch or modify the file with explicit future mtime to guarantee timestamp advance
        import time
        with open(self.test_file, "a", encoding="utf-8") as f:
            f.write("# comment\n")
        new_time = time.time() + 5
        os.utime(self.test_file, (new_time, new_time))

        mtimes_updated = scan_mtimes(self.tmp_dir.name)
        changed = detect_changes(mtimes_initial, mtimes_updated)
        self.assertEqual(changed, [os.path.abspath(self.test_file)])

    def test_run_watch_loop_once(self):
        cmd = f'"{sys.executable}" -c "print(\'watcher_test_pass\')"'
        exit_code = run_watch_loop(
            target_path=self.tmp_dir.name,
            command=cmd,
            once=True,
            interval=0.1
        )
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()

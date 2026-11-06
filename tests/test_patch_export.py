import os
import tempfile
import unittest

from apex_council.repair.patch_export import generate_patch, export_patch_file


class TestApexPatchExport(unittest.TestCase):
    def test_generate_patch(self):
        orig = "def fn():\n    return 1\n"
        mod = "def fn():\n    return 2\n"
        patch = generate_patch(orig, mod, "test.py")
        self.assertIn("--- a/test.py", patch)
        self.assertIn("+++ b/test.py", patch)
        self.assertIn("-    return 1", patch)
        self.assertIn("+    return 2", patch)

    def test_export_patch_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            orig_file = os.path.join(tmp_dir, "sample.py")
            bak_file = os.path.join(tmp_dir, "sample.py.bak")
            patch_file = os.path.join(tmp_dir, "fix.patch")

            with open(bak_file, "w", encoding="utf-8") as f:
                f.write("x = 10\n")
            with open(orig_file, "w", encoding="utf-8") as f:
                f.write("x = 20\n")

            ok, msg = export_patch_file(orig_file, output_patch=patch_file)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(patch_file))

            with open(patch_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("-x = 10", content)
            self.assertIn("+x = 20", content)


if __name__ == "__main__":
    unittest.main()

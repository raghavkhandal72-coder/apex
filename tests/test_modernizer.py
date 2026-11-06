import os
import tempfile
import unittest

from apex_council.lint.modernizer import modernize_code, modernize_file


class TestApexModernizer(unittest.TestCase):
    def test_modernize_types(self):
        legacy = (
            "from typing import Optional, List, Dict, Union\n\n"
            "def process(items: List[str], mapping: Dict[str, int], flag: Optional[bool] = None) -> Union[int, str]:\n"
            "    return 42\n"
        )
        modernized, changes = modernize_code(legacy)
        self.assertIn("list[str]", modernized)
        self.assertIn("dict[str, int]", modernized)
        self.assertIn("bool | None", modernized)
        self.assertIn("int | str", modernized)
        self.assertTrue(len(changes) >= 4)

    def test_modernize_file_write_and_backup(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "legacy.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("from typing import List\ndef get() -> List[int]: return []\n")

            res = modernize_file(file_path, write=True)
            self.assertTrue(res["success"])
            self.assertTrue(res["changed"])
            self.assertTrue(res["written"])

            # Verify backup was created
            bak_path = f"{file_path}.bak"
            self.assertTrue(os.path.exists(bak_path))

            # Verify target file updated
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("list[int]", content)


if __name__ == "__main__":
    unittest.main()

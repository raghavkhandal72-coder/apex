import unittest

from apex_council.formal.swift_guard import audit_swift_safety, format_swift_report


class TestApexSwiftGuard(unittest.TestCase):
    def test_non_exhaustive_pattern_match(self):
        code = (
            "def handle(val):\n"
            "    match val:\n"
            "        case 1:\n"
            "            return 'one'\n"
            "        case 2:\n"
            "            return 'two'\n"
        )
        findings = audit_swift_safety(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "SWIFT001")
        self.assertIn("Non-exhaustive", findings[0].message)

    def test_exhaustive_pattern_match(self):
        code = (
            "def handle(val):\n"
            "    match val:\n"
            "        case 1:\n"
            "            return 'one'\n"
            "        case _:\n"
            "            return 'other'\n"
        )
        findings = audit_swift_safety(code)
        self.assertEqual(len(findings), 0)

    def test_format_swift_report(self):
        rep_clean = format_swift_report([], "clean.py")
        self.assertIn("APEX SWIFT-GUARD", rep_clean)
        self.assertIn("All pattern matches are fully exhaustive", rep_clean)


if __name__ == "__main__":
    unittest.main()

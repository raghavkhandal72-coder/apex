import unittest

from apex_council.analysis.fingerprint import compute_crash_fingerprint, format_fingerprint_report


class TestApexFingerprint(unittest.TestCase):
    def test_fingerprint_deduplication_across_line_shifts(self):
        tb1 = (
            'Traceback (most recent call last):\n'
            '  File "app/server.py", line 42, in handle_request\n'
            '    dispatch(req)\n'
            '  File "app/router.py", line 105, in dispatch\n'
            '    return execute(req)\n'
            'ZeroDivisionError: division by zero\n'
        )

        # tb2 has shifted line numbers (e.g. code was added above line 42)
        tb2 = (
            'Traceback (most recent call last):\n'
            '  File "app/server.py", line 98, in handle_request\n'
            '    dispatch(req)\n'
            '  File "app/router.py", line 160, in dispatch\n'
            '    return execute(req)\n'
            'ZeroDivisionError: division by zero\n'
        )

        fp1 = compute_crash_fingerprint(tb1)
        fp2 = compute_crash_fingerprint(tb2)

        self.assertIsNotNone(fp1)
        self.assertIsNotNone(fp2)
        # Fingerprint MUST be identical despite line number drift!
        self.assertEqual(fp1.sha256_hash, fp2.sha256_hash)
        self.assertEqual(fp1.error_type, "ZeroDivisionError")
        self.assertEqual(fp1.crash_file, "router.py")
        self.assertEqual(fp1.crash_function, "dispatch")

    def test_format_report(self):
        tb = 'Traceback:\n  File "foo.py", line 1, in bar\nIndexError: list index out of range\n'
        fp = compute_crash_fingerprint(tb)
        self.assertIsNotNone(fp)
        rep = format_fingerprint_report(fp)
        self.assertIn("APEX CRASH FINGERPRINT", rep)
        self.assertIn("IndexError", rep)


if __name__ == "__main__":
    unittest.main()

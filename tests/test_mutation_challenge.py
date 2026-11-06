import unittest

from apex_council.evaluator.mutation_challenge import render_challenge_report, run_mutation_challenge


class MutationChallengeTests(unittest.TestCase):
    def test_mutation_challenge_detects_blindspot(self):
        # Function has 2 checks, but test suite only tests positive numbers
        code = (
            "def check_val(x):\n"
            "    if x > 0:\n"
            "        return 1\n"
            "    return 0\n"
        )
        # Test only tests x > 0! Never tests x <= 0!
        weak_tests = "assert check_val(5) == 1\nassert check_val(10) == 1\n"

        rep = run_mutation_challenge(code, weak_tests, max_mutants=5)
        self.assertGreater(rep.total_mutants, 0)
        # Some mutant should survive because x <= 0 is never tested
        self.assertGreater(rep.survived, 0)
        output = render_challenge_report(rep, "check_val.py")
        self.assertIn("Mutation Resilience Score", output)
        self.assertIn("Test Suite Blindspots", output)

    def test_mutation_challenge_kills_mutants_with_complete_tests(self):
        code = (
            "def is_positive(x):\n"
            "    return x > 0\n"
        )
        strong_tests = (
            "assert is_positive(1) is True\n"
            "assert is_positive(0) is False\n"
            "assert is_positive(-1) is False\n"
        )
        rep = run_mutation_challenge(code, strong_tests, max_mutants=5)
        self.assertEqual(rep.survived, 0)
        self.assertEqual(rep.score_pct, 100.0)


if __name__ == "__main__":
    unittest.main()

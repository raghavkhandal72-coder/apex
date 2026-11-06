import unittest

from apex_council.synthesis.cegis_engine import CEGISEngine, _ASTCandidateMutator


class CEGISGrammarTests(unittest.TestCase):
    def test_boolop_mutation_in_candidates(self):
        code = "def f(a, b):\n    return a and b\n"
        candidates = CEGISEngine.generate_candidate_programs(code)
        self.assertTrue(any("return a or b" in c for c in candidates))

    def test_membership_mutation_in_candidates(self):
        code = "def f(x, s):\n    return x in s\n"
        candidates = CEGISEngine.generate_candidate_programs(code)
        self.assertTrue(any("return x not in s" in c for c in candidates))

    def test_constant_off_by_one_mutations(self):
        code = "def f(x):\n    return x + 5\n"
        candidates = CEGISEngine.generate_candidate_programs(code)
        self.assertTrue(any("return x + 6" in c for c in candidates))
        self.assertTrue(any("return x + 4" in c for c in candidates))

    def test_synthesizes_boolop_repair(self):
        buggy = (
            "def check_access(is_admin, is_owner):\n"
            "    if is_admin and is_owner:\n"
            "        return True\n"
            "    return False\n"
        )
        tests = (
            "assert check_access(True, False) == True\n"
            "assert check_access(False, True) == True\n"
            "assert check_access(False, False) == False\n"
            "assert check_access(True, True) == True\n"
        )
        engine = CEGISEngine()
        rep = engine.synthesize_and_verify(buggy, tests)
        self.assertTrue(rep.success)
        self.assertIn("if is_admin or is_owner:", rep.synthesized_code)

    def test_synthesizes_off_by_one_constant_repair(self):
        buggy = (
            "def get_last_index(arr):\n"
            "    return len(arr) - 2\n"  # Off by one! Should be - 1
        )
        tests = (
            "assert get_last_index([10, 20, 30]) == 2\n"
            "assert get_last_index([10]) == 0\n"
        )
        engine = CEGISEngine()
        rep = engine.synthesize_and_verify(buggy, tests)
        self.assertTrue(rep.success)
        self.assertIn("return len(arr) - 1", rep.synthesized_code)


if __name__ == "__main__":
    unittest.main()

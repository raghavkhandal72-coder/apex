import unittest

from apex_council.synthesis.differential_oracle import (
    find_counterexamples, reference_binary_search, sorted_unique_search_gen)


def correct(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


def off_by_one(arr, target):
    left, right = 0, len(arr) - 1
    while left < right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


def overfit_len_div(arr, target):  # the earlier wrong "repair": right = len(arr)
    left, right = 0, len(arr)
    while left < right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


def run(fn):
    return find_counterexamples(fn, reference_binary_search, sorted_unique_search_gen, n=800, seed=1)


class DifferentialOracleTests(unittest.TestCase):
    def test_correct_has_no_counterexample(self):
        self.assertEqual(run(correct), [])

    def test_off_by_one_is_caught_as_wrong_answer(self):
        kinds = {c.kind for c in run(off_by_one)}
        self.assertIn("wrong_answer", kinds)

    def test_overfit_candidate_is_caught(self):
        self.assertTrue(run(overfit_len_div))

    def test_crash_is_classified(self):
        def crasher(arr, target):
            return arr[0]
        kinds = {c.kind for c in run(crasher)}
        self.assertTrue(kinds & {"candidate_exception", "wrong_answer"})


if __name__ == "__main__":
    unittest.main()

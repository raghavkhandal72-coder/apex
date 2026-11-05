"""Test suite for unseen_binary_search.py (Balanced positive and negative test cases).
Demonstrates Spectrum-Based Fault Localization (SBFL) with 4 passing and 2 failing tests.
"""
from examples.unseen_binary_search import binary_search


def test_find_last():
    # FAILS on buggy code: left < right exits prematurely when left == right == 4
    assert binary_search([1, 2, 3, 4, 5], 5) == 4


def test_find_first():
    # PASSES on buggy code
    assert binary_search([1, 2, 3, 4, 5], 1) == 0


def test_find_middle():
    # PASSES on buggy code
    assert binary_search([1, 2, 3, 4, 5], 3) == 2


def test_missing_element():
    # PASSES on buggy code: missing element correctly falls out of loop and hits line 12 (return -1)
    assert binary_search([1, 2, 3, 4, 5], 6) == -1


def test_empty_array():
    # PASSES on buggy code: empty list correctly hits line 12 (return -1)
    assert binary_search([], 3) == -1


def test_single_element_match():
    # FAILS on buggy code: left=0, right=0; 0 < 0 is False, exits loop and returns -1 instead of 0
    assert binary_search([7], 7) == 0

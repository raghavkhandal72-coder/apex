"""Test harness for calculator module."""
from examples.calculator import add, divide, is_positive

def test_add():
    assert add(2, 3) == 5

def test_divide():
    assert divide(10, 2) == 5.0

def test_positive():
    assert is_positive(5) is True
    assert is_positive(-1) is False

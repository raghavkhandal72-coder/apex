"""Example calculator module with an off-by-one / operator bug for CEGIS & SBFL demonstrations."""

def add(a: int, b: int) -> int:
    # Bug: subtracts instead of adds
    return a - b

def divide(a: float, b: float) -> float:
    # Potential zero division
    return a / b

def is_positive(n: int) -> bool:
    # Off-by-one bug: 0 is not strictly positive
    return n >= 0

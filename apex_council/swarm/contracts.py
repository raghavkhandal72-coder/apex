"""Pre-Implementation and Post-Implementation AST Invariant & Contract Verifier.
Validates architectural contracts, cyclomatic complexity bounds, signature backward-compatibility,
and type completeness before code is considered for rollout.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ContractSpecification:
    required_symbols: List[str] = field(default_factory=list)
    preserved_signatures: Dict[str, List[str]] = field(default_factory=dict)
    prohibited_imports: List[str] = field(default_factory=list)
    max_cyclomatic_complexity: int = 15
    enforce_docstrings: bool = True
    enforce_type_annotations: bool = False
    disallow_global_mutation: bool = True


@dataclass
class ContractReport:
    is_compliant: bool
    violations: List[str] = field(default_factory=list)
    symbol_complexities: Dict[str, int] = field(default_factory=dict)
    declared_symbols: List[str] = field(default_factory=list)
    imported_modules: List[str] = field(default_factory=list)


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """Calculates McCabe Cyclomatic Complexity V(G) = 1 + number of decision points."""

    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each extra boolean operand in and/or adds a branch
        self.complexity += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)


class ContractVerifier:
    """Rigorous AST invariant auditor."""

    @classmethod
    def verify(cls, code: str, spec: ContractSpecification) -> ContractReport:
        violations: List[str] = []
        complexities: Dict[str, int] = {}
        declared_symbols: List[str] = []
        imported_modules: List[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as ex:
            return ContractReport(
                is_compliant=False,
                violations=[f"SyntaxError in code: {str(ex)}"],
            )

        # 1. Imports Analysis
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.append(node.module)

        for prohibited in spec.prohibited_imports:
            for imp in imported_modules:
                if imp == prohibited or imp.startswith(f"{prohibited}."):
                    violations.append(f"Prohibited import detected: `{imp}` violates security contract")

        # 2. Extract Top-Level and Method Symbols
        symbol_map: Dict[str, ast.AST] = {}
        for item in tree.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                declared_symbols.append(item.name)
                symbol_map[item.name] = item

                # Calculate Complexity
                calc = CyclomaticComplexityVisitor()
                calc.visit(item)
                complexities[item.name] = calc.complexity

                if calc.complexity > spec.max_cyclomatic_complexity:
                    violations.append(
                        f"Symbol `{item.name}` cyclomatic complexity {calc.complexity} "
                        f"exceeds ceiling {spec.max_cyclomatic_complexity}"
                    )

                # Check Docstrings
                if spec.enforce_docstrings:
                    doc = ast.get_docstring(item)
                    if not doc or not doc.strip():
                        violations.append(f"Symbol `{item.name}` is missing required architectural docstring")

                # Check Type Annotations
                if spec.enforce_type_annotations and isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in item.args.args:
                        if arg.arg != "self" and arg.arg != "cls" and arg.annotation is None:
                            violations.append(f"Argument `{arg.arg}` in function `{item.name}` lacks type annotation")
                    if item.returns is None:
                        violations.append(f"Function `{item.name}` lacks return type annotation")

            elif isinstance(item, ast.Global) and spec.disallow_global_mutation:
                violations.append(f"Disallowed global keyword declaration: {', '.join(item.names)}")

        # 3. Check Required Symbols
        for req in spec.required_symbols:
            if req not in declared_symbols:
                violations.append(f"Required architectural symbol `{req}` is not declared in code")

        # 4. Check Preserved Signatures
        for func_name, expected_args in spec.preserved_signatures.items():
            if func_name in symbol_map:
                fn_node = symbol_map[func_name]
                if isinstance(fn_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    actual_args = [a.arg for a in fn_node.args.args]
                    for exp in expected_args:
                        if exp not in actual_args:
                            violations.append(
                                f"Signature regression in `{func_name}`: missing required backward-compatible parameter `{exp}`"
                            )

        return ContractReport(
            is_compliant=(len(violations) == 0),
            violations=violations,
            symbol_complexities=complexities,
            declared_symbols=declared_symbols,
            imported_modules=imported_modules,
        )

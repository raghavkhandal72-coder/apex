"""Normalized AST Structural Hasher.
Strips variable, function, and class identifiers to compute a SHA-256 structural fingerprint.
Enables 100% precision matching of identical structural patterns across different files.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import ast
import hashlib
import re


class ASTNormalizer(ast.NodeTransformer):
    """Normalizes identifiers, variable names, and arguments while preserving semantic constants.
    Preserves purely the abstract structural topology and semantic constants of the code.
    """

    def __init__(self, normalize_constants: bool = False) -> None:
        self.normalize_constants = normalize_constants

    def _strip_docstring(self, body: list[ast.stmt]) -> list[ast.stmt]:
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            return body[1:]
        return body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = "_f"
        node.body = self._strip_docstring(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = "_af"
        node.body = self._strip_docstring(node.body)
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.name = "_c"
        node.body = self._strip_docstring(node.body)
        return self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> ast.AST:
        node.body = self._strip_docstring(node.body)
        return self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = "_a"
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = "_v"
        return self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if self.normalize_constants:
            if isinstance(node.value, str):
                node.value = ""
            elif isinstance(node.value, (int, float)):
                node.value = 0
        return self.generic_visit(node)


class NormalizedASTHasher:
    """Computes a canonical SHA-256 fingerprint of the normalized AST topology."""

    @staticmethod
    def compute_fingerprint(code: str, normalize_constants: bool = False) -> str:
        try:
            tree = ast.parse(code)
            normalizer = ASTNormalizer(normalize_constants=normalize_constants)
            normalized_tree = normalizer.visit(tree)
            ast.fix_missing_locations(normalized_tree)
            canonical_code = ast.unparse(normalized_tree) if hasattr(ast, "unparse") else ast.dump(normalized_tree)
            return hashlib.sha256(canonical_code.encode("utf-8")).hexdigest()
        except Exception:
            # Fallback token normalization
            tokens = re.sub(r"\s+", " ", code).strip()
            return hashlib.sha256(tokens.encode("utf-8")).hexdigest()

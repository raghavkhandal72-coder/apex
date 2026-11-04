from __future__ import annotations

import ast


class ASTBombDetected(ValueError):
    """Raised when malicious code payload exceeds AST depth or node limits."""
    pass


class ASTShield:
    """Protects against AST Bombs, deeply nested expressions, and stack-exhaustion exploits."""

    MAX_DEPTH = 200
    MAX_NODES = 25000

    @classmethod
    def inspect_ast_safety(cls, code: str) -> bool:
        # Pre-check code length (reject single payloads > 1.5MB)
        if len(code) > 1.5 * 1024 * 1024:
            raise ASTBombDetected("Payload size exceeds 1.5MB safety threshold")

        try:
            tree = ast.parse(code)
        except RecursionError:
            raise ASTBombDetected("AST Recursion Bomb: Deeply nested syntax triggered stack overflow")
        except SyntaxError as e:
            if any(k in str(e).lower() for k in ("too many", "nested", "maximum recursion")):
                raise ASTBombDetected(f"AST Bomb detected: {str(e)}")
            return False

        # Measure node count and recursion depth
        node_count = 0
        max_depth_seen = 0

        def traverse(node: ast.AST, depth: int):
            nonlocal node_count, max_depth_seen
            node_count += 1
            if depth > max_depth_seen:
                max_depth_seen = depth

            if node_count > cls.MAX_NODES:
                raise ASTBombDetected(f"Excessive AST nodes ({node_count} > {cls.MAX_NODES})")
            if depth > cls.MAX_DEPTH:
                raise ASTBombDetected(f"Excessive AST depth ({depth} > {cls.MAX_DEPTH})")

            for child in ast.iter_child_nodes(node):
                traverse(child, depth + 1)

        traverse(tree, 1)
        return True

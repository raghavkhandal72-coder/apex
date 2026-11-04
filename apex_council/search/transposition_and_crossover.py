"""Apex-Sovereign: Canonical AST Transposition & Genetic Bitmask Crossover Engine.
100% Pure Python Standard Library | Zero Dependencies | Zero Mocks.

Components:
1. _CanonicalAlphaNormalizer: Normalizes local identifiers, arguments, and docstrings
   to produce canonical AST representations invariant to variable renames.
2. ASTMetricsAndHashEngine: Computes canonical SHA-256 fingerprints, McCabe cyclomatic
   complexity, and Minimum Description Length (MDL) metrics.
3. ASTTranspositionTable: High-performance O(1) in-memory cache to skip redundant
   hermetic sandbox evaluations during MCTS search.
4. BitmaskGeneticASTCrossover: Genetic crossover engine that recombines functions, methods,
   and guards across competing candidate ASTs using bitmask recombination.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class _CanonicalAlphaNormalizer(ast.NodeTransformer):
    """
    Alpha-renames local variables and parameters to canonical forms (_arg0, _var0, etc.)
    and strips docstrings so that structurally identical code generates identical hashes.
    """

    BUILTIN_NAMES = {
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes", "callable",
        "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod",
        "enumerate", "eval", "exec", "filter", "float", "format", "frozenset", "getattr",
        "globals", "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance",
        "issubclass", "iter", "len", "list", "locals", "map", "max", "memoryview", "min",
        "next", "object", "oct", "open", "ord", "pow", "print", "property", "range",
        "repr", "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod",
        "str", "sum", "super", "tuple", "type", "vars", "zip", "__import__", "self", "cls",
    }

    def __init__(self) -> None:
        self.scope_stack: List[Dict[str, str]] = [{}]
        self.counter: int = 0

    def _get_canonical_name(self, original_name: str) -> str:
        if original_name in self.BUILTIN_NAMES or original_name.startswith("__"):
            return original_name
        current_scope = self.scope_stack[-1]
        if original_name in current_scope:
            return current_scope[original_name]
        canon = f"_v{self.counter}"
        self.counter += 1
        current_scope[original_name] = canon
        return canon

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        # Strip function docstring if present
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:] or [ast.Pass()]

        # New scope for function parameters and body
        self.scope_stack.append({})
        for arg in node.args.args:
            if arg.arg not in ("self", "cls"):
                arg.arg = self._get_canonical_name(arg.arg)
        for arg in node.args.kwonlyargs:
            arg.arg = self._get_canonical_name(arg.arg)

        self.generic_visit(node)
        self.scope_stack.pop()
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self.visit_FunctionDef(node)  # type: ignore

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id not in self.BUILTIN_NAMES and not node.id.startswith("__"):
            # If variable exists in current or enclosing scope, rename it
            for scope in reversed(self.scope_stack):
                if node.id in scope:
                    node.id = scope[node.id]
                    return node
            if isinstance(node.ctx, (ast.Store, ast.Param)):
                node.id = self._get_canonical_name(node.id)
        return node


class ASTMetricsAndHashEngine:
    """Computes canonical structural fingerprints, McCabe complexity, and description length."""

    @classmethod
    def compute_mccabe_complexity(cls, tree: ast.AST) -> int:
        """
        Calculates cyclomatic complexity (McCabe metric) M = E - N + 2P
        Equivalent to counting decision branching nodes + 1.
        """
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, (ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(node, ast.IfExp):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # 'and' or 'or' adds branching for each extra value
                complexity += max(0, len(node.values) - 1)
            elif isinstance(node, ast.Assert):
                complexity += 1
        return complexity

    @classmethod
    def compute_canonical_fingerprint(cls, code: str) -> str:
        """
        Parses source, alpha-normalizes identifiers, strips docstrings,
        and generates a deterministic SHA-256 fingerprint.
        """
        try:
            tree = ast.parse(code)
            normalizer = _CanonicalAlphaNormalizer()
            normalized_tree = normalizer.visit(tree)
            ast.fix_missing_locations(normalized_tree)
            dumped_ast = ast.dump(normalized_tree, include_attributes=False)
            return hashlib.sha256(dumped_ast.encode("utf-8")).hexdigest()
        except Exception:
            # Fallback to plain normalized text hash
            clean = "".join(code.split())
            return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    @classmethod
    def compute_mdl_score(cls, code: str) -> Tuple[int, int, int]:
        """
        Computes Minimum Description Length (MDL) tuple:
        (mccabe_complexity, total_ast_nodes, raw_byte_length)
        Lower values represent simpler, more elegant code.
        """
        try:
            tree = ast.parse(code)
            complexity = cls.compute_mccabe_complexity(tree)
            node_count = len(list(ast.walk(tree)))
        except Exception:
            complexity = 999
            node_count = 9999
        return complexity, node_count, len(code.encode("utf-8"))


@dataclasses.dataclass
class TranspositionEntry:
    ast_hash: str
    eval_score: float
    eval_details: Dict[str, Any]
    visit_count: int
    created_at: float
    mccabe_complexity: int = 1
    node_count: int = 0


class ASTTranspositionTable:
    """O(1) in-memory cache of evaluated AST states to eliminate redundant test executions."""

    def __init__(self, max_entries: int = 5000) -> None:
        self.max_entries = max_entries
        self.table: Dict[str, TranspositionEntry] = {}
        self.hits: int = 0
        self.misses: int = 0

    def lookup(self, code: str) -> Optional[Tuple[float, Dict[str, Any]]]:
        ast_hash = ASTMetricsAndHashEngine.compute_canonical_fingerprint(code)
        if ast_hash in self.table:
            self.hits += 1
            entry = self.table[ast_hash]
            entry.visit_count += 1
            return entry.eval_score, entry.eval_details
        self.misses += 1
        return None

    def store(self, code: str, score: float, details: Dict[str, Any]) -> str:
        ast_hash = ASTMetricsAndHashEngine.compute_canonical_fingerprint(code)
        if len(self.table) >= self.max_entries:
            # Evict oldest entry
            oldest_key = min(self.table.keys(), key=lambda k: self.table[k].created_at)
            del self.table[oldest_key]

        complexity, nodes, _ = ASTMetricsAndHashEngine.compute_mdl_score(code)
        self.table[ast_hash] = TranspositionEntry(
            ast_hash=ast_hash,
            eval_score=score,
            eval_details=details,
            visit_count=1,
            created_at=time.time(),
            mccabe_complexity=complexity,
            node_count=nodes,
        )
        return ast_hash

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0

    def clear(self) -> None:
        self.table.clear()
        self.hits = 0
        self.misses = 0


@dataclasses.dataclass
class CrossoverResult:
    merged_code: str
    combined_symbols: List[str]
    crossover_type: str  # "AST_HYBRID_CROSSOVER", "BITMASK_GENE_SPLICING", "FALLBACK_A", "FALLBACK_B"


class BitmaskGeneticASTCrossover:
    """
    Decomposes competing AST candidates into discrete genetic units (functions, methods,
    imports, guards) and synthesizes hybrid candidates via bitmask recombination.
    """

    @classmethod
    def decompose_into_genes(cls, code: str) -> Dict[str, ast.AST]:
        """Extracts top-level genes: imports, functions, classes, and top-level statements."""
        try:
            tree = ast.parse(code)
        except Exception:
            return {}
        genes: Dict[str, ast.AST] = {}
        for idx, stmt in enumerate(tree.body):
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                genes[f"func_{stmt.name}"] = stmt
            elif isinstance(stmt, ast.ClassDef):
                genes[f"class_{stmt.name}"] = stmt
            elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
                genes[f"import_{idx}"] = stmt
            else:
                genes[f"stmt_{idx}"] = stmt
        return genes

    @classmethod
    def recombine_with_bitmask(
        cls,
        parent_a: str,
        parent_b: str,
        bitmask: int,
    ) -> Optional[str]:
        """
        Selects genes from parent_a (bit 0) or parent_b (bit 1) based on bitmask.
        Returns synthesized code string or None if unparseable.
        """
        genes_a = cls.decompose_into_genes(parent_a)
        genes_b = cls.decompose_into_genes(parent_b)

        all_keys = sorted(list(set(genes_a.keys()) | set(genes_b.keys())))
        if not all_keys:
            return None

        merged_body: List[ast.AST] = []
        for i, key in enumerate(all_keys):
            pick_b = (bitmask >> (i % 32)) & 1
            if pick_b and key in genes_b:
                merged_body.append(genes_b[key])
            elif key in genes_a:
                merged_body.append(genes_a[key])
            elif key in genes_b:
                merged_body.append(genes_b[key])

        new_module = ast.Module(body=merged_body, type_ignores=[])
        ast.fix_missing_locations(new_module)
        try:
            return ast.unparse(new_module)
        except Exception:
            return None

    @classmethod
    def cross_synthesize(cls, code_a: str, code_b: str) -> CrossoverResult:
        """
        High-level genetic merger: Combines complementary functions and class methods
        from two competing candidate codes into an airtight hybrid AST.
        """
        try:
            tree_a = ast.parse(code_a)
            tree_b = ast.parse(code_b)
        except Exception:
            try:
                ast.parse(code_a)
                return CrossoverResult(code_a, ["code_a"], "FALLBACK_A")
            except Exception:
                return CrossoverResult(code_b, ["code_b"], "FALLBACK_B")

        funcs_a = {n.name: n for n in tree_a.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        funcs_b = {n.name: n for n in tree_b.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        classes_a = {n.name: n for n in tree_a.body if isinstance(n, ast.ClassDef)}
        classes_b = {n.name: n for n in tree_b.body if isinstance(n, ast.ClassDef)}

        merged_body: List[ast.AST] = []
        combined_names: List[str] = []

        # 1. Deduplicated imports
        for stmt in tree_a.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                merged_body.append(stmt)
        for stmt in tree_b.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                if not any(ast.dump(stmt) == ast.dump(existing) for existing in merged_body):
                    merged_body.append(stmt)

        # 2. Merge functions: pick richer/more guarded implementation
        all_func_names = sorted(list(set(funcs_a.keys()) | set(funcs_b.keys())))
        for fname in all_func_names:
            if fname in funcs_a and fname in funcs_b:
                nodes_a = len(list(ast.walk(funcs_a[fname])))
                nodes_b = len(list(ast.walk(funcs_b[fname])))
                chosen = funcs_a[fname] if nodes_a >= nodes_b else funcs_b[fname]
                merged_body.append(chosen)
                combined_names.append(f"{fname}(hybrid)")
            elif fname in funcs_a:
                merged_body.append(funcs_a[fname])
                combined_names.append(f"{fname}(A)")
            else:
                merged_body.append(funcs_b[fname])
                combined_names.append(f"{fname}(B)")

        # 3. Merge classes and class methods
        all_class_names = sorted(list(set(classes_a.keys()) | set(classes_b.keys())))
        for cname in all_class_names:
            if cname in classes_a and cname in classes_b:
                ca = classes_a[cname]
                cb = classes_b[cname]
                methods_a = {m.name: m for m in ca.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
                methods_b = {m.name: m for m in cb.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
                merged_class_body: List[ast.AST] = []

                for s in ca.body:
                    if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        merged_class_body.append(s)

                for mname in sorted(list(set(methods_a.keys()) | set(methods_b.keys()))):
                    if mname in methods_a and mname in methods_b:
                        count_a = len(list(ast.walk(methods_a[mname])))
                        count_b = len(list(ast.walk(methods_b[mname])))
                        merged_class_body.append(methods_a[mname] if count_a >= count_b else methods_b[mname])
                    elif mname in methods_a:
                        merged_class_body.append(methods_a[mname])
                    else:
                        merged_class_body.append(methods_b[mname])

                ca.body = merged_class_body
                merged_body.append(ca)
                combined_names.append(f"class {cname}(merged)")
            elif cname in classes_a:
                merged_body.append(classes_a[cname])
                combined_names.append(f"class {cname}(A)")
            else:
                merged_body.append(classes_b[cname])
                combined_names.append(f"class {cname}(B)")

        merged_module = ast.Module(body=merged_body, type_ignores=[])
        ast.fix_missing_locations(merged_module)
        merged_code = ast.unparse(merged_module)

        return CrossoverResult(
            merged_code=merged_code,
            combined_symbols=combined_names,
            crossover_type="AST_HYBRID_CROSSOVER",
        )


# Backward-compatible alias for SemanticASTCrossover
SemanticASTCrossover = BitmaskGeneticASTCrossover


if __name__ == "__main__":
    print("=" * 70)
    print("Apex-Sovereign: AST Transposition & Genetic Crossover Verification")
    print("=" * 70)

    # 1. Transposition Alpha-Equivalence Check
    table = ASTTranspositionTable()
    code1 = "def add(x, y):\n    return x + y\n"
    code2 = "def add(foo, bar):\n    return foo + bar\n"
    table.store(code1, 1.0, {"status": "PASS"})
    res = table.lookup(code2)
    print(f"[TEST 1 - TRANSPOSITION] Cached score for alpha-renamed function: {res[0] if res else None}")
    assert res is not None and res[0] == 1.0, "Transposition table must match alpha-renamed ASTs"

    # 2. McCabe Complexity & MDL Metric Check
    complex_code = """
def process(data):
    if not data:
        return None
    for item in data:
        if item > 10 and item < 20:
            print(item)
    return True
"""
    mccabe, nodes, bytes_len = ASTMetricsAndHashEngine.compute_mdl_score(complex_code)
    print(f"[TEST 2 - MDL METRICS] McCabe: {mccabe} | Nodes: {nodes} | Bytes: {bytes_len}")
    assert mccabe >= 4, "McCabe complexity should detect branching points"

    # 3. Genetic Crossover Check
    cand_a = "def step_one(): return 1\n"
    cand_b = "def step_two(): return 2\n"
    crossed = BitmaskGeneticASTCrossover.cross_synthesize(cand_a, cand_b)
    print(f"[TEST 3 - CROSSOVER] Combined: {crossed.combined_symbols}")
    assert "step_one" in crossed.merged_code and "step_two" in crossed.merged_code

    print("=" * 70)
    print("ALL TRANSPOSITION & CROSSOVER CHECKS PASSED - 100% GREEN")
    print("=" * 70)

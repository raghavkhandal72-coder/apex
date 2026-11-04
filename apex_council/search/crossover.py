"""Cross-Model Semantic Diff Merger / Genetic AST Crossover.
Synthesizes hybrid child nodes by merging complementary functions, classes, and edge-case guards from two models.
Pure Python standard library implementation.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CrossoverResult:
    merged_code: str
    combined_symbols: List[str]
    crossover_type: str  # "FUNCTION_LEVEL_MERGE", "CLASS_METHOD_MERGE", "REPRESENTATIVE_UNION"


class SemanticASTCrossover:
    """Merges passing AST definitions from two competing model candidates into a hybrid node."""

    @staticmethod
    def cross_synthesize(code_a: str, code_b: str) -> CrossoverResult:
        try:
            tree_a = ast.parse(code_a)
            tree_b = ast.parse(code_b)
        except Exception:
            # Fallback if one candidate has syntax error: return the other
            try:
                ast.parse(code_a)
                return CrossoverResult(code_a, ["code_a"], "FALLBACK_A")
            except Exception:
                return CrossoverResult(code_b, ["code_b"], "FALLBACK_B")

        # Map top-level definitions in tree_a and tree_b
        funcs_a = {n.name: n for n in tree_a.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        funcs_b = {n.name: n for n in tree_b.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        classes_a = {n.name: n for n in tree_a.body if isinstance(n, ast.ClassDef)}
        classes_b = {n.name: n for n in tree_b.body if isinstance(n, ast.ClassDef)}

        merged_body: List[ast.AST] = []
        combined_names: List[str] = []

        # 1. Preserve top-level docstrings and imports from both
        for stmt in tree_a.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                merged_body.append(stmt)
        for stmt in tree_b.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                # Avoid duplicate imports
                if not any(ast.dump(stmt) == ast.dump(existing) for existing in merged_body):
                    merged_body.append(stmt)

        # 2. Merge functions: If present in both, pick the one with more AST nodes (deeper logic/guards)
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

        # 3. Merge classes
        all_class_names = sorted(list(set(classes_a.keys()) | set(classes_b.keys())))
        for cname in all_class_names:
            if cname in classes_a and cname in classes_b:
                # Merge methods from both classes
                ca = classes_a[cname]
                cb = classes_b[cname]
                methods_a = {m.name: m for m in ca.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
                methods_b = {m.name: m for m in cb.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
                merged_class_body: List[ast.AST] = []

                # Add class docstring or non-method statements
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

        # Build merged Module
        hybrid_module = ast.Module(body=merged_body, type_ignores=[])
        ast.fix_missing_locations(hybrid_module)

        unparsed = ast.unparse(hybrid_module) if hasattr(ast, "unparse") else code_a
        return CrossoverResult(
            merged_code=unparsed,
            combined_symbols=combined_names,
            crossover_type="AST_HYBRID_CROSSOVER",
        )

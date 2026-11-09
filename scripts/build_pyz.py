"""Pure Python Standalone Executable Compiler using standard library zipapp.
Bundles the entire Apex codebase into an airtight zero-dependency apex.pyz executable.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
import zipapp
from pathlib import Path


def build_standalone_pyz(output_path: str = "dist/apex.pyz") -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    src_package = repo_root / "apex_council"
    out_file = repo_root / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Packaging Apex-Sovereign from: {src_package}")

    with tempfile.TemporaryDirectory() as staging_dir:
        staging_path = Path(staging_dir)
        target_pkg = staging_path / "apex_council"
        
        # Copy source package, excluding caches and tests
        shutil.copytree(
            src_package,
            target_pkg,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git*", "*.html", "*.md"),
        )

        # Optimize staging files using safe Python AST compilation to preserve strict < 450 KB budget
        import ast

        class DocstringStripper(ast.NodeTransformer):
            def _strip_doc(self, node):
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                    node.body = node.body[1:]
                    if not node.body:
                        node.body = [ast.Pass()]
                return node
            def visit_FunctionDef(self, node):
                self.generic_visit(node)
                node.returns = None
                for arg in node.args.args + node.args.kwonlyargs:
                    arg.annotation = None
                if node.args.vararg:
                    node.args.vararg.annotation = None
                if node.args.kwarg:
                    node.args.kwarg.annotation = None
                return self._strip_doc(node)

            def visit_AsyncFunctionDef(self, node):
                self.generic_visit(node)
                node.returns = None
                for arg in node.args.args + node.args.kwonlyargs:
                    arg.annotation = None
                if node.args.vararg:
                    node.args.vararg.annotation = None
                if node.args.kwarg:
                    node.args.kwarg.annotation = None
                return self._strip_doc(node)
            def visit_ClassDef(self, node):
                self.generic_visit(node)
                return self._strip_doc(node)
            def visit_Module(self, node):
                self.generic_visit(node)
                return self._strip_doc(node)

        for py_file in target_pkg.rglob("*.py"):
            try:
                raw = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(raw)
                tree = DocstringStripper().visit(tree)
                ast.fix_missing_locations(tree)
                optimized = ast.unparse(tree)
                py_file.write_text(optimized, encoding="utf-8")
            except Exception:
                pass

        # Create __main__.py inside staging root
        main_py = staging_path / "__main__.py"
        main_py.write_text(
            '"""Apex-Sovereign Standalone Executable Entrypoint."""\n'
            "import os\n"
            "import sys\n"
            "# Ensure current working directory is on sys.path for user module imports\n"
            "if os.getcwd() not in sys.path:\n"
            "    sys.path.insert(0, os.getcwd())\n"
            "from apex_council.cli import main\n\n"
            'if __name__ == "__main__":\n'
            "    sys.exit(main())\n",
            encoding="utf-8",
        )

        # Build zipapp executable archive
        zipapp.create_archive(
            source=staging_path,
            target=out_file,
            interpreter="/usr/bin/env python3",
            main=None,  # Handled by __main__.py
            compressed=True,
        )

    # Set executable permissions on POSIX
    try:
        out_file.chmod(out_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass

    size_kb = out_file.stat().st_size / 1024
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"[OK] Successfully compiled standalone executable: {out_file} ({size_kb:.1f} KB)")
    return out_file


if __name__ == "__main__":
    build_standalone_pyz()

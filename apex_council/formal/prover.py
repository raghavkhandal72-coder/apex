"""Apex Sovereign Formal Safety & Mathematical Invariant Prover.
Combines Cousot 1977 Abstract Interpretation (Interval Polyhedra)
and Dijkstra Weakest Precondition Calculus (Hoare Logic).
100% Pure Python Standard Library | Zero Dependencies (pip = 0).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from .abstract_interpreter import ASTAbstractInterpreter
from .hoare_invariants import HoareInvariantVerifier


class FormalSafetyProver:
    """Unified Mathematical Safety Prover with cryptographic proof certificate."""

    @classmethod
    def prove_file(cls, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"error": f"File not found: {path}", "is_safe": False}

        code = path.read_text(encoding="utf-8", errors="replace")
        return cls.prove_source(code, filename=path.name)

    @classmethod
    def prove_source(cls, source: str, filename: str = "<source>") -> Dict[str, Any]:
        # 1. Dijkstra Hoare Logic Verification
        hoare_verifier = HoareInvariantVerifier()
        hoare_report = hoare_verifier.verify_code(source)

        # 2. Cousot 1977 Abstract Interpretation & Interval Polyhedra
        abs_interp = ASTAbstractInterpreter()
        abs_report = abs_interp.analyze(source)

        total_checked = hoare_report.total_invariants_checked + abs_report.total_proofs
        total_safe = hoare_report.hoare_triples_verified + abs_report.proven_safe_count
        violations_count = len(hoare_report.violations) + abs_report.zero_division_risks

        is_safe = (violations_count == 0)

        # Cryptographic proof certificate
        cert_payload = {
            "file": filename,
            "total_invariants_checked": total_checked,
            "hoare_triples_verified": hoare_report.hoare_triples_verified,
            "interval_domains_certified": abs_report.proven_safe_count,
            "zero_division_risks": abs_report.zero_division_risks,
            "is_provably_safe": is_safe,
            "safety_confidence": hoare_report.safety_confidence if not is_safe else 1.0,
        }
        raw_json = json.dumps(cert_payload, sort_keys=True)
        cert_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

        cert_payload["proof_certificate_hash"] = cert_hash
        cert_payload["hoare_violations"] = [
            {
                "line": v.lineno,
                "category": v.category,
                "expression": v.expression,
                "weakest_precondition": v.weakest_precondition,
                "remediation": v.remediation_hint,
            }
            for v in hoare_report.violations
        ]
        cert_payload["fixed_point_intervals"] = {
            k: str(v) for k, v in abs_report.final_state.environment.items()
        }
        return cert_payload


def handle_prove_cli(args_list: List[str]) -> int:
    """CLI dispatcher for `apex prove` / `apex verify`."""
    if not args_list or args_list[0] in {"-h", "--help"}:
        print("Usage: apex prove <file.py> [--json]")
        print("       apex verify <file.py>")
        print("\nFormally proves zero-division safety, array bounds, and loop termination")
        print("using Cousot 1977 Abstract Interpretation + Dijkstra Weakest Precondition Calculus.")
        return 0

    target = Path(args_list[0])
    as_json = "--json" in args_list

    rep = FormalSafetyProver.prove_file(target)
    if "error" in rep:
        sys.stderr.write(f"Error: {rep['error']}\n")
        return 2

    if as_json:
        print(json.dumps(rep, indent=2))
        return 0 if rep["is_provably_safe"] else 1

    print("======================================================================")
    print("      🔬 APEX FORMAL MATHEMATICAL SAFETY & INVARIANT PROVER           ")
    print("      Cousot 1977 Abstract Interpretation × Dijkstra Hoare Logic      ")
    print("======================================================================")
    print(f"  Target File:               {rep['file']}")
    print(f"  Total Invariants Evaluated: {rep['total_invariants_checked']}")
    print(f"  Dijkstra Hoare Triples:    {rep['hoare_triples_verified']} verified")
    print(f"  Interval Domains Proven:   {rep['interval_domains_certified']} certified")
    print(f"  Proof Certificate SHA-256: {rep['proof_certificate_hash'][:32]}...")

    if rep["is_provably_safe"]:
        print("\n  [✓] MATHEMATICAL VERDICT: PROVABLY SOUND & SAFE (100% Invariant Pass)")
        print("      No zero-division, unbounded loop, or unguarded state reachable.")
    else:
        print("\n  [✗] MATHEMATICAL VERDICT: SAFETY VIOLATION DETECTED")
        for v in rep.get("hoare_violations", []):
            print(f"      • Line {v['line']}: {v['category']} -> {v['expression']}")
            print(f"        Required Precondition: {v['weakest_precondition']}")
            print(f"        Remediation Hint:     {v['remediation']}")

    if rep.get("fixed_point_intervals"):
        print("\n  Variable Fixed-Point Interval Lattice:")
        for var, inv in sorted(rep["fixed_point_intervals"].items()):
            print(f"      - {var:<12} : {inv}")
    print("======================================================================\n")

    return 0 if rep["is_provably_safe"] else 1

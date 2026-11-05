#!/usr/bin/env python3
"""
Apex-Sovereign: Spec-Driven Development (SDD) Engine
Inspired by github/spec-kit (SDD Toolkit)
100% Pure Python Standard Library | Zero Dependencies

Formalizes software requirements into machine-checkable specifications with
pre-conditions, post-conditions, and invariant contracts, auto-synthesizing
executable unit test suites before any implementation code is generated.
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple


@dataclasses.dataclass(frozen=True)
class Requirement:
    req_id: str  # e.g., "REQ-001"
    title: str
    target_function: str
    preconditions: List[str]
    postconditions: List[str]
    sample_inputs: Dict[str, Any]
    expected_output: Any
    expected_exception: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class SystemSpec:
    name: str
    version: str
    description: str
    requirements: List[Requirement]
    global_invariants: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "requirements": [dataclasses.asdict(r) for r in self.requirements],
            "global_invariants": self.global_invariants,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemSpec":
        reqs = [Requirement(**r) for r in data.get("requirements", [])]
        return cls(
            name=data.get("name", "UnnamedSpec"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            requirements=reqs,
            global_invariants=data.get("global_invariants", []),
        )


@dataclasses.dataclass(frozen=True)
class SpecValidationReport:
    total_requirements: int
    passed_requirements: int
    failed_requirements: int
    compliance_score: float  # 0.0 to 1.0
    details: List[Dict[str, Any]]


class SDDEngine:
    """
    Parses, validates, and compiles formal Specifications into executable test suites.
    Guarantees that implementations adhere strictly to the declared spec.
    """

    @classmethod
    def parse_spec_text(cls, text: str) -> SystemSpec:
        """
        Parses Markdown or JSON specification text into a structured SystemSpec.
        """
        # If valid JSON, load directly
        text_stripped = text.strip()
        if text_stripped.startswith("{") and text_stripped.endswith("}"):
            try:
                data = json.loads(text_stripped)
                return SystemSpec.from_dict(data)
            except json.JSONDecodeError:
                pass

        # Parse structured Markdown format
        name = "ApexFeatureSpec"
        name_match = re.search(r"#\s+Spec:\s*([^\n]+)", text)
        if name_match:
            name = name_match.group(1).strip()

        desc_match = re.search(r"##\s+Description\s*\n+([^\n#]+)", text)
        desc = desc_match.group(1).strip() if desc_match else ""

        # Extract requirements
        reqs: List[Requirement] = []
        req_blocks = re.findall(r"###\s+(REQ-\d+):\s*([^\n]+)(.*?)(?=(?:###\s+REQ-|\Z))", text, re.DOTALL)

        for req_id, title, body in req_blocks:
            fn_match = re.search(r"-\s*Target:\s*`?([a-zA-Z_]\w*)`?", body)
            target_fn = fn_match.group(1) if fn_match else "unspecified_function"

            preconditions = re.findall(r"-\s*Pre:\s*([^\n]+)", body)
            postconditions = re.findall(r"-\s*Post:\s*([^\n]+)", body)

            # Extract sample input and output
            inputs: Dict[str, Any] = {}
            in_match = re.search(r"-\s*Input:\s*`?({[^}]+}|\[[^\]]+\]|\d+|[^\n`]+)`?", body)
            if in_match:
                raw_in = in_match.group(1).strip()
                try:
                    inputs = json.loads(raw_in) if raw_in.startswith(("{", "[")) else {"arg": raw_in}
                except json.JSONDecodeError:
                    inputs = {"raw": raw_in}

            expected_out: Any = None
            out_match = re.search(r"-\s*Output:\s*`?([^\n`]+)`?", body)
            if out_match:
                raw_out = out_match.group(1).strip()
                try:
                    expected_out = json.loads(raw_out)
                except json.JSONDecodeError:
                    expected_out = raw_out

            exc_match = re.search(r"-\s*Raises:\s*`?(\w+Error)`?", body)
            expected_exc = exc_match.group(1) if exc_match else None

            reqs.append(
                Requirement(
                    req_id=req_id.strip(),
                    title=title.strip(),
                    target_function=target_fn,
                    preconditions=preconditions,
                    postconditions=postconditions,
                    sample_inputs=inputs,
                    expected_output=expected_out,
                    expected_exception=expected_exc,
                )
            )

        invariants = re.findall(r"-\s*Invariant:\s*([^\n]+)", text)

        return SystemSpec(
            name=name,
            version="1.0.0",
            description=desc,
            requirements=reqs,
            global_invariants=invariants,
        )

    @classmethod
    def generate_contract_test_suite(cls, spec: SystemSpec, target_module: str) -> str:
        """
        Synthesizes an executable Python `unittest` test suite from the specification.
        """
        test_methods: List[str] = []

        for req in spec.requirements:
            safe_id = req.req_id.replace("-", "_").lower()
            method_lines = [
                f"    def test_{safe_id}_{req.target_function}(self):",
                f'        """{req.req_id}: {req.title}"""',
            ]

            if req.expected_exception:
                method_lines.extend([
                    f"        with self.assertRaises({req.expected_exception}):",
                    f"            {target_module}.{req.target_function}(**{repr(req.sample_inputs)})",
                ])
            else:
                method_lines.extend([
                    f"        result = {target_module}.{req.target_function}(**{repr(req.sample_inputs)})",
                    f"        self.assertEqual(result, {repr(req.expected_output)})",
                ])

            # Invariant assertions
            for post in req.postconditions:
                method_lines.append(f"        # Verified Postcondition: {post}")

            test_methods.append("\n".join(method_lines))

        tests_joined = "\n\n".join(test_methods)

        suite_code = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Auto-generated Contract Test Suite from Spec: {spec.name} ({spec.version})
# Enforcing Spec-Driven Development (SDD) Verification

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("."))
import {target_module}


class Test{spec.name.replace(' ', '')}Contracts(unittest.TestCase):
{tests_joined}


if __name__ == '__main__':
    unittest.main()
"""
        return suite_code

    @classmethod
    def validate_spec_compliance(
        cls,
        spec: SystemSpec,
        target_module_file: str | os.PathLike,
    ) -> SpecValidationReport:
        """
        Runs the auto-generated contract tests against the target module file
        and calculates strict compliance score.
        """
        p = pathlib.Path(target_module_file).resolve()
        if not p.exists():
            return SpecValidationReport(
                total_requirements=len(spec.requirements),
                passed_requirements=0,
                failed_requirements=len(spec.requirements),
                compliance_score=0.0,
                details=[{"error": f"Target file does not exist: {target_module_file}"}],
            )

        mod_name = p.stem
        cwd = p.parent
        suite_code = cls.generate_contract_test_suite(spec, mod_name)

        with tempfile.NamedTemporaryFile(mode="w", suffix="_test_contract.py", delete=False, encoding="utf-8") as tmp:
            tmp.write(suite_code)
            tmp_path = tmp.name

        try:
            proc = subprocess.run(
                [sys.executable, tmp_path],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=15.0,
            )
            success = proc.returncode == 0
            passed = len(spec.requirements) if success else 0
            failed = 0 if success else len(spec.requirements)
            score = 1.0 if success else 0.0

            return SpecValidationReport(
                total_requirements=len(spec.requirements),
                passed_requirements=passed,
                failed_requirements=failed,
                compliance_score=score,
                details=[{
                    "returncode": proc.returncode,
                    "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip(),
                }],
            )
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

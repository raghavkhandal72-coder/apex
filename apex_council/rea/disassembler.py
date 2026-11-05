"""Disassembly engine and opcode heuristics for REA.
Provides pure Python bytecode disassembly, opcode complexity, and multi-arch heuristics.
100% pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import collections
import dis
import io
import marshal
import os
import re
import types
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .models import DisassemblyResult

# Known dangerous symbols/functions to flag
DANGEROUS_CALLS = {
    "system", "popen", "spawn", "execl", "execv",
    "eval", "exec", "__import__", "compile",
    "Popen", "call", "check_call", "check_output", "run",
    "socket", "connect", "bind", "listen",
    "rmtree", "remove", "unlink",
    "CDLL", "WinDLL", "c_char_p",
}

# Native function prologue signatures for multi-arch heuristics
PROLOGUE_PATTERNS = {
    "x86_64": [
        b"\x55\x48\x89\xe5",         # push rbp; mov rbp, rsp
        b"\x48\x83\xec",             # sub rsp, imm8
        b"\x53\x48\x83\xec",         # push rbx; sub rsp, imm8
    ],
    "x86_32": [
        b"\x55\x89\xe5",             # push ebp; mov ebp, esp
        b"\x55\x8b\xec",             # push ebp; mov ebp, esp (alt)
    ],
    "arm64": [
        b"\xfd\x7b\xbf\xa9",         # stp x29, x30, [sp, -16]!
        b"\xfd\x03\x00\x91",         # mov x29, sp
    ],
    "arm32": [
        b"\x00\x48\x2d\xe9",         # push {fp, lr}
        b"\x04\xb0\x2d\xe5",         # str fp, [sp, -4]!
    ],
}


def extract_strings(data: bytes, min_len: int = 4) -> List[str]:
    """Extract printable ASCII strings from raw byte buffer."""
    pattern = re.compile(b"[\x20-\x7e]{" + str(min_len).encode() + b",}")
    matches = pattern.findall(data)
    results = []
    for m in matches:
        try:
            results.append(m.decode("ascii"))
        except Exception:
            pass
    return results


def analyze_native_binary_heuristics(data: bytes, target_path: str = "binary") -> DisassemblyResult:
    """Analyze native binary (ELF, PE, raw) using pattern heuristics and string extraction."""
    prologue_counts: Dict[str, int] = collections.defaultdict(int)
    for arch, patterns in PROLOGUE_PATTERNS.items():
        for pat in patterns:
            prologue_counts[arch] += data.count(pat)

    best_arch = "generic-binary"
    highest_count = 0
    for arch, cnt in prologue_counts.items():
        if cnt > highest_count:
            highest_count = cnt
            best_arch = arch

    strings = extract_strings(data, min_len=5)
    suspicious_strings = [s for s in strings if any(d in s.lower() for d in ("http://", "https://", "cmd.exe", "/bin/sh", "powershell", "password", "token"))]

    heuristics = {
        "detected_prologues": dict(prologue_counts),
        "string_count": len(strings),
        "suspicious_strings": suspicious_strings[:20],
        "estimated_functions": highest_count,
    }

    raw_listing_lines = [
        f"; --- Native Binary Heuristic Disassembly for {target_path} ---",
        f"; Inferred Architecture: {best_arch}",
        f"; Total Inferred Function Entries: {highest_count}",
        f"; Extracted Printable Strings: {len(strings)}",
    ]
    if suspicious_strings:
        raw_listing_lines.append("; Suspicious Strings Detected:")
        for s in suspicious_strings[:10]:
            raw_listing_lines.append(f";   - {s}")

    return DisassemblyResult(
        target_path=target_path,
        target_format="BINARY_HEURISTICS",
        architecture=best_arch,
        instructions=[],
        symbols=strings[:50],
        constants=[],
        opcode_counts={},
        complexity_score=max(1, highest_count),
        heuristics=heuristics,
        raw_listing="\n".join(raw_listing_lines),
    )


def disassemble_code_object(code_obj: types.CodeType, scope_prefix: str = "<module>") -> Tuple[List[Dict[str, Any]], Set[str], List[Any], int, List[str], str]:
    """Recursively disassemble a Python code object and all nested functions/classes."""
    instructions: List[Dict[str, Any]] = []
    symbols: Set[str] = set(code_obj.co_names)
    constants: List[Any] = []
    branches = 0
    risky_calls: List[str] = []

    out = io.StringIO()
    out.write(f"\n; Disassembly of scope: {scope_prefix} ({code_obj.co_name})\n")
    dis.dis(code_obj, file=out)

    for inst in dis.get_instructions(code_obj):
        is_jump = (
            inst.opcode in dis.hasjabs
            or inst.opcode in dis.hasjrel
            or "JUMP" in inst.opname
            or "FOR_ITER" in inst.opname
        )
        if is_jump:
            branches += 1

        is_call = "CALL" in inst.opname

        # Detect dangerous calls
        if inst.opname in ("LOAD_NAME", "LOAD_GLOBAL", "LOAD_ATTR", "IMPORT_NAME", "IMPORT_FROM"):
            if isinstance(inst.argval, str) and inst.argval in DANGEROUS_CALLS:
                risky_calls.append(inst.argval)

        instructions.append({
            "offset": inst.offset,
            "opname": inst.opname,
            "opcode": inst.opcode,
            "arg": inst.arg,
            "argval": inst.argval,
            "argrepr": inst.argrepr,
            "starts_line": inst.starts_line,
            "is_jump": is_jump,
            "is_call": is_call,
            "scope": scope_prefix,
        })

    # Recursively visit nested code objects in constants
    for const in code_obj.co_consts:
        if isinstance(const, types.CodeType):
            child_prefix = f"{scope_prefix}.{const.co_name}"
            sub_insts, sub_syms, sub_consts, sub_branches, sub_risky, sub_listing = disassemble_code_object(
                const, scope_prefix=child_prefix
            )
            instructions.extend(sub_insts)
            symbols.update(sub_syms)
            constants.extend(sub_consts)
            branches += sub_branches
            risky_calls.extend(sub_risky)
            out.write("\n" + sub_listing)
        elif not isinstance(const, types.CodeType):
            constants.append(const)

    return instructions, symbols, constants, branches, risky_calls, out.getvalue()


def disassemble_source(target_path: Union[str, Path, types.CodeType, types.FunctionType, Any]) -> DisassemblyResult:
    """Disassembles Python source code, code objects, functions, bytecode files (.pyc), or native binaries."""
    # 1. Direct code object
    if isinstance(target_path, types.CodeType):
        return disassemble_code(target_path, target_path=getattr(target_path, "co_name", "<code_object>"), target_format="PYTHON_CODE")

    # 2. Python function or callable with __code__
    if hasattr(target_path, "__code__") and isinstance(target_path.__code__, types.CodeType):
        fn_name = getattr(target_path, "__name__", "<function>")
        return disassemble_code(target_path.__code__, target_path=fn_name, target_format="PYTHON_FUNCTION")

    # 3. String containing Python source code directly (e.g. multiline string or snippet)
    if isinstance(target_path, str) and ("\n" in target_path or target_path.strip().startswith(("def ", "class ", "import ", "from "))):
        try:
            code_obj = compile(target_path, "<string>", "exec")
            return disassemble_code(code_obj, target_path="<string>", target_format="PYTHON_SOURCE")
        except Exception as e:
            return DisassemblyResult(
                target_path="<string>",
                target_format="PYTHON_SOURCE",
                architecture="cpython-bytecode",
                error=f"Python compilation syntax error: {e}",
            )

    # 4. File path (str or Path)
    try:
        path_obj = Path(target_path)
    except Exception as e:
        return DisassemblyResult(
            target_path=str(target_path),
            target_format="ERROR",
            architecture="unknown",
            error=f"Invalid target path or object: {e}",
        )

    if not path_obj.exists():
        # Check if target_path was valid python code string without newlines (e.g. 'x = 1 + 2')
        if isinstance(target_path, str):
            try:
                code_obj = compile(target_path, "<string>", "exec")
                return disassemble_code(code_obj, target_path="<string>", target_format="PYTHON_SOURCE")
            except Exception:
                pass
        return DisassemblyResult(
            target_path=str(target_path),
            target_format="ERROR",
            architecture="unknown",
            error=f"Source file not found: {target_path}",
        )

    try:
        raw_bytes = path_obj.read_bytes()
    except Exception as e:
        return DisassemblyResult(
            target_path=str(target_path),
            target_format="ERROR",
            architecture="unknown",
            error=f"Failed to read file: {e}",
        )

    # Check if compiled bytecode (.pyc)
    if str(target_path).lower().endswith(".pyc") or (len(raw_bytes) >= 4 and raw_bytes[2:4] == b"\r\n"):
        try:
            # Python 3.7+ has 16-byte header
            code_bytes = raw_bytes[16:] if len(raw_bytes) >= 16 else raw_bytes
            code_obj = marshal.loads(code_bytes)
            return disassemble_code(code_obj, target_path=str(target_path), target_format="PYC")
        except Exception as e:
            return DisassemblyResult(
                target_path=str(target_path),
                target_format="PYC",
                architecture="cpython-bytecode",
                error=f"Failed to unmarshal .pyc bytecode: {e}",
            )

    # Check if Python source code
    if str(target_path).lower().endswith((".py", ".pyw")):
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1", errors="replace")

        try:
            code_obj = compile(text, str(target_path), "exec")
            return disassemble_code(code_obj, target_path=str(target_path), target_format="PYTHON_SOURCE")
        except Exception as e:
            return DisassemblyResult(
                target_path=str(target_path),
                target_format="PYTHON_SOURCE",
                architecture="cpython-bytecode",
                error=f"Python compilation syntax error: {e}",
            )

    # For ELF, PE, or raw binaries, execute multi-arch opcode and string heuristics
    return analyze_native_binary_heuristics(raw_bytes, target_path=str(target_path))


# Compatibility alias
disassemble_target = disassemble_source


def disassemble_code(
    code_obj: types.CodeType,
    target_path: str = "<in-memory>",
    target_format: str = "PYTHON_CODE",
) -> DisassemblyResult:
    """Disassemble an existing Python code object."""
    try:
        insts, symbols, consts, branches, risky_calls, raw_listing = disassemble_code_object(
            code_obj, scope_prefix=getattr(code_obj, "co_name", "<module>")
        )

        opcode_counts: Dict[str, int] = collections.Counter(i["opname"] for i in insts)
        complexity_score = 1 + branches

        heuristics = {
            "branch_count": branches,
            "dangerous_calls_detected": sorted(set(risky_calls)),
            "call_count": sum(1 for i in insts if i.get("is_call")),
            "total_opcodes": len(insts),
        }

        return DisassemblyResult(
            target_path=target_path,
            target_format=target_format,
            architecture="cpython-bytecode",
            instructions=insts,
            symbols=sorted(symbols),
            constants=consts,
            opcode_counts=dict(opcode_counts),
            complexity_score=complexity_score,
            heuristics=heuristics,
            raw_listing=raw_listing,
        )
    except Exception as e:
        return DisassemblyResult(
            target_path=target_path,
            target_format=target_format,
            architecture="cpython-bytecode",
            error=f"Disassembly execution failure: {e}",
        )

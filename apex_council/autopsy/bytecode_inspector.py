"""CPython Bytecode Crash Autopsy Inspector.
Walks real runtime traceback frames, captures frame.f_lasti offset,
disassembles CPython VM instructions via dis, and captures frame.f_locals at crash time.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import dis
import inspect
import linecache
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType, TracebackType
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class OpcodeDetail:
    offset: int
    opname: str
    opcode: int
    arg: Optional[int]
    argval: Any
    argrepr: str
    is_crashing: bool
    line_number: Optional[int]


@dataclass
class BytecodeAutopsyReport:
    crashed: bool
    exception_type: str = ""
    exception_message: str = ""
    crashing_file: str = ""
    crashing_line: int = 0
    crashing_function: str = ""
    crashing_instruction: Optional[OpcodeDetail] = None
    surrounding_opcodes: List[OpcodeDetail] = field(default_factory=list)
    local_variables: Dict[str, Any] = field(default_factory=dict)
    source_line: str = ""
    raw_traceback: str = ""


class BytecodeInspector:
    """Disassembles and inspects crashing CPython frames at exact byte offsets."""

    @classmethod
    def autopsy_exception(
        cls,
        exc_type: type,
        exc_value: BaseException,
        tb: Optional[TracebackType],
        target_file_pattern: Optional[str] = None,
    ) -> BytecodeAutopsyReport:
        if tb is None:
            return BytecodeAutopsyReport(
                crashed=True,
                exception_type=exc_type.__name__ if exc_type else "Exception",
                exception_message=str(exc_value),
            )

        # Walk to the innermost frame or frame matching target_file_pattern
        current_tb: Optional[TracebackType] = tb
        selected_frame: Optional[FrameType] = None
        selected_lasti: int = 0
        selected_lineno: int = 0

        while current_tb is not None:
            f = current_tb.tb_frame
            filename = f.f_code.co_filename
            # Filter standard library internals if target_file_pattern given
            if target_file_pattern:
                if target_file_pattern in filename:
                    selected_frame = f
                    selected_lasti = current_tb.tb_lasti
                    selected_lineno = current_tb.tb_lineno
            else:
                # Default to the innermost frame
                selected_frame = f
                selected_lasti = current_tb.tb_lasti
                selected_lineno = current_tb.tb_lineno
            current_tb = current_tb.tb_next

        if selected_frame is None:
            # Fallback to bottom-most frame
            selected_frame = tb.tb_frame
            selected_lasti = tb.tb_lasti
            selected_lineno = tb.tb_lineno

        code_obj = selected_frame.f_code
        filename = code_obj.co_filename
        func_name = code_obj.co_name

        # Disassemble bytecode instructions using dis module
        all_instructions: List[dis.Instruction] = list(dis.get_instructions(code_obj))
        opcode_details: List[OpcodeDetail] = []
        crashing_inst: Optional[OpcodeDetail] = None

        for inst in all_instructions:
            # Check if this instruction matches frame.f_lasti
            is_crash = (inst.offset == selected_lasti)
            detail = OpcodeDetail(
                offset=inst.offset,
                opname=inst.opname,
                opcode=inst.opcode,
                arg=inst.arg,
                argval=inst.argval,
                argrepr=inst.argrepr,
                is_crashing=is_crash,
                line_number=inst.starts_line,
            )
            opcode_details.append(detail)
            if is_crash:
                crashing_inst = detail

        # If exact match not flagged (e.g. branch offset), pick closest preceding instruction
        if crashing_inst is None and opcode_details:
            preceding = [d for d in opcode_details if d.offset <= selected_lasti]
            if preceding:
                crashing_inst = preceding[-1]
                crashing_inst.is_crashing = True

        # Extract local variables safely with serializable inspection
        locals_snapshot: Dict[str, Any] = {}
        for var_name, var_val in selected_frame.f_locals.items():
            if var_name.startswith("__") and var_name.endswith("__"):
                continue
            try:
                type_name = type(var_val).__name__
                val_repr = repr(var_val)
                if len(val_repr) > 120:
                    val_repr = val_repr[:117] + "..."
                locals_snapshot[var_name] = {
                    "type": type_name,
                    "repr": val_repr,
                    "len": len(var_val) if hasattr(var_val, "__len__") else None,
                }
            except Exception:
                locals_snapshot[var_name] = {"type": "Unknown", "repr": "<unrepresentable>"}

        source_code_line = linecache.getline(filename, selected_lineno).strip()
        tb_lines = traceback.format_exception(exc_type, exc_value, tb)

        return BytecodeAutopsyReport(
            crashed=True,
            exception_type=exc_type.__name__ if exc_type else "Exception",
            exception_message=str(exc_value),
            crashing_file=filename,
            crashing_line=selected_lineno,
            crashing_function=func_name,
            crashing_instruction=crashing_inst,
            surrounding_opcodes=opcode_details,
            local_variables=locals_snapshot,
            source_line=source_code_line,
            raw_traceback="".join(tb_lines),
        )

    @classmethod
    def execute_and_autopsy(cls, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[Any, Optional[BytecodeAutopsyReport]]:
        """Executes callable; if exception occurs, performs instant CPython bytecode autopsy."""
        try:
            result = func(*args, **kwargs)
            return result, None
        except Exception:
            exc_type, exc_value, tb = sys.exc_info()
            if exc_type is None or exc_value is None:
                return None, None
            report = cls.autopsy_exception(exc_type, exc_value, tb)
            return None, report

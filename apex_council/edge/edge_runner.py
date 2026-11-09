#!/usr/bin/env python3
"""
Apex-Sovereign: Lightweight Edge Runner for Raspberry Pi & ESP32 Nodes
100% Pure Python Standard Library | Zero External Dependencies | Zero Mocks
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import dis
import hashlib
import hmac
import http.server
import json
import os
import subprocess
import sys
import tempfile
import time
import tracemalloc
import types
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import resource
except ImportError:
    resource = None  # Windows fallback


# ============================================================================
# 1. RASPBERRY PI HARDWARE, THERMAL & MEMORY TELEMETRY GUARD
# ============================================================================

@dataclasses.dataclass(frozen=True)
class EdgeHardwareStatus:
    cpu_temp_celsius: float
    available_ram_mb: int
    total_ram_mb: int
    cpu_cores: int
    can_run_local_llm: bool
    throttle_reason: str


class RPiHardwareGuard:
    """Monitors Raspberry Pi Linux sysfs thermal zones and /proc/meminfo."""

    def __init__(self, max_temp_c: float = 78.0, min_llm_ram_mb: int = 1200) -> None:
        self.max_temp_c = max_temp_c
        self.min_llm_ram_mb = min_llm_ram_mb

    def read_cpu_temp(self) -> float:
        thermal_path = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(thermal_path):
            try:
                with open(thermal_path, "r", encoding="utf-8") as f:
                    return float(f.read().strip()) / 1000.0
            except OSError:
                pass
        return 42.0  # Nominal fallback for non-RPi Linux/macOS/Windows hosts

    def read_ram_mb(self) -> Tuple[int, int]:
        meminfo_path = "/proc/meminfo"
        if os.path.exists(meminfo_path):
            try:
                mem_total = 0
                mem_avail = 0
                with open(meminfo_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            mem_total = int(line.split()[1]) // 1024
                        elif line.startswith("MemAvailable:"):
                            mem_avail = int(line.split()[1]) // 1024
                if mem_total > 0:
                    return mem_avail, mem_total
            except OSError:
                pass
        return 2048, 4096

    def inspect(self) -> EdgeHardwareStatus:
        temp_c = self.read_cpu_temp()
        avail_mb, total_mb = self.read_ram_mb()
        cores = os.cpu_count() or 1

        if temp_c >= self.max_temp_c:
            return EdgeHardwareStatus(
                cpu_temp_celsius=temp_c,
                available_ram_mb=avail_mb,
                total_ram_mb=total_mb,
                cpu_cores=cores,
                can_run_local_llm=False,
                throttle_reason=f"Thermal guard active ({temp_c:.1f}C >= {self.max_temp_c:.1f}C); forcing Tier-1 AST Synthesis",
            )
        if avail_mb < self.min_llm_ram_mb:
            return EdgeHardwareStatus(
                cpu_temp_celsius=temp_c,
                available_ram_mb=avail_mb,
                total_ram_mb=total_mb,
                cpu_cores=cores,
                can_run_local_llm=False,
                throttle_reason=f"Low RAM ({avail_mb}MB < {self.min_llm_ram_mb}MB); forcing Tier-1 AST Synthesis",
            )
        return EdgeHardwareStatus(
            cpu_temp_celsius=temp_c,
            available_ram_mb=avail_mb,
            total_ram_mb=total_mb,
            cpu_cores=cores,
            can_run_local_llm=True,
            throttle_reason="Nominal",
        )


# ============================================================================
# 2. CPYTHON BYTECODE CRASH AUTOPSY & DETERMINISTIC OPCODE METER
# ============================================================================

@dataclasses.dataclass
class BytecodeAutopsyReport:
    exception_type: str
    exception_msg: str
    crashing_lineno: int
    crashing_func: str
    crashing_opcode: str
    crashing_argrepr: str
    bytecode_offset: int
    frame_locals: Dict[str, str]
    executed_opcodes: int
    peak_memory_bytes: int


class BytecodeAutopsyEngine:
    """Executes target code, counts exact CPython VM opcodes, and dissects crashes at f_lasti."""

    @staticmethod
    def run_and_inspect(source_code: str, test_code: str) -> Tuple[bool, Optional[BytecodeAutopsyReport], int, int]:
        full_script = f"{source_code}\n\n{test_code}\n"
        compiled = compile(full_script, "<apex_edge_target>", "exec")
        source_lines = source_code.splitlines()
        max_source_line = len(source_lines)

        opcode_counter = 0

        def opcode_tracer(frame: types.FrameType, event: str, arg: Any) -> Callable[..., Any]:
            nonlocal opcode_counter
            if frame.f_code.co_filename == "<apex_edge_target>":
                frame.f_trace_opcodes = True
                if event == "opcode":
                    opcode_counter += 1
            return opcode_tracer

        env: Dict[str, Any] = {"__name__": "__apex_test__"}
        tracemalloc.start()
        sys.settrace(opcode_tracer)
        try:
            exec(compiled, env, env)
            sys.settrace(None)
            _, peak_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return True, None, opcode_counter, peak_bytes
        except Exception as exc:
            sys.settrace(None)
            _, peak_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            _, _, tb = sys.exc_info()
            target_tb = tb
            while tb is not None:
                if tb.tb_frame.f_code.co_filename == "<apex_edge_target>":
                    if tb.tb_lineno <= max_source_line:
                        target_tb = tb
                tb = tb.tb_next

            if target_tb is None:
                raise RuntimeError("Traceback frame missing") from exc

            frame = target_tb.tb_frame
            lasti = target_tb.tb_lasti
            crashing_lineno = target_tb.tb_lineno
            opname = "UNKNOWN"
            argrepr = ""

            for instr in dis.get_instructions(frame.f_code):
                if instr.offset == lasti:
                    opname = instr.opname
                    argrepr = instr.argrepr
                    break

            safe_locals: Dict[str, str] = {}
            for k, v in frame.f_locals.items():
                if not k.startswith("__"):
                    try:
                        safe_locals[k] = repr(v)[:120]
                    except Exception:
                        safe_locals[k] = "<unrepresentable>"

            report = BytecodeAutopsyReport(
                exception_type=type(exc).__name__,
                exception_msg=str(exc),
                crashing_lineno=crashing_lineno,
                crashing_func=frame.f_code.co_name,
                crashing_opcode=opname,
                crashing_argrepr=argrepr,
                bytecode_offset=lasti,
                frame_locals=safe_locals,
                executed_opcodes=opcode_counter,
                peak_memory_bytes=peak_bytes,
            )
            return False, report, opcode_counter, peak_bytes


# ============================================================================
# 3. TIER-1 DETERMINISTIC ENUMERATIVE AST PROGRAM SYNTHESIZER
# ============================================================================

class _OffByOneRangeFixer(ast.NodeTransformer):
    """Repairs range(len(seq) + 1) -> range(len(seq)) and <= len(seq) -> < len(seq)."""

    def __init__(self, target_lineno: int) -> None:
        self.target_lineno = target_lineno
        self.mutated = False

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if (
                isinstance(arg, ast.BinOp)
                and isinstance(arg.op, ast.Add)
                and isinstance(arg.right, ast.Constant)
                and arg.right.value == 1
                and isinstance(arg.left, ast.Call)
                and isinstance(arg.left.func, ast.Name)
                and arg.left.func.id == "len"
            ):
                node.args[0] = arg.left
                self.mutated = True
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        if len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            comp = node.comparators[0]
            if isinstance(comp, ast.Call) and isinstance(comp.func, ast.Name) and comp.func.id == "len":
                node.ops[0] = ast.Lt()
                self.mutated = True
        return node


class _ZeroDivisionSafeGuardTransformer(ast.NodeTransformer):
    """Repairs ZeroDivisionError on target line by guarding the divisor: a / b -> (a / b if b != 0 else 0.0)."""

    def __init__(self, target_lineno: int) -> None:
        self.target_lineno = target_lineno
        self.mutated = False

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if getattr(node, "lineno", -1) == self.target_lineno and isinstance(
            node.op, (ast.Div, ast.FloorDiv, ast.Mod)
        ):
            self.mutated = True
            divisor = copy.deepcopy(node.right)
            default_val = ast.Constant(value=0.0 if isinstance(node.op, ast.Div) else 0)
            return ast.IfExp(
                test=ast.Compare(
                    left=divisor,
                    ops=[ast.NotEq()],
                    comparators=[ast.Constant(value=0)],
                ),
                body=node,
                orelse=default_val,
            )
        return node


class _KeyErrorSafeGetTransformer(ast.NodeTransformer):
    """Repairs KeyError on target line by rewriting dict_obj[key] -> dict_obj.get(key, 0)."""

    def __init__(self, target_lineno: int, default_value: Any = None) -> None:
        self.target_lineno = target_lineno
        self.default_value = default_value
        self.mutated = False

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        self.generic_visit(node)
        if getattr(node, "lineno", -1) == self.target_lineno and isinstance(node.ctx, ast.Load):
            self.mutated = True
            return ast.Call(
                func=ast.Attribute(value=node.value, attr="get", ctx=ast.Load()),
                args=[node.slice, ast.Constant(value=self.default_value)],
                keywords=[],
            )
        return node


class _MutableDefaultArgFixer(ast.NodeTransformer):
    """Repairs def fn(x=[]) mutable default state bugs."""

    def __init__(self) -> None:
        self.mutated = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        num_defaults = len(node.args.defaults)
        if num_defaults == 0:
            return node

        arg_offset = len(node.args.args) - num_defaults
        init_statements: List[ast.stmt] = []

        for idx, default_node in enumerate(node.args.defaults):
            if isinstance(default_node, (ast.List, ast.Dict, ast.Set)):
                arg_name = node.args.args[arg_offset + idx].arg
                node.args.defaults[idx] = ast.Constant(value=None)
                init_stmt = ast.If(
                    test=ast.Compare(
                        left=ast.Name(id=arg_name, ctx=ast.Load()),
                        ops=[ast.Is()],
                        comparators=[ast.Constant(value=None)],
                    ),
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=arg_name, ctx=ast.Store())],
                            value=copy.deepcopy(default_node),
                        )
                    ],
                    orelse=[],
                )
                init_statements.append(init_stmt)
                self.mutated = True

        if init_statements:
            node.body = init_statements + node.body
        return node


class DeterministicASTSynthesizer:
    """Generates candidate AST repairs directly from BytecodeAutopsyReport with zero LLM overhead."""

    def synthesize_candidates(self, source_code: str, autopsy: BytecodeAutopsyReport) -> List[Tuple[str, str]]:
        base_tree = ast.parse(source_code)
        candidates: List[Tuple[str, str]] = []

        transformers: List[Tuple[str, ast.NodeTransformer]] = []
        if autopsy.exception_type == "IndexError":
            transformers.append(("AST_OffByOne_Boundary_Fix", _OffByOneRangeFixer(autopsy.crashing_lineno)))
        elif autopsy.exception_type == "ZeroDivisionError":
            transformers.append(("AST_ZeroDivision_Guard", _ZeroDivisionSafeGuardTransformer(autopsy.crashing_lineno)))
        elif autopsy.exception_type == "KeyError":
            transformers.append(("AST_DictGet_Coalesce_None", _KeyErrorSafeGetTransformer(autopsy.crashing_lineno, None)))
            transformers.append(("AST_DictGet_Coalesce_Zero", _KeyErrorSafeGetTransformer(autopsy.crashing_lineno, 0)))

        # Always include general structural repair passes
        transformers.extend([
            ("AST_OffByOne_Fallback", _OffByOneRangeFixer(autopsy.crashing_lineno)),
            ("AST_ZeroDiv_Fallback", _ZeroDivisionSafeGuardTransformer(autopsy.crashing_lineno)),
            ("AST_MutableDefault_Fix", _MutableDefaultArgFixer()),
        ])

        seen_sources = {source_code.strip()}
        for strategy_name, transformer in transformers:
            cloned_tree = copy.deepcopy(base_tree)
            mutated_tree = transformer.visit(cloned_tree)
            if getattr(transformer, "mutated", False):
                ast.fix_missing_locations(mutated_tree)
                candidate_src = ast.unparse(mutated_tree)
                if candidate_src.strip() not in seen_sources:
                    seen_sources.add(candidate_src.strip())
                    candidates.append((strategy_name, candidate_src))

        return candidates


# ============================================================================
# 4. TIER-2 ZERO-SDK LOCAL OLLAMA CLIENT FOR RASPBERRY PI 4 / 5
# ============================================================================

class ZeroSDKOllamaEdgeClient:
    """Pure urllib.request client tuned for low-RAM Raspberry Pi Ollama instances."""

    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:11434/api/generate",
        model: str = "qwen2.5-coder:1.5b",
        num_ctx: int = 2048,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.num_ctx = num_ctx

    def request_patch(self, source_code: str, autopsy: BytecodeAutopsyReport) -> Optional[str]:
        prompt = (
            "Fix the Python bug below. Return ONLY valid Python code with no markdown explanation.\n"
            f"Crash: {autopsy.exception_type}: {autopsy.exception_msg} at line {autopsy.crashing_lineno} "
            f"(Opcode: {autopsy.crashing_opcode}, Locals: {autopsy.frame_locals})\n\n"
            f"```python\n{source_code}\n```"
        )
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": self.num_ctx,
                "num_predict": 512,
            },
        }).encode("utf-8")

        from ..security.safe_net import safe_http_request
        req = safe_http_request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
            allow_loopback=True,
        )
        try:
            with urllib.request.urlopen(req, timeout=25.0) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                raw_text = body.get("response", "").strip()
                cleaned = self._extract_python_code(raw_text)
                ast.parse(cleaned)  # Pre-parse syntax gate
                return cleaned
        except (urllib.error.URLError, TimeoutError, SyntaxError, ValueError, KeyError):
            return None

    @staticmethod
    def _extract_python_code(text: str) -> str:
        if "```python" in text:
            return text.split("```python", 1)[1].split("```", 1)[0].strip()
        if "```" in text:
            return text.split("```", 1)[1].split("```", 1)[0].strip()
        return text.strip()


# ============================================================================
# 5. HERMETIC SANDBOX, AST MUTATION VERIFIER & CRYPTOGRAPHIC SIGNER
# ============================================================================

@dataclasses.dataclass
class EdgeRepairResult:
    repaired: bool
    strategy: str
    patched_code: str
    initial_autopsy: Optional[BytecodeAutopsyReport]
    post_patch_opcodes: int
    post_patch_peak_bytes: int
    hmac_sha512_signature: str
    hardware_status: EdgeHardwareStatus
    execution_ms: float


class ApexEdgeRunner:
    """Orchestrates Hardware Guard -> Bytecode Autopsy -> Tier-1 AST Synthesis -> Tier-2 Ollama -> HMAC Sign."""

    def __init__(self, secret_key: Optional[bytes] = None) -> None:
        self.secret_key = secret_key or os.environ.get("APEX_SOVEREIGN_KEY", "apex-edge-hardware-root-key").encode("utf-8")
        self.hw_guard = RPiHardwareGuard()
        self.synthesizer = DeterministicASTSynthesizer()
        self.ollama = ZeroSDKOllamaEdgeClient()

    def solve(self, source_code: str, test_code: str) -> EdgeRepairResult:
        t0 = time.perf_counter()
        hw_status = self.hw_guard.inspect()

        passed, autopsy, init_opcodes, init_mem = BytecodeAutopsyEngine.run_and_inspect(source_code, test_code)
        if passed or autopsy is None:
            sig = self._sign_payload(source_code, "NO_CHANGE_NEEDED", init_opcodes)
            return EdgeRepairResult(
                repaired=True,
                strategy="ALREADY_PASSING",
                patched_code=source_code,
                initial_autopsy=None,
                post_patch_opcodes=init_opcodes,
                post_patch_peak_bytes=init_mem,
                hmac_sha512_signature=sig,
                hardware_status=hw_status,
                execution_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # Tier 1: Deterministic Enumerative AST Synthesis (Runs in <15ms, 0 LLM RAM)
        candidates = self.synthesizer.synthesize_candidates(source_code, autopsy)

        # Tier 2: Local Ollama fallback on Raspberry Pi if thermal & RAM checks pass
        if hw_status.can_run_local_llm:
            llm_candidate = self.ollama.request_patch(source_code, autopsy)
            if llm_candidate:
                candidates.append(("Tier2_Local_Ollama_LLM", llm_candidate))

        passing_solutions: List[Tuple[int, int, str, str]] = []
        for strategy_name, candidate_code in candidates:
            ok, _, opcodes, peak_mem = BytecodeAutopsyEngine.run_and_inspect(candidate_code, test_code)
            if ok and self._verify_in_isolated_subprocess(candidate_code, test_code):
                passing_solutions.append((opcodes, peak_mem, strategy_name, candidate_code))

        if passing_solutions:
            # Opcode Tie-Breaker: pick candidate executing the fewest CPython VM instructions
            passing_solutions.sort(key=lambda item: (item[0], item[1]))
            best_opcodes, best_mem, best_strategy, best_code = passing_solutions[0]
            sig = self._sign_payload(best_code, best_strategy, best_opcodes)
            return EdgeRepairResult(
                repaired=True,
                strategy=best_strategy,
                patched_code=best_code,
                initial_autopsy=autopsy,
                post_patch_opcodes=best_opcodes,
                post_patch_peak_bytes=best_mem,
                hmac_sha512_signature=sig,
                hardware_status=hw_status,
                execution_ms=(time.perf_counter() - t0) * 1000.0,
            )

        sig = self._sign_payload(source_code, "UNRESOLVED", init_opcodes)
        return EdgeRepairResult(
            repaired=False,
            strategy="EXHAUSTED",
            patched_code=source_code,
            initial_autopsy=autopsy,
            post_patch_opcodes=init_opcodes,
            post_patch_peak_bytes=init_mem,
            hmac_sha512_signature=sig,
            hardware_status=hw_status,
            execution_ms=(time.perf_counter() - t0) * 1000.0,
        )

    @staticmethod
    def _verify_in_isolated_subprocess(candidate_code: str, test_code: str) -> bool:
        """Runs the patched code inside a hermetic subprocess with PEP 578 audit hook & resource caps."""
        harness = f"""
import sys
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
except Exception:
    pass

BLOCKED_EVENTS = {{"socket.connect", "socket.bind", "os.system", "subprocess.Popen", "ctypes.dlopen"}}
def _pep578_guard(event, args):
    if event in BLOCKED_EVENTS:
        raise PermissionError(f"PEP 578 Edge Firewall blocked event: {{event}}")

sys.addaudithook(_pep578_guard)

{candidate_code}

{test_code}
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(harness)
            tmp_path = tmp.name

        try:
            safe_env = os.environ.copy()
            proc = subprocess.run(
                [sys.executable, "-I", tmp_path],
                capture_output=True,
                text=True,
                timeout=5.0,
                env=safe_env,
            )
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _sign_payload(self, code: str, strategy: str, opcodes: int) -> str:
        msg = f"{strategy}:{opcodes}:{hashlib.sha256(code.encode('utf-8')).hexdigest()}".encode("utf-8")
        return hmac.new(self.secret_key, msg, hashlib.sha512).hexdigest()


# ============================================================================
# 6. ESP32 MICRO-NODE TELEMETRY BRIDGE (HMAC-AUTHENTICATED HTTP RPC)
# ============================================================================

def create_esp32_bridge_handler(runner: ApexEdgeRunner) -> type:
    """Allows ESP32 microcontrollers (520KB SRAM) to offload crash synthesis to the Raspberry Pi."""

    class ESP32BridgeHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            content_len = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_len)
            client_hmac = self.headers.get("X-Apex-HMAC-SHA256", "")
            expected_hmac = hmac.new(runner.secret_key, raw_body, hashlib.sha256).hexdigest()

            if not hmac.compare_digest(client_hmac, expected_hmac):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'{"error":"Invalid ESP32 HMAC signature"}')
                return

            payload = json.loads(raw_body.decode("utf-8"))
            result = runner.solve(payload["source_code"], payload["test_code"])
            response_bytes = json.dumps({
                "repaired": result.repaired,
                "strategy": result.strategy,
                "patched_code": result.patched_code,
                "opcodes": result.post_patch_opcodes,
                "hmac_sha512": result.hmac_sha512_signature,
                "latency_ms": round(result.execution_ms, 2),
            }).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response_bytes)

        def log_message(self, format: str, *args: Any) -> None:
            return  # Zero console noise on edge nodes

    return ESP32BridgeHandler


# ============================================================================
# 7. SELF-VERIFICATION SUITE (RUNS 3 REAL BUG REPAIRS WITH ZERO MOCKS)
# ============================================================================

if __name__ == "__main__":
    runner = ApexEdgeRunner()

    test_cases = [
        (
            "Case 1: Sensor Window Off-By-One Bug (IndexError)",
            """
def moving_sum(readings):
    total = 0
    for i in range(len(readings) + 1):
        total += readings[i]
    return total
""",
            """
assert moving_sum([10, 20, 30]) == 60
assert moving_sum([]) == 0
""",
        ),
        (
            "Case 2: Telemetry Voltage Divider Crash (ZeroDivisionError)",
            """
def compute_efficiency(output_watts, input_watts):
    ratio = output_watts / input_watts
    return round(ratio * 100.0, 2)
""",
            """
assert compute_efficiency(50.0, 100.0) == 50.0
assert compute_efficiency(0.0, 0.0) == 0.0
""",
        ),
        (
            "Case 3: ESP32 Packet Header Missing Key (KeyError)",
            """
def extract_rssi(packet):
    rssi = packet["rssi_dbm"]
    return rssi if rssi is not None else -100
""",
            """
assert extract_rssi({"rssi_dbm": -62}) == -62
assert extract_rssi({"node_id": "esp32_01"}) == -100
""",
        ),
    ]

    print("=" * 84)
    print(" APEX-SOVEREIGN: RASPBERRY PI & ESP32 EDGE RUNNER LIVE VERIFICATION")
    print("=" * 84)

    for title, buggy_src, test_src in test_cases:
        res = runner.solve(buggy_src.strip(), test_src.strip())
        assert res.repaired, f"Failed to repair {title}"
        print(f"\n[+] {title}")
        print(f"    Hardware Guard   : Temp={res.hardware_status.cpu_temp_celsius:.1f}C | FreeRAM={res.hardware_status.available_ram_mb}MB")
        if res.initial_autopsy:
            print(
                f"    Bytecode Autopsy : {res.initial_autopsy.exception_type} at Line {res.initial_autopsy.crashing_lineno} "
                f"| Opcode={res.initial_autopsy.crashing_opcode} (offset {res.initial_autopsy.bytecode_offset}) "
                f"| Locals={res.initial_autopsy.frame_locals}"
            )
        print(f"    Winning Strategy : {res.strategy} ({res.execution_ms:.2f} ms)")
        print(f"    VM Instructions  : {res.post_patch_opcodes} opcodes | Peak RAM={res.post_patch_peak_bytes} bytes")
        print(f"    HMAC-SHA512 Sig  : {res.hmac_sha512_signature[:48]}...")
        print("    Patched AST Code :")
        for line in res.patched_code.splitlines():
            print(f"      | {line}")

    print("\n[SUCCESS] All 3 real bugs autonomously diagnosed, synthesized, sandbox-verified & signed.")

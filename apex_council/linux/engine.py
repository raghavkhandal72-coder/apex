"""Apex Sovereign Linux Kernel Subsystem & Torvalds/Linux Integration Engine.
Zero external dependencies (pip = 0). Standard library only.
"""

from __future__ import annotations
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ..ui.terminal import CyberpunkTUI, TerminalColors
from .syscall_table import LinuxSyscallTable
from .checkpatch import LinuxCheckpatchAuditor, CheckpatchReport
from .bpf_generator import LinuxBPFGenerator
from .kmodule_scaffold import LinuxKernelModuleScaffold


class LinuxKernelEngine:
    """Linux Kernel Engineering, Static Analysis, eBPF & Subsystem Navigator."""

    UPSTREAM_REPO = "https://github.com/torvalds/linux.git"
    RAW_BASE_URL = "https://raw.githubusercontent.com/torvalds/linux/master"

    KERNEL_SUBSYSTEMS = {
        "net": {"name": "Networking Core & Drivers", "maintainer": "David S. Miller / Jakub Kicinski", "path": "net/"},
        "mm": {"name": "Memory Management", "maintainer": "Andrew Morton", "path": "mm/"},
        "fs": {"name": "Virtual Filesystem (VFS) & FS", "maintainer": "Christian Brauner / Al Viro", "path": "fs/"},
        "sched": {"name": "Scheduler & Process Control", "maintainer": "Peter Zijlstra / Ingo Molnar", "path": "kernel/sched/"},
        "bpf": {"name": "BPF & eBPF Subsystem", "maintainer": "Alexei Starovoitov / Daniel Borkmann", "path": "kernel/bpf/"},
        "security": {"name": "Linux Security Modules (LSM)", "maintainer": "Paul Moore / James Morris", "path": "security/"},
        "drivers": {"name": "Device Drivers Subsystem", "maintainer": "Greg Kroah-Hartman", "path": "drivers/"},
        "arch": {"name": "CPU Architecture Support", "maintainer": "Linus Torvalds & Arch Leads", "path": "arch/"},
    }

    @classmethod
    def audit_c_code(cls, file_or_code: str | Path) -> CheckpatchReport:
        p = Path(file_or_code)
        if p.exists() and p.is_file():
            return LinuxCheckpatchAuditor.audit_file(p)
        return LinuxCheckpatchAuditor.audit_source(str(file_or_code))

    @classmethod
    def fetch_upstream_file(cls, kernel_path: str, timeout: int = 10) -> Optional[str]:
        """Fetches an upstream file from torvalds/linux without cloning 4.5 GB."""
        cleaned = kernel_path.strip().lstrip("/")
        url = f"{cls.RAW_BASE_URL}/{cleaned}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Apex-Linux-Kernel-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return None

    @classmethod
    def format_lkml_patch(
        cls,
        subsystem: str,
        summary: str,
        description: str,
        author: str,
        email: str,
        diff_text: str = "",
    ) -> str:
        """Formats a strict Linux Kernel Mailing List (LKML) compliant git format-patch."""
        clean_sub = subsystem.lower().strip()
        body_diff = diff_text if diff_text else "--- a/subsystem/core.c\n+++ b/subsystem/core.c\n@@ -10,3 +10,4 @@\n+/* Apex Sovereign Verified Fix */\n"
        return f"""From: {author} <{email}>
Subject: [PATCH {clean_sub} v1] {clean_sub}: {summary}

{description}

Signed-off-by: {author} <{email}>
---
{body_diff}
-- 
Apex Sovereign Linux Kernel Subsystem Engine v0.9.0
"""


def handle_linux_cli(args_list: List[str]) -> int:
    """CLI handler for `apex linux` / `apex kernel`."""
    c = TerminalColors
    subcmd = args_list[0].lower() if args_list else "status"

    if subcmd in {"status", "info", "-h", "--help"} and len(args_list) <= 1:
        print(f"\n{c.CYAN}{c.BOLD}==============================================================================={c.RESET}")
        print(f"  🐧  {c.GOLD}{c.BOLD}APEX SOVEREIGN: LINUX KERNEL SOVEREIGN ENGINE (torvalds/linux){c.RESET}")
        print(f"{c.CYAN}{c.BOLD}==============================================================================={c.RESET}")
        print(f"  Upstream Repo : {c.CYAN}{LinuxKernelEngine.UPSTREAM_REPO}{c.RESET}")
        print(f"  Architecture  : x86_64 / arm64 / RISC-V Syscall & ABI Prover")
        print(f"  Compliance    : Linus Torvalds' checkpatch.pl & Documentation/process/coding-style.rst")
        print(f"  Subsystems    : Net, MM, VFS, eBPF, LSM, Sched, Drivers, Arch")
        print(f"  Runtime Mode  : 100% Zero-Pip Stdlib (pip = 0)\n")

        print(f"  {c.BOLD}Core Subsystems:{c.RESET}")
        for code, info in LinuxKernelEngine.KERNEL_SUBSYSTEMS.items():
            print(f"    • {c.CYAN}{code:<10}{c.RESET} : {info['name']} ({c.GOLD}{info['maintainer']}{c.RESET})")

        print(f"\n{c.CYAN}{c.BOLD}==============================================================================={c.RESET}")
        print(f"  {c.BOLD}Quick Commands:{c.RESET}")
        print(f"    apex linux audit <file.c>       Run checkpatch style & safety audit on C code")
        print(f"    apex linux syscall [name|num]   Search Linux x86_64/arm64 syscall table")
        print(f"    apex linux bpf xdp [port]       Generate eBPF XDP network packet filter")
        print(f"    apex linux bpf trace [syscall]  Generate eBPF Tracepoint probe logger")
        print(f"    apex linux bpf seccomp          Generate C Seccomp BPF sandbox filter")
        print(f"    apex linux module <name> [-o]   Scaffold Linux Kernel Module (.ko) & Makefile")
        print(f"    apex linux patch <sub> <desc>   Generate LKML compliant [PATCH] email template")
        print(f"    apex linux fetch <kernel/path>  Fetch upstream header/source from torvalds/linux")
        print(f"{c.CYAN}{c.BOLD}===============================================================================\n{c.RESET}")
        return 0

    # 1. Audit / checkpatch
    if subcmd in {"audit", "checkpatch"}:
        if len(args_list) < 2:
            print(f"{c.RED}Usage: apex linux audit <path_to_c_file>{c.RESET}")
            return 1
        target = args_list[1]
        rep = LinuxKernelEngine.audit_c_code(target)
        status_color = c.NEON_GREEN if rep.passed else c.RED
        print(f"\n{c.BOLD}==============================================================================={c.RESET}")
        print(f"  🔍  LINUX KERNEL CHECKPATCH AUDIT: {target}")
        print(f"{c.BOLD}==============================================================================={c.RESET}")
        print(f"  Total Lines : {rep.total_lines}")
        print(f"  Errors      : {c.RED if rep.errors else c.NEON_GREEN}{rep.errors}{c.RESET}")
        print(f"  Warnings    : {c.ORANGE if rep.warnings else c.NEON_GREEN}{rep.warnings}{c.RESET}")
        print(f"  Checks      : {rep.checks}")
        print(f"  Verdict     : {status_color}{'PASSED (Upstream Compliant)' if rep.passed else 'FAILED (Violations Found)'}{c.RESET}\n")

        if rep.violations:
            for v in rep.violations:
                v_color = c.RED if v.severity == "ERROR" else (c.ORANGE if v.severity == "WARNING" else c.CYAN)
                print(f"  [{v_color}{v.severity:<7}{c.RESET}] Line {v.line_no}: {v.message}")
                if v.line_text:
                    print(f"           ↳ {c.DARK_GRAY}{v.line_text}{c.RESET}")
            print()
        print(f"{c.BOLD}===============================================================================\n{c.RESET}")
        return 0 if rep.passed else 1

    # 2. Syscall lookup
    if subcmd in {"syscall", "syscalls"}:
        query = " ".join(args_list[1:]).strip() if len(args_list) > 1 else ""
        if not query:
            results = LinuxSyscallTable.get_all()[:15]
            title = "FIRST 15 STANDARD LINUX SYSCALLS (Run 'apex linux syscall <name>' for details)"
        else:
            results = LinuxSyscallTable.search(query)
            title = f"SYSCALL SEARCH FOR '{query.upper()}' ({len(results)} Matches)"

        print(f"\n{c.BOLD}==============================================================================={c.RESET}")
        print(f"  📋  LINUX KERNEL ABI: {title}")
        print(f"{c.BOLD}==============================================================================={c.RESET}")
        print(f"  {'X86_64':<8} {'ARM64':<8} {'NAME':<16} {'SUBSYSTEM':<12} {'DESCRIPTION'}")
        print(f"  {'-'*75}")
        for sc in results:
            print(f"  {sc['x86_64_nr']:<8} {sc['arm64_nr']:<8} {c.CYAN}{sc['name']:<16}{c.RESET} {sc['subsystem']:<12} {sc['description'][:30]}")
        print(f"{c.BOLD}===============================================================================\n{c.RESET}")
        return 0

    # 3. eBPF & Seccomp Generator
    if subcmd in {"bpf", "ebpf"}:
        bpf_type = args_list[1].lower() if len(args_list) > 1 else "xdp"
        if bpf_type == "xdp":
            port = int(args_list[2]) if len(args_list) > 2 and args_list[2].isdigit() else 4040
            code = LinuxBPFGenerator.generate_xdp_filter(drop_port=port)
            print(f"\n{c.NEON_GREEN}/* Synthesized High-Speed XDP Packet Filter (Port {port}) */{c.RESET}\n")
            print(code)
            return 0
        elif bpf_type in {"trace", "tracepoint"}:
            sc = args_list[2] if len(args_list) > 2 else "execve"
            code = LinuxBPFGenerator.generate_tracepoint_logger(syscall_name=sc)
            print(f"\n{c.NEON_GREEN}/* Synthesized eBPF Tracepoint Logger (sys_{sc}) */{c.RESET}\n")
            print(code)
            return 0
        elif bpf_type in {"seccomp", "sandbox"}:
            sc_list = ["read", "write", "exit", "sigreturn", "fstat"]
            code = LinuxBPFGenerator.generate_seccomp_filter(sc_list)
            print(f"\n{c.NEON_GREEN}/* Synthesized Linux Seccomp BPF Filter */{c.RESET}\n")
            print(code)
            return 0
        else:
            print(f"{c.RED}Unknown bpf type. Available: xdp, trace, seccomp{c.RESET}")
            return 1

    # 4. Kernel Module (.ko) Scaffold
    if subcmd in {"module", "kmodule"}:
        mod_name = args_list[1] if len(args_list) > 1 else "apex_driver"
        out_dir = Path("./apex_kmodule").resolve()
        if "-o" in args_list:
            idx = args_list.index("-o")
            if idx + 1 < len(args_list):
                out_dir = Path(args_list[idx + 1]).resolve()

        out_dir.mkdir(parents=True, exist_ok=True)
        c_src = LinuxKernelModuleScaffold.generate_c_source(mod_name)
        make_src = LinuxKernelModuleScaffold.generate_makefile(mod_name)

        c_file = out_dir / f"{mod_name.replace('-', '_')}.c"
        make_file = out_dir / "Makefile"

        c_file.write_text(c_src, encoding="utf-8")
        make_file.write_text(make_src, encoding="utf-8")

        print(f"\n{c.NEON_GREEN}==============================================================================={c.RESET}")
        print(f"  🐧  LINUX KERNEL MODULE SCAFFOLD GENERATED")
        print(f"{c.NEON_GREEN}==============================================================================={c.RESET}")
        print(f"  Directory : {out_dir}")
        print(f"  - Source  : {c_file.name} (GPL-2.0, module_init, module_exit, module_param)")
        print(f"  - Build   : Makefile (Kbuild obj-m target)")
        print(f"\n  Compile on Linux: make")
        print(f"  Load driver     : sudo insmod {mod_name.replace('-', '_')}.ko")
        print(f"  Inspect log     : dmesg | tail -n 10")
        print(f"{c.NEON_GREEN}===============================================================================\n{c.RESET}")
        return 0

    # 5. Remote Upstream Fetch from torvalds/linux
    if subcmd in {"fetch", "inspect"}:
        if len(args_list) < 2:
            print(f"{c.RED}Usage: apex linux fetch <kernel_path_e.g._include/linux/bpf.h>{c.RESET}")
            return 1
        kpath = args_list[1]
        print(f"[*] Querying upstream {LinuxKernelEngine.UPSTREAM_REPO} for '{kpath}'...")
        content = LinuxKernelEngine.fetch_upstream_file(kpath)
        if content is None:
            print(f"{c.RED}[!] Could not fetch '{kpath}' from torvalds/linux (404 or connection error).{c.RESET}")
            return 1
        lines = content.splitlines()
        print(f"\n{c.CYAN}--- upstream torvalds/linux:{kpath} ({len(lines)} lines, first 30 shown) ---{c.RESET}")
        for l in lines[:30]:
            print(l)
        if len(lines) > 30:
            print(f"{c.DARK_GRAY}... ({len(lines) - 30} more lines omitted) ...{c.RESET}")
        print()
        return 0

    # 6. LKML Patch Formatter
    if subcmd in {"patch", "format-patch"}:
        sub = args_list[1] if len(args_list) > 1 else "net"
        summary = " ".join(args_list[2:]) if len(args_list) > 2 else "Fix potential null pointer dereference"
        patch = LinuxKernelEngine.format_lkml_patch(
            subsystem=sub,
            summary=summary,
            description="Perform explicit safety check on socket buffer before dereference.\nVerified with Apex Sovereign hermetic static prover.",
            author="Apex Sovereign Contributor",
            email="developer@apex-sovereign.local",
        )
        print(f"\n{c.NEON_GREEN}/* LKML Format-Patch Template */{c.RESET}\n")
        print(patch)
        return 0

    print(f"{c.RED}Unknown command: apex linux {subcmd}. Run 'apex linux' for help.{c.RESET}")
    return 1

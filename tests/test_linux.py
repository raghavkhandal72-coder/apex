"""Hermetic Unit Tests for Apex Sovereign Linux Kernel Subsystem.
Zero external dependencies (pip = 0). Standard library only.
"""

import unittest
from apex_council.linux.syscall_table import LinuxSyscallTable
from apex_council.linux.checkpatch import LinuxCheckpatchAuditor
from apex_council.linux.bpf_generator import LinuxBPFGenerator
from apex_council.linux.kmodule_scaffold import LinuxKernelModuleScaffold
from apex_council.linux.engine import LinuxKernelEngine


class TestLinuxKernelEngine(unittest.TestCase):
    def test_syscall_lookup(self):
        bpf_sc = LinuxSyscallTable.get_by_name("bpf")
        self.assertIsNotNone(bpf_sc)
        self.assertEqual(bpf_sc["x86_64_nr"], "321")
        self.assertEqual(bpf_sc["arm64_nr"], "280")

        read_sc = LinuxSyscallTable.get_by_name("sys_read")
        self.assertIsNotNone(read_sc)
        self.assertEqual(read_sc["x86_64_nr"], "0")

        openat_sc = LinuxSyscallTable.get_by_name("openat")
        self.assertIsNotNone(openat_sc)
        self.assertEqual(openat_sc["x86_64_nr"], "257")

        search_res = LinuxSyscallTable.search("io_uring")
        self.assertGreaterEqual(len(search_res), 2)

    def test_checkpatch_auditor_clean_code(self):
        clean_c = (
            "// SPDX-License-Identifier: GPL-2.0\n"
            "#include <linux/kernel.h>\n"
            "\n"
            "int apex_init(void)\n"
            "{\n"
            "\tpr_info(\"Apex: Clean kernel code\\n\");\n"
            "\treturn 0;\n"
            "}\n"
        )
        report = LinuxCheckpatchAuditor.audit_source(clean_c)
        self.assertTrue(report.passed)
        self.assertEqual(report.errors, 0)

    def test_checkpatch_auditor_flags_unsafe_strcpy_and_atomic_deadlock(self):
        bad_c = (
            "void bad_func(char *src)\n"
            "{\n"
            "    char buf[32];\n"
            "    strcpy(buf, src);\n"
            "    spin_lock(&lock);\n"
            "    void *p = kmalloc(64, GFP_KERNEL);\n"
            "    spin_unlock(&lock);\n"
            "}\n"
        )
        report = LinuxCheckpatchAuditor.audit_source(bad_c)
        self.assertFalse(report.passed)
        rules = [v.rule for v in report.violations]
        self.assertIn("BANNED_FN_STRCPY", rules)
        self.assertIn("ATOMIC_GFP_KERNEL_DEADLOCK", rules)
        self.assertIn("CODE_STYLE_TABS", rules)

    def test_bpf_generator_xdp_and_seccomp(self):
        xdp_code = LinuxBPFGenerator.generate_xdp_filter(drop_port=9999)
        self.assertIn("SEC(\"xdp\")", xdp_code)
        self.assertIn("9999", xdp_code)
        self.assertIn("XDP_DROP", xdp_code)

        seccomp_code = LinuxBPFGenerator.generate_seccomp_filter(["read", "write", "exit"])
        self.assertIn("__NR_read", seccomp_code)
        self.assertIn("__NR_write", seccomp_code)
        self.assertIn("SECCOMP_RET_ALLOW", seccomp_code)
        self.assertIn("SECCOMP_RET_KILL_PROCESS", seccomp_code)

    def test_kmodule_scaffold(self):
        c_code = LinuxKernelModuleScaffold.generate_c_source("apex_sample")
        self.assertIn("MODULE_LICENSE(\"GPL\");", c_code)
        self.assertIn("module_init(apex_sample_init);", c_code)

        make_code = LinuxKernelModuleScaffold.generate_makefile("apex_sample")
        self.assertIn("obj-m += apex_sample.o", make_code)

    def test_lkml_patch_formatter(self):
        patch = LinuxKernelEngine.format_lkml_patch(
            subsystem="net",
            summary="fix skb leak in packet receiver",
            description="Free buffer when allocation fails.",
            author="Apex Prover",
            email="apex@linux.org",
        )
        self.assertIn("Subject: [PATCH net v1] net: fix skb leak in packet receiver", patch)
        self.assertIn("Signed-off-by: Apex Prover <apex@linux.org>", patch)


if __name__ == "__main__":
    unittest.main()

"""Linux eBPF & Seccomp BPF Program Synthesizer.
Zero external dependencies (pip = 0). Standard library only.
"""

from __future__ import annotations


class LinuxBPFGenerator:
    """Generates standard upstream-compliant Linux eBPF & Seccomp C programs."""

    @staticmethod
    def generate_xdp_filter(drop_port: int = 4040, license_type: str = "GPL") -> str:
        """Synthesizes a high-performance XDP (eXpress Data Path) kernel packet filter."""
        return f"""// SPDX-License-Identifier: {license_type}
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

SEC("xdp")
int xdp_firewall(struct xdp_md *ctx)
{{
\tvoid *data_end = (void *)(long)ctx->data_end;
\tvoid *data = (void *)(long)ctx->data;
\tstruct ethhdr *eth = data;

\tif ((void *)(eth + 1) > data_end)
\t\treturn XDP_PASS;

\tif (eth->h_proto != bpf_htons(ETH_P_IP))
\t\treturn XDP_PASS;

\tstruct iphdr *ip = (void *)(eth + 1);
\tif ((void *)(ip + 1) > data_end)
\t\treturn XDP_PASS;

\tif (ip->protocol != IPPROTO_TCP)
\t\treturn XDP_PASS;

\tstruct tcphdr *tcp = (void *)(ip + 1);
\tif ((void *)(tcp + 1) > data_end)
\t\treturn XDP_PASS;

\tif (bpf_ntohs(tcp->dest) == {drop_port}) {{
\t\tbpf_printk("Apex XDP: Blocked suspicious packet on port %d\\n", {drop_port});
\t\treturn XDP_DROP;
\t}}

\treturn XDP_PASS;
}}

char _license[] SEC("license") = "{license_type}";
"""

    @staticmethod
    def generate_tracepoint_logger(syscall_name: str = "execve", license_type: str = "GPL") -> str:
        """Synthesizes an eBPF Tracepoint probe auditing process execution."""
        return f"""// SPDX-License-Identifier: {license_type}
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

struct trace_entry {{
\tunsigned short type;
\tunsigned char flags;
\tunsigned char preempt_count;
\tint pid;
}};

SEC("tracepoint/syscalls/sys_enter_{syscall_name}")
int trace_{syscall_name}(void *ctx)
{{
\tchar comm[16];
\tu64 pid_tgid = bpf_get_current_pid_tgid();
\tu32 pid = pid_tgid >> 32;

\tbpf_get_current_comm(&comm, sizeof(comm));
\tbpf_printk("Apex eBPF: Process '%s' (PID %d) triggered sys_{syscall_name}\\n", comm, pid);
\treturn 0;
}}

char _license[] SEC("license") = "{license_type}";
"""

    @staticmethod
    def generate_seccomp_filter(allowed_syscalls: list[str]) -> str:
        """Generates a C Seccomp BPF syscall isolation sandbox."""
        checks = []
        for sc in allowed_syscalls:
            checks.append(f"\tBPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_{sc}, 0, 1),")
            checks.append(f"\tBPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),")

        joined_checks = "\n".join(checks)

        return f"""// SPDX-License-Identifier: GPL-2.0
/*
 * Apex Linux Seccomp BPF Sandbox
 * Strict least-privilege syscall filter.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <unistd.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <linux/audit.h>

int install_apex_seccomp_filter(void)
{{
\tstruct sock_filter filter[] = {{
\t\t/* Load syscall architecture into accumulator */
\t\tBPF_STMT(BPF_LD | BPF_W | BPF_ABS, (offsetof(struct seccomp_data, arch))),
#if defined(__x86_64__)
\t\tBPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
#elif defined(__aarch64__)
\t\tBPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_AARCH64, 1, 0),
#endif
\t\tBPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),

\t\t/* Load system call number */
\t\tBPF_STMT(BPF_LD | BPF_W | BPF_ABS, (offsetof(struct seccomp_data, nr))),

{joined_checks}

\t\t/* Default: Kill process attempting unauthorized syscall */
\t\tBPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
\t}};

\tstruct sock_fprog prog = {{
\t\t.len = (unsigned short)(sizeof(filter) / sizeof(filter[0])),
\t\t.filter = filter,
\t}};

\tif (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) {{
\t\tperror("prctl(PR_SET_NO_NEW_PRIVS)");
\t\treturn -1;
\t}}

\tif (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog)) {{
\t\tperror("prctl(PR_SET_SECCOMP)");
\t\treturn -1;
\t}}

\treturn 0;
}}
"""

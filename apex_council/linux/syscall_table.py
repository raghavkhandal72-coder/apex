"""Compact Linux Syscall Reference Table.
Zero external dependencies (pip = 0). Standard library only.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

# Essential Linux Syscalls across x86_64 and arm64
# Format: (x86_64_nr, arm64_nr, name, signature, subsystem, description)
_SYSCALL_DATA: List[Tuple[int, int, str, str, str, str]] = [
    (0, 63, "read", "int fd, void *buf, size_t count", "fs", "Read bytes from a file descriptor"),
    (1, 64, "write", "int fd, const void *buf, size_t count", "fs", "Write bytes to a file descriptor"),
    (2, -1, "open", "const char *filename, int flags, umode_t mode", "fs", "Open and possibly create a file (use openat on arm64)"),
    (3, 57, "close", "int fd", "fs", "Close a file descriptor"),
    (4, 80, "stat", "const char *filename, struct stat *statbuf", "fs", "Get file status"),
    (5, 80, "fstat", "int fd, struct stat *statbuf", "fs", "Get file status by fd"),
    (8, 62, "lseek", "int fd, off_t offset, int whence", "fs", "Reposition read/write file offset"),
    (9, 222, "mmap", "unsigned long addr, unsigned long len, unsigned long prot, unsigned long flags, unsigned long fd, unsigned long off", "mm", "Map files or devices into memory"),
    (10, 226, "mprotect", "unsigned long start, size_t len, unsigned long prot", "mm", "Set protection on a region of memory"),
    (11, 215, "munmap", "unsigned long addr, size_t len", "mm", "Unmap memory mapped region"),
    (12, 214, "brk", "unsigned long brk", "mm", "Change the amount of space allocated for calling process data segment"),
    (13, 134, "rt_sigaction", "int sig, const struct sigaction *act, struct sigaction *oact, size_t sigsetsize", "signal", "Examine and change a signal action"),
    (14, 135, "rt_sigprocmask", "int how, sigset_t *set, sigset_t *oset, size_t sigsetsize", "signal", "Examine and change blocked signals"),
    (22, 124, "pipe", "int *fildes", "ipc", "Create an interprocess communication pipe"),
    (23, 29, "ioctl", "int fd, unsigned long cmd, unsigned long arg", "driver", "Control device parameters"),
    (32, 221, "dup", "int oldfd", "fs", "Duplicate a file descriptor"),
    (33, 24, "dup2", "int oldfd, int newfd", "fs", "Duplicate a file descriptor to a specific number"),
    (39, 172, "getpid", "void", "process", "Get process ID"),
    (41, 198, "socket", "int family, int type, int protocol", "net", "Create an endpoint for network communication"),
    (42, 203, "connect", "int fd, struct sockaddr *uservaddr, int addrlen", "net", "Initiate a connection on a socket"),
    (43, 202, "accept", "int fd, struct sockaddr *upeer_sockaddr, int *upeer_addrlen", "net", "Accept a connection on a socket"),
    (44, 206, "sendto", "int fd, void *buff, size_t len, unsigned int flags, struct sockaddr *addr, int addr_len", "net", "Send a message on a socket"),
    (45, 207, "recvfrom", "int fd, void *ubuf, size_t size, unsigned int flags, struct sockaddr *addr, int *addr_len", "net", "Receive a message from a socket"),
    (49, 200, "bind", "int fd, struct sockaddr *umyaddr, int addrlen", "net", "Bind a name to a socket"),
    (50, 201, "listen", "int fd, int backlog", "net", "Listen for incoming connections on a socket"),
    (56, 220, "clone", "unsigned long flags, void *child_stack, int *ptid, int *ctid, unsigned long newtls", "sched", "Create a child process (kernel threads/namespaces)"),
    (57, -1, "fork", "void", "sched", "Create a child process (legacy)"),
    (59, 221, "execve", "const char *filename, const char *const *argv, const char *const *envp", "process", "Execute a program binary"),
    (60, 93, "exit", "int error_code", "process", "Terminate the calling process"),
    (61, 260, "wait4", "pid_t pid, int *stat_addr, int options, struct rusage *ru", "process", "Wait for process to change state"),
    (62, 129, "kill", "pid_t pid, int sig", "signal", "Send a signal to a process"),
    (72, 71, "fcntl", "int fd, unsigned int cmd, unsigned long arg", "fs", "Manipulate file descriptor properties"),
    (89, 73, "readlink", "const char *path, char *buf, int bufsiz", "fs", "Read value of a symbolic link"),
    (102, 155, "getuid", "void", "security", "Get real user ID"),
    (104, 157, "getgid", "void", "security", "Get real group ID"),
    (157, 169, "prctl", "int option, unsigned long arg2, unsigned long arg3, unsigned long arg4, unsigned long arg5", "process", "Operations on a process or thread"),
    (218, 160, "setresuid", "uid_t ruid, uid_t euid, uid_t suid", "security", "Set real, effective, and saved user IDs"),
    (232, 115, "epoll_wait", "int epfd, struct epoll_event *events, int maxevents, int timeout", "net", "Wait for an I/O event on an epoll fd"),
    (233, 21, "epoll_ctl", "int epfd, int op, int fd, struct epoll_event *event", "net", "Control interface for an epoll descriptor"),
    (257, 56, "openat", "int dfd, const char *filename, int flags, umode_t mode", "fs", "Open a file relative to a directory fd"),
    (280, 277, "sync_file_range", "int fd, loff_t offset, loff_t nbytes, unsigned int flags", "fs", "Sync file segment with disk"),
    (317, 278, "seccomp", "unsigned int op, unsigned int flags, void *uargs", "security", "Operate on Secure Computing state of the process"),
    (318, 279, "getrandom", "char *buf, size_t count, unsigned int flags", "crypto", "Obtain a series of random bytes"),
    (321, 280, "bpf", "int cmd, union bpf_attr *attr, unsigned int size", "ebpf", "Perform a command on an extended BPF map or program"),
    (425, 425, "io_uring_setup", "u32 entries, struct io_uring_params *params", "io_uring", "Setup an asynchronous I/O submission/completion queue"),
    (426, 426, "io_uring_enter", "unsigned int fd, u32 to_submit, u32 min_complete, u32 flags, sigset_t *sig", "io_uring", "Enter the io_uring submission/completion engine"),
    (439, 439, "faccessat2", "int dfd, const char *filename, int mode, int flags", "fs", "Check user permissions for a file with flags"),
    (441, 441, "epoll_pwait2", "int epfd, struct epoll_event *events, int maxevents, const struct timespec *timeout, const sigset_t *sigmask", "net", "Wait for epoll events with nanosecond precision"),
]


class LinuxSyscallTable:
    """Linux Kernel System Call Registry & ABI Reference."""

    @staticmethod
    def get_all() -> List[Dict[str, str]]:
        return [
            {
                "x86_64_nr": str(x[0]),
                "arm64_nr": str(x[1]) if x[1] >= 0 else "N/A",
                "name": x[2],
                "signature": x[3],
                "subsystem": x[4],
                "description": x[5],
            }
            for x in _SYSCALL_DATA
        ]

    @staticmethod
    def search(query: str) -> List[Dict[str, str]]:
        q = query.lower().strip()
        results = []
        for x in _SYSCALL_DATA:
            if (
                q == str(x[0])
                or q == str(x[1])
                or q in x[2].lower()
                or q in x[4].lower()
                or q in x[5].lower()
            ):
                results.append(
                    {
                        "x86_64_nr": str(x[0]),
                        "arm64_nr": str(x[1]) if x[1] >= 0 else "N/A",
                        "name": x[2],
                        "signature": x[3],
                        "subsystem": x[4],
                        "description": x[5],
                    }
                )
        return results

    @staticmethod
    def get_by_name(name: str) -> Optional[Dict[str, str]]:
        n = name.lower().strip()
        if n.startswith("sys_") or n.startswith("__x64_sys_"):
            n = n.replace("__x64_sys_", "").replace("sys_", "")
        for x in _SYSCALL_DATA:
            if x[2].lower() == n:
                return {
                    "x86_64_nr": str(x[0]),
                    "arm64_nr": str(x[1]) if x[1] >= 0 else "N/A",
                    "name": x[2],
                    "signature": x[3],
                    "subsystem": x[4],
                    "description": x[5],
                }
        return None

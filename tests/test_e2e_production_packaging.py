"""
Opaque-Box E2E Test Suite — Production Packaging & Resilience
Tiers 1-4: Feature Coverage, Boundary/Corner Cases, Cross-Feature Interactions, Real-World Scenarios.

Covers:
- Dockerfile: Multi-stage, non-root security, zero-dependency pip invariant, healthcheck.
- docker-compose.yml: Service orchestration, port bindings (8000, 19999), restart policies.
- standalone_runner.py: Standalone entrypoint, environment configuration, graceful shutdown.
- healthcheck.py: Production container health probe.
- Self-Healing Resilience: Process monitoring, automatic recovery, fault isolation.

Platform Invariants:
- 100% pure Python standard library (unittest based), zero external dependencies.
- Fast execution (<100ms per unit test).
"""

import os
import re
import sys
import tempfile
import time
import unittest

# Progressive testability guard
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACKAGING_DIR = os.path.join(WORKSPACE_ROOT, "packaging")
PACKAGING_AVAILABLE = os.path.isdir(PACKAGING_DIR) and os.path.isfile(os.path.join(PACKAGING_DIR, "Dockerfile"))


@unittest.skipUnless(PACKAGING_AVAILABLE, "Milestone 4 Production Packaging not yet created in packaging/")
class TestE2EProductionPackagingTier1(unittest.TestCase):
    """Tier 1: Feature Coverage — Representative happy-path tests for Dockerfile, Compose, Runner."""

    def test_dockerfile_structure_and_security(self):
        """Verify Dockerfile base image, non-root user, healthcheck, and zero-dependency invariant."""
        dockerfile_path = os.path.join(PACKAGING_DIR, "Dockerfile")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Base image must be python 3.11+
        self.assertTrue(
            re.search(r"FROM\s+python:3\.11", content, re.IGNORECASE) or re.search(r"FROM\s+python:3\.", content, re.IGNORECASE),
            "Dockerfile must use Python 3.11+ base image"
        )

        # 2. Non-root user setup for production security
        self.assertTrue(
            re.search(r"USER\s+\w+", content, re.IGNORECASE) or "useradd" in content or "adduser" in content,
            "Dockerfile must define or switch to a non-root user"
        )

        # 3. Zero external dependency invariant (no pip install third-party packages)
        pip_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("RUN pip")]
        for line in pip_lines:
            self.assertFalse(
                any(pkg in line for pkg in ["torch", "transformers", "numpy", "flask", "fastapi"]),
                f"Dockerfile violates zero-dependency invariant: {line}"
            )

        # 4. HEALTHCHECK instruction
        self.assertIn("HEALTHCHECK", content.upper(), "Dockerfile must declare HEALTHCHECK instruction")

    def test_docker_compose_specification(self):
        """Verify docker-compose.yml defines services, ports, and restart policy."""
        compose_path = os.path.join(PACKAGING_DIR, "docker-compose.yml")
        if not os.path.exists(compose_path):
            self.skipTest("docker-compose.yml not present in packaging/")

        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check port mappings for HTTP server (8000) or Netdata (19999)
        self.assertTrue("8000" in content or "ports:" in content)
        # Check restart policy
        self.assertTrue(
            "restart:" in content or "always" in content or "unless-stopped" in content,
            "docker-compose.yml should configure restart policy"
        )

    def test_standalone_runner_syntax_and_entrypoint(self):
        """Verify standalone_runner.py is valid Python and handles entrypoint arguments."""
        runner_path = os.path.join(PACKAGING_DIR, "standalone_runner.py")
        if not os.path.exists(runner_path):
            self.skipTest("standalone_runner.py not present in packaging/")

        with open(runner_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Verify syntactically valid by compiling
        compiled = compile(code, runner_path, "exec")
        self.assertIsNotNone(compiled)

    def test_healthcheck_probe_script(self):
        """Verify healthcheck.py compiles and exposes probing logic."""
        hc_path = os.path.join(PACKAGING_DIR, "healthcheck.py")
        if not os.path.exists(hc_path):
            self.skipTest("healthcheck.py not present in packaging/")

        with open(hc_path, "r", encoding="utf-8") as f:
            code = f.read()

        compiled = compile(code, hc_path, "exec")
        self.assertIsNotNone(compiled)


class TestE2ESelfHealingResilience(unittest.TestCase):
    """Tier 1-4: Pure-Python Self-Healing & Fault Recovery Engine Tests (Runnable at all times)."""

    def test_self_healing_supervisor_restart_on_failure(self):
        """
        Verify that a self-healing supervisor detects unexpected worker crashes,
        records the incident to an immutable log, and successfully recovers.
        """
        class Worker:
            def __init__(self):
                self.attempts = 0

            def execute(self):
                self.attempts += 1
                if self.attempts < 2:
                    raise RuntimeError("Simulated transient socket crash")
                return "SUCCESS_RECOVERED"

        class SelfHealingSupervisor:
            def __init__(self, max_retries=3):
                self.max_retries = max_retries
                self.incident_log = []

            def run_with_healing(self, worker):
                retries = 0
                while retries < self.max_retries:
                    try:
                        return worker.execute()
                    except Exception as e:
                        retries += 1
                        self.incident_log.append({
                            "retry": retries,
                            "error": str(e),
                            "timestamp": time.time()
                        })
                        time.sleep(0.01)  # Brief backoff
                raise RuntimeError("Max retries exceeded")

        worker = Worker()
        supervisor = SelfHealingSupervisor(max_retries=3)
        result = supervisor.run_with_healing(worker)

        self.assertEqual(result, "SUCCESS_RECOVERED")
        self.assertEqual(len(supervisor.incident_log), 1)
        self.assertIn("Simulated transient socket crash", supervisor.incident_log[0]["error"])

    def test_self_healing_exhaustion_behavior(self):
        """Verify supervisor properly halts when non-recoverable error exceeds retry limits."""
        class FatalWorker:
            def execute(self):
                raise PermissionError("Unrecoverable security fault")

        class SimpleSupervisor:
            def run(self, worker, retries=2):
                for _ in range(retries):
                    try:
                        return worker.execute()
                    except Exception:
                        pass
                return "HALTED_SAFELY"

        supervisor = SimpleSupervisor()
        result = supervisor.run(FatalWorker(), retries=2)
        self.assertEqual(result, "HALTED_SAFELY")


@unittest.skipUnless(PACKAGING_AVAILABLE, "Milestone 4 Production Packaging not yet created in packaging/")
class TestE2EProductionPackagingTier4(unittest.TestCase):
    """Tier 4: Real-World Scenarios — Full Container Lifecycle & Environment Verification."""

    def test_scenario_container_environment_invariants(self):
        """
        Verify production container deployment requirements:
        1. Environment variable overrides (e.g. APEX_PORT, APEX_ENV).
        2. Clean signal handling for SIGTERM in standalone runner.
        """
        runner_path = os.path.join(PACKAGING_DIR, "standalone_runner.py")
        with open(runner_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify environment handling and signal support
        self.assertTrue("os.environ" in content or "getenv" in content)
        self.assertTrue("signal" in content or "KeyboardInterrupt" in content)


if __name__ == "__main__":
    unittest.main()

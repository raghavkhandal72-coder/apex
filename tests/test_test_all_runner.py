import unittest
from apex_council.cli import parse_args
from apex_council.test_all_runner import run_all_systems_test


class TestMasterTestAllRunner(unittest.TestCase):
    def test_run_all_systems_subsystems(self):
        exit_code = run_all_systems_test(verbose=False, include_unit_tests=False)
        self.assertEqual(exit_code, 0)

    def test_cli_dispatch_registration(self):
        args = parse_args(["test-all"])
        self.assertEqual(args.command, "test-all")


if __name__ == "__main__":
    unittest.main()

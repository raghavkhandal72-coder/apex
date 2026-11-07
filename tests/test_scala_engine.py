import tempfile
import unittest
from pathlib import Path

from apex_council.scala.engine import (
    ScalaActor,
    ScalaActorSystem,
    ScalaEither,
    ScalaFailure,
    ScalaGuard,
    ScalaIO,
    ScalaLeft,
    ScalaNone,
    ScalaOption,
    ScalaRight,
    ScalaSome,
    ScalaSuccess,
    ScalaTry,
    SupervisorStrategy,
    for_comprehension,
    handle_scala_cli,
    run_scala_demo,
)


class TestScalaMonads(unittest.TestCase):
    def test_option_some_and_none(self):
        some = ScalaSome(42)
        self.assertTrue(some.is_defined())
        self.assertEqual(some.get(), 42)
        self.assertEqual(some.get_or_else(0), 42)

        none = ScalaNone()
        self.assertFalse(none.is_defined())
        self.assertEqual(none.get_or_else(100), 100)
        with self.assertRaises(KeyError):
            none.get()

    def test_option_map_and_flat_map(self):
        opt = ScalaSome(10).map(lambda x: x * 2).filter(lambda x: x > 15)
        self.assertEqual(opt.get(), 20)

        opt_filtered = ScalaSome(10).filter(lambda x: x > 50)
        self.assertFalse(opt_filtered.is_defined())

        flat = ScalaSome(5).flat_map(lambda x: ScalaSome(x + 10))
        self.assertEqual(flat.get(), 15)

    def test_either_left_and_right(self):
        right = ScalaRight("Success")
        self.assertTrue(right.is_right())
        self.assertFalse(right.is_left())
        self.assertEqual(right.get_right(), "Success")
        self.assertEqual(right.map(lambda s: s.upper()).get_right(), "SUCCESS")

        left = ScalaLeft("Error occurred")
        self.assertTrue(left.is_left())
        self.assertEqual(left.get_left(), "Error occurred")
        self.assertEqual(left.get_or_else("Default"), "Default")

    def test_try_success_and_failure(self):
        t_success = ScalaTry.apply(lambda: 10 // 2)
        self.assertTrue(t_success.is_success())
        self.assertEqual(t_success.get(), 5)

        t_fail = ScalaTry.apply(lambda: 10 // 0)
        self.assertFalse(t_fail.is_success())
        self.assertIsInstance(t_fail.failed_exception(), ZeroDivisionError)
        self.assertEqual(t_fail.get_or_else(-1), -1)

    def test_io_monad(self):
        side_effects = []
        io_action = (
            ScalaIO.pure(5)
            .map(lambda x: x * 2)
            .flat_map(lambda x: ScalaIO(lambda: (side_effects.append(x), x + 1)[1]))
        )
        self.assertEqual(len(side_effects), 0)  # Pure until unsafe_run_sync
        res = io_action.unsafe_run_sync()
        self.assertEqual(res, 11)
        self.assertEqual(side_effects, [10])

    def test_for_comprehension(self):
        m1 = ScalaSome(2)
        m2 = ScalaSome(3)
        m3 = ScalaSome(4)

        result = for_comprehension([m1, m2, m3], lambda a, b, c: a * b * c)
        self.assertEqual(result.get(), 24)

        m_fail = ScalaNone()
        fail_res = for_comprehension([m1, m_fail, m3], lambda a, b, c: a * b * c)
        self.assertFalse(fail_res.is_defined())


class TestScalaActorSystem(unittest.TestCase):
    def test_actor_message_passing_and_ask(self):
        system = ScalaActorSystem("TestSystem")

        class EchoActor(ScalaActor):
            def receive(self, msg):
                if isinstance(msg, dict) and msg.get("type") == "ping":
                    if self.sender:
                        self.sender.tell({"type": "pong", "payload": msg.get("data")})

        actor = system.actor_of(EchoActor, "echo")
        reply = actor.ask({"type": "ping", "data": "Apex-Scala"}, timeout=1.5)
        self.assertTrue(reply.is_right())
        self.assertEqual(reply.get_right()["type"], "pong")
        self.assertEqual(reply.get_right()["payload"], "Apex-Scala")
        system.terminate()


class TestScalaGuard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_guard_detects_missing_wildcard_in_match(self):
        code = (
            "def testMatch(status: Status): String = status match {\n"
            "  case Active => \"Running\"\n"
            "  case Inactive => \"Stopped\"\n"
            "}\n"
        )
        (self.dir_path / "Status.scala").write_text(code, encoding="utf-8")
        guard = ScalaGuard(str(self.dir_path))
        findings = guard.audit()

        f_match = [f for f in findings if f.rule_id == "SCALA001"]
        self.assertTrue(len(f_match) >= 1)
        self.assertEqual(f_match[0].severity, "HIGH")

    def test_guard_detects_unsafe_get_on_option(self):
        code = "def getVal(opt: Option[String]): String = opt.get\n"
        (self.dir_path / "Unsafe.scala").write_text(code, encoding="utf-8")
        guard = ScalaGuard(str(self.dir_path))
        findings = guard.audit()

        f_get = [f for f in findings if f.rule_id == "SCALA002"]
        self.assertTrue(len(f_get) >= 1)

    def test_guard_detects_unsafe_as_instance_of(self):
        code = "val obj: Any = 123\nval num = obj.asInstanceOf[String]\n"
        (self.dir_path / "Cast.scala").write_text(code, encoding="utf-8")
        guard = ScalaGuard(str(self.dir_path))
        findings = guard.audit()

        f_cast = [f for f in findings if f.rule_id == "SCALA003"]
        self.assertTrue(len(f_cast) >= 1)

    def test_guard_detects_sql_injection_interpolator(self):
        code = 'val q = s"SELECT * FROM users WHERE id = $userId"\n'
        (self.dir_path / "Repo.scala").write_text(code, encoding="utf-8")
        guard = ScalaGuard(str(self.dir_path))
        findings = guard.audit()

        f_sql = [f for f in findings if f.rule_id == "SCALA004"]
        self.assertTrue(len(f_sql) >= 1)
        self.assertEqual(f_sql[0].severity, "CRITICAL")

    def test_cli_execution(self):
        ret = handle_scala_cli(["guard", str(self.dir_path)])
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()

import unittest

from apex_council.lint.null_guard import analyze_null_safety, apply_null_fixes


class NullGuardTests(unittest.TestCase):
    def test_detects_unguarded_dict_get_dereference(self):
        code = (
            "def process_user(data):\n"
            "    user = data.get('user')\n"
            "    email = user.email\n"  # Unguarded!
            "    return email\n"
        )
        violations = analyze_null_safety(code, "app.py")
        self.assertEqual(len(violations), 1)
        v = violations[0]
        self.assertEqual(v.variable_name, "user")
        self.assertEqual(v.lineno, 3)
        self.assertIn(".get() lookup", v.source_origin)

    def test_guarded_dict_get_is_safe(self):
        code = (
            "def process_user(data):\n"
            "    user = data.get('user')\n"
            "    if user is not None:\n"
            "        return user.email\n"
            "    return 'anonymous'\n"
        )
        violations = analyze_null_safety(code, "app.py")
        self.assertEqual(len(violations), 0)

    def test_early_return_guard_is_safe(self):
        code = (
            "def process_user(data):\n"
            "    user = data.get('user')\n"
            "    if user is None:\n"
            "        return 'anonymous'\n"
            "    return user.email\n"  # Safe because of early return!
        )
        violations = analyze_null_safety(code, "app.py")
        self.assertEqual(len(violations), 0)

    def test_apply_kotlin_style_null_fix(self):
        code = (
            "def process(d):\n"
            "    item = d.get('key')\n"
            "    name = item.name\n"
        )
        violations = analyze_null_safety(code)
        fixed = apply_null_fixes(code, violations)
        self.assertIn("item.name if item is not None else None", fixed)


if __name__ == "__main__":
    unittest.main()

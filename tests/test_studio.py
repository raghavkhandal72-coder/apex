import unittest

from apex_council.ui.studio import generate_sparkline, render_studio_dashboard


class TestApexStudio(unittest.TestCase):
    def test_sparkline_generator(self):
        spark = generate_sparkline([1.0, 2.0, 5.0, 10.0])
        self.assertEqual(len(spark), 4)

    def test_studio_dashboard_render(self):
        output = render_studio_dashboard(suite_tests=310, binary_size_kb=430.0)
        self.assertIn("APEX PRO STUDIO", output)
        self.assertIn("CEGIS Engine", output)
        self.assertIn("Instruments", output)


if __name__ == "__main__":
    unittest.main()

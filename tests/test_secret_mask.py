import unittest

from apex_council.security.secret_mask import mask_secrets


class TestApexSecretMask(unittest.TestCase):
    def test_mask_google_and_openai_secrets(self):
        fake_google_key = "AIza" + "SyD1234567890abcdefghijklmnopqrstuv"
        fake_openai_key = "sk-" + "abcdef1234567890abcdef123456"
        log = (
            f"Error authenticating with key {fake_google_key}\n"
            f"OpenAI token {fake_openai_key} failed.\n"
        )
        masked, count = mask_secrets(log)
        self.assertEqual(count, 2)
        self.assertNotIn(fake_google_key, masked)
        self.assertNotIn(fake_openai_key, masked)
        self.assertIn("***[REDACTED_GOOGLE_API_KEY]***", masked)
        self.assertIn("***[REDACTED_OPENAI_KEY]***", masked)

    def test_mask_clean_text(self):
        clean = "Normal log without any tokens or keys."
        masked, count = mask_secrets(clean)
        self.assertEqual(count, 0)
        self.assertEqual(masked, clean)


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "firmware" / "tgbot"))
from access_control import is_allowed_user, parse_allowed_user_ids


class AccessControlTests(unittest.TestCase):
    def test_parses_and_deduplicates_ids(self):
        self.assertEqual(parse_allowed_user_ids("123, 456,123"), frozenset({123, 456}))

    def test_missing_allowlist_fails_closed(self):
        for value in (None, "", "   "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_allowed_user_ids(value)

    def test_invalid_ids_fail_closed(self):
        for value in ("123,abc", "0", "-3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_allowed_user_ids(value)

    def test_only_allowlisted_id_is_authorized(self):
        allowed = parse_allowed_user_ids("123,456")
        self.assertTrue(is_allowed_user(123, allowed))
        self.assertFalse(is_allowed_user(999, allowed))
        self.assertFalse(is_allowed_user(None, allowed))


if __name__ == "__main__":
    unittest.main()

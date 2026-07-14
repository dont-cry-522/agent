import unittest

from scripts.import_markdown import format_timestamp


class FormatTimestampTests(unittest.TestCase):
    def test_accepts_numeric_timestamp(self) -> None:
        self.assertEqual(format_timestamp(1710000000), "2024-03-07 17:46:40")

    def test_accepts_string_timestamp(self) -> None:
        self.assertEqual(format_timestamp("2026-07-12 14:17:20"), "2026-07-12 14:17:20")


if __name__ == "__main__":
    unittest.main()

"""Tests for the Week 3 text and numeric-token processor."""

import unittest

from core.week3_tdd import (
    DataValidationError,
    StringDataProcessor,
    TokenCorruptedError,
)


class TestStringDataProcessor(unittest.TestCase):
    def test_sanitize_unicode_whitespace(self) -> None:
        self.assertEqual(
            StringDataProcessor.sanitize_whitespace(
                "  Crème\tbrûlée\n東京  "
            ),
            "Crème brûlée 東京",
        )

    def test_sanitize_empty_and_invalid_input(self) -> None:
        self.assertEqual(StringDataProcessor.sanitize_whitespace(" \t\n"), "")
        with self.assertRaises(DataValidationError):
            StringDataProcessor.sanitize_whitespace(
                None  # type: ignore[arg-type]
            )
        with self.assertRaises(DataValidationError):
            StringDataProcessor.sanitize_whitespace(
                42  # type: ignore[arg-type]
            )

    def test_frequency_unicode_casefold(self) -> None:
        result = StringDataProcessor.extract_word_frequencies(
            "Straße STRASSE café CAFÉ 東京 東京"
        )
        self.assertEqual(result, {"strasse": 2, "café": 2, "東京": 2})

    def test_frequency_empty_and_invalid(self) -> None:
        self.assertEqual(
            StringDataProcessor.extract_word_frequencies("  "),
            {},
        )
        with self.assertRaises(DataValidationError):
            StringDataProcessor.extract_word_frequencies(
                None  # type: ignore[arg-type]
            )

    def test_parse_numbers_valid_and_custom_delimiter(self) -> None:
        self.assertEqual(
            StringDataProcessor.parse_delimited_numbers(
                " 1.5 | 2 | -3.25 ",
                "|",
            ),
            [1.5, 2.0, -3.25],
        )

    def test_parse_delimited_numbers_handles_empty_payload(self) -> None:
        self.assertEqual(StringDataProcessor.parse_delimited_numbers(""), [])
        self.assertEqual(
            StringDataProcessor.parse_delimited_numbers(" \t "),
            [],
        )

    def test_parse_numbers_malformed_delimiters(self) -> None:
        for raw_str in (",1", "1,", "1,,2"):
            with self.subTest(raw_str=raw_str):
                with self.assertRaises(TokenCorruptedError):
                    StringDataProcessor.parse_delimited_numbers(raw_str)
        with self.assertRaises(DataValidationError):
            StringDataProcessor.parse_delimited_numbers("1,2", "")

    def test_parse_numbers_corrupt_token_and_types(self) -> None:
        with self.assertRaises(TokenCorruptedError):
            StringDataProcessor.parse_delimited_numbers("1,not-a-number,3")
        with self.assertRaises(DataValidationError):
            StringDataProcessor.parse_delimited_numbers(
                None  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()

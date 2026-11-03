"""Unit tests for string sanitization and statistics processing."""

import unittest

from string_processor import DataValidationError, StringProcessor


class TestStringProcessor(unittest.TestCase):
    def test_sanitize_text_removes_punctuation_and_normalizes_whitespace(self):
        result = StringProcessor.sanitize_text("  Hello,   World! @2026 #Python  ")
        self.assertEqual(result, "Hello World 2026 Python")

    def test_sanitize_text_empty_and_whitespace(self):
        self.assertEqual(StringProcessor.sanitize_text(""), "")
        self.assertEqual(StringProcessor.sanitize_text(" \t\n "), "")

    def test_sanitize_text_none_raises_validation_error(self):
        with self.assertRaises(DataValidationError):
            StringProcessor.sanitize_text(None)

    def test_sanitize_text_non_string_raises_validation_error(self):
        with self.assertRaises(DataValidationError):
            StringProcessor.sanitize_text(42)

    def test_calculate_word_frequencies_is_case_insensitive(self):
        result = StringProcessor.calculate_word_frequencies("AI ai Ai aI")
        self.assertEqual(result, {"ai": 4})

    def test_calculate_word_frequencies_includes_number_tokens(self):
        result = StringProcessor.calculate_word_frequencies("Code 2026; code 2026, 42!")
        self.assertEqual(result, {"code": 2, "2026": 2, "42": 1})

    def test_calculate_word_frequencies_empty_or_whitespace(self):
        self.assertEqual(StringProcessor.calculate_word_frequencies(""), {})
        self.assertEqual(StringProcessor.calculate_word_frequencies(" \t "), {})

    def test_calculate_word_frequencies_none_raises_validation_error(self):
        with self.assertRaises(DataValidationError):
            StringProcessor.calculate_word_frequencies(None)

    def test_parse_numeric_series_parses_integers_and_floats(self):
        result = StringProcessor.parse_numeric_series("10, -2.5, 3e1, .25")
        self.assertEqual(result, [10.0, -2.5, 30.0, 0.25])

    def test_parse_numeric_series_supports_custom_delimiter(self):
        result = StringProcessor.parse_numeric_series("1|2.5|3", delimiter="|")
        self.assertEqual(result, [1.0, 2.5, 3.0])

    def test_parse_numeric_series_ignores_empty_tokens(self):
        result = StringProcessor.parse_numeric_series("1,, 2, ,3,")
        self.assertEqual(result, [1.0, 2.0, 3.0])

    def test_parse_numeric_series_empty_input_returns_empty_list(self):
        self.assertEqual(StringProcessor.parse_numeric_series(" \t "), [])

    def test_parse_numeric_series_invalid_token_raises_validation_error(self):
        with self.assertRaises(DataValidationError):
            StringProcessor.parse_numeric_series("1, two, 3")

    def test_parse_numeric_series_none_raises_validation_error(self):
        with self.assertRaises(DataValidationError):
            StringProcessor.parse_numeric_series(None)

    def test_parse_numeric_series_invalid_delimiter_raises_validation_error(self):
        for delimiter in ("", None):
            with self.subTest(delimiter=delimiter):
                with self.assertRaises(DataValidationError):
                    StringProcessor.parse_numeric_series("1,2", delimiter=delimiter)

    def test_compute_summary_statistics_for_values(self):
        result = StringProcessor.compute_summary_statistics([1, 2.5, 4])
        self.assertEqual(
            result,
            {"count": 3.0, "sum": 7.5, "mean": 2.5, "min": 1.0, "max": 4.0},
        )

    def test_compute_summary_statistics_rounds_to_four_decimal_places(self):
        result = StringProcessor.compute_summary_statistics([1.11111, 2.22222])
        self.assertEqual(
            result,
            {
                "count": 2.0,
                "sum": 3.3333,
                "mean": 1.6667,
                "min": 1.1111,
                "max": 2.2222,
            },
        )

    def test_compute_summary_statistics_empty_list_returns_zero_values(self):
        result = StringProcessor.compute_summary_statistics([])
        self.assertEqual(
            result,
            {"count": 0.0, "sum": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0},
        )

    def test_compute_summary_statistics_rejects_non_list_input(self):
        with self.assertRaises(DataValidationError):
            StringProcessor.compute_summary_statistics((1, 2, 3))

    def test_compute_summary_statistics_rejects_non_numeric_values(self):
        with self.assertRaises(DataValidationError):
            StringProcessor.compute_summary_statistics([1, "two", 3])


if __name__ == "__main__":
    unittest.main()
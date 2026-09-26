"""
Comprehensive Automated Unit Test Suite (TDD Verified)
Author: Akshya Gupta (YuvaIntern Junior Python Developer)
Framework: Python standard unittest
"""

import unittest
from string_data_processor import StringDataProcessor, DataValidationError

class TestStringDataProcessor(unittest.TestCase):

    # ------------------ sanitize_text Tests ------------------ #
    def test_sanitize_text_nominal(self):
        result = StringDataProcessor.sanitize_text("  Hello, World! @2026 #Python  ")
        self.assertEqual(result, "Hello World 2026 Python")

    def test_sanitize_text_empty_and_whitespace(self):
        self.assertEqual(StringDataProcessor.sanitize_text(""), "")
        self.assertEqual(StringDataProcessor.sanitize_text("     \t\n  "), "")

    def test_sanitize_text_none_exception(self):
        with self.assertRaises(DataValidationError):
            StringDataProcessor.sanitize_text(None)

    def test_sanitize_text_invalid_type(self):
        with self.assertRaises(DataValidationError):
            StringDataProcessor.sanitize_text(12345)

    # ------------ calculate_word_frequencies Tests ----------- #
    def test_calculate_word_frequencies_standard(self):
        text = "Python is fast. Python is dynamic."
        expected = {"python": 2, "is": 2, "fast": 1, "dynamic": 1}
        self.assertEqual(StringDataProcessor.calculate_word_frequencies(text), expected)

    def test_calculate_word_frequencies_empty(self):
        self.assertEqual(StringDataProcessor.calculate_word_frequencies(""), {})

    def test_calculate_word_frequencies_case_insensitivity(self):
        text = "AI ai Ai aI"
        self.assertEqual(StringDataProcessor.calculate_word_frequencies(text), {"ai": 4})

    # -------------- parse_numeric_series Tests --------------- #
    def test_parse_numeric_series_valid(self):
        series = "10.5, 20.0, 30.25, 40"
        expected = [10.5, 20.0, 30.25, 40.0]
        self.assertEqual(StringDataProcessor.parse_numeric_series(series), expected)

    def test_parse_numeric_series_custom_delimiter(self):
        series = "100|200|300"
        expected = [100.0, 200.0, 300.0]
        self.assertEqual(StringDataProcessor.parse_numeric_series(series, delimiter="|"), expected)

    def test_parse_numeric_series_corrupted_token(self):
        with self.assertRaises(DataValidationError):
            StringDataProcessor.parse_numeric_series("10, 20, INVALID, 40")

    def test_parse_numeric_series_empty(self):
        self.assertEqual(StringDataProcessor.parse_numeric_series(""), [])

    # ----------- compute_summary_statistics Tests ------------ #
    def test_compute_summary_statistics_nominal(self):
        numbers = [10.0, 20.0, 30.0]
        res = StringDataProcessor.compute_summary_statistics(numbers)
        self.assertEqual(res["count"], 3.0)
        self.assertEqual(res["sum"], 60.0)
        self.assertEqual(res["mean"], 20.0)
        self.assertEqual(res["min"], 10.0)
        self.assertEqual(res["max"], 30.0)

    def test_compute_summary_statistics_empty_list(self):
        res = StringDataProcessor.compute_summary_statistics([])
        self.assertEqual(res, {"count": 0.0, "sum": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0})

    def test_compute_summary_statistics_invalid_elements(self):
        with self.assertRaises(DataValidationError):
            StringDataProcessor.compute_summary_statistics([1.0, "two", 3.0])

if __name__ == "__main__":
    unittest.main()

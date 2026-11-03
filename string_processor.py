"""String sanitization, token counting, and numeric statistics utilities."""

import re
from typing import Dict, List, Optional


class DataValidationError(ValueError):
    """Raised when input data cannot be processed safely."""


class StringProcessor:
    """Provides text cleaning, token parsing, and summary statistics."""

    @staticmethod
    def sanitize_text(raw_text: Optional[str]) -> str:
        """Remove punctuation and collapse whitespace while preserving case."""
        if raw_text is None:
            raise DataValidationError("Input text cannot be None.")
        if not isinstance(raw_text, str):
            raise DataValidationError(
                f"Expected str, received {type(raw_text).__name__}."
            )

        cleaned_text = re.sub(r"[^a-zA-Z0-9\s]", "", raw_text)
        return " ".join(cleaned_text.split())

    @staticmethod
    def calculate_word_frequencies(text: str) -> Dict[str, int]:
        """Count case-insensitive alphanumeric tokens in text."""
        if not isinstance(text, str):
            raise DataValidationError("Expected string input.")
        if not text.strip():
            return {}

        tokens = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
        frequencies: Dict[str, int] = {}
        for token in tokens:
            frequencies[token] = frequencies.get(token, 0) + 1
        return frequencies

    @staticmethod
    def parse_numeric_series(csv_series: str, delimiter: str = ",") -> List[float]:
        """Parse a delimited string of numbers, ignoring blank tokens."""
        if not isinstance(csv_series, str):
            raise DataValidationError("Numeric series must be a string.")
        if not isinstance(delimiter, str) or not delimiter:
            raise DataValidationError("Delimiter must be a non-empty string.")
        if not csv_series.strip():
            return []

        parsed_numbers: List[float] = []
        for item in csv_series.split(delimiter):
            clean_item = item.strip()
            if not clean_item:
                continue
            try:
                parsed_numbers.append(float(clean_item))
            except ValueError as error:
                raise DataValidationError(
                    f"Invalid numeric token detected: '{clean_item}'"
                ) from error
        return parsed_numbers

    @staticmethod
    def compute_summary_statistics(numbers: List[float]) -> Dict[str, float]:
        """Return count, sum, mean, minimum, and maximum for numeric values."""
        if not isinstance(numbers, list):
            raise DataValidationError("Expected a list of numbers.")
        if not numbers:
            return {"count": 0.0, "sum": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}

        for number in numbers:
            if not isinstance(number, (int, float)):
                raise DataValidationError(
                    "Unsupported non-numeric type in sequence: "
                    f"{type(number).__name__}"
                )

        total = sum(numbers)
        return {
            "count": float(len(numbers)),
            "sum": round(total, 4),
            "mean": round(total / len(numbers), 4),
            "min": round(min(numbers), 4),
            "max": round(max(numbers), 4),
        }
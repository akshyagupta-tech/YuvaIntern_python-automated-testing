"""
Data Processing & String Sanitization Engine
Author: Akshya Gupta (YuvaIntern Junior Python Developer Track - Week 3)
Designed for Test-Driven Development (TDD) and high testability.
"""

import re
from typing import List, Dict, Any, Optional

class DataValidationError(ValueError):
    """Custom exception raised for invalid processing payloads."""

class StringDataProcessor:
    """Core processor implementing string algorithms and parsing utilities."""

    @staticmethod
    def sanitize_text(raw_text: Optional[str]) -> str:
        """Strips special characters, redundant spaces, and normalizes casing."""
        if raw_text is None:
            raise DataValidationError("Input text cannot be None.")
        if not isinstance(raw_text, str):
            raise DataValidationError(f"Expected str, received {type(raw_text).__name__}.")
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', raw_text)
        return " ".join(cleaned.split()).strip()

    @staticmethod
    def calculate_word_frequencies(text: str) -> Dict[str, int]:
        """Calculates token frequencies with punctuation stripping."""
        if not isinstance(text, str):
            raise DataValidationError("Expected string input.")
        if not text.strip():
            return {}
        tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        frequencies: Dict[str, int] = {}
        for token in tokens:
            frequencies[token] = frequencies.get(token, 0) + 1
        return frequencies

    @staticmethod
    def parse_numeric_series(csv_series: str, delimiter: str = ",") -> List[float]:
        """Parses delimited numeric sequences safely with robust type checking."""
        if not isinstance(csv_series, str):
            raise DataValidationError("Numeric series must be a string representation.")
        if not csv_series.strip():
            return []
        
        parsed_numbers: List[float] = []
        raw_items = csv_series.split(delimiter)
        for item in raw_items:
            clean_item = item.strip()
            if not clean_item:
                continue
            try:
                parsed_numbers.append(float(clean_item))
            except ValueError as err:
                raise DataValidationError(f"Invalid numeric token detected: '{clean_item}'") from err
        return parsed_numbers

    @staticmethod
    def compute_summary_statistics(numbers: List[float]) -> Dict[str, float]:
        """Calculates count, sum, mean, min, and max defensively."""
        if not isinstance(numbers, list):
            raise DataValidationError("Expected a list of numbers.")
        if not numbers:
            return {"count": 0.0, "sum": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}
        
        for n in numbers:
            if not isinstance(n, (int, float)):
                raise DataValidationError(f"Unsupported non-numeric type in sequence: {type(n).__name__}")

        total = sum(numbers)
        return {
            "count": float(len(numbers)),
            "sum": round(total, 4),
            "mean": round(total / len(numbers), 4),
            "min": round(min(numbers), 4),
            "max": round(max(numbers), 4)
        }

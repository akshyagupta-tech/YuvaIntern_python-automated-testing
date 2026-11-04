"""UI-independent text processing, numeric analysis, and serialization."""

from __future__ import annotations

import csv
import io
import json
import math
import re
import time
import unicodedata
from pathlib import Path
from statistics import median
from typing import Any, Callable, Mapping, Sequence

from exceptions import (
    ArithmeticAggregationError,
    DataValidationError,
    EmptyTokenStreamError,
    MalformedPayloadException,
    TokenCorruptedError,
)
from presets import PRESETS, get_preset


_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACE_PATTERN = re.compile(r"\s+")
_NUMBER_PATTERN = re.compile(
    r"(?<![\d.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
    r"(?:[eE][+-]?\d+)?(?![\d.])"
)
_WORD_PATTERN = re.compile(r"\b[^\W_]+\b", re.UNICODE)
MAX_TEXT_LENGTH = 5_000_000


class StringDataProcessor:
    """Provide validated sanitization, tokenization, and analytics methods."""

    @staticmethod
    def _validate_text(text: str, field: str = "text") -> str:
        if not isinstance(text, str):
            raise DataValidationError(
                "Expected a string input.",
                {"field": field, "received_type": type(text).__name__},
            )
        if len(text) > MAX_TEXT_LENGTH:
            raise MalformedPayloadException(
                "Text payload exceeds the configured size limit.",
                {
                    "field": field,
                    "length": len(text),
                    "limit": MAX_TEXT_LENGTH,
                },
            )
        return text

    @classmethod
    def sanitize_multistage(cls, raw_text: str) -> str:
        """Normalize Unicode, remove controls, retain printable text."""
        text = cls._validate_text(raw_text)
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.replace("\t", " ").replace("\n", " ").replace(
            "\r", " "
        )
        normalized = _CONTROL_PATTERN.sub("", normalized)
        printable = "".join(
            character for character in normalized if character.isprintable()
        )
        return _SPACE_PATTERN.sub(" ", printable).strip()

    @classmethod
    def sanitize_text(
        cls,
        raw_text: str,
        preset: str = "Alphanumeric Clean",
    ) -> str:
        """Apply common sanitation and a named normalization profile."""
        normalized = cls.sanitize_multistage(raw_text)
        return get_preset(preset).transform(normalized)

    @classmethod
    def calculate_word_frequencies(cls, text: str) -> dict[str, int]:
        """Return case-folded Unicode word and number frequencies."""
        validated = cls._validate_text(text)
        frequencies: dict[str, int] = {}
        for token in _WORD_PATTERN.findall(validated.casefold()):
            frequencies[token] = frequencies.get(token, 0) + 1
        return frequencies

    @classmethod
    def extract_numeric_tokens(cls, text: str) -> list[float]:
        """Extract finite signed integer, decimal, and exponent tokens."""
        validated = cls._validate_text(text)
        tokens: list[float] = []
        for match in _NUMBER_PATTERN.finditer(validated):
            try:
                number = float(match.group())
            except ValueError as error:
                raise MalformedPayloadException(
                    "Numeric token could not be parsed.",
                    {"token": match.group(), "position": match.start()},
                ) from error
            if not math.isfinite(number):
                raise ArithmeticAggregationError(
                    "Numeric token is outside the finite range.",
                    {"token": match.group(), "position": match.start()},
                )
            tokens.append(number)
        return tokens

    @staticmethod
    def aggregate_numbers(numbers: Sequence[float]) -> dict[str, float]:
        """Calculate count, sum, mean, minimum, maximum, and median."""
        if isinstance(numbers, (str, bytes)) or not isinstance(
            numbers, Sequence
        ):
            raise DataValidationError(
                "Expected a sequence of numeric values.",
                {"received_type": type(numbers).__name__},
            )
        if not numbers:
            raise EmptyTokenStreamError(
                "At least one numeric token is required."
            )

        checked: list[float] = []
        for index, value in enumerate(numbers):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise DataValidationError(
                    "Sequence contains a non-numeric value.",
                    {"index": index, "received_type": type(value).__name__},
                )
            numeric_value = float(value)
            if not math.isfinite(numeric_value):
                raise ArithmeticAggregationError(
                    "All values must be finite.",
                    {"index": index, "value": value},
                )
            checked.append(numeric_value)

        try:
            total = math.fsum(checked)
        except OverflowError as error:
            raise ArithmeticAggregationError(
                "The sum exceeds the finite numeric range.",
                {"count": len(checked)},
            ) from error
        if not math.isfinite(total):
            raise ArithmeticAggregationError(
                "The sum exceeds the finite numeric range.",
                {"count": len(checked)},
            )
        result = {
            "count": float(len(checked)),
            "sum": total,
            "mean": total / len(checked),
            "min": min(checked),
            "max": max(checked),
            "median": float(median(checked)),
        }
        return {key: round(value, 4) for key, value in result.items()}

    @classmethod
    def aggregate_numeric_tokens(cls, text: str) -> dict[str, float]:
        """Extract numeric tokens and calculate their aggregate statistics."""
        return cls.aggregate_numbers(cls.extract_numeric_tokens(text))

    @classmethod
    def parse_numeric_series(
        cls, csv_series: str, delimiter: str = ","
    ) -> list[float]:
        """Parse strict delimiter-separated numbers, ignoring blank fields."""
        validated = cls._validate_text(csv_series, "numeric_series")
        if not isinstance(delimiter, str) or not delimiter:
            raise DataValidationError(
                "Delimiter must be a non-empty string.",
                {"delimiter": delimiter},
            )
        if not validated.strip():
            return []

        numbers: list[float] = []
        for index, token in enumerate(validated.split(delimiter)):
            clean_token = token.strip()
            if not clean_token:
                continue
            try:
                value = float(clean_token)
            except ValueError as error:
                raise TokenCorruptedError(
                    "Invalid numeric token in delimited input.",
                    {"token": clean_token, "index": index},
                ) from error
            if not math.isfinite(value):
                raise TokenCorruptedError(
                    "Numeric tokens must be finite.",
                    {"token": clean_token, "index": index},
                )
            numbers.append(value)
        return numbers

    @classmethod
    def compute_summary_statistics(
        cls, numbers: list[float]
    ) -> dict[str, float]:
        """Return legacy count/sum/mean/min/max fields for compatibility."""
        if not isinstance(numbers, list):
            raise DataValidationError(
                "Expected a list of numbers.",
                {"received_type": type(numbers).__name__},
            )
        if not numbers:
            return {
                "count": 0.0,
                "sum": 0.0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
            }
        result = cls.aggregate_numbers(numbers)
        return {
            key: result[key]
            for key in ("count", "sum", "mean", "min", "max")
        }

    @classmethod
    def analyze(
        cls, text: str, preset: str = "Alphanumeric Clean"
    ) -> dict[str, Any]:
        """Build a serializable result containing text and analytics."""
        validated = cls._validate_text(text)
        tokens = cls.extract_numeric_tokens(validated)
        analytics = (
            cls.aggregate_numbers(tokens)
            if tokens
            else {
                "count": 0.0,
                "sum": 0.0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "median": 0.0,
            }
        )
        return {
            "sanitized_text": cls.sanitize_text(validated, preset),
            "preset": preset,
            "word_frequencies": cls.calculate_word_frequencies(validated),
            "numeric_tokens": tokens,
            "statistics": analytics,
        }

    @staticmethod
    def to_json(summary: Mapping[str, Any]) -> str:
        """Serialize an analysis result as stable, readable JSON."""
        return json.dumps(
            summary, ensure_ascii=False, indent=2, sort_keys=True
        )

    @staticmethod
    def to_csv(summary: Mapping[str, Any]) -> str:
        """Serialize tokens and statistics as a two-column CSV document."""
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("category", "name", "value"))
        for index, token in enumerate(
            summary.get("numeric_tokens", []), start=1
        ):
            writer.writerow(("token", index, token))
        statistics = summary.get("statistics", {})
        if isinstance(statistics, Mapping):
            for name, value in statistics.items():
                writer.writerow(("statistic", name, value))
        return output.getvalue()

    @staticmethod
    def to_table(summary: Mapping[str, Any]) -> str:
        """Render aggregate statistics as a compact plain-text table."""
        statistics = summary.get("statistics", {})
        if not isinstance(statistics, Mapping) or not statistics:
            raise DataValidationError(
                "Analysis result does not contain statistics.",
                {"available_keys": list(summary.keys())},
            )
        rows = [(str(name), str(value)) for name, value in statistics.items()]
        width = max(len("Metric"), *(len(name) for name, _ in rows))
        value_width = max(len("Value"), *(len(value) for _, value in rows))
        border = f"+{'-' * (width + 2)}+{'-' * (value_width + 2)}+"
        lines = [
            border,
            f"| {'Metric'.ljust(width)} | {'Value'.rjust(value_width)} |",
            border,
        ]
        lines.extend(
            f"| {name.ljust(width)} | {value.rjust(value_width)} |"
            for name, value in rows
        )
        lines.append(border)
        return "\n".join(lines)

    @staticmethod
    def load_text_file(path: str | Path) -> str:
        """Read UTF-8 input and translate file-system errors."""
        source = Path(path)
        try:
            return source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise MalformedPayloadException(
                "Unable to read a UTF-8 text payload.",
                {"path": str(source), "reason": str(error)},
            ) from error

    @classmethod
    def ingest(cls, fetcher: Callable[[], str]) -> str:
        """Call an external text source and validate its returned payload."""
        if not callable(fetcher):
            raise DataValidationError("Fetcher must be callable.")
        try:
            payload = fetcher()
        except Exception as error:
            raise MalformedPayloadException(
                "External text ingestion failed.",
                {"error_type": type(error).__name__, "reason": str(error)},
            ) from error
        return cls._validate_text(payload, "external_payload")

    @staticmethod
    def benchmark_sanitization(
        text: str, iterations: int = 100
    ) -> dict[str, float]:
        """Compare regex compilation and string operations in microseconds."""
        if not isinstance(text, str):
            raise DataValidationError("Benchmark input must be a string.")
        if (
            isinstance(iterations, bool)
            or not isinstance(iterations, int)
            or iterations < 1
        ):
            raise DataValidationError(
                "Iterations must be a positive integer.",
                {"iterations": iterations},
            )

        def regex_compiled_per_call() -> str:
            return re.compile(r"\s+").sub(" ", text).strip()

        def string_operations() -> str:
            return " ".join(text.split())

        measurements: dict[str, float] = {}
        for name, operation in (
            ("regex", regex_compiled_per_call),
            ("string_operations", string_operations),
        ):
            started = time.perf_counter_ns()
            for _ in range(iterations):
                operation()
            elapsed = time.perf_counter_ns() - started
            measurements[f"{name}_microseconds_per_call"] = (
                elapsed / iterations / 1000
            )
        measurements["iterations"] = float(iterations)
        return measurements

    @staticmethod
    def sanitize_whitespace(text: str) -> str:
        """Legacy API alias preserving Unicode whitespace behavior."""
        validated = StringDataProcessor._validate_text(text)
        return " ".join(validated.split())

    @staticmethod
    def extract_word_frequencies(text: str) -> dict[str, int]:
        """Legacy API alias for Unicode-aware word-frequency analysis."""
        return StringDataProcessor.calculate_word_frequencies(text)

    @staticmethod
    def parse_delimited_numbers(
        raw_str: str, delimiter: str = ","
    ) -> list[float]:
        """Legacy API alias for strict delimited-number parsing."""
        return StringDataProcessor.parse_numeric_series(raw_str, delimiter)


__all__ = [
    "ArithmeticAggregationError",
    "DataValidationError",
    "EmptyTokenStreamError",
    "MalformedPayloadException",
    "PRESETS",
    "StringDataProcessor",
    "TokenCorruptedError",
]
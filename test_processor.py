"""Unit, boundary, mutation, and regression tests for the text engine."""

from __future__ import annotations

import io
import json
import random
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from exceptions import (
    ArithmeticAggregationError,
    DataValidationError,
    EmptyTokenStreamError,
    MalformedPayloadException,
    TokenCorruptedError,
)
from presets import PRESETS, get_preset
from processor import StringDataProcessor


def noisy_text_samples(seed: int = 17, count: int = 30) -> list[str]:
    """Generate deterministic mixed text for repeatable parser stress tests."""
    generator = random.Random(seed)
    alphabet = "abcXYZ  \t\n!@#$%^&*()_+=-😀é"
    samples: list[str] = []
    for _ in range(count):
        fragments = [
            "".join(generator.choices(alphabet, k=generator.randint(0, 40))),
            str(generator.randint(-100_000, 100_000)),
            f"{generator.uniform(-1000, 1000):.3f}",
        ]
        generator.shuffle(fragments)
        samples.append("".join(fragments))
    return samples


class CountingTestCase(unittest.TestCase):
    """Shared base for test cases included in assertion-count reporting."""


class TestSanitization(CountingTestCase):
    def test_multistage_sanitation_unicode_controls(self) -> None:
        self.assertEqual(
            StringDataProcessor.sanitize_multistage("Ａ  B\tC\x00\n😀"),
            "A B C 😀",
        )

    def test_control_only_and_whitespace_inputs_become_empty(self) -> None:
        for value in ("", " \t\n ", "\x00\x01\x7f"):
            with self.subTest(value=value):
                self.assertEqual(
                    StringDataProcessor.sanitize_multistage(value), ""
                )

    def test_preset_matrix(self) -> None:
        cases = (
            ("Strict Alpha", "Café 2026!", "Caf"),
            ("Financial/Numeric Only", "USD -12.50x", "-12.50"),
            ("Slugify", "Crème brûlée! 2026", "creme-brulee-2026"),
            ("Alphanumeric Clean", "Hello, 東京 42!", "Hello 42"),
        )
        for preset, text, expected in cases:
            with self.subTest(preset=preset):
                self.assertEqual(
                    StringDataProcessor.sanitize_text(text, preset), expected
                )

    def test_unknown_preset_has_context(self) -> None:
        with self.assertRaises(DataValidationError) as raised:
            get_preset("not-a-profile")
        self.assertEqual(raised.exception.context["preset"], "not-a-profile")
        self.assertEqual(
            set(PRESETS),
            {
                "Strict Alpha",
                "Financial/Numeric Only",
                "Slugify",
                "Alphanumeric Clean",
            },
        )

    def test_legacy_sanitizer_remains_ascii_alphanumeric(self) -> None:
        self.assertEqual(
            StringDataProcessor.sanitize_text(
                "  Hello, World! @2026 #Python  "
            ),
            "Hello World 2026 Python",
        )

    def test_invalid_type_and_oversized_payload_are_rejected(self) -> None:
        with self.assertRaises(DataValidationError):
            StringDataProcessor.sanitize_multistage(
                None  # type: ignore[arg-type]
            )
        with patch("processor.MAX_TEXT_LENGTH", 3):
            with self.assertRaises(MalformedPayloadException):
                StringDataProcessor.sanitize_multistage("oversized")


class TestNumericAnalysis(CountingTestCase):
    def test_extracts_signed_integer_decimal_and_exponent_tokens(self) -> None:
        tokens = StringDataProcessor.extract_numeric_tokens(
            "order A has -12, +3.5 units, .25 tax, and 2e2 total"
        )
        self.assertEqual(tokens, [-12.0, 3.5, 0.25, 200.0])

    def test_numeric_tokens_from_mixed_alphanumeric_text(self) -> None:
        self.assertEqual(
            StringDataProcessor.extract_numeric_tokens(
                "item42 version2.0 abc"
            ),
            [42.0, 2.0],
        )

    def test_aggregation_includes_median(self) -> None:
        result = StringDataProcessor.aggregate_numeric_tokens(
            "Revenue: 1, 2, 8, 9"
        )
        self.assertEqual(
            result,
            {
                "count": 4.0,
                "sum": 20.0,
                "mean": 5.0,
                "min": 1.0,
                "max": 9.0,
                "median": 5.0,
            },
        )

    def test_empty_token_stream_raises_domain_exception(self) -> None:
        with self.assertRaises(EmptyTokenStreamError) as raised:
            StringDataProcessor.aggregate_numeric_tokens("nothing numeric")
        self.assertIsInstance(raised.exception.context, dict)

    def test_invalid_and_nonfinite_aggregation_values_fail(self) -> None:
        with self.assertRaises(DataValidationError):
            StringDataProcessor.aggregate_numbers(
                [1.0, "bad"]  # type: ignore[list-item]
            )
        with self.assertRaises(ArithmeticAggregationError):
            StringDataProcessor.aggregate_numbers([float("inf")])
        with self.assertRaises(ArithmeticAggregationError):
            StringDataProcessor.extract_numeric_tokens("1e999")
        with self.assertRaises(ArithmeticAggregationError):
            StringDataProcessor.aggregate_numbers([1e308, 1e308])

    def test_aggregation_rejects_empty_and_non_sequence_inputs(self) -> None:
        with self.assertRaises(EmptyTokenStreamError):
            StringDataProcessor.aggregate_numbers([])
        with self.assertRaises(DataValidationError):
            StringDataProcessor.aggregate_numbers(
                "1,2"  # type: ignore[arg-type]
            )
        with self.assertRaises(DataValidationError):
            StringDataProcessor.aggregate_numbers([True])

    def test_legacy_delimited_parser_retains_boundary_behavior(self) -> None:
        self.assertEqual(
            StringDataProcessor.parse_numeric_series("10.5, 20.0, 30.25, 40"),
            [10.5, 20.0, 30.25, 40.0],
        )
        self.assertEqual(StringDataProcessor.parse_numeric_series(" , , "), [])
        with self.assertRaises(TokenCorruptedError) as raised:
            StringDataProcessor.parse_numeric_series("10,broken,30")
        self.assertEqual(raised.exception.context["token"], "broken")

    def test_delimiter_matrix(self) -> None:
        for raw, delimiter, expected in (
            ("1|2.5|-3", "|", [1.0, 2.5, -3.0]),
            ("1,,2", ",", [1.0, 2.0]),
            ("", ",", []),
        ):
            with self.subTest(raw=raw, delimiter=delimiter):
                self.assertEqual(
                    StringDataProcessor.parse_numeric_series(
                        raw, delimiter
                    ),
                    expected,
                )

    def test_malformed_delimiters_and_nonfinite_values(self) -> None:
        for delimiter in ("", None):
            with self.subTest(delimiter=delimiter):
                with self.assertRaises(DataValidationError):
                    StringDataProcessor.parse_numeric_series(
                        "1,2", delimiter  # type: ignore[arg-type]
                    )
        for raw in ("1,broken,3", "1,inf,3"):
            with self.subTest(raw=raw):
                with self.assertRaises(TokenCorruptedError):
                    StringDataProcessor.parse_numeric_series(raw)

    def test_frequency_map_handles_unicode_and_empty_text(self) -> None:
        self.assertEqual(
            StringDataProcessor.calculate_word_frequencies(
                "Straße STRASSE 東京 東京"
            ),
            {"strasse": 2, "東京": 2},
        )
        self.assertEqual(
            StringDataProcessor.calculate_word_frequencies(" \t"), {}
        )


class TestIntegrationAndSerialization(CountingTestCase):
    def test_analysis_serializes_to_json_csv_and_table(self) -> None:
        result = StringDataProcessor.analyze("items 2 and 4")
        encoded = StringDataProcessor.to_json(result)
        self.assertEqual(json.loads(encoded)["numeric_tokens"], [2.0, 4.0])
        csv_text = StringDataProcessor.to_csv(result)
        self.assertIn("token,1,2.0", csv_text)
        self.assertIn("statistic,median,3.0", csv_text)
        self.assertIn("Metric", StringDataProcessor.to_table(result))

    def test_file_system_failure_is_translated_with_context(self) -> None:
        with patch(
            "pathlib.Path.read_text",
            side_effect=OSError("disk unavailable"),
        ):
            with self.assertRaises(MalformedPayloadException) as raised:
                StringDataProcessor.load_text_file("missing.txt")
        self.assertEqual(raised.exception.context["path"], "missing.txt")

    def test_successful_file_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("sample", encoding="utf-8")
            self.assertEqual(
                StringDataProcessor.load_text_file(source), "sample"
            )

    def test_invalid_utf8_file_is_translated(self) -> None:
        with patch(
            "pathlib.Path.read_text", side_effect=UnicodeDecodeError(
                "utf-8", b"\xff", 0, 1, "invalid start byte"
            )
        ):
            with self.assertRaises(MalformedPayloadException):
                StringDataProcessor.load_text_file("invalid.txt")

    def test_external_ingestion_failure_and_payload_validation(self) -> None:
        fetcher = Mock(side_effect=TimeoutError("upstream timeout"))
        with self.assertRaises(MalformedPayloadException) as raised:
            StringDataProcessor.ingest(fetcher)
        self.assertEqual(
            raised.exception.context["error_type"], "TimeoutError"
        )
        fetcher.assert_called_once_with()
        with self.assertRaises(DataValidationError):
            StringDataProcessor.ingest(lambda: 42)  # type: ignore[arg-type]
        with self.assertRaises(DataValidationError):
            StringDataProcessor.ingest(None)  # type: ignore[arg-type]

    def test_mocked_latency_is_measured_in_microseconds(self) -> None:
        with patch(
            "processor.time.perf_counter_ns",
            side_effect=[0, 10_000, 20_000, 50_000],
        ):
            result = StringDataProcessor.benchmark_sanitization(
                "a   b", iterations=2
            )
        self.assertEqual(result["regex_microseconds_per_call"], 5.0)
        self.assertEqual(
            result["string_operations_microseconds_per_call"], 15.0
        )

    def test_benchmark_rejects_bad_iteration_count(self) -> None:
        with self.assertRaises(DataValidationError):
            StringDataProcessor.benchmark_sanitization("text", iterations=0)
        with self.assertRaises(DataValidationError):
            StringDataProcessor.benchmark_sanitization(
                None  # type: ignore[arg-type]
            )

    def test_text_table_rejects_missing_statistics(self) -> None:
        with self.assertRaises(DataValidationError):
            StringDataProcessor.to_table({})

    def test_fuzzy_generator_is_deterministic_and_stable(self) -> None:
        samples = noisy_text_samples(seed=9, count=40)
        self.assertEqual(samples, noisy_text_samples(seed=9, count=40))
        for sample in samples:
            tokens = StringDataProcessor.extract_numeric_tokens(sample)
            self.assertTrue(all(isinstance(token, float) for token in tokens))
            self.assertTrue(all(token == token for token in tokens))

    def test_large_text_input_is_supported_within_limit(self) -> None:
        large_text = "batch 12 " * 100_000
        self.assertEqual(
            len(StringDataProcessor.extract_numeric_tokens(large_text)),
            100_000,
        )

    def test_legacy_regression_sentinel(self) -> None:
        self.assertEqual(
            StringDataProcessor.calculate_word_frequencies(
                "Python is fast. Python is dynamic."
            ),
            {"python": 2, "is": 2, "fast": 1, "dynamic": 1},
        )
        self.assertEqual(
            StringDataProcessor.compute_summary_statistics([10.0, 20.0, 30.0]),
            {
                "count": 3.0,
                "sum": 60.0,
                "mean": 20.0,
                "min": 10.0,
                "max": 30.0,
            },
        )


class TestTestUtilities(CountingTestCase):
    def test_property_generator_has_requested_size(self) -> None:
        self.assertEqual(len(noisy_text_samples(count=7)), 7)

    def test_coverage_thresholds(self) -> None:
        self.assertEqual(coverage_state(90.0), "GREEN")
        self.assertEqual(coverage_state(75.0), "AMBER")
        self.assertEqual(coverage_state(74.9), "RED")

    def test_malicious_payloads_are_rejected_explicitly(self) -> None:
        for payload in (None, {}, ["1", "2"]):
            with self.subTest(payload=payload):
                with self.assertRaises(DataValidationError):
                    StringDataProcessor.extract_numeric_tokens(
                        payload  # type: ignore[arg-type]
                    )


class DiscoveryResult(unittest.TextTestResult):
    """Text result augmented with assertion and per-test duration totals."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.assertion_count = 0
        self.test_durations: list[float] = []
        self._started: dict[int, float] = {}

    def startTest(self, test: unittest.TestCase) -> None:
        self._started[id(test)] = time.perf_counter()
        test._runner_assertion_count = 0  # type: ignore[attr-defined]
        for name in dir(unittest.TestCase):
            if name.startswith("assert"):
                assertion = getattr(test, name, None)
                if callable(assertion):

                    def counted(
                        *args: Any,
                        _assertion: Any = assertion,
                        **kwargs: Any,
                    ) -> Any:
                        assertion_count = getattr(
                            test, "_runner_assertion_count", 0
                        ) + 1
                        setattr(
                            test, "_runner_assertion_count", assertion_count
                        )
                        return _assertion(*args, **kwargs)

                    setattr(test, name, counted)
        super().startTest(test)

    def stopTest(self, test: unittest.TestCase) -> None:
        self.assertion_count += int(
            getattr(test, "_runner_assertion_count", 0)
        )
        started = self._started.pop(id(test), time.perf_counter())
        self.test_durations.append(time.perf_counter() - started)
        super().stopTest(test)


def _coverage_summary(coverage_session: Any) -> dict[str, Any] | None:
    """Build statement and branch metrics from a completed coverage session."""
    if coverage_session is None:
        return None

    coverage_session.stop()
    with tempfile.TemporaryDirectory() as directory:
        report_path = Path(directory) / "coverage.json"
        coverage_session.json_report(outfile=str(report_path))
        report = json.loads(report_path.read_text(encoding="utf-8"))
    files = report.get("files", {}).values()
    statement_total = sum(
        file_data["summary"]["num_statements"] for file_data in files
    )
    files = report.get("files", {}).values()
    statement_covered = sum(
        file_data["summary"]["covered_lines"] for file_data in files
    )
    files = report.get("files", {}).values()
    branch_total = sum(
        file_data["summary"].get("num_branches", 0) for file_data in files
    )
    files = report.get("files", {}).values()
    branch_covered = sum(
        file_data["summary"].get("covered_branches", 0) for file_data in files
    )
    return {
        "statement_percent": 100.0 * statement_covered / statement_total
        if statement_total else 100.0,
        "branch_percent": (
            100.0 * branch_covered / branch_total if branch_total else 100.0
        ),
    }


def _start_coverage() -> Any:
    """Start optional branch coverage for supported engine modules."""
    try:
        import coverage
    except ImportError:
        return None

    coverage_session = coverage.Coverage(
        data_file=None,
        branch=True,
        source=["processor", "presets", "exceptions", "string_processor"],
        omit=["*/test_*.py"],
    )
    coverage_session.start()
    return coverage_session


def run_test_suite() -> dict[str, Any]:
    """Discover, execute, and summarize the complete local unittest suite."""
    project_root = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(project_root),
        pattern="test*.py",
        top_level_dir=str(project_root),
    )
    output = io.StringIO()
    runner = unittest.TextTestRunner(
        stream=output, verbosity=2, resultclass=DiscoveryResult
    )
    started = time.perf_counter()
    coverage_session = _start_coverage()
    result = runner.run(suite)
    duration = time.perf_counter() - started
    coverage_metrics = _coverage_summary(coverage_session)
    return {
        "passed": result.wasSuccessful(),
        "tests_run": result.testsRun,
        "failures": len(result.failures) + len(result.errors),
        "assertions": result.assertion_count,
        "duration_seconds": duration,
        "test_durations_seconds": result.test_durations,
        "output": output.getvalue(),
        "coverage": coverage_metrics,
    }


def main() -> int:
    """Run tests from the command line with an ASCII summary."""
    result = run_test_suite()
    print(result["output"], end="")
    print(
        "\nTests: {tests_run} | Failures: {failures} "
        "| Assertions: {assertions} "
        "| Duration: {duration:.6f}s".format(
            tests_run=result["tests_run"],
            failures=result["failures"],
            assertions=result["assertions"],
            duration=result["duration_seconds"],
        )
    )
    coverage_metrics = result["coverage"]
    if coverage_metrics:
        for metric, label in (
            ("statement_percent", "Statements"),
            ("branch_percent", "Branches"),
        ):
            value = coverage_metrics[metric]
            state = coverage_state(value)
            print(f"Coverage {label}: {value:.1f}% [{state}]")
    return 0 if result["passed"] else 1


def coverage_state(percent: float) -> str:
    """Classify coverage using the runner's documented thresholds."""
    return "GREEN" if percent >= 90 else "AMBER" if percent >= 75 else "RED"


if __name__ == "__main__":
    raise SystemExit(main())
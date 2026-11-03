"""Unicode-aware text sanitization and delimited-number parsing."""

import importlib.util
import io
import re
import sys
import unittest
from pathlib import Path
from typing import Dict, List


class DataValidationError(ValueError):
    """Raised when a processor receives an invalid input type or option."""


class TokenCorruptedError(DataValidationError):
    """Raised when a delimited numeric payload contains an invalid token."""


class StringDataProcessor:
    """Provide defensive text and numeric-token processing helpers."""

    @staticmethod
    def sanitize_whitespace(text: str) -> str:
        """Trim text and collapse consecutive Unicode whitespace."""
        if not isinstance(text, str):
            raise DataValidationError("Text input must be a string.")
        return " ".join(text.split())

    @staticmethod
    def extract_word_frequencies(text: str) -> Dict[str, int]:
        """Count case-insensitive Unicode words in the supplied text."""
        if not isinstance(text, str):
            raise DataValidationError("Text input must be a string.")

        words = re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)
        frequencies: Dict[str, int] = {}
        for word in words:
            frequencies[word] = frequencies.get(word, 0) + 1
        return frequencies

    @staticmethod
    def parse_delimited_numbers(
        raw_str: str,
        delimiter: str = ",",
    ) -> List[float]:
        """Parse delimited numbers, rejecting empty or corrupted tokens."""
        if not isinstance(raw_str, str):
            raise DataValidationError("Numeric input must be a string.")
        if not isinstance(delimiter, str) or not delimiter:
            raise DataValidationError("Delimiter must be a non-empty string.")
        if not raw_str.strip():
            return []

        numbers: List[float] = []
        for token in raw_str.split(delimiter):
            clean_token = token.strip()
            if not clean_token:
                raise TokenCorruptedError(
                    "Numeric input contains an empty token."
                )
            try:
                numbers.append(float(clean_token))
            except ValueError as error:
                raise TokenCorruptedError(
                    f"Invalid numeric token: {clean_token!r}."
                ) from error
        return numbers


def _run_unit_tests() -> tuple[bool, str]:
    """Load and execute the companion unit tests, returning captured output."""
    project_root = Path(__file__).resolve().parents[1]
    test_path = project_root / "tests" / "test_week3.py"
    spec = importlib.util.spec_from_file_location(
        "week3_browser_tests",
        test_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load tests from {test_path}.")

    test_module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(project_root))
    try:
        spec.loader.exec_module(test_module)
    finally:
        sys.path.remove(str(project_root))

    suite = unittest.defaultTestLoader.loadTestsFromModule(test_module)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    return result.wasSuccessful(), output.getvalue()


def _run_streamlit_app() -> None:
    """Render the text-analysis playground and companion test runner."""
    import streamlit as st

    st.title("Text Analysis Playground")
    text_column, numbers_column = st.columns(2)

    with text_column:
        text = st.text_area(
            "Text",
            value="Crème brûlée\nCrème brûlée 東京",
        )
        st.subheader("Sanitization preview")
        try:
            st.code(StringDataProcessor.sanitize_whitespace(text))
        except DataValidationError as error:
            st.error(str(error))

        st.subheader("Word frequencies")
        frequencies = StringDataProcessor.extract_word_frequencies(text)
        st.table(
            [
                {"Word": word, "Frequency": count}
                for word, count in frequencies.items()
            ]
        )

    with numbers_column:
        raw_numbers = st.text_input("Delimited numbers", value="1.5, 2, -3.25")
        delimiter = st.text_input("Delimiter", value=",")
        try:
            numbers = StringDataProcessor.parse_delimited_numbers(
                raw_numbers,
                delimiter,
            )
        except DataValidationError as error:
            st.error(str(error))
        else:
            st.write("Parsed values:", numbers)

    st.divider()
    if st.button("Run unit tests"):
        try:
            tests_passed, output = _run_unit_tests()
        except (OSError, RuntimeError) as error:
            st.error(f"Could not run unit tests: {error}")
        else:
            if tests_passed:
                st.success("All unit tests passed.")
            else:
                st.error("Some unit tests failed.")
            st.code(output or "No test output.")


if __name__ == "__main__":
    _run_streamlit_app()

"""Streamlit adapter for the Automated Testing & Text Processing Engine."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from exceptions import DataValidationError
from presets import PRESETS
from processor import StringDataProcessor


st.set_page_config(
    page_title="Automated Testing & Text Processing Engine",
    layout="wide",
)
st.title("Automated Testing & Text Processing Engine")
st.caption("Text sanitation, numeric analysis, and regression checks")

left_column, right_column = st.columns([1, 1], gap="large")
with left_column:
    raw_text = st.text_area(
        "Text input",
        value="Revenue rose from -12.5 to 18.75 across 3 quarters.",
        height=220,
    )
    preset_name = st.selectbox("Normalization profile", options=list(PRESETS))

try:
    st.session_state["analysis_result"] = StringDataProcessor.analyze(
        raw_text, preset_name
    )
except DataValidationError as error:
    st.session_state.pop("analysis_result", None)
    st.error(f"Input rejected: {error}")

analysis_result = st.session_state.get("analysis_result")
with right_column:
    st.subheader("Sanitized output")
    st.code(
        analysis_result["sanitized_text"] if analysis_result else "",
        language="text",
    )
    if analysis_result:
        statistics = analysis_result["statistics"]
        metric_columns = st.columns(3)
        for column, metric in zip(
            metric_columns, ("count", "sum", "mean"), strict=True
        ):
            column.metric(metric.title(), statistics[metric])
        st.write("Numeric tokens", analysis_result["numeric_tokens"])

if analysis_result:
    chart_column, export_column = st.columns([1, 1], gap="large")
    with chart_column:
        st.subheader("Token frequency")
        frequencies = analysis_result["word_frequencies"]
        if frequencies:
            frequency_data = pd.DataFrame(
                sorted(frequencies.items()), columns=("Token", "Frequency")
            ).set_index("Token")
            st.bar_chart(frequency_data)
        else:
            st.info("No word tokens found.")
    with export_column:
        st.subheader("Processed summary")
        st.code(StringDataProcessor.to_table(analysis_result), language="text")
        st.download_button(
            "Download CSV",
            data=StringDataProcessor.to_csv(analysis_result),
            file_name="text-analysis.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if st.button("Benchmark sanitation", use_container_width=True):
            measurements = StringDataProcessor.benchmark_sanitization(
                raw_text * 100, iterations=100
            )
            st.json(measurements)

st.divider()
st.subheader("Automated regression suite")
if st.button("Run unittest suite", use_container_width=False):
    try:
        from test_processor import run_test_suite

        with st.spinner("Discovering and running tests..."):
            suite_result = run_test_suite()
        st.session_state["suite_result"] = suite_result
    except Exception as error:
        st.error(f"Test runner failed: {type(error).__name__}: {error}")

suite_result = st.session_state.get("suite_result")
if suite_result:
    if suite_result["passed"]:
        st.success(f"PASS: {suite_result['tests_run']} tests completed.")
    else:
        st.error(f"FAIL: {suite_result['failures']} failing tests.")
    st.write(
        f"Assertions: {suite_result['assertions']} | "
        f"Duration: {suite_result['duration_seconds']:.4f}s"
    )
    coverage_result = suite_result["coverage"]
    if coverage_result:
        statement_rate = coverage_result["statement_percent"]
        branch_rate = coverage_result["branch_percent"]
        st.write(
            f"Statement coverage: {statement_rate:.1f}% | "
            f"Branch coverage: {branch_rate:.1f}%"
        )
        coverage_frame = pd.DataFrame(
            {"Coverage": [statement_rate, branch_rate]},
            index=("Statements", "Branches"),
        )
        st.bar_chart(coverage_frame)
    st.code(suite_result["output"] or "No test output.", language="text")

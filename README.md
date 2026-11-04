# Automated Testing & Text Processing Engine

**Intern:** Akshya Gupta
**Track:** YuvaIntern — Junior Python Developer
**Milestone:** Week 3 Task

## Overview
The Week 3 project is a UI-independent text-processing library with a Streamlit
workbench. The engine provides multi-stage Unicode sanitation, normalization
profiles, numeric token analytics, structured domain errors, and JSON, CSV, and
plain-text exports. Its unittest suite includes boundary matrices, deterministic
fuzzy inputs, mocked integration failures, and legacy regression checks.

## Modules
- `processor.py`: UI-independent processing engine and compatibility methods.
- `exceptions.py`: Context-carrying domain exception hierarchy.
- `presets.py`: Strict Alpha, Financial/Numeric Only, Slugify, and Alphanumeric Clean profiles.
- `test_processor.py`: New behavior tests, full test discovery CLI, benchmark, and coverage summary.
- `app.py`: Reactive Streamlit text lab, analytics visualizer, CSV export, and test runner.
- `string_data_processor.py`: Backward-compatible import path for existing callers.

## Setup
```bash
python3 -m pip install -r requirements.txt
```

## Run Tests
Run all top-level Week 3 test modules with verbose discovery and coverage totals:
```bash
python3 test_processor.py
```

Run the feature suite directly or discover tests with `unittest`:
```bash
python3 -m unittest -v test_processor.py
python3 -m unittest discover -v
```

Coverage percentages are measured at runtime and reported with green, amber, or
red thresholds; they are not hard-coded guarantees. Without `coverage.py`, the
test runner still executes and reports test outcomes, assertion counts, and
durations.

## Run the Web App
```bash
streamlit run app.py
```

The engine can also be used without Streamlit:
```python
from processor import StringDataProcessor

result = StringDataProcessor.analyze("Quarterly revenue: -12.5, 18.75, 3")
print(result["statistics"])
print(StringDataProcessor.to_csv(result))
```

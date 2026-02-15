Test a specific AIPEA module with coverage reporting.

Usage: /test-module <module_name>

Run targeted tests for the specified module (e.g., security, analyzer, engine, enhancer, knowledge, search) and report coverage for that module only.

Steps:
1. Run: `pytest tests/test_$ARGUMENTS.py -v --cov=src/aipea/$ARGUMENTS --cov-report=term-missing`
2. If the test file doesn't exist, search for matching test files: `ls tests/test_*$ARGUMENTS*.py`
3. Report pass/fail count, coverage percentage, and any uncovered lines
4. If coverage is below 75%, suggest which lines/branches need tests

from pathlib import Path

import pytest

from analyze_repo import analyze_codebase

TESTDATA = Path(__file__).parent / "testdata" / "java"

ZEROS = {
    "statement_count": 0,
    "math_ops": 0,
    "bitwise_ops": 0,
    "conditionals": 0,
    "logical_ops": 0,
    "comparisons": 0,
    "calls": 0,
    "assertions": 0,
    "exception_handlers": 0,
}


def _expect(results, name, **overrides):
    """Assert all metrics match. Unspecified fields default to 0."""
    assert results[name] == {**ZEROS, **overrides}


@pytest.fixture(scope="module")
def results():
    return analyze_codebase(TESTDATA, "java")


# ---------------------------------------------------------------------------
# Ops.java — operator categories
# ---------------------------------------------------------------------------


def test_math_ops(results):
    _expect(results, "Ops.Ops.mathOps", statement_count=3, math_ops=3)


def test_bitwise_ops(results):
    _expect(results, "Ops.Ops.bitwiseOps", statement_count=2, bitwise_ops=2)


def test_comparisons(results):
    _expect(results, "Ops.Ops.comparisons", statement_count=3, conditionals=1, comparisons=1)


def test_logical_ops(results):
    _expect(results, "Ops.Ops.logicalOps", statement_count=1, logical_ops=3)


def test_conditionals(results):
    _expect(results, "Ops.Ops.conditionals", statement_count=5, conditionals=3, comparisons=2, math_ops=1)


# ---------------------------------------------------------------------------
# Ops.java — call counting
# ---------------------------------------------------------------------------


def test_calls_one(results):
    _expect(results, "Ops.Ops.callsOne", statement_count=1, calls=1)


def test_calls_two(results):
    _expect(results, "Ops.Ops.callsTwo", statement_count=2, calls=2)


def test_calls_three(results):
    _expect(results, "Ops.Ops.callsThree", statement_count=3, calls=3)


# ---------------------------------------------------------------------------
# Ops.java — assertions, exceptions
# ---------------------------------------------------------------------------


def test_assertions(results):
    _expect(results, "Ops.Ops.withAssertion", statement_count=1, assertions=1, comparisons=1)


def test_exception_handlers(results):
    _expect(results, "Ops.Ops.withException", statement_count=4, calls=3, exception_handlers=2)


# ---------------------------------------------------------------------------
# Boilerplate class
# ---------------------------------------------------------------------------


def test_boilerplate(results):
    _expect(results, "Ops.Boilerplate.boilerplate", statement_count=4)


def test_min_statements_filtering():
    filtered = analyze_codebase(TESTDATA, "java", min_statements=3)
    for fn in filtered.values():
        assert fn["statement_count"] >= 3

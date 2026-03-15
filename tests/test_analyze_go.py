from pathlib import Path

import pytest

from analyze_repo import analyze_codebase

TESTDATA = Path(__file__).parent / "testdata" / "go"

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
    return analyze_codebase(TESTDATA, "go")


# ---------------------------------------------------------------------------
# ops.go — operator categories
# ---------------------------------------------------------------------------


def test_math_ops(results):
    _expect(results, "ops.mathOps", statement_count=3, math_ops=3)


def test_bitwise_ops(results):
    _expect(results, "ops.bitwiseOps", statement_count=2, bitwise_ops=2)


def test_comparisons(results):
    _expect(results, "ops.comparisons", statement_count=1, comparisons=1)


def test_logical_ops(results):
    _expect(results, "ops.logicalOps", statement_count=1, logical_ops=3)


def test_conditionals(results):
    _expect(results, "ops.conditionals", statement_count=5, conditionals=3, comparisons=2, math_ops=1)


# ---------------------------------------------------------------------------
# ops.go — call counting
# ---------------------------------------------------------------------------


def test_calls_zero(results):
    _expect(results, "ops.callsZero", statement_count=1)


def test_calls_one(results):
    _expect(results, "ops.callsOne", statement_count=1, calls=1)


def test_calls_two(results):
    _expect(results, "ops.callsTwo", statement_count=2, calls=2)


def test_calls_three(results):
    _expect(results, "ops.callsThree", statement_count=3, calls=3)


# ---------------------------------------------------------------------------
# ops.go — struct method, boilerplate
# ---------------------------------------------------------------------------


def test_method_dotted_path(results):
    _expect(results, "ops.method", statement_count=1, math_ops=1)


def test_boilerplate(results):
    _expect(results, "ops.boilerplate", statement_count=4)


def test_min_statements_filtering():
    filtered = analyze_codebase(TESTDATA, "go", min_statements=2)
    for fn in filtered.values():
        assert fn["statement_count"] >= 2

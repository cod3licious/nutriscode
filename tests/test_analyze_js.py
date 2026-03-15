from pathlib import Path

import pytest
from helpers import expected_counts as _expect

from analyze_repo import analyze_codebase

TESTDATA = Path(__file__).parent / "testdata" / "js"


@pytest.fixture(scope="module")
def results():
    return analyze_codebase(TESTDATA, "ts")


# ---------------------------------------------------------------------------
# ops.js — operator categories
# ---------------------------------------------------------------------------


def test_math_ops(results):
    _expect(results, "ops.mathOps", statement_count=3, math_ops=3)


def test_bitwise_ops(results):
    _expect(results, "ops.bitwiseOps", statement_count=2, bitwise_ops=2)


def test_comparisons(results):
    _expect(results, "ops.comparisons", statement_count=3, conditionals=1, comparisons=1)


def test_logical_ops(results):
    _expect(results, "ops.logicalOps", statement_count=1, logical_ops=3)


def test_conditionals(results):
    # if/else if/else → 3 conditionals; x > 0 and x < 0 → 2 comparisons; -x → 1 math
    _expect(results, "ops.conditionals", statement_count=5, conditionals=3, comparisons=2, math_ops=1)


# ---------------------------------------------------------------------------
# ops.js — call counting
# ---------------------------------------------------------------------------


def test_calls_zero(results):
    _expect(results, "ops.callsZero", statement_count=1)


def test_calls_one(results):
    _expect(results, "ops.callsOne", statement_count=2, calls=1)


def test_calls_two(results):
    _expect(results, "ops.callsTwo", statement_count=2, calls=2)


def test_calls_three(results):
    _expect(results, "ops.callsThree", statement_count=3, calls=3)


# ---------------------------------------------------------------------------
# ops.js — exceptions, arrow, class
# ---------------------------------------------------------------------------


def test_exception_handlers(results):
    _expect(results, "ops.withException", statement_count=4, calls=3, exception_handlers=2)


def test_arrow_function_inline(results):
    # return items.map(x => x + 1) — map is a call, x + 1 from arrow body counted inline
    _expect(results, "ops.withArrow", statement_count=1, math_ops=1, calls=1)


def test_class_method_dotted_path(results):
    _expect(results, "ops.MyClass.method", statement_count=1, math_ops=1)


def test_boilerplate(results):
    _expect(results, "ops.boilerplate", statement_count=4)


# ---------------------------------------------------------------------------
# JS/TS family scanning — .ts and .tsx files picked up alongside .js
# ---------------------------------------------------------------------------


def test_ts_file_included(results):
    _expect(results, "types.tsComputations", statement_count=1, math_ops=2)


def test_ts_class_method(results):
    _expect(results, "types.TypedClass.compute", statement_count=1, math_ops=1)


def test_tsx_file_included(results):
    # value > 0 ? value : 0 — ternary is a conditional, > is a comparison
    _expect(results, "component.SimpleComponent", statement_count=1, conditionals=1, comparisons=1)


def test_min_statements_filtering():
    filtered = analyze_codebase(TESTDATA, "ts", min_statements=2)
    for fn in filtered.values():
        assert fn["statement_count"] >= 2

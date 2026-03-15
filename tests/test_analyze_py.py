from pathlib import Path

import pytest
from helpers import expected_counts as _expect

from analyze_repo import analyze_codebase

TESTDATA = Path(__file__).parent / "testdata" / "py"


@pytest.fixture(scope="module")
def results():
    return analyze_codebase(TESTDATA, "py")


# ---------------------------------------------------------------------------
# ops.py — operator categories
# ---------------------------------------------------------------------------


def test_math_ops(results):
    # x = a + b; y = x * 2; return y - 1
    _expect(results, "ops.math_ops", statement_count=3, math_ops=3)


def test_bitwise_ops(results):
    # x = a | b; y = x & 1; return y
    _expect(results, "ops.bitwise_ops", statement_count=3, bitwise_ops=2)


def test_type_union_not_bitwise(results):
    # def f(x: int | str, y: float | None) -> bool | None: return x
    _expect(results, "ops.type_union_not_bitwise", statement_count=1)


def test_comparisons(results):
    # if a == b: return a / return b
    _expect(results, "ops.comparisons", statement_count=3, conditionals=1, comparisons=1)


def test_logical_ops(results):
    # return (a and b) or not c
    _expect(results, "ops.logical_ops", statement_count=1, logical_ops=3)


def test_conditionals(results):
    # if x > 0: return x / if x < 0: return -x / return 0
    _expect(results, "ops.conditionals", statement_count=5, conditionals=2, comparisons=2, math_ops=1)


# ---------------------------------------------------------------------------
# ops.py — call counting
# ---------------------------------------------------------------------------


def test_calls_zero(results):
    _expect(results, "ops.calls_zero", statement_count=1)


def test_calls_one(results):
    _expect(results, "ops.calls_one", statement_count=2, calls=1)


def test_calls_two(results):
    _expect(results, "ops.calls_two", statement_count=2, calls=2)


def test_calls_three(results):
    _expect(results, "ops.calls_three", statement_count=3, calls=3)


# ---------------------------------------------------------------------------
# ops.py — assertions, exceptions
# ---------------------------------------------------------------------------


def test_assertions(results):
    # assert x > 0; return x — assert_statement is not a statement_node_type in Python
    _expect(results, "ops.with_assertion", statement_count=1, assertions=1, comparisons=1)


def test_exception_handlers(results):
    # try: foo() / except: bar() / finally: baz()
    _expect(results, "ops.with_exception", statement_count=4, calls=3, exception_handlers=2)


# ---------------------------------------------------------------------------
# ops.py — nested functions, lambdas, classes
# ---------------------------------------------------------------------------


def test_nested_inner_scored_separately(results):
    _expect(results, "ops.nested_inner", statement_count=1, math_ops=1)


def test_nested_outer_excludes_inner_ops(results):
    # y = x + 1; return y — nested_inner not counted here
    _expect(results, "ops.nested_outer", statement_count=2, math_ops=1)


def test_lambda_counted_inline(results):
    # return sorted(items, key=lambda x: x + 1)
    _expect(results, "ops.with_lambda", statement_count=1, math_ops=1, calls=1)


def test_class_method_dotted_path(results):
    _expect(results, "ops.MyClass.method", statement_count=1, math_ops=1)


# ---------------------------------------------------------------------------
# ops.py — boilerplate and statement-only functions
# ---------------------------------------------------------------------------


def test_boilerplate(results):
    # x = data; y = x; z = y; return z — all statements, zero ops
    _expect(results, "ops.boilerplate", statement_count=4)


def test_augmented_assignments(results):
    # x += 1; x -= 2; return x — no double-counting with expression_statement
    _expect(results, "ops.augmented_assignments", statement_count=3, math_ops=2)


def test_annotated_assignments(results):
    # x: int = 5; y: str = "hello"; return x, y — annotations don't produce ops
    _expect(results, "ops.annotated_assignments", statement_count=3)


def test_yield(results):
    # for item in items: yield item + 1
    _expect(results, "ops.with_yield", statement_count=2, conditionals=1, math_ops=1)


# ---------------------------------------------------------------------------
# loops.py — multi-file scanning + loop counting
# ---------------------------------------------------------------------------


def test_multifile_scanning(results):
    assert "ops.math_ops" in results
    assert "loops.for_loop" in results
    assert "loops.while_loop" in results


def test_for_loop(results):
    # total = 0; for item in items: total += item; return total
    _expect(results, "loops.for_loop", statement_count=4, math_ops=1, conditionals=1)


def test_while_loop(results):
    # result = 1; while n > 0: result *= n; n -= 1; return result
    _expect(results, "loops.while_loop", statement_count=5, math_ops=2, conditionals=1, comparisons=1)


# ---------------------------------------------------------------------------
# min_statements filtering
# ---------------------------------------------------------------------------


def test_min_statements_filtering():
    filtered = analyze_codebase(TESTDATA, "py", min_statements=3)
    for fn in filtered.values():
        assert fn["statement_count"] >= 3

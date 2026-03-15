from pathlib import Path

import pytest

from analyze_repo import analyze_codebase

TESTDATA = Path(__file__).parent / "testdata" / "py"


@pytest.fixture(scope="module")
def results():
    return analyze_codebase(TESTDATA, "py")


def test_math_ops(results):
    fn = results["ops.math_ops"]
    assert fn["statement_count"] == 5
    assert fn["math_ops"] == 3


def test_bitwise_ops(results):
    fn = results["ops.bitwise_ops"]
    assert fn["bitwise_ops"] == 2
    assert fn["math_ops"] == 0


def test_type_union_not_bitwise(results):
    fn = results["ops.type_union_not_bitwise"]
    assert fn["bitwise_ops"] == 0


def test_comparisons(results):
    fn = results["ops.comparisons"]
    assert fn["comparisons"] == 1
    assert fn["conditionals"] == 1


def test_logical_ops(results):
    fn = results["ops.logical_ops"]
    assert fn["logical_ops"] == 3


def test_conditionals(results):
    fn = results["ops.conditionals"]
    assert fn["conditionals"] == 2
    assert fn["comparisons"] == 2


def test_calls_zero(results):
    fn = results["ops.calls_zero"]
    assert fn["calls"] == 0


def test_calls_one(results):
    fn = results["ops.calls_one"]
    assert fn["calls"] == 1


def test_calls_two(results):
    fn = results["ops.calls_two"]
    assert fn["calls"] == 2


def test_calls_three(results):
    fn = results["ops.calls_three"]
    assert fn["calls"] == 3


def test_assertions(results):
    fn = results["ops.with_assertion"]
    assert fn["assertions"] == 1


def test_exception_handlers(results):
    fn = results["ops.with_exception"]
    assert fn["exception_handlers"] == 2


def test_nested_inner_is_own_entry(results):
    assert "ops.nested_inner" in results


def test_nested_outer_excludes_inner_ops(results):
    outer = results["ops.nested_outer"]
    # outer has: y = x + 1 (1 math op), return y (1 stmt), y = x + 1 (1 stmt), nested_inner def (1 stmt)
    assert outer["math_ops"] == 1
    # nested_inner's math_ops should NOT be included in outer
    inner = results["ops.nested_inner"]
    assert inner["math_ops"] == 1


def test_lambda_counted_inline(results):
    fn = results["ops.with_lambda"]
    assert fn["math_ops"] == 1  # x + 1 in the lambda body


def test_class_method_dotted_path(results):
    assert "ops.MyClass.method" in results
    fn = results["ops.MyClass.method"]
    assert fn["math_ops"] == 1


def test_min_statements_filtering():
    results = analyze_codebase(TESTDATA, "py", min_statements=3)
    for fn in results.values():
        assert fn["statement_count"] >= 3


def test_multifile_scanning(results):
    # ops.py functions present
    assert "ops.math_ops" in results
    # loops.py functions present
    assert "loops.for_loop" in results
    assert "loops.while_loop" in results


def test_for_loop(results):
    fn = results["loops.for_loop"]
    assert fn["statement_count"] == 6
    assert fn["math_ops"] == 1
    assert fn["conditionals"] == 1


def test_while_loop(results):
    fn = results["loops.while_loop"]
    assert fn["statement_count"] == 8
    assert fn["math_ops"] == 2
    assert fn["comparisons"] == 1

from pathlib import Path

import pytest

from analyze_repo import analyze_codebase

TESTDATA = Path(__file__).parent / "testdata" / "js"


@pytest.fixture(scope="module")
def results():
    return analyze_codebase(TESTDATA, "ts")


def test_math_ops(results):
    fn = results["ops.mathOps"]
    assert fn["statement_count"] == 3
    assert fn["math_ops"] == 3


def test_bitwise_ops(results):
    fn = results["ops.bitwiseOps"]
    assert fn["bitwise_ops"] == 2
    assert fn["math_ops"] == 0


def test_comparisons(results):
    fn = results["ops.comparisons"]
    assert fn["comparisons"] == 1
    assert fn["conditionals"] == 1


def test_logical_ops(results):
    fn = results["ops.logicalOps"]
    assert fn["logical_ops"] == 3


def test_conditionals(results):
    fn = results["ops.conditionals"]
    assert fn["conditionals"] == 3
    assert fn["comparisons"] == 2


def test_calls_zero(results):
    fn = results["ops.callsZero"]
    assert fn["calls"] == 0


def test_calls_one(results):
    fn = results["ops.callsOne"]
    assert fn["calls"] == 1


def test_calls_two(results):
    fn = results["ops.callsTwo"]
    assert fn["calls"] == 2


def test_calls_three(results):
    fn = results["ops.callsThree"]
    assert fn["calls"] == 3


def test_exception_handlers(results):
    fn = results["ops.withException"]
    assert fn["exception_handlers"] == 2


def test_arrow_function_inline(results):
    fn = results["ops.withArrow"]
    assert fn["math_ops"] == 1  # x + 1 in arrow body


def test_class_method_dotted_path(results):
    assert "ops.MyClass.method" in results
    fn = results["ops.MyClass.method"]
    assert fn["math_ops"] == 1


def test_ts_file_included(results):
    # types.ts functions should be picked up
    assert "types.tsComputations" in results
    fn = results["types.tsComputations"]
    assert fn["math_ops"] == 2


def test_ts_class_method(results):
    assert "types.TypedClass.compute" in results
    fn = results["types.TypedClass.compute"]
    assert fn["math_ops"] == 1


def test_tsx_file_included(results):
    # component.tsx should be picked up
    assert "component.SimpleComponent" in results
    fn = results["component.SimpleComponent"]
    assert fn["comparisons"] == 1
    assert fn["conditionals"] == 1


def test_min_statements_filtering():
    results = analyze_codebase(TESTDATA, "ts", min_statements=2)
    for fn in results.values():
        assert fn["statement_count"] >= 2

from pathlib import Path

import pytest

from analyze_repo import analyze_codebase

TESTDATA = Path(__file__).parent / "testdata" / "java"


@pytest.fixture(scope="module")
def results():
    return analyze_codebase(TESTDATA, "java")


def test_math_ops(results):
    fn = results["Ops.Ops.mathOps"]
    assert fn["statement_count"] == 3
    assert fn["math_ops"] == 3


def test_bitwise_ops(results):
    fn = results["Ops.Ops.bitwiseOps"]
    assert fn["bitwise_ops"] == 2
    assert fn["math_ops"] == 0


def test_comparisons(results):
    fn = results["Ops.Ops.comparisons"]
    assert fn["comparisons"] == 1
    assert fn["conditionals"] == 1


def test_logical_ops(results):
    fn = results["Ops.Ops.logicalOps"]
    assert fn["logical_ops"] == 3


def test_conditionals(results):
    fn = results["Ops.Ops.conditionals"]
    assert fn["conditionals"] == 3
    assert fn["comparisons"] == 2


def test_calls_one(results):
    fn = results["Ops.Ops.callsOne"]
    assert fn["calls"] == 1


def test_calls_two(results):
    fn = results["Ops.Ops.callsTwo"]
    assert fn["calls"] == 2


def test_calls_three(results):
    fn = results["Ops.Ops.callsThree"]
    assert fn["calls"] == 3


def test_assertions(results):
    fn = results["Ops.Ops.withAssertion"]
    assert fn["assertions"] == 1


def test_exception_handlers(results):
    fn = results["Ops.Ops.withException"]
    assert fn["exception_handlers"] == 2


def test_min_statements_filtering():
    results = analyze_codebase(TESTDATA, "java", min_statements=3)
    for fn in results.values():
        assert fn["statement_count"] >= 3

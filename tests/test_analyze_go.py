from pathlib import Path

import pytest

from analyze_repo import analyze_codebase

TESTDATA = Path(__file__).parent / "testdata" / "go"


@pytest.fixture(scope="module")
def results():
    return analyze_codebase(TESTDATA, "go")


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


def test_method_dotted_path(results):
    # Go method on struct — keyed with just function name since Go has no class hierarchy in file
    assert "ops.method" in results
    fn = results["ops.method"]
    assert fn["math_ops"] == 1


def test_min_statements_filtering():
    results = analyze_codebase(TESTDATA, "go", min_statements=2)
    for fn in results.values():
        assert fn["statement_count"] >= 2

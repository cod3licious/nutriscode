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


def expected_counts(results, name, **overrides):
    """Helper to create a full dict with unspecified fields defaulting to 0."""
    assert results[name] == {**ZEROS, **overrides}

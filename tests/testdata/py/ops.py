def math_ops(a, b):
    x = a + b
    y = x * 2
    return y - 1


def bitwise_ops(a, b):
    x = a | b
    y = x & 1
    return y


def type_union_not_bitwise(x: int | str, y: float | None) -> bool | None:
    return x


def comparisons(a, b):
    if a == b:
        return a
    return b


def logical_ops(a, b, c):
    return (a and b) or not c


def conditionals(x):
    if x > 0:
        return x
    if x < 0:
        return -x
    return 0


def calls_zero(a):
    return a


def calls_one():
    foo()
    return 1


def calls_two():
    foo()
    bar()


def calls_three():
    foo()
    bar()
    baz()


def with_assertion(x):
    assert x > 0
    return x


def with_exception():
    try:
        foo()
    except ValueError:
        bar()
    finally:
        baz()


def nested_outer(x):
    y = x + 1

    def nested_inner(z):
        return z * 2

    return y


def with_lambda(items):
    return sorted(items, key=lambda x: x + 1)


class MyClass:
    def method(self, x):
        return x * 2

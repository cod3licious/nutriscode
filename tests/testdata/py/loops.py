def for_loop(items):
    total = 0
    for item in items:
        total += item
    return total


def while_loop(n):
    result = 1
    while n > 0:
        result *= n
        n -= 1
    return result

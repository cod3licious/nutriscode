function mathOps(a, b) {
    const x = a + b;
    const y = x * 2;
    return y - 1;
}

function bitwiseOps(a, b) {
    const x = a | b;
    return x & 1;
}

function comparisons(a, b) {
    if (a === b) {
        return a;
    }
    return b;
}

function logicalOps(a, b, c) {
    return a && b || !c;
}

function conditionals(x) {
    if (x > 0) {
        return x;
    } else if (x < 0) {
        return -x;
    }
    return 0;
}

function callsZero(a) {
    return a;
}

function callsOne() {
    foo();
    return 1;
}

function callsTwo() {
    foo();
    bar();
}

function callsThree() {
    foo();
    bar();
    baz();
}

function withException() {
    try {
        foo();
    } catch (e) {
        bar();
    } finally {
        baz();
    }
}

function withArrow(items) {
    return items.map(x => x + 1);
}

class MyClass {
    method(x) {
        return x * 2;
    }
}

function boilerplate(data) {
    const x = data;
    const y = x;
    const z = y;
    return z;
}

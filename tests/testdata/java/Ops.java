public class Ops {

    public int mathOps(int a, int b) {
        int x = a + b;
        int y = x * 2;
        return y - 1;
    }

    public int bitwiseOps(int a, int b) {
        int x = a | b;
        return x & 1;
    }

    public boolean comparisons(int a, int b) {
        if (a == b) {
            return true;
        }
        return false;
    }

    public boolean logicalOps(boolean a, boolean b, boolean c) {
        return a && b || !c;
    }

    public int conditionals(int x) {
        if (x > 0) {
            return x;
        } else if (x < 0) {
            return -x;
        }
        return 0;
    }

    public void callsOne() {
        foo();
    }

    public void callsTwo() {
        foo();
        bar();
    }

    public void callsThree() {
        foo();
        bar();
        baz();
    }

    public void withAssertion(int x) {
        assert x > 0;
    }

    public void withException() {
        try {
            foo();
        } catch (Exception e) {
            bar();
        } finally {
            baz();
        }
    }
}

class Boilerplate {
    public int boilerplate(int data) {
        int x = data;
        int y = x;
        int z = y;
        return z;
    }
}

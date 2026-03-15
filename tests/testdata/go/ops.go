package ops

func mathOps(a, b int) int {
	x := a + b
	y := x * 2
	return y - 1
}

func bitwiseOps(a, b int) int {
	x := a | b
	return x & 1
}

func comparisons(a, b int) bool {
	return a == b
}

func logicalOps(a, b, c bool) bool {
	return a && b || !c
}

func conditionals(x int) int {
	if x > 0 {
		return x
	} else if x < 0 {
		return -x
	}
	return 0
}

func callsZero(a int) int {
	return a
}

func callsOne() {
	foo()
}

func callsTwo() {
	foo()
	bar()
}

func callsThree() {
	foo()
	bar()
	baz()
}

type MyStruct struct{}

func (s MyStruct) method(x int) int {
	return x * 2
}

func boilerplate(data int) int {
	x := data
	y := x
	z := y
	return z
}

# 13강 검산: 론스키안, 기저 -> ODE.
from sympy import symbols, exp, log, cos, sin, cosh, sinh, simplify, diff, Matrix

x = symbols('x', positive=True)


def W(f, g):
    return simplify(f * diff(g, x) - diff(f, x) * g)


def ode_ok(y, a2, a1, a0):
    """a2(x) y'' + a1(x) y' + a0(x) y = 0 에 y 를 넣은 잔차가 0인지"""
    return simplify(a2 * diff(y, x, 2) + a1 * diff(y, x) + a0 * y) == 0


def check(title, basis, ans, wrongs):
    y1, y2 = basis
    print(f"{title}: W = {W(y1, y2)}")
    print(f"   answer {ans[3]}: {'OK' if ode_ok(y1, *ans[:3]) and ode_ok(y2, *ans[:3]) else 'FAIL'}")
    for w in wrongs:
        both = ode_ok(y1, *w[:3]) and ode_ok(y2, *w[:3])
        print(f"   wrong  {w[3]}: {'both solve (!!)' if both else 'fails for a basis function'}")


print("existing W checks:", W(exp(x), exp(2 * x)), W(cos(x), sin(x)), W(exp(x), 3 * exp(x)), W(x, x * log(x)))
print("other pairs (should be nonzero):", W(x, x**2), W(sin(x), cos(x)), W(exp(x), exp(-x)))
print("W(0, y2) =", W(0 * x, exp(x)), "| W(cosh, sinh) =", W(cosh(x), sinh(x)))

check("e^{2x}, e^{-3x}", (exp(2 * x), exp(-3 * x)), (1, 1, -6, "y'' + y' - 6y"),
      [(1, -1, -6, "y'' - y' - 6y"), (1, 5, 6, "y'' + 5y' + 6y"), (1, -1, 6, "y'' - y' + 6y")])
check("x^2, x^3", (x**2, x**3), (x**2, -4 * x, 6, "x^2y'' - 4xy' + 6y"),
      [(x**2, -5 * x, 6, "x^2y'' - 5xy' + 6y"), (1, -5, 6, "y'' - 5y' + 6y"), (x**2, 4 * x, 6, "x^2y'' + 4xy' + 6y")])
check("e^x cos2x, e^x sin2x", (exp(x) * cos(2 * x), exp(x) * sin(2 * x)), (1, -2, 5, "y'' - 2y' + 5y"),
      [(1, 2, 5, "y'' + 2y' + 5y"), (1, -2, -3, "y'' - 2y' - 3y"), (1, 0, 4, "y'' + 4y")])
check("x, x ln x", (x, x * log(x)), (x**2, -x, 1, "x^2y'' - xy' + y"),
      [(x**2, -2 * x, 1, "x^2y'' - 2xy' + y"), (1, -2, 1, "y'' - 2y' + y"), (x**2, x, 1, "x^2y'' + xy' + y")])
print("W(x, x ln x) at x->0+: zero only in the limit; W = x is not identically 0 -> independent")

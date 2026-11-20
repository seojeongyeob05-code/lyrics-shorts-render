# 11강 검산: 2계 상수계수 제차. 정답은 일반해(상수 2개)로 식을 만족, 오답은 불만족 또는 상수 부족.
from sympy import symbols, exp, cos, sin, cosh, sinh, simplify, diff, Rational, I

x, A, B, w = symbols('x A B omega', positive=True)
C1, C2 = A, B


def ok(Y, a2, a1, a0):
    return simplify(a2 * diff(Y, x, 2) + a1 * diff(Y, x) + a0 * Y) == 0


def check(title, coeffs, ans, wrongs):
    print(f"{title}: answer {'OK' if ok(ans, *coeffs) else 'FAIL'}")
    for w_ in wrongs:
        print(f"    wrong {w_}: {'satisfies (!!)' if ok(w_, *coeffs) else 'not a solution'}")


check("y'' - 5y' + 6y", (1, -5, 6), C1*exp(2*x) + C2*exp(3*x), [C1*exp(-2*x) + C2*exp(-3*x), (C1 + C2*x)*exp(5*x), C1*exp(x) + C2*exp(6*x)])
check("y'' + 4y' + 4y", (1, 4, 4), (C1 + C2*x)*exp(-2*x), [C1*exp(2*x) + C2*x*exp(2*x), C1*cos(2*x) + C2*sin(2*x)])
print("    note: C1 e^{-2x} + C2 e^{-2x} solves but is one constant (C1+C2) e^{-2x}")
check("y'' + 2y' + 5y", (1, 2, 5), exp(-x)*(A*cos(2*x) + B*sin(2*x)), [exp(x)*(A*cos(2*x) + B*sin(2*x)), exp(-2*x)*(A*cos(x) + B*sin(x)), C1*exp(-x) + C2*exp(-5*x)])
check("y'' + 4y' = 0 (trap)", (1, 4, 0), C1 + C2*exp(-4*x), [A*cos(2*x) + B*sin(2*x), C1*exp(4*x) + C2, (C1 + C2*x)*exp(-4*x)])
check("y'' = 0 (k = 0)", (1, 0, 0), C1 + C2*x, [C1*exp(x) + C2*exp(-x), A*cos(x) + B*sin(x)])
check("y'' - w^2 y = 0", (1, 0, -w**2), A*cosh(w*x) + B*sinh(w*x), [A*cos(w*x) + B*sin(w*x), (A + B*x)*exp(w*x), A*cosh(x) + B*sinh(x)])
print("    cosh/sinh form equals C1 e^{wx} + C2 e^{-wx}:", simplify((A*cosh(w*x) + B*sinh(w*x)).rewrite(exp) - ((A + B)/2*exp(w*x) + (A - B)/2*exp(-w*x))) == 0)
check("2y'' - 3y' + y", (2, -3, 1), C1*exp(x) + C2*exp(x/2), [C1*exp(x) + C2*exp(2*x), C1*exp(-x) + C2*exp(-x/2), (C1 + C2*x)*exp(x)])
check("y'' + 9y", (1, 0, 9), A*cos(3*x) + B*sin(3*x), [])
print("IVP y'' - y = 0, y(0) = 2, y'(0) = 0:")
for nm, Y in [("e^x + e^-x", exp(x) + exp(-x)), ("2e^x", 2*exp(x)), ("e^x - e^-x", exp(x) - exp(-x)), ("2cos x", 2*cos(x))]:
    print(f"    {nm:12} ODE {ok(Y, 1, 0, -1)}  y(0)={Y.subs(x, 0)}  y'(0)={diff(Y, x).subs(x, 0)}")
print("Euler: e^{i b x} =", simplify(exp(I*3*x).rewrite(cos)))

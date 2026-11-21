# 12강 검산: 오일러-코시 x^2 y'' + a x y' + b y = 0 (x > 0).
from sympy import symbols, log, cos, sin, sqrt, exp, simplify, diff, solve, Rational

x = symbols('x', positive=True)
C1, C2, A, B, m = symbols('C1 C2 A B m')


def ok(Y, a2, a1, a0):
    return simplify(a2 * x**2 * diff(Y, x, 2) + a1 * x * diff(Y, x) + a0 * Y) == 0


def check(title, co, ans, wrongs):
    print(f"{title}: answer {'OK' if ok(ans, *co) else 'FAIL'}")
    for w in wrongs:
        print(f"    wrong {w}: {'satisfies (!!)' if ok(w, *co) else 'not a solution'}")


check("x^2y'' - 2xy' + 2y", (1, -2, 2), C1 * x + C2 * x**2, [C1 / x + C2 / x**2, C1 * exp(x) + C2 * exp(2 * x), x * (C1 + C2 * log(x))])
check("x^2y'' - xy' + y", (1, -1, 1), x * (C1 + C2 * log(x)), [C1 * x + C2 / x, (C1 + C2 * x) * exp(x), C1 * cos(log(x)) + C2 * sin(log(x))])
check("x^2y'' + xy' + y", (1, 1, 1), A * cos(log(x)) + B * sin(log(x)), [A * cos(x) + B * sin(x), x * (A * cos(x) + B * sin(x)), C1 * x + C2 / x])
check("x^2y'' + 3xy' + y", (1, 3, 1), (C1 + C2 * log(x)) / x, [C1 / x + C2 * x, (C1 + C2 * x) * exp(-x), x * (C1 + C2 * log(x))])
check("4x^2y'' + 8xy' + y  (y'' 계수 4)", (4, 8, 1), x**Rational(-1, 2) * (C1 + C2 * log(x)),
      [sqrt(x) * (C1 + C2 * log(x)), C1 / sqrt(x) + C2 * sqrt(x), (C1 + C2 * log(x)) / x])
print("    aux eq after dividing by 4:", solve(m * (m - 1) + 2 * m + Rational(1, 4), m), "| plugging a=8,b=1 without dividing:", solve(m**2 + 7 * m + 1, m))

print("IVP x^2y'' - 2xy' + 2y = 0, y(1)=3, y'(1)=4:")
sol = solve([C1 + C2 - 3, C1 + 2 * C2 - 4], [C1, C2])
Y = (C1 * x + C2 * x**2).subs(sol)
print("   ", sol, "| y =", Y, "| ODE", ok(Y, 1, -2, 2), "| y(1) =", Y.subs(x, 1), "y'(1) =", diff(Y, x).subs(x, 1))
print("   swapping constants (Q&A 2): C1 x^2 + C2 x is the same family:", ok(C1 * x**2 + C2 * x, 1, -2, 2))

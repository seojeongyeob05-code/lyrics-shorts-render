# 10강 검산: 공식 계수내림 y2 = y1 * int( e^{-int p} / y1^2 ).
from sympy import symbols, Function, exp, log, cos, sin, tan, simplify, diff, integrate

x, C1, C2 = symbols('x C1 C2', positive=True)


def y2_formula(p, y1):
    U = simplify(exp(-integrate(p, x)) / y1**2)
    return U, simplify(y1 * integrate(U, x))


def is_sol(Y, p, q):
    return simplify(diff(Y, x, 2) + p * diff(Y, x) + q * Y) == 0


cases = [
    ("y'' - 2y' + y = 0, y1 = e^x", -2, 1, exp(x), [exp(-x), exp(2 * x), x**2 * exp(x)]),
    ("x^2y'' - 3xy' + 4y = 0, y1 = x^2", -3 / x, 4 / x**2, x**2, [x**3, x**-2, x * log(x)]),
    ("x^2y'' + xy' - y = 0, y1 = x", 1 / x, -1 / x**2, x, [x * log(x), x**2, log(x)]),
    ("y'' + y = 0, y1 = cos x", 0, 1, cos(x), [x * cos(x), tan(x), cos(x) * log(cos(x))]),
    ("x^2y'' + xy' + y = 0, y1 = cos(ln x)", 1 / x, 1 / x**2, cos(log(x)), [log(x) * cos(log(x)), x * cos(log(x)), sin(x)]),
]
for title, p, q, y1, wrongs in cases:
    U, y2 = y2_formula(p, y1)
    print(f"{title}:  U = {U},  y2 = {y2},  y1 ok {is_sol(y1, p, q)},  y2 ok {is_sol(y2, p, q)}")
    for w in wrongs:
        print(f"    wrong {w}: {'solution (!!)' if is_sol(w, p, q) else 'not a solution'}")

print("general solution of y'' - 2y' + y = 0:")
for nm, Y in [("(C1 + C2 x)e^x", (C1 + C2 * x) * exp(x)), ("C1 e^x + C2 e^-x", C1 * exp(x) + C2 * exp(-x)),
              ("(C1 + C2 x)e^-x", (C1 + C2 * x) * exp(-x))]:
    print(f"    {nm:20} {'solution' if is_sol(Y, -2, 1) else 'not a solution'}")
print("    C e^x (1 + x): one constant only -> solution but not general:", is_sol(C1 * exp(x) * (1 + x), -2, 1))

# 증명: y = u y1 대입 -> y1 u'' + (2 y1' + p y1) u' = 0
u, y1f, pf, qf = Function('u')(x), Function('y1')(x), Function('p')(x), Function('q')(x)
expr = diff(u * y1f, x, 2) + pf * diff(u * y1f, x) + qf * u * y1f
expr = expr.subs(diff(y1f, x, 2), -pf * diff(y1f, x) - qf * y1f)
print("substitution leaves:", simplify(expr.expand()))

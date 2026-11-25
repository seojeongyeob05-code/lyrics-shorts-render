# 16강 검산: 비제차 오일러-코시 x^2y'' + a x y' + b y = r(x), x > 0.
from sympy import symbols, log, simplify, diff, solve, expand, Rational, integrate

x = symbols('x', positive=True)
A, B, C = symbols('A B C')


def L(y, a, b):
    return x**2 * diff(y, x, 2) + a * x * diff(y, x) + b * y


def try_form(name, form, unknowns, a, b, r):
    eq = expand(simplify(L(form, a, b) - r))
    pts = [Rational(k + 2, 3) for k in range(len(unknowns) + 4)]
    sol = solve([eq.subs(x, pt) for pt in pts], unknowns, dict=True)
    good = bool(sol) and simplify(eq.subs(sol[0])) == 0
    print(f"    {name:22} -> {'works: y_p = ' + str(simplify(form.subs(sol[0]))) if good else 'cannot work'}")


print("existing: x^2y'' - 2xy' + 2y = x^3")
try_form("A x^3", A * x**3, [A], -2, 2, x**3)
print("x^2y'' - 2xy' + 2y = x  (x overlaps y_h = x, x^2 -> multiply ln x)")
for nm, f, u in [("A x ln x", A * x * log(x), [A]), ("A x^2", A * x**2, [A]), ("A x", A * x, [A]), ("A x^2 ln x", A * x**2 * log(x), [A])]:
    try_form(nm, f, u, -2, 2, x)
print("x^2y'' + xy' - y = x^2  (y_h = x, 1/x)")
for nm, f, u in [("A x^2", A * x**2, [A]), ("A x", A * x, [A]), ("A ln x + B", A * log(x) + B, [A, B]), ("A x^2 ln x", A * x**2 * log(x), [A])]:
    try_form(nm, f, u, 1, -1, x**2)
print("x^2y'' - 2xy' + 2y = ln x")
for nm, f, u in [("A ln x + B", A * log(x) + B, [A, B]), ("A ln x", A * log(x), [A]), ("A x ln x", A * x * log(x), [A]), ("A (ln x)^2", A * log(x)**2, [A])]:
    try_form(nm, f, u, -2, 2, log(x))

# 매개변수법으로도 같은 결과인지 (표준형 r/x^2)
y1, y2 = x, x**2
W = simplify(y1 * diff(y2, x) - diff(y1, x) * y2)
r = x / x**2
yp = simplify(-y1 * integrate(simplify(y2 * r / W), x) + y2 * integrate(simplify(y1 * r / W), x))
print("VOP for x^2y''-2xy'+2y = x with r/x^2:", yp, "| residual:", simplify(L(yp, -2, 2) - x))
r_wrong = x
yp_w = simplify(-y1 * integrate(simplify(y2 * r_wrong / W), x) + y2 * integrate(simplify(y1 * r_wrong / W), x))
print("VOP with r (forgot /x^2):", yp_w, "| residual:", simplify(L(yp_w, -2, 2) - x))

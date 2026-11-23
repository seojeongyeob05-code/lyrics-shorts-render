# 14강 검산: 미정계수법. 틀에 미지계수를 넣고 대입해서 풀리면 맞는 틀, 모순이면 틀린 틀.
from sympy import symbols, exp, cos, sin, simplify, diff, solve, expand, Rational, Eq

x = symbols('x')
A, B, C, D = symbols('A B C D')


def L(y, a, b):
    return diff(y, x, 2) + a * diff(y, x) + b * y


def try_form(name, form, unknowns, a, b, r):
    eq = expand(simplify(L(form, a, b) - r))
    # 모든 x 에서 0 이어야 함: 여러 점에서 계수 방정식을 세워 푼다
    pts = [Rational(k, 3) for k in range(1, len(unknowns) + 4)]
    sol = solve([eq.subs(x, pt) for pt in pts], unknowns, dict=True)
    good = bool(sol) and simplify(eq.subs(sol[0])) == 0
    yp = simplify(form.subs(sol[0])) if good else None
    print(f"    {name:32} -> {'works: y_p = ' + str(yp) if good else 'cannot work'}")
    return yp


print("y'' - 3y' + 2y = 4 :"); try_form("A", A + 0 * x, [A], -3, 2, 4)
print("y'' + y = e^{2x} :"); try_form("A e^{2x}", A * exp(2 * x), [A], 0, 1, exp(2 * x))
print("y'' - y = e^x :")
for nm, f, u in [("A x e^x", A * x * exp(x), [A]), ("A e^x", A * exp(x), [A]), ("A x^2 e^x", A * x**2 * exp(x), [A])]:
    try_form(nm, f, u, 0, -1, exp(x))
print("y'' - 2y' + y = e^x :")
for nm, f, u in [("A x^2 e^x", A * x**2 * exp(x), [A]), ("A x e^x", A * x * exp(x), [A]), ("(Ax+B)e^x", (A * x + B) * exp(x), [A, B])]:
    try_form(nm, f, u, -2, 1, exp(x))
print("y'' + 4y = sin 2x :")
for nm, f, u in [("x(A cos2x + B sin2x)", x * (A * cos(2 * x) + B * sin(2 * x)), [A, B]), ("A sin 2x", A * sin(2 * x), [A]),
                 ("A cos2x + B sin2x", A * cos(2 * x) + B * sin(2 * x), [A, B]), ("A x sin 2x", A * x * sin(2 * x), [A])]:
    try_form(nm, f, u, 0, 4, sin(2 * x))
print("y'' + y' = x^2 :")
for nm, f, u in [("x(Ax^2+Bx+C)", x * (A * x**2 + B * x + C), [A, B, C]), ("Ax^2+Bx+C", A * x**2 + B * x + C, [A, B, C]), ("A x^2", A * x**2, [A])]:
    try_form(nm, f, u, 1, 0, x**2)

print("NEW y'' - y' = 2x + e^{2x}  (y_h = C1 + C2 e^x):")
for nm, f, u in [("x(Ax+B) + C e^{2x}", x * (A * x + B) + C * exp(2 * x), [A, B, C]),
                 ("x(Ax + B + C e^{2x})", x * (A * x + B + C * exp(2 * x)), [A, B, C]),
                 ("Ax + B + C e^{2x}", A * x + B + C * exp(2 * x), [A, B, C]),
                 ("A x^2 + C e^{2x}", A * x**2 + C * exp(2 * x), [A, C])]:
    try_form(nm, f, u, -1, 0, 2 * x + exp(2 * x))
print("NEW y'' - y = x e^{2x}  (y_h = e^{x}, e^{-x}):")
for nm, f, u in [("(Ax+B)e^{2x}", (A * x + B) * exp(2 * x), [A, B]), ("A x e^{2x}", A * x * exp(2 * x), [A]),
                 ("Ax + B + C e^{2x}", A * x + B + C * exp(2 * x), [A, B, C]), ("x(Ax+B)e^{2x}", x * (A * x + B) * exp(2 * x), [A, B])]:
    try_form(nm, f, u, 0, -1, x * exp(2 * x))
print("NEW y'' - 2y' + 2y = cos x  (y_h = e^x(cos x, sin x)):")
for nm, f, u in [("A cos x + B sin x", A * cos(x) + B * sin(x), [A, B]), ("x(A cos x + B sin x)", x * (A * cos(x) + B * sin(x)), [A, B]),
                 ("e^x(A cos x + B sin x)", exp(x) * (A * cos(x) + B * sin(x)), [A, B]), ("A cos x", A * cos(x), [A])]:
    try_form(nm, f, u, -2, 2, cos(x))
print("NEW IVP y'' + y = 2x, y(0)=0, y'(0)=3:")
yp = try_form("Ax + B", A * x + B, [A, B], 0, 1, 2 * x)
C1, C2 = symbols('C1 C2')
Y = C1 * cos(x) + C2 * sin(x) + yp
s = solve([Y.subs(x, 0), diff(Y, x).subs(x, 0) - 3], [C1, C2])
print("    constants:", s, "| y =", Y.subs(s), "| check:", simplify(L(Y.subs(s), 0, 1) - 2 * x) == 0)

# 18강 검산: 고계 상수계수 ODE
from sympy import symbols, Function, dsolve, Eq, exp, cos, sin, factor, Matrix, simplify, diff, solve, integrate, log, Rational

x, l, A, B = symbols('x l A B')
y = Function('y')
D = lambda f, n=1: diff(f, x, n)

cases = {
    "y'''-y'": (y(x).diff(x, 3) - y(x).diff(x), l**3 - l),
    "y'''-3y''+3y'-y": (y(x).diff(x, 3) - 3 * y(x).diff(x, 2) + 3 * y(x).diff(x) - y(x), l**3 - 3 * l**2 + 3 * l - 1),
    "y4-16y": (y(x).diff(x, 4) - 16 * y(x), l**4 - 16),
    "y4+2y''+y": (y(x).diff(x, 4) + 2 * y(x).diff(x, 2) + y(x), l**4 + 2 * l**2 + 1),
    "y5-3y4+3y'''-y''": (y(x).diff(x, 5) - 3 * y(x).diff(x, 4) + 3 * y(x).diff(x, 3) - y(x).diff(x, 2), l**5 - 3 * l**4 + 3 * l**3 - l**2),
}
for name, (lhs, ch) in cases.items():
    print(name, "| char:", factor(ch), "|", dsolve(Eq(lhs, 0)).rhs)

# 론스키안 W(1, e^x, e^-x)
fs = [1, exp(x), exp(-x)]
W = Matrix([[D(f, k) if k else f for f in fs] for k in range(3)]).det()
print("W(1,e^x,e^-x) =", simplify(W))

# 3계 매개변수법 공식 검산: y''' - y' = e^{2x}
r = exp(2 * x)
M = Matrix([[D(f, k) if k else f for f in fs] for k in range(3)])
yp = 0
for j in range(3):
    Mj = M.copy(); Mj[:, j] = Matrix([0, 0, 1])
    yp += fs[j] * integrate(simplify(Mj.det() / W * r), x)
yp = simplify(yp)
print("VOP y_p for y'''-y'=e^{2x}:", yp, "| residual:", simplify(D(yp, 3) - D(yp) - r))

# 행렬식 연산
a = Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 10]])
d0 = a.det()
b = a.copy(); b[:, 1] = a[:, 1] + 3 * a[:, 0]; print("det", d0, "| col2 += 3*col1:", b.det())
b = a.copy(); b[:, 1] = 3 * a[:, 1] + a[:, 0]; print("col2 = 3*col2 + col1:", b.det())
b = a.copy(); b[:, 0] = a[:, 1]; b[:, 1] = a[:, 0]; print("swap col1,col2:", b.det())
b = a.copy(); b[:, 1] = 3 * a[:, 1] - a[:, 0]; print("col2 = 3*col2 - col1:", b.det())

# y''' - 3y'' + 3y' - y = e^x : 틀 후보
L3 = lambda f: D(f, 3) - 3 * D(f, 2) + 3 * D(f) - f
for nm, f in [("A x^3 e^x", A * x**3 * exp(x)), ("A e^x", A * exp(x)), ("A x e^x", A * x * exp(x)), ("A x^2 e^x", A * x**2 * exp(x))]:
    print(" ", nm, "->", simplify(L3(f)), "| A =", solve(simplify(L3(f) / exp(x)) - 1, A))

# y''' + y' = x + 1 : 틀 후보 (r = x 이면 A x^2 만으로도 맞아서 x + 1 로 바꿈)
L = lambda f: D(f, 3) + D(f)
for nm, f, u in [("A x^2 + B x", A * x**2 + B * x, [A, B]), ("A x + B", A * x + B, [A, B]), ("A x^2", A * x**2, [A]), ("A x^3 + B x^2", A * x**3 + B * x**2, [A, B])]:
    eq = simplify(L(f) - x - 1)
    sol = solve([eq.subs(x, k) for k in range(5)], u, dict=True)
    print(" ", nm, "->", sol)
print("general y'''+y'=x+1:", dsolve(Eq(y(x).diff(x, 3) + y(x).diff(x), x + 1)).rhs)

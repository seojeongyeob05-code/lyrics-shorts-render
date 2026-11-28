# 19강 검산: 고계 오일러-코시 x^3y''' + a x^2y'' + b xy' + c y = r(x), x > 0
from sympy import symbols, Function, diff, simplify, expand, factor, log, cos, sin, Matrix, integrate, Rational, solve

x = symbols('x', positive=True)
m, A = symbols('m A')
D = lambda f, n=1: diff(f, x, n)


def L(f, a, b, c):
    return x**3 * D(f, 3) + a * x**2 * D(f, 2) + b * x * D(f) + c * f


def aux(a, b, c):
    return expand(m * (m - 1) * (m - 2) + a * m * (m - 1) + b * m + c)


print("x^3 y''' of x^m:", simplify(x**3 * D(x**m, 3) / x**m), "=", factor(simplify(x**3 * D(x**m, 3) / x**m)))
for nm, (a, b, c), basis in [
    ("x^3y'''+xy'-y", (0, 1, -1), [x, x * log(x), x * log(x)**2]),
    ("x^3y'''+3x^2y''-2xy'+2y", (3, -2, 2), [x, x * log(x), x**-2]),
    ("x^3y'''+2x^2y''+xy'-y", (2, 1, -1), [x, cos(log(x)), sin(log(x))]),
    ("x^3y'''-3x^2y''+6xy'-6y", (-3, 6, -6), [x, x**2, x**3]),
]:
    print(nm, "| aux:", aux(a, b, c), "=", factor(aux(a, b, c)), "| basis check:", [simplify(L(f, a, b, c)) for f in basis])
# 오답 보조방정식 (계수 그대로) 은 다른 근
print("wrong aux m^3+2m^2+m-1 roots:", solve(m**3 + 2 * m**2 + m - 1, m)[:1], "...")
# 복소 중근 ±i : (m^2+1)^2 -> 4계 오일러-코시 x^4y''''+6x^3y'''+9x^2y''+3xy'+y? 직접 확인
f4 = lambda f: x**4 * D(f, 4) + 6 * x**3 * D(f, 3) + 9 * x**2 * D(f, 2) + 3 * x * D(f) + f
print("4th-order aux:", factor(expand(m*(m-1)*(m-2)*(m-3) + 6*m*(m-1)*(m-2) + 9*m*(m-1) + 3*m + 1)))
print("  ln x cos(ln x), ln x sin(ln x):", simplify(f4(log(x) * cos(log(x)))), simplify(f4(log(x) * sin(log(x)))), "| x cos(ln x):", simplify(f4(x * cos(log(x)))) != 0)
# 비제차 x^3y''' - 3x^2y'' + 6xy' - 6y = x^4
fs = [x, x**2, x**3]
M = Matrix([[D(f, k) if k else f for f in fs] for k in range(3)])
W = simplify(M.det()); print("W(x,x^2,x^3) =", W)
r = x**4 / x**3
yp = 0
for j in range(3):
    Mj = M.copy(); Mj[:, j] = Matrix([0, 0, 1])
    yp += fs[j] * integrate(simplify(Mj.det() / W * r), x)
yp = simplify(yp); print("VOP y_p (r = x^4/x^3):", yp, "| residual:", simplify(L(yp, -3, 6, -6) - x**4))
r_bad = x**4
yp_b = simplify(sum(fs[j] * integrate(simplify((lambda Mj: (Mj.__setitem__((slice(None), j), Matrix([0, 0, 1])), Mj)[1])(M.copy()).det() / W * r_bad), x) for j in range(3)))
print("VOP with r = x^4 (forgot /x^3):", yp_b, "| residual:", simplify(L(yp_b, -3, 6, -6) - x**4))
print("undetermined A x^4:", simplify(L(A * x**4, -3, 6, -6)), "-> A =", solve(L(A * x**4, -3, 6, -6) / x**4 - 1, A))

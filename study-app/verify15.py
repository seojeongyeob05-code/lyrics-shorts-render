# 15강 검산: 매개변수 변환법 y_p = -y1 int(y2 r / W) + y2 int(y1 r / W)  (표준형 r)
from sympy import symbols, exp, log, cos, sin, tan, sec, simplify, diff, integrate, Rational

x = symbols('x', positive=True)


def W(y1, y2):
    return simplify(y1 * diff(y2, x) - diff(y1, x) * y2)


def vop(y1, y2, r):
    w = W(y1, y2)
    return simplify(-y1 * integrate(simplify(y2 * r / w), x) + y2 * integrate(simplify(y1 * r / w), x))


def L(y, a, b):
    return simplify(diff(y, x, 2) + a * diff(y, x) + b * y)


print("y'' + y = sec x")
yp = vop(cos(x), sin(x), sec(x))
print("  y_p =", yp, "| residual:", simplify(L(yp, 0, 1) - sec(x)))
ans = cos(x) * log(cos(x)) + x * sin(x)
print("  answer cos x ln cos x + x sin x residual:", simplify(L(ans, 0, 1) - sec(x)))
for nm, w_ in [("x cos x + sin x ln cos x", x * cos(x) + sin(x) * log(cos(x))), ("sec x tan x", sec(x) * tan(x)), ("x sin x", x * sin(x))]:
    print("  wrong", nm, ":", "solves (!!)" if simplify(L(w_, 0, 1) - sec(x)) == 0 else "not a y_p")

print("swap y1, y2 gives the same y_p:", simplify(vop(cos(x), sin(x), sec(x)) - vop(sin(x), cos(x), sec(x))) == 0)

print("y'' + y = cos x: method of undetermined coeff y_p = x sin x / 2; VOP y_p =", vop(cos(x), sin(x), cos(x)))
d = simplify(vop(cos(x), sin(x), cos(x)) - x * sin(x) / 2)
print("  difference =", d, "-> is a homogeneous solution:", simplify(L(d, 0, 1)) == 0)

print("y'' - 2y' + y = e^x / x  (y1 = e^x, y2 = x e^x)")
print("  W =", W(exp(x), x * exp(x)))
yp = vop(exp(x), x * exp(x), exp(x) / x)
print("  raw y_p =", simplify(yp))
cand = x * exp(x) * log(x)
print("  x e^x ln x residual:", simplify(L(cand, -2, 1) - exp(x) / x))
for nm, w_ in [("e^x ln x", exp(x) * log(x)), ("x e^x", x * exp(x)), ("x^2 e^x ln x", x**2 * exp(x) * log(x))]:
    print("  wrong", nm, ":", "solves (!!)" if simplify(L(w_, -2, 1) - exp(x) / x) == 0 else "not a y_p")

print("2y'' + 2y = sec x -> standard r = sec(x)/2; y_p =", vop(cos(x), sin(x), sec(x) / 2),
      "| residual of 2y''+2y:", simplify(2 * diff(vop(cos(x), sin(x), sec(x) / 2), x, 2) + 2 * vop(cos(x), sin(x), sec(x) / 2) - sec(x)))
print("y'' + y = tan x  y_p =", vop(cos(x), sin(x), tan(x)))
print("superposition y'' + y = x + tan x : x + y_p(tan) residual:",
      simplify(L(x + vop(cos(x), sin(x), tan(x)), 0, 1) - (x + tan(x))))

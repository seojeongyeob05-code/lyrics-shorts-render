# 01강 2일차 새 문제 검산: 정답은 식을 만족, 오답은 불만족.
from sympy import symbols, Function, exp, log, cos, sin, tan, sec, cosh, sinh, simplify, diff

x, C = symbols('x C')
y = Function('y')(x)
yp = diff(y, x)


def implicit_ok(F, rhs):
    # F(x, y) = C 를 x로 미분한 뒤 y' = rhs 를 넣었을 때 0 이면 해
    return simplify(diff(F, x).subs(yp, rhs))


print("y' = cos y")
rhs = cos(y)
print("  answer ln|sec y + tan y| - x:", implicit_ok(log(sec(y) + tan(y)) - x, rhs))
for name, F in [("ln|cos y| - x", log(cos(y)) - x), ("tan y - x", tan(y) - x), ("sin y - x", sin(y) - x)]:
    print("  wrong", name, "->", "0 (!!)" if implicit_ok(F, rhs) == 0 else "nonzero")

print("y' = x e^(x-y)")
f = lambda Y: x * exp(x - Y)
for name, Y, want in [("answer ln((x-1)e^x + C)", log((x - 1) * exp(x) + C), True),
                      ("wrong ln(x e^x + C)", log(x * exp(x) + C), False),
                      ("wrong ln((x+1)e^x + C)", log((x + 1) * exp(x) + C), False),
                      ("wrong (x-1)e^x + C", (x - 1) * exp(x) + C, False)]:
    r = simplify(diff(Y, x) - f(Y))
    print(" ", name, "residual", r)

print("y' = y cosh x, y(0) = 3")
Y = 3 * exp(sinh(x))
print("  residual", simplify(diff(Y, x) - Y * cosh(x)), " y(0) =", Y.subs(x, 0))
for name, W in [("wrong C e^(cosh x)", 3 * exp(cosh(x))), ("wrong C e^x", 3 * exp(x))]:
    print(" ", name, "residual nonzero" if simplify(diff(W, x) - W * cosh(x)) != 0 else "0 (!!)")

# Weierstrass: with t = tan(x/2), dx/(1+cos x) = dt
t = symbols('t')
xs = 2 * __import__('sympy').atan(t)
print("Weierstrass 1/(1+cos x) dx in t:", simplify((1 / (1 + cos(xs))) * diff(xs, t)))

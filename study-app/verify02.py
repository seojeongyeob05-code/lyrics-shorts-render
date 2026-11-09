# 02강 검산: 정답은 식을 만족, 오답은 불만족.
from sympy import symbols, Function, exp, log, cos, tan, atan, sqrt, simplify, diff, solve, Rational

x, C = symbols('x C')
y = Function('y')(x)
yp = diff(y, x)


def implicit(F, rhs):
    """F(x, y) = C 가 y' = rhs 의 해인지: dF/dx 에 y' = rhs 대입 후 0 인지"""
    return simplify(diff(F, x).subs(yp, rhs))


def explicit(Y, rhs):
    return simplify(diff(Y, x) - rhs.subs(y, Y))


def report(name, val):
    print(f"  {name:48} -> {'OK (0)' if val == 0 else 'nonzero'}")


print("1) y' = (x+y)^2, u = x+y:  u' = 1 + y' = 1 + u^2 (u'에 y'를 넣으면 성립)")
u = x + y
report("u' - (1+u^2)", simplify(diff(u, x).subs(yp, (x + y)**2) - (1 + u**2)))

print("2) y' = y/x + 1  ->  y = x ln|x| + Cx")
rhs = y / x + 1
report("answer x ln x + Cx", explicit(x * log(x) + C * x, rhs))
for n, Y in [("wrong ln x + C", log(x) + C), ("wrong x + Cx^2", x + C * x**2), ("wrong C x e^x", C * x * exp(x))]:
    report(n, explicit(Y, rhs))

print("3) y' = y/x + x/y  ->  y^2 = 2x^2 ln|x| + Cx^2  i.e. y^2/x^2 - 2 ln x = C")
rhs = y / x + x / y
report("answer y^2/x^2 - 2ln x", implicit(y**2 / x**2 - 2 * log(x), rhs))
for n, F in [("wrong y^2 - x^2", y**2 - x**2), ("wrong y/x - ln x", y / x - log(x)), ("wrong y^2 - 2 ln x", y**2 - 2 * log(x))]:
    report(n, implicit(F, rhs))

print("4) y' = cos(x+y)  ->  x + y = 2 arctan(x + C)   i.e.  tan((x+y)/2) - x = C")
rhs = cos(x + y)
report("answer tan((x+y)/2) - x", implicit(tan((x + y) / 2) - x, rhs))
for n, F in [("wrong tan(x+y) - x", tan(x + y) - x), ("wrong tan(x+y) [x+y = arctan(x+C)] ", tan(x + y) - x),
             ("wrong y - sin x", y - __import__('sympy').sin(x))]:
    report(n, implicit(F, rhs))

print("5) y' = 1/(x+y)  ->  x + y + 1 = C e^y   i.e. (x+y+1) e^{-y} = C")
rhs = 1 / (x + y)
report("answer (x+y+1)e^{-y}", implicit((x + y + 1) * exp(-y), rhs))
for n, F in [("wrong (x+y+1)e^{-x}", (x + y + 1) * exp(-x)), ("wrong (x+y)e^{-y}", (x + y) * exp(-y)),
             ("wrong (y+x+1)e^{-x} [y'=x+y]", (y + x + 1) * exp(-x))]:
    report(n, implicit(F, rhs))

print("6) quasi-homogeneous y' = (x+y-3)/(x-y-1)")
h, k = symbols('h k')
print("  intersection:", solve([h + k - 3, h - k - 1], [h, k]))
X, Y = symbols('X Y')
print("  shifted numerator/denominator:", simplify((X + 2) + (Y + 1) - 3), "/", simplify((X + 2) - (Y + 1) - 1))
rhs = (x + y - 3) / (x - y - 1)
Xs, Ys = x - 2, y - 1
report("answer atan(Y/X) - ln sqrt(X^2+Y^2)", implicit(atan(Ys / Xs) - log(sqrt(Xs**2 + Ys**2)), rhs))
for n, F in [("wrong unshifted atan(y/x) - ln sqrt(x^2+y^2)", atan(y / x) - log(sqrt(x**2 + y**2))),
             ("wrong sign atan(Y/X) + ln sqrt(X^2+Y^2)", atan(Ys / Xs) + log(sqrt(Xs**2 + Ys**2))),
             ("wrong shift (x+2, y+1)", atan((y + 1) / (x + 2)) - log(sqrt((x + 2)**2 + (y + 1)**2)))]:
    report(n, implicit(F, rhs))

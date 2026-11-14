# 06강 검산: 베르누이 방정식. 정답은 식을 만족, 오답은 불만족.
from sympy import symbols, Function, exp, log, sqrt, simplify, diff, Integral, Rational

x, C, n = symbols('x C n')
y = Function('y')(x)
yp = diff(y, x)


def explicit(Y, f):
    return simplify(diff(Y, x) - f(Y))


def implicit(F, rhs):
    return simplify(diff(F, x).subs(yp, rhs))


def rep(name, v):
    print(f"  {name:42} -> {'OK (0)' if v == 0 else 'nonzero'}")


print("u = y^(1-n) => u' :", simplify(diff(y**(1 - n), x) - (1 - n) * y**(-n) * yp))

print("y' + y = y^3  -> y^-2 = 1 + Ce^{2x}")
rhs = y**3 - y
rep("answer y^-2 - Ce^{2x} (implicit)", implicit((y**-2 - 1) * exp(-2*x), rhs))

print("y' + y = sqrt(y)  -> y = (1 + Ce^{-x/2})^2")
f = lambda Y: sqrt(Y) - Y
Ys = (1 + C*exp(-x/2))**2
rep("answer (1 + Ce^{-x/2})^2  [C>0 branch]", simplify(explicit(Ys, f).subs(C, 1)))
for nm, W in [("1 + Ce^{-x/2}", 1 + C*exp(-x/2)), ("(1 + Ce^{-x})^2", (1 + C*exp(-x))**2), ("(1 + Ce^{-2x})^2", (1 + C*exp(-2*x))**2)]:
    rep("wrong " + nm, simplify(explicit(W, f).subs(C, 1)))

print("y' + y/x = x y^2  -> y = 1/(Cx - x^2)")
f = lambda Y: x*Y**2 - Y/x
rep("answer 1/(Cx - x^2)", explicit(1/(C*x - x**2), f))
for nm, W in [("1/(Cx + x^2)", 1/(C*x + x**2)), ("Cx - x^2", C*x - x**2), ("1/(C - x^2)", 1/(C - x**2))]:
    rep("wrong " + nm, explicit(W, f))

print("y' + y = 1/y  (n = -1)  -> y^2 = 1 + Ce^{-2x}")
rhs = 1/y - y
rep("answer y^2 - Ce^{-2x}", implicit((y**2 - 1)*exp(2*x), rhs))
for nm, F in [("y^2 = 1 + Ce^{-x}", (y**2 - 1)*exp(x)), ("y = 1 + Ce^{-2x}", (y - 1)*exp(2*x)), ("y^-2 = 1 + Ce^{2x}", (y**-2 - 1)*exp(-2*x))]:
    rep("wrong " + nm, implicit(F, rhs))

print("y' + y ln y = e^{-x} y   (u = ln y)  -> ln y = (x + C) e^{-x}")
rhs = exp(-x)*y - y*log(y)
rep("answer ln y e^x - x", implicit(log(y)*exp(x) - x, rhs))
for nm, F in [("y = (x+C)e^{-x}", y*exp(x) - x), ("ln y = x e^{-x} + C", log(y) - x*exp(-x)), ("ln y = (x+C)e^{x}", log(y)*exp(-x) - x)]:
    rep("wrong " + nm, implicit(F, rhs))

print("y(x) = 2 + int_0^x (y - y^2) dt  ->  y' = y - y^2, y(0) = 2")
f = lambda Y: Y - Y**2
for nm, Y in [("answer 2/(2 - e^{-x})", 2/(2 - exp(-x))), ("wrong 1/(1 + e^{-x})", 1/(1 + exp(-x))),
              ("wrong 2/(1 + e^{-x})", 2/(1 + exp(-x))), ("wrong 2e^x", 2*exp(x))]:
    print(f"  {nm:42} ODE: {'OK' if explicit(Y, f) == 0 else 'no'}  y(0) = {simplify(Y.subs(x, 0))}")

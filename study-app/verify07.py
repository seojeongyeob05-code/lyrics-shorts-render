# 07강 검산: 리카티 방정식.
from sympy import symbols, Function, exp, simplify, diff, sin, cos

x, C = symbols('x C')
y = Function('y')(x)


def explicit(Y, f):
    return simplify(diff(Y, x) - f(Y))


def rep(name, v):
    print(f"  {name:40} -> {'OK (0)' if v == 0 else 'nonzero'}")


# A) y' = y^2 - 2/x^2, y1 = 1/x
f = lambda Y: Y**2 - 2/x**2
print("A) y' = y^2 - 2/x^2")
for nm, Y in [("y1 = 1/x", 1/x), ("y1 = -2/x", -2/x), ("x", x), ("2/x", 2/x), ("x^2", x**2)]:
    rep("particular " + nm, explicit(Y, f))
# v equation: y = 1/x + 1/v  ->  v' + (2/x) v = -1
v = Function('v')(x)
Ysub = 1/x + 1/v
expr = simplify((diff(Ysub, x) - f(Ysub)) * (-v**2))  # = v' + (2/x)v + 1 after clearing
print("  substituted (times -v^2):", simplify(expr))
rep("answer 1/x + 3x^2/(C - x^3)", explicit(1/x + 3*x**2/(C - x**3), f))
for nm, W in [("1/x + x^2/(C - x^3)", 1/x + x**2/(C - x**3)), ("3x^2/(C - x^3)", 3*x**2/(C - x**3)),
              ("1/x + (C - x^3)/(3x^2)", 1/x + (C - x**3)/(3*x**2))]:
    rep("wrong " + nm, explicit(W, f))

# B) y' = y^2 - y/x - 1/x^2, find y1, solve
f = lambda Y: Y**2 - Y/x - 1/x**2
print("B) y' = y^2 - y/x - 1/x^2")
for nm, Y in [("1/x", 1/x), ("x", x), ("x^2", x**2), ("e^x", exp(x)), ("-x", -x)]:
    rep("candidate " + nm, explicit(Y, f))
Ysub = 1/x + 1/v
print("  substituted (times -v^2):", simplify((diff(Ysub, x) - f(Ysub)) * (-v**2)))
rep("answer 1/x + 2x/(C - x^2)", explicit(1/x + 2*x/(C - x**2), f))
for nm, W in [("1/x + x/(C - x^2)", 1/x + x/(C - x**2)), ("2x/(C - x^2)", 2*x/(C - x**2)),
              ("1/x + (C - x^2)/(2x)", 1/x + (C - x**2)/(2*x))]:
    rep("wrong " + nm, explicit(W, f))

# C) y = y1 + u gives Bernoulli: for general Riccati
p, q, r, y1, u = symbols('p q r y1 u')
y1f = Function('y1')(x); uf = Function('u')(x); pf, qf, rf = [Function(n)(x) for n in 'pqr']
# assume y1' = p + q y1 + r y1^2
res = diff(y1f + uf, x) - (pf + qf*(y1f + uf) + rf*(y1f + uf)**2)
res = res.subs(diff(y1f, x), pf + qf*y1f + rf*y1f**2)
print("C) u' =", simplify(-res + diff(uf, x)))

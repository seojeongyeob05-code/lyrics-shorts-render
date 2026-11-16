# 07강 2일차 검산: 삼각함수 특수해 리카티 y' = cos x - (tan x) y + y^2 / cos x
from sympy import symbols, Function, sin, cos, tan, simplify, diff

x, C = symbols('x C')
v = Function('v')(x)
f = lambda Y: cos(x) - tan(x) * Y + Y**2 / cos(x)
chk = lambda Y: simplify(diff(Y, x) - f(Y))

print("candidates:")
for nm, Y in [("sin x", sin(x)), ("cos x", cos(x)), ("tan x", tan(x)), ("1", 1 + 0 * x)]:
    print(f"  {nm:8}", "OK" if chk(Y) == 0 else "no")

Ys = sin(x) + 1 / v
print("v-equation (times -v^2 cos x):", simplify((diff(Ys, x) - f(Ys)) * (-v**2) * cos(x)))

for nm, Y in [("answer sin x + 1/(C cos x - sin x)", sin(x) + 1 / (C * cos(x) - sin(x))),
              ("wrong  sin x + 1/(C cos x + sin x)", sin(x) + 1 / (C * cos(x) + sin(x))),
              ("wrong  1/(C cos x - sin x)", 1 / (C * cos(x) - sin(x))),
              ("wrong  C cos x", C * cos(x))]:
    print(f"  {nm:38}", "OK (0)" if chk(Y) == 0 else "nonzero")

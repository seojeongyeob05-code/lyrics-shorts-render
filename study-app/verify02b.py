# 02강 2일차 검산: Level 2 대표 문제 2개. 정답은 식을 만족, 오답은 불만족.
from sympy import symbols, Function, sqrt, log, simplify, diff

x = symbols('x')
y = Function('y')(x)
yp = diff(y, x)


def implicit(F, rhs):
    return simplify(diff(F, x).subs(yp, rhs))


def report(name, F, rhs):
    v = implicit(F, rhs)
    print(f"  {name:55} -> {'OK (0)' if v == 0 else 'nonzero'}")


u = x + y
print("A) y' = sqrt(x + y):  u' = 1 + sqrt(u), t = sqrt(u)")
rhs = sqrt(x + y)
report("answer 2sqrt(u) - 2ln(1+sqrt(u)) - x", 2 * sqrt(u) - 2 * log(1 + sqrt(u)) - x, rhs)
report("wrong  2sqrt(u) - x", 2 * sqrt(u) - x, rhs)
report("wrong  2sqrt(u) + 2ln(1+sqrt(u)) - x", 2 * sqrt(u) + 2 * log(1 + sqrt(u)) - x, rhs)
report("wrong  sqrt(u) - ln(1+sqrt(u)) - x", sqrt(u) - log(1 + sqrt(u)) - x, rhs)

print("B) y' = (x + y + 1)/(x + y - 1): parallel lines, u = x + y")
rhs = (x + y + 1) / (x + y - 1)
report("answer y - x - ln|x+y|", y - x - log(x + y), rhs)
report("wrong  y - x + ln|x+y|", y - x + log(x + y), rhs)
report("wrong  y + x - ln|x+y|", y + x - log(x + y), rhs)
report("wrong  ln|x+y| - 2x", log(x + y) - 2 * x, rhs)

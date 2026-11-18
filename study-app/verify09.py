# 09강 검산: 치환 계수내림. 2계 ODE 는 y'' 까지 확인한다. 정답은 만족, 오답은 불만족.
from sympy import symbols, exp, log, tan, cos, sec, atan, simplify, diff, Rational

x, C1, C2 = symbols('x C1 C2')


def res(Y, F):
    """F(x, y, y', y'') = 0 의 잔차"""
    return simplify(F(Y, diff(Y, x), diff(Y, x, 2)))


def check(title, F, ans, wrongs):
    print(title)
    print(f"  answer {ans}: {'OK (0)' if res(ans, F) == 0 else 'NONZERO'}")
    for w in wrongs:
        print(f"  wrong  {w}: {'0 (!!)' if res(w, F) == 0 else 'nonzero'}")


check("x y'' + y' = 0", lambda y, p, q: x*q + p, C1*log(x) + C2, [C1*x + C2, C1*exp(x) + C2, C1*x**2 + C2])
check("y y'' = (y')^2", lambda y, p, q: y*q - p**2, C2*exp(C1*x), [C1*x + C2, C1*log(x) + C2, (C1*x + C2)**2])
check("y'' = y'", lambda y, p, q: q - p, C1*exp(x) + C2, [C1*exp(-x) + C2, C1*x + C2])
check("y'' = 1 + (y')^2", lambda y, p, q: q - 1 - p**2, log(sec(x + C1)) + C2,
      [tan(x + C1) + C2, log(cos(x + C1)) + C2, atan(x) + C1*x + C2])
check("x y'' + y' = x", lambda y, p, q: x*q + p - x, x**2/4 + C1*log(x) + C2,
      [x**2/2 + C1*log(x) + C2, x**2/4 + C1*x + C2, x**3/6 + C1*log(x) + C2])
check("y'' = (y')^2  (x, y 둘 다 없음)", lambda y, p, q: q - p**2, -log(x + C1) + C2,
      [log(x + C1) + C2, C1*exp(x) + C2, -1/(x + C1)])

print("IVP y'' = y', y(0)=1, y'(0)=2:")
for nm, Y in [("2e^x - 1", 2*exp(x) - 1), ("2e^x + 1", 2*exp(x) + 1), ("e^{2x}", exp(2*x)), ("e^x", exp(x))]:
    ok = res(Y, lambda y, p, q: q - p) == 0 and Y.subs(x, 0) == 1 and diff(Y, x).subs(x, 0) == 2
    print(f"  {nm:10} -> {'all OK' if ok else 'fails'}")

print("IVP x y'' + y' = 0, y(1)=2, y'(1)=3: C1 =", (diff(C1*log(x) + C2, x)).subs(x, 1), "-> C1 = 3, C2 =",
      (3*log(x) + C2).subs(x, 1), "= 2 -> C2 = 2")
Y = 3*log(x) + 2
print("  y = 3 ln x + 2 satisfies:", res(Y, lambda y, p, q: x*q + p) == 0, Y.subs(x, 1), diff(Y, x).subs(x, 1))

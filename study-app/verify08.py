# 08강 검산: 물탱크 A h' = -a sqrt(2 g h), h(0) = h0
from sympy import symbols, sqrt, simplify, diff, solve, Rational, nsimplify

t, A, a, g, h0, c = symbols('t A a g h0 c', positive=True)

k = (a / A) * sqrt(g / 2)
h = (sqrt(h0) - k * t)**2
# 해가 식을 만족하는지 (sqrt(h) = sqrt(h0) - k t > 0 인 구간)
lhs = A * diff(h, t)
rhs = -a * sqrt(2 * g) * (sqrt(h0) - k * t)  # sqrt(h) 를 양수 가지로
print("answer satisfies ODE:", simplify(lhs - rhs) == 0, "| h(0) =", simplify(h.subs(t, 0)))

wrongs = {
    "linear h0 - (a/A) sqrt(2g) t": h0 - (a / A) * sqrt(2 * g) * t,
    "missing 1/2: (sqrt h0 - (a/A) sqrt(2g) t)^2": (sqrt(h0) - (a / A) * sqrt(2 * g) * t)**2,
}
for nm, W in wrongs.items():
    rW = -a * sqrt(2 * g) * sqrt(W) if 'linear' in nm else -a * sqrt(2 * g) * (sqrt(h0) - (a / A) * sqrt(2 * g) * t)
    print(" wrong", nm, "satisfies:", simplify(A * diff(W, t) - rW) == 0)

T = solve(sqrt(h0) - k * t, t)[0]
print("empty time T =", simplify(T), "| equals (A/a) sqrt(2 h0 / g):", simplify(T - (A / a) * sqrt(2 * h0 / g)) == 0)
t_quarter = solve(sqrt(h0 / 4) - (sqrt(h0) - k * t), t)[0]
print("time to h0/4 over T:", simplify(t_quarter / T))
print("A doubled -> T ratio:", simplify(T.subs(A, 2 * A) / T))
print("numeric A=1, a=0.01, h0=5, g=10 -> T =", T.subs({A: 1, a: Rational(1, 100), h0: 5, g: 10}))
Tc = solve(sqrt(h0) - (a * c / A) * sqrt(g / 2) * t, t)[0]
print("with discharge coefficient c: T_c / T =", simplify(Tc / T))
# 그래프: h'' > 0 (아래로 볼록), h' < 0
print("h' :", simplify(diff(h, t)), "| h'' :", simplify(diff(h, t, 2)))

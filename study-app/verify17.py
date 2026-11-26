# 17강 검산: MS / MSD 시스템 my'' + cy' + ky = 0
from sympy import symbols, Function, dsolve, Eq, sqrt, simplify, pi, cos, sin, exp, diff, solve, Rational, roots

t = symbols('t', real=True)
m, c, k = symbols('m c k', positive=True)
y = Function('y')


def char_roots(mv, cv, kv):
    l = symbols('l')
    return roots(mv * l**2 + cv * l + kv, l)


print("omega0 m=2,k=18:", sqrt(Rational(18, 2)), "| T =", 2 * pi / sqrt(Rational(18, 2)))
print("period ratio when m -> 4m:", simplify((2 * pi * sqrt(4 * m / k)) / (2 * pi * sqrt(m / k))))
print("amplitude 3cos2t+4sin2t:", sqrt(3**2 + 4**2))
# 당겼다 놓기: y(0)=y0, y'(0)=0 -> y0 cos(w t)
y0 = symbols('y0')
sol = dsolve(Eq(2 * y(t).diff(t, 2) + 8 * y(t), 0), ics={y(0): y0, y(t).diff(t).subs(t, 0): 0})
print("released from rest:", sol)
print("critical c for m=1,k=4:", solve(Eq(c**2, 4 * 1 * 4), c))
print("roots m=1,c=2,k=5:", char_roots(1, 2, 5))
sol = dsolve(Eq(y(t).diff(t, 2) + 4 * y(t).diff(t) + 4 * y(t), 0))
print("critical m=1,c=4,k=4:", sol)
for cv in [5, 4, 2]:
    print(f"  m=1,c={cv},k=4 roots:", char_roots(1, cv, 4))
# 저감쇠 주기 T(m) = 4*pi*m/sqrt(4mk - c^2), c,k 고정
T = 4 * pi * m / sqrt(4 * m * k - c**2)
print("dT/dm = 0 at:", solve(Eq(diff(T, m), 0), m))
cv, kv = 2, 1  # 저감쇠 조건 m > c^2/(4k) = 1, 최소 m = c^2/(2k) = 2
for mv in [Rational(11, 10), Rational(3, 2), 2, 3, 5]:
    print(f"  T(m={mv}) =", float(T.subs({c: cv, k: kv, m: mv})))
# 중력 상쇄: m y'' = mg - k(s0 + y),  k s0 = mg
g, s0 = symbols('g s0', positive=True)
Y = Function('Y')(t)
rhs = (m * g - k * (s0 + Y)).subs(s0, m * g / k)
print("net force with ks0=mg:", simplify(rhs))
# 공진: y'' + 4y = cos 2t
print("resonance:", dsolve(Eq(y(t).diff(t, 2) + 4 * y(t), cos(2 * t))))
# 음의 감쇠 c=-1
print("c=-1 roots:", char_roots(1, -1, 4))

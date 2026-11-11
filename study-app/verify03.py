# 03강 검산: 완전성 판정과 해 u(x, y) = C.
# 해 확인: u_x = M, u_y = N 이면 u = C 가 M dx + N dy = 0 의 해. 오답은 그렇지 않아야 한다
# (u_x : u_y 비율이 M : N 과 다르면 다른 방정식의 해).
from sympy import symbols, sin, cos, log, atan, simplify, diff

x, y = symbols('x y', positive=True)


def exact(M, N):
    return simplify(diff(M, y) - diff(N, x)) == 0


def solves(u, M, N):
    # u = C 의 접선 방향이 M dx + N dy = 0 과 같은지: u_x N - u_y M == 0
    return simplify(diff(u, x) * N - diff(u, y) * M) == 0


def check(title, M, N, answer, wrongs):
    print(title, "| exact:", exact(M, N))
    print("   answer", answer, "->", "OK" if solves(answer, M, N) and simplify(diff(answer, x) - M) == 0 and simplify(diff(answer, y) - N) == 0 else "FAIL")
    for w in wrongs:
        print("   wrong ", w, "->", "solves (!!)" if solves(w, M, N) else "not a solution")


print("which is exact:")
for name, M, N in [("(2xy+3)dx + (x^2-1)dy", 2*x*y + 3, x**2 - 1), ("y dx - x dy", y, -x),
                   ("(x+y^2)dx + xy dy", x + y**2, x*y), ("sin y dx + sin x dy", sin(y), sin(x))]:
    print("  ", name, exact(M, N))

check("(2xy+3)dx + (x^2-1)dy", 2*x*y + 3, x**2 - 1, x**2*y + 3*x - y, [x**2*y + 3*x, x**2*y - y, 2*x*y + 3*x - y])
check("(y cos x + 2x)dx + (sin x + 1)dy", y*cos(x) + 2*x, sin(x) + 1, y*sin(x) + x**2 + y, [y*sin(x) + x**2, y*cos(x) + x**2 + y, y*sin(x) + 2*x + y])
check("sin x cos y dx + cos x sin y dy", sin(x)*cos(y), cos(x)*sin(y), -cos(x)*cos(y), [sin(x)*sin(y), cos(x) + cos(y), sin(x)*cos(y)])
check("(ln y + 1)dx + (x/y)dy", log(y) + 1, x/y, x*log(y) + x, [x*log(y), log(y) + x, x/y + x])
check("(2x+y)dx + (x+2y)dy", 2*x + y, x + 2*y, x**2 + x*y + y**2, [x**2 + 2*x*y + y**2, x**2 + y**2, x**2 - x*y + y**2])
print("   IVP y(1)=1 -> C =", (x**2 + x*y + y**2).subs({x: 1, y: 1}))
M = 2*x + y/(1 + x**2*y**2); N = x/(1 + x**2*y**2)
check("(2x + y/(1+x^2y^2))dx + x/(1+x^2y^2) dy", M, N, x**2 + atan(x*y), [x**2 + atan(y), x**2 + log(1 + x**2*y**2), x**2 + x*y])
k = symbols('k')
print("k for (3x^2+ky)dx + (2x+cos y)dy:", [kk for kk in [0, 1, 2, 3] if exact(3*x**2 + kk*y, 2*x + cos(y))])

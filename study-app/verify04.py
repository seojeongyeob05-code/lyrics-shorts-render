# 04강 검산: 적분인자 판정, mu, 해.
from sympy import symbols, exp, log, simplify, diff, integrate, Rational

x, y = symbols('x y', positive=True)


def exact(M, N):
    return simplify(diff(M, y) - diff(N, x)) == 0


def solves(u, M, N):
    return simplify(diff(u, x) * N - diff(u, y) * M) == 0


def show(title, M, N):
    rx = simplify((diff(M, y) - diff(N, x)) / N)
    ry = simplify((diff(N, x) - diff(M, y)) / M)
    print(f"{title}: exact={exact(M, N)}  (My-Nx)/N = {rx}  (Nx-My)/M = {ry}")
    return rx, ry


# 기존 문제: (x^2+y^2+x)dx + xy dy
M, N = x**2 + y**2 + x, x * y
rx, _ = show("(x^2+y^2+x)dx + xy dy", M, N)
mu = simplify(exp(integrate(rx, x)))
print("  mu =", mu, " exact after:", exact(mu * M, mu * N))
u = x**4 / 4 + x**2 * y**2 / 2 + x**3 / 3
print("  answer solves:", solves(u, M, N), "| wrong x^3/3+xy^2+x^2/2:", solves(x**3/3 + x*y**2 + x**2/2, M, N),
      "| wrong x^4+x^2y^2:", solves(x**4 + x**2*y**2, M, N), "| wrong x^2y^2/2:", solves(x**2*y**2/2, M, N))

# y dx - x dy: 적분인자 후보
M, N = y, -x
for name, m in [("1/y^2", 1/y**2), ("y^2", y**2), ("x+y", x + y), ("e^x", exp(x))]:
    print("  y dx - x dy  mu =", name, "->", exact(m * M, m * N))

# y dx + (2x - y e^y) dy : mu(y) = y
M, N = y, 2*x - y*exp(y)
_, ry = show("y dx + (2x - y e^y) dy", M, N)
print("  mu(y) =", simplify(exp(integrate(ry, y))))

# 2y dx + x dy
M, N = 2*y, x
rx, _ = show("2y dx + x dy", M, N)
print("  mu =", simplify(exp(integrate(rx, x))), " x^2 y solves:", solves(x**2*y, M, N), "| xy^2:", solves(x*y**2, M, N),
      "| x^2+y:", solves(x**2 + y, M, N), "| y - C x^2 (C=1):", solves(y - x**2, M, N))

# 경우 4 판단: (x + y^2)dx + (x^2 + y)dy
M, N = x + y**2, x**2 + y
show("(x + y^2)dx + (x^2 + y)dy  [case 4?]", M, N)

# y' = y/(x - x^2 y)  ->  y dx + (x^2 y - x) dy = 0
M, N = y, x**2*y - x
rx, _ = show("y dx + (x^2 y - x) dy", M, N)
mu = simplify(exp(integrate(rx, x)))
print("  mu =", mu, " exact after:", exact(mu * M, mu * N))
for name, u in [("answer y^2/2 - y/x", y**2/2 - y/x), ("wrong y^2/2 + y/x", y**2/2 + y/x), ("wrong y^2 - xy", y**2 - x*y), ("wrong y/x", y/x)]:
    print("  ", name, "->", solves(u, M, N))
# 같은 식을 y' 꼴로 썼을 때 우변 확인
print("  -M/N =", simplify(-M / N))
print("exp(-2 ln x) =", simplify(exp(-2*log(x))))

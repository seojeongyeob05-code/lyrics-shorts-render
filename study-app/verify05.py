# 05강 검산: 1계 선형 ODE. 정답은 식을 만족, 오답은 불만족.
from sympy import symbols, Function, exp, log, sin, cos, tan, cot, atan, simplify, diff, integrate, limit, oo

x, C = symbols('x C')
y = Function('y')(x)
yp = diff(y, x)


def explicit(Y, rhs_of):
    return simplify(diff(Y, x) - rhs_of(Y))


def rep(name, v):
    print(f"  {name:45} -> {'OK (0)' if v == 0 else 'nonzero'}")


print("mu checks:")
print("  y'+y/x: mu =", simplify(exp(integrate(1/x, x))))
print("  y'+cot(x) y: mu =", simplify(exp(integrate(cot(x), x))))
print("  xy'+2y=x^2 -> y'+(2/x)y: mu =", simplify(exp(integrate(2/x, x))), "| without dividing: e^{int 2} =", exp(integrate(2, x)))
print("  y'+tan(x) y: mu =", simplify(exp(integrate(tan(x), x))))

print("y' + y/x = x")
f = lambda Y: x - Y/x
rep("answer x^2/3 + C/x", explicit(x**2/3 + C/x, f))
for n, W in [("x^3/3 + C", x**3/3 + C), ("x^2 + Cx", x**2 + C*x), ("x^2/2 + C/x", x**2/2 + C/x)]:
    rep("wrong " + n, explicit(W, f))

print("y' + 2y = 4")
f = lambda Y: 4 - 2*Y
rep("answer 2 + Ce^{-2x}", explicit(2 + C*exp(-2*x), f))
for n, W in [("4 + Ce^{-2x}", 4 + C*exp(-2*x)), ("2 + Ce^{2x}", 2 + C*exp(2*x)), ("4x + C", 4*x + C)]:
    rep("wrong " + n, explicit(W, f))
print("  limit:", limit(2 + C*exp(-2*x), x, oo), "| IVP y(0)=5 -> C =", 5 - 2)

print("x y' + 2y = x^2")
f = lambda Y: (x**2 - 2*Y)/x
rep("answer x^2/4 + C/x^2", explicit(x**2/4 + C/x**2, f))

print("y' + tan(x) y = cos x")
f = lambda Y: cos(x) - tan(x)*Y
rep("answer (x + C) cos x", explicit((x + C)*cos(x), f))
for n, W in [("(x + C) sin x", (x + C)*sin(x)), ("x cos x + C", x*cos(x) + C), ("(x + C) sec x", (x + C)/cos(x))]:
    rep("wrong " + n, explicit(W, f))

print("y' + y = cos x")
f = lambda Y: cos(x) - Y
rep("answer (cos x + sin x)/2 + Ce^{-x}", explicit((cos(x) + sin(x))/2 + C*exp(-x), f))
for n, W in [("(sin x - cos x)/2 + Ce^{-x}", (sin(x) - cos(x))/2 + C*exp(-x)), ("sin x + Ce^{-x}", sin(x) + C*exp(-x)),
             ("(cos x + sin x)/2 + Ce^{x}", (cos(x) + sin(x))/2 + C*exp(x))]:
    rep("wrong " + n, explicit(W, f))

print("y' + y/(1+x^2) = e^{-arctan x}/(1+x^2)")
f = lambda Y: exp(-atan(x))/(1 + x**2) - Y/(1 + x**2)
rep("answer (arctan x + C) e^{-arctan x}", explicit((atan(x) + C)*exp(-atan(x)), f))
for n, W in [("(arctan x + C) e^{arctan x}", (atan(x) + C)*exp(atan(x))), ("arctan x + C", atan(x) + C),
             ("(x + C) e^{-arctan x}", (x + C)*exp(-atan(x)))]:
    rep("wrong " + n, explicit(W, f))

print("y' = y/(x + y^3)  (inverse: x as function of y)")
yy = symbols('yy')
X = Function('X')(yy)
# 해 F(x, y) = C 를 implicit 로: x = y^3/2 + C y  <=>  x/y - y^2/2 = C
Y = Function('Y')(x)
F_ok = x/Y - Y**2/2
rhs = Y/(x + Y**3)
chk = lambda F: simplify(diff(F, x).subs(diff(Y, x), rhs))
rep("answer x = y^3/2 + Cy", chk(F_ok))
for n, F in [("y = x^3/2 + Cx", Y/x - x**2/2), ("x = y^3 + Cy", x/Y - Y**2), ("x = y^2/2 + C", x - Y**2/2)]:
    rep("wrong " + n, chk(F))

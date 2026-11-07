# Check every 01강 answer: the stated solution satisfies the ODE, and every wrong option does not.
from sympy import symbols, Function, exp, tan, sin, sqrt, simplify, diff, Eq, solve, log

x, C, k = symbols('x C k')


def residual(y, rhs):
    return simplify(diff(y, x) - rhs(y))


cases = {
    "y'=ky": (lambda y: k * y, C * exp(k * x), [k * x + C, C * exp(x / k), exp(k * x) + C]),
    "y'=2xy": (lambda y: 2 * x * y, C * exp(x**2), [C * exp(2 * x), x**2 + C, C * exp(x**2 / 2)]),
    "y'=y e^x": (lambda y: y * exp(x), C * exp(exp(x)), [exp(exp(x)) + C, C * exp(x), exp(x) + C]),
    "y'=1-y": (lambda y: 1 - y, 1 + C * exp(-x), [1 + C * exp(x), C * exp(x) - 1, C * exp(-x) - 1]),
    "y'=1+y^2": (lambda y: 1 + y**2, tan(x + C), [tan(x) + C, C * exp(x) - 1]),
    "y'=sqrt(1-y^2)": (lambda y: sqrt(1 - y**2), sin(x + C), [sin(x) + C, C * exp(x)]),
    "y'=y(1-y)": (lambda y: y * (1 - y), C * exp(x) / (1 + C * exp(x)), [1 / (1 + C * exp(x)), C * exp(x), 1 - C * exp(-x)]),
    "y'=xy^2": (lambda y: x * y**2, -2 / (x**2 + C), [2 / (x**2 + C), -1 / (x**2 + C)]),
}
for name, (rhs, ans, wrongs) in cases.items():
    r = residual(ans, rhs)
    if name == "y'=sqrt(1-y^2)":
        # cos(x+C) = +sqrt(1 - sin^2) on the branch where cos > 0; check numerically there
        r = (diff(ans, x) - rhs(ans)).subs({C: 0, x: 0.3}).evalf()
    print(f"{name:16} answer residual = {r}")
    for w in wrongs:
        rw = simplify(diff(w, x) - rhs(w))
        print(f"{'':16}   wrong {w}: residual {'0 (!!)' if rw == 0 else 'nonzero'}")

# implicit: y' = x/y  ->  y^2 - x^2 = C ; differentiate implicitly
y = Function('y')(x)
print("y'=x/y implicit:", simplify(diff(y**2 - x**2, x).subs(diff(y, x), x / y)))
for w in [y**2 + x**2]:
    print("   wrong y^2+x^2:", simplify(diff(w, x).subs(diff(y, x), x / y)))
# IVP y'=3y, y(0)=2 -> 2e^{3x}
print("IVP:", simplify(diff(2 * exp(3 * x), x) - 3 * 2 * exp(3 * x)), (2 * exp(3 * x)).subs(x, 0))
# integral sign check
yy = symbols('yy')
from sympy import integrate
print("int 1/(1-y) =", integrate(1 / (1 - yy), yy))

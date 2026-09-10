"""Sample math operations module for coverage fixture."""


def add(a, b):
    return a + b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def uncovered_power(a, b):
    return a ** b

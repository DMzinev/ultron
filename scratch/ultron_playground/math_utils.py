# Ultron Playground Sample Module
import time

def add_elements(a, b):
    # Simple low complexity function
    return a + b

def complex_operation(x, y, op="add"):
    # Moderate complexity McCabe branch (Complexity: 3)
    if op == "add":
        return x + y
    elif op == "subtract":
        return x - y
    else:
        # Fallback loop
        result = 0
        for i in range(abs(int(x))):
            result += y
        return result

def highly_coupled_calculator(val1, val2, operation):
    # This calls add_elements and complex_operation, coupling them
    # Impact score will be high because of coupling and complexity
    print(f"Executing coupled calculator on {val1} and {val2} using {operation}")
    
    # We call these functions (coupling)
    step1 = add_elements(val1, 10)
    step2 = complex_operation(step1, val2, op=operation)
    
    return step2

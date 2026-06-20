import sys
import os
import json
import random

# Add root folder and ultron to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ultron")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "synapse_project", "synapse_mutator")))

import fuzz
import mutate

# Define 3 separate code blocks to mutate
samples = [
    {
        "name": "Tax Calculator (math_ops.py)",
        "code": """def add_tax(amount):
    return amount * 1.15
"""
    },
    {
        "name": "Formatter (target.py)",
        "code": """def process_data_and_format(value):
    temp = value * 2
    temp = temp + 5
    return f"Value is {temp}"
"""
    },
    {
        "name": "Interest Estimator (custom_math.py)",
        "code": """def estimate_interest(principal, rate):
    return principal * rate * 0.0825
"""
    }
]

print("=== Generation Method ===")
print("The input generation method is random selection from a predefined mixed-type pool")
print("(integers, floats, empty/non-empty strings, lists, dicts, booleans, and None),")
print("which is then padded to the required function argument count.")
print()

for idx, sample in enumerate(samples, 1):
    print(f"=== Mutant #{idx}: {sample['name']} ===")
    old_code = sample["code"]
    mutated_code, success = mutate.apply_mutation(old_code)
    
    print("--- Original Code ---")
    print(old_code.strip())
    print("--- Mutated Code ---")
    print(mutated_code.strip())
    
    # We intercept the fuzz generation to show the actual values
    funcs = fuzz.discover_functions_ast(old_code)
    fn = funcs[0]
    n_args = len(fn["args"])
    # Generate 5 sample inputs to display
    sample_inputs = []
    for _ in range(5):
        sample_inputs.append([random.choice(fuzz.generate_fuzz_values()) for _ in range(n_args)])
        
    print("--- Sample Fuzzed Inputs (5 of 40 runs) ---")
    for i, inp in enumerate(sample_inputs, 1):
        print(f"  Run {i}: {inp}")
        
    # Calculate CEST divergence
    divergence = fuzz.compute_cest_divergence(None, old_code, mutated_code, repo_path=os.getcwd())
    print(f"--- CEST Divergence Rate ---")
    print(f"Divergence: {divergence:.4f}")
    print("=" * 60)
    print()

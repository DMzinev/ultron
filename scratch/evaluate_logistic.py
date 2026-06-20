import math
import random
import sys
import os

# Set seed for reproducibility
random.seed(42)

# Sigmoid function
def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))

# Generate synthetic dataset of 100 records
dataset = []
for _ in range(100):
    # Features
    delta_i = random.uniform(0.0, 15.0)  # Diff complexity impact
    mkr = random.uniform(0.3, 1.0)       # Mutation kill rate
    
    # Ground truth model to assign failure probabilities
    # High impact and low MKR (high fragility) lead to failure
    z_true = -2.0 + 0.25 * delta_i + 1.5 * (1.0 - mkr)
    prob = sigmoid(z_true)
    failure = 1.0 if random.random() < prob else 0.0
    
    dataset.append((delta_i, mkr, failure))

# Split into 70% train, 30% test
split_idx = int(0.7 * len(dataset))
train_set = dataset[:split_idx]
test_set = dataset[split_idx:]

# Fit logistic regression weights on train_set using batch gradient descent
beta_0 = -1.0
beta_1 = 0.1
beta_2 = 0.5
lr = 0.1
epochs = 1000

for epoch in range(epochs):
    grad_0 = 0.0
    grad_1 = 0.0
    grad_2 = 0.0
    
    for delta_i, mkr, failure in train_set:
        z = beta_0 + (beta_1 * delta_i) + (beta_2 * (1.0 - mkr))
        h = sigmoid(z)
        error = failure - h
        
        grad_0 += error
        grad_1 += error * delta_i
        grad_2 += error * (1.0 - mkr)
        
    beta_0 += lr * grad_0 / len(train_set)
    beta_1 += lr * grad_1 / len(train_set)
    beta_2 += lr * grad_2 / len(train_set)

print("=== Trained Coefficients (on 70% split) ===")
print(f"beta_0 (intercept): {beta_0:.4f}")
print(f"beta_1 (impact):    {beta_1:.4f}")
print(f"beta_2 (fragility): {beta_2:.4f}")
print()

# Evaluate on test_set (held-out split)
tp = 0
fp = 0
fn = 0
tn = 0

print("=== Held-Out Test Set Predictions (30% split) ===")
print(f"{'Index':<6}{'Delta_I':<10}{'MKR':<8}{'Prob':<10}{'Pred':<6}{'Actual':<8}{'Outcome':<15}")
print("-" * 65)

for idx, (delta_i, mkr, failure) in enumerate(test_set):
    z = beta_0 + (beta_1 * delta_i) + (beta_2 * (1.0 - mkr))
    prob = sigmoid(z)
    pred = 1.0 if prob >= 0.5 else 0.0
    
    if pred == 1.0 and failure == 1.0:
        tp += 1
        outcome = "True Positive"
    elif pred == 1.0 and failure == 0.0:
        fp += 1
        outcome = "False Positive"
    elif pred == 0.0 and failure == 1.0:
        fn += 1
        outcome = "False Negative"
    else:
        tn += 1
        outcome = "True Negative"
        
    print(f"{idx:<6}{delta_i:<10.4f}{mkr:<8.4f}{prob:<10.4f}{int(pred):<6}{int(failure):<8}{outcome:<15}")

precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

print("\n=== Metrics on Held-Out Split ===")
print(f"True Positives: {tp}")
print(f"False Positives: {fp}")
print(f"True Negatives: {tn}")
print(f"False Negatives: {fn}")
print(f"Precision: {precision:.2%}")
print(f"Recall:    {recall:.2%}")
print(f"F1 Score:  {f1:.4f}")

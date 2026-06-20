import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ultron"))
import classifier

repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_anomaly_dir"))
names, probs = classifier.build_models(repo, exclude_file=os.path.join(repo, "target_anomaly.py"))
print("Defined Names:", sorted(list(names)))
print("Transition Probs:", probs)

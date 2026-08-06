"""Analyze and check command handlers."""
def handle_analyze(args):
    path = getattr(args, "path", ".")
    print(f"Running analysis over path: {path}")

def handle_check(args):
    print("Running compliance check...")

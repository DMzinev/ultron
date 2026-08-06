"""Dashboard command handler."""
def handle_dashboard(args):
    port = getattr(args, "port", 8000)
    print(f"Starting dashboard server on port {port}")

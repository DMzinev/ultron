"""Init command handler."""
def handle_init(args):
    print(f"Initialized Ultron repository in {args.path if hasattr(args, 'path') else '.'}")

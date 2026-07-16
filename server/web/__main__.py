"""``python -m server.web`` — Korean chat WebSocket server entry point."""

from server.web.serve import main

if __name__ == "__main__":
    raise SystemExit(main())

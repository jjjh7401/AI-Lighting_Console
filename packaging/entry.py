"""PyInstaller frozen entrypoint for the GrandMA3 Copilot packaged app (M6).

The packaged (frozen) app is NOT launched via ``python -m server.web`` — a frozen
bundle runs a single top-level script. This tiny entrypoint is that script: it
boots the production server through :func:`server.web.serve.main`, the same
``main`` the dev ``python -m server.web`` invocation calls.

Keeping the entrypoint separate (rather than pointing PyInstaller at
``server/web/__main__.py``) gives the ``.spec`` a stable, unambiguous script
path and lets ``multiprocessing.freeze_support`` run first (a no-op unless a
spawned child process is created, but the recommended frozen-app guard).
"""

from __future__ import annotations

import multiprocessing
import sys

from server.web.serve import main

if __name__ == "__main__":
    # Frozen-app guard: harmless when no multiprocessing child is spawned; must be
    # the first statement in the frozen entrypoint if one ever is.
    multiprocessing.freeze_support()
    sys.exit(main())

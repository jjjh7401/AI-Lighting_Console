"""Look library — the choreography vocabulary layer (SPEC-COPILOT-LOOKLIB-001).

Pure data + pure functions. This package never touches the console: it holds no
OSC surface, imports no transport, and produces no side effects. Instantiation
(the only path that reaches a console) is built on top of it in M4 and runs
through the existing ``run_commands`` -> ``gate.screen()`` chokepoint.
"""

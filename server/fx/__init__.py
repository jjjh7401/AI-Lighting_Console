"""FX library — the time-axis (effect) vocabulary layer (SPEC-COPILOT-FXLIB-001).

The sister package of ``server/looks/``: where a look is one stage picture, an
fx is one movement pattern over time — which attribute walks between which step
values, at which phase spread, at which speed, over which MAtricks division.

Pure data + pure functions. This package never touches the console: it holds no
OSC surface, imports no transport, and produces no side effects. Instantiation
(the only path that reaches a console) is built on top of it in M4 and runs
through the existing ``run_commands`` -> ``gate.screen()`` chokepoint
(REQ-FXLIB-017).
"""

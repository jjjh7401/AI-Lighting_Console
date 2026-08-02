"""Scene compiler — look + fx + timing composed into ONE cue (SPEC-COPILOT-SCENE-001).

Stage 2 of the intent -> memory pipeline. ``server/looks/`` owns the still-frame
vocabulary and ``server/fx/`` owns the time-axis vocabulary; both are stage 1,
and both are PRESERVE here (plan.md §A.5 — read-only imports). This package
composes their entries into a single stored cue: look values first, the fx step
run on top, then the timing that names where it lands.

Pure data + pure functions. This package never touches the console: it holds no
OSC surface, imports no transport and imports no gate surface (REQ-SCENE-019).
The one path that reaches a console is the ``compile_scene`` tool handler, which
is a caller of the existing ``run_commands`` -> ``gate.screen()`` chokepoint.
"""

"""Lua plugin deployment gate (M7 — REQ-MVP-019/027).

Pure policy package: pcall compile harness (:mod:`server.deploy.compile`),
best-effort destructive ``Cmd()`` scan (:mod:`server.deploy.scan`), human
review types (:mod:`server.deploy.review`), and the deny-by-default pipeline
(:mod:`server.deploy.pipeline`). Console-bound sends stay behind the safety
gate's deploy surface (REQ-MVP-029) — nothing in this package imports the
OSC bridge.
"""

"""Safety gate package (Milestone M4) — the single chokepoint toward the console.

Every command bound for the console passes the 3-stage gate pipeline
(① grammar validator → ② risk classification → ③ human approval for risky
commands) plus the live-lock, backup, and health checks (REQ-MVP-011~018,
026~036). This package is the ONLY production package allowed to import the
OSC send surface (``server.bridge``) — the AC-MVP-019 import-boundary
architecture test enforces that invariant.
"""

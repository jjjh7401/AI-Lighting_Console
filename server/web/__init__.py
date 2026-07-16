"""Korean chat web layer (M5) — FastAPI + WebSocket server for the copilot.

Everything console-bound goes through the M4 safety gate: this package NEVER
imports the OSC send surface (``server.bridge`` / ``pythonosc``) — the
AC-MVP-019 import-boundary architecture test pins that contract. Production
console-stack composition is gate-owned (``server.safety.bootstrap``).
"""

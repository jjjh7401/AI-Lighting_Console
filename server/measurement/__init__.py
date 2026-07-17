"""Measurement harness (M6) — grammar error-rate + round-trip corpus runner.

Offline (mock) mode drives the acceptance measurement machinery end to end
with a deterministic scripted provider and an in-memory console — no LLM API
call, no network, no credentials. Live mode (M6b) reuses the SAME corpus and
rules against a real provider + console.
"""

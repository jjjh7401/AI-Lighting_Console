"""Pre-show checklist (SPEC-COPILOT-PRESHOW-001).

Runs the standard pre-performance checklist in one pass: OSC round-trip
liveness, sequence/executor presence, preset (look) library integrity, and the
project's known field pitfalls (stale socket, OSC settings row, feedback port
drift). Every check degrades to ``skip`` — never a silent ``pass`` — when the
evidence it needs is unavailable, per the project's
"no unobserved-claim" verification-claim-integrity invariant.

Public surface: :func:`server.preshow.runner.run_preshow_checklist` and the
report/result types in :mod:`server.preshow.models`.
"""

from __future__ import annotations

from server.preshow.models import CheckResult, PreshowReport
from server.preshow.runner import run_preshow_checklist

__all__ = ["CheckResult", "PreshowReport", "run_preshow_checklist"]

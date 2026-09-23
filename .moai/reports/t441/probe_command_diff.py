"""t441 — prepare_songcue 가 인터뷰 기록 유무에 따라 내보내는 명령 diff.

실행: `uv run python -m .moai.reports.t441.probe_command_diff` 가 아니라
저장소 루트에서 `uv run python .moai/reports/t441/probe_command_diff.py`.
"""

import importlib
import sys

sys.path.insert(0, ".")
_suite = importlib.import_module("server.tests.test_chorus_color_two_paths_t441")

wiring = _suite.TestToolsetWiring()
out: dict[str, list[dict[str, str]]] = {}
for label, port in (
    ("none", None),
    ("modulate", _suite._RecordsPort(_suite._records("modulate"))),
):
    registry = wiring._registry(interview_records=port) if port else wiring._registry()
    _execution, payload = wiring._dispatch(registry)
    out[label] = payload["commands"]
    print(label, "commands", len(out[label]))
diff = [(a, b) for a, b in zip(out["none"], out["modulate"], strict=True) if a != b]
print("differing commands:", len(diff))
for a, b in diff:
    print(" -", a["command"])
    print(" +", b["command"])

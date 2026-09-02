"""t237 — dedupe 면제가 Clear 를 실제로 살리는지. 콘솔 접촉 0."""

from server.orchestrator.tools import _is_programmer_state

for c in [
    "Clear",
    "clear",
    "ClearAll",
    "Clear Clear",
    "Fixture 501",
    "Attribute 'Zoom' At 45",
    "Off Fixture 501",
    "Store Preset 4.1",
]:
    print(f"  {c!r:28} programmer_state={_is_programmer_state(c)}")

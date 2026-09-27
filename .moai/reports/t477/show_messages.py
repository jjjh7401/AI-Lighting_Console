"""판정서 §0 문면 확인 — 가짜 콘솔(t469 캡처)로 반영을 돌려 메시지와 프리셋 줄을 찍는다.

uv run python .moai/reports/t477/show_messages.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from server.tests.test_preset_name_resolve_t477 import _apply, _captured_pools  # noqa: E402

for fields in ({"phaser": "Breathe Soft"}, {"position": "POS05", "phaser": "DIM-BREATHE"}):
    event, console = _apply(Path(tempfile.mkdtemp()), _captured_pools(), **fields)
    print("##", fields)
    print(event["text"])
    print([line for line in console.executed if "Preset" in line])

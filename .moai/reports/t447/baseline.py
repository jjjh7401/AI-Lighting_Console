"""t447 — 8곡 게이트 기준선 + 표 바이트 지문 + Outro 없는 변형.

실행: uv run python .moai/reports/t447/baseline.py
"""

import copy
import dataclasses
import hashlib
import json
from collections import Counter
from pathlib import Path

from server.concept.gates import build_song, evaluate_song

songs = [
    s
    for s in json.loads(
        Path("server/tests/fixtures/pilot_baseline.json").read_text(encoding="utf-8")
    )
    if "error" not in s
]


def _canonical(value):
    """frozenset 은 실행마다 반복 순서가 달라(해시 무작위화) repr 지문이
    흔들린다 — 정렬된 목록으로 바꿔 결정적인 JSON 으로 만든다."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _canonical(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(_canonical(v) for v in value)
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


tally: Counter[str] = Counter()
for song in songs:
    results = evaluate_song(song)
    for result in results.values():
        tally["PASS" if result.passed is True else "FAIL" if result.passed is False else "n/a"] += 1
    build = build_song(song)
    table = json.dumps(_canonical([build.table, build.rows]), sort_keys=True, ensure_ascii=False)
    print(song["song"], "table", hashlib.sha256(table.encode()).hexdigest()[:12])
print("8곡 합계", dict(tally))

for song in songs:
    trimmed = copy.deepcopy(song)
    trimmed["sections"] = trimmed["sections"][:-1]
    try:
        g9 = next(v for k, v in evaluate_song(trimmed).items() if k.startswith("G9"))
        print(
            "no-last", song["song"], trimmed["sections"][-1]["baseline_name"], g9.passed, g9.detail
        )
    except Exception as exc:  # noqa: BLE001 — 재현 기록용
        print(
            "no-last",
            song["song"],
            trimmed["sections"][-1]["baseline_name"],
            "EXC",
            type(exc).__name__,
        )

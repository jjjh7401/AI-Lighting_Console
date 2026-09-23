"""t452 — 수정이 기존 8곡(pilot_baseline.json)의 판정을 안 바꾸는지.

수정 전 규칙(마지막 시퀀스 행)과 수정 후 규칙(마지막 cue_only 아닌 행)이
고르는 행이 같으면 두 경로의 입력이 바이트 동일하다 — 곡마다 두 행
번호를 나란히 찍고, 게이트 판정 전체(detail 포함)를 함께 남긴다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from server.concept.gates import (  # noqa: E402
    _RELEASE_REF_BASE_NAME,
    GATE_NAMES,
    build_song,
    evaluate_song,
)

songs = [
    s
    for s in json.loads(Path("server/tests/fixtures/pilot_baseline.json").read_text("utf-8"))
    if "error" not in s
]
same = 0
for song in songs:
    rows = build_song(song).rows
    seq_idx = [i for i, row in enumerate(rows) if row.get("kind") != "safety"]
    old_owner = seq_idx[-1]
    new_owner = next(
        i for i, row in enumerate(rows) if row.get("base_name") == _RELEASE_REF_BASE_NAME
    )
    same += old_owner == new_owner
    result = evaluate_song(song)
    marks = " ".join(f"{name.split(' ')[0]}={result[name].passed}" for name in GATE_NAMES)
    last_tracking = rows[old_owner].get("tracking")
    print(
        f"{song['song']}: old_owner={old_owner} new_owner={new_owner} last_tracking={last_tracking}"
    )
    print(f"  {marks}")
    for name in GATE_NAMES:
        print(f"    {name}: {result[name].detail}")
print(f"\n같은 행을 고른 곡: {same}/{len(songs)}")

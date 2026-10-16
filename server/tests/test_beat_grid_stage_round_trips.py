"""박자 배치 무대 판독의 콘솔 왕복 수 — LOVE ATTACK 실측 규모의 가짜 콘솔 (카드 apply-latency).

실기에서 박자 배치에 들어갈 때 무대 읽기가 수십 초 걸렸다. 콘솔 왕복 한 번의 값은 기기·
경로마다 다르므로 여기서는 **질의 수**만 고정한다(시간 ≈ 질의 수 × 왕복 한 번). 실기 접촉 0 —
``FakeConsole`` 만 쓴다.

목표 모양: 장비마다 질의 한 번(좌표와 SUBFIXTUREINDEX 를 한 묶음으로), 그룹마다 창 수만큼.
"""

from __future__ import annotations

import math

from server.design.beat_grid_stage import read_beat_grid_stage

from .test_beat_grid_stage import FIXTURES, GROUPS, FakeConsole

#: LOVE ATTACK 기본 격자의 트랙 — (트랙 이름, 콘솔 그룹 번호, 소속 장비 수).
TRACKS = (
    ("FOH", 3, 8),
    ("WASH-ALL", 10, 20),
    ("BACK", 4, 8),
    ("SIDE-ALL", 7, 4),
    ("MOVER-U", 11, 4),
    ("MOVER-D", 12, 4),
    ("BLIND", 14, 4),
    ("STROBE", 15, 4),
)
#: 실기 무대 규모(장비 80대).
FIXTURE_COUNT = 80
#: SELECTIONDATA 한 창의 항목 수 — 가정이다(실기 응답 한도에 따라 다르다).
WINDOW = 8


def _rig() -> FakeConsole:
    fixtures = [
        {
            "slot": i + 1,
            "fid": 100 + i,
            "name": f"Fixture {i + 1}",
            "x": float(i % 9),
            "y": float(i % 5),
            "z": 2.0,
            "sf": 1000 + i * 2,
        }
        for i in range(FIXTURE_COUNT)
    ]
    groups: dict[int, tuple[str, list[int]]] = {}
    cursor = 0
    for name, number, members in TRACKS:
        sfs = [fixtures[(cursor + k) % FIXTURE_COUNT]["sf"] for k in range(members)]
        groups[number] = (name, sfs)
        cursor += members
    return FakeConsole(fixtures=fixtures, groups=groups, window=WINDOW)


def _breakdown(fake: FakeConsole) -> dict[str, int]:
    counts = {
        "listing": 0,
        "groups_listing": 0,
        "fixture_props": 0,
        "subfixture": 0,
        "selection": 0,
    }
    for call in fake.calls:
        kind = call[0]
        if kind == "state":
            counts["listing" if call[1] == FIXTURES else "groups_listing"] += 1
        elif kind == "props":
            path, names = call[1], call[2]
            if path.startswith(GROUPS + "/"):
                counts["selection"] += 1
            elif tuple(names) == ("SUBFIXTUREINDEX",):
                counts["subfixture"] += 1
            else:
                counts["fixture_props"] += 1
    return counts


def test_stage_read_round_trips_at_show_scale() -> None:
    fake = _rig()
    read_beat_grid_stage(
        fake,
        fixtures_path=FIXTURES,
        groups_path=GROUPS,
        track_names=[name for name, _, _ in TRACKS],
    )
    counts = _breakdown(fake)
    total = sum(counts.values())
    print(f"\n[stage round trips] {counts} total={total}")

    selection_expected = sum(math.ceil(members / WINDOW) for _, _, members in TRACKS)
    # 장비마다 질의 한 번: 좌표·SUBFIXTUREINDEX 를 한 묶음으로 받는다(따로 두 번 묻지 않는다).
    assert counts["subfixture"] == 0
    assert counts["fixture_props"] == FIXTURE_COUNT
    assert counts["selection"] == selection_expected
    assert total == 2 + FIXTURE_COUNT + selection_expected

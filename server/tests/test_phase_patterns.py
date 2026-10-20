"""장비별 위상 디머 효과 생성기(``server.fx.phase_patterns``).

정답지는 감독이 LOVE ATTACK 손 연출로 콘솔에 실제로 보낸 명령이다(감사 기록 2026-10-19,
``Store Preset 22.21~22.43 … /Selective``). 그 리그의 좌표는 시험에 없어서, 같은 모양의 좌표
(BACK 한 줄 12대, WASH 위아래 두 줄 10열, SIDE 좌우 기둥 높이 세 단)를 지어 넣고 감독이 적은
위상이 그대로 나오는지 본다.
"""

from __future__ import annotations

import pytest

from server.fx.phase_patterns import (
    PHASE_LAYOUTS,
    PhaseEffect,
    PhasePatternError,
    fixture_phases,
    phase_effect_commands,
)
from server.spatial.schema import SpatialFixture


def _fixture(fid: int, x: float, z: float = 5.0, y: float = 0.0) -> SpatialFixture:
    return SpatialFixture(fid=fid, name=f"F{fid}", x=x, y=y, z=z)


#: BACK — 무대 뒤 한 줄 12대(왼쪽부터 201~212).
BACK = [_fixture(201 + i, -5.5 + i) for i in range(12)]
#: WASH — 위 줄(WU 401~410, 높이 6)과 아래 줄(WD 421~430, 높이 4)이 같은 10열.
WASH = [_fixture(401 + i, -4.5 + i, z=6.0) for i in range(10)] + [
    _fixture(421 + i, -4.5 + i, z=4.0) for i in range(10)
]
#: SIDE — 왼쪽 기둥(301~306)·오른쪽 기둥(311~316), 기둥마다 높이 1·2·3 이 두 번.
SIDE = [_fixture(301 + i, -8.0, z=1.0 + i % 3) for i in range(6)] + [
    _fixture(311 + i, 8.0, z=1.0 + i % 3) for i in range(6)
]


def _by_phase(phases: dict[int, int]) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = {}
    for fid, phase in sorted(phases.items()):
        grouped.setdefault(phase, []).append(fid)
    return grouped


# -- 감독 프리셋의 위상이 그대로 나온다 ------------------------------------------------------


def test_order_is_the_directors_left_to_right_back_chase() -> None:
    # 22.21 LA BK L2R: 201~212 에 0·30·…·330. 22.22 R2L 은 거꾸로.
    assert fixture_phases(BACK, "order") == {201 + i: 30 * i for i in range(12)}
    assert fixture_phases(BACK, "order", reverse=True) == {212 - i: 30 * i for i in range(12)}


def test_odd_even_is_the_directors_back_odd_even() -> None:
    # 22.25 LA BK ODDEVEN: 201·203·…·211 은 0, 202·…·212 는 180.
    assert _by_phase(fixture_phases(BACK, "odd_even")) == {
        0: list(range(201, 213, 2)),
        180: list(range(202, 213, 2)),
    }


def test_wings_is_the_directors_outside_in_and_inside_out() -> None:
    # 22.23 LA BK OUTIN: 바깥 쌍 201+212 가 0, 그다음 쌍마다 60. 22.24 INOUT 은 안쪽 쌍이 0.
    out_in = _by_phase(fixture_phases(BACK, "wings"))
    assert out_in == {60 * k: [201 + k, 212 - k] for k in range(6)}
    in_out = _by_phase(fixture_phases(BACK, "wings", reverse=True))
    assert in_out == {60 * k: [206 - k, 207 + k] for k in range(6)}


def test_wash_columns_rows_and_wings_match_the_directors_wash_presets() -> None:
    # 22.31 LA WS L2R: 같은 열의 위·아래 장비가 같은 위상, 열마다 36.
    assert _by_phase(fixture_phases(WASH, "order")) == {
        36 * i: [401 + i, 421 + i] for i in range(10)
    }
    # 22.32 LA WS UPDOWN: 위 줄 0, 아래 줄 180.
    assert _by_phase(fixture_phases(WASH, "rows")) == {
        0: list(range(401, 411)),
        180: list(range(421, 431)),
    }
    # 22.34 LA WS OUTIN: 바깥 열부터 0·72·144·216·288.
    assert sorted(_by_phase(fixture_phases(WASH, "wings"))) == [0, 72, 144, 216, 288]
    assert _by_phase(fixture_phases(WASH, "wings"))[0] == [401, 410, 421, 430]


def test_height_is_the_directors_side_uprise() -> None:
    # 22.27 LA SD UPRISE: 기둥마다 높이 세 단 — 301·304·311·314 가 0, 한 단 위마다 120.
    assert _by_phase(fixture_phases(SIDE, "height")) == {
        0: [301, 304, 311, 314],
        120: [302, 305, 312, 315],
        240: [303, 306, 313, 316],
    }


def test_the_back_left_to_right_bundle_is_the_directors_command_list() -> None:
    # 감독이 보낸 22.21 묶음(감사 기록 12:52:11 UTC)과 한 줄씩 같다.
    # 번호·이름·스피드 마스터만 넘긴다.
    sent = (
        ["ChangeDestination Root", "ClearAll", "Fixture 201 Thru 212"]
        + ["Attribute 'Dimmer' At 100", "Step 2", "Attribute 'Dimmer' At 0"]
        + [
            line
            for i in range(12)
            for line in (f"Fixture {201 + i}", f"Attribute 'Dimmer' At Phase {30 * i}")
        ]
        + ["Fixture 201 Thru 212", "Attribute 'Dimmer' At Width 30"]
        + ["Attribute 'Dimmer' At Measure 2", "Attribute 'Dimmer' At SpeedMaster 15"]
        + ["Store Preset 22.21 'LA BK L2R' /Selective", "ClearAll"]
    )
    made = phase_effect_commands(
        BACK,
        PhaseEffect("order", period_beats=2, width=30),
        preset_pool=22,
        preset_slot=21,
        label="LA BK L2R",
        speed_master=15,
    )
    assert list(made) == sent


def test_fixtures_sharing_a_phase_are_selected_together() -> None:
    made = phase_effect_commands(
        BACK,
        PhaseEffect("wings", period_beats=4, width=40),
        preset_pool=22,
        preset_slot=90,
        label="LDBEAT TEST",
        speed_master=15,
    )
    assert "Fixture 201 + 212" in made
    assert "Attribute 'Dimmer' At Measure 4" in made
    assert made[-2] == "Store Preset 22.90 'LDBEAT TEST' /Selective"


# -- 번호를 코드에 두지 않는다 --------------------------------------------------------------


def test_any_fixture_numbers_give_the_same_shape() -> None:
    # 다른 리그(장비 번호 1001~1012, 좌표는 오른쪽에서 왼쪽으로 번호가 늘어남)에서도 자리로 정한다.
    other = [_fixture(1001 + i, 5.5 - i) for i in range(12)]
    assert fixture_phases(other, "order") == {1012 - i: 30 * i for i in range(12)}


@pytest.mark.parametrize("layout", PHASE_LAYOUTS)
def test_every_layout_gives_at_least_two_phases_on_a_wash_grid(layout: str) -> None:
    rig = WASH if layout != "height" else SIDE
    assert len(set(fixture_phases(rig, layout).values())) >= 2


# -- 만들 수 없는 것은 거절한다 ---------------------------------------------------------------


def test_rows_on_a_flat_rig_are_refused() -> None:
    with pytest.raises(PhasePatternError, match="단이 하나"):
        fixture_phases(BACK, "rows")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"layout": "zigzag", "period_beats": 2, "width": 30}, "모르는 위상 배치"),
        ({"layout": "order", "period_beats": 3, "width": 30}, "1·2·4·8박"),
        ({"layout": "order", "period_beats": True, "width": 30}, "1·2·4·8박"),
        ({"layout": "order", "period_beats": 2, "width": 0}, "1~100"),
        ({"layout": "order", "period_beats": 2, "width": 101}, "1~100"),
    ],
)
def test_a_bad_effect_is_refused(kwargs: dict, match: str) -> None:
    with pytest.raises(PhasePatternError, match=match):
        PhaseEffect(**kwargs)


def test_bad_inputs_are_refused() -> None:
    effect = PhaseEffect("order", period_beats=2, width=30)
    with pytest.raises(PhasePatternError, match="둘 이상"):
        fixture_phases(BACK[:1], "order")
    with pytest.raises(PhasePatternError, match="같은 장비 번호"):
        fixture_phases([BACK[0], BACK[0]], "order")
    with pytest.raises(PhasePatternError, match="영문"):
        phase_effect_commands(
            BACK, effect, preset_pool=22, preset_slot=90, label="백 체이스", speed_master=15
        )
    with pytest.raises(PhasePatternError, match="1 이상"):
        phase_effect_commands(
            BACK, effect, preset_pool=22, preset_slot=0, label="LDBEAT TEST", speed_master=15
        )

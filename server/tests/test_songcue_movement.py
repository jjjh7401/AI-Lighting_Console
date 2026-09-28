"""t357 — 움직임을 콘솔로 보낸다: 룩의 `MovementSpec` → fx 페이저 → 곡 큐 번들.

정본은 `docs/proposals/song-structure-lighting-standard.md` §6.2(세 층) · §6.4(움직임 속도
· 관객 눈 하드룰) · §12 항목 1(고칠 것).

**고치기 전에 실측한 것**(2026-09-11, main `28a0dc1`):
`grep -rn "server.fx" server/looks server/design` → 0건. 무빙 페이저는
`server/fx/library/movement.yaml` 에 실재하고 `Look.movement` 필드도 선언돼 있는데 곡→큐
경로가 fx 계층을 부르지 않으므로, 룩에 움직임을 적으면 **조용히 버려졌다**.

**이 파일이 재지 않는 것**도 적는다.

* **콘솔에서의 효과.** 저장된 페이저 큐는 빈 큐와 구별되지 않고 `Phase`/`Speed` 는 되읽히지
  않는다(`server/fx/instantiate.py` 머리의 @MX:WARN, M0 실측). 그러므로 여기서 재는 것은
  **명령 문면**이고, 무대에서 무엇이 움직이는지는 실기 회차의 몫이다.
* **정적 값과 페이저를 한 캡처에 섞는 것.** 값 라인 뒤에 스텝 런을 두는 순서가 이 카드의
  유일한 미실측 가정이다(`songcue.py` `_section_bundle` 의 주석).
* **출하 라이브러리.** 지금 출하되는 룩 중 movement 를 선언한 것은 **하나도 없다** —
  `test_looks_library.py` 의 `FORBIDDEN_ATTRIBUTE_TOKENS` 가 자산 **원문**에서 `Pan`/`Tilt`
  를 금지하는 spec.md §D 범위 경계이기 때문이다. 그 경계를 옮기는 것은 LOOKLIB 쪽 결정이고
  이 카드에서 하지 않는다. 그래서 여기의 룩은 전부 시험 자료다.
"""

from __future__ import annotations

import pytest

from server.looks.movement import (
    EYE_DWELL_LIMIT_SECONDS,
    MOVEMENT_FAST,
    MOVEMENT_MID,
    MOVEMENT_SLOW,
    MOVEMENT_STILL,
    SPEED_FLOOR_BPM,
    SPEED_OUT_OF_BAND,
    MovementError,
    band_for_dynamics,
    band_speed_range,
    plan_movement,
)
from server.looks.schema import AttributeValue, Look, MovementSpec


class TestTheBandComesFromSectionIntent:
    """정본 §6.4 — 느림 = 빌드·앰비언스, 중속 = 그루브, 빠름 = **드롭 전용**."""

    def test_each_dynamics_level_routes_to_the_documented_band(self):
        assert [band_for_dynamics(level) for level in (1, 2, 3, 4, 5)] == [
            MOVEMENT_STILL,
            MOVEMENT_SLOW,
            MOVEMENT_SLOW,
            MOVEMENT_MID,
            MOVEMENT_FAST,
        ]

    def test_fast_is_the_drop_alone(self):
        """「빠름 = 드롭 전용」의 대우 — D5 아래 어느 세기도 빠름이 아니다."""
        assert [
            level for level in (1, 2, 3, 4, 5) if band_for_dynamics(level) == MOVEMENT_FAST
        ] == [5]

    def test_the_bands_do_not_overlap_and_rise(self):
        slow, mid, fast = (
            band_speed_range(b) for b in (MOVEMENT_SLOW, MOVEMENT_MID, MOVEMENT_FAST)
        )
        assert slow[1] == mid[0]
        assert mid[1] == fast[0]
        assert slow[0] < mid[0] < fast[0]

    def test_a_drop_band_look_is_faster_than_a_build_band_look(self):
        """카드가 요구한 대조 — 드롭 대역이 빌드 대역보다 빠르다."""
        build = plan_movement(_moving_look("build", dynamics=3), band=MOVEMENT_SLOW)
        drop = plan_movement(_moving_look("drop", dynamics=5), band=MOVEMENT_FAST)

        assert build is not None and drop is not None
        assert build.speed < drop.speed
        assert (build.speed, drop.speed) == (SPEED_FLOOR_BPM, band_speed_range(MOVEMENT_FAST)[0])


class TestTheAudienceEyeRule:
    """정본 §6.4 하드룰 — 기계로 막는 절반과 못 막는 절반."""

    def test_the_speed_floor_is_derived_from_the_five_second_limit(self):
        assert SPEED_FLOOR_BPM == 60.0 / EYE_DWELL_LIMIT_SECONDS
        assert band_speed_range(MOVEMENT_SLOW)[0] == SPEED_FLOOR_BPM

    def test_every_band_floor_completes_a_cycle_inside_the_limit(self):
        for band in (MOVEMENT_SLOW, MOVEMENT_MID, MOVEMENT_FAST):
            low, _high = band_speed_range(band)
            assert 60.0 / low <= EYE_DWELL_LIMIT_SECONDS

    def test_a_speed_below_the_floor_is_refused(self):
        look = _moving_look("too-slow", dynamics=3, speed=10.0)

        with pytest.raises(MovementError) as raised:
            plan_movement(look, band=MOVEMENT_SLOW)
        assert raised.value.reason == SPEED_OUT_OF_BAND

    def test_an_authored_speed_inside_the_band_is_used_verbatim(self):
        """대조군 — 대역 안의 값은 거절되지 않는다. 위 단정이 「항상 거절」이 아니라는 증거."""
        plan = plan_movement(_moving_look("in-band", dynamics=3, speed=18.0), band=MOVEMENT_SLOW)

        assert plan is not None
        assert plan.speed == 18.0

    def test_a_drop_speed_authored_into_the_slow_band_is_refused_too(self):
        """경계는 양방향이다 — 위로 벗어난 값도 조용히 끌어내리지 않는다."""
        with pytest.raises(MovementError) as raised:
            plan_movement(_moving_look("too-fast", dynamics=3, speed=120.0), band=MOVEMENT_SLOW)
        assert raised.value.reason == SPEED_OUT_OF_BAND


def _moving_look(
    look_id: str,
    *,
    dynamics: int,
    dimmer: float = 90,
    axes: tuple[tuple[str, float], ...] = (("Pan", 20.0),),
    speed: float | None = None,
) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=(
            AttributeValue("Dimmer", dimmer),
            AttributeValue("ColorRGB_R", 72),
            AttributeValue("ColorRGB_G", 100),
            AttributeValue("ColorRGB_B", 0),
        ),
        movement=tuple(
            MovementSpec(
                attribute=name, phase_from=0, phase_to=360, speed=speed, relative=magnitude
            )
            for name, magnitude in axes
        ),
    )


def _still_look(
    look_id: str,
    *,
    dynamics: int,
    dimmer: float = 90,
    zoom: float | None = None,
) -> Look:
    attributes = [
        AttributeValue("Dimmer", dimmer),
        AttributeValue("ColorRGB_R", 72),
        AttributeValue("ColorRGB_G", 100),
        AttributeValue("ColorRGB_B", 0),
    ]
    if zoom is not None:
        attributes.append(AttributeValue("Zoom", zoom))
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=tuple(attributes),
    )


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }

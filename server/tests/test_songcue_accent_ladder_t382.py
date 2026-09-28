"""t382 — 반복 회차는 양보로 자리를 얻어도 찍는 액센트를 잃지 않는다.

**고치기 전에 실측한 것**(카드 t382 보고, 후렴 일곱 회차·단일 축(``Dimmer`` 뿐)
룩·시작값 95): 값 라인 충돌-회피 사다리(``_distinct_values_line``)가 먼저이므로,
헤드룸이 한 걸음뿐인 룩에서는 대부분의 회차가 사다리를 오르지 못하고
양보(``LADDER_DIMMER_YIELD``, :func:`server.looks.songcue._yield_bundle`)나 양보로
비워진 기준값 자리를 그대로 물려받아 액센트 없이 밝기만 오르내렸다 — 7회차 중
1~5회차가 전부 ``(dimmer_yield,)``, 6회차만 ``(dimmer_hit, zoom_pinch)``, 7회차는
빈 튜플이었다.

이 파일은 :func:`server.looks.songcue._ensure_marking_accent` /
:func:`server.looks.songcue._finalize_marking_accents` 가 반복 회차(instance >= 2)
마다 정확히 하나의 찍는 액센트를 붙이는 것을, 그 값이 양보·재배열을 거쳐 최종
확정된 뒤에도 실측한다. 밝기(``Dimmer``) 자체의 단조 상승·재배열 성질(t366·t368·
t369)은 여기서 다시 재지 않는다 — 그 자리는 `test_songcue_ladder.py` ·
`test_songcue_chorus_rescue.py` 다.
"""

from __future__ import annotations

from server.looks.schema import AttributeValue, Look
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_resolver import LXSEQ_RIG

#: 실기 리그 그대로(`test_songcue_accent_fixture.py` 와 같은 자료) — 블라인더 그룹이
#: 실제로 있는 리그라야 AC-2 가 공허하지 않다.
_LXSEQ_GROUPS: tuple[tuple[int, str], ...] = tuple(
    (index + 1, name) for index, (name, _count) in enumerate(LXSEQ_RIG)
)

#: 카드 t382 재현 자리(`FULL_RIG`)에는 블라인더 그룹이 없다(`busking_fixtures.py`) —
#: D1·D2 재현·검사에 쓰는 곡 모양은 그대로 두고 블라인더 그룹 하나만 보탠다.
#: 이름 "BLIND"는 `server.looks.resolver`의 힌트 매칭이 역할 "블라인더"로 묶는
#: 이름이다(`test_songcue_ladder.py`의 실기 리그·`test_songcue_accent_fixture.py`의
#: ``_LXSEQ_GROUPS`` 와 같은 방식).
_RIG_WITH_BLINDER: tuple[tuple[int, str], ...] = FULL_RIG + ((20, "BLIND"),)


def _single_axis_look(dimmer: float = 95.0) -> Look:
    return Look(
        look_id="chorus-single-axis",
        display_name="chorus-single-axis",
        genre="edm",
        dynamics=5,
        roles=("백라이트",),
        attributes=(
            AttributeValue("Dimmer", dimmer),
            AttributeValue("ColorRGB_R", 72),
            AttributeValue("ColorRGB_G", 100),
            AttributeValue("ColorRGB_B", 0),
        ),
    )


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _chorus_times(count: int) -> tuple[tuple[str, str], ...]:
    times = []
    for index in range(count):
        total_seconds = index * 20
        minute, second = divmod(total_seconds, 60)
        times.append((f"{minute}:{second:02d}",))
    return tuple(("Chorus", time) for (time,) in times)


def _zoom_only_look(dimmer: float = 20.0) -> Look:
    return Look(
        look_id="zoom-only",
        display_name="zoom-only",
        genre="edm",
        dynamics=5,
        roles=("백라이트",),
        attributes=(
            AttributeValue("Dimmer", dimmer),
            AttributeValue("Zoom", 18),
            AttributeValue("ColorRGB_R", 72),
            AttributeValue("ColorRGB_G", 100),
            AttributeValue("ColorRGB_B", 0),
        ),
    )

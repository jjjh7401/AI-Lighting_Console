"""장비별 위상 디머 효과 생성기 — 감독 LOVE ATTACK 손 연출(22.21~22.43)의 저장 방식을 일반화한다.

감독의 위상 효과 23종은 모두 「디머 100 → 0 두 스텝 + 장비마다 다른 위상」이고, 위상은 장비의
자리에서 나온다: 왼쪽에서 오른쪽 차례, 홀짝, 바깥에서 안쪽(날개), 위아래 줄, 높이 단계. 이 모듈은
리그에서 읽은 장비 좌표(:class:`~server.spatial.schema.SpatialFixture`)만 보고 장비마다 위상을
정하고, 그 효과를 프리셋 하나로 저장하는 콘솔 명령 묶음을 만든다.

- 순수 함수다. 파일을 읽지 않고 콘솔에 닿지 않는다. 명령은 호출한 쪽이 승인 관문으로 보낸다.
- 장비 번호·그룹 번호를 코드에 두지 않는다. 장비 번호는 넘겨받은 좌표 기록의 ``fid`` 다.
- 저장은 ``/Selective`` 다. 장비마다 위상을 따로 적은 프리셋이고, 감독 프리셋이 이 방식으로
  무대에서 동작했다(감사 기록 2026-10-19 12:52~13:04 UTC,
  ``Store Preset 22.21 'LA BK L2R' /Selective`` 등). 앱의 다른 효과 저장(``instantiate.py``)은
  ``/Universal`` 이고 이 모듈과 무관하다.
- 한 바퀴는 박 수(``Measure``)로 적고 스피드 마스터에 묶는다. 곡 BPM 은 스피드 마스터가 든다.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from server.spatial.rows import SPATIAL_ROW_NOISE_SPAN
from server.spatial.schema import SpatialFixture

__all__ = [
    "PHASE_LAYOUTS",
    "PHASE_PERIOD_BEATS",
    "PhaseEffect",
    "PhasePatternError",
    "fixture_phases",
    "phase_effect_commands",
]

#: 위상 배치 다섯 가지. ``order`` 왼쪽→오른쪽 차례(같은 x 의 장비는 같은 위상), ``odd_even`` 차례의
#: 홀짝, ``wings`` 바깥→안쪽(가운데에서 같은 거리면 같은 위상), ``rows`` 위 줄·아래 줄(높이 두 단),
#: ``height`` 높이 세 단(낮은 단부터).
PHASE_LAYOUTS: tuple[str, ...] = ("order", "odd_even", "wings", "rows", "height")
#: 한 바퀴 박 수. 박 나누기 규칙(1·2·4박)에 감독이 쓴 8박을 더한다.
PHASE_PERIOD_BEATS: tuple[int, ...] = (1, 2, 4, 8)
#: 콘솔 프리셋 이름에 쓸 수 있는 글자(``beat_grid_edit._ASCII_LABEL_PATTERN`` 과 같은 허용 글자).
_LABEL_PATTERN = re.compile(r"[0-9A-Za-z _.-]+")
#: 높이 단 수 — 배치마다 고정이다.
_LEVELS_OF_LAYOUT = {"rows": 2, "height": 3}


class PhasePatternError(ValueError):
    """이 장비 배치로는 요청한 위상 효과를 만들 수 없다(이유는 한국어 문장)."""


@dataclass(frozen=True)
class PhaseEffect:
    """위상 디머 효과 하나의 결정.

    - ``layout``: :data:`PHASE_LAYOUTS` 중 하나.
    - ``period_beats``: 한 바퀴 박 수(:data:`PHASE_PERIOD_BEATS`).
    - ``width``: 켜져 있는 폭(콘솔 ``Width``, 1~100). 감독은 차례 30·교대 50·날개 40·스파크 20.
    - ``reverse``: 위상 차례를 거꾸로(오른쪽→왼쪽, 안쪽→바깥, 아래 줄 먼저, 높은 단부터).
    """

    layout: str
    period_beats: int
    width: int
    reverse: bool = False

    def __post_init__(self) -> None:
        if self.layout not in PHASE_LAYOUTS:
            raise PhasePatternError(f"모르는 위상 배치입니다: {self.layout!r}")
        if isinstance(self.period_beats, bool) or self.period_beats not in PHASE_PERIOD_BEATS:
            raise PhasePatternError("한 바퀴는 1·2·4·8박 중 하나여야 합니다.")
        if isinstance(self.width, bool) or not isinstance(self.width, int):
            raise PhasePatternError("폭은 정수여야 합니다.")
        if not 1 <= self.width <= 100:
            raise PhasePatternError("폭은 1~100 사이여야 합니다.")


def fixture_phases(
    fixtures: Sequence[SpatialFixture], layout: str, *, reverse: bool = False
) -> dict[int, int]:
    """장비 번호(``fid``) → 위상(도, 0~359 정수). 단(段)이 k 개면 단마다 ``360/k`` 씩 벌어진다."""
    if layout not in PHASE_LAYOUTS:
        raise PhasePatternError(f"모르는 위상 배치입니다: {layout!r}")
    if len(fixtures) < 2:
        raise PhasePatternError("위상을 나누려면 장비가 둘 이상이어야 합니다.")
    if len({fixture.fid for fixture in fixtures}) != len(fixtures):
        raise PhasePatternError("같은 장비 번호가 두 번 있습니다.")
    buckets = _buckets(fixtures, layout)
    if len(buckets) < 2:
        raise PhasePatternError(
            f"이 장비 배치로는 「{layout}」 위상을 나눌 수 없습니다(단이 하나)."
        )
    if reverse:
        buckets = buckets[::-1]
    step = 360 / len(buckets)
    return {fid: round(index * step) % 360 for index, fids in enumerate(buckets) for fid in fids}


def phase_effect_commands(
    fixtures: Sequence[SpatialFixture],
    effect: PhaseEffect,
    *,
    preset_pool: int,
    preset_slot: int,
    label: str,
    speed_master: int,
) -> tuple[str, ...]:
    """위상 디머 효과를 프리셋 ``preset_pool.preset_slot`` 에 ``/Selective`` 로 저장하는 명령 묶음.

    모양은 감독 프리셋을 저장한 묶음과 같다: 전체 선택 → 디머 100·0 두 스텝 → 위상이 같은 장비끼리
    선택해 ``At Phase`` → 전체 선택 → 폭·한 바퀴(박)·스피드 마스터 → 저장 → 비움.
    """
    for name, value in (
        ("풀", preset_pool),
        ("번호", preset_slot),
        ("스피드 마스터", speed_master),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise PhasePatternError(f"프리셋 {name}는 1 이상의 정수여야 합니다: {value!r}")
    if not _LABEL_PATTERN.fullmatch(label or ""):
        raise PhasePatternError(f"프리셋 이름은 영문·숫자·공백·. _ - 만 됩니다: {label!r}")
    phases = fixture_phases(fixtures, effect.layout, reverse=effect.reverse)
    everyone = _selection(sorted(phases))
    lines = [
        "ChangeDestination Root",
        "ClearAll",
        f"Fixture {everyone}",
        "Attribute 'Dimmer' At 100",
        "Step 2",
        "Attribute 'Dimmer' At 0",
    ]
    for phase in sorted(set(phases.values())):
        members = sorted(fid for fid, value in phases.items() if value == phase)
        lines += [f"Fixture {_selection(members)}", f"Attribute 'Dimmer' At Phase {phase}"]
    lines += [
        f"Fixture {everyone}",
        f"Attribute 'Dimmer' At Width {effect.width}",
        f"Attribute 'Dimmer' At Measure {effect.period_beats}",
        f"Attribute 'Dimmer' At SpeedMaster {speed_master}",
        f"Store Preset {preset_pool}.{preset_slot} '{label}' /Selective",
        "ClearAll",
    ]
    return tuple(lines)


def _buckets(fixtures: Sequence[SpatialFixture], layout: str) -> list[list[int]]:
    """위상이 같은 장비 묶음을 위상 차례대로. 같은 좌표·같은 거리는 오차(``SPATIAL_ROW_NOISE_SPAN``)
    안에서 한 묶음이고, 묶음 안은 장비 번호 순서다."""
    if layout == "order":
        return _clusters(fixtures, lambda fixture: fixture.x)
    if layout == "odd_even":
        ordered = sorted(fixtures, key=lambda fixture: (fixture.x, fixture.fid))
        return [[f.fid for f in ordered[0::2]], [f.fid for f in ordered[1::2]]]
    if layout == "wings":
        center = (min(f.x for f in fixtures) + max(f.x for f in fixtures)) / 2
        return _clusters(fixtures, lambda fixture: -abs(fixture.x - center))
    levels = _levels(fixtures, _LEVELS_OF_LAYOUT[layout])
    return levels[::-1] if layout == "rows" else levels


def _clusters(fixtures: Sequence[SpatialFixture], key) -> list[list[int]]:
    """``key`` 값 오름차순으로, 이웃과 오차 이하로 붙은 장비를 한 묶음으로 모은다."""
    ordered = sorted(fixtures, key=lambda fixture: (key(fixture), fixture.fid))
    groups: list[list[SpatialFixture]] = [[ordered[0]]]
    for fixture in ordered[1:]:
        if key(fixture) - key(groups[-1][-1]) <= SPATIAL_ROW_NOISE_SPAN:
            groups[-1].append(fixture)
        else:
            groups.append([fixture])
    return [sorted(f.fid for f in group) for group in groups]


def _levels(fixtures: Sequence[SpatialFixture], count: int) -> list[list[int]]:
    """높이(z)를 낮은 단부터 최대 ``count`` 단으로 나눈다 — 가장 넓은 높이 틈(오차보다 넓은 것)에서
    자른다. 높이가 고르면 단이 하나라 위상을 나눌 수 없다."""
    ordered = sorted(fixtures, key=lambda fixture: (fixture.z, fixture.fid))
    gaps = sorted(
        (
            (ordered[i + 1].z - ordered[i].z, i)
            for i in range(len(ordered) - 1)
            if ordered[i + 1].z - ordered[i].z > SPATIAL_ROW_NOISE_SPAN
        ),
        reverse=True,
    )
    cuts = sorted(index for _gap, index in gaps[: count - 1])
    levels, start = [], 0
    for cut in cuts:
        levels.append(sorted(f.fid for f in ordered[start : cut + 1]))
        start = cut + 1
    levels.append(sorted(f.fid for f in ordered[start:]))
    return levels


def _selection(fids: Sequence[int]) -> str:
    """장비 번호 목록을 콘솔 선택 문법으로 — 이어진 번호는 ``a Thru b``, 그 밖은 ``+`` 로."""
    runs: list[tuple[int, int]] = []
    for fid in sorted(fids):
        if runs and fid == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], fid)
        else:
            runs.append((fid, fid))
    return " + ".join(str(a) if a == b else f"{a} Thru {b}" for a, b in runs)

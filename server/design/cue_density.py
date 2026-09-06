"""큐 밀도 — 긴 구간을 마디 경계에서 여러 큐로 쪼갠다 (카드 t305).

오늘까지 이 앱은 **구간 하나에 큐 하나**를 세웠다. 4구간 곡이면 큐 4장.
운영자의 정본 산출물(`LXSEQ_SAMPLE_01_Sugar_r3.timeline.html`, Maroon 5 —
Sugar, 3:56 / 120 BPM / 4/4)은 같은 길이의 곡에 **큐 18장**을 세우고, 한
구간 **안에서** 그림이 자란다. VERSE1 은 한 구간인데 Q020·Q030 둘로 갈리고,
CHORUS3(32마디)은 Q130~Q160 넷으로 갈린다.

## 정본에서 실측한 구간별 큐 수

표는 위 파일의 Cue Sheet 를 세어 만든 것이다(마디 수는 같은 파일의
Timeline 밴드가 구간마다 적어 둔 값).

| 구간     | 마디 | 큐 | 큐당 마디 | 큐 번호 |
|----------|-----|----|----------|---------|
| INTRO    |   4 |  1 | 4        | Q010 |
| VERSE1   |  16 |  2 | 8 · 8    | Q020 Q030 |
| PRE1     |   8 |  1 | 8        | Q040 |
| CHORUS1  |  16 |  2 | 8 · 8    | Q050 Q060 |
| VERSE2   |   8 |  1 | 8        | Q070 |
| PRE2     |   8 |  1 | 8        | Q080 |
| CHORUS2  |  16 |  2 | 8 · 8    | Q090 Q100 |
| BRIDGE   |   8 |  2 | 4 · 4    | Q110 Q120 |
| CHORUS3  |  32 |  4 | 8×4      | Q130~Q160 |
| OUTRO    |   2 |  2 | 2 · 0    | Q170 Q180 |

열 중 여덟은 **8마디 단위** 하나로 설명된다: `큐 수 = floor(마디/8)`,
최소 1. 16→2, 32→4, 8→1, 4→1, 2→1 이 전부 맞는다.

설명되지 **않는** 두 줄을 숨기지 않는다:

* `BRIDGE` 는 8마디를 4·4 로 쪼갠다. 이것은 마디 수에서 나오지 않는다 —
  "낙차를 만들었다가 다시 불붙인다"는 연출 판단(35 → 75)이고, 이 규칙은
  그 판단을 흉내 내지 않는다. 8마디 브리지는 큐 하나로 나간다.
* `OUTRO` 의 둘째 큐(Q180)는 쪼갠 것이 아니라 곡 끝의 **암전**이다. 구간
  분할과 다른 종류의 큐라 이 규칙 밖에 있다.

그래서 채택한 규칙은 "정본이 실제로 하는 것 중 마디 수만으로 도출되는
부분"이다. 지어낸 숫자가 아니다.

## 규칙

* 단위는 **8마디**(`BAR_UNIT_BARS`). 한 구간의 큐 수는
  `floor(구간 마디 수 / 8)`, 최소 1.
* 8마디에 못 미치는 구간은 큐 하나. 나누어떨어지지 않는 나머지는 **마지막
  큐가 흡수**한다 — 20마디는 8+12 로 두 큐이지, 8+8+4 로 세 큐가 아니다.
  4마디짜리 꼬투리 큐는 연출이 아니라 잡음이다.
* 마지막 구간은 끝나는 시각을 아무도 안 주면 길이를 모르므로 **쪼개지
  않는다**(`song_end_ms` 를 주면 쪼갠다).

## 안 재고는 안 쓴다

마디 연산에는 BPM 과 박자표가 둘 다 필요하다. 카드 t283 이 실측했듯 둘 다
**선언해야 있는** 값이다. 그래서:

* `bpm` 이 `None` 이면 분할은 **한 건도** 일어나지 않는다 — 오늘과 바이트
  동일. `MusicProfile.effective_bpm`(없으면 120)은 **쓰지 않는다**: 안 잰
  템포로 계산한 마디는 틀린 자리에 큐를 놓고, 틀린 마디의 큐는 통째로
  남은 구간보다 나쁘다.
* 박자표를 못 읽으면 같은 이유로 분할 없음.

## 쪼갠 큐가 서로 달라야 한다

16초 간격의 똑같은 큐 둘은 큐 하나보다 나쁘다. 정본의 쪼갠 큐는 서로
다르다 — Q060 은 "강도 유지, 색만 교체", Q140 은 "색상만 순환시켜 체감
변화 유지". 이 규칙이 표현할 수 있는 차이도 **팔레트 회전** 하나다.

따라서 색이 하나뿐인 구간은 회전해도 같은 큐가 나오므로 **쪼개지 않는다**
(`palette_sizes`). 이것이 카드의 "차이를 못 만들면 큐 하나만 내라"이고,
그 사유는 `SplitPlan.notes` 로 밖에 나간다.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

#: 분할 단위. 정본이 8마디에 큐 하나를 놓는다(위 표의 여덟 줄).
BAR_UNIT_BARS = 8

#: 이 단위 수 미만이면 쪼개지 않는다 — 즉 16마디부터 둘로 갈린다.
MIN_UNITS_TO_SPLIT = 2

#: 팔레트가 이 색 수 미만이면 회전이 항등이라 쪼갠 큐가 서로 같아진다.
MIN_PALETTE_COLORS_TO_SPLIT = 2

_METER_PATTERN = re.compile(r"\s*(\d+)\s*/\s*(\d+)\s*\Z")

_MILLISECONDS_PER_MINUTE = 60_000.0


@dataclass(frozen=True)
class CueSplit:
    """구간 하나에서 나온 큐 하나.

    ``unit_index`` 0 은 구간을 여는 큐, 1 이상은 그 구간 **안에서** 이어지는
    큐다. 팔레트 회전량이 곧 이 값이다.
    """

    source_index: int
    unit_index: int
    start_ms: int


@dataclass(frozen=True)
class SplitPlan:
    """분할 결과와, 쪼개지 **않은** 구간의 사유."""

    splits: tuple[CueSplit, ...]
    notes: tuple[str, ...] = ()

    @property
    def cue_count(self) -> int:
        return len(self.splits)

    @property
    def source_origins(self) -> tuple[int, ...]:
        """``splits`` 와 같은 길이의, 큐마다 원래 구간 번호(0-based)."""
        return tuple(split.source_index for split in self.splits)


def beats_per_bar(meter: object) -> int | None:
    """``4/4`` 꼴에서 마디당 박수. 못 읽으면 ``None`` — 추측하지 않는다."""
    match = _METER_PATTERN.fullmatch(str(meter or ""))
    if match is None:
        return None
    beats = int(match.group(1))
    return beats if beats > 0 else None


def bar_milliseconds(bpm: float | None, meter: object = "4/4") -> float | None:
    """한 마디의 밀리초. **선언된** BPM 과 읽히는 박자표가 둘 다 있을 때만.

    120 BPM · 4/4 면 2000.0 — 정본이 헤더에 적어 둔 `1마디 2.000s` 와 같다.
    """
    if bpm is None or isinstance(bpm, bool) or not isinstance(bpm, int | float):
        return None
    if bpm <= 0:
        return None
    beats = beats_per_bar(meter)
    if beats is None:
        return None
    return beats * _MILLISECONDS_PER_MINUTE / float(bpm)


def plan_cue_density(
    starts_ms: Sequence[int],
    *,
    bpm: float | None,
    meter: object = "4/4",
    palette_sizes: Sequence[int] | None = None,
    song_end_ms: int | None = None,
) -> SplitPlan:
    """구간 시작 시각 목록을 큐 목록으로 바꾼다.

    :param starts_ms: 구간 시작 시각. 오름차순 가정(호출자가 이미 정렬한다).
    :param bpm: **선언된** BPM. ``None`` 이면 분할 없음.
    :param meter: 박자표 문자열. 못 읽으면 분할 없음.
    :param palette_sizes: 구간별 팔레트 색 수. 2 미만인 구간은 쪼개지 않는다.
    :param song_end_ms: 곡 끝. 주면 마지막 구간도 길이를 알아 쪼갤 수 있다.
    """
    starts = list(starts_ms)
    if not starts:
        return SplitPlan(splits=())

    identity = tuple(
        CueSplit(source_index=index, unit_index=0, start_ms=start)
        for index, start in enumerate(starts)
    )

    bar_ms = bar_milliseconds(bpm, meter)
    if bar_ms is None:
        reason = (
            "BPM 미선언 — 마디를 계산할 수 없어 구간을 쪼개지 않았습니다"
            if bpm is None
            else f"박자표 {meter!r} 를 읽지 못해 구간을 쪼개지 않았습니다"
        )
        return SplitPlan(splits=identity, notes=(reason,))

    unit_ms = bar_ms * BAR_UNIT_BARS
    splits: list[CueSplit] = []
    notes: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else song_end_ms
        units = _unit_count(start, end, unit_ms)
        if units >= MIN_UNITS_TO_SPLIT and not _palette_can_differ(palette_sizes, index):
            notes.append(
                f"구간 {index + 1}: 색이 하나뿐이라 쪼갠 큐가 서로 같아집니다 — 큐 하나로 둡니다"
            )
            units = 1
        for unit_index in range(units):
            splits.append(
                CueSplit(
                    source_index=index,
                    unit_index=unit_index,
                    start_ms=start + round(unit_index * unit_ms),
                )
            )
    return SplitPlan(splits=tuple(splits), notes=tuple(notes))


def rotate_palette(colors: Sequence[str], unit_index: int) -> tuple[str, ...]:
    """이어지는 큐의 팔레트 — 색 목록을 ``unit_index`` 만큼 돌린다.

    색이 하나면 항등이다. ``plan_cue_density`` 가 그런 구간을 애초에 쪼개지
    않으므로 이 함수가 같은 큐를 만들어 내는 일은 없지만, 다른 호출자가
    생겨도 안전하도록 항등을 그대로 돌려준다.
    """
    items = tuple(colors)
    if len(items) < MIN_PALETTE_COLORS_TO_SPLIT or unit_index <= 0:
        return items
    shift = unit_index % len(items)
    return items[shift:] + items[:shift]


def _unit_count(start_ms: int, end_ms: int | None, unit_ms: float) -> int:
    if end_ms is None or end_ms <= start_ms:
        return 1
    units = int((end_ms - start_ms) // unit_ms)
    return max(1, units)


def _palette_can_differ(palette_sizes: Sequence[int] | None, index: int) -> bool:
    if palette_sizes is None:
        return True
    if index >= len(palette_sizes):
        return True
    return palette_sizes[index] >= MIN_PALETTE_COLORS_TO_SPLIT

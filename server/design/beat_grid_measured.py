"""측정된 무빙 허용목록 — M1 ⑤⑦⑨ 게이트 우회 (카드 t553,
REQ-LDBEAT-001/006(vi)).

이 모듈은 콘솔에 아무것도 쓰지 않는다. `beat_grid_data/measured_movements.yaml`
하나를 읽는 순수 함수뿐이다(``server.design.beat_grid``·``app_movement``와
같은 모양). 그룹 번호·모양·축 조합은 전부 그 데이터 파일에서 온다 — 이
모듈 코드 안에는 리그 전용 리터럴이 없다(REQ-LDBEAT-006(vi-6)와 같은 원칙).

이 모듈이 푸는 문제: `beat_grid_emit.blocked_m1_items_for_cue`는
progress.md의 M1 표만 본다. 그런데 카드 t538·t548의 실기 프로브가
progress.md의 원래 표(⑤⑨ "움직임 없음"/"미확인")보다 **더 구체적으로**
확인한 사실이 있다 — "이 특정 그룹·모양·축 조합은 실제로 움직인다"
(예: MOVER-D의 Tilt wave). 원래 M1 표의 판정 문자열은 고치지 않고(기록을
수정하지 않는다, progress.md M1 표 자체는 PRESERVE 대상), 그 구체적
사실만 별도 허용목록으로 얹어 게이트를 선택적으로 연다 — "부분 적용
0건" 원칙은 유지한다: 매칭되지 않는 칸은 여전히 막힌다.

``base_condition`` 이 ``"any"``가 아닌 엔트리(예:
``"requires_tilted_base_unverifiable"``)는 매칭되어도 게이트를 절대
열지 않는다 — 측정한 사실의 기록일 뿐이다. 자세한 뜻은
``beat_grid_data/measured_movements.yaml``의 머리말 주석 참조.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

__all__ = [
    "MEASURED_MOVEMENTS",
    "MeasuredMovement",
    "is_movement_measured_open",
]

_DATA_PATH = Path(__file__).resolve().parent / "beat_grid_data" / "measured_movements.yaml"

#: 이 값이면 매칭되는 엔트리가 있어도 게이트를 절대 열지 않는다(위 모듈
#: 독스트링 참조) — "any"만 게이트를 연다(기본값은 닫힘, 지어내지 않음).
_OPEN_BASE_CONDITION = "any"


@dataclass(frozen=True)
class MeasuredMovement:
    group_no: int
    shape: str
    axes: frozenset[str]
    base_condition: str
    source: str


def _load_entries() -> tuple[MeasuredMovement, ...]:
    with _DATA_PATH.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    raw_entries = document.get("entries") if isinstance(document, dict) else None
    if not raw_entries:
        return ()
    entries: list[MeasuredMovement] = []
    for raw in raw_entries:
        entries.append(
            MeasuredMovement(
                group_no=int(raw["group_no"]),
                shape=str(raw["shape"]),
                axes=frozenset(raw["axes"]),
                base_condition=str(raw["base_condition"]),
                source=str(raw["source"]),
            )
        )
    return tuple(entries)


#: 모듈 로드 시 한 번 읽는다(``beat_grid.default_beat_grid``와 달리 이
#: 목록은 호출마다 바뀌는 곡 제목 인자가 없어 상수로 캐싱해도 안전하다).
MEASURED_MOVEMENTS: tuple[MeasuredMovement, ...] = _load_entries()


_AXIS_SPELLING = {"pan": "Pan", "tilt": "Tilt"}


def canonical_axes(axes: Sequence[str] | frozenset[str]) -> tuple[str, ...]:
    """축 이름 철자를 콘솔 철자(``Pan``·``Tilt``)로 맞춘다. 자동 배치 초안이 한때 소문자
    ``pan`` 을 적었고, 그 격자는 저장돼 있다 — 철자만 다른 같은 축이 실기 기록 대조·프리셋
    계획·송신에서 따로 취급되지 않게 한다. 모르는 이름은 그대로 둔다(지어내지 않는다)."""
    return tuple(_AXIS_SPELLING.get(str(axis).strip().casefold(), str(axis)) for axis in axes)


def is_movement_measured_open(
    group_no: int | None, shape: object, axes: Sequence[str] | frozenset[str]
) -> bool:
    """``group_no``·``shape``·``axes``(정확히 일치 — 부분집합이나 상위집합은
    매칭으로 보지 않는다)와 맞는 측정 기록이 있고, 그 기록의
    ``base_condition``이 ``"any"``일 때만 True. 그 밖은 전부 False
    (부분 적용 0건, 느슨하게 풀지 않는다)."""
    if group_no is None:
        return False
    axes_frozen = frozenset(canonical_axes(axes))
    for entry in MEASURED_MOVEMENTS:
        if entry.group_no == group_no and entry.shape == shape and entry.axes == axes_frozen:
            return entry.base_condition == _OPEN_BASE_CONDITION
    return False

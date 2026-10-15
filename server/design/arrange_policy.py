"""곡별 배치 규칙 설정 — SPEC-LDARRANGE-001 REQ-LDARRANGE-004.

규칙 값(구간 길이 4마디, 리듬층 둘·드롭 셋)은 전역 상수가 아니라 곡마다 든다. 기본값은
배치 규칙서(``reports/effect-arrangement-rules-20261007.md`` §1 규칙 3·4)의 값이다. 이
객체는 불변이라 한 곡의 설정을 바꿔도 다른 곡의 설정에 닿지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ArrangementPolicy"]


# @MX:NOTE: [AUTO] 곡별 규칙 설정 — 전역 상수가 아니라 곡마다 따로 든다(REQ-LDARRANGE-004).
@dataclass(frozen=True)
class ArrangementPolicy:
    """이 곡에 적용할 배치 규칙 값.

    - ``slow_song``: 「느린 곡」 플래그. 켜면 스트로브를 한 칸도 제안하지 않는다
      (REQ-LDARRANGE-007). 기준 자체는 spec.md §5 항목 3의 기본안(곡 메타데이터의
      명시 플래그)이고, 기본값은 꺼짐이다.
    - ``window_bars``: 주인공 교대와 리듬층 세기를 재는 구간 길이(규칙 4: 4마디).
    - ``base_layer_cap``: 보통 구간의 리듬층 상한(규칙 3: 둘).
    - ``drop_layer_cap``: 드롭 구간의 리듬층 상한(규칙 3: 셋). 마지막 코러스 라벨은
      마디 지도에 없어서 드롭 구간에만 적용한다(spec.md §5 항목 1 공백 (나)).
    """

    slow_song: bool = False
    window_bars: int = 4
    base_layer_cap: int = 2
    drop_layer_cap: int = 3

    def __post_init__(self) -> None:
        if self.window_bars < 1:
            raise ValueError("구간 길이는 1마디 이상이어야 합니다.")
        if not 1 <= self.base_layer_cap <= self.drop_layer_cap:
            raise ValueError("리듬층 상한은 1 이상이고, 드롭 상한은 보통 상한 이상이어야 합니다.")

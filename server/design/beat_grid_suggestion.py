"""박자 격자 편집 경로 ③(AI 제안) — 보류~「적용」 메커니즘 (SPEC-LDBEAT-001
M3, 카드 t551).

확정된 감독 결정④(``reports/ldbeat-runbook-mockup-20261008.md`` §2): AI
제안은 바꿀 칸 목록을 제안 카드로만 보여주고, 감독이 「적용」을 누르기
전에는 초안도 콘솔도 바뀌지 않는다. 이 모듈은 그 **보류 상태**만 담는다
— 제안을 만들 때 ``apply_beat_grid_edit``를 부르지 않고, 「적용」이 들어온
뒤에야(이 모듈 밖에서, 호출자가) 그 함수를 부른다.

제안 소스는 교체 가능하다(pluggable, ``SuggestionSource``). **이 카드는
실제 AI 백엔드를 갖지 않는다** — ``NullSuggestionSource``가 그 부재를
정직하게 말하는 기본값이다(지어낸 제안 0건). 실제 AI 연동은 이 카드의
범위 밖이며, run-phase 후속 카드가 이 Protocol을 구현하는 소스로
교체하면 된다(이 모듈·호출부는 바뀌지 않는다)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

__all__ = [
    "BeatGridSuggestion",
    "NullSuggestionSource",
    "PendingSuggestionStore",
    "SuggestionSource",
]


@dataclass(frozen=True)
class BeatGridSuggestion:
    """보류 중인 제안 하나 — `apply_beat_grid_edit(grid, bar=bar,
    target=target, changes=changes)`가 받을 그대로의 모양을 이미 담고
    있다(「적용」 클릭이 추가로 해석할 것이 없다)."""

    suggestion_id: str
    bar: int
    target: str
    changes: dict[str, object] = field(default_factory=dict)
    rationale: str = ""


class SuggestionSource(Protocol):
    """``(changes, rationale)`` 또는 제안이 없으면 ``None``을 돌려준다.
    이 모듈은 무엇이 이 소스를 구현하는지 모른다 — AI 백엔드든, 결정적
    규칙이든, 시험용 더블이든 교체 가능하다."""

    def __call__(
        self, grid: Mapping[str, object], bar: int, target: str
    ) -> tuple[dict[str, object], str] | None: ...


class NullSuggestionSource:
    """정직한 기본값 — 실제 AI 백엔드가 이 카드 범위 밖이라, 지어낸 제안을
    만들지 않고 항상 "제안 없음"(``None``)을 돌려준다."""

    def __call__(
        self, grid: Mapping[str, object], bar: int, target: str
    ) -> tuple[dict[str, object], str] | None:
        return None


class PendingSuggestionStore:
    """제안 생성~「적용」 사이의 보류 상태. 보류 중엔 격자·콘솔 둘 다
    바뀌지 않는다 — `create`는 ``grid``를 읽기만 하고(소스에 넘길 뿐)
    쓰지 않는다. 한 번 `consume`하면 다시 쓸 수 없다(재생 불가, 적용은
    정확히 한 번만)."""

    def __init__(self) -> None:
        self._pending: dict[str, BeatGridSuggestion] = {}

    def create(
        self,
        grid: Mapping[str, object],
        bar: int,
        target: str,
        *,
        source: SuggestionSource,
    ) -> BeatGridSuggestion | None:
        result = source(grid, bar, target)
        if result is None:
            return None
        changes, rationale = result
        suggestion = BeatGridSuggestion(
            suggestion_id=str(uuid.uuid4()),
            bar=bar,
            target=target,
            changes=dict(changes),
            rationale=rationale,
        )
        self._pending[suggestion.suggestion_id] = suggestion
        return suggestion

    def peek(self, suggestion_id: str) -> BeatGridSuggestion | None:
        """보류 중인 제안을 소비하지 않고 들여다본다 — UI 렌더용."""
        return self._pending.get(suggestion_id)

    def consume(self, suggestion_id: str) -> BeatGridSuggestion | None:
        """「적용」(또는 폐기) — 찾으면 꺼내고 보류 목록에서 지운다. 모르는
        id·이미 소비된 id는 지어내지 않고 ``None``."""
        return self._pending.pop(suggestion_id, None)

    def __len__(self) -> int:
        return len(self._pending)

"""초안 타임라인의 되돌리기/다시하기 이력 (t281).

`SongTimelineStore.latest` 가 **초안 그 자체**다 — 화면이 읽는 것과 편집이
고치는 것이 같은 하나여야 「고친 게 안 보인다」가 생기지 않는다. 이 클래스는
그 옆에 붙어 **직전 상태의 깊은 사본**만 쌓는다.

경계 셋:

* 콘솔에 닿지 않는다. 여기 있는 것은 사전뿐이고 명령 문자열이 없다.
* 라이브러리에 닿지 않는다. 저장본은 `SongTimelineLibrary` 의 별도 항목이며
  되돌리기는 그것을 건드리지 않는다.
* 상한이 있다. :data:`DRAFT_HISTORY_LIMIT` 개까지만 쌓고 그 너머는 가장 오래된
  것부터 버린다 — 한 세션이 편집을 몇 번 하든 메모리가 선형으로 자라지 않게.
"""

from __future__ import annotations

import copy
from collections import deque

__all__ = ["DRAFT_HISTORY_LIMIT", "TimelineDraftHistory"]

#: 되돌릴 수 있는 걸음 수. 20 은 「한 곡을 손보는 한 자리」의 편집 횟수를 덮으면서
#: (구간 12~20개 × 칸 하나씩) 한 항목이 큐시트 사전 하나라는 무게를 감안한 값이다.
#: 더 늘리려면 무게를 먼저 재라 — 항목 하나가 곡 전체의 깊은 사본이다.
DRAFT_HISTORY_LIMIT = 20


class TimelineDraftHistory:
    """되돌리기/다시하기 스택 한 쌍. 상태는 전부 깊은 사본으로 보관한다."""

    def __init__(self, limit: int = DRAFT_HISTORY_LIMIT) -> None:
        if limit < 1:
            raise ValueError("draft history limit must be >= 1")
        self._limit = limit
        self._undo: deque[dict] = deque(maxlen=limit)
        self._redo: deque[dict] = deque(maxlen=limit)

    @property
    def can_undo(self) -> bool:
        return len(self._undo) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo) > 0

    @property
    def depth(self) -> int:
        """되돌릴 수 있는 걸음 수 — 화면의 「수정됨」 배지가 읽는 값."""
        return len(self._undo)

    def record(self, previous: dict) -> None:
        """편집 **직전** 상태를 쌓는다. 새 편집은 다시하기 가지를 잘라낸다."""
        self._undo.append(copy.deepcopy(previous))
        self._redo.clear()

    def undo(self, current: dict) -> dict | None:
        """직전 상태를 돌려준다. 없으면 ``None`` (화면은 그대로 둔다)."""
        if not self._undo:
            return None
        self._redo.append(copy.deepcopy(current))
        return copy.deepcopy(self._undo.pop())

    def redo(self, current: dict) -> dict | None:
        """되돌리기로 물러난 상태를 다시 돌려준다. 없으면 ``None``."""
        if not self._redo:
            return None
        self._undo.append(copy.deepcopy(current))
        return copy.deepcopy(self._redo.pop())

    def clear(self) -> None:
        """새 곡 설계처럼 초안의 계보가 끊기는 자리에서 부른다."""
        self._undo.clear()
        self._redo.clear()

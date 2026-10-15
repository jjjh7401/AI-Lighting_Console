"""배치 초안 보류 저장소 — SPEC-LDARRANGE-001 두 번째 묶음.

제안은 「적용」 전까지 보류 상태로만 있다. 격자와 콘솔은 바뀌지 않는다. 한 번 꺼내면 다시
쓸 수 없다. 적용과 거절은 모두 꺼내기다.
"""

from __future__ import annotations

import uuid

from server.design.arrange_generator import ArrangementDraft

__all__ = ["PendingDraftStore"]


class PendingDraftStore:
    """보류 중인 배치 초안을 id 로 담는다. 만들기, 들여다보기, 한 번만 꺼내기가 있다."""

    def __init__(self) -> None:
        self._pending: dict[str, ArrangementDraft] = {}

    def create(self, draft: ArrangementDraft) -> str:
        draft_id = str(uuid.uuid4())
        self._pending[draft_id] = draft
        return draft_id

    def peek(self, draft_id: str) -> ArrangementDraft | None:
        return self._pending.get(draft_id)

    def consume(self, draft_id: str) -> ArrangementDraft | None:
        return self._pending.pop(draft_id, None)

    def __len__(self) -> int:
        return len(self._pending)

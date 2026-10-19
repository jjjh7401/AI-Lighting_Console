"""칸 옮기기를 콘솔에 바로 반영할 때의 허락 — 미리보기 승인과 따로 둔다 (SPEC-LDRHYTHM-001 TC5).

콘솔 접촉 0건 — 순수 상태 객체뿐이다.

- ``CellLiveApproval`` — 감독이 허락한 일의 범위(``SCOPE_MOVE`` · ``SCOPE_CREATE_DELETE``)를 모아
  두고, 이번 일에 필요한 범위를 모두 덮는지만 답한다. 아무것도 파일에 저장하지 않는다.
- ``SongTimelineStore.cell_live_approval`` — 저장소마다 하나씩 들고 있는 자리. 미리보기 승인
  (``preview_approval``, 세션당 1회)과는 다른 객체이고, 한쪽 승인이 다른 쪽을 열지 않는다.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid_cell_live import SCOPE_CREATE_DELETE, SCOPE_MOVE
from server.design.send_approval import CellLiveApproval, PreviewApprovalSession
from server.web.session import SongTimelineStore

_MOVE = frozenset({SCOPE_MOVE})
_CREATE_DELETE = frozenset({SCOPE_CREATE_DELETE})
_BOTH = _MOVE | _CREATE_DELETE


class TestCellLiveApproval:
    def test_a_fresh_object_covers_no_scope(self) -> None:
        approval = CellLiveApproval()
        assert approval.covers(_MOVE) is False
        assert approval.covers(_CREATE_DELETE) is False

    def test_an_empty_need_is_trivially_covered(self) -> None:
        # 필요한 범위가 없으면 허락받을 것도 없다 — 빈 집합은 어떤 집합의 부분집합이기도 하다.
        assert CellLiveApproval().covers(frozenset()) is True

    def test_an_approved_scope_covers_itself_but_not_another(self) -> None:
        approval = CellLiveApproval()
        approval.approve(_MOVE)
        assert approval.covers(_MOVE) is True
        assert approval.covers(_CREATE_DELETE) is False

    def test_covering_part_of_the_need_is_not_covering_it(self) -> None:
        # 옮기기만 허락했는데 옮기기와 만들기·지우기가 다 필요한 일은 덮이지 않는다.
        # 겹침이 아니라 부분집합이어야 한다.
        approval = CellLiveApproval()
        approval.approve(_MOVE)
        assert approval.covers(_BOTH) is False

    def test_approvals_accumulate(self) -> None:
        approval = CellLiveApproval()
        approval.approve(_MOVE)
        approval.approve(_CREATE_DELETE)
        assert approval.covers(_BOTH) is True
        assert approval.covers(_MOVE) is True
        assert approval.covers(_CREATE_DELETE) is True

    def test_a_new_instance_inherits_nothing(self) -> None:
        first = CellLiveApproval()
        first.approve(_MOVE)
        second = CellLiveApproval()
        assert second.covers(_MOVE) is False
        # 대조군 — 첫 객체는 자기 허락을 그대로 쥐고 있다.
        assert first.covers(_MOVE) is True

    def test_approving_nothing_changes_nothing(self) -> None:
        approval = CellLiveApproval()
        approval.approve(frozenset())
        assert approval.covers(_MOVE) is False
        approval.approve(_MOVE)
        approval.approve(frozenset())
        assert approval.covers(_MOVE) is True
        assert approval.covers(_CREATE_DELETE) is False

    def test_the_approved_set_cannot_be_injected_through_the_constructor(self) -> None:
        # 새 객체는 항상 빈 채로 시작한다 — 만들면서 미리 허락해 둘 길이 없다.
        with pytest.raises(TypeError):
            CellLiveApproval(_MOVE)  # type: ignore[call-arg]

    def test_it_is_not_a_kind_of_preview_approval(self) -> None:
        assert not issubclass(CellLiveApproval, PreviewApprovalSession)


class TestStoreSlot:
    def test_the_store_holds_its_own_cell_live_approval(self) -> None:
        store = SongTimelineStore()
        assert isinstance(store.cell_live_approval, CellLiveApproval)
        assert store.cell_live_approval is not store.preview_approval
        assert store.cell_live_approval.covers(_MOVE) is False

    def test_two_stores_do_not_share_an_approval(self) -> None:
        first = SongTimelineStore()
        first.cell_live_approval.approve(_MOVE)
        assert SongTimelineStore().cell_live_approval.covers(_MOVE) is False

    def test_a_preview_approval_does_not_open_cell_live(self) -> None:
        store = SongTimelineStore()
        store.preview_approval.approve()
        assert store.cell_live_approval.covers(_MOVE) is False

    def test_a_cell_live_approval_does_not_open_the_preview(self) -> None:
        store = SongTimelineStore()
        store.cell_live_approval.approve(_BOTH)
        assert store.preview_approval.is_approved is False

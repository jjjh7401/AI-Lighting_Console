"""「적용」 뒤 콘솔 반영 — ``beat_grid_apply`` 의 ``live`` 와 ``SCOPE_APPLY`` (SPEC-LDRHYTHM-001).

감독이 앱에서 「적용」을 누르면 앱 편집이 성공한 같은 칸이 기존 「⇪ 콘솔에 반영」 칸 단위
길(``cells``)로 콘솔에도 나간다. 이 파일은 서버 쪽 세 가지를 못박는다.

* 프로토콜 — ``live`` 는 mode 'apply' + ``cells`` 와 함께일 때만, 참/거짓 값으로만 받는다.
* 승인 범위 — ``SCOPE_APPLY`` 는 ``SCOPE_MOVE``·``SCOPE_CREATE_DELETE`` 와 따로다.
* 세션 — 첫 live 반영은 ⇪ 와 같은 승인 카드를 묻고, 카드가 성공한 뒤의 live 반영은 카드 없이
  나간다. 거절·실패한 카드는 승인을 남기지 않는다. ``live`` 가 없으면 ⇪ 는 한 바이트도
  달라지지 않는다.

콘솔 접촉: 0건. ``FakeConsole`` 만 쓰고(``test_beat_grid_cells_subset`` 의 하네스를 그대로
쓴다) 앱 데이터 폴더·HTTP·HOME 은 건드리지 않는다.
"""

from __future__ import annotations

import json

import pytest

from server.design.beat_grid_cell_live import SCOPE_APPLY, SCOPE_CREATE_DELETE, SCOPE_MOVE
from server.design.send_approval import CellLiveApproval
from server.web.messages import PROTOCOL_VERSION, ProtocolError, parse_client_message

from .test_beat_grid_cells_subset import ENTRY, Applied, _applied

_APPLY = frozenset({SCOPE_APPLY})


def _raw(**fields: object) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False)


# =============================================================================
# 1. 프로토콜 — beat_grid_apply 의 live
# =============================================================================


class TestBeatGridApplyLiveMessage:
    def test_live_with_cells_is_kept_as_true(self) -> None:
        message = parse_client_message(_raw(type="beat_grid_apply", cells=[["BACK", 2]], live=True))
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_apply",
            "mode": "apply",
            "cells": [("BACK", 2)],
            "live": True,
        }

    def test_explicit_apply_mode_accepts_live(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_apply", mode="apply", cells=[["BACK", 2]], live=True)
        )
        assert message["live"] is True

    def test_live_false_leaves_no_key(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_apply", cells=[["BACK", 2]], live=False)
        )
        assert "live" not in message

    def test_without_live_the_message_is_unchanged(self) -> None:
        assert parse_client_message(_raw(type="beat_grid_apply", cells=[["BACK", 2]])) == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_apply",
            "mode": "apply",
            "cells": [("BACK", 2)],
        }
        assert parse_client_message(_raw(type="beat_grid_apply")) == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_apply",
            "mode": "apply",
        }

    @pytest.mark.parametrize("live", [True, False])
    def test_live_without_cells_is_refused(self, live: bool) -> None:
        # 곡 전체 반영에는 live 가 없다 — 있으면 승인 범위가 엉뚱한 일에 새어 나간다.
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_apply", live=live))

    @pytest.mark.parametrize("live", [1, 0, "true", "yes", None, [True], {"a": 1}])
    def test_a_non_bool_live_is_refused(self, live: object) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_apply", cells=[["BACK", 2]], live=live))

    def test_live_with_preset_plan_mode_is_refused(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(type="beat_grid_apply", mode="preset_plan", cells=[["BACK", 2]], live=True)
            )


# =============================================================================
# 2. 승인 범위 — SCOPE_APPLY
# =============================================================================


class TestScopeApply:
    def test_covers_only_after_approve(self) -> None:
        approval = CellLiveApproval()
        assert approval.covers(_APPLY) is False
        approval.approve(_APPLY)
        assert approval.covers(_APPLY) is True

    def test_approving_apply_does_not_cover_move_or_create_delete(self) -> None:
        approval = CellLiveApproval()
        approval.approve(_APPLY)
        assert approval.covers(frozenset({SCOPE_MOVE})) is False
        assert approval.covers(frozenset({SCOPE_CREATE_DELETE})) is False

    def test_approving_move_does_not_cover_apply(self) -> None:
        approval = CellLiveApproval()
        approval.approve(frozenset({SCOPE_MOVE, SCOPE_CREATE_DELETE}))
        assert approval.covers(_APPLY) is False

    def test_the_three_scope_names_are_distinct(self) -> None:
        assert len({SCOPE_APPLY, SCOPE_MOVE, SCOPE_CREATE_DELETE}) == 3


# =============================================================================
# 3. 세션 — 첫 live 는 카드, 이후는 카드 없이
# =============================================================================


def _edited(s: Applied, *edits: tuple[int, str]) -> None:
    for bar, target in edits:
        s.edit(bar, target, ENTRY)


class TestLiveApplyGate:
    def test_the_first_live_apply_asks_the_same_card_and_records_the_approval(
        self, tmp_path
    ) -> None:
        s = _applied(tmp_path)
        _edited(s, (2, "BACK"))
        assert s.store.cell_live_approval.covers(_APPLY) is False

        status = s.session.beat_grid_apply(cells=[("BACK", 2)], live=True)

        assert status["ok"] is True
        assert status["approval_vs_sent"]["match"] is True
        assert status["subset"]["applied"] == [["BACK", 2]]
        assert len(s.approval.requests) == 1  # ⇪ 와 같은 카드 한 장
        reasons = s.approval.requests[-1].items[0].risk_reasons
        assert reasons[0] == "박자 격자 칸 반영 — 선택한 1칸만 1회 승인"
        assert s.store.cell_live_approval.covers(_APPLY) is True

    def test_the_second_live_apply_goes_through_without_a_card(self, tmp_path) -> None:
        s = _applied(tmp_path)
        _edited(s, (2, "BACK"))
        assert s.session.beat_grid_apply(cells=[("BACK", 2)], live=True)["ok"] is True
        first_lines = s.lines()
        assert first_lines  # 첫 반영은 실제로 나갔다
        s.console.executed.clear()
        s.approval.requests.clear()

        _edited(s, (3, "FOH"))
        status = s.session.beat_grid_apply(cells=[("FOH", 3)], live=True)

        assert status["ok"] is True
        assert status["approval_vs_sent"]["match"] is True
        assert status["completed"] == "reflected"
        assert status["subset"]["applied"] == [["FOH", 3]]
        assert s.approval.requests == []  # 카드가 뜨지 않았다
        lines = s.lines()
        assert "Group 8 ; At Preset 4.3" in lines  # 줄은 카드 길과 같은 칸 줄이다
        assert any(line.startswith("Store Sequence 2 Cue 3 ") for line in lines)
        # 보낸 칸은 칸 기록에 올라 다시 미반영으로 남지 않는다.
        assert s.unsent() is None or {"group_name": "FOH", "bar": 3} not in s.unsent()

    def test_the_preapproved_lines_equal_what_a_card_would_have_sent(self, tmp_path) -> None:
        (tmp_path / "card").mkdir()
        (tmp_path / "live").mkdir()
        card = _applied(tmp_path / "card")
        _edited(card, (2, "BACK"))
        card.session.beat_grid_apply(cells=[("BACK", 2)])  # live 없음 — 카드 길
        card_lines = card.lines()

        live = _applied(tmp_path / "live")
        live.store.cell_live_approval.approve(_APPLY)
        _edited(live, (2, "BACK"))
        live.session.beat_grid_apply(cells=[("BACK", 2)], live=True)

        assert live.approval.requests == []
        assert live.lines() == card_lines

    def test_a_declined_card_does_not_record_the_approval(self, tmp_path) -> None:
        # 첫 True 는 하네스가 먼저 하는 전체 반영의 카드다 — 그다음 live 카드는 거절, 그다음은 승인.
        s = _applied(tmp_path, decisions=(True, False, True))
        _edited(s, (2, "BACK"))

        declined = s.session.beat_grid_apply(cells=[("BACK", 2)], live=True)

        assert declined["ok"] is False
        assert len(s.approval.requests) == 1
        assert s.lines() == []  # 거절이면 한 줄도 나가지 않았다
        assert s.store.cell_live_approval.covers(_APPLY) is False

        # 다음 live 도 다시 카드를 묻는다 — 거절이 승인으로 남지 않았다.
        retry = s.session.beat_grid_apply(cells=[("BACK", 2)], live=True)
        assert retry["ok"] is True
        assert len(s.approval.requests) == 2
        assert s.store.cell_live_approval.covers(_APPLY) is True

    def test_a_failed_card_send_does_not_record_the_approval(self, tmp_path) -> None:
        s = _applied(tmp_path)
        _edited(s, (2, "BACK"))
        s.console.fail_on["Group 7 ; At Preset 4.2"] = "console refused"

        status = s.session.beat_grid_apply(cells=[("BACK", 2)], live=True)

        assert status["ok"] is False
        assert len(s.approval.requests) == 1  # 카드는 승인됐지만 송신이 실패했다
        assert s.store.cell_live_approval.covers(_APPLY) is False

    def test_a_failed_preapproved_send_reports_the_same_not_executed_error(self, tmp_path) -> None:
        s = _applied(tmp_path)
        s.store.cell_live_approval.approve(_APPLY)
        _edited(s, (2, "BACK"))
        before_snapshot = dict(s.store.beat_grid_snapshots)
        s.console.fail_on["Group 7 ; At Preset 4.2"] = "console refused"

        status = s.session.beat_grid_apply(cells=[("BACK", 2)], live=True)

        assert status["ok"] is False
        assert "콘솔 반영이 실행되지 않았습니다" in status["reason"]
        assert s.approval.requests == []
        # 실패했으니 칸 기록은 그대로다 — 이 칸은 계속 미반영으로 남는다.
        assert dict(s.store.beat_grid_snapshots) == before_snapshot
        assert {"group_name": "BACK", "bar": 2} in (s.unsent() or [])

    def test_the_preapproved_verification_ignores_the_backup_line(
        self, tmp_path, monkeypatch
    ) -> None:
        # 쇼 백업 줄(SaveShow)은 카드 길의 게이트만 보낸다. 승인된 길은 백업을 하지 않으므로,
        # 승인 쪽 목록에도 그 줄이 없어야 대조가 맞는다(있으면 「승인만 있고 보내지 않은 줄」로
        # 어긋난다).
        s = _applied(tmp_path)
        s.store.cell_live_approval.approve(_APPLY)
        _edited(s, (2, "BACK"))
        monkeypatch.setattr(s.session, "_beat_grid_gate_backup_lines", lambda: ("SaveShow",))

        status = s.session.beat_grid_apply(cells=[("BACK", 2)], live=True)

        assert status["ok"] is True
        assert status["approval_vs_sent"]["match"] is True
        assert status["approval_vs_sent"]["approved_not_sent"] == []

    def test_without_live_the_card_is_asked_every_time_and_nothing_is_recorded(
        self, tmp_path
    ) -> None:
        s = _applied(tmp_path)
        _edited(s, (2, "BACK"), (3, "FOH"))

        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        assert s.session.beat_grid_apply(cells=[("FOH", 3)])["ok"] is True

        assert len(s.approval.requests) == 2  # ⇪ 는 매번 카드다
        assert s.store.cell_live_approval.covers(_APPLY) is False

    def test_a_live_approval_does_not_waive_the_card_for_the_plain_button(self, tmp_path) -> None:
        s = _applied(tmp_path)
        s.store.cell_live_approval.approve(_APPLY)
        _edited(s, (2, "BACK"))

        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True  # live 없음

        assert len(s.approval.requests) == 1  # ⇪ 는 여전히 카드를 묻는다

    def test_an_approval_for_moves_does_not_waive_the_card_for_live_apply(self, tmp_path) -> None:
        s = _applied(tmp_path)
        s.store.cell_live_approval.approve(frozenset({SCOPE_MOVE, SCOPE_CREATE_DELETE}))
        _edited(s, (2, "BACK"))

        assert s.session.beat_grid_apply(cells=[("BACK", 2)], live=True)["ok"] is True

        assert len(s.approval.requests) == 1
        assert s.store.cell_live_approval.covers(_APPLY) is True

"""SPEC-LDBEAT-001 M4 — 승인 단위 (카드 t549, REQ-LDBEAT-012, AC-LDBEAT-002(b),
AC-LDBEAT-015).

콘솔 접촉 0건 — 순수 상태 객체 + 순수 함수뿐이다.

- `build_write_approval_batch` — N≥2개의 격자 칸 배치여도 승인 아티팩트는
  정확히 1개다(REQ-LDBEAT-012(a), AC-LDBEAT-015).
- `PreviewApprovalSession` — 미리보기(Goto Cue/Off Sequence)는 세션 시작
  때 1회만 승인받는다. 쓰기는 이 세션과 무관하게 매번 승인받는다
  (REQ-LDBEAT-012(b), AC-LDBEAT-002(b)) — 이 클래스는 쓰기 승인을 **절대**
  대신하지 않는다.
"""

from __future__ import annotations

from server.design.send_approval import PreviewApprovalSession, build_write_approval_batch


class TestBuildWriteApprovalBatch:
    def test_single_cell_produces_one_artifact(self) -> None:
        batch = build_write_approval_batch([("Store Sequence 1", "Off Sequence 1")])
        assert batch.cell_count == 1
        assert batch.commands == ("Store Sequence 1", "Off Sequence 1")

    def test_n_cells_still_produce_exactly_one_artifact(self) -> None:
        cells = [
            ("Store Sequence 1",),
            ("Store Sequence 2", "Store Cue 1 Sequence 2"),
            ("Assign Sequence 1 At Timecode 30",),
        ]
        batch = build_write_approval_batch(cells)
        assert batch.cell_count == 3
        total_commands = sum(len(cell) for cell in cells)
        assert len(batch.commands) == total_commands
        # 한 파일에 전부 들어간다(순서 보존, 칸 경계 없음).
        assert batch.commands == (
            "Store Sequence 1",
            "Store Sequence 2",
            "Store Cue 1 Sequence 2",
            "Assign Sequence 1 At Timecode 30",
        )

    def test_sha256_is_over_the_full_batch_text(self) -> None:
        import hashlib

        cells = [("A",), ("B",)]
        batch = build_write_approval_batch(cells)
        expected = hashlib.sha256(b"A\nB\n").hexdigest()
        assert batch.sha256 == expected

    def test_empty_cells_produce_zero_commands_but_still_one_artifact(self) -> None:
        batch = build_write_approval_batch([(), ()])
        assert batch.cell_count == 2
        assert batch.commands == ()


class TestPreviewApprovalSession:
    def test_fresh_session_is_not_approved(self) -> None:
        session = PreviewApprovalSession()
        assert session.is_approved is False
        assert session.authorize_preview() is False

    def test_approve_once_authorizes_every_subsequent_preview_call(self) -> None:
        session = PreviewApprovalSession()
        session.approve()
        assert session.is_approved is True
        # 반복 호출(N>=2) 모두 재승인 프롬프트 없이 통과한다.
        assert session.authorize_preview() is True
        assert session.authorize_preview() is True
        assert session.authorize_preview() is True

    def test_preview_approval_does_not_leak_into_a_write_approval_flag(self) -> None:
        # REQ-LDBEAT-012(b) — 미리보기 승인은 (a)의 쓰기 승인을 대체하지
        # 않는다. 이 클래스에는 "쓰기 승인됨" 개념 자체가 없다(writes go
        # through build_write_approval_batch + an external approval record).
        session = PreviewApprovalSession()
        session.approve()
        assert not hasattr(session, "write_approved")

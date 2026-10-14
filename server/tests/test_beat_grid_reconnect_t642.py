"""카드 t642 — 콘솔 재연결(=새 WebSocket) 뒤 박자 격자 「끄기」·「미리보기」가
**반영 번호를 잃는** 결함의 재현 시험 (RED 단계).

``ChatSession._beat_grid_applied`` 는 가장 최근 「콘솔에 반영」이 실제로 쓴 시퀀스·큐
번호를 쥔다. 이 필드는 연결(=세션)마다 ``None`` 으로 새로 만들어지고 저장소
(``SongTimelineStore``)에서 복원되지 않는다. 재연결하면 ``server/web/app.py`` 가 새
``ChatSession`` 을 만들므로, 콘솔에는 반영한 시퀀스가 그대로 남아 있는데도 새 세션은
「아직 콘솔에 반영된 적이 없다」고 답하며 ``Off Sequence`` / ``Goto Cue`` 를 보내지 못한다.
재연결을 살아남는 것은 두 세션이 함께 쥔 ``SongTimelineStore`` 뿐이다(t635 가 곡별
스냅샷을 저장소로 옮긴 것과 같은 모양).

구성은 t635 시험과 같다: 한 ``SongTimelineStore`` 를 공유하는 두 ``ChatSession``.
세션 A = 재연결 전, 세션 B = 같은 저장소 위에 새로 만든 재연결 뒤 세션.
이 파일은 단위 층이다 — 실제 WebSocket 재연결 경로는 재지 않는다.

콘솔 접촉: 0건. ``FakeConsole``(승인=송신 각본)만 쓰고 실기 포트로는 한 바이트도
나가지 않는다. 반영 번호는 필드를 직접 쓰지 않고 실제 ``beat_grid_apply`` 성공 경로로만
만든다.
"""

from __future__ import annotations

from server.web.session import SongTimelineStore

from .test_beat_grid_send_t563 import _new_session, _timeline


def _applied_session_a(tmp_path):
    """세션 A(재연결 전) — 실제 「콘솔에 반영」을 마친 세션과 그 저장소를 돌려준다."""
    store = SongTimelineStore()
    store.latest = _timeline()
    session_a, _console_a, _approval_a, _audit_a = _new_session(tmp_path, store=store)
    applied = session_a.beat_grid_apply()
    # 전제: 반영이 승인=송신까지 정말 성공했다. 이 줄이 빠지면 아래 실패가 「반영이
    # 안 됐다」와 구별되지 않아 재연결 때문이라는 주장이 공허해진다.
    assert applied["ok"] is True
    return store, session_a


class TestOffAndPreviewAfterReconnect:
    def test_off_after_reconnect_still_turns_off_applied_sequences(self, tmp_path):
        store, _session_a = _applied_session_a(tmp_path)

        # 재연결 — 같은 저장소 위의 새 ChatSession, 새 FakeConsole. 콘솔 쪽에는 반영한
        # 시퀀스가 그대로 남아 있다고 보는 것이 이 시험의 전제다.
        session_b, console_b, _approval_b, _audit_b = _new_session(tmp_path, store=store)
        event = session_b.beat_grid_preview_off()

        # 결함: 새 세션은 번호를 잃어 「아직 반영된 적이 없다」며 거절한다. ok 플래그와
        # 실제로 나간 명령 둘 다 단언한다 — 거절하면서 명령도 0줄이어야 정직하므로,
        # 고쳐진 뒤에는 ok=True 이고 Off Sequence 가 콘솔로 나가야 한다.
        assert event["ok"] is True, f"재연결 뒤 끄기가 거절됨: {event.get('reason')}"
        assert any("Off Sequence" in command for command in console_b.executed), (
            f"재연결 뒤 Off Sequence 가 나가지 않음 — executed: {console_b.executed}"
        )

    def test_preview_after_reconnect_still_goes_to_applied_cues(self, tmp_path):
        store, _session_a = _applied_session_a(tmp_path)

        session_b, console_b, _approval_b, _audit_b = _new_session(tmp_path, store=store)
        # 1마디는 반영한 곡의 BACK 트랙 큐가 실제로 담당하는 마디다(``_timeline`` 의 cues).
        event = session_b.beat_grid_preview(1)

        # 결함: 새 세션은 큐 번호를 잃어 미리보기를 거절한다. 고쳐진 뒤에는 ok=True 이고
        # 반영한 큐로 Goto Cue 가 콘솔로 나가야 한다.
        assert event["ok"] is True, f"재연결 뒤 미리보기가 거절됨: {event.get('reason')}"
        assert any("Goto Cue" in command for command in console_b.executed), (
            f"재연결 뒤 Goto Cue 가 나가지 않음 — executed: {console_b.executed}"
        )


class TestSameSessionControl:
    def test_off_in_same_session_after_apply_control(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _timeline()
        session_a, console_a, _approval_a, _audit_a = _new_session(tmp_path, store=store)
        assert session_a.beat_grid_apply()["ok"] is True

        # 대조군: 재연결 없이 같은 세션에서 끄면 된다. 이 시험이 통과해야 위 두 시험의
        # 실패가 「끄기 경로에 못 닿는 하네스」가 아니라 재연결 때문이라고 말할 수 있다.
        event = session_a.beat_grid_preview_off()
        assert event["ok"] is True, f"같은 세션 끄기가 거절됨: {event.get('reason')}"
        assert any("Off Sequence" in command for command in console_a.executed), (
            f"같은 세션 Off Sequence 가 나가지 않음 — executed: {console_a.executed}"
        )

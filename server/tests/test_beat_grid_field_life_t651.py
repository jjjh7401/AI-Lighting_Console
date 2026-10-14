"""카드 t651 — 박자 격자 재연결 뒤 세션 필드 수명 점검: 필드마다 재현 시험.

카드 t642 가 ``_beat_grid_applied`` 를 저장소(``SongTimelineStore``)로 옮긴 뒤, 같은 질문을
나머지 세션 필드에 던진다. 재연결(=새 WebSocket)은 ``server/web/app.py`` 가 새
``ChatSession`` 을 만드는 일이라, 세션 필드는 연결마다 비고 저장소는 살아남는다. 필드마다
사용자에게 보이는 결함인지 가린다.

- ``_beat_grid_pool_slots`` (콘솔 프리셋 풀의 마지막 완전 판독) — **결함**. 연결 때 보내는
  재생 프레임(``song_timeline_replay``, app.py 489행)의 빈 프리셋 표식은 이 메모리로 갈라지는데,
  새 세션 메모리는 비어 있어 표식이 0개로 나간다. 콘솔 풀은 그대로인데 표식이 사라진다 (RED).
- ``_beat_grid_empty_marks`` (곡마다 마지막으로 내보낸 표식의 기억) — **결함 아님**. 재생 때
  파생 값으로 다시 써지므로 클라이언트가 보는 값과 같이 간다. 재연결 뒤 읽기가 다시 보낸다 (대조군).
- ``_beat_grid_suggestions`` (보류 중인 AI 제안) — **조건부 결함**. 재연결하면 서버의 보류 목록은
  비고 클라이언트 카드는 남는다. 「적용」은 「이미 적용됐거나 만료됐습니다」라는 틀린 사유로
  거절된다. 현재 빌드는 제안 소스가 ``NullSuggestionSource`` 뿐이라 카드가 생기지 않는다.
  특성 시험으로 현재 동작을 고정한다. 기대 동작은 제품 결정이다.

콘솔 접촉: 0건. ``FakeConsole`` 만 쓴다. WebSocket 배선(app.py 489행)은 읽기만 했고 돌리지 않았다.
"""

from __future__ import annotations

import json

from server.web.session import SongTimelineStore

from . import test_session_beat_grid_edit_t551 as t551
from .test_apply_time_approval_t577 import _new_session as _new_session_t577
from .test_apply_time_approval_t577 import _timeline as _timeline_t577
from .test_beat_grid_send_t563 import _timeline as _timeline_t563


def _cue_timeline():
    """BACK bar 1 에 빈 효과 번호(4.99) 하나만 둔 격자.

    풀 4 는 21 만 있으니 4.99 는 빈 번호다.
    """
    timeline = _timeline_t577()
    timeline["beat_grid"]["tracks"][0]["cues"] = [
        {"bar": 1, "effect_preset_no": "4.99", "effect_kind": "position", "evidence": None},
    ]
    return timeline


def _marked_bars(event: dict) -> list[int]:
    return [cell["bar"] for cell in event["timeline"]["beat_grid"]["empty_preset_cells"]]


def _text(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False, default=str)


def _suggest_source(grid, bar, target):
    """제안 소스 더블 — 항상 같은 편집을 제안한다(``SuggestionSource`` 계약)."""
    return ({"effect_preset_no": "4.21"}, "재연결 시험용 제안")


class TestEmptyPresetMarksAcrossReconnect:
    """``_beat_grid_pool_slots`` — 결함.

    표식은 풀 판독에서 오는데, 그 판독 기억이 연결에 갇혀 있다.
    """

    def test_control_same_session_replay_keeps_the_marks(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        # 전제: 반영(=풀 판독)이 이 세션의 풀 메모리를 채운다. 이 줄이 빠지면 아래 RED 가
        # 「판독 전이라 표식이 없다」와 구별되지 않는다.
        session_a.beat_grid_apply()
        assert _marked_bars(session_a.song_timeline_replay()) == [1]

    def test_marks_come_back_once_the_new_session_reads_the_pool(self, tmp_path):
        # 원인 되묻기: 표식을 잃는 게 풀 메모리 탓인지 확인한다.
        # 콘솔·저장소는 그대로 두고, 새 세션이 풀을 한 번 읽기만 해도
        # 같은 재생 경로가 표식을 되살린다 → 원인은 세션 메모리다.
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        session_a.beat_grid_apply()

        session_b, _console_b, _approval_b, _audit_b = _new_session_t577(tmp_path, store=store)
        # 재연결 직후에는 풀 메모리가 비어 표식이 없다.
        assert _marked_bars(session_b.song_timeline_replay()) == []
        session_b.beat_grid_apply()  # 같은 콘솔을 한 번 읽는다
        assert _marked_bars(session_b.song_timeline_replay()) == [1]

    def test_marks_survive_a_new_connection_while_the_console_is_unchanged(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        session_a.beat_grid_apply()
        # 대조군: 같은 연결에서는 표식이 나간다.
        assert _marked_bars(session_a.song_timeline_replay()) == [1]

        # 재연결: 같은 저장소 위의 새 ChatSession, 새 FakeConsole.
        # 콘솔 풀은 _state_tree() 그대로다.
        session_b, _console_b, _approval_b, _audit_b = _new_session_t577(tmp_path, store=store)
        marked = _marked_bars(session_b.song_timeline_replay())

        # 결함: 새 세션은 풀을 읽은 적이 없어 재생 프레임에 표식 0개를 싣는다. 콘솔은 그대로인데
        # 표식이 사라진다. 고쳐지면 bar 1 표식이 그대로 나가야 한다.
        assert marked == [1], f"재연결 뒤 빈 프리셋 표식이 사라짐 — 재생 프레임 표식 bar: {marked}"


class TestEmptyMarkMemoAfterReconnect:
    """``_beat_grid_empty_marks`` — 결함 아님(대조군).

    곡마다 마지막으로 보낸 표식을 기억하는 메모일 뿐이다.
    """

    def test_a_read_after_reconnect_resends_the_marks_the_client_lacks(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        session_a.beat_grid_apply()

        sent_b: list[dict] = []
        session_b, _console_b, _approval_b, _audit_b = _new_session_t577(
            tmp_path, store=store, sent=sent_b
        )
        # 재연결 재생 — 이 시점 클라이언트가 가진 표식은 0개다(위 결함 시험과 같은 이유).
        assert _marked_bars(session_b.song_timeline_replay()) == []
        sent_b.clear()

        # 재연결 뒤 반영 시도가 풀을 다시 읽으면, 기억이 비어 있어도 표식을 다시 실어야 한다.
        session_b.beat_grid_apply()
        resent = [event for event in sent_b if event.get("type") == "song_timeline"]
        assert any(_marked_bars(event) == [1] for event in resent), (
            f"재연결 뒤 읽기가 표식을 다시 보내지 않음 — song_timeline 이벤트 {len(resent)}건"
        )


class TestPendingSuggestionAcrossReconnect:
    """``_beat_grid_suggestions`` — 조건부 결함.

    현재 빌드에서는 도달하지 않고, 제안 소스가 붙으면 결함이다.
    """

    def test_default_source_creates_no_pending_suggestion_in_this_build(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _timeline_t563()
        # 소스를 넘기지 않는다 — 운영 경로(app.py)도 넘기지 않는다. 기본값은 NullSuggestionSource.
        session, _console = t551._new_session(tmp_path, store=store)
        event = session.beat_grid_suggest(1, "BACK")
        assert "suggestion_id" not in event
        assert "제안 없음" in _text(event)

    def test_same_connection_apply_finds_the_pending_suggestion(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _timeline_t563()
        session_a, _console_a = t551._new_session(
            tmp_path, store=store, suggestion_source=_suggest_source
        )
        suggestion_id = session_a.beat_grid_suggest(1, "BACK")["suggestion_id"]
        applied = session_a.beat_grid_suggestion_apply(suggestion_id)
        # 대조군: 같은 연결에서는 제안을 찾는다.
        # 아래 거절이 재연결 때문이라고 말하려면 이 줄이 필요하다.
        assert "찾을 수 없습니다" not in _text(applied)

    def test_apply_after_reconnect_is_refused_with_a_misleading_reason(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _timeline_t563()
        session_a, _console_a = t551._new_session(
            tmp_path, store=store, suggestion_source=_suggest_source
        )
        suggestion_id = session_a.beat_grid_suggest(1, "BACK")["suggestion_id"]

        sent_b: list[dict] = []
        session_b, _console_b = t551._new_session(
            tmp_path, store=store, sent=sent_b, suggestion_source=_suggest_source
        )
        applied = session_b.beat_grid_suggestion_apply(suggestion_id)

        # 특성 시험: 현재 동작을 고정한다. 서버는 재연결로 보류 목록을 잃고 「이미 적용됐거나
        # 만료됐습니다」로 거절한다 — 원인이 틀린 사유다. 기대 동작(연결을 넘겨 살릴지, 클라이언트가
        # 재연결 때 카드를 지울지)은 제품 결정이다. 결정이 나면 이 단언을 바꾼다.
        assert "찾을 수 없습니다" in _text(applied)
        assert any(event.get("type") == "beat_grid_suggestion_consumed" for event in sent_b)

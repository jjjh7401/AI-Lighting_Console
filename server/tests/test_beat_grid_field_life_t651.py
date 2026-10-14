"""카드 t651 — 박자 격자 재연결 뒤 세션 필드 수명: 재현 시험과 수정 A 의 시험.

카드 t642 가 ``_beat_grid_applied`` 를 저장소(``SongTimelineStore``)로 옮긴 뒤,
같은 질문을 나머지 세션 필드에 던졌다. 재연결(=새 WebSocket)은
``server/web/app.py`` 가 새 ``ChatSession`` 을 만드는 일이라, 세션 필드는
연결마다 비고 저장소는 살아남는다.

- ``_beat_grid_pool_slots`` (콘솔 프리셋 풀의 마지막 완전 판독) — **결함, 고침**.
  재연결 뒤 「빈 프리셋」 표식이 0개로 나가던 것을 저장소(프로세스 단위)로 옮겨
  막았다(카드 t651 수정 A). 판독 시각(``empty_preset_read_at``)을 함께 싣는다.
  송신 성공으로 만든 번호(추정)는 판독 시각을 바꾸지 않는다(카드 t595 구별).
- ``_beat_grid_empty_marks`` (곡마다 마지막으로 내보낸 표식의 기억) — **결함 아님**.
  연결마다 새로 만들고, 재생 프레임이 현재 표식으로 다시 쓴다. 그대로 둔다.
- ``_beat_grid_suggestions`` (보류 중인 AI 제안) — **조건부 결함, 별도 카드**.
  감독 결정: 연결 수명, 재연결하면 버린다. 특성 시험은 현재 동작을 고정한 채 둔다.
- 로드 응답(``POST /api/timelines/{id}/load``)도 같은 풀 기억을 쓴다 —
  재생 프레임과 같은 표식을 싣는다(``TestLoadResponseParity``).

콘솔 접촉: 0건. ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi.testclient import TestClient

from server.web.app import create_app
from server.web.session import SongTimelineStore

from . import test_session_beat_grid_edit_t551 as t551
from .test_apply_time_approval_t577 import _new_session as _new_session_t577
from .test_apply_time_approval_t577 import _state_tree
from .test_apply_time_approval_t577 import _timeline as _timeline_t577
from .test_beat_grid_send_t563 import _timeline as _timeline_t563
from .test_web_beat_grid_send_t563 import _deps as _web_deps


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
    """``_beat_grid_pool_slots`` — 결함, 수정 A 로 고침.

    표식은 풀 판독에서 오는데, 그 판독 기억이 연결에 갇혀 있었다. 이제 저장소에 있다.
    """

    def test_control_same_session_replay_keeps_the_marks(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        # 전제: 반영(=풀 판독)이 풀 메모리를 채운다. 이 줄이 빠지면 아래 시험이
        # 「판독 전이라 표식이 없다」와 구별되지 않는다.
        session_a.beat_grid_apply()
        assert _marked_bars(session_a.song_timeline_replay()) == [1]

    def test_a_never_read_store_gives_no_marks_on_connect(self, tmp_path):
        # 대조군: 판독 전에는 표식이 없다. 저장소를 나눠도 없는 표식이 생기지는 않는다.
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session, _console, _approval, _audit = _new_session_t577(tmp_path, store=store)
        grid = session.song_timeline_replay()["timeline"]["beat_grid"]
        assert grid["empty_preset_cells"] == []
        assert "empty_preset_read_at" not in grid  # 판독이 없으면 시각 키도 없다(옛 응답과 같다)

    def test_marks_survive_a_new_connection_while_the_console_is_unchanged(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        session_a.beat_grid_apply()
        assert _marked_bars(session_a.song_timeline_replay()) == [1]

        # 재연결: 같은 저장소 위의 새 ChatSession, 새 FakeConsole. 콘솔 풀은 그대로다.
        session_b, _console_b, _approval_b, _audit_b = _new_session_t577(tmp_path, store=store)
        marked = _marked_bars(session_b.song_timeline_replay())

        # 수정 A 전에는 이 단언이 RED 였다(새 세션이 빈 메모리로 표식 0개를 실었다).
        # 고쳐진 뒤에는 bar 1 표식이 그대로 나간다.
        assert marked == [1], f"재연결 뒤 빈 프리셋 표식이 사라짐 — 재생 프레임 표식 bar: {marked}"

    def test_replay_says_when_the_marks_were_read(self, tmp_path):
        # 5절 위험의 처방: 표식이 기대는 판독의 시각을 재생 프레임이 싣는다.
        # 판독한 풀만 싣고, 값은 UTC 오프셋이 붙은 ISO 8601 시각이다.
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        session_a.beat_grid_apply()

        session_b, _console_b, _approval_b, _audit_b = _new_session_t577(tmp_path, store=store)
        grid = session_b.song_timeline_replay()["timeline"]["beat_grid"]
        read_at = grid["empty_preset_read_at"]
        assert set(read_at) == {"4"}
        assert datetime.fromisoformat(read_at["4"]).utcoffset() is not None


class TestEmptyMarkMemoAfterReconnect:
    """``_beat_grid_empty_marks`` — 결함 아님(대조군).

    곡마다 마지막으로 보낸 표식을 기억하는 메모다. 연결마다 새로 만들어지고, 재생이
    현재 표식으로 다시 쓰므로 클라이언트가 보는 값과 어긋나지 않는다.
    """

    def test_a_console_change_after_reconnect_still_resends_the_marks(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        session_a.beat_grid_apply()  # 풀 4 = {21} 을 저장소에 판독해 둔다

        # 재연결 B 의 콘솔: 풀 4 에 99 가 생겼다 → 4.99 는 이제 빈 번호가 아니다.
        tree = _state_tree()
        tree["DataPool/PresetPools/4"] = {
            "children": [{"i": 21, "name": "P21"}, {"i": 99, "name": "P99"}]
        }
        sent_b: list[dict] = []
        session_b, _console_b, _approval_b, _audit_b = _new_session_t577(
            tmp_path, store=store, sent=sent_b, state_tree=tree
        )
        # 재연결 재생은 저장소 기억 [1] 을 준다 — 클라이언트가 지금 보는 값이다.
        assert _marked_bars(session_b.song_timeline_replay()) == [1]
        sent_b.clear()

        # 읽기: 콘솔이 바뀌었으니 표식이 사라져야 하고, 메모와 달라졌으므로 격자를 다시 보내야 한다.
        session_b.beat_grid_apply()
        resent = [event for event in sent_b if event.get("type") == "song_timeline"]
        assert any(_marked_bars(event) == [] for event in resent), (
            f"콘솔 변화가 격자로 다시 나가지 않음 — song_timeline 이벤트 {len(resent)}건"
        )


class TestCreationEstimateAcrossConnections:
    """카드 t595 의 구별을 잰다 — 추정은 판독이 아니다.

    송신 성공으로 만든 번호(추정)는 저장소에 남아 새 연결에도 「있음」으로 보이고,
    판독 시각은 추정으로 바뀌지 않는다.
    """

    def test_a_creation_estimate_survives_and_keeps_the_read_time(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _cue_timeline()
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        session_a.beat_grid_apply()  # 실제 판독: 풀 4 = {21}
        grid = session_a.song_timeline_replay()["timeline"]["beat_grid"]
        read_at = grid["empty_preset_read_at"]

        # 추정: 4.99 를 만들었다(송신 성공의 결과). 같은 연결에서는 표식이 사라진다.
        session_a._beat_grid_note_created_presets(["4.99"])  # 카드 t595 시험과 같은 진입점
        same = session_a.song_timeline_replay()["timeline"]["beat_grid"]
        assert same["empty_preset_cells"] == []
        assert same["empty_preset_read_at"] == read_at  # 추정은 판독 시각을 바꾸지 않는다

        # 새 연결: 추정은 저장소에 남아 있다 — 표식은 여전히 없고 시각도 그대로다.
        session_b, _console_b, _approval_b, _audit_b = _new_session_t577(tmp_path, store=store)
        replayed = session_b.song_timeline_replay()["timeline"]["beat_grid"]
        assert replayed["empty_preset_cells"] == []
        assert replayed["empty_preset_read_at"] == read_at


class TestLoadResponseParity:
    """REST 층 — 「불러오기」 응답의 표식은 새 연결의 첫 재생 프레임과 같다(카드 t651).

    두 길은 같은 저장소와 같은 풀 기억을 읽는다. 모양만 같고 표식이 다르면 같은 곡이
    들어온 길에 따라 달리 보인다. 로드 응답 주석이 약속한 「첫 재생 프레임과 같은 상태」를
    단언한다.
    """

    def test_load_response_and_connect_replay_show_the_same_marks(self, tmp_path):
        deps = _web_deps(tmp_path)
        store = deps.song_timeline_store
        store.latest = _cue_timeline()
        # 콘솔 풀 4 를 한 번 읽는다(반영 경로). 같은 저장소의 기억이라 두 길이 모두 본다.
        session_a, _console_a, _approval_a, _audit_a = _new_session_t577(tmp_path, store=store)
        session_a.beat_grid_apply()

        with TestClient(create_app(deps)) as client:
            saved = client.post("/api/timelines", json={"name": "t651 표식 패리티"})
            assert saved.status_code == 200, saved.text
            loaded = client.post(f"/api/timelines/{saved.json()['item']['id']}/load")
        assert loaded.status_code == 200, loaded.text
        load_cells = loaded.json()["timeline"]["beat_grid"]["empty_preset_cells"]

        session_b, _console_b, _approval_b, _audit_b = _new_session_t577(tmp_path, store=store)
        replay_cells = session_b.song_timeline_replay()["timeline"]["beat_grid"][
            "empty_preset_cells"
        ]

        # 대조군: 두 길 모두 표식 bar 1 을 실제로 싣는다. 빈 응답끼리 같아서 통과하는 일은 없다.
        assert [cell["bar"] for cell in replay_cells] == [1]
        assert load_cells == replay_cells


class TestPendingSuggestionAcrossReconnect:
    """``_beat_grid_suggestions`` — 조건부 결함, 별도 카드.

    현재 빌드에서는 도달하지 않고, 제안 소스가 붙으면 결함이다. 감독 결정(연결 수명,
    재연결하면 버린다)은 별도 카드로 뺐다. 여기서는 현재 동작을 고정만 한다.
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
        # 만료됐습니다」로 거절한다 — 원인이 틀린 사유다. 기대 동작(클라이언트가 재연결 때 카드를
        # 지우는지)은 별도 카드에서 정한다. 그 카드에서 이 단언을 바꾼다.
        assert "찾을 수 없습니다" in _text(applied)
        assert any(event.get("type") == "beat_grid_suggestion_consumed" for event in sent_b)

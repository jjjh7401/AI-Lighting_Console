"""SPEC-LDBEAT-001 M3 — 박자 격자 편집 세 길의 서버 진입점 배선 (카드
t551 후속, 리드 지시 — "편집 세 길이 전부 서버 연산에 도달하게").

``server/web/session.py`` 의 ``beat_grid_edit``/``beat_grid_suggest``/
``beat_grid_suggestion_apply`` 세 메서드만 다룬다 — 채팅 디스패치 체인
(``run_instruction``, ``_cue_sheet_draft_edit`` 등)을 거치지 않는 **전용
경로**다(AC-LDBEAT-005). ``FakeConsole.executed == []``로 콘솔 무접촉을
직접 잰다(``test_session_bar_map_store.py``와 같은 관행).

AC-LDBEAT-005: 세 편집 경로(직접 고르기=changes, 문장=sentence, AI 제안=
apply)가 전부 같은 새 서버 연산(``apply_beat_grid_edit``)을 거친다 —
호출 스택이 그 연산을 지난다는 것을 성공 결과의 report 내용으로 간접
확인한다(새 연산만이 "~마디 ~ 수정" 보고 문자열을 만든다). AI 제안은
「적용」전까지 상태 diff 0.
AC-LDBEAT-010: 거절 사유 문자열이 이벤트 text에 그대로(verbatim) 실린다.
"""

from __future__ import annotations

import copy

import pytest

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole


class RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("이 경로는 모델을 부르지 않는다")


def _timeline(**overrides: object) -> dict:
    base = {"song_title": "LOVE ATTACK", "sequence_number": 210}
    base.update(overrides)
    return base


def _new_session(
    tmp_path, *, store: SongTimelineStore, sent: list[dict] | None = None, suggestion_source=None
):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    kwargs: dict[str, object] = {}
    if suggestion_source is not None:
        kwargs["beat_grid_suggestion_source"] = suggestion_source
    session = ChatSession(
        gate=gate,
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=(sent.append if sent is not None else (lambda event: None)),
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
        **kwargs,
    )
    return session, console


@pytest.fixture
def harness(tmp_path):
    store = SongTimelineStore()
    store.latest = _timeline()
    sent: list[dict] = []
    session, console = _new_session(tmp_path, store=store, sent=sent)
    return session, console, store, sent


def _texts(sent: list[dict]) -> list[str]:
    return [event["text"] for event in sent if "text" in event]


# -- 경로 ① 직접 고르기(changes) ----------------------------------------------


class TestDirectPickPath:
    def test_valid_changes_edits_the_grid_through_the_new_op(self, harness) -> None:
        session, console, store, sent = harness
        event = session.beat_grid_edit(
            bar=7, target="BACK", changes={"entry": {"fade_bars": 2, "mib_mode": None}}
        )
        assert event["status"] == "ok"
        grid = store.latest["beat_grid"]
        back = next(t for t in grid["tracks"] if t["group_name"] == "BACK")
        cue = next(c for c in back["cues"] if c["bar"] == 7)
        assert cue["entry"]["fade_bars"] == 2
        assert console.executed == []

    def test_rejection_reason_reaches_the_event_text_verbatim(self, harness) -> None:
        # AC-LDBEAT-010 — 거절 사유 문자열이 그대로 노출된다.
        session, console, store, sent = harness
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_edit(bar=7, target="BACK", changes={"not_a_real_field": 1})
        assert "not_a_real_field" in event["text"]
        assert "콘솔에는 아무것도 쓰지 않았습니다" in event["text"]
        assert store.latest == before  # 거절 시 격자 상태 변경 0건
        assert console.executed == []

    def test_unknown_target_rejection_names_known_tracks(self, harness) -> None:
        session, console, store, sent = harness
        event = session.beat_grid_edit(
            bar=7, target="NO-SUCH-GROUP", changes={"entry": {"fade_bars": 1, "mib_mode": None}}
        )
        assert "NO-SUCH-GROUP" in event["text"]
        assert console.executed == []

    def test_no_timeline_refuses_without_console_contact(self, tmp_path) -> None:
        store = SongTimelineStore()  # latest 는 None
        session, console = _new_session(tmp_path, store=store)
        event = session.beat_grid_edit(bar=7, target="BACK", changes={"entry": {"fade_bars": 1}})
        assert "박자 격자가 아직 없습니다" in event["text"] or "타임라인" in event["text"]
        assert console.executed == []


# -- 경로 ② 문장(sentence) ----------------------------------------------------


class TestSentencePath:
    def test_valid_sentence_edits_the_grid(self, harness) -> None:
        session, console, store, sent = harness
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="7마디 BACK 위치를 2.9로"
        )
        assert event["status"] == "ok"
        grid = store.latest["beat_grid"]
        back = next(t for t in grid["tracks"] if t["group_name"] == "BACK")
        cue = next(c for c in back["cues"] if c["bar"] == 7)
        assert cue["position_preset_no"] == "2.9"
        assert console.executed == []

    def test_unparseable_sentence_is_a_single_cause_rejection(self, harness) -> None:
        session, console, store, sent = harness
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="오늘 날씨가 좋습니다"
        )
        assert "문장" in event["text"]
        assert store.latest == before
        assert console.executed == []

    def test_range_sentence_edits_every_existing_cue_in_bounds(self, harness) -> None:
        # mockup 명령창 기본값과 같은 범위 모양("22~25마디 ...") — MOVER-U 는
        # 3·7·11·14마디에 큐가 있다.
        session, console, store, sent = harness
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="3~14마디 MOVER-U 밝기를 55%로"
        )
        assert event["status"] == "ok"
        grid = store.latest["beat_grid"]
        mover_u = next(t for t in grid["tracks"] if t["group_name"] == "MOVER-U")
        for bar in (3, 7, 11, 14):
            cue = next(c for c in mover_u["cues"] if c["bar"] == bar)
            assert cue["brightness"]["value_percent"] == 55
        assert console.executed == []

    def test_range_sentence_with_no_matching_cues_is_rejected(self, harness) -> None:
        session, console, store, sent = harness
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="100~110마디 MOVER-U 밝기를 55%로"
        )
        assert "100" in event["text"] and "110" in event["text"]
        assert store.latest == before
        assert console.executed == []


# -- 경로 ③ AI 제안(suggest → apply) -----------------------------------------


def _deterministic_test_double(grid, bar, target):
    """AI 가 아니다 — 결정적 테스트 더블."""
    return (
        {"brightness": {"mode": "value", "value_percent": 61, "preset_no": None}},
        "결정적 테스트 더블 제안(AI 아님)",
    )


class TestAiSuggestionPath:
    def test_null_source_reports_no_suggestion_without_touching_state(self, harness) -> None:
        session, console, store, sent = harness
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_suggest(bar=7, target="BACK")
        assert store.latest == before
        assert console.executed == []
        assert event is not None

    def test_suggestion_creation_does_not_mutate_grid_state(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        sent: list[dict] = []
        session, console = _new_session(
            tmp_path, store=store, sent=sent, suggestion_source=_deterministic_test_double
        )
        before = copy.deepcopy(store.latest)
        session.beat_grid_suggest(bar=7, target="BACK")
        assert store.latest == before  # 결정④ — 적용 전 상태 diff 0
        assert console.executed == []

    def test_apply_consumes_the_suggestion_and_edits_through_the_same_op(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        sent: list[dict] = []
        session, console = _new_session(
            tmp_path, store=store, sent=sent, suggestion_source=_deterministic_test_double
        )
        suggest_event = session.beat_grid_suggest(bar=7, target="BACK")
        suggestion_id = suggest_event["suggestion_id"]
        apply_event = session.beat_grid_suggestion_apply(suggestion_id)
        assert apply_event["status"] == "ok"
        grid = store.latest["beat_grid"]
        back = next(t for t in grid["tracks"] if t["group_name"] == "BACK")
        cue = next(c for c in back["cues"] if c["bar"] == 7)
        assert cue["brightness"]["value_percent"] == 61
        assert console.executed == []

    def test_apply_sends_a_consumed_event_pairing_approval_resolved(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        sent: list[dict] = []
        session, console = _new_session(
            tmp_path, store=store, sent=sent, suggestion_source=_deterministic_test_double
        )
        suggest_event = session.beat_grid_suggest(bar=7, target="BACK")
        suggestion_id = suggest_event["suggestion_id"]
        session.beat_grid_suggestion_apply(suggestion_id)
        consumed = [e for e in sent if e.get("type") == "beat_grid_suggestion_consumed"]
        assert consumed and consumed[0]["suggestion_id"] == suggestion_id
        assert console.executed == []

    def test_apply_is_single_use(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console = _new_session(
            tmp_path, store=store, suggestion_source=_deterministic_test_double
        )
        suggest_event = session.beat_grid_suggest(bar=7, target="BACK")
        suggestion_id = suggest_event["suggestion_id"]
        session.beat_grid_suggestion_apply(suggestion_id)
        second = session.beat_grid_suggestion_apply(suggestion_id)
        assert "찾을 수 없습니다" in second["text"] or "이미" in second["text"]
        assert console.executed == []

    def test_unknown_suggestion_id_apply_is_a_single_cause_rejection(self, harness) -> None:
        session, console, store, sent = harness
        before = copy.deepcopy(store.latest)
        session.beat_grid_suggestion_apply("no-such-id")
        assert store.latest == before
        assert console.executed == []

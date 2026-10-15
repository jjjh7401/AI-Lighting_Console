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


#: 콘솔 응답 모양 — `console_slots.resolve_named_pool_no`/`paged_pool_
#: children`이 한 창(페이징 불필요)으로 완결로 읽도록(``truncated`` 없음,
#: ``childCount == len(children)``).
def _pool_list_payload(pools: dict[str, int]) -> dict:
    children = [{"i": no, "name": name} for name, no in pools.items()]
    return {"children": children, "node": {"childCount": len(children)}}


def _pool_children_payload(entries: dict[int, str]) -> dict:
    children = [{"i": slot, "name": name} for slot, name in entries.items()]
    return {"children": children, "node": {"childCount": len(children)}}


def _new_session(
    tmp_path,
    *,
    store: SongTimelineStore,
    sent: list[dict] | None = None,
    suggestion_source=None,
    state_tree: dict | None = None,
):
    console = FakeConsole(state_tree=state_tree)
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

    def test_reject_discards_without_editing_the_grid(self, tmp_path) -> None:
        # mockup aNo 핸들러(지시 1항) — 거절은 격자·콘솔 둘 다 바꾸지 않는다.
        store = SongTimelineStore()
        store.latest = _timeline()
        sent: list[dict] = []
        session, console = _new_session(
            tmp_path, store=store, sent=sent, suggestion_source=_deterministic_test_double
        )
        before = copy.deepcopy(store.latest)
        suggest_event = session.beat_grid_suggest(bar=7, target="BACK")
        suggestion_id = suggest_event["suggestion_id"]
        session.beat_grid_suggestion_reject(suggestion_id)
        assert store.latest == before
        consumed = [e for e in sent if e.get("type") == "beat_grid_suggestion_consumed"]
        assert consumed and consumed[0]["suggestion_id"] == suggestion_id
        assert console.executed == []

    def test_reject_then_apply_is_a_no_op_single_cause_rejection(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console = _new_session(
            tmp_path, store=store, suggestion_source=_deterministic_test_double
        )
        suggest_event = session.beat_grid_suggest(bar=7, target="BACK")
        suggestion_id = suggest_event["suggestion_id"]
        session.beat_grid_suggestion_reject(suggestion_id)
        apply_event = session.beat_grid_suggestion_apply(suggestion_id)
        assert "찾을 수 없습니다" in apply_event["text"]
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


# -- 문장 경로의 이름 값(name_lookup) — 카드 t551 후속(근본 원인 정정) -------
#
# 콘솔 **읽기**만(쓰기 0) — `console.executed`(쓰기만 기록)로 직접 잰다.
# 콘솔 질의는 FakeConsole.query_state를 통해 실제 세션 코드 경로(registry
# → query_state 도구 → gate.state_port → console)를 그대로 탄다 —
# 가짜 응답을 흉내 낸 별도 대역이 아니다.


class TestSentenceNameLookup:
    def test_position_name_resolves_through_the_real_console_read_path(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {
            "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
            "DataPool/PresetPools/2": _pool_children_payload({41: "Center"}),
        }
        session, console = _new_session(tmp_path, store=store, state_tree=state_tree)
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="7마디 BACK 위치를 Center로"
        )
        assert "거절" not in event["summary"], event["text"]
        grid = store.latest["beat_grid"]
        back = next(t for t in grid["tracks"] if t["group_name"] == "BACK")
        cue = next(c for c in back["cues"] if c["bar"] == 7)
        assert cue["position_preset_no"] == "2.41"
        assert console.executed == []  # 읽기만 — 쓰기 0건

    def test_color_name_resolves_through_the_color_pool(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {
            "DataPool/PresetPools": _pool_list_payload({"Color": 4}),
            "DataPool/PresetPools/4": _pool_children_payload({21: "LA Pink"}),
        }
        session, console = _new_session(tmp_path, store=store, state_tree=state_tree)
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="7마디 BACK 색을 LA Pink로"
        )
        assert "거절" not in event["summary"], event["text"]
        grid = store.latest["beat_grid"]
        back = next(t for t in grid["tracks"] if t["group_name"] == "BACK")
        cue = next(c for c in back["cues"] if c["bar"] == 7)
        assert cue["color_preset_no"] == "4.21"
        assert console.executed == []

    def test_effect_name_resolves_and_derives_effect_kind_from_the_matched_pool(
        self, tmp_path
    ) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {
            "DataPool/PresetPools": _pool_list_payload(
                {"Position": 2, "Color": 4, "Dimmer": 1, "All 1": 21}
            ),
            "DataPool/PresetPools/2": _pool_children_payload({61: "LA Sweep 2"}),
            "DataPool/PresetPools/4": _pool_children_payload({}),
            "DataPool/PresetPools/1": _pool_children_payload({}),
            "DataPool/PresetPools/21": _pool_children_payload({}),
        }
        session, console = _new_session(tmp_path, store=store, state_tree=state_tree)
        # 이 시험은 "이름→번호 해석이 맞는가"를 가린다 — 해석기를 직접 본다.
        resolved, reason = session._resolve_beat_grid_name_lookup(
            {"field": "효과", "name": "LA Sweep 2"}
        )
        assert reason is None
        assert resolved["effect_preset_no"] == "2.61"
        assert resolved["effect_kind"] == "position"
        # MOVER-U bar 14 에는 기존 번호(21.5)의 승인(카드 t543)이 있지만, 새
        # 번호 2.61 은 이번 변경에 함께 온 승인만 인정한다(REQ-LDBEAT-015(f)(g),
        # 감독 선택 2026-10-11 — 카드 t555). 문장 경로는 승인을 싣지 못한다.
        # 카드 t577(REQ-LDBEAT-015(h-1)) 갱신 — 이제는 편집 시점에 거절하지
        # 않는다. 초안에 그대로 받아들여지고 "승인 대기"로 남는다 — 쓰기(콘솔
        # 반영)는 여전히 별도의 「⇪ 콘솔에 반영」 승인 경로에서만 일어난다
        # (콘솔 접촉은 이 편집 경로에서 전과 다름없이 0건).
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_edit(
            bar=None,
            target=None,
            changes=None,
            sentence="14마디 MOVER-U 효과를 LA Sweep 2로",
        )
        assert "수정" in event["summary"]
        assert "승인 대기" in event["text"]
        assert store.latest != before
        updated_grid = store.latest["beat_grid"]
        mover_u = next(t for t in updated_grid["tracks"] if t["group_name"] == "MOVER-U")
        cue = next(c for c in mover_u["cues"] if c["bar"] == 14)
        assert cue["effect_preset_no"] == "2.61"
        assert console.executed == []

    def test_name_not_found_is_rejected_without_fabricating_a_number(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {
            "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
            "DataPool/PresetPools/2": _pool_children_payload({41: "Center"}),
        }
        session, console = _new_session(tmp_path, store=store, state_tree=state_tree)
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="7마디 BACK 위치를 No Such Preset로"
        )
        assert "찾지 못했습니다" in event["text"]
        assert store.latest == before
        assert console.executed == []

    def test_pool_unread_is_rejected_as_band_unconfirmed_not_as_name_absent(self, tmp_path) -> None:
        # 지시 2항 — 풀을 못 읽으면 "번호대를 확인할 수 없다"고 또렷이
        # 말해야 한다(이름이 없다는 사유와 섞이면 안 된다).
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {"DataPool/PresetPools": _pool_list_payload({})}  # Position 풀 자체가 없음
        session, console = _new_session(tmp_path, store=store, state_tree=state_tree)
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="7마디 BACK 위치를 Center로"
        )
        assert "번호대" in event["text"] and "확인할 수 없습니다" in event["text"]
        assert console.executed == []

    def test_ambiguous_name_is_rejected_naming_the_candidates(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {
            "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
            "DataPool/PresetPools/2": _pool_children_payload({41: "Center", 42: "Center"}),
        }
        session, console = _new_session(tmp_path, store=store, state_tree=state_tree)
        event = session.beat_grid_edit(
            bar=None, target=None, changes=None, sentence="7마디 BACK 위치를 Center로"
        )
        assert "특정할 수 없습니다" in event["text"]
        assert console.executed == []


# -- 프리셋 서랍(지시 1항) — 실제 콘솔 판독, 데모 데이터 0건 ------------------


class TestBeatGridPresetDrawer:
    def test_drawer_sections_come_from_the_real_pool_read(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {
            "DataPool/PresetPools": _pool_list_payload({"Dimmer": 1, "Position": 2, "Color": 4}),
            "DataPool/PresetPools/1": _pool_children_payload({1: "LA Full"}),
            "DataPool/PresetPools/2": _pool_children_payload({41: "Center"}),
            "DataPool/PresetPools/4": _pool_children_payload({21: "LA Pink"}),
        }
        sent: list[dict] = []
        session, console = _new_session(tmp_path, store=store, sent=sent, state_tree=state_tree)
        event = session.beat_grid_preset_drawer()
        assert event["type"] == "beat_grid_drawer"
        titles = [section["title"] for section in event["sections"]]
        assert titles == [
            "디머 풀 1 — 밝기·밝기 효과",
            "위치 풀 2 — 위치·움직임(상대값)",
            "색 풀 4",
        ]
        assert console.executed == []

    def test_drawer_color_entries_fall_back_to_console_preset_values(self, tmp_path) -> None:
        # 응답기 1.7.0 `presetdata` 폴백. 아래 GetPresetData 모양은 지어낸 것이다 —
        # 실기 모양은 확인 전이다.
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {
            "DataPool/PresetPools": _pool_list_payload({"Dimmer": 1, "Position": 2, "Color": 4}),
            "DataPool/PresetPools/1": _pool_children_payload({1: "LA Full"}),
            "DataPool/PresetPools/2": _pool_children_payload({41: "Center"}),
            "DataPool/PresetPools/4": _pool_children_payload({21: "LA Pink", 22: "Two Tone"}),
        }
        session, _console = _new_session(tmp_path, store=store, state_tree=state_tree)
        calls: list[tuple[str, int]] = []

        class PresetPort:
            def query_preset_data(self, path, *, offset=0):
                calls.append((path, offset))
                if path.endswith("/22"):
                    data = (
                        '[{"ColorRGB_R":100,"ColorRGB_G":0,"ColorRGB_B":0},'
                        '{"ColorRGB_R":0,"ColorRGB_G":0,"ColorRGB_B":100}]'
                    )
                else:
                    data = "[]"
                return {"ok": True, "offset": offset, "truncated": False, "data": data}

        session._preset_value_port = PresetPort()
        event = session.beat_grid_preset_drawer()
        color = next(sec for sec in event["sections"] if sec["pool_name"] == "Color")
        by_no = {entry["preset_no"]: entry for entry in color["entries"]}
        assert by_no["4.22"]["rgb"] == [100.0, 0.0, 0.0]
        assert by_no["4.22"]["rgbs"] == [[100.0, 0.0, 0.0], [0.0, 0.0, 100.0]]
        assert "rgb" not in by_no["4.21"]  # 읽혔지만 알아볼 값이 없음 — 지어내지 않는다
        assert {path for path, _ in calls} == {
            "DataPool/PresetPools/4/21",
            "DataPool/PresetPools/4/22",
        }
        session.beat_grid_preset_drawer()
        assert len(calls) == 2  # 세션 기억 — 다시 묻지 않는다

    def test_drawer_survives_a_responder_without_presetdata(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = {
            "DataPool/PresetPools": _pool_list_payload({"Dimmer": 1, "Position": 2, "Color": 4}),
            "DataPool/PresetPools/1": _pool_children_payload({1: "LA Full"}),
            "DataPool/PresetPools/2": _pool_children_payload({41: "Center"}),
            "DataPool/PresetPools/4": _pool_children_payload({21: "LA Pink"}),
        }
        session, _console = _new_session(tmp_path, store=store, state_tree=state_tree)

        class OldResponder:
            def query_preset_data(self, path, *, offset=0):
                raise RuntimeError("unknown request kind: presetdata")

        session._preset_value_port = OldResponder()
        event = session.beat_grid_preset_drawer()
        color = next(sec for sec in event["sections"] if sec["pool_name"] == "Color")
        assert [entry["preset_no"] for entry in color["entries"]] == ["4.21"]
        assert "rgb" not in color["entries"][0]

    def test_drawer_carries_preset_pools_yaml_confirmed_flag(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console = _new_session(tmp_path, store=store, state_tree={})
        event = session.beat_grid_preset_drawer()
        # preset_pools.yaml 은 이 카드 시점에 confirmed: false 다(§B 위험 11
        # 미해소) — 섹션마다 그 값을 그대로 싣는다(번호대를 사실로 내보이지
        # 않는다, 지시 2항).
        assert all(section["bands_confirmed"] is False for section in event["sections"])

    def test_unreadable_pools_mark_unread_true_with_no_fabricated_entries(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console = _new_session(tmp_path, store=store, state_tree={})  # 풀 목록조차 없음
        event = session.beat_grid_preset_drawer()
        assert all(section["unread"] is True for section in event["sections"])
        assert all(section["entries"] == [] for section in event["sections"])
        assert console.executed == []

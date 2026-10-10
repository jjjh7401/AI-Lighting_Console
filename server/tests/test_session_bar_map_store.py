"""M4 — 마디 지도 저장 인터페이스, 세션 배선 (SPEC-LDBARMAP-001, 카드 t539).

``server/web/session.py`` 의 ``store_timeline_bar_map``/``timeline_bar_map``
두 메서드만 다룬다 — 순수 스키마 검증(``validate_bar_map`` 각 규칙 음성
대조군)은 ``test_audio_bar_map_store.py``.

AC-LDBARMAP-010 의 여섯 조건 중 이 파일이 재는 것: 조건 1(왕복, 세션 경로),
조건 2(영속화 — ``SongTimelineStore`` 재생성·``SongTimelineLibrary`` 왕복),
조건 3(되돌리기 1회), 조건 4(잘못된 페이로드 거부), 조건 5(비-4/4 픽스처 ×
되돌리기). 모든 경로는 ``FakeConsole.executed == []`` 로 콘솔 무접촉을 직접
잰다 — "안 나갔을 것이다"가 아니라 "센 결과 0건"(``test_web_cue_sheet_draft.py``
와 같은 관행).
"""

from __future__ import annotations

import copy

import pytest

from server.audio.bar_map_store import BAR_MAP_KEY, build_bar_map_payload
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole


class RefusingProvider:
    """모델을 부르면 시험이 깨진다 — 이 경로는 제공자 없이 동작해야 한다."""

    def complete(self, *args, **kwargs):  # pragma: no cover - 불려선 안 된다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


def _timeline(**overrides: object) -> dict:
    base = {"song_title": "LOVE ATTACK", "sequence_number": 210}
    base.update(overrides)
    return base


def _simple_4_4_beats(n_bars: int = 3) -> list[int]:
    return list(range(0, n_bars * 4 * 500, 500))


def _valid_payload() -> dict:
    return build_bar_map_payload(_simple_4_4_beats(3), 0, bpm=112.35, time_signature=(4, 4))


def _new_session(tmp_path, *, store: SongTimelineStore, sent: list[dict] | None = None):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    session = ChatSession(
        gate=gate,
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=(sent.append if sent is not None else (lambda event: None)),
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    return session, console


@pytest.fixture
def harness(tmp_path):
    store = SongTimelineStore()
    store.latest = _timeline()
    sent: list[dict] = []
    session, console = _new_session(tmp_path, store=store, sent=sent)
    return session, console, store, sent


def _timelines(sent: list[dict]) -> list[dict]:
    return [event["timeline"] for event in sent if event.get("type") == "song_timeline"]


# -- 1. 왕복(쓰기→읽기, AC-LDBARMAP-010 조건 1) ------------------------------


def test_store_then_read_round_trips(harness):
    session, console, store, _sent = harness
    payload = _valid_payload()
    event = session.store_timeline_bar_map(payload)
    assert event["status"] == "ok"
    assert session.timeline_bar_map() == payload
    assert store.latest[BAR_MAP_KEY] == payload
    assert console.executed == []


def test_store_pushes_a_song_timeline_event_carrying_the_bar_map(harness):
    session, _console, _store, sent = harness
    payload = _valid_payload()
    session.store_timeline_bar_map(payload)
    pushed = _timelines(sent)
    assert pushed and pushed[-1][BAR_MAP_KEY] == payload


def test_timeline_bar_map_is_none_before_any_write(harness):
    session, _console, _store, _sent = harness
    assert session.timeline_bar_map() is None


def test_store_with_no_timeline_refuses_without_console_contact(tmp_path):
    store = SongTimelineStore()  # latest 는 None
    session, console = _new_session(tmp_path, store=store)
    event = session.store_timeline_bar_map(_valid_payload())
    assert "저장할 타임라인이 아직 없습니다" in event["text"]
    assert console.executed == []


def test_store_does_not_call_remember_draft_baseline(harness):
    """마디 지도 저장은 큐시트 콘솔 반영 기준본과 무관하다 — 건드리지 않는다."""
    session, _console, _store, _sent = harness
    baseline_before = session._draft_baseline
    session.store_timeline_bar_map(_valid_payload())
    assert session._draft_baseline is baseline_before


# -- 2. 영속화 (AC-LDBARMAP-010 조건 2) --------------------------------------


def test_persists_across_a_fresh_songtimelinestore_instance(tmp_path):
    path = tmp_path / "timeline.json"
    store = SongTimelineStore(path)
    store.latest = _timeline()
    session, console = _new_session(tmp_path, store=store)
    payload = _valid_payload()
    session.store_timeline_bar_map(payload)

    # 프로세스 재시작을 흉내 — 새 인스턴스가 디스크의 원자적 JSON을 다시 읽는다.
    reloaded = SongTimelineStore(path)
    assert reloaded.latest[BAR_MAP_KEY] == payload
    assert console.executed == []


def test_persists_through_songtimelinelibrary_save_and_get(harness, tmp_path):
    session, console, store, _sent = harness
    payload = _valid_payload()
    session.store_timeline_bar_map(payload)

    library = SongTimelineLibrary(tmp_path / "saved.json")
    saved = library.save("LOVE ATTACK v1", store.latest)
    fetched = library.get(saved["id"])
    assert fetched["timeline"][BAR_MAP_KEY] == payload
    assert console.executed == []


# -- 3. 되돌리기 1회 (AC-LDBARMAP-010 조건 3) --------------------------------


def test_undo_restores_exact_pre_write_timeline_when_bar_map_was_absent(harness):
    session, console, store, _sent = harness
    before = copy.deepcopy(store.latest)
    assert BAR_MAP_KEY not in before
    session.store_timeline_bar_map(_valid_payload())
    session.undo_timeline_draft()
    assert BAR_MAP_KEY not in store.latest  # 부재가 다시 부재 — 빈 값으로 남지 않는다
    # 되돌리기는 복원된 타임라인에 "수정됨" 표식을 다시 얹는다(_draft_step 의
    # 공통 경로, test_web_cue_sheet_draft.py 와 같은 관행) — 표식을 뺀 나머지는
    # 쓰기 이전과 바이트 동일해야 한다.
    restored = {k: v for k, v in store.latest.items() if k != "draft"}
    assert restored == before
    assert store.latest["draft"]["dirty"] is False
    assert console.executed == []


def test_undo_restores_previous_bar_map_value_when_one_existed(harness):
    session, console, store, _sent = harness
    first_payload = _valid_payload()
    session.store_timeline_bar_map(first_payload)
    second_payload = build_bar_map_payload(
        _simple_4_4_beats(5), 0, bpm=100.0, time_signature=(4, 4)
    )
    session.store_timeline_bar_map(second_payload)

    session.undo_timeline_draft()
    assert store.latest[BAR_MAP_KEY] == first_payload
    assert console.executed == []


def test_redo_reapplies_the_undone_bar_map_write(harness):
    session, console, store, _sent = harness
    payload = _valid_payload()
    session.store_timeline_bar_map(payload)
    session.undo_timeline_draft()
    session.redo_timeline_draft()
    assert store.latest[BAR_MAP_KEY] == payload
    assert console.executed == []


# -- 4. 잘못된 페이로드 거부 (AC-LDBARMAP-010 조건 4) ------------------------


@pytest.mark.parametrize(
    "mutate,description",
    [
        (lambda p: p["bars"][0].__setitem__("bar", -1), "negative bar"),
        (
            lambda p: p["events"].append(
                {
                    "kind": "break",
                    "start_bar": 1,
                    "end_bar": 1,
                    "start_beat": 0,
                    "grade": "measured",
                }
            ),
            "start_beat zero",
        ),
        (
            lambda p: p["events"].append(
                {
                    "kind": "break",
                    "start_bar": 1,
                    "end_bar": 1,
                    "start_beat": 5,
                    "grade": "measured",
                }
            ),
            "start_beat above numerator",
        ),
        (lambda p: p.update(schema_version=2), "wrong schema_version"),
        (lambda p: p.update(bpm=-1.0), "negative bpm"),
        (lambda p: p["bars"][0].pop("start_ms"), "missing bar field"),
    ],
)
def test_refuses_invalid_payload_and_leaves_state_and_depth_unchanged(harness, mutate, description):
    session, console, store, _sent = harness
    before = copy.deepcopy(store.latest)
    depth_before = session._draft_history.depth

    payload = copy.deepcopy(_valid_payload())
    mutate(payload)

    event = session.store_timeline_bar_map(payload)
    assert "저장하지 않았습니다" in event["text"], description
    assert store.latest == before, description
    assert session._draft_history.depth == depth_before, description
    assert console.executed == []


# -- 5. 비-4/4 픽스처 × 되돌리기 (AC-LDBARMAP-010 조건 5) --------------------


def _three_four_no_pickup_partial_last() -> list[int]:
    return [i * 400 for i in range(8)]


def _six_eight_with_pickup() -> tuple[list[int], int]:
    return [i * 250 for i in range(14)], 2


@pytest.mark.parametrize(
    "beats,offset,bpm,time_signature,expect_pickup",
    [
        (_three_four_no_pickup_partial_last(), 0, 90.0, (3, 4), False),
        (_six_eight_with_pickup()[0], _six_eight_with_pickup()[1], 140.0, (6, 8), True),
        ([0, 500, 1000, 1500, 2000, 2500, 3000, 3500], 0, 120.0, (4, 4), False),  # 2-bar song
    ],
)
def test_non_love_attack_fixtures_round_trip_and_undo(
    harness, beats, offset, bpm, time_signature, expect_pickup
):
    session, console, store, _sent = harness
    before = copy.deepcopy(store.latest)
    payload = build_bar_map_payload(beats, offset, bpm=bpm, time_signature=time_signature)
    assert (payload["bars"][0]["bar"] == 0) is expect_pickup

    session.store_timeline_bar_map(payload)
    assert session.timeline_bar_map() == payload

    session.undo_timeline_draft()
    assert BAR_MAP_KEY not in store.latest
    restored = {k: v for k, v in store.latest.items() if k != "draft"}
    assert restored == before
    assert console.executed == []

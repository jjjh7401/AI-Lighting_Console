"""SPEC-LDBEAT-001 재적용 소유권 (카드 t572, REQ-LDBEAT-011~013).

두 번째 이후의 「콘솔에 반영」(재적용)은 새 시퀀스·타임코드 번호를 고르는
대신, **이 앱이 저번에 쓴** 번호를 콘솔에서 확인한 뒤에만 덮어쓴다 — 콘솔이
만들지 않은 객체는 절대 건드리지 않는다. 소유권 레코드는
``SongTimelineStore``에 곡별로 저장된다(``server.web.session``,
``_beat_grid_song_key`` 그대로).

콘솔 접촉: 0건. ``FakeConsole``만 쓰고 실기 포트로는 한 바이트도 나가지
않는다.
"""

from __future__ import annotations

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole

# -- 공용 픽스처 ---------------------------------------------------------------


class RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("이 경로는 모델을 부르지 않는다")


class ScriptedApproval:
    """``test_safety_gate.ScriptedApproval``과 같은 모양 — 이 파일은
    ``server/tests`` 밖 임포트를 늘리지 않으려 복제한다(결정적이고 짧다)."""

    def __init__(self, decisions=(True,)):
        self.decisions = list(decisions)
        self.requests = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        if not self.decisions:
            return False
        return self.decisions.pop(0)


_APPROVED_EVIDENCE = {"approval": {"by": "supervisor", "date": "2026-10-11", "source": "t572"}}

SONG_TITLE = "LOVE ATTACK"
SEQUENCE_NUMBER = 210
TIMECODE_NUMBER = 20
#: 첫 반영이 고를 시퀀스 번호 — 빈 풀(``_empty_pool_state_tree``)에서
#: ``select_sequence_number``는 1부터 고른다(songcue.py:548).
FIRST_SEQUENCE_NUMBER = 1
OWNED_SEQUENCE_NAME = "LDBEAT BACK"
OWNED_TIMECODE_NAME = "LDBEAT Timecode 20"


def _bar_map(bpm: float = 112.35, beats_per_bar: int = 4) -> dict:
    return {
        "bpm": bpm,
        "time_signature": [beats_per_bar, 4],
        "bars": [
            {"bar": n, "start_ms": 1000 + (n - 1) * 2000, "beats_ms": [1000 + (n - 1) * 2000]}
            for n in range(1, 30)
        ],
    }


def _cue(bar: int, preset: str) -> dict:
    return {"bar": bar, "position_preset_no": preset, "evidence": _APPROVED_EVIDENCE}


def _timeline(cues: list[dict] | None = None, **overrides: object) -> dict:
    if cues is None:
        cues = [_cue(1, "1.1")]
    base: dict[str, object] = {
        "song_title": SONG_TITLE,
        "sequence_number": SEQUENCE_NUMBER,
        "bar_map": _bar_map(),
        "timecode_number": TIMECODE_NUMBER,
        "beat_grid": {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": cues,
                }
            ],
            "probe_results": {1: "통과", 2: "통과", 4: "통과", 5: "통과", 7: "통과", 9: "통과"},
        },
    }
    base.update(overrides)
    return base


def _song_key() -> tuple[object, object]:
    return (SONG_TITLE, SEQUENCE_NUMBER)


#: 카드 t600 — 이 시험들의 칸이 가리키는 프리셋 번호가 콘솔 풀에 **있는** 상태.
_EXISTING_PRESET_POOLS = {
    f"DataPool/PresetPools/{pool}": {
        "children": [{"i": i, "name": f"P{pool}.{i}"} for i in range(1, 6)]
    }
    for pool in (1, 2, 3, 4)
}


def _empty_pool_state_tree() -> dict:
    return {
        # 카드 t600 — 반영은 승인된 칸의 프리셋 번호도 콘솔 풀을 읽어 가른다(빈
        # 번호·못 읽은 풀은 송신 보류). 이 시험들이 쓰는 번호는 콘솔에 있는 프리셋이다.
        **_EXISTING_PRESET_POOLS,
        "DataPool/Sequences": {"children": []},
        "DataPool/Timecodes": {"children": [], "node": {"childCount": 0, "enumeration": "ok"}},
    }


def _owned_state_tree(
    *,
    sequence_number: int = FIRST_SEQUENCE_NUMBER,
    sequence_name: str = OWNED_SEQUENCE_NAME,
    timecode_number: int = TIMECODE_NUMBER,
    timecode_name: str = OWNED_TIMECODE_NAME,
) -> dict:
    """소유권 레코드가 기억하는 객체가 **지금 콘솔에 실제로 있는** 상태를
    흉내 낸다(``FakeConsole``은 ``execute()``가 상태 나무를 갈아 끼우지
    않으므로, "저번 반영이 이미 만들었다"를 시험이 직접 심어야 한다)."""
    return {
        # 카드 t600 — 반영은 승인된 칸의 프리셋 번호도 콘솔 풀을 읽어 가른다(빈
        # 번호·못 읽은 풀은 송신 보류). 이 시험들이 쓰는 번호는 콘솔에 있는 프리셋이다.
        **_EXISTING_PRESET_POOLS,
        "DataPool/Sequences": {"children": [{"i": sequence_number, "name": sequence_name}]},
        "DataPool/Timecodes": {
            "children": [{"i": timecode_number, "name": timecode_name}],
            "node": {"childCount": 1},
        },
    }


def _seed_record(store: SongTimelineStore, **overrides: object) -> dict:
    record: dict[str, object] = {
        "timecode_number": TIMECODE_NUMBER,
        "timecode_name": OWNED_TIMECODE_NAME,
        "tracks": {
            "BACK": {
                "sequence_number": FIRST_SEQUENCE_NUMBER,
                "sequence_name": OWNED_SEQUENCE_NAME,
                "cues": {"1": 1},
            }
        },
    }
    record.update(overrides)
    store.set_beat_grid_allocation(_song_key(), record)
    return record


def _new_session(
    tmp_path,
    *,
    store: SongTimelineStore,
    decisions=(True,) * 10,
    state_tree: dict | None = None,
    sent: list[dict] | None = None,
):
    console = FakeConsole(
        state_tree=state_tree if state_tree is not None else _empty_pool_state_tree()
    )
    audit = AuditLog(tmp_path / "audit")
    approval = ScriptedApproval(decisions=decisions)
    gate = SafetyGate(console=console, audit=audit, approval_port=approval)
    channel = ApprovalChannel(timeout_seconds=1.0)
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
    return session, console, approval, audit


def _non_cue_store_lines(executed: list[str]) -> list[str]:
    return [c for c in executed if c not in ("SaveShow",)]


# =============================================================================
# 적용 흐름 — 소유한 번호를 재사용하고, 바뀐 부분만 콘솔에 보낸다
# =============================================================================


class TestReapplyFlows:
    def test_reapply_reuses_owned_numbers_and_sends_overwrite(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, decisions=(True,) * 10
        )

        first = session.beat_grid_apply()
        assert first["ok"] is True
        assert len(approval.requests) == 1

        # 저번 반영이 실제로 만든 객체가 지금 콘솔에 있다고 가정한다.
        console.state_tree = _owned_state_tree()
        console.executed.clear()

        second = session.beat_grid_apply()
        assert second["ok"] is True
        assert second["approval_vs_sent"]["match"] is True
        assert len(approval.requests) == 2

        executed = _non_cue_store_lines(console.executed)
        # 맨 Store Sequence 줄(큐 없는 것)만 금지 — 큐 저장 줄 ``Store Sequence N Cue M`` 은 남는다.
        assert not any(c.startswith("Store Sequence ") and " Cue " not in c for c in executed)
        # 카드 tc-events — 앱이 만든 타임코드는 지우고 처음부터 다시 만든다(옛 빈 트랙이 쌓이지
        # 않게). 시퀀스는 기록된 번호를 그대로 재사용한다.
        assert executed.index("Delete Timecode 20 /NoConfirm") < executed.index("Store Timecode 20")
        assert any(c.startswith("Assign Sequence 1 At Timecode 20.1.") for c in executed)
        assert any("/Overwrite" in c for c in executed)
        # 재실행 3 B1 — 소유한 시퀀스는 이름을 다시 쓰지 않는다(콘솔이 「#숫자」를 붙인다).
        assert not any(
            c.startswith(f"Set Sequence {FIRST_SEQUENCE_NUMBER} Property 'Name' ") for c in executed
        )

    def test_reapply_removing_a_cell_emits_delete_cue(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline(cues=[_cue(1, "1.1"), _cue(2, "2.2")])
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, decisions=(True,) * 10
        )

        first = session.beat_grid_apply()
        assert first["ok"] is True
        record = store.beat_grid_allocation(_song_key())
        assert record["tracks"]["BACK"]["cues"] == {"1": 1, "2": 2}

        console.state_tree = _owned_state_tree()
        console.executed.clear()
        store.latest = _timeline(cues=[_cue(1, "1.1")])  # 2마디 칸을 뺀다

        second = session.beat_grid_apply()
        assert second["ok"] is True
        assert any(c == f"Delete Cue 2 Sequence {FIRST_SEQUENCE_NUMBER}" for c in console.executed)
        updated_record = store.beat_grid_allocation(_song_key())
        assert updated_record["tracks"]["BACK"]["cues"] == {"1": 1}

    def test_track_added_between_applies_gets_a_fresh_number(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, decisions=(True,) * 10
        )

        first = session.beat_grid_apply()
        assert first["ok"] is True

        owned_tree = _owned_state_tree()
        console.state_tree = owned_tree
        console.executed.clear()
        store.latest = _timeline(
            beat_grid={
                "tracks": [
                    {
                        "group_name": "BACK",
                        "group_no": 7,
                        "group_no_confirmed": True,
                        "cues": [_cue(1, "1.1")],
                    },
                    {
                        "group_name": "FRONT",
                        "group_no": 8,
                        "group_no_confirmed": True,
                        "cues": [_cue(1, "3.3")],
                    },
                ],
                "probe_results": {1: "통과", 2: "통과", 4: "통과", 5: "통과", 7: "통과", 9: "통과"},
            }
        )

        second = session.beat_grid_apply()
        assert second["ok"] is True
        executed = console.executed
        # 새 트랙(FRONT)은 전부(Store Sequence + Assign) 그대로 낸다.
        assert any("Store Sequence 2" in c for c in executed)
        assert any("Assign Sequence 2 At Timecode 20" in c for c in executed)
        # 소유 트랙(BACK)은 시퀀스 재사용 경로다. 타임코드는 지우고 다시 만드니 배정도 다시 낸다.
        assert "Store Sequence 1" not in executed
        assert "Delete Timecode 20 /NoConfirm" in executed
        assert any("Assign Sequence 1 At Timecode 20" in c for c in executed)
        record = store.beat_grid_allocation(_song_key())
        assert record["tracks"]["FRONT"]["sequence_number"] == 2


# =============================================================================
# 거절 — 소유권 확인이 실패하면 명령 0줄
# =============================================================================


class TestReapplyRefusals:
    def test_no_record_timecode_occupied_by_foreign_object_is_refused(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = _empty_pool_state_tree()
        state_tree["DataPool/Timecodes"] = {
            "children": [{"i": TIMECODE_NUMBER, "name": "Foreign"}],
            "node": {"childCount": 1},
        }
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )

        event = session.beat_grid_apply()

        assert event["ok"] is False
        assert console.executed == []
        assert len(approval.requests) == 0

    def test_record_exists_but_console_sequence_name_differs_is_refused(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        state_tree = _owned_state_tree(sequence_name="Someone Else Sequence")
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )

        event = session.beat_grid_apply()

        assert event["ok"] is False
        assert "이름" in event["reason"]
        assert console.executed == []
        assert len(approval.requests) == 0

    def test_record_exists_but_recorded_sequence_number_missing_is_refused(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        state_tree = _empty_pool_state_tree()  # 시퀀스 1번이 콘솔에 없다
        state_tree["DataPool/Timecodes"] = {
            "children": [{"i": TIMECODE_NUMBER, "name": OWNED_TIMECODE_NAME}],
            "node": {"childCount": 1},
        }
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )

        event = session.beat_grid_apply()

        assert event["ok"] is False
        assert "찾지 못" in event["reason"]
        assert console.executed == []
        assert len(approval.requests) == 0

    def test_record_exists_but_console_timecode_name_differs_is_refused(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        state_tree = _owned_state_tree(timecode_name="Someone Else Timecode")
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )

        event = session.beat_grid_apply()

        assert event["ok"] is False
        assert console.executed == []
        assert len(approval.requests) == 0

    def test_record_exists_but_timecode_slot_now_free_is_refused_as_stale(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        state_tree = _owned_state_tree()
        state_tree["DataPool/Timecodes"] = {
            "children": [],
            "node": {"childCount": 0, "enumeration": "ok"},
        }
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )

        event = session.beat_grid_apply()

        assert event["ok"] is False
        assert "낡" in event["reason"]
        assert console.executed == []
        assert len(approval.requests) == 0


# =============================================================================
# 레코드 생명주기
# =============================================================================


class TestReapplyRecordLifecycle:
    def test_declined_apply_does_not_write_the_record(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, decisions=(False,)
        )

        event = session.beat_grid_apply()

        assert event["ok"] is False
        assert console.executed == []
        assert store.beat_grid_allocation(_song_key()) is None

    def test_blocked_apply_does_not_write_the_record(self, tmp_path) -> None:
        store = SongTimelineStore()
        timeline = _timeline()
        del timeline["bar_map"]
        store.latest = timeline
        session, console, _approval, _audit = _new_session(tmp_path, store=store)

        event = session.beat_grid_apply()

        assert event["ok"] is False
        assert console.executed == []
        assert store.beat_grid_allocation(_song_key()) is None

    def test_record_survives_a_store_reload(self, tmp_path) -> None:
        path = tmp_path / "song-timeline.json"
        store = SongTimelineStore(path)
        store.latest = _timeline()
        session, _console, _approval, _audit = _new_session(tmp_path, store=store)

        event = session.beat_grid_apply()
        assert event["ok"] is True

        reborn = SongTimelineStore(path)  # 서버 재시작 흉내
        record = reborn.beat_grid_allocation(_song_key())
        assert record is not None
        assert record["tracks"]["BACK"]["sequence_number"] == FIRST_SEQUENCE_NUMBER
        assert record["tracks"]["BACK"]["sequence_name"] == OWNED_SEQUENCE_NAME
        assert record["timecode_number"] == TIMECODE_NUMBER

    def test_two_songs_records_are_independent(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, decisions=(True,) * 10
        )

        first = session.beat_grid_apply()
        assert first["ok"] is True
        before_first = store.beat_grid_allocation(_song_key())
        assert before_first is not None

        other_key = ("Sugar", 999)
        store.latest = _timeline(song_title="Sugar", sequence_number=999)
        console.state_tree = _empty_pool_state_tree()  # 둘째 곡은 빈 풀에서 새로 고른다
        console.executed.clear()

        second = session.beat_grid_apply()
        assert second["ok"] is True

        after_first = store.beat_grid_allocation(_song_key())
        second_record = store.beat_grid_allocation(other_key)
        assert after_first == before_first  # 첫 곡 레코드는 그대로다
        assert second_record is not None
        assert second_record["tracks"]["BACK"]["sequence_number"] == FIRST_SEQUENCE_NUMBER


# =============================================================================
# 타임코드 판정 세 갈래 (기존 동작, 재적용 경로에서도 지켜지는지)
# =============================================================================


class TestTimecodeResolutionBranches:
    def test_missing_timecode_number_is_refused(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, _console, _approval, _audit = _new_session(tmp_path, store=store)

        number, reason = session._resolve_beat_grid_timecode_number(None)

        assert number is None
        assert reason == "타임코드 번호를 넣어 주세요"

    def test_occupied_timecode_is_refused(self, tmp_path) -> None:
        state_tree = _empty_pool_state_tree()
        state_tree["DataPool/Timecodes"] = {
            "children": [{"i": TIMECODE_NUMBER, "name": "Foreign"}],
            "node": {"childCount": 1},
        }
        store = SongTimelineStore()
        store.latest = _timeline()
        session, _console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )

        number, reason = session._resolve_beat_grid_timecode_number(TIMECODE_NUMBER)

        assert number is None
        assert reason is not None
        assert "Foreign" in reason

    def test_unknown_timecode_occupancy_is_refused(self, tmp_path) -> None:
        state_tree = _empty_pool_state_tree()
        state_tree["DataPool/Timecodes"] = {"truncated": True}  # 점유 여부를 알 수 없다
        store = SongTimelineStore()
        store.latest = _timeline()
        session, _console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )

        number, reason = session._resolve_beat_grid_timecode_number(TIMECODE_NUMBER)

        assert number is None
        assert reason is not None


# =============================================================================
# 카드 t572 리드 결정 — 막힌 칸의 옛 큐는 지우지도 덮어쓰지도 않는다
# =============================================================================

_ALL_PASS = {1: "통과", 2: "통과", 4: "통과", 5: "통과", 7: "통과", 9: "통과"}


def _progress_table(results: dict) -> str:
    """진행표 M1 표 모양의 최소 텍스트 — 항목 번호는 ①~⑨ 원문자다."""
    return "\n".join(
        f"| {chr(0x2460 + item - 1)} 항목 | {status} | 본 것 | 근거 |"
        for item, status in results.items()
    )


def _effect_cue(bar: int, preset: str) -> dict:
    """효과 프리셋 리콜 칸 — M1 ④가 「통과」가 아니면 에미터가 이 칸만 막는다
    (``beat_grid_emit._EFFECT_PRESET_RECALL_ITEM``)."""
    return {"bar": bar, "effect_preset_no": preset, "evidence": _APPROVED_EVIDENCE}


def _three_cell_timeline(probe_results: dict) -> dict:
    return _timeline(
        beat_grid={
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [_cue(1, "1.1"), _effect_cue(2, "3.1"), _cue(3, "1.3")],
                }
            ],
            "probe_results": probe_results,
        }
    )


class TestBlockedCellsArePreserved:
    def test_a_blocked_cell_is_neither_deleted_nor_overwritten(self, tmp_path, monkeypatch) -> None:
        # 반영은 progress.md 의 M1 표를 그 자리에서 다시 읽는다 — 판정은 파일로 주입한다.
        progress = tmp_path / "progress.md"
        monkeypatch.setattr("server.web.session.default_progress_md_path", lambda: progress)
        progress.write_text(_progress_table(_ALL_PASS), encoding="utf-8")
        store = SongTimelineStore()
        store.latest = _three_cell_timeline(_ALL_PASS)
        session, console, approval, _audit = _new_session(tmp_path, store=store)

        first = session.beat_grid_apply()
        assert first["ok"] is True
        assert store.beat_grid_allocation(_song_key())["tracks"]["BACK"]["cues"] == {
            "1": 1,
            "2": 2,
            "3": 3,
        }

        console.state_tree = _owned_state_tree()
        console.executed.clear()
        # 이번에는 M1 ④가 미확인 — 2마디(효과 칸)만 막힌다.
        store.latest = _three_cell_timeline({**_ALL_PASS, 4: "미확인"})
        progress.write_text(_progress_table({**_ALL_PASS, 4: "미확인"}), encoding="utf-8")

        second = session.beat_grid_apply()
        assert second["ok"] is True
        seq = FIRST_SEQUENCE_NUMBER
        # 막힌 칸(큐 2)은 지우지도, 다른 칸 내용으로 덮어쓰지도 않는다.
        assert not any(c.startswith(f"Delete Cue 2 Sequence {seq}") for c in console.executed)
        assert not any(c.startswith(f"Store Sequence {seq} Cue 2") for c in console.executed)
        # 3마디는 당겨지지 않고 원래 번호 3에 덮어쓴다.
        assert f"Store Sequence {seq} Cue 3 /Overwrite" in console.executed
        # 기록에도 막힌 칸의 번호가 그대로 남는다.
        assert store.beat_grid_allocation(_song_key())["tracks"]["BACK"]["cues"] == {
            "1": 1,
            "2": 2,
            "3": 3,
        }
        # 승인 카드에 「막혀서 그대로 둔 칸」이 적힌다.
        reasons = [r for item in approval.requests[-1].items for r in item.risk_reasons]
        assert any("막혀서 그대로 둔 칸 1개" in r and "BACK 2마디" in r for r in reasons)

    def test_a_really_emptied_cell_is_deleted(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _three_cell_timeline(_ALL_PASS)
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        assert session.beat_grid_apply()["ok"] is True

        console.state_tree = _owned_state_tree()
        console.executed.clear()
        # 2마디 칸을 초안에서 정말 지운다(막힘이 아니다).
        store.latest = _timeline(cues=[_cue(1, "1.1"), _cue(3, "1.3")])

        second = session.beat_grid_apply()
        assert second["ok"] is True
        seq = FIRST_SEQUENCE_NUMBER
        assert f"Delete Cue 2 Sequence {seq}" in console.executed
        assert f"Store Sequence {seq} Cue 3 /Overwrite" in console.executed
        assert store.beat_grid_allocation(_song_key())["tracks"]["BACK"]["cues"] == {
            "1": 1,
            "3": 3,
        }

    def test_a_wholly_blocked_owned_track_keeps_every_cue(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _three_cell_timeline(_ALL_PASS)
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        assert session.beat_grid_apply()["ok"] is True
        record_before = store.beat_grid_allocation(_song_key())

        console.state_tree = _owned_state_tree()
        console.executed.clear()
        timeline = _three_cell_timeline(_ALL_PASS)
        # 트랙 전체가 막힌다(그룹 번호 미확인) — 같이 반영할 다른 트랙을 둔다.
        timeline["beat_grid"]["tracks"][0]["group_no_confirmed"] = False
        timeline["beat_grid"]["tracks"].append(
            {
                "group_name": "FRONT",
                "group_no": 8,
                "group_no_confirmed": True,
                "cues": [_cue(1, "3.3")],
            }
        )
        store.latest = timeline

        second = session.beat_grid_apply()
        assert second["ok"] is True
        seq = FIRST_SEQUENCE_NUMBER
        assert not any(f"Sequence {seq}" in c and "Delete" in c for c in console.executed)
        assert (
            store.beat_grid_allocation(_song_key())["tracks"]["BACK"]
            == record_before["tracks"]["BACK"]
        )


class TestNewBarBetweenRecordedBars:
    def test_a_new_bar_between_takes_the_next_number_and_is_reported(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline(cues=[_cue(1, "1.1"), _cue(3, "1.3")])
        session, console, approval, _audit = _new_session(tmp_path, store=store)
        assert session.beat_grid_apply()["ok"] is True

        console.state_tree = _owned_state_tree()
        console.executed.clear()
        store.latest = _timeline(cues=[_cue(1, "1.1"), _cue(2, "1.2"), _cue(3, "1.3")])

        second = session.beat_grid_apply()
        assert second["ok"] is True
        seq = FIRST_SEQUENCE_NUMBER
        # 새 마디(2)는 최대 번호(2) 다음 정수 3을 받는다 — 소수점 번호 없음.
        # 3마디는 기록된 번호 2를 그대로 쓴다.
        assert f"Store Sequence {seq} Cue 3" in console.executed
        assert f"Store Sequence {seq} Cue 2 /Overwrite" in console.executed
        # 큐 번호(``Store Sequence <s> Cue <n>`` 의 다섯째 토큰)는 소수점이 없어야 한다.
        assert not any(
            "." in c.split()[4]
            for c in console.executed
            if c.startswith("Store Sequence ") and " Cue " in c
        )
        assert store.beat_grid_allocation(_song_key())["tracks"]["BACK"]["cues"] == {
            "1": 1,
            "2": 3,
            "3": 2,
        }
        reasons = [r for item in approval.requests[-1].items for r in item.risk_reasons]
        assert any("번호 순서와 시간 순서가 다른 큐 1개" in r for r in reasons)


class TestApprovalSentMismatch:
    def test_a_mismatch_leaves_the_record_untouched(self, tmp_path, monkeypatch) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        assert session.beat_grid_apply()["ok"] is True
        record_before = store.beat_grid_allocation(_song_key())

        class _Mismatch:
            passed = False
            sent_not_approved = ("Store Sequence 1 Cue 9",)
            approved_not_sent = ()

        monkeypatch.setattr(
            session, "_beat_grid_verify_approval_vs_sent", lambda *a, **k: _Mismatch()
        )
        console.state_tree = _owned_state_tree()
        store.latest = _timeline(cues=[_cue(1, "1.1"), _cue(2, "2.2")])

        event = session.beat_grid_apply()
        assert event["approval_vs_sent"]["match"] is False
        assert store.beat_grid_allocation(_song_key()) == record_before

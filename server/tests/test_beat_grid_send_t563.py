"""SPEC-LDBEAT-001 M4 — 박자 격자 상단 바 「이 마디 콘솔에서 보기」·「끄기」·
「콘솔에 반영」 배선 (카드 t563, REQ-LDBEAT-011~013/017).

이 파일은 세 층을 다룬다:

1. ``server.design.beat_grid_send`` 의 순수 입력 소스 헬퍼
   (``pick_sequence_numbers``·``resolve_dimmer_attributes``·
   ``build_song_timing_from_bar_map``) — 콘솔 접촉 0, 전부 이미 읽은 값의
   순수 변환.
2. ``ChatSession.beat_grid_apply``/``beat_grid_preview``/
   ``beat_grid_preview_off`` — 가짜 콘솔(``FakeConsole``) + 각본
   승인(``ScriptedApproval``)로 실기 왕복 없이 승인=송신 경로 전체를 잰다.
3. 대기 수(``pending_apply_count``) = ``unsent_cells`` 길이(스냅샷이
   없으면 ``None``) — 편집 성공 횟수를 세는 카운터가 아니라 곡별 칸
   스냅샷과 지금 격자의 차이다(코디네이터 계약, t568과 합의).

콘솔 접촉: 0건. ``FakeConsole`` 만 쓰고 실기 포트로는 한 바이트도 나가지
않는다.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid_send import (
    beat_grid_cell_snapshot,
    build_song_timing_from_bar_map,
    pick_sequence_numbers,
    resolve_dimmer_attributes,
    unsent_beat_grid_cells,
)
from server.design.capability_join import FixtureCapability, RigCapabilities
from server.design.rig_capability_read import DesignRigRead
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole

# =============================================================================
# 1. 입력 소스 헬퍼 — server.design.beat_grid_send
# =============================================================================


class TestPickSequenceNumbers:
    def test_no_group_names_is_not_a_refusal(self):
        chosen, reason = pick_sequence_numbers({"children": []}, [])
        assert chosen == {}
        assert reason is None

    def test_sequential_picking_skips_occupied_and_previously_chosen(self):
        # 1·3 이 이미 점유 — 첫 트랙은 2를 받고, 둘째 트랙은 2도 점유로
        # 치므로(방금 고른 번호) 4를 받는다(3은 이미 점유라 건너뛴다).
        section = {"children": [{"i": 1, "name": "a"}, {"i": 3, "name": "b"}]}
        chosen, reason = pick_sequence_numbers(section, ["track-a", "track-b"])
        assert reason is None
        assert chosen == {"track-a": 2, "track-b": 4}

    def test_truncated_pool_refuses_the_whole_batch(self):
        section = {"children": [], "truncated": True}
        chosen, reason = pick_sequence_numbers(section, ["track-a", "track-b"])
        assert chosen == {}
        assert reason is not None
        assert "잘려" in reason

    def test_unreadable_pool_refuses_the_whole_batch(self):
        section = {"reason": "console_unreachable"}
        chosen, reason = pick_sequence_numbers(section, ["track-a"])
        assert chosen == {}
        assert reason is not None

    def test_a_child_without_a_number_refuses_the_whole_batch(self):
        section = {"children": [{"name": "no-number-here"}]}
        chosen, reason = pick_sequence_numbers(section, ["track-a"])
        assert chosen == {}
        assert reason is not None

    def test_does_not_mutate_the_caller_section(self):
        section = {"children": [{"i": 1, "name": "a"}]}
        pick_sequence_numbers(section, ["track-a", "track-b"])
        assert section == {"children": [{"i": 1, "name": "a"}]}


def _capability(type_name: str, attributes: tuple[str, ...], *, whole: bool = True):
    from server.prechk.capability_read import AxisRange

    axes = tuple(AxisRange(attribute=name, channel_name=name) for name in attributes)
    return FixtureCapability(
        fid=1,
        type_slot=1,
        type_name=type_name,
        mode_slot=1,
        mode_name="Mode 1",
        mode_width=None,
        channel_count=1,
        axes=axes,
        gaps=() if whole else ("some_gap",),
    )


class TestResolveDimmerAttributes:
    def test_not_whole_yields_nothing(self):
        rig = DesignRigRead(attempted=True, gap="rig_unreadable")
        assert resolve_dimmer_attributes(rig, ["track-a"]) == {}

    def test_uniform_dimmer_attributes_across_fixture_types_apply_to_every_track(self):
        capabilities = RigCapabilities(
            fixtures={
                1: _capability("MOVER-D", ("Dimmer", "Dimmer2", "Pan")),
                2: _capability("MOVER-U", ("Dimmer", "Dimmer2", "Tilt")),
            }
        )
        rig = DesignRigRead(attempted=True, gap="", capabilities=capabilities)
        resolved = resolve_dimmer_attributes(rig, ["track-a", "track-b"])
        assert resolved == {
            "track-a": ("Dimmer", "Dimmer2"),
            "track-b": ("Dimmer", "Dimmer2"),
        }

    def test_differing_dimmer_attributes_across_fixture_types_yield_nothing(self):
        capabilities = RigCapabilities(
            fixtures={
                1: _capability("MOVER-D", ("Dimmer", "Dimmer2")),
                2: _capability("PAR-LED", ("Dimmer",)),
            }
        )
        rig = DesignRigRead(attempted=True, gap="", capabilities=capabilities)
        assert resolve_dimmer_attributes(rig, ["track-a"]) == {}

    def test_an_incomplete_fixture_capability_yields_nothing(self):
        capabilities = RigCapabilities(
            fixtures={1: _capability("MOVER-D", ("Dimmer",), whole=False)}
        )
        rig = DesignRigRead(attempted=True, gap="", capabilities=capabilities)
        assert resolve_dimmer_attributes(rig, ["track-a"]) == {}

    def test_unread_or_incomplete_fid_registry_yields_nothing(self):
        capabilities = RigCapabilities(
            fixtures={1: _capability("MOVER-D", ("Dimmer",))}, unread={2: "no reply"}
        )
        rig = DesignRigRead(attempted=True, gap="", capabilities=capabilities)
        assert resolve_dimmer_attributes(rig, ["track-a"]) == {}

    def test_no_dimmer_attribute_at_all_yields_nothing(self):
        capabilities = RigCapabilities(fixtures={1: _capability("STROBE", ("Strobe",))})
        rig = DesignRigRead(attempted=True, gap="", capabilities=capabilities)
        assert resolve_dimmer_attributes(rig, ["track-a"]) == {}


class TestUnsentBeatGridCells:
    def _grid(self, cues: list[dict]) -> dict:
        return {"tracks": [{"group_name": "BACK", "cues": cues}]}

    def test_no_snapshot_is_none(self):
        grid = self._grid([{"bar": 1, "position_preset_no": "1.1"}])
        assert unsent_beat_grid_cells(grid, None) is None

    def test_identical_snapshot_is_empty(self):
        grid = self._grid([{"bar": 1, "position_preset_no": "1.1"}])
        snapshot = beat_grid_cell_snapshot(grid)
        assert unsent_beat_grid_cells(grid, snapshot) == []

    def test_a_changed_cell_is_named(self):
        grid = self._grid([{"bar": 1, "position_preset_no": "1.1"}])
        snapshot = beat_grid_cell_snapshot(grid)
        changed = self._grid([{"bar": 1, "position_preset_no": "2.2"}])
        assert unsent_beat_grid_cells(changed, snapshot) == [{"group_name": "BACK", "bar": 1}]

    def test_an_added_cell_is_named(self):
        grid = self._grid([{"bar": 1, "position_preset_no": "1.1"}])
        snapshot = beat_grid_cell_snapshot(grid)
        with_new_bar = self._grid(
            [{"bar": 1, "position_preset_no": "1.1"}, {"bar": 2, "position_preset_no": "3.3"}]
        )
        assert unsent_beat_grid_cells(with_new_bar, snapshot) == [{"group_name": "BACK", "bar": 2}]

    def test_a_removed_cell_is_named(self):
        grid = self._grid(
            [{"bar": 1, "position_preset_no": "1.1"}, {"bar": 2, "position_preset_no": "3.3"}]
        )
        snapshot = beat_grid_cell_snapshot(grid)
        without_bar_2 = self._grid([{"bar": 1, "position_preset_no": "1.1"}])
        assert unsent_beat_grid_cells(without_bar_2, snapshot) == [{"group_name": "BACK", "bar": 2}]


class TestBuildSongTimingFromBarMap:
    def test_no_bar_map_is_none(self):
        assert build_song_timing_from_bar_map(None) is None

    def test_missing_bar_1_is_none(self):
        bar_map = {"bpm": 120.0, "time_signature": [4, 4], "bars": []}
        assert build_song_timing_from_bar_map(bar_map) is None

    def test_well_formed_bar_map_without_pickup(self):
        bar_map = {
            "bpm": 120.0,
            "time_signature": [4, 4],
            "bars": [{"bar": 1, "start_ms": 1000, "beats_ms": [1000, 1500, 2000, 2500]}],
        }
        timing = build_song_timing_from_bar_map(bar_map)
        assert timing is not None
        assert timing.bpm == 120.0
        assert timing.beats_per_bar == 4
        assert timing.downbeat_bar1_seconds == 1.0
        assert timing.pickup_beats is None
        # 못갖춘마디(0마디) 없이도 1마디 이상은 환산 가능해야 한다.
        assert timing.bar_start_seconds(2) == pytest.approx(3.0)

    def test_pickup_bar_zero_sets_pickup_beats(self):
        bar_map = {
            "bpm": 120.0,
            "time_signature": [4, 4],
            "bars": [
                {"bar": 0, "start_ms": 0, "beats_ms": [0, 500]},
                {"bar": 1, "start_ms": 1000, "beats_ms": [1000, 1500, 2000, 2500]},
            ],
        }
        timing = build_song_timing_from_bar_map(bar_map)
        assert timing is not None
        assert timing.pickup_beats == 2.0
        assert timing.bar_start_seconds(0) == pytest.approx(0.0)


# =============================================================================
# 2~3. 세션 통합 — ChatSession.beat_grid_apply / preview / preview_off
# =============================================================================


class RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("이 경로는 모델을 부르지 않는다")


class ScriptedApproval:
    """``test_safety_gate.ScriptedApproval``과 같은 모양(이 파일은
    ``server/tests`` 밖 임포트를 늘리지 않으려 복제한다 — 결정적이고
    짧다)."""

    def __init__(self, decisions=(True,)):
        self.decisions = list(decisions)
        self.requests = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        if not self.decisions:
            return False
        return self.decisions.pop(0)


_SEQUENCES_SECTION = {"children": []}
_TIMECODE_POOL_CHILDREN_EMPTY = {"children": [], "node": {"childCount": 0, "enumeration": "ok"}}


def _bar_map(bpm: float = 112.35, beats_per_bar: int = 4) -> dict:
    return {
        "bpm": bpm,
        "time_signature": [beats_per_bar, 4],
        "bars": [
            {"bar": n, "start_ms": 1000 + (n - 1) * 2000, "beats_ms": [1000 + (n - 1) * 2000]}
            for n in range(1, 30)
        ],
    }


#: 위치 프리셋 리콜은 M1 게이트에도 디머 속성에도 기대지 않는다
#: (`beat_grid_emit._cue_attribute_commands` — "elif position_preset_no is
#: not None" 분기는 M1 항목도 `dimmer_attributes`도 읍지 않는다) —
#: 그래서 "행복한 경로" 시험은 리그 판독 배선 없이도 성공한다. 프리셋
#: **번호**를 쓰므로 `check_evidence_approval`(REQ-LDBEAT-015(f))이
#: 완전한 `evidence.approval`을 요구한다.
_APPROVED_EVIDENCE = {"approval": {"by": "supervisor", "date": "2026-10-11", "source": "t563"}}


def _timeline(**overrides: object) -> dict:
    base: dict[str, object] = {
        "song_title": "LOVE ATTACK",
        "sequence_number": 210,
        "bar_map": _bar_map(),
        "timecode_number": 20,
        "beat_grid": {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [
                        {
                            "bar": 1,
                            "position_preset_no": "1.1",
                            "evidence": _APPROVED_EVIDENCE,
                        }
                    ],
                }
            ],
            "probe_results": {1: "통과", 2: "통과", 4: "통과", 5: "통과", 7: "통과", 9: "통과"},
        },
    }
    base.update(overrides)
    return base


#: 카드 t600 — 이 시험들의 칸이 가리키는 프리셋 번호가 콘솔 풀에 **있는** 상태.
_EXISTING_PRESET_POOLS = {
    f"DataPool/PresetPools/{pool}": {
        "children": [{"i": i, "name": f"P{pool}.{i}"} for i in range(1, 6)]
    }
    for pool in (1, 2, 3, 4)
}


def _state_tree() -> dict:
    return {
        # 카드 t600 — 반영은 승인된 칸의 프리셋 번호도 콘솔 풀을 읽어 가른다(빈
        # 번호·못 읽은 풀은 송신 보류). 이 시험들이 쓰는 번호는 콘솔에 있는 프리셋이다.
        **_EXISTING_PRESET_POOLS,
        "DataPool/Sequences": _SEQUENCES_SECTION,
        "DataPool/Timecodes": _TIMECODE_POOL_CHILDREN_EMPTY,
    }


def _new_session(
    tmp_path,
    *,
    store: SongTimelineStore,
    decisions=(True, True, True, True, True),
    state_tree: dict | None = None,
    sent: list[dict] | None = None,
):
    console = FakeConsole(state_tree=state_tree if state_tree is not None else _state_tree())
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


@pytest.fixture
def harness(tmp_path):
    store = SongTimelineStore()
    store.latest = _timeline()
    sent: list[dict] = []
    session, console, approval, audit = _new_session(tmp_path, store=store, sent=sent)
    return {
        "tmp_path": tmp_path,
        "store": store,
        "session": session,
        "console": console,
        "approval": approval,
        "audit": audit,
        "sent": sent,
    }


class TestBeatGridApply:
    def test_apply_dispatches_exactly_one_approval_artifact(self, harness):
        event = harness["session"].beat_grid_apply()
        assert event["ok"] is True
        assert len(harness["approval"].requests) == 1

    def test_apply_sends_commands_that_match_the_approved_batch(self, harness):
        harness["session"].beat_grid_apply()
        executed_writes = [cmd for cmd in harness["console"].executed if cmd not in ("SaveShow",)]
        assert "Store Sequence" in executed_writes[0] or any(
            "Store Sequence" in c for c in executed_writes
        )
        assert any("Store Sequence" in c and " Cue " in c for c in executed_writes)

    def test_declined_approval_sends_nothing(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, approval, _audit = _new_session(tmp_path, store=store, decisions=(False,))
        event = session.beat_grid_apply()
        assert event["ok"] is False
        assert console.executed == []

    def test_blocked_emitter_sends_nothing_and_surfaces_the_reason(self, tmp_path):
        store = SongTimelineStore()
        # 곡 타이밍(bar_map)이 없으면 에미터 자신이 **배치 전체**를
        # 거절한다(timing=None) — 커맨드 0줄, console 접촉 0건이어야 한다.
        timeline = _timeline()
        del timeline["bar_map"]
        store.latest = timeline
        session, console, approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_apply()
        assert console.executed == []
        assert event["ok"] is False
        assert "타이밍" in event["reason"]
        assert len(approval.requests) == 0

    def test_apply_resets_pending_count_and_approved_vs_sent_matches(self, harness):
        session = harness["session"]
        session.beat_grid_edit(1, "BACK", {"position_preset_no": "2.3"})
        status_before = session.beat_grid_apply()
        assert status_before["pending_apply_count"] == 0
        assert status_before["approval_vs_sent"]["match"] is True


class TestBeatGridPreview:
    def test_preview_before_any_apply_is_refused(self, harness):
        event = harness["session"].beat_grid_preview(1)
        assert event["ok"] is False
        assert harness["console"].executed == []

    def test_preview_session_approval_reason_appears_only_on_the_first_call(self, harness):
        """REQ-LDBEAT-012(b) — 이 세션이 스스로 미리보기 승인을 세션 시작
        1회만 **요청하는지**(``PreviewApprovalSession``이 다스리는 범위).

        ⚠️ **갭 — gate 는 "Goto"/"Off"가 참조하는 ``Sequence N`` 을 매번
        독립적으로 검증한다**(``classify.py`` ``_extract_reference`` +
        ``expand.py`` 의 body 검증, `server/web/panel.py`의 기존 Goto
        처리도 같은 경로를 탄다) — 이 테스트 하네스처럼 그 바디(해당
        시퀀스의 큐 이름들)를 콘솔에서 검증할 수 없으면 게이트 **자신이**
        매 호출마다 독립적으로 승인을 요구한다(REQ-BULKGATE 와 무관한,
        이 저장소의 선재 안전 설계). 이 메서드가 다스리는 것은 **이
        세션이 자기 사유를 몇 번 보태느냐**뿐이다 — 그래서 "요청 수"가
        아니라 "요청에 실린 사유 문자열"을 잰다."""
        session = harness["session"]
        approval = harness["approval"]
        console = harness["console"]
        session.beat_grid_apply()

        event = session.beat_grid_preview(1)
        assert event["ok"] is True
        assert any("Goto Cue" in c for c in console.executed)
        first_request = approval.requests[-1]
        first_reasons = [reason for item in first_request.items for reason in item.risk_reasons]
        assert any("세션 시작 1회 승인" in reason for reason in first_reasons)

        console.executed.clear()
        event2 = session.beat_grid_preview(1)
        assert event2["ok"] is True
        assert any("Goto Cue" in c for c in console.executed)
        second_request = approval.requests[-1]
        second_reasons = [reason for item in second_request.items for reason in item.risk_reasons]
        # 두 번째 호출은 이 세션이 다시 사유를 보태지 않는다 — 요청 자체가
        # 사라지는 것은 보장하지 못한다(위 갭 참조).
        assert not any("세션 시작 1회 승인" in reason for reason in second_reasons)

    def test_preview_off_emits_off_sequence(self, harness):
        session = harness["session"]
        console = harness["console"]
        session.beat_grid_apply()
        session.beat_grid_preview(1)
        console.executed.clear()
        event = session.beat_grid_preview_off()
        assert event["ok"] is True
        assert any("Off Sequence" in c for c in console.executed)


def _status_events(sent: list[dict]) -> list[dict]:
    return [event for event in sent if event.get("type") == "beat_grid_send_status"]


def _timeline_events(sent: list[dict]) -> list[dict]:
    return [event for event in sent if event.get("type") == "song_timeline"]


def _last_unsent_cells(sent: list[dict]) -> list[dict] | None:
    return _timeline_events(sent)[-1]["timeline"]["beat_grid"]["unsent_cells"]


class TestBeatGridUnsentCells:
    """코디네이터 계약(2026-10-11, t568과 합의) — 대기 수(pending_apply_count)는
    더는 "성공한 편집 횟수" 카운터가 아니라 곡별 칸 스냅샷과의 차이
    (``unsent_cells``) 하나다. ``beat_grid_send_status``의
    ``pending_apply_count``는 그 길이(또는 스냅샷이 없으면 ``None``)와
    **항상 같아야 한다**(단일 출처, 계약 5항)."""

    def test_no_snapshot_yet_is_null_not_empty_list(self, harness):
        session = harness["session"]
        session.beat_grid_edit(1, "BACK", {"position_preset_no": "2.3"})
        statuses = _status_events(harness["sent"])
        assert statuses[-1]["pending_apply_count"] is None
        assert _last_unsent_cells(harness["sent"]) is None

    def test_after_a_successful_apply_unsent_cells_is_empty(self, harness):
        session = harness["session"]
        apply_status = session.beat_grid_apply()
        assert apply_status["ok"] is True
        assert apply_status["pending_apply_count"] == 0
        assert _last_unsent_cells(harness["sent"]) == []

    def test_editing_one_cell_after_apply_names_exactly_that_cell(self, harness):
        session = harness["session"]
        session.beat_grid_apply()
        session.beat_grid_edit(1, "BACK", {"position_preset_no": "2.4"})
        statuses = _status_events(harness["sent"])
        assert statuses[-1]["pending_apply_count"] == 1
        unsent = _last_unsent_cells(harness["sent"])
        assert unsent == [{"group_name": "BACK", "bar": 1}]

    def test_declined_apply_leaves_the_snapshot_and_unsent_cells_unchanged(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _timeline()
        sent: list[dict] = []
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, decisions=(True, False), sent=sent
        )
        session.beat_grid_apply()  # 성공 — 스냅샷을 찍는다.
        session.beat_grid_edit(1, "BACK", {"position_preset_no": "2.4"})  # unsent 1건.
        before = _last_unsent_cells(sent)
        assert before == [{"group_name": "BACK", "bar": 1}]
        declined = session.beat_grid_apply()  # 각본 두 번째 결정 — 거절.
        assert declined["ok"] is False
        after = _last_unsent_cells(sent)
        # 스냅샷이 그대로라 거절 뒤에도 같은 칸이 계속 "미반영"으로 남는다.
        assert after == before

    def test_two_songs_have_independent_snapshots(self, tmp_path):
        store = SongTimelineStore()
        store.latest = _timeline()
        sent: list[dict] = []
        session, console, approval, _audit = _new_session(tmp_path, store=store, sent=sent)
        session.beat_grid_apply()
        assert _last_unsent_cells(sent) == []

        other_song = _timeline(song_title="OTHER SONG", sequence_number=211)
        store.latest = other_song
        session.beat_grid_edit(1, "BACK", {"position_preset_no": "9.9"})
        # 다른 곡은 아직 반영 기록이 없다 — 첫 곡의 스냅샷을 빌려 오지 않는다.
        assert _last_unsent_cells(sent) is None

        store.latest = _timeline()
        session.beat_grid_edit(1, "BACK", {"position_preset_no": "2.4"})
        # 첫 곡으로 돌아오면 그 곡의 스냅샷(반영 완료)이 여전히 살아 있다.
        assert _last_unsent_cells(sent) == [{"group_name": "BACK", "bar": 1}]

"""칸 옮기기를 콘솔 타임코드 이벤트에 바로 반영하는 세션 경로 (SPEC-LDRHYTHM-001 TC5).

격자에서 칸을 옮기면 그 칸의 TC5 이벤트 시각도 콘솔에서 바로 옮긴다
(``ChatSession.beat_grid_cell_edit``). 세션은 진짜 ``SafetyGate`` 와 메모리 안 상태 나무를 가진 가짜
콘솔(``FakeConsole`` 계열)로 조립한다 — 승인 채널·게이트·``_dispatch_declared`` 를 실제로 지난다.
콘솔 접촉 0건: 실기 클라이언트는 만들지 않고, 보내는 줄은 가짜 콘솔이 받아 적는다.

콘솔의 타임코드 트랙과 이벤트는 **실제 에미터**가 이 격자에서 내는 시각으로 채운다(손으로 쓴 숫자가
아니다). 그래서 옮긴 뒤 콘솔의 이벤트가 같은 격자를 처음부터 다시 반영했을 때와 같은지를 에미터를
심판으로 견준다(「옮기기 = 다시 반영」).

시험하는 것:

1. 승인 안 된 옮기기는 카드를 한 번 묻고, 성공하면 격자·소유 기록·칸 기록이 함께 옮겨지고 옮기기
   범위만 승인으로 남는다. 승인된 범위면 카드 없이 계획한 줄만 보낸다.
2. 보내기 전에 거절하는 갈래 — 격자 규칙, 소유 기록, 콘솔 트랙·이벤트 찾기 — 는 아무것도 보내지 않고
   격자·기록을 그대로 두며, 한국어 사유를 ``beat_grid_send_status`` 로 클라이언트에 보낸다.
3. 소유하지 않은 타임코드는 읽지도 쓰지도 않는다. 허용 목록(``move_bundle_allowed``)이 마지막
   안전핀이다.
4. 승인 카드 거절, 승인 창이 열린 사이 바뀐 이벤트(송신 직전 재확인), 줄 하나의 실패는 아무것도
   확정하지 않고 옮기기 승인도 남기지 않는다.
5. 승인 창이 열린 사이 다른 연결이 격자를 고친 경우에도 그 고침을 지우지 않는다.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from server.design.beat_grid_console_audio_offset import CONSOLE_AUDIO_OFFSET_SECONDS
from server.design.beat_grid_emit import emit_beat_grid_write_bundle
from server.design.beat_grid_send import (
    beat_grid_cell_snapshot,
    build_song_timing_from_bar_map,
    unsent_beat_grid_cells,
)
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_beat_grid_emit_t549 import _ALL_M1_PASS, _position_cue, _track
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole
from .test_web_beat_grid_send_t563 import _approve_until, _send

HANGUL = re.compile(r"[가-힣]")

SONG = ("LOVE ATTACK", 210)
TIMECODE = 5
OWNED_NAME = "LDBEAT Timecode 5"
LEAD = CONSOLE_AUDIO_OFFSET_SECONDS
_MOVE = frozenset({"move"})
_CREATE_DELETE = frozenset({"create_delete"})

# 감독에게 그대로 보이는 고정 사유 — 문구가 바뀌면 시험이 붉어져야 한다.
CARD_TEXT = (
    "칸 편집 바로 반영 — 칸을 옮기면 콘솔의 이벤트 시각도 바로 바뀝니다. "
    "이 승인은 이 서버를 켜 둔 동안 옮기기에만 씁니다."
)
NO_GRID = "이 곡의 격자가 없습니다"
NO_RECORD = (
    "이 곡은 아직 콘솔에 보낸 기록이 없어 칸을 바로 옮길 수 없습니다. ⇪ 전체 반영을 먼저 해 주세요"
)
NO_TRACK = "콘솔에서 이 줄의 트랙을 찾지 못했습니다"
NO_EVENT = "콘솔의 이벤트를 시각으로 찾지 못해 옮기지 않았습니다"

# 120 BPM 4/4 — 한 박 0.5초, 한 마디 2초, 1마디 다운비트 1.5초, 콘솔 지연 3.002초.
#   BACK: 3마디 8.502 · 5마디(3박 트리거) 13.502 · 9마디 20.502
#   SIDE: 3마디 8.502 · 7마디 16.502
LINE_BACK_5_TO_6 = "Set Timecode 5.1.1.1.1.2 Property 'Time' 15.502"
LINE_BACK_9_TO_11 = "Set Timecode 5.1.1.1.1.3 Property 'Time' 24.502"
LINE_SIDE_7_TO_8 = "Set Timecode 5.1.2.1.1.2 Property 'Time' 18.502"

#: 콘솔 타임코드의 트랙 상태 자리(1번은 마커) — 명령에 쓰는 트랙 번호는 자리 - 1 이다.
_STATE_INDEX = {"BACK": 2, "SIDE": 3}
_SEQUENCES = {"BACK": 1, "SIDE": 2}
_TARGETS = {"BACK": "LDBEAT BACK", "SIDE": "LDBEAT SIDE"}


# == 하니스 ===========================================================================


def _move(group: str, bar: int, to_bar: int) -> dict:
    return {"op": "move", "group_name": group, "bar": bar, "to_bar": to_bar}


def _lit(cue: dict, label: str, **entry: object) -> dict:
    """켜진 칸으로 만든다 — 꺼진 칸 사이에는 반영 준비(MIB)가 사전이동 큐를 끼우고 그 이벤트가 칸
    이벤트와 섞이기 때문이다(그 경우는 따로 시험한다)."""
    cue["label"] = label
    cue["entry"] = {**cue["entry"], **entry}
    return cue


def _tracks() -> list[dict]:
    return [
        _track(
            "BACK",
            7,
            [
                _lit(_position_cue(3, position_preset_no="1.1"), "A"),
                _lit(_position_cue(5, position_preset_no="1.2"), "B", trigger_beat=3),
                _lit(_position_cue(9, position_preset_no="1.3"), "C"),
            ],
        ),
        _track(
            "SIDE",
            8,
            [
                _lit(_position_cue(3, position_preset_no="2.1"), "D"),
                _lit(_position_cue(7, position_preset_no="2.2"), "E"),
            ],
        ),
    ]


def _bar_map() -> dict:
    return {
        "bpm": 120.0,
        "time_signature": [4, 4],
        "bars": [{"bar": 1, "start_ms": 1500, "beats_ms": [1500, 2000, 2500, 3000]}],
    }


def _timeline(tracks: list[dict] | None = None) -> dict:
    return {
        "song_title": SONG[0],
        "sequence_number": SONG[1],
        "bar_map": _bar_map(),
        "timecode_number": TIMECODE,
        "beat_grid": {
            "tracks": tracks if tracks is not None else _tracks(),
            "probe_results": dict(_ALL_M1_PASS),
        },
    }


def _record() -> dict:
    return {
        "timecode_number": TIMECODE,
        "timecode_name": OWNED_NAME,
        "extra_timecodes": [],
        "tracks": {
            "BACK": {
                "sequence_number": 1,
                "sequence_name": "LDBEAT BACK",
                "cues": {"3": 1, "5": 2, "9": 3},
            },
            "SIDE": {
                "sequence_number": 2,
                "sequence_name": "LDBEAT SIDE",
                "cues": {"3": 1, "7": 2},
            },
        },
    }


def _emitted_event_ms(tracks: list[dict]) -> dict[str, list[int]]:
    """실제 에미터가 이 격자에서 줄마다 내는 타임코드 이벤트 시각(ms, 오름차순).
    콘솔을 채우고 견주는 기준이다."""
    result = emit_beat_grid_write_bundle(
        tracks,
        timing=build_song_timing_from_bar_map(_bar_map()),
        sequence_numbers=_SEQUENCES,
        timecode_numbers={name: TIMECODE for name in _SEQUENCES},
        dimmer_attributes={},
        probe_results=_ALL_M1_PASS,
        timecode_lead_seconds=LEAD,
    )
    assert result.blocked_reason is None
    assert all(cue.trigger_ms is not None for track in result.tracks for cue in track.cues)
    return {
        track.group_name: sorted({cue.trigger_ms for cue in track.cues if cue.trigger_ms})
        for track in result.tracks
    }


def _timecode_nodes(
    timecode: int,
    event_ms: dict[str, list[int]],
    targets: dict[str, str] | None = None,
    rows: dict[str, int] | None = None,
) -> dict:
    """콘솔 상태 나무에서 타임코드 하나의 노드들 — 트랙(1번 자리는 마커)과 그 이벤트 컨테이너.

    ``rows`` 는 이 타임코드가 가진 줄 -> 트랙 상태 자리다(생략하면 두 줄 모두)."""
    targets = targets or _TARGETS
    rows = rows or _STATE_INDEX
    base = f"DataPool/Timecodes/{timecode}/1"
    nodes: dict = {
        base: {
            "children": [
                {"i": 1, "class": "Marker"},
                *({"i": index, "class": "Track"} for index in rows.values()),
            ]
        },
        f"{base}/1": {"children": [], "props": {}},
    }
    for group, index in rows.items():
        nodes[f"{base}/{index}"] = {
            "children": [],
            "props": {"TARGET": targets[group], "NAME": f"Track {index - 1}"},
        }
        container = f"{base}/{index}/1/1"
        nodes[container] = {
            "children": [{"i": n, "class": "TimeEvent"} for n in range(1, len(event_ms[group]) + 1)]
        }
        for n, ms in enumerate(event_ms[group], start=1):
            nodes[f"{container}/{n}"] = {"children": [], "props": {"TIME": f"{ms / 1000:.6f}"}}
    return nodes


def _console_tree(event_ms: dict[str, list[int]], targets: dict[str, str] | None = None) -> dict:
    return {
        "DataPool/Timecodes": {
            "children": [{"i": TIMECODE, "name": OWNED_NAME}],
            "node": {"childCount": 1},
        },
        **_timecode_nodes(TIMECODE, event_ms, targets),
    }


_SET_TIME = re.compile(r"Set Timecode (\d+)\.1\.(\d+)\.1\.1\.(\d+) Property 'Time' (\S+)")


class _MovingConsole(FakeConsole):
    """``Set … Property 'Time'`` 줄을 받으면 상태 나무의 이벤트 시각을 바꾸고, 읽은 경로를 적어 두는
    가짜 콘솔. 실제 콘솔로는 한 바이트도 나가지 않는다."""

    def __init__(self, state_tree: dict) -> None:
        super().__init__(state_tree=state_tree)
        self.reads: list[str] = []

    def execute(self, command: str):
        outcome = super().execute(command)
        moved = _SET_TIME.fullmatch(command)
        if moved is not None and outcome.status == "ok":
            timecode, track, event, seconds = moved.groups()
            path = f"DataPool/Timecodes/{timecode}/1/{int(track) + 1}/1/1/{event}"
            self.state_tree[path]["props"]["TIME"] = f"{float(seconds):.6f}"
        return outcome

    def query_state(self, path: str) -> dict:
        self.reads.append(path)
        return super().query_state(path)

    def query_properties(self, path: str, property_names, *, offset=None) -> dict:
        self.reads.append(path)
        return super().query_properties(path, property_names, offset=offset)


def _console_event_ms(console: FakeConsole, group: str, timecode: int = TIMECODE) -> list[int]:
    container = f"DataPool/Timecodes/{timecode}/1/{_STATE_INDEX[group]}/1/1"
    return sorted(
        round(float(console.state_tree[f"{container}/{child['i']}"]["props"]["TIME"]) * 1000)
        for child in console.state_tree[container]["children"]
    )


class _RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - 이 경로는 모델을 부르지 않는다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


_UNSET = object()


@dataclass
class _Harness:
    session: ChatSession
    store: SongTimelineStore
    console: _MovingConsole
    gate: SafetyGate
    audit: AuditLog
    sent: list[dict]
    hooks: SimpleNamespace
    before: dict


def _build(
    tmp_path,
    *,
    answers: tuple[bool, ...] = (True,),
    timeline: dict | None = None,
    tree: dict | None = None,
    record: object = _UNSET,
) -> _Harness:
    """세션 하나 — 실제 게이트·승인 채널, 가짜 콘솔. ``answers`` 는 카드가 뜰 때마다 차례로 답한다.

    ``hooks.on_card`` 는 카드가 뜬 바로 그 순간(승인 창이 열린 사이) 한 번 불린다."""
    timeline = timeline if timeline is not None else _timeline()
    store = SongTimelineStore()
    store.latest = timeline
    grid = timeline["beat_grid"]
    key = (timeline["song_title"], timeline["sequence_number"])
    store.beat_grid_snapshots[key] = beat_grid_cell_snapshot(grid)
    assert unsent_beat_grid_cells(grid, store.beat_grid_snapshots[key]) == []
    if record is _UNSET:
        record = _record()
    if record is not None:
        store.set_beat_grid_allocation(SONG, record)  # type: ignore[arg-type]
    console = _MovingConsole(
        tree if tree is not None else _console_tree(_emitted_event_ms(grid["tracks"]))
    )
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    sent: list[dict] = []
    hooks = SimpleNamespace(on_card=None)
    pending = list(answers)

    def deliver(event: dict) -> None:
        sent.append(event)
        if event.get("type") == "approval_request":
            if hooks.on_card is not None:
                hooks.on_card()
            channel.resolve(event["request_id"], approved=pending.pop(0) if pending else False)

    session = ChatSession(
        gate=gate,
        provider=_RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=deliver,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    return _Harness(
        session=session,
        store=store,
        console=console,
        gate=gate,
        audit=audit,
        sent=sent,
        hooks=hooks,
        before={
            "timeline": copy.deepcopy(store.latest),
            "record": copy.deepcopy(store.beat_grid_allocation(SONG)),
            "snapshot": copy.deepcopy(store.beat_grid_snapshots.get(key)),
            "key": key,
        },
    )


def _cards(h: _Harness) -> list[dict]:
    return [event for event in h.sent if event.get("type") == "approval_request"]


def _status(h: _Harness) -> dict:
    """클라이언트가 받은 마지막 칸 편집 상태."""
    statuses = [
        event
        for event in h.sent
        if event.get("type") == "beat_grid_send_status" and event.get("last_action") == "cell_edit"
    ]
    assert statuses, "칸 편집은 어떤 결과든 상태로 끝나야 한다"
    return statuses[-1]


def _bars(h: _Harness, group: str) -> list[int]:
    (track,) = (t for t in h.store.latest["beat_grid"]["tracks"] if t["group_name"] == group)
    return [cue["bar"] for cue in track["cues"]]


def _assert_untouched(h: _Harness) -> None:
    """격자·소유 기록·칸 기록이 시작 때 그대로다."""
    assert h.store.latest == h.before["timeline"]
    assert h.store.beat_grid_allocation(SONG) == h.before["record"]
    assert h.store.beat_grid_snapshots.get(h.before["key"]) == h.before["snapshot"]


def _assert_refused_before_sending(h: _Harness, event: dict, *needles: str) -> None:
    assert event["ok"] is False
    assert event["last_action"] == "cell_edit"
    assert HANGUL.search(event["reason"])
    for needle in needles:
        assert needle in event["reason"]
    assert _status(h) == event  # 사유가 클라이언트에 닿는다
    assert h.console.executed == []
    assert _cards(h) == []
    assert not h.store.cell_live_approval.covers(_MOVE)
    _assert_untouched(h)


@dataclass
class _PreapprovedCall:
    commands: list[str]
    risk: object
    showfile_backup: object


def _spy_preapproved(monkeypatch: pytest.MonkeyPatch, gate: SafetyGate) -> list[_PreapprovedCall]:
    """게이트의 ``execute_preapproved`` 호출을 적어 두고 그대로 넘긴다(승인 카드 없는 길)."""
    calls: list[_PreapprovedCall] = []
    real = gate.execute_preapproved

    def spy(commands, *, risk=None, showfile_backup=True):
        calls.append(_PreapprovedCall(list(commands), risk, showfile_backup))
        return real(commands, risk=risk, showfile_backup=showfile_backup)

    monkeypatch.setattr(gate, "execute_preapproved", spy)
    return calls


def _shift_event(tree: dict, group: str, event: int, delta: float) -> None:
    """콘솔 상태 나무에서 이벤트 하나의 시각을 ``delta`` 초 옮긴다(누가 콘솔에서 손으로 옮긴 듯)."""
    path = f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX[group]}/1/1/{event}"
    props = tree[path]["props"]
    props["TIME"] = f"{float(props['TIME']) + delta:.6f}"


# == 하니스가 믿을 만한가 ================================================================


class TestHarness:
    def test_the_console_holds_exactly_what_the_real_emitter_would_send(self, tmp_path) -> None:
        h = _build(tmp_path)
        assert _console_event_ms(h.console, "BACK") == [8502, 13502, 20502]
        assert _console_event_ms(h.console, "SIDE") == [8502, 16502]
        assert _emitted_event_ms(h.store.latest["beat_grid"]["tracks"]) == {
            "BACK": [8502, 13502, 20502],
            "SIDE": [8502, 16502],
        }

    def test_a_fresh_session_has_no_approval_and_no_unsent_cell(self, tmp_path) -> None:
        h = _build(tmp_path)
        assert not h.store.cell_live_approval.covers(_MOVE)
        assert h.console.executed == []


# == 승인 안 된 옮기기 — 카드를 한 번 묻는다 ===============================================


class TestUnapprovedMove:
    def test_a_card_is_asked_and_the_move_lands_everywhere_once_it_succeeds(self, tmp_path) -> None:
        h = _build(tmp_path)
        original = copy.deepcopy(h.store.latest["beat_grid"]["tracks"][0]["cues"][1])

        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])

        cards = _cards(h)
        assert len(cards) == 1
        assert [item["command"] for item in cards[0]["items"]] == [LINE_BACK_5_TO_6]
        assert all(CARD_TEXT in item["risk_reasons"] for item in cards[0]["items"])
        approved = [e for e in h.audit.iter_events() if e["event"] == "approved"]
        assert [e.get("kind") for e in approved] == ["beat_grid_cell_live"]
        # 카드는 결과 상태보다 먼저 나갔다.
        assert h.sent.index(cards[0]) < h.sent.index(_status(h))
        assert h.console.executed == [LINE_BACK_5_TO_6]
        # 격자: 그 칸은 bar 만 바뀐 같은 칸이다.
        assert _bars(h, "BACK") == [3, 6, 9]
        assert _bars(h, "SIDE") == [3, 7]
        moved = h.store.latest["beat_grid"]["tracks"][0]["cues"][1]
        assert moved == {**original, "bar": 6}
        # 소유 기록과 칸 기록도 같이 옮겨졌다 — 큐 번호는 그대로다.
        assert h.store.beat_grid_allocation(SONG)["tracks"]["BACK"]["cues"] == {
            "3": 1,
            "6": 2,
            "9": 3,
        }
        snapshot = h.store.beat_grid_snapshots[h.before["key"]]
        assert ("BACK", 6) in snapshot
        assert ("BACK", 5) not in snapshot
        assert snapshot == beat_grid_cell_snapshot(h.store.latest["beat_grid"])
        # 옮기기 범위만 승인으로 남는다.
        assert h.store.cell_live_approval.covers(_MOVE)
        assert not h.store.cell_live_approval.covers(_CREATE_DELETE)
        # 상태: 성공이고 미반영 칸이 없다(옮긴 칸이 「미반영」으로 남지 않는다).
        assert event["ok"] is True
        assert event["last_action"] == "cell_edit"
        assert event["pending_apply_count"] == 0
        assert _status(h) == event

    def test_the_client_gets_the_moved_grid_to_redraw(self, tmp_path) -> None:
        h = _build(tmp_path)
        h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        timelines = [e for e in h.sent if e.get("type") == "song_timeline"]
        assert timelines
        tracks = timelines[-1]["timeline"]["beat_grid"]["tracks"]
        assert [cue["bar"] for cue in tracks[0]["cues"]] == [3, 6, 9]

    def test_the_first_card_opens_later_moves_for_the_rest_of_the_server_run(
        self, tmp_path
    ) -> None:
        h = _build(tmp_path, answers=(True,))
        h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        h.session.beat_grid_cell_edit([_move("BACK", 9, 11)])
        assert len(_cards(h)) == 1
        assert h.console.executed == [LINE_BACK_5_TO_6, LINE_BACK_9_TO_11]
        assert _bars(h, "BACK") == [3, 6, 11]

    def test_several_cells_in_several_rows_go_as_one_bundle_under_one_card(self, tmp_path) -> None:
        h = _build(tmp_path)
        event = h.session.beat_grid_cell_edit(
            [_move("BACK", 5, 6), _move("BACK", 9, 11), _move("SIDE", 7, 8)]
        )
        assert len(_cards(h)) == 1
        planned = [LINE_BACK_5_TO_6, LINE_BACK_9_TO_11, LINE_SIDE_7_TO_8]
        assert [item["command"] for item in _cards(h)[0]["items"]] == planned
        assert h.console.executed == planned
        assert event["ok"] is True
        assert (_bars(h, "BACK"), _bars(h, "SIDE")) == ([3, 6, 11], [3, 8])


# == 승인된 범위 — 카드 없이 계획한 줄만 =================================================


class TestApprovedMove:
    def test_an_approved_scope_sends_exactly_the_planned_lines_and_asks_no_card(
        self, tmp_path, monkeypatch
    ) -> None:
        h = _build(tmp_path)
        h.store.cell_live_approval.approve(_MOVE)
        calls = _spy_preapproved(monkeypatch, h.gate)

        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6), _move("SIDE", 7, 8)])

        planned = [LINE_BACK_5_TO_6, LINE_SIDE_7_TO_8]
        assert [call.commands for call in calls] == [planned]
        assert calls[0].risk.kind == "beat_grid_cell_live_session"
        assert calls[0].showfile_backup is False
        assert _cards(h) == []
        assert h.console.executed == planned
        assert event["ok"] is True
        assert (_bars(h, "BACK"), _bars(h, "SIDE")) == ([3, 6, 9], [3, 8])
        assert h.store.beat_grid_allocation(SONG)["tracks"]["SIDE"]["cues"] == {"3": 1, "8": 2}

    def test_a_scope_other_than_move_does_not_open_the_move_path(self, tmp_path) -> None:
        h = _build(tmp_path)
        h.store.cell_live_approval.approve(_CREATE_DELETE)
        h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert len(_cards(h)) == 1


# == 보내기 전에 거절 — 아무것도 보내지 않고 아무것도 바꾸지 않는다 ==========================


class TestRefusedByTheGridRules:
    @pytest.mark.parametrize(
        ("ops", "needle"),
        [
            pytest.param([_move("BACK", 4, 6)], "4마디", id="no-cell-starts-at-the-bar"),
            pytest.param([_move("BACK", 5, 9)], "9마디", id="lands-on-another-cell"),
            pytest.param([_move("BACK", 5, 10)], "넘어", id="jumps-over-a-cell"),
            pytest.param([_move("BACK", 5, 5)], "같은 마디", id="same-bar"),
            pytest.param([_move("BACK", 5, 6), _move("BACK", 5, 7)], "두 번", id="same-cell-twice"),
            pytest.param([_move("NOPE", 5, 6)], "NOPE", id="no-such-row"),
        ],
    )
    def test_a_move_the_grid_cannot_make_is_refused_with_its_reason(
        self, tmp_path, ops: list, needle: str
    ) -> None:
        h = _build(tmp_path)
        event = h.session.beat_grid_cell_edit(ops)
        _assert_refused_before_sending(h, event, needle)

    @pytest.mark.parametrize(
        ("ops", "needle"),
        [
            pytest.param([], "고르지 않았", id="empty"),
            pytest.param(
                [{"op": "create", "group_name": "BACK", "bar": 3, "to_bar": 5}],
                "옮기기만",
                id="not-a-move",
            ),
            pytest.param(
                [{"op": "move", "group_name": "BACK", "bar": "3", "to_bar": 5}],
                "올바르지 않",
                id="bar-is-text",
            ),
            pytest.param(
                [{"op": "move", "group_name": "BACK", "bar": 3}], "올바르지 않", id="no-to-bar"
            ),
        ],
    )
    def test_a_request_that_is_not_a_move_is_refused_in_korean(
        self, tmp_path, ops: list, needle: str
    ) -> None:
        h = _build(tmp_path)
        event = h.session.beat_grid_cell_edit(ops)
        _assert_refused_before_sending(h, event, needle)

    def test_a_song_with_no_grid_is_refused(self, tmp_path) -> None:
        h = _build(tmp_path)
        h.store.latest = None  # 격자가 아직 없는 저장소
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is False
        assert NO_GRID in event["reason"]
        assert _status(h) == event
        assert h.console.executed == []


class TestRefusedByTheOwnedRecord:
    @pytest.mark.parametrize(
        "record",
        [
            pytest.param(None, id="no-record"),
            pytest.param(
                {"timecode_number": TIMECODE, "timecode_name": OWNED_NAME, "tracks": {}},
                id="empty-tracks",
            ),
        ],
    )
    def test_a_song_never_sent_to_the_console_names_the_apply_button(
        self, tmp_path, record: dict | None
    ) -> None:
        h = _build(tmp_path, record=record)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, NO_RECORD, "⇪ 전체 반영")
        assert h.console.reads == []  # 기록이 없으면 콘솔을 읽지도 않는다

    def test_a_record_that_does_not_know_the_cue_is_refused_before_anything_is_sent(
        self, tmp_path
    ) -> None:
        record = _record()
        del record["tracks"]["BACK"]["cues"]["5"]
        h = _build(tmp_path, record=record)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "5마디")

    def test_a_song_with_no_timing_is_refused(self, tmp_path) -> None:
        timeline = _timeline()
        del timeline["bar_map"]
        h = _build(tmp_path, timeline=timeline)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "타이밍")

    def test_a_cell_the_emitter_would_have_blocked_has_no_event_to_move(self, tmp_path) -> None:
        tracks = _tracks()
        tracks[0]["cues"][1]["entry"]["trigger_beat"] = (
            9  # 에미터는 이 칸을 막아 이벤트를 만들지 않는다
        )
        h = _build(
            tmp_path,
            timeline=_timeline(tracks),
            tree=_console_tree({"BACK": [8502, 20502], "SIDE": [8502, 16502]}),
        )
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "trigger_beat")


class TestRefusedByTheConsole:
    @staticmethod
    def _tree() -> dict:
        return _console_tree(_emitted_event_ms(_tracks()))

    def test_a_row_with_no_track_on_the_owned_timecode_is_refused(self, tmp_path) -> None:
        tree = self._tree()
        tree[f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX['BACK']}"]["props"]["TARGET"] = (
            "LDBEAT OTHER"
        )
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, NO_TRACK, "BACK")

    def test_a_timecode_with_no_tracks_at_all_is_refused(self, tmp_path) -> None:
        tree = self._tree()
        tree[f"DataPool/Timecodes/{TIMECODE}/1"]["children"] = [{"i": 1, "class": "Marker"}]
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, NO_TRACK)

    def test_two_tracks_on_one_sequence_are_not_guessed_between(self, tmp_path) -> None:
        tree = self._tree()
        tree[f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX['SIDE']}"]["props"]["TARGET"] = (
            "LDBEAT BACK"
        )
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "BACK")

    def test_an_unmoved_row_with_no_track_does_not_block_the_moved_row(self, tmp_path) -> None:
        tree = self._tree()
        tree[f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX['SIDE']}"]["props"]["TARGET"] = (
            "LDBEAT OTHER"
        )
        h = _build(tmp_path, tree=tree, answers=(True,))
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is True
        assert h.console.executed == [LINE_BACK_5_TO_6]

    def test_a_timecode_that_cannot_be_read_is_refused_not_guessed(self, tmp_path) -> None:
        tree = self._tree()
        del tree[f"DataPool/Timecodes/{TIMECODE}/1"]
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "읽지 못")

    def test_a_track_list_that_was_cut_short_is_refused(self, tmp_path) -> None:
        tree = self._tree()
        tree[f"DataPool/Timecodes/{TIMECODE}/1"]["truncated"] = True
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "읽지 못")

    def test_an_event_list_that_was_cut_short_is_refused(self, tmp_path) -> None:
        tree = self._tree()
        tree[f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX['BACK']}/1/1"]["truncated"] = True
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "읽지 못")

    def test_an_event_whose_time_cannot_be_read_refuses_the_whole_move(self, tmp_path) -> None:
        tree = self._tree()
        container = f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX['BACK']}/1/1"
        tree[f"{container}/3"][
            "props"
        ] = {}  # 옮기지 않을 이벤트라도 못 읽으면 모호함을 가릴 수 없다
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "읽지 못")


class TestEventsFoundByTime:
    @staticmethod
    def _tree() -> dict:
        return _console_tree(_emitted_event_ms(_tracks()))

    def test_a_missing_event_is_refused_and_no_other_event_is_touched(self, tmp_path) -> None:
        tree = self._tree()
        container = f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX['BACK']}/1/1"
        tree[container]["children"] = [c for c in tree[container]["children"] if c["i"] != 2]
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, NO_EVENT, "BACK 5마디")

    def test_an_event_at_another_time_is_not_taken_for_the_cell(self, tmp_path) -> None:
        tree = self._tree()
        _shift_event(tree, "BACK", 2, 0.5)
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, NO_EVENT)

    def test_two_events_at_the_cells_time_are_not_guessed_between(self, tmp_path) -> None:
        tree = self._tree()
        container = f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX['BACK']}/1/1"
        tree[container]["children"].append({"i": 4, "class": "TimeEvent"})
        tree[f"{container}/4"] = {"children": [], "props": {"TIME": "13.505000"}}
        h = _build(tmp_path, tree=tree)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, NO_EVENT)

    def test_event_numbers_are_found_by_time_not_by_rank(self, tmp_path) -> None:
        # 칸이 아닌 이벤트(예: 사전이동 큐의 이벤트)가 섞여 있으면 이벤트 번호는 칸 순서와 다르다.
        event_ms = _emitted_event_ms(_tracks())
        event_ms["BACK"] = sorted([*event_ms["BACK"], 11000])  # 8502, 11000, 13502, 20502
        h = _build(tmp_path, tree=_console_tree(event_ms))
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is True
        # 5마디 칸의 이벤트는 순서상 3번째다. 끼어든 11 초 이벤트는 그대로다.
        assert h.console.executed == ["Set Timecode 5.1.1.1.1.3 Property 'Time' 15.502"]
        assert _console_event_ms(h.console, "BACK") == [8502, 11000, 15502, 20502]


# == 옮길 자리에 이미 이벤트가 있는 경우 ================================================


class TestTargetTimeAlreadyTaken:
    @staticmethod
    def _tree_with_stray_event(stray_ms: int) -> dict:
        # 장부(소유 기록·칸 기록)에는 없는 이벤트 — 콘솔이 장부와 어긋난 경우다.
        event_ms = _emitted_event_ms(_tracks())
        event_ms["BACK"] = sorted([*event_ms["BACK"], stray_ms])
        return _console_tree(event_ms)

    @pytest.mark.parametrize("stray_ms", [15502, 15505, 15495], ids=str)
    def test_an_event_already_at_the_target_time_refuses_the_move(
        self, tmp_path, stray_ms: int
    ) -> None:
        # 5마디 칸이 가는 자리(15.502초)에 이벤트가 있으면 같은 시각에 Go+ 가 둘 선다.
        h = _build(tmp_path, tree=self._tree_with_stray_event(stray_ms))
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "BACK 5마디", "이미 다른 이벤트")

    def test_an_event_just_outside_the_same_time_tolerance_does_not_block(self, tmp_path) -> None:
        h = _build(tmp_path, tree=self._tree_with_stray_event(15520))
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is True
        assert _console_event_ms(h.console, "BACK") == [8502, 15502, 15520, 20502]


# == 소유하지 않은 타임코드는 건드리지 않는다 ==============================================


class TestForeignTimecode:
    @staticmethod
    def _tree_with_foreign_timecode() -> dict:
        event_ms = _emitted_event_ms(_tracks())
        tree = _console_tree(event_ms)
        # 이 곡이 소유하지 않은 TC3 — 같은 시퀀스를 가리키는 트랙과, 같은 시각의 이벤트를 가졌다.
        tree.update(_timecode_nodes(3, event_ms))
        return tree

    def test_a_timecode_the_record_does_not_own_is_never_read_or_written(self, tmp_path) -> None:
        h = _build(tmp_path, tree=self._tree_with_foreign_timecode())
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is True
        assert h.console.executed == [LINE_BACK_5_TO_6]
        assert [path for path in h.console.reads if path.startswith("DataPool/Timecodes/3/")] == []
        assert _console_event_ms(h.console, "BACK", timecode=3) == [8502, 13502, 20502]

    def test_a_line_for_another_timecode_is_refused_by_the_allow_list(
        self, tmp_path, monkeypatch
    ) -> None:
        h = _build(tmp_path, tree=self._tree_with_foreign_timecode())
        # 대응표가 소유하지 않은 TC3 의 트랙을 가리키는 고장 — 허용 목록이 마지막 안전핀이다.
        monkeypatch.setattr(
            "server.web.session.console_tracks_for_groups", lambda record, reads: {"BACK": (3, 1)}
        )
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "타임코드 3")
        assert _console_event_ms(h.console, "BACK", timecode=3) == [8502, 13502, 20502]

    def test_a_line_of_another_shape_is_refused_by_the_allow_list(
        self, tmp_path, monkeypatch
    ) -> None:
        h = _build(tmp_path)
        monkeypatch.setattr(
            "server.web.session.plan_tc_cell_commands",
            lambda *args, **kwargs: ["Delete Timecode 5.1.1.1.1.2"],
        )
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        _assert_refused_before_sending(h, event, "허용된 명령 꼴")


# == 승인 카드 거절 · 송신 직전 재확인 · 줄 실패 =========================================


class TestNothingIsCommittedUnlessEveryLineWent:
    def test_a_declined_card_sends_nothing_and_grants_nothing(self, tmp_path) -> None:
        h = _build(tmp_path, answers=(False,))
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert len(_cards(h)) == 1
        assert event["ok"] is False
        assert "거절" in event["reason"]
        assert _status(h) == event
        assert h.console.executed == []
        assert not h.store.cell_live_approval.covers(_MOVE)
        _assert_untouched(h)

    @pytest.mark.parametrize("shift", [0.5, -0.5, 0.011, -0.011], ids=str)
    def test_an_event_that_moved_while_the_card_was_open_blocks_the_whole_bundle(
        self, tmp_path, shift: float
    ) -> None:
        h = _build(tmp_path)
        h.hooks.on_card = lambda: _shift_event(h.console.state_tree, "SIDE", 2, shift)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6), _move("SIDE", 7, 8)])
        assert len(_cards(h)) == 1
        assert event["ok"] is False
        assert "승인을 기다리는 동안" in event["reason"]
        assert "SIDE" in event["reason"]
        assert _status(h) == event
        assert h.console.executed == []  # 바뀌지 않은 BACK 줄도 나가지 않는다
        assert not h.store.cell_live_approval.covers(_MOVE)
        _assert_untouched(h)

    @pytest.mark.parametrize("shift", [0.009, -0.009, 0.0], ids=str)
    def test_a_shift_within_the_same_time_tolerance_does_not_block(
        self, tmp_path, shift: float
    ) -> None:
        h = _build(tmp_path)
        h.hooks.on_card = lambda: _shift_event(h.console.state_tree, "BACK", 2, shift)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is True
        assert h.console.executed == [LINE_BACK_5_TO_6]

    def test_an_event_that_vanished_while_the_card_was_open_blocks_the_bundle(
        self, tmp_path
    ) -> None:
        h = _build(tmp_path)
        path = f"DataPool/Timecodes/{TIMECODE}/1/{_STATE_INDEX['BACK']}/1/1/2"
        h.hooks.on_card = lambda: h.console.state_tree.pop(path)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is False
        assert "읽지 못" in event["reason"]
        assert h.console.executed == []
        assert not h.store.cell_live_approval.covers(_MOVE)
        _assert_untouched(h)

    @pytest.mark.parametrize("preapproved", [False, True], ids=["card", "session-approval"])
    def test_a_failing_line_commits_nothing_and_says_how_many_lines_already_went(
        self, tmp_path, preapproved: bool
    ) -> None:
        h = _build(tmp_path)
        if preapproved:
            h.store.cell_live_approval.approve(_MOVE)
        h.console.fail_on[LINE_BACK_9_TO_11] = "no confirmation"
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6), _move("BACK", 9, 11)])
        assert h.console.executed == [LINE_BACK_5_TO_6, LINE_BACK_9_TO_11]
        assert event["ok"] is False
        assert LINE_BACK_9_TO_11 in event["reason"]
        assert "이미 콘솔에 나간 1줄" in event["reason"]
        assert "⇪ 전체 반영" in event["reason"]
        assert _status(h) == event
        _assert_untouched(h)
        assert (
            h.store.cell_live_approval.covers(_MOVE) is preapproved
        )  # 실패한 카드는 승인을 남기지 않는다

    def test_a_first_line_that_fails_says_nothing_went(self, tmp_path) -> None:
        h = _build(tmp_path)
        h.console.fail_on[LINE_BACK_5_TO_6] = "no confirmation"
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is False
        assert "이미 콘솔에 나간" not in event["reason"]
        _assert_untouched(h)
        assert not h.store.cell_live_approval.covers(_MOVE)


# == 승인 창이 열린 사이 다른 연결이 격자를 고친 경우 =======================================


class TestEditsMadeWhileTheCardWasOpen:
    def test_another_connections_edit_is_kept_and_the_move_still_lands(self, tmp_path) -> None:
        h = _build(tmp_path)

        def other_tab_edits_a_side_cell() -> None:
            latest = copy.deepcopy(h.store.latest)
            latest["beat_grid"]["tracks"][1]["cues"][0]["position_preset_no"] = "9.9"
            h.store.latest = latest

        h.hooks.on_card = other_tab_edits_a_side_cell
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is True
        assert _bars(h, "BACK") == [3, 6, 9]
        assert h.store.latest["beat_grid"]["tracks"][1]["cues"][0]["position_preset_no"] == "9.9"
        assert event["pending_apply_count"] == 1  # 다른 연결이 고친 칸은 미반영으로 남는다

    def test_a_cell_removed_meanwhile_leaves_the_grid_and_says_so(self, tmp_path) -> None:
        h = _build(tmp_path)

        def other_tab_deletes_the_cell() -> None:
            latest = copy.deepcopy(h.store.latest)
            latest["beat_grid"]["tracks"][0]["cues"].pop(1)
            h.store.latest = latest

        h.hooks.on_card = other_tab_deletes_the_cell
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert h.console.executed == [LINE_BACK_5_TO_6]  # 콘솔은 이미 옮겨졌다
        assert event["ok"] is False
        assert "콘솔의 이벤트는 옮겼지만" in event["reason"]
        assert "⇪ 전체 반영" in event["reason"]
        assert _status(h) == event
        # 격자는 다른 연결이 고친 그대로이고, 장부(소유 기록·칸 기록)는 콘솔이 있는 그대로를 적는다.
        assert _bars(h, "BACK") == [3, 9]
        assert h.store.beat_grid_allocation(SONG)["tracks"]["BACK"]["cues"] == {
            "3": 1,
            "6": 2,
            "9": 3,
        }
        assert ("BACK", 6) in h.store.beat_grid_snapshots[h.before["key"]]
        assert event["pending_apply_count"] == 1  # 그래서 이 칸은 미반영으로 센다
        assert h.store.cell_live_approval.covers(_MOVE)  # 승인된 줄은 모두 나갔다


# == 예상하지 못한 오류 — 던지지 않고 사실대로 알린다 =====================================


class TestUnexpectedErrors:
    @staticmethod
    def _explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    def test_an_error_while_sending_is_reported_and_commits_nothing(
        self, tmp_path, monkeypatch
    ) -> None:
        h = _build(tmp_path)
        monkeypatch.setattr(h.session, "_dispatch_declared", self._explode)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is False
        assert "예기치 못한 오류" in event["reason"]
        assert "boom" in event["reason"]
        assert "⇪ 전체 반영" in event["reason"]
        assert _status(h) == event
        assert h.console.executed == []
        assert not h.store.cell_live_approval.covers(_MOVE)
        _assert_untouched(h)

    def test_an_error_while_committing_is_still_reported(self, tmp_path, monkeypatch) -> None:
        # 줄은 이미 나갔다 — 던지면 화면은 아무것도 모른 채 콘솔과 어긋난다.
        h = _build(tmp_path)
        monkeypatch.setattr(h.session, "_draft_badge", self._explode)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert h.console.executed == [LINE_BACK_5_TO_6]
        assert event["ok"] is False
        assert "예기치 못한 오류" in event["reason"]
        assert "boom" in event["reason"]
        assert _status(h) == event


# == 옮긴 뒤 콘솔의 이벤트는 같은 격자를 다시 반영했을 때와 같다 ============================


class TestMovingEqualsApplyingAgain:
    def _assert_console_matches_a_fresh_apply(self, h: _Harness) -> None:
        tracks = h.store.latest["beat_grid"]["tracks"]
        expected = _emitted_event_ms(tracks)
        for group in ("BACK", "SIDE"):
            assert _console_event_ms(h.console, group) == expected[group]
        # 이벤트를 시각순으로 놓으면 칸을 마디순으로 놓은 것과 같은 순서다(칸마다 이벤트 하나).
        timing = build_song_timing_from_bar_map(_bar_map())
        for track in tracks:
            by_bar = sorted(track["cues"], key=lambda cue: cue["bar"])
            assert len(by_bar) == len(_console_event_ms(h.console, track["group_name"]))
            for cue, ms in zip(
                by_bar, _console_event_ms(h.console, track["group_name"]), strict=True
            ):
                offset = 0.5 * (cue["entry"].get("trigger_beat", 1) - 1)
                assert ms / 1000 == pytest.approx(
                    LEAD + timing.bar_start_seconds(cue["bar"]) + offset, abs=0.0006
                )

    def test_several_cells_moved_in_several_rows(self, tmp_path) -> None:
        h = _build(tmp_path)
        h.session.beat_grid_cell_edit(
            [_move("BACK", 5, 6), _move("BACK", 9, 11), _move("SIDE", 7, 8)]
        )
        self._assert_console_matches_a_fresh_apply(h)

    def test_a_block_of_neighbouring_cells_shifted_together(self, tmp_path) -> None:
        # SIDE 의 3·7 마디를 7·9 마디로 — 첫 칸이 둘째 칸의 옛 자리로 들어가고 둘째 칸은 비켜 준다.
        h = _build(tmp_path)
        event = h.session.beat_grid_cell_edit([_move("SIDE", 3, 7), _move("SIDE", 7, 9)])
        assert event["ok"] is True
        assert h.console.executed == [
            "Set Timecode 5.1.2.1.1.1 Property 'Time' 16.502",
            "Set Timecode 5.1.2.1.1.2 Property 'Time' 20.502",
        ]
        assert _bars(h, "SIDE") == [7, 9]
        assert h.store.beat_grid_allocation(SONG)["tracks"]["SIDE"]["cues"] == {"7": 1, "9": 2}
        assert event["pending_apply_count"] == 0
        self._assert_console_matches_a_fresh_apply(h)

    def test_a_cell_with_a_trigger_beat_keeps_its_offset_in_the_new_bar(self, tmp_path) -> None:
        h = _build(tmp_path)
        h.session.beat_grid_cell_edit([_move("BACK", 5, 7)])
        # 7마디 시작 13.5 + 3박 트리거 1.0 + 콘솔 지연 3.002
        assert _console_event_ms(h.console, "BACK") == [8502, 17502, 20502]
        self._assert_console_matches_a_fresh_apply(h)

    def test_a_move_then_a_move_back_returns_the_console_to_where_it_started(
        self, tmp_path
    ) -> None:
        h = _build(tmp_path)
        h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        h.session.beat_grid_cell_edit([_move("BACK", 6, 5)])
        assert _console_event_ms(h.console, "BACK") == [8502, 13502, 20502]
        assert h.store.beat_grid_allocation(SONG) == h.before["record"]
        assert h.store.beat_grid_snapshots[h.before["key"]] == h.before["snapshot"]


# == 줄이 여러 타임코드에 나뉘어 담긴 곡 ===================================================


class TestRowsSplitAcrossTimecodes:
    """줄이 많으면 반영이 다음 타임코드에 이어 담는다.
    그 번호가 소유 기록의 ``extra_timecodes`` 다."""

    @staticmethod
    def _split_tree() -> dict:
        # BACK 은 TC5 의 1번 트랙, SIDE 는 TC6 의 1번 트랙이다(트랙 번호는 타임코드마다 1부터).
        event_ms = _emitted_event_ms(_tracks())
        return {
            "DataPool/Timecodes": {"children": [], "node": {"childCount": 0}},
            **_timecode_nodes(5, event_ms, rows={"BACK": 2}),
            **_timecode_nodes(6, event_ms, rows={"SIDE": 2}),
        }

    @staticmethod
    def _split_record() -> dict:
        record = _record()
        record["extra_timecodes"] = [{"timecode_number": 6, "timecode_name": "LDBEAT Timecode 6"}]
        return record

    def test_each_row_is_moved_on_the_timecode_that_holds_its_track(self, tmp_path) -> None:
        h = _build(tmp_path, tree=self._split_tree(), record=self._split_record())
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6), _move("SIDE", 7, 8)])
        assert event["ok"] is True
        assert h.console.executed == [
            LINE_BACK_5_TO_6,
            "Set Timecode 6.1.1.1.1.2 Property 'Time' 18.502",
        ]
        assert (_bars(h, "BACK"), _bars(h, "SIDE")) == ([3, 6, 9], [3, 8])

    def test_a_timecode_the_record_does_not_list_is_not_searched(self, tmp_path) -> None:
        h = _build(tmp_path, tree=self._split_tree())  # 기록에 TC6 이 없다
        event = h.session.beat_grid_cell_edit([_move("SIDE", 7, 8)])
        _assert_refused_before_sending(h, event, NO_TRACK, "SIDE")
        assert [path for path in h.console.reads if path.startswith("DataPool/Timecodes/6/")] == []


# == WebSocket 층을 지나는 길 ============================================================


def _wire_deps(tmp_path, *, record: object = _UNSET) -> tuple[WebDeps, _MovingConsole]:
    """``create_app`` 이 짓는 실제 연결에 붙일 의존성 — 세션 시험과 같은 콘솔·격자·기록이다."""
    timeline = _timeline()
    console = _MovingConsole(_console_tree(_emitted_event_ms(timeline["beat_grid"]["tracks"])))
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=5.0)
    deps = WebDeps(
        gate=SafetyGate(console=console, audit=audit, approval_port=channel),
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    store = deps.song_timeline_store
    store.latest = timeline
    store.beat_grid_snapshots[SONG] = beat_grid_cell_snapshot(timeline["beat_grid"])
    record = _record() if record is _UNSET else record
    if record is not None:
        store.set_beat_grid_allocation(SONG, record)  # type: ignore[arg-type]
    return deps, console


class TestOverTheWire:
    def test_a_move_frame_asks_the_card_moves_the_event_and_reports_success(self, tmp_path) -> None:
        deps, console = _wire_deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_cell_edit", ops=[_move("BACK", 5, 6)])
            status = _approve_until(ws, "beat_grid_send_status")
        assert (status["last_action"], status["ok"]) == ("cell_edit", True)
        assert console.executed == [LINE_BACK_5_TO_6]
        store = deps.song_timeline_store
        assert [cue["bar"] for cue in store.latest["beat_grid"]["tracks"][0]["cues"]] == [3, 6, 9]
        assert store.cell_live_approval.covers(_MOVE)

    def test_a_refusal_reaches_the_client_as_a_status_with_its_reason(self, tmp_path) -> None:
        deps, console = _wire_deps(tmp_path, record=None)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_cell_edit", ops=[_move("BACK", 5, 6)])
            status = _approve_until(ws, "beat_grid_send_status")
        assert (status["last_action"], status["ok"]) == ("cell_edit", False)
        assert NO_RECORD in status["reason"]
        assert console.executed == []


# == 곡 열쇠가 어긋난 곡(라이브러리에서 불러온 곡) =========================================


class TestSongLoadedFromTheLibrary:
    def test_the_record_found_by_the_original_title_is_written_back_under_that_title(
        self, tmp_path
    ) -> None:
        # 라이브러리에서 불러오면 song_title 이 저장 이름으로 바뀐다.
        # 반영 기록은 원래 제목 열쇠에 남는다.
        timeline = _timeline()
        timeline["song_title"] = "LOVE ATTACK (자동 v1)"
        timeline["beat_grid"]["song_title"] = SONG[0]
        h = _build(tmp_path, timeline=timeline)
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is True
        assert h.store.beat_grid_allocation(SONG)["tracks"]["BACK"]["cues"] == {
            "3": 1,
            "6": 2,
            "9": 3,
        }
        assert h.store.beat_grid_allocation(("LOVE ATTACK (자동 v1)", SONG[1])) is None
        # 칸 기록은 지금 곡 열쇠 아래에 있다.
        assert ("BACK", 6) in h.store.beat_grid_snapshots[h.before["key"]]
        assert event["pending_apply_count"] == 0


class TestSongWithNoCellSnapshot:
    def test_a_song_whose_cell_record_is_gone_moves_without_inventing_one(self, tmp_path) -> None:
        # 서버를 다시 띄우면 칸 기록은 사라지고 소유 기록은 남는다.
        # 옮기기는 없던 칸 기록을 지어내지 않는다.
        h = _build(tmp_path)
        del h.store.beat_grid_snapshots[h.before["key"]]
        event = h.session.beat_grid_cell_edit([_move("BACK", 5, 6)])
        assert event["ok"] is True
        assert h.before["key"] not in h.store.beat_grid_snapshots
        assert event["pending_apply_count"] is None

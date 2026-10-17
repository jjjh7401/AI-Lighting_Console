"""박자 격자 2D 무대 판독 — 장비 좌표 + 그룹→소속 장비 (카드 t565, SPEC-LDBEAT-001 REQ-022).

콘솔 없이 가짜 포트로만 돈다. 가짜 포트는 응답기 PROTOCOL.md §4.2(state 페이징)·
§4.8(props 표 값 offset 페이징, 1.6.6)의 응답 모양을 그대로 흉내 낸다.
"""

from __future__ import annotations

import json

import pytest

from server.bridge.protocol import ProtocolError, build_props_query
from server.design.beat_grid_stage import (
    read_beat_grid_stage,
    read_group_selection,
)

FIXTURES = "Patch/Stages/1/Fixtures"
GROUPS = "ShowData/DataPools/Default/Groups"


def _entry(sf_index: int) -> dict:
    return {"grid": {"inv": 0, "x": 0, "y": 0, "z": 0}, "sf_index": sf_index}


class FakeConsole:
    """state · query_property · query_properties(offset) 를 흉내 내는 읽기 전용 포트."""

    def __init__(
        self,
        *,
        fixtures: list[dict],
        groups: dict[int, tuple[str, list[int]]],
        window: int = 2,
        props_offset_supported: bool = True,
    ) -> None:
        # fixtures: {"slot","fid","name","x","y","z","sf"}
        self.fixtures = fixtures
        self.groups = groups
        self.window = window
        self.props_offset_supported = props_offset_supported
        self.calls: list[tuple] = []

    # -- §4.2 state ---------------------------------------------------------
    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls.append(("state", path, offset))
        if path == FIXTURES:
            children = [
                {"i": f["slot"], "name": f["name"], "class": "Fixture"} for f in self.fixtures
            ]
        elif path == GROUPS:
            children = [
                {"i": no, "name": name, "class": "Group"} for no, (name, _) in self.groups.items()
            ]
        else:
            raise AssertionError(f"unexpected state path {path}")
        return {
            "ok": True,
            "path": path,
            "offset": offset,
            "node": {"childCount": len(children)},
            "children": children[offset:],
            "truncated": False,
        }

    # -- 장비 좌표 (read_spatial_fixtures 가 쓰는 두 읽기) ---------------------
    def _fixture(self, path: str) -> dict:
        slot = int(path.rsplit("/", 1)[1])
        return next(f for f in self.fixtures if f["slot"] == slot)

    def query_property(self, path: str, property_name: str) -> dict:
        self.calls.append(("prop", path, property_name))
        f = self._fixture(path)
        value = {"fid": f["fid"], "posx": f["x"], "posy": f["y"], "posz": f["z"]}[
            property_name.lower()
        ]
        return {"ok": True, "value": str(value)}

    # -- §4.8 props ---------------------------------------------------------
    def query_properties(self, path: str, property_names, *, offset: int | None = None) -> dict:
        names = tuple(property_names)
        self.calls.append(("props", path, names, offset))
        if path.startswith(GROUPS + "/"):
            if not self.props_offset_supported and offset is not None:
                raise RuntimeError("props query failed: path not found (1.6.5 offset token)")
            no = int(path.rsplit("/", 1)[1])
            _, members = self.groups[no]
            entries = [_entry(sf) for sf in members]
            start = offset or 0
            chunk = entries[start : start + self.window]
            read = {
                "n": "SELECTIONDATA",
                "ok": True,
                "t": "table",
                "v": json.dumps(chunk),
                "offset": start,
                "total": len(entries),
                "truncated": start + len(chunk) < len(entries),
            }
            return {"ok": True, "path": path, "reads": [read], "truncated": False}
        f = self._fixture(path)
        reads = []
        for name in names:
            key = name.lower()
            if key == "subfixtureindex":
                reads.append({"n": name, "ok": True, "t": "number", "v": str(f["sf"])})
            else:
                value = {"fid": f["fid"], "posx": f["x"], "posy": f["y"], "posz": f["z"]}[key]
                reads.append({"n": name, "ok": True, "t": "number", "v": str(value)})
        return {"ok": True, "path": path, "reads": reads, "truncated": False}


def _rig() -> FakeConsole:
    fixtures = [
        {"slot": 1, "fid": 201, "name": "Back 1", "x": -2.0, "y": 5.0, "z": 3.0, "sf": 70},
        {"slot": 2, "fid": 202, "name": "Back 2", "x": 2.0, "y": 5.0, "z": 3.0, "sf": 72},
        {"slot": 3, "fid": 301, "name": "Side L 1", "x": -6.0, "y": 1.0, "z": 1.2, "sf": 94},
        {"slot": 4, "fid": 302, "name": "Side L 2", "x": -6.0, "y": 2.0, "z": 2.0, "sf": 96},
        {"slot": 5, "fid": 311, "name": "Side R 1", "x": 6.0, "y": 1.0, "z": 1.2, "sf": 98},
    ]
    groups = {
        4: ("BACK", [70, 72]),
        5: ("SIDE-L", [94, 96]),
        6: ("SIDE-ALL", [94, 96, 98]),
        9: ("KEY", [1]),
    }
    return FakeConsole(fixtures=fixtures, groups=groups)


# -- build_props_query offset (PROTOCOL.md §4.8) --------------------------------


def test_props_query_without_offset_is_byte_identical() -> None:
    assert build_props_query("r1", "Groups/4", ["SELECTIONDATA"]) == build_props_query(
        "r1", "Groups/4", ["SELECTIONDATA"], offset=None
    )
    assert "offset=" not in build_props_query("r1", "Groups/4", ["SELECTIONDATA"])


def test_props_query_offset_zero_still_sends_the_token() -> None:
    """§4.8: 창 모드는 토큰이 있을 때만 — 첫 페이지도 offset=0 을 실어야 한다."""
    line = build_props_query("r1", "Groups/4", ["SELECTIONDATA"], offset=0)
    assert "props r1 SELECTIONDATA Groups/4 offset=0" in line


def test_props_query_offset_requires_exactly_one_name() -> None:
    with pytest.raises(ProtocolError):
        build_props_query("r1", "Groups/4", ["SELECTIONDATA", "NAME"], offset=0)


def test_props_query_offset_must_be_non_negative_int() -> None:
    with pytest.raises(ProtocolError):
        build_props_query("r1", "Groups/4", ["SELECTIONDATA"], offset=-1)
    with pytest.raises(ProtocolError):
        build_props_query("r1", "Groups/4", ["SELECTIONDATA"], offset=True)  # type: ignore[arg-type]


# -- read_group_selection --------------------------------------------------------


def test_group_selection_pages_until_not_truncated() -> None:
    console = _rig()
    result = read_group_selection(console, f"{GROUPS}/6")
    assert result.sf_indexes == (94, 96, 98)
    assert result.complete is True
    assert result.reason is None
    offsets = [c[3] for c in console.calls if c[0] == "props"]
    assert offsets == [0, 2]


def test_group_selection_on_old_responder_is_incomplete_with_reason() -> None:
    console = _rig()
    console.props_offset_supported = False
    result = read_group_selection(console, f"{GROUPS}/4")
    assert result.complete is False
    assert result.sf_indexes == ()
    assert "1.6.5" in (result.reason or "") or "판독 실패" in (result.reason or "")


def test_group_selection_stops_on_no_progress() -> None:
    class Stuck(FakeConsole):
        def query_properties(self, path, property_names, *, offset=None):
            return {
                "ok": True,
                "reads": [
                    {
                        "n": "SELECTIONDATA",
                        "ok": True,
                        "t": "table",
                        "v": "[]",
                        "offset": offset,
                        "total": 3,
                        "truncated": True,
                    }
                ],
            }

    result = read_group_selection(Stuck(fixtures=[], groups={}), f"{GROUPS}/6")
    assert result.complete is False
    assert "진전" in (result.reason or "")


def test_group_selection_rejects_missing_offset_echo() -> None:
    class NoEcho(FakeConsole):
        def query_properties(self, path, property_names, *, offset=None):
            return {
                "ok": True,
                "reads": [
                    {"n": "SELECTIONDATA", "ok": True, "t": "table", "v": "[]", "truncated": True}
                ],
            }

    result = read_group_selection(NoEcho(fixtures=[], groups={}), f"{GROUPS}/6")
    assert result.complete is False
    assert result.reason


# -- read_beat_grid_stage --------------------------------------------------------


def test_stage_returns_fixtures_and_track_groups_only() -> None:
    console = _rig()
    payload = read_beat_grid_stage(
        console,
        fixtures_path=FIXTURES,
        groups_path=GROUPS,
        track_names=["BACK", "side-all", "WASH"],
    )
    assert [f["fid"] for f in payload["fixtures"]] == [201, 202, 301, 302, 311]
    assert payload["fixtures"][0] == {"fid": 201, "name": "Back 1", "x": -2.0, "y": 5.0, "z": 3.0}
    groups = {g["group_name"]: g for g in payload["groups"]}
    # 트랙 이름과 정확히 같은(대소문자만 무시) 콘솔 그룹만 — KEY·SIDE-L 은 트랙이 아니라 없다.
    assert set(groups) == {"BACK", "SIDE-ALL"}
    assert groups["BACK"] == {
        "group_no": 4,
        "group_name": "BACK",
        "member_fids": [201, 202],
        "complete": True,
    }
    assert groups["SIDE-ALL"]["member_fids"] == [301, 302, 311]
    # WASH 는 콘솔에 그룹이 없다 — 지어내지 않고 이유를 남긴다.
    assert any("WASH" in reason for reason in payload["unread"])


def test_stage_reads_every_console_group_when_no_track_names_are_given() -> None:
    # 카드 WT-all-fixtures — 배치 줄을 콘솔 그룹으로 정할 때는 이름을 고르지 않고 전부 읽는다.
    payload = read_beat_grid_stage(
        _rig(), fixtures_path=FIXTURES, groups_path=GROUPS, track_names=None
    )
    groups = {g["group_name"]: g for g in payload["groups"]}
    assert set(groups) == {"BACK", "SIDE-L", "SIDE-ALL", "KEY"}
    assert groups["SIDE-L"]["member_fids"] == [301, 302]
    # KEY 의 sf 1 은 본체 장비에 없다 — 소속을 지어내지 않고 불완전으로 둔다.
    assert groups["KEY"]["complete"] is False
    assert not any("그룹이 없음" in reason for reason in payload["unread"])


def test_stage_never_writes() -> None:
    console = _rig()
    read_beat_grid_stage(console, fixtures_path=FIXTURES, groups_path=GROUPS, track_names=["BACK"])
    assert {c[0] for c in console.calls} <= {"state", "prop", "props"}
    assert not hasattr(console, "execute")


def test_stage_unmatched_sf_index_marks_group_incomplete() -> None:
    console = _rig()
    console.groups[4] = ("BACK", [70, 71, 72])  # 71 = 본체가 아닌 서브픽스처 번호
    payload = read_beat_grid_stage(
        console, fixtures_path=FIXTURES, groups_path=GROUPS, track_names=["BACK"]
    )
    back = payload["groups"][0]
    assert back["member_fids"] == [201, 202]
    assert back["complete"] is False
    assert any("71" in reason or "대응" in reason for reason in payload["unread"])


def test_stage_old_responder_keeps_coordinates_and_reports_groups_unread() -> None:
    console = _rig()
    console.props_offset_supported = False
    payload = read_beat_grid_stage(
        console, fixtures_path=FIXTURES, groups_path=GROUPS, track_names=["BACK"]
    )
    assert len(payload["fixtures"]) == 5
    assert payload["groups"][0]["complete"] is False
    assert payload["groups"][0]["member_fids"] == []
    assert payload["unread"]


def test_stage_without_group_tracks_skips_subfixture_reads() -> None:
    console = _rig()
    read_beat_grid_stage(console, fixtures_path=FIXTURES, groups_path=GROUPS, track_names=["WASH"])
    assert not any(c[0] == "props" and "SUBFIXTUREINDEX" in c[2] for c in console.calls)


def test_stage_coordinate_read_failure_is_reported_not_raised() -> None:
    class Dead(FakeConsole):
        def query_state(self, path, *, offset=0):
            raise RuntimeError("console silent")

    payload = read_beat_grid_stage(
        Dead(fixtures=[], groups={}),
        fixtures_path=FIXTURES,
        groups_path=GROUPS,
        track_names=["BACK"],
    )
    assert payload["fixtures"] == []
    assert payload["groups"] == []
    assert any("좌표" in reason for reason in payload["unread"])


# -- WS 메시지 + 세션 배선 -------------------------------------------------------


def test_stage_request_message_is_payload_free() -> None:
    from server.web.messages import PROTOCOL_VERSION, parse_client_message

    raw = json.dumps({"v": PROTOCOL_VERSION, "type": "beat_grid_stage_request"})
    assert parse_client_message(raw) == {"v": PROTOCOL_VERSION, "type": "beat_grid_stage_request"}


def test_stage_event_shape() -> None:
    from server.web.messages import PROTOCOL_VERSION, beat_grid_stage_event

    event = beat_grid_stage_event(fixtures=[{"fid": 1}], groups=[], unread=["x"])
    assert event == {
        "v": PROTOCOL_VERSION,
        "type": "beat_grid_stage",
        "fixtures": [{"fid": 1}],
        "groups": [],
        "unread": ["x"],
    }


def test_session_sends_stage_event_for_song_tracks(tmp_path) -> None:
    from server.safety.audit import AuditLog
    from server.safety.gate import SafetyGate
    from server.web.approval_bridge import ApprovalChannel
    from server.web.session import ChatSession, SongTimelineStore
    from server.web.timeline_library import SongTimelineLibrary

    from .test_safety_gate import FakeConsole as GateConsole

    class _NoModel:
        def complete(self, *args, **kwargs):  # pragma: no cover - must not be called
            raise AssertionError("이 경로는 모델을 부르지 않는다")

    store = SongTimelineStore()
    store.latest = {"song_title": "LOVE ATTACK", "sequence_number": 210}
    sent: list[dict] = []
    gate_console = GateConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    session = ChatSession(
        gate=SafetyGate(console=gate_console, audit=audit, approval_port=channel),
        provider=_NoModel(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    stage = _rig()
    session._stage_port = stage
    session._rig_paths = {**session._rig_paths, "fixtures": FIXTURES, "groups": GROUPS}

    event = session.beat_grid_stage()

    assert sent == [event]
    assert event["type"] == "beat_grid_stage"
    assert len(event["fixtures"]) == 5
    # LOVE ATTACK 기본 격자의 트랙 중 콘솔(가짜)에 있는 것만 — BACK·SIDE-ALL.
    assert {g["group_name"] for g in event["groups"]} == {"BACK", "SIDE-ALL"}
    assert gate_console.executed == []

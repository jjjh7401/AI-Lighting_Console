"""무대 이벤트 장비의 ``pan_tilt`` — 리그 능력 판독으로 알 때만 싣고, 모르면 키를 뺀다."""

from __future__ import annotations

from server.design.beat_grid_stage import fixture_pan_tilt
from server.design.capability_join import FixtureCapability, RigCapabilities
from server.design.rig_capability_read import DesignRigRead
from server.prechk.capability_read import AxisRange


def _cap(fid: int, attrs: tuple[str, ...], gaps: tuple[str, ...] = ()) -> FixtureCapability:
    return FixtureCapability(
        fid=fid,
        type_slot=1,
        type_name="T",
        mode_slot=1,
        mode_name="M",
        mode_width=None,
        channel_count=len(attrs),
        axes=tuple(AxisRange(attribute=a, channel_name=a) for a in attrs),
        gaps=gaps,
    )


def test_helper_true_false_unknown() -> None:
    assert fixture_pan_tilt(_cap(1, ("Dimmer", "Pan", "Tilt"))) is True
    assert fixture_pan_tilt(_cap(1, ("Tilt",))) is True
    assert fixture_pan_tilt(_cap(2, ("Dimmer", "ColorRGB_R"))) is False
    # 부분 판독에서 안 보이는 것은 「없다」가 아니다
    assert fixture_pan_tilt(_cap(3, ("Dimmer",), gaps=("속성 일부 못 읽음",))) is None
    assert fixture_pan_tilt(_cap(3, ("Pan",), gaps=("일부",))) is True


def _session(tmp_path, rig_read: DesignRigRead):
    from server.safety.audit import AuditLog
    from server.safety.gate import SafetyGate
    from server.web.approval_bridge import ApprovalChannel
    from server.web.session import ChatSession, SongTimelineStore
    from server.web.timeline_library import SongTimelineLibrary

    from .test_beat_grid_stage import FIXTURES, GROUPS, _rig
    from .test_safety_gate import FakeConsole as GateConsole

    class _NoModel:
        def complete(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("이 경로는 모델을 부르지 않는다")

    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    store = SongTimelineStore()
    store.latest = {"song_title": "X", "sequence_number": 1}
    session = ChatSession(
        gate=SafetyGate(console=GateConsole(), audit=audit, approval_port=channel),
        provider=_NoModel(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=lambda _e: None,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    session._stage_port = _rig()
    session._rig_paths = {**session._rig_paths, "fixtures": FIXTURES, "groups": GROUPS}
    session._try_rig_capabilities = lambda: rig_read  # type: ignore[method-assign]
    return session


def test_stage_event_carries_pan_tilt_only_when_known(tmp_path) -> None:
    caps = RigCapabilities(
        fixtures={
            201: _cap(201, ("Dimmer", "Pan", "Tilt")),
            202: _cap(202, ("Dimmer", "ColorRGB_R")),
            # 302 는 부분 판독, 301/311 은 판독 자체에 없음
            302: _cap(302, ("Dimmer",), gaps=("일부",)),
        }
    )
    event = _session(tmp_path, DesignRigRead(attempted=True, capabilities=caps)).beat_grid_stage()
    by_fid = {f["fid"]: f for f in event["fixtures"]}
    assert by_fid[201]["pan_tilt"] is True
    assert by_fid[202]["pan_tilt"] is False
    assert "pan_tilt" not in by_fid[302]
    assert "pan_tilt" not in by_fid[301]
    assert "pan_tilt" not in by_fid[311]


def test_stage_event_omits_key_when_capabilities_unread(tmp_path) -> None:
    event = _session(tmp_path, DesignRigRead()).beat_grid_stage()
    assert event["fixtures"]
    assert all("pan_tilt" not in f for f in event["fixtures"])

"""장비 판독 캐시의 수명 — 시간으로 끊지 않는다.

리드 결정(2026-10-19 재측정 뒤): 기종·장비 판독은 서버가 살아 있는 동안 유지한다. 버리는 때는
(1) 앱의 패치 쓰기 epoch 가 바뀔 때, (2) 「장비 다시 읽기」 때뿐이다. 그룹 소속은 무대 칸이 다시
그려질 때도 갱신되므로 기존처럼 짧게 둔다.
"""

from __future__ import annotations

import json

import pytest

from server.design.rig_read_cache import (
    KIND_FIXTURE,
    KIND_MEMBERS,
    KIND_MODE_CAPS,
    KIND_SINGLE,
    KIND_TYPE_MODES,
    LIVE_TTL_SECONDS,
    RigReadCache,
)
from server.safety.gate import _alters_patch
from server.web.messages import PROTOCOL_VERSION, parse_client_message

from .test_apply_rig_round_trips import _apply_rig
from .test_beat_grid_stage_round_trips import TRACKS
from .test_rig_read_cache import _Clock, _rig_and_members, show_scale_types  # noqa: F401
from .test_rig_read_server_scope import _connection_on, _delta

DEVICE_KINDS = (KIND_TYPE_MODES, KIND_MODE_CAPS, KIND_FIXTURE, KIND_SINGLE)


def test_device_layers_are_kept_until_invalidated_not_cut_by_time() -> None:
    clock = _Clock()
    cache = RigReadCache(clock=clock)
    for kind in DEVICE_KINDS:
        cache.put(kind, ("k",), "v")
    clock.now += 10_000_000.0
    for kind in DEVICE_KINDS:
        assert cache.get(kind, ("k",)) == "v", kind


def test_group_membership_still_expires_because_the_stage_redraw_refreshes_it() -> None:
    clock = _Clock()
    cache = RigReadCache(clock=clock)
    cache.put(KIND_MEMBERS, ("g",), "members")
    clock.now += LIVE_TTL_SECONDS + 1
    assert cache.get(KIND_MEMBERS, ("g",)) is None


def test_only_patch_altering_commands_move_the_patch_epoch() -> None:
    assert _alters_patch("Patch Fixture 1 At 1")
    assert _alters_patch("Patch/FixtureTypes/4 Name")
    assert not _alters_patch("Store Sequence 61 Cue 2 /Merge")
    assert not _alters_patch("Set Cue 2 Sequence 61 Property 'TrigType' 'Time'")
    assert not _alters_patch("Set Timecode 5 Property 'Cursor' 19.699")
    assert not _alters_patch("Group 4 ; At Preset 2.101")


@pytest.mark.usefixtures("show_scale_types")
def test_a_patch_write_drops_the_device_layers_on_the_next_apply(tmp_path) -> None:
    port, _ = _apply_rig()
    names = [name for name, _, _ in TRACKS]
    session = _connection_on(tmp_path, port, RigReadCache())
    _rig_and_members(session, names)
    # 앱이 패치를 바꾸는 쓰기를 했다 — 게이트의 패치 epoch 가 올라간다.
    session._gate.patch_write_epoch += 1
    before = dict(port.calls)
    _rig_and_members(session, names)
    reread = {k: v for k, v in _delta(before, port.calls).items() if k.endswith("type-mode")}
    assert reread, "패치가 바뀌었는데 옛 기종 배치로 반영했다"


@pytest.mark.usefixtures("show_scale_types")
def test_refresh_button_rereads_the_device_layers_and_the_next_apply_reads_none(tmp_path) -> None:
    port, _ = _apply_rig()
    names = [name for name, _, _ in TRACKS]
    session = _connection_on(tmp_path, port, RigReadCache())
    _rig_and_members(session, names)
    before_refresh = dict(port.calls)
    session.beat_grid_rig_refresh()
    changed = _delta(before_refresh, port.calls)
    refreshed = {k: v for k, v in changed.items() if k.endswith("type-mode")}
    assert refreshed, "「장비 다시 읽기」가 기종 배치를 다시 읽지 않았다"
    before = dict(port.calls)
    _rig_and_members(session, names)
    reread = {k: v for k, v in _delta(before, port.calls).items() if k.endswith("type-mode")}
    assert reread == {}


def test_the_refresh_message_parses_without_a_payload() -> None:
    raw = json.dumps({"v": PROTOCOL_VERSION, "type": "beat_grid_rig_refresh"})
    assert parse_client_message(raw) == {"v": PROTOCOL_VERSION, "type": "beat_grid_rig_refresh"}

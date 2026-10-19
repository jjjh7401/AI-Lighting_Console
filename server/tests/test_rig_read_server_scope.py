"""리그 판독 캐시의 수명 — 기종·모드 배치는 서버가 살아 있는 동안 한 번만 읽는다.

실기(2026-10-19, lead-preview 감사): 「⇪ 콘솔에 반영」마다 기종 채널 걷기가 다시 나왔다.
원인은 캐시가 연결(``ChatSession``)마다 새로 만들어진 것이다 — 웹소켓 연결이 바뀔 때마다
기종 배치를 처음부터 다시 읽었다. 그리고 계획 단계가 공유 스냅샷을 쓰지 않아 장비 전수 읽기가
한 반영에서 두 번 났다.
"""

from __future__ import annotations

import pytest

from server.design.rig_read_cache import RigReadCache
from server.web.session import SongTimelineStore

from . import test_capability_verdict as verdict
from .test_apply_rig_round_trips import GROUPS, _apply_rig
from .test_beat_grid_send_t563 import _new_session, _timeline
from .test_beat_grid_stage_round_trips import TRACKS
from .test_rig_read_cache import _rig_and_members, show_scale_types  # noqa: F401 (usefixtures)

#: 장비 80대 × 속성 묶음 2개 — 한 반영(계획 + 리그)이 장비를 이 이상 읽으면 전수를 두 번 읽은 것.
FIXTURE_READS_PER_APPLY = 160


def _delta(before: dict, after: dict) -> dict:
    changed = {}
    for key, value in after.items():
        diff = value - before.get(key, 0)
        if diff:
            changed[key] = diff
    return changed


def _wire(session, port):
    session._rig_capability_port = port
    session._stage_port = port
    session._rig_paths = {
        "fixtures": verdict._FIXTURE_ROOT,
        "groups": GROUPS,
        "fixture_types": verdict._TYPES_ROOT,
    }
    return session


def _session_on(tmp_path, port):
    store = SongTimelineStore()
    store.latest = _timeline()
    session, *_ = _new_session(tmp_path, store=store)
    return _wire(session, port)


def _connection_on(tmp_path, port, server_cache: RigReadCache):
    """서버 수명 캐시(``server_cache``)를 받은 연결 하나 — ``ChatSession`` 생성자 인자로 넘긴다."""
    store = SongTimelineStore()
    store.latest = _timeline()
    session, *_ = _new_session(tmp_path, store=store, rig_read_cache=server_cache)
    return _wire(session, port)


@pytest.mark.usefixtures("show_scale_types")
def test_a_later_connection_on_the_same_server_keeps_the_device_layout(tmp_path):
    port, _ = _apply_rig()
    names = [name for name, _, _ in TRACKS]
    server_cache = RigReadCache()
    _rig_and_members(_connection_on(tmp_path / "connection_1", port, server_cache), names)
    before = dict(port.calls)
    _rig_and_members(_connection_on(tmp_path / "connection_2", port, server_cache), names)
    reread_layout = {k: v for k, v in _delta(before, port.calls).items() if k.endswith("type-mode")}
    # 두 번째 연결은 기종·모드 배치(채널 걷기 포함)를 다시 읽지 않는다.
    assert reread_layout == {}


@pytest.mark.usefixtures("show_scale_types")
def test_one_apply_reads_each_fixture_once_across_the_plan_and_the_rig_stage(tmp_path):
    port, _ = _apply_rig()
    session = _session_on(tmp_path, port)
    names = [name for name, _, _ in TRACKS]
    before = dict(port.calls)
    # 「⇪ 콘솔에 반영」 한 번: 계획 단계(프리셋 디머 속성) → 리그 단계(장비 판독 + 그룹 소속).
    session._beat_grid_preset_dimmer_attributes(names)
    _rig_and_members(session, names)
    fixture_reads = sum(v for k, v in _delta(before, port.calls).items() if "fixture" in k)
    assert fixture_reads <= FIXTURE_READS_PER_APPLY

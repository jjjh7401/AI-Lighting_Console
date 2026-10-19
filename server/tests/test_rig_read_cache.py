"""리그 판독 캐시 시험 — 「⇪ 콘솔에 반영」 두 번째부터는 리그·디머 그룹 단계가 거의 읽지 않는다.

실기(LOVE ATTACK) 첫 반영: 리그 단계 상태 읽기 588건·약 40초, 디머 그룹 단계 85건·약 5.7초.
여기서는 가짜 콘솔에 읽기 한 건당 69ms 의 **가상 지연**을 얹어(실제로 자지 않는다) 첫 반영과 두 번째
반영의 읽기 수·가상 시간을 잰다. 실기 접촉 0 — 가짜 콘솔만 쓴다.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid_stage import read_beat_grid_stage
from server.design.fixture_snapshot import FixtureSnapshotPort
from server.design.rig_capability_read import read_design_rig
from server.design.rig_read_cache import (
    LIVE_TTL_SECONDS,
    RigReadCache,
)
from server.web.session import ChatSession, SongTimelineStore

from . import test_capability_verdict as verdict
from .test_apply_rig_round_trips import GROUPS, _apply_rig, _ApplyFake, _CountingPort
from .test_beat_grid_send_t563 import _new_session, _timeline
from .test_beat_grid_stage_round_trips import TRACKS

#: 실기에서 잰 콘솔 읽기 한 건의 평균(ms).
READ_MS = 69.0
EXTRA_TYPES = 14


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class _LatencyPort(_CountingPort):
    """읽기마다 가상 시간을 쌓는다 — 실제로 자지 않는다."""

    def __init__(self, inner) -> None:
        super().__init__(inner)
        self.reads = 0

    def _tick(self) -> None:
        self.reads += 1

    def query_state(self, path, *, offset=0):
        self._tick()
        return super().query_state(path, offset=offset)

    def query_property(self, path, name):
        self._tick()
        return super().query_property(path, name)

    def query_properties(self, path, property_names, *, offset=None):
        self._tick()
        return super().query_properties(path, property_names, offset=offset)

    @property
    def virtual_seconds(self) -> float:
        return self.reads * READ_MS / 1000.0


@pytest.fixture
def show_scale_types(monkeypatch):
    """기종을 늘려 채널 걷기가 지배적인 실기 규모를 흉내 낸다."""
    for n in range(EXTRA_TYPES):
        slot = 100 + n
        monkeypatch.setitem(
            verdict._TYPES, slot, (f"Wide {n}", {1: "Pan", 2: "Tilt", 3: "Zoom", 4: "Dimmer"})
        )
        monkeypatch.setitem(verdict._TYPE_NAMES, slot, f"Wide {n}")


def _session(tmp_path, port):
    store = SongTimelineStore()
    store.latest = _timeline()
    session, *_ = _new_session(tmp_path, store=store)
    assert isinstance(session, ChatSession)
    session._rig_capability_port = port
    session._stage_port = port
    session._rig_paths = {
        "fixtures": verdict._FIXTURE_ROOT,
        "groups": GROUPS,
        "fixture_types": verdict._TYPES_ROOT,
    }
    return session


def _rig_and_members(session, names):
    """``beat_grid_apply`` 의 리그·디머 그룹 두 단계와 같은 호출."""
    snapshot = session._beat_grid_fixture_snapshot()
    rig = read_design_rig(
        snapshot, fixture_types_root=verdict._TYPES_ROOT, cache=session._rig_read_cache
    )
    members = session._beat_grid_group_members(names, port=snapshot)
    return rig, members


def test_second_apply_reads_almost_nothing_and_is_under_two_seconds(tmp_path, show_scale_types):
    port, _ = _apply_rig()
    port = _LatencyPort(port._inner)
    session = _session(tmp_path, port)
    names = [name for name, _, _ in TRACKS]

    first_rig, first_members = _rig_and_members(session, names)
    first_reads = port.reads
    first_seconds = port.virtual_seconds
    port.reads = 0
    second_rig, second_members = _rig_and_members(session, names)

    print(
        f"\n[rig cache] first={first_reads} reads ({first_seconds:.1f}s) "
        f"second={port.reads} reads ({port.virtual_seconds:.2f}s)"
    )
    assert first_reads > 300
    assert first_seconds > 20
    # 같은 답 — 캐시가 결과를 바꾸지 않는다.
    assert second_rig.patch == first_rig.patch
    assert second_rig.gap == first_rig.gap == ""
    # 캐시가 먹었다는 계기 — 둘째 판독은 기종·능력 상위 판독을 하지 않았다.
    assert first_rig.capabilities.round_trips > 0
    assert second_rig.capabilities.round_trips == 0
    assert second_members == first_members
    assert first_rig.whole and first_members
    # 두 번째 반영: 콘솔에 거의 묻지 않는다(그룹 소속·기종·장비 모두 캐시).
    assert port.reads <= 10
    assert port.virtual_seconds < 2.0


def test_second_apply_only_re_lists_the_patch_so_a_changed_patch_is_seen(tmp_path):
    port, _ = _apply_rig()
    session = _session(tmp_path, port)
    names = [name for name, _, _ in TRACKS]
    _rig_and_members(session, names)
    before = dict(port.calls)
    _rig_and_members(session, names)
    extra = {
        k: port.calls[k] - before.get(k, 0) for k in port.calls if port.calls[k] != before.get(k, 0)
    }
    # 기종 목록·장비 목록 같은 목록 읽기만 남는다(패치 구성 변화를 보는 값싼 읽기).
    assert set(extra) <= {"state:type-library", "state:fixture"}
    assert sum(extra.values()) <= 4


def test_invalidate_forces_a_full_reread(tmp_path, show_scale_types):
    port, _ = _apply_rig()
    port = _LatencyPort(port._inner)
    session = _session(tmp_path, port)
    names = [name for name, _, _ in TRACKS]
    _rig_and_members(session, names)
    first_reads = port.reads
    port.reads = 0
    session.invalidate_rig_read_cache()
    rig, _members = _rig_and_members(session, names)
    assert rig.whole
    assert port.reads == first_reads


def test_device_layers_outlive_the_old_ttls_while_group_members_still_expire() -> None:
    clock = _Clock()
    cache = RigReadCache(clock=clock)
    cache.put("mode_caps", ("k",), "static")
    cache.put("fixture", ("p",), "live")
    cache.put("members", ("m",), "members")
    clock.now += LIVE_TTL_SECONDS + 1
    assert cache.get("fixture", ("p",)) == "live"  # 장비 판독은 시간으로 끊지 않는다(리드 결정).
    assert cache.get("mode_caps", ("k",)) == "static"
    assert cache.get("members", ("m",)) is None  # 그룹 소속만 짧게 산다.


def test_a_long_gap_rereads_no_device_layer_only_group_membership(tmp_path, show_scale_types):
    clock = _Clock()
    port, _ = _apply_rig()
    port = _LatencyPort(port._inner)
    session = _session(tmp_path, port)
    session._rig_read_cache = RigReadCache(clock=clock)
    names = [name for name, _, _ in TRACKS]
    _rig_and_members(session, names)
    port.reads = 0
    clock.now += 10_000_000.0  # 시간이 아무리 지나도 장비·기종은 다시 읽지 않는다.
    rig, _ = _rig_and_members(session, names)
    assert rig.whole
    # 남는 것은 목록 읽기와 그룹 소속(짧은 수명)뿐이다. 장비 80대·기종 채널 걷기는 없다.
    assert port.reads < 20


def test_partial_reads_are_never_cached() -> None:
    class _Flaky(_ApplyFake):
        failing = True

        def query_state(self, path, *, offset=0):
            if self.failing and "DMXChannels" in path:
                return {"ok": False}
            return super().query_state(path, offset=offset)

    fixtures = {slot: (11, 100 + slot) for slot in range(1, 5)}
    port = _CountingPort(_Flaky(fixtures, {}))
    cache = RigReadCache()
    snapshot = FixtureSnapshotPort(port, fixture_root=verdict._FIXTURE_ROOT, cache=cache)
    first = read_design_rig(snapshot, fixture_types_root=verdict._TYPES_ROOT, cache=cache)
    assert not first.whole  # 채널을 못 읽었다 — 부분 판독.
    port._inner.failing = False
    second = read_design_rig(snapshot, fixture_types_root=verdict._TYPES_ROOT, cache=cache)
    assert second.whole  # 실패가 굳지 않았다 — 다시 읽어 전수가 됐다.


def test_a_renamed_mode_does_not_hit_the_old_capability_entry() -> None:
    port, _ = _apply_rig()
    cache = RigReadCache()
    read_design_rig(port, fixture_types_root=verdict._TYPES_ROOT, cache=cache)
    keys = [k for k in cache._entries if k[0] == "mode_caps"]
    assert keys, "전수로 읽힌 능력이 저장돼야 한다"
    # 키에 기종·모드 이름이 들어 있다 — 이름이 바뀌면 적중하지 않는다.
    assert all(isinstance(part, str) for key in keys for part in key[1][2:5:2])


def test_stage_redraw_refreshes_the_cached_group_members(tmp_path) -> None:
    port, groups = _apply_rig()
    session = _session(tmp_path, port)
    names = [name for name, _, _ in TRACKS]
    _rig_and_members(session, names)
    # 콘솔에서 그룹 구성이 바뀐 뒤 무대 칸이 다시 그려진다 → 캐시가 새 소속으로 갈린다.
    number, (name, members) = next(iter(groups.items()))
    groups[number] = (name, members[:-1])
    payload = read_beat_grid_stage(
        port, fixtures_path=verdict._FIXTURE_ROOT, groups_path=GROUPS, track_names=names
    )
    fresh = session._group_members_from_payload(payload, names)
    session._rig_read_cache.put("members", session._group_members_key(names), fresh)
    assert session._beat_grid_group_members(names)[name] == fresh[name]
    assert len(fresh[name]) == len(members) - 1

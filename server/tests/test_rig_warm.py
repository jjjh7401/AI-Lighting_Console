"""장비 판독 예열 — 서버를 띄울 때와 곡을 열 때 캐시를 미리 채운다(리드 결정, 2026-10-19)."""

from __future__ import annotations

import threading
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.design.love_attack_timeline import LOVE_ATTACK_ENTRY_ID, love_attack_library_entry
from server.design.rig_read_cache import RigReadCache, wait_while_reading
from server.web import rig_warm
from server.web.rig_warm import warm_device_layers
from server.web.session import SongTimelineStore
from server.web.timeline_api import TimelineLibraryDeps, build_timeline_router
from server.web.timeline_library import SongTimelineLibrary

from . import test_capability_verdict as verdict
from .test_apply_rig_round_trips import GROUPS, _apply_rig
from .test_beat_grid_stage_round_trips import TRACKS
from .test_rig_read_cache import _rig_and_members, show_scale_types  # noqa: F401 (usefixtures)
from .test_rig_read_server_scope import _connection_on, _delta

RIG_PATHS = {
    "fixtures": verdict._FIXTURE_ROOT,
    "groups": GROUPS,
    "fixture_types": verdict._TYPES_ROOT,
}


def _gate(port, epoch: int = 0):
    return types.SimpleNamespace(state_port=port, patch_write_epoch=epoch)


class _BrokenPort:
    def query_state(self, path, *, offset=0):
        raise RuntimeError("console is gone")

    def query_property(self, path, name):
        raise RuntimeError("console is gone")

    def query_properties(self, path, property_names, *, offset=None):
        raise RuntimeError("console is gone")


@pytest.mark.usefixtures("show_scale_types")
def test_warm_fills_the_cache_so_a_later_connection_reads_no_device_layout(tmp_path) -> None:
    port, _ = _apply_rig()
    cache = RigReadCache()
    assert warm_device_layers(_gate(port), rig_paths=RIG_PATHS, cache=cache) is True
    names = [name for name, _, _ in TRACKS]
    session = _connection_on(tmp_path, port, cache)
    before = dict(port.calls)
    _rig_and_members(session, names)
    reread = {k: v for k, v in _delta(before, port.calls).items() if k.endswith("type-mode")}
    assert reread == {}


def test_a_broken_console_returns_false_and_leaves_the_cache_empty() -> None:
    cache = RigReadCache()
    assert warm_device_layers(_gate(_BrokenPort()), rig_paths=RIG_PATHS, cache=cache) is False
    assert len(cache) == 0


def test_no_fixture_path_means_no_warm_and_no_console_read() -> None:
    port, _ = _apply_rig()
    before = dict(port.calls)
    paths = {"fixture_types": verdict._TYPES_ROOT}
    assert warm_device_layers(_gate(port), rig_paths=paths, cache=RigReadCache()) is False
    assert dict(port.calls) == before


def test_a_warm_while_another_runs_returns_at_once() -> None:
    port, _ = _apply_rig()
    rig_warm._WARM_LOCK.acquire()
    try:
        assert warm_device_layers(_gate(port), rig_paths=RIG_PATHS, cache=RigReadCache()) is False
    finally:
        rig_warm._WARM_LOCK.release()


@pytest.mark.usefixtures("show_scale_types")
def test_a_changed_patch_epoch_drops_the_old_layout_before_warming() -> None:
    port, _ = _apply_rig()
    cache = RigReadCache()
    gate = _gate(port)
    assert warm_device_layers(gate, rig_paths=RIG_PATHS, cache=cache) is True
    gate.patch_write_epoch = 1
    before = dict(port.calls)
    assert warm_device_layers(gate, rig_paths=RIG_PATHS, cache=cache) is True
    reread = {k: v for k, v in _delta(before, port.calls).items() if k.endswith("type-mode")}
    assert reread, "패치가 바뀌었는데 예열이 옛 기종 배치를 그대로 믿었다"


def test_loading_a_song_calls_the_open_hook_once() -> None:
    library = SongTimelineLibrary(path=None, seed=(love_attack_library_entry(),))
    store = SongTimelineStore()
    opened: list[str] = []
    app = FastAPI()
    app.include_router(
        build_timeline_router(
            TimelineLibraryDeps(store=store, library=library, on_open=lambda: opened.append("open"))
        )
    )
    response = TestClient(app).post(f"/api/timelines/{LOVE_ATTACK_ENTRY_ID}/load")
    assert response.status_code == 200
    assert opened == ["open"]


def test_the_cue_tick_does_not_wait_when_no_device_read_runs() -> None:
    assert wait_while_reading(RigReadCache(), cap_seconds=5.0) < 0.5


def test_the_cue_tick_waits_for_a_running_device_read_but_no_longer_than_the_cap() -> None:
    cache = RigReadCache()
    with cache.reading():
        waited = wait_while_reading(cache, cap_seconds=0.2)
    assert 0.15 <= waited < 1.0


def test_the_cue_tick_resumes_as_soon_as_the_device_read_ends() -> None:
    cache = RigReadCache()
    started = threading.Event()
    release = threading.Event()

    def device_read() -> None:
        with cache.reading():
            started.set()
            release.wait(timeout=5)

    reader = threading.Thread(target=device_read)
    reader.start()
    started.wait(timeout=5)
    threading.Timer(0.1, release.set).start()
    waited = wait_while_reading(cache, cap_seconds=5.0)
    reader.join(timeout=5)
    assert waited < 2.0

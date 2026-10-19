"""반영 경로의 장비 판독 재사용 — 리드 재측정(2026-10-19, 02:40 UTC) 뒤.

반영 한 번에 `Patch,FixtureType,Mode,Name` 장비 전수 읽기가 세 번 나갔다.
반영 경로의 기종 판독(`_try_rig_capabilities`)이 공유 스냅샷을 거치지
않고 원시 포트로 장비를 읽었기 때문이다. 예열은 콘솔이 아직 응답하지 않으면
한 번 실패하고 조용히 끝났다. 재시도로 막는다.
"""

from __future__ import annotations

import logging
import types

import pytest

from server.design.rig_read_cache import RigReadCache
from server.web.rig_warm import warm_device_layers

from . import test_capability_verdict as verdict
from .test_apply_rig_round_trips import GROUPS, _apply_rig, _CountingPort
from .test_rig_read_cache import show_scale_types  # noqa: F401 (usefixtures)
from .test_rig_read_server_scope import _connection_on, _delta, _session_on

RIG_PATHS = {
    "fixtures": verdict._FIXTURE_ROOT,
    "groups": GROUPS,
    "fixture_types": verdict._TYPES_ROOT,
}


class _Gated:
    """콘솔이 아직 응답하지 않는 상태를 흉내 낸다. ``open()`` 뒤에만 실제 포트로 답한다."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self._open = False

    def open(self) -> None:
        self._open = True

    def _check(self) -> None:
        if not self._open:
            raise RuntimeError("console is not answering yet")

    def query_state(self, path, *, offset=0):
        self._check()
        return self._inner.query_state(path, offset=offset)

    def query_property(self, path, name):
        self._check()
        return self._inner.query_property(path, name)

    def query_properties(self, path, property_names, *, offset=None):
        self._check()
        return self._inner.query_properties(path, property_names, offset=offset)


@pytest.mark.usefixtures("show_scale_types")
def test_repeated_rig_capability_reads_reuse_the_fixture_snapshot(tmp_path) -> None:
    port, _ = _apply_rig()
    session = _session_on(tmp_path, port)
    session._try_rig_capabilities()  # 첫 판독은 장비를 전수로 읽는다.
    before = dict(port.calls)
    session._try_rig_capabilities()
    session._try_rig_capabilities()
    bulk = {
        k: v
        for k, v in _delta(before, port.calls).items()
        if k.startswith(("props:fixture", "prop:fixture"))
    }
    assert bulk == {}, "반영 안에서 두 번째 판독부터 장비 전수 읽기가 다시 나갔다"


@pytest.mark.usefixtures("show_scale_types")
def test_a_warm_retries_until_the_console_answers() -> None:
    from server.web.rig_warm import warm_until_answered

    port, _ = _apply_rig()
    gated = _Gated(port)
    gate = types.SimpleNamespace(state_port=gated, patch_write_epoch=0)
    waits: list[float] = []

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        gated.open()  # 기다리는 사이 콘솔이 응답하기 시작한다.

    cache = RigReadCache()
    assert (
        warm_until_answered(gate, rig_paths=RIG_PATHS, cache=cache, delays=(0.0, 1.0), sleep=sleep)
        is True
    )
    assert waits == [1.0], "첫 시도가 실패한 뒤 한 번 기다리고 다시 시도해야 한다"
    assert len(cache) > 0


class _Silent(_CountingPort):
    """일부 장비가 답을 주지 않는다(``{"ok": False}``). 실기에서 장비 71대가 이랬다(리드 로그)."""

    def __init__(self, inner, slots) -> None:
        super().__init__(inner)
        self._slots = set(slots)

    def _silent(self, path: str) -> bool:
        tail = path.rsplit("/", 1)[-1]
        prefix = verdict._FIXTURE_ROOT + "/"
        return path.startswith(prefix) and tail.isdigit() and int(tail) in self._slots

    def query_property(self, path, name):
        reply = super().query_property(path, name)
        return {"ok": False} if self._silent(path) else reply

    def query_properties(self, path, property_names, *, offset=None):
        reply = super().query_properties(path, property_names, offset=offset)
        return {"ok": False} if self._silent(path) else reply


@pytest.mark.usefixtures("show_scale_types")
def test_a_silent_fixture_is_not_asked_again_on_the_next_apply(tmp_path) -> None:
    port, _ = _apply_rig()
    silent = _Silent(port._inner, slots={3, 7})
    session = _session_on(tmp_path, silent)
    session._try_rig_capabilities()
    before = dict(silent.calls)
    session._try_rig_capabilities()
    asked_again = {
        k: v
        for k, v in _delta(before, silent.calls).items()
        if k.startswith(("props:fixture", "prop:fixture"))
    }
    assert asked_again == {}, "답을 주지 않은 장비를 다음 반영이 다시 물었다"


@pytest.mark.usefixtures("show_scale_types")
def test_the_warm_succeeds_when_every_fixture_has_answered_even_if_some_stay_silent() -> None:
    port, _ = _apply_rig()
    silent = _Silent(port._inner, slots={3, 7})
    gate = types.SimpleNamespace(state_port=silent, patch_write_epoch=0)
    assert warm_device_layers(gate, rig_paths=RIG_PATHS, cache=RigReadCache()) is True


@pytest.mark.usefixtures("show_scale_types")
def test_the_warm_log_names_how_many_fixtures_stayed_silent(caplog) -> None:
    port, _ = _apply_rig()
    silent = _Silent(port._inner, slots={3, 7})
    gate = types.SimpleNamespace(state_port=silent, patch_write_epoch=0)
    with caplog.at_level(logging.WARNING, logger="server.web.rig_warm"):
        warm_device_layers(gate, rig_paths=RIG_PATHS, cache=RigReadCache())
    assert "답 없음 2대" in caplog.text


@pytest.mark.usefixtures("show_scale_types")
def test_a_later_connection_does_not_ask_the_silent_fixtures_again(tmp_path) -> None:
    port, _ = _apply_rig()
    silent = _Silent(port._inner, slots={3, 7})
    server_cache = RigReadCache()
    _connection_on(tmp_path / "connection_1", silent, server_cache)._try_rig_capabilities()
    before = dict(silent.calls)
    _connection_on(tmp_path / "connection_2", silent, server_cache)._try_rig_capabilities()
    asked_again = {
        k: v
        for k, v in _delta(before, silent.calls).items()
        if k.startswith(("props:fixture", "prop:fixture"))
    }
    assert asked_again == {}, "서버가 기억한 「답 없음」을 다음 연결이 다시 물었다"

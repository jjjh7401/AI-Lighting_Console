"""반영 두 번째부터 장비 판독 0 — 실기 원인(잘린 루트 목록의 슬롯 훑기)을 재현하는 시험.

실기 로그(2026-10-19): 반영 한 번에 rig 71·bundle 71 콘솔 읽기. 루트 목록이 childCount 보다
적게 돌아와 리그 판독이 1..childCount 슬롯을 하나씩 물었고(``query_state``), 그 목록 읽기는
기억하지 않아 두 번째 반영도 다시 물었다. 가짜 콘솔은 루트를 온전히 주어서 이 경로가 빠져 있었다.
셈은 반영 계측(``apply.timing`` 의 ``console_reads``)과 같은 방식(``counted_read``)으로 한다.
"""

from __future__ import annotations

import logging
import types

import pytest

from server.design.rig_capability_read import read_design_rig
from server.design.rig_read_cache import RigReadCache
from server.observability.console_tally import counted_read
from server.web.apply_timing import ApplyClock, apply_stage
from server.web.rig_warm import warm_device_layers
from server.web.session import _FIXTURE_TYPES_ROOT

from . import test_capability_verdict as verdict
from .test_apply_rig_round_trips import _apply_rig
from .test_rig_read_cache import show_scale_types  # noqa: F401 (usefixtures)
from .test_rig_read_server_scope import _connection_on, _session_on

RIG_PATHS = {"fixtures": verdict._FIXTURE_ROOT, "fixture_types": _FIXTURE_TYPES_ROOT}


class _TruncatedRoot:
    """루트 목록을 잘라 답하는 콘솔 포트 — 실기처럼 childCount 가 목록보다 크다.

    읽기 메서드는 게이트의 상태 포트와 같이 ``counted_read`` 로 센다.
    """

    def __init__(self, inner, *, keep: int = 2) -> None:
        self._inner = inner
        self._keep = keep

    @counted_read
    def query_state(self, path: str, *, offset: int = 0) -> dict:
        if path == verdict._FIXTURE_ROOT:
            children = list(self._inner.query_state(path).get("children") or [])
            return {
                "ok": True,
                "node": {"childCount": len(children)},
                "children": children[: self._keep],
            }
        try:
            if offset:
                return self._inner.query_state(path, offset=offset)
            return self._inner.query_state(path)
        except Exception:  # noqa: BLE001 — 없는 슬롯은 콘솔이 「없음」으로 답하는 것과 같다
            return {"ok": False}

    @counted_read
    def query_property(self, path: str, property_name: str) -> dict:
        return self._inner.query_property(path, property_name)

    @counted_read
    def query_properties(self, path: str, property_names, *, offset=None) -> dict:
        if offset:
            return self._inner.query_properties(path, property_names, offset=offset)
        return self._inner.query_properties(path, property_names)


class _Lines(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def _apply(session) -> dict[str, int]:
    """반영 한 번 — 리그·기종 단계를 실제 코드 경로로 타고 단계별 콘솔 읽기 수를 돌려준다."""
    lines = _Lines()
    log = logging.getLogger("server.web.apply_timing")
    log.addHandler(lines)
    clock = ApplyClock()
    clock.start()
    try:
        snapshot = session._beat_grid_fixture_snapshot()
        with session._rig_read_cache.reading():
            read_design_rig(
                snapshot, fixture_types_root=_FIXTURE_TYPES_ROOT, cache=session._rig_read_cache
            )
        apply_stage("rig")
        session._try_rig_capabilities()
        apply_stage("bundle")
    finally:
        clock.finish()
        log.removeHandler(lines)
    reads: dict[str, int] = {}
    for line in lines.lines:
        for stage in ("rig", "bundle"):
            if f"apply.timing stage={stage} " in line:
                reads[stage] = int(line.split("console_reads=")[1].split()[0])
    return reads


@pytest.mark.usefixtures("show_scale_types")
def test_the_second_apply_reads_no_device_state_when_the_root_listing_is_truncated(
    tmp_path,
) -> None:
    port, _ = _apply_rig()
    session = _session_on(tmp_path, _TruncatedRoot(port))
    first = _apply(session)
    assert first["rig"] > 0, (
        "첫 반영은 잘린 루트를 슬롯마다 물어야 한다 — 시험이 그 경로를 탔는지 본다"
    )
    assert _apply(session) == {"rig": 0, "bundle": 0}


@pytest.mark.usefixtures("show_scale_types")
def test_a_warm_at_start_makes_the_first_apply_read_no_device_state(tmp_path) -> None:
    port, _ = _apply_rig()
    wrapped = _TruncatedRoot(port)
    cache = RigReadCache()
    gate = types.SimpleNamespace(state_port=wrapped, patch_write_epoch=0)
    assert warm_device_layers(gate, rig_paths=RIG_PATHS, cache=cache) is True
    session = _connection_on(tmp_path, wrapped, cache)
    assert _apply(session) == {"rig": 0, "bundle": 0}

"""Rig-readiness checks: sequences/executors and preset (look) library integrity.

The two console-state checks reuse the same read-only state-query contract the
orchestrator and ``server.prechk`` already depend on
(``server.orchestrator.ports.StateQueryPort`` — any object with a
``query_state(path) -> dict`` method satisfies it structurally; no import of
that module is required here). This module never imports ``server.bridge``,
so it needs no exemption from the REQ-MVP-029 single-chokepoint architecture
test (``server/tests/test_architecture.py``).
"""

from __future__ import annotations

from typing import Protocol

from server.preshow.models import CheckResult

DEFAULT_SEQUENCES_PATH = "DataPool/Sequences"
DEFAULT_PRESET_POOLS_PATH = "DataPool/PresetPools"


class StateQueryPort(Protocol):
    """Structural twin of ``server.orchestrator.ports.StateQueryPort``."""

    def query_state(self, path: str) -> dict: ...


def _child_count(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    node = payload.get("node")
    if not isinstance(node, dict):
        return None
    count = node.get("childCount")
    if not isinstance(count, int) or isinstance(count, bool):
        return None
    return count


def _check_children_exist(
    state_port: StateQueryPort, *, name: str, path: str, empty_label: str
) -> CheckResult:
    try:
        payload = state_port.query_state(path)
    except Exception as error:  # noqa: BLE001 — any port failure degrades to skip, never fail
        return CheckResult(
            name=name,
            status="skip",
            detail=f"콘솔 미연결 또는 조회 실패 — {path} 확인을 건너뜀: {error}",
        )
    count = _child_count(payload)
    if count is None:
        return CheckResult(
            name=name,
            status="fail",
            detail=f"{path} 조회 결과를 판독하지 못했다 (childCount 없음).",
            data=payload if isinstance(payload, dict) else None,
        )
    if count == 0:
        return CheckResult(
            name=name,
            status="fail",
            detail=f"{path}에 {empty_label}가 없다.",
            data={"path": path, "child_count": count},
        )
    return CheckResult(
        name=name,
        status="pass",
        detail=f"{path}에 {empty_label} {count}개 확인.",
        data={"path": path, "child_count": count},
    )


def check_sequences_exist(state_port: StateQueryPort, *, path: str = DEFAULT_SEQUENCES_PATH) -> CheckResult:
    """At least one sequence/executor target exists under ``path``."""
    return _check_children_exist(
        state_port, name="sequences_exist", path=path, empty_label="시퀀스"
    )


def check_preset_pools_exist(
    state_port: StateQueryPort, *, path: str = DEFAULT_PRESET_POOLS_PATH
) -> CheckResult:
    """At least one preset pool exists under ``path`` (console-side half of preset integrity)."""
    return _check_children_exist(
        state_port, name="preset_pools_exist", path=path, empty_label="프리셋 풀"
    )


def check_preset_library_integrity(loader=None) -> CheckResult:
    """The on-disk look/preset library loads without a schema error.

    Uses :func:`server.looks.loader.load_library_from_dir` by default. Needs
    no console connection, so — unlike the two checks above — this never
    reports ``skip`` for "console unreachable"; a broken library file is
    always catchable before showtime.
    """
    from server.looks.loader import LookSchemaError, load_library_from_dir

    load = loader or load_library_from_dir
    try:
        library = load()
    except LookSchemaError as error:
        return CheckResult(
            name="preset_library_integrity",
            status="fail",
            detail=f"프리셋(룩) 라이브러리 스키마 오류: {error}",
        )
    count = len(library.looks)
    return CheckResult(
        name="preset_library_integrity",
        status="pass",
        detail=f"프리셋(룩) 라이브러리 {count}건 무결성 확인.",
        data={"count": count},
    )

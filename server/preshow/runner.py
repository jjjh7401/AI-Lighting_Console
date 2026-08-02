"""The pre-show checklist runner — composes every check into one report.

Every input is optional. Omitting ``osc_config`` or ``state_port`` does not
abort the run; the checks that need it report ``skip`` (see
``server/preshow/models.py`` — the whole point of the three-status design is
that a missing console never masquerades as a passing one).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from server.preshow.checks import (
    DEFAULT_PRESET_POOLS_PATH,
    DEFAULT_SEQUENCES_PATH,
    StateQueryPort,
    check_preset_library_integrity,
    check_preset_pools_exist,
    check_sequences_exist,
)
from server.preshow.models import CheckResult, PreshowReport
from server.preshow.osc_check import (
    DEFAULT_STATE_PATH,
    check_osc_roundtrip,
    check_receive_port_binding,
)
from server.preshow.pitfalls import (
    check_feedback_port_drift,
    check_osc_slot_send_row,
    check_stale_socket_advisory,
)

DEFAULT_OSC_SLOT = 1


class BridgeConfigLike(Protocol):
    """Structural twin of ``server.bridge.osc.BridgeConfig``.

    This module must not import ``server.bridge`` itself (REQ-MVP-029
    single-chokepoint — ``server/tests/test_architecture.py`` does not exempt
    this file, only ``server/preshow/osc_check.py``, which carries the one
    runtime bridge import this package needs). A real ``BridgeConfig``
    satisfies this protocol structurally, so callers pass one unchanged.
    """

    receive_port: int


def _skip(name: str, reason: str) -> CheckResult:
    return CheckResult(name=name, status="skip", detail=reason)


def run_preshow_checklist(
    *,
    osc_config: BridgeConfigLike | None = None,
    state_port: StateQueryPort | None = None,
    osc_wait: float = 3.0,
    osc_state_path: str = DEFAULT_STATE_PATH,
    sequences_path: str = DEFAULT_SEQUENCES_PATH,
    preset_pools_path: str = DEFAULT_PRESET_POOLS_PATH,
    library_loader=None,
    configured_osc_slot: int = DEFAULT_OSC_SLOT,
    live_osc_rows: Mapping[int, Mapping[str, object]] | None = None,
    configured_feedback_port: int | None = None,
) -> PreshowReport:
    """Run every pre-show check and return one traffic-light report.

    ``configured_feedback_port`` defaults to ``osc_config.receive_port`` when
    ``osc_config`` is given, otherwise the feedback-port-drift check reports
    ``skip`` — there is nothing configured to drift from.
    """
    checks: list[CheckResult] = []

    # ① OSC round trip (ping/state) + receive-port binding.
    if osc_config is not None:
        osc_roundtrip = check_osc_roundtrip(osc_config, wait=osc_wait, path=osc_state_path)
        receive_port_binding = check_receive_port_binding(osc_config)
    else:
        osc_roundtrip = _skip("osc_roundtrip", "osc_config가 주어지지 않아 OSC 왕복 확인을 건너뜀.")
        receive_port_binding = _skip(
            "receive_port_binding", "osc_config가 주어지지 않아 수신 포트 확인을 건너뜀."
        )
    checks.append(osc_roundtrip)
    checks.append(receive_port_binding)

    # ② sequences/executors exist.
    if state_port is not None:
        checks.append(check_sequences_exist(state_port, path=sequences_path))
    else:
        checks.append(_skip("sequences_exist", "state_port가 주어지지 않아 시퀀스 확인을 건너뜀."))

    # ③ preset integrity: console-side pool presence + local library schema.
    if state_port is not None:
        checks.append(check_preset_pools_exist(state_port, path=preset_pools_path))
    else:
        checks.append(
            _skip("preset_pools_exist", "state_port가 주어지지 않아 프리셋 풀 확인을 건너뜀.")
        )
    checks.append(check_preset_library_integrity(library_loader))

    # ④ known pitfalls.
    checks.append(check_stale_socket_advisory(osc_roundtrip))
    checks.append(check_osc_slot_send_row(configured_osc_slot, live_osc_rows))
    feedback_port = configured_feedback_port
    if feedback_port is None and osc_config is not None:
        feedback_port = osc_config.receive_port
    observed_port = None
    if receive_port_binding.data is not None:
        observed_port = receive_port_binding.data.get("actual")
    if feedback_port is not None:
        checks.append(check_feedback_port_drift(feedback_port, observed_port))
    else:
        checks.append(
            _skip(
                "feedback_port_drift",
                "설정된 응답 포트가 없어(osc_config·configured_feedback_port 모두 미지정) "
                "드리프트 확인을 건너뜀.",
            )
        )

    return PreshowReport(checks=tuple(checks))

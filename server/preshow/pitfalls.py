"""Known-pitfall diagnostics — the project's field-observed failure modes.

Three items, drawn from operational memory (``console/lua/README.md`` §
Deployment Reliability and this project's own incident notes):

1. a stale OSC socket that answers nothing until onPC's OSC Enable Input /
   Output is cycled off and on;
2. an ``osc_slot`` settings row that is not the ``Send = Yes`` row, so
   replies never leave the console;
3. a console feedback/response port that drifted from the configured value.

None of these require a live console BY THEMSELVES — each degrades to
``skip`` when the evidence it needs was not supplied, per
``.claude/rules/moai/core/verification-claim-integrity.md`` §1 (no
unobserved-claim, in either direction): a pitfall this module cannot actually
inspect is reported as unverified, never as a silent pass.
"""

from __future__ import annotations

from collections.abc import Mapping

from server.preshow.models import CheckResult

STALE_SOCKET_ADVICE = (
    "onPC에서 OSC Enable Input/Output을 껐다 다시 켜는 사이클을 시도하라 — "
    "화면상 설정이 이미 켜진 것처럼 보여도 소켓이 스테일 상태일 수 있다."
)


def check_stale_socket_advisory(osc_roundtrip: CheckResult) -> CheckResult:
    """Surface the stale-socket recovery step when the live round trip did not pass.

    Derived from :func:`server.preshow.osc_check.check_osc_roundtrip`'s own
    outcome rather than re-probing the console — a second probe would just
    hit the same stale socket.
    """
    if osc_roundtrip.status == "pass":
        return CheckResult(
            name="stale_socket_advisory",
            status="pass",
            detail="OSC 왕복이 정상 응답했다 — 스테일 소켓 징후 없음.",
        )
    return CheckResult(
        name="stale_socket_advisory",
        status="skip",
        detail=f"OSC 왕복이 통과하지 못했다({osc_roundtrip.status}). {STALE_SOCKET_ADVICE}",
        data={"osc_roundtrip_status": osc_roundtrip.status},
    )


def check_osc_slot_send_row(
    configured_slot: int,
    live_rows: Mapping[int, Mapping[str, object]] | None,
    *,
    slot_is_configured: bool = True,
) -> CheckResult:
    """Confirm the console's OSC settings row for ``configured_slot`` has Send = Yes.

    ``live_rows`` maps OSC settings row index -> ``{"send": bool, ...}``, as
    read from the console. No responder verb reads this today, so callers
    typically pass ``None`` and the check reports ``skip`` with the manual
    verification step instead of a false pass.

    ``slot_is_configured`` (SPEC-COPILOT-PRESHOW-001 T-G3) marks whether
    ``configured_slot`` was actually resolved from the site's real settings,
    or is only a hardcoded fallback because the setting could not be read.
    This project has already suffered TWO incidents from an ``osc_slot`` row
    that was not the ``Send = Yes`` row — a checklist that names an
    unconfirmed fallback as if it were the confirmed site value sends the
    operator to check the wrong row and past the real culprit, which is worse
    than no guidance at all. When ``False``, every detail message discloses
    the fallback explicitly (never presents an unobserved value as observed —
    ``.claude/rules/moai/core/verification-claim-integrity.md`` §1).
    """
    disclosure = (
        ""
        if slot_is_configured
        else (
            f"osc_slot 설정값을 확인할 수 없어 기본값 {configured_slot}을 기준으로 안내한다 — "
            "실제 osc_slot 값을 먼저 확인하라. "
        )
    )
    slot_qualifier = "설정된" if slot_is_configured else "(미확인) 기본값"
    extra_data: dict[str, object] = {} if slot_is_configured else {"slot_is_configured": False}

    if live_rows is None:
        return CheckResult(
            name="osc_slot_send_row",
            status="skip",
            detail=(
                f"{disclosure}{slot_qualifier} osc_slot={configured_slot}의 Send=Yes 여부를 "
                "자동 조회할 경로가 없다 — onPC Settings > OSC 화면에서 해당 행이 Send=Yes인지 "
                "직접 확인하라."
            ),
            data={"configured_slot": configured_slot, **extra_data},
        )
    row = live_rows.get(configured_slot)
    if row is None:
        return CheckResult(
            name="osc_slot_send_row",
            status="fail",
            detail=f"{disclosure}osc_slot={configured_slot} 행을 콘솔 OSC 설정에서 찾지 못했다.",
            data={"configured_slot": configured_slot, **extra_data},
        )
    if not row.get("send"):
        return CheckResult(
            name="osc_slot_send_row",
            status="fail",
            detail=(
                f"{disclosure}osc_slot={configured_slot} 행이 Send=Yes가 아니다 — 응답 미수신의 "
                "원인일 수 있다."
            ),
            data={"configured_slot": configured_slot, "row": dict(row), **extra_data},
        )
    return CheckResult(
        name="osc_slot_send_row",
        status="pass",
        detail=f"{disclosure}osc_slot={configured_slot} 행이 Send=Yes로 확인됨.",
        data={"configured_slot": configured_slot, "row": dict(row), **extra_data},
    )


def check_feedback_port_drift(configured_port: int, observed_port: int | None) -> CheckResult:
    """Compare the configured feedback/response port against an observed one.

    ``observed_port`` is whatever the caller actually measured (e.g. the
    bound receive port of a live :class:`server.bridge.osc.OscBridge`).
    ``None`` when nothing was observed reports ``skip`` rather than a silent
    pass — mirrors the field incident where the console's OSC output row
    quietly targeted a different port than the one configured on this side.
    """
    if observed_port is None:
        return CheckResult(
            name="feedback_port_drift",
            status="skip",
            detail=(
                f"응답 포트 드리프트를 확인할 관측값이 없다 — 설정값은 {configured_port}. "
                "onPC OSC 출력 행의 대상 포트가 설정값과 같은지 직접 확인하라."
            ),
            data={"configured_port": configured_port},
        )
    if observed_port != configured_port:
        return CheckResult(
            name="feedback_port_drift",
            status="fail",
            detail=f"응답 포트 드리프트 — 설정값 {configured_port} != 실측값 {observed_port}.",
            data={"configured_port": configured_port, "observed_port": observed_port},
        )
    return CheckResult(
        name="feedback_port_drift",
        status="pass",
        detail=f"응답 포트 {observed_port} 일치 확인.",
        data={"configured_port": configured_port, "observed_port": observed_port},
    )

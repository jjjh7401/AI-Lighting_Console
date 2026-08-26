"""t100 — 컬러+디머 복합 프리셋을 `/Universal` 로 저장할 수 있는가 (설계 §4.1).

**검증 도구다 — 제품 코드가 아니다.** `lxseq_presets_e2e.py` 의 형태를 승계한다:
실포트 조립(`build_console_stack` + `build_toolset`), 우회 배선 0, `--approve` 없으면
콘솔에 아무것도 닿지 않는다.

## 무엇을 재는가

판정이 두 곳에서 충돌한다. `fx/instantiate.py:694` 는 `Store Preset <pool>.<n>
'<label>' /Universal` 을 live-verified 로 적었고, `web/session.py:1934` 는 같은
플래그를 「미검증 문법」(REQ-COLORPRESET-008)이라 적었다. **둘 다 참일 수 있다** —
FX 쪽은 페이저를 담은 프리셋이고, 이 카드가 묻는 것은 **컬러+디머를 담은** 프리셋이다.
같은 문법이지만 같은 대상이 아니므로 FX 근거를 빌려오지 않는다.

## 되읽기 한계 — 미리 적는다

**슬롯 점유만 읽힌다.** 「그 프리셋이 정말 Universal 인가」는 이 채널로 못 읽는다.
이 실측이 답하는 것은 **「이 명령이 거절되지 않는가」까지**다. 그 이상을 결론에
적지 마라.

## 안 하는 것

- **풀 번호를 지어내지 않는다.** `--pool` 은 필수이고, `--action probe` 가
  `DataPool/PresetPools` 를 열거해 그 번호를 **재게** 해 준다. 틀린 풀에 쓰면
  점유 슬롯을 덮어쓰고, 프리셋 값은 되읽을 수 없어 복구도 못 한다.
- **바이트를 판정 근거로 쓰지 않는다**(t72: 2044B 거절 · 2080B 통과). 기록만 한다.
- **한 건만 쏜다.** 번들 하나, 프리셋 하나.
"""

from __future__ import annotations

import argparse
import json
import sys

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.presets.store import preset_store_commands
from server.preshow.checks import DEFAULT_PRESET_POOLS_PATH
from server.safety.bootstrap import build_console_stack
from server.spatial.pointing import SpatialPointingError

# 사본을 늘리지 않는다 — 대조군 경로도 상태 판독 헬퍼도 형제 하네스가 이미 가졌다.
from server.tools.lxseq_presets_e2e import (
    FABRICATED_PATH,
    FIXTURES_PATH,
    GROUPS_PATH,
    _RecordingApproval,
    _RefusingQuestions,
    _state,
)
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

_PCT_RANGE = (0, 100)


def _checked_pct(value: float, what: str) -> float:
    low, high = _PCT_RANGE
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpatialPointingError(f"{what} {value!r} must be a number")
    if not low <= value <= high:
        raise SpatialPointingError(f"{what} {value!r} is outside {low}..{high}")
    return value


def composite_bundle(
    *,
    group: int,
    dimmer_pct: float,
    rgb: tuple[int, int, int],
    pool_no: int,
    preset_no: int,
    label: str,
) -> tuple[str, ...]:
    """컬러+디머를 프로그래머에 싣고 `/Universal` 로 저장하는 **한 번들**.

    `Store` 문형은 `presets/store.py` 에서 받는다 — 이 프로브가 보태는 것은
    `/Universal` **토큰 하나**뿐이다. 그것이 이 카드가 재는 대상이고, 그 이상을
    손으로 적으면 무엇을 쟀는지 흐려진다(설계 §1.2 사본 증식 금지).

    값 문형은 라이브 실측된 두 자리를 따른다 — 디머는 `session.py:920` 의
    `Group <n> ; Attribute 'Dimmer' At <pct>`, 컬러는
    `_color_phaser_step_commands` 의 3채널 한 줄 연결(한 스텝의 색이 채널별로
    어긋나지 않게 한다).
    """
    if isinstance(group, bool) or not isinstance(group, int) or group <= 0:
        raise SpatialPointingError(f"group number {group!r} must be a positive integer")
    _checked_pct(dimmer_pct, "dimmer percent")
    if len(rgb) != 3:
        raise SpatialPointingError(f"rgb {rgb!r} must carry three channels")
    red, green, blue = (_checked_pct(v, "colour channel") for v in rgb)

    store_line, label_line = preset_store_commands(pool_no, preset_no, label)
    return (
        f"Group {group} ; Attribute 'Dimmer' At {dimmer_pct:g}",
        f"Attribute 'ColorRGB_R' At {red:g} ; Attribute 'ColorRGB_G' At {green:g} ; "
        f"Attribute 'ColorRGB_B' At {blue:g}",
        store_line + " /Universal",
        label_line,
        "ClearAll",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--action", choices=["probe", "apply"], default="probe")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument("--pool", type=int, default=None, help="복합(All) 풀 번호 — 재서 넣는다")
    parser.add_argument("--preset-no", type=int, default=None, help="비어 있는 슬롯 번호")
    parser.add_argument("--group", type=int, default=None, help="값을 실을 그룹 번호")
    parser.add_argument("--label", default=None)
    parser.add_argument("--dimmer-pct", type=float, default=85.0)
    parser.add_argument("--rgb", default="100,55,5", help="0-100 세 채널, 쉼표 구분")
    parser.add_argument("--approve", action="store_true", help="없으면 콘솔에 아무것도 닿지 않는다")
    parser.add_argument("--out", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    # [HARD] `--approve` 는 **행위**를 막는다. 승인 통로의 대답만 정하면 아무것도
    # 안 막는다 — 2026-08-25 사고가 정확히 그것이었다. 콘솔 스택을 세우기 **전에**
    # 거부한다. 안전장치가 도는지의 확인은 실기가 아니라 검사가 한다
    # (`server/tests/test_t100_universal_composite.py`).
    if args.action == "apply":
        if not args.approve:
            parser.error(
                "--action apply 는 --approve 를 요구한다. 승인 없이는 콘솔에 닿지 않는다.\n"
                "안전장치가 도는지 확인하려고 apply 를 쏘지 마라 — 확인과 사고가 "
                "같은 행위이면 그 절차가 사고다."
            )
        missing = [
            name
            for name, value in (
                ("--pool", args.pool),
                ("--preset-no", args.preset_no),
                ("--group", args.group),
                ("--label", args.label),
            )
            if value is None
        ]
        if missing:
            parser.error(
                "apply 에는 " + ", ".join(missing) + " 가 필요하다. "
                "지어내지 않는다 — 풀 번호는 --action probe 로 먼저 재라."
            )

    rgb = tuple(int(part) for part in str(args.rgb).split(","))
    out: dict[str, object] = dict(
        action=args.action,
        approve=args.approve,
        listen_port=args.listen_port,
        pool=args.pool,
        preset_no=args.preset_no,
        group=args.group,
        label=args.label,
        dimmer_pct=args.dimmer_pct,
        rgb=list(rgb),
        readback_limit="슬롯 점유만 읽힌다 — Universal 여부는 이 채널로 못 읽는다",
    )

    approval = _RecordingApproval(approve=args.approve)
    questions = _RefusingQuestions()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=approval,
    )

    exit_code = 0
    try:
        out["preflight"] = preflight(
            stack.gate,
            receive_host="127.0.0.1",
            receive_port=args.listen_port,
            console_port=args.port,
        )
        fabricated = _state(stack.gate.state_port, FABRICATED_PATH)
        fixtures = _state(stack.gate.state_port, FIXTURES_PATH)
        groups = _state(stack.gate.state_port, GROUPS_PATH)
        pools = _state(stack.gate.state_port, DEFAULT_PRESET_POOLS_PATH)
        trustworthy = (not fabricated["ok"]) and fixtures["ok"] and groups["ok"]
        out["baseline"] = dict(
            fabricated_control=fabricated,
            fixtures=fixtures,
            groups=groups,
            preset_pools=pools,
            channel_trustworthy=trustworthy,
        )
        if args.pool is not None:
            out["pool_before"] = _state(
                stack.gate.state_port, DEFAULT_PRESET_POOLS_PATH + "/" + str(args.pool)
            )
        if not trustworthy:
            # 날조 경로가 통과했거나 실경로가 안 읽혔다 — 어느 쪽이든 이 하네스의
            # 관측이 증거가 아니게 되므로 멈춘다.
            out["stopped"] = "channel_untrustworthy"
            exit_code = 2
        elif args.action == "probe":
            out["stopped"] = "probe_only"
        else:
            commands = composite_bundle(
                group=args.group,
                dimmer_pct=args.dimmer_pct,
                rgb=rgb,
                pool_no=args.pool,
                preset_no=args.preset_no,
                label=args.label,
            )
            out["commands"] = list(commands)
            # t72 — 기록이지 판정 근거가 아니다. 콘솔 거절은 길이가 아니라 내용에 달렸다.
            out["longest_command_bytes"] = max(len(c.encode("utf-8")) for c in commands)
            registry = build_toolset(
                execution_port=stack.gate.execution_port,
                state_port=stack.gate.state_port,
                property_port=stack.gate.state_port,
                bundle_gate=stack.gate,
                question_port=questions,
                group_approval_port=approval,
            )
            execution = registry.dispatch(
                ToolCall(id="t100", name="run_commands", arguments=dict(commands=list(commands)))
            )
            out["tool"] = json.loads(execution.result.content)
            out["outcomes"] = [
                dict(command=o.command, status=o.status, detail=o.detail)
                for o in execution.command_outcomes
            ]
            # 툴 응답을 생성 증거로 쓰지 않는다 — 명령이 성공한 것과 대상이 바뀐
            # 것은 다르다. 풀을 **독립적으로** 되읽는다. 별도 프로세스 재조회는
            # `t95_state_dump --path DataPool/PresetPools/<pool>` 로 따로 돈다.
            out["pool_after"] = _state(
                stack.gate.state_port, DEFAULT_PRESET_POOLS_PATH + "/" + str(args.pool)
            )
            out["fabricated_control_after"] = _state(stack.gate.state_port, FABRICATED_PATH)
            out["fixtures_after"] = _state(stack.gate.state_port, FIXTURES_PATH)
            out["groups_after"] = _state(stack.gate.state_port, GROUPS_PATH)
        out["approval_requests"] = [list(bundle) for bundle in approval.asked]
        out["questions_asked"] = questions.asked
    finally:
        stack.stop()

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out is not None:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

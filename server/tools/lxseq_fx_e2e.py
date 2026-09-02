"""LX-SEQ FX 라이브 하네스 (4단계 보조 -- 큐가 참조하는 FX 프리셋을 만든다).

검증 도구다 -- 제품 코드가 아니다. server/tools/lxseq_presets_e2e.py 의
형태를 승계한다: 실포트 조립(build_console_stack + build_toolset), 우회
배선 0, --approve 없으면 콘솔에 아무것도 닿지 않는다.

## 왜 compose_fx 인가 (find_fx 가 아니다)

find_fx 는 저장소 내장 큐레이션 라이브러리를 퍼지 텍스트로 검색한다 --
fx.csv 의 영문 코드형 이름(DIM-CHASE 등)과 그 라이브러리의 한글 표시
이름은 어휘 체계 자체가 다르다(t209 실측: 8종 중 확정 매칭 1건뿐). fx.csv
에는 레시피(Attribute/WaveSteps/BaseRate/Width/Phase)가 이미 있으므로
찾지 않고 그 레시피로 직접 만든다 -- compose_fx 가 그 문이다
(server/orchestrator/tools.py:6292, "the only model-reachable entry that
builds a phaser the LIBRARY does not hold").
## 번역 규칙 (리드 판정, 2026-08-31)

- 접두사(Attribute 열)가 속성, WaveSteps/BaseRate/Width/Phase 가 나머지 축.
- 속성이 KNOWN_ATTRIBUTES 밖이면 건너뛴다 -- FX.04/FX.06.
  조용히 빠뜨리지 않는다: skipped 목록에 사유와 함께 남는다.
- 패턴은 ID별로 리드가 못 박았다(아래 _PATTERN_BY_ID).
- PT-CIRCLE(FX.08)의 "Ø소"는 수치가 아니다. Pan/Tilt +-5도는 해석값이다.
  interpreted 목록에 남긴다. FX.02 는 시트가 수치를 전부 준다 -- 해석 없음.

## destination=preset

compose_fx 기본은 시퀀스를 만든다. 이 하네스는 항상 preset 을 명시한다.

## 안 하는 것

- 효과가 맞게 도는지 확인하지 않는다.
- 바이트를 판정 근거로 쓰지 않는다.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

from server.fx.schema import KNOWN_ATTRIBUTES
from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

FABRICATED_PATH = "Patch/FixtureTypesZZZNotAThing/9999"
FIXTURES_PATH = "Patch/Stages/1/Fixtures"
GROUPS_PATH = "DataPool/Groups"
PRESET_POOLS_PATH = "DataPool/PresetPools"

_PATTERN_BY_ID = {
    "FX.01": "chase",
    "FX.02": "pulse",
    "FX.03": "pulse",
    "FX.04": "wave",
    "FX.05": "sweep",
    "FX.06": "chase",
    "FX.07": "chase",
    "FX.08": "circle",
}

_ATTRIBUTE_AXES = {
    "Dimmer": ("Dimmer",),
    "Tilt": ("Tilt",),
    "Pan": ("Pan",),
    "Pan+Tilt": ("Pan", "Tilt"),
}

_CIRCLE_INTERPRETED_DEGREES = 5.0

_PM_RANGE_RE = re.compile(r"\xb1\s*(\d+(?:\.\d+)?)")
_TWO_VALUE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:/|\u2194|\u2192)\s*(-?\d+(?:\.\d+)?)")
_LEADING_NUMBER_RE = re.compile(r"(-?\d+(?:\.\d+)?)")
_PHASE_RANGE_RE = re.compile(r"(-?\d+)\s*\.\.\s*(-?\d+)")


class _RecordingApproval:
    def __init__(self, *, approve: bool) -> None:
        self._approve = approve
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return self._approve


class _RefusingQuestions:
    def __init__(self) -> None:
        self.asked: list[str] = []

    def ask(self, request) -> str:
        self.asked.append(getattr(request, "prompt", "") or "")
        return ""


def _state(state_port, path: str) -> dict:
    try:
        payload = state_port.query_state(path) or {}
    except Exception as error:  # noqa: BLE001
        return dict(path=path, ok=False, child_count=None, truncated=False, detail=str(error))
    node = payload.get("node") or {}
    return dict(
        path=path,
        ok=True,
        child_count=node.get("childCount"),
        children_in_reply=len(payload.get("children") or []),
        truncated=bool(payload.get("truncated")),
        detail=None,
    )


def read_fx_rows(csv_path: Path) -> list[dict]:
    text = csv_path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _steps_for(axes, row: dict, fx_id: str):
    if fx_id == "FX.08":
        d = _CIRCLE_INTERPRETED_DEGREES
        return (
            [
                {axis: -d for axis in axes},
                {axis: d for axis in axes},
            ],
            None,
        )
    wave = row.get("WaveSteps", "")
    two = _TWO_VALUE_RE.search(wave)
    if two is not None:
        a, b = float(two.group(1)), float(two.group(2))
        return [{axis: a for axis in axes}, {axis: b for axis in axes}], None
    pm = _PM_RANGE_RE.search(wave)
    if pm is not None:
        d = float(pm.group(1))
        return [{axis: -d for axis in axes}, {axis: d for axis in axes}], None
    return None, f"WaveSteps 에서 두 수치를 못 뽑았다: {wave!r}"


def _speed_for(row: dict):
    match = _LEADING_NUMBER_RE.search(row.get("BaseRate", ""))
    return float(match.group(1)) if match is not None else None


def _width_for(row: dict):
    raw = (row.get("Width", "") or "").strip()
    if not raw or raw in ("\u2014", "-"):
        return None
    match = _LEADING_NUMBER_RE.search(raw)
    return float(match.group(1)) if match is not None else None


def _phase_for(row: dict):
    match = _PHASE_RANGE_RE.search(row.get("Phase", ""))
    if match is not None:
        return float(match.group(1)), float(match.group(2))
    match = _LEADING_NUMBER_RE.search(row.get("Phase", ""))
    if match is not None:
        return float(match.group(1)), None
    return None, None


def translate_row(row: dict) -> dict:
    fx_id = row["ID"]
    name = row["Name"]
    attribute = row["Attribute"]
    axes = _ATTRIBUTE_AXES.get(attribute)
    if axes is None or any(axis not in KNOWN_ATTRIBUTES for axis in axes):
        return dict(
            fx_id=fx_id,
            name=name,
            skip_reason=f"attribute {attribute!r} 는 KNOWN_ATTRIBUTES 밖이다",
        )
    steps, step_error = _steps_for(axes, row, fx_id)
    if steps is None:
        return dict(fx_id=fx_id, name=name, skip_reason=step_error)
    pattern = _PATTERN_BY_ID.get(fx_id)
    if pattern is None:
        return dict(fx_id=fx_id, name=name, skip_reason=f"{fx_id} 의 pattern 이 안 박혀 있다")
    speed = _speed_for(row)
    if speed is None:
        return dict(
            fx_id=fx_id,
            name=name,
            skip_reason=f"BaseRate 를 못 읽었다: {row.get('BaseRate')!r}",
        )
    width = _width_for(row)
    phase_from, phase_to = _phase_for(row)
    arguments: dict = dict(
        pattern=pattern,
        steps=steps,
        destination="preset",
        speed=speed,
        label=name,
    )
    if width is not None:
        arguments["width"] = width
    # circle 은 phase_to 를 안 받는다(compose_fx 계약 -- "a circle's axes
    # are a quarter cycle apart by definition, measured from phase_from").
    # 정본 시트는 FX.08 만 circle 이고 Phase 열이 "0..360" 이라 phase_to 가
    # 채워지므로, 이 패턴에서만 명시적으로 걸러낸다.
    if pattern == "circle":
        if phase_from is not None:
            arguments["phase_from"] = phase_from
    else:
        if phase_from is not None:
            arguments["phase_from"] = phase_from
        if phase_to is not None:
            arguments["phase_to"] = phase_to
    return dict(
        fx_id=fx_id,
        name=name,
        arguments=arguments,
        interpreted=(fx_id == "FX.08"),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fx-csv", type=Path, required=True, help="정본 FX RIG CSV 절대경로")
    parser.add_argument("--action", choices=["preview", "apply"], default="preview")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--group",
        type=int,
        required=True,
        help="이 rig 에서 get_rig_context 가 답한 그룹 번호(이름 아님)",
    )
    parser.add_argument(
        "--only-ids",
        type=str,
        default=None,
        help="쉼표 구분 ID 부분집합(예 'FX.02,FX.08'). 생략하면 8종 전부",
    )
    parser.add_argument("--approve", action="store_true", help="없으면 콘솔에 아무것도 안 닿는다")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.action == "apply" and not args.approve:
        parser.error(
            "--action apply 는 --approve 를 요구한다. 승인 없이는 콘솔에 안 닿는다.\n"
            "확인과 사고가 같은 행위면 그 절차가 사고다."
        )

    only_ids = None if args.only_ids is None else set(args.only_ids.split(","))

    out: dict = dict(
        action=args.action,
        approve=args.approve,
        listen_port=args.listen_port,
        fx_csv=str(args.fx_csv),
        group=args.group,
        only_ids=sorted(only_ids) if only_ids is not None else None,
    )

    rows = read_fx_rows(args.fx_csv)
    if only_ids is not None:
        rows = [r for r in rows if r["ID"] in only_ids]
    translated = [translate_row(row) for row in rows]
    out["skipped"] = [
        dict(fx_id=t["fx_id"], name=t["name"], reason=t["skip_reason"])
        for t in translated
        if "skip_reason" in t
    ]
    out["interpreted"] = [
        dict(
            fx_id=t["fx_id"],
            name=t["name"],
            note=(
                "Ø소 는 시트가 수치를 주지 않는다 -- Pan/Tilt +-"
                f"{_CIRCLE_INTERPRETED_DEGREES}도는 우리 해석이다. "
                "감독이 GUI 에서 재녹화할 수 있다."
            ),
        )
        for t in translated
        if t.get("interpreted")
    ]
    runnable = [t for t in translated if "arguments" in t]
    out["runnable_count"] = len(runnable)
    out["skipped_count"] = len(out["skipped"])

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
        pools_before = _state(stack.gate.state_port, PRESET_POOLS_PATH)
        trustworthy = (not fabricated["ok"]) and fixtures["ok"] and groups["ok"]
        out["baseline"] = dict(
            fabricated_control=fabricated,
            fixtures=fixtures,
            groups=groups,
            preset_pools_before=pools_before,
            channel_trustworthy=trustworthy,
        )
        if not trustworthy:
            out["stopped"] = "channel_untrustworthy"
            exit_code = 2
        else:
            registry = build_toolset(
                execution_port=stack.gate.execution_port,
                state_port=stack.gate.state_port,
                property_port=stack.gate.state_port,
                bundle_gate=stack.gate,
                question_port=questions,
                group_approval_port=approval,
            )
            results = []
            for entry in runnable:
                call_args = dict(entry["arguments"])
                call_args["group"] = args.group
                execution = registry.dispatch(
                    ToolCall(id=f"fxe2e-{entry['fx_id']}", name="compose_fx", arguments=call_args)
                )
                results.append(
                    dict(
                        fx_id=entry["fx_id"],
                        name=entry["name"],
                        arguments=call_args,
                        is_error=execution.result.is_error,
                        response=json.loads(execution.result.content),
                    )
                )
            out["results"] = results
            out["preset_pools_after"] = _state(stack.gate.state_port, PRESET_POOLS_PATH)
        out["approval_requests"] = [list(bundle) for bundle in approval.asked]
        out["questions_asked"] = questions.asked
    finally:
        stack.stop()

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

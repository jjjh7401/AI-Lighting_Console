"""POS 포지션 프리셋 산출·저장 라이브 하네스 (t220).

**검증 도구다 — 제품 코드가 아니다.** `server/tools/lxseq_presets_e2e.py` 의 형태를
승계한다: 실포트 조립(`build_console_stack` + `build_toolset`), 우회 배선 0,
`--approve` 없으면 콘솔에 아무것도 닿지 않는다.

## 무엇을 하나

1. 판독 채널을 먼저 잰다 — 날조 경로가 거절되고 실경로가 읽히는지(대조군 두 팔).
2. `get_spatial_context` 로 **리그 전체** 좌표를 읽는다. 부분 판독이면 멈춘다.
3. `server/lxseq/position_derive.py` 가 POS 시트 + 그룹 멤버십 + 좌표에서 조준값을
   산출한다. 못 푸는 행은 사유와 함께 남기고 **날조하지 않는다.**
4. `--action apply --approve` 일 때만 룩마다 적용 -> Store -> Label -> ClearAll
   한 번들을 쏜다. 실패한 룩이 있어도 나머지는 산다.
5. 풀을 **독립적으로** 되읽는다 — 툴 응답을 생성 증거로 쓰지 않는다.

## 안 하는 것

- **값이 맞는지 확인하지 않는다.** 프리셋 값 판독 채널이 없다(t105). 슬롯 점유와
  이름만 되읽는다. 조준이 실제로 어디 떨어지는지는 **현장에서 사람이 본다.**
- **Position 풀 밖을 건드리지 않는다.**
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.lxseq.position_derive import (
    DERIVED_LABEL_SUFFIX,
    SYNTHETIC_LABEL_SUFFIX,
    derive_position_presets,
    group_members_from_sheets,
    parse_position_sheet,
    position_preset_bundles,
)
from server.orchestrator.tools import build_toolset
from server.preshow.checks import DEFAULT_PRESET_POOLS_PATH
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack
from server.spatial.pointing import POSITION_PRESET_POOL
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

#: 판독 채널 날조 대조군. 있을 수 없는 경로라 **ok=False 가 정답**이다.
FABRICATED_PATH = "Patch/FixtureTypesZZZNotAThing/9999"

FIXTURES_PATH = "Patch/Stages/1/Fixtures"


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
    """한 경로의 state 를 요약한다. 읽기 전용.

    거절은 예외로 온다 — 날조 대조군에게는 그 예외가 **정답**이므로 잡아서
    ok=False 로 적는다. 새어 나가게 두면 대조군이 하네스를 죽인다.
    """
    try:
        payload = state_port.query_state(path) or dict()
    except Exception as error:  # noqa: BLE001
        return dict(path=path, ok=False, child_count=None, truncated=False, detail=str(error))
    node = payload.get("node") or dict()
    children = payload.get("children") or []
    return dict(
        path=path,
        ok=True,
        child_count=node.get("childCount"),
        children_in_reply=len(children),
        names=[c.get("name") for c in children if isinstance(c, dict)],
        truncated=bool(payload.get("truncated")),
        detail=None,
    )


def _coordinates(registry) -> tuple[dict, str | None]:
    """리그 전체 좌표. 부분 판독이면 (빈 dict, 사유).

    `server/web/session.py:_read_pointing_coordinates` 와 **같은 판정**이다 —
    절단된 판독으로 반 리그를 조준하지 않는다.
    """
    execution = registry.dispatch(
        ToolCall(id="t220-coords", name="get_spatial_context", arguments=dict())
    )
    if execution.result.is_error:
        return dict(), "get_spatial_context 가 오류를 냈다: " + execution.result.content[:200]
    try:
        payload = json.loads(execution.result.content)
    except json.JSONDecodeError as error:
        return dict(), "좌표 응답이 JSON 이 아니다: " + str(error)
    if "fixtures" in payload:
        records = payload["fixtures"]
    else:
        if payload.get("truncated") or payload.get("roundtrip_capped"):
            return dict(), "좌표 판독이 절단됐다 — 반 리그를 조준하지 않는다"
        records = payload.get("partial_fixtures") or []
    coordinates = dict()
    for record in records:
        if not isinstance(record, dict):
            continue
        fid = record.get("fid")
        if not isinstance(fid, int) or isinstance(fid, bool):
            continue
        try:
            coordinates[fid] = (
                float(record["x"]),
                float(record["y"]),
                float(record["z"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
    if not coordinates:
        return dict(), "좌표가 확인된 장비가 0대다"
    return coordinates, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pos-csv", type=Path, required=True, help="정본 preset-pos CSV")
    parser.add_argument("--patch-csv", type=Path, required=True, help="정본 patch CSV")
    parser.add_argument("--group-csv", type=Path, required=True, help="정본 group CSV")
    parser.add_argument("--action", choices=["preview", "apply"], default="preview")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="산출된 룩 앞 N 개만 쏜다. 기본 1 — 「소수 먼저 넣고 되읽는다」. 0 이면 전부",
    )
    parser.add_argument("--probe-only", action="store_true", help="기준 상태만 읽는다. 콘솔 쓰기 0")
    # 라벨 꼬리는 **좌표의 출처**를 나른다. 기본값 「산출값」은 조준값이 계산됐다는
    # 뜻이라 좌표는 실측인 것처럼 읽힌다 — 좌표 자체가 합성이면 그쪽이 더 강한
    # 주장이고, 그 사실이 라벨에 없으면 계산된 조준이 현장 레코드로 오독된다.
    parser.add_argument(
        "--synthetic-coords",
        action="store_true",
        help=(
            "리그 좌표가 합성이면 붙인다. 라벨 꼬리가 "
            f"「· {DERIVED_LABEL_SUFFIX}」 대신 「· {SYNTHETIC_LABEL_SUFFIX}」 가 된다"
        ),
    )
    parser.add_argument("--approve", action="store_true", help="없으면 콘솔에 아무것도 닿지 않는다")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    # [HARD] --approve 는 **행위**를 막는다. 승인 통로의 대답만 정하면 아무것도
    # 안 막는다. 콘솔 스택을 세우기 **전에** 거부한다.
    if args.action == "apply" and not args.approve:
        parser.error("--action apply 는 --approve 를 요구한다. 승인 없이는 콘솔에 닿지 않는다.")

    limit = None if args.limit == 0 else args.limit
    label_suffix = SYNTHETIC_LABEL_SUFFIX if args.synthetic_coords else DERIVED_LABEL_SUFFIX
    pool_path = DEFAULT_PRESET_POOLS_PATH + "/" + str(POSITION_PRESET_POOL)
    out: dict[str, object] = dict(
        action=args.action,
        approve=args.approve,
        listen_port=args.listen_port,
        limit=limit,
        pool_path=pool_path,
        label_suffix=label_suffix,
    )

    rows = parse_position_sheet(args.pos_csv.read_text(encoding="utf-8-sig"))
    members = group_members_from_sheets(
        args.patch_csv.read_text(encoding="utf-8-sig"),
        args.group_csv.read_text(encoding="utf-8-sig"),
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
        pool_before = _state(stack.gate.state_port, pool_path)
        trustworthy = (not fabricated["ok"]) and fixtures["ok"] and pool_before["ok"]
        out["baseline"] = dict(
            fabricated_control=fabricated,
            fixtures=fixtures,
            pool_before=pool_before,
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
            coordinates, coord_reason = _coordinates(registry)
            out["coordinates_read"] = dict(count=len(coordinates), reason=coord_reason)
            if coord_reason is not None:
                out["stopped"] = "no_coordinates"
                exit_code = 2
            else:
                result = derive_position_presets(
                    rows, members, coordinates, label_suffix=label_suffix
                )
                out["derived"] = [
                    dict(
                        preset_id=item.preset_id,
                        slot=item.slot,
                        label=item.label,
                        target_group=item.target_group,
                        rule_kind=item.rule_kind,
                        summary=item.summary,
                        aim_count=len(item.aims),
                        aims=[list(aim) for aim in item.aims],
                        skipped_fids=list(item.skipped_fids),
                    )
                    for item in result.derived
                ]
                out["skipped"] = [
                    dict(
                        preset_id=item.preset_id,
                        target_group=item.target_group,
                        reason=item.reason,
                        detail=item.detail,
                    )
                    for item in result.skipped
                ]
                out["unverified"] = list(result.unverified)
                out["unverified_reason"] = result.unverified_reason
                selected = result.derived if limit is None else result.derived[:limit]
                bundles = position_preset_bundles(selected)
                out["bundles"] = [list(bundle) for bundle in bundles]
                if args.probe_only or args.action != "apply":
                    out["stopped"] = "probe_only" if args.probe_only else "preview"
                else:
                    sent: list[dict[str, object]] = []
                    for item, bundle in zip(selected, bundles, strict=True):
                        execution = registry.dispatch(
                            ToolCall(
                                id="t220-" + item.preset_id,
                                name="run_commands",
                                arguments=dict(commands=list(bundle)),
                            )
                        )
                        sent.append(
                            dict(
                                preset_id=item.preset_id,
                                is_error=execution.result.is_error,
                                payload=json.loads(execution.result.content),
                            )
                        )
                    out["sent"] = sent
                # 툴 응답을 생성 증거로 쓰지 않는다 — 풀을 독립적으로 되읽는다.
                out["pool_after"] = _state(stack.gate.state_port, pool_path)
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

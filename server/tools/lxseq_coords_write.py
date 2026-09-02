"""RIG 팩 좌표 CSV 를 콘솔 패치에 올리는 라이브 하네스 (t224).

**검증 도구다 — 제품 코드가 아니다.** `server/tools/lxseq_pos_e2e.py` 의 형태를
승계한다: 실포트 조립(`build_console_stack` + `build_toolset`), 우회 배선 0,
`--approve` 없으면 콘솔에 **쓰기**가 닿지 않는다.

## 왜 이 하네스가 있나

t221 이 「POS 3행 불가」의 뿌리를 좌표로 특정했다 — 콘솔의 86대가 전부 원점이라
규칙이 퇴화한 입력을 받았고, 죽은 세 행보다 **거짓 초록으로 산 세 행**이 더
위험했다. 막힌 것은 능력이 아니라 데이터였다: `arrange_fixtures` 가 이미
`Posx/Posy/Posz` 를 쓴다.

다만 그 도구의 프리셋은 전부 **도형**이었다. 이 하네스가 필요로 하는 것은
장비마다 다른 값이라 도형이 아니고, 그래서 t224 가 `explicit` 프리셋을 더했다.
봉투(백업 → 정적 범위검사 → 쓰기 → 되읽기)는 한 줄도 우회하지 않는다.

## 무엇을 하나

1. 판독 채널을 먼저 잰다 — 날조 경로가 거절되고 실경로가 읽히는지(대조군 두 팔).
2. 좌표 CSV 를 읽어 `⟦fid, x, y, z⟧` 계획을 만든다.
3. `--action preview` 는 **승인을 거부하는 채널**로 같은 호출을 돌린다. 백업은
   콘솔에서 실제로 읽히고 복원 번들이 산출되지만 쓰기는 게이트에서 막힌다 —
   즉 **쓰기 전에 복원 번들을 확보하는** 자리다.
4. `--action apply --approve` 만 실제로 쓴다. 도구가 스스로 되읽어 수치로
   대조하고, 그 결과가 `verified` 다.
5. 표본 장비의 좌표를 **호출 전후로 따로** 읽는다 — 도구 응답을 그 도구의
   증거로 쓰지 않는다.

## 안 하는 것

- **좌표 이외의 어떤 것도 안 건드린다.** 정적 범위검사가 `Set Fixture <fid>
  Pos[xyz]` 밖의 줄을 이미 거절한다.
- **이 값이 맞는 자리인지 판정하지 않는다.** CSV 가 합성이면 콘솔도 합성이다.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import EXPLICIT_PRESET, build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

#: 판독 채널 날조 대조군. 있을 수 없는 경로라 **ok=False 가 정답**이다.
FABRICATED_PATH = "Patch/FixtureTypesZZZNotAThing/9999"

FIXTURES_PATH = "Patch/Stages/1/Fixtures"

#: 좌표 CSV 가 반드시 들어야 하는 열. 나머지 열(Group·FixtureType·Position)은
#: 사람이 읽는 자리라 있어도 되고 없어도 된다.
REQUIRED_COLUMNS = ("FID", "X", "Y", "Z")


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


def parse_coords_sheet(text: str) -> list[dict]:
    """좌표 CSV → `arrange_fixtures` 의 `positions` 항목 목록.

    날조하지 않는다: 열이 없거나 값이 숫자가 아니면 **그 행을 조용히 건너뛰지
    않고** 예외를 낸다. 한 대가 빠진 리그는 좌표가 0 인 리그보다 알아보기
    어렵다 — 나머지 85대가 제자리에 있으면 그 한 대는 눈에 안 띈다.
    """
    reader = csv.DictReader(io.StringIO(text))
    columns = tuple(reader.fieldnames or ())
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise ValueError(f"좌표 CSV 에 열이 없다: {missing} (읽은 열: {list(columns)})")
    rows: list[dict] = []
    for number, row in enumerate(reader, start=2):
        raw_fid = (row.get("FID") or "").strip()
        if not raw_fid:
            continue
        try:
            entry = dict(
                fid=int(raw_fid),
                x=float((row.get("X") or "").strip()),
                y=float((row.get("Y") or "").strip()),
                z=float((row.get("Z") or "").strip()),
            )
        except ValueError as error:
            raise ValueError(f"{number}행을 숫자로 못 읽었다: {error}") from error
        rows.append(entry)
    if not rows:
        raise ValueError("좌표 CSV 에 행이 0건이다")
    return rows


def _state(state_port, path: str) -> dict:
    """한 경로의 state 요약. 읽기 전용.

    거절은 예외로 온다 — 날조 대조군에게는 그 예외가 **정답**이므로 잡아서
    ok=False 로 적는다. 새어 나가게 두면 대조군이 하네스를 죽인다.
    """
    try:
        payload = state_port.query_state(path) or dict()
    except Exception as error:  # noqa: BLE001
        return dict(path=path, ok=False, child_count=None, detail=str(error))
    node = payload.get("node") or dict()
    children = payload.get("children") or []
    return dict(
        path=path,
        ok=True,
        child_count=node.get("childCount"),
        children_in_reply=len(children),
        truncated=bool(payload.get("truncated")),
        detail=None,
    )


def _read_axes(state_port, slot: int) -> dict:
    """한 슬롯의 FID 와 세 축을 **도구 밖에서** 직접 읽는다.

    도구가 자기 되읽기로 `verified` 를 말하지만, 그 판정을 그 도구의 응답으로만
    확인하면 계기와 피검사체가 같아진다. 이 팔은 별도 호출이다.
    """
    out: dict[str, object] = dict(slot=slot)
    for name in ("FID", "Posx", "Posy", "Posz"):
        try:
            reply = state_port.query_property(f"{FIXTURES_PATH}/{slot}", name)
        except Exception as error:  # noqa: BLE001
            out[name] = dict(ok=False, detail=str(error))
            continue
        out[name] = dict(ok=bool(reply.get("ok")), value=reply.get("value"))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coords-csv", type=Path, required=True, help="정본 coords CSV")
    parser.add_argument("--action", choices=["preview", "apply"], default="preview")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="앞 N 대만 올린다. 기본 3 — 「소수 먼저 넣고 되읽는다」. 0 이면 전부",
    )
    parser.add_argument("--approve", action="store_true", help="없으면 콘솔에 쓰기가 안 닿는다")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    # [HARD] --approve 는 **행위**를 막는다. 승인 통로의 대답만 정하면 아무것도
    # 안 막는다. 콘솔 스택을 세우기 **전에** 거부한다.
    if args.action == "apply" and not args.approve:
        parser.error("--action apply 는 --approve 를 요구한다. 승인 없이는 콘솔에 안 쓴다.")

    entries = parse_coords_sheet(args.coords_csv.read_text(encoding="utf-8-sig"))
    selected = entries if args.limit == 0 else entries[: args.limit]
    fids = [entry["fid"] for entry in selected]

    out: dict[str, object] = dict(
        action=args.action,
        approve=args.approve,
        listen_port=args.listen_port,
        coords_csv=str(args.coords_csv),
        rows_in_sheet=len(entries),
        targets=len(selected),
        extent=dict(
            x=[min(e["x"] for e in entries), max(e["x"] for e in entries)],
            y=[min(e["y"] for e in entries), max(e["y"] for e in entries)],
            z=[min(e["z"] for e in entries), max(e["z"] for e in entries)],
        ),
    )

    approval = _RecordingApproval(approve=args.action == "apply" and args.approve)
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
        trustworthy = (not fabricated["ok"]) and fixtures["ok"]
        out["baseline"] = dict(
            fabricated_control=fabricated,
            fixtures=fixtures,
            channel_trustworthy=trustworthy,
            sample_before=_read_axes(stack.gate.state_port, 1),
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
            execution = registry.dispatch(
                ToolCall(
                    id="t224-coords",
                    name="arrange_fixtures",
                    arguments=dict(preset=EXPLICIT_PRESET, fids=fids, positions=selected),
                )
            )
            payload = json.loads(execution.result.content)
            out["arrange"] = dict(is_error=execution.result.is_error, payload=payload)
            # 도구 응답을 그 도구의 증거로 쓰지 않는다 — 표본을 따로 읽는다.
            out["sample_after"] = _read_axes(stack.gate.state_port, 1)
            if execution.result.is_error and args.action == "apply":
                exit_code = 2
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

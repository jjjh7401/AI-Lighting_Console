"""LX-SEQ 프리셋 라이브 하네스 (SPEC-COPILOT-LXSEQ-003 M4).

**검증 도구다 — 제품 코드가 아니다.** `server/tools/lxseq_groups_e2e.py` 의 형태를
승계한다: 실포트 조립(`build_console_stack` + `build_toolset`), 우회 배선 0,
`--approve` 없으면 콘솔에 아무것도 닿지 않는다.

## 왜 `--limit` 이 있고 기본값이 1인가

SPEC 의 M4 [HARD] 는 「**소수 먼저 넣고 되읽은 뒤 다음을 정한다**」이다. 계획이
6건이어도 6을 한 번에 넣는 것은 그 조항을 만족시키지 않는다 — 3번째에서 실패하면
무엇이 남았는지 **사람이 눈으로 세야** 하고, 프리셋 값은 되읽을 수 없어 확인할
방법도 없다. 한 건이 성공하면 문형·슬롯 배정·되읽기 경로가 전부 참이고, 실패하면
**되돌릴 것이 한 건**이다.

`--limit` 은 시트를 자른다 — 툴은 평소대로 동작한다. 툴에 상한을 넣으면 제품
코드가 하네스 사정을 알게 된다.

## 안 하는 것

- **값이 맞는지 확인하지 않는다.** 채널이 없다. 슬롯 점유만 되읽는다.
- **바이트를 판정 근거로 쓰지 않는다.** 콘솔 거절이 길이가 아니라 내용에
  달려 있다(t72: 2044B 거절 · 2080B 통과, 재현됨). 기록만 한다.
- **프리셋 풀 밖을 건드리지 않는다.** 콘솔에 미저장 유일본이 있다.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.preshow.checks import DEFAULT_PRESET_POOLS_PATH
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument, preflight

#: 판독 채널 날조 대조군. 있을 수 없는 경로라 **`ok=False` 가 정답**이다.
FABRICATED_PATH = "Patch/FixtureTypesZZZNotAThing/9999"

FIXTURES_PATH = "Patch/Stages/1/Fixtures"
GROUPS_PATH = "DataPool/Groups"


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
    """한 경로의 state 를 읽어 요약한다. 읽기 전용.

    거절은 예외로 온다 — 날조 대조군에게는 그 예외가 **정답**이므로 잡아서
    `ok=False` 로 적는다. 새어 나가게 두면 대조군이 하네스를 죽인다.
    """
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


def _sliced(csv_path: Path, limit: int | None, *, skip: int = 0) -> bytes:
    """헤더 + `skip` 행을 건너뛴 뒤의 `limit` 행. `limit` 가 `None` 이면 나머지 전부.

    매퍼는 이름 중복을 안 본다 — 점유 안 된 슬롯을 오름차순으로 고를 뿐이다.
    그래서 「이미 들어간 행을 다시 안 쏜다」는 여기서 책임진다. 파생 CSV 를
    만들지 않는 이유도 같다: 출처(sha256)가 정본 시트를 가리켜야 한다.
    """
    text = csv_path.read_text(encoding="utf-8-sig")
    lines = [line for line in text.splitlines() if line.strip()]
    if limit is None and skip == 0:
        return text.encode("utf-8")
    header, rows = lines[0], lines[1 + skip :]
    if limit is not None:
        rows = rows[:limit]
    return ("\n".join([header, *rows]) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset-csv", type=Path, required=True, help="정본 PRESET CSV 절대경로")
    parser.add_argument("--action", choices=["preview", "apply"], default="preview")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="시트에서 앞 N 행만 쓴다. 기본 1 — SPEC M4 의 「소수 먼저」다. 0 이면 통째",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="기준 상태만 읽고 툴은 부르지 않는다. 콘솔 쓰기 0",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="시트 앞 N 행을 건너뛴다. 이미 들어간 행을 다시 쏘지 않기 위한 오프셋",
    )
    parser.add_argument("--approve", action="store_true", help="없으면 콘솔에 아무것도 닿지 않는다")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    # [HARD] `--approve` 는 **행위**를 막는다. 승인 통로의 대답만 정하면
    # 아무것도 안 막는다 — 2026-08-25 사고가 정확히 그것이었다. 콘솔 스택을
    # 세우기 **전에** 거부한다.
    if args.action == "apply" and not args.approve:
        parser.error(
            "--action apply 는 --approve 를 요구한다. 승인 없이는 콘솔에 닿지 않는다.\n"
            "안전장치가 도는지 확인하려고 apply 를 쏘지 마라 — 그 확인은 "
            "server/tests/test_lxseq_preset_safety.py 가 한다. 확인과 사고가 "
            "같은 행위이면 그 절차가 사고다."
        )

    limit = None if args.limit == 0 else args.limit
    out: dict[str, object] = dict(
        action=args.action,
        approve=args.approve,
        listen_port=args.listen_port,
        preset_csv=str(args.preset_csv),
        limit=limit,
        skip=args.skip,
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
        trustworthy = (not fabricated["ok"]) and fixtures["ok"] and groups["ok"]
        out["baseline"] = dict(
            fabricated_control=fabricated,
            fixtures=fixtures,
            groups=groups,
            channel_trustworthy=trustworthy,
        )
        if not trustworthy:
            # 날조 경로가 통과했거나 실경로가 안 읽혔다 — 어느 쪽이든 이 하네스의
            # 관측이 증거가 아니게 되므로 멈춘다.
            out["stopped"] = "channel_untrustworthy"
            exit_code = 2
        elif args.probe_only:
            out["stopped"] = "probe_only"
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
                    id="lxp1",
                    name="import_lxseq_presets",
                    arguments=dict(
                        file_content_base64=base64.b64encode(
                            _sliced(args.preset_csv, limit, skip=args.skip)
                        ).decode("ascii"),
                        action=args.action,
                    ),
                )
            )
            out["tool"] = json.loads(execution.result.content)
            # 툴 응답을 생성 증거로 쓰지 않는다 — 명령이 성공한 것과 대상이 바뀐
            # 것은 다르다. 풀을 **독립적으로** 되읽는다.
            pool_no = out["tool"].get("pool_no")
            if isinstance(pool_no, int):
                out["pool_after"] = _state(
                    stack.gate.state_port,
                    DEFAULT_PRESET_POOLS_PATH + "/" + str(pool_no),
                )
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

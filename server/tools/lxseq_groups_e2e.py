"""LX-SEQ 그룹 라이브 하네스 (SPEC-COPILOT-LXSEQ-002 M4).

**검증 도구다 — 제품 코드가 아니다.** 001 의 `server/tools/lxseq_e2e.py` 형태를
그대로 승계한다: 실포트 조립(`build_console_stack` + `build_toolset`), 우회 배선 0,
`--approve` 없으면 콘솔에 아무것도 닿지 않는다.

사용 (읽기 전용 프로브만):

    uv run python -m server.tools.lxseq_groups_e2e \
        --group-csv <정본 group.csv> --patch-csv <정본 patch.csv> \
        --listen-port 9005 --probe-only

발사 (사람이 계획을 읽고 동의한 뒤에만):

    uv run python -m server.tools.lxseq_groups_e2e \
        --group-csv ... --patch-csv ... --listen-port 9005 \
        --action apply --approve

`--listen-port` 는 **기본값이 없는 필수 인자**다. 이 저장소의 하네스들이 9005 와
9000 으로 갈려 있고(카드 t61), 기본값에 기대면 틀린 포트로 조용히 쏜 뒤 그 침묵을
「응답기가 죽었다」로 오독한다. 실제로 이 카드가 그 오독 직전까지 갔다. 그래서
새 도구는 처음부터 **말하게 한다.**
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

#: 판독 채널 날조 대조군. 있을 수 없는 이름이라 **`ok=False` 가 정답**이다.
#: `ok=True` 가 오면 채널이 아무 말에나 「있다」고 답한다는 뜻이고, 그때는 이
#: 하네스의 어떤 관측도 증거가 아니다.
FABRICATED_PATH = "Patch/FixtureTypesZZZNotAThing/9999"

#: M4 전제 P3. 경로 주의 — `Patch/Fixtures` 는 RETIRED_PATHS 다.
FIXTURES_PATH = "Patch/Stages/1/Fixtures"

#: M4 전제 P4. 그룹 풀.
GROUPS_PATH = "DataPool/Groups"

#: P3 이 요구하는 픽스처 수. **`childCount` 로만 판정한다** — 같은 조회의
#: `children` 은 절단되어 86 이 아니라 19 로 온다(실측). 절단은 개수가 아니라
#: 페이로드 예산이므로 「N개가 돌아온다」로 못박지 않는다.
EXPECTED_FIXTURE_COUNT = 86


class _RecordingApproval:
    """번들 승인 채널. 승인 여부와 무관하게 요청을 그대로 기록한다."""

    def __init__(self, *, approve: bool) -> None:
        self._approve = approve
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        self.asked.append(tuple(request.commands))
        return self._approve


class _RefusingQuestions:
    """질문 카드 통로 — 이 하네스는 **대신 답하지 않는다.**"""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def ask(self, request) -> str:
        self.asked.append(getattr(request, "prompt", "") or "")
        return ""


def _state(state_port, path: str) -> dict:
    """한 경로의 state 를 읽어 요약한다. 읽기 전용.

    **거절은 예외로 온다** — 게이트의 `query_state` 는 없는 경로에
    `StateQueryError` 를 던진다. 날조 대조군에게는 그 예외가 **정답**이므로
    잡아서 `ok=False` 로 적는다. 예외를 새어 나가게 두면 대조군이 하네스를
    죽여 정작 재려던 것을 못 잰다 — 이 카드가 처음 돌렸을 때 그렇게 됐다.
    """
    try:
        payload = state_port.query_state(path) or {}
    except Exception as error:  # noqa: BLE001 — 거절 사유를 그대로 싣는다
        return {
            "path": path,
            "ok": False,
            "child_count": None,
            "children_in_reply": 0,
            "truncated": False,
            "detail": str(error),
        }
    node = payload.get("node") or {}
    return {
        "path": path,
        "ok": True,
        "child_count": node.get("childCount"),
        "children_in_reply": len(payload.get("children") or []),
        "truncated": bool(payload.get("truncated")),
        "detail": None,
    }


def _probe_preconditions(state_port) -> dict:
    """M4 전제 P1~P4 를 읽기 전용으로 잰다. 콘솔 쓰기 0.

    **날조 대조군을 먼저 쏜다.** 없는 경로가 거절되는 것을 본 뒤에야 0 을
    「없다」의 증거로 쓴다 — 대조군 없이 나온 0 은 판독 실패와 구분되지 않는다.
    """
    fabricated = _state(state_port, FABRICATED_PATH)
    fixtures = _state(state_port, FIXTURES_PATH)
    groups = _state(state_port, GROUPS_PATH)

    channel_trustworthy = (not fabricated["ok"]) and fixtures["ok"] and groups["ok"]

    # @MX:ANCHOR: [AUTO] `channel_trustworthy` 는 아래 `all_pass` 안에 **반드시**
    #   남아 있어야 한다. 「대조군은 앞에서 한 번 보면 되지」로 빼지 마라.
    # @MX:REASON: P4 는 「0이면 통과」다. 그러므로 **판독 채널이 죽어서 0을 답해도
    #   통과로 읽힌다** — 빈 풀과 안 읽히는 풀이 같은 값을 낸다. 대조군 결과가
    #   all_pass 안에 있어야 그 거짓 통과가 막힌다. 이것을 앞단의 일회성 점검으로
    #   옮기면, 채널이 그 사이에 죽었을 때 「전부 0이니 발사해도 된다」가 성립한다.
    #   그리고 이 발사는 되돌릴 수 없다(그룹 멤버십은 되읽히지 않고 Delete 는
    #   블랙리스트다).

    checks = {
        "P3_patched_fixtures": {
            "observed_child_count": fixtures["child_count"],
            "expected": EXPECTED_FIXTURE_COUNT,
            "pass": fixtures["child_count"] == EXPECTED_FIXTURE_COUNT,
            "note": (
                "childCount 로만 판정한다. children_in_reply="
                + str(fixtures["children_in_reply"])
                + " 는 절단된 값이며 개수가 아니다"
            ),
        },
        "P4_empty_group_pool": {
            "observed_child_count": groups["child_count"],
            "expected": 0,
            "pass": groups["child_count"] == 0,
            "note": "빈 쇼파일이라 0 인 것과 재료가 준비돼 0 인 것은 다르다",
        },
    }
    return {
        "channel_trustworthy": channel_trustworthy,
        "fabricated_control": fabricated,
        "fixtures": fixtures,
        "groups": groups,
        "checks": checks,
        "all_pass": channel_trustworthy and all(c["pass"] for c in checks.values()),
    }


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group-csv", type=Path, required=True, help="정본 GROUP CSV 절대경로")
    parser.add_argument("--patch-csv", type=Path, required=True, help="정본 패치 CSV 절대경로")
    parser.add_argument("--action", choices=["preview", "apply"], default="preview")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="전제 P1~P4 만 읽고 툴은 부르지 않는다. 콘솔 쓰기 0",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="승인 게이트를 통과시킨다. 없으면 콘솔에 아무것도 닿지 않는다",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    out: dict[str, object] = {
        "action": args.action,
        "approve": args.approve,
        "listen_port": args.listen_port,
        "group_csv": str(args.group_csv),
        "patch_csv": str(args.patch_csv),
    }

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
        # 응답기가 답하는지, 안 답하면 **왜 안 답하는지** 먼저 이름 붙인다.
        # 틀린 포트의 침묵과 죽은 응답기의 침묵은 구분되지 않는다(t61) —
        # 아래 전제 판독이 조용히 실패하기 전에 그 구분을 세운다.
        out["preflight"] = preflight(
            stack.gate,
            receive_host="127.0.0.1",
            receive_port=args.listen_port,
            console_port=args.port,
        )
        preconditions = _probe_preconditions(stack.gate.state_port)
        out["preconditions"] = preconditions

        if not preconditions["channel_trustworthy"]:
            # 날조 대조군이 통과했거나 실경로가 안 읽혔다. 어느 쪽이든 이 하네스의
            # 관측이 증거가 아니게 되므로 여기서 멈춘다.
            out["stopped"] = "channel_untrustworthy"
            exit_code = 2
        elif args.probe_only:
            out["stopped"] = "probe_only"
        elif not preconditions["all_pass"]:
            # 전제가 하나라도 미충족이면 발사하지 않는다. 감독 승인 조건이다.
            out["stopped"] = "preconditions_unmet"
            exit_code = 3
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
                    id="lxg1",
                    name="import_lxseq_groups",
                    arguments={
                        "group_content_base64": _b64(args.group_csv),
                        "patch_content_base64": _b64(args.patch_csv),
                        "action": args.action,
                    },
                )
            )
            out["tool"] = json.loads(execution.result.content)
            # 툴 응답을 생성 증거로 쓰지 않는다 — 명령이 성공한 것과 대상이 바뀐
            # 것은 다르다. 풀을 **독립적으로** 되읽는다.
            out["groups_after"] = _state(stack.gate.state_port, GROUPS_PATH)
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

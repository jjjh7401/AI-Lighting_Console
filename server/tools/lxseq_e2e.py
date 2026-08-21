"""LX-SEQ M4 종단 라이브 검증 하네스 (AC-LXSEQ-016).

This is a DEV TOOL, not a production execution path — the same class as
``busking_e2e``·``groupgen_e2e``: it needs **no** import-boundary exemption
because it reaches the console only through the production seam. The OSC send
surface is not named anywhere in this file, which is mechanically checkable and
is the form `plan.md` M4 asked for::

    grep -c server\\.bridge server/tools/lxseq_e2e.py   # must print 0

(그 문자열을 이 독스트링에 그대로 적으면 검사가 스스로를 세게 되므로 이스케이프해
둔다 — 검사 대상은 임포트이지 산문이 아니다.)

**우회 배선을 만들지 않는다**: 콘솔 스택은 조립 루트 `build_console_stack`이
세우고, 툴은 `ChatSession`이 쓰는 것과 같은 `build_toolset`으로 만든다. 배포
파이프라인도 `serve.py`가 세우는 것과 같은 `DeployPipeline`이다. 여기서
게이트·감사·브리지를 손으로 엮으면 M4가 검증하는 것이 제품 경로가 아니게 된다.

**파일은 이 스크립트가 읽는다.** `import_lxseq_patch`는 파일 경로 인자를
가지지 않는다(REQ-LXSEQ-010 인자 집합 불변). 여기서 정본 CSV 바이트를 읽어
base64로 인코딩해 툴 인자 `file_content_base64`를 채운다 — 채팅 본문 텍스트로
바이트를 만드는 경로는 어디에도 없다(REQ-LXSEQ-016).

Usage (from the project root, with grandMA3 onPC running the responder)::

    uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> \
        --action preview --listen-port 9005

`--action apply`는 **`--approve`가 함께 있을 때만** 콘솔에 닿는다. 없으면
`DenyAllApprovalPort`·`DenyAllReviewPort`가 막고, 그때의 관측(콘솔 송신 0건)도
유효한 결과다. 이 앱에는 실행 취소가 없고 MA3는 패치된 장비를 코파일럿으로
지울 수단이 없다 — 그래서 기본값은 무해한 쪽이다.

**채널 검증이 먼저 돈다.** 판독 채널이 거짓 `ok`를 내면 그 뒤의 모든 관측은
증거로 쓸 수 없다. 그래서 매 실행마다 (a) 정상 왕복 1회와 (b) **날조 대조군**
1회를 먼저 쏘고, (b)가 `ok`로 돌아오면 계획도 세우지 않고 멈춘다.

⚠ `sys.path[0]` 함정: 이 모듈을 파일 경로로 실행하면 스크립트 디렉터리가
`sys.path[0]`이 되어 editable 설치가 가리키는 **다른 체크아웃**의 `server`
패키지를 import할 수 있다(이 저장소에서 실측된 함정). 반드시 `-m`으로 실행하라.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

from server.deploy.compile import LuaCompileChecker
from server.deploy.pipeline import DeployPipeline
from server.deploy.review import ReviewRequest
from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack

#: 판독 채널 날조 대조군이 물어보는 경로. 콘솔에 있을 수 없는 이름이라
#: **`ok=False`가 정답**이다. `ok=True`가 오면 채널이 아무 말에나 «있다»고
#: 답한다는 뜻이고, 그때는 이 하네스의 어떤 관측도 증거가 아니다.
FABRICATED_PATH = "Patch/FixtureTypesZZZNotAThing/9999"

#: 정상 왕복이 물어보는 경로 — 툴이 타입을 확정할 때 쓰는 바로 그 트리다.
LIVE_PATH = "Patch/FixtureTypes"


class _RecordingApproval:
    """번들 승인 채널. 승인 여부와 상관없이 요청을 그대로 기록한다."""

    def __init__(self, *, approve: bool) -> None:
        self._approve = approve
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        self.asked.append(tuple(request.commands))
        return self._approve


class _RecordingReview:
    """플러그인 배포 검토 채널. 무엇이 배포되려 했는지 남긴다."""

    def __init__(self, *, approve: bool) -> None:
        self._approve = approve
        self.asked: list[str] = []

    def request_review(self, request: ReviewRequest) -> bool:
        self.asked.append(request.plugin_name)
        return self._approve


class _RefusingQuestions:
    """질문 카드 통로 — 이 하네스는 **대신 답하지 않는다.**

    `patch_fixtures`가 사람에게 물으면 그 런은 `not_run`으로 남고 그것이 정직한
    관측이다. 자동으로 «실행했습니다»를 내면 사람이 편집기를 열지 않았는데도
    앱이 다시 쏘게 되고, 0건 판정의 원인이 뒤섞인다.
    """

    def __init__(self) -> None:
        self.asked: list[str] = []

    def ask(self, request) -> str:
        self.asked.append(getattr(request, "prompt", "") or "")
        return ""


def _payload(execution) -> dict:
    try:
        return json.loads(execution.result.content)
    except (json.JSONDecodeError, TypeError):
        return {"raw": execution.result.content}


def _probe_channel(state_port) -> dict:
    """(a) 정상 왕복 · (b) 날조 대조군. (b)가 `ok`면 채널을 못 믿는다."""

    def one(path: str) -> dict:
        try:
            answer = state_port.query_state(path)
        except Exception as error:  # 판독 실패도 관측이다 — 예외를 삼키지 않는다
            return {"path": path, "raised": f"{type(error).__name__}: {error}"}
        if not isinstance(answer, dict):
            return {"path": path, "raw": repr(answer)[:200]}
        node = answer.get("node") or {}
        children = answer.get("children") or []
        return {
            "path": path,
            "ok": answer.get("ok"),
            "child_count": node.get("childCount") if isinstance(node, dict) else None,
            "children_returned": len(children) if isinstance(children, list) else None,
            "truncated": answer.get("truncated"),
            "names": [
                c.get("name")
                for c in (children if isinstance(children, list) else [])
                if isinstance(c, dict)
            ][:16],
        }

    live = one(LIVE_PATH)
    fabricated = one(FABRICATED_PATH)
    trustworthy = live.get("ok") is True and fabricated.get("ok") is not True
    return {
        "live": live,
        "fabricated_control": fabricated,
        "trustworthy": trustworthy,
        "verdict_ko": (
            "판독 채널 신뢰 가능 — 실재 경로는 ok, 날조 경로는 ok가 아니다."
            if trustworthy
            else (
                "판독 채널을 증거로 쓸 수 없다 — 날조 경로가 ok로 돌아왔거나 "
                "실재 경로가 응답하지 않았다. 여기서 멈춘다."
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, required=True, help="정본 패치 CSV 절대경로")
    parser.add_argument("--action", choices=["preview", "apply"], default="preview")
    parser.add_argument("--name-prefix-mode", choices=["group", "type"], default="group")
    parser.add_argument("--only-fids", default=None, help="쉼표로 구분한 FID 부분집합")
    parser.add_argument("--mode-overrides", default=None, help='JSON: {"<CSV타입>": "<콘솔모드>"}')
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--listen-port", type=int, default=9005)
    parser.add_argument("--plugin-import-dir", default=None)
    parser.add_argument(
        "--approve",
        action="store_true",
        help="승인 게이트를 통과시킨다; 없으면 콘솔에 아무것도 닿지 않는다",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="채널 검증만 하고 툴은 부르지 않는다",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.action == "apply" and not args.approve:
        print(
            "주의: --action apply 인데 --approve 가 없다 — 승인 게이트가 막으므로 "
            "콘솔에는 아무것도 닿지 않는다. 그대로 진행한다.",
            file=sys.stderr,
        )

    # **파일은 여기서 읽는다.** 서버는 경로를 받지 않는다.
    raw = args.csv.read_bytes()
    arguments: dict[str, object] = {
        "file_content_base64": base64.b64encode(raw).decode("ascii"),
        "action": args.action,
        "name_prefix_mode": args.name_prefix_mode,
    }
    if args.only_fids:
        arguments["only_fids"] = [int(v) for v in args.only_fids.split(",") if v.strip()]
    if args.mode_overrides:
        arguments["mode_overrides"] = json.loads(args.mode_overrides)

    out: dict = {
        "csv": str(args.csv),
        "action": args.action,
        "approve": args.approve,
        "local_file": {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw),
        },
    }

    approval = _RecordingApproval(approve=args.approve)
    review = _RecordingReview(approve=args.approve)
    questions = _RefusingQuestions()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=approval,
        plugin_import_dir=args.plugin_import_dir or None,
    )
    exit_code = 0
    try:
        out["probe"] = _probe_channel(stack.gate.state_port)
        if not out["probe"]["trustworthy"]:
            out["stopped"] = "channel_untrustworthy"
            exit_code = 2
        elif args.probe_only:
            out["stopped"] = "probe_only"
        else:
            deploy_pipeline = DeployPipeline(
                compile_checker=LuaCompileChecker(),
                ruleset=stack.ruleset,
                deploy_port=stack.gate,
                registry=stack.registry,
                audit=stack.audit,
                review_port=review,
            )
            registry = build_toolset(
                execution_port=stack.gate.execution_port,
                state_port=stack.gate.state_port,
                bundle_gate=stack.gate,
                deploy_pipeline=deploy_pipeline,
                question_port=questions,
            )
            execution = registry.dispatch(
                ToolCall(id="lxseq-m4", name="import_lxseq_patch", arguments=arguments)
            )
            payload = _payload(execution)
            out["is_error"] = execution.result.is_error
            out["awaited_human"] = execution.awaited_human
            out["payload"] = payload
            source = payload.get("source") or {}
            out["sha256_matches_local_file"] = (
                source.get("sha256") == out["local_file"]["sha256"]
                and source.get("byte_length") == out["local_file"]["byte_length"]
            )
            plan = payload.get("plan") or {}
            skipped = plan.get("skipped") or []
            kinds: dict[str, int] = {}
            for row in skipped:
                kind = str(row.get("kind"))
                kinds[kind] = kinds.get(kind, 0) + 1
            out["digest"] = {
                "runs": len(plan.get("runs") or []),
                "write_count_planned": plan.get("write_count_planned"),
                "skipped_total": len(skipped),
                "skipped_by_kind": kinds,
                "types_unresolved": [
                    row.get("csv_type")
                    for row in (payload.get("types") or {}).get("unresolved", [])
                ],
                "addresses": [
                    {
                        "index": run.get("index"),
                        "group": run.get("group"),
                        "console_type": run.get("console_type"),
                        "console_mode": run.get("console_mode"),
                        "address": run.get("address"),
                        "count": run.get("count"),
                        "channels_per_fixture": run.get("channels_per_fixture"),
                        "fids": run.get("fids"),
                    }
                    for run in (plan.get("runs") or [])
                ],
                "apply_runs": (payload.get("apply") or {}).get("runs"),
                "stopped_at": (payload.get("apply") or {}).get("stopped_at"),
                "summary_ko": payload.get("summary_ko"),
            }
            out["questions_asked"] = questions.asked
            out["approval_bundles_asked"] = len(approval.asked)
            out["deploy_reviews_asked"] = review.asked
            if execution.result.is_error:
                exit_code = 1
    finally:
        stack.stop()

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

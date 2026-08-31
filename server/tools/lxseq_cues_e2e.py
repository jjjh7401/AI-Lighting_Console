"""LX-SEQ 큐 라이브 하네스 (4단계 — 곡 큐 투입).

**검증 도구다 — 제품 코드가 아니다.** `server/tools/lxseq_presets_e2e.py` 의 형태를
승계한다: 실포트 조립, 우회 배선 0, `--approve` 없으면 콘솔에 아무것도 닿지 않는다.

## 형제와 달라지는 자리 둘 — 둘 다 명세서가 시킨 것

1. **`--limit` 은 행이 아니라 큐를 자른다.** `LX-SEQ-SPEC-v2.1.md:272` (§11.1 1열)
   이 「부분집합 금지 — 모든 큐에 최소 1행」이다. 행으로 자르면 경계에 걸린 큐가
   반쪽이 되어 발사기가 스스로 명세서를 어긴다. 선택된 큐의 행은 전부 포함한다.

2. **`LED-W` 그룹은 콘솔 명령 대상이 아니다.** 영상팀 큐다
   (`ma3-runbook.md:42` · `exec_data.py:18`). 과거 명령 유출 사고가 난 자리라
   [HARD] 로 취급한다.

   🔴 **판별기는 그룹명 하나다. `Note` 텍스트를 판별에 쓰지 않는다.**
   실측(2026-08-31, 정본 CSV 직독): 6행 중 **5행만** 「영상 큐 LW-0N 콜」 형태이고
   Q170 은 「영상 페이드아웃 동기」다. `LW-` 나 「콜」로 매칭하면 6 중 5만 걸리고
   **1행이 콘솔로 샌다** — 0/6 이면 눈에 띄지만 **5/6 은 그럴듯해서 안 띈다.**
   유출 사고가 났던 자리에서 가장 안 보이는 형태로 새는 것이다.
   `census.note_pattern_hits` 가 이 수를 매 실행마다 다시 재서 남긴다.

## 왜 `--sequence-name` 이 필수이고 파일명에서 유도하지 않는가

`map_cues` 는 시퀀스를 **이름으로** 찾거나 만드는데 그 이름이 **CSV 바이트에
없다**(곡·쇼 이름). 그래서 발사기가 인자로 받아 넘긴다.

🔴 **파일명에서 유도하지 않는다.** `LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv` 에서
`Sugar` 를 꺼내려면 명명 규약을 가정해야 하고, **그 이름은 콘솔에 영구히
남는다.** 틀린 이름이 쇼파일에 박히느니 인자를 요구하는 편이 싸다. 규약이 바뀌면
유도기는 조용히 틀린 이름을 만들고, 되돌리려면 콘솔에서 사람이 지워야 한다.

## 「안 나갔다」를 어떻게 재는가

스킵 플래그는 **코드가 자기 자신에 대해 하는 말**이다. 이 하네스는 승인 기록기가
담은 **밖으로 나갈 명령 묶음**을 스캔해 전송 목록에 그 그룹이 없음을 단언한다.
그리고 CSV 자체 인구조사를 **독립 분모**로 나란히 낸다 — 툴이 답한 수와 하네스가
센 수가 어긋나면 그 자체가 발견이다.

## 완료 판정 — 콘솔이 답한 두 수의 차이로 말한다

시퀀스 풀의 `childCount` 를 **발사 전에 찍고 발사 후 다시 찍는다.** 리드 실측
기준선(2026-08-31, 응답기 1.6.2): 발사 전 `1`. 성공하면 `2` 가 되고 새 시퀀스
안에 큐 자식이 정본 CSV 고유 큐 수(18)만큼 있어야 한다.

## 안 하는 것

- **큐 내용이 맞는지 확인하지 않는다.** 되읽기는 번호·이름까지만 열린다
  (`cue_monitor._cue_items`, 2026-08-02 LIVE-VERIFIED). 값은 안 온다.
- **바이트를 판정 근거로 쓰지 않는다.** 콘솔 거절이 길이가 아니라 내용에 달려
  있다(t72). 기록만 한다.
- **시퀀스 풀 밖을 건드리지 않는다.**
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

# 되읽기는 이미 LIVE-VERIFIED 된 판독기를 그대로 쓴다. 여기서 다시 구현하면
# 검증 안 된 두 번째 판독기가 생기고, 둘이 어긋날 때 어느 쪽이 맞는지 모른다.
from server.web.cue_monitor import SEQUENCE_PATH_TEMPLATE, _cue_items

assert_same_tree(__file__)

#: 판독 채널 날조 대조군. 있을 수 없는 경로라 **`ok=False` 가 정답**이다.
FABRICATED_PATH = "Patch/FixtureTypesZZZNotAThing/9999"

FIXTURES_PATH = "Patch/Stages/1/Fixtures"
GROUPS_PATH = "DataPool/Groups"
SEQUENCES_PATH = "DataPool/Sequences"

#: [HARD] 콘솔 명령 대상이 아닌 그룹. 판별은 **그룹명으로만** 한다 (모듈 docstring).
VIDEO_CALL_GROUP = "LED-W"

#: `Note` 를 판별기로 쓰면 안 되는 이유를 매 실행마다 재기 위한 대조 패턴.
#: 이 패턴이 잡는 수 < 그룹이 잡는 수 인 것이 요점이다.
NOTE_PATTERN_NOT_A_DISCRIMINATOR = "LW-"

#: 이 스킵 사유는 이름을 고정한다. 「미해석」·「알 수 없음」에 섞으면 진짜 결함이
#: 이 행들 뒤에 숨는다.
VIDEO_CALL_SKIP_REASON = "video_call_not_console"


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


def read_rows(csv_path: Path) -> list[dict]:
    """정본 CSV 를 행 사전 목록으로 읽는다. BOM 을 벗긴다."""
    return list(csv.DictReader(io.StringIO(csv_path.read_text(encoding="utf-8-sig"))))


def census(rows: list[dict]) -> dict:
    """정본 CSV 를 하네스가 **직접** 센다 — 툴 응답과 독립인 분모.

    89 를 하나로 뭉개지 않는다. 콘솔 대상과 영상 콜을 나란히 낸다.
    `note_pattern_hits` 는 「`Note` 로 매칭했으면 몇 건만 걸렸을까」이며,
    `video_call_rows` 보다 작다는 것이 `Note` 를 판별기로 쓰면 안 되는 증거다.
    """
    cue_numbers = list(dict.fromkeys(row["Q#"] for row in rows))
    video = [row for row in rows if row["Group"] == VIDEO_CALL_GROUP]
    note_hits = [
        row for row in video if NOTE_PATTERN_NOT_A_DISCRIMINATOR in (row.get("Note") or "")
    ]
    return dict(
        total_rows=len(rows),
        cue_count=len(cue_numbers),
        cue_numbers=cue_numbers,
        console_rows=len(rows) - len(video),
        video_call_rows=len(video),
        video_call_cues=sorted(dict.fromkeys(row["Q#"] for row in video)),
        video_call_skip_reason=VIDEO_CALL_SKIP_REASON,
        note_pattern=NOTE_PATTERN_NOT_A_DISCRIMINATOR,
        note_pattern_hits=len(note_hits),
        note_pattern_would_miss=len(video) - len(note_hits),
    )


def slice_by_cue(csv_path: Path, limit: int | None, *, skip: int = 0) -> bytes:
    """헤더 + `skip` 큐를 건너뛴 뒤의 `limit` **큐**. `limit` 가 `None` 이면 나머지 전부.

    자르는 단위가 행이 아니라 큐인 이유는 모듈 docstring 참조 — §11.1 이 큐의
    부분집합을 금지한다. 파생 CSV 를 만들지 않는 것은 형제와 같다: 출처가 정본
    시트를 가리켜야 한다.
    """
    text = csv_path.read_text(encoding="utf-8-sig")
    if limit is None and skip == 0:
        return text.encode("utf-8")
    rows = read_rows(csv_path)
    order = list(dict.fromkeys(row["Q#"] for row in rows))
    chosen = order[skip:] if limit is None else order[skip : skip + limit]
    keep = set(chosen)
    lines = [line for line in text.splitlines() if line.strip()]
    header = lines[0]
    body = [line for line, row in zip(lines[1:], rows, strict=True) if row["Q#"] in keep]
    return ("\n".join([header, *body]) + "\n").encode("utf-8")


def leaked_commands(bundles: list[tuple[str, ...]]) -> list[str]:
    """밖으로 나갈 명령 묶음에서 영상 콜 그룹이 언급된 명령을 찾는다.

    스킵 플래그가 아니라 **전송 목록**을 잰다. 0 이 정답이다.
    """
    return [
        command
        for bundle in bundles
        for command in bundle
        if VIDEO_CALL_GROUP.lower() in command.lower()
    ]


def tool_arguments(payload: str, action: str, sequence_name: str) -> dict:
    """`import_lxseq_cues` 에 넘길 인자. 스키마가 이 셋을 요구한다.

    `additionalProperties: False` 라 여분 키를 넣으면 거절된다.
    """
    return dict(
        file_content_base64=payload,
        action=action,
        sequence_name=sequence_name,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cue-csv", type=Path, required=True, help="정본 CUE-EX CSV 절대경로")
    parser.add_argument("--action", choices=["preview", "apply"], default="preview")
    parser.add_argument(
        "--sequence-name",
        required=True,
        help=(
            "콘솔에 찾거나 만들 시퀀스 이름(곡·쇼 이름). 필수 — 기본값 없다. "
            "파일명에서 유도하지 않는 이유는 모듈 docstring 참조"
        ),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="시트에서 앞 N 개 큐만 쓴다(행 아님). 기본 1 — 소수 먼저. 0 이면 통째",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="앞 N 개 큐를 건너뛴다. 이미 들어간 큐를 다시 쏘지 않기 위한 오프셋",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="기준 상태와 인구조사만 하고 툴은 부르지 않는다. 콘솔 쓰기 0",
    )
    parser.add_argument("--approve", action="store_true", help="없으면 콘솔에 아무것도 닿지 않는다")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    # [HARD] `--approve` 는 **행위**를 막는다. 승인 통로의 대답만 정하면 아무것도
    # 안 막는다 — 2026-08-25 사고가 정확히 그것이었다. 콘솔 스택을 세우기 **전에**
    # 거부한다.
    if args.action == "apply" and not args.approve:
        parser.error(
            "--action apply 는 --approve 를 요구한다. 승인 없이는 콘솔에 닿지 않는다. "
            "안전장치가 도는지 확인하려고 apply 를 쏘지 마라 — 확인과 사고가 같은 "
            "행위이면 그 절차가 사고다."
        )

    # `required=True` 는 **플래그 유무**만 본다 — `--sequence-name ""` 는 통과한다.
    # 툴은 그걸 거절하지만, 거절을 콘솔 왕복 뒤에 받느니 여기서 사유를 말한다.
    if not args.sequence_name.strip():
        parser.error(
            "--sequence-name 이 비었다. map_cues 는 시퀀스를 이름으로 찾거나 만드는데 "
            "그 이름이 CSV 바이트에 없다(곡·쇼 이름). "
            "파일명에서 유도하지 않는 이유: 그 이름은 콘솔에 영구히 남는다 — "
            "명명 규약을 가정해 틀린 이름을 쇼파일에 박느니 인자를 요구한다."
        )

    limit = None if args.limit == 0 else args.limit
    sheet = census(read_rows(args.cue_csv))
    out: dict[str, object] = dict(
        action=args.action,
        approve=args.approve,
        listen_port=args.listen_port,
        cue_csv=str(args.cue_csv),
        sequence_name=args.sequence_name,
        limit=limit,
        skip=args.skip,
        census=sheet,
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
        sequences_before = _state(stack.gate.state_port, SEQUENCES_PATH)
        trustworthy = (not fabricated["ok"]) and fixtures["ok"] and groups["ok"]
        out["baseline"] = dict(
            fabricated_control=fabricated,
            fixtures=fixtures,
            groups=groups,
            sequences=sequences_before,
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
            payload = base64.b64encode(slice_by_cue(args.cue_csv, limit, skip=args.skip)).decode(
                "ascii"
            )
            try:
                execution = registry.dispatch(
                    ToolCall(
                        id="lxc1",
                        name="import_lxseq_cues",
                        arguments=tool_arguments(payload, args.action, args.sequence_name),
                    )
                )
            except Exception as error:  # noqa: BLE001
                # 등재 전이면 여기로 온다. 뼈대는 그래도 baseline·인구조사·대조군을
                # 냈으므로 「아무것도 못 쟀다」와 구분되게 사유를 적는다.
                out["tool"] = None
                out["stopped"] = "tool_unavailable"
                out["tool_error"] = str(error)
                exit_code = 3
            else:
                out["tool"] = json.loads(execution.result.content)
                # 툴 응답을 생성 증거로 쓰지 않는다 — 명령이 성공한 것과 대상이
                # 바뀐 것은 다르다. 시퀀스 풀을 **독립적으로** 되읽는다.
                out["sequences_after"] = _state(stack.gate.state_port, SEQUENCES_PATH)
                sequence_no = out["tool"].get("sequence_no")
                if isinstance(sequence_no, int):
                    path = SEQUENCE_PATH_TEMPLATE.format(sequence_no=sequence_no)
                    out["sequence_after"] = _state(stack.gate.state_port, path)
                    try:
                        detail = stack.gate.state_port.query_state(path) or {}
                        cues = _cue_items(detail.get("children") or [])
                    except Exception as error:  # noqa: BLE001
                        out["cues_readback"] = dict(ok=False, detail=str(error))
                    else:
                        out["cues_readback"] = dict(
                            ok=True,
                            count=len(cues),
                            expected=sheet["cue_count"],
                            matches_expected=len(cues) == sheet["cue_count"],
                            cues=cues,
                        )

        leaked = leaked_commands(approval.asked)
        out["approval_requests"] = [list(bundle) for bundle in approval.asked]
        out["questions_asked"] = questions.asked
        # [HARD] 「스킵했다」가 아니라 「전송 목록에 없다」를 단언한다.
        out["video_call_containment"] = dict(
            group=VIDEO_CALL_GROUP,
            rows_in_sheet=sheet["video_call_rows"],
            commands_referencing_group=len(leaked),
            leaked_commands=leaked,
            no_command_emitted=not leaked,
        )
        if leaked:
            exit_code = max(exit_code, 4)
    finally:
        stack.stop()

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

"""t513 — t498 real_console.py 복사: LOVE ATTACK · 시퀀스 219 · 타임코드 19 (song 단계만).

t498 과 다른 점:
  1) 음원 = LOVE ATTACK(저장소 밖), 지시문 번호 = 219/19(t513 run0 실기 판독으로 빈 칸 확인).
  2) 전부-거절 모드(--approve 없음)의 쓰기 0 보장 두 겹:
     a) 앱이 거절 뒤 보내는 프로그래머 정리 `ClearAll`
        (server/web/session.py 「song-design-cleanup」)을 세션 레지스트리에서 가로채
        콘솔에 보내지 않고 기록만 한다(리드 지시: ClearAll 금지).
     b) 콘솔 링크의 실행 경로(_execute)를 막아, 어떤 명령이든 콘솔로 나가려 하면 보내지 않고
        `failed` 로 돌려주며 기록한다. 읽기(state/prop/props/introspect/ping)는 그대로 간다.
  3) 읽기 질의를 경로·자식 수와 함께 기록한다(queries.json) — 페이저 풀 응답 확인용.
  승인 모드(--approve)에서는 2b)만 꺼진다. 2a)는 두 모드 모두 켜져 있다 — 거절된 묶음은
  콘솔에 아무것도 보내지 않았으므로 정리할 프로그래머 내용이 없다(앱 본래 동작과 다른 점).

원문 머리말(t498):
t498 — t474 real_console.py 복사: 곡 지시만 시퀀스 211 · 타임코드 11 로 바꿨다
(presets 단계는 쓰지 않는다).
원문: t474 — M8 실기 1곡: 앱의 실제 콘솔 스택(build_console_stack)으로 Rain 을 대화 길로 반영한다.

두 단계:
  presets — 「기본 포지션 10개를 프리셋 21번부터 저장해줘」(풀 2 의 21~30 빈 칸, 감독 결정)
  song    — Rain 업로드 → 실제 DSP 분석 → 확인 →
            「디자인 큐 시트, 시퀀스 210, 프리셋 21번부터, 타임코드 9」

승인 규칙(이 파일의 안전장치):
  --approve 가 없으면 게이트 승인 요청을 **전부 거절**한다 → 쓰기 0(거절 뒤 앱이 보내는
  `ClearAll` 1줄 제외). 승인 요청의 명령은 <출력>/approval_request_N.txt 에 남는다.
  --approve <파일|폴더> 가 있으면, 승인 요청의 명령 목록이 그 파일(폴더면 그 안의
  approval_request_*.txt 중 하나)과 **글자까지 같을 때만** 승인한다.

쇼 저장: 세션 시작 백업은 끄고(attempt_session_backup=False), 게이트의 실행 직전 백업
(SaveShow)도 감독 결정(2026-09-27)으로 「보내지 않고 기록만」으로 바꿔 끼운다.

실행: uv run python .moai/reports/t498/real_console.py <presets|song> <출력> [--approve <경로>]
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from server.llm.types import ToolResult
from server.orchestrator.tools import ToolExecution
from server.safety.bootstrap import build_console_stack
from server.safety.console import ExecOutcome
from server.web.approval_bridge import ApprovalChannel
from server.web.question import UNANSWERED
from server.web.session import ChatSession

STEP = sys.argv[1]
OUT = Path(sys.argv[2])
APPROVE = Path(sys.argv[sys.argv.index("--approve") + 1]) if "--approve" in sys.argv else None
OUT.mkdir(parents=True, exist_ok=True)
RAIN = Path("/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3")

PRESET_INSTRUCTION = "기본 포지션 10개를 프리셋 21번부터 저장해줘"
SONG_INSTRUCTION = "디자인 큐 시트, 시퀀스 219, 프리셋 21번부터, 타임코드 19"
SONG_ANSWERS = [
    "확인",
    "우주",
    "우주 색 조합",
    "",
    "Ring In",
    "우주 컨셉 우선 배치",
    "템포 맞춤 (BPM 기준)",
]


class _PinnedApproval:
    def __init__(self, pinned: list[list[str]] | None):
        self.pinned = pinned
        self.requests: list[dict] = []

    def request_approval(self, request) -> bool:
        commands = list(request.commands)
        decision = self.pinned is not None and commands in self.pinned
        self.requests.append({"commands": commands, "approved": decision})
        return decision

    def bind(self, *_a, **_kw):
        return None


class _Questions:
    def __init__(self, answers):
        self.answers = list(answers)
        self.log = []

    def ask(self, request, **_kw):
        text = getattr(request, "question", None) or getattr(request, "prompt", None)
        options = [getattr(o, "label", str(o)) for o in (getattr(request, "options", ()) or ())]
        if self.answers:
            answer = self.answers.pop(0)
        elif "이 매핑 사용" in options:
            answer = "이 매핑 사용"
        elif any(str(label).startswith("승인") for label in options):
            answer = "승인"
        else:
            answer = UNANSWERED
        self.log.append({"question": text, "options": options[:20], "answer": answer})
        return answer

    def bind(self, *_a, **_kw):
        return None


class _Provider:
    def complete(self, *_a, **_kw):  # pragma: no cover
        raise AssertionError("이 경로는 모델을 부르지 않는다")


pinned = None
if APPROVE is not None:
    files = sorted(APPROVE.glob("approval_request_*.txt")) if APPROVE.is_dir() else [APPROVE]
    pinned = [path.read_text("utf-8").splitlines() for path in files]
approval = _PinnedApproval(pinned)
stack = build_console_stack(
    send_port=8000,
    receive_port=9005,
    approval_port=approval,
    audit_dir=OUT / "audit",
    attempt_session_backup=False,
)
#: 감독 결정(2026-09-27): 자동 쇼 저장(SaveShow)은 끄고, 저장은 끝에 따로 묻는다.
#: 게이트의 실행 직전 백업 동작을 「보내지 않고 기록만」으로 바꿔 끼운다 — 앱 본래 동작과 다른 점.
skipped_backups: list[str] = []
stack.backup._backup_action = lambda: skipped_backups.append("SaveShow skipped (supervisor)")

#: t513 — 읽기 질의 기록(경로 · ok · 자식 수).
queries: list[dict] = []
for _name in ("query_state", "query_property", "query_properties", "enumerate_fields"):
    _orig = getattr(stack.link, _name)

    def _logged(*args, _orig=_orig, _name=_name, **kwargs):
        try:
            reply = _orig(*args, **kwargs)
        except Exception as error:  # noqa: BLE001 — 기록 후 그대로 던진다
            queries.append({"op": _name, "args": [str(a) for a in args], "error": str(error)})
            raise
        queries.append(
            {
                "op": _name,
                "args": [str(a) for a in args],
                "ok": reply.get("ok") if isinstance(reply, dict) else None,
                "children": len(reply.get("children", []))
                if isinstance(reply, dict) and isinstance(reply.get("children"), list)
                else None,
            }
        )
        return reply

    setattr(stack.link, _name, _logged)

#: t513 — 전부-거절 모드: 콘솔 실행 경로 봉쇄(2b).
blocked_exec: list[str] = []
if pinned is None:

    def _blocked_execute(command, **_kw):
        blocked_exec.append(command)
        return ExecOutcome(status="failed", detail="t513 deny-all: not sent to console")

    stack.link._execute = _blocked_execute
sent: list[dict] = []
replies: list[dict] = []
try:
    session = ChatSession(
        gate=stack.gate,
        provider=_Provider(),
        system_prefix="PREFIX",
        audit=stack.audit,
        send_event=sent.append,
        approval_channel=ApprovalChannel(timeout_seconds=5.0),
    )
    #: t513 — 거절 뒤 프로그래머 정리 ClearAll 가로채기(2a).
    intercepted: list[list[str]] = []
    _inner_dispatch = session._registry.dispatch

    def _dispatch(call, *args, **kwargs):
        if call.id == "song-design-cleanup":
            intercepted.append(list(call.arguments.get("commands", [])))
            return ToolExecution(
                ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content="t513 deny-all: cleanup not sent",
                )
            )
        return _inner_dispatch(call, *args, **kwargs)

    session._registry.dispatch = _dispatch
    if STEP == "presets":
        questions = _Questions([])
        session._question_channel = questions
        replies.append(session.run_instruction(PRESET_INSTRUCTION))
    elif STEP == "song":
        questions = _Questions(SONG_ANSWERS)
        session._question_channel = questions
        data = RAIN.read_bytes()
        replies.append(
            session.upload_song_audio(RAIN.name, "audio/mpeg", base64.b64encode(data).decode())
        )
        replies.append(session.analyse_song_audio())
        replies.append(session.run_instruction(SONG_INSTRUCTION))
    else:
        raise SystemExit(f"unknown step {STEP!r}")
finally:
    stack.stop()

(OUT / "approval_requests.json").write_text(
    json.dumps(approval.requests, ensure_ascii=False, indent=1), "utf-8"
)
for index, request in enumerate(approval.requests, start=1):
    (OUT / f"approval_request_{index}.txt").write_text(
        "\n".join(request["commands"]) + "\n", "utf-8"
    )
(OUT / "cards.json").write_text(json.dumps(questions.log, ensure_ascii=False, indent=1), "utf-8")
(OUT / "replies.json").write_text(
    json.dumps([r.get("text") for r in replies], ensure_ascii=False, indent=1), "utf-8"
)
(OUT / "events.json").write_text(
    json.dumps(sent, ensure_ascii=False, indent=1, default=str), "utf-8"
)
(OUT / "skipped_backups.json").write_text(json.dumps(skipped_backups), "utf-8")
(OUT / "queries.json").write_text(json.dumps(queries, ensure_ascii=False, indent=1), "utf-8")
(OUT / "blocked_exec.json").write_text(
    json.dumps(blocked_exec, ensure_ascii=False, indent=1), "utf-8"
)
(OUT / "intercepted_cleanup.json").write_text(
    json.dumps(intercepted, ensure_ascii=False, indent=1), "utf-8"
)
print(f"blocked_exec={len(blocked_exec)} intercepted_cleanup={intercepted} queries={len(queries)}")
print(
    f"skipped_saveshow={len(skipped_backups)} "
    f"step={STEP} approve={'pinned' if pinned is not None else 'deny-all'} "
    f"approval_requests={len(approval.requests)} "
    f"approved={sum(1 for r in approval.requests if r['approved'])} "
    f"lines={[len(r['commands']) for r in approval.requests]}"
)
for reply in replies:
    print("REPLY:", (reply.get("text") or "")[:1500])

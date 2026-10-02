"""t501 AC-016 — t498 `real_console.py` 일반화. 곡 파일명·시퀀스·타임코드를
인자로 받는다(presets 단계는 t498 때 이미 다 썼으므로 이 스크립트엔 없다 —
풀 2 의 21~30 은 지금 콘솔에 이미 있다, `.moai/reports/t501/ac016_readonly_
before.txt`).

승인 규칙(이 파일의 안전장치, t498 과 바이트 동일 로직):
  --approve 가 없으면 게이트 승인 요청을 **전부 거절**한다 → 쓰기 0(거절 뒤
  앱이 보내는 `ClearAll` 1줄 제외). 승인 요청의 명령은 <출력>/approval_
  request_N.txt 에 남는다.
  --approve <파일|폴더> 가 있으면, 승인 요청의 명령 목록이 그 파일(폴더면
  그 안의 approval_request_*.txt 중 하나)과 **글자까지 같을 때만** 승인한다.

쇼 저장: 세션 시작 백업은 끄고(attempt_session_backup=False), 게이트의 실행
직전 백업(SaveShow)도 t498 때의 감독 결정(2026-09-27)을 그대로 따라
「보내지 않고 기록만」으로 바꿔 끼운다.

🔴 이 스크립트는 **실행하지 않는다** — 배차서 지시(ABSOLUTELY NO REAL CONSOLE
CONTACT). 레인이 실기에서 돌린다: 먼저 전부-거절(--approve 없이)로 승인
목록만 뜨고 README.md 절차대로 classify_diff.py 로 리허설과 대조한 뒤에만
--approve 로 재실행한다.

실행(레인 전용): uv run python .moai/reports/t501/ac016/real_song.py \
      <song-file-name> <sequence> <timecode> <출력> [--approve <경로>]
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from server.safety.bootstrap import build_console_stack
from server.web.approval_bridge import ApprovalChannel
from server.web.question import UNANSWERED
from server.web.session import ChatSession

SONG_FILE = sys.argv[1]
SEQUENCE = sys.argv[2]
TIMECODE = sys.argv[3]
OUT = Path(sys.argv[4])
APPROVE = Path(sys.argv[sys.argv.index("--approve") + 1]) if "--approve" in sys.argv else None
OUT.mkdir(parents=True, exist_ok=True)
AUDIO_ROOT = Path("/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music")
AUDIO = AUDIO_ROOT / SONG_FILE

SONG_INSTRUCTION = f"디자인 큐 시트, 시퀀스 {SEQUENCE}, 프리셋 21번부터, 타임코드 {TIMECODE}"
#: t498/t499/M7 과 바이트 동일한 고정 인터뷰 답변 목록(재사용, 다시 안 적음).
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
#: t498 감독 결정(2026-09-27)과 동일: 자동 쇼 저장(SaveShow)은 끄고, 저장은
#: 콘솔에서 감독이 복사본에 직접 한다. 게이트의 실행 직전 백업 동작을
#: 「보내지 않고 기록만」으로 바꿔 끼운다 — 앱 본래 동작과 다른 점.
skipped_backups: list[str] = []
stack.backup._backup_action = lambda: skipped_backups.append("SaveShow skipped (supervisor)")
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
    questions = _Questions(SONG_ANSWERS)
    session._question_channel = questions
    data = AUDIO.read_bytes()
    mime = "audio/wav" if AUDIO.suffix.lower() == ".wav" else "audio/mpeg"
    replies.append(session.upload_song_audio(AUDIO.name, mime, base64.b64encode(data).decode()))
    replies.append(session.analyse_song_audio())
    replies.append(session.run_instruction(SONG_INSTRUCTION))
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
print(
    f"song={SONG_FILE} seq={SEQUENCE} tc={TIMECODE} "
    f"skipped_saveshow={len(skipped_backups)} "
    f"approve={'pinned' if pinned is not None else 'deny-all'} "
    f"approval_requests={len(approval.requests)} "
    f"approved={sum(1 for r in approval.requests if r['approved'])} "
    f"lines={[len(r['commands']) for r in approval.requests]}"
)
for reply in replies:
    print("REPLY:", (reply.get("text") or "")[:1500])

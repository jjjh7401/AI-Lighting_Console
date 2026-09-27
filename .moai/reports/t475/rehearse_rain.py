"""t475 — M8 사전 리허설: Rain 을 대화 길(main 파이프라인) 끝까지 돌려 콘솔 명령 전체를 파일로 뜬다.

실제 오디오(src/sample music/Rain.mp3, 주 체크아웃의 비추적 파일) → upload_song_audio →
analyse_song_audio(실제 DSP) → 확인 카드 「확인」(전 구간 채택) → 디자인 지시문(구간 미기재 →
확정 구간 사용) → 연출 인터뷰 → 리뷰 승인 → 게이트 승인 → _song_finalize → 가짜 콘솔.

콘솔 쓰기 0: 명령은 in-process FakeConsole(server/tests/test_safety_gate.py)이 받는다.
그룹 풀은 t379 실측 이름(rig.py 주석)에 **번호를 지어 붙인** 가짜 주소록이다 — 실기 번호 아님.

실행: uv run python .moai/reports/t475/rehearse_rain.py <rain.mp3 경로> <출력 디렉터리>
"""

from __future__ import annotations

import base64
import json
import re
import sys
import tempfile
from pathlib import Path

from server.llm.types import ToolResult
from server.orchestrator.tools import ToolExecution
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.tests.test_safety_gate import FakeConsole
from server.web.approval_bridge import ApprovalChannel
from server.web.question import UNANSWERED
from server.web.session import ChatSession

AUDIO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

INSTRUCTION = "디자인 큐 시트, 시퀀스 210, 프리셋 21번부터, 타임코드 9"
#: 확인 카드 1장 + 인터뷰 6장. 그 밖의 카드(재질의·리뷰)는 아래 채널이 선택지로 답한다.
ANSWERS = [
    "확인",
    "우주",
    "우주 색 조합",
    "",  # Q2B_COLOR_USAGE 기본 수락
    "Ring In",
    "우주 컨셉 우선 배치",
    "템포 맞춤 (BPM 기준)",
]

#: t379 실측 그룹 이름(server/design/rig.py 83-85행 주석). 번호는 지어낸 것.
T379_GROUPS = [
    "KEY",
    "FOH",
    "BACK",
    "SIDE-L",
    "SIDE-R",
    "SIDE-ALL",
    "MOVER-U",
    "MOVER-D",
    "MOVER-ALL",
    "WASH-U",
    "WASH-D",
    "WASH-ALL",
    "BLIND",
    "STROBE",
    "HAZE",
    "ALL",
    "ODD",
    "EVEN",
]
GROUPS = {"ok": True, "children": [{"i": 1 + i, "name": n} for i, n in enumerate(T379_GROUPS)]}
POSITION_POOL = {
    "ok": True,
    "children": [{"i": 21 + i, "name": name} for i, name in enumerate(BASIC_POSITION_SEQUENCE)],
}


_STORE_CUE = re.compile(r"^Store Sequence (\d+) Cue ([\d.]+) '([^']*)'")
_SET_CUE = re.compile(r"^Set Cue ([\d.]+) Sequence (\d+) Property '(\w+)' '?([^']*)'?$")
_STORE_TC = re.compile(r"^Store Timecode (\d+)$")


class _Console(FakeConsole):
    """빈 슬롯은 실기처럼 'path segment not found' 로 답한다.

    되읽기용 최소 저장 모델: 이 콘솔이 **받은 명령 문자열**에서 Store Sequence/Cue,
    Set Cue … Property, Store Timecode 만 파싱해 되돌려 준다. 따라서 되읽기 통과는
    「명령이 검증기가 기대하는 값을 담고 있다」는 자기 일관성의 증거일 뿐이고,
    실기 콘솔이 그 명령을 받아들이는지의 증거가 아니다(그건 t474).
    """

    def __init__(self):
        super().__init__()
        self.queried: list[str] = []
        self.sequences: dict[str, dict[str, dict]] = {}
        self.timecodes: set[str] = set()

    def execute(self, command: str):
        outcome = super().execute(command)
        if m := _STORE_CUE.match(command):
            seq, cue, name = m.groups()
            self.sequences.setdefault(seq, {})[cue] = {"no": float(cue), "name": name}
        elif m := _SET_CUE.match(command):
            cue, seq, prop, value = m.groups()
            self.sequences.setdefault(seq, {}).setdefault(cue, {"no": float(cue)})[prop] = value
        elif m := _STORE_TC.match(command):
            self.timecodes.add(m.group(1))
        return outcome

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path == "DataPool/PresetPools/2":
            return POSITION_POOL
        if path == "DataPool/Groups":
            return GROUPS
        head, _, number = path.rpartition("/")
        if head.endswith("Sequences") and number in self.sequences:
            return {
                "ok": True,
                "name": f"Sequence {number}",
                "children": list(self.sequences[number].values()),
            }
        if head.endswith("Timecodes") and number in self.timecodes:
            return {"ok": True, "name": f"Timecode {number}", "i": int(number)}
        raise RuntimeError(f"path segment not found: {path}")


class _Questions:
    def __init__(self, answers):
        self.answers = list(answers)
        self.log = []

    def ask(self, request, **_kw):
        header = getattr(request, "header", None) or getattr(request, "title", None)
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
        self.log.append(
            {
                "type": type(request).__name__,
                "header": header,
                "question": text,
                "options": options[:20],
                "answer": answer,
            }
        )
        return answer

    def bind(self, *_a, **_kw):
        return None


class _Approval:
    def __init__(self):
        self.requests = []

    def request_approval(self, request):
        self.requests.append(request)
        return True

    def bind(self, *_a, **_kw):
        return None


class _Spatial:
    """좌표 판독만 대역(writegate 시험과 같은 두 기구) — 나머지는 실제 레지스트리."""

    def __init__(self, inner):
        self._inner = inner
        self.dispatched = []

    def definitions(self):
        return self._inner.definitions()

    def dispatch(self, call, context=None):
        self.dispatched.append(call.name)
        if call.name == "get_spatial_context":
            return ToolExecution(
                ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        {
                            "fixtures": [
                                {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
                                {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
                            ],
                            "coverage": {"complete": True},
                        }
                    ),
                )
            )
        if context is None:
            return self._inner.dispatch(call)
        return self._inner.dispatch(call, context)


class _Provider:
    def complete(self, *_a, **_kw):  # pragma: no cover
        raise AssertionError("이 경로는 모델을 부르지 않는다")


#: 조립기 산출(번들)을 그대로 붙잡는다 — 명령 생성기로 가는 값을 가로채지 않고 기록만 한다.
_captured: list[object] = []
_original_reviewed = ChatSession._reviewed_song_commands


def _recording_reviewed(self, composition, **kwargs):
    _captured.append(composition)
    return _original_reviewed(self, composition, **kwargs)


ChatSession._reviewed_song_commands = _recording_reviewed

tmp = Path(tempfile.mkdtemp(prefix="t475-"))
console = _Console()
audit = AuditLog(tmp / "audit")
approval = _Approval()
gate = SafetyGate(console=console, audit=audit, approval_port=approval)
sent: list[dict] = []
session = ChatSession(
    gate=gate,
    provider=_Provider(),
    system_prefix="PREFIX",
    audit=audit,
    send_event=sent.append,
    approval_channel=ApprovalChannel(timeout_seconds=1.0),
)
session._registry = _Spatial(session._registry)
questions = _Questions(ANSWERS)
session._question_channel = questions

data = AUDIO.read_bytes()
replies = [
    session.upload_song_audio(AUDIO.name, "audio/mpeg", base64.b64encode(data).decode()),
    session.analyse_song_audio(),
]
analysis = session.song_analysis
replies.append(session.run_instruction(INSTRUCTION))

(OUT / "console_commands_sent.txt").write_text("\n".join(console.executed) + "\n", "utf-8")
previews = [event for event in sent if event.get("type") == "execution_preview"]
if previews:
    (OUT / "console_commands_approved.txt").write_text(
        "\n".join(row["command"] for row in previews[-1]["commands"]) + "\n", "utf-8"
    )
(OUT / "cards.json").write_text(json.dumps(questions.log, ensure_ascii=False, indent=1), "utf-8")
(OUT / "replies.json").write_text(
    json.dumps([r.get("text") for r in replies], ensure_ascii=False, indent=1), "utf-8"
)
(OUT / "events.json").write_text(
    json.dumps(sent, ensure_ascii=False, indent=1, default=str), "utf-8"
)
(OUT / "analysis.json").write_text(
    json.dumps(
        None
        if analysis is None
        else {
            "sha256": analysis.source_sha256,
            "bpm": analysis.bpm.bpm,
            "bpm_source": analysis.bpm.source,
            "sections": [
                {
                    "i": s.index,
                    "label": s.label,
                    "start_ms": s.start_ms,
                    "end_ms": s.end_ms,
                    "d": s.d_level,
                    "selected": s.selected,
                }
                for s in analysis.sections
            ],
        },
        ensure_ascii=False,
        indent=1,
    ),
    "utf-8",
)
bundle_rows = []
if _captured and _captured[-1].bundle is not None:
    for cue in _captured[-1].bundle.cues:
        bundle_rows.append(
            {
                "cue": cue.cue_number,
                "kind": cue.kind,
                "name": cue.cue_name,
                "d": cue.d_level,
                "dimmer": cue.dimmer.to_dict()
                if hasattr(cue.dimmer, "to_dict")
                else str(cue.dimmer),
                "position": cue.position.to_dict()
                if hasattr(cue.position, "to_dict")
                else str(cue.position),
                "color": cue.color.to_dict()
                if getattr(cue, "color", None) is not None and hasattr(cue.color, "to_dict")
                else str(getattr(cue, "color", None)),
                "mib": cue.mib.to_dict() if getattr(cue, "mib", None) is not None else None,
                "pre_drop_from": getattr(cue, "pre_drop_from", None),
                "accent": cue.accent_fixture.to_dict() if cue.accent_fixture else None,
                "start_ms": cue.timing.start_ms,
                "fade": cue.fade_seconds,
            }
        )
    (OUT / "bundle_cues.json").write_text(
        json.dumps(
            {
                "cues": bundle_rows,
                "arc_notes": list(_captured[-1].bundle.arc_notes),
            },
            ensure_ascii=False,
            indent=1,
            default=str,
        ),
        "utf-8",
    )
(OUT / "queries.txt").write_text("\n".join(console.queried) + "\n", "utf-8")
print(
    f"commands={len(console.executed)} approvals={len(approval.requests)} "
    f"cards={len(questions.log)} events={len(sent)} dispatched={session._registry.dispatched}"
)
for reply in replies:
    print("REPLY:", (reply.get("text") or "")[:800])

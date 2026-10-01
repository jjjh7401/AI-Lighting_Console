"""카드 t501 M3⑤ — AC-LDRENDER-001 오프라인 판독, t499 8곡 재현 + 실기 그룹.

t499 `rehearse_song.py`(대화 길 끝까지, FakeConsole)의 일반화 — 다른 점은 **DSP를
다시 돌리지 않는다**는 것 하나뿐이다. 이 워크트리에는 원곡 오디오(`src/sample
music/*.mp3`, 주 체크아웃의 비추적 파일)가 없어 `upload_song_audio`/
`analyse_song_audio`를 부를 수 없다(코드 판독 + `find` 실측, 이 트리에 mp3/wav
0건 — M3 progress.md §Gaps 참조). 대신 t499 가 이미 DSP 로 측정해 커밋해 둔
`.moai/reports/t499/runs/<곡>/analysis.json`(BPM·구간 D레벨 — 실측값, 지어낸
값 아님)을 `ConfirmedSongAnalysis`/`BpmResolution` 으로 직접 재구성해
`session._song_analysis`/`_song_bpm` 에 꽂는다. `analyse_song_audio()`가 하는
일은 "DSP → 카드 → 사람 확정"인데, 이 확정 값 자체(각 섹션의 d_level·선택 여부)는
analysis.json 에 이미 있으므로 이 우회는 **DSP 를 건너뛰는 것이지 확정을 지어내는
것이 아니다**.

이 치환이 M3 의 판정에 영향을 주지 않는 이유(코드 판독, M3.md 참조): 디머
렌더링(`_role_dimmer_value_lines`)은 `layer_mapping`+`cue.dimmer.role_pct`
에서만 역할별 값을 읽고, `cue.dimmer.role_pct`는 `_dimmer_data`가 ``key``/``back``
둘만 채운다(side/wash/mover 는 M3 가 막아 둔 미해결 결정) — 즉 송신 디머 값은
곡 내용(BPM·구간 D레벨)에 의존하지만 **역할 집합**에는 의존하지 않는다. 이
대체가 재현하는 것은 "그 곡의 BPM/구간이 실제로 무엇인지"이지 "디머 렌더링 로직이
무엇을 하는지"가 아니므로, 판정 결과(LIT 층 수)는 analysis.json 경유든 실제 DSP
경유든 같다.

입력: `.moai/reports/t499/runs/<곡>/analysis.json` (8개, t499 커밋).
출력: 표준출력 + `.moai/reports/t501/ac001_8songs.json` + `.moai/reports/t501/ac001_8songs.txt`.

실행: uv run python .moai/reports/t501/measure_ac001_8songs.py
콘솔 접촉: 0건(in-process FakeConsole, t499 와 동일).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import tempfile
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path

from server.design.ldrender_gate import BLACKOUT_KIND, MIB_PREMOVE_KIND, SectionCue, evaluate
from server.design.profile import BpmResolution
from server.design.rig import resolve_layer_role
from server.llm.types import ToolResult
from server.orchestrator.tools import ToolExecution
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.tests.test_safety_gate import FakeConsole
from server.web.approval_bridge import ApprovalChannel
from server.web.question import UNANSWERED, ConfirmedSongAnalysis, ConfirmedSongSection
from server.web.session import ChatSession, SongAudioUpload

HERE = Path(__file__).resolve().parent
T499 = HERE.parent / "t499"
T498 = HERE.parent / "t498"

# t499/readout.py 는 패키지가 아니라 독립 스크립트라 sys.path 삽입 뒤에만 임포트
# 가능하다(위 server.* 임포트와 달리 이 한 줄만 경로 조작에 의존한다) — 수정
# 없이 재사용만 한다(M1 선례, ldrender_gate.py 모듈 독스트링과 같은 경계).
sys.path.insert(0, str(T499))
import readout as _readout  # noqa: E402

INSTRUCTION = "디자인 큐 시트, 시퀀스 211, 프리셋 21번부터, 타임코드 11"
#: t499 ANSWERS 에서 첫 "확인" 하나를 뺐다 — 그 답은 `analyse_song_audio()`의
#: 구간 확정 카드용이었는데, 이 재현은 그 카드 자체를 안 띄운다(DSP 를 다시
#: 돌리지 않고 `ConfirmedSongAnalysis`를 직접 꽂는다 — 머리말 참조). 그대로
#: 두면 다음 카드(Q1 컨셉)가 "확인"을 받아 답 전체가 한 칸씩 밀린다(실측:
#: 2026-10-01, "연출 답변을 해석하지 못해 큐를 쓰지 않았습니다" 응답으로 발견).
ANSWERS = [
    "우주",
    "우주 색 조합",
    "",
    "Ring In",
    "우주 컨셉 우선 배치",
    "템포 맞춤 (BPM 기준)",
]

#: t498 run0_readonly_state.txt:16 실기 판독 — rehearse_song.py REAL_GROUPS 와 바이트 동일.
REAL_GROUPS = [
    (1, "ALL"),
    (2, "KEY"),
    (3, "FOH"),
    (4, "BACK"),
    (5, "SIDE-L"),
    (6, "SIDE-R"),
    (7, "SIDE-ALL"),
    (8, "WASH-U"),
    (9, "WASH-D"),
    (10, "WASH-ALL"),
    (11, "MOVER-U"),
    (12, "MOVER-D"),
    (13, "MOVER-ALL"),
    (14, "BLIND"),
    (15, "STROBE"),
    (16, "HAZE"),
    (17, "ODD"),
    (18, "EVEN"),
]
GROUPS = {"ok": True, "children": [{"i": i, "name": n} for i, n in REAL_GROUPS]}
POSITION_POOL = {
    "ok": True,
    "children": [{"i": 21 + i, "name": name} for i, name in enumerate(BASIC_POSITION_SEQUENCE)],
}
_REAL_LIST = T498 / "run3_rain_real_denyall/approval_request_1.txt"
REAL_FIDS = [
    int(x)
    for x in _REAL_LIST.read_text("utf-8")
    .splitlines()[1]
    .split(";")[0]
    .removeprefix("Fixture ")
    .split(" + ")
]
assert len(REAL_FIDS) == 86, len(REAL_FIDS)

_STORE_CUE = re.compile(r"^Store Sequence (\d+) Cue ([\d.]+) '([^']*)'")
_SET_CUE = re.compile(r"^Set Cue ([\d.]+) Sequence (\d+) Property '(\w+)' '?([^']*)'?$")
_STORE_TC = re.compile(r"^Store Timecode (\d+)$")


class _Console(FakeConsole):
    """t499 rehearse_song.py `_Console` 과 바이트 동일(복사 — import 불가, 그 파일은
    모듈 수준에서 `sys.argv`를 읽어 임포트 시점에 죽는다)."""

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
        options = [getattr(o, "label", str(o)) for o in (getattr(request, "options", ()) or ())]
        if self.answers:
            answer = self.answers.pop(0)
        elif "이 매핑 사용" in options:
            answer = "이 매핑 사용"
        elif any(str(label).startswith("승인") for label in options):
            answer = "승인"
        else:
            answer = UNANSWERED
        self.log.append({"options": options[:20], "answer": answer})
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
                                {
                                    "fid": fid,
                                    "name": f"FID {fid}",
                                    "x": float(k),
                                    "y": 0.0,
                                    "z": 6.0,
                                }
                                for k, fid in enumerate(REAL_FIDS)
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


def _confirmed_analysis_from_t499(analysis_path: Path, song_name: str) -> ConfirmedSongAnalysis:
    """t499 analysis.json(DSP 실측 BPM·구간) → `ConfirmedSongAnalysis` 재구성.

    DSP 를 다시 돌리지 않는다 — 이미 사람이 확정한(t499 rehearse_song.py 의
    `analyse_song_audio()` 호출이 기록한) 값을 그대로 옮긴다. ``selected`` 가
    False 인 구간도 보존한다(원본 확정 기록과 바이트 동일한 구조).
    """
    data = json.loads(analysis_path.read_text("utf-8"))
    sections = tuple(
        ConfirmedSongSection(
            index=s["i"],
            label=s["label"],
            start_ms=s["start_ms"],
            end_ms=s["end_ms"],
            d_level=s["d"],
            selected=s["selected"],
        )
        for s in data["sections"]
    )
    resolution = BpmResolution(
        bpm=data["bpm"],
        source=data["bpm_source"],
        reason="t501 — t499 analysis.json 재사용(DSP 재실행 없음)",
    )
    return ConfirmedSongAnalysis(
        source_sha256=data["sha256"],
        source_file_name=song_name,
        confirmed_at=datetime.now(UTC).isoformat(),
        bpm=resolution,
        sections=sections,
    ), resolution


def rehearse(song_name: str, analysis_path: Path) -> dict:
    _captured: list[object] = []
    _original_reviewed = ChatSession._reviewed_song_commands

    def _recording_reviewed(self, composition, **kwargs):
        _captured.append(composition)
        return _original_reviewed(self, composition, **kwargs)

    ChatSession._reviewed_song_commands = _recording_reviewed
    try:
        tmp = Path(tempfile.mkdtemp(prefix="t501-"))
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

        record, resolution = _confirmed_analysis_from_t499(analysis_path, song_name)
        fake_bytes = song_name.encode("utf-8")
        session._song_audio = SongAudioUpload(
            file_name=song_name,
            mime_type="audio/mpeg",
            content_base64=base64.b64encode(fake_bytes).decode(),
            sha256=hashlib.sha256(fake_bytes).hexdigest(),
            byte_length=len(fake_bytes),
        )
        session._song_analysis = record
        session._song_bpm = resolution

        reply = session.run_instruction(INSTRUCTION)

        commands = list(console.executed)
        bundle_cues = list(_captured[-1].bundle.cues) if _captured and _captured[-1].bundle else []
        return {
            "song": song_name,
            "commands": commands,
            "bundle_cues": bundle_cues,
            "reply": reply,
            "cards": questions.log,
            "n_captured": len(_captured),
        }
    finally:
        ChatSession._reviewed_song_commands = _original_reviewed


def _kind_for_gate(cue) -> str:
    """ComposedCue → ldrender_gate 의 ``kind`` 어휘(``section``/``blackout``/
    ``mib_premove``) — M7(아직 배선 안 됨)이 할 변환을 이 측정에서 선취한다.
    `ComposedCue.kind` 자체는 "blackout"을 모른다(``dimmer.blackout`` 플래그로만
    구분) — `BLACKOUT_KIND` 상수가 기대하는 문자열로 옮기는 것은 이 스크립트의
    추론이고, M7 실제 배선이 아니다(progress.md §Gaps 명시)."""
    if cue.kind == MIB_PREMOVE_KIND:
        return MIB_PREMOVE_KIND
    if getattr(cue.dimmer, "blackout", False):
        return BLACKOUT_KIND
    return "section"


def _gate_cues_from_commands(commands: list[str], bundle_cues: list) -> list[SectionCue]:
    """송신 명령 → `ldrender_gate.SectionCue` 목록. t499 readout.py 의
    `parse_sent`/`apply`(수정 없이 재사용)로 큐별 선택을 펼치고, 역할은
    `rig.resolve_layer_role`(production 과 같은 함수)로 그룹 이름 → 역할 변환한다
    — readout.py 자신의 8-way RIG 그룹(§M1 progress.md 가 이미 "다른 셈법"이라고
    명시)이 아니라 REQ-001 이 실제로 쓰는 7-역할 어휘로 센다."""
    cues_by_number = {cue.cue_number: cue for cue in bundle_cues}
    state: dict[int, dict] = {}
    gate_cues: list[SectionCue] = []
    for row in _readout.parse_sent(commands):
        applied = _readout.apply(row["lines"], state)
        cue_no_str = row["no"]
        try:
            cue_no_float = float(cue_no_str)
        except ValueError:
            cue_no_float = None
        composed = cues_by_number.get(cue_no_float)
        kind = _kind_for_gate(composed) if composed is not None else "section"
        role_view: dict[str, list[dict]] = OrderedDict()
        for fid, fid_state in state.items():
            row_info = _readout.FID_TABLE.get(fid)
            if row_info is None:
                continue
            role = resolve_layer_role(row_info["group"])
            if role is None:
                continue
            role_view.setdefault(role, []).append(dict(fid_state))
        gate_cues.append(
            SectionCue(
                cue_no=cue_no_str,
                name=row["name"],
                kind=kind,
                role_view=role_view,
                sent_rgb=tuple(sorted(applied["rgbs"])),
                group_lines=tuple(applied["group_lines"]),
            )
        )
    return gate_cues


def main() -> None:
    analysis_files = sorted((T499 / "runs").glob("*/analysis.json"))
    # Rain_first 는 t499 자신이 재현 시험(2회차)용으로 남긴 중복 — 8곡 집합 밖.
    analysis_files = [p for p in analysis_files if p.parent.name != "Rain_first"]
    assert len(analysis_files) == 8, [p.parent.name for p in analysis_files]

    summary = []
    for analysis_path in analysis_files:
        song_name = analysis_path.parent.name
        result = rehearse(song_name, analysis_path)
        gate_cues = _gate_cues_from_commands(result["commands"], result["bundle_cues"])
        fx_requested = sum(
            len(c.fx.requested) for c in result["bundle_cues"] if c.kind == "section"
        )
        # t499 readout 의 phaser_hint 파싱은 replies.json 을 읽는다 — 이 재현엔 없음(§Gaps).
        fx_hinted = 0
        gate_result = evaluate(
            gate_cues,
            sent_lines=result["commands"],
            fx_requested=fx_requested,
            fx_hinted=fx_hinted,
        )
        under3 = [(no, n) for no, n in gate_result.cue_lit_layers if n < 3]
        row = {
            "song": song_name,
            "n_section_cues": len(gate_result.cue_lit_layers),
            "n_cues_lit_ge_3": len(gate_result.cue_lit_layers) - len(under3),
            "n_cues_lit_lt_3": len(under3),
            "failing_cues": under3,
            "color_count": gate_result.color_count,
            "effect_lines_sent": gate_result.effect_lines_sent,
            "fx_requested": fx_requested,
            "warns": gate_result.warns,
            "violations": list(gate_result.violations),
        }
        summary.append(row)
        print(
            f"{song_name}: 구간 큐 {row['n_section_cues']}개 · "
            f"LIT≥3 {row['n_cues_lit_ge_3']}개 · LIT<3 {row['n_cues_lit_lt_3']}개 · "
            f"색 {row['color_count']}종 · 효과줄 {row['effect_lines_sent']} · "
            f"경고 {'YES' if row['warns'] else 'no'}"
        )
        for clause in row["violations"]:
            print(f"  위반: {clause}")

    (HERE / "ac001_8songs.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), "utf-8"
    )
    lines = []
    for row in summary:
        lines.append(
            f"{row['song']}: 구간 큐 {row['n_section_cues']} LIT>=3 {row['n_cues_lit_ge_3']} "
            f"LIT<3 {row['n_cues_lit_lt_3']} 색 {row['color_count']} "
            f"효과줄 {row['effect_lines_sent']} 경고 {row['warns']}"
        )
        for no, n in row["failing_cues"]:
            lines.append(f"  실패 큐 {no}: LIT {n}")
    (HERE / "ac001_8songs.txt").write_text("\n".join(lines) + "\n", "utf-8")


if __name__ == "__main__":
    main()

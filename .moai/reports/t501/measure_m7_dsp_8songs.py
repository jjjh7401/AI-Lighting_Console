"""카드 t501 M7 — **최종 오프라인 판정**(리드 결정 2026-10-02): 재구성
(`measure_m7_8songs.py`, analysis.json 재생)이 아니라 **실제 음원 DSP**
경로로 8곡 전부를 끝까지 돌린다.

`.moai/reports/t499/rehearse_song.py`(t499 의 원본 — 실제 오디오 →
`upload_song_audio` → `analyse_song_audio`(진짜 DSP) → 확인 카드 → 디자인
지시문 → 콘솔 명령)의 몸통을 함수로 재사용 가능하게 옮긴 것이다 — 로직은
한 글자도 바꾸지 않았다(아래 ``_rehearse_one`` 이 그 스크립트의 213~398행과
바이트 단위로 같은 순서를 따른다), 8곡 루프 + M7 능력/풀 몽키패치
(`measure_m7_8songs._patched_try_rig_capabilities`/`_patch_console_query_
state`, 재사용 — 새로 안 만든다) + 게이트 결과 캡처만 더했다.

오디오: `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample
music/*`(주 체크아웃의 비추적 파일, 읽기 전용) — 이 배차서가 지정한 절대
경로 그대로다. 콘솔 접촉: 0건(in-process FakeConsole).

실행: uv run python .moai/reports/t501/measure_m7_dsp_8songs.py
출력: 표준출력 + .moai/reports/t501/measure_m7_dsp_8songs.json
"""

from __future__ import annotations

import base64
import json
import re
import tempfile
import time
from pathlib import Path

import measure_m5_8songs as m5  # noqa: E402
import measure_m7_8songs as m7  # noqa: E402

from server.llm.types import ToolResult
from server.orchestrator.tools import ToolExecution
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.tests.test_safety_gate import FakeConsole
from server.web.approval_bridge import ApprovalChannel
from server.web.question import UNANSWERED
from server.web.session import ChatSession

HERE = Path(__file__).resolve().parent
AUDIO_ROOT = Path("/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music")
#: 배차서가 지정한 8개 파일 그대로(이 카드의 측정 집합 — 폴더에 있는 다른
#: 2개, Let's Dance.mp3·LoveMe.mp3 는 배차서 목록 밖이라 포함하지 않는다).
AUDIO_FILES: dict[str, Path] = {
    "Club Diver": AUDIO_ROOT / "Club Diver.mp3",
    "Cut and Run": AUDIO_ROOT / "Cut and Run.mp3",
    "걸그룹DinoDino_C_max최고품질": AUDIO_ROOT / "걸그룹DinoDino_C_max최고품질.wav",
    "Ice cream": AUDIO_ROOT / "Ice cream.mp3",
    "Morning": AUDIO_ROOT / "Morning.mp3",
    "Rain": AUDIO_ROOT / "Rain.mp3",
    "scott-buckley-neon": AUDIO_ROOT / "scott-buckley-neon.mp3",
    "Too Cool": AUDIO_ROOT / "Too Cool.mp3",
}
for _name, _path in AUDIO_FILES.items():
    assert _path.is_file(), f"{_name}: {_path} 없음(읽기 전용 확인 실패)"

INSTRUCTION = "디자인 큐 시트, 시퀀스 211, 프리셋 21번부터, 타임코드 11"
#: t499 rehearse_song.py 와 바이트 동일(확인 카드 1장 + 인터뷰 6장).
ANSWERS = [
    "확인",
    "우주",
    "우주 색 조합",
    "",
    "Ring In",
    "우주 컨셉 우선 배치",
    "템포 맞춤 (BPM 기준)",
]

T498 = HERE.parent / "t498"
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

REAL_GROUPS = [
    (1, "ALL"), (2, "KEY"), (3, "FOH"), (4, "BACK"), (5, "SIDE-L"), (6, "SIDE-R"),
    (7, "SIDE-ALL"), (8, "WASH-U"), (9, "WASH-D"), (10, "WASH-ALL"), (11, "MOVER-U"),
    (12, "MOVER-D"), (13, "MOVER-ALL"), (14, "BLIND"), (15, "STROBE"), (16, "HAZE"),
    (17, "ODD"), (18, "EVEN"),
]  # fmt: skip
GROUPS = {"ok": True, "children": [{"i": i, "name": n} for i, n in REAL_GROUPS]}
POSITION_POOL = {
    "ok": True,
    "children": [{"i": 21 + i, "name": name} for i, name in enumerate(BASIC_POSITION_SEQUENCE)],
}

_STORE_CUE = re.compile(r"^Store Sequence (\d+) Cue ([\d.]+) '([^']*)'")
_SET_CUE = re.compile(r"^Set Cue ([\d.]+) Sequence (\d+) Property '(\w+)' '?([^']*)'?$")
_STORE_TC = re.compile(r"^Store Timecode (\d+)$")


class _Console(FakeConsole):
    """t499 rehearse_song.py `_Console`와 바이트 동일 + M7 풀 경로 3개
    (`measure_m7_8songs._PATCHED_POOL_PATHS`, 저장된 실기 증거 — 새 조회
    0건) 추가."""

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
        if path in m7._PATCHED_POOL_PATHS:
            return m7._PATCHED_POOL_PATHS[path]
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


def _rehearse_one(song_name: str, audio_path: Path) -> dict:
    """실제 음원 바이트 → 실제 DSP(`analyse_song_audio`) → 끝까지. t499
    rehearse_song.py 213~297행과 같은 순서(바이트 동일 로직) + M7 능력/풀
    몽키패치 + 게이트 결과 캡처."""
    _captured: list[object] = []
    original_reviewed = ChatSession._reviewed_song_commands
    original_try_rig = ChatSession._try_rig_capabilities
    captured_gate: list[object] = []
    original_finalize = ChatSession._song_finalize

    def _recording_reviewed(self, composition, **kwargs):
        _captured.append(composition)
        return original_reviewed(self, composition, **kwargs)

    def _recording_finalize(self, *args, **kwargs):
        result = original_finalize(self, *args, **kwargs)
        captured_gate.append(self._last_gate_result)
        return result

    ChatSession._reviewed_song_commands = _recording_reviewed
    ChatSession._try_rig_capabilities = m7._patched_try_rig_capabilities
    ChatSession._song_finalize = _recording_finalize
    try:
        tmp = Path(tempfile.mkdtemp(prefix="t501-m7-dsp-"))
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

        data = audio_path.read_bytes()
        mime = "audio/wav" if audio_path.suffix.lower() == ".wav" else "audio/mpeg"
        t0 = time.monotonic()
        replies = [
            session.upload_song_audio(audio_path.name, mime, base64.b64encode(data).decode()),
            session.analyse_song_audio(),
        ]
        analysis = session.song_analysis
        dsp_seconds = time.monotonic() - t0
        reply = session.run_instruction(INSTRUCTION)
        replies.append(reply)

        commands = list(console.executed)
        bundle_cues = list(_captured[-1].bundle.cues) if _captured and _captured[-1].bundle else []
        return {
            "song": song_name,
            "commands": commands,
            "bundle_cues": bundle_cues,
            "reply": reply,
            "cards": questions.log,
            "n_captured": len(_captured),
            "gate_result": captured_gate[-1] if captured_gate else None,
            "dsp_seconds": dsp_seconds,
            "analysis_bpm": None if analysis is None else analysis.bpm.bpm,
            "analysis_n_sections": None if analysis is None else len(analysis.sections),
        }
    finally:
        ChatSession._reviewed_song_commands = original_reviewed
        ChatSession._try_rig_capabilities = original_try_rig
        ChatSession._song_finalize = original_finalize


def main() -> None:
    summary = []
    for song_name, audio_path in AUDIO_FILES.items():
        t0 = time.monotonic()
        result = _rehearse_one(song_name, audio_path)
        elapsed = time.monotonic() - t0
        commands = result["commands"]
        bundle_cues = {c.cue_number: c for c in result["bundle_cues"]}
        gate_result = result["gate_result"]

        effect_rows = m5._effect_states_per_cue(commands)
        non_accent_violations = {name: 0 for name in m5._EFFECT_GROUPS.values()}
        non_accent_cue_count = 0
        accent_rows = []
        prev_dims = {name: None for name in m5._EFFECT_GROUPS.values()}
        for row in effect_rows:
            try:
                cue_no_float = float(row["cue_no"])
            except ValueError:
                prev_dims = {name: row[name] for name in m5._EFFECT_GROUPS.values()}
                continue
            composed = bundle_cues.get(cue_no_float)
            is_accent_cue = composed is not None and composed.accent_fixture is not None
            if is_accent_cue:
                accent_group_name = m5._EFFECT_GROUPS.get(composed.accent_fixture.group_no)
                if accent_group_name is not None:
                    before = prev_dims[accent_group_name]
                    after = row[accent_group_name]
                    accent_rows.append(
                        {
                            "cue_no": row["cue_no"],
                            "group": accent_group_name,
                            "before": before,
                            "after": after,
                            "rises": (before or 0.0) < (after or 0.0),
                        }
                    )
            else:
                non_accent_cue_count += 1
                for name in m5._EFFECT_GROUPS.values():
                    val = row[name]
                    if val is not None and val > 0:
                        non_accent_violations[name] += 1
            prev_dims = {name: row[name] for name in m5._EFFECT_GROUPS.values()}

        under3 = [(no, n) for no, n in gate_result.cue_lit_layers if n < 3] if gate_result else []
        row = {
            "song": song_name,
            "dsp_seconds": round(result["dsp_seconds"], 2),
            "wall_seconds": round(elapsed, 2),
            "analysis_bpm": result["analysis_bpm"],
            "analysis_n_sections": result["analysis_n_sections"],
            "color_count": gate_result.color_count if gate_result else None,
            "color_change_count": gate_result.color_change_count if gate_result else None,
            "n_section_cues": len(gate_result.cue_lit_layers) if gate_result else 0,
            "n_cues_lit_lt_3": len(under3),
            "failing_cues": under3,
            "fx_requested": gate_result.fx_requested if gate_result else None,
            "fx_hinted": gate_result.fx_hinted if gate_result else None,
            "effect_lines_sent": gate_result.effect_lines_sent if gate_result else None,
            "n_non_accent_cues": non_accent_cue_count,
            "non_accent_effect_violations": non_accent_violations,
            "n_accent_cues": len(accent_rows),
            "n_accent_rises": sum(1 for r in accent_rows if r["rises"]),
            "gate_warns": gate_result.warns if gate_result else None,
            "gate_violations": list(gate_result.violations) if gate_result else [],
        }
        summary.append(row)
        total_violations = sum(non_accent_violations.values())
        print(
            f"{song_name}: DSP {row['dsp_seconds']}s · BPM {row['analysis_bpm']} · "
            f"구간 {row['analysis_n_sections']} · 색 {row['color_count']}종 · "
            f"색변화 {row['color_change_count']} · "
            f"LIT<3 {row['n_cues_lit_lt_3']}/{row['n_section_cues']} · "
            f"fx 요청/힌트/송신 "
            f"{row['fx_requested']}/{row['fx_hinted']}/{row['effect_lines_sent']} · "
            f"비액센트 effect>0 위반 {total_violations}/{non_accent_cue_count} · "
            f"액센트 상승 {row['n_accent_rises']}/{row['n_accent_cues']} · "
            f"게이트 경고 {'YES' if row['gate_warns'] else 'no'}",
            flush=True,
        )
        for clause in row["gate_violations"]:
            print(f"  게이트 위반: {clause}")

    (HERE / "measure_m7_dsp_8songs.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), "utf-8"
    )


if __name__ == "__main__":
    main()

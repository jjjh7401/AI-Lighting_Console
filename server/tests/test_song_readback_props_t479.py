"""카드 t479 — 곡 되읽기 검사가 실기에서 성공한 반영을 「실패」로 알리던 결함.

실측(t474, ``.moai/reports/t474/``): Rain 을 실기 시퀀스 210 에 반영하자 명령 119줄이 모두
``executed_ok`` 였는데, 감독에게 「readback 검증에 실패 … timed cue 1의 TrigType이 Time이
아닙니다: None」이 떴다. 같은 큐를 속성 읽기(``props``)로 읽으면 13/13 이 ``Time`` 이고 시각도
같았다(``run8_cue_props.txt``).

원인: ``_validate_song_sequence_readback`` 은 시퀀스 ``state`` 응답의 자식에서 ``TrigType``·
``TrigTime`` 을 찾는다. 실기 응답기의 ``state`` 자식은 ``class``·``i``·``name``·``cueNo`` 만 싣는다
(``run7_seq210_state.txt``). 가짜 콘솔 시험들은 자식에 속성을 넣어 돌려줘서 이 차이가 안 보였다.

이 파일의 가짜 콘솔은 **실기 모양**으로 답한다 — 자식에는 속성이 없고, 속성은 큐 경로에 대한
``props`` 읽기로만 나온다. 값은 콘솔이 받은 명령에서 온다.
"""

from __future__ import annotations

import re

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.tests.test_dedupe_value_lines_t476 import (
    _POSITION_POOL,
    _RAIN_BPM,
    _T379_GROUPS,
    _rain_analysis,
)
from server.tests.test_safety_gate import FakeConsole
from server.tests.test_writegate_song_finalize import _Approval, _Provider, _Questions, _Spatial
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession

_STORE_CUE = re.compile(r"^Store Sequence (\d+) Cue ([\d.]+) '([^']*)'")
_SET_CUE = re.compile(r"^Set Cue ([\d.]+) Sequence (\d+) Property '(\w+)' '?([^']*)'?$")
_STORE_TC = re.compile(r"^Store Timecode (\d+)$")


def _cue_label(number: float) -> str:
    return str(int(number)) if float(number).is_integer() else f"{number:g}"


class _LiveShapedConsole(FakeConsole):
    """t474 실기 회신 모양 — ``state`` 자식은 속성을 싣지 않고, 속성은 ``props`` 로만 읽힌다."""

    def __init__(self, *, trig_time_shift: dict[str, float] | None = None, props_fail=False):
        super().__init__()
        self.cues: dict[str, dict[str, object]] = {}
        self.timecodes: set[str] = set()
        self.props_paths: list[str] = []
        self._shift = trig_time_shift or {}
        self._props_fail = props_fail

    def execute(self, command: str):
        outcome = super().execute(command)
        if match := _STORE_CUE.match(command):
            _seq, cue, name = match.groups()
            self.cues.setdefault(cue, {})["name"] = name
        elif match := _SET_CUE.match(command):
            cue, _seq, prop, value = match.groups()
            self.cues.setdefault(cue, {})[prop.upper()] = value
        elif match := _STORE_TC.match(command):
            self.timecodes.add(match.group(1))
        return outcome

    def _ordered(self) -> list[tuple[int, str]]:
        # 실기처럼 OffCue(i=1)·CueZero(i=2) 다음에 큐가 번호 순으로 i=3.. 에 놓인다.
        numbers = sorted(self.cues, key=float)
        return [(index + 3, number) for index, number in enumerate(numbers)]

    def query_state(self, path: str) -> dict:
        if path == "DataPool/PresetPools/2":
            return _POSITION_POOL
        if path == "DataPool/Groups":
            return {
                "ok": True,
                "children": [{"i": 1 + i, "name": n} for i, n in enumerate(_T379_GROUPS)],
            }
        if path == "DataPool/Sequences/210" and self.cues:
            children = [
                {"class": "Cue", "i": 1, "name": "OffCue"},
                {"class": "Cue", "cueNo": 0, "i": 2, "name": "CueZero"},
            ]
            for index, number in self._ordered():
                cue_no = float(number)
                children.append(
                    {
                        "class": "Cue",
                        "cueNo": int(cue_no) if cue_no.is_integer() else cue_no,
                        "i": index,
                        "name": self.cues[number].get("name", ""),
                    }
                )
            return {
                "ok": True,
                "children": children,
                "node": {"childCount": len(children), "class": "Sequence"},
            }
        if path.startswith("DataPool/Timecodes/") and path.rsplit("/", 1)[1] in self.timecodes:
            return {"ok": True, "children": [], "node": {"childCount": 1, "class": "Timecode"}}
        raise RuntimeError(f"path segment not found: {path}")

    def query_properties(self, path: str, property_names) -> dict:
        self.props_paths.append(path)
        if self._props_fail:
            raise RuntimeError("props timeout")
        index = int(path.rsplit("/", 1)[1])
        number = dict(self._ordered())[index]
        stored = self.cues[number]
        reads = []
        for name in property_names:
            key = name.upper()
            if key == "TRIGTIME" and key in stored:
                value = float(stored[key]) + self._shift.get(_cue_label(float(number)), 0.0)
                reads.append({"n": key, "ok": True, "t": "number", "v": f"{value}"})
            elif key in stored:
                reads.append({"n": key, "ok": True, "t": "string", "v": stored[key]})
            else:
                reads.append({"n": key, "ok": False, "e": f"property not readable: {key}"})
        return {"ok": True, "path": path, "reads": reads}


def _drive(tmp_path, console: _LiveShapedConsole) -> tuple[str, dict]:
    audit = AuditLog(tmp_path / "audit")
    sent: list[dict] = []
    session = ChatSession(
        gate=SafetyGate(console=console, audit=audit, approval_port=_Approval(True)),
        provider=_Provider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=ApprovalChannel(timeout_seconds=1.0),
    )
    session._registry = _Spatial(session._registry, [])
    session._question_channel = _Questions(
        (
            "우주",
            "우주 색 조합",
            "",
            "Ring In",
            "우주 컨셉 우선 배치",
            "템포 맞춤 (BPM 기준)",
            "이 매핑 사용",
            "승인",
        )
    )
    session._song_analysis = _rain_analysis()
    session._song_bpm = _RAIN_BPM
    event = session.run_instruction("디자인 큐 시트, 시퀀스 210, 프리셋 21번부터, 타임코드 9")
    timelines = [e for e in sent if e.get("type") == "song_timeline"]
    return event["text"], timelines[-1]["timeline"]


def test_a_live_shaped_console_that_stored_everything_reads_back_as_verified(tmp_path):
    console = _LiveShapedConsole()
    text, timeline = _drive(tmp_path, console)

    # 계기가 공허하지 않다: 콘솔이 실제로 큐 13개와 그 TrigTime 을 받았고, 자식에는 속성이 없다.
    assert len(console.cues) == 13
    assert all("TRIGTIME" in cue for cue in console.cues.values())
    assert "readback 검증 완료" in text, text
    assert timeline["readback"]["verified"] is True
    # 속성은 큐 경로에 대한 props 읽기로 가져왔다.
    assert console.props_paths
    assert all(path.startswith("DataPool/Sequences/210/") for path in console.props_paths)


def test_a_wrong_trig_time_read_through_props_still_fails(tmp_path):
    # 음성 대조: props 로 읽은 값이 승인 값과 다르면 여전히 실패다.
    console = _LiveShapedConsole(trig_time_shift={"6": 1.0})
    text, timeline = _drive(tmp_path, console)

    assert "readback 검증에 실패" in text
    assert "TrigTime" in timeline["readback"]["message"]
    assert timeline["readback"]["verified"] is False


def test_a_props_read_failure_is_not_reported_as_verified(tmp_path):
    # 속성을 못 읽으면 「검증 완료」가 아니다 — 부재는 통과의 증거가 아니다.
    console = _LiveShapedConsole(props_fail=True)
    text, timeline = _drive(tmp_path, console)

    assert "readback 검증 완료" not in text
    assert timeline["readback"]["verified"] is False

"""t449 재현 — 무드 인터뷰 포지션 큐 시트(`ChatSession._position_cue_sheet`)를
가짜 콘솔 풀 상태 세 가지에 올린다. t232 `repro_song_cue_path.py`의 네 번째 경로판.

콘솔 접촉 0(FakeConsole). 스크립트는 이 카드의 수정 전/후 **동일하게** 실행
된다 — 세션 진입점(`_position_cue_sheet(text)`)의 호출 형태는 안 바뀌었고,
그 안의 번호 산출 방식만 바뀌었기 때문이다.

사용: .venv/bin/python .moai/reports/t449/repro_cuesheet_path.py

지시문은 "프리셋 1번부터"로 시작 번호를 준다. 구간 무드는 두 개 —
'잔잔하게'(→ Vocal DSC 계열), '클럽 드롭'(→ 다른 라벨) — 이고 실제로 고른
라벨은 출력의 회신 줄에 나온다.

상태:
  C  — 슬롯 1~10에 BASIC_POSITION_SEQUENCE 10종이 순서대로 있다(정상 쇼파일).
  D  — 슬롯 1~10에 "POS01 시트".."POS10 시트"가 앉아 있고(시작 번호는 여전히
       1), 진짜 기본 10종은 41~50에 있다.
  D2 — 슬롯 1~10은 시트 프리셋이고, 기본 10종은 어디에도 없다.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 트리 동일성 — t232 repro 와 같은 이유(editable .pth 가 메인 체크아웃을
# 임포트시키는 함정). 이 파일의 트리를 sys.path 맨 앞에 얹는다.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.tests.conftest import AutoApproveChannel
from server.tests.test_runner_self_correction import ScriptedProvider
from server.tests.test_safety_gate import FakeConsole
from server.web.session import ChatSession

_EMPTY = {"ok": True, "node": {"childCount": 0}, "children": []}

_TEXT = "포지션 큐 시트, 시퀀스 110, 프리셋 1번부터: 인트로 0:00 잔잔하게, 후렴 0:40 클럽 드롭"


class _PoolConsole(FakeConsole):
    """ "DataPool/PresetPools/2"만 상태로 답하고, 나머지는 미점유로 답한다."""

    def __init__(self, position_pool: dict) -> None:
        super().__init__()
        self._position_pool = position_pool

    def query_state(self, path: str) -> dict:
        if path == "DataPool/PresetPools/2":
            return self._position_pool
        if path.startswith(("DataPool/Sequences/", "DataPool/Timecodes/", "DataPool/Groups")):
            return _EMPTY
        raise RuntimeError(f"repro: 예상 밖 경로 조회 {path!r}")


def _pool_payload(entries: dict[int, str]) -> dict:
    return {"ok": True, "children": [{"i": slot, "name": name} for slot, name in entries.items()]}


def _build_session(tmp_path: Path, console: FakeConsole) -> ChatSession:
    provider = ScriptedProvider([])
    audit = AuditLog(tmp_path / "audit")
    channel = AutoApproveChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    return ChatSession(
        gate=gate,
        provider=provider,
        system_prefix="PREFIX",
        audit=audit,
        send_event=lambda _event: None,
        approval_channel=channel,
    )


def _run(position_pool: dict):
    tmp = Path(tempfile.mkdtemp(prefix="t449-repro-"))
    console = _PoolConsole(position_pool)
    session = _build_session(tmp, console)
    session._read_pointing_coordinates = lambda _tag: [(1, (0.0, 0.0, 5.0)), (2, (2.0, 0.0, 5.0))]
    # t232 repro 의 FX 경로와 같은 대역 — 시퀀스 110 이 비어 있다고 답한다.
    session._song_sequence_occupied = lambda _no: False
    result = session._position_cue_sheet(_TEXT)
    return list(console.executed), (result.text if result is not None else "(라우팅 안 됨)")


def _report(title: str, position_pool: dict) -> None:
    print(title)
    executed, text = _run(position_pool)
    recalls = [line for line in executed if "At Preset" in line]
    print(f"  recall -> {recalls}")
    print(f"  콘솔 전송 줄 수: {len(executed)}")
    print("  회신:")
    for line in text.splitlines():
        print(f"    {line}")
    print("  전체 명령열:")
    for line in executed:
        print(f"    {line}")


def main() -> None:
    _report(
        "상태 C — 기본 10종이 1~10(정상 쇼파일), 시작 1",
        _pool_payload({1 + i: name for i, name in enumerate(BASIC_POSITION_SEQUENCE)}),
    )
    print()
    pool_d = _pool_payload({1 + i: f"POS{i + 1:02d} 시트" for i in range(10)})
    pool_d["children"].extend(
        {"i": 41 + i, "name": name} for i, name in enumerate(BASIC_POSITION_SEQUENCE)
    )
    _report("상태 D — 1~10은 시트 프리셋, 진짜 기본 10종은 41~50, 시작 1", pool_d)
    print()
    _report(
        "상태 D2 — 1~10은 시트 프리셋, 기본 10종은 어디에도 없음, 시작 1",
        _pool_payload({1 + i: f"POS{i + 1:02d} 시트" for i in range(10)}),
    )


if __name__ == "__main__":
    main()

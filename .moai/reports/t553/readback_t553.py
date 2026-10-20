"""t553 Part ② — 실행 뒤 읽기 전용 되읽기 (리드가 「실행」 뒤에 돌린다).

이 스크립트는 아무것도 쓰지 않는다 — `state`/`props` 읽기만 보낸다. 지금(실행
전) 돌리면 두 슬롯이 비어 있다는 걸 보여준다(전부-거절 결과와 일치하는지
재확인용). 리드가 승인 목록을 실행한 **뒤**에 다시 돌리면 판정 근거가 된다.

읽는 것:
  1. ``Timecodes/32/1`` 의 자식 수(9 = Marker 1 + Track 8 기대) + 각 Track의
     ``TARGET`` 속성이 시퀀스 226..233 순서인지(P1b PASS/FAIL 기준).
  2. ``Sequences/336/1`` 의 존재 여부 + 크기(``MEMORYFOOTPRINT`` 류 — 저장
     전/후 비교용, t548 p3/p10/p11 되읽기와 같은 방식).

실행: uv run python .moai/reports/t553/readback_t553.py
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
from m1_common import seq_path, tc_path  # noqa: E402
from server.tools.probe_preflight import preflight  # noqa: E402

from server.safety.bootstrap import build_console_stack  # noqa: E402
from server.safety.console import StateQueryError  # noqa: E402

TC_NO = 32
TRACK_SEQS = (226, 227, 228, 229, 230, 231, 232, 233)
SEQ_NO = 336


def main() -> int:
    stack = build_console_stack(
        send_host="127.0.0.1",
        send_port=8000,
        receive_host="127.0.0.1",
        receive_port=9005,
        approval_port=None,
        audit_dir=".moai/reports/t553/live/readback_audit",
        attempt_session_backup=False,
    )
    result: dict[str, object] = {}
    try:
        health = preflight(
            stack.gate, receive_host="127.0.0.1", receive_port=9005, console_port=8000
        )
        result["preflight"] = health
        if health.get("verdict") != "responder_ok":
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1

        port = stack.gate.state_port

        # 1. Timecode 32/1 — 자식 수 + Track TARGET 순서
        try:
            node = port.query_state(f"{tc_path(TC_NO)}/1")
            children = node.get("children", [])
            tracks = [c for c in children if c.get("class") == "Track"]
            result["timecode_32_1"] = dict(
                childCount=node.get("node", {}).get("childCount"),
                track_count=len(tracks),
            )
            targets = []
            for i in range(1, len(TRACK_SEQS) + 1):
                try:
                    prop = port.query_properties(f"{tc_path(TC_NO)}/1/{i + 1}", ["TARGET"])
                    targets.append(prop)
                except StateQueryError as error:
                    targets.append(dict(error=str(error)))
            result["track_targets"] = targets
            result["expected_target_order"] = list(TRACK_SEQS)
        except StateQueryError as error:
            result["timecode_32_1"] = dict(error=str(error))

        # 2. Sequence 336 — 존재 + 크기
        try:
            node = port.query_state(seq_path(SEQ_NO))
            result["sequence_336"] = dict(exists=True, node=node.get("node"))
        except StateQueryError as error:
            result["sequence_336"] = dict(exists=False, error=str(error))
    finally:
        stack.stop()

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""SPEC-LDCOMPILE-001 C6 P1 — 축별 timing 쓰기 후보 프로브.

**검증 도구다 — 제품 코드가 아니다.** `server/tools/t60_bare_form_sweep.py` 의
형태를 승계한다: 실포트 조립(`build_console_stack`), `--approve` 없이는 콘솔에
아무것도 닿지 않는다.

## 무엇을 하나

1. Sequence 1999 'LDCOMPILE-C6 SCRATCH DELETABLE' 를 실측된 유일한 페이드
   키워드(`CueFade`)로 만든다 — 알려진 정상 형태의 대조군(baseline).
2. `MOVER-ALL` 그룹을 그 Cue 에 태우고, `PRESET2FADE`/`PRESET2DELAY`
   (Position) · `INDIVIDUALTIMING`/`INDIVFADE`/`INDIVDELAY` 를 쓰는 **후보**
   명령 묶음(recipe)을 하나씩 순서대로 쏘아 콘솔의 ok/detail 응답을 그대로
   기록한다.
3. **후보 문법은 검증된 게 아니라 추정이다.** 성공/실패를 이 스크립트가
   정하지 않고 콘솔 응답이 정한다 — 관측 전에는 `AXIS_TIMING_OBSERVED` 를
   채우지 않는다(그건 이 스크립트의 일이 아니라 사람이 결과를 읽고 하는 일).
4. 각 recipe 끝에 `ClearAll` 로 프로그래머를 비운다.
5. `Sequence 1999` 밖은 건드리지 않는다.

## 안 하는 것

- 값이 보존되는지 확인하지 않는다(되읽기는 별도 `introspect_probe` 호출).
- 성공을 가정하지 않는다 — 실패도 유효한 결과다.
- 여러 recipe 를 무한정 시도하지 않는다 — 후보 목록은 고정되어 있고, 다
  실패하면 사람이 다음 후보를 판단한다.
"""

from __future__ import annotations

import argparse
import json
import sys

from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

SEQ_NO = 1999
SEQ_NAME = "LDCOMPILE-C6 SCRATCH DELETABLE"
GROUP = "MOVER-ALL"
CLEAR = "ClearAll"

#: 대조군 — 실측된 유일한 페이드 키워드로 시퀀스·큐를 만든다.
BASELINE = [
    f"Store Sequence {SEQ_NO} Cue 1 '{SEQ_NAME}' CueFade 1",
]

#: 후보 recipe 들. 각 recipe 는 한 세트로 이어서 쏜다(중간에 ClearAll 없음) —
#: Fixture 선택 -> 속성 초점 -> timing 지정 -> Store 가 프로그래머 상태를
#: 공유해야 사슬이 이어진다는 가정이다. 이 가정 자체가 검증 대상이다.
#: MA3 는 이중인용도 받지만 이 브릿지는 명령을 플러그인 인자 문자열 안에 감싸
#: 보내서, 명령에 `"` 가 들어가면 그 감싼 문자열이 조기 종료된다
#: (`server/bridge/protocol.py:126-130`). MA3 는 단일인용도 받으므로 이름은
#: 전부 단일인용으로 쓴다.
#: Round 2 — `Fixture '<group>'` 는 R1 에서 "Illegal object" 로 거절됐다. `MOVER-ALL`
#: 은 이 저장소의 다른 프로브들이 그룹으로 다뤄왔으므로, `Group` 동사로 바꿔 다시 시도한다.
CANDIDATE_RECIPES: list[tuple[str, list[str]]] = [
    (
        "group_verb_attribute_focus_fade_delay",
        [
            f"Group '{GROUP}'",
            "Attribute 'Position'",
            "Fade 3 Enter",
            "Delay 1 Enter",
            f"Store Sequence {SEQ_NO} Cue 1 /Merge",
        ],
    ),
    (
        "group_verb_slash_qualifier_fade",
        [
            f"Group '{GROUP}'",
            f"Store Sequence {SEQ_NO} Cue 1 Fade 3 /Position /Merge",
        ],
    ),
    (
        "group_verb_named_property_bare",
        [
            f"Group '{GROUP}'",
            "PRESET2FADE 3 Enter",
            "PRESET2DELAY 1 Enter",
            f"Store Sequence {SEQ_NO} Cue 1 /Merge",
        ],
    ),
]


def _fire_sequence(gate, label: str, lines: list[str]) -> dict:
    """한 recipe 를 순서대로 쏜다. 각 줄의 clearance+실행 결과를 남긴다."""
    steps = []
    for line in lines:
        decision = gate.screen([line])
        if not decision.cleared:
            steps.append(
                dict(command=line, cleared=False, ok=None, detail=decision.status)
            )
            continue
        result = gate._execute_cleared(line)
        steps.append(
            dict(command=line, cleared=True, ok=result.ok, detail=result.detail)
        )
    return dict(label=label, steps=steps)


def _clear(gate) -> dict:
    decision = gate.screen([CLEAR])
    if not decision.cleared:
        return dict(command=CLEAR, cleared=False, ok=None, detail=decision.status)
    result = gate._execute_cleared(CLEAR)
    return dict(command=CLEAR, cleared=True, ok=result.ok, detail=result.detail)


def main() -> int:
    args = sys.argv[1:]
    if "--approve" not in args:
        print("--approve 없이는 아무것도 쏘지 않는다")
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    add_listen_port_argument(parser)
    parser.add_argument("--approve", action="store_true")
    known, _rest = parser.parse_known_args(args)

    class _Approve:
        def request_approval(self, request) -> bool:
            return True

    stack = build_console_stack(
        send_host="127.0.0.1",
        send_port=8000,
        receive_port=known.listen_port,
        approval_port=_Approve(),
    )
    report: dict = dict(baseline=None, candidates=[])
    try:
        gate = stack.gate
        report["baseline"] = _fire_sequence(gate, "baseline_store_cuefade", BASELINE)
        report["baseline"]["clear"] = _clear(gate)
        for label, lines in CANDIDATE_RECIPES:
            entry = _fire_sequence(gate, label, lines)
            entry["clear"] = _clear(gate)
            report["candidates"].append(entry)
    finally:
        stack.stop()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

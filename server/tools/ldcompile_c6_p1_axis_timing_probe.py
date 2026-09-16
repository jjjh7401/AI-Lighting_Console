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

#: Round 3 — fid 501(MOVER-U 1번, `src/Lighting_Designer/02_RIG팩/
#: LXSEQ_RIG_01_ShowBase_r3.patch.csv` 실측) 하나만 움직인다(감독 승인 완료).
#: `Fixture 'MOVER-ALL'`/`Group 'MOVER-ALL'`(이름) 대신 fid 번호를 직접 쓴다 —
#: `server/spatial/pointing.py::aimed_commands` 의 검증된 형태
#: (`Fixture <fid> ; Attribute 'Pan' At <p> ; Attribute 'Tilt' At <t>`).
#: 임의 각도를 새로 만들지 않고, 이미 존재하는 Preset 2.1('POS01 보컬 센터
#: 페이스 · 합성좌표')을 그대로 recall 한다(`preset_recall_command` 형태) —
#: 이미 실측·사용된 좌표라 새 값을 지어내는 것보다 안전하다.
FID = 501
PRESET_NO = 1

#: 대조군 — 실측된 유일한 페이드 키워드로 시퀀스·큐를 만든다. Cue 1 은 이미
#: round 1/2 에서 만들어져 있으므로(재실행 시 콘솔이 확인 팝업을 내고 취소됨),
#: 이번엔 새 Cue 번호를 쓴다 — `position_cue_store_commands` 의 규율대로
#: `/Merge`/`/Overwrite` 는 쓰지 않는다(머지가 phaser 를 깨뜨린다는 이 저장소의
#: 실측, `server/spatial/pointing.py:412-414`).
CUE_NO = 2
BASELINE = [
    f"Store Sequence {SEQ_NO} Cue {CUE_NO} '{SEQ_NAME} R3' CueFade 1",
]

#: 후보 recipe 들. 각 recipe 는 한 세트로 이어서 쏜다(중간에 ClearAll 없음).
#: MA3 는 이중인용도 받지만 이 브릿지는 명령을 플러그인 인자 문자열 안에 감싸
#: 보내서, 명령에 `"` 가 들어가면 그 감싼 문자열이 조기 종료된다
#: (`server/bridge/protocol.py:126-130`). MA3 는 단일인용도 받으므로 이름은
#: 전부 단일인용으로 쓴다.
#: Round 4 — round 3 이 값 설정까지는 전부 `ok:true` 였지만 Store 를 안 넣어서
#: 무엇도 Cue 에 안 남았다(ClearAll 이 프로그래머를 비웠다). 이번엔 값 설정 뒤
#: 곧바로 새 Cue(3)에 Store 해서 되읽을 수 있게 한다.
CUE_NO_R4 = 3
CANDIDATE_RECIPES: list[tuple[str, list[str]]] = [
    (
        "recall_preset_inline_fade_then_store",
        [
            f"Fixture {FID} ; At Preset 2.{PRESET_NO} Fade 3 Delay 1",
            f"Store Sequence {SEQ_NO} Cue {CUE_NO_R4} 'R4 recall-inline'",
        ],
    ),
    (
        "attribute_pan_tilt_inline_fade_then_store",
        [
            f"Fixture {FID} ; At Preset 2.{PRESET_NO}",
            "Attribute 'Pan' At 200 Fade 3",
            "Attribute 'Tilt' At 45 Fade 1",
            f"Store Sequence {SEQ_NO} Cue {CUE_NO_R4 + 1} 'R4 attribute-inline'",
        ],
    ),
]

#: Round 5 — `Set Cue <n> Sequence <seq> Property '<name>' <value>` 형태다.
#: round 1~4 는 전부 프로그래머 경로(Fixture/Attribute/At + Store)였고 이 형태는
#: 시도한 적이 없다. `.moai/reports/t215/verdict.md` §3(F1)이 **다른 카드**에서
#: 이 정확한 문법으로 `PRESET2FADE`(값 4)를 실측·되읽기까지 확인했다
#: (`Set Cue 1 Sequence 9 Property 'Preset2Fade' 4` → ok → 되읽기 4.0) — 이 카드는
#: 그 결과를 이 문법을 다시 추측하지 않고 그대로 재사용해 C6 의 SEQ_NO(1999)
#: 위에서 재현한다. Store 가 필요 없다 — 이미 저장된 Cue 의 CuePart 속성을 직접
#: 덮어쓰는 통로라 프로그래머를 거치지 않는다(t215 실측). `INDIVFADE`/`INDIVDELAY`
#: 를 이 Set…Property 형태로 직접 쓰는 것과 `INDIVIDUALTIMING`(문자열 enum,
#: 기본값 `Default`)에 `'On'` 을 써 보는 것은 **미시도 후보**다 — t215 는
#: INDIVFADE 를 다른 통로(bare `At <레벨> Fade` + Store)로만 관측했다.
CANDIDATE_RECIPES_R5: list[tuple[str, list[str]]] = [
    (
        "set_property_preset2fade_on_existing_cue",
        [f"Set Cue {CUE_NO} Sequence {SEQ_NO} Property 'Preset2Fade' 4"],
    ),
    (
        "set_property_preset2delay_on_existing_cue",
        [f"Set Cue {CUE_NO} Sequence {SEQ_NO} Property 'Preset2Delay' 1.5"],
    ),
    (
        "set_property_indivfade_on_existing_cue",
        [f"Set Cue {CUE_NO} Sequence {SEQ_NO} Property 'IndivFade' 2"],
    ),
    (
        "set_property_indivdelay_on_existing_cue",
        [f"Set Cue {CUE_NO} Sequence {SEQ_NO} Property 'IndivDelay' 0.8"],
    ),
    (
        "set_property_individualtiming_on_existing_cue",
        [f"Set Cue {CUE_NO} Sequence {SEQ_NO} Property 'IndividualTiming' 'On'"],
    ),
]


def _fire_sequence(gate, label: str, lines: list[str]) -> dict:
    """한 recipe 를 순서대로 쏜다. 각 줄의 clearance+실행 결과를 남긴다."""
    steps = []
    for line in lines:
        decision = gate.screen([line])
        if not decision.cleared:
            steps.append(dict(command=line, cleared=False, ok=None, detail=decision.status))
            continue
        result = gate._execute_cleared(line)
        steps.append(dict(command=line, cleared=True, ok=result.ok, detail=result.detail))
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
        for label, lines in CANDIDATE_RECIPES_R5:
            entry = _fire_sequence(gate, label, lines)
            entry["clear"] = _clear(gate)
            report["candidates"].append(entry)
    finally:
        stack.stop()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

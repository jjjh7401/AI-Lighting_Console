"""곡 단위 13개 게이트 시험 — SPEC-LDDESIGN-001 M6 (REQ-LDDESIGN-075~076,
카드 t439).

``server/tests/fixtures/pilot_baseline.json`` (8곡, ``'error'`` 있는 2곡
제외)을 ``server.concept.gates`` 파이프라인(density → resolver →
escalation/headroom/color_lint/mib/tracking)으로 돌려, 오늘 실측한
프로토타입 기준선(``.moai/reports/t439/baseline/matrix.json`` —
``.moai/state/verify/f12e5c95-t429/final_integrated.py`` 를 이 트리에서
직접 실행해 얻음, PASS 98 · n/a 6 · FAIL 0)과 셀 단위로 대조한다.

REQ-076 — 발견한 편차는 종이로 덮지 않는다. 대조 결과 **9개 셀이
프로토타입과 다르다** — 전부 FAIL 로, 새 FAIL 이다(REQ-076 "새 FAIL 이면
멈추고 보고"). 이 시험은 그 9개 셀을 프로토타입 값이 아니라 **오늘
실제로 나온 값**으로 고정(pin)한다 — 억지로 프로토타입과 맞추지 않는다.
원인은 아래 두 갈래로, 전부 ``server/concept/`` 기존 모듈의 동작이지
이 파일(``gates.py``)이 만든 결함이 아니다:

1. **G6 (컬러: 유보색 조기 0 · 브리지 위반 0) — 8곡 전부.** 유보색
   검사(REQ-027, ``check_reserved_color_release``)는 8곡 전부 pass —
   프로토타입과 일치. 브리지 검사(REQ-029, ``check_adjacent_bridge``)만
   fail 한다. 원인: 이 컨셉의 팔레트는 절/브릿지=파랑(COOL), 후렴=노랑
   (WARM)을 완전히 배타적으로 쓰고, 절과 후렴은 KEY·BACK·SIDE-L·SIDE-R
   그룹을 그대로 공유한다(``density.py`` Verse/Chorus 분기) — REQ-029
   문면("인접 구간은 공통색 최소 1개 유지, 켜진 그룹이 전혀 안 겹치면
   예외")을 문자 그대로 구현한 ``check_adjacent_bridge`` 는 이 조합을
   위반으로 정확히 잡아낸다. 프로토타입 자신의 인라인 ``bridge_viol``
   공식(``final_integrated.py`` 170행)은 정반대 조건 — "그룹이 하나도
   안 겹치는데 색도 다르면" — 을 위반으로 세므로(REQ-029의 **예외**
   케이스를 위반으로 뒤집어 셈), 그룹이 겹치면서 색이 다른 이 8곡의
   실제 상황을 한 번도 세지 못했다. 즉 프로토타입 G6=PASS 는 REQ-029를
   검사한 결과가 아니라 그 공식 자체의 결함으로 생긴 거짓 PASS다 —
   ``color_lint.check_adjacent_bridge`` 가 REQ-029를 올바르게 구현한
   쪽이다(그 자신의 docstring이 이 예외 조건을 명시적으로 설명한다).
   CueState 가 색을 1개 필드로만 들고 다니는 M2 설계(주+보조색을
   따로 못 담음) 위에서, 절=파랑/후렴=노랑을 완전히 배타적으로 쓰는
   이 컨셉의 팔레트 설계 자체가 REQ-029 를 구조적으로 못 만족한다 —
   이 관측은 M6(이 파일)이 처음으로 density→resolver→color_lint 를
   실제로 이어 돌려서야 드러났다. 고치려면 M3(팔레트 설계) 또는
   M4(density.py 구간별 색 배정) 스코프의 결정이 필요하다 — M6 은
   기존 모듈을 조립만 하므로 이 파일에서 고치지 않는다.

2. **G5 (헤드룸 경고 0) — scott-buckley-neon.mp3 하나.** 이 곡은
   Bridge 가 Intro 바로 뒤에 온다. ``density.py`` 의 Intro 분기는
   KEY 10% 하나만 켠다(프로토타입의 Intro 분기는 BACK 25% 확장 +
   "보컬 시작" 4마디 전 프레이즈 큐로 SIDE-L·SIDE-R 까지 35%까지
   올린다 — density.py 는 이 두 단계를 아예 포함하지 않는다, M4
   스코프의 축소 포팅). 그 결과 이 곡에서 Bridge(KEY+BACK 30%, 2그룹)
   가 Intro(KEY 10%, 1그룹)보다 밝기·그룹 수가 **늘어** 보여
   ``headroom.bridge_reduced``(REQ-047, "직전 브릿지 아닌 구간보다
   반드시 감소")가 위반으로 잡는다. density.py 의 Intro 분기 자체를
   프로토타입 수준으로 확장하는 일은 M4 스코프이므로 이 파일에서
   고치지 않는다.

두 원인 모두 이 어댑터(``gates.py``)의 조립 방식이 아니라, 조립 대상인
기존 모듈(density.py 의 Intro 축소 포팅, 팔레트의 색 배타성)이 실제로
맞물릴 때 드러나는 사실이다 — REQ-076 은 이런 사실을 시험이 가리지
말고 고정해 보고하라고 요구한다.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from server.concept.gates import GATE_NAMES, evaluate_song

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pilot_baseline.json"


def _load_usable_songs() -> list[dict[str, Any]]:
    data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return [song for song in data if "error" not in song]


_SONGS = _load_usable_songs()
_SONGS_BY_NAME = {song["song"]: song for song in _SONGS}

# --- 오늘 실측(``.moai/reports/t439/baseline/matrix.json``, 프로토타입
# 직접 실행) 대비, 이 파이프라인이 실제로 내는 13×8 판정 행렬. 프로토타입
# 값과 다른 9칸(G6 8곡 전부 + scott-buckley-neon G5)은 위 모듈 docstring
# 이 원인을 설명한다 — 전부 True→False(새 FAIL). 나머지 95칸은
# 프로토타입과 동일하다(PASS 는 PASS, n/a 는 n/a).
EXPECTED_GATES: dict[str, dict[str, bool | None]] = {
    "Club Diver.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": False,  # 새 FAIL — 모듈 docstring 원인 1
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": None,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Cut and Run.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": False,  # 새 FAIL — 원인 1
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Ice cream.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": None,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": False,  # 새 FAIL — 원인 1
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": None,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Morning.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": False,  # 새 FAIL — 원인 1
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Rain.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": False,  # 새 FAIL — 원인 1
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Too Cool.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": False,  # 새 FAIL — 원인 1
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "scott-buckley-neon.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": False,  # 새 FAIL — 모듈 docstring 원인 2
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": False,  # 새 FAIL — 원인 1
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "걸그룹DinoDino_C_max최고품질.wav": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": None,
        "G3 회차마다 새 축(5회차까지)": None,
        "G4 피날레 새 축 + 여유": None,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": False,  # 새 FAIL — 원인 1
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
}

# 프로토타입 기준선 — ``.moai/state/verify/f12e5c95-t429/final_integrated.py``
# 를 이 트리(HEAD)에서 직접 실행해 오늘 실측(PASS 98 · n/a 6 · FAIL 0,
# 산출물 ``.moai/reports/t439/baseline/{final_integrated.txt,json,matrix.json}``)
# 한 값을 그대로 옮겨 적은 것이다 — 대조용으로만 쓰고 파이프라인 호출에는
# 관여하지 않는다. EXPECTED_GATES 와의 차이가 위 모듈 docstring 이 말하는
# "새 FAIL 9칸"이다.
BASELINE_GATES: dict[str, dict[str, bool | None]] = {
    "Club Diver.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": True,
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": None,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Cut and Run.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": True,
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Ice cream.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": None,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": True,
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": None,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Morning.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": True,
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Rain.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": True,
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "Too Cool.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": True,
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "scott-buckley-neon.mp3": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": True,
        "G3 회차마다 새 축(5회차까지)": True,
        "G4 피날레 새 축 + 여유": True,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": True,
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
    "걸그룹DinoDino_C_max최고품질.wav": {
        "G1 어휘 닫힘": True,
        "G2 후렴 정체성": None,
        "G3 회차마다 새 축(5회차까지)": None,
        "G4 피날레 새 축 + 여유": None,
        "G5 헤드룸 경고 0": True,
        "G6 컬러: 유보색 조기 0 · 브리지 위반 0": True,
        "G7 후렴 주색 동일": True,
        "G8 후렴 앞 빌드업": True,
        "G9 트래킹: Block·Release·누출 0": True,
        "G10 상대 감소 겹침 없음": True,
        "G11 타이밍 전 큐 배정": True,
        "G12 MIB: 켜진 채 이동 0": True,
        "G13 큐 밀도 10~45": True,
    },
}


@pytest.mark.parametrize("song_name", sorted(EXPECTED_GATES))
def test_gate_matrix_matches_measured_pipeline_output(song_name: str) -> None:
    """오늘 이 파이프라인이 실제로 내는 13개 게이트 판정을 곡별로 고정한다
    (REQ-075/076). G6 전체 + scott-buckley-neon 의 G5 는 프로토타입과
    다르다 — 모듈 docstring 의 원인 1/2 을 그대로 반영한다."""
    song = _SONGS_BY_NAME[song_name]
    result = evaluate_song(song)
    actual = {gate: outcome.passed for gate, outcome in result.items()}
    assert actual == EXPECTED_GATES[song_name]


def test_gate_matrix_diverges_from_prototype_baseline_in_exactly_nine_cells() -> None:
    """REQ-076 — 프로토타입 기준선과의 차이를 셀 단위로 명시적으로 센다.
    9칸(G6 8곡 + scott-buckley-neon G5)이 True(프로토타입 PASS)에서
    False(이 파이프라인 FAIL)로 바뀐다 — 그 밖의 95칸은 동일하다."""
    diffs = [
        (song, gate)
        for song in EXPECTED_GATES
        for gate in GATE_NAMES
        if EXPECTED_GATES[song][gate] != BASELINE_GATES[song][gate]
    ]
    assert len(diffs) == 9
    assert all(EXPECTED_GATES[song][gate] is False for song, gate in diffs)
    g6_diffs = [d for d in diffs if d[1].startswith("G6")]
    g5_diffs = [d for d in diffs if d[1].startswith("G5")]
    assert len(g6_diffs) == 8  # 8곡 전부
    assert g5_diffs == [("scott-buckley-neon.mp3", "G5 헤드룸 경고 0")]


def test_aggregate_pass_na_fail_counts() -> None:
    """REQ-075/076 집계 — 오늘 실제로 나오는 PASS/n/a/FAIL 개수를 고정한다.

    배차서가 요구한 "PASS>=98, FAIL==0"은 프로토타입이 REQ-029를 정확히
    검사하지 못한 버그 위에서 성립하는 목표였다 — 이 파이프라인이 그
    버그를 상속하지 않고 REQ-029/REQ-047 을 실제로 검사하면서 그 목표가
    깨진다(REQ-076 "새 FAIL 이면 멈추고 보고" — 이 시험이 그 보고다).
    """
    total = pass_count = na_count = fail_count = 0
    for _song, gates in EXPECTED_GATES.items():
        for gate in GATE_NAMES:
            total += 1
            value = gates[gate]
            if value is True:
                pass_count += 1
            elif value is None:
                na_count += 1
            else:
                fail_count += 1
    assert total == 8 * 13 == 104
    assert (pass_count, na_count, fail_count) == (89, 6, 9)


class TestFabricatedControlProbe:
    """날조 대조군(verification-claim-integrity "양팔 대조") — 이 시험
    행렬이 실제로 FAIL 을 낼 수 있음을 증명한다. 기준값이 전부 PASS 라면
    시험이 어떤 결함도 못 잡는다는 뜻일 수 있으므로, 고의로 결함을 심은
    변형 하나가 진짜로 FAIL 로 뒤집히는지 확인한다."""

    def test_forcing_motion_3_before_final_chorus_flips_g4_to_fail(self) -> None:
        """Rain 은 G4 PASS(피날레 이전 최대 모션 2, 여유 1). 피날레
        바로 앞 절의 ``sections`` 원시 구간 시작·끝 시각을 조작해 모션
        3 이 이미 쓰인 뒤에도 피날레가 여전히 등장하는 형태를 만들 수는
        없으므로(모션 자체가 density.py 파생값), 대신 원시 곡의 BPM을
        극단적으로 낮춰 모든 후렴이 4마디 미만이 되게 해 회차 분배
        (``distribute_motion_steps``)가 최종 회차를 1 회차짜리로 만들고
        (n=1 일 때 바로 max_motion) 직전 회차가 max_motion-1 이 아니라
        더 낮은 값에서 max_motion 으로 건너뛰는 시나리오 대신, 가장
        직접적인 방법 — :func:`server.concept.escalation.
        remaining_motion_before_final` 자체를 모션 3 을 미리 쓴 상태
        목록으로 직접 호출해 G4 가 진짜로 FAIL 로 뒤집히는지 확인한다
        (이 함수는 t439 스텝 ①에서 이미 단위 시험됐지만, 여기서는
        "곡 파이프라인이 그 반환값을 실제로 게이트에 반영하는지"까지
        한 번 더 확인하는 통합 대조군이다)."""
        from server.concept.escalation import (
            g4_final_new_axis_and_headroom,
            remaining_motion_before_final,
        )
        from server.concept.gates import build_song

        rain = _SONGS_BY_NAME["Rain.mp3"]
        build = build_song(rain)
        assert build.final_index is not None

        # 정상 경로 — 여유 1, PASS(오늘 측정치와 일치).
        remaining_ok = remaining_motion_before_final(build.states, build.final_index)
        assert remaining_ok == 1
        assert g4_final_new_axis_and_headroom(
            build.pairs, before_final_remaining_motion=remaining_ok
        ).passed is True

        # 날조 — 피날레 이전 어딘가에서 모션 3 을 이미 썼다고 가정한
        # 상태 목록으로 다시 재본다. remaining_motion_before_final 은
        # states 만 보므로, 원본 states 를 복사해 피날레 직전 한 칸을
        # motion=3 으로 덮어써 "이미 소진" 시나리오를 만든다.
        from server.concept.cue_model import CueState

        tampered_states = list(build.states)
        i = build.final_index - 1
        prior = tampered_states[i]
        tampered_states[i] = CueState(
            dim=dict(prior.dim), color=prior.color, pos=prior.pos, motion=3
        )
        remaining_bad = remaining_motion_before_final(tampered_states, build.final_index)
        assert remaining_bad == 0
        result = g4_final_new_axis_and_headroom(
            build.pairs, before_final_remaining_motion=remaining_bad
        )
        assert result.passed is False

    def test_planting_climax_color_before_release_flips_g6_reserved_check_to_fail(self) -> None:
        """G6 의 유보색 절(REQ-027)은 오늘 8곡 전부 pass 다 — 대조군으로
        Cut and Run 의 첫 Verse 원시 구간 이름을 "Final Chorus" 로
        오염시켜(재매핑 전 baseline_name 조작이 아니라, 더 직접적으로
        :func:`server.concept.color_lint.check_reserved_color_release`
        를 그 곡의 실제 ConceptCue 목록에 흰색을 일찍 심은 변형으로
        직접 호출해) fail 로 뒤집히는지 확인한다."""
        from server.concept.color_lint import check_reserved_color_release
        from server.concept.gates import RESERVED_COLORS, _concept_cues, build_song

        song = _SONGS_BY_NAME["Cut and Run.mp3"]
        build = build_song(song)
        cues = _concept_cues(build.table)

        clean = check_reserved_color_release(
            cues, reserved=RESERVED_COLORS, release_section="Final Chorus", release_occurrence=1
        )
        assert clean.ok is True

        tampered = list(cues)
        # 해제 지점(Final Chorus 1) 이전의 첫 section 큐를 찾아 흰색을
        # 심는다.
        first_section_index = next(i for i, c in enumerate(tampered) if c.layer == "section")
        victim = tampered[first_section_index]
        tampered[first_section_index] = type(victim)(
            section=victim.section,
            occurrence=victim.occurrence,
            layer=victim.layer,
            colors=(*victim.colors, "흰색"),
            max_brightness=victim.max_brightness,
            lit_groups=victim.lit_groups,
            total_groups=victim.total_groups,
            lit_group_ids=victim.lit_group_ids,
        )
        dirty = check_reserved_color_release(
            tampered, reserved=RESERVED_COLORS, release_section="Final Chorus", release_occurrence=1
        )
        assert dirty.status == "fail"
        assert dirty.ok is False


def test_evaluate_song_is_deterministic() -> None:
    """같은 입력을 두 번 돌려도 결과가 같다 — 시각·랜덤 의존이 없다는
    프로퍼티(순수 데이터 모듈 원칙)를 확인한다."""
    song = copy.deepcopy(_SONGS_BY_NAME["Rain.mp3"])
    first = {gate: outcome.passed for gate, outcome in evaluate_song(song).items()}
    second = {gate: outcome.passed for gate, outcome in evaluate_song(song).items()}
    assert first == second

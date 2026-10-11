"""박자 격자 편집 경로 ②(문장) 규칙 파서 (SPEC-LDBEAT-001 M3, 카드 t551).

NLU가 아니다 — `cue_sheet_edit.parse_cue_sheet_edit_request`와 같은 모양의
고정 문장-꼴 규칙 파서다. 정해진 꼴은 명령창의 실제 자리에 적힌 그대로
(`reports/ldbeat-runbook-ui-proposal-20261008.html` 명령창 입력 자리 기본값
+ `bRule` 핸들러의 정규식, 2026-10-08):

    「(마디)~(마디)마디 (그룹) (밝기|위치|색)를 (값)으로」

예: ``"22~25마디 MOVER-D 밝기를 70%로"`` → ``{"bar": 22, "bar_end": 25,
"target": "MOVER-D", "changes": {...}}``. 단일 마디는 끝 마디를 생략한다
(``"7마디 BACK 위치를 2.9로"`` → ``bar_end == bar``). 이해 못 하는 문장은
지어내지 않고 ``None``을 돌려준다 — 호출자(``ChatSession.beat_grid_edit``)가
단일-원인 거절을 낸다(REQ-LDBEAT-007/008과 같은 "내 것이 아니다"/"내 것인데
틀렸다" 구분, `cue_sheet_edit.parse_cue_sheet_edit_request`의 관행).

**모양(mockup) 과의 차이 — 의도적 부분집합, 지어내지 않음**:

1. 이 파서가 받는 항목은 세 가지뿐이다("밝기"/"위치"/"색") — mockup의
   네 번째 항목 "효과"는 포함하지 않는다. mockup 예시("효과를 Sweep
   2박으로")는 프리셋 **이름**을 프리셋 카탈로그에서 찾아 번호로 바꾸는데
   (``bRule`` 핸들러의 ``id=Object.keys(P).find(...)``), 이 앱에는 그
   카탈로그(이름↔번호, 풀 소속, 사용처)를 읽는 경로가 어디에도 없다 —
   지어낼 수 없어 이 항목은 빠졌다(이 카드의 ``## Missing Inputs`` 참조).
2. "위치"/"색"의 값은 mockup처럼 **프리셋 이름**이 아니라 프리셋 **번호**
   문자열 그대로다 — 같은 이유(카탈로그 부재)로 이름 검색을 할 수 없다.
   번호를 직접 받는 것은 mockup이 보여주는 사용자 경험과 다르다(deviation).

돌려주는 ``changes``는 `beat_grid_edit.apply_beat_grid_edit`가 받는 모양과
바이트까지 같다 — 이 모듈은 그 함수를 호출하지 않는다(순수 파싱 전용,
콘솔 무접촉)."""

from __future__ import annotations

import re

__all__ = ["parse_beat_grid_sentence"]

#: 「(마디)[~(마디)]마디 (그룹) (밝기|위치|색)를 (값)으로」 — mockup 명령창
#: (`ldbeat-runbook-ui-proposal-20261008.html` `#cmdIn`/`#bRule`)의 실제
#: 정규식과 같은 모양(끝 마디는 선택— 단일 마디 문장도 받는다. mockup
#: 자체는 범위 전용이지만, REQ-LDBEAT-007의 "문장" 경로 자체는 단일 칸
#: 편집도 요구한다 — 둘 다 받는 상위집합이지 mockup보다 좁지 않다).
_SENTENCE_PATTERN = re.compile(
    r"^(?P<bar>\d+)\s*(?:~\s*(?P<bar_end>\d+)\s*)?마디\s+(?P<target>\S+)\s+"
    r"(?P<field>밝기|위치|색)\s*(를|을)\s*(?P<value>.+?)\s*(?:으로|로)$"
)

#: 항목 → `BeatGridCue`의 단순 번호 필드(값 하나만 받는 것만). "밝기"는
#: 퍼센트 전용 특수 처리라 아래 분기에서 따로 다룬다. "위치"가 mockup의
#: 글자 그대로다 — `position_preset_no`의 화면 레이블("포지션")과는 다른
#: 자리이므로 이 매핑에서만 "위치"를 쓴다(§Missing Inputs에 기록한 교정).
_FIELD_TO_SIMPLE_KEY: dict[str, str] = {
    "위치": "position_preset_no",
    "색": "color_preset_no",
}


def parse_beat_grid_sentence(text: str) -> dict[str, object] | None:
    """정해진 꼴 문장 하나를 읽어 ``{"bar": int, "bar_end": int, "target":
    str, "changes": dict}``로 돌려준다(``bar_end >= bar``, 단일 마디면
    ``bar_end == bar``). 이 모듈의 어휘가 아니거나 값이 숫자가 아니면
    ``None``(추측하지 않는다)."""
    match = _SENTENCE_PATTERN.match(text.strip())
    if match is None:
        return None
    bar = int(match["bar"])
    bar_end = int(match["bar_end"]) if match["bar_end"] is not None else bar
    if bar_end < bar:
        return None
    target = match["target"]
    field = match["field"]
    raw_value = match["value"].strip()

    if field == "밝기":
        percent_text = raw_value.rstrip("%").strip()
        try:
            percent = int(percent_text)
        except ValueError:
            return None
        return {
            "bar": bar,
            "bar_end": bar_end,
            "target": target,
            "changes": {
                "brightness": {"mode": "value", "value_percent": percent, "preset_no": None}
            },
        }

    key = _FIELD_TO_SIMPLE_KEY[field]
    return {"bar": bar, "bar_end": bar_end, "target": target, "changes": {key: raw_value}}

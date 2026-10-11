"""박자 격자 편집 경로 ②(문장) 규칙 파서 (SPEC-LDBEAT-001 M3, 카드 t551).

NLU가 아니다 — `cue_sheet_edit.parse_cue_sheet_edit_request`와 같은 모양의
고정 문장-꼴 규칙 파서다. 정해진 꼴은 명령창의 실제 자리에 적힌 그대로
(`reports/ldbeat-runbook-ui-proposal-20261008.html` 명령창 입력 자리 기본값
+ `bRule` 핸들러의 정규식, 2026-10-08):

    「(마디)~(마디)마디 (그룹) (밝기|위치|색|효과)를 (값)으로」

예: ``"22~25마디 MOVER-D 밝기를 70%로"`` → ``{"bar": 22, "bar_end": 25,
"target": "MOVER-D", "changes": {...}}``. 단일 마디는 끝 마디를 생략한다
(``"7마디 BACK 위치를 2.9로"`` → ``bar_end == bar``). 이해 못 하는 문장은
지어내지 않고 ``None``을 돌려준다 — 호출자(``ChatSession.beat_grid_edit``)가
단일-원인 거절을 낸다(REQ-LDBEAT-007/008과 같은 "내 것이 아니다"/"내 것인데
틀렸다" 구분, `cue_sheet_edit.parse_cue_sheet_edit_request`의 관행).

**근본 원인 정정(카드 t551 후속, 리드 지시 2026-10-11)**: 1차 구현은
"프리셋 카탈로그를 읽는 경로가 없다"고 "효과" 항목과 이름 값 해석을
빼 두었다 — 틀렸다. `server.design.console_slots`/`preset_names`가 이미
그 경로다(t477/t480). 이 모듈은 여전히 **순수 파서다**(콘솔 무접촉) —
카탈로그 조회(콘솔 읽기)는 호출자(``ChatSession.beat_grid_edit``)가 이
파서의 결과를 받은 뒤에 한다. 그래서 이 파서는 값이 "번호"(``N.NN``
그대로, 카탈로그 조회 불필요)인지 "이름"(카탈로그 조회 필요)인지만
가르고, 이름이면 ``changes`` 대신 ``name_lookup``(``{"field", "name"}``)
을 돌려준다 — 둘은 상호배타(정확히 하나만 있는 딕셔너리 키).

"효과"는 이름 전용이다 — ``effect_preset_no``는 ``effect_kind``가 함께
필요한데, 그 종류는 **어느 풀에서 이름이 매칭됐는지**로만 정해진다(풀
번호만으로는 역추적할 수 없다) — 그래서 "효과"는 항상 ``name_lookup``
이고, 번호 직접 입력은 받지 않는다."""

from __future__ import annotations

import re

__all__ = ["parse_beat_grid_sentence"]

#: 「(마디)[~(마디)]마디 (그룹) (밝기|위치|색|효과)를 (값)으로」 — mockup
#: 명령창(`ldbeat-runbook-ui-proposal-20261008.html` `#cmdIn`/`#bRule`)의
#: 실제 정규식과 같은 모양(끝 마디는 선택 — 단일 마디 문장도 받는다.
#: mockup 자체는 범위 전용이지만, REQ-LDBEAT-007의 "문장" 경로 자체는
#: 단일 칸 편집도 요구한다 — 둘 다 받는 상위집합이지 mockup보다 좁지 않다).
_SENTENCE_PATTERN = re.compile(
    r"^(?P<bar>\d+)\s*(?:~\s*(?P<bar_end>\d+)\s*)?마디\s+(?P<target>\S+)\s+"
    r"(?P<field>밝기|위치|색|효과)\s*(를|을)\s*(?P<value>.+?)\s*(?:으로|로)$"
)

#: 항목 → `BeatGridCue`의 단순 번호 필드(값이 **번호**일 때만). "밝기"는
#: 퍼센트 전용 특수 처리라 아래 분기에서 따로 다룬다. "위치"가 mockup의
#: 글자 그대로다 — `position_preset_no`의 화면 레이블("포지션")과는 다른
#: 자리이므로 이 매핑에서만 "위치"를 쓴다.
_FIELD_TO_SIMPLE_KEY: dict[str, str] = {
    "위치": "position_preset_no",
    "색": "color_preset_no",
}

#: 풀 번호 꼴("2.41" 같은)만 번호로 본다 — 이것과 다르면 카탈로그에서
#: 찾을 **이름**이다. 지어내지 않는다(이 패턴에 안 맞는 숫자는 이름 취급
#: — 예를 들어 "2" 하나뿐인 값은 번호가 아니라 이름 "2"로 카탈로그 검색).
_NUMBER_VALUE = re.compile(r"^\d+\.\d+$")


def parse_beat_grid_sentence(text: str) -> dict[str, object] | None:
    """정해진 꼴 문장 하나를 읽어 돌려준다 — 키는 항상 ``bar``/``bar_end``/
    ``target`` + (``changes`` **또는** ``name_lookup`` 중 정확히 하나).
    이 모듈의 어휘가 아니거나 값이 숫자(밝기)가 아니면 ``None``(추측하지
    않는다)."""
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

    if field == "효과":
        # effect_kind 는 어느 풀에서 이름이 매칭됐는지로만 정해진다 —
        # 번호 직접 입력은 그 역추적이 불가능해 받지 않는다(이름 전용).
        return {
            "bar": bar,
            "bar_end": bar_end,
            "target": target,
            "name_lookup": {"field": field, "name": raw_value},
        }

    # 위치/색 — 번호 꼴이면 그대로, 아니면 카탈로그에서 찾을 이름이다.
    if _NUMBER_VALUE.match(raw_value):
        key = _FIELD_TO_SIMPLE_KEY[field]
        return {"bar": bar, "bar_end": bar_end, "target": target, "changes": {key: raw_value}}
    return {
        "bar": bar,
        "bar_end": bar_end,
        "target": target,
        "name_lookup": {"field": field, "name": raw_value},
    }

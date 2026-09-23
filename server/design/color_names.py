"""색 이름 → RGB(0-100) 사전 (카드 t408).

콘솔에 컬러 명령을 보내려면 "warm white" 같은 이름 하나가 실제로 무슨
RGB 인지 답할 출처가 있어야 한다. `_palette_rgb`
(`server/design/cue_sheet_apply.py`)는 감독의 팔레트 범례(``palette_legend``)
가 있을 때만 값을 찾았는데, 실제 곡 분석 경로에는 범례가 아예 안 실린다
(`server/web/session.py` 의 `_song_cue_sheet_view_fields` 주석 — 룩
라이브러리가 팔레트에 **이름**을 안 달아서 지어낼 수 없다는 이유). 그래서
아크가 내는 팔레트 값(`_ARC_PALETTE`)과 감독의 한국어 원색 표기는 범례가
없으면 항상 `None` 이었다(카드 t408 실측 — 39구간 중 0구간이 컬러를 냈다).

이 파일은 그 값을 **지어내지 않고** 두 기존 출처에서만 끌어온다:

1. ``COLOR_PALETTE_SEQUENCE`` — spec.md §A.2 가 고정한 표준 무대 팔레트
   10색. 원래 `server/web/session.py` 에 있었다(프리셋 재생성 기능이
   쓴다) — 순환 임포트 없이 `server/design` 계층에서도 쓰려고 이 파일로
   옮기고 `session.py` 는 이 파일에서 다시 가져간다(단일 출처, 값은
   바이트 그대로). 4번 Amber(100/55/5)·8번 Blue(5/20/100)는 기존
   `fx/library/color.yaml` 실측 대역에서 왔다(session.py 쪽 주석 그대로).
2. ``_KO_EN_COLOR_EQUIV`` — 감독이 화면에 적는 한국어 원색 표기가
   가리키는 영어 이름. 카드 t406 이 아크 팔레트 코드용으로 이미 관리하던
   표를 그대로 옮겼다(같은 이유로 순환 임포트를 피한다).

이 두 표 밖의 이름(예: "gold"·"pink"·"orange"·"warm special")은
**일부러** 비워 둔다 — 표준 팔레트 10색에 없는 색은 실제 값이 없으므로
지어내지 않고 `resolve_color_name` 이 `None` 을 돌려준다. 그러면 호출부는
`CueSkip` 으로 실패를 알려야 한다(색을 지어내지 않는다는 이 저장소의
불변식, `cue_sheet_apply.py` 의 `_palette_rgb` 참고).
"""

from __future__ import annotations

import re

#: 표준 무대 팔레트 10색 — 슬롯 순서가 계약이다(spec.md §A.2). 값은
#: `server/web/session.py` 의 원본과 바이트 동일 — 그 파일은 이제 이 표를
#: 다시 가져간다(단일 출처).
COLOR_PALETTE_SEQUENCE: tuple[tuple[str, tuple[int, int, int]], ...] = (
    ("Warm White", (100, 75, 40)),
    ("Cool White", (85, 95, 100)),
    ("Red", (100, 0, 0)),
    ("Amber", (100, 55, 5)),
    ("Yellow", (100, 85, 0)),
    ("Green", (0, 100, 10)),
    ("Cyan", (0, 90, 100)),
    ("Blue", (5, 20, 100)),
    ("Magenta", (100, 0, 70)),
    ("Lavender", (55, 35, 100)),
)

_PALETTE_RGB_BY_NAME: dict[str, tuple[int, int, int]] = {
    name.casefold(): rgb for name, rgb in COLOR_PALETTE_SEQUENCE
}

#: 카드 t406 — 한국어 원색 이름과 아크 팔레트(`_ARC_PALETTE`, session.py)의
#: 영어 표기가 같은 색상을 가리킬 수 있다("블루" == "blue"). 감독이 화면에
#: 보는 원색 표기는 절대 안 바꾼다(입력 그대로 유지) — 이 표는 조회에만
#: 쓴다.
_KO_EN_COLOR_EQUIV: dict[str, str] = {
    "블루": "blue",
    "파랑": "blue",
    "파란": "blue",
    "레드": "red",
    "빨강": "red",
    "빨간": "red",
    "그린": "green",
    "초록": "green",
    "녹색": "green",
    "옐로우": "yellow",
    "엘로우": "yellow",
    "노랑": "yellow",
    "노란": "yellow",
    "골드": "gold",
    "금색": "gold",
    "마젠타": "magenta",
    "시안": "cyan",
    "청록": "cyan",
    # SPEC-LDDESIGN-001 M2(2026-09-23) 재확인 — 흰색 표기는 **여전히 배선하지
    # 않는다**. 카드 t409 가 퍼플/보라만 판정하고 화이트/흰색/하양은 "감독 판정
    # 대상 목록에는 있었지만 배선 대상은 아니다"로 남긴 그대로다
    # (`server/tests/test_cue_sheet_apply.py`
    #  `test_words_the_director_did_not_rule_on_still_fail_loudly`).
    # 표준 팔레트에는 `Warm White`(100,75,40)와 `Cool White`(85,95,100)가
    # 둘 다 있어 맨 "흰색"이 어느 쪽인지는 감독만 정할 수 있다 — 무대에서
    # 눈에 띄게 다른 두 색이므로 한쪽으로 몰면 지어내는 것이다.
    # 미해소는 조용히 넘어가지 않고 사유로 노출된다(`_color_failure_note`).
    "화이트": "white",
    "흰색": "white",
    "하양": "white",
    "앰버": "amber",
    # 카드 t408 잔여 → 카드 t409 감독 판정: "퍼플" 은 표준 팔레트에 정확히
    # 일치하는 이름이 없지만, 감독이 "퍼플/보라 → Lavender(55,35,100)" 로
    # 직접 판정했다(#A.2 10색 중 유일한 보라 계열). 값을 새로 짓지 않고
    # 이미 있는 Lavender 슬롯을 가리키기만 한다.
    "퍼플": "lavender",
    "보라": "lavender",
    "핑크": "pink",
    "오렌지": "orange",
    "주황": "orange",
}

#: 아크/감독 표기가 쓰는 색조 수식어 — 색상 동일성 판정 전에 벗겨낸다
#: ("deep blue" 와 "블루" 는 수식어를 떼면 둘 다 blue).
_HUE_MODIFIER_STRIP = re.compile(
    r"^(deep|cold|warm|pale|light|dark|짙은|연한|쿨톤|웜톤)\s+", re.IGNORECASE
)


def resolve_color_name(value: str) -> tuple[int, int, int] | None:
    """색 이름 문자열 → RGB(0-100) 백분율. 표에 없으면 ``None``.

    순서가 정확도를 가른다:

    1. 표준 팔레트 이름과 정확히 일치("Warm White") — 수식어를 벗기기
       **전에** 먼저 시도해야 한다. 안 그러면 "warm" 을 먼저 벗긴
       "white" 는 표에 없는 이름이 되어 오히려 못 찾는다(표에는 합성
       이름 "Warm White"만 있고 맨 "White" 는 없다).
    2. 한국어 원색 표기 → 영어 이름으로 바꿔 재시도("블루" → "blue").
    3. 색조 수식어(짙은/연한/deep/cold/warm 등)를 벗기고 재시도 —
       "cold blue"·"deep blue" 는 색상 정체성(hue)이 blue 이므로 그
       값으로 되돌아간다. "warm special" 처럼 벗긴 뒤에도 색이 아닌
       말(역할 이름 "special")이 남으면 여기서도 못 찾고 ``None`` —
       지어내지 않는다.
    """
    text = value.strip()
    if not text:
        return None

    hit = _PALETTE_RGB_BY_NAME.get(text.casefold())
    if hit is not None:
        return hit

    english = _KO_EN_COLOR_EQUIV.get(text)
    if english is not None:
        hit = _PALETTE_RGB_BY_NAME.get(english.casefold())
        if hit is not None:
            return hit

    stripped = _HUE_MODIFIER_STRIP.sub("", text).strip()
    if stripped and stripped != text:
        base = _KO_EN_COLOR_EQUIV.get(stripped, stripped)
        hit = _PALETTE_RGB_BY_NAME.get(base.casefold())
        if hit is not None:
            return hit

    return None


def color_hex(value: str) -> str | None:
    """색 이름 → 화면용 ``#RRGGBB``. :func:`resolve_color_name` 이 못 찾으면 ``None``.

    카드 t456 — 런북 화면이 색 표를 따로 들고 있지 않도록 서버가 HEX 까지
    내보낸다. 0-100 백분율을 0-255 로 반올림할 뿐 값을 새로 짓지 않는다.
    """
    rgb = resolve_color_name(value)
    if rgb is None:
        return None
    return "#" + "".join(f"{round(channel * 255 / 100):02X}" for channel in rgb)

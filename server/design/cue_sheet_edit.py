"""큐시트 초안 편집 — 코파일럿이 선택된 큐의 큐시트 칸을 고치는 순수 모델 (t281).

이 모듈은 **콘솔에 아무것도 쓰지 않는다.** 입력은 `_song_timeline_payload` 가
만든 타임라인 사전이고, 출력은 그 사전의 **새 사본**이다. 명령 문자열도,
`ToolCall` 도, 승인 카드도 여기 없다 — 그래서 이 경로로는 원리적으로 콘솔에
닿을 수 없다.

거절은 조용하지 않다. 못 고치는 요청은 :class:`CueSheetEditError` 로 **사유
문자열과 함께** 튀어나온다. 이 저장소에는 「거짓 사유가 먼저 떠서 참 사유가
가려진」 결함 계열이 기록돼 있으므로(t112), 사유는 한 가지 원인만 지목하고
시험은 사유 문자열 자체를 단언한다.

편집 가능한 칸은 모델이 **이미 가진** 것뿐이다(`ui/src/protocol.ts`
``SongTimelineSection``). 없는 칸은 지어내지 않고 거절한다.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping

__all__ = [
    "CueSheetEditError",
    "EDITABLE_FIELD_LABELS",
    "TRANS_VALUES",
    "apply_cue_sheet_edit",
    "parse_cue_sheet_edit_request",
    "section_intensity_percent",
]


class CueSheetEditError(ValueError):
    """편집을 못 했다. 메시지는 감독에게 그대로 보여도 되는 한국어 사유다."""


#: 고칠 수 있는 칸과 화면 이름. 이 표에 없는 이름은 「없는 칸」으로 거절한다.
EDITABLE_FIELD_LABELS: dict[str, str] = {
    "mood": "무드",
    "palette_primary": "컬러(주)",
    "palette_secondary": "컬러(보조)",
    "intensity": "조도",
    "movement": "무브먼트",
    "effect": "이펙트",
    "trans": "전환",
    "fade_seconds": "페이드",
    "note": "노트",
}

#: 정본 `Snap` 열이 받는 값. 다른 값은 지어내지 않는다.
TRANS_VALUES: tuple[str, ...] = ("SNAP", "XFADE", "FADE")

#: 조도 상·하한. 콘솔 백분율 축 그대로다.
_INTENSITY_MIN = 0
_INTENSITY_MAX = 100

#: 페이드 상한. 이보다 긴 값은 오타로 보고 거절한다(초 단위).
_FADE_MAX_SECONDS = 60.0

#: 상대 조도 한 걸음.
_INTENSITY_STEP = 20


def section_intensity_percent(section: Mapping[str, object]) -> int:
    """구간의 현재 조도(0..100). 그룹별 값이 있으면 최댓값, 없으면 d_level×20.

    `ui/src/components/CueSheetTimeline.tsx` 의 `sectionIntensityPercent` 와
    같은 규칙이다 — 화면이 읽는 값과 편집이 고치는 값이 갈리면 안 된다.
    """
    entries = section.get("intensity")
    if isinstance(entries, list) and entries:
        levels = [
            int(entry["level"])
            for entry in entries
            if isinstance(entry, Mapping) and isinstance(entry.get("level"), (int, float))
        ]
        if levels:
            return max(levels)
    level = section.get("d_level")
    if isinstance(level, (int, float)):
        return max(_INTENSITY_MIN, min(_INTENSITY_MAX, int(level) * _INTENSITY_STEP))
    return 0


# -- 요청 문장 읽기 -------------------------------------------------------------

_CUE_NUMBER = re.compile(r"큐\s*(?P<cue>\d+)")
_BRIGHTER = re.compile(r"(더\s*)?(밝게|밝혀|올려|높여)")
_DARKER = re.compile(r"(더\s*)?(어둡게|어둡|낮춰|내려)")
_INTENSITY_ABS = re.compile(r"(조도|밝기|인텐시티)\s*(를|을)?\s*(?P<v>\d{1,3})\s*%?")
_FADE = re.compile(r"페이드\s*(를|을)?\s*(?P<v>\d+(?:\.\d+)?)\s*(초|s)?")
_TRANS = re.compile(
    r"(전환|트랜스|trans)\s*(를|을)?\s*(?P<v>SNAP|XFADE|FADE|스냅|크로스페이드)", re.I
)
_SNAP_WORD = re.compile(r"스냅(으로|로)")
_MOOD = re.compile(r"무드\s*(를|을)?\s*(?P<v>[^,.\n]+?)\s*(으로|로)\s*(바꿔|해줘|변경|수정|설정)")
_MOVEMENT = re.compile(
    r"(무브먼트|무브|움직임)\s*(를|을)?\s*(?P<v>[^,.\n]+?)\s*(으로|로)\s*(바꿔|해줘|변경|수정|설정)"
)
_EFFECT = re.compile(
    r"(이펙트|효과)\s*(를|을)?\s*(?P<v>[^,.\n]+?)\s*(으로|로)\s*(바꿔|해줘|변경|수정|설정)"
)
_COLOR = re.compile(
    r"(컬러|색|색상|팔레트)\s*(를|을)?\s*(?P<v>[^,.\n]+?)\s*(으로|로)\s*(바꿔|해줘|변경|수정|설정)"
)
_NOTE = re.compile(
    r"(노트|메모)\s*(를|을)?\s*(?P<v>[^\n]+?)\s*(으로|로)?\s*(적어|남겨|바꿔|해줘|설정)"
)

#: 이 모듈이 「내 요청」이라고 인정하는 최소 신호. 하나도 없으면 None 을 돌려
#: 기존 라우트 사슬로 그대로 흘려보낸다(오라우팅 방지).
_EDIT_VERB = re.compile(r"(바꿔|변경|수정|해줘|설정|적어|남겨|밝게|어둡게|올려|낮춰|높여|내려)")

#: **큐 지시어**. 편집 동사만으로는 부족하다 — 실측(2026-09-06): 곡 전체를
#: 서술하는 설계 브리핑("0:00 도입은 무대를 어둡게 두고 …")이 「어둡게」 하나로
#: 이 라우트에 삼켜져 곡 설계 인터뷰 32건이 통째로 깨졌다. 한 구간을 가리키는
#: 지시어를 **필수 게이트**로 두면 브리핑은 그대로 아래로 흘러내린다.
_CUE_ANCHOR = re.compile(r"큐\s*\d+|이\s*(구간|큐|부분|씬|장면)|선택(한|된)\s*(구간|큐|부분)")


def parse_cue_sheet_edit_request(text: str) -> dict[str, object] | None:
    """한국어 요청 한 줄에서 큐시트 편집 지시를 읽어낸다.

    돌려주는 사전은 ``{"cue": int|None, "changes": {...}}`` 이고, 이 모듈이
    다루는 어휘가 하나도 없으면 ``None`` 이다 — 「내 것이 아니다」와 「내
    것인데 틀렸다」를 가른다. 후자는 :func:`apply_cue_sheet_edit` 가 사유를
    붙여 거절한다.
    """
    if _EDIT_VERB.search(text) is None or _CUE_ANCHOR.search(text) is None:
        return None
    changes: dict[str, object] = {}

    if (match := _INTENSITY_ABS.search(text)) is not None:
        changes["intensity"] = int(match.group("v"))
    elif _BRIGHTER.search(text) is not None:
        changes["intensity_delta"] = _INTENSITY_STEP
    elif _DARKER.search(text) is not None:
        changes["intensity_delta"] = -_INTENSITY_STEP

    if (match := _FADE.search(text)) is not None:
        changes["fade_seconds"] = float(match.group("v"))

    if (match := _TRANS.search(text)) is not None:
        raw = match.group("v").upper()
        changes["trans"] = {"스냅": "SNAP", "크로스페이드": "XFADE"}.get(match.group("v"), raw)
    elif _SNAP_WORD.search(text) is not None:
        changes["trans"] = "SNAP"

    for field, pattern in (
        ("mood", _MOOD),
        ("movement", _MOVEMENT),
        ("effect", _EFFECT),
        ("palette_primary", _COLOR),
        ("note", _NOTE),
    ):
        if (match := pattern.search(text)) is not None:
            value = match.group("v").strip()
            if value:
                changes[field] = value

    if not changes:
        return None
    cue_match = _CUE_NUMBER.search(text)
    return {
        "cue": int(cue_match.group("cue")) if cue_match is not None else None,
        "changes": changes,
    }


# -- 적용 -----------------------------------------------------------------------


def _find_section(timeline: Mapping[str, object], cue_number: int) -> tuple[int, dict]:
    sections = timeline.get("sections")
    if not isinstance(sections, list) or not sections:
        raise CueSheetEditError("수정할 큐시트가 비어 있습니다. 곡 설계를 먼저 완료해 주세요.")
    for slot, section in enumerate(sections):
        if isinstance(section, Mapping) and section.get("cue_number") == cue_number:
            return slot, dict(section)
    known = [
        str(section.get("cue_number"))
        for section in sections
        if isinstance(section, Mapping) and section.get("cue_number") is not None
    ]
    raise CueSheetEditError(
        f"큐 {cue_number}가 이 큐시트에 없습니다. (보유 큐: {', '.join(known) or '없음'})"
    )


def _set_intensity(section: dict, percent: int, report: list[str]) -> None:
    before = section_intensity_percent(section)
    entries = section.get("intensity")
    if isinstance(entries, list) and entries:
        section["intensity"] = [
            {**entry, "level": percent} if isinstance(entry, Mapping) else entry
            for entry in entries
        ]
    # d_level 은 1..5 축이다. 백분율을 그 축으로 환산해 같이 옮긴다 — 한쪽만
    # 고치면 화면(그룹별 값)과 폴리라인(d_level)이 서로 다른 값을 말한다.
    section["d_level"] = max(1, min(5, round(percent / _INTENSITY_STEP)))
    report.append(f"{EDITABLE_FIELD_LABELS['intensity']} {before} → {percent}")


def apply_cue_sheet_edit(
    timeline: Mapping[str, object],
    cue_number: int,
    changes: Mapping[str, object],
) -> tuple[dict, list[str]]:
    """``timeline`` 의 사본에 ``changes`` 를 적용하고 (새 타임라인, 변경 보고)를 돌려준다.

    원본은 건드리지 않는다(초안 되돌리기가 「직전 상태 그대로」를 복원할 수
    있어야 하므로). 못 고치는 항목은 :class:`CueSheetEditError` 로 거절하며,
    **부분 적용은 없다** — 사유를 던지기 전에 아무것도 쓰지 않는다.
    """
    if not changes:
        raise CueSheetEditError(
            "무엇을 고칠지 못 읽었습니다. 예: '큐 3 조도 80으로 바꿔줘', '이 구간 더 밝게'."
        )
    unknown = [
        key for key in changes if key not in EDITABLE_FIELD_LABELS and key != "intensity_delta"
    ]
    if unknown:
        editable = ", ".join(EDITABLE_FIELD_LABELS.values())
        raise CueSheetEditError(
            f"'{unknown[0]}'은(는) 큐시트가 가진 항목이 아닙니다. 수정 가능한 항목: {editable}."
        )

    slot, section = _find_section(timeline, cue_number)

    # --- 검증을 전부 끝낸 뒤에 쓴다 (부분 적용 금지) ---
    target_percent: int | None = None
    if "intensity" in changes:
        raw = changes["intensity"]
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            raise CueSheetEditError(f"조도는 숫자여야 합니다 (받은 값: {raw!r}).")
        target_percent = int(raw)
    elif "intensity_delta" in changes:
        delta = changes["intensity_delta"]
        if not isinstance(delta, (int, float)) or isinstance(delta, bool):
            raise CueSheetEditError(f"조도 증감은 숫자여야 합니다 (받은 값: {delta!r}).")
        target_percent = section_intensity_percent(section) + int(delta)
    if target_percent is not None and not (_INTENSITY_MIN <= target_percent <= _INTENSITY_MAX):
        raise CueSheetEditError(
            f"조도는 {_INTENSITY_MIN}~{_INTENSITY_MAX} 사이여야 합니다 (요청값: {target_percent})."
        )

    if "trans" in changes:
        trans = changes["trans"]
        if not isinstance(trans, str) or trans.upper() not in TRANS_VALUES:
            raise CueSheetEditError(
                f"전환 값은 {', '.join(TRANS_VALUES)} 중 하나여야 합니다 (받은 값: {trans!r})."
            )

    if "fade_seconds" in changes:
        fade = changes["fade_seconds"]
        if not isinstance(fade, (int, float)) or isinstance(fade, bool):
            raise CueSheetEditError(f"페이드는 숫자여야 합니다 (받은 값: {fade!r}).")
        if not (0 <= float(fade) <= _FADE_MAX_SECONDS):
            raise CueSheetEditError(
                f"페이드는 0~{_FADE_MAX_SECONDS:g}초 사이여야 합니다 (요청값: {fade})."
            )

    for field in ("mood", "palette_primary", "palette_secondary", "movement", "effect", "note"):
        if field in changes:
            value = changes[field]
            if not isinstance(value, str) or not value.strip():
                raise CueSheetEditError(
                    f"{EDITABLE_FIELD_LABELS[field]} 값이 비어 있습니다 — "
                    "무엇으로 바꿀지 적어 주세요."
                )

    # --- 여기부터 쓰기. 위를 전부 통과했으므로 중간에 튀지 않는다. ---
    report: list[str] = []
    if target_percent is not None:
        _set_intensity(section, target_percent, report)
    if "trans" in changes:
        before = section.get("trans")
        section["trans"] = str(changes["trans"]).upper()
        report.append(f"{EDITABLE_FIELD_LABELS['trans']} {before or '—'} → {section['trans']}")
    if "fade_seconds" in changes:
        before = section.get("fade_seconds")
        section["fade_seconds"] = float(changes["fade_seconds"])
        report.append(
            f"{EDITABLE_FIELD_LABELS['fade_seconds']} "
            f"{'—' if before is None else f'{float(before):g}초'} → {section['fade_seconds']:g}초"
        )
    for field in ("mood", "palette_primary", "palette_secondary", "movement", "effect", "note"):
        if field in changes:
            before = section.get(field)
            section[field] = str(changes[field]).strip()
            report.append(f"{EDITABLE_FIELD_LABELS[field]} {before or '—'} → {section[field]}")

    updated = copy.deepcopy(dict(timeline))
    sections = list(updated["sections"])
    sections[slot] = section
    updated["sections"] = sections
    return updated, report

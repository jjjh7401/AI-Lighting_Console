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

#: 상대 페이드 한 걸음(초). 「페이드 좀 길게」가 옮기는 양이다. 조도의 20%와
#: 같은 성격의 고정 오프셋이며, 비례 배율이 아닌 이유도 같다(되돌리기가 정확히
#: 대칭이 된다). 0~60초 사이에서 잘리고, 잘린 사실은 리포트에 적힌다.
_FADE_STEP = 1.0


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
#: t300 — 페이드를 **상대로** 옮기는 말. 「페이드」를 요구하는 것이 이 술어의
#: 핵심이다: 「더 빠르게」 넉 자만으로는 페이드인지 무브먼트 속도인지 이펙트
#: 속도인지 갈리지 않는다. 갈리지 않는 문장은 지어내지 않고 흘려보낸다.
_FADE_LONGER = re.compile(r"페이드[^\n]{0,8}?(길게|느리게|천천히|늘려|늘리)")
_FADE_SHORTER = re.compile(r"페이드[^\n]{0,8}?(짧게|빠르게|빨리|줄여|줄이)")

#: 페이드 0초 = 스냅. 같은 물리 현상을 감독은 두 가지로 말한다.
_FADE_NONE = re.compile(r"페이드\s*(를|을)?\s*(없이|없애|빼)|스냅(으로|로)")
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

#: **자기 완결형 페이드 지시**. 실측(2026-09-06): 「큐 20 페이드 3초로」가
#: `None` 을 돌려받았다 — `_FADE` 는 이 문장을 읽을 수 있는데 위 동사 목록에
#: 「로」가 없어 그 앞 게이트에서 잘렸다. 페이드를 데스크로 보내는 명령
#: (`Store … CueFade <초> /Merge`)은 이미 실측으로 콘솔에 닿는데, 감독이
#: 그것을 부를 말이 없었다.
#:
#: 이 술어는 동사 목록의 **대안**이지 확장이 아니다: 문장 자체가 「페이드를
#: 얼마로」를 이미 말하고 있으면 「바꿔줘」를 덧붙이라고 요구하지 않는다.
#: 두 번째 게이트(지시어 또는 t290 판별기)는 그대로 남는다.
_FADE_DIRECTIVE = re.compile(
    r"페이드\s*(를|을)?\s*\d+(?:\.\d+)?\s*(초|s)"  # 페이드 3초 / 페이드를 3.5초로
    r"|페이드[^\n]{0,8}?(길게|짧게|느리게|빠르게|빨리|천천히|늘려|늘리|줄여|줄이)"
    r"|페이드\s*(를|을)?\s*(없이|없애|빼)"
    r"|스냅(으로|로)"
)

#: 페이드-단독 게이트가 **열지 않는** 문장. 실측 회귀(2026-09-06): 「프리셋
#: 2.28을 시퀀스 101 큐 1로 저장, 페이드 5초」가 위 술어와 `큐 1` 지시어를
#: 함께 갖고 있어 큐시트 편집으로 삼켜졌다 — 콘솔로 나가야 할 프리셋 저장이
#: 0건이 됐다. 편집 동사가 따로 있는 문장은 이 배제를 받지 않는다(그쪽은
#: 감독이 「고쳐라」라고 말한 문장이다).
_NOT_A_CUE_SHEET_EDIT = re.compile(r"프리셋|저장|스토어|Store", re.IGNORECASE)

#: **큐 지시어**. 편집 동사만으로는 부족하다 — 실측(2026-09-06): 곡 전체를
#: 서술하는 설계 브리핑("0:00 도입은 무대를 어둡게 두고 …")이 「어둡게」 하나로
#: 이 라우트에 삼켜져 곡 설계 인터뷰 32건이 통째로 깨졌다. 한 구간을 가리키는
#: 지시어를 게이트로 두면 브리핑은 그대로 아래로 흘러내린다.
_CUE_ANCHOR = re.compile(r"큐\s*\d+|이\s*(구간|큐|부분|씬|장면)|선택(한|된)\s*(구간|큐|부분)")

#: 지시어 없는 문장을 받아 주는 한 걸음(t290). 화면에서 큐를 이미 고른 상태라면
#: 「더 밝게」 넉 자에 지시어를 덧붙이게 하는 것은 감독에게 같은 말을 두 번
#: 시키는 일이다. 그래서 지시어를 **필수**에서 **판별기의 한 축**으로 낮추되,
#: 위 브리핑 회귀는 그대로 막아야 한다 — 아래 세 축이 그 일을 한다.
#:
#: ① 길이. 한 구간에 던지는 명령은 짧다("더 밝게", "페이드 3초로"). 곡 브리핑은
#:    길다(위 회귀 문장 89자). 경계 40자는 코퍼스 실측으로 잡았다.
#: ② 줄 수. 브리핑은 여러 줄·여러 문장이다. 한 구간 명령은 한 줄이다.
#: ③ 어휘. 곡을 서술하는 표지 — 타임코드(0:00), 구간 이름(도입·후렴·…),
#:    곡/장르/BPM, 그리고 **범위어**(전체·모든·곡 내내) — 가 하나라도 있으면
#:    「선택한 한 큐에 대한 명령」이 아니다. 범위어는 특히 중요하다:
#:    "전체적으로 더 밝게"는 짧고 한 줄이지만 한 큐를 가리키지 않는다.
_ANCHORLESS_MAX_CHARS = 40
_SONG_BRIEF_MARKER = re.compile(
    r"\d{1,2}\s*:\s*\d{2}"  # 타임코드 (0:00, 1:32)
    r"|도입|인트로|벌스|후렴|코러스|브릿지|간주|아웃트로|드롭|빌드업|엔딩|마지막"
    r"|곡\s*(은|는|이|전체)|노래|장르|BPM|bpm|무대\s*(는|은)"
    r"|전체|전부|모든|다\s*같이|내내|처음부터|끝까지"
)


def _is_anchorless_cue_command(text: str) -> bool:
    """지시어 없는 문장이 「선택한 큐 하나에 던진 짧은 명령」인가.

    참을 돌려주는 조건은 셋 다 성립할 때뿐이다(위 ①②③). 하나라도 어긋나면
    거짓이고, 문장은 기존 라우트 사슬로 그대로 흘러내린다.
    """
    stripped = text.strip()
    if len(stripped) > _ANCHORLESS_MAX_CHARS:
        return False
    if "\n" in stripped:
        return False
    return _SONG_BRIEF_MARKER.search(stripped) is None


def parse_cue_sheet_edit_request(
    text: str, *, cue_selected: bool = False
) -> dict[str, object] | None:
    """한국어 요청 한 줄에서 큐시트 편집 지시를 읽어낸다.

    돌려주는 사전은 ``{"cue": int|None, "changes": {...}}`` 이고, 이 모듈이
    다루는 어휘가 하나도 없으면 ``None`` 이다 — 「내 것이 아니다」와 「내
    것인데 틀렸다」를 가른다. 후자는 :func:`apply_cue_sheet_edit` 가 사유를
    붙여 거절한다.

    ``cue_selected`` 는 화면에서 감독이 이미 큐를 고른 상태인지다(t290).
    참이면 지시어 없는 **짧은 한 줄 명령**도 받아 준다 —
    :func:`_is_anchorless_cue_command` 가 그 판별기다. 기본값은 거짓이라
    호출자가 아무것도 바꾸지 않으면 t281 그대로 동작한다.
    """
    fade_only_gate = (
        _FADE_DIRECTIVE.search(text) is not None and _NOT_A_CUE_SHEET_EDIT.search(text) is None
    )
    if _EDIT_VERB.search(text) is None and not fade_only_gate:
        return None
    if _CUE_ANCHOR.search(text) is None and not (cue_selected and _is_anchorless_cue_command(text)):
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
    elif _FADE_LONGER.search(text) is not None:
        changes["fade_delta"] = _FADE_STEP
    elif _FADE_SHORTER.search(text) is not None:
        changes["fade_delta"] = -_FADE_STEP

    if (match := _TRANS.search(text)) is not None:
        raw = match.group("v").upper()
        changes["trans"] = {"스냅": "SNAP", "크로스페이드": "XFADE"}.get(match.group("v"), raw)
    elif _FADE_NONE.search(text) is not None:
        changes["trans"] = "SNAP"

    # t300 — `Trans: SNAP` 과 `fade 0` 은 **같은 물리 현상**이다(즉시 전환).
    # t293 은 `trans` 를 「초로 환산할 근거가 없다」며 콘솔에서 건너뛰었는데,
    # 그 환산이 없는 것은 XFADE·FADE 쪽이다 — SNAP 은 0초로 정확히 환산된다.
    # 그래서 여기서 접는다: SNAP 을 말한 문장은 페이드 0초도 말한 것으로 읽어,
    # 이미 실측된 `CueFade` 통로로 데스크에 닿게 한다. 환산을 `cue_sheet_apply`
    # 에 심지 않는 이유는 XFADE·FADE 의 거절 사유가 계속 참이어야 하기 때문이다.
    if changes.get("trans") == "SNAP" and not ({"fade_seconds", "fade_delta"} & changes.keys()):
        changes["fade_seconds"] = 0.0

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


def _group_levels(section: Mapping[str, object]) -> list[tuple[int, str, int]]:
    """구간의 그룹별 조도 — ``(칸 번호, 그룹 이름, 값)``. 없으면 빈 목록.

    「그룹별 값이 있다」가 **형태가 있다**는 뜻이다. 이 목록이 비면 이 구간에는
    지킬 간격 자체가 없고, 올림과 지정이 같은 동작이 된다.
    """
    entries = section.get("intensity")
    if not isinstance(entries, list):
        return []
    levels: list[tuple[int, str, int]] = []
    for slot, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            continue
        level = entry.get("level")
        if isinstance(level, bool) or not isinstance(level, (int, float)):
            continue
        levels.append((slot, str(entry.get("group") or f"#{slot + 1}"), int(level)))
    return levels


def _write_d_level(section: dict, percent: int) -> None:
    # d_level 은 1..5 축이다. 백분율을 그 축으로 환산해 같이 옮긴다 — 한쪽만
    # 고치면 화면(그룹별 값)과 폴리라인(d_level)이 서로 다른 값을 말한다.
    section["d_level"] = max(1, min(5, round(percent / _INTENSITY_STEP)))


def _per_group_report(levels: list[tuple[int, str, int]], after: dict[int, int]) -> str:
    return ", ".join(f"{name} {level}→{after[slot]}" for slot, name, level in levels)


def _set_intensity(section: dict, percent: int, report: list[str]) -> None:
    """**지정**: 모든 그룹을 같은 값으로 맞춘다 — 「조도 90으로」.

    그룹 간의 차이는 사라진다. 그것이 이 동사의 뜻이다(감독이 「전부 90」이라고
    말했으므로). 형태를 지키는 쪽은 :func:`_lift_intensity` 다.
    """
    before = section_intensity_percent(section)
    levels = _group_levels(section)
    entries = section.get("intensity")
    if levels and isinstance(entries, list):
        section["intensity"] = [
            {**entry, "level": percent} if isinstance(entry, Mapping) else entry
            for entry in entries
        ]
        after = {slot: percent for slot, _name, _level in levels}
        report.append(
            f"{EDITABLE_FIELD_LABELS['intensity']} 전체 {percent} (그룹 통일) — "
            + _per_group_report(levels, after)
        )
    else:
        report.append(f"{EDITABLE_FIELD_LABELS['intensity']} {before} → {percent}")
    _write_d_level(section, percent)


def _lift_intensity(section: dict, delta: int, report: list[str]) -> None:
    """**올림/내림**: 그룹 간 간격을 유지한 채로 통째로 옮긴다 — 「더 밝게」.

    산술은 **고정 오프셋**이다. 비례 배율이 아닌 이유: 비례는 어두운 그룹을
    거의 안 움직여(35 × 1.3 = 45.5) 감독이 「올렸다」고 느끼는 양과 어긋나고,
    되돌리기가 정확히 대칭이 아니다. 오프셋은 KEY−BACK 차이를 **글자 그대로**
    보존하고, 같은 크기의 반대 오프셋으로 정확히 되돌아온다.

    **천장·바닥에서**: 오프셋을 그룹마다 잘라 내면(clamp per group) 천장에 닿은
    그룹만 멈추고 나머지는 따라와 — 결국 형태가 다시 뭉개진다. 그래서 자르는
    것은 **한 걸음 전체**다: 가장 밝은 그룹이 100 을 넘게 되는 만큼 걸음을
    줄여 모두가 같은 양만큼 움직인다. 간격은 천장에서도 그대로 남고, 리포트가
    「요청 +20 → 천장 100에 맞춰 +10」처럼 줄어든 사실을 적는다. 더 갈 곳이
    없으면(걸음이 0) 조용히 통과시키지 않고 사유를 붙여 거절한다.
    """
    levels = _group_levels(section)
    if not levels:
        # 형태가 없다 — 지정과 같은 동작이고, 리포트도 기존 한 줄 그대로다.
        percent = section_intensity_percent(section) + delta
        percent = max(_INTENSITY_MIN, min(_INTENSITY_MAX, percent))
        _set_intensity(section, percent, report)
        return

    low = min(level for _slot, _name, level in levels)
    high = max(level for _slot, _name, level in levels)
    if delta > 0:
        effective = min(delta, _INTENSITY_MAX - high)
        limit = f"천장 {_INTENSITY_MAX}"
    else:
        effective = max(delta, _INTENSITY_MIN - low)
        limit = f"바닥 {_INTENSITY_MIN}"
    if effective == 0:
        raise CueSheetEditError(
            f"이 큐는 이미 {limit}에 닿아 있어 더 옮길 수 없습니다 "
            f"(그룹별 값: {', '.join(f'{name} {level}' for _slot, name, level in levels)})."
        )

    entries = list(section["intensity"])
    after: dict[int, int] = {}
    for slot, _name, level in levels:
        entry = entries[slot]
        after[slot] = level + effective
        entries[slot] = {**entry, "level": after[slot]}
    section["intensity"] = entries
    _write_d_level(section, high + effective)

    step = f"{effective:+d}"
    clipped = "" if effective == delta else f", 요청 {delta:+d} → {limit}에 맞춰 {step}"
    report.append(
        f"{EDITABLE_FIELD_LABELS['intensity']} {step} (그룹 간격 유지{clipped}) — "
        + _per_group_report(levels, after)
    )


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
        key
        for key in changes
        if key not in EDITABLE_FIELD_LABELS and key not in ("intensity_delta", "fade_delta")
    ]
    if unknown:
        editable = ", ".join(EDITABLE_FIELD_LABELS.values())
        raise CueSheetEditError(
            f"'{unknown[0]}'은(는) 큐시트가 가진 항목이 아닙니다. 수정 가능한 항목: {editable}."
        )

    slot, section = _find_section(timeline, cue_number)

    # --- 검증을 전부 끝낸 뒤에 쓴다 (부분 적용 금지) ---
    # 「지정」과 「올림」은 다른 지시다(t289). 지정은 모든 그룹을 한 값으로
    # 맞추고, 올림은 그룹 간 간격을 지킨 채 통째로 옮긴다. 둘을 한 숫자로
    # 합치면 「더 밝게」가 리그를 평평하게 만든다 — 그것이 이 갈래의 이유다.
    target_percent: int | None = None
    lift_delta: int | None = None
    if "intensity" in changes:
        raw = changes["intensity"]
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            raise CueSheetEditError(f"조도는 숫자여야 합니다 (받은 값: {raw!r}).")
        target_percent = int(raw)
        if not (_INTENSITY_MIN <= target_percent <= _INTENSITY_MAX):
            raise CueSheetEditError(
                f"조도는 {_INTENSITY_MIN}~{_INTENSITY_MAX} 사이여야 합니다 "
                f"(요청값: {target_percent})."
            )
    elif "intensity_delta" in changes:
        delta = changes["intensity_delta"]
        if not isinstance(delta, (int, float)) or isinstance(delta, bool):
            raise CueSheetEditError(f"조도 증감은 숫자여야 합니다 (받은 값: {delta!r}).")
        lift_delta = int(delta)

    if "trans" in changes:
        trans = changes["trans"]
        if not isinstance(trans, str) or trans.upper() not in TRANS_VALUES:
            raise CueSheetEditError(
                f"전환 값은 {', '.join(TRANS_VALUES)} 중 하나여야 합니다 (받은 값: {trans!r})."
            )

    fade_target: float | None = None
    if "fade_seconds" in changes:
        fade = changes["fade_seconds"]
        if not isinstance(fade, (int, float)) or isinstance(fade, bool):
            raise CueSheetEditError(f"페이드는 숫자여야 합니다 (받은 값: {fade!r}).")
        if not (0 <= float(fade) <= _FADE_MAX_SECONDS):
            raise CueSheetEditError(
                f"페이드는 0~{_FADE_MAX_SECONDS:g}초 사이여야 합니다 (요청값: {fade})."
            )
        fade_target = float(fade)
    elif "fade_delta" in changes:
        # 상대 페이드는 **기준값**을 요구한다. 값이 없는 큐에 「좀 길게」는
        # 0초를 가정하거나 기본값을 지어내야 답할 수 있고, 둘 다 감독이 말한
        # 적 없는 숫자다 — 그래서 사유를 붙여 거절한다(틀린 페이드보다 낫다).
        delta = changes["fade_delta"]
        if not isinstance(delta, (int, float)) or isinstance(delta, bool):
            raise CueSheetEditError(f"페이드 증감은 숫자여야 합니다 (받은 값: {delta!r}).")
        before_fade = section.get("fade_seconds")
        if not isinstance(before_fade, (int, float)) or isinstance(before_fade, bool):
            raise CueSheetEditError(
                "이 큐에는 기준이 될 페이드 값이 없어 「더 길게/짧게」를 계산할 수 "
                "없습니다 — 초를 적어 주세요 (예: '페이드 3초로')."
            )
        fade_target = max(0.0, min(_FADE_MAX_SECONDS, float(before_fade) + float(delta)))
        if fade_target == float(before_fade):
            limit = f"천장 {_FADE_MAX_SECONDS:g}초" if delta > 0 else "바닥 0초"
            raise CueSheetEditError(
                f"이 큐의 페이드는 이미 {limit}에 닿아 있어 더 옮길 수 없습니다 "
                f"(현재 {float(before_fade):g}초)."
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
    # 조도가 맨 앞이다. 「더 옮길 곳이 없다」 거절은 여기서 나며, 그 시점에는
    # 아직 아무 칸도 쓰지 않았으므로 부분 적용이 생기지 않는다.
    report: list[str] = []
    if target_percent is not None:
        _set_intensity(section, target_percent, report)
    elif lift_delta is not None:
        _lift_intensity(section, lift_delta, report)
    if "trans" in changes:
        before = section.get("trans")
        section["trans"] = str(changes["trans"]).upper()
        report.append(f"{EDITABLE_FIELD_LABELS['trans']} {before or '—'} → {section['trans']}")
    if fade_target is not None:
        before = section.get("fade_seconds")
        section["fade_seconds"] = fade_target
        line = (
            f"{EDITABLE_FIELD_LABELS['fade_seconds']} "
            f"{'—' if before is None else f'{float(before):g}초'} → {fade_target:g}초"
        )
        if "fade_delta" in changes:
            requested = float(changes["fade_delta"])
            actual = fade_target - float(before)
            line += f" ({actual:+g}초)"
            if actual != requested:
                limit = f"천장 {_FADE_MAX_SECONDS:g}초" if requested > 0 else "바닥 0초"
                line += f", 요청 {requested:+g}초 → {limit}에 맞춰 {actual:+g}초"
        report.append(line)
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

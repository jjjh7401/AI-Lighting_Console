# SPEC-LDDESIGN-001 M3 — 컬러 검사기 (REQ-LDDESIGN-027~031, 034, 카드 t436).
#
# 순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다.
#
# REQ-031 narrow reading(t436 배차 결정 1) — 이 모듈은 후렴 회차마다
# 보조색을 회전시키던 기존 로직(``server/web/session.py``)을 import 하거나
# 호출하지 않는다. 그 파일 자체를 고쳐 실제 출력 색을 바꾸는 일(REQ-004)은
# 이 SPEC의 M6 스코프이며 여기서는 건드리지 않는다 — 대신 정체성 판정
# (REQ-030 :func:`check_chorus_identity`)을 그 회전 로직에 전혀 기대지
# 않는 새 코드로 구현해, "그 경로에서 더 이상 호출되지 않는다"를 이
# 마일스톤이 만드는 새 코드의 성질로 만족시킨다.
#
# t409 흰색 경계(카드 t409) — ``server/design/color_names.py`` 의 색조
# 수식어 벗기기 정규식은 "warm"/"cold" 를 벗겨 Warm White 와 Cool White 를
# 같은 색으로 만든다. 이 모듈의 색 정체성 비교(:func:`_normalize_color_name`)
# 는 그 정규식을 쓰지 않는다 — 대소문자·공백만 정규화하고, 겉으로 다른 두
# 색 이름을 절대 합치지 않는다.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from server.concept.color_strip import ConceptCue

LintStatus = Literal["pass", "fail", "not_evaluated"]


def _normalize_color_name(name: str) -> str:
    """색 정체성 비교용 정규화 — 대소문자·공백만 접는다(t409 흰색 경계).
    ``color_names.py`` 의 ``_HUE_MODIFIER_STRIP`` 처럼 색조 수식어를
    벗기지 않는다 — 그러면 Warm White 와 Cool White 가 같아진다."""
    return " ".join(name.strip().casefold().split())


@dataclass(frozen=True)
class ColorLintViolation:
    """검사 위반 한 건 — 어느 구간·회차에서, 무엇이 문제였는지."""

    section: str
    occurrence: int
    detail: str


@dataclass(frozen=True)
class ColorLintResult:
    """검사 결과 — REQ-034 처럼 제약이 비어 있으면 ``not_evaluated`` 로
    보고한다(평가를 건너뛴 것과 평가해서 통과한 것을 구분한다 — 안 재고는
    "통과"라고 부르지 않는다)."""

    rule: str
    status: LintStatus
    violations: tuple[ColorLintViolation, ...] = ()

    @property
    def ok(self) -> bool:
        """``fail`` 이 아니면 참 — ``pass``/``not_evaluated`` 모두 게이트를
        막지 않는다는 뜻으로 쓴다."""
        return self.status != "fail"


@dataclass(frozen=True)
class Constraints:
    """REQ-034 — 의상·세트·LED·피부톤 등 고정 제약. 워크시트가 안 채운
    칸은 ``None``(또는 빈 문자열)로 두면 관련 린트가 평가되지 않는다."""

    costume: str | None = None
    set_design: str | None = None
    led_fixture: str | None = None
    skin_tone: str | None = None


def _section_cues(cues: Sequence[ConceptCue]) -> list[ConceptCue]:
    """구간 큐(``layer == "section"``)만 남긴다 — 프레이즈·원샷 큐는 컬러
    검사 대상이 아니다(REQ-033 과 같은 경계)."""
    return [cue for cue in cues if cue.layer == "section"]


# --- REQ-027 — 유보색은 해제 이전에 나타나면 위반 --------------------------


def check_reserved_color_release(
    cues: Sequence[ConceptCue],
    *,
    reserved: Sequence[str],
    release_section: str,
    release_occurrence: int | None = None,
) -> ColorLintResult:
    """REQ-027 — 유보색(``palette.reserved``)이 해제 큐(``release_section``,
    선택적으로 ``release_occurrence``) 이전에 나타나면 위반이다.

    ``cues`` 는 곡 진행 순서(시간순)로 이미 정렬돼 있다고 가정한다 — 실제
    파이프라인이 만드는 큐 목록의 자연스러운 순서이며, 이 함수는 그 순서를
    다시 만들지 않는다.
    """
    reserved_norm = {_normalize_color_name(color) for color in reserved}
    if not reserved_norm:
        return ColorLintResult(rule="reserved_color_release", status="pass")

    violations: list[ColorLintViolation] = []
    released = False
    for cue in _section_cues(cues):
        is_release_cue = cue.section == release_section and (
            release_occurrence is None or cue.occurrence == release_occurrence
        )
        if not released:
            cue_colors = {_normalize_color_name(color) for color in cue.colors}
            hit = cue_colors & reserved_norm
            if hit and not is_release_cue:
                violations.append(
                    ColorLintViolation(
                        section=cue.section,
                        occurrence=cue.occurrence,
                        detail=f"유보색 {sorted(hit)} 이 해제({release_section}) 전에 등장",
                    )
                )
        if is_release_cue:
            released = True

    status: LintStatus = "fail" if violations else "pass"
    return ColorLintResult(
        rule="reserved_color_release", status=status, violations=tuple(violations)
    )


# --- REQ-029 — 인접 구간 브리지: 공통색 최소 1개, 암전 전환은 예외 ---------


def check_adjacent_bridge(cues: Sequence[ConceptCue]) -> ColorLintResult:
    """REQ-029 — 인접한 두 구간 큐는 공통색을 최소 1개 유지한다. 단 두
    구간의 켜진 그룹 집합(``lit_group_ids``)이 전혀 겹치지 않으면(완전한
    암전 전환 등) 이 규칙을 적용하지 않는다."""
    section_cues = _section_cues(cues)
    violations: list[ColorLintViolation] = []
    for prev, curr in zip(section_cues, section_cues[1:], strict=False):
        both_have_groups = prev.lit_group_ids and curr.lit_group_ids
        if both_have_groups and not (prev.lit_group_ids & curr.lit_group_ids):
            continue  # 켜진 그룹 집합이 전혀 안 겹침 — 규칙 미적용
        prev_colors = {_normalize_color_name(color) for color in prev.colors}
        curr_colors = {_normalize_color_name(color) for color in curr.colors}
        if not (prev_colors & curr_colors):
            violations.append(
                ColorLintViolation(
                    section=curr.section,
                    occurrence=curr.occurrence,
                    detail=(
                        f"{prev.section}#{prev.occurrence} → {curr.section}#{curr.occurrence} "
                        "전환에 공통색 0개"
                    ),
                )
            )
    status: LintStatus = "fail" if violations else "pass"
    return ColorLintResult(
        rule="adjacent_bridge_shared_color", status=status, violations=tuple(violations)
    )


# --- REQ-030 — 후렴(Chorus) 전체 동일 주색, Final Chorus 예외 --------------

_CHORUS_IDENTITY_SECTION = "Chorus"


def check_chorus_identity(cues: Sequence[ConceptCue]) -> ColorLintResult:
    """REQ-030, AC-LDDESIGN-007/016 — 후렴(``Chorus``, Final Chorus 제외)
    구간 큐 전체가 동일한 주색(``colors[0]``)을 갖는지 검사한다."""
    chorus_cues = [cue for cue in _section_cues(cues) if cue.section == _CHORUS_IDENTITY_SECTION]
    if not chorus_cues:
        return ColorLintResult(rule="chorus_primary_color_identity", status="not_evaluated")

    primaries = {_normalize_color_name(cue.colors[0]) for cue in chorus_cues if cue.colors}
    if len(primaries) <= 1:
        return ColorLintResult(rule="chorus_primary_color_identity", status="pass")

    violations = tuple(
        ColorLintViolation(
            section=cue.section,
            occurrence=cue.occurrence,
            detail=(
                f"후렴 주색 불일치 — 이 큐 주색 {cue.colors[0]!r}, "
                f"전체 주색 집합 {sorted(primaries)}"
            ),
        )
        for cue in chorus_cues
        if cue.colors
    )
    return ColorLintResult(
        rule="chorus_primary_color_identity", status="fail", violations=violations
    )


# --- REQ-028 — 후렴 3회 이상이면 클라이맥스색 언더페인팅 최소 1회 ---------

_UNDERPAINTING_SECTIONS = frozenset({"Chorus", "Final Chorus"})
_UNDERPAINTING_MIN_OCCURRENCES = 3


def check_underpainting(cues: Sequence[ConceptCue], *, climax_color: str) -> ColorLintResult:
    """REQ-028 — 후렴(Chorus/Final Chorus) 구간이 3회 이상이면, 클라이맥스
    색이 채도를 낮춘 형태(``desaturated=True``)로 정식 등장보다 앞선
    구간에 최소 1회 심겨 있어야 한다. 후렴 3회 미만 곡, 또는 클라이맥스
    색이 아예 정식 등장하지 않는 픽스처는 평가 대상이 아니다."""
    section_cues = _section_cues(cues)
    chorus_like = [cue for cue in section_cues if cue.section in _UNDERPAINTING_SECTIONS]
    if len(chorus_like) < _UNDERPAINTING_MIN_OCCURRENCES:
        return ColorLintResult(rule="climax_underpainting", status="not_evaluated")

    climax_norm = _normalize_color_name(climax_color)

    first_full_index: int | None = None
    for index, cue in enumerate(section_cues):
        cue_colors = {_normalize_color_name(color) for color in cue.colors}
        if climax_norm in cue_colors and not cue.desaturated:
            first_full_index = index
            break
    if first_full_index is None:
        # 클라이맥스 색이 정식으로 전혀 등장하지 않음 — REQ-030 등 다른
        # 검사의 몫이지 이 검사가 판단할 대상이 아니다.
        return ColorLintResult(rule="climax_underpainting", status="not_evaluated")

    planted = any(
        cue.desaturated and climax_norm in {_normalize_color_name(color) for color in cue.colors}
        for cue in section_cues[:first_full_index]
    )
    if planted:
        return ColorLintResult(rule="climax_underpainting", status="pass")

    anchor = section_cues[first_full_index]
    return ColorLintResult(
        rule="climax_underpainting",
        status="fail",
        violations=(
            ColorLintViolation(
                section=anchor.section,
                occurrence=anchor.occurrence,
                detail=(
                    f"클라이맥스 색 {climax_color!r} 언더페인팅 0회(정식 등장 전 심긴 자리 없음)"
                ),
            ),
        ),
    )


# --- REQ-034 — 빈 제약은 관련 린트를 평가하지 않는다 ------------------------

#: 피부톤과 시각적으로 충돌하기 쉬운 색 — 이 SPEC 범위에서는 최소 한 종만
#: 다룬다(t436 배차 결정 4 — "스킵 기제 + 제약이 있을 때 도는 최소 규칙
#: 하나"만 필요, 피부톤 규칙 내용 자체는 이 SPEC 범위 밖).
_DEFAULT_SKIN_TONE_CLASH_COLORS = frozenset({"green"})


def check_skin_tone_clash(
    cues: Sequence[ConceptCue],
    *,
    constraints: Constraints,
    clashing_colors: frozenset[str] = _DEFAULT_SKIN_TONE_CLASH_COLORS,
) -> ColorLintResult:
    """REQ-034 — 피부톤 제약(``constraints.skin_tone``)이 비어 있으면 이
    린트는 평가하지 않는다("안 재고는 안 쓴다"). 제약이 있으면 충돌 색
    목록에 속한 색을 쓰는 구간 큐를 위반으로 기록한다."""
    if constraints.skin_tone is None or not constraints.skin_tone.strip():
        return ColorLintResult(rule="skin_tone_color_clash", status="not_evaluated")

    clash_norm = {_normalize_color_name(color) for color in clashing_colors}
    violations: list[ColorLintViolation] = []
    for cue in _section_cues(cues):
        cue_colors = {_normalize_color_name(color) for color in cue.colors}
        hit = cue_colors & clash_norm
        if hit:
            violations.append(
                ColorLintViolation(
                    section=cue.section,
                    occurrence=cue.occurrence,
                    detail=f"피부톤({constraints.skin_tone}) 충돌 색 {sorted(hit)}",
                )
            )
    status: LintStatus = "fail" if violations else "pass"
    return ColorLintResult(
        rule="skin_tone_color_clash", status=status, violations=tuple(violations)
    )

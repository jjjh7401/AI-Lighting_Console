# SPEC-LDDESIGN-001 M3 — Color Strip 산출 + 팔레트 해석
# (REQ-LDDESIGN-026, 032, 033, 035, 카드 t436).
#
# 순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다
# (plan.md M3 원칙, worksheet.py/vocab.py 와 동일).
#
# 큐 모델 v2(``layer``/``operation``/``tracking``/... 7필드, M2 스코프)는
# 다른 레인이 ``server/concept/cue_model.py``·``resolver.py``·
# ``description.py`` 로 병행 진행 중이다(t436 배차 결정 2) — 이 모듈은
# 그 타입을 import 하지 않고, Color Strip 산출과 컬러 검사기(``color_lint.py``)
# 가 함께 쓰는 최소 입력 타입 :class:`ConceptCue` 를 독립적으로 정의한다.
# M6 하류 배선(§3.6 "기존 하류 브리지")에서 실제 큐 모델 v2와 이 타입을
# 어떻게 연결할지 결정한다 — 이 SPEC의 이후 마일스톤 스코프다.

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from server.concept.worksheet import Palette

#: REQ-018 참고 — 구간/프레이즈/원샷 3층(§3.6, M4 스코프)의 이름을 그대로
#: 빌려 쓴다. 이 모듈은 "구간 큐만" 필터링(REQ-033)에 이 값을 쓴다.
Layer = Literal["section", "phrase", "one_shot"]


@dataclass(frozen=True)
class ConceptCue:
    """컨셉 계층(§3.5)이 소비하는 최소 큐 입력 — REQ-026~035 전용.

    실제 큐 모델 v2(§3.4, 7필드)의 부분집합이 아니라, 이 마일스톤의 컬러
    규칙·Color Strip 산출에 필요한 값만 담는 독립 타입이다(t436 배차
    결정 2). 필드:

    - ``section``: 9종 어휘(REQ-005) 중 하나 — 이 모듈은 값을 신뢰하고
      재검증하지 않는다(검증은 ``vocab.validate_section`` 의 몫).
    - ``occurrence``: 그 구간의 회차 번호.
    - ``layer``: 구간/프레이즈/원샷 중 하나(REQ-033 필터링에 쓰인다).
    - ``colors``: 이 큐가 쓰는 색 이름들, 순서가 있다 — 0번째가 주색.
    - ``max_brightness``: 이 큐의 최대 밝기(REQ-026 "최대 밝기").
    - ``lit_groups``/``total_groups``: 켜진 그룹 수/전체 그룹 수 —
      면적(REQ-026 "켜진 그룹 비율=면적") 계산에 쓴다.
    - ``intent``: 의도 한 문장(REQ-026).
    - ``desaturated``: 이 큐의 색이 채도를 낮춘 "언더페인팅" 형태인지
      (REQ-028) — 실제 채도값(HSV 등) 계산은 이 SPEC 범위 밖이라 불리언
      플래그로만 표현한다(t436 배차 결정 8, 설계 선택을 여기 명시한다).
    - ``lit_group_ids``: 켜진 그룹의 식별자 집합 — REQ-029 브리지 검사의
      "켜진 그룹 집합이 전혀 겹치지 않으면" 판정에 쓴다. 비어 있으면(기본값)
      그 판정은 건너뛰고 색 공유만으로 브리지를 검사한다.
    """

    section: str
    occurrence: int
    layer: Layer
    colors: tuple[str, ...]
    max_brightness: float
    lit_groups: int
    total_groups: int
    intent: str = ""
    desaturated: bool = False
    lit_group_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ColorStripEntry:
    """Color Strip 한 칸 — 구간 하나의 주색·보조색·최대 밝기·면적·의도
    (REQ-026)."""

    section: str
    occurrence: int
    primary_color: str
    secondary_color: str | None
    max_brightness: float
    area: float
    intent: str


def compute_color_strip(cues: Sequence[ConceptCue]) -> tuple[ColorStripEntry, ...]:
    """REQ-026, REQ-033/AC-LDDESIGN-031 — 구간 큐(``layer == "section"``)만
    대상으로 Color Strip 을 산출한다. 프레이즈·원샷 큐는 조용히 제외한다."""
    entries: list[ColorStripEntry] = []
    for cue in cues:
        if cue.layer != "section":
            continue
        primary = cue.colors[0] if cue.colors else ""
        secondary = cue.colors[1] if len(cue.colors) > 1 else None
        area = cue.lit_groups / cue.total_groups if cue.total_groups else 0.0
        entries.append(
            ColorStripEntry(
                section=cue.section,
                occurrence=cue.occurrence,
                primary_color=primary,
                secondary_color=secondary,
                max_brightness=cue.max_brightness,
                area=area,
                intent=cue.intent,
            )
        )
    return tuple(entries)


def render_concept_bullet(concept_text: str) -> str:
    """REQ-032, AC-LDDESIGN-046 — 워크시트 ``concept`` 필드의 인과 불릿을
    요약·재작성 없이 그대로 돌려준다(순수 항등 함수 — 컴파일 과정에서
    손대지 않는다는 계약을 코드로 못박는다)."""
    return concept_text


# --- REQ-035 — 팔레트 4칸 미입력 시 인터뷰 답변으로 자동 초안 --------------


@dataclass(frozen=True)
class PaletteDraft:
    """REQ-035 — 팔레트 해석 결과. ``auto_draft`` 가 참이면 워크시트가
    비어 있어 인터뷰 답변으로 채운 초안이라는 뜻이다(REQ-009 "감독 확인"
    표시와 같은 방향 — 조용히 채우지 않고 초안임을 노출한다)."""

    palette: Palette
    auto_draft: bool


def is_palette_blank(palette: Palette | None) -> bool:
    """팔레트가 아예 없거나(``None``), 필수 3칸(primary/secondary/climax)
    중 공백만 있는 칸이 하나라도 있으면 "비었다"로 본다."""
    if palette is None:
        return True
    return not (palette.primary.strip() and palette.secondary.strip() and palette.climax.strip())


#: Q2 인터뷰 답변(색 경향 자유 문자열, ``server/design/interview.py`` 의
#: ``_palette_value_tokens`` 와 같은 구분자 집합)을 색 토큰으로 쪼갠다.
#: 그 함수를 직접 import 하지 않는다 — private 헬퍼(밑줄 접두)라 이
#: 모듈이 기대는 계약이 아니고, M3 은 워크시트 파싱을 건드리지 않으므로
#: interview.py 에도 의존하지 않는 독립 재구현으로 남긴다(t436 배차
#: 결정 5).
_COLOR_TOKEN_SPLIT = re.compile(r"[/,、=+·\s]+")
_JOIN_PARTICLES = ("이랑", "하고", "랑", "와", "과")


def _split_interview_color_tokens(value: str) -> tuple[str, ...]:
    chunks = _COLOR_TOKEN_SPLIT.split(value)
    tokens: list[str] = []
    for chunk in chunks:
        cleaned = chunk.strip()
        if not cleaned:
            continue
        for particle in _JOIN_PARTICLES:
            if len(cleaned) > len(particle) and cleaned.endswith(particle):
                cleaned = cleaned[: -len(particle)]
                break
        if cleaned and cleaned not in tokens:
            tokens.append(cleaned)
    return tuple(tokens)


def draft_palette_from_interview(q2_answer: str) -> Palette:
    """REQ-035 — Q2 인터뷰 답변(색 경향 문자열)을 팔레트 초안으로 바꾼다.

    첫 토큰이 주색, 둘째 토큰이 보조색(하나뿐이면 주색과 같음), 마지막
    토큰이 클라이맥스 색이자 유보색 기본값이다(REQ-012 의 ``reserved``
    기본값 규칙과 같은 방향).
    """
    tokens = _split_interview_color_tokens(q2_answer)
    if not tokens:
        raise ValueError("인터뷰 답변에서 색 토큰을 하나도 못 찾음: " + repr(q2_answer))
    primary = tokens[0]
    secondary = tokens[1] if len(tokens) > 1 else tokens[0]
    climax = tokens[-1]
    return Palette(primary=primary, secondary=secondary, climax=climax, reserved=(climax,))


def resolve_palette(palette: Palette | None, *, interview_q2_answer: str | None) -> PaletteDraft:
    """REQ-035, AC-LDDESIGN-047 — 워크시트 팔레트가 채워져 있으면 그대로
    쓰고(``auto_draft=False``), 비어 있으면 인터뷰 Q2 답변으로 초안을
    만든다(``auto_draft=True``). 인터뷰 답변도 없으면 초안을 만들 수
    없다는 뜻이므로 예외를 던진다 — 지어내지 않는다."""
    if not is_palette_blank(palette):
        assert palette is not None  # is_palette_blank(None) 은 항상 True
        return PaletteDraft(palette=palette, auto_draft=False)
    if interview_q2_answer is None or not interview_q2_answer.strip():
        raise ValueError("팔레트가 비었고 인터뷰 답변도 없어 초안을 만들 수 없음")
    return PaletteDraft(palette=draft_palette_from_interview(interview_q2_answer), auto_draft=True)

# SPEC-LDDESIGN-001 M1 — 닫힌 어휘(vocabulary) 정의 (REQ-LDDESIGN-005~010).
#
# 순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다
# (plan.md M3 "server/concept/ 패키지 신설" 원칙을 M1 부터 지킨다).

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


class VocabError(ValueError):
    """닫힌 어휘 위반 — spec.md §3.2 (REQ-005~007) · §3.3 REQ-016.

    ``server/looks/songcue.py`` 의 ``SongCueBundleError`` 와 같은 모양으로
    ``reason`` 을 속성으로 남긴다 — 메시지 문자열만이 아니라 원인을 구조로도
    쥘 수 있게 한다.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


# --- REQ-005 — 구간 어휘, 정확히 9종, 닫힘 ---------------------------------

SECTIONS: tuple[str, ...] = (
    "Intro",
    "Verse",
    "Pre-Chorus",
    "Chorus",
    "Post-Chorus",
    "Bridge",
    "Rap/Solo/Dance Break",
    "Final Chorus",
    "Outro",
)
_SECTIONS_SET = frozenset(SECTIONS)


def validate_section(value: str) -> str:
    """REQ-005/016 — 9종 밖의 이름이면 조립을 거부한다."""
    if value not in _SECTIONS_SET:
        raise VocabError(f"section: 닫힌 어휘(9종) 밖의 값 {value!r}")
    return value


# --- REQ-006 — 트리거 어휘, 정확히 10 토큰, 닫힘 ----------------------------
#
# 문서 8항목 중 "보컬 시작/종료" · "악기 추가/제거" 를 각각 독립 토큰으로
# 분리해 실제로는 10 토큰이 된다(spec.md REQ-LDDESIGN-006 괄호주).

TRIGGERS: tuple[str, ...] = (
    "보컬 시작",
    "보컬 종료",
    "악기 추가",
    "악기 제거",
    "코드·조성 변화",
    "빌드업 시작",
    "드롭 직전의 정적",
    "핵심 가사",
    "안무 대형 변화",
    "중심 멤버·솔로 변경",
)
_TRIGGERS_SET = frozenset(TRIGGERS)


def validate_trigger(value: str) -> str:
    """REQ-006/016 — 10 토큰 밖의 이름이면 조립을 거부한다."""
    if value not in _TRIGGERS_SET:
        raise VocabError(f"trigger: 닫힌 어휘(10종) 밖의 값 {value!r}")
    return value


# --- REQ-010 — 오디오 분석으로 검출 불가능한 트리거 4종 ---------------------
#
# 이 4종은 감독이 워크시트에 직접 적는 자유 선택지로만 존재하고, 자동
# 생성되지 않는다(§3.3 워크시트 로더·§4 이후 자동 생성기가 함께 지켜야
# 하는 불변식 — M1 은 이 구분을 어휘 수준에서 인코딩만 한다).

DIRECTOR_ONLY_TRIGGERS: frozenset[str] = frozenset(
    {
        "코드·조성 변화",
        "핵심 가사",
        "안무 대형 변화",
        "중심 멤버·솔로 변경",
    }
)


def is_director_only_trigger(trigger: str) -> bool:
    """REQ-010 — 이 트리거가 오디오 분석 검출 불가·감독 전용 입력인지."""
    return trigger in DIRECTOR_ONLY_TRIGGERS


# --- REQ-007 — 원샷 어휘, 정확히 7종, 닫힘 ----------------------------------
#
# 문면 확인: "Kick·Snare·Cymbal accent" 는 내부 구분자 "·"(공백 없음)로
# 세 타악기를 하나의 원샷 개념으로 묶은 **단일 항목**이다 — 항목 사이
# 구분자는 공백을 낀 " · " 다. spec.md 의 Out of Scope 절이 "원샷 어휘
# 7종 중 Kick·Snare·Cymbal accent(...), Color bump(...), Position
# snap(...)" 로 이 항목을 7종 중 하나로 다시 명시한다(spec.md:379) —
# 문면과 열거 개수가 불일치하는 결함이 아니라 7종이 맞다(이 판단의
# 근거는 완료 보고서의 Claim/Evidence 절에 그대로 옮긴다).

ONE_SHOTS: tuple[str, ...] = (
    "Kick·Snare·Cymbal accent",
    "Dimmer bump",
    "White hit",
    "짧은 Strobe",
    "Color bump",
    "Position snap",
    "Blinder hit",
)
_ONE_SHOTS_SET = frozenset(ONE_SHOTS)


def validate_one_shot(value: str) -> str:
    """REQ-007/016 — 7종 밖의 이름이면 조립을 거부한다."""
    if value not in _ONE_SHOTS_SET:
        raise VocabError(f"shot: 닫힌 어휘(7종) 밖의 값 {value!r}")
    return value


# --- REQ-019(§3.5) — `operation` 필드가 참조하는 동작 어휘 9종 -------------
#
# 값 자체의 실행 의미(§3.5 해석기)는 M2 스코프다. M1 은 워크시트
# `operation` 필드(REQ-014)를 검증하는 데만 이 상수를 쓴다.

OPERATIONS: tuple[str, ...] = (
    "retain",
    "add",
    "remove",
    "reduce",
    "replace",
    "isolate",
    "expand",
    "restore",
    "release",
)
_OPERATIONS_SET = frozenset(OPERATIONS)


def validate_operation(value: str) -> str:
    """REQ-019/016 — 9종 밖의 이름이면 조립을 거부한다."""
    if value not in _OPERATIONS_SET:
        raise VocabError(f"operation: 닫힌 어휘(9종) 밖의 값 {value!r}")
    return value


# --- REQ-008/009 — 구간 판정기 재매핑 계층 ---------------------------------
#
# 실측 출처: ``server/web/session.py`` 의 ``_infer_confirmed_role``
# (835~861행) 구현 + 그 아래 ``_CONFIRMED_ROLE_DISPLAY_NAME`` 주석
# (866행 부근) — "`_infer_confirmed_role` 이 내는 역할 5종만 다루면
# 되므로 "other" 는 방어적으로만 존재한다"(구간 개수 0인 경우의 방어
# 분기 전용이라 정식 5종에 넣지 않는다).

CLASSIFIER_ROLES: tuple[str, ...] = ("intro", "verse", "chorus", "bridge", "finale")
_CLASSIFIER_ROLES_SET = frozenset(CLASSIFIER_ROLES)

# 판정기 원시 역할 → 9종 어휘 기본 매핑. "chorus" 는 마지막 발생 여부에
# 따라 Chorus/Final Chorus 로 갈리므로 이 표에는 없고
# :func:`remap_classifier_role` 안에서 별도 분기한다.
_CLASSIFIER_TO_SECTION: Mapping[str, str] = {
    "intro": "Intro",
    "verse": "Verse",
    "bridge": "Bridge",
    "finale": "Outro",
}

# 이 판정기 원시 역할 → 어휘 변환에는 REQ-009 "감독 확인" 표시가 붙는다.
# 근거: reports/vocab-closed-verification-20260921.md 11행 — "판정기
# 이름 → 문서 어휘 재매핑 곡당 1~2건(마지막 Chorus → Final Chorus,
# Finale → Outro) ... 감독 확인 표시가 붙어 나온다." 단순 표기 정규화
# (intro→Intro, verse→Verse, bridge→Bridge, 비-마지막 chorus→Chorus)는
# 재매핑이 아니라 표시 이름 정규화일 뿐이라 플래그를 세우지 않는다.
_DIRECTOR_CONFIRM_ROLES: frozenset[str] = frozenset({"finale"})


@dataclass(frozen=True)
class RemappedSection:
    """REQ-008/009 — 판정기 원시 역할 하나를 9종 어휘로 재매핑한 결과.

    Attributes:
        section: 9종 어휘 중 하나(REQ-005).
        original: 판정기가 낸 원래 역할 이름 — 그대로 보존한다(REQ-008).
        director_confirm: "감독 확인" 표시 여부(REQ-009). 렌더링은 M7 스코프 —
            M1 은 플래그를 정의하고 세우기만 한다.
    """

    section: str
    original: str
    director_confirm: bool


def remap_classifier_role(role: str, *, is_last_chorus: bool = False) -> RemappedSection:
    """판정기 원시 역할 하나를 9종 어휘로 재매핑한다(REQ-008/009).

    ``is_last_chorus`` 는 호출자가(또는 :func:`remap_classifier_roles` 가)
    전체 구간 순서에서 이 chorus 가 마지막 chorus 인지 판정해 넘긴다 —
    단일 역할 하나만으로는 "마지막" 여부를 알 수 없기 때문이다.
    """
    if role not in _CLASSIFIER_ROLES_SET:
        raise VocabError(
            f"classifier role: 판정기 5종({', '.join(CLASSIFIER_ROLES)}) 밖의 값 {role!r}"
        )
    if role == "chorus":
        if is_last_chorus:
            return RemappedSection(section="Final Chorus", original=role, director_confirm=True)
        return RemappedSection(section="Chorus", original=role, director_confirm=False)
    section = _CLASSIFIER_TO_SECTION[role]
    director_confirm = role in _DIRECTOR_CONFIRM_ROLES
    return RemappedSection(section=section, original=role, director_confirm=director_confirm)


def remap_classifier_roles(roles: Sequence[str]) -> list[RemappedSection]:
    """판정기 원시 역할 시퀀스 전체를 재매핑한다 — 마지막 chorus 자동 판정.

    "마지막 Chorus → Final Chorus"(REQ-008 예시)를 판정하려면 구간 전체
    순서가 필요하다: ``roles`` 중 값이 ``"chorus"`` 인 마지막 인덱스만
    Final Chorus 로 승급한다.
    """
    last_chorus_index: int | None = None
    for index, role in enumerate(roles):
        if role == "chorus":
            last_chorus_index = index
    return [
        remap_classifier_role(role, is_last_chorus=(index == last_chorus_index))
        for index, role in enumerate(roles)
    ]

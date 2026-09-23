"""트래킹 4모드 기본값 배정 — SPEC-LDDESIGN-001 M5 (REQ-LDDESIGN-053~057).

값 자체(4모드: block/track/cue_only/release)의 검증과 해석기 경계 보장
(REQ-057 — cue_only 큐가 다음 큐로 전파되지 않는다)은 이미
:mod:`server.concept.cue_model`/:mod:`server.concept.resolver`(M2)가
갖고 있다 — 이 파일은 REQ-053~056 이 요구하는 큐 종류별 **기본값
배정 규칙**과, 그 경계가 실제로 지켜졌는지 프로퍼티로 확인하는
:func:`verify_no_cue_only_leak` 만 담당한다(두 번째 해석기를 만들지
않는다).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from server.concept.cue_model import validate_tracking
from server.concept.resolver import resolve_sequence

__all__ = [
    "CUE_KIND_SAFETY_FIRST",
    "CUE_KIND_SAFETY_LAST",
    "CUE_KIND_SECTION",
    "CUE_KIND_PHRASE",
    "default_tracking",
    "verify_no_cue_only_leak",
]

# 안전 큐 둘은 "구간"·"프레이즈"가 아닌 별도 종류다(REQ-054) — 곡의 첫
# 큐/마지막 큐 자리라는 위치로 구분되지, 9종 구간 어휘의 일부가 아니다.
CUE_KIND_SAFETY_FIRST = "safety_first"
CUE_KIND_SAFETY_LAST = "safety_last"
CUE_KIND_SECTION = "section"
CUE_KIND_PHRASE = "phrase"

_DEFAULTS: Mapping[str, str] = {
    CUE_KIND_SAFETY_FIRST: "block",  # REQ-054 — 앞 곡 잔존 차단
    CUE_KIND_SAFETY_LAST: "release",  # REQ-054 — 제어 반환
    CUE_KIND_SECTION: "track",  # REQ-055
    CUE_KIND_PHRASE: "cue_only",  # REQ-056 — Track 이면 구간이 끝난 뒤에도 새어 나간다
}


def default_tracking(cue_kind: str) -> str:
    """REQ-053~056 — 큐 종류별 기본 tracking 값을 낸다.

    Raises:
        ValueError: ``cue_kind`` 가 4종(안전 처음·안전 끝·구간·프레이즈)
            밖의 값이면.
    """
    try:
        value = _DEFAULTS[cue_kind]
    except KeyError as exc:
        raise ValueError(f"default_tracking: 알 수 없는 cue_kind {cue_kind!r}") from exc
    return validate_tracking(value)


def verify_no_cue_only_leak(rows: Sequence[Mapping[str, object]]) -> bool:
    """REQ-057/AC-LDDESIGN-015 — cue_only 큐의 값이 다음 큐로 새지 않았는지
    프로퍼티로 확인한다.

    방법: ``rows`` 를 그대로 해석한 결과에서 cue_only 행의 상태를 빼고 남은
    행들의 상태와, ``rows`` 에서 cue_only 행 자체를 아예 제거하고 다시
    해석한 결과를 비교한다. cue_only 행이 다음 큐로 값을 새게 하지
    않는다면 두 결과는 완전히 같아야 한다 — 다르면 새어 나간 것이다.
    (이 판정 자체는 :func:`server.concept.resolver.resolve_sequence` 를
    두 번 호출할 뿐, 새 해석 로직을 만들지 않는다.)
    """
    with_cue_only = resolve_sequence(rows)
    without_rows = [row for row in rows if row.get("tracking") != "cue_only"]
    without_cue_only = resolve_sequence(without_rows)
    kept_states = [
        state
        for row, state in zip(rows, with_cue_only, strict=True)
        if row.get("tracking") != "cue_only"
    ]
    return kept_states == without_cue_only

from __future__ import annotations

from types import MappingProxyType

from server.vwx.diff import MULTI_SYSTEM_MAPPING_ABSENT

COMPARISON_NOT_PERFORMED = "comparison_not_performed"
INVALID_REPORT_PAYLOAD = "invalid_report_payload"

UNKNOWN_CANDIDATE_ID = "unknown_candidate_id"

CANDIDATE_REJECTION_REASON = frozenset(
    {
        COMPARISON_NOT_PERFORMED,
        INVALID_REPORT_PAYLOAD,
        MULTI_SYSTEM_MAPPING_ABSENT,
    }
)
SELECTION_ERROR_REASON = frozenset({UNKNOWN_CANDIDATE_ID})

AUTOPATCH_CLOSED_VOCABULARIES = MappingProxyType(
    {
        "candidate_rejection_reason": CANDIDATE_REJECTION_REASON,
        "selection_error_reason": SELECTION_ERROR_REASON,
    }
)


class UnknownAutopatchVerdict(ValueError):
    pass


def validate_autopatch(vocabulary: str, value: str) -> str:
    try:
        allowed = AUTOPATCH_CLOSED_VOCABULARIES[vocabulary]
    except KeyError:
        raise UnknownAutopatchVerdict(
            f"no such autopatch vocabulary {vocabulary!r} "
            f"(known: {sorted(AUTOPATCH_CLOSED_VOCABULARIES)})"
        ) from None
    if value not in allowed:
        raise UnknownAutopatchVerdict(
            f"{value!r} is not a {vocabulary} (allowed: {sorted(allowed)})"
        )
    return value


_CANDIDATE_REJECTION_LABELS = {
    COMPARISON_NOT_PERFORMED: "1단계 콘솔 대조 미수행 리포트",
    INVALID_REPORT_PAYLOAD: "패치 후보 입력으로 쓸 수 없는 리포트 payload",
    MULTI_SYSTEM_MAPPING_ABSENT: "멀티시스템 매핑 부재로 콘솔 대조 미수행",
}
_SELECTION_ERROR_LABELS = {
    UNKNOWN_CANDIDATE_ID: "존재하지 않는 패치 후보 식별자",
}

_AUTOPATCH_VOCABULARY_LABELS = MappingProxyType(
    {
        "candidate_rejection_reason": MappingProxyType(_CANDIDATE_REJECTION_LABELS),
        "selection_error_reason": MappingProxyType(_SELECTION_ERROR_LABELS),
    }
)

if set(_AUTOPATCH_VOCABULARY_LABELS) != set(AUTOPATCH_CLOSED_VOCABULARIES):
    raise UnknownAutopatchVerdict(
        "autopatch label tables and closed vocabularies disagree: "
        f"tables {sorted(_AUTOPATCH_VOCABULARY_LABELS)} vs vocabularies "
        f"{sorted(AUTOPATCH_CLOSED_VOCABULARIES)}"
    )
for _autopatch_vocabulary, _autopatch_codes in AUTOPATCH_CLOSED_VOCABULARIES.items():
    if set(_AUTOPATCH_VOCABULARY_LABELS[_autopatch_vocabulary]) != set(_autopatch_codes):
        raise UnknownAutopatchVerdict(
            f"autopatch label table for {_autopatch_vocabulary} mismatches its vocabulary"
        )


def autopatch_label(vocabulary: str, code: str) -> str:
    validate_autopatch(vocabulary, code)
    return _AUTOPATCH_VOCABULARY_LABELS[vocabulary][code]


def candidate_rejection_label(code: str) -> str:
    return autopatch_label("candidate_rejection_reason", code)


def selection_error_label(code: str) -> str:
    return autopatch_label("selection_error_reason", code)

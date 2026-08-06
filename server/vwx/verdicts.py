from __future__ import annotations

from types import MappingProxyType

from server.vwx.diff import MULTI_SYSTEM_MAPPING_ABSENT

COMPARISON_NOT_PERFORMED = "comparison_not_performed"
INVALID_REPORT_PAYLOAD = "invalid_report_payload"

UNKNOWN_CANDIDATE_ID = "unknown_candidate_id"

FID_RANGE_REQUIRED = "fid_range_required"
INVALID_FID_RANGE = "invalid_fid_range"
FID_RANGE_CONFIRMATION_REQUIRED = "fid_range_confirmation_required"

FID_RANGE_EXHAUSTED = "fid_range_exhausted"
FID_ALREADY_IN_USE = "fid_already_in_use"

FID_CONFLICT_PRECHECK_DESCOPE = "fid_conflict_precheck_descope"

CANDIDATE_REJECTION_REASON = frozenset(
    {
        COMPARISON_NOT_PERFORMED,
        INVALID_REPORT_PAYLOAD,
        MULTI_SYSTEM_MAPPING_ABSENT,
    }
)
SELECTION_ERROR_REASON = frozenset({UNKNOWN_CANDIDATE_ID})
FID_ASSIGNMENT_REJECTION_REASON = frozenset(
    {
        FID_RANGE_REQUIRED,
        INVALID_FID_RANGE,
        FID_RANGE_CONFIRMATION_REQUIRED,
    }
)
TARGET_EXCLUSION_REASON = frozenset({FID_RANGE_EXHAUSTED, FID_ALREADY_IN_USE})
SKIPPED_CHECK_KIND = frozenset({FID_CONFLICT_PRECHECK_DESCOPE})

AUTOPATCH_CLOSED_VOCABULARIES = MappingProxyType(
    {
        "candidate_rejection_reason": CANDIDATE_REJECTION_REASON,
        "fid_assignment_rejection_reason": FID_ASSIGNMENT_REJECTION_REASON,
        "selection_error_reason": SELECTION_ERROR_REASON,
        "skipped_check_kind": SKIPPED_CHECK_KIND,
        "target_exclusion_reason": TARGET_EXCLUSION_REASON,
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
_FID_ASSIGNMENT_REJECTION_LABELS = {
    FID_RANGE_REQUIRED: "빈 FID 범위 미제공",
    INVALID_FID_RANGE: "빈 FID 범위 형식 오류",
    FID_RANGE_CONFIRMATION_REQUIRED: "FID 범위 육안 확인 미제공",
}
_TARGET_EXCLUSION_LABELS = {
    FID_RANGE_EXHAUSTED: "빈 FID 범위 초과",
    FID_ALREADY_IN_USE: "기존 FID와 충돌",
}
_SKIPPED_CHECK_LABELS = {
    FID_CONFLICT_PRECHECK_DESCOPE: "FID 충돌 사전검사 미수행",
}

_AUTOPATCH_VOCABULARY_LABELS = MappingProxyType(
    {
        "candidate_rejection_reason": MappingProxyType(_CANDIDATE_REJECTION_LABELS),
        "fid_assignment_rejection_reason": MappingProxyType(_FID_ASSIGNMENT_REJECTION_LABELS),
        "selection_error_reason": MappingProxyType(_SELECTION_ERROR_LABELS),
        "skipped_check_kind": MappingProxyType(_SKIPPED_CHECK_LABELS),
        "target_exclusion_reason": MappingProxyType(_TARGET_EXCLUSION_LABELS),
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


def fid_assignment_rejection_label(code: str) -> str:
    return autopatch_label("fid_assignment_rejection_reason", code)


def target_exclusion_label(code: str) -> str:
    return autopatch_label("target_exclusion_reason", code)


def skipped_check_label(code: str) -> str:
    return autopatch_label("skipped_check_kind", code)

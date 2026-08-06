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

FIXTURE_TYPE_NOT_IN_LIBRARY = "fixture_type_not_in_library"
DMX_MODE_NOT_IN_LIBRARY = "dmx_mode_not_in_library"

ADDRESS_ALREADY_OCCUPIED = "address_already_occupied"
ADDRESS_OVERLAP_IN_PLAN = "address_overlap_in_plan"
FOOTPRINT_UNKNOWN = "footprint_unknown"

FID_NOT_ASSIGNED = "fid_not_assigned"
FIXTURE_NAME_MISSING = "fixture_name_missing"
TYPE_CONFIRMATION_PENDING = "type_confirmation_pending"
LUA_GENERATION_REFUSED = "lua_generation_refused"

ALREADY_PATCHED_IDENTICAL = "already_patched_identical"
ADDRESS_CONFLICTS_WITH_EXISTING = "address_conflicts_with_existing_fixture"
EXISTING_IDENTITY_UNCONFIRMED = "existing_fixture_identity_unconfirmed"
CONSOLE_READ_INCOMPLETE = "console_read_incomplete"

FID_CONFLICT_PRECHECK_DESCOPE = "fid_conflict_precheck_descope"
FOOTPRINT_MATCH_DESCOPE = "footprint_match_descope"
FIXTURE_TYPE_LIBRARY_TRUNCATED = "fixture_type_library_truncated"
FIXTURE_TYPE_LIBRARY_UNREADABLE = "fixture_type_library_unreadable"

TYPE_RESOLVED = "resolved"
TYPE_NEEDS_CONFIRMATION = "needs_confirmation"
TYPE_LIBRARY_ABSENT = "library_absent"
TYPE_LIBRARY_INCOMPLETE = "library_incomplete"

VERIFICATION_OBSERVED = "observed"
VERIFICATION_NOT_OBSERVED = "not_observed"
VERIFICATION_MISMATCHED = "mismatched"
VERIFICATION_IDENTITY_UNCONFIRMED = "identity_unconfirmed"

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
TARGET_EXCLUSION_REASON = frozenset(
    {
        FID_RANGE_EXHAUSTED,
        FID_ALREADY_IN_USE,
        FIXTURE_TYPE_NOT_IN_LIBRARY,
        DMX_MODE_NOT_IN_LIBRARY,
        ADDRESS_ALREADY_OCCUPIED,
        ADDRESS_OVERLAP_IN_PLAN,
        FOOTPRINT_UNKNOWN,
        FID_NOT_ASSIGNED,
        FIXTURE_NAME_MISSING,
        TYPE_CONFIRMATION_PENDING,
        LUA_GENERATION_REFUSED,
        ALREADY_PATCHED_IDENTICAL,
        ADDRESS_CONFLICTS_WITH_EXISTING,
        EXISTING_IDENTITY_UNCONFIRMED,
        CONSOLE_READ_INCOMPLETE,
    }
)
SKIPPED_CHECK_KIND = frozenset(
    {
        FID_CONFLICT_PRECHECK_DESCOPE,
        FOOTPRINT_MATCH_DESCOPE,
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
    }
)
TYPE_RESOLUTION_STATUS = frozenset(
    {
        TYPE_RESOLVED,
        TYPE_NEEDS_CONFIRMATION,
        TYPE_LIBRARY_ABSENT,
        TYPE_LIBRARY_INCOMPLETE,
    }
)
VERIFICATION_OUTCOME = frozenset(
    {
        VERIFICATION_OBSERVED,
        VERIFICATION_NOT_OBSERVED,
        VERIFICATION_MISMATCHED,
        VERIFICATION_IDENTITY_UNCONFIRMED,
    }
)

AUTOPATCH_CLOSED_VOCABULARIES = MappingProxyType(
    {
        "candidate_rejection_reason": CANDIDATE_REJECTION_REASON,
        "fid_assignment_rejection_reason": FID_ASSIGNMENT_REJECTION_REASON,
        "selection_error_reason": SELECTION_ERROR_REASON,
        "skipped_check_kind": SKIPPED_CHECK_KIND,
        "target_exclusion_reason": TARGET_EXCLUSION_REASON,
        "type_resolution_status": TYPE_RESOLUTION_STATUS,
        "verification_outcome": VERIFICATION_OUTCOME,
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
    FIXTURE_TYPE_NOT_IN_LIBRARY: "콘솔 라이브러리에 대응 FixtureType 없음",
    DMX_MODE_NOT_IN_LIBRARY: "콘솔 라이브러리에 대응 DMXMode 없음",
    ADDRESS_ALREADY_OCCUPIED: "도면 주소가 콘솔에서 이미 점유됨",
    ADDRESS_OVERLAP_IN_PLAN: "같은 유니버스 안에서 다른 계획 항목과 점유 구간이 겹침",
    FOOTPRINT_UNKNOWN: "점유폭 미확정 — 추측하지 않고 제외",
    FID_NOT_ASSIGNED: "FID 미배정 — 배정 없이 생성하지 않음",
    FIXTURE_NAME_MISSING: "픽스처 이름 미제공 — 이름을 지어내지 않고 제외",
    TYPE_CONFIRMATION_PENDING: "타입·모드 사용자 확인 대기 — 확인 전에는 전달하지 않음",
    LUA_GENERATION_REFUSED: "Lua 생성기가 이름을 거부 — 조용히 고치지 않고 제외",
    ALREADY_PATCHED_IDENTICAL: "네 값이 모두 일치하는 픽스처가 이미 있음 — 멱등 건너뜀",
    ADDRESS_CONFLICTS_WITH_EXISTING: "같은 주소를 타입 또는 모드가 다른 픽스처가 점유 — 충돌",
    EXISTING_IDENTITY_UNCONFIRMED: (
        "같은 주소의 기존 픽스처 정체를 확인할 수 없음 — 멱등으로 간주하지 않음"
    ),
    CONSOLE_READ_INCOMPLETE: (
        "콘솔 재조회에 미판독이 남아 있음 — 없음을 단정할 수 없어 생성하지 않음"
    ),
}
_SKIPPED_CHECK_LABELS = {
    FID_CONFLICT_PRECHECK_DESCOPE: "FID 충돌 사전검사 미수행",
    FOOTPRINT_MATCH_DESCOPE: "점유폭 일치 확인 미수행",
    FIXTURE_TYPE_LIBRARY_TRUNCATED: "FixtureType 열거 절단 — 부재 단정 불가",
    FIXTURE_TYPE_LIBRARY_UNREADABLE: "FixtureType 열거 실패 — 부재 단정 불가",
}
_TYPE_RESOLUTION_STATUS_LABELS = {
    TYPE_RESOLVED: "타입·모드 확정",
    TYPE_NEEDS_CONFIRMATION: "후보 제시 — 사용자 확인 대기",
    TYPE_LIBRARY_ABSENT: "콘솔 라이브러리 부재 — 하드 스톱",
    TYPE_LIBRARY_INCOMPLETE: "라이브러리 관측 불완전 — 부재를 단정하지 않음",
}
_VERIFICATION_OUTCOME_LABELS = {
    VERIFICATION_OBSERVED: "재조회에서 관측됨",
    VERIFICATION_NOT_OBSERVED: "재조회에서 관측되지 않음",
    VERIFICATION_MISMATCHED: "그 주소에 다른 타입 또는 모드가 관측됨",
    VERIFICATION_IDENTITY_UNCONFIRMED: "그 주소에 픽스처는 있으나 정체를 확인할 수 없음",
}

_AUTOPATCH_VOCABULARY_LABELS = MappingProxyType(
    {
        "candidate_rejection_reason": MappingProxyType(_CANDIDATE_REJECTION_LABELS),
        "fid_assignment_rejection_reason": MappingProxyType(_FID_ASSIGNMENT_REJECTION_LABELS),
        "selection_error_reason": MappingProxyType(_SELECTION_ERROR_LABELS),
        "skipped_check_kind": MappingProxyType(_SKIPPED_CHECK_LABELS),
        "target_exclusion_reason": MappingProxyType(_TARGET_EXCLUSION_LABELS),
        "type_resolution_status": MappingProxyType(_TYPE_RESOLUTION_STATUS_LABELS),
        "verification_outcome": MappingProxyType(_VERIFICATION_OUTCOME_LABELS),
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


def verification_outcome_label(code: str) -> str:
    return autopatch_label("verification_outcome", code)


def skipped_check_label(code: str) -> str:
    return autopatch_label("skipped_check_kind", code)


def type_resolution_status_label(code: str) -> str:
    return autopatch_label("type_resolution_status", code)

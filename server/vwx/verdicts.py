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
#: round18 결함 R18-E — 도면 타입 이름이 **공허**(정규화 후 영숫자 0개)해서 라이브러리
#: 대조 기준이 되지 못한다. round17은 이 갈래를 `needs_confirmation`으로 넘겼는데
#: **제시된 후보가 0건**이다 — 확인할 것이 없는 상태를 "확인 대기"라 부르면 조작자는
#: 화면에 없는 것을 고르려 기다린다. 그래서 하드 스톱이다.
#: 이름이 `None`·`''`면 `typemap._alias_for`의 `if not key: continue`에 걸려 별칭 탈출구도
#: 없다(실측). truthy 공허 이름은 그 이름을 키로 한 별칭에 실재 콘솔 이름을 저장하면
#: 해결되며, 그때는 이 갈래에 오지 않는다 — 이 코드는 그 탈출구를 막지 않는다.
#: `fixture_type_not_in_library`로 적을 수 없다: 찾아보지도 않았으므로 부재 단정이 된다.
FIXTURE_TYPE_NAME_UNUSABLE = "fixture_type_name_unusable"

#: round19 결함 major#5 — 콘솔에서 확정된 FixtureType의 **어느 DMXMode도** 도면
#: DMX Footprint와 채널 수가 맞지 않는다(전 모드 실측 · 열거 절단 없음 · 미판독 없음).
#:
#: **왜 `dmx_mode_not_in_library`를 재사용하지 않는가**: 그 코드의 등재 라벨은 "대응
#: DMXMode 없음"이고 그것이 가리키는 조치는 **콘솔에서 GDTF 라이브러리를 임포트하라**다.
#: 그런데 이 갈래에서 모드는 라이브러리에 **있다** — 도면이 적은 점유폭이 그 모드들 중
#: 어느 것과도 맞지 않을 뿐이다. 임포트를 다시 해도 상태는 그대로이므로 조작자는 원인이
#: 아닌 곳을 고치고 재시도는 영원히 실패한다(`lua_generation_refused`가 어느 필드가
#: 거부됐는지 말하도록 고쳐진 round11 M5 N3와 같은 이유다).
#:
#: **왜 `type_confirmation_pending`이 아닌가**: 고를 선택지가 없다. 라이브러리의 전 모드를
#: 채널 수와 함께 노출해도 도면 점유폭과 맞는 것이 하나도 없으므로, 모드 선택으로는
#: 벗어날 수 없는 막다른 길이다 — 확인 대기라 적으면 조작자는 오지 않는 화면을 기다린다.
#:
#: **왜 `footprint_unknown`이 아닌가**: 그 코드는 도면 점유폭을 **모르는** 상태다.
#: 여기서는 알고 있고, 안 맞는다 — 고칠 대상이 다르다(도면 값 자체).
DESIGNED_FOOTPRINT_MATCHES_NO_MODE = "designed_footprint_matches_no_console_mode"

ADDRESS_ALREADY_OCCUPIED = "address_already_occupied"
ADDRESS_OVERLAP_IN_PLAN = "address_overlap_in_plan"
FOOTPRINT_UNKNOWN = "footprint_unknown"
#: round17 결함 R17-A — 1단계가 준 유니버스·주소가 콘솔 최소 인덱스(1) 미만이다.
#: 절대주소 역산(``server/vwx/address.py``)은 음수 입력에서 유니버스 0·음수를
#: 산출하고, Universe+DMX Address 직접 읽기는 음수 주소를 그대로 통과시킨다 —
#: 그 값이 그대로 ``patch = { "0.507" }`` 같은 Lua 전달물이 되어 사람 손에 갔다.
#: 값을 고쳐 통과시키지 않고(자동 보정 0건) **등재된 코드로 배제**한다.
ADDRESS_BELOW_MINIMUM = "address_below_minimum"

#: round18 결함 R18-A — 배정하려던 FID가 콘솔 최소 FID(1) 미만이다.
#:
#: **왜 `address_below_minimum`을 재사용하지 않는가**: 그 코드의 등재 라벨은
#: "유니버스 또는 주소"를 가리키고, 조작자는 배제 사유를 보고 **무엇을 고칠지**
#: 결정한다. FID 위반에 주소 코드를 붙이면 사용자는 도면 좌표를 고치러 가고
#: 재시도는 영원히 실패한다(`lua_generation_refused`가 어느 필드가 거부됐는지
#: 말하도록 고쳐진 round11 M5 N3와 같은 이유다).
#:
#: **왜 `invalid_fid_range`로 갈음하지 않는가**: 그 코드는 사용자 입력 `fid_range`
#: 전체를 되돌려보내는 **거부**(`fid_assignment_rejection_reason`) 어휘이고, 이 코드는
#: 대상 하나를 계획에서 빼는 **배제**(`target_exclusion_reason`) 어휘다. 두 어휘는
#: payload의 다른 자리에 실리므로 서로 대체할 수 없다.
FID_BELOW_MINIMUM = "fid_below_minimum"

FID_NOT_ASSIGNED = "fid_not_assigned"
FIXTURE_NAME_MISSING = "fixture_name_missing"
TYPE_CONFIRMATION_PENDING = "type_confirmation_pending"
LUA_GENERATION_REFUSED = "lua_generation_refused"

ALREADY_PATCHED_IDENTICAL = "already_patched_identical"
ADDRESS_CONFLICTS_WITH_EXISTING = "address_conflicts_with_existing_fixture"
EXISTING_IDENTITY_UNCONFIRMED = "existing_fixture_identity_unconfirmed"
CONSOLE_READ_INCOMPLETE = "console_read_incomplete"
FID_PRECHECK_READ_INCOMPLETE = "fid_precheck_read_incomplete"

FID_CONFLICT_PRECHECK_DESCOPE = "fid_conflict_precheck_descope"
FOOTPRINT_MATCH_DESCOPE = "footprint_match_descope"
FIXTURE_TYPE_LIBRARY_TRUNCATED = "fixture_type_library_truncated"
FIXTURE_TYPE_LIBRARY_UNREADABLE = "fixture_type_library_unreadable"
#: round20 결함 R20-D — FixtureType·DMXMode **열거 응답은 정상으로 받았는데**(`ok=true`),
#: 그 안의 행 일부가 슬롯 번호(`i`)를 갖고 있지 않거나 매핑조차 아니어서 쓰지 못했다.
#: `typemap`은 그런 행을 **계수 없이 버렸고**, 그래서 "슬롯이 확립되지 않았다"가
#: `library_absent`("라이브러리에 없다")로 바뀌어 나갔다. responder `safe_children`의
#: `probe_slots` 통째 nil / per-child `slot_confirms` 폴백이 이 스냅샷을 실제로 만든다 —
#: PRESERVE `server/prechk/inventory.py` 독스트링이 슬롯 부재를 "documented responder
#: behaviour rather than a hypothesis"라 못박은 그 형태다.
#:
#: **왜 `fixture_type_library_truncated`를 재사용하지 않는가**: 절단은 **목록이 잘려 뒤가
#: 안 온 것**이고 조치는 더 좁은 재판독·표적 스윕이다. 여기서는 목록이 끝까지 왔고 그
#: 안의 행이 못 쓸 상태다 — 같은 범위를 다시 읽어도 같은 행이 온다. 절단으로 적으면
#: 조작자는 효과 없는 재판독을 반복한다. 형제 `patchplan.ExistingFidRead`가 이미 두 축을
#: `unseen_count`와 `unusable_row_count`로 **따로** 센다 — 그 구별을 그대로 가져온다.
#:
#: **왜 `fixture_type_library_unreadable`이 아닌가**: 그 코드의 사유는 "열거를 읽지
#: 못했다"이고 조치는 재시도다. 여기서는 열거를 **읽었다** — 그렇게 적으면 payload가
#: 관측 사실을 거짓으로 말한다(R18-A "검사했고 깨끗하다"와 같은 형태의 반대편).
#:
#: **왜 `fixture_type_not_in_library`가 아닌가**: 그것이 R20-D가 낸 거짓 그 자체다.
#: 라이브러리는 온전히 있는데 "콘솔에서 GDTF 라이브러리 임포트를 먼저 하라"고 말했다.
FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED = "fixture_type_library_rows_discarded"
FID_CONFLICT_PRECHECK_INCOMPLETE = "fid_conflict_precheck_incomplete"
EXISTING_FOOTPRINT_UNREADABLE = "existing_footprint_unreadable"
#: round18 결함 R18-J — 1단계(`server/vwx/diff.py`, AC-AUTOPATCH-025 무변경 계층)의
#: 콘솔 부재 판정은 `rig.fuzzy_type_equal`로 조인한다. 정규화 후 영숫자가 남지 않는 도면
#: 타입 이름은 **이름이 빈 칸이 아닌 콘솔 타입 전부**와 일치하므로 그 픽스처는
#: `missing_in_console`에서 조용히 사라진다(실증). 1단계는 그 소멸을 `skipped_checks`에
#: 적지 않는다 — 고칠 권한은 1단계에 있지만 **고지할 자리는 2단계에도 있다**.
#:
#: [round19 major#3] 이 코드는 **`missing_in_console` 축 전용**이다. round18판은 한 코드로
#: 두 축을 말하면서 부재 축의 필터(`classification == "patched"` · 좌표 존재)만 베껴 왔고,
#: 그래서 수량 축에서 실제로 소멸하는 미패치·좌표부재 픽스처를 0건으로 셌다. 축마다 1단계
#: 필터가 다르므로 축마다 코드가 다르다.
DESIGNED_TYPE_NAME_VACUOUS = "designed_type_name_vacuous"
#: [round19 major#3] 1단계 수량 대조(`diff.py`의 `designed_counts` 루프)는 `classification`도
#: 좌표도 가리지 않고 **전 도면 픽스처**를 센다 — 그 루프에는 `if`가 하나도 없다. 그래서
#: 미패치 픽스처와 좌표가 `None`인 패치 픽스처도 이 축에서는 소멸한다(실측 확인).
DESIGNED_TYPE_NAME_VACUOUS_QUANTITY_AXIS = "designed_type_name_vacuous_quantity_axis"
#: [round19 major#1] 1단계 콘솔 조인이 **아예 수행되지 않은** 리포트에서는 위 두 코드의
#: 문장이 거짓이다: 일치로 본 적도, 소멸한 적도 없다. `diff.compare`의
#: `if not multi_system:` 가드가 두 축 루프를 통째로 건너뛰고, `diffs.performed=False`는
#: 세 키가 생략된 상태이며, `diffs`가 없는 payload에는 축 산출이라 할 것이 없다. 그 갈래에서는
#: 공허한 이름의 **존재**만 고지하고 소멸 여부는 말하지 않는다.
DESIGNED_TYPE_NAME_VACUOUS_JOIN_ABSENT = "designed_type_name_vacuous_join_absent"

TYPE_RESOLVED = "resolved"
TYPE_NEEDS_CONFIRMATION = "needs_confirmation"
TYPE_LIBRARY_ABSENT = "library_absent"
TYPE_LIBRARY_INCOMPLETE = "library_incomplete"
#: round18 결함 R18-E — 도면 타입 이름이 공허해 대조 기준도, 별칭 확인 경로도 없다.
#: `needs_confirmation`(확인 대기)도 `library_absent`(부재 단정)도 참이 아니다.
TYPE_NAME_UNUSABLE = "designed_type_name_unusable"
#: round19 결함 major#5 — 콘솔 라이브러리의 **전 모드를 실측**했고 도면 DMX Footprint와
#: 채널 수가 맞는 모드가 하나도 없다. `needs_confirmation`(확인 대기)이 아니다: 고를 수
#: 있는 모드가 없다. `library_absent`(부재 단정)도 아니다: 모드는 라이브러리에 있고
#: 점유폭만 안 맞는다 — 임포트가 아니라 도면 값이 고칠 대상이다.
TYPE_FOOTPRINT_UNMATCHABLE = "designed_footprint_unmatchable"

VERIFICATION_OBSERVED = "observed"
VERIFICATION_NOT_OBSERVED = "not_observed"
VERIFICATION_MISMATCHED = "mismatched"
VERIFICATION_IDENTITY_UNCONFIRMED = "identity_unconfirmed"

# 재조회가 무엇을 못 봤는지 — caveat으로 payload에 실리므로 닫힌 어휘여야 한다
# (round11 N03: 이전 판은 apply.py의 맨 문자열이라 라벨도 검증도 없이 나갔다).
CONSOLE_READ_INDEX_DOMAIN_UNKNOWN = "console_read_index_domain_unknown"
CONSOLE_READ_UNPATCHED_PRESENT = "console_read_unpatched_fixtures_present"

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
        FIXTURE_TYPE_NAME_UNUSABLE,
        DESIGNED_FOOTPRINT_MATCHES_NO_MODE,
        # [round19 major#4 형제 필드] 두 어휘에 함께 사는 코드다. `skipped_check_kind`로는
        # "이 확인을 못 했다"를, `target_exclusion_reason`으로는 "그래서 이 대상을 뺐다"를
        # 말한다 — `console_read_incomplete`가 배제 어휘와 caveat 어휘 양쪽에 있는 선례와
        # 같다. 이 둘이 배제 어휘에 없으면 `TypeResolution.incompleteness_kind`가
        # `type_confirmation_pending`으로 뭉개지고, 조작자는 **고를 것이 없는 상태**에서
        # 확인 화면을 기다린다(R18-E와 같은 거짓).
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
        ADDRESS_ALREADY_OCCUPIED,
        ADDRESS_OVERLAP_IN_PLAN,
        FOOTPRINT_UNKNOWN,
        ADDRESS_BELOW_MINIMUM,
        FID_BELOW_MINIMUM,
        FID_NOT_ASSIGNED,
        FIXTURE_NAME_MISSING,
        TYPE_CONFIRMATION_PENDING,
        LUA_GENERATION_REFUSED,
        ALREADY_PATCHED_IDENTICAL,
        ADDRESS_CONFLICTS_WITH_EXISTING,
        EXISTING_IDENTITY_UNCONFIRMED,
        CONSOLE_READ_INCOMPLETE,
        FID_PRECHECK_READ_INCOMPLETE,
    }
)
SKIPPED_CHECK_KIND = frozenset(
    {
        FID_CONFLICT_PRECHECK_DESCOPE,
        FOOTPRINT_MATCH_DESCOPE,
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
        FID_CONFLICT_PRECHECK_INCOMPLETE,
        EXISTING_FOOTPRINT_UNREADABLE,
        DESIGNED_TYPE_NAME_VACUOUS,
        DESIGNED_TYPE_NAME_VACUOUS_QUANTITY_AXIS,
        DESIGNED_TYPE_NAME_VACUOUS_JOIN_ABSENT,
    }
)
TYPE_RESOLUTION_STATUS = frozenset(
    {
        TYPE_RESOLVED,
        TYPE_NEEDS_CONFIRMATION,
        TYPE_LIBRARY_ABSENT,
        TYPE_LIBRARY_INCOMPLETE,
        TYPE_NAME_UNUSABLE,
        TYPE_FOOTPRINT_UNMATCHABLE,
    }
)
CONSOLE_READ_CAVEAT_KIND = frozenset(
    {
        CONSOLE_READ_INCOMPLETE,
        CONSOLE_READ_INDEX_DOMAIN_UNKNOWN,
        CONSOLE_READ_UNPATCHED_PRESENT,
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
        "console_read_caveat_kind": CONSOLE_READ_CAVEAT_KIND,
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
    FIXTURE_TYPE_NAME_UNUSABLE: (
        "도면 타입 이름이 공허 — 대조 기준도 별칭 확인 경로도 없어 제외, 도면을 고쳐야 함"
    ),
    DESIGNED_FOOTPRINT_MATCHES_NO_MODE: (
        "도면 DMX Footprint와 채널 수가 맞는 콘솔 DMXMode가 하나도 없음 — "
        "모드 선택으로 벗어날 수 없어 제외, 도면 점유폭을 고쳐야 함"
    ),
    # [round19 major#4 형제 필드] 같은 코드가 `skipped_check_kind`에서는 "부재 단정 불가"를
    # 말한다. 배제 자리의 라벨은 **그래서 이 대상을 어떻게 했는가**와 조작자가 할 일을 적는다.
    # [round21 R20-A ⓒ] "라이브러리를 다시 읽어야 함"은 **수행 불가능한 지시**였다.
    # 열거 상한이 하드 캡이고 payload 예산이 그보다 먼저 물기 때문에, 재판독은 결정적으로
    # 같은 앞부분을 다시 준다. 표적 스윕(`typemap.recover_requested_types`)까지 실패한
    # 뒤에야 이 자리에 오므로, 라벨은 조작자가 **실제로 할 수 있는 것**을 가리킨다.
    FIXTURE_TYPE_LIBRARY_TRUNCATED: (
        "FixtureType·DMXMode 열거에 미관측분이 남음 — 고를 수 있는 것을 다 보여줄 수 없어 제외. "
        "재판독은 같은 앞부분을 다시 준다(열거 상한이 하드 캡) — 도면 타입명을 콘솔 표기와 "
        "맞추거나, 그 GDTF를 콘솔 라이브러리에 임포트해야 함"
    ),
    FIXTURE_TYPE_LIBRARY_UNREADABLE: (
        "FixtureType·DMXMode 또는 채널 수를 읽지 못함 — 고를 수 있는 것을 다 보여줄 수 없어 제외. "
        "콘솔 응답을 먼저 확인하고, 그 뒤 도면 타입명을 콘솔 표기와 맞추거나 그 GDTF를 "
        "콘솔 라이브러리에 임포트해야 함"
    ),
    # [round20 R20-D 형제 필드] 절단·판독실패와 **다른 축**이므로 조치도 다르게 적는다.
    # 재판독을 시키지 않는다 — 같은 범위를 다시 읽어도 같은 행이 온다.
    FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED: (
        "FixtureType·DMXMode 열거 행 일부에 슬롯 번호가 없어 쓰지 못함 — "
        "라이브러리 목록을 전수로 세울 수 없어 제외, 콘솔 열거 응답이 슬롯 번호를 주지 않았다"
    ),
    ADDRESS_ALREADY_OCCUPIED: "도면 주소가 콘솔에서 이미 점유됨",
    ADDRESS_OVERLAP_IN_PLAN: "같은 유니버스 안에서 다른 계획 항목과 점유 구간이 겹침",
    FOOTPRINT_UNKNOWN: "점유폭 미확정 — 추측하지 않고 제외",
    ADDRESS_BELOW_MINIMUM: "유니버스 또는 주소가 콘솔 최소 인덱스 미만 — 값을 고치지 않고 제외",
    FID_BELOW_MINIMUM: "배정 FID가 콘솔 최소 FID 미만 — 값을 고치지 않고 제외",
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
    FID_PRECHECK_READ_INCOMPLETE: (
        "FID 충돌 사전검사가 불완전 — 빈 FID를 단정할 수 없어 배정하지 않음"
    ),
}
_SKIPPED_CHECK_LABELS = {
    FID_CONFLICT_PRECHECK_DESCOPE: "FID 충돌 사전검사 미수행",
    FOOTPRINT_MATCH_DESCOPE: "점유폭 일치 확인 미수행",
    # [round21 R20-A ⓐ] "절단"만 적으면 계수만 어긋난 스냅샷(플래그는 거짓)에서 라벨이
    # 일어나지 않은 원인을 단정한다. 관측 축의 사실은 **미관측분이 남았다**는 것 하나다.
    FIXTURE_TYPE_LIBRARY_TRUNCATED: "FixtureType 열거 미관측분 — 부재 단정 불가",
    FIXTURE_TYPE_LIBRARY_UNREADABLE: "FixtureType 열거 실패 — 부재 단정 불가",
    FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED: "FixtureType 열거 행 폐기 — 부재 단정 불가",
    FID_CONFLICT_PRECHECK_INCOMPLETE: "FID 충돌 사전검사 부분 관측 — 빈 FID 단정 불가",
    EXISTING_FOOTPRINT_UNREADABLE: ("기존 픽스처 점유폭 미판독 — 꼬리 구간 겹침은 검출되지 않는다"),
    DESIGNED_TYPE_NAME_VACUOUS: (
        "도면 타입 이름이 공허한 픽스처가 있음 — 1단계 콘솔 부재 판정이 그 항목을 삼켰을 수 "
        "있어 콘솔 부재 단정 불가"
    ),
    DESIGNED_TYPE_NAME_VACUOUS_QUANTITY_AXIS: (
        "도면 타입 이름이 공허한 픽스처가 있음 — 1단계 수량 대조가 그 항목을 삼켰을 수 있어 "
        "수량 차이 단정 불가"
    ),
    DESIGNED_TYPE_NAME_VACUOUS_JOIN_ABSENT: (
        "도면 타입 이름이 공허한 픽스처가 있음 — 1단계 콘솔 조인 미수행이라 소멸 여부 자체를 "
        "말할 수 없음"
    ),
}
_TYPE_RESOLUTION_STATUS_LABELS = {
    TYPE_RESOLVED: "타입·모드 확정",
    TYPE_NEEDS_CONFIRMATION: "후보 제시 — 사용자 확인 대기",
    TYPE_LIBRARY_ABSENT: "콘솔 라이브러리 부재 — 하드 스톱",
    TYPE_LIBRARY_INCOMPLETE: "라이브러리 관측 불완전 — 부재를 단정하지 않음",
    TYPE_NAME_UNUSABLE: "도면 타입 이름이 공허 — 확인 경로 없음, 하드 스톱",
    TYPE_FOOTPRINT_UNMATCHABLE: "도면 점유폭과 맞는 DMXMode 없음 — 선택 경로 없음, 하드 스톱",
}
_CONSOLE_READ_CAVEAT_LABELS = {
    CONSOLE_READ_INCOMPLETE: "재조회에 미판독이 남았다 — 없음을 단정할 수 없다",
    CONSOLE_READ_INDEX_DOMAIN_UNKNOWN: (
        "열거는 절단됐으나 선언된 자식을 전부 관측했다 — 인덱스 도메인만 미상"
    ),
    CONSOLE_READ_UNPATCHED_PRESENT: (
        "최소 인덱스 미만 Patch 값을 가진 픽스처가 있다 — 미실측 가정 위의 판정이니 대조하라"
    ),
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
        "console_read_caveat_kind": MappingProxyType(_CONSOLE_READ_CAVEAT_LABELS),
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


def console_read_caveat_label(code: str) -> str:
    return autopatch_label("console_read_caveat_kind", code)


def skipped_check_label(code: str) -> str:
    return autopatch_label("skipped_check_kind", code)


def type_resolution_status_label(code: str) -> str:
    return autopatch_label("type_resolution_status", code)

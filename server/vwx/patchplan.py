from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from types import MappingProxyType
from typing import Protocol

from server.vwx.address import ADDRESS_BASIS_ABS_BACK_CALCULATED
from server.vwx.diff import MULTI_SYSTEM_MAPPING_ABSENT
from server.vwx.verdicts import (
    ADDRESS_ALREADY_OCCUPIED,
    ADDRESS_BELOW_MINIMUM,
    ADDRESS_OVERLAP_IN_PLAN,
    COMPARISON_NOT_PERFORMED,
    FID_ALREADY_IN_USE,
    FID_CONFLICT_PRECHECK_DESCOPE,
    FID_CONFLICT_PRECHECK_INCOMPLETE,
    FID_PRECHECK_READ_INCOMPLETE,
    FID_RANGE_CONFIRMATION_REQUIRED,
    FID_RANGE_EXHAUSTED,
    FID_RANGE_REQUIRED,
    FOOTPRINT_UNKNOWN,
    INVALID_FID_RANGE,
    INVALID_REPORT_PAYLOAD,
    UNKNOWN_CANDIDATE_ID,
    autopatch_label,
    skipped_check_label,
    target_exclusion_label,
    validate_autopatch,
)

IRREVERSIBLE_WARNING = (
    "이 앱에는 실행 취소·백업 복원 경로가 없고, 잘못 생성된 픽스처는 콘솔에서 사람이 지워야 한다."
)
SOURCE_PATH_MISSING_IN_CONSOLE = "diffs.missing_in_console"
FID_FIXTURE_ROOT = "Patch/Stages/1/Fixtures"
FID_PROPERTY_NAME = "FID"
#: 콘솔 번호 체계가 시작하는 최소 인덱스 — 유니버스·주소 **양쪽**의 바닥이다.
#: 두 축에 같은 바닥을 쓰는 근거는 별도 추정이 아니라 PRESERVE 경로의 원전이다:
#: `server/prechk/patch.py`의 `normalize_address`가 "Both halves must be at least
#: `_MINIMUM_INDEX`. The console's own numbering starts at one, so `0.0` · `1.0` ·
#: `0.1` name no addressable channel"이라고 못박고 `universe < _MINIMUM_INDEX or
#: address < _MINIMUM_INDEX`를 한 조건으로 검사한다(patch.py:121-123·141). 여기도
#: 같은 형태로 둔다 — 유니버스만 막고 주소를 통과시키거나 그 반대면 반쪽이다.
#: 상한은 두지 않는다(같은 독스트링의 "deliberately NO upper bound", ASSUMPTION-33)
#: — `plan_addresses` 안 주석과 `test_r17_no_ceiling_is_fabricated_above_the_universe_width`
#: 참조. 사본을 두는 이유는 비공개 이름을 계층 넘어 import하지 않기 위해서이고,
#: 두 값이 어긋나면 대조군이 잡는다
#: (`test_autopatch_verify.py::test_r17_minimum_index_matches_the_preserve_path`).
_MINIMUM_ADDRESS_INDEX = 1

# ==========================================================================
# [round17 S17-04] 사람이 읽는 문장의 **형태 불변식**
#
# 이 SPEC은 같은 결함을 세 번 냈다. 셋 다 **조각은 멀쩡한데 조립한 결과가 깨진** 형태다:
#   round15 N11 — `reason()`의 끝 마침표와 호출부의 `. `가 겹쳐 `..`
#   round16 S16-01 — 완결 문장을 `" · "` 목록에 넣어 `…대조하라. — 이 상태의…`
#   round17 S17-04 — 대시를 품은 조각을 대시 있는 문장에 끼워 **한 문장 안 대시 둘**
# 조각만 보면 셋 다 보이지 않으므로 **조립부에서 조립 결과를** 검사한다. 검사는 테스트가
# 아니라 프로덕션에 둔다 — 이 문자열은 되돌릴 수 없는 쓰기를 판단하는 사람에게 나가고,
# 절 경계를 잃은 문장은 판정을 뒤집어 읽힌다(S16-01은 미판독 판정이 미패치 절에 붙었다).
#: (부분문자열, 무엇이 잘못됐는지) — 한 문장 안에서 발견되면 조립을 거부한다.
_SENTENCE_SHAPE_DEFECTS: tuple[tuple[str, str], ...] = (
    ("..", "마침표가 겹쳤다"),
    (". —", "문장이 대시로 시작한다"),
    ("  ", "공백이 겹쳤다"),
    # `" ."`는 넣지 않는다 — `reader.py`의 `"openpyxl 없이는 .xlsx를 판독할 수 없다"`처럼
    # 확장자·파일명 앞 공백에서 거짓 양성을 낸다. 흔한 거짓 양성은 게이트를 무력화한다(§0 2b④).
    ("· ·", "빈 절이 목록에 있다"),
    (" · —", "대시 절이 목록 항목 자리에 있다"),
)
#: 한 문장이 품어도 되는 ` — `의 최대 개수. 둘 이상이면 어디까지가 어느 절인지 사라진다.
_MAX_DASHES_PER_SENTENCE = 1


def sentence_shape_violation(text: str, *, require_terminal: bool = True) -> str | None:
    """사람이 읽는 문자열의 형태 위반을 돌려준다 — 없으면 `None`.

    조각이 아니라 **조립 결과**에 거는 것이 원칙이다. 조각 단위 검사는 이 SPEC이 세 번
    통과시킨 바로 그 검사다(위 주석).

    `require_terminal=False`는 **정적 뼈대**를 잴 때만 쓴다 — 소스에서 뽑은 조각은 아직
    이어 붙기 전이라 마침표로 끝나지 않는 것이 정상이다. 나머지 규칙은 조각에도 그대로
    적용된다: 조각이 이미 `..`·`. —`·이중공백·한 문장 대시 둘을 품고 있으면 어떻게
    이어 붙여도 깨진 문장이 된다.
    """
    for needle, label in _SENTENCE_SHAPE_DEFECTS:
        if needle in text:
            return f"{label}: {needle!r}"
    if require_terminal and not text.endswith("."):
        return "문장이 종결되지 않았다"
    for sentence in text.split(". "):
        if sentence.count(" — ") > _MAX_DASHES_PER_SENTENCE:
            return f"한 문장에 ' — '가 {sentence.count(' — ')}개다: {sentence!r}"
    return None


def assemble_sentences(*sentences: str) -> str:
    """완결 문장 여럿을 한 문단으로 잇고 **형태 불변식을 강제한다**.

    빈 조각은 버린다 — 관측되지 않은 축을 빈 문장으로 남기면 `..`·`  `가 생긴다.
    위반이면 사람에게 내보내지 않고 **즉시 실패한다**: 조용히 나가면 이 SPEC이
    일곱 라운드 반복한 대로 다음 감사에서야 발견된다.
    """
    text = " ".join(sentence for sentence in sentences if sentence)
    violation = sentence_shape_violation(text)
    if violation is not None:
        raise ValueError(f"조립된 문장의 형태가 깨졌다({violation}): {text!r}")
    return text


ASSUMPTION_71_GO = "go"
ASSUMPTION_71_NEGATIVE = "negative"
ASSUMPTION_71_INCONCLUSIVE = "inconclusive"
ASSUMPTION_71_VALUES = frozenset(
    {
        ASSUMPTION_71_GO,
        ASSUMPTION_71_NEGATIVE,
        ASSUMPTION_71_INCONCLUSIVE,
    }
)

DEFERRED_TO_M2 = "deferred_to_m2"
DEFERRED_TO_M3 = "deferred_to_m3"
DEFERRED_TO_M4 = "deferred_to_m4"

TARGET_TABLE_COLUMNS = (
    "type",
    "mode",
    "fid",
    "universe",
    "address",
    "footprint",
    "address_basis",
)
UNRESOLVED_TARGET_FIELDS = MappingProxyType(
    {
        "mode": DEFERRED_TO_M3,
        "fid": DEFERRED_TO_M2,
        "footprint": DEFERRED_TO_M3,
    }
)


class FidPropertyPort(Protocol):
    def query_state(self, path: str) -> Mapping[str, object]: ...

    def query_property(self, path: str, property_name: str) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class FIDRange:
    start: int
    end: int


@dataclass(frozen=True)
class PatchCandidate:
    id: str
    unit_number: str | None
    instrument_type: str
    universe: int
    address: int
    detail: str
    address_basis: str | None
    source_index: int
    assigned_fid: int | None = None
    fid_range_visually_confirmed_empty: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "unit_number": self.unit_number,
            "type": self.instrument_type,
            "universe": self.universe,
            "address": self.address,
            "detail": self.detail,
            "address_basis": self.address_basis,
            "source_path": SOURCE_PATH_MISSING_IN_CONSOLE,
            "source_index": self.source_index,
        }

    def with_fid(
        self, fid: int, *, fid_range_visually_confirmed_empty: bool | None = None
    ) -> PatchCandidate:
        return replace(
            self,
            assigned_fid=fid,
            fid_range_visually_confirmed_empty=fid_range_visually_confirmed_empty,
        )

    def target_row(self) -> dict[str, object]:
        unresolved_reason = dict(UNRESOLVED_TARGET_FIELDS)
        if self.assigned_fid is not None:
            unresolved_reason.pop("fid")
        row: dict[str, object] = {
            "id": self.id,
            "type": self.instrument_type,
            "mode": None,
            "fid": self.assigned_fid,
            "universe": self.universe,
            "address": self.address,
            "footprint": None,
            "address_basis": self.address_basis,
            "unresolved_reason": unresolved_reason,
        }
        if self.fid_range_visually_confirmed_empty is not None:
            row["fid_range_visually_confirmed_empty"] = self.fid_range_visually_confirmed_empty
        return row


@dataclass(frozen=True)
class PatchTargetExclusion:
    candidate_id: str
    code: str
    reason: str
    proposed_fid: int | None = None
    #: [round17 S17-03a] 이 제외를 낳은 **점유자 전원**. 원소는 `ConsoleFixture.to_dict()`
    #: 모양이다(slot·universe·address·type_display·mode_display·type_name·mode_name·
    #: identity_resolved).
    #:
    #: round15 D가 세운 단수 쌍 `observed_type_display`/`observed_mode_display`를
    #: **대체한다**. 단수 쌍은 N>=2를 구조적으로 표현할 수 없으므로 "단수 필드를 채운다"는
    #: 규약에는 **면제 갈래가 영원히 남는다** — 실제로 `screen_idempotent`의 다중 점유
    #: 갈래가 그 면제였고, 그 갈래의 payload에는 점유자가 몇 대인지 말하는 문장만 있을 뿐
    #: **무엇이 점유했는지**가 어디에도 없었다(형제 갈래 `address_already_occupied`는
    #: 슬롯·주소를 준다 — 한 payload 안에서 정보 밀도가 갈렸다). 조작자는 되돌릴 수 없는
    #: 쓰기를 그 상태로 판단했다. 그 면제가 이 SPEC이 일곱 라운드 반복한 형제-갈래 위반의
    #: 기제다. 리스트는 0·1·N을 전부 표현하므로 면제가 없다 — `len()`이 곧 상태다.
    #:
    #: 콘솔이 돌려준 **표시 문자열 원문**을 사유 **문장**에는 되싣지 않는 규율(§0 2b④ ·
    #: `apply._rejected_field` 선례)은 그대로다. 문장에 원문을 넣으면 AC-014① 산출물
    #: 스캐너가 거짓 양성을 내 게이트가 강제력을 잃는다 — 계획 주소를 점유한 픽스처의
    #: `FixtureType`이 `'CD 5'`인 것만으로 전달물 전체가 위반으로 찍혔다(실측).
    #: 관측값 자체는 조작자에게 그대로 보여야 하므로(§0 2c①) 버리지 않고 **여기로** 옮긴다.
    #:
    #: [round17 S17-03b] 사유 문장에 "원문은 이 필드에 있다"는 **포인터도 넣지 않는다.**
    #: 포인터를 무조건 붙이면 값이 비었을 때도 있다고 말하게 되어, 점유자 2대인 상태와
    #: 점유자 1대인데 표시 문자열을 못 읽은 상태가 같은 문장으로 나갔다. payload의 키
    #: 이름이 곧 포인터이고, 두 상태는 `len(observed_occupants)`가 가른다.
    observed_occupants: tuple[Mapping[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "code": validate_autopatch("target_exclusion_reason", self.code),
            "label": target_exclusion_label(self.code),
            "reason": self.reason,
            "proposed_fid": self.proposed_fid,
            "observed_occupants": [dict(occupant) for occupant in self.observed_occupants],
        }


@dataclass(frozen=True)
class AddressPlanEntry:
    """계획된 한 항목의 점유 구간. `address`는 **언제나 도면 주소 그대로**다."""

    candidate_id: str
    universe: int
    address: int
    footprint: int
    end_address: int

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "universe": self.universe,
            "address": self.address,
            "footprint": self.footprint,
            "end_address": self.end_address,
        }


@dataclass(frozen=True)
class AddressPlan:
    entries: tuple[AddressPlanEntry, ...] = ()
    exclusions: tuple[PatchTargetExclusion, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "exclusions": [exclusion.to_dict() for exclusion in self.exclusions],
        }


@dataclass(frozen=True)
class DesignedAttributes:
    """1단계 도면이 후보 하나에 대해 준 값 — **콘솔에서 읽은 값이 아니다**.

    `footprint`가 도면 점유폭이며, 콘솔의 `DMXChannels` 개수로 대체하면 안 된다
    (M0 함정 7: 실측 14 vs 실제 stride 16).
    """

    gdtf_fixture: str | None = None
    mode: str | None = None
    footprint: int | None = None


def designed_attributes_by_candidate(
    report: Mapping[str, object], targets: Sequence[PatchCandidate]
) -> dict[str, DesignedAttributes]:
    """후보 식별자 -> 도면 값. `_address_basis_by_fixture`와 **같은 조인 키**를 쓴다.

    조인 키는 `(unit_number, instrument_type, universe, address)`다 — 후보 자체가
    그 네 값으로 만들어졌으므로(`_candidate_id`) 같은 키로 되짚을 수 있다.
    도면 행을 찾지 못하면 빈 값을 돌려준다 — **추측하지 않는다**. 그 결과
    폭 미확정 항목은 `plan_addresses`가 `footprint_unknown`으로 제외한다.
    """
    designed = report.get("designed_rig")
    indexed: dict[tuple[str | None, str, int, int], DesignedAttributes] = {}
    if isinstance(designed, Mapping):
        for fixture in _mapping_rows(designed.get("fixtures")):
            instrument_type = _optional_string(fixture.get("instrument_type"))
            universe = _optional_int(fixture.get("universe"))
            address = _optional_int(fixture.get("address"))
            if instrument_type is None or universe is None or address is None:
                continue
            key = (
                _optional_string(fixture.get("unit_number")),
                instrument_type,
                universe,
                address,
            )
            indexed[key] = DesignedAttributes(
                gdtf_fixture=_optional_string(fixture.get("gdtf_fixture")),
                mode=_optional_string(fixture.get("mode")),
                footprint=_optional_int(fixture.get("footprint")),
            )
    return {
        target.id: indexed.get(
            (target.unit_number, target.instrument_type, target.universe, target.address),
            DesignedAttributes(),
        )
        for target in targets
    }


def plan_addresses(
    targets: Sequence[PatchCandidate],
    *,
    footprints: Mapping[str, int | None],
    occupied: Mapping[int, Sequence[tuple[int, int]]],
) -> AddressPlan:
    """도면 주소를 그대로 쓰면서 겹치는 항목을 **제외**한다 (REQ-AUTOPATCH-019).

    `footprints`는 **1단계 도면이 준 점유폭**이다 — 콘솔에서 읽은 `DMXChannels` 개수를
    넣으면 안 된다(M0 함정 7: 그것은 점유폭이 아니다). 폭을 모르는 항목은 추측하지 않고
    `footprint_unknown`으로 제외한다.

    `occupied`는 유니버스별 기존 점유 구간 `(시작, 끝)` 목록이다.

    유니버스·주소가 콘솔 최소 인덱스 미만인 항목은 ``address_below_minimum``으로
    제외한다(round17 결함 R17-A) — 아래 :data:`_MINIMUM_ADDRESS_INDEX` 주석 참조.

    **재배치는 하지 않는다** — 빈 주소를 찾아 옮겨 붙이는 경로가 이 함수에 없다.
    그것은 사람이 결정할 일이다(design.md §7 안티패턴 7).
    """
    entries: list[AddressPlanEntry] = []
    exclusions: list[PatchTargetExclusion] = []
    planned_spans: dict[int, list[tuple[int, int]]] = {}

    for target in targets:
        # round17 결함 R17-A — **바닥만** 검사한다. 1단계(`server/vwx/address.py`)는
        # 절대주소 음수 입력을 유니버스 0·음수로 역산하고 Universe+DMX Address 직접
        # 읽기는 음수 주소를 그대로 통과시킨다. 그 값이 `plan_addresses`를 지나면
        # `span` 산술과 점유 대조가 존재하지 않는 채널 위에서 이뤄지고, 최종적으로
        # `patch = { "0.507" }` 같은 Lua가 사람 손에 간다(되돌릴 수 없다). 값을 고쳐
        # 통과시키지 않고 등재된 코드로 배제한다 — 자동 보정 0건(AC-AUTOPATCH-021②).
        #
        # 왜 상한은 두지 않는가: `server/prechk/patch.py`의 `normalize_address`가
        # "per-universe channel capacity is unmeasured(ASSUMPTION-33) — inventing a
        # ceiling would reject addresses the console accepts"라며 **의도적으로 상한을
        # 두지 않는다**. 여기서 512를 천장으로 삼으면 콘솔이 받아들이는 주소를 이
        # 계층이 날조로 거부하게 되고, PRESERVE 경로의 판정과도 어긋난다.
        # `server/vwx/address.py`의 `_UNIVERSE_WIDTH`(512)는 **절대주소 역산의 전제**
        # 이지 채널 수용량 천장이 아니므로 여기 상한으로 재사용하지 않는다.
        # 유니버스 끝을 넘는 `end_address`(꼬리 넘침)도 같은 이유로 이 함수의 판정
        # 대상이 아니다 — `server/prechk/patch.py`가 "out of scope"로 명시한 축이다.
        if target.universe < _MINIMUM_ADDRESS_INDEX or target.address < _MINIMUM_ADDRESS_INDEX:
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=ADDRESS_BELOW_MINIMUM,
                    reason=(
                        f"계획 대상 좌표(유니버스 {target.universe} 주소 "
                        f"{target.address})가 콘솔 최소 인덱스 {_MINIMUM_ADDRESS_INDEX} "
                        "미만이다 — 값을 고쳐 통과시키지 않고 제외한다."
                    ),
                )
            )
            continue

        footprint = footprints.get(target.id)
        if not isinstance(footprint, int) or isinstance(footprint, bool) or footprint <= 0:
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=FOOTPRINT_UNKNOWN,
                    reason=(
                        "점유폭이 확정되지 않아 간격을 계산할 수 없다 — "
                        "콘솔의 DMXChannels 개수는 점유폭이 아니므로 대체하지 않는다."
                    ),
                )
            )
            continue

        span = (target.address, target.address + footprint - 1)

        console_spans = tuple(occupied.get(target.universe, ()))
        if any(_spans_overlap(span, existing) for existing in console_spans):
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=ADDRESS_ALREADY_OCCUPIED,
                    reason=(
                        f"유니버스 {target.universe} 주소 {span[0]}~{span[1]} 구간이 "
                        "콘솔에서 이미 점유되어 있다 — 빈 주소로 옮겨 붙이지 않고 제외한다."
                    ),
                )
            )
            continue

        same_universe = planned_spans.setdefault(target.universe, [])
        if any(_spans_overlap(span, existing) for existing in same_universe):
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=ADDRESS_OVERLAP_IN_PLAN,
                    reason=(
                        f"유니버스 {target.universe} 주소 {span[0]}~{span[1]} 구간이 "
                        "같은 계획의 다른 항목과 겹친다 — 도면 주소를 바꾸지 않고 제외한다."
                    ),
                )
            )
            continue

        same_universe.append(span)
        entries.append(
            AddressPlanEntry(
                candidate_id=target.id,
                universe=target.universe,
                address=target.address,
                footprint=footprint,
                end_address=span[1],
            )
        )

    return AddressPlan(entries=tuple(entries), exclusions=tuple(exclusions))


def _spans_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


@dataclass(frozen=True)
class PatchPlanRejection:
    code: str
    reason: str
    quoted_report_reason: str | None = None
    vocabulary: str = "candidate_rejection_reason"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": validate_autopatch(self.vocabulary, self.code),
            "label": autopatch_label(self.vocabulary, self.code),
            "reason": self.reason,
        }
        if self.quoted_report_reason is not None:
            payload["quoted_report_reason"] = self.quoted_report_reason
        return payload


@dataclass(frozen=True)
class PatchPlan:
    ok: bool
    status: str
    dry_run: bool
    candidates: tuple[PatchCandidate, ...]
    selected: tuple[str, ...] = ()
    targets: tuple[PatchCandidate, ...] = ()
    rejection: PatchPlanRejection | None = None
    errors: tuple[dict[str, str], ...] = ()
    address_basis_notes: tuple[str, ...] = ()
    target_exclusions: tuple[PatchTargetExclusion, ...] = ()
    skipped_checks: tuple[Mapping[str, object], ...] = ()
    fid_safety: Mapping[str, object] | None = None
    fid_range_visually_confirmed_empty: bool | None = None

    @property
    def execution_requested(self) -> bool:
        return not self.dry_run

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ok": self.ok,
            "status": self.status,
            "dry_run": self.dry_run,
            "execution_requested": self.execution_requested,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected": list(self.selected),
            "targets": [target.target_row() for target in self.targets],
            "target_table": {
                "columns": list(TARGET_TABLE_COLUMNS),
                "rows": [target.target_row() for target in self.targets],
            },
            "warnings": [IRREVERSIBLE_WARNING],
            "address_basis_notes": list(self.address_basis_notes),
            "target_exclusions": [exclusion.to_dict() for exclusion in self.target_exclusions],
            "skipped_checks": [dict(check) for check in self.skipped_checks],
            "lua_source": None,
            "lua_source_unresolved_reason": DEFERRED_TO_M4,
        }
        if self.fid_safety is not None:
            payload["fid_safety"] = dict(self.fid_safety)
        if self.fid_range_visually_confirmed_empty is not None:
            payload["fid_range_visually_confirmed_empty"] = self.fid_range_visually_confirmed_empty
        if self.rejection is not None:
            payload["rejection"] = self.rejection.to_dict()
        if self.errors:
            payload["errors"] = [dict(error) for error in self.errors]
        return payload


def build_patch_plan(
    report: Mapping[str, object],
    *,
    selected: Sequence[str] | None = None,
    dry_run: bool = True,
    fid_range: Mapping[str, object] | None = None,
    assumption_71: str | None = None,
    fid_range_visually_confirmed_empty: bool | None = None,
    fid_property_port: FidPropertyPort | None = None,
    assignment_requested: bool | None = None,
) -> PatchPlan:
    rejection = _rejection_for_report(report)
    if rejection is not None:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=(),
            rejection=rejection,
        )

    candidates = _candidates_from_report(report)
    selected_ids = tuple(selected or ())
    candidates_by_id = {candidate.id: candidate for candidate in candidates}
    unknown = tuple(
        candidate_id for candidate_id in selected_ids if candidate_id not in candidates_by_id
    )
    if unknown:
        return PatchPlan(
            ok=False,
            status="selection_error",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            errors=tuple(
                {
                    "code": validate_autopatch("selection_error_reason", UNKNOWN_CANDIDATE_ID),
                    "candidate_id": candidate_id,
                }
                for candidate_id in unknown
            ),
        )

    target_ids = frozenset(selected_ids)
    targets = tuple(candidate for candidate in candidates if candidate.id in target_ids)
    if not _fid_assignment_requested(
        fid_range, assumption_71, fid_range_visually_confirmed_empty, assignment_requested
    ):
        return PatchPlan(
            ok=True,
            status="planned",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            address_basis_notes=_address_basis_notes(report, targets),
        )

    assumption_71_value = _assumption_71_or_default(assumption_71)
    parsed_fid_range = _parse_fid_range(fid_range)
    if fid_range is None:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=FID_RANGE_REQUIRED,
                reason=(
                    "패치할 빈 FID 범위를 fid_range {'start': int, 'end': int} 형식으로 "
                    "입력해야 한다."
                ),
                vocabulary="fid_assignment_rejection_reason",
            ),
        )
    if parsed_fid_range is None:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=INVALID_FID_RANGE,
                reason=(
                    "fid_range는 정수 start와 end를 포함해야 하며 end는 start보다 작을 수 없다."
                ),
                vocabulary="fid_assignment_rejection_reason",
            ),
        )

    confirmation_required = assumption_71_value != ASSUMPTION_71_GO
    confirmation_recorded = (
        bool(fid_range_visually_confirmed_empty) if confirmation_required else None
    )
    fid_safety = _fid_safety_payload(
        assumption_71_value,
        confirmation_required=confirmation_required,
        confirmation_recorded=confirmation_recorded,
        existing_read=ExistingFidRead(),
        precheck_performed=assumption_71_value == ASSUMPTION_71_GO,
    )
    if confirmation_required and confirmation_recorded is not True:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=FID_RANGE_CONFIRMATION_REQUIRED,
                reason=(
                    "ASSUMPTION-71 부정 또는 INCONCLUSIVE 분기에서는 FID 범위를 콘솔에서 "
                    "눈으로 확인했다는 별도 확인(fid_range_visually_confirmed_empty=true)이 "
                    "필요하다."
                ),
                vocabulary="fid_assignment_rejection_reason",
            ),
            fid_safety=fid_safety,
            fid_range_visually_confirmed_empty=False,
        )

    precheck_enabled = assumption_71_value == ASSUMPTION_71_GO
    existing_read = (
        _existing_fids_from_console(fid_property_port) if precheck_enabled else ExistingFidRead()
    )

    # [round11 N01] 사전검사가 **부분 관측**이면 배정하지 않는다. 부분 집합을 전부라고 읽고
    # "빈" FID를 고르면 이미 쓰이는 번호를 배정하게 되고, MA3는 그것을 조용히 받아들여
    # 엉뚱한 픽스처를 덮는다(§0 함정 2). 이 앱에는 실행 취소가 없으므로 모르면 하지 않는다.
    if precheck_enabled and not existing_read.complete:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=FID_PRECHECK_READ_INCOMPLETE,
                # [round17 S17-04] 조각을 문장 안에 끼우던 조립을 **문장 단위 조립**으로
                # 바꾼다. `reason()`은 조각(대시·마침표 없음), `notes()`는 완결 문장이고,
                # `assemble_sentences`가 결과의 형태 불변식을 강제한다.
                reason=assemble_sentences(
                    f"기존 FID 사전검사가 불완전하다 — {existing_read.reason()}.",
                    *existing_read.notes(),
                    "부분 관측으로 빈 FID를 단정하면 이미 쓰이는 번호를 배정하게 된다.",
                ),
                vocabulary="target_exclusion_reason",
            ),
            skipped_checks=(_fid_precheck_incomplete_check(existing_read),),
            fid_safety=_fid_safety_payload(
                assumption_71_value,
                confirmation_required=confirmation_required,
                confirmation_recorded=confirmation_recorded,
                existing_read=existing_read,
                precheck_performed=False,
            ),
            fid_range_visually_confirmed_empty=confirmation_recorded,
        )

    planned_targets, target_exclusions = _assign_fids(
        targets,
        parsed_fid_range,
        existing_fids=frozenset(existing_read.fids),
        fid_range_visually_confirmed_empty=confirmation_recorded,
    )
    skipped_checks = _fid_skipped_checks(assumption_71_value)
    return PatchPlan(
        ok=True,
        status="planned",
        dry_run=dry_run,
        candidates=candidates,
        selected=selected_ids,
        targets=planned_targets,
        address_basis_notes=_address_basis_notes(report, planned_targets),
        target_exclusions=target_exclusions,
        skipped_checks=skipped_checks,
        fid_safety=_fid_safety_payload(
            assumption_71_value,
            confirmation_required=confirmation_required,
            confirmation_recorded=confirmation_recorded,
            existing_read=existing_read,
            precheck_performed=precheck_enabled,
        ),
        fid_range_visually_confirmed_empty=confirmation_recorded,
    )


def _fid_precheck_incomplete_check(read: ExistingFidRead) -> Mapping[str, object]:
    return {
        "kind": validate_autopatch("skipped_check_kind", FID_CONFLICT_PRECHECK_INCOMPLETE),
        "label": skipped_check_label(FID_CONFLICT_PRECHECK_INCOMPLETE),
        "reason": (
            "기존 FID 열거가 부분 관측이라 빈 FID를 단정할 수 없다 — "
            "절단은 이 콘솔의 기본 경로이고 childCount가 진짜 총계다."
        ),
        **read.to_dict(),
    }


def _fid_assignment_requested(
    fid_range: Mapping[str, object] | None,
    assumption_71: str | None,
    fid_range_visually_confirmed_empty: bool | None,
    assignment_requested: bool | None = None,
) -> bool:
    """FID를 배정하려는 호출인가.

    `assignment_requested`는 **명시 신호**다(round11 M7 N03). 이전에는 호출자가
    `assumption_71`을 넘기는 것으로 이 분기를 열었는데, 그러면 실측 판정값이 요청 신호를
    겸하게 되어 ① 툴 경계에서 NEGATIVE·INCONCLUSIVE 분기에 영영 도달하지 못하고
    ② `fid_range_visually_confirmed_empty`가 요구되지도 기록되지도 않는 죽은 필드가 된다.
    """
    if assignment_requested is not None:
        return assignment_requested
    return (
        fid_range is not None
        or assumption_71 is not None
        or fid_range_visually_confirmed_empty is not None
    )


def validate_assumption_71(value: str) -> str:
    """`ASSUMPTION-71` 판정값을 닫힌 집합에 대해 검증한다 — payload로 나가기 전에 쓴다."""
    if value not in ASSUMPTION_71_VALUES:
        raise ValueError(
            f"assumption_71 must be one of {sorted(ASSUMPTION_71_VALUES)}, got {value!r}"
        )
    return value


def _assumption_71_or_default(value: str | None) -> str:
    if value is None:
        return ASSUMPTION_71_GO
    if value not in ASSUMPTION_71_VALUES:
        raise ValueError(
            f"assumption_71 must be one of {sorted(ASSUMPTION_71_VALUES)}, got {value!r}"
        )
    return value


def _parse_fid_range(value: Mapping[str, object] | None) -> FIDRange | None:
    if value is None:
        return None
    start = _optional_int(value.get("start"))
    end = _optional_int(value.get("end"))
    if start is None or end is None or end < start:
        return None
    return FIDRange(start=start, end=end)


def _assign_fids(
    targets: tuple[PatchCandidate, ...],
    fid_range: FIDRange,
    *,
    existing_fids: frozenset[int],
    fid_range_visually_confirmed_empty: bool | None,
) -> tuple[tuple[PatchCandidate, ...], tuple[PatchTargetExclusion, ...]]:
    planned: list[PatchCandidate] = []
    exclusions: list[PatchTargetExclusion] = []
    next_fid = fid_range.start
    for target in targets:
        if next_fid > fid_range.end:
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=FID_RANGE_EXHAUSTED,
                    reason=(
                        f"사용자가 입력한 FID 범위 {fid_range.start}-{fid_range.end}를 "
                        "초과해 이 장비에는 FID를 배정하지 않았다."
                    ),
                )
            )
            continue
        proposed_fid = next_fid
        next_fid += 1
        if proposed_fid in existing_fids:
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=FID_ALREADY_IN_USE,
                    reason=f"FID {proposed_fid}는 콘솔 기존 픽스처가 이미 사용 중이다.",
                    proposed_fid=proposed_fid,
                )
            )
            continue
        planned.append(
            target.with_fid(
                proposed_fid,
                fid_range_visually_confirmed_empty=fid_range_visually_confirmed_empty,
            )
        )
    return tuple(planned), tuple(exclusions)


@dataclass(frozen=True)
class ExistingFidRead:
    """콘솔에서 읽은 기존 FID와 **못 읽은 것의 수**.

    어느 축이든 0이 아니면 `fids`는 기존 FID의 **부분 집합**이다 — 그것을
    전체로 읽고 "빈 FID"를 고르면 **이미 쓰이는 번호를 배정**하게 되고,
    §0 함정 2가 적은 대로 MA3는 그것을 조용히 받아들여 엉뚱한 픽스처를 덮는다.
    이 앱에는 실행 취소가 없다.

    **[round15 N01/N02] 기본 인스턴스는 "조회하지 않았다"를 뜻한다.** 이전 판은
    기본값이 `complete=True`여서 ① 포트가 없을 때(`fid_property_port=None`,
    시그니처상 기본값) GO 분기 가드가 발화하지 않은 채 FID가 배정되고
    ② 비-GO 분기 payload가 **수행하지 않은 읽기**를 "완전 · 기존 FID 0개"로 보고했다.
    round14 T02가 루트 실패 갈래에만 처방을 적용하고 같은 함수 6줄 위의 형제 갈래를
    빠뜨린 결과다. 조회를 실제로 시도한 경로만 `attempted=True`를 붙인다.
    """

    fids: tuple[int, ...] = ()
    child_count: int | None = None
    enumerated_count: int = 0
    #: 선언됐으나 열거에 나오지 않은 슬롯 수. 총계를 모르면 `None`.
    unseen: int | None = 0
    #: 슬롯은 봤으나 FID 값을 얻지 못한 건수 — 열거 축과 **다른 축**이라 따로 센다.
    unreadable_fids: int = 0
    #: 슬롯 번호가 없거나 중복이라 쓸 수 없던 행 수.
    unusable_rows: int = 0
    #: 매핑이 아니라 슬롯 번호조차 물어볼 수 없던 행 수 — [round15 N06] 이전 판은
    #: 이 행을 계수 없이 버려 다섯 축 어디에도 걸리지 않는 여섯 번째 실패 형태를 남겼다.
    unparsable_rows: int = 0
    #: 열거 행이 선언 총계보다 많다 — 형제 리더는 이 스냅샷을 거부한다.
    over_enumerated: bool = False
    #: 루트 상태 자체를 못 읽었다 — 아무 것도 모른다.
    root_unreadable: bool = False
    #: 콘솔 조회를 **시도했는가**. 기본은 거짓 — 미수행과 "읽었고 깨끗했다"는 다르다.
    attempted: bool = False

    @property
    def complete(self) -> bool:
        return self.attempted and not (
            self.root_unreadable
            or self.over_enumerated
            or self.unseen is None
            or self.unseen > 0
            or self.unreadable_fids > 0
            or self.unusable_rows > 0
            or self.unparsable_rows > 0
        )

    def reason(self) -> str:
        """왜 불완전한가 — **관측된 사실만** 적는다. 전부 0인 문장을 내지 않는다.

        **[round17 S17-04] 반환값은 문장 *조각*이다 — 자체에 ` — `도 마침표도 넣지 않는다.**
        호출부(`build_patch_plan`)가 이 조각을 자기 문장 **안에** 끼워 넣으므로, 조각이
        대시를 품으면 완성된 문장에 대시가 둘이 되어 어디까지가 어느 절인지 사라진다 —
        `— 기존 FID 사전검사가 불완전하다 — 열거된 슬롯 3개가 … 많다 — 스냅샷이
        자기모순이다.`가 실제로 나갔다(48조합 중 24건). round16 S16-01이 같은 기제를
        `console_read_caveat`에서 이미 한 번 닫았다: 꼬리 판정은 **독립 문장**으로 잇는다.
        여기서는 그 꼬리를 `notes()`가 완결 문장으로 돌려준다.
        """
        if not self.attempted:
            return "콘솔 FID 조회를 수행하지 않았다"
        if self.root_unreadable:
            return "콘솔의 픽스처 루트 상태를 읽지 못했다"
        parts: list[str] = []
        if self.over_enumerated:
            parts.append(
                f"열거된 슬롯 {self.enumerated_count}개가 선언 총계 {self.child_count}개보다 많다"
            )
        if self.unseen is None:
            parts.append("선언 총계(childCount)를 읽지 못해 무엇을 못 봤는지 셀 수 없다")
        elif self.unseen > 0:
            parts.append(f"선언 {self.child_count}개 중 {self.unseen}개를 열거하지 못했다")
        if self.unusable_rows:
            parts.append(f"슬롯 번호가 없거나 중복인 행 {self.unusable_rows}개를 쓰지 못했다")
        if self.unparsable_rows:
            parts.append(f"슬롯으로 해석되지 않는 행 {self.unparsable_rows}개가 섞여 있다")
        if self.unreadable_fids:
            parts.append(f"열거된 슬롯 {self.unreadable_fids}개의 FID 값을 얻지 못했다")
        return " · ".join(parts) if parts else "부분 관측이다"

    def notes(self) -> tuple[str, ...]:
        """`reason()` 조각에 이어 붙는 **독립 완결 문장들**(각각 마침표로 끝난다).

        [round17 S17-04] 조각 안에 섞으면 한 문장에 대시가 둘이 되거나(위) `" · "` 목록
        중간에 판정 꼬리가 박혀 바로 앞 절에만 붙은 것처럼 읽힌다(S16-01이 명명한 기제).
        """
        if not self.attempted or self.root_unreadable:
            return ("기존 FID를 하나도 확인하지 못했다.",)
        if self.over_enumerated:
            return ("열거가 선언 총계를 넘었으므로 이 스냅샷은 자기모순이다.",)
        return ()

    def to_dict(self) -> dict[str, object]:
        return {
            "attempted": self.attempted,
            "child_count": self.child_count,
            "enumerated_count": self.enumerated_count,
            "unseen_count": self.unseen,
            "unreadable_fid_count": self.unreadable_fids,
            "unusable_row_count": self.unusable_rows,
            "unparsable_row_count": self.unparsable_rows,
            "over_enumerated": self.over_enumerated,
            "root_unreadable": self.root_unreadable,
            "complete": self.complete,
        }


def _existing_fids_from_console(fid_property_port: FidPropertyPort | None) -> ExistingFidRead:
    """기존 FID를 읽되 **못 읽은 것을 세서 함께 돌려준다**.

    `server/prechk/inventory.py` 모듈 독스트링 1·2번이 정한 규율을 그대로 따른다:
    **절단은 기본 경로**이고(실물 콘솔은 19대에서 절단된다), `node.childCount`가
    **진짜 총계**며, `len(children)`를 총계로 읽은 조사가 이 저장소에서 실제로 틀렸다.
    그래서 열거 수와 `childCount`를 대조하고, 프로퍼티 읽기 실패도 미판독으로 센다
    (round11 N01 — 이전 판은 둘 다 삼켜 이미 쓰이는 FID를 배정했다).
    """
    if fid_property_port is None:
        # [round15 N01] 포트가 없으면 **조회 자체를 하지 않았다**. 이전 판은 여기서
        # `complete=True`인 기본 인스턴스를 돌려줘 GO 분기 가드를 통과시켰고, payload는
        # 그것을 "읽었고 기존 FID가 0개였다"와 구별 불가능하게 실었다.
        return ExistingFidRead()
    state = fid_property_port.query_state(FID_FIXTURE_ROOT)
    if state.get("ok") is not True:
        # [round14 T02] 루트를 못 읽으면 **아무 것도 모른다**. 이전 판은 이 경우에도
        # 계수만 0으로 채워 "선언 None대 중 0대만 열거했고 0대는 FID를 얻지 못했다"는,
        # 조작자에게 **아무 문제 없음으로 읽히는** 문장을 냈다.
        return ExistingFidRead(attempted=True, root_unreadable=True)

    node = state.get("node")
    child_count = _optional_int(node.get("childCount")) if isinstance(node, Mapping) else None
    raw_rows = _row_sequence(state.get("children"))
    children = [row for row in raw_rows if isinstance(row, Mapping)]
    # [round15 N06] 매핑이 아닌 행은 슬롯 번호조차 물어볼 수 없다. 이전 판은 그것을
    # 계수 없이 버려 다섯 축 어디에도 걸리지 않는 여섯 번째 실패 형태를 만들었고,
    # 같은 스냅샷에서 형제 리더(`read_inventory`)는 `AttributeError`로 죽는다.
    unparsable_rows = len(raw_rows) - len(children)
    existing_fids: list[int] = []
    unread = 0
    # [round12 R01] **행 수가 아니라 서로 다른 슬롯 수**를 센다. 중복 `i`가 섞여 오면
    # `len(children)`이 부풀어 `childCount`와 맞아떨어지고, 실제로는 못 읽은 슬롯이 남았는데
    # `complete`로 보고돼 이미 쓰이는 FID를 배정했다 — C1과 **같은 실패 양식**이다.
    # 형제 리더가 같은 두 형태를 모두 방어한다(`server/prechk/inventory.py`의
    # 슬롯 중복 건너뛰기 · `observed_count > child_count`에서의 `InventoryReadError`).
    read_slots: set[int] = set()
    unreadable_fids = 0
    for child in children:
        child_index = _optional_int(child.get("i"))
        if child_index is None or child_index in read_slots:
            unread += 1
            continue
        response = fid_property_port.query_property(
            f"{FID_FIXTURE_ROOT}/{child_index}", FID_PROPERTY_NAME
        )
        # 조회를 시도해 **결말이 난** 슬롯은 모두 관측 슬롯이다 — 값을 못 읽었어도
        # "그 슬롯을 봤다"는 사실은 총계 대조에 쓰인다. [round13 S05] 이전 판은 실패 슬롯을
        # 관측에서 빼면서 `unread`도 올려 **같은 슬롯을 두 번** 셌고, 그 결과 사용자에게
        # "선언 2대 중 4대를 읽지 못했다"는 산술적으로 불가능한 문구가 나갔다.
        read_slots.add(child_index)
        fid = _fid_int(response.get("value")) if response.get("ok") is True else None
        if fid is None:
            unreadable_fids += 1
            continue
        existing_fids.append(fid)

    # 총계를 모르거나, 관측이 총계와 **어느 방향으로든** 어긋나면 완전하다고 말할 수 없다.
    # [round14 T01/T03] 같은 슬롯을 두 축으로 세지 않는다 — 루프에서 이미 센 못 쓴 행은
    # 총계 대조가 다시 세면 `unread > child_count`가 되어 "선언 2대 중 4대를 읽지 못했다"는
    # 산술적으로 불가능한 문구가 나갔다. 못 본 슬롯 수는 **한 번만** 센다.
    over_enumerated = child_count is not None and len(read_slots) > child_count
    unseen = None if child_count is None else max(child_count - len(read_slots), 0)

    return ExistingFidRead(
        fids=tuple(existing_fids),
        child_count=child_count,
        enumerated_count=len(read_slots),
        unseen=unseen,
        unreadable_fids=unreadable_fids,
        unusable_rows=unread,
        unparsable_rows=unparsable_rows,
        over_enumerated=over_enumerated,
        root_unreadable=False,
        attempted=True,
    )


def _fid_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _fid_skipped_checks(assumption_71: str) -> tuple[Mapping[str, object], ...]:
    if assumption_71 == ASSUMPTION_71_GO:
        return ()
    return (
        {
            "kind": validate_autopatch("skipped_check_kind", FID_CONFLICT_PRECHECK_DESCOPE),
            "label": skipped_check_label(FID_CONFLICT_PRECHECK_DESCOPE),
            "reason": (
                "ASSUMPTION-71이 부정 또는 INCONCLUSIVE라 기존 FID 충돌 사전검사를 수행하지 "
                "않고, 사용자가 입력한 FID 범위와 별도 육안 확인에 의존한다."
            ),
            "assumption_71": assumption_71,
        },
    )


def _fid_safety_payload(
    assumption_71: str,
    *,
    confirmation_required: bool,
    confirmation_recorded: bool | None,
    existing_read: ExistingFidRead,
    precheck_performed: bool,
) -> Mapping[str, object]:
    return {
        "assumption_71": assumption_71,
        "active_safety": (
            "fid_conflict_precheck"
            if assumption_71 == ASSUMPTION_71_GO
            else "visual_empty_range_confirmation"
        ),
        # `performed`가 부분 관측을 감추지 못하게 열거 계수를 함께 싣는다(round11 N01).
        "conflict_precheck": {
            "performed": precheck_performed,
            "property": FID_PROPERTY_NAME if precheck_performed else None,
            "source_path": FID_FIXTURE_ROOT if precheck_performed else None,
            "existing_fids": list(existing_read.fids),
            "read": existing_read.to_dict(),
        },
        "visual_confirmation": {
            "required": confirmation_required,
            "confirmed": confirmation_recorded,
            "field": "fid_range_visually_confirmed_empty",
        },
    }


def _rejection_for_report(report: Mapping[str, object]) -> PatchPlanRejection | None:
    for entry in _mapping_rows(report.get("skipped_checks")):
        if entry.get("kind") == MULTI_SYSTEM_MAPPING_ABSENT:
            reason = _string_or_default(
                entry.get("reason"), "System→콘솔 유니버스 매핑이 없어 콘솔 대조를 수행하지 않았다."
            )
            return PatchPlanRejection(code=MULTI_SYSTEM_MAPPING_ABSENT, reason=reason)

    diffs = report.get("diffs")
    if not isinstance(diffs, Mapping):
        return PatchPlanRejection(
            code=INVALID_REPORT_PAYLOAD,
            reason="리포트 payload에 diffs 객체가 없어 패치 후보를 만들 수 없다.",
        )
    if diffs.get("performed") is False:
        report_reason = _string_or_default(
            diffs.get("reason"), "1단계 리포트가 콘솔 대조 미수행 사유를 제공하지 않았다."
        )
        return PatchPlanRejection(
            code=COMPARISON_NOT_PERFORMED,
            reason=f"1단계 대조가 수행되지 않아 패치 후보를 만들 수 없다: {report_reason}",
            quoted_report_reason=report_reason,
        )
    return None


def _candidates_from_report(report: Mapping[str, object]) -> tuple[PatchCandidate, ...]:
    diffs = report.get("diffs")
    if not isinstance(diffs, Mapping):
        return ()
    fixture_basis = _address_basis_by_fixture(report)
    candidates: list[PatchCandidate] = []
    for index, row in enumerate(_mapping_rows(diffs.get("missing_in_console"))):
        unit_number = _optional_string(row.get("unit_number"))
        instrument_type = _required_string(row.get("instrument_type"))
        universe = _required_int(row.get("universe"))
        address = _required_int(row.get("address"))
        detail = _required_string(row.get("detail"))
        address_basis = fixture_basis.get((unit_number, instrument_type, universe, address))
        candidates.append(
            PatchCandidate(
                id=_candidate_id(index, unit_number, instrument_type, universe, address, detail),
                unit_number=unit_number,
                instrument_type=instrument_type,
                universe=universe,
                address=address,
                detail=detail,
                address_basis=address_basis,
                source_index=index,
            )
        )
    return tuple(candidates)


def _address_basis_by_fixture(
    report: Mapping[str, object],
) -> dict[tuple[str | None, str, int, int], str | None]:
    designed = report.get("designed_rig")
    if not isinstance(designed, Mapping):
        return {}
    indexed: dict[tuple[str | None, str, int, int], str | None] = {}
    for fixture in _mapping_rows(designed.get("fixtures")):
        unit_number = _optional_string(fixture.get("unit_number"))
        instrument_type = _optional_string(fixture.get("instrument_type"))
        universe = _optional_int(fixture.get("universe"))
        address = _optional_int(fixture.get("address"))
        if instrument_type is None or universe is None or address is None:
            continue
        indexed[(unit_number, instrument_type, universe, address)] = _optional_string(
            fixture.get("address_basis")
        )
    return indexed


def _address_basis_notes(
    report: Mapping[str, object], targets: tuple[PatchCandidate, ...]
) -> tuple[str, ...]:
    if not any(target.address_basis == ADDRESS_BASIS_ABS_BACK_CALCULATED for target in targets):
        return ()
    designed = report.get("designed_rig")
    if not isinstance(designed, Mapping):
        return ()
    note = _optional_string(designed.get("address_basis_note"))
    return (note,) if note else ()


def _candidate_id(
    index: int,
    unit_number: str | None,
    instrument_type: str,
    universe: int,
    address: int,
    detail: str,
) -> str:
    identity = {
        "address": address,
        "detail": detail,
        "instrument_type": instrument_type,
        "source_index": index,
        "unit_number": unit_number,
        "universe": universe,
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "vwx-missing-" + sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _mapping_rows(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _row_sequence(value: object) -> tuple[object, ...]:
    """행을 **거르지 않고** 그대로 돌려준다 — 버려진 행의 수를 세야 하는 자리에서 쓴다.

    `_mapping_rows`는 비매핑 행을 조용히 버린다. 그 침묵이 round15 N06이다:
    버려진 행은 어느 축에도 걸리지 않아 부분 관측이 "완전"으로 등급됐다.
    """
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(value)


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _required_string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _required_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _string_or_default(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from types import MappingProxyType
from typing import Protocol

from server.prechk.patch import normalize_address
from server.vwx.address import ADDRESS_BASIS_ABS_BACK_CALCULATED
from server.vwx.diff import MULTI_SYSTEM_MAPPING_ABSENT
from server.vwx.typemap import is_vacuous_type_name
from server.vwx.verdicts import (
    ADDRESS_ALREADY_OCCUPIED,
    ADDRESS_BELOW_MINIMUM,
    ADDRESS_OVERLAP_IN_PLAN,
    COMPARISON_NOT_PERFORMED,
    DESIGNED_TYPE_NAME_VACUOUS,
    DESIGNED_TYPE_NAME_VACUOUS_JOIN_ABSENT,
    DESIGNED_TYPE_NAME_VACUOUS_QUANTITY_AXIS,
    FID_ALREADY_IN_USE,
    FID_BELOW_MINIMUM,
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

#: 콘솔 FID 번호 체계가 시작하는 최소값 — `_MINIMUM_ADDRESS_INDEX`의 **형제 축**이다
#: (round18 결함 R18-A). 근거는 같은 원전이다: `server/prechk/patch.py`의
#: `normalize_address`가 "The console's own numbering starts at one, so `0.0` ·
#: `1.0` · `0.1` name no addressable channel"이라고 못박는다(patch.py:121-123).
#: **콘솔 번호 체계가 1에서 시작한다**는 그 사실은 좌표에만 걸리는 성질이 아니다 —
#: 룰북의 `AddFixtures` 예제도 `for fid = 2, 10`으로 1 이상만 쓴다
#: (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:46`).
#:
#: **FID 축에만 있는 추가 근거**: 음수 FID는 콘솔에서 읽은 `existing_fids`와
#: **절대 충돌하지 않는다**. 즉 바닥이 없으면 충돌 사전검사가 구조적으로 무력해지고,
#: 그런데도 같은 payload가 `conflict_precheck.performed=true`로 "검사했고 깨끗하다"고
#: 보고한다 — 안전망이 없는 값에 안전망이 있다는 **거짓 보고**가 함께 나간다.
#:
#: **상한은 두지 않는다.** 좌표 축과 같은 판정이고 근거도 같은 종류다: MA3의 FID
#: 수용 상한은 이 SPEC에서 **실측된 적이 없고**(§B.2 · research.md §3 — 콘솔의 기존
#: FID를 읽는 것 자체가 최대 난제였다), 룰북·PROTOCOL 어디에도 최대값이 없다.
#: 미실측 위에 천장을 지어내면 콘솔이 받아들이는 FID를 이 계층이 날조로 거부한다
#: ("inventing a ceiling would reject addresses the console accepts", patch.py:128-133).
#: 그 판정을 `test_r18_no_fid_ceiling_is_fabricated`가 고정한다 — 근거 없이 상한을
#: 넣으면 그 대조군이 실패한다.
_MINIMUM_FID = 1

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


#: 조립이 실패했을 때 `reason` 자리에 싣는 **등재 코드**. 사람이 읽는 문장 대신 이 코드가
#: 나가고, 무엇이 깨졌는지는 구조화 칸(`reason_defect`)이 진다.
REASON_UNAVAILABLE = "reason_unavailable"
#: 구조화 칸의 결함 코드 — 지금은 형태 불변식 위반 하나다.
SENTENCE_SHAPE_VIOLATION = "sentence_shape_violation"
#: `reason` 자리에 문장 대신 올 수 있는 코드 **전수**. 자유 문자열이 이 자리로 새면
#: 조작자는 그것이 사유인지 코드인지 구별할 수 없다.
REASON_PLACEHOLDER_CODES: frozenset[str] = frozenset({REASON_UNAVAILABLE})


def _join_sentences(sentences: Sequence[str]) -> str:
    """완결 문장 조각을 한 문단으로 잇는다 — 빈 조각은 버린다.

    관측되지 않은 축을 빈 문장으로 남기면 `..`·`  `가 생긴다. 두 조립기가 **같은**
    이 함수를 쓴다 — 둘이 다르게 이으면 강등 경로와 강제 경로의 판정이 갈린다.
    """
    return " ".join(sentence for sentence in sentences if sentence)


@dataclass(frozen=True)
class AssembledSentences:
    """조립 결과. 성공이면 `text`가 문장이고 `defect`는 `None`.

    실패면 `text`는 **등재 코드**(`REASON_UNAVAILABLE`)이고 `defect`가 무엇이 깨졌는지를
    구조화해 담는다 — 문장은 잃되 판정과 진단은 남는다.
    """

    text: str
    defect: Mapping[str, object] | None = None


def assemble_sentences_or_defect(*sentences: str) -> AssembledSentences:
    """조립 실패를 **예외가 아니라 값으로** 돌려준다 — 차단 화면을 짓는 자리에서 쓴다.

    **[round18 R18-D]** 형태 불변식의 유일한 프로덕션 강제 자리가 하필 되돌릴 수 없는
    쓰기를 **막는** 거부를 짓는 자리였고, `assemble_sentences`의 `ValueError`는
    `ToolRegistry.dispatch`·runner·session 어디에도 가드가 없어 툴 경계를 그대로 탈출했다.
    그러면 조립이 실패하는 순간 **차단 자체가 사라진다** — 게이트가 자기가 지키려던 것을
    죽인다. 그래서 이 자리에서는 실패를 payload 필드로 **강등한다**: 사유 문장 자리에는
    등재 코드가 가고, 위반 내용은 구조화 칸으로 조작자에게 그대로 보인다. 거부 판정
    (`ok=False` · 차단 코드)은 **그대로 남는다**.

    `except Exception`으로 뭉개지 않는다 — 예외를 잡는 것이 아니라 애초에 던지지 않고,
    판정은 `assemble_sentences`와 **같은** `sentence_shape_violation`이 한다.
    """
    text = _join_sentences(sentences)
    violation = sentence_shape_violation(text)
    if violation is None:
        return AssembledSentences(text=text)
    return AssembledSentences(
        text=REASON_UNAVAILABLE,
        defect=MappingProxyType(
            {
                "code": SENTENCE_SHAPE_VIOLATION,
                "violation": violation,
                "assembled": text,
                "fragments": tuple(sentence for sentence in sentences if sentence),
            }
        ),
    )


def assemble_sentences(*sentences: str) -> str:
    """완결 문장 여럿을 한 문단으로 잇고 **형태 불변식을 강제한다**.

    빈 조각은 버린다 — 관측되지 않은 축을 빈 문장으로 남기면 `..`·`  `가 생긴다.
    위반이면 사람에게 내보내지 않고 **즉시 실패한다**: 조용히 나가면 이 SPEC이
    일곱 라운드 반복한 대로 다음 감사에서야 발견된다.

    **사람에게 나가는 판정을 짓는 자리에서는 이것을 쓰지 마라** — 거기서 던지면 판정이
    통째로 사라진다(R18-D). 그런 자리는 `assemble_sentences_or_defect`로 강등한다.
    """
    text = _join_sentences(sentences)
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


#: 콘솔 슬롯 하나의 `Patch` 프로퍼티 이름 — `FID_PROPERTY_NAME`의 형제 축이다.
#: 이 계층은 이 값을 **좌표로만** 쓴다(누가 그 FID를 들고 있나). 판독은 짓지 않고
#: PRESERVE 경로의 `normalize_address`에 그대로 넘긴다 — 형제 표면
#: `apply.read_console_fixtures`와 같은 파서다. 좌표를 두 번 정의하지 않는다.
PATCH_PROPERTY_NAME = "Patch"

#: FID 하나를 든 콘솔 슬롯 **전원**의 좌표. 원소가 `None`이면 그 슬롯의 주소를 판독하지
#: 못했다는 뜻이고, 빈 튜플은 그 FID를 든 슬롯을 하나도 모른다는 뜻이다 — 두 상태 모두
#: 승격을 거부하지만 서로 다른 사실이라 뭉치지 않는다.
FidHolderAddresses = tuple[tuple[int, int] | None, ...]


def _no_fid_holders(_fid: int) -> FidHolderAddresses:
    """근거 없음 — `_assign_fids`의 기본 판독기.

    이 판독기를 쓰는 호출은 **모든 FID 점유를 진짜 충돌로** 본다. 즉 R21-A 이전과
    글자 그대로 같은 판정이다. 기본값을 fail-closed로 두는 이유는 `_assign_fids`가
    `FIDRange`를 직접 조립하는 형제 진입점에도 열려 있기 때문이다(round18 R18-A).
    """
    return ()


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
    #: [round18 R18-D] 사유 문장 **조립이 실패했을 때** 무엇이 깨졌는지. 이 칸이 차 있으면
    #: `reason`은 사람이 읽는 문장이 아니라 `REASON_PLACEHOLDER_CODES`의 등재 코드다.
    #: 거부 판정 자체(`code`·`label`)는 이 칸과 무관하게 그대로 나간다 — 문장을 짓다
    #: 죽어서 차단이 사라지는 일이 없어야 한다.
    reason_defect: Mapping[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": validate_autopatch(self.vocabulary, self.code),
            "label": autopatch_label(self.vocabulary, self.code),
            "reason": self.reason,
        }
        if self.quoted_report_reason is not None:
            payload["quoted_report_reason"] = self.quoted_report_reason
        if self.reason_defect is not None:
            payload["reason_defect"] = dict(self.reason_defect)
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
    """계획을 세우고 **1단계 대조가 삼켰을 수 있는 것을 고지한다**(round18 R18-J).

    고지는 `_plan_from_report`가 어느 갈래로 나가든 붙는다 — 계획 갈래에만 붙이면
    거부 화면을 본 조작자는 같은 사실을 보지 못하고, 그것이 이 SPEC이 여덟 라운드
    연속 지적받은 **형제 표면 미적용**이다. 붙이는 자리를 갈래마다 두지 않고 여기
    한 곳에 두는 이유도 같다: 갈래가 늘어날 때 새 갈래만 고지를 잃는 일이 없다.
    """
    plan = _plan_from_report(
        report,
        selected=selected,
        dry_run=dry_run,
        fid_range=fid_range,
        assumption_71=assumption_71,
        fid_range_visually_confirmed_empty=fid_range_visually_confirmed_empty,
        fid_property_port=fid_property_port,
        assignment_requested=assignment_requested,
    )
    notices = _vacuous_designed_type_checks(report)
    if not notices:
        return plan
    return replace(plan, skipped_checks=notices + plan.skipped_checks)


def _plan_from_report(
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
            # [round19 minor#9] 입력 거부도 **콘솔이 무엇을 못 보여줬는지**를 싣는다.
            # `server/orchestrator/tools.py`가 못박은 원칙이고, round18의 갈래 순서
            # 변경이 이 고지를 payload에서 지웠다. `fid_safety`는 여전히 싣지 않는다 —
            # 고지(무엇을 못 봤다)와 주장(검사했고 깨끗하다)은 다른 것이다.
            skipped_checks=_fid_precheck_notices(assumption_71_value, fid_property_port),
        )
    valid_fid_range = parsed_fid_range.parsed
    if valid_fid_range is None:
        # [round18 R18-A] 사유는 `_parse_fid_range`가 **어느 축이 왜 틀렸는지**로
        # 만든 것을 그대로 싣는다. 이전 판은 세 결함을 한 문장에 뭉쳐 두어
        # ① 조작자가 어느 축을 고쳐야 하는지 알 수 없었고 ② 축 하나를 지워도
        # 사유가 같아 대조군이 삭제를 잡지 못했다.
        #
        # **거부는 `_fid_safety_payload` 앞에서 끝난다** — 거부된 호출의 payload에는
        # `fid_safety`가 아예 실리지 않으므로 `conflict_precheck.performed=true`가
        # "검사했고 깨끗하다"고 주장할 자리가 없다. 이 정직성이 R18-A의 나머지 절반이다.
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=INVALID_FID_RANGE,
                reason=parsed_fid_range.defect,
                vocabulary="fid_assignment_rejection_reason",
            ),
            # [round19 minor#9] 고지만 복원한다 — 위 `fid_range_required`와 같은 규율.
            skipped_checks=_fid_precheck_notices(assumption_71_value, fid_property_port),
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
            # [round19 minor#9] 이 갈래는 비-GO뿐이므로 고지는 사전검사 **미수행**
            # 강등이고, 콘솔을 건드리지 않는다(round16 S16-02가 고정한 성질).
            skipped_checks=_fid_precheck_notices(assumption_71_value, fid_property_port),
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
        # [round17 S17-04] 조각을 문장 안에 끼우던 조립을 **문장 단위 조립**으로 바꾼다.
        # `reason()`은 조각(대시·마침표 없음), `notes()`는 완결 문장이다.
        # [round18 R18-D] 조립 실패는 **던지지 않는다** — 여기는 되돌릴 수 없는 쓰기를
        # 막는 거부를 짓는 자리이고, 여기서 예외가 나가면 `ToolRegistry.dispatch`에
        # 가드가 없어 차단 자체가 사라진다. 문장만 잃고 판정은 남긴다.
        reason = assemble_sentences_or_defect(
            f"기존 FID 사전검사가 불완전하다 — {existing_read.reason()}.",
            *existing_read.notes(),
            "부분 관측으로 빈 FID를 단정하면 이미 쓰이는 번호를 배정하게 된다.",
        )
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=FID_PRECHECK_READ_INCOMPLETE,
                reason=reason.text,
                vocabulary="target_exclusion_reason",
                reason_defect=reason.defect,
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
        valid_fid_range,
        existing_fids=frozenset(existing_read.fids),
        fid_range_visually_confirmed_empty=confirmation_recorded,
        # [round23 R21-A] 판독기는 **제안된 FID를 물을 때만** 콘솔에 간다. 포트가 없는
        # 호출(사전검사 미수행)에는 `_no_fid_holders`가 가고, 그 호출은 이전과 글자
        # 그대로 같은 판정을 받는다 — 모든 점유가 진짜 충돌이다.
        fid_holders=_fid_holder_reader(fid_property_port, existing_read),
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


@dataclass(frozen=True)
class _FidRangeParse:
    """사용자가 준 `fid_range` 하나를 정수 쌍으로 바꾼 결과, 또는 **왜 아닌지**.

    PRESERVE 경로의 :class:`server.prechk.patch.AddressParse`와 같은 형태다 — 실패하면
    값이 `None`이고 **기본값을 지어내지 않는다**("a fabricated ``0`` or ``1`` would enter
    collision detection as a real address", `server/prechk/patch.py:104-106`).

    사유를 값과 **함께** 싣는 이유는 두 가지다. ① 세 결함(형식·바닥·순서)은 조작자에게
    서로 다른 고칠 것을 가리킨다 — 하나로 뭉치면 어느 축을 고쳐야 하는지 알 수 없다
    (round11 M5 N3가 `lua_generation_refused`에서 배운 것과 같다). ② 축을 하나 지워도
    "거부됨"이라는 결과는 그대로라 **대조군이 축 삭제를 못 잡는다** — 사유가 갈라져
    있어야 잡힌다(round18 R18-A).

    `parsed`가 `None`인 것과 `defect`가 비지 않은 것은 **같은 사건**이다
    (`test_r18_fid_range_parse_is_exactly_one_of_value_or_defect`가 고정한다).
    """

    parsed: FIDRange | None = None
    defect: str = ""


def _parse_fid_range(value: Mapping[str, object] | None) -> _FidRangeParse:
    if value is None:
        return _FidRangeParse()
    start = _optional_int(value.get("start"))
    end = _optional_int(value.get("end"))
    if start is None or end is None:
        return _FidRangeParse(defect="fid_range는 정수 start와 end를 포함해야 한다.")
    # [round18 결함 R18-A] **바닥을 순서보다 먼저 본다.** 이전 판은 `end < start`만
    # 검사했고, 그래서 `{'start': -10, 'end': -8}`이 통과해 `fid = "-10"`인 Lua가
    # 사람 손에 갔다. 게다가 같은 payload가 `conflict_precheck.performed=true`로
    # "검사했고 깨끗하다"고 보고했다 — 음수 FID는 콘솔에서 읽은 기존 FID와 절대
    # 충돌하지 않으므로 충돌검사가 구조적으로 무력한데도 그렇다.
    #
    # 순서 검사를 먼저 두면 음수 쌍이 `end < start`에 흡수되지 않는 한 그대로 새고,
    # 흡수되는 경우에도 두 축 중 어느 검사가 살아 있는지 구별할 수 없다. 바닥을
    # 먼저 두면 `{'start': 5, 'end': -1}`이 **바닥 사유**로 거부되므로 `end` 축
    # 검사를 지우면 사유가 순서 사유로 바뀌어 대조군이 잡는다.
    #
    # 두 축을 `or` 한 조건으로 묶는 형태는 PRESERVE 경로가 좌표에서 쓰는 형태
    # 그대로다(`patch.py:141`) — 한쪽만 막으면 반쪽이다.
    if start < _MINIMUM_FID or end < _MINIMUM_FID:
        return _FidRangeParse(
            defect=(
                f"fid_range의 start·end는 콘솔 최소 FID {_MINIMUM_FID} 이상이어야 한다 — "
                f"입력은 start={start} end={end}다."
            )
        )
    if end < start:
        return _FidRangeParse(defect="fid_range의 end는 start보다 작을 수 없다.")
    # 상한은 두지 않는다 — `_MINIMUM_FID` 주석의 근거 참조. 거대값은 그대로 통과한다.
    return _FidRangeParse(parsed=FIDRange(start=start, end=end))


def _slot_address(port: FidPropertyPort, slot: int) -> tuple[int, int] | None:
    """콘솔 슬롯 하나의 `(유니버스, 주소)` — 못 읽었거나 주소가 아니면 `None`.

    **예외를 감싸지 않는다.** 이 슬롯은 이미 `query_property`에 성공적으로 답해
    FID를 내놓은 슬롯이다(그래서 `fid_slots`에 있다) — 열거로 왔든 절단 복구
    스윕으로 왔든 **실재가 증명된** 슬롯이라 투기적 프로브가 아니다. 스윕 프로브를
    감싸는 `_existing_fids_from_console`의 규약과 같은 기준이고, 감싸면 전송 결함이
    "주소를 못 읽었다"로 바뀌어 조작자가 원인이 아닌 것을 고치러 간다.
    """
    response = port.query_property(f"{FID_FIXTURE_ROOT}/{slot}", PATCH_PROPERTY_NAME)
    if response.get("ok") is not True:
        return None
    raw = response.get("value")
    parse = normalize_address(raw if isinstance(raw, str) else None)
    universe, address = parse.universe, parse.address
    if universe is None or address is None:
        return None
    return (universe, address)


def _fid_holder_reader(
    port: FidPropertyPort | None, read: ExistingFidRead
) -> Callable[[int], FidHolderAddresses]:
    """FID -> 그 값을 든 슬롯 전원의 좌표. **물어본 FID만** 콘솔에서 읽는다.

    **비용 상한 — 구조적이고, `fid_range`의 크기와 무관하다.**

    * 슬롯 하나는 FID 하나를 든다. 아래 `answered` 기억 때문에 **한 슬롯을 두 번 읽지
      않는다**. 따라서 이 판독기가 내는 `query_property` 총 횟수는
      **`len(read.fid_slots)`를 넘지 못한다** — 즉 사전검사가 FID를 읽어낸 슬롯 수이고,
      이미 수행한 읽기 횟수를 넘지 않는다(최악의 경우 FID 사전검사 비용의 2배).
    * 사용자가 `fid_range`를 아무리 넓게 줘도 이 상한은 움직이지 않는다. 넓은 대역은
      제안되는 FID의 **값**을 바꿀 뿐 콘솔에 있는 슬롯 수를 늘리지 못한다.
    * 실제 횟수는 보통 그보다 훨씬 작다: `_assign_fids`는 대상 하나에 FID 하나를
      제안하므로 프로브는 **충돌한 제안 수**만큼만 난다(실물 M8 2회차는 3회).

    기억을 caller의 성질(`next_fid` 단조 증가)에 맡기지 않고 **여기서 진다**. 맡기면
    상한이 호출자를 고쳐야 유지되는 약속이 되고, 이 SPEC이 반복해 배운 대로 그런 약속은
    형제 진입점에서 깨진다. 미리 전 슬롯의 주소를 읽어 표를 짓는 형태를 쓰지 않은 이유도
    같은 셈이다 — 그 표는 39대 리그에서 39회를 쓰면서 그중 3행만 쓰인다.

    범위를 미리 좁히지 않는 이유는 다른 규율이다 — 어느 FID가 제안되는지는
    `_assign_fids`의 산술이 정하고, 그 산술을 여기서 다시 쓰면 두 벌이 갈라진다.
    물어보는 쪽이 정하고 이 함수는 답만 한다.
    """
    if port is None:
        return _no_fid_holders
    slots_by_fid: dict[int, list[int]] = {}
    for slot, fid in read.fid_slots:
        slots_by_fid.setdefault(fid, []).append(slot)
    answered: dict[int, FidHolderAddresses] = {}

    def holders(fid: int) -> FidHolderAddresses:
        if fid not in answered:
            answered[fid] = tuple(_slot_address(port, slot) for slot in slots_by_fid.get(fid, ()))
        return answered[fid]

    return holders


def _fid_holder_is_this_target(
    proposed_fid: int,
    target: PatchCandidate,
    fid_holders: Callable[[int], FidHolderAddresses],
) -> bool:
    """그 FID를 든 콘솔 픽스처가 **이 대상의 도면 자리에 있는 바로 그 픽스처**인가.

    [round23 R21-A] 이것이 "내가 만든 것"과 "남이 쓰는 것"을 가르는 **유일한 규칙**이다.
    참이면 `_assign_fids`는 배제하지 않고 대상을 주소 계층으로 넘긴다 — 거기서
    `screen_idempotent`가 타입·모드까지 보고 멱등/충돌/확인 불가를 가른다. 이 함수가
    타입·모드를 **보지 않는 것은 의도**다: 그 판정은 이미 형제 표면에 있고, 여기서 한 번 더
    정의하면 두 규약이 갈라진다(이 SPEC이 일곱 라운드 반복한 기제).

    판정은 **관측된 점유자 집합 전체에 대한 등식 하나**다 — 후보 중 하나를 고르지 않는다.

    **[감사자에게 · round23] 이 형태는 round17 모호성 census(`ambiguity_candidate_sites`,
    `len(x) == 1` · `x[0]` · `next(...)` 세 축)의 등재를 피하려고 고른 것이 아니다.**
    census가 잡는 것은 *"후보 여럿에서 하나를 고르는"* 자리이고, 그런 자리는 열거 순서에
    판정이 의존할 수 있어 등재와 순서 불변 대조군을 요구한다. 여기에는 **고를 후보가
    없다**: 점유자 전원이 우리 자리의 그 한 대와 같아야만 참이고, 원소를 하나 집어
    비교하는 단계가 존재하지 않는다. 즉 모호성이 **숨겨진 것이 아니라 사라졌다** —
    순서를 뒤집어도(`holders`의 원소 순서를 바꿔도) 길이가 1이 아닌 순간 이미 거짓이라
    순서가 결과를 바꿀 수 없다. 초안은 `len(holders) != 1` + `holders[0]`이었고 그것은
    census가 정확히 옳게 잡았다. 쪼갠 형태를 되살리면 등재 대상이 되고, 그때는
    `test_autopatch_types.py`의 레지스트리에 두 행을 넣어야 한다.

    세 상태가 자동으로 fail-closed다.

    * 든 슬롯이 0이면 근거가 없다(판독기가 기본값이거나 그 FID를 든 슬롯을 하나도 모른다).
    * 2 이상이면 콘솔에 같은 FID가 중복이라 "그 픽스처"가 성립하지 않는다.
    * 좌표를 판독하지 못한 슬롯은 `None`이라 어떤 대상 좌표와도 같지 않다.

    셋 다 진짜 충돌로 다룬다 — 등식이 성립하지 않으므로 거짓이다.

    **승격이 안전한 근거**: 승격된 대상의 도면 자리에는 그 픽스처가 실재하므로
    `screen_idempotent`의 `occupants`가 반드시 비지 않고, 그 함수의 갈래 넷은 **전부 배제**다
    (`apply.screen_idempotent`). 즉 승격된 대상은 Lua 항목이 되지 못한다 — 중복 FID가
    전달물로 나가는 경로는 열리지 않는다. 그 성질을
    `test_r21_a_promoted_target_never_reaches_the_lua`가 파이프라인 전체로 고정한다.
    """
    return fid_holders(proposed_fid) == ((target.universe, target.address),)


def _assign_fids(
    targets: tuple[PatchCandidate, ...],
    fid_range: FIDRange,
    *,
    existing_fids: frozenset[int],
    fid_range_visually_confirmed_empty: bool | None,
    fid_holders: Callable[[int], FidHolderAddresses] = _no_fid_holders,
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
        # [round18 결함 R18-A · 개별 값 축] **범위가 아니라 배정될 값 자체를** 본다.
        # `_parse_fid_range`를 거쳐 온 호출에서는 여기 걸릴 값이 없지만, `_assign_fids`는
        # `FIDRange`를 직접 조립한 호출자에게도 열려 있는 **두 번째 진입점**이다.
        # round17이 좌표 축에서 배운 그대로 — 게이트를 한 함수 경계에만 두면 형제
        # 진입점이 그대로 새어 나가고, 그 값이 `with_fid`를 타고 `LuaPatchEntry.fid`가
        # 되어 `fid = "-10"`인 전달물이 된다. 값을 1로 끌어올려 통과시키지 않고
        # 등재된 코드로 배제한다 — 자동 보정 0건(AC-AUTOPATCH-021②).
        #
        # 기존 FID 대조보다 **먼저** 둔다: 성립하지 않는 번호를 "이미 사용 중"으로
        # 보고하면 조작자가 원인이 아닌 것을 고치러 간다.
        if proposed_fid < _MINIMUM_FID:
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=FID_BELOW_MINIMUM,
                    reason=(
                        f"배정하려던 FID {proposed_fid}는 콘솔 최소 FID {_MINIMUM_FID} "
                        "미만이다 — 값을 고쳐 통과시키지 않고 제외한다."
                    ),
                    proposed_fid=proposed_fid,
                )
            )
            continue
        # [round23 R21-A] **점유는 두 가지다 — 남이 쓰는 것과 내가 만든 것.**
        # 실물 M8 세션에서 ZZAP1~3을 FID 501~503으로 만든 뒤 **같은 인자로 재호출**하면
        # 세 대상이 전부 여기서 `fid_already_in_use`로 빠졌다. 대상이 0건이 되니
        # `screen_idempotent`까지 가지 못하고, payload에서 `handoff`·`types`·`verification`
        # 키가 통째로 사라졌다 — 2회차 재호출이 "이미 했음" 대신 "점유됨"으로 보고되는,
        # REQ-AUTOPATCH-022가 금지하는 바로 그 뭉갬이다. round12 R05가 `screen_idempotent`와
        # `screen_console_occupancy`의 **순서**로 같은 뭉갬을 닫았는데, FID 배정이 그 둘보다
        # 위에서 같은 것을 다시 했다.
        #
        # **순서는 바꾸지 않는다** — round12 R05가 순서를 고치다 다른 것을 깨뜨렸고, 여기서
        # 배정을 주소 계층 뒤로 옮기면 `plan.targets`가 FID 없이 그 계층에 들어간다.
        # 고치는 것은 **분류**다: 그 FID를 든 픽스처가 이 대상의 도면 자리에 있는 그 픽스처면
        # 배제하지 않고 주소 계층에 넘긴다. 판정은 거기 한 곳에만 있다.
        #
        # `fid_already_in_use`는 지우지 않는다. 남이 그 FID를 쓰는 경우는 실재하고
        # (M0 쇼파일의 C-CONFLICT 미끼 A13·A14가 그것이다) 그건 진짜 충돌이다.
        if proposed_fid in existing_fids and not _fid_holder_is_this_target(
            proposed_fid, target, fid_holders
        ):
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
    #: 절단 복구 스윕이 **추가로** 관측한 슬롯 수 — 열거가 아니라 스윕이 근거인 슬롯이다.
    #: 이 계수는 `complete`가 읽지 않는다: 스윕은 **detail을 올릴 뿐**이고 완전성은
    #: 여전히 `unseen`·`unreadable_fids` 같은 자기 근거로만 판정된다(형제 리더
    #: `server/prechk/inventory.py:401-404`가 못박은 규율). 이 계수를 `complete`의
    #: 근거로 쓰면 "스윕을 돌렸으니 다 읽었다"는 R18-A식 거짓 보고가 된다.
    recovered_count: int = 0
    #: 스윕의 상한(= `child_count`). 스윕하지 않았으면 `None` — "0까지 훑었다"와
    #: "훑지 않았다"는 다르다.
    recovery_boundary: int | None = None
    #: 스윕 프로브가 **결말을 내지 못한** 건수 — 응답 자체를 받지 못했거나(전송 결함),
    #: 응답은 왔지만 값이 FID로 해석되지 않았다(형제 리더 독스트링 3번의 포인터 문자열).
    #: `ok=false`는 여기 세지 않는다: 그것은 희소 풀의 **부재**일 수 있어 결함이라 부를 수
    #: 없고, 이미 `unseen`이 그 슬롯을 들고 있다. 진단 전용이고 완전성 축이 아니다 —
    #: 프로브가 실패한 슬롯은 이미 `unseen`에 남아 판정을 막으므로 여기서 또 세면
    #: round14 T01/T03이 만든 "선언 2대 중 4대를 읽지 못했다"는 산술 불가능 문구가
    #: 되살아난다. 같은 슬롯을 두 판정 축으로 세지 않는다.
    probe_failures: int = 0
    #: 관측된 `(슬롯, FID)` 쌍 전원 — 열거와 스윕 **양쪽**이 여기 들어온다.
    #: [round23 R21-A] `fids`만으로는 "그 FID를 누가 들고 있나"를 물을 수 없어, FID 배정이
    #: 자기가 만든 픽스처와 남의 픽스처를 구별하지 못했다. 슬롯은 인벤토리와의 조인 키다
    #: (`read_console_slot_addresses` 참조).
    #:
    #: `to_dict()`에 싣지 않는다 — 그 payload는 **완전성 계수**를 보고하는 자리이고 이 값은
    #: 판정 축이 아니라 조인 입력이다. 버려지는 관측도 아니다: 이 쌍이 낳은 판정은
    #: `target_exclusions`가 `fid_already_in_use`를 내는지로 그대로 드러난다.
    fid_slots: tuple[tuple[int, int], ...] = ()

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
            "recovered_count": self.recovered_count,
            "recovery_boundary": self.recovery_boundary,
            "unseen_count": self.unseen,
            "unreadable_fid_count": self.unreadable_fids,
            "unusable_row_count": self.unusable_rows,
            "unparsable_row_count": self.unparsable_rows,
            "probe_failure_count": self.probe_failures,
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

    **[round19] 절단 복구 스윕을 붙였다.** 이전 판은 단일 `query_state`만 해서, 위 규율의
    나머지 절반 — 형제 리더 `server/prechk/inventory.py:391-417`의 `1..childCount` 유계
    스윕 — 이 없었다. 절단이 기본 경로인 콘솔에서 스윕이 없으면 열거는 **영원히**
    `childCount`에 못 미치고 `unseen>0`이 상시 성립한다. 실물 39대 쇼파일은 19대에서
    잘리므로 GO 분기가 **한 대도** 배정하지 못했다(M8 대상 0건). 스윕은 원전의 규율을
    그대로 가져온다:

    * **전제**: 열거에서 쓸 수 있는 슬롯이 **하나라도** 있어야 스윕한다. 원전 주석이
      과거 사고를 명시한다 — *"A numeric path segment degrades to a LIST POSITION when
      not one child of the node has an established slot … sweeping then would adopt
      positions as slots -- the promotion this function forbids above, and the defect
      that issued commands against pools 1/5/7 once before."* responder의
      `copilot_responder.lua:434-447`이 `any_slot_known`이 거짓일 때만
      `children[wanted_slot]`을 돌려주므로, 빈 열거에서 스윕하면 **위치를 슬롯으로
      오인**한 값을 기존 FID로 적재한다.
    * **경계**: `1..childCount` 유계. 상한은 지어낸 수가 아니라 콘솔이 선언한 총계다.
      조기 중단은 두지 않는다. 다만 그것이 **차단을 지키기 때문이 아니다** — 아래
      인덱스 도메인 전제 때문에 관측 슬롯은 `1..childCount` 안에만 있고, 관측 수가
      총계에 닿는 순간 남은 슬롯은 전부 이미 관측된 것이라 루프가 건너뛴다. 즉
      `len(read_slots) == child_count`에서 끊는 변형은 **관측 가능한 차이가 없는 등가**
      변형이다. 그래서 굳이 두지 않았을 뿐이고, 이 자리에 대조군은 없다(무대조군이
      아니라 등가 뮤턴트다 — 그 판정 근거를 여기 남긴다).
    * **완전성은 스윕으로 승격되지 않는다.** 스윕은 `read_slots`·`fids`라는 **관측**을
      늘릴 뿐이고, `complete`는 여전히 `unseen`·`unreadable_fids` 대조로만 판정된다.
      "스윕을 돌렸으니 다 읽었다"는 플래그를 두면 그것이 R18-A와 같은 거짓 보고다.
    * **인덱스 도메인 일치**: 열거 슬롯이 `1..childCount` **밖**에 있으면 스윕하지
      않는다. 그 스냅샷의 인덱스 도메인은 스윕 도메인이 아니므로(희소 풀), 범위 안을
      훑어 관측을 채우면 총계는 맞아떨어지고 정작 범위 밖 픽스처의 FID는 못 읽은 채
      `complete`가 된다. 원전이 `index_domain_unknown`으로 따로 표시하는 상태다.

    **비용**: 스윕은 슬롯당 `query_property` **1회**다. 최악 `childCount`회이며 절단이
    있을 때만 발화한다(실물 39대 → 최대 20회). 원전은 슬롯당 `query_state` + 프로퍼티
    읽기를 하는데 우리는 프로퍼티 1회로 줄였다 — 원전은 스냅샷에서 **이름**을 얻어야
    하고 희소/단선을 구분해 보고하지만, 이 층이 필요한 것은 FID 값 하나뿐이고 그
    구분은 이 층의 어떤 계수도 바꾸지 못한다(둘 다 슬롯을 미관측으로 남긴다). 정책
    스위치(원전의 `recover_truncated`)는 두지 않는다: 원전은 리포트용 빠른 부분 판독도
    정당한 산출물이라 스위치가 필요하지만, 이 사전검사의 산출물은 하나뿐이고 스윕을
    끄면 GO 분기가 상시 거부로 되돌아가는 것 말고는 아무 효과가 없다.
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
    # [round23 R21-A] 값과 **슬롯을 함께** 든다 — `fids`는 여기서 파생한다. 두 목록을
    # 나란히 채우면 한쪽만 갱신하는 갈래가 생기고, 그 어긋남은 "그 FID를 누가 들고
    # 있나"를 조용히 틀리게 만든다.
    fid_slots: list[tuple[int, int]] = []
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
        fid_slots.append((child_index, fid))

    # 여기까지가 **열거**의 결말이다. 스윕이 관측을 늘리기 전에 계수를 못박아 둔다 —
    # `enumerated_count`는 열거가 근거인 슬롯 수여야 하고, 스윕이 찾은 슬롯을 여기에
    # 섞으면 `reason()`의 "열거된 슬롯 N개…" 문장이 스윕 결과를 열거라고 말하게 된다.
    enumerated_count = len(read_slots)
    recovered_count = 0
    recovery_boundary: int | None = None
    probe_failures = 0
    if (
        child_count is not None
        # 원전의 `slots_established` — 하나라도 확립된 슬롯이 있어야 responder의
        # 슬롯 해석기가 위치가 아닌 슬롯으로 답한다(위 독스트링의 인용).
        and read_slots
        # 절단 판정은 **계수 대조**로 한다(`truncated` 플래그가 아니다 — 원전 독스트링 2번).
        and enumerated_count < child_count
        # 인덱스 도메인이 스윕 도메인과 어긋나면 스윕하지 않는다.
        and all(1 <= slot <= child_count for slot in read_slots)
    ):
        recovery_boundary = child_count
        for slot in range(1, recovery_boundary + 1):
            if slot in read_slots:
                continue
            try:
                probe = fid_property_port.query_property(
                    f"{FID_FIXTURE_ROOT}/{slot}", FID_PROPERTY_NAME
                )
            except Exception:  # noqa: BLE001 — 프로브는 **투기적**이다(아래 주석)
                # 없을 수도 있는 슬롯을 찔러 보는 조회다. 여기서 예외가 나가면
                # `build_patch_plan`이 그대로 터지고, `ToolRegistry.dispatch`에 가드가
                # 없어 **구조화된 거부 자체가 사라진다**(round18 R18-D가 명명한 기제).
                # 열거된 슬롯의 읽기는 감싸지 않는다 — 그쪽은 콘솔이 스스로 목록에 올린
                # 슬롯에 대한 전송 결함이고, 투기적 프로브와 성질이 다르다.
                probe_failures += 1
                continue
            fid = _fid_int(probe.get("value")) if probe.get("ok") is True else None
            if fid is None:
                # `ok=false`는 **부재**일 수도 있고(희소 풀 — 정보다) 프로퍼티 판독
                # 실패일 수도 있어 구별할 수 없다. 열거된 슬롯과 달리 이 슬롯의 **실재
                # 자체가 미증명**이므로, `unreadable_fids`로 세면 "그 슬롯은 있다"를
                # 단정하게 된다. 관측으로 올리지 않고 `unseen`에 남긴다 — fail-closed다.
                # 응답은 왔지만 값이 FID로 해석되지 않은 경우(원전 독스트링 3번의
                # 포인터 문자열)도 같은 자리에 남기고, 진단으로만 센다.
                if probe.get("ok") is True:
                    probe_failures += 1
                continue
            read_slots.add(slot)
            recovered_count += 1
            fid_slots.append((slot, fid))

    # 총계를 모르거나, 관측이 총계와 **어느 방향으로든** 어긋나면 완전하다고 말할 수 없다.
    # [round14 T01/T03] 같은 슬롯을 두 축으로 세지 않는다 — 루프에서 이미 센 못 쓴 행은
    # 총계 대조가 다시 세면 `unread > child_count`가 되어 "선언 2대 중 4대를 읽지 못했다"는
    # 산술적으로 불가능한 문구가 나갔다. 못 본 슬롯 수는 **한 번만** 센다.
    #
    # **[round19] 이 두 줄이 완전성의 유일한 근거로 남는다.** 스윕은 `read_slots`를
    # 늘렸을 뿐 판정을 건드리지 않는다 — 스윕이 아무 것도 회수하지 못하면 `unseen`은
    # 그대로 남아 배정이 거부된다.
    over_enumerated = child_count is not None and len(read_slots) > child_count
    unseen = None if child_count is None else max(child_count - len(read_slots), 0)

    return ExistingFidRead(
        fids=tuple(fid for _slot, fid in fid_slots),
        fid_slots=tuple(fid_slots),
        child_count=child_count,
        enumerated_count=enumerated_count,
        recovered_count=recovered_count,
        recovery_boundary=recovery_boundary,
        probe_failures=probe_failures,
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


def _fid_precheck_notices(
    assumption_71: str, fid_property_port: FidPropertyPort | None
) -> tuple[Mapping[str, object], ...]:
    """FID 배정 요청 갈래의 **입력 거부**가 지고 나가는 사전검사 고지.

    [round19 minor#9] round18이 `fid_range` 검증을 사전검사 **앞으로** 옮긴 것은 옳다 —
    거부된 호출에 `fid_safety`가 실려 `conflict_precheck.performed=true`로 "검사했고
    깨끗하다"고 주장한 것이 R18-A의 치명이었다. 그런데 그 이동이 `skipped_checks`
    고지까지 함께 지웠다: 바닥 위반 범위 **동시에** 콘솔 판독이 불완전한 호출에서
    조작자는 "범위를 고쳐라"만 듣고, 범위를 고친 다음 또 거부당한다. `tools.py`가
    못박은 원칙은 *콘솔이 무엇을 보여줬고 무엇을 못 봤는지를 **어느 분기에서든** 먼저
    싣는다*이므로 고지를 복원한다.

    **고지와 주장을 구분한다.** 돌려주는 것은 `skipped_checks` 한 항목 — "이 검사를
    수행하지 못했다/불완전하다"는 **부정** 진술뿐이다. `fid_safety`는 여전히 거부
    payload에 실리지 않으므로 "검사했다"는 주장이 되살아날 자리가 없다.

    **비용**: GO 분기에서는 콘솔 판독을 실제로 수행한다. 거부될 호출에 읽기를 한 번
    쓰는 값이지만, 고지의 내용이 곧 **관측된 사실**이어야 하고(수행하지 않고 "불완전
    하다"고 적으면 그것이 또 거짓 문장이다) 조작자가 다음에 무엇을 고쳐야 하는지가
    이 판독에 달려 있다. 판독은 읽기 전용이며 성공 경로가 어차피 하는 같은 판독이다.
    비-GO 분기는 콘솔을 건드리지 않는다(round16 S16-02).
    """
    if assumption_71 != ASSUMPTION_71_GO:
        return _fid_skipped_checks(assumption_71)
    existing_read = _existing_fids_from_console(fid_property_port)
    if existing_read.complete:
        # 판독이 완전하면 건너뛴 검사가 없다 — 빈 고지를 지어내지 않는다.
        return ()
    return (_fid_precheck_incomplete_check(existing_read),)


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


#: [round19 major#1] 이 코드로 거부되는 리포트에서는 1단계 **콘솔 조인이 수행되지 않았다**.
#: 세 갈래 전부 조인 산출이 존재하지 않는다: `MULTI_SYSTEM_MAPPING_ABSENT`는
#: `diff.compare`의 `if not multi_system:` 가드가 두 축 루프를 통째로 건너뛴 상태이고,
#: `COMPARISON_NOT_PERFORMED`(`diffs.performed=False`)는 `report._diffs_payload`가 세 키를
#: 아예 생략한 상태이며, `INVALID_REPORT_PAYLOAD`는 `diffs` 객체 자체가 없는 상태다.
#: 그 갈래에서 "1단계가 그 이름을 콘솔 타입 전부와 일치로 봤다"고 쓰면 **하지 않은 일을
#: 했다고 단정**하는 거짓 문장이 되고, round18판이 무조건 부착으로 정확히 그렇게 했다.
#:
#: 손으로 베낀 목록이 아니다 — `test_autopatch_types.py`의 round19 대조군이
#: `_rejection_for_report`가 낼 수 있는 코드를 AST로 재도출해 이 집합과 맞춘다. 조인
#: 미수행이 **아닌** 거부 갈래가 생기면 그 대조군이 먼저 실패해 분류를 강제한다.
_JOIN_NOT_PERFORMED_REJECTIONS: frozenset[str] = frozenset(
    {COMPARISON_NOT_PERFORMED, INVALID_REPORT_PAYLOAD, MULTI_SYSTEM_MAPPING_ABSENT}
)


@dataclass(frozen=True)
class _VacuousAxis:
    """1단계 콘솔 조인의 한 축 — 그 축이 **실제로 적용하는 필터**를 그대로 들고 있다.

    [round19 major#3] round18판은 축 하나의 필터로 두 축을 말했다. `diff.compare`에서
    `missing_in_console` 루프는 `classification != "patched"`와 좌표 미해석을 `continue`로
    거르지만, `designed_counts` 루프는 **아무 `if` 없이** 전 도면 픽스처를 센다. 그래서
    미패치 픽스처와 좌표가 `None`인 패치 픽스처는 수량 축에서 실제로 소멸하는데 round18
    고지는 0건이었다. 축마다 필터가 다르므로 축마다 코드·문장·대상 집합이 다르다.
    """

    kind: str
    axis_key: str
    requires_patched: bool
    requires_coordinates: bool
    reason: str


_VACUOUS_AXES: tuple[_VacuousAxis, ...] = (
    _VacuousAxis(
        kind=validate_autopatch("skipped_check_kind", DESIGNED_TYPE_NAME_VACUOUS),
        axis_key="missing_in_console",
        requires_patched=True,
        requires_coordinates=True,
        reason=(
            "도면 타입 이름에 영숫자가 하나도 없는 패치 픽스처가 있다 — 1단계 콘솔 부재 "
            "판정은 그런 이름을 이름이 빈 칸이 아닌 콘솔 타입 전부와 일치로 보므로 이 "
            "항목이 missing_in_console에서 소멸했을 수 있다. 2단계는 1단계 판정을 "
            "재계산하지 않으므로 되살리지 않고 고지만 한다. 콘솔 부재를 단정할 수 없다."
        ),
    ),
    _VacuousAxis(
        kind=validate_autopatch("skipped_check_kind", DESIGNED_TYPE_NAME_VACUOUS_QUANTITY_AXIS),
        axis_key="quantity_mismatch",
        requires_patched=False,
        requires_coordinates=False,
        reason=(
            "도면 타입 이름에 영숫자가 하나도 없는 도면 픽스처가 있다 — 1단계 수량 대조는 "
            "미패치와 좌표 미해석을 가리지 않고 전 도면 픽스처를 세면서 그런 이름을 이름이 "
            "빈 칸이 아닌 콘솔 타입과 일치로 보므로 이 항목이 quantity_mismatch에서 "
            "소멸했을 수 있다. 2단계는 1단계 판정을 재계산하지 않으므로 되살리지 않고 "
            "고지만 한다. 수량 차이를 단정할 수 없다."
        ),
    ),
)
_VACUOUS_JOIN_ABSENT_KIND = validate_autopatch(
    "skipped_check_kind", DESIGNED_TYPE_NAME_VACUOUS_JOIN_ABSENT
)


def _designed_coordinates(fixture: Mapping[str, object]) -> str | None:
    """`유니버스.주소` — 어느 한쪽이라도 미해석이면 `None`(없는 주소를 지어내지 않는다)."""
    universe = _optional_int(fixture.get("universe"))
    address = _optional_int(fixture.get("address"))
    if universe is None or address is None:
        return None
    return f"{universe}.{address}"


def _vacuous_axis_targets(
    fixtures: Sequence[Mapping[str, object]], axis: _VacuousAxis
) -> tuple[int, ...]:
    """그 축에서 **1단계가 삼킬 수 있는** 도면 픽스처의 인덱스 — 축의 필터를 그대로 적용한다.

    [round19 major#2] 술어는 `is_vacuous_type_name` **하나만으로는 1단계와 맞지 않는다**.
    1단계 삼킴은 `rig.fuzzy_type_equal`이 하고 그것은 `if not a or not b: return False`라
    **falsy 이름은 아무것도 삼키지 않는다**. 공허 판정만 보면 `instrument_type=""`처럼
    양쪽에 정상 등장하는 항목까지 고지되고, 빈 타입명은 도면에서 흔하므로 상시 발화하는
    거짓 양성이 된다 — 흔한 거짓 양성은 게이트를 무력화한다(`_SENTENCE_SHAPE_DEFECTS`
    주석의 같은 원칙). 그래서 **truthy와의 결합**이 1단계 술어의 대응물이다. 술어를
    공유했다는 사실만으로 정렬이 보장되지 않았다는 것이 round19의 교훈이고, 정렬 자체를
    `test_autopatch_types.py`의 round19 대조군이 1단계 실측과 맞춘다.
    """
    targets: list[int] = []
    for index, fixture in enumerate(fixtures):
        if axis.requires_patched and fixture.get("classification") != "patched":
            continue
        match_type = fixture.get("gdtf_fixture") or fixture.get("instrument_type")
        if not (match_type and is_vacuous_type_name(match_type)):
            continue
        if axis.requires_coordinates and _designed_coordinates(fixture) is None:
            continue
        targets.append(index)
    return tuple(targets)


def _stage_one_axis_output_present(report: Mapping[str, object], axis_key: str) -> bool:
    """그 축의 1단계 산출이 이 리포트에 **실제로 있는가**(round19 major#1).

    갈래를 열거해 판정하지 않는다 — 열거는 목록에 없는 새 갈래에서 반드시 새고, 이
    저장소는 이미 그것으로 한 번 샜다(`report.VwxReport.comparison_performed`의 v0.1.3
    재설계 주석). 여기서는 두 가지를 **결과로** 본다: ① 조인 미수행을 뜻하는 거부가
    걸리는가 ② 그 축의 배열이 리포트에 실려 있는가. 둘 중 하나라도 아니면 우리 층은
    그 축에 대해 1단계가 무엇을 했는지 말할 근거가 없다.
    """
    rejection = _rejection_for_report(report)
    if rejection is not None and rejection.code in _JOIN_NOT_PERFORMED_REJECTIONS:
        return False
    diffs = report.get("diffs")
    if not isinstance(diffs, Mapping):
        return False
    return isinstance(diffs.get(axis_key), (list, tuple))


def _vacuous_notice(
    *,
    kind: str,
    reason: str,
    axes: Sequence[str],
    fixtures: Sequence[Mapping[str, object]],
    targets: Sequence[int],
) -> Mapping[str, object]:
    """고지 한 건 — 좌표로만 가리키고 도면 원문 이름은 싣지 않는다(§0 2b④).

    좌표가 없는 대상은 주소 목록에 실릴 수 없으므로 **개수로 따로 싣는다**. 그러지 않으면
    `affected_count`와 주소 개수가 조용히 갈라져 조작자가 목록을 전수로 읽는다.
    """
    coordinates = tuple(
        coordinate
        for coordinate in (_designed_coordinates(fixtures[index]) for index in targets)
        if coordinate is not None
    )
    return MappingProxyType(
        {
            "kind": kind,
            "label": skipped_check_label(kind),
            "reason": reason,
            "stage_one_axes": tuple(axes),
            "affected_designed_addresses": coordinates,
            "affected_count": len(targets),
            "affected_without_coordinates": len(targets) - len(coordinates),
        }
    )


def _vacuous_designed_type_checks(
    report: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    """도면 타입 이름이 공허한 픽스처를 **축별로** 세어 미수행 판정으로 고지한다.

    이것은 1단계 동작의 **기록**이 아니라 2단계의 **고지**다. 1단계 `diff.compare`는
    `rig.fuzzy_type_equal`로 조인하는데, 정규화 후 영숫자가 남지 않는 truthy 이름은 이름이
    빈 칸이 아닌 콘솔 타입 전부와 일치한다. 그래서 그 픽스처는 `missing_in_console`에서
    사라지고, `quantity_mismatch`에서도 콘솔 수량과 대조되어 사라진다(실측: 도면 2대 중
    1대 소멸, 1단계 `skipped_checks` 0건).

    고칠 권한은 1단계에 있다(AC-AUTOPATCH-025 「1단계 공개 계약 무변경」) — 그래서 여기서
    후보를 되살리지 않는다. **되살리면 1단계 판정을 2단계가 재계산하는 것**이고 그것은 이
    SPEC이 금지한다. 대신 조작자에게 "이 판정을 믿지 말라"를 등재 어휘로 낸다.

    [round19] 나가는 문장은 **전부 참이어야 한다**. 그래서 세 가지가 갈린다.

    · 축마다 대상 집합이 다르다(major#3) — 축의 필터를 축의 코드에만 적용한다.
    · 삼킴 술어는 공허 판정과 truthy의 **결합**이다(major#2) — falsy는 삼켜지지 않는다.
    · 그 축의 1단계 산출이 없으면 소멸을 말하지 않는다(major#1) — 존재만 고지한다.
      정보를 지우지도(고지 생략) 지어내지도(소멸 단정) 않는 유일한 선택이다.
    """
    designed = report.get("designed_rig")
    if not isinstance(designed, Mapping):
        return ()
    fixtures = _mapping_rows(designed.get("fixtures"))
    notices: list[Mapping[str, object]] = []
    unjoined_axes: list[str] = []
    unjoined_targets: set[int] = set()
    for axis in _VACUOUS_AXES:
        targets = _vacuous_axis_targets(fixtures, axis)
        if not targets:
            continue
        if _stage_one_axis_output_present(report, axis.axis_key):
            notices.append(
                _vacuous_notice(
                    kind=axis.kind,
                    reason=axis.reason,
                    axes=(axis.axis_key,),
                    fixtures=fixtures,
                    targets=targets,
                )
            )
            continue
        unjoined_axes.append(axis.axis_key)
        unjoined_targets.update(targets)
    if unjoined_axes:
        notices.append(
            _vacuous_notice(
                kind=_VACUOUS_JOIN_ABSENT_KIND,
                reason=(
                    "도면 타입 이름에 영숫자가 하나도 없는 도면 픽스처가 있다 — 1단계 콘솔 "
                    "조인이 이 리포트에서 수행되지 않아 그 축의 산출이 없으므로 소멸 여부를 "
                    "말할 수 없다. 1단계가 그 이름을 무엇과 대조했는지도 이 리포트로는 알 "
                    "수 없다."
                ),
                axes=tuple(unjoined_axes),
                fixtures=fixtures,
                targets=tuple(sorted(unjoined_targets)),
            )
        )
    return tuple(notices)


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

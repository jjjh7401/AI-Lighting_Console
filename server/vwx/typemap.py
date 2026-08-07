from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

from server.vwx.rig import _norm_type, fuzzy_type_equal
from server.vwx.verdicts import (
    DMX_MODE_NOT_IN_LIBRARY,
    FIXTURE_TYPE_LIBRARY_TRUNCATED,
    FIXTURE_TYPE_LIBRARY_UNREADABLE,
    FIXTURE_TYPE_NOT_IN_LIBRARY,
    FOOTPRINT_MATCH_DESCOPE,
    TYPE_LIBRARY_ABSENT,
    TYPE_LIBRARY_INCOMPLETE,
    TYPE_NEEDS_CONFIRMATION,
    TYPE_RESOLVED,
    skipped_check_label,
    target_exclusion_label,
    type_resolution_status_label,
    validate_autopatch,
)

FIXTURE_TYPE_LIBRARY_ROOT = "Patch/FixtureTypes"
DMX_MODES_SEGMENT = "DMXModes"
DMX_CHANNELS_SEGMENT = "DMXChannels"
MODE_NAME_PROPERTY = "Name"

ASSUMPTION_72_GO = "go"
ASSUMPTION_72_NEGATIVE = "negative"
ASSUMPTION_72_INCONCLUSIVE = "inconclusive"
ASSUMPTION_72_VALUES = frozenset(
    {
        ASSUMPTION_72_GO,
        ASSUMPTION_72_NEGATIVE,
        ASSUMPTION_72_INCONCLUSIVE,
    }
)

ALIAS_CONFIRMATION_SOURCE = "type_alias"
FOOTPRINT_UNVERIFIED_COLUMN = "footprint_unverified"

FOOTPRINT_DESCOPE_REASON = (
    "점유폭 일치 확인을 수행하지 않는다 — 모드의 DMXFootprint 프로퍼티는 responder 표면에서 "
    "table 포인터로만 돌아와 직렬화되지 않고, DMXChannels 자식 수는 점유폭이 아니다"
    "(M0 실측: 자식 수 14 vs 실제 주소 stride 16). 모드 선택은 사용자 확인 단독이며 "
    "'점유폭 미검증' 열이 그 축소를 건별로 표시한다. 근본 해결(responder의 DMXFootprint "
    "직렬화)은 console/lua 변경이라 본 SPEC의 PRESERVE이며 범위 밖이다."
)
LIBRARY_TRUNCATED_REASON = (
    "FixtureType 열거가 절단되어 라이브러리 전수를 보지 못했다 — 대응 항목이 후보에 "
    "없음을 단정하지 않는다."
)
LIBRARY_UNREADABLE_REASON = (
    "FixtureType 열거를 읽지 못했다 — 대응 항목이 후보에 없음을 단정하지 않는다."
)
#: [round17 · 공허 일치 차단] 정규화 후 영숫자가 남지 않는 이름은 라이브러리 대조 기준이
#: 되지 못한다 — `_comparable_key` 참조. 그 이름으로 "일치"를 주장하면 라이브러리 전 항목이
#: 후보가 되고, 항목이 하나뿐인 라이브러리에서는 그것이 유일 후보가 되어 확정까지 간다.
VACUOUS_TYPE_KEY_REASON = (
    "타입 이름에 영숫자가 하나도 없어 라이브러리 대조 기준이 되지 못한다 — 공허한 일치로 "
    "후보를 세지 않고 사용자 확인으로 넘긴다. 조회에 쓰려던 이름은 구조화 칸에 그대로 남긴다."
)

TYPE_TABLE_COLUMNS = (
    "candidate_id",
    "designed_type",
    "console_type",
    "console_mode",
    "status",
    "confirmation_source",
    "designed_footprint",
    "console_channel_count",
    FOOTPRINT_UNVERIFIED_COLUMN,
)
TYPE_TABLE_COLUMN_LABELS = MappingProxyType(
    {
        "candidate_id": "후보 식별자",
        "designed_type": "도면 타입",
        "console_type": "콘솔 FixtureType",
        "console_mode": "콘솔 DMXMode",
        "status": "판정",
        "confirmation_source": "확인 출처",
        "designed_footprint": "도면 점유폭",
        "console_channel_count": "콘솔 DMXChannels 자식 수",
        FOOTPRINT_UNVERIFIED_COLUMN: "점유폭 미검증",
    }
)


class LibraryPort(Protocol):
    def query_state(self, path: str) -> Mapping[str, object]: ...

    def query_property(self, path: str, property_name: str) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class LibraryMode:
    index: int
    name: str
    channel_count: int | None = None


@dataclass(frozen=True)
class LibraryType:
    index: int
    name: str
    modes: tuple[LibraryMode, ...] = ()
    modes_available: bool = True
    modes_truncated: bool = False


@dataclass(frozen=True)
class FixtureTypeLibrary:
    types: tuple[LibraryType, ...] = ()
    available: bool = True
    truncated: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "path": FIXTURE_TYPE_LIBRARY_ROOT,
            "available": self.available,
            "truncated": self.truncated,
            "type_count": len(self.types),
            "types": [
                {
                    "index": entry.index,
                    "name": entry.name,
                    "mode_count": len(entry.modes),
                    "modes_available": entry.modes_available,
                    "modes_truncated": entry.modes_truncated,
                }
                for entry in self.types
            ],
        }


@dataclass(frozen=True)
class TypeRequest:
    candidate_id: str
    instrument_type: str
    gdtf_fixture: str | None = None
    mode: str | None = None
    footprint: int | None = None
    cell_count: int | None = None

    @property
    def designed_type(self) -> str:
        return self.gdtf_fixture or self.instrument_type


@dataclass(frozen=True)
class TypeHardStop:
    candidate_id: str
    code: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "code": validate_autopatch("target_exclusion_reason", self.code),
            "label": target_exclusion_label(self.code),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TypeResolution:
    request: TypeRequest
    status: str
    reason: str
    console_type: LibraryType | None = None
    console_mode: LibraryMode | None = None
    type_candidates: tuple[LibraryType, ...] = ()
    mode_candidates: tuple[LibraryMode, ...] = ()
    confirmation_source: str | None = None
    alias_key: str | None = None
    footprint_check: Mapping[str, object] = field(default_factory=dict)
    hard_stop_code: str | None = None
    incompleteness_kind: str | None = None
    #: [round17 S17-02] 사유 **문장**에 콘솔 판독 원문을 보간하지 않기 위한 구조화 칸(§0 2b④).
    #: `console_type`은 **확정된** 타입만 담으므로(별칭 없이 후보 1건이면 `None`), 사람에게
    #: 제시된 이름을 담을 자리가 없었다. 그 자리가 없으면 문장이 그 역할을 떠맡는다 —
    #: 그렇게 들어간 `'CD 5'`가 `payload["types"]`에서 CD 게이트 밖으로 새어 나갔다.
    presented_type: LibraryType | None = None
    #: 라이브러리 조회에 실제로 쓴 이름(별칭이 있으면 별칭 값, 없으면 도면 값).
    searched_type_key: str | None = None
    searched_mode_key: str | None = None

    @property
    def hard_stop(self) -> TypeHardStop | None:
        if self.hard_stop_code is None:
            return None
        return TypeHardStop(
            candidate_id=self.request.candidate_id,
            code=self.hard_stop_code,
            reason=self.reason,
        )

    def row(self) -> dict[str, object]:
        channel_count = self.footprint_check.get("console_channel_count")
        return {
            "candidate_id": self.request.candidate_id,
            "designed_type": self.request.designed_type,
            "instrument_type": self.request.instrument_type,
            "gdtf_fixture": self.request.gdtf_fixture,
            "designed_mode": self.request.mode,
            "cell_count": self.request.cell_count,
            "status": validate_autopatch("type_resolution_status", self.status),
            "status_label": type_resolution_status_label(self.status),
            "console_type": self.console_type.name if self.console_type is not None else None,
            "console_type_index": (
                self.console_type.index if self.console_type is not None else None
            ),
            "console_mode": self.console_mode.name if self.console_mode is not None else None,
            "console_mode_index": (
                self.console_mode.index if self.console_mode is not None else None
            ),
            # [round17 S17-02] 사람에게 **제시된** 콘솔 이름 — 확정 여부와 무관하다.
            # 사유 문장은 이 칸을 대신 말하지 않는다(§0 2b④ · 2c①).
            "presented_console_type": (
                self.presented_type.name if self.presented_type is not None else None
            ),
            "presented_console_type_index": (
                self.presented_type.index if self.presented_type is not None else None
            ),
            "searched_type_key": self.searched_type_key,
            "searched_mode_key": self.searched_mode_key,
            "type_candidates": [entry.name for entry in self.type_candidates],
            "mode_candidates": [entry.name for entry in self.mode_candidates],
            "confirmation_source": self.confirmation_source,
            "confirmation_required": self.status == TYPE_NEEDS_CONFIRMATION,
            "designed_footprint": self.request.footprint,
            "console_channel_count": channel_count,
            FOOTPRINT_UNVERIFIED_COLUMN: self.footprint_check.get("match") is not True,
            "footprint_check": dict(self.footprint_check),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TypeResolutionPlan:
    assumption_72: str
    library: FixtureTypeLibrary
    resolutions: tuple[TypeResolution, ...]

    @property
    def footprint_match_performed(self) -> bool:
        return self.assumption_72 == ASSUMPTION_72_GO

    def to_dict(self) -> dict[str, object]:
        rows = [resolution.row() for resolution in self.resolutions]
        return {
            "ok": True,
            "assumption_72": self.assumption_72,
            "library": self.library.to_dict(),
            "type_table": {
                "columns": list(TYPE_TABLE_COLUMNS),
                "column_labels": dict(TYPE_TABLE_COLUMN_LABELS),
                "rows": rows,
            },
            "hard_stops": [
                resolution.hard_stop.to_dict()
                for resolution in self.resolutions
                if resolution.hard_stop is not None
            ],
            "skipped_checks": self._skipped_checks(),
            "footprint_mismatches": self._footprint_mismatches(),
            "alias_reuse": self._alias_reuse(),
            FOOTPRINT_UNVERIFIED_COLUMN: not self.footprint_match_performed,
        }

    def _skipped_checks(self) -> list[dict[str, object]]:
        checks: list[dict[str, object]] = []
        if not self.footprint_match_performed:
            checks.append(
                _skipped_check(
                    FOOTPRINT_MATCH_DESCOPE,
                    FOOTPRINT_DESCOPE_REASON,
                    assumption_72=self.assumption_72,
                )
            )
        for kind, reason in (
            (FIXTURE_TYPE_LIBRARY_UNREADABLE, LIBRARY_UNREADABLE_REASON),
            (FIXTURE_TYPE_LIBRARY_TRUNCATED, LIBRARY_TRUNCATED_REASON),
        ):
            if any(resolution.incompleteness_kind == kind for resolution in self.resolutions):
                checks.append(_skipped_check(kind, reason))
        return checks

    def _footprint_mismatches(self) -> list[dict[str, object]]:
        return [
            {
                "candidate_id": resolution.request.candidate_id,
                "console_type": resolution.footprint_check.get("console_type"),
                "console_mode": resolution.footprint_check.get("console_mode"),
                "designed_footprint": resolution.request.footprint,
                "console_channel_count": resolution.footprint_check.get("console_channel_count"),
                "reason": resolution.footprint_check.get("reason"),
            }
            for resolution in self.resolutions
            if resolution.footprint_check.get("match") is False
        ]

    def _alias_reuse(self) -> list[dict[str, object]]:
        return [
            {
                "candidate_id": resolution.request.candidate_id,
                "alias_key": resolution.alias_key,
                "console_type": resolution.console_type.name,
                "console_mode": (
                    resolution.console_mode.name if resolution.console_mode is not None else None
                ),
            }
            for resolution in self.resolutions
            if resolution.confirmation_source == ALIAS_CONFIRMATION_SOURCE
            and resolution.console_type is not None
        ]


def read_fixture_type_library(
    port: LibraryPort, *, read_channel_counts: bool = False
) -> FixtureTypeLibrary:
    state = port.query_state(FIXTURE_TYPE_LIBRARY_ROOT)
    if state.get("ok") is not True:
        return FixtureTypeLibrary(available=False)
    types: list[LibraryType] = []
    for child in _mapping_rows(state.get("children")):
        index = _optional_int(child.get("i"))
        listed = _optional_string(child.get("name"))
        if index is None or not listed:
            continue
        types.append(_read_type(port, index, listed, read_channel_counts=read_channel_counts))
    return FixtureTypeLibrary(
        types=tuple(types),
        available=True,
        truncated=state.get("truncated") is True,
    )


def resolve_fixture_types(
    requests: Sequence[TypeRequest],
    *,
    library_port: LibraryPort,
    assumption_72: str = ASSUMPTION_72_NEGATIVE,
    type_aliases: Mapping[str, object] | None = None,
) -> TypeResolutionPlan:
    branch = _assumption_72_or_default(assumption_72)
    footprint_enabled = branch == ASSUMPTION_72_GO
    library = read_fixture_type_library(library_port, read_channel_counts=footprint_enabled)
    aliases = dict(type_aliases or {})
    resolutions = tuple(
        _resolve_one(request, library, aliases, footprint_enabled=footprint_enabled)
        for request in requests
    )
    return TypeResolutionPlan(assumption_72=branch, library=library, resolutions=resolutions)


def _resolve_one(
    request: TypeRequest,
    library: FixtureTypeLibrary,
    aliases: Mapping[str, object],
    *,
    footprint_enabled: bool,
) -> TypeResolution:
    alias_key, alias_type, alias_mode = _alias_for(request, aliases)
    # [round17 S17-02] 조회에 실제로 쓴 이름을 **문장이 아니라 칸으로** 들고 다닌다.
    # 별칭 값은 사람이 콘솔에서 확인해 저장한 **콘솔 쪽 이름**이라 도면 값과 같은 등급이
    # 아니다 — 사유 문장에 보간되면 `payload["types"]`가 CD 게이트 밖으로 원문을 흘린다.
    searched_type_key = alias_type or request.designed_type
    searched_mode_key = alias_mode or request.mode
    if not _type_search_keys(request, alias_type):
        # [round17 · 공허 일치 차단] 대조 기준이 될 이름이 없다. "라이브러리에 없다"고
        # 적으면 **찾아보지도 않은 것을 부재로 단정**하는 것이므로 확인으로 넘긴다.
        return TypeResolution(
            request=request,
            status=TYPE_NEEDS_CONFIRMATION,
            reason=VACUOUS_TYPE_KEY_REASON,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            footprint_check=_footprint_check(
                None, None, request, footprint_enabled=footprint_enabled
            ),
        )
    type_candidates = _type_candidates(request, library, alias_type)
    if not type_candidates:
        incomplete = _library_incompleteness(library, None)
        if incomplete is not None:
            return TypeResolution(
                request=request,
                status=TYPE_LIBRARY_INCOMPLETE,
                reason=_incompleteness_reason(incomplete),
                incompleteness_kind=incomplete,
                searched_type_key=searched_type_key,
                searched_mode_key=searched_mode_key,
                footprint_check=_footprint_check(
                    None, None, request, footprint_enabled=footprint_enabled
                ),
            )
        return TypeResolution(
            request=request,
            status=TYPE_LIBRARY_ABSENT,
            reason=(
                "콘솔 라이브러리에 도면 타입에 대응하는 FixtureType이 없다. "
                "콘솔에서 GDTF 라이브러리 임포트를 먼저 수행해야 이 항목을 "
                "패치할 수 있다 — 유사한 이름으로 대체 배정하지 않는다."
            ),
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            hard_stop_code=FIXTURE_TYPE_NOT_IN_LIBRARY,
            footprint_check=_footprint_check(
                None, None, request, footprint_enabled=footprint_enabled
            ),
        )

    sole_candidate = type_candidates[0] if len(type_candidates) == 1 else None
    confirmed_type = sole_candidate if alias_type else None
    presented_type = confirmed_type or sole_candidate

    if presented_type is not None and not presented_type.modes_available:
        return TypeResolution(
            request=request,
            status=TYPE_LIBRARY_INCOMPLETE,
            reason=LIBRARY_UNREADABLE_REASON,
            console_type=confirmed_type,
            type_candidates=type_candidates,
            confirmation_source=ALIAS_CONFIRMATION_SOURCE if confirmed_type else None,
            alias_key=alias_key if confirmed_type else None,
            presented_type=presented_type,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            incompleteness_kind=FIXTURE_TYPE_LIBRARY_UNREADABLE,
            footprint_check=_footprint_check(
                confirmed_type, None, request, footprint_enabled=footprint_enabled
            ),
        )

    mode_candidates = _mode_candidates(request, presented_type, alias_mode)
    if presented_type is not None and not mode_candidates:
        incomplete = _library_incompleteness(library, presented_type)
        if incomplete is not None:
            return TypeResolution(
                request=request,
                status=TYPE_LIBRARY_INCOMPLETE,
                reason=_incompleteness_reason(incomplete),
                console_type=confirmed_type,
                type_candidates=type_candidates,
                confirmation_source=ALIAS_CONFIRMATION_SOURCE if confirmed_type else None,
                alias_key=alias_key if confirmed_type else None,
                presented_type=presented_type,
                searched_type_key=searched_type_key,
                searched_mode_key=searched_mode_key,
                incompleteness_kind=incomplete,
                footprint_check=_footprint_check(
                    confirmed_type, None, request, footprint_enabled=footprint_enabled
                ),
            )
        return TypeResolution(
            request=request,
            status=TYPE_LIBRARY_ABSENT,
            reason=(
                "콘솔에서 확인된 FixtureType에, 도면이 요구한 DMXMode에 대응하는 모드가 없다. "
                "해당 모드를 담은 GDTF 라이브러리 임포트가 선행되어야 한다 — "
                "유사한 이름의 다른 모드로 대체 배정하지 않는다."
            ),
            console_type=confirmed_type,
            presented_type=presented_type,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            type_candidates=type_candidates,
            confirmation_source=ALIAS_CONFIRMATION_SOURCE if confirmed_type else None,
            alias_key=alias_key if confirmed_type else None,
            hard_stop_code=DMX_MODE_NOT_IN_LIBRARY,
            footprint_check=_footprint_check(
                confirmed_type, None, request, footprint_enabled=footprint_enabled
            ),
        )

    confirmed_mode = mode_candidates[0] if alias_mode and len(mode_candidates) == 1 else None
    resolved = confirmed_type is not None and confirmed_mode is not None
    footprint_check = _footprint_check(
        confirmed_type if resolved else None,
        confirmed_mode if resolved else None,
        request,
        footprint_enabled=footprint_enabled,
    )
    if resolved and footprint_check.get("match") is False:
        return TypeResolution(
            request=request,
            status=TYPE_NEEDS_CONFIRMATION,
            reason=(
                "점유폭이 도면과 다르다 — 승인 전에 모드를 다시 확인해야 한다. "
                "셀 수가 다른 모드를 고르면 주소 계획 전체가 어긋난다."
            ),
            console_type=confirmed_type,
            console_mode=confirmed_mode,
            type_candidates=type_candidates,
            mode_candidates=mode_candidates,
            confirmation_source=ALIAS_CONFIRMATION_SOURCE,
            alias_key=alias_key,
            presented_type=presented_type,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            footprint_check=footprint_check,
        )
    return TypeResolution(
        request=request,
        status=TYPE_RESOLVED if resolved else TYPE_NEEDS_CONFIRMATION,
        reason=(
            "저장된 별칭으로 타입·모드를 확정했다 — 첫 확정은 사람이 했고 그 재사용을 표에 남긴다."
            if resolved
            else "라이브러리 후보를 제시했다 — 사용자 확인 없이 확정하지 않는다."
        ),
        console_type=confirmed_type,
        console_mode=confirmed_mode,
        type_candidates=type_candidates,
        mode_candidates=mode_candidates,
        confirmation_source=ALIAS_CONFIRMATION_SOURCE if resolved else None,
        alias_key=alias_key if resolved else None,
        presented_type=presented_type,
        searched_type_key=searched_type_key,
        searched_mode_key=searched_mode_key,
        footprint_check=footprint_check,
    )


def _comparable_key(value: object) -> str | None:
    """대조 기준이 되는 이름만 통과시킨다 — **정규화 후 영숫자가 남아야** 한다.

    [round17 · 공허 일치 차단] `rig.fuzzy_type_equal`은 `rig._norm_type`으로 비영숫자를
    전부 제거한 뒤 포함관계를 본다. 그래서 `'---'`·`'--'`처럼 영숫자가 없는 이름은 정규화
    결과가 빈 문자열이 되고, 빈 문자열은 **모든** 이름에 포함되므로 그 이름은 라이브러리
    전 항목과 "일치"한다. 라이브러리 항목이 하나뿐이면 그것이 **유일 후보**가 되어 별칭과
    함께 `resolved`까지 가고, 도면이 이름조차 준 적 없는 FixtureType이 전달 Lua의
    `Patch().FixtureTypes[...]`에 박힌다(실증됨).

    막는 층은 여기다 — `rig.py`는 1단계 공개 계약(AC-AUTOPATCH-025)이라 바꾸지 않는다.
    판정 술어를 재구현하지도 않는다: 같은 `_norm_type`을 호출해 **공허함만** 본다.
    """
    if not isinstance(value, str) or not value:
        return None
    return value if _norm_type(value) else None


def _alias_for(
    request: TypeRequest, aliases: Mapping[str, object]
) -> tuple[str | None, str | None, str | None]:
    for key in (request.gdtf_fixture, request.instrument_type):
        if not key:
            continue
        entry = aliases.get(key)
        if isinstance(entry, Mapping):
            # 공허한 별칭 값은 **저장된 확인**이 아니다 — 없는 것으로 취급해 확정 경로를 막는다.
            return key, _comparable_key(entry.get("type")), _comparable_key(entry.get("mode"))
        if isinstance(entry, str) and entry:
            return key, _comparable_key(entry), None
    return None, None, None


def _type_search_keys(request: TypeRequest, alias_type: str | None) -> tuple[str, ...]:
    """라이브러리 대조에 쓸 이름 — 공허한 이름은 기준이 되지 못하므로 제외한다."""
    raw: tuple[object, ...] = (
        (alias_type,) if alias_type else (request.instrument_type, request.gdtf_fixture)
    )
    keys = (_comparable_key(value) for value in raw)
    return tuple(key for key in keys if key is not None)


def _type_candidates(
    request: TypeRequest, library: FixtureTypeLibrary, alias_type: str | None
) -> tuple[LibraryType, ...]:
    keys = _type_search_keys(request, alias_type)
    return tuple(
        entry for entry in library.types if any(fuzzy_type_equal(key, entry.name) for key in keys)
    )


def _mode_candidates(
    request: TypeRequest, console_type: LibraryType | None, alias_mode: str | None
) -> tuple[LibraryMode, ...]:
    if console_type is None:
        return ()
    # 공허한 모드 이름은 "모드 미지정"과 같다 — 전 모드를 후보로 제시하고 확정은 하지 않는다.
    wanted = _comparable_key(alias_mode) or _comparable_key(request.mode)
    if not wanted:
        return console_type.modes
    return tuple(entry for entry in console_type.modes if fuzzy_type_equal(wanted, entry.name))


def _footprint_check(
    console_type: LibraryType | None,
    console_mode: LibraryMode | None,
    request: TypeRequest,
    *,
    footprint_enabled: bool,
) -> Mapping[str, object]:
    check: dict[str, object] = {
        "assumption_72": ASSUMPTION_72_GO if footprint_enabled else ASSUMPTION_72_NEGATIVE,
        "performed": False,
        "match": None,
        "presented_before_approval": False,
        "console_type": console_type.name if console_type is not None else None,
        "console_mode": console_mode.name if console_mode is not None else None,
        "designed_footprint": request.footprint,
        "console_channel_count": console_mode.channel_count if console_mode is not None else None,
        "source_path": (
            _channel_path(console_type, console_mode)
            if console_type is not None and console_mode is not None
            else None
        ),
        "reason": FOOTPRINT_DESCOPE_REASON,
    }
    if not footprint_enabled:
        return MappingProxyType(check)
    if console_mode is None:
        check["reason"] = "타입·모드가 확정되지 않아 점유폭을 대조하지 않았다."
        return MappingProxyType(check)
    if console_mode.channel_count is None:
        check["reason"] = (
            "콘솔에서 DMXChannels 자식 수를 읽지 못해 점유폭을 대조하지 않았다 — "
            "일치로 간주하지 않는다."
        )
        return MappingProxyType(check)
    if request.footprint is None:
        check["reason"] = "도면에 DMX Footprint 값이 없어 대조할 기준이 없다."
        return MappingProxyType(check)
    matched = console_mode.channel_count == request.footprint
    check["performed"] = True
    check["match"] = matched
    check["presented_before_approval"] = not matched
    check["reason"] = (
        "도면 DMX Footprint와 콘솔 DMXChannels 자식 수가 일치한다."
        if matched
        else "도면 DMX Footprint와 콘솔 DMXChannels 자식 수가 다르다 — 승인 전에 제시한다."
    )
    return MappingProxyType(check)


def _channel_path(console_type: LibraryType, console_mode: LibraryMode) -> str:
    return (
        f"{FIXTURE_TYPE_LIBRARY_ROOT}/{console_type.index}/{DMX_MODES_SEGMENT}/"
        f"{console_mode.index}/{DMX_CHANNELS_SEGMENT}"
    )


def _library_incompleteness(
    library: FixtureTypeLibrary, console_type: LibraryType | None
) -> str | None:
    if not library.available:
        return FIXTURE_TYPE_LIBRARY_UNREADABLE
    if library.truncated:
        return FIXTURE_TYPE_LIBRARY_TRUNCATED
    if console_type is None:
        return None
    if not console_type.modes_available:
        return FIXTURE_TYPE_LIBRARY_UNREADABLE
    if console_type.modes_truncated:
        return FIXTURE_TYPE_LIBRARY_TRUNCATED
    return None


def _incompleteness_reason(kind: str) -> str:
    if kind == FIXTURE_TYPE_LIBRARY_UNREADABLE:
        return LIBRARY_UNREADABLE_REASON
    return LIBRARY_TRUNCATED_REASON


def _skipped_check(kind: str, reason: str, **extra: object) -> dict[str, object]:
    check: dict[str, object] = {
        "kind": validate_autopatch("skipped_check_kind", kind),
        "label": skipped_check_label(kind),
        "reason": reason,
    }
    check.update(extra)
    return check


def _read_type(
    port: LibraryPort, index: int, listed: str, *, read_channel_counts: bool
) -> LibraryType:
    modes_path = f"{FIXTURE_TYPE_LIBRARY_ROOT}/{index}/{DMX_MODES_SEGMENT}"
    state = port.query_state(modes_path)
    if state.get("ok") is not True:
        return LibraryType(index=index, name=listed, modes_available=False)
    modes: list[LibraryMode] = []
    for child in _mapping_rows(state.get("children")):
        mode_index = _optional_int(child.get("i"))
        if mode_index is None:
            continue
        mode_path = f"{modes_path}/{mode_index}"
        mode_name = _read_mode_name(port, mode_path) or _optional_string(child.get("name")) or ""
        channel_count = _read_channel_count(port, mode_path) if read_channel_counts else None
        modes.append(LibraryMode(index=mode_index, name=mode_name, channel_count=channel_count))
    return LibraryType(
        index=index,
        name=listed,
        modes=tuple(modes),
        modes_truncated=state.get("truncated") is True,
    )


def _read_mode_name(port: LibraryPort, mode_path: str) -> str | None:
    response = port.query_property(mode_path, MODE_NAME_PROPERTY)
    if response.get("ok") is not True:
        return None
    return _optional_string(response.get("value"))


def _read_channel_count(port: LibraryPort, mode_path: str) -> int | None:
    state = port.query_state(f"{mode_path}/{DMX_CHANNELS_SEGMENT}")
    if state.get("ok") is not True:
        return None
    node = state.get("node")
    if not isinstance(node, Mapping):
        return None
    return _optional_int(node.get("childCount"))


def _assumption_72_or_default(value: str | None) -> str:
    if value is None:
        return ASSUMPTION_72_NEGATIVE
    if value not in ASSUMPTION_72_VALUES:
        raise ValueError(
            f"assumption_72 must be one of {sorted(ASSUMPTION_72_VALUES)}, got {value!r}"
        )
    return value


def _mapping_rows(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None

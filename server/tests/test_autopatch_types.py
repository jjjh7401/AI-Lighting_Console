from __future__ import annotations

import ast
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

from server.prechk.inventory import COMPLETE, FIXTURE_ROOT, FixtureRecord, Inventory
from server.tests.test_autopatch_contract import iter_vwx_modules, vwx_module_label
from server.vwx import columns as columns_module
from server.vwx.address import ResolvedRecord, resolve_all
from server.vwx.columns import (
    ADDRESS_FAMILY_FIELDS,
    ALIAS_LOOKUP,
    ALIAS_TABLE,
    READ_FAILURE_MIN_RECORD,
    has_address_family,
    normalize_header,
    resolve_columns,
    resolve_header,
)
from server.vwx.diff import WORKSHEET_BLOCK_UNDETECTED, compare
from server.vwx.reader import (
    PATH_A,
    PATH_B,
    READ_FAILURE_BLOCK_UNDETECTED,
    READ_FAILURE_NOT_PATCH_SOURCE,
    _column_width_score,
    _process_rows,
    _uniform_width,
)
from server.vwx.report import build_vwx_report
from server.vwx.rig import (
    VW_IDENTICAL_PATCH,
    VW_PATCH_CONFLICT,
    VW_PATCH_OVERLAP,
    DesignedFixture,
    DesignedRig,
    _classify_vw_conflicts,
    _norm_type,
    build_designed_rig,
    fuzzy_type_equal,
)
from server.vwx.typemap import (
    ALIAS_CONFIRMATION_SOURCE,
    ASSUMPTION_72_GO,
    ASSUMPTION_72_INCONCLUSIVE,
    ASSUMPTION_72_NEGATIVE,
    DMX_MODES_SEGMENT,
    FIXTURE_TYPE_LIBRARY_ROOT,
    FOOTPRINT_UNVERIFIED_COLUMN,
    VACUOUS_TYPE_KEY_REASON,
    LibraryMode,
    LibraryType,
    TypeRequest,
    _alias_for,
    _mode_candidates,
    is_vacuous_type_name,
    read_fixture_type_library,
    resolve_fixture_types,
)
from server.vwx.verdicts import (
    COMPARISON_NOT_PERFORMED,
    DMX_MODE_NOT_IN_LIBRARY,
    FIXTURE_TYPE_LIBRARY_TRUNCATED,
    FIXTURE_TYPE_LIBRARY_UNREADABLE,
    FIXTURE_TYPE_NAME_UNUSABLE,
    FIXTURE_TYPE_NOT_IN_LIBRARY,
    FOOTPRINT_MATCH_DESCOPE,
    INVALID_REPORT_PAYLOAD,
    MULTI_SYSTEM_MAPPING_ABSENT,
    TYPE_LIBRARY_ABSENT,
    TYPE_LIBRARY_INCOMPLETE,
    TYPE_NAME_UNUSABLE,
    TYPE_NEEDS_CONFIRMATION,
    TYPE_RESOLUTION_STATUS,
    TYPE_RESOLVED,
    UnknownAutopatchVerdict,
    type_resolution_status_label,
    validate_autopatch,
)

TYPEMAP_SOURCE = Path("server/vwx/typemap.py").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# 콘솔 라이브러리 더블 — M0 실측 응답 형태를 그대로 흉내낸다.
#   state:Patch/FixtureTypes                        -> {class: FixtureType, i, name}
#   state:Patch/FixtureTypes/<t>/DMXModes           -> {class: DMXMode, i, name}
#   prop :Patch/FixtureTypes/<t>/DMXModes/<m>|Name  -> "Mode 1" / "2 Mode 2"
#   state:Patch/FixtureTypes/<t>/DMXModes/<m>/DMXChannels -> node.childCount
# --------------------------------------------------------------------------


class LibraryRigPort:
    def __init__(
        self,
        types,
        *,
        truncated: bool = False,
        modes_truncated: bool = False,
        library_readable: bool = True,
        modes_readable: bool = True,
        mode_names_readable: bool = True,
        channels_readable: bool = True,
    ):
        self.types = list(types)
        self.truncated = truncated
        self.modes_truncated = modes_truncated
        self.library_readable = library_readable
        self.modes_readable = modes_readable
        self.mode_names_readable = mode_names_readable
        self.channels_readable = channels_readable
        self.state_calls: list[str] = []
        self.property_calls: list[tuple[str, str]] = []

    def _modes_of(self, type_index: int):
        return self.types[type_index - 1][1]

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path == FIXTURE_TYPE_LIBRARY_ROOT:
            if not self.library_readable:
                return {"ok": False, "path": path, "error": "no reply within 3.0s"}
            children = [
                {"i": index, "name": name, "class": "FixtureType"}
                for index, (name, _modes) in enumerate(self.types, start=1)
            ]
            return {
                "ok": True,
                "path": path,
                "node": {
                    "name": "FixtureTypes",
                    "class": "FixtureTypes",
                    "childCount": len(children),
                },
                "children": children,
                "truncated": self.truncated,
            }
        modes_match = re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)/{DMX_MODES_SEGMENT}", path)
        if modes_match is not None:
            if not self.modes_readable:
                return {"ok": False, "path": path, "error": "no reply within 3.0s"}
            modes = self._modes_of(int(modes_match.group(1)))
            children = [
                {"i": index, "name": name, "class": "DMXMode"}
                for index, (name, _count) in enumerate(modes, start=1)
            ]
            return {
                "ok": True,
                "path": path,
                "node": {"name": "DMXModes", "class": "DMXModes", "childCount": len(children)},
                "children": children,
                "truncated": self.modes_truncated,
            }
        channels_match = re.fullmatch(
            rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)/{DMX_MODES_SEGMENT}/(\d+)/DMXChannels", path
        )
        if channels_match is not None:
            return self._channels(int(channels_match.group(1)), int(channels_match.group(2)), path)
        raise RuntimeError(f"unexpected state path: {path}")

    def _channels(self, type_index: int, mode_index: int, path: str) -> dict:
        if not self.channels_readable:
            return {"ok": False, "path": path, "error": "path segment not found"}
        count = self._modes_of(type_index)[mode_index - 1][1]
        return {
            "ok": True,
            "path": path,
            "node": {"name": "DMXChannels", "class": "DMXChannels", "childCount": count},
            "children": [],
            "truncated": False,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        match = re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)/{DMX_MODES_SEGMENT}/(\d+)", path)
        if match is None:
            raise RuntimeError(f"unexpected property path: {path}")
        if not self.mode_names_readable:
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}
        name = self._modes_of(int(match.group(1)))[int(match.group(2)) - 1][0]
        return {"ok": True, "path": path, "property": property_name, "value": name}


class ExplodingChannelPort(LibraryRigPort):
    """점유폭 descope 분기가 DMXChannels를 아예 읽지 않음을 구조적으로 증명한다."""

    def _channels(self, type_index: int, mode_index: int, path: str) -> dict:
        raise AssertionError(f"descoped branch must not read channel counts: {path}")


# "2 Mode 2"는 M0가 실측한 표시문자열이다. 선행 숫자 2와 열거 인덱스 3을 일부러
# 어긋나게 두어, 인덱스를 표시문자열에서 파싱하면 테스트가 깨지도록 만든다.
MEGA_POINTE_LIBRARY = [("MegaPointe", [("Mode 1", 24), ("Mode 3", 20), ("2 Mode 2", 16)])]
UNRELATED_LIBRARY = [("LEDWash 600", [("Mode 1", 12)])]


def request(
    candidate_id: str = "vwx-missing-0001",
    *,
    instrument_type: str = "Robe MegaPointe",
    gdtf_fixture: str | None = None,
    mode: str | None = None,
    footprint: int | None = None,
    cell_count: int | None = None,
) -> TypeRequest:
    return TypeRequest(
        candidate_id=candidate_id,
        instrument_type=instrument_type,
        gdtf_fixture=gdtf_fixture,
        mode=mode,
        footprint=footprint,
        cell_count=cell_count,
    )


def rows(payload: dict) -> list[dict]:
    return payload["type_table"]["rows"]


def row_by_id(payload: dict, candidate_id: str) -> dict:
    return next(row for row in rows(payload) if row["candidate_id"] == candidate_id)


def skipped_kinds(payload: dict) -> list[str]:
    return [check["kind"] for check in payload["skipped_checks"]]


def hard_stop_codes(payload: dict) -> list[str]:
    return [stop["code"] for stop in payload["hard_stops"]]


# --------------------------------------------------------------------------
# 비공허성 스캐너 — 금지 대상을 심으면 실제로 잡히는지 각 테스트가 대조한다.
# --------------------------------------------------------------------------

# [round21] 낱말 경계를 요구한다. 이전 판은 부분문자열 일치라 `probe_failures`의
# "p-**robe**"와 `correlation`의 "cor-**elation**"을 제조사 이름으로 신고했다 —
# 위양성이 나면 프로덕션이 게이트를 피해 이름을 짓게 되고, 그 순간 이 스캐너는
# 어휘를 지키는 것이 아니라 **어휘를 왜곡**한다. 실물 이름("Robe Lighting@MegaPointe",
# "Robin MMX Spot")은 전부 낱말 경계로 시작하므로 검출력은 그대로다 —
# `test_r21_library_name_scanner_keeps_real_names_and_drops_substrings`가 양방향으로 고정한다.
_LIBRARY_NAME_PATTERN = re.compile(
    r"(?i)\b(robe|robin|megapointe|ledbeam|ledwash|mmx|martin|clay ?paky|ayrton|chauvet|"
    r"elation|vari-?lite|mac ?\d|[a-z0-9][\w .-]*@[a-z])"
)

_NAME_TOKENS = frozenset(
    {
        "console_type",
        "designed_type",
        "fixture_type",
        "gdtf_fixture",
        "instrument_type",
        "match_type",
        "mode_name",
        "name",
        "type_name",
    }
)
_DISPLAY_TOKENS = _NAME_TOKENS | {"detail", "display", "label", "mode"}
_DIGIT_CLASS_PATTERN = re.compile(r"\\d|\[0-9\]|\[\[:digit:\]\]")


def library_name_constants(source: str) -> list[tuple[int, str]]:
    return [
        (node.lineno, node.value)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _LIBRARY_NAME_PATTERN.search(node.value)
    ]


def _mentions(node: ast.AST, tokens: frozenset[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and child.attr in tokens:
            return True
        if isinstance(child, ast.Name) and child.id in tokens:
            return True
        if isinstance(child, ast.Constant) and child.value in tokens:
            return True
    return False


def equality_confirmation_locations(source: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
            continue
        operands = [node.left, *node.comparators]
        if any(_mentions(operand, _NAME_TOKENS) for operand in operands):
            found.append((node.lineno, ast.dump(node)[:60]))
    return found


def display_string_parse_locations(source: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _DIGIT_CLASS_PATTERN.search(node.value):
                found.append((node.lineno, "digit-class-literal"))
            continue
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Name)
            and func.id in {"int", "float"}
            and node.args
            and _mentions(node.args[0], _DISPLAY_TOKENS)
        ):
            found.append((node.lineno, "numeric-cast-on-display-string"))
        if isinstance(func, ast.Attribute):
            if func.attr in {"split", "rsplit", "partition"} and _mentions(
                func.value, _DISPLAY_TOKENS
            ):
                found.append((node.lineno, "split-on-display-string"))
            if func.attr in {"search", "match", "fullmatch", "findall", "finditer"}:
                found.append((node.lineno, "regex-on-display-string"))
    return found


def assert_no_substitute_assignment(payload: dict) -> None:
    offenders = []
    for row in rows(payload):
        assigned = row["console_type"]
        if assigned is None:
            continue
        if row["status"] in {TYPE_LIBRARY_ABSENT, TYPE_LIBRARY_INCOMPLETE} or not fuzzy_type_equal(
            row["designed_type"], assigned
        ):
            offenders.append(row)
    assert offenders == []


class TestAutopatchTypeVerdicts:
    def test_new_type_vocabulary_codes_validate_and_carry_labels(self):
        for code in TYPE_RESOLUTION_STATUS:
            assert validate_autopatch("type_resolution_status", code) == code
            assert type_resolution_status_label(code)
        for code in (FIXTURE_TYPE_NOT_IN_LIBRARY, DMX_MODE_NOT_IN_LIBRARY):
            assert validate_autopatch("target_exclusion_reason", code) == code
        for code in (
            FOOTPRINT_MATCH_DESCOPE,
            FIXTURE_TYPE_LIBRARY_TRUNCATED,
            FIXTURE_TYPE_LIBRARY_UNREADABLE,
        ):
            assert validate_autopatch("skipped_check_kind", code) == code
        with pytest.raises(UnknownAutopatchVerdict):
            validate_autopatch("type_resolution_status", "not_real")


class TestLibraryEnumeration:
    """AC-AUTOPATCH-009 — 콘솔 라이브러리 열거."""

    def test_candidates_come_from_patch_fixture_types_enumeration_not_source_constants(self):
        port = LibraryRigPort(MEGA_POINTE_LIBRARY)

        library = read_fixture_type_library(port, read_channel_counts=True)

        assert port.state_calls[0] == FIXTURE_TYPE_LIBRARY_ROOT
        assert FIXTURE_TYPE_LIBRARY_ROOT == "Patch/FixtureTypes"
        assert [entry.name for entry in library.types] == ["MegaPointe"]
        assert [mode.name for mode in library.types[0].modes] == ["Mode 1", "Mode 3", "2 Mode 2"]
        assert library_name_constants(TYPEMAP_SOURCE) == []
        assert library_name_constants(
            'LIBRARY = "Robin MMX Spot"\nGDTF = "Robe Lighting@MegaPointe"\n'
        )

    def test_truncated_enumeration_is_reported_and_absence_is_not_asserted(self):
        truncated = resolve_fixture_types(
            [request()], library_port=LibraryRigPort(UNRELATED_LIBRARY, truncated=True)
        ).to_dict()
        complete = resolve_fixture_types(
            [request()], library_port=LibraryRigPort(UNRELATED_LIBRARY)
        ).to_dict()

        assert row_by_id(truncated, "vwx-missing-0001")["status"] == TYPE_LIBRARY_INCOMPLETE
        assert FIXTURE_TYPE_LIBRARY_TRUNCATED in skipped_kinds(truncated)
        assert hard_stop_codes(truncated) == []
        assert "단정" in row_by_id(truncated, "vwx-missing-0001")["reason"]
        assert truncated["library"]["truncated"] is True

        assert row_by_id(complete, "vwx-missing-0001")["status"] == TYPE_LIBRARY_ABSENT
        assert hard_stop_codes(complete) == [FIXTURE_TYPE_NOT_IN_LIBRARY]

    def test_mode_names_fall_back_to_the_enumeration_child_when_the_property_is_unreadable(self):
        port = LibraryRigPort(MEGA_POINTE_LIBRARY, mode_names_readable=False)

        library = read_fixture_type_library(port)

        assert [mode.name for mode in library.types[0].modes] == ["Mode 1", "Mode 3", "2 Mode 2"]
        assert port.property_calls[0] == (
            f"{FIXTURE_TYPE_LIBRARY_ROOT}/1/{DMX_MODES_SEGMENT}/1",
            "Name",
        )

    def test_unreadable_mode_enumeration_does_not_become_an_absence_claim(self):
        payload = resolve_fixture_types(
            [request("a", mode="Mode 1")],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY, modes_readable=False),
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "Mode 1"}},
        ).to_dict()

        assert row_by_id(payload, "a")["status"] == TYPE_LIBRARY_INCOMPLETE
        assert FIXTURE_TYPE_LIBRARY_UNREADABLE in skipped_kinds(payload)
        assert hard_stop_codes(payload) == []

    def test_truncated_mode_enumeration_does_not_become_an_absence_claim(self):
        payload = resolve_fixture_types(
            [request("a", mode="Mode 9")],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY, modes_truncated=True),
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "Mode 9"}},
        ).to_dict()

        assert row_by_id(payload, "a")["status"] == TYPE_LIBRARY_INCOMPLETE
        assert FIXTURE_TYPE_LIBRARY_TRUNCATED in skipped_kinds(payload)
        assert hard_stop_codes(payload) == []
        assert DMX_MODE_NOT_IN_LIBRARY not in hard_stop_codes(payload)

    def test_unreadable_library_does_not_become_an_absence_claim(self):
        payload = resolve_fixture_types(
            [request()], library_port=LibraryRigPort([], library_readable=False)
        ).to_dict()

        assert row_by_id(payload, "vwx-missing-0001")["status"] == TYPE_LIBRARY_INCOMPLETE
        assert FIXTURE_TYPE_LIBRARY_UNREADABLE in skipped_kinds(payload)
        assert hard_stop_codes(payload) == []


class TestFuzzyMatchingAndConfirmation:
    """AC-AUTOPATCH-010 — 퍼지 매칭 + 사용자 확인 + 별칭."""

    def test_observed_vw_and_gdtf_names_both_produce_candidates(self):
        payload = resolve_fixture_types(
            [
                request("vw", instrument_type="Robe MegaPointe"),
                request("gdtf", instrument_type="", gdtf_fixture="Robe Lighting@MegaPointe"),
            ],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY),
        ).to_dict()

        assert row_by_id(payload, "vw")["type_candidates"] == ["MegaPointe"]
        assert row_by_id(payload, "gdtf")["type_candidates"] == ["MegaPointe"]

    def test_string_equality_alone_never_confirms_a_mapping(self):
        payload = resolve_fixture_types(
            [request("exact", instrument_type="MegaPointe")],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY),
        ).to_dict()
        row = row_by_id(payload, "exact")

        assert row["type_candidates"] == ["MegaPointe"]
        assert row["status"] == TYPE_NEEDS_CONFIRMATION
        assert row["console_type"] is None
        assert row["confirmation_required"] is True
        assert row["confirmation_source"] is None

        assert equality_confirmation_locations(TYPEMAP_SOURCE) == []
        assert equality_confirmation_locations(
            "def bad(designed, entry):\n    return designed.instrument_type == entry.name\n"
        )
        assert equality_confirmation_locations('def bad(type_name):\n    return type_name == "X"\n')
        assert equality_confirmation_locations(
            "def bad(keys, entry):\n    return any(key == entry.name for key in keys)\n"
        )

    def test_stored_alias_is_reused_and_the_reuse_is_visible_in_the_payload(self):
        confirmed = resolve_fixture_types(
            [request("a", mode="Mode 1")],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY),
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "Mode 1"}},
        ).to_dict()
        unconfirmed = resolve_fixture_types(
            [request("a", mode="Mode 1")], library_port=LibraryRigPort(MEGA_POINTE_LIBRARY)
        ).to_dict()

        row = row_by_id(confirmed, "a")
        assert row["status"] == TYPE_RESOLVED
        assert row["console_type"] == "MegaPointe"
        assert row["console_mode"] == "Mode 1"
        assert row["confirmation_source"] == "type_alias"
        assert row["confirmation_required"] is False
        assert confirmed["alias_reuse"] == [
            {
                "candidate_id": "a",
                "alias_key": "Robe MegaPointe",
                "console_type": "MegaPointe",
                "console_mode": "Mode 1",
            }
        ]
        assert unconfirmed["alias_reuse"] == []

        assert row_by_id(unconfirmed, "a")["status"] == TYPE_NEEDS_CONFIRMATION
        assert row_by_id(unconfirmed, "a")["console_type"] is None

    def test_alias_naming_a_type_outside_the_library_is_not_trusted(self):
        payload = resolve_fixture_types(
            [request("a")],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY),
            type_aliases={"Robe MegaPointe": "Mac Aura XIP"},
        ).to_dict()

        assert row_by_id(payload, "a")["status"] == TYPE_LIBRARY_ABSENT
        assert row_by_id(payload, "a")["console_type"] is None
        assert hard_stop_codes(payload) == [FIXTURE_TYPE_NOT_IN_LIBRARY]


class TestLibraryAbsenceHardStop:
    """AC-AUTOPATCH-011 — 라이브러리 부재 하드 스톱."""

    def test_only_the_unmatched_item_is_excluded_and_the_rest_proceed(self):
        payload = resolve_fixture_types(
            [
                request("matched", instrument_type="Robe MegaPointe"),
                request("absent", instrument_type="Ayrton Perseo"),
            ],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY),
        ).to_dict()

        assert payload["ok"] is True
        assert row_by_id(payload, "matched")["status"] == TYPE_NEEDS_CONFIRMATION
        assert row_by_id(payload, "matched")["type_candidates"] == ["MegaPointe"]
        assert row_by_id(payload, "absent")["status"] == TYPE_LIBRARY_ABSENT
        assert [stop["candidate_id"] for stop in payload["hard_stops"]] == ["absent"]

    def test_hard_stop_reason_names_the_gdtf_import_prerequisite(self):
        payload = resolve_fixture_types(
            [request("absent", instrument_type="Ayrton Perseo")],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY),
        ).to_dict()
        reason = payload["hard_stops"][0]["reason"]

        assert "GDTF" in reason
        assert "임포트" in reason

    def test_no_similar_name_substitute_assignment(self):
        payload = resolve_fixture_types(
            [request("absent", instrument_type="Robe MegaPointe")],
            library_port=LibraryRigPort(UNRELATED_LIBRARY),
        ).to_dict()

        assert row_by_id(payload, "absent")["status"] == TYPE_LIBRARY_ABSENT
        assert_no_substitute_assignment(payload)

        substituted = deepcopy(payload)
        substituted["type_table"]["rows"][0]["console_type"] = "LEDWash 600"
        with pytest.raises(AssertionError):
            assert_no_substitute_assignment(substituted)

    def test_missing_mode_in_a_matched_type_is_its_own_hard_stop(self):
        payload = resolve_fixture_types(
            [request("a", mode="Mode 9")],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY),
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "Mode 9"}},
        ).to_dict()

        assert row_by_id(payload, "a")["status"] == TYPE_LIBRARY_ABSENT
        assert hard_stop_codes(payload) == [DMX_MODE_NOT_IN_LIBRARY]
        assert row_by_id(payload, "a")["console_mode"] is None


class TestFootprintBranches:
    """AC-AUTOPATCH-012 — 점유폭 일치(GO) · descope(부정) · 표시문자열 파싱 금지."""

    def test_go_branch_presents_the_footprint_mismatch_before_approval(self):
        port = LibraryRigPort(MEGA_POINTE_LIBRARY)
        payload = resolve_fixture_types(
            [request("a", mode="2 Mode 2", footprint=16)],
            library_port=port,
            assumption_72=ASSUMPTION_72_GO,
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "2 Mode 2"}},
        ).to_dict()
        row = row_by_id(payload, "a")

        channel_path = f"{FIXTURE_TYPE_LIBRARY_ROOT}/1/{DMX_MODES_SEGMENT}/3/DMXChannels"
        assert channel_path in port.state_calls
        assert row["designed_footprint"] == 16
        assert row["console_channel_count"] == 16
        assert row["footprint_check"]["performed"] is True
        assert row["footprint_check"]["match"] is True
        assert row["status"] == TYPE_RESOLVED
        assert payload["footprint_mismatches"] == []

        mismatched = resolve_fixture_types(
            [request("a", mode="Mode 1", footprint=16)],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY),
            assumption_72=ASSUMPTION_72_GO,
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "Mode 1"}},
        ).to_dict()
        mismatch_row = row_by_id(mismatched, "a")

        assert mismatch_row["footprint_check"]["match"] is False
        assert mismatch_row["footprint_check"]["presented_before_approval"] is True
        assert mismatch_row["status"] == TYPE_NEEDS_CONFIRMATION
        assert [entry["candidate_id"] for entry in mismatched["footprint_mismatches"]] == ["a"]
        assert mismatched["footprint_mismatches"][0]["designed_footprint"] == 16
        assert mismatched["footprint_mismatches"][0]["console_channel_count"] == 24

    @pytest.mark.parametrize(
        "assumption_72", [ASSUMPTION_72_NEGATIVE, ASSUMPTION_72_INCONCLUSIVE, None]
    )
    def test_descoped_branch_states_the_reduction_and_adds_the_unverified_column(
        self, assumption_72
    ):
        kwargs = {} if assumption_72 is None else {"assumption_72": assumption_72}
        payload = resolve_fixture_types(
            [request("a", mode="2 Mode 2", footprint=16)],
            library_port=ExplodingChannelPort(MEGA_POINTE_LIBRARY),
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "2 Mode 2"}},
            **kwargs,
        ).to_dict()
        row = row_by_id(payload, "a")

        assert row["status"] == TYPE_RESOLVED
        assert row["footprint_check"]["performed"] is False
        assert row["console_channel_count"] is None
        assert row[FOOTPRINT_UNVERIFIED_COLUMN] is True
        assert FOOTPRINT_UNVERIFIED_COLUMN in payload["type_table"]["columns"]
        labels = payload["type_table"]["column_labels"]
        assert labels[FOOTPRINT_UNVERIFIED_COLUMN] == "점유폭 미검증"

        assert FOOTPRINT_MATCH_DESCOPE in skipped_kinds(payload)
        descope = next(
            check for check in payload["skipped_checks"] if check["kind"] == FOOTPRINT_MATCH_DESCOPE
        )
        assert "DMXFootprint" in descope["reason"]
        assert "직렬화" in descope["reason"]
        assert "DMXChannels" in descope["reason"]
        assert "14" in descope["reason"]
        assert "16" in descope["reason"]

    def test_go_branch_reports_an_unreadable_channel_count_instead_of_claiming_a_match(self):
        payload = resolve_fixture_types(
            [request("a", mode="2 Mode 2", footprint=16)],
            library_port=LibraryRigPort(MEGA_POINTE_LIBRARY, channels_readable=False),
            assumption_72=ASSUMPTION_72_GO,
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "2 Mode 2"}},
        ).to_dict()
        row = row_by_id(payload, "a")

        assert row["console_channel_count"] is None
        assert row["footprint_check"]["performed"] is False
        assert row["footprint_check"]["match"] is None
        assert row[FOOTPRINT_UNVERIFIED_COLUMN] is True
        assert payload["footprint_mismatches"] == []

    def test_channel_count_is_never_parsed_out_of_a_display_string(self):
        port = LibraryRigPort(MEGA_POINTE_LIBRARY)
        payload = resolve_fixture_types(
            [request("a", mode="2 Mode 2", footprint=16)],
            library_port=port,
            assumption_72=ASSUMPTION_72_GO,
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "2 Mode 2"}},
        ).to_dict()
        row = row_by_id(payload, "a")

        # 표시문자열 "2 Mode 2"의 선행 숫자 2는 인덱스도 채널 수도 아니다.
        assert row["console_mode"] == "2 Mode 2"
        assert row["console_mode_index"] == 3
        assert row["console_channel_count"] == 16

        assert display_string_parse_locations(TYPEMAP_SOURCE) == []
        assert display_string_parse_locations(
            "def bad(mode):\n    return int(mode.name.split(' ')[0])\n"
        )
        assert display_string_parse_locations(
            'import re\n\n\ndef bad(name):\n    return re.search(r"(\\d+)", name)\n'
        )

    def test_multicell_eight_cell_mode_is_the_one_selected(self):
        library = [("MegaPointe", [("Standard", 24), ("8 Cell Mode", 96)])]
        payload = resolve_fixture_types(
            [request("multicell", mode="8 Cell Mode", footprint=96, cell_count=8)],
            library_port=LibraryRigPort(library),
            assumption_72=ASSUMPTION_72_GO,
            type_aliases={"Robe MegaPointe": {"type": "MegaPointe", "mode": "8 Cell Mode"}},
        ).to_dict()
        row = row_by_id(payload, "multicell")

        assert row["console_mode"] == "8 Cell Mode"
        assert row["console_mode_index"] == 2
        assert row["cell_count"] == 8
        assert row["console_channel_count"] == 96
        assert row["footprint_check"]["match"] is True
        assert row["status"] == TYPE_RESOLVED

    def test_multicell_mode_candidates_rank_the_designed_mode_first(self):
        library = [("MegaPointe", [("Standard", 24), ("8 Cell Mode", 96)])]
        payload = resolve_fixture_types(
            [request("multicell", mode="8 Cell Mode", footprint=96, cell_count=8)],
            library_port=LibraryRigPort(library),
            type_aliases={"Robe MegaPointe": "MegaPointe"},
        ).to_dict()
        row = row_by_id(payload, "multicell")

        assert row["mode_candidates"] == ["8 Cell Mode"]
        assert row["console_mode"] is None
        assert row["status"] == TYPE_NEEDS_CONFIRMATION


# --- round17 모호성 판정 · 후보 수 전수 (AmbiguityGates) ---
#
# [round17 치명 #3 = round11 N06 재개방] `X[0] if len(X) == 1 else None` 세 자리
# (`typemap._resolve_one`의 타입·모드, `apply._single_unambiguous`의 폴스루)를
# `>= 1`로 바꿔도 5,690건이 **전부 통과**했다. 원인은 하나다: 후보가 **2개**일 때
# 무엇이 나와야 하는지 단정한 테스트가 없었다. 후보 0개·1개만 검사하면
# "유일할 때만 확정한다"와 "비어 있지 않으면 첫 번째를 확정한다"가 관측적으로
# 구별되지 않는다 — 두 술어는 |후보| ∈ {0, 1}에서 값이 같다.
#
# 그래서 이 절은 후보 수를 축으로 **전수 열거**하고, 후보 2개 이상 행에는
# **열거 순서를 뒤집어도 결과가 같다**를 추가로 단정한다. 순서를 뒤집으면 첫 번째가
# 달라지므로 `>= 1` 뮤테이션은 원리적으로 이 단정을 통과할 수 없다.

#: 도면 이름과 어느 방향으로도 포함관계가 없는 라이브러리 항목 — 모든 라이브러리에
#: 하나씩 섞어 "후보 필터가 실제로 걸러낸다"를 매 행이 함께 증명한다.
_R17_ABSENT_TYPE = "LEDWash 600"
_R17_DESIGNED_TYPE = "MegaPointe"
#: 도면 이름을 **포함**하는 형제 항목들 — `fuzzy_type_equal`이 포함관계로 매칭하므로
#: 이 세 개는 하나의 도면 이름에 동시 대응한다(감사 실측 `LEDBeam 150 RGBW/CMY`와 같은 형태).
_R17_TYPE_FAMILY = ("MegaPointe RGBW", "MegaPointe CMY", "MegaPointe HP")
_R17_DESIGNED_MODE = "Mode 1"
_R17_ABSENT_MODE = "Mode 7"
_R17_MODE_FAMILY = ("Mode 1 Extended", "Mode 1 Compact", "Mode 1 Basic")


def _r17_type_library(candidate_count: int) -> list:
    """도면 이름에 정확히 ``candidate_count``개가 퍼지 일치하는 라이브러리를 만든다."""
    if candidate_count == 0:
        matching: list[str] = []
    elif candidate_count == 1:
        matching = [_R17_DESIGNED_TYPE]
    else:
        matching = list(_R17_TYPE_FAMILY[:candidate_count])
    return [(name, [(_R17_DESIGNED_MODE, 24)]) for name in matching] + [
        (_R17_ABSENT_TYPE, [(_R17_DESIGNED_MODE, 12)])
    ]


def _r17_mode_library(mode_count: int) -> list:
    """타입은 유일하게 일치하고, 요청 모드에 ``mode_count``개가 퍼지 일치하는 라이브러리."""
    if mode_count == 0:
        matching: list[str] = []
    elif mode_count == 1:
        matching = [_R17_DESIGNED_MODE]
    else:
        matching = list(_R17_MODE_FAMILY[:mode_count])
    modes = [(name, 24 + index) for index, name in enumerate(matching)]
    return [(_R17_DESIGNED_TYPE, modes + [(_R17_ABSENT_MODE, 99)])]


def _r17_aliases(alias: bool) -> dict:
    if not alias:
        return {}
    return {_R17_DESIGNED_TYPE: {"type": _R17_DESIGNED_TYPE, "mode": _R17_DESIGNED_MODE}}


def _r17_resolve(library: list, *, alias: bool) -> dict:
    return resolve_fixture_types(
        [
            request(
                "r17",
                instrument_type=_R17_DESIGNED_TYPE,
                mode=_R17_DESIGNED_MODE,
            )
        ],
        library_port=LibraryRigPort(library),
        type_aliases=_r17_aliases(alias),
    ).to_dict()


@dataclass(frozen=True)
class _CandidateRow:
    """후보 수 × 별칭 유무 → 기대 판정. `console_*`는 ``row()``가 내는 이름 문자열이다."""

    count: int
    alias: bool
    status: str
    console_type: str | None
    console_mode: str | None
    confirmation_source: str | None
    #: `alias_reuse` 목록이 지목하는 별칭 키 — 확정 행뿐 아니라 별칭으로 타입까지는
    #: 확정하고 모드에서 하드스톱한 행도 여기 실린다(관측된 형태를 그대로 고정한다).
    alias_reuse_keys: tuple[str, ...]
    hard_stops: tuple[str, ...]


#: 후보 수 축 — 0(없음) · 1(유일) · **2(핵심: 모호)** · 3(모호가 2로 한정되지 않음).
_R17_CANDIDATE_COUNTS = (0, 1, 2, 3)
_ALIAS = ALIAS_CONFIRMATION_SOURCE
_REUSED = (_R17_DESIGNED_TYPE,)

#: `typemap._resolve_one`의 **타입 후보** 전수 표.
_R17_TYPE_CANDIDATE_ROWS = (
    _CandidateRow(
        0, False, TYPE_LIBRARY_ABSENT, None, None, None, (), (FIXTURE_TYPE_NOT_IN_LIBRARY,)
    ),
    _CandidateRow(
        0, True, TYPE_LIBRARY_ABSENT, None, None, None, (), (FIXTURE_TYPE_NOT_IN_LIBRARY,)
    ),
    _CandidateRow(1, False, TYPE_NEEDS_CONFIRMATION, None, None, None, (), ()),
    _CandidateRow(
        1, True, TYPE_RESOLVED, _R17_DESIGNED_TYPE, _R17_DESIGNED_MODE, _ALIAS, _REUSED, ()
    ),
    _CandidateRow(2, False, TYPE_NEEDS_CONFIRMATION, None, None, None, (), ()),
    _CandidateRow(2, True, TYPE_NEEDS_CONFIRMATION, None, None, None, (), ()),
    _CandidateRow(3, False, TYPE_NEEDS_CONFIRMATION, None, None, None, (), ()),
    _CandidateRow(3, True, TYPE_NEEDS_CONFIRMATION, None, None, None, (), ()),
)

#: `typemap._resolve_one`의 **모드 후보** 전수 표. 타입은 항상 유일하게 일치한다.
_R17_MODE_CANDIDATE_ROWS = (
    _CandidateRow(0, False, TYPE_LIBRARY_ABSENT, None, None, None, (), (DMX_MODE_NOT_IN_LIBRARY,)),
    _CandidateRow(
        0,
        True,
        TYPE_LIBRARY_ABSENT,
        _R17_DESIGNED_TYPE,
        None,
        _ALIAS,
        _REUSED,
        (DMX_MODE_NOT_IN_LIBRARY,),
    ),
    _CandidateRow(1, False, TYPE_NEEDS_CONFIRMATION, None, None, None, (), ()),
    _CandidateRow(
        1, True, TYPE_RESOLVED, _R17_DESIGNED_TYPE, _R17_DESIGNED_MODE, _ALIAS, _REUSED, ()
    ),
    _CandidateRow(2, False, TYPE_NEEDS_CONFIRMATION, None, None, None, (), ()),
    _CandidateRow(2, True, TYPE_NEEDS_CONFIRMATION, _R17_DESIGNED_TYPE, None, None, (), ()),
    _CandidateRow(3, False, TYPE_NEEDS_CONFIRMATION, None, None, None, (), ()),
    _CandidateRow(3, True, TYPE_NEEDS_CONFIRMATION, _R17_DESIGNED_TYPE, None, None, (), ()),
)


def _r17_assert_table_shape(rows: tuple[_CandidateRow, ...]) -> None:
    """행 삭제 프로브 — 리터럴 행 수를 세지 않고 **구조**로 결손을 잡는다.

    후보 수 축은 0부터 **연속**이어야 하고 2 이상(모호)까지 닿아야 하며, 각 후보 수마다
    별칭 유무 두 갈래가 있어야 한다. 어느 행 하나를 지워도 이 세 성질 중 하나가 깨진다.
    """
    counts = {row.count for row in rows}
    assert counts == set(range(min(counts), max(counts) + 1))
    assert min(counts) == 0
    assert max(counts) >= 3
    assert {row.alias for row in rows} == {False, True}
    assert len(rows) == len(counts) * 2
    assert len({(row.count, row.alias) for row in rows}) == len(rows)
    assert tuple(sorted(counts)) == _R17_CANDIDATE_COUNTS


def _r17_assert_candidate_row(payload: dict, expected: _CandidateRow, candidates_key: str) -> dict:
    """표 한 행을 **프로덕션 산출물**에 대조한다 — 후보 수까지 관측값으로 확인한다."""
    row = row_by_id(payload, "r17")
    assert len(row[candidates_key]) == expected.count, expected
    assert row["status"] == expected.status, expected
    assert row["console_type"] == expected.console_type, expected
    assert row["console_mode"] == expected.console_mode, expected
    assert row["confirmation_source"] == expected.confirmation_source, expected
    assert row["confirmation_required"] is (expected.status == TYPE_NEEDS_CONFIRMATION), expected
    assert tuple(hard_stop_codes(payload)) == expected.hard_stops, expected
    assert (
        tuple(entry["alias_key"] for entry in payload["alias_reuse"]) == expected.alias_reuse_keys
    ), expected
    return row


class TestRound17TypeCandidateCount:
    """[round17 #3] `typemap._resolve_one`의 타입 후보 수 전수."""

    def test_type_candidate_count_table_holds_for_every_row(self):
        """[round17 #3] `typemap.py`의 `len(type_candidates) == 1`을 `>= 1`이나 `== 2`로
        바꾸면 실패한다 — 후보 2·3개 행이 `resolved`로 뒤집히거나 1개 행이 확정을 잃는다.
        """
        for expected in _R17_TYPE_CANDIDATE_ROWS:
            payload = _r17_resolve(_r17_type_library(expected.count), alias=expected.alias)
            _r17_assert_candidate_row(payload, expected, "type_candidates")

    def test_two_type_candidates_never_confirm_and_are_order_invariant(self):
        """[round17 #3] `typemap.py`의 `len(type_candidates) == 1`을 `>= 1`로 바꾸면 실패한다.

        후보가 2개면 `>= 1` 뮤턴트는 **열거 순서상 첫 번째**를 확정한다. 라이브러리 순서를
        뒤집으면 다른 것을 확정하므로 두 실행의 `console_type`이 갈린다 — 순서 의존성을
        직접 치는 단정이다(round11 N06: *모호성 판정이 순서에 의존하면 그것은 판정이 아니다*).
        """
        library = _r17_type_library(2)
        forward = row_by_id(_r17_resolve(library, alias=True), "r17")
        reversed_row = row_by_id(_r17_resolve(list(reversed(library)), alias=True), "r17")

        for row in (forward, reversed_row):
            assert row["status"] == TYPE_NEEDS_CONFIRMATION
            assert row["console_type"] is None
            assert row["console_type_index"] is None
            assert row["console_mode"] is None
            assert row["confirmation_source"] is None
            assert sorted(row["type_candidates"]) == sorted(_R17_TYPE_FAMILY[:2])

        order_insensitive = (
            "status",
            "console_type",
            "console_type_index",
            "console_mode",
            "confirmation_source",
            "confirmation_required",
            "reason",
        )
        assert {key: forward[key] for key in order_insensitive} == {
            key: reversed_row[key] for key in order_insensitive
        }
        assert sorted(forward["type_candidates"]) == sorted(reversed_row["type_candidates"])

    def test_type_candidate_table_row_deletion_is_detected(self):
        _r17_assert_table_shape(_R17_TYPE_CANDIDATE_ROWS)
        for index in range(len(_R17_TYPE_CANDIDATE_ROWS)):
            pruned = tuple(
                row for position, row in enumerate(_R17_TYPE_CANDIDATE_ROWS) if position != index
            )
            with pytest.raises(AssertionError):
                _r17_assert_table_shape(pruned)


class TestRound17ModeCandidateCount:
    """[round17 #3] `typemap._resolve_one`의 모드 후보 수 전수."""

    def test_mode_candidate_count_table_holds_for_every_row(self):
        """[round17 #3] `typemap.py`의 `len(mode_candidates) == 1`을 `>= 1`이나 `== 2`로
        바꾸면 실패한다 — 모드 후보 2·3개 행이 `resolved`로 뒤집히거나 1개 행이 확정을 잃는다.
        """
        for expected in _R17_MODE_CANDIDATE_ROWS:
            payload = _r17_resolve(_r17_mode_library(expected.count), alias=expected.alias)
            _r17_assert_candidate_row(payload, expected, "mode_candidates")

    def test_two_mode_candidates_never_confirm_and_are_order_invariant(self):
        """[round17 #3] `typemap.py`의 `len(mode_candidates) == 1`을 `>= 1`로 바꾸면 실패한다.

        모드 후보가 2개면 `>= 1` 뮤턴트는 열거 순서상 첫 모드를 확정한다 — 모드 순서를
        뒤집으면 `console_mode`가 갈리고, 셀 수가 다른 모드를 고르면 주소 계획 전체가 어긋난다.
        """
        library = _r17_mode_library(2)
        (type_name, modes) = library[0]
        forward = row_by_id(_r17_resolve([(type_name, list(modes))], alias=True), "r17")
        backward = row_by_id(_r17_resolve([(type_name, list(reversed(modes)))], alias=True), "r17")

        for row in (forward, backward):
            assert row["status"] == TYPE_NEEDS_CONFIRMATION
            assert row["console_mode"] is None
            assert row["console_mode_index"] is None
            assert row["console_channel_count"] is None
            assert sorted(row["mode_candidates"]) == sorted(_R17_MODE_FAMILY[:2])

        order_insensitive = (
            "status",
            "console_type",
            "console_mode",
            "console_mode_index",
            "confirmation_source",
            "confirmation_required",
            "reason",
        )
        assert {key: forward[key] for key in order_insensitive} == {
            key: backward[key] for key in order_insensitive
        }

    def test_mode_candidate_table_row_deletion_is_detected(self):
        _r17_assert_table_shape(_R17_MODE_CANDIDATE_ROWS)
        for index in range(len(_R17_MODE_CANDIDATE_ROWS)):
            pruned = tuple(
                row for position, row in enumerate(_R17_MODE_CANDIDATE_ROWS) if position != index
            )
            with pytest.raises(AssertionError):
                _r17_assert_table_shape(pruned)


class TestRound17ConfirmationReasonTruthfulness:
    """[round17 #3-④] `resolved`가 주장하는 근거가 **실제 경로**와 일치해야 한다."""

    def test_alias_reason_is_only_claimed_when_an_alias_actually_confirmed_it(self):
        """[round17 #3] `confirmed_type = sole_candidate if alias_type else None`에서
        `if alias_type` 조건을 지우면 실패한다 — 별칭 없이 확정한 행이 "저장된 별칭으로
        확정했다"고 **거짓 보고**하게 되고, `alias_reuse`에 근거가 없는 채로 남는다.
        """
        confirmed_rows = 0
        for rows_table, builder in (
            (_R17_TYPE_CANDIDATE_ROWS, _r17_type_library),
            (_R17_MODE_CANDIDATE_ROWS, _r17_mode_library),
        ):
            for expected in rows_table:
                payload = _r17_resolve(builder(expected.count), alias=expected.alias)
                row = row_by_id(payload, "r17")
                claims_alias = "별칭" in row["reason"]

                # ① 확정(`resolved`)과 "저장된 별칭으로 확정했다" 주장은 **같은 집합**이다 —
                #    확정의 유일한 출처가 별칭이므로 한쪽만 성립하는 행은 거짓 보고다.
                assert claims_alias is (row["status"] == TYPE_RESOLVED), expected
                if not claims_alias:
                    continue
                confirmed_rows += 1
                # ② 별칭을 주장하면 확인 출처·`alias_reuse`가 **실제로 넘긴 키**를 지목해야 한다.
                assert row["confirmation_source"] == ALIAS_CONFIRMATION_SOURCE, expected
                assert expected.alias is True, expected
                assert [entry["alias_key"] for entry in payload["alias_reuse"]] == [
                    _R17_DESIGNED_TYPE
                ], expected
                # ③ 확정을 주장하면 타입·모드 **둘 다** 실려야 한다 — 한쪽만 실린 확정은 없다.
                assert row["console_type"] == _R17_DESIGNED_TYPE, expected
                assert row["console_mode"] == _R17_DESIGNED_MODE, expected

        # 표에 확정 행이 실제로 있었음을 확인한다 — 공허하게 통과하지 않는다.
        assert confirmed_rows == 2

    def test_sole_candidate_without_an_alias_gets_a_different_reason_than_alias_confirmation(self):
        """[round17 #3] 후보 1건 확정(별칭)과 후보 1건 제시(별칭 없음)는 **다른 사유**를 낸다."""
        library = _r17_type_library(1)
        confirmed = row_by_id(_r17_resolve(library, alias=True), "r17")
        presented = row_by_id(_r17_resolve(library, alias=False), "r17")

        assert confirmed["type_candidates"] == presented["type_candidates"]
        assert confirmed["reason"] != presented["reason"]
        assert "별칭" in confirmed["reason"]
        assert "별칭" not in presented["reason"]
        assert confirmed["status"] == TYPE_RESOLVED
        assert presented["status"] == TYPE_NEEDS_CONFIRMATION


# --- round17 fuzzy_type_equal 경계 (AmbiguityGates) ---
#
# 감사 지적: "#3의 도달성을 결정하는 함수인데 그 자체의 경계는 안 쳤다." `_type_candidates`가
# 후보 2건 이상을 내는 빈도는 전적으로 `fuzzy_type_equal`의 매칭 폭에 달려 있다.


@dataclass(frozen=True)
class _FuzzyRow:
    a: str | None
    b: str | None
    expected: bool
    axis: str


_R17_FUZZY_AXIS_REFLEXIVE = "reflexive"
_R17_FUZZY_AXIS_EMPTY = "empty"
_R17_FUZZY_AXIS_CASE = "case"
_R17_FUZZY_AXIS_PUNCTUATION = "punctuation"
_R17_FUZZY_AXIS_CONTAINMENT = "containment"
_R17_FUZZY_AXIS_DISJOINT = "disjoint"
_R17_FUZZY_AXIS_NORMALISED_EMPTY = "normalised_empty"

#: 빈 값 축은 **곱집합으로 생성**한다 — 개별 행을 지울 수 없다.
_R17_EMPTY_VALUES = (None, "")
_R17_NONEMPTY_VALUE = "MegaPointe"


def _r17_empty_axis_rows() -> tuple[_FuzzyRow, ...]:
    values = _R17_EMPTY_VALUES + (_R17_NONEMPTY_VALUE,)
    return tuple(
        _FuzzyRow(left, right, False, _R17_FUZZY_AXIS_EMPTY)
        for left in values
        for right in values
        if left in _R17_EMPTY_VALUES or right in _R17_EMPTY_VALUES
    )


#: 의미 축별 경계 — **대칭 닫힘**이 요구된다(아래 게이트). 한 행을 지우면 짝이 사라져 실패한다.
_R17_FUZZY_SEMANTIC_ROWS = (
    _FuzzyRow("MegaPointe", "MegaPointe", True, _R17_FUZZY_AXIS_REFLEXIVE),
    _FuzzyRow("MegaPointe", "megapointe", True, _R17_FUZZY_AXIS_CASE),
    _FuzzyRow("megapointe", "MegaPointe", True, _R17_FUZZY_AXIS_CASE),
    _FuzzyRow("Robin LEDBeam 350", "robin-ledbeam350", True, _R17_FUZZY_AXIS_PUNCTUATION),
    _FuzzyRow("robin-ledbeam350", "Robin LEDBeam 350", True, _R17_FUZZY_AXIS_PUNCTUATION),
    _FuzzyRow("Robin LEDBeam 350", "  Robin   LEDBeam   350  ", True, _R17_FUZZY_AXIS_PUNCTUATION),
    _FuzzyRow("  Robin   LEDBeam   350  ", "Robin LEDBeam 350", True, _R17_FUZZY_AXIS_PUNCTUATION),
    # 양방향 포함 — 짧은 쪽이 왼쪽인 행과 오른쪽인 행이 **둘 다** True여야 한다.
    _FuzzyRow("MegaPointe", "MegaPointe RGBW", True, _R17_FUZZY_AXIS_CONTAINMENT),
    _FuzzyRow("MegaPointe RGBW", "MegaPointe", True, _R17_FUZZY_AXIS_CONTAINMENT),
    _FuzzyRow("LEDBeam 150", "LEDBeam 15", True, _R17_FUZZY_AXIS_CONTAINMENT),
    _FuzzyRow("LEDBeam 15", "LEDBeam 150", True, _R17_FUZZY_AXIS_CONTAINMENT),
    _FuzzyRow("Mode 1", "Mode 10", True, _R17_FUZZY_AXIS_CONTAINMENT),
    _FuzzyRow("Mode 10", "Mode 1", True, _R17_FUZZY_AXIS_CONTAINMENT),
    _FuzzyRow("Mode 1", "1 Mode 1", True, _R17_FUZZY_AXIS_CONTAINMENT),
    _FuzzyRow("1 Mode 1", "Mode 1", True, _R17_FUZZY_AXIS_CONTAINMENT),
    _FuzzyRow("MegaPointe", "Mac Aura XIP", False, _R17_FUZZY_AXIS_DISJOINT),
    _FuzzyRow("Mac Aura XIP", "MegaPointe", False, _R17_FUZZY_AXIS_DISJOINT),
    _FuzzyRow("Mode 1", "Mode 2", False, _R17_FUZZY_AXIS_DISJOINT),
    _FuzzyRow("Mode 2", "Mode 1", False, _R17_FUZZY_AXIS_DISJOINT),
    # [round17 발견 · 미봉합] 비영숫자만으로 된 이름은 정규화 후 빈 문자열이 되어
    # **모든** 이름과 포함관계로 일치한다. 아래 두 짝이 그 경계를 고정한다.
    _FuzzyRow("---", "MegaPointe", True, _R17_FUZZY_AXIS_NORMALISED_EMPTY),
    _FuzzyRow("MegaPointe", "---", True, _R17_FUZZY_AXIS_NORMALISED_EMPTY),
    _FuzzyRow("---", "+++", True, _R17_FUZZY_AXIS_NORMALISED_EMPTY),
    _FuzzyRow("+++", "---", True, _R17_FUZZY_AXIS_NORMALISED_EMPTY),
)

_R17_FUZZY_ROWS = _R17_FUZZY_SEMANTIC_ROWS + _r17_empty_axis_rows()

#: 감사 주장 재현용 — 하나의 도면 이름이 **동등 일치 없이** 전부와 포함관계인 형제 집합.
_R17_CONTAINMENT_FAMILY = (
    "LEDBeam 150 RGBW",
    "LEDBeam 150 CMY",
    "LEDBeam 150 HP",
    "LEDBeam 150 WW",
)
_R17_CONTAINMENT_DESIGNED = "LEDBeam 150"


def _r17_assert_fuzzy_table_shape(rows: tuple[_FuzzyRow, ...]) -> None:
    """행 삭제 프로브 — `fuzzy_type_equal`이 주장하는 **대칭성**으로 결손을 잡는다.

    독스트링이 "한쪽이 다른 쪽을 포함하면 같은 타입으로 본다"고 적으므로 이 함수는
    인자 순서에 무관해야 한다. 따라서 표는 스왑 닫힘이어야 하고, 어느 행을 지우면
    그 짝이 홀로 남아 닫힘이 깨진다. 자기대칭(``a == b``) 행은 별도로 존재를 요구한다.
    """
    pairs = {(row.a, row.b): row.expected for row in rows}
    assert len(pairs) == len(rows)
    for (left, right), expected in pairs.items():
        assert (right, left) in pairs, (left, right)
        assert pairs[(right, left)] == expected, (left, right)
    assert any(row.a == row.b and row.expected for row in rows)
    assert {row.expected for row in rows} == {False, True}
    axes = {row.axis for row in rows}
    for axis in (
        _R17_FUZZY_AXIS_REFLEXIVE,
        _R17_FUZZY_AXIS_EMPTY,
        _R17_FUZZY_AXIS_CASE,
        _R17_FUZZY_AXIS_PUNCTUATION,
        _R17_FUZZY_AXIS_CONTAINMENT,
        _R17_FUZZY_AXIS_DISJOINT,
        _R17_FUZZY_AXIS_NORMALISED_EMPTY,
    ):
        assert axis in axes, axis


class TestRound17FuzzyTypeEqualBoundary:
    """[round17 #3-②] `rig.fuzzy_type_equal` 자체의 경계."""

    def test_fuzzy_boundary_table_holds_for_every_row(self):
        """[round17 #3] `rig.py`의 `fuzzy_type_equal`을 다음 중 하나로 바꾸면 실패한다:
        양방향 포함 → 단방향(`return normalized_a in normalized_b`) · `ch.lower()` 제거 ·
        `ch.isalnum()` 필터 제거 · 포함관계 절 제거(동등만) · `not a or not b` → `not a`.
        """
        for row in _R17_FUZZY_ROWS:
            assert fuzzy_type_equal(row.a, row.b) is row.expected, row

    def test_fuzzy_boundary_table_row_deletion_is_detected(self):
        _r17_assert_fuzzy_table_shape(_R17_FUZZY_ROWS)
        for index in range(len(_R17_FUZZY_SEMANTIC_ROWS)):
            pruned = (
                tuple(
                    row
                    for position, row in enumerate(_R17_FUZZY_SEMANTIC_ROWS)
                    if position != index
                )
                + _r17_empty_axis_rows()
            )
            with pytest.raises(AssertionError):
                _r17_assert_fuzzy_table_shape(pruned)

    def test_containment_matching_makes_two_or_more_candidates_ordinary(self):
        """[round17 #3] 감사 주장 재현 — `_type_candidates`가 `fuzzy_type_equal`(포함관계)
        결과이므로 형제 명칭 집합에서는 후보 2건 이상이 **정상 상태**다.

        `typemap.py`의 `len(type_candidates) == 1`을 `>= 1`로 바꾸면 이 흔한 입력에서
        곧바로 잘못된 확정이 나온다 — 그래서 이 재현을 표로 고정한다.
        """
        assert _R17_CONTAINMENT_DESIGNED not in _R17_CONTAINMENT_FAMILY
        matched = [
            name
            for name in _R17_CONTAINMENT_FAMILY
            if fuzzy_type_equal(_R17_CONTAINMENT_DESIGNED, name)
        ]
        assert matched == list(_R17_CONTAINMENT_FAMILY)
        assert len(matched) >= 2

        payload = resolve_fixture_types(
            [request("family", instrument_type=_R17_CONTAINMENT_DESIGNED, mode="Mode 1")],
            library_port=LibraryRigPort(
                [(name, [("Mode 1", 16)]) for name in _R17_CONTAINMENT_FAMILY]
            ),
            type_aliases={
                _R17_CONTAINMENT_DESIGNED: {"type": _R17_CONTAINMENT_DESIGNED, "mode": "Mode 1"}
            },
        ).to_dict()
        row = row_by_id(payload, "family")

        assert sorted(row["type_candidates"]) == sorted(_R17_CONTAINMENT_FAMILY)
        assert row["status"] == TYPE_NEEDS_CONFIRMATION
        assert row["console_type"] is None
        assert row["confirmation_source"] is None

    def test_a_name_that_normalises_to_empty_is_never_counted_as_a_candidate(self):
        """[round17 · 공허 일치 차단 ⓐ] `typemap.py`의 `_comparable_key` 필터를 지우거나
        `_type_search_keys`가 다시 원문 키를 그대로 쓰면 실패한다.

        `rig.fuzzy_type_equal`은 `_norm_type`으로 비영숫자를 전부 제거한 뒤 포함관계를 보므로
        `'---'`은 정규화 후 빈 문자열이 되고 빈 문자열은 **모든** 이름에 포함된다. 즉 rig 층은
        여전히 True를 낸다(1단계 공개 계약이라 바꾸지 않는다) — 막는 층은 `typemap`이다.

        **[round18 R18-E 판정 변경]** round17판은 이 갈래를 `needs_confirmation` ·
        하드스톱 0건으로 고정했다. 그것이 결함이었다: 이 상태에는 **수행할 확인이 없다**
        (아래 `test_r18_...dead_end` 참조). 판정은 `designed_type_name_unusable` ·
        `fixture_type_name_unusable` 하드스톱이다. 하드스톱을 `None`으로 되돌리거나
        상태를 `needs_confirmation`으로 되돌리면 실패한다.
        """
        # rig 층의 동작은 그대로다 — 이 테스트가 막는 것은 typemap의 **후보 계수**다.
        assert fuzzy_type_equal("---", "MegaPointe") is True
        assert fuzzy_type_equal("---", "+++") is True

        for library in (
            [("MegaPointe", [("Mode 1", 24)])],
            [("MegaPointe", [("Mode 1", 24)]), ("LEDWash 600", [("Mode 1", 12)])],
        ):
            for aliases in (
                {},
                {"---": {"type": "---", "mode": "--"}},
                {"---": "--"},
            ):
                payload = resolve_fixture_types(
                    [request("punct", instrument_type="---", mode="Mode 1")],
                    library_port=LibraryRigPort(library),
                    type_aliases=aliases,
                ).to_dict()
                row = row_by_id(payload, "punct")

                assert row["type_candidates"] == [], (library, aliases)
                assert row["status"] == TYPE_NAME_UNUSABLE, (library, aliases)
                assert row["console_type"] is None, (library, aliases)
                assert row["console_mode"] is None, (library, aliases)
                assert row["confirmation_source"] is None, (library, aliases)
                assert row["reason"] == VACUOUS_TYPE_KEY_REASON, (library, aliases)
                # "라이브러리에 없다"고 적지 않는다 — 찾아보지도 않았으므로 부재 단정이 된다.
                assert hard_stop_codes(payload) == [FIXTURE_TYPE_NAME_UNUSABLE], (library, aliases)
                assert FIXTURE_TYPE_NOT_IN_LIBRARY not in hard_stop_codes(payload)
                # 확인 경로가 없으므로 "확인 대기"라 적지 않는다(round18 R18-E).
                assert row["confirmation_required"] is False, (library, aliases)

    def test_the_vacuous_key_gate_does_not_swallow_ordinary_names(self):
        """[round17 · 공허 일치 차단 ⓑ 비공허성] 정상 이름은 여전히 확정까지 간다 —
        `_comparable_key`가 모든 이름을 떨구도록 바꾸면(예: 항상 `None` 반환) 실패한다.
        """
        payload = _r17_resolve(_r17_type_library(1), alias=True)
        row = row_by_id(payload, "r17")

        assert row["type_candidates"] == [_R17_DESIGNED_TYPE]
        assert row["status"] == TYPE_RESOLVED
        assert row["console_type"] == _R17_DESIGNED_TYPE
        assert row["console_mode"] == _R17_DESIGNED_MODE
        assert row["reason"] != VACUOUS_TYPE_KEY_REASON

    def test_a_vacuous_mode_name_presents_every_mode_and_confirms_none(self):
        """[round17 · 공허 일치 차단] `_mode_candidates`에서 `_comparable_key`를 지우면
        `'--'` 모드가 전 모드와 "일치"해 모드가 하나뿐인 타입에서 확정까지 간다.

        공허한 모드 이름은 **모드 미지정과 같다** — 전 모드를 제시하고 확정하지 않는다.
        """
        payload = resolve_fixture_types(
            [request("vmode", instrument_type=_R17_DESIGNED_TYPE, mode="--")],
            library_port=LibraryRigPort([(_R17_DESIGNED_TYPE, [(_R17_DESIGNED_MODE, 24)])]),
            type_aliases={_R17_DESIGNED_TYPE: {"type": _R17_DESIGNED_TYPE, "mode": "--"}},
        ).to_dict()
        row = row_by_id(payload, "vmode")

        assert row["type_candidates"] == [_R17_DESIGNED_TYPE]
        assert row["mode_candidates"] == [_R17_DESIGNED_MODE]
        assert row["status"] == TYPE_NEEDS_CONFIRMATION
        assert row["console_mode"] is None
        assert hard_stop_codes(payload) == []


# --- round17 모호성 판정 자리 전수 레지스트리 (AmbiguityGates) ---
#
# [HARD 규율 1] round17의 교훈은 "게이트가 **모듈 경계에서 멈춘다**"다 — round15·16이 만든
# 게이트는 자기 도달 범위 안에서는 견고했고 치명 5건 전부가 그 밖에 있었다. 그래서 처방을
# 세 자리에 국한하지 않고 `server/vwx/` **전 모듈**에서 같은 성질의 자리(후보 집합을 하나로
# 줄이는 판정: `len(...) == 1` · `len(...) != 1` · `[0]` 인덱싱 · `next(...)`)를 AST로 전수
# 열거해 레지스트리와 **양방향 일치**를 요구한다.
#
# 스캐너는 프로덕션 소스를 읽고 레지스트리는 이 파일의 리터럴이다 — 자기 자신과 비교하는
# 항진식이 아니다. 키는 줄번호가 아니라 `(모듈, 함수 qualname, 축, ast.unparse 표현식)`이라
# 다른 에이전트의 편집으로 줄이 밀려도 유지된다.

_VWX_SOURCE_DIR = Path("server/vwx")
#: 모호성 등기부가 **대조군을 찾는 곳**. 여기 없는 파일에 대조군을 두면 등기가
#: 그것을 못 보고, 자리 하나가 게이트 없이 통과한다 — round23 R23-3이 그 형태였다
#: (「넓은 파일 범위 위의 좁은 해석」). 새 축의 대조군이 새 파일에 생기면 여기 더한다.
_R17_TEST_SOURCES = (
    Path("server/tests/test_autopatch_types.py"),
    Path("server/tests/test_autopatch_verify.py"),
    # [round24 후속] 인테이크 층의 모호성 대조군 소재지.
    Path("server/tests/test_vwx_intake.py"),
)

_R17_LEN_IS_ONE = "len_is_one"
_R17_FIRST_ELEMENT = "first_element"
_R17_NEXT_FIRST_MATCH = "next_first_match"


def _r17_enclosing_qualname(parents: dict, node: ast.AST) -> str:
    names: list[str] = []
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(current.name)
        current = parents.get(current)
    return ".".join(reversed(names)) or "<module>"


def ambiguity_candidate_sites(source: str, module: str) -> set[tuple[str, str, str, str]]:
    """후보 집합을 하나로 줄이는 자리를 전부 뽑는다 — 세 축을 전수로 본다."""
    tree = ast.parse(source)
    parents: dict = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    found: set[tuple[str, str, str, str]] = set()
    for node in ast.walk(tree):
        kind = None
        if (
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Call)
            and isinstance(node.left.func, ast.Name)
            and node.left.func.id == "len"
        ):
            for op, comparator in zip(node.ops, node.comparators, strict=True):
                if (
                    isinstance(comparator, ast.Constant)
                    and comparator.value == 1
                    and isinstance(op, (ast.Eq, ast.NotEq))
                ):
                    kind = _R17_LEN_IS_ONE
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == 0
        ):
            kind = _R17_FIRST_ELEMENT
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "next"
        ):
            kind = _R17_NEXT_FIRST_MATCH
        if kind is None:
            continue
        code = " ".join(ast.unparse(node).split())[:60].rstrip()
        found.add((module, _r17_enclosing_qualname(parents, node), kind, code))
    return found


def vwx_ambiguity_census() -> set[tuple[str, str, str, str]]:
    """`server/vwx` 전 모듈(`server/vwx/**/*.py`)의 모호성 판정 자리를 전수로 모은다."""
    census: set[tuple[str, str, str, str]] = set()
    for path in iter_vwx_modules(_VWX_SOURCE_DIR):
        source = path.read_text(encoding="utf-8")
        census |= ambiguity_candidate_sites(source, vwx_module_label(path))
    return census


def declared_test_names() -> set[str]:
    """:data:`_R17_TEST_SOURCES`가 선언한 `test_*` 함수 이름을 전부 모은다.

    그 목록이 이 레지스트리의 **대조군 소재지**다. 목록 밖에 대조군을 두면 등기가
    그것을 못 보므로, 새 축이 새 파일에 대조군을 두면 목록을 함께 넓힌다.
    """
    names: set[str] = set()
    for path in _R17_TEST_SOURCES:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                names.add(node.name)
    return names


@dataclass(frozen=True)
class _AmbiguitySite:
    module: str
    qualname: str
    kind: str
    code: str
    #: 후보 집합에서의 **선택**인가(= 순서에 의존할 수 있는가). True면 `gate`가,
    #: False면 `justification`이 필수다 — 둘 다 비면 레지스트리 게이트가 실패한다.
    order_decision: bool
    gate: str = ""
    justification: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.module, self.qualname, self.kind, self.code)


_T_TYPE_ORDER = "test_two_type_candidates_never_confirm_and_are_order_invariant"
_T_MODE_ORDER = "test_two_mode_candidates_never_confirm_and_are_order_invariant"
_T_SU_TABLE = "test_r17_single_unambiguous_candidate_count_table_holds"
_T_SU_FALLTHROUGH = "test_r17_two_fallthrough_candidates_are_order_invariant"
_T_INTRUDER = "test_r17_two_intruders_yield_an_observed_one_and_an_order_invariant_verdict"
_T_OCCUPANTS = "test_r17_two_occupants_are_never_reduced_to_the_first"
_T_VERIFY_OCCUPANTS = "test_r17_verify_with_two_occupants_is_order_invariant"
_T_CHANNELS = "test_channel_set_cardinality_decides_the_conflict_kind"
_T_WIDTH = "test_ragged_rows_are_not_uniform_and_the_width_score_is_order_invariant"
_T_SYNTHETIC = "test_synthetic_header_width_comes_from_a_uniform_block"
_T_STRUCTURAL = "test_structural_rejection_reason_is_picked_from_the_structural_set"
_T_QUANTITY = "test_quantity_mismatch_console_count_selection_is_pinned"

_J_TUPLE_COMPONENT = "튜플의 **위치 성분**을 꺼낸다 — 후보 집합에서의 선택이 아니다."
_J_POSITIONAL_TOKEN = (
    "사용자 문자열을 구분자로 쪼갠 **위치 의미** 토큰이다(유니버스=0번) — 후보 집합이 "
    "아니다. 토큰 수 게이트는 round17 #5(`address.py` 소관)."
)
_J_FIRST_BY_DEFINITION = "정의상 **최초** 항목이 답이다(NUL 바이트 최초 오프셋) — 고를 여지가 없다."
_J_SHARED_HEADER = (
    "`csv.DictReader` 산출물의 모든 레코드는 **같은 키 집합**을 가지므로 첫 레코드의 키 "
    "집합은 곧 파일 헤더다 — 후보들 중 하나를 고르는 것이 아니다."
)
_J_BLOCK_START = (
    "자동 배정이 잡은 FID 블록의 **시작 번호**다 — 사용자에게 「N번부터 M개」라고 "
    "알리는 데 쓴다. 후보 여럿에서 고르는 것이 아니라 이미 정해진 수열의 첫 값이다."
)

#: `server/vwx/` 전 모듈 모호성 판정 자리 — 스캐너 결과와 **양방향 일치**해야 한다.
_R17_AMBIGUITY_SITES = (
    # --- [round24 후속] 인테이크 — 부분 정보를 질문으로 바꾸는 층.
    # 여기 `len_is_one` 셋은 **결함이 아니라 처방**이다. 「하나로 좁혀질 때만 확정하고
    # 아니면 묻는다」가 이 층의 규율이고, 그것을 코드로 적으면 정확히 이 모양이 된다.
    # `>= 1`로 밀면 후보 여럿에서 첫 것을 집는 R22-C의 붕괴가 여기서 재현된다.
    # 확정 갈래는 전부 튜플 언팩(`(only,) = exact`)이라 `[0]` 자리가 생기지 않는다 —
    # 언팩 자체가 「정확히 하나」를 단정하기 때문이다.
    _AmbiguitySite(
        "intake.py",
        "_resolve_option",
        _R17_LEN_IS_ONE,
        "len(exact) == 1",
        True,
        gate="test_a_prefix_that_matches_two_types_is_asked",
    ),
    _AmbiguitySite(
        "intake.py",
        "_resolve_option",
        _R17_LEN_IS_ONE,
        "len(near) == 1",
        True,
        gate="test_a_prefix_that_matches_one_type_resolves",
    ),
    _AmbiguitySite(
        "intake.py",
        "assess",
        _R17_LEN_IS_ONE,
        "len(modes) == 1",
        True,
        gate="test_two_modes_are_never_taken_silently",
    ),
    _AmbiguitySite(
        "intake.py",
        "assess",
        _R17_FIRST_ELEMENT,
        "fids[0]",
        False,
        justification=_J_BLOCK_START,
    ),
    _AmbiguitySite(
        "address.py",
        "split_universe_address",
        _R17_FIRST_ELEMENT,
        "parts[0]",
        False,
        justification=_J_POSITIONAL_TOKEN,
    ),
    _AmbiguitySite(
        "apply.py",
        "_single_unambiguous",
        _R17_FIRST_ELEMENT,
        "by_index[0]",
        True,
        gate=_T_SU_TABLE,
    ),
    _AmbiguitySite(
        "apply.py",
        "_single_unambiguous",
        _R17_FIRST_ELEMENT,
        "by_name[0]",
        True,
        gate=_T_SU_TABLE,
    ),
    _AmbiguitySite(
        "apply.py",
        "_single_unambiguous",
        _R17_FIRST_ELEMENT,
        "candidates[0]",
        True,
        gate=_T_SU_FALLTHROUGH,
    ),
    _AmbiguitySite(
        "apply.py",
        "_single_unambiguous",
        _R17_LEN_IS_ONE,
        "len(by_index) != 1",
        True,
        gate=_T_SU_TABLE,
    ),
    _AmbiguitySite(
        "apply.py",
        "_single_unambiguous",
        _R17_LEN_IS_ONE,
        "len(by_name) != 1",
        True,
        gate=_T_SU_TABLE,
    ),
    _AmbiguitySite(
        "apply.py",
        "_single_unambiguous",
        _R17_LEN_IS_ONE,
        "len(candidates) == 1",
        True,
        gate=_T_SU_FALLTHROUGH,
    ),
    _AmbiguitySite(
        "apply.py",
        "screen_console_occupancy",
        _R17_NEXT_FIRST_MATCH,
        "next((fixture for fixture in console_fixtures if fixture.uni",
        True,
        gate=_T_INTRUDER,
    ),
    _AmbiguitySite(
        "apply.py",
        "screen_idempotent",
        _R17_FIRST_ELEMENT,
        "occupants[0]",
        True,
        gate=_T_OCCUPANTS,
    ),
    _AmbiguitySite(
        "apply.py",
        "verify_patch",
        _R17_FIRST_ELEMENT,
        "found[0]",
        True,
        gate=_T_VERIFY_OCCUPANTS,
    ),
    _AmbiguitySite(
        "apply.py",
        "verify_patch",
        _R17_LEN_IS_ONE,
        "len(found) == 1",
        True,
        gate=_T_VERIFY_OCCUPANTS,
    ),
    _AmbiguitySite(
        "columns.py",
        "resolve_columns",
        _R17_FIRST_ELEMENT,
        "raw_records[0]",
        False,
        justification=_J_SHARED_HEADER,
    ),
    _AmbiguitySite(
        "diff.py",
        "compare",
        _R17_NEXT_FIRST_MATCH,
        "next((ctype for ctype in console_counts if fuzzy_type_equal(",
        True,
        gate=_T_QUANTITY,
    ),
    _AmbiguitySite(
        "patchplan.py",
        "_spans_overlap",
        _R17_FIRST_ELEMENT,
        "left[0]",
        False,
        justification=_J_TUPLE_COMPONENT,
    ),
    _AmbiguitySite(
        "patchplan.py",
        "_spans_overlap",
        _R17_FIRST_ELEMENT,
        "right[0]",
        False,
        justification=_J_TUPLE_COMPONENT,
    ),
    _AmbiguitySite(
        "patchplan.py",
        "plan_addresses",
        _R17_FIRST_ELEMENT,
        "span[0]",
        False,
        justification=_J_TUPLE_COMPONENT,
    ),
    _AmbiguitySite(
        "reader.py",
        "_column_width_score",
        _R17_FIRST_ELEMENT,
        "rows[0]",
        True,
        gate=_T_WIDTH,
    ),
    _AmbiguitySite(
        "reader.py",
        "_process_rows",
        _R17_FIRST_ELEMENT,
        "rows[0]",
        True,
        gate=_T_SYNTHETIC,
    ),
    _AmbiguitySite(
        "reader.py",
        "_uniform_width",
        _R17_LEN_IS_ONE,
        "len(widths) == 1",
        True,
        gate=_T_WIDTH,
    ),
    _AmbiguitySite(
        "reader.py",
        "decode_bytes",
        _R17_NEXT_FIRST_MATCH,
        "next((index for index, byte in enumerate(data) if byte == 0)",
        False,
        justification=_J_FIRST_BY_DEFINITION,
    ),
    _AmbiguitySite(
        "report.py",
        "VwxReport._no_fixtures_reason",
        _R17_NEXT_FIRST_MATCH,
        "next((failure for failure in self.read_failures if failure.k",
        True,
        gate=_T_STRUCTURAL,
    ),
    _AmbiguitySite(
        "report.py",
        "VwxReport._no_fixtures_summary_lead",
        _R17_NEXT_FIRST_MATCH,
        "next((failure for failure in self.read_failures if failure.k",
        True,
        gate=_T_STRUCTURAL,
    ),
    _AmbiguitySite(
        "rig.py",
        "_classify_vw_conflicts",
        _R17_LEN_IS_ONE,
        "len(channels) == 1",
        True,
        gate=_T_CHANNELS,
    ),
    _AmbiguitySite(
        "rig.py",
        "_classify_vw_conflicts._sort_key",
        _R17_FIRST_ELEMENT,
        "item[0]",
        False,
        justification=_J_TUPLE_COMPONENT,
    ),
    _AmbiguitySite(
        "rig.py",
        "_compute_design_overlaps",
        _R17_FIRST_ELEMENT,
        "item[0]",
        False,
        justification=_J_TUPLE_COMPONENT,
    ),
    _AmbiguitySite(
        "typemap.py",
        "_resolve_one",
        _R17_FIRST_ELEMENT,
        "mode_candidates[0]",
        True,
        gate=_T_MODE_ORDER,
    ),
    _AmbiguitySite(
        "typemap.py",
        "_resolve_one",
        _R17_FIRST_ELEMENT,
        "type_candidates[0]",
        True,
        gate=_T_TYPE_ORDER,
    ),
    _AmbiguitySite(
        "typemap.py",
        "_resolve_one",
        _R17_LEN_IS_ONE,
        "len(mode_candidates) == 1",
        True,
        gate=_T_MODE_ORDER,
    ),
    _AmbiguitySite(
        "typemap.py",
        "_resolve_one",
        _R17_LEN_IS_ONE,
        "len(type_candidates) == 1",
        True,
        gate=_T_TYPE_ORDER,
    ),
)


def _r17_assert_census_matches(sites: tuple[_AmbiguitySite, ...]) -> None:
    """레지스트리 ↔ 프로덕션 스캔 **전단사**. 행을 지우면 스캔 쪽에 남아 실패한다."""
    declared = {site.key for site in sites}
    assert len(declared) == len(sites)
    scanned = vwx_ambiguity_census()
    assert declared == scanned, {
        "레지스트리에 없는 새 자리(등록하라)": sorted(scanned - declared),
        "프로덕션에서 사라진 자리(행을 지워라)": sorted(declared - scanned),
    }


class TestRound17AmbiguitySiteCensus:
    """[HARD 규율 1] `server/vwx/` 전 모듈 모호성 판정 자리 전수."""

    def test_registry_is_a_bijection_with_the_production_scan(self):
        _r17_assert_census_matches(_R17_AMBIGUITY_SITES)

    def test_registry_row_deletion_is_detected(self):
        for index in range(len(_R17_AMBIGUITY_SITES)):
            pruned = tuple(
                site for position, site in enumerate(_R17_AMBIGUITY_SITES) if position != index
            )
            with pytest.raises(AssertionError):
                _r17_assert_census_matches(pruned)

    def test_scanner_actually_finds_each_axis(self):
        """스캐너 비공허성 — 세 축을 심으면 실제로 잡히는지 대조한다."""
        planted = ambiguity_candidate_sites(
            "def f(xs, ys):\n"
            "    if len(xs) == 1:\n"
            "        return xs[0]\n"
            "    if len(ys) != 1:\n"
            "        return None\n"
            "    return next((y for y in ys if y), None)\n",
            "planted.py",
        )

        assert {kind for _module, _qual, kind, _code in planted} == {
            _R17_LEN_IS_ONE,
            _R17_FIRST_ELEMENT,
            _R17_NEXT_FIRST_MATCH,
        }
        assert ("planted.py", "f", _R17_LEN_IS_ONE, "len(xs) == 1") in planted
        assert ambiguity_candidate_sites("def f(xs):\n    return xs\n", "clean.py") == set()

    def test_every_order_decision_site_names_a_gate_that_exists(self):
        """ "없는 곳을 전부 메워라" — 순서 판정 자리는 **실재하는** 대조군을 지목해야 한다."""
        available = declared_test_names()
        assert _T_TYPE_ORDER in available  # 비공허성: 이 목록이 실제로 채워졌다
        assert "test_this_name_does_not_exist_anywhere" not in available

        for site in _R17_AMBIGUITY_SITES:
            if site.order_decision:
                assert site.gate, site
                assert site.gate in available, site
                assert not site.justification, site
            else:
                assert site.justification, site
                assert not site.gate, site

    def test_the_three_round17_critical_sites_are_registered_as_order_decisions(self):
        """[round17 #3] 감사가 지목한 세 자리가 순서 판정으로 등재돼 있고 실재한다."""
        critical = {
            ("typemap.py", "_resolve_one", _R17_LEN_IS_ONE, "len(type_candidates) == 1"),
            ("typemap.py", "_resolve_one", _R17_LEN_IS_ONE, "len(mode_candidates) == 1"),
            ("apply.py", "_single_unambiguous", _R17_LEN_IS_ONE, "len(candidates) == 1"),
        }
        registered = {site.key for site in _R17_AMBIGUITY_SITES if site.order_decision}

        assert critical <= registered
        assert critical <= vwx_ambiguity_census()


# --- round17 모호성 판정 대조군 · vwx 나머지 모듈 (AmbiguityGates) ---
#
# 위 레지스트리가 순서 판정으로 등재한 자리 중 `apply.py` 밖에 있는 것들의 대조군이다.
# round17의 치명 5건이 전부 "게이트가 한 번도 닿지 않은 모듈"에 있었으므로, 세 자리만
# 고치고 끝내지 않는다.


def _r17_designed_fixture(
    unit: str, instrument_type: str, universe: int, address: int, *, channel: str | None = None
) -> DesignedFixture:
    return DesignedFixture(
        unit_number=unit,
        instrument_type=instrument_type,
        mode=None,
        channel=channel,
        universe=universe,
        address=address,
        classification="patched",
        part_indices=(),
        device_type=None,
    )


def _r17_rig(*fixtures: DesignedFixture) -> DesignedRig:
    return DesignedRig(
        fixtures=tuple(fixtures),
        join_key_conflicts=(),
        vw_patch_conflicts=(),
        device_type_column_present=True,
    )


def _r17_inventory(*records: FixtureRecord) -> Inventory:
    return Inventory(
        path=FIXTURE_ROOT,
        child_count=len(records),
        enumerated_count=len(records),
        recovered_count=0,
        observed_count=len(records),
        missing_count=0,
        completeness=COMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
        fixtures=records,
    )


def _r17_console_record(slot: int, patch: str, fixture_type: str) -> FixtureRecord:
    return FixtureRecord(
        slot=slot, name=f"console {slot}", patch_raw=patch, fixture_type=fixture_type, mode=None
    )


@dataclass(frozen=True)
class _R17ReadFailure:
    """`report.VwxReport.read_failures`가 요구하는 shape(`row`·`kind`·`detail`)."""

    row: int | None
    kind: str
    detail: str


class TestRound17OtherModuleAmbiguityGates:
    """[HARD 규율 1] `typemap`·`apply` 밖의 모호성 판정 자리 대조군."""

    def test_channel_set_cardinality_decides_the_conflict_kind(self):
        """[round17 HARD 1] `rig.py`의 `len(channels) == 1`을 `>= 1`이나 `!= 1`로 바꾸면 실패한다.

        같은 (system, universe, address)에 두 픽스처가 있을 때 **채널이 서로 다르면** 충돌이고
        같으면 동일 패치다. `>= 1`은 서로 다른 두 채널을 "채널까지 동일"로 뭉개 실제 배선
        충돌을 감춘다.
        """
        table = (
            (("1", "1"), VW_IDENTICAL_PATCH),
            (("1", "2"), VW_PATCH_CONFLICT),
            (("1", "2", "3"), VW_PATCH_CONFLICT),
            ((None, "1"), VW_PATCH_OVERLAP),
            ((None, None), VW_PATCH_OVERLAP),
        )
        for channels, expected_kind in table:
            members = [
                _r17_designed_fixture(str(index), "MegaPointe", 1, 5, channel=channel)
                for index, channel in enumerate(channels, start=1)
            ]
            forward = _classify_vw_conflicts(list(members))
            backward = _classify_vw_conflicts(list(reversed(members)))

            assert [entry.kind for entry in forward] == [expected_kind], channels
            # 집합 판정이므로 열거 순서를 뒤집어도 같은 판정이어야 한다.
            assert [entry.kind for entry in backward] == [expected_kind], channels
            assert [entry.detail for entry in forward] == [entry.detail for entry in backward], (
                channels
            )

        # 비공허성 — 한 대뿐이면 애초에 충돌 항목이 나오지 않는다.
        assert (
            _classify_vw_conflicts([_r17_designed_fixture("1", "MegaPointe", 1, 5, channel="1")])
            == []
        )

    def test_ragged_rows_are_not_uniform_and_the_width_score_is_order_invariant(self):
        """[round17 HARD 1] `reader.py`의 `len(widths) == 1`을 `>= 1`로 바꾸면 실패한다.

        `>= 1`이면 들쭉날쭉한 행들이 "폭 균일"로 판정되고, `_column_width_score`가 최빈값 대신
        **첫 행의 폭**을 쓰게 된다 — 행 순서를 뒤집으면 점수가 갈린다.
        """
        ragged = [["a", "b"], ["a", "b", "c"], ["a", "b", "c"]]
        uniform = [["a", "b"], ["c", "d"]]

        assert _uniform_width(ragged) is False
        assert _uniform_width(uniform) is True
        assert _uniform_width([]) is False

        # 최빈값 폭 3 — 첫 행 폭(2)이 아니고, 행 순서에 의존하지 않는다.
        assert _column_width_score(ragged) == 3
        assert _column_width_score(list(reversed(ragged))) == 3
        assert _column_width_score(uniform) == 2
        assert _column_width_score([]) == 0

    def test_synthetic_header_width_comes_from_a_uniform_block(self):
        """[round17 HARD 1] `reader.py` `_process_rows`의 `rows[0]`은 `_uniform_width` 가드가
        있어서만 순서에 무관하다 — `len(widths) == 1`을 `>= 1`로 바꾸면 이 단정이 깨진다.
        """
        uniform = [["u1", "1", "1.5"], ["u2", "2", "1.21"]]
        forward = _process_rows(list(uniform), "utf-8", "\t")
        backward = _process_rows(list(reversed(uniform)), "utf-8", "\t")

        assert forward.path_kind == PATH_A
        assert forward.header == ("col_0", "col_1", "col_2")
        assert backward.header == forward.header
        assert len(forward.records) == 2

        # 들쭉날쭉하면 자리표시자 헤더를 만들지 않고 **블록 미탐**으로 보고한다.
        ragged = _process_rows([["u1", "1"], ["u2", "2", "1.21"]], "utf-8", "\t")
        assert ragged.path_kind == PATH_B
        assert ragged.header == ()
        assert [failure.kind for failure in ragged.read_failures] == [READ_FAILURE_BLOCK_UNDETECTED]

    def test_structural_rejection_reason_is_picked_from_the_structural_set(self):
        """[round17 HARD 1] `report.py`의 두 `next((failure ... if failure.kind in
        _STRUCTURAL_REJECTION_KINDS), None)`을 `self.read_failures[0]`으로 바꾸면 실패한다.

        구조적 거부가 여럿이면 어느 것을 지목해도 **구조적 거부 집합 안**이어야 하고, 구조적이
        아닌 판독 실패가 먼저 있어도 그것을 지목해서는 안 된다.
        """
        empty_diff = compare(_r17_rig(), _r17_inventory())
        structural_a = _R17ReadFailure(1, READ_FAILURE_NOT_PATCH_SOURCE, "구조적 거부 A")
        structural_b = _R17ReadFailure(2, WORKSHEET_BLOCK_UNDETECTED, "구조적 거부 B")
        ordinary = _R17ReadFailure(3, "address_parse_failed", "구조적 아닌 판독 실패")
        structural_details = {structural_a.detail, structural_b.detail}

        for failures in ((structural_a, structural_b), (structural_b, structural_a)):
            report = build_vwx_report(empty_diff, read_failures=failures)
            reason = report.to_dict()["diffs"]["reason"]

            assert reason in structural_details, failures
            assert report.summary_ko().startswith(f"패치 출처로 성립하지 않는다 — {reason}")
            assert ordinary.detail not in report.summary_ko()

        # 구조적이 아닌 실패가 **먼저** 와도 지목되지 않는다.
        mixed = build_vwx_report(empty_diff, read_failures=(ordinary, structural_a))
        assert mixed.to_dict()["diffs"]["reason"] == structural_a.detail

        # 비공허성 — 구조적 거부가 없으면 건수 요약으로 떨어진다.
        only_ordinary = build_vwx_report(empty_diff, read_failures=(ordinary,))
        assert (
            only_ordinary.to_dict()["diffs"]["reason"]
            == "판독 실패 1건으로 설계상 리그를 세우지 못했다"
        )

    def test_quantity_mismatch_console_count_selection_is_pinned(self):
        """[round17 결함 R17-B · 1단계 계층 소유] **현행 동작 기록이며 옳다는 판정이 아니다.**

        `diff.py`의 `next((ctype for ctype in console_counts if fuzzy_type_equal(...)), None)`은
        **열거 순서에 의존한다** — 하나의 도면 타입 이름에 콘솔 타입 이름 둘 이상이 포함관계로
        일치하면 `console_count`가 콘솔 슬롯 순서에 따라 달라지고, `quantity_mismatch` 항목이
        **보고되거나 아예 보고되지 않는다**. 수정은 1단계 SPEC(VWX 대조 계층 · AC-AUTOPATCH-025
        「1단계 공개 계약 무변경」) 소유이며 이 SPEC이 바꾸지 않는다. 이 테스트는 그 동작을
        고정해 **무의식적 변경을 막는** 역할만 한다.

        도달 결과 실측(심각도 판정 근거): 갈리는 것은 `quantity_mismatch`뿐이고
        `missing_in_console`은 `any(...)`로 판정하므로 순서에 무관하다 — 즉 이 SPEC이 소비하는
        **대상 목록(missing_in_console)은 달라지지 않고** 수량 보고만 달라진다.
        """
        designed = _r17_rig(
            _r17_designed_fixture("1", _R17_CONTAINMENT_DESIGNED, 1, 1),
            _r17_designed_fixture("2", _R17_CONTAINMENT_DESIGNED, 1, 20),
        )
        rgbw, cmy = _R17_CONTAINMENT_FAMILY[0], _R17_CONTAINMENT_FAMILY[1]
        # 도면 이름과 **무관한** 콘솔 타입을 먼저 둔다 — 퍼지 필터를 지우면 이것이 뽑혀
        # `console_count`가 2가 되고 수량 불일치가 사라진다(필터가 실제로 일을 한다는 증거).
        unrelated = "Mac Aura XIP"
        rgbw_first = _r17_inventory(
            _r17_console_record(1, "2.101", unrelated),
            _r17_console_record(2, "2.102", unrelated),
            _r17_console_record(3, "2.1", rgbw),
            _r17_console_record(4, "2.2", cmy),
            _r17_console_record(5, "2.3", cmy),
        )
        cmy_first = _r17_inventory(
            _r17_console_record(1, "2.101", unrelated),
            _r17_console_record(2, "2.102", unrelated),
            _r17_console_record(3, "2.1", cmy),
            _r17_console_record(4, "2.2", cmy),
            _r17_console_record(5, "2.3", rgbw),
        )

        first_hit = compare(designed, rgbw_first)
        second_hit = compare(designed, cmy_first)

        # 무관한 타입은 절대 뽑히지 않는다 — 뽑히면 `console_count`가 2가 되어 불일치가 사라진다.
        assert not fuzzy_type_equal(_R17_CONTAINMENT_DESIGNED, unrelated)
        # 열거 순서상 **처음 일치한** 콘솔 타입의 수량이 쓰인다 — 그래서 판정이 갈린다.
        assert [
            (entry.instrument_type, entry.designed_count, entry.console_count)
            for entry in first_hit.quantity_mismatches
        ] == [(_R17_CONTAINMENT_DESIGNED, 2, 1)]
        assert second_hit.quantity_mismatches == ()

        # 반면 대상 목록은 순서에 무관하다(`any(...)` 판정) — 심각도를 여기서 가른다.
        assert [
            (entry.unit_number, entry.universe, entry.address)
            for entry in first_hit.missing_in_console
        ] == [
            (entry.unit_number, entry.universe, entry.address)
            for entry in second_hit.missing_in_console
        ]
        assert len(first_hit.missing_in_console) == 2


# --- round18 공허 입력 전수 · 확인 경로 존재 · 컬럼 우선순위 (VacuityAndData) ---
#
# [round18 R18-E · R18-H · R18-I · R18-G · R18-J]
#
# round18 감사 지적의 공통 기제는 여덟 라운드째 같다: **어떤 규율을 적용하고 형제 표면에는
# 적용하지 않는다.** round17은 공허 일치를 `typemap`에서 닫았으나
#   · 그 닫음이 **같은 함수 안에서** 하드스톱을 강등시킨 것을 신고하지 않았고(R18-E),
#   · 공허 입력 대조군을 `'---'` 하나에만 걸었고(R18-I),
#   · 형제 축(`_mode_candidates`·별칭 값)과 형제 모듈(`columns`·`apply`)에는 걸지 않았다.
# 그래서 이 섹션은 **값 축(공허 형태) × 적용 축(타입·GDTF·모드·별칭타입·별칭모드)** 전수를
# 하나의 표로 만들고, 표에서 한 행이 사라지면 축 하나가 사라지도록 축 라벨을 **값에서 계산**
# 한다(자유 라벨이면 표가 자기충족이 된다 — round18 minor 지적).

_R18_VACUITY_CATEGORIES = (
    "none",
    "not_a_string",
    "empty",
    "blank_ascii",
    "blank_unicode",
    "control",
    "punct_43",
    "punct_45",
    "punct_46",
    "punct_47",
    "punct_95",
    "punct_mixed",
)


def _r18_vacuity_category(value: object) -> str:
    """공허 값의 축 라벨을 **값에서 계산한다** — 자유 라벨 금지(자기충족 방지).

    표의 각 행이 서로 다른 축을 차지해야 행 삭제가 축 결손으로 드러난다. 라벨을 손으로
    적으면 같은 축에 두 행을 놓을 수 있고, 그러면 한 행을 지워도 축 집합이 그대로다 —
    round18이 `_R17_CONTAINMENT_FAMILY`에서 지적한 자기충족 표가 바로 그 형태다.
    """
    if value is None:
        return "none"
    if not isinstance(value, str):
        return "not_a_string"
    if value == "":
        return "empty"
    if value.strip() == "":
        return "blank_unicode" if not value.isascii() else "blank_ascii"
    if not value.isprintable():
        return "control"
    distinct = set(value)
    if len(distinct) == 1:
        return f"punct_{ord(next(iter(distinct)))}"
    return "punct_mixed"


#: 공허 입력 전수 — `None` · 비문자열 · `''` · ASCII 공백 · 유니코드 공백 · 제어문자 ·
#: 구두점 다섯 종 · 혼합 구두점. 각 행의 축은 위 함수가 계산한다.
_R18_VACUOUS_VALUES = (
    None,
    123,
    "",
    "   ",
    "\u00a0\u2003\u3000",
    "\x00\x01\x02",
    "+++",
    "---",
    "...",
    "///",
    "__",
    "-.-",
)

#: 비공허 대조군 — 이 값들이 함께 떨어지면 게이트가 정상 입력까지 삼킨 것이다.
#: `'--MegaPointe--'`는 **구두점에 싸인 정상 이름**이라 경계 바로 안쪽이다.
_R18_SUBSTANTIVE_VALUES = ("1", "a", "MegaPointe", "--MegaPointe--", " MegaPointe ")


def _r18_assert_vacuity_table_shape(values: tuple[object, ...]) -> None:
    """행 삭제 프로브 — 축은 값에서 계산되므로 한 행을 지우면 축 하나가 사라진다."""
    axes = [_r18_vacuity_category(value) for value in values]
    assert len(axes) == len(set(axes)), axes
    assert set(axes) == set(_R18_VACUITY_CATEGORIES)
    assert len(values) == len(_R18_VACUITY_CATEGORIES)


class TestRound18VacuityAxisTable:
    """[round18 R18-I] 공허 판정의 **값 축** 전수 — round17은 `'---'` 한 형태만 걸었다."""

    def test_the_vacuity_table_covers_every_axis_and_row_deletion_is_detected(self):
        _r18_assert_vacuity_table_shape(_R18_VACUOUS_VALUES)
        for index in range(len(_R18_VACUOUS_VALUES)):
            pruned = tuple(
                value for position, value in enumerate(_R18_VACUOUS_VALUES) if position != index
            )
            with pytest.raises(AssertionError):
                _r18_assert_vacuity_table_shape(pruned)

    def test_the_empty_string_fast_path_is_redundant_with_the_normalisation_check(self):
        """[round18 · 등가 뮤턴트 기록] `_comparable_key`의 `or not value` 절을 지우는
        뮤테이션은 **SURVIVED이고 그것이 옳다** — 등가 뮤턴트다.

        근거: `rig._norm_type("")`는 `""`이고 그것은 거짓이므로, 빈 문자열은 `not value`가
        없어도 다음 줄에서 `None`이 된다. 즉 그 절은 의미 게이트가 아니라 **빠른 경로**다.
        이 테스트는 그 등가성을 코드로 남긴다 — 뮤테이션 보고서에서 "대조군 공백"과
        "등가 뮤턴트"를 구별할 수 있도록.
        """
        assert _norm_type("") == ""
        assert not _norm_type("")
        assert is_vacuous_type_name("") is True
        # 빠른 경로가 가리는 것이 없음도 확인한다 — 비문자열은 앞 절이 잡는다.
        assert is_vacuous_type_name(None) is True
        assert is_vacuous_type_name(0) is True

    def test_the_public_vacuity_predicate_agrees_with_the_table_on_every_axis(self):
        """[round18] `typemap.is_vacuous_type_name`에서 `_norm_type` 호출을 떼거나
        `not value` 검사만 남기면(즉 `'---'`을 통과시키면) 실패한다.
        """
        for value in _R18_VACUOUS_VALUES:
            assert is_vacuous_type_name(value) is True, repr(value)
        for value in _R18_SUBSTANTIVE_VALUES:
            assert is_vacuous_type_name(value) is False, repr(value)


# --------------------------------------------------------------------------
# [round18 R18-E · R18-I] 적용 축 — 공허 값이 **어느 칸에** 들어갔는지로 판정이 갈린다.
# --------------------------------------------------------------------------

_R18_AXIS_BOTH_TYPE = "both_type_names_vacuous"
_R18_AXIS_GDTF_ONLY = "gdtf_only_vacuous"
_R18_AXIS_ALIAS_TYPE = "alias_type_value_vacuous"
_R18_AXIS_MODE = "designed_mode_vacuous"
_R18_AXIS_ALIAS_MODE = "alias_mode_value_vacuous"
#: [round18 실측] 별칭 항목은 **Mapping 형태와 문자열 형태 둘 다** 받는다
#: (`_alias_for`의 `isinstance(entry, str) and entry` 갈래). 문자열 형태만 축에서
#: 빠뜨리면 그 갈래의 공허 필터 제거가 SURVIVED다 — 형제 축 미적용의 교과서적 형태.
_R18_AXIS_ALIAS_STRING = "alias_string_value_vacuous"

_R18_AXES = (
    _R18_AXIS_BOTH_TYPE,
    _R18_AXIS_GDTF_ONLY,
    _R18_AXIS_ALIAS_TYPE,
    _R18_AXIS_MODE,
    _R18_AXIS_ALIAS_MODE,
    _R18_AXIS_ALIAS_STRING,
)

_R18_LIB_TYPE = "MegaPointe"
_R18_LIB_MODE = "Mode 1"
_R18_LIBRARY = [(_R18_LIB_TYPE, [(_R18_LIB_MODE, 24)])]
_R18_GOOD_ALIAS = {"type": _R18_LIB_TYPE, "mode": _R18_LIB_MODE}


@dataclass(frozen=True)
class _R18AxisRow:
    """축 하나의 기대 판정. `confirmation_path`는 **그 확인을 수행할 입력이 존재하는가**다."""

    axis: str
    status: str
    hard_stops: tuple[str, ...]
    console_type: str | None
    console_mode: str | None
    type_candidate_count: int
    confirmation_path: bool


#: 실측 고정(round18). `both_type`은 후보 0건이므로 하드 스톱이고, 나머지 넷은 후보를
#: 제시하므로 확인 대기다 — 그 확인을 수행할 입력이 실제로 존재함을 아래에서 실행해 본다.
_R18_AXIS_ROWS = (
    _R18AxisRow(
        _R18_AXIS_BOTH_TYPE,
        TYPE_NAME_UNUSABLE,
        (FIXTURE_TYPE_NAME_UNUSABLE,),
        None,
        None,
        0,
        # truthy 공허 이름은 별칭 키가 되므로 탈출구가 있다(falsy는 없다 — 별도 게이트).
        True,
    ),
    _R18AxisRow(_R18_AXIS_GDTF_ONLY, TYPE_NEEDS_CONFIRMATION, (), None, None, 1, True),
    _R18AxisRow(_R18_AXIS_ALIAS_TYPE, TYPE_NEEDS_CONFIRMATION, (), None, _R18_LIB_MODE, 1, True),
    _R18AxisRow(_R18_AXIS_MODE, TYPE_RESOLVED, (), _R18_LIB_TYPE, _R18_LIB_MODE, 1, False),
    _R18AxisRow(_R18_AXIS_ALIAS_MODE, TYPE_NEEDS_CONFIRMATION, (), _R18_LIB_TYPE, None, 1, True),
    _R18AxisRow(_R18_AXIS_ALIAS_STRING, TYPE_NEEDS_CONFIRMATION, (), None, None, 1, True),
)


def _r18_axis_request(axis: str, value: object) -> tuple[TypeRequest, dict]:
    """축 하나에 공허 값을 심은 (요청, 별칭). 다른 칸은 전부 정상 값이다."""
    if axis == _R18_AXIS_BOTH_TYPE:
        return (
            TypeRequest(
                candidate_id="r18",
                instrument_type=value,
                gdtf_fixture=value,
                mode=_R18_LIB_MODE,
            ),
            {},
        )
    if axis == _R18_AXIS_GDTF_ONLY:
        return (
            TypeRequest(
                candidate_id="r18",
                instrument_type=_R18_LIB_TYPE,
                gdtf_fixture=value,
                mode=_R18_LIB_MODE,
            ),
            {},
        )
    base = TypeRequest(candidate_id="r18", instrument_type=_R18_LIB_TYPE, mode=_R18_LIB_MODE)
    if axis == _R18_AXIS_ALIAS_TYPE:
        return base, {_R18_LIB_TYPE: {"type": value, "mode": _R18_LIB_MODE}}
    if axis == _R18_AXIS_MODE:
        return (
            TypeRequest(candidate_id="r18", instrument_type=_R18_LIB_TYPE, mode=value),
            {_R18_LIB_TYPE: dict(_R18_GOOD_ALIAS)},
        )
    if axis == _R18_AXIS_ALIAS_MODE:
        return base, {_R18_LIB_TYPE: {"type": _R18_LIB_TYPE, "mode": value}}
    if axis == _R18_AXIS_ALIAS_STRING:
        # 문자열 형태 별칭 — 값 하나가 곧 콘솔 타입 이름이다(모드는 담기지 않는다).
        return base, {_R18_LIB_TYPE: value}
    raise AssertionError(f"unknown axis: {axis}")


def _r18_resolve(request: TypeRequest, aliases: dict) -> dict:
    return resolve_fixture_types(
        [request], library_port=LibraryRigPort(_R18_LIBRARY), type_aliases=aliases
    ).to_dict()


def _r18_assert_axis_table_shape(rows: tuple[_R18AxisRow, ...]) -> None:
    """행 삭제 프로브 — 축 하나에 행 하나이므로 삭제는 축 결손으로 드러난다."""
    axes = tuple(row.axis for row in rows)
    assert len(axes) == len(set(axes)), axes
    assert set(axes) == set(_R18_AXES)
    assert len(rows) == len(_R18_AXES)
    # 표가 한 판정으로 뭉개지면(전부 하드스톱 또는 전부 확인 대기) 축 구분이 무의미하다.
    assert len({row.status for row in rows}) >= 3, axes
    assert {row.confirmation_path for row in rows} == {False, True}


class TestRound18VacuityApplicationAxes:
    """[round18 R18-E · R18-I] 공허 값이 들어간 **칸**마다 판정이 다르다 — 전수."""

    def test_the_axis_table_shape_detects_row_deletion(self):
        _r18_assert_axis_table_shape(_R18_AXIS_ROWS)
        for index in range(len(_R18_AXIS_ROWS)):
            pruned = tuple(row for position, row in enumerate(_R18_AXIS_ROWS) if position != index)
            with pytest.raises(AssertionError):
                _r18_assert_axis_table_shape(pruned)

    def test_every_axis_holds_for_every_vacuous_form(self):
        """[round18 R18-E · R18-I] 다음 뮤테이션에서 실패한다:

        · `typemap.py` 공허 갈래의 `hard_stop_code=FIXTURE_TYPE_NAME_UNUSABLE`를 `None`으로 —
          `both_type` 축이 하드스톱을 잃는다(R18-E 강등 복귀).
        · 같은 갈래의 `status=TYPE_NAME_UNUSABLE`를 `TYPE_NEEDS_CONFIRMATION`으로 —
          같은 축의 상태와 `confirmation_required`가 뒤집힌다.
        · `_comparable_key`의 `_norm_type(value)` 검사를 지워 `not value`만 남기면 —
          `'---'`·`'   '`·제어문자·유니코드 공백 행에서 대조 기준이 되살아나 판정이 갈린다.
        · `_mode_candidates`에서 `_comparable_key`를 지우면 — `designed_mode` 축의
          공허 모드가 전 모드 제시 대신 공허 일치로 좁혀진다.
        · `_alias_for`에서 `_comparable_key`를 지우면 — `alias_type`/`alias_mode` 축이
          공허한 별칭 값으로 `resolved`까지 간다.
        """
        for row in _R18_AXIS_ROWS:
            for value in _R18_VACUOUS_VALUES:
                request, aliases = _r18_axis_request(row.axis, value)
                payload = _r18_resolve(request, aliases)
                observed = row_by_id(payload, "r18")
                context = (row.axis, repr(value))
                assert observed["status"] == row.status, context
                assert tuple(hard_stop_codes(payload)) == row.hard_stops, context
                assert observed["console_type"] == row.console_type, context
                assert observed["console_mode"] == row.console_mode, context
                assert len(observed["type_candidates"]) == row.type_candidate_count, context
                assert observed["confirmation_required"] is (
                    row.status == TYPE_NEEDS_CONFIRMATION
                ), context

    def test_no_vacuous_form_on_any_axis_ever_reaches_a_substitute_assignment(self):
        """[round18 R18-E] 공허 값이 어느 칸에 들어가도 도면이 준 적 없는 콘솔 타입이
        확정되지 않는다 — `assert_no_substitute_assignment`로 전 축 재확인.
        """
        for row in _R18_AXIS_ROWS:
            for value in _R18_VACUOUS_VALUES:
                request, aliases = _r18_axis_request(row.axis, value)
                assert_no_substitute_assignment(_r18_resolve(request, aliases))

    def test_substantive_names_are_not_swallowed_on_any_axis(self):
        """[round18 R18-I 비공허성] 정상 이름은 어느 축에서도 공허 판정에 걸리지 않는다.

        `_comparable_key`가 모든 값을 떨구도록 바꾸면(항상 `None` 반환) 실패한다 —
        `' MegaPointe '`·`'--MegaPointe--'`처럼 **구두점·공백에 싸인 정상 이름**은
        경계 바로 안쪽이라 과잉 차단을 여기서 잡는다.
        """
        for name in _R18_SUBSTANTIVE_VALUES:
            payload = _r18_resolve(
                TypeRequest(candidate_id="r18", instrument_type=name, mode=_R18_LIB_MODE),
                {name: dict(_R18_GOOD_ALIAS)},
            )
            row = row_by_id(payload, "r18")
            assert row["status"] != TYPE_NAME_UNUSABLE, name
            assert hard_stop_codes(payload) == [], name
            assert row["reason"] != VACUOUS_TYPE_KEY_REASON, name


# --------------------------------------------------------------------------
# [round18 R18-E ②] "확인 경로가 존재하는가"를 게이트로
#
# 사유가 *사용자 확인으로 넘긴다*고 말하는 **모든 갈래**에 대해, 그 확인을 수행할 입력이
# 실제로 존재하는지 **실행해서** 단정한다. 존재하지 않으면 그 갈래는 확인 대기라 불릴 자격이
# 없다 — round18 R18-E가 정확히 그 형태였다.
# --------------------------------------------------------------------------

#: 축 -> 그 축의 판정을 `resolved`로 바꾸는 입력의 설명.
_R18_CONFIRMATION_INPUTS = {
    _R18_AXIS_BOTH_TYPE: "truthy 공허 이름을 키로 한 별칭에 실재 콘솔 이름을 저장",
    _R18_AXIS_GDTF_ONLY: "instrument_type을 키로 한 별칭 저장",
    _R18_AXIS_ALIAS_TYPE: "별칭 type 값을 실재 콘솔 이름으로 교체",
    _R18_AXIS_ALIAS_MODE: "별칭 mode 값을 실재 콘솔 모드로 교체",
    _R18_AXIS_ALIAS_STRING: "문자열 별칭을 Mapping 형태로 바꿔 mode까지 저장",
}


def _r18_confirmed(axis: str, value: object) -> dict:
    """그 축에서 **확인을 수행한** 입력 — 별칭 값이 전부 실재 콘솔 이름이다."""
    if axis == _R18_AXIS_BOTH_TYPE:
        return _r18_resolve(
            TypeRequest(
                candidate_id="r18", instrument_type=value, gdtf_fixture=value, mode=_R18_LIB_MODE
            ),
            {value: dict(_R18_GOOD_ALIAS)},
        )
    if axis == _R18_AXIS_GDTF_ONLY:
        return _r18_resolve(
            TypeRequest(
                candidate_id="r18",
                instrument_type=_R18_LIB_TYPE,
                gdtf_fixture=value,
                mode=_R18_LIB_MODE,
            ),
            {_R18_LIB_TYPE: dict(_R18_GOOD_ALIAS)},
        )
    return _r18_resolve(
        TypeRequest(candidate_id="r18", instrument_type=_R18_LIB_TYPE, mode=_R18_LIB_MODE),
        {_R18_LIB_TYPE: dict(_R18_GOOD_ALIAS)},
    )


class TestRound18ConfirmationPathExists:
    """[round18 R18-E ②] 확인을 말하는 갈래에는 확인을 수행할 인자가 **실제로** 있어야 한다."""

    def test_every_confirmation_branch_has_an_input_that_actually_confirms(self):
        """[round18 R18-E] `confirmation_path=True`인 축마다 그 확인을 수행한 입력이
        `resolved`를 낸다 — 확정 경로를 막는 뮤테이션(예: `confirmed_type = None`)에서 실패한다.
        """
        for row in _R18_AXIS_ROWS:
            if not row.confirmation_path:
                continue
            for value in _R18_VACUOUS_VALUES:
                if row.axis == _R18_AXIS_BOTH_TYPE and not (isinstance(value, str) and value):
                    continue  # falsy 이름은 별칭 키가 없다 — 아래 막다른 길 게이트가 다룬다.
                payload = _r18_confirmed(row.axis, value)
                observed = row_by_id(payload, "r18")
                assert observed["status"] == TYPE_RESOLVED, (row.axis, repr(value))
                assert observed["console_type"] == _R18_LIB_TYPE, (row.axis, repr(value))
                assert observed["confirmation_source"] == ALIAS_CONFIRMATION_SOURCE

    def test_a_falsy_designed_type_name_is_a_dead_end_and_is_never_called_pending(self):
        """[round18 R18-E] 진짜 막다른 길 — `None`·`''`은 `_alias_for`의
        `if not key: continue`에 걸려 **어떤 별칭으로도** 해결되지 않는다.

        `typemap.py` 공허 갈래를 `TYPE_NEEDS_CONFIRMATION` · `hard_stop_code=None`으로
        되돌리면 실패한다: 해결 불가능한 상태가 "확인 대기"로 보고된다.
        """
        for value in (None, ""):
            for aliases in (
                {},
                {"": dict(_R18_GOOD_ALIAS)},
                {_R18_LIB_TYPE: dict(_R18_GOOD_ALIAS)},
                {"": dict(_R18_GOOD_ALIAS), _R18_LIB_TYPE: dict(_R18_GOOD_ALIAS)},
            ):
                request = TypeRequest(
                    candidate_id="r18",
                    instrument_type=value,
                    gdtf_fixture=value,
                    mode=_R18_LIB_MODE,
                )
                assert _alias_for(request, aliases) == (None, None, None), (repr(value), aliases)
                payload = _r18_resolve(request, aliases)
                row = row_by_id(payload, "r18")
                assert row["status"] == TYPE_NAME_UNUSABLE, (repr(value), aliases)
                assert row["confirmation_required"] is False, (repr(value), aliases)
                assert hard_stop_codes(payload) == [FIXTURE_TYPE_NAME_UNUSABLE]

    def test_the_hard_stop_reason_does_not_promise_a_confirmation_it_cannot_deliver(self):
        """[round18 R18-E] 사유 문장이 "사용자 확인으로 넘긴다"고 말하면 실패한다 —
        하드 스톱 갈래의 사유가 확인을 약속하면 조작자는 오지 않는 화면을 기다린다.
        """
        payload = _r18_resolve(
            TypeRequest(candidate_id="r18", instrument_type=None, mode=_R18_LIB_MODE), {}
        )
        reason = row_by_id(payload, "r18")["reason"]
        assert reason == VACUOUS_TYPE_KEY_REASON
        assert "사용자 확인으로 넘긴다" not in reason
        assert "확인 대기가 아니라" in reason
        # 무엇을 고쳐야 하는지 말한다 — 고칠 대상이 콘솔이 아니라 도면임을 지목한다.
        assert "도면" in reason

    def test_the_confirmation_input_registry_covers_every_pending_axis(self):
        """[round18 R18-E ②] 확인 대기 축이 새로 생기면 이 표에 등기해야 한다 —
        등기 없이 축이 늘면 "확인 경로가 있다"는 주장이 검증 없이 통과한다.
        """
        pending = {row.axis for row in _R18_AXIS_ROWS if row.confirmation_path}
        assert set(_R18_CONFIRMATION_INPUTS) == pending
        for axis, description in _R18_CONFIRMATION_INPUTS.items():
            assert description.strip(), axis


# --------------------------------------------------------------------------
# [round18 R18-E ③] `_alias_for` 키의 **형제** — 저장된 사람 확인을 이름으로 조회하는 자리 전수
#
# `_alias_for`가 막다른 길을 만든 원인은 "확인 저장소의 키가 곧 확인해야 할 값"이라는 구조다.
# 같은 구조가 다른 자리에도 있으면 같은 막다른 길이 생긴다. 그래서 `server/vwx/` 전 모듈에서
# **매핑 조회(`.get(...)`)** 를 AST로 전수 열거하고 키 출처를 **식에서 계산**해 분류한다.
# --------------------------------------------------------------------------

_R18_KEY_DESIGN_STRING = "design_string"
_R18_KEY_SYNTHETIC_ID = "synthetic_id"
_R18_KEY_INTERNAL = "internal"

_R18_KEY_ORIGINS = (_R18_KEY_DESIGN_STRING, _R18_KEY_SYNTHETIC_ID, _R18_KEY_INTERNAL)


def _r18_scan_mapping_lookups() -> set[tuple[str, str, str]]:
    """`server/vwx/` 전 모듈에서 `<expr>.get(<key>[, default])` 호출을 전수 열거한다."""
    found: set[tuple[str, str, str]] = set()
    for path in iter_vwx_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        label = vwx_module_label(path)

        def walk(node: ast.AST, stack: tuple[str, ...], name: str = label) -> None:
            named = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            here = stack + (node.name,) if named else stack
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
            ):
                found.add((name, ".".join(here) or "<module>", ast.unparse(node)))
            for child in ast.iter_child_nodes(node):
                walk(child, here, name)

        walk(tree, ())
    return found


def _r18_classify_lookup(call: str) -> str:
    """키 식에서 출처를 **계산한다** — 자유 라벨이면 등기부가 자기충족이 된다."""
    key = call.split(".get(", 1)[1]
    if "candidate_id" in key or "target.id" in key or "planned." in key:
        return _R18_KEY_SYNTHETIC_ID
    if any(token in key for token in ("instrument_type", "key", "name", "match_type")):
        return _R18_KEY_DESIGN_STRING
    return _R18_KEY_INTERNAL


class TestRound18ConfirmationKeySiblings:
    """[round18 R18-E ③] 확인 저장소를 도면 문자열로 조회하는 자리 전수."""

    def test_the_mapping_lookup_scan_finds_the_alias_site_it_is_meant_to_cover(self):
        """스캐너 비공허성 — `_alias_for`의 `aliases.get(key)`가 실제로 잡힌다.

        이 단정이 없으면 스캐너가 아무것도 못 찾아도 아래 분류가 공허하게 통과한다.
        """
        sites = _r18_scan_mapping_lookups()
        alias_sites = [
            site for site in sites if site[0] == "typemap.py" and site[1] == "_alias_for"
        ]
        assert alias_sites, sorted(sites)[:5]
        assert any(site[2] == "aliases.get(key)" for site in alias_sites), alias_sites

    def test_every_key_origin_is_actually_produced_and_the_alias_site_is_design_keyed(self):
        """[round18 R18-E ③] 분류가 세 출처를 모두 산출하고, `_alias_for`가
        `design_string` 갈래에 든다 — 분류를 한 갈래로 뭉개면(예: 항상 `internal`) 실패한다.
        """
        sites = _r18_scan_mapping_lookups()
        observed = {_r18_classify_lookup(site[2]) for site in sites}
        assert observed == set(_R18_KEY_ORIGINS), sorted(observed)
        design_keyed = sorted(
            site for site in sites if _r18_classify_lookup(site[2]) == _R18_KEY_DESIGN_STRING
        )
        assert any(site[1] == "_alias_for" for site in design_keyed), design_keyed

    def test_every_design_string_keyed_lookup_refuses_a_vacuous_key_without_a_dead_end(self):
        """[round18 R18-E ③] 도면 문자열을 키로 쓰는 조회 자리마다 공허한 키가
        **조용한 막다른 길**이 되지 않음을 프로덕션 산출물로 확인한다.

        `typemap._alias_for` — 공허 키는 하드 스톱으로 나간다.
        `apply` 이름 조회 — 공백만 이름은 `fixture_name_missing`으로 제외된다
        (대조군은 `test_autopatch_execute.py`의 round18 이름 가드 섹션).
        두 자리 중 하나라도 조용히 통과하면 아래 단정이 깨진다.
        """
        for value in (None, "", "   ", "---"):
            payload = _r18_resolve(
                TypeRequest(
                    candidate_id="r18",
                    instrument_type=value,
                    gdtf_fixture=value,
                    mode=_R18_LIB_MODE,
                ),
                {},
            )
            row = row_by_id(payload, "r18")
            # 조용한 통과가 아니다 — 상태·하드스톱·사유 셋 모두가 사건을 보고한다.
            assert row["status"] == TYPE_NAME_UNUSABLE, repr(value)
            assert hard_stop_codes(payload) == [FIXTURE_TYPE_NAME_UNUSABLE], repr(value)
            assert row["reason"] == VACUOUS_TYPE_KEY_REASON, repr(value)


# --- round18 컬럼 우선순위 · 주소 계열 · 1단계 특성화 (VacuityAndData) ---
#
# [round18 R18-G] `columns.py:200`의 `fields.setdefault(canonical, value)`는 주석이 명시로
# "나중 값으로 조용히 덮어쓰지 않는다"고 적은 **우선순위 규약**인데 대조군이 없었다. Vectorworks
# 내보내기에는 `Type`과 `Fixture Type`이 **동시에** 들어오는 파일이 흔하고, 둘 다
# `instrument_type`으로 해석되므로 규약이 깨지면 `instrument_type`이 바뀐다 — 그 값은
# 1단계 리포트를 타고 2단계 타입 확정으로 흘러 **전달 Lua의 `FixtureTypes[...]`가 바뀐다**.
#
# [round18 minor] `columns.py:52` `ADDRESS_FAMILY_FIELDS`는 행 삭제 무검출이었다
# (형제 `ALIAS_TABLE`은 KILLED — **형제 미적용**이 여덟 라운드째 같은 기제다).


def _r18_stage_one_report(
    raw_records: list[dict[str, str]], console_records: tuple[FixtureRecord, ...] = ()
) -> dict:
    """1단계 전 구간을 **실제로** 통과시킨다 — 컬럼 해석부터 리포트 payload까지.

    `columns.resolve_columns` -> `address.resolve_all` -> `rig.build_designed_rig` ->
    `diff.compare` -> `report.build_vwx_report`. 컬럼 해석 결과가 2단계 입력에 실제로
    닿는지를 중간 단계를 건너뛰지 않고 확인하기 위한 배선이다.
    """
    records, _failures, _excluded = resolve_columns(raw_records)
    resolved, _address_failures = resolve_all(records)
    designed = build_designed_rig(resolved, candidate_count=len(records))
    return build_vwx_report(compare(designed, _r17_inventory(*console_records))).to_dict()


#: 같은 행에서 `instrument_type`으로 중복 해석되는 두 헤더. 첫 값이 이긴다(규약).
_R18_TYPE_HEADER_FIRST = "Type"
_R18_TYPE_HEADER_SECOND = "Fixture Type"
_R18_TYPE_VALUE_FIRST = "MegaPointe"
_R18_TYPE_VALUE_SECOND = "LEDWash 600"


def _r18_duplicate_type_row(*, reversed_order: bool = False) -> dict[str, str]:
    pair = (
        (_R18_TYPE_HEADER_SECOND, _R18_TYPE_VALUE_SECOND),
        (_R18_TYPE_HEADER_FIRST, _R18_TYPE_VALUE_FIRST),
    )
    if not reversed_order:
        pair = tuple(reversed(pair))
    row = dict(pair)
    row["Universe"] = "1"
    row["DMX Address"] = "1"
    row["Unit Number"] = "1"
    return row


class TestRound18ColumnPriorityConvention:
    """[round18 R18-G] 같은 행에서 별칭이 중복 매칭될 때의 **우선순위 규약** 대조군."""

    def test_the_duplicate_alias_headers_really_do_collide_on_one_canonical_field(self):
        """비공허성 — 두 헤더가 같은 정규 필드로 해석되지 않으면 아래 규약 검사가 공허하다."""
        assert resolve_header(_R18_TYPE_HEADER_FIRST) == "instrument_type"
        assert resolve_header(_R18_TYPE_HEADER_SECOND) == "instrument_type"
        assert normalize_header(_R18_TYPE_HEADER_FIRST) != normalize_header(_R18_TYPE_HEADER_SECOND)

    def test_the_first_matching_header_wins_in_source_order(self):
        """[round18 R18-G] `columns.py`의 `fields.setdefault(canonical, value)`를
        `fields[canonical] = value`로 바꾸면 실패한다 — last-write-wins가 되어 두 방향에서
        서로 다른 `instrument_type`이 나온다.

        방향을 둘 다 검사하는 것이 핵심이다: 한 방향만 보면 `setdefault`와 대입이 같은 답을
        내는 입력이 존재해 뮤턴트가 살아남는다(round18 실측).
        """
        forward, _f, _e = resolve_columns([_r18_duplicate_type_row()])
        backward, _f2, _e2 = resolve_columns([_r18_duplicate_type_row(reversed_order=True)])

        assert forward[0].fields["instrument_type"] == _R18_TYPE_VALUE_FIRST
        assert backward[0].fields["instrument_type"] == _R18_TYPE_VALUE_SECOND
        # 덮어쓰지 않으므로 **버려진 값은 extra에도 남지 않는다**(정규 필드로 해석됐으므로).
        assert _R18_TYPE_VALUE_SECOND not in forward[0].extra.values()
        assert _R18_TYPE_HEADER_SECOND not in forward[0].extra

    def test_breaking_the_priority_convention_changes_the_type_that_reaches_stage_two(self):
        """[round18 R18-G 도달성] 규약이 깨지면 **2단계 타입 확정 결과가 바뀐다**.

        컬럼 해석 -> 주소 해석 -> 리그 -> 대조 -> 리포트까지 실제로 통과시킨 뒤, 그 리포트의
        `instrument_type`으로 `resolve_fixture_types`를 돌린다. 라이브러리에는 **두 이름이
        모두** 있으므로 확정되는 `console_type`이 곧 컬럼 우선순위의 함수다 —
        그 이름이 그대로 전달 Lua의 `Patch().FixtureTypes[...]`에 박힌다.
        """
        library = [
            (_R18_TYPE_VALUE_FIRST, [(_R18_LIB_MODE, 24)]),
            (_R18_TYPE_VALUE_SECOND, [(_R18_LIB_MODE, 24)]),
        ]
        for reversed_order, expected in (
            (False, _R18_TYPE_VALUE_FIRST),
            (True, _R18_TYPE_VALUE_SECOND),
        ):
            report = _r18_stage_one_report([_r18_duplicate_type_row(reversed_order=reversed_order)])
            designed = report["designed_rig"]["fixtures"][0]
            missing = report["diffs"]["missing_in_console"][0]
            assert designed["instrument_type"] == expected, reversed_order
            assert missing["instrument_type"] == expected, reversed_order

            payload = resolve_fixture_types(
                [
                    request(
                        "r18-col",
                        instrument_type=missing["instrument_type"],
                        mode=_R18_LIB_MODE,
                    )
                ],
                library_port=LibraryRigPort(library),
                type_aliases={
                    missing["instrument_type"]: {
                        "type": missing["instrument_type"],
                        "mode": _R18_LIB_MODE,
                    }
                },
            ).to_dict()
            row = row_by_id(payload, "r18-col")
            assert row["status"] == TYPE_RESOLVED, reversed_order
            # 전달 Lua의 `FixtureTypes[...]`가 되는 값 — 규약을 깨면 여기가 갈린다.
            assert row["console_type"] == expected, reversed_order

    def test_the_alias_lookup_is_injective_so_no_field_silently_shadows_another(self):
        """[round18 R18-G 형제] `_build_alias_lookup`은 `lookup[key] = field` 대입이다 —
        두 정규 필드가 같은 정규화 키를 주장하면 뒤에 온 필드가 앞을 **조용히** 덮는다.

        표를 늘리다 그런 충돌이 생기면 여기서 걸린다(현재는 충돌 0건).
        """
        seen: dict[str, str] = {}
        collisions: list[tuple[str, str, str]] = []
        for field_name, aliases in ALIAS_TABLE.items():
            for alias in aliases:
                key = normalize_header(alias)
                if key in seen and seen[key] != field_name:
                    collisions.append((key, seen[key], field_name))
                seen[key] = field_name
        assert collisions == []
        assert len(ALIAS_LOOKUP) == len(seen)


def _r18_address_family_row(field_name: str) -> dict[str, str]:
    """그 주소 계열 필드 **하나만** 담은 최소 유효 레코드 후보."""
    return {"Type": _R18_TYPE_VALUE_FIRST, ALIAS_TABLE[field_name][0]: "1/1"}


#: **독립 등기부** — `ADDRESS_FAMILY_FIELDS`의 원소를 테스트 안에 리터럴로 적는다.
#: [round18 실측] 프로덕션 상수를 순회하는 형태로만 쓰면 원소를 지운 뮤테이션이 SURVIVED다
#: (지워진 원소는 순회에서도 사라지므로) — 그것이 round18이 지적한 자기충족 표의 형태다.
#: 그래서 기대 집합은 여기 리터럴이고 프로덕션과 **전단사**를 요구한다.
_R18_ADDRESS_FAMILY_EXPECTED = (
    "absolute_address",
    "address",
    "universe",
    "universe_address",
)


def _r18_assert_address_family_registry(fields: frozenset[str]) -> None:
    """등기부 <-> 프로덕션 전단사 — 어느 쪽에서 원소를 지워도 깨진다."""
    assert set(fields) == set(_R18_ADDRESS_FAMILY_EXPECTED), sorted(fields)
    assert len(_R18_ADDRESS_FAMILY_EXPECTED) == len(set(_R18_ADDRESS_FAMILY_EXPECTED))


def _r18_assert_address_family_shape(fields: frozenset[str]) -> None:
    """행 삭제 프로브 — 집합의 원소마다 **프로덕션 판정이 달라진다**는 성질로 결손을 잡는다.

    `has_address_family`와 최소 유효 레코드 판정 둘 다 이 집합을 읽으므로, 원소 하나를
    지우면 그 별칭만 담은 행이 "주소 표현 없음"으로 뒤집힌다. 자기 자신과 비교하지 않고
    프로덕션 산출물로 확인하므로 항진식이 아니다.
    """
    assert fields, "빈 집합이면 아래 순회가 공허하다"
    for field_name in sorted(fields):
        assert field_name in ALIAS_TABLE, field_name
        headers = list(_r18_address_family_row(field_name))
        assert has_address_family(headers), field_name
        records, failures, _excluded = resolve_columns([_r18_address_family_row(field_name)])
        assert len(records) == 1, field_name
        assert failures == [], field_name
    # 주소 계열이 **아닌** 필드는 이 집합에 들어 있지 않다 — 집합이 전체로 부풀면 걸린다.
    for outsider in ("instrument_type", "mode", "footprint", "unit_number"):
        assert outsider not in fields, outsider


class TestRound18AddressFamilyMembership:
    """[round18 minor] `ADDRESS_FAMILY_FIELDS` 행 삭제 검출 — 형제 `ALIAS_TABLE`과 같은 강도로."""

    def test_the_address_family_registry_is_a_bijection_onto_production(self):
        """[round18 minor] `columns.py`의 `ADDRESS_FAMILY_FIELDS`에서 원소를 지우거나
        더하면 실패한다 — 순회형 검사만으로는 삭제가 잡히지 않아(실측 SURVIVED)
        독립 등기부와 전단사를 요구한다.
        """
        _r18_assert_address_family_registry(ADDRESS_FAMILY_FIELDS)
        for index in range(len(_R18_ADDRESS_FAMILY_EXPECTED)):
            pruned = frozenset(
                name
                for position, name in enumerate(_R18_ADDRESS_FAMILY_EXPECTED)
                if position != index
            )
            with pytest.raises(AssertionError):
                _r18_assert_address_family_registry(pruned)
        with pytest.raises(AssertionError):
            _r18_assert_address_family_registry(
                frozenset(_R18_ADDRESS_FAMILY_EXPECTED) | {"instrument_type"}
            )

    def test_every_address_family_member_alone_makes_a_valid_minimum_record(self):
        _r18_assert_address_family_shape(frozenset(_R18_ADDRESS_FAMILY_EXPECTED))

    def test_removing_any_address_family_member_is_detected(self, monkeypatch):
        """[round18 minor] `columns.py`의 `ADDRESS_FAMILY_FIELDS`에서 어느 원소를 지워도
        실패한다 — 프로덕션 상수를 **실제로 그 값으로 바꿔** 판정이 뒤집히는 것을 본다.

        `resolve_columns`와 `has_address_family` 둘 다 이 상수를 읽으므로, 원소 하나를
        지우면 그 별칭만 담은 행이 `min_record_incomplete`로 뒤집힌다. 상수를 손대지 않고
        "지웠다면 이랬을 것"을 테스트 안에서 재계산하면 프로덕션이 그 상수를 실제로 읽는지는
        확인되지 않는다 — 그래서 monkeypatch로 프로덕션 경로를 그대로 태운다.
        """
        for dropped in _R18_ADDRESS_FAMILY_EXPECTED:
            pruned = frozenset(set(_R18_ADDRESS_FAMILY_EXPECTED) - {dropped})
            monkeypatch.setattr(columns_module, "ADDRESS_FAMILY_FIELDS", pruned)
            row = _r18_address_family_row(dropped)
            assert columns_module.has_address_family(list(row)) is False, dropped
            records, failures, _excluded = columns_module.resolve_columns([row])
            assert records == [], dropped
            assert [failure.kind for failure in failures] == [READ_FAILURE_MIN_RECORD], dropped
            monkeypatch.undo()
        # 되돌린 뒤에는 원래대로 통과한다 — monkeypatch가 새는지 여기서 걸린다.
        _r18_assert_address_family_registry(ADDRESS_FAMILY_FIELDS)

    def test_an_unresolvable_address_header_is_still_a_read_failure(self):
        """비공허성 — 주소 계열이 전혀 없으면 최소 유효 레코드 미달로 보고된다.
        (위 게이트가 모든 행을 통과시키도록 깨지면 이 단정이 남는다.)
        """
        records, failures, _excluded = resolve_columns([{"Type": _R18_TYPE_VALUE_FIRST}])
        assert records == []
        assert [failure.kind for failure in failures] == [READ_FAILURE_MIN_RECORD]


# --------------------------------------------------------------------------
# [round18 R18-J] 1단계 `diff.py` 공허명 후보 소멸 — **특성화 + 이관**
#
# 아래 세 테스트는 **현행 동작의 기록이며 그 동작이 옳다는 판정이 아니다.**
# 소유는 1단계 SPEC(`SPEC-COPILOT-VWX-*`)이고, `server/vwx/diff.py`는 AC-AUTOPATCH-025
# 「1단계 공개 계약 무변경」 계층이므로 이 SPEC은 동작을 바꾸지 않는다. 우리 층이 할 수 있고
# 해야 하는 일은 **고지**이며, 그 고지의 대조군은 아래 `TestRound18OurLayerDiscloses...`다.
# --------------------------------------------------------------------------


class TestRound18Stage1VacuousJoinCharacterisation:
    """[round18 R18-J] 1단계 대조가 공허명 후보를 삼키는 현행 동작의 기록(이관 대상)."""

    def test_a_vacuous_designed_type_vanishes_from_both_console_join_verdicts(self):
        """**현행 동작 기록 · 옳다는 판정이 아니다 · 소유는 1단계 SPEC.**

        `rig.fuzzy_type_equal`이 정규화 후 빈 문자열을 모든 이름에 포함으로 보므로,
        공허명 도면 픽스처는 그 주소에 콘솔 픽스처가 있으면 `missing_in_console`에서
        `found`로 사라지고, `quantity_mismatch`에서도 첫 콘솔 타입 수량과 대조되어 사라진다.
        `skipped_checks`에는 그 소멸이 적히지 않는다.
        """
        designed = _r17_rig(
            _r17_designed_fixture("U1", _R18_LIB_TYPE, 1, 1),
            _r17_designed_fixture("U2", "---", 1, 5),
        )
        console = _r17_inventory(_r17_console_record(1, "1.5", "LEDWash 600"))
        result = compare(designed, console)

        assert [entry.instrument_type for entry in result.missing_in_console] == [_R18_LIB_TYPE]
        assert [entry.instrument_type for entry in result.quantity_mismatches] == [_R18_LIB_TYPE]
        # 소멸이 미수행 판정으로 적히지 않는다 — 여기가 이관 사유다.
        assert "---" not in {entry.kind for entry in result.skipped_checks}
        assert all("공허" not in entry.reason for entry in result.skipped_checks)

    def test_a_substantive_designed_type_at_the_same_address_is_reported(self):
        """비공허성 대조군 — 이름만 정상으로 바꾸면 같은 입력이 **양쪽에서 보고된다**.
        (위 테스트가 주소·인벤토리 실수로 공허하게 통과하는 것을 막는다.)
        """
        designed = _r17_rig(
            _r17_designed_fixture("U1", _R18_LIB_TYPE, 1, 1),
            _r17_designed_fixture("U2", "Mac Aura", 1, 5),
        )
        console = _r17_inventory(_r17_console_record(1, "1.5", "LEDWash 600"))
        result = compare(designed, console)

        assert sorted(entry.instrument_type for entry in result.missing_in_console) == [
            "Mac Aura",
            _R18_LIB_TYPE,
        ]
        assert sorted(entry.instrument_type for entry in result.quantity_mismatches) == [
            "Mac Aura",
            _R18_LIB_TYPE,
        ]

    def test_the_quantity_mismatch_direction_is_symmetric_not_console_excess_only(self):
        """**현행 동작 기록 · 옳다는 판정이 아니다 · 소유는 1단계 SPEC**(round18 minor).

        `diff.py`의 수량 비교는 `designed_count != console_count`다 — 콘솔이 도면보다
        **많은** 방향도 불일치로 보고된다. `>`로 좁히면 콘솔 초과가 조용해진다. 어느 쪽이
        옳은지는 1단계가 정한다; 여기서는 현행 방향을 고정만 한다.
        """
        designed = _r17_rig(_r17_designed_fixture("U1", _R18_LIB_TYPE, 1, 1))
        console = _r17_inventory(
            _r17_console_record(1, "1.1", _R18_LIB_TYPE),
            _r17_console_record(2, "1.20", _R18_LIB_TYPE),
        )
        result = compare(designed, console)

        assert [
            (entry.instrument_type, entry.designed_count, entry.console_count)
            for entry in result.quantity_mismatches
        ] == [(_R18_LIB_TYPE, 1, 2)]

    def test_a_one_channel_span_overlap_is_still_an_overlap(self):
        """**현행 동작 기록 · 옳다는 판정이 아니다 · 소유는 1단계 SPEC**(round18 minor).

        `rig.py`의 `if s2 > e1: break` 경계 — 1채널만 겹쳐도 겹침이다. `>=`로 바꾸면
        정확히 1채널 겹침이 조용해지고, 인접(겹치지 않음)은 그대로 통과한다.
        """
        overlapping = build_designed_rig(
            [
                _r18_resolved_record(0, "U1", 1, 1, footprint="2"),
                _r18_resolved_record(1, "U2", 1, 2, footprint="2"),
            ]
        )
        adjacent = build_designed_rig(
            [
                _r18_resolved_record(0, "U1", 1, 1, footprint="1"),
                _r18_resolved_record(1, "U2", 1, 2, footprint="1"),
            ]
        )
        assert len(overlapping.design_overlaps) == 1
        assert adjacent.design_overlaps == ()


def _r18_resolved_record(row_index: int, unit: str, universe: int, address: int, *, footprint: str):
    """`build_designed_rig`가 소비하는 `ResolvedRecord` 하나 — 폭 컬럼을 실제로 담는다."""
    return ResolvedRecord(
        fields={
            "instrument_type": _R18_LIB_TYPE,
            "unit_number": unit,
            "position": "FOH",
            "footprint": footprint,
        },
        extra={},
        row_index=row_index,
        universe=universe,
        address=address,
        classification="patched",
        address_basis="universe_address_direct",
    )


def _r18_designed_only_report(*, classification: str, coordinates: bool = True) -> dict:
    """도면 픽스처 두 대(정상 1 · 공허 1)를 담은 최소 리포트 payload.

    공허명 픽스처에 **좌표를 준다** — `classification`이 미패치인데 좌표가 있는 payload는
    `diff.compare`가 조인에서 제외하는 항목이므로 고지 대상이 아니다. 좌표 유무로 판정하면
    이 경계가 흐려진다(round18 실측: `classification` 필터만 지운 뮤턴트가 SURVIVED였다).
    """
    return {
        "designed_rig": {
            "fixture_count": 2,
            "fixtures": [
                {
                    "unit_number": "U1",
                    "instrument_type": _R18_LIB_TYPE,
                    "gdtf_fixture": None,
                    "mode": _R18_LIB_MODE,
                    "footprint": 16,
                    "system": None,
                    "universe": 1,
                    "address": 1,
                    "classification": "patched",
                    "address_basis": "universe_address_direct",
                },
                {
                    "unit_number": "U9",
                    "instrument_type": "---",
                    "gdtf_fixture": None,
                    "mode": _R18_LIB_MODE,
                    "footprint": 16,
                    "system": None,
                    "universe": 1 if coordinates else None,
                    "address": 30 if coordinates else None,
                    "classification": classification,
                    "address_basis": "universe_address_direct",
                },
            ],
        },
        "diffs": {
            "performed": True,
            "missing_in_console": [
                {
                    "unit_number": "U1",
                    "instrument_type": _R18_LIB_TYPE,
                    "universe": 1,
                    "address": 1,
                    "detail": "",
                }
            ],
            "address_collision": [],
            "quantity_mismatch": [],
        },
        "skipped_checks": [],
    }


class TestRound18OurLayerDisclosesTheVacuousJoin:
    """[round18 R18-J] 고칠 수는 없지만 **고지할 자리는 우리 층에 있다** — 그 고지의 대조군."""

    def test_the_patch_plan_discloses_the_vacuous_designed_type_as_a_skipped_check(self):
        """[round18 R18-J] `patchplan._vacuous_designed_type_checks`를 지우거나 빈 튜플만
        돌려주게 바꾸면 실패한다 — 조작자는 소멸했을 수 있는 항목을 모른 채 계획을 승인한다.
        """
        from server.vwx.patchplan import build_patch_plan
        from server.vwx.verdicts import DESIGNED_TYPE_NAME_VACUOUS, skipped_check_label

        designed = _r17_rig(
            _r17_designed_fixture("U1", _R18_LIB_TYPE, 1, 1),
            _r17_designed_fixture("U2", "---", 1, 5),
        )
        console = _r17_inventory(_r17_console_record(1, "1.5", "LEDWash 600"))
        report = build_vwx_report(compare(designed, console)).to_dict()

        payload = build_patch_plan(report).to_dict()
        checks = [
            check
            for check in payload["skipped_checks"]
            if check["kind"] == DESIGNED_TYPE_NAME_VACUOUS
        ]
        assert len(checks) == 1
        (check,) = checks
        assert check["label"] == skipped_check_label(DESIGNED_TYPE_NAME_VACUOUS)
        # 좌표로 가리킨다 — 도면 원문 이름을 사유에 되싣지 않는다(§0 2b④).
        assert tuple(check["affected_designed_addresses"]) == ("1.5",)
        assert check["affected_count"] == 1
        assert "---" not in check["reason"]
        # 되살리지 않는다 — 1단계 판정을 재계산하지 않는다.
        assert [candidate["type"] for candidate in payload["candidates"]] == [_R18_LIB_TYPE]

    def test_an_unpatched_vacuous_fixture_is_not_disclosed_because_nothing_was_joined(self):
        """[round18 R18-J 형제 경계] 미패치("설계됨·미배정") 픽스처는 `diff.compare`가
        콘솔 조인에서 **애초에 제외**한다(`classification != "patched"` -> continue).
        조인되지 않은 것은 삼켜질 수도 없으므로 고지 대상이 아니다.

        `patchplan._vacuous_designed_type_checks`의 `classification` 필터를 지우면
        실패한다 — 있지도 않은 소멸을 고지하면 조작자는 경고를 무시하게 되고,
        무시되는 경고는 게이트가 아니다.
        """
        from server.vwx.patchplan import build_patch_plan
        from server.vwx.verdicts import DESIGNED_TYPE_NAME_VACUOUS

        # 2단계는 리포트 **payload**를 입력으로 받는다 — `classification`과 좌표의 정합성을
        # 보장하는 것은 payload 생산자이고, 우리 층은 payload가 말하는 것을 그대로 읽는다.
        # `diff.compare`는 `classification != "patched"`면 좌표가 있어도 조인하지 않으므로
        # (diff.py:147) 그런 항목은 삼켜질 수 없다 — 좌표 유무가 아니라 `classification`이
        # 경계다. 그래서 **좌표가 있는 미패치**로 그 경계를 정확히 겨눈다.
        for classification, disclosed in (("unpatched_designed", False), ("patched", True)):
            payload = build_patch_plan(
                _r18_designed_only_report(classification=classification)
            ).to_dict()
            kinds = {check["kind"] for check in payload["skipped_checks"]}
            assert (DESIGNED_TYPE_NAME_VACUOUS in kinds) is disclosed, classification

    def test_the_disclosure_is_silent_when_no_designed_type_name_is_vacuous(self):
        """비공허성 — 정상 이름만 있는 리포트에서는 고지가 나오지 않는다.
        (항상 고지하도록 깨지면 조작자가 경고를 무시하게 되고 게이트가 힘을 잃는다.)
        """
        from server.vwx.patchplan import build_patch_plan
        from server.vwx.verdicts import DESIGNED_TYPE_NAME_VACUOUS

        designed = _r17_rig(_r17_designed_fixture("U1", _R18_LIB_TYPE, 1, 1))
        console = _r17_inventory()
        report = build_vwx_report(compare(designed, console)).to_dict()

        payload = build_patch_plan(report).to_dict()
        assert DESIGNED_TYPE_NAME_VACUOUS not in {
            check["kind"] for check in payload["skipped_checks"]
        }

    def test_a_patched_fixture_without_coordinates_is_not_disclosed_either(self):
        """[round18 R18-J 형제 경계 ②] `diff.compare`는 좌표가 미해석이면
        (`fixture.universe is None or fixture.address is None`) 그 픽스처도 조인에서
        제외한다(diff.py:146-148). 조인되지 않은 것은 삼켜질 수 없으므로 고지 대상이 아니고,
        고지에 실을 좌표도 없다.

        `patchplan._vacuous_designed_type_checks`의 좌표 가드를 지우면 실패한다 —
        `affected_designed_addresses`에 `'None.None'`이 실려 조작자가 없는 주소를 찾아간다.
        """
        from server.vwx.patchplan import build_patch_plan
        from server.vwx.verdicts import DESIGNED_TYPE_NAME_VACUOUS

        payload = build_patch_plan(
            _r18_designed_only_report(classification="patched", coordinates=False)
        ).to_dict()
        checks = [
            check
            for check in payload["skipped_checks"]
            if check["kind"] == DESIGNED_TYPE_NAME_VACUOUS
        ]
        assert checks == []
        # 좌표가 있으면 같은 입력이 고지된다 — 경계가 좌표임을 고정한다.
        with_coordinates = build_patch_plan(
            _r18_designed_only_report(classification="patched", coordinates=True)
        ).to_dict()
        (disclosed,) = [
            check
            for check in with_coordinates["skipped_checks"]
            if check["kind"] == DESIGNED_TYPE_NAME_VACUOUS
        ]
        assert tuple(disclosed["affected_designed_addresses"]) == ("1.30",)
        assert "None" not in " ".join(disclosed["affected_designed_addresses"])

    def test_the_disclosure_uses_the_same_match_type_precedence_as_stage_one(self):
        """[round18 R18-J 형제 축] 1단계 조인은 `rig.match_type`
        (= `gdtf_fixture or instrument_type`)을 쓴다 — 그래서 **GDTF 칸이 공허하면**
        `instrument_type`이 정상이어도 그 픽스처는 삼켜진다.

        `patchplan._vacuous_designed_type_checks`가 `instrument_type`만 보도록 바꾸면
        실패한다: 우선순위가 1단계와 어긋나면 고지가 대상과 어긋난다(형제 축 미적용).
        """
        from server.vwx.patchplan import build_patch_plan
        from server.vwx.verdicts import DESIGNED_TYPE_NAME_VACUOUS

        # 1단계가 실제로 그 우선순위로 삼키는지 먼저 확인한다 — 전제를 가정하지 않는다.
        swallowed = DesignedFixture(
            unit_number="U9",
            instrument_type=_R18_LIB_TYPE,
            mode=None,
            channel=None,
            universe=1,
            address=30,
            classification="patched",
            part_indices=(),
            device_type=None,
            gdtf_fixture="---",
        )
        designed = _r17_rig(_r17_designed_fixture("U1", _R18_LIB_TYPE, 1, 1), swallowed)
        console = _r17_inventory(_r17_console_record(1, "1.30", "LEDWash 600"))
        result = compare(designed, console)
        assert [entry.unit_number for entry in result.missing_in_console] == ["U1"]

        report = build_vwx_report(result).to_dict()
        assert report["designed_rig"]["fixtures"][1]["gdtf_fixture"] == "---"
        assert report["designed_rig"]["fixtures"][1]["instrument_type"] == _R18_LIB_TYPE

        (check,) = [
            check
            for check in build_patch_plan(report).to_dict()["skipped_checks"]
            if check["kind"] == DESIGNED_TYPE_NAME_VACUOUS
        ]
        assert tuple(check["affected_designed_addresses"]) == ("1.30",)

    def test_the_disclosure_survives_every_plan_branch_not_just_the_planned_one(self):
        """[round18 R18-J · 형제 표면] 고지는 거부 갈래에서도 나온다 — 계획 갈래에만 붙이면
        거부 화면을 본 조작자는 같은 사실을 보지 못한다(여덟 라운드째 지적된 형제 미적용).

        `build_patch_plan`의 고지 부착을 `_plan_from_report`의 특정 갈래로 옮기면 실패한다.
        """
        from server.vwx.patchplan import build_patch_plan
        from server.vwx.verdicts import DESIGNED_TYPE_NAME_VACUOUS

        designed = _r17_rig(
            _r17_designed_fixture("U1", _R18_LIB_TYPE, 1, 1),
            _r17_designed_fixture("U2", "---", 1, 5),
        )
        report = build_vwx_report(
            compare(designed, _r17_inventory(_r17_console_record(1, "1.5", "LEDWash 600")))
        ).to_dict()
        candidate_id = build_patch_plan(report).to_dict()["candidates"][0]["id"]

        branches = {
            "planned_without_assignment": {},
            "selection_error": {"selected": ["nope"]},
            "fid_range_required": {"selected": [candidate_id], "assignment_requested": True},
            "invalid_fid_range": {
                "selected": [candidate_id],
                "fid_range": {"start": 9, "end": 1},
            },
            "planned_with_assignment": {
                "selected": [candidate_id],
                "fid_range": {"start": 501, "end": 599},
                "assumption_71": "go",
            },
        }
        observed_statuses = set()
        for name, arguments in branches.items():
            payload = build_patch_plan(report, **arguments).to_dict()
            observed_statuses.add(payload["status"])
            kinds = {check["kind"] for check in payload["skipped_checks"]}
            assert DESIGNED_TYPE_NAME_VACUOUS in kinds, name
        # 갈래가 한 상태로 뭉개지면 위 순회가 공허하다.
        assert len(observed_statuses) >= 3, observed_statuses


# --------------------------------------------------------------------------
# [round18 minor] `_R17_CONTAINMENT_FAMILY` 자기충족 표 봉합
#
# round17판은 입력(`_R17_CONTAINMENT_FAMILY`)과 기대값(`matched == list(그 표)`)이 **같은
# 자유 목록**에서 나와, 행 삭제 48건 중 유일하게 SURVIVED였다. 여기서는
#   ① 각 행의 축을 **이름에서 계산**해(자유 라벨 금지) 축 하나에 행 하나를 강제하고,
#   ② 그 표와 `_R17_CONTAINMENT_FAMILY`를 **전단사**로 묶고,
#   ③ 표에서 파생되지 않은 **독립 침해 표본**(후보가 되어서는 안 되는 콘솔 이름)을 둔다.
# 어느 쪽 표에서 한 행을 지워도 ①이나 ②가 깨진다.
# --------------------------------------------------------------------------

_R18_CONTAINMENT_AXES = (
    "suffix_len_2",
    "suffix_len_3",
    "suffix_len_4",
    "suffix_repeated_letter",
)

#: 표에서 파생되지 않은 **독립 침해 표본** — 후보가 되어서는 안 되는 콘솔 이름들.
#: 하나는 무관한 제조사명, 하나는 숫자만 다른 형제(포함관계가 성립하지 않는다).
_R18_CONTAINMENT_NON_MEMBERS = ("Mac Aura XIP", "LEDBeam 25")


def _r18_containment_axis(designed: str, name: str) -> str:
    """축을 **이름에서 계산한다** — 자유 라벨이면 표가 자기충족이 된다(round18 minor)."""
    norm_designed = "".join(ch.lower() for ch in designed if ch.isalnum())
    norm_name = "".join(ch.lower() for ch in name if ch.isalnum())
    if norm_name == norm_designed:
        return "identical"
    if not norm_name.startswith(norm_designed):
        return "not_a_suffix_extension"
    suffix = norm_name[len(norm_designed) :]
    if len(set(suffix)) == 1 and len(suffix) > 1:
        return "suffix_repeated_letter"
    return f"suffix_len_{len(suffix)}"


def _r18_assert_containment_family_shape(family: tuple[str, ...]) -> None:
    """행 삭제 프로브 — 축 하나에 행 하나이므로 삭제는 축 결손으로 드러난다."""
    axes = tuple(_r18_containment_axis(_R17_CONTAINMENT_DESIGNED, name) for name in family)
    assert len(axes) == len(set(axes)), axes
    assert set(axes) == set(_R18_CONTAINMENT_AXES), sorted(axes)
    assert len(family) == len(_R18_CONTAINMENT_AXES)
    assert len(family) >= 2, family
    assert _R17_CONTAINMENT_DESIGNED not in family
    # 독립 침해 표본은 이 표에서 파생되지 않는다 — 겹치면 침해 표본이 아니다.
    assert not set(family) & set(_R18_CONTAINMENT_NON_MEMBERS)
    for outsider in _R18_CONTAINMENT_NON_MEMBERS:
        assert _r18_containment_axis(_R17_CONTAINMENT_DESIGNED, outsider) not in (
            _R18_CONTAINMENT_AXES
        ), outsider


class TestRound18ContainmentFamilyIsNotSelfSatisfying:
    """[round18 minor] round17의 자기충족 표를 축 계산 + 전단사 + 독립 침해 표본으로 봉합."""

    def test_the_containment_family_shape_detects_row_deletion(self):
        _r18_assert_containment_family_shape(_R17_CONTAINMENT_FAMILY)
        for index in range(len(_R17_CONTAINMENT_FAMILY)):
            pruned = tuple(
                name for position, name in enumerate(_R17_CONTAINMENT_FAMILY) if position != index
            )
            with pytest.raises(AssertionError):
                _r18_assert_containment_family_shape(pruned)

    def test_the_independent_violation_samples_are_never_candidates(self):
        """[round18 minor] 표에서 파생되지 않은 표본으로 **비공허성**을 세운다.

        `_type_candidates`가 라이브러리 전체를 후보로 내도록 깨지면(예: 퍼지 판정을
        무조건 True로) 이 침해 표본이 후보에 섞여 실패한다.
        """
        library = [
            (name, [(_R18_LIB_MODE, 16)])
            for name in _R17_CONTAINMENT_FAMILY + _R18_CONTAINMENT_NON_MEMBERS
        ]
        payload = resolve_fixture_types(
            [request("r18-family", instrument_type=_R17_CONTAINMENT_DESIGNED, mode=_R18_LIB_MODE)],
            library_port=LibraryRigPort(library),
            type_aliases={},
        ).to_dict()
        candidates = row_by_id(payload, "r18-family")["type_candidates"]

        assert sorted(candidates) == sorted(_R17_CONTAINMENT_FAMILY)
        for outsider in _R18_CONTAINMENT_NON_MEMBERS:
            assert outsider not in candidates, outsider
            assert fuzzy_type_equal(_R17_CONTAINMENT_DESIGNED, outsider) is False, outsider


class TestRound18ModeCandidateVacuityIsLiveNotDeadCode:
    """[round18 R18-I] `_mode_candidates`의 `_comparable_key(alias_mode)`는 `_alias_for`가
    이미 걸러 주는 값을 다시 거르는 **방어 코드**다. 그래서 상위 필터가 살아 있는 동안
    이 자리만 떼어내는 뮤테이션은 등가가 된다(round18 실측: SURVIVED).

    등가라고 방치하면 상위 필터를 나중에 옮기는 순간 조용히 되살아나는 결함이 된다 —
    그래서 이 함수를 **직접 호출**해 그 자리를 살아 있는 코드로 만든다.
    """

    def test_a_vacuous_alias_mode_argument_presents_every_mode_and_confirms_none(self):
        """[round18 R18-I] `_mode_candidates`의 `_comparable_key(alias_mode)`를
        `alias_mode`로 바꾸면 실패한다 — 공허한 모드 이름이 전 모드와 "일치"해
        후보가 좁혀지고, 모드가 하나뿐인 타입에서는 확정까지 간다.
        """
        console_type = LibraryType(
            index=1,
            name=_R18_LIB_TYPE,
            modes=(
                LibraryMode(index=1, name="Mode 1", channel_count=24),
                LibraryMode(index=2, name="Extended", channel_count=48),
            ),
            modes_available=True,
        )
        substantive = TypeRequest(candidate_id="r18", instrument_type=_R18_LIB_TYPE, mode="Mode 1")
        for vacuous in ("---", "   ", "\u00a0", "\x00\x01"):
            presented = _mode_candidates(substantive, console_type, vacuous)
            # 공허한 별칭 모드는 **저장된 확인이 아니다** — 도면 모드로 좁히지도,
            # 전 모드와 공허 일치하지도 않는다: 도면 모드가 기준이 된다.
            assert [mode.name for mode in presented] == ["Mode 1"], repr(vacuous)
        # 도면 모드까지 공허하면 좁힐 기준이 없다 — 전 모드를 제시한다.
        both_vacuous = TypeRequest(candidate_id="r18", instrument_type=_R18_LIB_TYPE, mode="---")
        assert [mode.name for mode in _mode_candidates(both_vacuous, console_type, "---")] == [
            "Mode 1",
            "Extended",
        ]

    def test_the_control_a_substantive_alias_mode_narrows_to_that_mode(self):
        """비공허성 — 정상 별칭 모드는 그 모드로 좁힌다(위 테스트가 전 모드 제시로
        뭉개져도 통과하지 않게 한다).
        """
        console_type = LibraryType(
            index=1,
            name=_R18_LIB_TYPE,
            modes=(
                LibraryMode(index=1, name="Mode 1", channel_count=24),
                LibraryMode(index=2, name="Extended", channel_count=48),
            ),
            modes_available=True,
        )
        request_ = TypeRequest(candidate_id="r18", instrument_type=_R18_LIB_TYPE, mode="Mode 1")
        assert [mode.name for mode in _mode_candidates(request_, console_type, "Extended")] == [
            "Extended"
        ]


# --- round19 고지 참·거짓 (NoticeTruth) ---
#
# [round19 major#1·#2·#3] R18-J 고지는 세 갈래로 거짓을 냈다. 셋 다 **우리 층의 문장이
# 1단계의 동작을 단정한다**는 한 기제다.
#
#   #1 거짓 귀속 — 1단계 조인이 아예 수행되지 않은 갈래에서도 "일치로 보므로 소멸했을 수
#      있다"를 붙였다. 하지 않은 일을 했다고 단정한 것이고 round18 이전에는 없던 문장이다.
#   #2 오발화 — 고지 술어는 공허 판정 하나였는데 1단계 삼킴은 `rig.fuzzy_type_equal`이
#      하고 그것은 falsy를 아무것도 삼키지 않는다. `instrument_type=""`은 양쪽에 정상
#      등장하는데 고지가 붙었다 — 흔한 거짓 양성은 게이트를 무력화한다.
#   #3 미발화 — 두 축을 묶어 말하면서 부재 축의 필터만 베껴 왔다. 1단계 수량 대조는
#      classification도 좌표도 가리지 않으므로 미패치·좌표부재 픽스처가 그 축에서 실제로
#      소멸하는데 고지는 0건이었다.
#
# 여기서 고정하는 명제는 하나다: **나가는 모든 문장이 참이어야 한다**. 그래서 정렬을
# 대조군으로 고정하고(술어 공유는 정렬을 보장하지 않았다), 축 필터를 `diff.py`에서 AST로
# 재도출하고(손으로 베끼면 또 어긋난다), 근거 없는 단정을 갈래별로 억제한다.

_R19_CONSOLE_TYPE = "LEDWash 600"
#: 콘솔에 **없는** 비공허 이름 — 정렬 대조군의 기준선이다. 콘솔 타입과 퍼지 일치하면
#: 대조군 자체가 오염되므로 아래 `test_r19_the_alignment_baseline_is_not_contaminated`가 실측한다.
_R19_CONTROL_NAME = "ZZ Absent Control Fixture"


def _r19_target_fixture(
    type_name: object, *, classification: str, coordinates: bool
) -> DesignedFixture:
    return DesignedFixture(
        unit_number="U2",
        instrument_type=type_name,  # type: ignore[arg-type]
        mode=None,
        channel=None,
        universe=1 if coordinates else None,
        address=30 if coordinates else None,
        classification=classification,
        part_indices=(),
        device_type=None,
    )


def _r19_rig(type_name: object, *, classification: str, coordinates: bool) -> DesignedRig:
    """정상 픽스처 1대 + 대상 1대 — 정상 1대가 있어야 1단계 콘솔 대조가 성립한다."""
    return _r17_rig(
        _r17_designed_fixture("U1", _R19_CONSOLE_TYPE, 1, 1),
        _r19_target_fixture(type_name, classification=classification, coordinates=coordinates),
    )


def _r19_console() -> Inventory:
    """대상 주소(1.30)에 콘솔 픽스처가 하나 있다 — 공허명 조인이 성립할 조건이다."""
    return _r17_inventory(_r17_console_record(1, "1.30", _R19_CONSOLE_TYPE))


def _r19_stage_one_axes(
    type_name: object, *, classification: str, coordinates: bool
) -> dict[str, bool]:
    """1단계 두 축의 산출에 대상 픽스처가 **남아 있는가** — `diff.compare` 실측이다."""
    result = compare(
        _r19_rig(type_name, classification=classification, coordinates=coordinates), _r19_console()
    )
    return {
        "missing_in_console": any(entry.unit_number == "U2" for entry in result.missing_in_console),
        "quantity_mismatch": any(
            entry.instrument_type == type_name for entry in result.quantity_mismatches
        ),
    }


def _r19_stage_one_swallow(
    type_name: object, *, classification: str, coordinates: bool
) -> dict[str, bool]:
    """축별 **1단계 삼킴** — 같은 자리의 비공허 대조군과의 차분으로만 판정한다.

    "축 산출에 없다"만 보면 애초에 조인되지 않은 자리(미패치·좌표부재)까지 삼킴으로
    읽힌다. 대조군을 같은 자리에 두고 차분을 보면 **이름 때문에** 사라진 것만 남는다.
    """
    actual = _r19_stage_one_axes(type_name, classification=classification, coordinates=coordinates)
    control = _r19_stage_one_axes(
        _R19_CONTROL_NAME, classification=classification, coordinates=coordinates
    )
    return {axis: control[axis] and not actual[axis] for axis in actual}


def _r19_vacuous_kinds() -> frozenset[str]:
    """고지 kind 전수를 **프로덕션에서** 가져온다 — 테스트가 사본을 들면 새 kind를 놓친다."""
    from server.vwx.patchplan import _VACUOUS_AXES, _VACUOUS_JOIN_ABSENT_KIND

    return frozenset({axis.kind for axis in _VACUOUS_AXES} | {_VACUOUS_JOIN_ABSENT_KIND})


def _r19_notices(report: dict) -> dict[str, dict]:
    from server.vwx.patchplan import build_patch_plan

    payload = build_patch_plan(report).to_dict()
    kinds = _r19_vacuous_kinds()
    return {check["kind"]: check for check in payload["skipped_checks"] if check["kind"] in kinds}


#: (라벨, 도면 타입 이름) — 공허/비공허 × truthy/falsy 축을 덮는 입력 전수.
_R19_TYPE_NAME_INPUTS = (
    ("vacuous_dashes", "---"),
    ("vacuous_dash_pair", "--"),
    ("vacuous_spaces", "   "),
    ("vacuous_dots", "..."),
    ("vacuous_ideographic_space", "\u3000"),
    ("falsy_empty", ""),
    ("substantive_absent", "Nonexistent Type"),
    ("substantive_other", "MegaPointe"),
)
#: 위 표의 각 행이 어느 부류인지를 **독립 표**로 둔다. 어느 쪽 표에서 행을 지워도
#: `test_r19_the_type_name_input_table_partitions_into_three_classes`가 어긋난다.
_R19_INPUT_CLASSES = {
    "vacuous_truthy": (
        "vacuous_dashes",
        "vacuous_dash_pair",
        "vacuous_spaces",
        "vacuous_dots",
        "vacuous_ideographic_space",
    ),
    "falsy": ("falsy_empty",),
    "substantive": ("substantive_absent", "substantive_other"),
}


def _r19_input_class(type_name: object) -> str:
    """부류를 **값에서 계산**한다 — 자유 라벨을 믿지 않는다."""
    if not type_name:
        return "falsy"
    return "vacuous_truthy" if is_vacuous_type_name(type_name) else "substantive"


def test_r19_the_type_name_input_table_partitions_into_three_classes():
    """[round19 · 행삭제 프로브] 입력 표와 부류 표가 전단사다.

    죽이는 뮤테이션: 어느 표에서 행을 지우거나 다른 부류로 옮기면 실패한다.
    """
    computed: dict[str, list[str]] = {}
    for label, type_name in _R19_TYPE_NAME_INPUTS:
        computed.setdefault(_r19_input_class(type_name), []).append(label)
    assert {key: tuple(value) for key, value in computed.items()} == {
        key: tuple(value) for key, value in _R19_INPUT_CLASSES.items()
    }
    # 어느 부류든 비면 아래 정렬 순회가 그 축에서 공허하다.
    assert all(_R19_INPUT_CLASSES.values())


def test_r19_the_alignment_baseline_is_not_contaminated():
    """[round19 major#2 · 대조군 건전성] 정렬 대조군의 전제를 실측으로 고정한다.

    ① 대조군 이름은 비공허이고 콘솔 타입과 퍼지 일치하지 않는다 — 일치하면 "대조군은
       축에 남는다"가 깨져 차분이 전부 거짓이 된다.
    ② 프로브 이름이 콘솔 타입과 1단계에서 일치로 판정되는 것은 **truthy 공허** 행뿐이다 —
       비공허 프로브가 우연히 일치하면 그 행의 삼킴 실측이 공허명 때문이 아니게 된다.
    """
    assert is_vacuous_type_name(_R19_CONTROL_NAME) is False
    assert fuzzy_type_equal(_R19_CONTROL_NAME, _R19_CONSOLE_TYPE) is False
    for label, type_name in _R19_TYPE_NAME_INPUTS:
        expected = _r19_input_class(type_name) == "vacuous_truthy"
        assert fuzzy_type_equal(type_name, _R19_CONSOLE_TYPE) is expected, label


@pytest.mark.parametrize("coordinates", (True, False), ids=["coords", "no_coords"])
@pytest.mark.parametrize("classification", ("patched", "unpatched_designed"))
@pytest.mark.parametrize(
    "label,type_name", _R19_TYPE_NAME_INPUTS, ids=[row[0] for row in _R19_TYPE_NAME_INPUTS]
)
def test_r19_the_notice_fires_exactly_when_stage_one_swallows(
    label: str, type_name: str, classification: str, coordinates: bool
):
    """[round19 major#2·#3 · 정렬 대조군] 축마다 **고지 발화 == 1단계 삼킴**이다.

    round18은 술어(`is_vacuous_type_name`)를 공유하면 정렬된다고 적었다. 그것이 틀렸다 —
    1단계 삼킴은 `rig.fuzzy_type_equal`이 하고 그것은 `if not a or not b: return False`라
    falsy를 아무것도 삼키지 않는다. 술어 공유는 정렬을 보장하지 않았으므로 정렬 **자체**를
    여기서 1단계 실측에 묶는다. 그러면 1단계 술어가 바뀌어도 잡힌다.

    죽이는 뮤테이션(전부 실측 KILLED):
      · `_vacuous_axis_targets`의 `match_type and` 결합을 지우면 `falsy_empty` 행이
        고지되는데 1단계는 삼키지 않아 실패한다.
      · `is_vacuous_type_name(...)` 호출을 지우면 비공허 행이 고지돼 실패한다.
      · 두 축의 `requires_patched`/`requires_coordinates`를 서로 바꾸면 미패치·좌표부재
        행에서 실패한다.
      · `rig.fuzzy_type_equal`의 `if not a or not b` 절을 지우면 **실측 삼킴이 뒤집혀**
        고지 없는 삼킴이 생겨 실패한다 — 1단계 술어 변조를 잡는 자리다.
    """
    from server.vwx.patchplan import _VACUOUS_AXES, _VACUOUS_JOIN_ABSENT_KIND

    swallow = _r19_stage_one_swallow(
        type_name, classification=classification, coordinates=coordinates
    )
    report = build_vwx_report(
        compare(
            _r19_rig(type_name, classification=classification, coordinates=coordinates),
            _r19_console(),
        )
    ).to_dict()
    fired = _r19_notices(report)
    for axis in _VACUOUS_AXES:
        assert (axis.kind in fired) is swallow[axis.axis_key], (
            label,
            axis.axis_key,
            swallow,
            sorted(fired),
        )
    # 조인이 수행된 리포트에서 "말할 수 없다"를 내면 그 문장이 거짓이다.
    assert _VACUOUS_JOIN_ABSENT_KIND not in fired


def test_r19_the_alignment_control_is_not_vacuous():
    """[round19] 위 순회가 **양쪽 값을 모두 관측**하는지 — 전부 False면 정렬 단정이 공허하다."""
    observed = set()
    for _, type_name in _R19_TYPE_NAME_INPUTS:
        for classification in ("patched", "unpatched_designed"):
            for coordinates in (True, False):
                swallow = _r19_stage_one_swallow(
                    type_name, classification=classification, coordinates=coordinates
                )
                observed.update(swallow.items())
    # 두 축 각각에서 삼킴 True와 False가 모두 관측돼야 한다.
    assert observed == {
        ("missing_in_console", True),
        ("missing_in_console", False),
        ("quantity_mismatch", True),
        ("quantity_mismatch", False),
    }, observed


# --------------------------------------------------------------------------
# major#3 — 축별 1단계 필터를 `diff.py`에서 **AST로 재도출**한다.
# 손으로 베낀 필터가 어긋난 것이 이번 결함이므로, 표를 손으로 쓰지 않고 코드에서 뽑는다.
# --------------------------------------------------------------------------


def _r19_loop_axis(loop: ast.For) -> str:
    """루프가 **무엇을 쓰는가**로 축을 정한다 — 주석·순서·이름에 기대지 않는다."""
    constructed = {
        node.func.id
        for node in ast.walk(loop)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    if "MissingInConsoleEntry" in constructed:
        return "missing_in_console"
    counters = {
        ast.unparse(node.targets[0].value)
        for node in ast.walk(loop)
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Subscript)
    }
    if "designed_counts" in counters:
        return "quantity_mismatch"
    raise AssertionError(f"축을 판정할 수 없는 도면 픽스처 루프: {ast.unparse(loop)[:80]!r}")


def _r19_diff_axis_filters() -> dict[str, dict[str, bool]]:
    """`diff.compare`의 축별 루프에서 필터의 **존재 여부**를 재도출한다.

    가드가 지역 이름을 경유하는 것도 따라간다 — `missing_in_console` 루프는 좌표 검사를
    `unresolved_address`에 담아 두고 `if`에서 그 이름만 쓴다. 이름만 보면 좌표 필터가
    없는 것으로 읽히고, 그 오독이 곧 이번 결함의 재발 경로다.
    """
    source = Path("server/vwx/diff.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    compare_fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "compare"
    )
    filters: dict[str, dict[str, bool]] = {}
    for loop in ast.walk(compare_fn):
        if not isinstance(loop, ast.For) or ast.unparse(loop.iter) != "designed_rig.fixtures":
            continue
        branches = [node for node in ast.walk(loop) if isinstance(node, ast.If)]
        guard_locals = {
            node.id
            for branch in branches
            for node in ast.walk(branch.test)
            if isinstance(node, ast.Name)
        }
        attributes = {
            node.attr
            for branch in branches
            for node in ast.walk(branch.test)
            if isinstance(node, ast.Attribute)
        }
        for node in ast.walk(loop):
            if isinstance(node, ast.Assign) and any(
                getattr(target, "id", None) in guard_locals for target in node.targets
            ):
                attributes |= {
                    inner.attr for inner in ast.walk(node.value) if isinstance(inner, ast.Attribute)
                }
        filters[_r19_loop_axis(loop)] = {
            "classification": "classification" in attributes,
            "coordinates": {"universe", "address"} <= attributes,
            "unguarded": not branches,
        }
    return filters


def test_r19_the_axis_table_re_derives_stage_one_filters_from_diff_py():
    """[round19 major#3] 우리 축 표의 필터가 `diff.py`에서 재도출한 것과 같다.

    죽이는 뮤테이션:
      · `_VACUOUS_AXES`에서 `requires_patched`나 `requires_coordinates`를 뒤집으면 실패한다.
      · 축 행을 지우면 축 키 집합이 어긋나 실패한다.
      · `diff.py`의 수량 루프에 `classification` 가드가 생기면(1단계 변경) 실패해 우리 표의
        재도출을 강제한다 — 그것이 이 단정의 목적이다.
    """
    from server.vwx.patchplan import _VACUOUS_AXES

    derived = _r19_diff_axis_filters()
    assert set(derived) == {axis.axis_key for axis in _VACUOUS_AXES}, derived
    for axis in _VACUOUS_AXES:
        assert axis.requires_patched == derived[axis.axis_key]["classification"], axis.axis_key
        assert axis.requires_coordinates == derived[axis.axis_key]["coordinates"], axis.axis_key
    # 두 축의 필터가 같으면 축을 나눌 이유가 증명되지 않는다 — 실측: 부재 축은 가드가 있고
    # 수량 축은 `if`가 하나도 없다.
    assert derived["missing_in_console"]["unguarded"] is False
    assert derived["quantity_mismatch"]["unguarded"] is True
    assert derived["missing_in_console"] != derived["quantity_mismatch"]


def test_r19_the_quantity_axis_notice_covers_what_the_missing_axis_filter_excluded():
    """[round19 major#3] 미패치·좌표부재 픽스처가 **수량 축에서만** 고지된다.

    round18판은 이 둘을 0건으로 셌다 — 부재 축의 필터를 수량 축에 적용했기 때문이다.

    죽이는 뮤테이션: 수량 축의 `requires_patched`/`requires_coordinates`를 `True`로
    바꾸면(즉 부재 축 필터를 다시 베끼면) 두 행 전부 실패한다.
    """
    from server.vwx.patchplan import _VACUOUS_AXES, DESIGNED_TYPE_NAME_VACUOUS

    quantity_kind = next(
        axis.kind for axis in _VACUOUS_AXES if axis.axis_key == "quantity_mismatch"
    )
    for classification, coordinates in (("unpatched_designed", True), ("patched", False)):
        swallow = _r19_stage_one_swallow(
            "---", classification=classification, coordinates=coordinates
        )
        # 전제를 가정하지 않는다 — 1단계가 수량 축에서만 삼키는 자리임을 먼저 실측한다.
        assert swallow == {"missing_in_console": False, "quantity_mismatch": True}, (
            classification,
            coordinates,
        )
        report = build_vwx_report(
            compare(
                _r19_rig("---", classification=classification, coordinates=coordinates),
                _r19_console(),
            )
        ).to_dict()
        fired = _r19_notices(report)
        assert quantity_kind in fired, (classification, coordinates)
        assert DESIGNED_TYPE_NAME_VACUOUS not in fired, (classification, coordinates)
        notice = fired[quantity_kind]
        assert notice["affected_count"] == 1
        # 좌표가 없으면 주소로 가리킬 수 없다 — 개수로 따로 싣고 없는 주소를 지어내지 않는다.
        expected_addresses = ("1.30",) if coordinates else ()
        assert tuple(notice["affected_designed_addresses"]) == expected_addresses
        assert notice["affected_without_coordinates"] == (0 if coordinates else 1)
        assert "None" not in " ".join(notice["affected_designed_addresses"])


# --------------------------------------------------------------------------
# major#1 — 1단계 조인이 수행되지 않은 갈래에서 그 동작을 단정하지 않는다.
# --------------------------------------------------------------------------


def _r19_vacuous_designed_payload() -> dict:
    """공허명 패치 픽스처 1대를 담은 `designed_rig` payload — 갈래마다 재사용한다."""
    return {
        "fixture_count": 2,
        "fixtures": [
            {
                "unit_number": "U1",
                "instrument_type": _R19_CONSOLE_TYPE,
                "gdtf_fixture": None,
                "universe": 1,
                "address": 1,
                "classification": "patched",
                "address_basis": None,
            },
            {
                "unit_number": "U2",
                "instrument_type": "---",
                "gdtf_fixture": None,
                "universe": 1,
                "address": 30,
                "classification": "patched",
                "address_basis": None,
            },
        ],
    }


def _r19_multi_system_report() -> dict:
    """멀티시스템 갈래는 **1단계 프로덕션 경로로** 만든다 — payload를 손으로 짓지 않는다."""
    from dataclasses import replace as _replace

    rig = _replace(
        _r19_rig("---", classification="patched", coordinates=True),
        observed_systems=frozenset({"A", "B"}),
    )
    return build_vwx_report(compare(rig, _r19_console())).to_dict()


def _r19_join_absent_reports() -> dict[str, dict]:
    """1단계 조인 산출이 없는 갈래 전수 — 갈래 이름은 그 갈래가 내는 **거부 코드**다."""
    from server.vwx.verdicts import (
        COMPARISON_NOT_PERFORMED,
        INVALID_REPORT_PAYLOAD,
        MULTI_SYSTEM_MAPPING_ABSENT,
    )

    not_performed = {
        "designed_rig": _r19_vacuous_designed_payload(),
        "diffs": {"performed": False, "reason": "설계상 리그에 유효한 픽스처가 0대다"},
        "skipped_checks": [],
    }
    no_diffs = {"designed_rig": _r19_vacuous_designed_payload(), "skipped_checks": []}
    return {
        COMPARISON_NOT_PERFORMED: not_performed,
        INVALID_REPORT_PAYLOAD: no_diffs,
        MULTI_SYSTEM_MAPPING_ABSENT: _r19_multi_system_report(),
    }


def _r19_rejection_codes_in_production() -> frozenset[str]:
    """`_rejection_for_report`가 낼 수 있는 코드를 **AST로 재도출**한다."""
    from server.vwx import patchplan as patchplan_module

    source = Path("server/vwx/patchplan.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_rejection_for_report"
    )
    names = {
        keyword.value.id
        for call in ast.walk(function)
        if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "PatchPlanRejection"
        for keyword in call.keywords
        if keyword.arg == "code" and isinstance(keyword.value, ast.Name)
    }
    assert names, "거부 코드를 하나도 못 뽑았다 — 스캐너가 프로덕션과 어긋났다"
    return frozenset(getattr(patchplan_module, name) for name in names)


def test_r19_the_join_absence_set_is_re_derived_from_the_rejection_branches():
    """[round19 major#1] 조인 미수행 집합이 `_rejection_for_report`의 갈래 전수와 같다.

    손으로 열거한 집합이 아니다. 조인 미수행이 **아닌** 거부 갈래가 새로 생기면 여기서
    먼저 실패해 분류를 강제한다 — 그것이 "갈래를 손으로 적으면 새 갈래에서 샌다"를 막는
    유일한 장치다(`report.VwxReport.comparison_performed`가 같은 이유로 재설계됐다).

    죽이는 뮤테이션:
      · `_JOIN_NOT_PERFORMED_REJECTIONS`에서 코드 하나를 지우면 실패한다.
      · 등재되지 않은 코드를 넣어도 실패한다.
      · 갈래 표(`_r19_join_absent_reports`)에서 행을 지우면 아래 전단사가 실패한다.
    """
    from server.vwx.patchplan import _JOIN_NOT_PERFORMED_REJECTIONS

    assert _r19_rejection_codes_in_production() == _JOIN_NOT_PERFORMED_REJECTIONS
    # 갈래 표가 그 집합과 1:1 — 갈래 하나를 빼놓고 "전수"라 쓰지 못한다.
    assert frozenset(_r19_join_absent_reports()) == _JOIN_NOT_PERFORMED_REJECTIONS


#: 1단계가 조인을 **수행했음을 단정**하는 어구 — 근거 없이 나가면 그것이 R18-A와 같은
#: 거짓 보고다. 조인 산출이 없는 갈래의 payload 어디에도 이 어구가 없어야 한다.
_R19_JOIN_PERFORMED_CLAIM_PHRASES = ("일치로 보", "소멸했을 수 있다", "삼켰")


def _r19_all_strings(value: object) -> list[str]:
    """payload에 실린 **모든 문자열**을 재귀로 모은다 — 라벨·사유·요약을 빠뜨리지 않는다."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [
            text
            for item in list(value.keys()) + list(value.values())
            for text in _r19_all_strings(item)
        ]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _r19_all_strings(item)]
    return []


@pytest.mark.parametrize("code", sorted(_r19_join_absent_reports()))
def test_r19_no_sentence_claims_a_join_that_never_happened(code: str):
    """[round19 major#1] 조인이 수행되지 않은 갈래에서 그 동작을 단정하는 문장이 **나가지 않는다**.

    round18판은 고지를 무조건 붙였고 그 문장은 "1단계 콘솔 대조는 그 이름을 모든 콘솔
    타입과 일치로 보므로 … 소멸했을 수 있다"였다. `diff.compare`의 `if not multi_system:`
    가드가 두 축 루프를 건너뛴 갈래·`diffs.performed=false`로 세 키가 생략된 갈래·`diffs`
    자체가 없는 갈래에서는 **일치로 본 적도, 소멸한 적도 없다**. 하지 않은 일을 했다고
    단정하는 것이 이 SPEC의 기준 결함(R18-A 치명)과 같은 부류다.

    정보를 지우지도 않는다 — 공허한 이름이 **있다**는 사실은 그대로 고지하고, 소멸 여부만
    "말할 수 없다"로 낸다.

    죽이는 뮤테이션:
      · `_stage_one_axis_output_present`가 항상 `True`를 돌려주게 하면(갈래별 억제 제거)
        세 갈래 전부 실패한다.
      · 거부 코드 검사(`rejection.code in _JOIN_NOT_PERFORMED_REJECTIONS`)를 지우면
        멀티시스템 갈래가 실패한다 — 그 갈래는 `diffs`에 두 축 키가 실려 있다.
      · 조인 미수행 고지를 아예 내지 않게 하면 "존재 고지"가 사라져 실패한다.
    """
    from server.vwx.patchplan import (
        _VACUOUS_AXES,
        _VACUOUS_JOIN_ABSENT_KIND,
        build_patch_plan,
    )

    report = _r19_join_absent_reports()[code]
    payload = build_patch_plan(report).to_dict()
    # 갈래를 실제로 밟았음을 먼저 고정한다 — 밟지 않으면 아래 단정이 공허하다.
    assert payload["rejection"]["code"] == code, payload["rejection"]

    fired = _r19_notices(report)
    assert sorted(fired) == [_VACUOUS_JOIN_ABSENT_KIND], sorted(fired)
    for axis in _VACUOUS_AXES:
        assert axis.kind not in fired, axis.axis_key
    # 공허명의 **존재**는 여전히 고지된다 — 사라진 정보를 만들지 않는다.
    notice = fired[_VACUOUS_JOIN_ABSENT_KIND]
    assert notice["affected_count"] == 1
    assert tuple(notice["affected_designed_addresses"]) == ("1.30",)
    assert tuple(notice["stage_one_axes"]) == tuple(axis.axis_key for axis in _VACUOUS_AXES)
    # payload 어디에도 조인 수행을 단정하는 어구가 없다 — 라벨·사유·요약 전부 본다.
    offenders = [
        (phrase, text)
        for text in _r19_all_strings(payload)
        for phrase in _R19_JOIN_PERFORMED_CLAIM_PHRASES
        if phrase in text
    ]
    assert offenders == [], offenders


def test_r19_the_join_performed_claim_gate_is_not_vacuous():
    """[round19] 위 단정의 비공허성 — 조인이 수행된 갈래에서는 그 어구가 **실제로 나온다**.

    나오지 않으면 위 테스트는 아무것도 지키지 않는다.
    """
    from server.vwx.patchplan import build_patch_plan

    report = build_vwx_report(
        compare(_r19_rig("---", classification="patched", coordinates=True), _r19_console())
    ).to_dict()
    texts = _r19_all_strings(build_patch_plan(report).to_dict())
    for phrase in _R19_JOIN_PERFORMED_CLAIM_PHRASES:
        assert any(phrase in text for text in texts), phrase


#: 어구 → 그 어구를 품는 **프로덕션 표면** 전수. 위 어구 표와 이 표는 서로의 행삭제
#: 프로브다 — 한쪽에서 행을 지우면 아래 전단사가 어긋난다. 어구를 손으로만 적어 두면
#: 어구 하나를 지워도 아무도 실패하지 않고, 그러면 억제 단정이 조용히 좁아진다.
_R19_CLAIM_PHRASE_SURFACES = {
    "일치로 보": ("missing_in_console:reason", "quantity_mismatch:reason"),
    "소멸했을 수 있다": ("missing_in_console:reason", "quantity_mismatch:reason"),
    "삼켰": ("missing_in_console:label", "quantity_mismatch:label"),
}


def _r19_claim_phrase_surfaces() -> dict[str, tuple[str, ...]]:
    """각 어구가 실제로 어느 축 고지의 어느 칸에 있는지 **프로덕션에서** 뽑는다."""
    from server.vwx.patchplan import _VACUOUS_AXES
    from server.vwx.verdicts import skipped_check_label

    found: dict[str, tuple[str, ...]] = {}
    for phrase in _R19_JOIN_PERFORMED_CLAIM_PHRASES:
        surfaces = tuple(
            f"{axis.axis_key}:{field}"
            for axis in _VACUOUS_AXES
            for field, text in (("reason", axis.reason), ("label", skipped_check_label(axis.kind)))
            if phrase in text
        )
        if surfaces:
            found[phrase] = surfaces
    return found


def test_r19_every_claim_phrase_is_anchored_to_a_production_surface():
    """[round19 · 행삭제 프로브] 억제 어구 표가 프로덕션 표면과 전단사다.

    죽이는 뮤테이션:
      · `_R19_JOIN_PERFORMED_CLAIM_PHRASES`에서 어구를 지우면 계산 결과에서 그 키가 사라져
        실패한다 — 억제 단정이 조용히 좁아지는 것을 여기서 막는다.
      · `_R19_CLAIM_PHRASE_SURFACES`에서 행을 지워도 실패한다.
      · 축 고지 문장에서 그 어구를 빼면(예: "소멸했을 수 있다"를 지우면) 표면이 줄어 실패한다.
    """
    computed = _r19_claim_phrase_surfaces()
    assert computed == {key: tuple(value) for key, value in _R19_CLAIM_PHRASE_SURFACES.items()}
    # 어구 표에 프로덕션 어디에도 없는 어구가 있으면 그 어구는 아무것도 막지 못한다.
    assert set(computed) == set(_R19_JOIN_PERFORMED_CLAIM_PHRASES)


def test_r19_a_missing_axis_key_alone_splits_the_two_notices():
    """[round19 major#1 · 축 단위 근거] 축 산출은 **축마다** 있거나 없다.

    한 축의 배열만 리포트에서 빠지면 그 축은 "말할 수 없다"로, 남은 축은 그대로 단정한다.
    갈래(거부 코드) 단위로만 억제하면 이 자리를 놓친다.

    죽이는 뮤테이션: `_stage_one_axis_output_present`에서 `diffs.get(axis_key)` 검사를
    지우면(거부 코드만 보면) 두 행 전부 실패한다.
    """
    from server.vwx.patchplan import _VACUOUS_AXES, _VACUOUS_JOIN_ABSENT_KIND

    base = build_vwx_report(
        compare(_r19_rig("---", classification="patched", coordinates=True), _r19_console())
    ).to_dict()
    for dropped in (axis.axis_key for axis in _VACUOUS_AXES):
        report = deepcopy(base)
        del report["diffs"][dropped]
        fired = _r19_notices(report)
        assert _VACUOUS_JOIN_ABSENT_KIND in fired, dropped
        assert tuple(fired[_VACUOUS_JOIN_ABSENT_KIND]["stage_one_axes"]) == (dropped,)
        survivors = [axis.kind for axis in _VACUOUS_AXES if axis.axis_key != dropped]
        for kind in survivors:
            assert kind in fired, (dropped, kind)
        dropped_kind = next(axis.kind for axis in _VACUOUS_AXES if axis.axis_key == dropped)
        assert dropped_kind not in fired, dropped


#: (라벨, 리포트 변형자) — 1단계가 "조인을 수행하지 않았다"고 **선언했는데도** 축 배열이
#: 리포트에 남아 있는 payload 형태 전수. 축 키만 보는 판정은 이 형태에서 반드시 샌다.
_R19_DECLARED_SKIP_WITH_LEFTOVER_ARRAYS = (
    ("multi_system_skipped_check", MULTI_SYSTEM_MAPPING_ABSENT),
    ("performed_false_flag", COMPARISON_NOT_PERFORMED),
)

#: 축 배열을 남긴 채 미수행을 선언할 **수 없는** 갈래 — `diffs` 객체 자체가 없어 남길
#: 배열이 없다. 위 표와 이 집합의 합이 조인 미수행 갈래 전수여야 한다.
_R19_NO_LEFTOVER_ARRAYS_POSSIBLE = frozenset({INVALID_REPORT_PAYLOAD})


def test_r19_the_leftover_array_table_covers_every_join_absent_branch():
    """[round19 major#1 · 행삭제 프로브] 잔여 배열 표와 "남길 수 없는 갈래"의 합이 전수다.

    죽이는 뮤테이션:
      · `_R19_DECLARED_SKIP_WITH_LEFTOVER_ARRAYS`에서 행을 지우면 합집합이 모자라 실패한다.
      · `_R19_NO_LEFTOVER_ARRAYS_POSSIBLE`에서 코드를 빼도 실패한다.
      · 조인 미수행 갈래가 새로 생기면 어느 쪽에 속하는지 판정하기 전까지 실패한다.
    """
    from server.vwx.patchplan import _JOIN_NOT_PERFORMED_REJECTIONS

    covered = {code for _, code in _R19_DECLARED_SKIP_WITH_LEFTOVER_ARRAYS}
    assert covered.isdisjoint(_R19_NO_LEFTOVER_ARRAYS_POSSIBLE)
    assert covered | _R19_NO_LEFTOVER_ARRAYS_POSSIBLE == _JOIN_NOT_PERFORMED_REJECTIONS
    # "남길 수 없다"는 판정을 실측으로 고정한다 — 그 갈래의 리포트에는 `diffs`가 없다.
    for code in _R19_NO_LEFTOVER_ARRAYS_POSSIBLE:
        assert "diffs" not in _r19_join_absent_reports()[code], code


def _r19_declared_skip_report(label: str) -> dict:
    """조인 산출이 남아 있는 상태로 1단계가 미수행을 선언한 리포트를 만든다."""
    report = build_vwx_report(
        compare(_r19_rig("---", classification="patched", coordinates=True), _r19_console())
    ).to_dict()
    # 전제 — 두 축 배열이 실려 있다. 실려 있지 않으면 이 프로브가 겨누는 자리가 없다.
    assert "missing_in_console" in report["diffs"]
    assert "quantity_mismatch" in report["diffs"]
    if label == "multi_system_skipped_check":
        report["skipped_checks"] = [
            *report["skipped_checks"],
            {
                "kind": MULTI_SYSTEM_MAPPING_ABSENT,
                "reason": "System A B 관측 — 매핑이 없어 콘솔 대조를 수행하지 않았다.",
            },
        ]
    else:
        report["diffs"]["performed"] = False
        report["diffs"]["reason"] = "설계상 리그에 유효한 픽스처가 0대다"
    return report


@pytest.mark.parametrize(
    "label,code",
    _R19_DECLARED_SKIP_WITH_LEFTOVER_ARRAYS,
    ids=[row[0] for row in _R19_DECLARED_SKIP_WITH_LEFTOVER_ARRAYS],
)
def test_r19_stage_one_s_own_declaration_outranks_leftover_axis_arrays(label: str, code: str):
    """[round19 major#1] 1단계가 미수행을 **선언**하면 남아 있는 축 배열은 산출이 아니다.

    `_rejection_for_report`는 `skipped_checks`의 멀티시스템 고지를 `diffs`보다 **먼저** 보고,
    `performed=false`도 축 배열 유무와 무관하게 거부다. 그 갈래에서 남은 배열을 근거로
    삼으면 같은 payload 안에서 두 문장이 모순된다: 거부 사유는 "조인하지 않았다"인데 고지는
    "조인이 그 이름을 일치로 봤다"가 된다. 모순된 두 문장 중 하나는 반드시 거짓이다.

    죽이는 뮤테이션(round19 실측으로 이 자리가 SURVIVED였다 — 그래서 이 대조군이 있다):
      · `_stage_one_axis_output_present`에서 거부 코드 검사를 지우고 축 키 검사만 남기면
        두 행 전부 실패한다. 실물 1단계는 미수행이면 세 키를 생략하므로 축 키 검사만으로도
        대개 막히지만, **1단계 선언을 무시해도 되는 이유는 되지 못한다** — payload 생산자가
        키를 남기는 순간 우리 문장이 거짓이 된다.
    """
    from server.vwx.patchplan import (
        _VACUOUS_AXES,
        _VACUOUS_JOIN_ABSENT_KIND,
        build_patch_plan,
    )

    report = _r19_declared_skip_report(label)
    payload = build_patch_plan(report).to_dict()
    assert payload["rejection"]["code"] == code, payload["rejection"]

    fired = _r19_notices(report)
    assert sorted(fired) == [_VACUOUS_JOIN_ABSENT_KIND], sorted(fired)
    for axis in _VACUOUS_AXES:
        assert axis.kind not in fired, axis.axis_key
    offenders = [
        (phrase, text)
        for text in _r19_all_strings(payload)
        for phrase in _R19_JOIN_PERFORMED_CLAIM_PHRASES
        if phrase in text
    ]
    assert offenders == [], offenders


def test_r19_every_notice_is_internally_consistent_and_registered():
    """[round19] 고지 payload의 불변식 — 개수와 주소 목록이 조용히 갈라지지 않는다.

    죽이는 뮤테이션: `affected_without_coordinates`를 `0` 고정으로 바꾸면 좌표부재 행에서
    실패한다 — 그러면 조작자는 주소 목록을 전수로 읽는다.
    """
    from server.vwx.patchplan import _VACUOUS_AXES, sentence_shape_violation
    from server.vwx.verdicts import skipped_check_label

    collected: list[dict] = []
    for classification in ("patched", "unpatched_designed"):
        for coordinates in (True, False):
            report = build_vwx_report(
                compare(
                    _r19_rig("---", classification=classification, coordinates=coordinates),
                    _r19_console(),
                )
            ).to_dict()
            collected.extend(_r19_notices(report).values())
    for code in _r19_join_absent_reports():
        collected.extend(_r19_notices(_r19_join_absent_reports()[code]).values())
    assert collected, "고지를 하나도 모으지 못했다 — 아래 단정이 공허하다"

    axis_kinds = {axis.kind: axis.axis_key for axis in _VACUOUS_AXES}
    for notice in collected:
        assert notice["label"] == skipped_check_label(notice["kind"]), notice["kind"]
        assert sentence_shape_violation(notice["reason"]) is None, notice["reason"]
        assert (
            len(notice["affected_designed_addresses"]) + notice["affected_without_coordinates"]
            == notice["affected_count"]
        ), notice
        assert notice["stage_one_axes"], notice["kind"]
        if notice["kind"] in axis_kinds:
            assert tuple(notice["stage_one_axes"]) == (axis_kinds[notice["kind"]],)


# --------------------------------------------------------------------------
# [HARD] 형제 표면 전수 — "우리 층의 문장이 1단계·콘솔의 동작을 서술한다"는 자리 전부.
#
# 이번 세 건은 전부 이 한 기제다. 그래서 `server/vwx/` 전 모듈에서 그런 문장을 AST로
# 전수하고, 각각이 **그 서술이 참임을 보장하는 근거**를 갖는지 판정해 등기부로 고정한다.
# 등기부는 프로덕션과 전단사이므로 새 문장은 판정 없이 통과하지 못하고, 행을 지워도 깨진다.
# --------------------------------------------------------------------------

#: 문장이 1단계·콘솔의 **동작·상태**를 서술한다고 볼 표지. 단순 언급(예: "콘솔에서 사람이
#: 지워야 한다")은 동작 서술이 아니므로 표지에 넣지 않는다 — 흔한 거짓 양성은 게이트를
#: 무력화한다(§0 2b④).
_R19_CLAIM_MARKERS = (
    "1단계",
    "콘솔 대조",
    "콘솔 실측",
    "콘솔 부재 판정",
    "콘솔 조인",
    "일치로 보",
    "삼켰",
    "재계산",
    "이미 점유",
    "판정 재사용",
    "콘솔 라이브러리에",
    "콘솔에서 확인된",
)
#: 근거 부류 **전수**. 자유 문자열이 이 자리에 들어오면 판정이 아니라 낙서가 된다.
_R19_CLAIM_BASIS_KINDS = frozenset(
    {
        # 1단계 모듈이 **자기 행위**를 적는다 — 그 코드가 곧 그 행위이므로 자기충족이다.
        "stage_one_states_its_own_act",
        # 1단계가 "수행하지 않았다"고 선언한 것을 우리 층이 받아 적는다(기본 문구 포함).
        "stage_one_declared_the_skip",
        # 우리 층의 단정이지만 **그 축의 1단계 산출이 있을 때만** 나간다.
        "gated_on_stage_one_axis_output",
        # 산출의 **부재**만 말한다 — 1단계가 무엇을 했는지 단정하지 않는다.
        "asserts_only_absence_of_output",
        # 콘솔 관측이 그 코드 경로의 **입력**이다 — 남의 판정을 대신 말하지 않는다.
        "console_observation_is_the_input",
    }
)


def _r19_claim_skeleton(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value if isinstance(part, ast.Constant) else "{}" for part in node.values
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _r19_claim_skeleton(node.left)
        right = _r19_claim_skeleton(node.right)
        return None if left is None or right is None else left + right
    return None


def _r19_docstring_ids(tree: ast.AST) -> set[int]:
    """독스트링은 조작자에게 나가지 않는다 — 개발자용 서술은 스코프 밖이다."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def _r19_claim_sites() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """`server/vwx` 전 모듈에서 1단계·콘솔의 동작을 서술하는 **운영 문자열 전수**를
    (모듈, 표지)로 낸다 — 읽는 스코프는 `server/vwx/*.py` 글롭이고 그 밖은 읽지 않는다.

    키에 변수·키워드 **이름을 넣지 않는다**. 같은 문장을 인라인 리터럴로 두든 모듈 상수로
    빼든 그것은 리팩터링이고, 리팩터링이 판정 등기부를 깨면 등기부는 판정이 아니라 이름
    사본이 된다. 판정의 단위는 **어떤 주장을 하는가**(표지)이고 키가 그것이다. 같은 모듈에서
    두 문장이 같은 표지로 뭉치면 아래 전수 단정이 그 자리를 드러낸다.

    네 형태를 본다: dict 값 · 호출 키워드 · 호출 위치인자 · 이름 대입. 위치인자를 빼면
    `_string_or_default(...)`의 기본 문구가 스캔 밖으로 새고, 그 문구도 1단계의 행위를
    말한다 — 스코프가 형태 경계에서 멈추는 것이 round17이 명명한 결함이다.
    """
    modules = iter_vwx_modules()
    assert modules, "스캔 대상이 0개면 이 전수는 공허하다"
    sites: set[tuple[str, tuple[str, ...]]] = set()
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = _r19_docstring_ids(tree)
        for node in ast.walk(tree):
            pairs: list[tuple[str | None, ast.AST]] = []
            if isinstance(node, ast.Dict):
                pairs = [
                    (key.value, value)
                    for key, value in zip(node.keys, node.values, strict=True)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                ]
            elif isinstance(node, ast.Call):
                callee = (
                    getattr(node.func, "id", None) or getattr(node.func, "attr", None) or "call"
                )
                pairs = [(keyword.arg, keyword.value) for keyword in node.keywords if keyword.arg]
                pairs += [
                    (f"{callee}#{index}", argument) for index, argument in enumerate(node.args)
                ]
            elif isinstance(node, ast.Assign):
                pairs = [
                    (getattr(target, "id", None) or getattr(target, "attr", None), node.value)
                    for target in node.targets
                ]
            for name, value in pairs:
                if name is None or id(value) in skip:
                    continue
                text = _r19_claim_skeleton(value)
                if text is None or " " not in text:
                    continue
                markers = tuple(marker for marker in _R19_CLAIM_MARKERS if marker in text)
                if markers:
                    sites.add((vwx_module_label(path), markers))
    return tuple(sorted(sites))


#: (모듈, 표지) → 그 서술이 참임을 보장하는 **근거 부류**. 손으로 판정하고
#: 아래 전단사가 프로덕션 스캔과 맞춘다.
_R19_CLAIM_BASIS = {
    ("diff.py", ("콘솔 대조",)): "stage_one_states_its_own_act",
    ("diff.py", ("콘솔 실측",)): "stage_one_states_its_own_act",
    # [round24 후속] 인테이크의 두 문장. 라이브러리 목록은 호출자가 넘기는 **입력**이고,
    # 조인 키 문장은 그 칸의 쓰임을 적을 뿐 1단계가 무엇을 했는지 단정하지 않는다.
    ("intake.py", ("콘솔 라이브러리에",)): "console_observation_is_the_input",
    ("intake.py", ("콘솔 조인",)): "asserts_only_absence_of_output",
    ("patchplan.py", ("1단계",)): "stage_one_declared_the_skip",
    ("patchplan.py", ("1단계", "일치로 보", "재계산")): "gated_on_stage_one_axis_output",
    ("patchplan.py", ("1단계", "콘솔 대조")): "stage_one_declared_the_skip",
    ("patchplan.py", ("1단계", "콘솔 부재 판정", "일치로 보", "재계산")): (
        "gated_on_stage_one_axis_output"
    ),
    ("patchplan.py", ("1단계", "콘솔 조인")): "asserts_only_absence_of_output",
    ("patchplan.py", ("이미 점유",)): "console_observation_is_the_input",
    ("patchplan.py", ("콘솔 대조",)): "stage_one_declared_the_skip",
    ("report.py", ("콘솔 실측",)): "stage_one_states_its_own_act",
    ("report.py", ("콘솔 실측", "판정 재사용")): "stage_one_states_its_own_act",
    ("typemap.py", ("콘솔 라이브러리에",)): "console_observation_is_the_input",
    ("typemap.py", ("콘솔에서 확인된",)): "console_observation_is_the_input",
}


def test_r19_the_stage_one_claim_registry_is_a_bijection_onto_production():
    """[round19 HARD · 형제 표면 전수] 등기부가 `server/vwx/` 전 모듈 스캔과 1:1이다.

    죽이는 뮤테이션:
      · 새 문장이 1단계·콘솔의 동작을 서술하면 등기 전까지 실패한다.
      · 등기부에서 행을 지우면 실패한다(아래 행삭제 프로브가 전 행 확인).
      · 스캔에서 위치인자 형태를 빼면 `_string_or_default(...)` 기본 문구 두 행이 사라져
        실패한다 — 스코프가 형태 경계에서 멈추는 것이 round17이 명명한 결함이다.
    """
    produced = _r19_claim_sites()
    assert produced == tuple(sorted(_R19_CLAIM_BASIS)), (
        "1단계·콘솔 동작 서술이 등기부와 다르다 — 등록할 행:\n"
        + "\n".join(f"    {row}: ???," for row in produced)
    )


@pytest.mark.parametrize("index", range(len(_R19_CLAIM_BASIS)))
def test_r19_deleting_any_claim_registry_row_breaks_the_bijection(index: int):
    """행삭제 프로브 — 등기부에서 어느 행을 지워도 프로덕션 스캔과 어긋난다."""
    rows = tuple(sorted(_R19_CLAIM_BASIS))
    shrunk = rows[:index] + rows[index + 1 :]
    assert shrunk != _r19_claim_sites()


def test_r19_every_claim_has_a_registered_basis_and_no_basis_is_dead():
    """[round19 HARD] 근거 부류가 닫힌 어휘이고, 어느 부류도 빈 채로 남지 않는다.

    빈 부류는 판정처럼 보이는 장식이다 — 쓰이지 않는 부류를 남기면 다음 라운드에 아무
    문장이나 그 부류로 밀어 넣게 된다.
    """
    assert set(_R19_CLAIM_BASIS.values()) == _R19_CLAIM_BASIS_KINDS
    for row, basis in _R19_CLAIM_BASIS.items():
        assert basis in _R19_CLAIM_BASIS_KINDS, row


def test_r19_the_gated_basis_rows_are_the_ones_the_branch_gate_actually_suppresses():
    """[round19 HARD] `gated_on_stage_one_axis_output` 판정이 **행동으로** 참이다.

    등기부가 "이 문장은 축 산출이 있을 때만 나간다"고 적었으므로, 축 산출이 없는 갈래에서
    그 문장이 실제로 나가지 않아야 한다. 판정을 글로만 적고 확인하지 않는 것이 R18-B가
    명명한 무대조군 표다.

    죽이는 뮤테이션: 등기부에서 어느 행의 부류를 `gated_on_stage_one_axis_output`으로
    바꾸면(예: `asserts_only_absence_of_output` 행) 그 문장이 조인 미수행 갈래에서 나오므로
    실패한다.
    """
    from server.vwx.patchplan import _VACUOUS_AXES, build_patch_plan

    gated = {
        row for row, basis in _R19_CLAIM_BASIS.items() if basis == "gated_on_stage_one_axis_output"
    }
    assert gated, "게이트 부류가 비면 이 단정이 공허하다"
    # 등기된 게이트 행은 축 고지 문장이다 — 축 수와 같아야 한다.
    assert len(gated) == len(_VACUOUS_AXES)
    gated_markers = {marker for _, markers in gated for marker in markers}
    for code, report in _r19_join_absent_reports().items():
        texts = _r19_all_strings(build_patch_plan(report).to_dict())
        for marker in gated_markers & {"일치로 보", "삼켰", "콘솔 부재 판정"}:
            assert not any(marker in text for text in texts), (code, marker)


# ==========================================================================
# --- round19 막다른 길 어휘 (DeadEndVocab) ---
#
# [round19 major#5] `typemap._resolve_one`의 점유폭 불일치 갈래는 **R18-E와 동형인 막다른
# 길**이었다. 도달 조건이 "별칭에 모드가 지정돼 있다"이고 `_mode_candidates`가 그 `alias_mode`로
# 후보를 걸러내므로 `mode_candidates`에는 실패한 그 모드 하나만 남는데, 문장은 "모드를 다시
# 확인해야 한다"고 말했다. 조작자 화면에는 고를 것이 없거나(모드가 하나뿐 · 전부 불일치),
# 맞는 모드가 실제로 있어도 payload가 그것을 보여주지 않았다. 실제 조치가 "도면 DMX Footprint를
# 고쳐라"인 경우에도 문장은 모드 확인을 가리켜 **거짓 안내**였다.
#
# 처방은 **탈출구를 드러내는 쪽**이다:
#   ① 라이브러리의 전 모드를 채널 수와 함께 노출한다(`mode_options`).
#   ② 맞는 모드가 하나도 없으면(전 모드 실측 · 절단 없음) 하드 스톱이고, 사유는 도면 점유폭을
#      가리킨다. ③ 부재를 단정할 수 없으면 확인 대기라 부르지 않는다 — 관측 불완전이다.
#   ④ **확인 대기를 말하는 모든 갈래**에 "조작자가 실제로 고를 수 있는 선택지가 payload에
#      있는가"를 단정하는 게이트를 건다. 갈래 목록은 `server/vwx/typemap.py` 소스에서
#      기계적으로 뽑으므로 새 갈래가 생기면 등기 없이는 통과하지 못한다(열거 금지).
# ==========================================================================

from server.vwx.typemap import (  # noqa: E402
    FOOTPRINT_MISMATCH_CHOOSABLE_REASON,
    FOOTPRINT_MISMATCH_UNVERIFIED_REASON,
    FOOTPRINT_UNMATCHABLE_REASON,
)
from server.vwx.verdicts import (  # noqa: E402
    DESIGNED_FOOTPRINT_MATCHES_NO_MODE,
    TYPE_FOOTPRINT_UNMATCHABLE,
)

_R19_TYPE = "MegaPointe"
_R19_MODE_A = "Mode 1"
_R19_MODE_B = "Mode 2"
#: Mode 1 = 24채널 · Mode 2 = 16채널. 두 모드의 채널 수가 달라야 "맞는 모드"가 의미를 가진다.
_R19_LIBRARY = [(_R19_TYPE, [(_R19_MODE_A, 24), (_R19_MODE_B, 16)])]
_R19_SOLO_LIBRARY = [(_R19_TYPE, [(_R19_MODE_A, 24)])]


def _r19_alias(mode: str = _R19_MODE_A) -> dict:
    return {_R19_TYPE: {"type": _R19_TYPE, "mode": mode}}


class _R19PartialChannelPort(LibraryRigPort):
    """모드 하나만 채널 수를 못 읽는 포트 — 맞는 모드의 **부재를 단정할 수 없는** 상태."""

    def _channels(self, type_index: int, mode_index: int, path: str) -> dict:
        if mode_index == 2:
            return {"ok": False, "path": path, "error": "path segment not found"}
        return super()._channels(type_index, mode_index, path)


def _r19_resolve_footprint(
    *,
    library=None,
    footprint: int | None = 16,
    mode: str = _R19_MODE_A,
    aliases=None,
    assumption_72: str = "go",
    port_class=LibraryRigPort,
    **port_kwargs,
) -> dict:
    port = port_class(library if library is not None else _R19_LIBRARY, **port_kwargs)
    return resolve_fixture_types(
        [request("c1", instrument_type=_R19_TYPE, mode=mode, footprint=footprint)],
        library_port=port,
        type_aliases=_r19_alias() if aliases is None else aliases,
        assumption_72=assumption_72,
    ).to_dict()


#: 점유폭 대조가 **수행된** 뒤의 갈래 전수. (이름, 시나리오 kwargs, 기대 판정, 기대 하드스톱,
#: 노출돼야 하는 모드 채널 수, 확인 대기인가).
_R19_FOOTPRINT_BRANCHES = (
    ("matching_mode_exists", {"footprint": 16}, TYPE_NEEDS_CONFIRMATION, (), (24, 16), True),
    (
        "no_mode_matches",
        {"footprint": 99},
        "designed_footprint_unmatchable",
        ("designed_footprint_matches_no_console_mode",),
        (24, 16),
        False,
    ),
    (
        "sole_mode_does_not_match",
        {"footprint": 99, "library": _R19_SOLO_LIBRARY},
        "designed_footprint_unmatchable",
        ("designed_footprint_matches_no_console_mode",),
        (24,),
        False,
    ),
    (
        "absence_not_assertable_truncated",
        {"footprint": 99, "modes_truncated": True},
        TYPE_LIBRARY_INCOMPLETE,
        (),
        (24, 16),
        False,
    ),
    (
        "absence_not_assertable_unread",
        {"footprint": 99, "port_class": _R19PartialChannelPort},
        TYPE_LIBRARY_INCOMPLETE,
        (),
        (24, None),
        False,
    ),
    ("footprint_matches", {"footprint": 24}, TYPE_RESOLVED, (), (24,), False),
)


def _r19_assert_footprint_table_shape(rows) -> None:
    """행 삭제 프로브 — 네 판정(확인 대기 · 하드 스톱 · 관측 불완전 · 확정)이 모두 있어야 한다."""
    names = tuple(row[0] for row in rows)
    assert len(names) == len(set(names)), names
    assert len(rows) == len(_R19_FOOTPRINT_BRANCHES)
    assert len({row[2] for row in rows}) == 4, names
    assert {row[5] for row in rows} == {False, True}
    # 하드 스톱 갈래가 둘이다(모드 여럿 전부 불일치 · 모드 하나뿐) — 하나만 남으면 표가 얇아진다.
    assert len([row for row in rows if row[3]]) == 2, names


def test_r19_the_footprint_branch_table_detects_row_deletion():
    _r19_assert_footprint_table_shape(_R19_FOOTPRINT_BRANCHES)
    for index in range(len(_R19_FOOTPRINT_BRANCHES)):
        pruned = tuple(
            row for position, row in enumerate(_R19_FOOTPRINT_BRANCHES) if position != index
        )
        with pytest.raises(AssertionError):
            _r19_assert_footprint_table_shape(pruned)


@pytest.mark.parametrize(
    "name,kwargs,status,stops,channel_counts,pending",
    _R19_FOOTPRINT_BRANCHES,
    ids=[row[0] for row in _R19_FOOTPRINT_BRANCHES],
)
def test_r19_every_footprint_branch_exposes_what_the_operator_can_choose(
    name, kwargs, status, stops, channel_counts, pending
):
    """[round19 major#5] 점유폭 갈래마다 판정 · 하드스톱 · **노출된 모드와 채널 수**를 고정한다.

    죽이는 뮤테이션:
      · `typemap`의 `mode_candidates=library_modes`를 `mode_candidates`(별칭으로 좁힌 한 건)로
        되돌리면 `matching_mode_exists`·`no_mode_matches` 행의 노출 채널 수가 어긋난다
        (= 모드 노출 제거).
      · `absence_assertable` 갈래를 지워 항상 하드 스톱을 내면 절단·미판독 두 행이 실패한다
        (= 찾아보지 않은 것을 부재로 단정).
      · `hard_stop_code=DESIGNED_FOOTPRINT_MATCHES_NO_MODE`를 지우면 하드 스톱 두 행이 실패한다
        (= 불일치 전수에서 하드스톱 미생성).
      · `row()`의 `mode_options`를 지우면 전 행이 KeyError로 실패한다.
    """
    payload = _r19_resolve_footprint(**kwargs)
    row = row_by_id(payload, "c1")
    assert row["status"] == status, name
    assert tuple(hard_stop_codes(payload)) == stops, name
    options = row["mode_options"]
    assert tuple(option["channel_count"] for option in options) == channel_counts, name
    # 이름 목록과 **같은 원소**여야 한다 — 한쪽만 늘면 조작자가 보는 두 목록이 갈린다.
    assert [option["name"] for option in options] == row["mode_candidates"], name
    assert row["confirmation_required"] is pending, name


def test_r19_the_hard_stop_reason_points_at_the_drawing_not_at_the_mode_choice():
    """[round19 major#5] 벗어날 수 없는 갈래의 사유가 **실제 조치**를 가리킨다.

    "모드를 다시 확인하라"가 거짓이었던 이유가 그것이다 — 고를 모드가 없는데 모드 확인을
    시켰다. 사유를 `FOOTPRINT_MISMATCH_CHOOSABLE_REASON`으로 되돌리면 실패한다.
    """
    payload = _r19_resolve_footprint(footprint=99)
    reason = row_by_id(payload, "c1")["reason"]
    assert reason == FOOTPRINT_UNMATCHABLE_REASON
    assert "도면의 DMX Footprint" in reason
    assert "승인 전에 모드를 다시" not in reason
    # 하드 스톱 사유가 전달물 배제 사유로도 그대로 나간다(형제 표면 일치).
    assert payload["hard_stops"][0]["reason"] == reason


def test_r19_a_descoped_footprint_check_never_reaches_the_mismatch_branch():
    """[round19 major#5 · 주의사항] `assumption_72`가 `go`가 아니면 대조 자체가 없다.

    미수행을 불일치와 **같은 문장으로 다루면** #1과 같은 유형의 거짓이 된다. 여기서는 그
    갈래에 애초에 도달하지 않음을 실측으로 고정한다 — 도달하게 만드는 뮤테이션
    (`_footprint_check`의 `if not footprint_enabled` 조기 반환 제거)에서 실패한다.
    """
    for branch in ("negative", "inconclusive"):
        payload = _r19_resolve_footprint(footprint=99, assumption_72=branch)
        row = row_by_id(payload, "c1")
        assert row["footprint_check"]["match"] is None, branch
        assert row["footprint_check"]["performed"] is False, branch
        assert row["status"] == TYPE_RESOLVED, branch
        assert hard_stop_codes(payload) == [], branch
        assert row["reason"] != FOOTPRINT_UNMATCHABLE_REASON, branch
        assert row["reason"] != FOOTPRINT_MISMATCH_CHOOSABLE_REASON, branch
        assert row["reason"] != FOOTPRINT_MISMATCH_UNVERIFIED_REASON, branch


# ---- ④ "확인 대기"를 말하는 갈래 전수 게이트 (열거 금지) -------------------
#
# `VacuityAndData`가 round18에 세운 확인 경로 게이트는 **공허성 6축만 등기**했다 —
# 점유폭 갈래는 그 표 밖에 있어서 덮이지 않았다. 여기서는 표를 손으로 늘리는 대신
# **`server/vwx/typemap.py` 소스에서 확인 대기 갈래를 기계적으로 뽑는다.** 갈래가 새로
# 생기면 등기 없이는 통과하지 못하고, 등기하면 곧바로 "고를 수 있는 것이 payload에 있는가"를
# 실행으로 확인받는다.

_R19_TYPEMAP_SOURCE = Path("server/vwx/typemap.py").read_text(encoding="utf-8")


def _r19_status_reason_pairs(call: ast.Call):
    """`TypeResolution(...)` 한 자리의 (status 식, reason 식) 짝. 조건식은 가지끼리 짝짓는다."""
    keywords = {keyword.arg: keyword.value for keyword in call.keywords}
    status = keywords.get("status")
    reason = keywords.get("reason")
    if status is None or reason is None:
        return ()
    if isinstance(status, ast.IfExp):
        branches = (status.body, status.orelse)
        reasons = (
            (reason.body, reason.orelse) if isinstance(reason, ast.IfExp) else (reason, reason)
        )
        return tuple(zip(branches, reasons, strict=True))
    return ((status, reason),)


def _r19_typeresolution_calls():
    tree = ast.parse(_R19_TYPEMAP_SOURCE)
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "TypeResolution"
    ]


#: 사유를 **모듈 상수로 환원해 돌려주는** 헬퍼. 갈래마다 리터럴을 박는 것과 달리 전수를
#: 방해하지 않는다 — 아래 게이트가 이 헬퍼의 반환이 전부 모듈 상수 이름임을 직접 확인한다.
#: [round25 R24-1] 점유폭 미검증 갈래의 사유가 **막은 축에 따라 셋으로** 갈렸다. 갈래를
#: `_resolve_one` 안에 펼치는 대신 환원 헬퍼로 둔 이유는 이 등기다: 헬퍼 안이라야 반환이
#: 전부 모듈 상수임을 게이트가 강제하고, `_resolve_one`의 `TypeResolution` 전수 계수도
#: 흔들리지 않는다.
_R19_REASON_RESOLVERS = ("_incompleteness_reason", "_footprint_unverified_reason")


def _r19_reason_is_module_constant(reason: ast.expr) -> bool:
    if isinstance(reason, ast.Name):
        return True
    return (
        isinstance(reason, ast.Call) and getattr(reason.func, "id", None) in _R19_REASON_RESOLVERS
    )


def test_r19_every_type_resolution_reason_is_a_module_constant():
    """구조 게이트 — `server/vwx/typemap.py`의 판정 사유는 전부 **모듈 상수로 환원된다**.

    이것이 아래 갈래 전수를 가능하게 하는 전제다. 사유를 갈래 안에 리터럴로 박으면 소스에서
    갈래를 셀 수 없고, 셀 수 없으면 새 갈래가 확인 경로 게이트를 조용히 빠져나간다 —
    R18-E가 정확히 그 형태였다.

    ㉠ 모든 `TypeResolution(...)`의 사유는 모듈 상수 이름이거나 등기된 환원 헬퍼 호출이다.
    ㉡ 환원 헬퍼가 돌려주는 것도 전부 모듈 상수 이름이다 — 헬퍼 안에 리터럴을 숨기면 실패한다.
    ㉢ **확인 대기** 갈래는 헬퍼도 허용하지 않는다: 그 갈래는 이름으로 등기돼야 아래 전단사가
       갈래 하나하나를 시나리오와 묶을 수 있다.

    죽이는 뮤테이션: 어느 갈래의 `reason=`을 리터럴 문자열로 되돌리면 실패한다.
    """
    offenders = []
    for call in _r19_typeresolution_calls():
        for status, reason in _r19_status_reason_pairs(call):
            pending = getattr(status, "id", None) == "TYPE_NEEDS_CONFIRMATION"
            allowed = (
                isinstance(reason, ast.Name) if pending else _r19_reason_is_module_constant(reason)
            )
            if not allowed:
                offenders.append((call.lineno, ast.unparse(reason)[:60]))
    assert offenders == [], offenders

    tree = ast.parse(_R19_TYPEMAP_SOURCE)
    resolvers = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in _R19_REASON_RESOLVERS
    ]
    assert len(resolvers) == len(_R19_REASON_RESOLVERS), [node.name for node in resolvers]
    for resolver in resolvers:
        returns = [node for node in ast.walk(resolver) if isinstance(node, ast.Return)]
        assert returns, resolver.name
        for node in returns:
            assert isinstance(node.value, ast.Name), (resolver.name, ast.unparse(node))


def _r19_pending_reason_constants() -> tuple[str, ...]:
    """`server/vwx/typemap.py`에서 판정이 `needs_confirmation`이 되는 갈래의 사유 상수 이름 전수."""
    found: list[str] = []
    for call in _r19_typeresolution_calls():
        for status, reason in _r19_status_reason_pairs(call):
            if getattr(status, "id", None) != "TYPE_NEEDS_CONFIRMATION":
                continue
            if isinstance(reason, ast.Name):
                found.append(reason.id)
    return tuple(sorted(set(found)))


#: 확인 대기 갈래 -> 그 갈래에 **실제로 닿는** 시나리오 kwargs(`_r19_resolve_footprint` 인자).
#: 키는 소스에서 뽑은 사유 상수 이름이라, 갈래가 늘면 이 표 없이는 전단사가 깨진다.
_R19_PENDING_BRANCH_SCENARIOS = {
    # 별칭이 없어 타입을 확정하지 않았다 — 후보를 제시하고 사람이 고른다.
    "CANDIDATES_PRESENTED_REASON": {"footprint": 24, "aliases": {}},
    # 점유폭이 다르지만 **맞는 모드가 라이브러리에 있다** — 고를 것을 보여주고 기다린다.
    "FOOTPRINT_MISMATCH_CHOOSABLE_REASON": {"footprint": 16},
}


def test_r19_the_pending_branch_registry_is_a_bijection_onto_typemap():
    """[round19 major#5 ④] 확인 대기 갈래가 늘면 등기 없이는 통과하지 못한다.

    표를 손으로 열거하지 않는다 — 갈래 목록은 `server/vwx/typemap.py` 소스에서 나온다.
    죽이는 뮤테이션: 점유폭 관측 불완전 갈래를 `TYPE_NEEDS_CONFIRMATION`으로 되돌리면
    (round19가 그것을 `library_incomplete`로 고친 이유가 "고를 것이 없어서"다) 새 사유 상수가
    전수에 나타나 등기와 어긋난다.
    """
    assert _r19_pending_reason_constants() == tuple(sorted(_R19_PENDING_BRANCH_SCENARIOS))


@pytest.mark.parametrize("index", range(len(_R19_PENDING_BRANCH_SCENARIOS)))
def test_r19_deleting_any_pending_branch_row_breaks_the_bijection(index: int):
    """행 삭제 프로브 — 등기부에서 어느 행을 지워도 소스 전수와 어긋난다."""
    names = sorted(_R19_PENDING_BRANCH_SCENARIOS)
    shrunk = tuple(name for position, name in enumerate(names) if position != index)
    assert shrunk != _r19_pending_reason_constants()


def _r19_escapes_by_choosing_a_listed_option(kwargs, row) -> list[tuple[str, str, str]]:
    """payload가 제시한 선택지를 **실제로 골라** 다시 돌린다 — 확인 대기를 벗어난 조합들.

    조작자가 할 수 있는 것은 "제시된 타입·모드를 별칭으로 확정한다"뿐이다. 그래서 선택지는
    `type_candidates` × `mode_options`이고, 그중 하나라도 확인 대기를 벗어나면 그 갈래에는
    실제로 수행 가능한 확인 경로가 있다.
    """
    escaped: list[tuple[str, str, str]] = []
    type_names = row["type_candidates"] or [row["presented_console_type"]]
    for type_name in type_names:
        for option in row["mode_options"]:
            chosen = dict(kwargs)
            chosen["aliases"] = {_R19_TYPE: {"type": type_name, "mode": option["name"]}}
            after = row_by_id(_r19_resolve_footprint(**chosen), "c1")
            # **벗어났다** = 확정에 도달했다. "확인 대기가 아니게 됐다"로는 부족하다 —
            # 하드 스톱도 확인 대기가 아니므로 그 술어는 막다른 길을 탈출로 세어 버린다.
            if after["status"] == TYPE_RESOLVED:
                escaped.append((type_name, option["name"], after["status"]))
    return escaped


@pytest.mark.parametrize("reason_name", sorted(_R19_PENDING_BRANCH_SCENARIOS))
def test_r19_every_pending_branch_ships_an_option_the_operator_can_actually_choose(reason_name):
    """[round19 major#5 ④] "확인 대기"를 말하는 갈래마다 **고를 수 있는 것**이 payload에 있다.

    ㉠ 시나리오가 실제로 그 갈래에 닿는다(사유 상수 일치) — 닿지 않으면 게이트가 공허하다.
    ㉡ 제시된 선택지가 0건이 아니다.
    ㉢ 그 선택지 중 **하나 이상을 실제로 고르면** 확인 대기를 벗어난다 — 실행으로 확인한다.

    죽이는 뮤테이션:
      · 점유폭 갈래의 `mode_candidates=library_modes`를 별칭으로 좁힌 한 건으로 되돌리면
        `FOOTPRINT_MISMATCH_CHOOSABLE_REASON` 행에서 ㉢이 실패한다 — 제시된 유일한 모드가
        **점유폭이 안 맞은 그 모드**라 골라도 같은 자리로 돌아온다(= R18-E와 동형인 막다른 길).
      · 점유폭 하드 스톱을 확인 대기로 되돌리면 그 갈래가 전수에 추가돼 앞의 전단사가 깨지고,
        등기하면 여기서 ㉢이 실패한다.
    """
    import server.vwx.typemap as typemap_module

    kwargs = _R19_PENDING_BRANCH_SCENARIOS[reason_name]
    row = row_by_id(_r19_resolve_footprint(**kwargs), "c1")
    assert row["reason"] == getattr(typemap_module, reason_name), reason_name
    assert row["confirmation_required"] is True, reason_name
    assert row["type_candidates"] or row["presented_console_type"], reason_name
    assert row["mode_options"], reason_name
    escaped = _r19_escapes_by_choosing_a_listed_option(kwargs, row)
    assert escaped, (reason_name, row["mode_options"])


def test_r19_the_pending_branch_gate_is_not_vacuous_about_dead_ends():
    """대조군 건전성 — 게이트가 **막다른 길을 실제로 구별한다**.

    확인 대기가 아닌 갈래(점유폭 전수 불일치)에서는 어떤 선택지를 골라도 벗어나지 못한다.
    이 단정이 없으면 위 게이트의 ㉢은 "무엇이든 통과"일 수 있다.
    """
    kwargs = {"footprint": 99}
    row = row_by_id(_r19_resolve_footprint(**kwargs), "c1")
    assert row["status"] == "designed_footprint_unmatchable"
    assert row["mode_options"], "하드 스톱이어도 라이브러리가 무엇을 제공하는지는 보여준다"
    assert _r19_escapes_by_choosing_a_listed_option(kwargs, row) == []


def test_r19_the_new_footprint_vocabulary_is_registered_in_both_closed_sets():
    """[round19 major#5] 신설 어휘 둘이 닫힌 어휘에 등재되고 라벨을 갖는다.

    배제 코드는 `target_exclusion_reason`에, 판정은 `type_resolution_status`에 들어간다 —
    등재를 지우면 `validate_autopatch`가 던지고, 라벨을 지우면 `verdicts` 임포트 자체가
    실패한다(모듈 최상위 전단사 검사).

    두 어휘 **모두**가 필요한 이유: 배제 코드만 있으면 `types` 표가 이 상태를
    `needs_confirmation`으로 적어야 하고, 판정만 있으면 전달물 배제가 다시
    `type_confirmation_pending`으로 뭉개진다 — 어느 쪽이든 한 payload가 모순된 말을 한다.
    """
    from server.vwx.verdicts import (
        TARGET_EXCLUSION_REASON,
        TYPE_RESOLUTION_STATUS,
        target_exclusion_label,
        type_resolution_status_label,
        validate_autopatch,
    )

    assert DESIGNED_FOOTPRINT_MATCHES_NO_MODE in TARGET_EXCLUSION_REASON
    assert TYPE_FOOTPRINT_UNMATCHABLE in TYPE_RESOLUTION_STATUS
    assert (
        validate_autopatch("target_exclusion_reason", DESIGNED_FOOTPRINT_MATCHES_NO_MODE)
        == DESIGNED_FOOTPRINT_MATCHES_NO_MODE
    )
    assert (
        validate_autopatch("type_resolution_status", TYPE_FOOTPRINT_UNMATCHABLE)
        == TYPE_FOOTPRINT_UNMATCHABLE
    )
    # 라벨은 조작자가 축을 짚는 근거다 — 두 라벨 모두 도면 점유폭을 가리킨다.
    assert "점유폭" in target_exclusion_label(DESIGNED_FOOTPRINT_MATCHES_NO_MODE)
    assert "점유폭" in type_resolution_status_label(TYPE_FOOTPRINT_UNMATCHABLE)
    # 프로덕션이 실제로 두 자리에 같은 판정을 싣는다.
    payload = _r19_resolve_footprint(footprint=99)
    assert row_by_id(payload, "c1")["status"] == TYPE_FOOTPRINT_UNMATCHABLE
    assert hard_stop_codes(payload) == [DESIGNED_FOOTPRINT_MATCHES_NO_MODE]


# --- round21 라이브러리 열거 절단 규율 (LibraryTruncation) ---
#
# R20-A 세 갈래를 고정한다: ⓐ `node.childCount` 계수 대조 · ⓑ 표적 회수 스윕 ·
# ⓒ 수행 불가능한 라벨의 교체.

from server.vwx.typemap import (  # noqa: E402
    FixtureTypeLibrary,
    recover_requested_types,
)
from server.vwx.verdicts import (  # noqa: E402
    skipped_check_label,
    target_exclusion_label,
)

_R21_RESPONDER_SOURCE = Path("console/lua/copilot_responder.lua").read_text(encoding="utf-8")


def _r21_config_int(name: str) -> int:
    """`CONFIG`의 정수 설정을 **responder 소스에서** 읽는다.

    상수를 테스트에 베끼면 예산이 바뀌었을 때 모델이 조용히 거짓이 된다 — 그 형태가
    이 SPEC이 반복해서 잡힌 "전달값 베끼기"다.
    """
    match = re.search(rf"^\s*{name}\s*=\s*(\d+)\s*,", _R21_RESPONDER_SOURCE, re.M)
    assert match is not None, name
    return int(match.group(1))


_R21_MAX_CHILDREN = _r21_config_int("max_children")
_R21_MAX_PAYLOAD = _r21_config_int("max_payload")
_R21_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def _r21_json_encode(value) -> str:
    """`M.json_encode`의 복제 — 키 정렬·배열·정수·불리언까지 같은 규칙."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value:d}"
    if isinstance(value, str):
        return '"' + value + '"'
    if isinstance(value, list):
        return "[" + ",".join(_r21_json_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        return (
            "{" + ",".join(f'"{key}":{_r21_json_encode(value[key])}' for key in sorted(value)) + "}"
        )
    raise TypeError(value)


def _r21_percent_encode(text: str) -> str:
    """`M.percent_encode`의 복제 — 비예약 바이트 외 전부 `%XX`."""
    return "".join(
        char if char in _R21_UNRESERVED else "".join(f"%{byte:02X}" for byte in char.encode())
        for char in text
    )


def _r21_snapshot(path: str, names, node_name: str, node_class: str, child_class: str) -> dict:
    """`M.build_snapshot`의 복제 — 자식 캡 → payload 예산 루프 순서까지 같다."""
    total = len(names)
    cap = min(total, _R21_MAX_CHILDREN)
    items = [{"name": names[index], "class": child_class, "i": index + 1} for index in range(cap)]
    payload = {
        "v": "1.5.0",
        "kind": "state",
        "id": 1,
        "path": path,
        "ok": True,
        "node": {"name": node_name, "class": node_class, "childCount": total},
        "children": items,
        "truncated": cap < total,
    }
    while len(_r21_percent_encode(_r21_json_encode(payload))) > _R21_MAX_PAYLOAD and items:
        items.pop()
        payload["children"] = items
        payload["truncated"] = True
    return payload


_R21_TYPE_AXIS = ("Patch/FixtureTypes", "FixtureTypes", "FixtureTypes", "FixtureType")
_R21_MODE_AXIS = ("Patch/FixtureTypes/1/DMXModes", "DMXModes", "DMXModes", "DMXMode")


def _r21_last_fitting(name_length: int, axis) -> int:
    """그 이름 길이에서 **절단 없이 실리는 최대 항목 수**."""
    path, node_name, node_class, child_class = axis
    filler = "T" * name_length
    for count in range(1, 4 * _R21_MAX_CHILDREN):
        snapshot = _r21_snapshot(path, [filler] * count, node_name, node_class, child_class)
        if snapshot["truncated"]:
            return count - 1
    raise AssertionError("절단이 개시되지 않았다 — 모델이 예산을 재현하지 못한다")


#: 이름 길이 → 절단 없이 실리는 최대 종수. 각 행의 길이는 그 개시점을 내는 **최소 길이**라
#: 행과 개시점이 전단사다 — 행을 지우면 개시점 하나가 사라져
#: `_r21_assert_onset_table_shape`가 즉시 잡는다.
#:
#: 감사 실측(별도 모델)과 대조: 타입 축 8자→19 · 12자→18 · 16자→17 · 20~24자→16 ·
#: 30자→15 · 40자→13이 이 표에서 그대로 재현된다(아래 대조 시험이 값으로 확인한다).
#: 모드 축에서 감사는 8자→20 · 12자→19로 하나씩 높은데, 그것은 감사 모델이 더 짧은
#: 경로를 썼기 때문이고 `test_r21_the_onset_moves_with_the_encoded_byte_weight`가
#: 경로 한 글자가 개시점을 옮긴다는 것을 실측으로 보인다.
_R21_TYPE_ONSETS = ((4, 19), (9, 18), (13, 17), (19, 16), (25, 15), (31, 14), (39, 13))
_R21_MODE_ONSETS = ((4, 20), (8, 19), (12, 18), (17, 17), (22, 16), (28, 15), (35, 14))

#: 재계산 스윕의 **고정 구간**. 표에서 유도하면(= `min..max`) 끝 행을 지웠을 때 구간도
#: 함께 줄어들어 전단사가 그대로 성립한다 — 자기충족이다. 구간을 표 밖에 못박아야
#: 끝 행 삭제가 개시점 하나의 결손으로 드러난다(round18 M24와 같은 형태의 공백).
#: 상한 40자는 감사가 실측한 이름 길이 대역의 끝이다(GDTF 제조사명+모델명 최장 표본).
_R21_ONSET_SWEEP = (4, 40)

#: 오늘(2026-08-08 M8) 실물 콘솔이 실제로 준 타입 이름 3종. 비공허성 대조군의 근거다.
_R21_TODAYS_LIBRARY = ("Robin MMX Spot", "FixtureType 2", "Robin LEDBeam 350")


def _r21_assert_onset_table_shape(rows, axis) -> None:
    """행 삭제 프로브 — 표의 행과 **개시점 값**이 전단사임을 재계산으로 강제한다.

    행마다 자유 라벨이 아니라 계산된 개시점이 붙어 있고, 각 행의 길이는 그 개시점을
    내는 최소 길이여야 한다. 그래서 한 행을 지우면 그 개시점 값이 선언 집합에서
    사라지고, 스윕으로 다시 계산한 집합과 어긋난다.
    """
    lengths = [length for length, _ in rows]
    assert lengths == sorted(set(lengths)), lengths
    low, high = _R21_ONSET_SWEEP
    assert lengths[0] == low, lengths
    swept: dict[int, int] = {}
    for length in range(low, high + 1):
        swept.setdefault(_r21_last_fitting(length, axis), length)
    # 선언 ↔ 재계산 전단사. 어느 쪽에서 행을 지워도 깨진다.
    assert dict(rows) == {length: onset for onset, length in swept.items()}
    onsets = [onset for _, onset in rows]
    # 개시점은 단조 감소하고 **연속 값**을 이룬다 — 중간 행을 지우면 구멍이 난다.
    assert onsets == sorted(onsets, reverse=True), onsets
    assert set(onsets) == set(range(min(onsets), max(onsets) + 1)), onsets


def test_r21_truncation_onset_table_reproduces_the_responder_arithmetic():
    """이름 길이 × 종수 절단 개시점 — responder 인코더 복제로 값까지 대조한다."""
    _r21_assert_onset_table_shape(_R21_TYPE_ONSETS, _R21_TYPE_AXIS)
    _r21_assert_onset_table_shape(_R21_MODE_ONSETS, _R21_MODE_AXIS)
    for length, onset in _R21_TYPE_ONSETS:
        assert _r21_last_fitting(length, _R21_TYPE_AXIS) == onset, length
    for length, onset in _R21_MODE_ONSETS:
        assert _r21_last_fitting(length, _R21_MODE_AXIS) == onset, length
    # 감사가 보고한 타입 축 수치를 값으로 재현한다.
    assert [
        _r21_last_fitting(length, _R21_TYPE_AXIS) for length in (8, 12, 16, 20, 24, 30, 40)
    ] == [19, 18, 17, 16, 16, 15, 13]


def test_r21_the_payload_budget_bites_before_the_child_cap():
    """`max_children`은 하드 캡이지만 **예산이 항상 먼저 문다** — 처방 ⓑ의 전제다.

    이름을 한 글자로 줄여도 개시점이 캡에 닿지 못한다. 그래서 "재판독하면 더 온다"는
    지시가 수행 불가능하고(ⓒ), 회수는 스윕으로만 가능하다.
    """
    assert _R21_MAX_CHILDREN == 24
    for _length, onset in _R21_TYPE_ONSETS + _R21_MODE_ONSETS:
        assert onset < _R21_MAX_CHILDREN, onset
    assert _r21_last_fitting(1, _R21_TYPE_AXIS) < _R21_MAX_CHILDREN


def test_r21_the_onset_moves_with_the_encoded_byte_weight():
    """개시점을 정하는 것은 **글자 수가 아니라 인코딩 바이트 수**다.

    ① 같은 18자라도 공백이 든 이름은 `%20`으로 3바이트가 되어 한 종 일찍 절단된다 —
       감사의 실물 GDTF 표본(평균 18자) 16종 통과가 그 값이다.
    ② 경로 한 조각이 길어져도 개시점이 옮겨간다 — 감사의 모드 축 수치가 이 표보다
       하나 높았던 이유이고, 두 모델이 어긋난 것이 아니라 입력이 달랐다는 증거다.
    """
    path, node_name, node_class, child_class = _R21_TYPE_AXIS
    spaced = ("ab cde" * 4)[:18]
    assert len(spaced) == 18 and " " in spaced
    plain_onset = _r21_last_fitting(18, _R21_TYPE_AXIS)
    spaced_onset = next(
        count - 1
        for count in range(1, 40)
        if _r21_snapshot(path, [spaced] * count, node_name, node_class, child_class)["truncated"]
    )
    assert spaced_onset == plain_onset - 1 == 16

    short_path = "Patch/FixtureTypes/1"
    shifted = next(
        count - 1
        for count in range(1, 40)
        if _r21_snapshot(short_path, ["T" * 8] * count, "DMXModes", "DMXModes", "DMXMode")[
            "truncated"
        ]
    )
    assert shifted == _r21_last_fitting(8, _R21_MODE_AXIS) + 1 == 20


def test_r21_todays_three_type_library_is_not_truncated():
    """비공허성 대조군 — 오늘 실물 3종은 무해하다. 모델이 아무거나 절단이라 하지 않는다."""
    path, node_name, node_class, child_class = _R21_TYPE_AXIS
    snapshot = _r21_snapshot(path, list(_R21_TODAYS_LIBRARY), node_name, node_class, child_class)
    assert snapshot["truncated"] is False
    assert snapshot["node"]["childCount"] == len(snapshot["children"]) == 3

    # 그 스냅샷을 프로덕션 리더에 그대로 먹이면 미관측이 0이다.
    library = read_fixture_type_library(LibraryRigPort(_r21_types(_R21_TODAYS_LIBRARY)))
    assert library.child_count == 3
    assert library.enumerated_count == 3
    assert library.unseen == 0
    assert library.enumeration_short is False
    assert library.enumeration_incomplete is False


def _r21_types(names, modes=(("Mode 1", 16),)):
    return [(name, list(modes)) for name in names]


class _R21ShortPort(LibraryRigPort):
    """선언 총계가 반환 행 수보다 큰 포트 — 절단의 **실물 형태**를 그대로 흉내낸다.

    `declared_types`는 루트 `node.childCount`, `hidden`은 열거에 실리지 않았지만
    `Patch/FixtureTypes/<i>`로는 답하는 타입이다(= 표적 스윕이 회수할 수 있는 것).
    `flag`가 거짓이면 **`truncated` 플래그 없이 계수만 어긋난** 스냅샷이 된다.
    """

    def __init__(self, types, *, declared_types, hidden=(), flag=False, dead=(), **kwargs):
        super().__init__(types, truncated=flag, **kwargs)
        self.declared_types = declared_types
        self.hidden = dict(hidden)
        self.dead = frozenset(dead)
        self.probe_paths: list[str] = []

    def _modes_of(self, type_index: int):
        if type_index in self.hidden:
            return self.hidden[type_index][1]
        return super()._modes_of(type_index)

    def query_state(self, path: str) -> dict:
        if path == FIXTURE_TYPE_LIBRARY_ROOT:
            payload = super().query_state(path)
            payload["node"]["childCount"] = self.declared_types
            return payload
        probe = re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)", path)
        if probe is not None:
            index = int(probe.group(1))
            self.state_calls.append(path)
            self.probe_paths.append(path)
            if index in self.dead:
                raise RuntimeError("no reply within 3.0s")
            if index not in self.hidden:
                return {"ok": False, "path": path, "error": "path segment not found"}
            return {
                "ok": True,
                "path": path,
                "node": {"name": self.hidden[index][0], "class": "FixtureType"},
                "children": [],
                "truncated": False,
            }
        return super().query_state(path)


def test_r21_a_count_mismatch_without_the_flag_is_still_incomplete():
    """계수 대조 대조군 — **플래그만 보는 구판은 통과하고 신판은 잡는다**.

    `truncated=false`인데 선언 총계가 반환 행 수보다 크다. 플래그 단독 판정은 이
    입력을 전수로 읽고 부재까지 단정했다.
    """
    port = _R21ShortPort(_r21_types(["LEDWash 600"]), declared_types=30, flag=False)
    library = read_fixture_type_library(port)

    # 구판이 본 것: 플래그는 거짓이다.
    assert library.truncated is False
    # 신판이 보는 것: 계수가 어긋난다.
    assert library.child_count == 30
    assert library.returned_row_count == 1
    assert library.enumerated_count == 1
    assert library.unseen == 29
    assert library.enumeration_short is True
    assert library.enumeration_incomplete is True

    payload = resolve_fixture_types([request()], library_port=port).to_dict()
    assert row_by_id(payload, "vwx-missing-0001")["status"] == TYPE_LIBRARY_INCOMPLETE
    assert FIXTURE_TYPE_LIBRARY_TRUNCATED in skipped_kinds(payload)
    # 부재를 단정하지 않는다 — 이것이 구판이 어겼던 것이다.
    assert FIXTURE_TYPE_NOT_IN_LIBRARY not in hard_stop_codes(payload)


def test_r21_the_flag_alone_still_counts_when_the_totals_agree():
    """병존 대조군 — 계수는 맞는데 **플래그만** 참인 입력도 불완전이다.

    두 근거 중 하나를 지우는 뮤턴트가 각각 다른 시험에서 죽어야 축이 갈린다.
    """
    port = LibraryRigPort(_r21_types(["LEDWash 600"]), truncated=True)
    library = read_fixture_type_library(port)

    assert library.enumeration_short is False
    assert library.unseen == 0
    assert library.truncated is True
    assert library.enumeration_incomplete is True


def test_r21_declared_totals_and_unobserved_counts_are_in_the_payload():
    """조용한 부분집합 금지 — 미관측이 있으면 **payload에 보여야** 한다.

    기존 `type_count`·`mode_count`의 뜻은 바꾸지 않았다(= 본 수). 칸을 늘렸다.
    """
    port = _R21ShortPort(
        _r21_types(["LEDWash 600"], modes=(("Mode 1", 16),)), declared_types=30, flag=False
    )
    library = read_fixture_type_library(port).to_dict()

    assert library["type_count"] == 1  # 뜻 불변 — 본 수
    assert library["child_count"] == 30
    assert library["unseen_count"] == 29
    assert library["enumeration_short"] is True
    assert library["enumeration_incomplete"] is True
    entry = library["types"][0]
    assert entry["mode_count"] == 1  # 뜻 불변 — 본 수
    assert entry["mode_child_count"] == 1
    assert entry["mode_unseen_count"] == 0
    assert entry["modes_incomplete"] is False
    # 표시가 없으면 완전하다는 뜻이 되도록, 키는 **항상** 실린다.
    clean = read_fixture_type_library(LibraryRigPort(_r21_types(["LEDWash 600"]))).to_dict()
    assert clean["unseen_count"] == 0 and clean["child_count"] == 1
    assert clean["types"][0]["mode_unseen_count"] == 0


def test_r21_mode_enumeration_gets_the_same_count_comparison():
    """모드 축도 계수 대조를 받는다 — 플래그 없이 짧은 DMXModes 스냅샷."""

    class _ShortModes(LibraryRigPort):
        def query_state(self, path: str) -> dict:
            payload = super().query_state(path)
            if path.endswith(DMX_MODES_SEGMENT):
                payload["node"]["childCount"] = 5
            return payload

    port = _ShortModes(_r21_types(["MegaPointe"], modes=(("Mode 1", 16), ("Mode 2", 24))))
    entry = read_fixture_type_library(port).types[0]

    assert entry.modes_truncated is False
    assert entry.mode_child_count == 5
    assert entry.returned_mode_row_count == 2
    assert entry.observed_mode_count == 2
    assert entry.modes_unseen == 3
    assert entry.modes_enumeration_short is True
    assert entry.modes_incomplete is True


def _r21_sweep_port(**kwargs):
    """열거 1종 · 선언 30종 · 20번 슬롯에 요청된 타입이 숨어 있는 포트."""
    return _R21ShortPort(
        _r21_types(["LEDWash 600"]),
        declared_types=30,
        hidden={20: ("MegaPointe", [("Mode 1", 16), ("Mode 2", 24)])},
        **kwargs,
    )


_R21_SWEEP_REQUEST = TypeRequest(
    candidate_id="s1", instrument_type="MegaPointe", gdtf_fixture="MegaPointe", mode="Mode 1"
)


def test_r21_the_targeted_sweep_recovers_the_requested_name():
    """스윕 도달성 — **스윕이 있을 때와 없을 때 같은 입력의 산출물이 갈린다**."""
    without_sweep = read_fixture_type_library(_r21_sweep_port())
    assert [entry.name for entry in without_sweep.types] == ["LEDWash 600"]
    assert without_sweep.recovery_boundary is None

    port = _r21_sweep_port()
    with_sweep = recover_requested_types(port, read_fixture_type_library(port), ["MegaPointe"])
    assert [entry.name for entry in with_sweep.types] == ["LEDWash 600", "MegaPointe"]
    assert with_sweep.recovered_count == 1
    assert with_sweep.recovery_boundary == 30
    recovered = with_sweep.types[1]
    assert recovered.recovered is True and recovered.index == 20
    # 회수분은 관측이므로 미관측 수가 줄어든다 — 그러나 아래 시험대로 판정은 안 오른다.
    assert with_sweep.unseen == 28

    # 프로덕션 경로(`resolve_fixture_types`)가 실제로 스윕을 건다.
    payload = resolve_fixture_types([_R21_SWEEP_REQUEST], library_port=_r21_sweep_port()).to_dict()
    assert payload["library"]["recovered_count"] == 1
    assert "MegaPointe" in [entry["name"] for entry in payload["library"]["types"]]
    assert FIXTURE_TYPE_NOT_IN_LIBRARY not in hard_stop_codes(payload)


def test_r21_the_sweep_does_not_promote_the_completeness_verdict():
    """스윕 비승격 — 회수해도 완전성 판정은 자기 근거로만 난다(R18-A 방지)."""
    port = _r21_sweep_port()
    before = read_fixture_type_library(port)
    after = recover_requested_types(port, before, ["MegaPointe"])

    for library in (before, after):
        assert library.child_count == 30
        assert library.enumerated_count == 1
        assert library.returned_row_count == 1
        assert library.enumeration_short is True
        assert library.enumeration_incomplete is True
    assert after.recovered_count == 1  # 관측만 올랐다

    payload = resolve_fixture_types([_R21_SWEEP_REQUEST], library_port=_r21_sweep_port()).to_dict()
    # 회수해서 후보를 냈지만 고지는 그대로 나간다.
    assert FIXTURE_TYPE_LIBRARY_TRUNCATED in skipped_kinds(payload)
    assert payload["library"]["enumeration_incomplete"] is True
    assert payload["library"]["unseen_count"] == 28


def test_r21_the_sweep_requires_an_established_slot():
    """스윕 전제 — 열거가 **비면** 인덱스가 위치로 강등되므로 훑지 않는다."""
    port = _R21ShortPort(
        [], declared_types=30, hidden={20: ("MegaPointe", [("Mode 1", 16)])}, flag=True
    )
    library = read_fixture_type_library(port)
    assert library.types == ()

    swept = recover_requested_types(port, library, ["MegaPointe"])
    assert swept.probe_paths_seen == [] if hasattr(swept, "probe_paths_seen") else True
    assert port.probe_paths == []
    assert swept.recovery_boundary is None
    assert swept.recovered_count == 0


def test_r21_the_sweep_boundary_is_exactly_one_to_child_count():
    """경계 ±1 대조군 — 0도 `child_count+1`도 프로브하지 않는다."""
    port = _R21ShortPort(
        _r21_types(["LEDWash 600"]), declared_types=6, hidden={9: ("MegaPointe", [("M", 16)])}
    )
    swept = recover_requested_types(port, read_fixture_type_library(port), ["MegaPointe"])

    probed = sorted(int(path.rsplit("/", 1)[1]) for path in port.probe_paths)
    assert probed == [2, 3, 4, 5, 6]  # 1은 열거로 이미 관측, 0·7은 범위 밖
    assert swept.recovery_boundary == 6
    assert swept.recovered_count == 0  # 경계 밖의 9번은 회수되지 않는다


def test_r23_the_sweep_reads_modes_only_for_matches_and_stays_within_the_cost_bound():
    """비용 대조군 — **전수 스윕으로 확대하면 죽는다**.

    표적 스윕은 인덱스당 `query_state` 1회로 이름만 보고, `_read_type`(DMXModes +
    모드당 이름 프로퍼티)은 **일치한 타입에만** 딸려온다. 요청되지 않은 인덱스의
    DMXModes를 한 번이라도 읽으면 그것이 전수 스윕이고 비용이 차수만큼 뛴다.

    **[round23 R22-C] 왜 단정을 바꿨는가 — 이 시험의 구판이 결함을 고정하고 있었다.**
    구명은 `test_r21_the_sweep_stops_at_the_first_match_and_never_reads_unrequested_types`
    이고 `assert probed == [2, 3, 4, 5, 6, 7, 8]`로 **조기 종료를 요구사항으로 못박았다**.
    그런데 `fuzzy_type_equal`은 포함관계 매칭이라, 요청 이름을 부분 포함하는 다른 제품이
    더 낮은 슬롯에 있으면 조기 종료는 **그 엉뚱한 타입을 확정**하고 정답 슬롯은
    프로브조차 하지 않는다(같은 절의 `test_r23_the_sweep_does_not_collapse_...` 실증).
    즉 구판 단정은 정확성 결함을 대조군으로 봉인한 **역방향 대조군**이었다.

    비용을 재는 의도는 유효하므로 시험은 남기고 **단정의 형태만** 바꿨다: 프로브 인덱스
    목록을 값으로 고정하는 대신 ① 이름 프로브는 미열거 슬롯당 **1회 이하** ② `_read_type`은
    **일치한 슬롯에만** ③ 총 왕복이 `U + k(1 + c·m)` 상한 이하 — 어느 것도 "어디서
    멈추는가"를 고정하지 않는다. 정확성을 고정하지 않는 단정이라야 다음 라운드가 정확성을
    고치려 할 때 이 시험이 길을 막지 않는다.
    """
    port = _R21ShortPort(
        _r21_types(["LEDWash 600"]),
        declared_types=30,
        hidden={
            5: ("Sharpy Plus", [("Mode 1", 16), ("Mode 2", 24)]),
            8: ("MegaPointe", [("Mode 1", 16), ("Mode 2", 24)]),
        },
    )
    swept = recover_requested_types(port, read_fixture_type_library(port), ["MegaPointe"])

    probed = sorted(int(path.rsplit("/", 1)[1]) for path in port.probe_paths)
    # ① 미열거 슬롯당 이름 프로브 1회 이하 — 같은 슬롯을 두 번 묻지 않고, 열거로 이미
    #    관측한 1번과 경계 밖은 아예 묻지 않는다.
    assert len(probed) == len(set(probed))
    assert set(probed) <= set(range(1, 31)) - {1}
    # ② 5번(요청되지 않은 실재 타입)의 이름은 봤지만 **모드는 읽지 않았다**.
    mode_reads = [
        call
        for call in port.state_calls
        if call.endswith(DMX_MODES_SEGMENT)
        and not call.startswith(f"{FIXTURE_TYPE_LIBRARY_ROOT}/1/")
    ]
    assert mode_reads == [f"{FIXTURE_TYPE_LIBRARY_ROOT}/8/{DMX_MODES_SEGMENT}"]
    assert [entry.name for entry in swept.types] == ["LEDWash 600", "MegaPointe"]

    # ③ 비용 상한 `U + k(1 + c·m)`: U = 30 − 1(열거분), k = 일치 1건, c = 1(negative).
    modes = len(swept.types[1].modes)
    read_type_calls = len(mode_reads) + len(
        [
            call
            for call in port.property_calls
            if not call[0].startswith(f"{FIXTURE_TYPE_LIBRARY_ROOT}/1/")
        ]
    )
    assert len(port.probe_paths) + read_type_calls <= (30 - 1) + 1 * (1 + 1 * modes)
    # 왕복 수는 payload가 직접 말한다 — 상한 단정이 재는 것과 같은 값이다(R22-F).
    assert swept.recovery_probe_count == len(port.probe_paths)


def test_r21_probe_failures_are_diagnostics_and_never_observations():
    """프로브 실패는 **진단 계수**로 남고 관측으로 올라가지 않는다.

    `ok=false`는 실패가 아니다 — 유계 범위 안의 빈 인덱스는 희소 풀의 정보다.
    """
    port = _R21ShortPort(
        _r21_types(["LEDWash 600"]),
        declared_types=6,
        hidden={},
        dead=(3, 4),
    )
    swept = recover_requested_types(port, read_fixture_type_library(port), ["MegaPointe"])

    assert swept.probe_failures == 2  # 3·4번만 — 2·5·6번의 ok=false는 세지 않는다
    assert swept.recovered_count == 0
    assert [entry.name for entry in swept.types] == ["LEDWash 600"]
    assert swept.unseen == 5  # 실패가 관측을 늘리지 않았다
    assert swept.to_dict()["probe_failure_count"] == 2


def test_r21_a_recovered_type_gets_the_same_count_discipline_as_an_enumerated_one():
    """경로별로 규율이 갈리지 않는다 — 회수 경로와 열거 경로의 계수 산식이 같다."""
    modes = [("Mode 1", 16), ("Mode 2", 24)]
    enumerated = read_fixture_type_library(
        LibraryRigPort([("LEDWash 600", list(modes)), ("MegaPointe", list(modes))])
    ).types[1]

    port = _r21_sweep_port()
    recovered = recover_requested_types(
        port, read_fixture_type_library(port), ["MegaPointe"]
    ).types[1]

    assert recovered.name == enumerated.name == "MegaPointe"
    for field_name in (
        "mode_child_count",
        "modes_enumerated_count",
        "returned_mode_row_count",
        "observed_mode_count",
        "modes_unseen",
        "modes_enumeration_short",
        "modes_incomplete",
        "modes_available",
        "modes_truncated",
    ):
        assert getattr(recovered, field_name) == getattr(enumerated, field_name), field_name
    # 다른 것은 **출처 표시 하나**뿐이다.
    assert recovered.recovered is True and enumerated.recovered is False


def test_r21_the_sweep_declines_when_the_index_domain_does_not_match():
    """열거 인덱스가 경계 밖이면 스윕 도메인이 어긋난 것이므로 훑지 않는다."""
    port = _R21ShortPort(
        _r21_types(["LEDWash 600"]), declared_types=30, hidden={20: ("MegaPointe", [("M", 16)])}
    )
    library = read_fixture_type_library(port)
    outside = FixtureTypeLibrary(
        types=(LibraryType(index=99, name="LEDWash 600"),),
        available=True,
        child_count=library.child_count,
        enumerated_count=1,
        returned_row_count=1,
    )
    port.probe_paths.clear()

    swept = recover_requested_types(port, outside, ["MegaPointe"])

    assert port.probe_paths == []
    assert swept.recovery_boundary is None


def test_r21_the_dead_end_labels_name_an_action_the_operator_can_perform():
    """ⓒ — "라이브러리를 다시 읽어야 함"은 **수행 불가능한 지시**였다.

    재판독이 같은 앞부분을 준다는 것은 위 예산 시험이 값으로 보였다. 라벨은 이제
    도면 타입명 확인 또는 GDTF 임포트를 가리킨다.
    """
    for code in (FIXTURE_TYPE_LIBRARY_TRUNCATED, FIXTURE_TYPE_LIBRARY_UNREADABLE):
        label = target_exclusion_label(code)
        assert "다시 읽" not in label, code
        assert "타입명" in label and "임포트" in label, code
    # 미관측을 부재라 적지 않는다 — 건너뛴 검사 라벨은 여전히 부재 단정 불가를 말한다.
    assert "부재 단정 불가" in skipped_check_label(FIXTURE_TYPE_LIBRARY_TRUNCATED)
    assert "부재 단정 불가" in skipped_check_label(FIXTURE_TYPE_LIBRARY_UNREADABLE)


def test_r21_the_two_library_axis_labels_are_distinguishable():
    """라벨 축 구별성 대조군 — 두 코드의 라벨을 맞바꾸면 잡힌다.

    각 라벨은 **자기 축의 판별자**를 담아야 한다: 절단 축은 미관측, 판독 실패 축은
    응답을 못 받았다는 사실. 문구를 형제 축의 것으로 바꾸면 이 시험이 죽는다.
    """
    truncated = target_exclusion_label(FIXTURE_TYPE_LIBRARY_TRUNCATED)
    unreadable = target_exclusion_label(FIXTURE_TYPE_LIBRARY_UNREADABLE)
    assert truncated != unreadable
    assert "미관측" in truncated and "미관측" not in unreadable
    assert "읽지 못함" in unreadable and "읽지 못함" not in truncated
    assert "콘솔 응답" in unreadable and "콘솔 응답" not in truncated

    skipped_truncated = skipped_check_label(FIXTURE_TYPE_LIBRARY_TRUNCATED)
    skipped_unreadable = skipped_check_label(FIXTURE_TYPE_LIBRARY_UNREADABLE)
    assert skipped_truncated != skipped_unreadable
    # 같은 코드의 두 자리도 서로 다른 것을 말한다(배제 라벨 = 조치, 고지 라벨 = 인식 한계).
    assert skipped_truncated != truncated


def test_r21_library_name_scanner_keeps_real_names_and_drops_substrings():
    """소스텍스트 게이트의 위양성 교정을 **양방향으로** 고정한다."""
    # 실물 이름은 여전히 잡힌다.
    for planted in ("Robe Lighting@MegaPointe", "Robin MMX Spot", "LEDBeam 350", "Mac 2000"):
        assert library_name_constants(f'X = "{planted}"\n'), planted
    # 영어 낱말 속 부분문자열은 더 이상 제조사가 아니다.
    for benign in ("probe_failures", "correlation", "wardrobe_count", "microbe"):
        assert library_name_constants(f'X = "{benign}"\n') == [], benign
    # 프로덕션은 깨끗하다.
    assert library_name_constants(TYPEMAP_SOURCE) == []


def test_r21_the_apply_sibling_refuses_an_index_reading_on_a_count_short_library():
    """형제 표면 대조군 — `apply._resolve_library_type`도 **계수 대조**를 본다.

    그 자리의 규율은 "목록이 전수가 아니면 **부정 결론**(= 이름이 열거에 없다)을
    증거로 쓰지 않는다"이다. 근거를 `truncated` 플래그로 좁히면, 계수만 어긋난
    스냅샷에서 `FixtureType <n>` 표시 하나로 다른 타입을 확정해 버린다 —
    멱등 판정과 검증이 그 확정 위에 선다.
    """
    from server.vwx.apply import _resolve_library_type

    listed = LibraryType(index=2, name="LEDWash 600")
    short = FixtureTypeLibrary(
        types=(listed,),
        available=True,
        truncated=False,  # 플래그만 보는 구판은 이 입력을 전수로 읽는다
        child_count=30,
        enumerated_count=1,
        returned_row_count=1,
    )
    assert short.truncated is False and short.enumeration_incomplete is True
    # 이름 일치가 없는데 인덱스 형태만 맞는 표시 — 부정 결론에 기댄 해석이라 거부한다.
    assert _resolve_library_type("FixtureType 2", short) is None

    # 긍정 증거(이름 정확 일치)는 절단과 무관하게 그대로 채택된다 — 과잉 거부가 아니다.
    assert _resolve_library_type("LEDWash 600", short) is listed

    # 계수가 맞으면 인덱스 형태 해석도 살아난다 — 위 거부가 공허하지 않다는 대조군.
    # [round23 R22-B] 대조군 스냅샷을 **자기정합**으로 고친다. 구판은 `child_count=1`에
    # 슬롯 2번을 실었다: 계수만 맞고 인덱스가 선언 경계 밖이라, 같은 스냅샷을
    # `recover_requested_types`는 훑기를 거부하면서 완전성 진술은 전수라고 말했다.
    # 대조군이 그 모순 위에 서 있으면 "계수가 맞다"의 뜻이 자리마다 갈린다 —
    # 도메인 위반 자체는 아래 round23 절이 **양성 사례**로 따로 고정한다.
    whole_listed = LibraryType(index=1, name="LEDWash 600")
    whole = FixtureTypeLibrary(
        types=(whole_listed,),
        available=True,
        child_count=1,
        enumerated_count=1,
        returned_row_count=1,
    )
    assert whole.enumeration_incomplete is False
    assert _resolve_library_type("FixtureType 1", whole) is whole_listed


# --------------------------------------------------------------------------
# --- round21 목록 완전성 침묵 차단 (ModeSilence) ---
#
# R20-B: `_mode_candidates`가 요청 모드를 못 찾으면 `console_type.modes`를 그대로
# 돌려주는데, 그 튜플은 **절단될 수 있는 열거 결과**다. 목록이 비지 않으므로 호출자의
# 절단 가드를 지나가고, `incompleteness_kind`가 서지 않아 `skipped_checks`가 **0건**이
# 됐다. 조작자는 부분 목록을 "고를 것 전부"로 봤다. round19가 신설한
# `mode_options`(index·name·channel_count)가 정확히 그 부분 목록을 실었으므로,
# round19 자신의 기준(*"고를 수 있는 것을 보여주는 것이 확인 대기의 전제"*)이 자기
# 새 필드에서 깨진 것이다.
#
# 처방은 **침묵을 구조적으로 불가능하게** 만드는 것이다:
#   ① 목록 옆에 완전성 진술을 **항상** 싣는다(`row()`가 그것을 필수 키워드로 받는다).
#   ② 완전성이 "불완전"이라 말하면 고지가 **같은 근거에서** 난다.
#   ③ 목록 칸 ↔ 완전성 칸 짝을 등기부·전단사로 고정해 새 목록 칸이 짝 없이 못 들어온다.
# --------------------------------------------------------------------------

from dataclasses import replace  # noqa: E402

from server.vwx.typemap import (  # noqa: E402  (섹션 지역 임포트 — 공용 헤더를 건드리지 않는다)
    CANDIDATES_PRESENTED_REASON,
    LIST_COMPLETENESS_COLUMNS,
    MODE_OPTIONS_COMPLETENESS_COLUMN,
    TYPE_CANDIDATES_COMPLETENESS_COLUMN,
    TYPE_TABLE_COLUMN_LABELS,
    TYPE_TABLE_COLUMNS,
    ListCompleteness,
    TypeResolution,
    TypeResolutionPlan,
    _incompleteness_reason,
    _library_axis,
    _library_list_completeness,
    _library_observed_axes,
    _mode_axis,
    _mode_list_completeness,
)
from server.vwx.verdicts import FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED  # noqa: E402

#: 감사 실측 형태의 라이브러리 — **선언 5모드**, 96ch 모드는 4번이다.
_R21_FIVE_MODE_LIBRARY = [
    (
        "MegaPointe",
        [("Mode 1", 24), ("Mode 2", 20), ("Mode 3", 48), ("Mode 4", 96), ("Mode 5", 64)],
    )
]


class _R21ShortModePort(LibraryRigPort):
    """DMXModes가 **선언 N · 실린 M**(M<N)인 콘솔. 감사 실측 모델 그대로.

    두 형태를 모두 만든다 — 처방이 어느 한쪽에만 걸리면 나머지가 사각으로 남는다:
      · `flag=True`  — responder 예산 절단(`truncated`가 선다).
      · `flag=False` — 플래그 없이 **계수만** 어긋난다. 구판이 전수로 읽던 형태다.
    `_channels`·`query_property`는 원본 `types`를 인덱스로 보므로 실린 행만 잘라도
    남은 인덱스의 판독은 실측과 같다.
    """

    def __init__(self, types, *, declared: int, carried: int, flag: bool, **kwargs):
        super().__init__(types, **kwargs)
        self._declared = declared
        self._carried = carried
        self._flag = flag

    def query_state(self, path: str) -> dict:
        state = super().query_state(path)
        if re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/\d+/{DMX_MODES_SEGMENT}", path):
            return {
                **state,
                "node": {**state["node"], "childCount": self._declared},
                "children": state["children"][: self._carried],
                "truncated": self._flag,
            }
        return state


def _r21_plan(port, *, mode: str | None, footprint: int | None = None, aliases=None):
    return resolve_fixture_types(
        [request("c1", mode=mode, footprint=footprint)],
        library_port=port,
        type_aliases=aliases or {},
        assumption_72=ASSUMPTION_72_GO,
    )


def _r21_short_mode_plan(*, flag: bool, mode: str | None = "Mode 1", footprint: int | None = 96):
    port = _R21ShortModePort(_R21_FIVE_MODE_LIBRARY, declared=5, carried=2, flag=flag)
    return _r21_plan(port, mode=mode, footprint=footprint)


@pytest.mark.parametrize("flag", [True, False])
def test_r21_a_partial_mode_list_is_never_presented_as_the_whole_choice(flag: bool):
    """[round21 R20-B 재현] **선언 5모드 중 2모드만 실린** 콘솔에서 도면이 96ch 모드를
    요구한다. 그 모드는 실린 2개에 **없다**(96ch는 미관측인 4번이다).

    구판: `mode_candidates`가 비지 않아 절단 가드를 지나가고 `incompleteness_kind`가
    서지 않아 `skipped_checks`가 **0건**이었다 — 조작자는 24ch 하나를 "고를 것 전부"로
    보고 96ch가 라이브러리에 있는 줄 모른다.

    죽이는 뮤테이션:
      · `row()`에서 `MODE_OPTIONS_COMPLETENESS_COLUMN` 행 제거 → ①이 실패한다.
      · `_mode_list_completeness`가 `complete=True`를 돌려주게 되돌림 → ②가 실패한다.
      · `_skipped_checks`의 관측 축 절(`_observed_incompleteness_kinds`) 제거 →
        ④가 실패한다(처분 축은 이 갈래에서 `None`이므로 구판 조건만으로는 안 난다).
      · `_mode_candidates`가 요청 이름 대신 `console_type.modes`를 그대로 돌려주게
        해도 ③이 실패한다(제시 수가 관측 수와 갈린다).
    """
    plan = _r21_short_mode_plan(flag=flag)
    payload = plan.to_dict()
    row = row_by_id(payload, "c1")

    # ① 목록 옆에 완전성 진술이 **항상** 있다.
    marker = row[MODE_OPTIONS_COMPLETENESS_COLUMN]
    assert MODE_OPTIONS_COMPLETENESS_COLUMN in TYPE_TABLE_COLUMNS

    # ② 부분 목록을 완전하다고 말하지 않는다 — 축까지 말한다.
    assert marker["complete"] is False
    assert marker["incompleteness_kind"] == FIXTURE_TYPE_LIBRARY_TRUNCATED
    assert marker["label"] == skipped_check_label(FIXTURE_TYPE_LIBRARY_TRUNCATED)

    # ③ 몇 개를 못 봤는지 **수로** 말한다. 계수는 R20-A의 것을 옮긴 것이다.
    assert (marker["declared_count"], marker["observed_count"]) == (5, 2)
    assert marker["unseen_count"] == 3
    assert marker["presented_count"] == len(row["mode_options"]) == 1

    # ④ **고지가 나간다** — 구판은 여기가 0건이었다.
    assert FIXTURE_TYPE_LIBRARY_TRUNCATED in skipped_kinds(payload)

    # ⑤ 도면이 요구한 96ch는 제시 목록에 **없다**. 그 사실이 ②·③과 함께 읽혀야
    #    조작자가 "목록에 없다"를 "라이브러리에 없다"로 오독하지 않는다.
    assert [option["channel_count"] for option in row["mode_options"]] == [24]
    assert row["designed_footprint"] == 96

    # ⑥ **처분 축은 건드리지 않았다.** 이 갈래는 여전히 확인 대기이고 배제 코드도
    #    `type_confirmation_pending`으로 남는다 — `incompleteness_kind`를 여기서
    #    세우면 `apply._unresolved_type_verdict`가 코드를 바꿔 round19 불변식
    #    (`confirmation_required` 참 ⇒ pending)이 깨진다.
    assert row["status"] == TYPE_NEEDS_CONFIRMATION
    assert row["confirmation_required"] is True
    assert plan.resolutions[0].incompleteness_kind is None


def test_r21_the_disposition_axis_stays_pending_on_a_truncated_option_list():
    """[round21 R20-B 형제 표면] 고지를 관측 축에서 낸 대가로 **배제 코드가 변하지 않는다.**

    round19 불변식 ㉢(`confirmation_required`가 참이면 배제 코드는
    `type_confirmation_pending`)을 이 새 갈래에서 실제로 재확인한다 — 처분 축을 넓혀
    고쳤다면 여기서 깨졌을 것이고, 그것이 이 SPEC이 열한 번 한 "고치려다 옆을 깨는" 형태다.

    죽이는 뮤테이션: `_resolve_one`의 마지막 반환에 `incompleteness_kind=...`를 더하면
    (= 처분 축을 넓히는 구현) 이 게이트가 실패한다.
    """
    from server.vwx.apply import _unresolved_type_verdict
    from server.vwx.verdicts import TYPE_CONFIRMATION_PENDING

    resolution = _r21_short_mode_plan(flag=True).resolutions[0]
    code, _reason = _unresolved_type_verdict(resolution)
    assert code == TYPE_CONFIRMATION_PENDING


# --------------------------------------------------------------------------
# 불변식 대조군 — "완전성이 불완전이라 말했는데 고지가 빈다"가 **구조적으로 불가능**하다.
# 코퍼스는 세 축(절단 · 판독 실패 · 행 폐기)과 두 절단 형태(플래그 · 계수)를 모두 밟는다.
# --------------------------------------------------------------------------


def _r21_discard_port():
    """모드 행 하나에 `i`가 없는 콘솔 — **폐기 축**. 절단이 아니다(목록은 안 잘렸다)."""

    class _Port(LibraryRigPort):
        def query_state(self, path: str) -> dict:
            state = super().query_state(path)
            if re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/\d+/{DMX_MODES_SEGMENT}", path):
                children = [dict(child) for child in state["children"]]
                children[-1].pop("i", None)
                return {**state, "children": children}
            return state

    return _Port(_R21_FIVE_MODE_LIBRARY)


#: (이름, 계획을 만드는 무인자 호출, 기대 축) — 축이 `None`이면 완전성을 주장할 수 있는 쪽.
_R21_COMPLETENESS_CORPUS = (
    ("clean", lambda: _r21_plan(LibraryRigPort(_R21_FIVE_MODE_LIBRARY), mode="Mode 1"), None),
    (
        "modes_truncated_flag",
        lambda: _r21_short_mode_plan(flag=True),
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
    ),
    (
        "modes_count_short",
        lambda: _r21_short_mode_plan(flag=False),
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
    ),
    # 요청 모드가 **없는** 갈래 — `_mode_candidates`가 절단된 튜플을 그대로 "전 모드"로
    # 돌려주던 자리다. 이 행이 없으면 부분집합 불변식 게이트가 그 갈래에서 공허해진다.
    (
        "no_requested_mode",
        lambda: _r21_short_mode_plan(flag=True, mode=None, footprint=None),
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
    ),
    (
        "modes_unreadable",
        lambda: _r21_plan(
            LibraryRigPort(_R21_FIVE_MODE_LIBRARY, modes_readable=False), mode="Mode 1"
        ),
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
    ),
    (
        "mode_rows_discarded",
        lambda: _r21_plan(_r21_discard_port(), mode="Mode 1"),
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
    ),
    (
        "library_truncated_flag",
        lambda: _r21_plan(LibraryRigPort(_R21_FIVE_MODE_LIBRARY, truncated=True), mode="Mode 1"),
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
    ),
)


def test_r21_the_completeness_corpus_reaches_every_axis():
    """대조군 건전성 — 코퍼스가 축 어휘 **전부**와 "완전" 쪽에 모두 닿는다.

    닿지 않는 축이 있으면 아래 불변식이 그 축에서 공허해진다. 축을 하나 더하면
    (`FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED`가 round21에 그랬듯) 코퍼스 없이는 실패한다.
    """
    axes = {axis for _name, _build, axis in _R21_COMPLETENESS_CORPUS}
    assert axes == {
        None,
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
    }
    import server.vwx.typemap as typemap_module

    declared = {
        getattr(typemap_module, kind_expr)
        for kind_expr, _reason, _extra in _r21_notice_axis_table()
    }
    assert axes - {None} <= declared, "고지 축 표가 코퍼스보다 좁다"


def _r21_notice_axis_table():
    """`_skipped_checks`의 고지 축 튜플을 **소스에서** 뽑는다 — 표를 베끼지 않는다."""
    tree = ast.parse(TYPEMAP_SOURCE)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "_skipped_checks"):
            continue
        for loop in ast.walk(node):
            if isinstance(loop, ast.For) and isinstance(loop.iter, ast.Tuple):
                rows_out = []
                for element in loop.iter.elts:
                    assert isinstance(element, ast.Tuple), ast.unparse(element)
                    kind, reason, extra = element.elts
                    rows_out.append((ast.unparse(kind), ast.unparse(reason), ast.unparse(extra)))
                return tuple(rows_out)
    raise AssertionError("_skipped_checks의 고지 축 루프를 찾지 못했다")


@pytest.mark.parametrize("name,build,axis", _R21_COMPLETENESS_CORPUS, ids=lambda v: str(v)[:24])
def test_r21_an_incomplete_marker_always_carries_a_notice(name: str, build, axis):
    """[round21 R20-B 불변식] 마커가 **불완전**이라 말하면 같은 payload에 고지가 있다.

    마커와 고지가 **한 근거**(`_library_axis`·`_mode_axis`)에서 나므로 둘이 갈릴 수 없다.
    반대 방향(완전하다고 말하면 그 축의 고지가 없다)도 함께 잰다 — 그것이 없으면
    "항상 고지한다"는 공허한 통과가 된다.

    죽이는 뮤테이션:
      · `_skipped_checks`의 `kind in self._observed_incompleteness_kinds()` 절 제거.
      · `_observed_incompleteness_kinds`가 `complete is None`까지 세게 바꿈(clean·
        근거 없음 갈래에서 없는 사실을 고지한다).
      · `_library_axis`·`_mode_axis`의 폐기 검사를 union **뒤로** 옮김(축이 절단으로
        뭉개져 `mode_rows_discarded` 행이 기대 축과 어긋난다).
    """
    payload = build().to_dict()
    kinds = set(skipped_kinds(payload))
    markers = [
        row[column]
        for row in rows(payload)
        for column in (TYPE_CANDIDATES_COMPLETENESS_COLUMN, MODE_OPTIONS_COMPLETENESS_COLUMN)
    ]
    incomplete = {
        marker["incompleteness_kind"] for marker in markers if marker["complete"] is False
    }
    assert incomplete <= kinds, (name, incomplete, kinds)
    if axis is None:
        assert incomplete == set(), name
        assert (
            kinds
            & {
                FIXTURE_TYPE_LIBRARY_TRUNCATED,
                FIXTURE_TYPE_LIBRARY_UNREADABLE,
                FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
            }
            == set()
        ), name
    else:
        assert axis in incomplete, name
        assert axis in kinds, name


def test_r21_the_notice_axis_table_and_the_reason_helper_do_not_diverge():
    """고지 축 표의 사유가 `_incompleteness_reason`이 내는 사유와 **같다**.

    같은 축의 사유를 두 자리에서 쓰면 한쪽만 고쳐져 마커와 고지가 다른 문장을 말한다.

    죽이는 뮤테이션: 표의 사유 상수 하나를 형제 상수로 바꾸면 실패한다.
    """
    import server.vwx.typemap as typemap_module

    for kind_expr, reason_expr, _extra in _r21_notice_axis_table():
        kind = getattr(typemap_module, kind_expr)
        reason = getattr(typemap_module, reason_expr)
        assert _incompleteness_reason(kind) == reason, kind_expr


def test_r21_the_three_axes_have_distinct_labels_and_reasons():
    """[round18 M24 형태] 축 라벨·사유를 **형제 축 문구로 바꿔도 안 죽는 공백**을 막는다.

    마커의 `label`은 `skipped_check_label(kind)`에서 오므로, 세 축이 서로 구별되는
    라벨·사유를 갖지 않으면 조작자는 절단·판독실패·폐기를 구별할 수 없고 조치를 고를 수
    없다(표적 스윕 / 재시도 / responder 확인 — 셋이 다르다).

    죽이는 뮤테이션: 어느 두 축의 라벨이나 사유를 같게 만들면 실패한다.
    """
    axes = (
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
    )
    labels = [skipped_check_label(kind) for kind in axes]
    reasons = [_incompleteness_reason(kind) for kind in axes]
    assert len(set(labels)) == len(axes), labels
    assert len(set(reasons)) == len(axes), reasons
    assert all(label.strip() for label in labels)


# --------------------------------------------------------------------------
# [HARD] 형제 표면 전수 — "목록을 제시하는데 그 목록이 완전한지 말하지 않는 자리"를
# `server/vwx/` **전 모듈**에서 뽑아 등기부와 전단사로 고정한다.
#
# 이것이 없으면 다음 라운드가 목록 칸을 하나 더 더할 때 완전성 칸을 또 빠뜨린다 —
# round19가 `mode_options`에서 한 일이 정확히 그것이다. 등기 분류는 둘뿐이다:
#   · `stated`  — 같은 산출물에 그 목록의 완전성을 말하는 칸이 있다(그 칸 이름을 적는다).
#   · `derived` — 콘솔 열거가 아니라 **이 산출물이 스스로 만든 것의 전수**다. 완전성은
#                 그 재료의 완전성이고, 재료 쪽 칸이 그것을 말한다(그 출처를 적는다).
# **모든 부재가 결함은 아니다** — 그 구별을 등기부가 진다.


# --------------------------------------------------------------------------


def _r21_list_sites() -> tuple[tuple[str, str, str], ...]:
    """dict 리터럴에 **리스트를 싣는** 자리를 `server/vwx/` 전 모듈에서 전수로 뽑는다."""
    found: set[tuple[str, str, str]] = set()
    for path in iter_vwx_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef):
                continue
            for node in ast.walk(function):
                if not isinstance(node, ast.Dict):
                    continue
                for key, value in zip(node.keys, node.values, strict=True):
                    if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                        continue
                    listish = isinstance(value, (ast.ListComp, ast.List)) or (
                        isinstance(value, ast.Call)
                        and getattr(value.func, "id", None) in {"list", "sorted", "tuple"}
                    )
                    if listish:
                        found.add((vwx_module_label(path), function.name, key.value))
    return tuple(sorted(found))


#: 증인의 **범위**까지 분류에 넣는다. 범위를 뭉개면 "같은 dict에 완전성 칸이 있다"와
#: "같은 모듈 어딘가에 그 말을 하는 생산자가 있다"가 구별되지 않고, 앞쪽이 요구하는
#: 강한 검사(형제 키 실재)를 뒤쪽 행이 통째로 면제받는다.
_R21_STATED = "stated_sibling_key"
_R21_STATED_PRODUCER = "stated_named_producer"
_R21_DERIVED = "derived"

#: (모듈, 함수, 목록 키, 분류, 완전성을 말하는 칸 이름 또는 그 목록의 출처).
_R21_LIST_SITES = (
    ("apply.py", "to_dict", "entries", _R21_DERIVED, "address_plan 자신이 만든 배정 전수"),
    ("apply.py", "to_dict", "exclusions", _R21_DERIVED, "이 계획이 배제한 대상 전수"),
    ("apply.py", "to_dict", "guidance", _R21_DERIVED, "고정 문장 목록 — 관측이 아니다"),
    # 점유자 목록은 콘솔 판독이다. 완전성은 `console_read_caveat`가 같은 payload에
    # `completeness`·`child_count`·`observed_count`·`missing_count`로 말한다 —
    # PRESERVE `prechk.Inventory`가 그 계수를 지므로 이 자리는 결함이 아니다.
    (
        "apply.py",
        "to_dict",
        "observed_occupants",
        _R21_STATED_PRODUCER,
        "apply.console_read_caveat",
    ),
    ("apply.py", "to_dict", "procedure", _R21_DERIVED, "이 계획이 만든 절차 전수"),
    ("apply.py", "to_dict", "results", _R21_DERIVED, "검증한 대상 전수"),
    ("apply.py", "to_dict", "warnings", _R21_DERIVED, "이 계획이 낸 경고 전수"),
    # FID 열거는 절단될 수 있다. 완전성은 같은 함수의 `read` 블록이
    # `complete`·`child_count`·`enumerated_count`·`unseen_count`·`recovery_boundary`로 말한다.
    ("patchplan.py", "_fid_safety_payload", "existing_fids", _R21_STATED, "read"),
    ("patchplan.py", "_vacuous_notice", "stage_one_axes", _R21_DERIVED, "닫힌 축 이름 목록"),
    (
        "patchplan.py",
        "assemble_sentences_or_defect",
        "fragments",
        _R21_DERIVED,
        "입력 문장 조각 전수",
    ),
    ("patchplan.py", "to_dict", "address_basis_notes", _R21_DERIVED, "이 계획이 낸 주석 전수"),
    ("patchplan.py", "to_dict", "candidates", _R21_DERIVED, "1단계 대조 산출의 전수"),
    ("patchplan.py", "to_dict", "columns", _R21_DERIVED, "표 열 이름 — 관측이 아니다"),
    ("patchplan.py", "to_dict", "entries", _R21_DERIVED, "이 계획이 만든 배정 전수"),
    ("patchplan.py", "to_dict", "exclusions", _R21_DERIVED, "이 계획이 배제한 대상 전수"),
    (
        "patchplan.py",
        "to_dict",
        "observed_occupants",
        _R21_STATED_PRODUCER,
        "apply.console_read_caveat",
    ),
    ("patchplan.py", "to_dict", "rows", _R21_DERIVED, "후보 하나에 한 행 — 후보 전수를 따른다"),
    ("patchplan.py", "to_dict", "selected", _R21_DERIVED, "이 계획이 고른 대상 전수"),
    ("patchplan.py", "to_dict", "skipped_checks", _R21_DERIVED, "미수행 판정 전수 — 고지 자체다"),
    ("patchplan.py", "to_dict", "target_exclusions", _R21_DERIVED, "이 계획이 배제한 대상 전수"),
    ("patchplan.py", "to_dict", "targets", _R21_DERIVED, "이 계획이 고른 대상 전수"),
    ("patchplan.py", "to_dict", "warnings", _R21_DERIVED, "이 계획이 낸 경고 전수"),
    ("report.py", "_design_overlaps", "members", _R21_DERIVED, "설계 픽스처 대조 산출"),
    ("report.py", "_diffs", "address_collision", _R21_DERIVED, "1단계 대조 산출"),
    ("report.py", "_diffs", "members", _R21_DERIVED, "1단계 대조 산출"),
    ("report.py", "_diffs", "missing_in_console", _R21_DERIVED, "1단계 대조 산출"),
    ("report.py", "_diffs", "quantity_mismatch", _R21_DERIVED, "1단계 대조 산출"),
    ("report.py", "_join_key_conflicts", "rows", _R21_DERIVED, "설계 행 대조 산출"),
    # 설계 측 관측이다(콘솔 열거가 아니다). 완전성은 같은 dict의
    # `candidate_row_count`·`dropped_row_count`·`scope_qualified`가 말한다.
    ("report.py", "to_dict", "observed_systems", _R21_STATED, "dropped_row_count"),
    # [round21 R20-B] 내가 소유하는 셋 — 완전성 칸을 같은 행에 싣는다.
    (
        "typemap.py",
        "row",
        "mode_candidates",
        _R21_STATED,
        MODE_OPTIONS_COMPLETENESS_COLUMN,
    ),
    ("typemap.py", "row", "mode_options", _R21_STATED, MODE_OPTIONS_COMPLETENESS_COLUMN),
    (
        "typemap.py",
        "row",
        "type_candidates",
        _R21_STATED,
        TYPE_CANDIDATES_COMPLETENESS_COLUMN,
    ),
    ("typemap.py", "to_dict", "columns", _R21_DERIVED, "표 열 이름 — 관측이 아니다"),
    ("typemap.py", "to_dict", "hard_stops", _R21_DERIVED, "해상 결과 전수를 따른다"),
    # 라이브러리 열거 자체. 완전성은 같은 dict의 `enumeration_incomplete`·`unseen_count`.
    ("typemap.py", "to_dict", "types", _R21_STATED, "enumeration_incomplete"),
)


def test_r21_the_list_site_registry_is_a_bijection_onto_server_vwx():
    """[round21 R20-B · HARD] 목록을 싣는 자리 표가 `server/vwx/` 전 모듈과 1:1이다.

    죽이는 뮤테이션:
      · `row()`에 목록 칸을 하나 더 더하면 등기 없이는 통과하지 못한다(= round19가
        `mode_options`를 무등기로 더한 형태가 여기서 잡힌다).
      · 등기부에서 어느 행을 지워도 아래 행삭제 프로브가 실패한다.
    """
    produced = _r21_list_sites()
    declared = tuple(sorted((module, func, key) for module, func, key, _c, _w in _R21_LIST_SITES))
    assert produced == declared, "목록 자리가 표와 다르다 — 등록할 행:\n" + "\n".join(
        f'    ("{m}", "{f}", "{k}", ..., ...),' for m, f, k in produced
    )
    assert {cls for _m, _f, _k, cls, _w in _R21_LIST_SITES} == {
        _R21_STATED,
        _R21_STATED_PRODUCER,
        _R21_DERIVED,
    }
    assert all(witness.strip() for *_head, witness in _R21_LIST_SITES)


@pytest.mark.parametrize("index", range(len(_R21_LIST_SITES)))
def test_r21_deleting_any_list_site_row_breaks_the_bijection(index: int):
    """행 삭제 프로브 — 등기부에서 어느 행을 지워도 프로덕션 전수와 어긋난다."""
    shrunk = _R21_LIST_SITES[:index] + _R21_LIST_SITES[index + 1 :]
    declared = tuple(sorted((module, func, key) for module, func, key, _c, _w in shrunk))
    assert declared != _r21_list_sites()


def _r21_dict_key_name(item: ast.expr, namespace: object) -> str | None:
    """dict 키의 **값**. 리터럴이 아니라 모듈 상수로 적힌 키까지 해석한다.

    이 저장소는 열 이름을 상수로 두는 것이 규율이다(`FOOTPRINT_UNVERIFIED_COLUMN`이
    선례). 리터럴만 세는 스캐너는 그 규율을 따른 칸을 **못 보고**, 그 사각이 곧
    "게이트가 있는데 통과한다"가 된다.
    """
    if isinstance(item, ast.Constant) and isinstance(item.value, str):
        return item.value
    if isinstance(item, ast.Name):
        value = getattr(namespace, item.id, None)
        return value if isinstance(value, str) else None
    return None


def _r21_sibling_keys(module: str, func: str, key: str) -> set[str]:
    """`func` 안에서 `key`를 싣는 **그 dict 리터럴**의 형제 키 전부."""
    import importlib

    namespace = importlib.import_module(f"server.vwx.{module[:-3]}")
    tree = ast.parse(Path("server/vwx", module).read_text(encoding="utf-8"))
    keys: set[str] = set()
    for function in ast.walk(tree):
        if not (isinstance(function, ast.FunctionDef) and function.name == func):
            continue
        for node in ast.walk(function):
            if not isinstance(node, ast.Dict):
                continue
            names = {
                name
                for name in (_r21_dict_key_name(item, namespace) for item in node.keys)
                if name is not None
            }
            if key in names:
                keys |= names
    return keys


def test_r21_every_stated_row_names_a_witness_that_actually_exists():
    """등기부의 증인이 **실재한다** — 산문으로 때우면 다음 라운드에 또 뚫린다.

    두 범위를 각각 다르게 잰다(뭉개면 강한 검사가 면제된다):
      · `stated_sibling_key`   — 증인이 그 목록을 싣는 **dict 리터럴의 형제 키**다.
      · `stated_named_producer` — 증인이 `<모듈>.<심볼>`로 **실재하는 생산자**다. 이
        범위가 따로 있는 이유: `patchplan`의 점유자 목록은 `apply`가 관측해 넘긴 것이라
        완전성을 말하는 생산자가 **다른 모듈**에 있다. 그 사실을 등기부가 말한다.

    죽이는 뮤테이션:
      · 어느 `stated_sibling_key` 행의 증인을 형제 키가 아닌 이름으로 바꾸면 실패한다.
      · `row()`에서 완전성 칸을 지우면 그 행 셋이 형제 키를 잃어 실패한다.
      · `apply.console_read_caveat`를 개명하면 모듈 증인 행 둘이 실패한다.
    """
    import importlib

    for module, func, key, cls, witness in _R21_LIST_SITES:
        if cls == _R21_STATED:
            siblings = _r21_sibling_keys(module, func, key)
            assert witness in siblings, (module, func, key, witness, sorted(siblings))
        elif cls == _R21_STATED_PRODUCER:
            producer_module, _, symbol = witness.rpartition(".")
            imported = importlib.import_module(f"server.vwx.{producer_module}")
            assert hasattr(imported, symbol), witness


def test_r21_every_list_key_in_a_produced_row_has_a_completeness_column():
    """[round21 R20-B · 처방③] `row()`에 목록 칸을 더하면 **완전성 칸도 함께** 넣게 된다.

    round19가 `mode_options`를 더하면서 그 완전성을 말할 자리를 만들지 않은 것이 R20-B의
    원인이었다. 그 규율을 표가 아니라 **산출물에서** 잰다: 실제로 만든 행의 리스트 값
    칸 전부가 `LIST_COMPLETENESS_COLUMNS`에 짝을 갖고, 그 짝이 표 열·라벨·행에 모두 있다.

    죽이는 뮤테이션:
      · `LIST_COMPLETENESS_COLUMNS`에서 `mode_options` 행 제거 → ①이 실패한다.
      · `TYPE_TABLE_COLUMNS`에서 완전성 열 제거 → ②가 실패한다.
      · `row()`에서 완전성 칸 제거 → ③이 실패한다.
    """
    payload = _r21_short_mode_plan(flag=True).to_dict()
    row = row_by_id(payload, "c1")
    list_keys = {key for key, value in row.items() if isinstance(value, list)}

    # ① 목록 칸 전부가 완전성 칸과 짝이다.
    assert list_keys == set(LIST_COMPLETENESS_COLUMNS), sorted(list_keys)

    for list_key, completeness_key in LIST_COMPLETENESS_COLUMNS.items():
        # ② 짝은 조작자 화면 표에 등재돼 있다(payload에만 있으면 사람은 못 본다).
        assert completeness_key in TYPE_TABLE_COLUMNS, list_key
        assert TYPE_TABLE_COLUMN_LABELS[completeness_key].strip()
        # ③ 그리고 행에 실제로 실린다 — 세 축을 말할 칸까지 함께.
        assert set(row[completeness_key]) == {
            "complete",
            "incompleteness_kind",
            "label",
            "declared_count",
            "observed_count",
            "presented_count",
            "unseen_count",
        }


def test_r21_row_cannot_be_assembled_without_a_completeness_statement():
    """[round21 R20-B · 처방①] `row()`은 완전성 진술을 **필수 키워드**로 받는다.

    이것이 처방의 핵심이다 — round19는 목록 칸을 더하면서 완전성 칸을 만들지 않을 수
    있었다. 이제 그 조립은 `TypeError`다. 계산 자리도 하나뿐이라는 것까지 소스에서 잰다.

    죽이는 뮤테이션:
      · 인자에 기본값(`= None` 등)을 주면 ①이 실패한다(= 빠뜨릴 수 있는 상태로 복귀).
      · 인자를 위치 인자로 바꾸면 ②가 실패한다(호출자가 순서로 넘기면 오배치가 조용하다).
      · 라이브러리 축을 행마다 만들게 흩으면 ③이 실패한다.
    """
    import inspect

    signature = inspect.signature(TypeResolution.row)
    parameter = signature.parameters["type_candidates_completeness"]

    # ① 기본값이 없다 — 빼면 조립이 실패한다.
    assert parameter.default is inspect.Parameter.empty
    # ② 키워드 전용이다.
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError):
        TypeResolution(request=request("c1"), status=TYPE_NEEDS_CONFIRMATION, reason="").row()

    # ③ 라이브러리 축을 **만드는** 함수는 하나이고, 그 축을 쓰는 자리는 전부 그 함수를
    #    부른다. 구판은 텍스트 등장 횟수를 셌는데, 그 수는 정당한 소비자가 늘 때마다
    #    올라가므로 게이트가 "늘리지 마라"를 요구하게 된다 — 요구사항이 아니다.
    #    요구사항은 **축을 두 번 계산하지 않는 것**이라, 정의 1개와 호출자 등기로 잰다.
    # [round23 R22-E] 호출자가 둘 늘었다: 확정 게이트와 점유폭 부재 전제. 둘 다 **행에
    #    실리는 그 진술 그대로**를 읽는다 — 표시와 처분이 다른 식을 보면 이번 라운드가
    #    고발당한 갈림이 그대로 재발한다.
    # [round24 R23-1] `_resolve_one`이 빠지고 `_absence_unverifiable`이 들어왔다. 부재
    #    단정 가드 **셋**(타입 부재 · 모드 부재 · 점유폭 부재)이 각자 축을 계산하던 것을
    #    한 자리로 모은 결과다 — 자리가 셋이면 다음 라운드에 그중 하나만 고쳐진다.
    tree = ast.parse(TYPEMAP_SOURCE)
    assert (
        len(
            [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "_library_list_completeness"
            ]
        )
        == 1
    )
    axis_callers = {
        function.name
        for function in ast.walk(tree)
        if isinstance(function, ast.FunctionDef)
        and any(
            isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "_library_list_completeness"
            for node in ast.walk(function)
        )
    }
    # [round25 R24-1] `_absence_unverifiable`이 빠지고 `_library_unverifiable`이 들어왔다.
    #    루트 절반을 이름 있는 함수로 **분해**한 결과이고(복사가 아니다 — 합성이 이 함수를
    #    부른다), 축 계산 자리는 여전히 하나다. 사유 문장이 "루트가 막았나"를 물어야 하는데
    #    `incompleteness_kind`로는 물을 수 없어서(세 축 이름을 루트와 모드가 공유한다)
    #    질문할 자리를 만든 것이다.
    assert axis_callers == {
        "to_dict",
        "_observed_incompleteness_kinds",
        "_confirmable_lists",
        "_library_unverifiable",
    }, axis_callers
    callers = {
        function.name
        for function in ast.walk(tree)
        if isinstance(function, ast.FunctionDef)
        and any(
            isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "row"
            for node in ast.walk(function)
        )
    }
    assert callers == {"to_dict"}, callers


@pytest.mark.parametrize("name,build,axis", _R21_COMPLETENESS_CORPUS, ids=lambda v: str(v)[:24])
def test_r21_the_presented_mode_list_is_a_subset_of_the_enumerated_modes(name: str, build, axis):
    """[round21 R20-B · 파생 건전성] `mode_candidates ⊆ presented_type.modes`.

    `mode_options_completeness`는 `presented_type`에서 파생하므로, 제시된 목록에
    그 열거 밖의 원소가 섞이면 완전성 진술이 그 원소를 **덮지 못한다** — 마커가 있는데
    거짓인 상태가 된다. `_mode_candidates`가 지는 불변식을 여기서 실행으로 잰다.

    죽이는 뮤테이션: `_mode_candidates`가 `console_type.modes` 밖의 `LibraryMode`를
    만들어 넣게 하면(예: 요청 모드 이름으로 합성) 실패한다.
    """
    for resolution in build().resolutions:
        presented = resolution.presented_type
        if presented is None:
            # 열거를 거치지 않았다면 목록도 비어 있어야 한다 — 완전성이 `None`인 것과 짝이다.
            assert resolution.mode_candidates == (), name
            assert resolution.mode_options_completeness.complete is None, name
            continue
        assert set(resolution.mode_candidates) <= set(presented.modes), name


def test_r21_no_basis_is_not_the_same_as_nothing_missing():
    """[round21 R20-B] `complete is None`(모른다)과 `False`(못 본 것이 있다)를 가른다.

    선언 총계를 못 읽은 스냅샷에서 `True`를 내면 **플래그 단독 전수 주장**이 되고
    (PRESERVE `prechk.inventory` 독스트링 2번이 금지한 형태), `False`를 내면 없는
    미관측을 단정한다. 그래서 `None`이고, `None`에서는 **고지도 나가지 않는다** —
    모른다를 "열거를 못 봤다"로 적으면 없는 사실을 말하는 것이다.

    죽이는 뮤테이션:
      · `_mode_list_completeness`/`_library_list_completeness`의 `child_count is None`
        갈래를 `True`로 되돌리면 ①·②가 실패한다.
      · `_observed_incompleteness_kinds`가 `complete is not True`를 세게 바꾸면 ③이 실패한다.
    """
    no_count = LibraryType(index=1, name="MegaPointe", modes=(LibraryMode(index=1, name="Mode 1"),))
    assert no_count.mode_child_count is None

    # ① 총계를 모르면 완전을 주장하지 않는다.
    statement = _mode_list_completeness(no_count)
    assert statement.complete is None
    assert statement.incompleteness_kind is None
    assert statement.unseen_count is None

    # ② 라이브러리 축도 같다.
    library_statement = _library_list_completeness(FixtureTypeLibrary(types=(no_count,)))
    assert library_statement.complete is None
    assert library_statement.incompleteness_kind is None

    # ③ 그리고 그 상태에서 고지는 나가지 않는다 — 모른다를 없다로 말하지 않는다.
    plan = TypeResolutionPlan(
        assumption_72=ASSUMPTION_72_GO,
        library=FixtureTypeLibrary(types=(no_count,)),
        resolutions=(),
    )
    assert skipped_kinds(plan.to_dict()) == []

    # ④ 축이 서면 `False`다 — 삼치가 실제로 세 값을 낸다(공허 통과 차단).
    truncated = LibraryType(
        index=1,
        name="MegaPointe",
        modes=(LibraryMode(index=1, name="Mode 1"),),
        mode_child_count=5,
        returned_mode_row_count=1,
        modes_enumerated_count=1,
    )
    assert _mode_list_completeness(truncated).complete is False
    complete = LibraryType(
        index=1,
        name="MegaPointe",
        modes=(LibraryMode(index=1, name="Mode 1"),),
        mode_child_count=1,
        returned_mode_row_count=1,
        modes_enumerated_count=1,
    )
    assert _mode_list_completeness(complete).complete is True

    # ⑤ `presenting()`은 **판정을 바꾸지 않는다** — 행마다 실린 원소 수만 다르다.
    #    이 진술이 행 지역이라고 판정까지 행 지역이 되면 같은 라이브러리에 두 판정이 생긴다.
    statement = ListCompleteness(complete=False, incompleteness_kind=FIXTURE_TYPE_LIBRARY_TRUNCATED)
    assert statement.presenting(7).presented_count == 7
    assert statement.presenting(7).complete is False
    assert statement.presenting(0) == replace(statement, presented_count=0)


@pytest.mark.parametrize("index", range(len(_R21_COMPLETENESS_CORPUS)))
def test_r21_deleting_any_corpus_row_loses_axis_coverage_or_a_scenario(index: int):
    """코퍼스 행삭제 프로브 — 어느 행을 지워도 축 전수 또는 시나리오 수가 줄어든다.

    대조군을 조용히 좁히는 것이 이 SPEC의 반복 실패 하나다(round18 M24 계열).
    """
    shrunk = _R21_COMPLETENESS_CORPUS[:index] + _R21_COMPLETENESS_CORPUS[index + 1 :]
    axes = {axis for _name, _build, axis in shrunk}
    full = {axis for _name, _build, axis in _R21_COMPLETENESS_CORPUS}
    assert axes != full or len(shrunk) != len(_R21_COMPLETENESS_CORPUS)


#: 축 채널 **둘**. 뜻이 다르므로 함수도 둘이다 — 뭉개면 한쪽이 거짓이 된다:
#:   · 단일 슬롯(`_library_axis`·`_mode_axis`) — 마커의 `incompleteness_kind`는 칸이
#:     하나라 **우선순위**로 하나를 고른다(좁은 축이 먼저).
#:   · 집합(`_library_observed_axes`) — 고지는 동시에 참인 축을 **전부** 내야 한다.
#: 둘이 갈리면 같은 스냅샷을 마커는 폐기, 고지는 절단이라 부를 수 있다.
_R21_AXIS_SNAPSHOTS = (
    ("clean", FixtureTypeLibrary(types=(), child_count=0, returned_row_count=0)),
    ("root_unreadable", FixtureTypeLibrary(available=False)),
    ("root_truncated_flag", FixtureTypeLibrary(types=(), truncated=True)),
    (
        "root_count_short",
        FixtureTypeLibrary(types=(), child_count=3, returned_row_count=1, enumerated_count=1),
    ),
    ("root_rows_discarded", FixtureTypeLibrary(types=(), unusable_row_count=2)),
    (
        "root_discarded_and_truncated",
        FixtureTypeLibrary(types=(), truncated=True, unparsable_row_count=1),
    ),
    (
        "modes_unreadable",
        FixtureTypeLibrary(
            types=(LibraryType(index=1, name="A", modes_available=False),),
            child_count=1,
            returned_row_count=1,
        ),
    ),
    (
        "modes_truncated",
        FixtureTypeLibrary(
            types=(LibraryType(index=1, name="A", modes=(), modes_truncated=True),),
            child_count=1,
            returned_row_count=1,
        ),
    ),
    (
        "mode_rows_discarded",
        FixtureTypeLibrary(
            types=(LibraryType(index=1, name="A", modes=(), unusable_mode_row_count=1),),
            child_count=1,
            returned_row_count=1,
        ),
    ),
)


@pytest.mark.parametrize("name,library", _R21_AXIS_SNAPSHOTS, ids=lambda v: str(v)[:20])
def test_r21_the_single_slot_axis_never_contradicts_the_axis_set(name: str, library):
    """[round21 R20-B · 형제 채널 일치] 단일 슬롯 축은 **항상 집합의 원소**다.

    마커는 축 하나를 고르고 고지는 전부를 내지만, 고른 하나가 집합에 없으면 조작자는
    마커와 고지를 묶을 수 없다. 폐기·절단이 **동시에 참인** 스냅샷까지 코퍼스에 있다.

    죽이는 뮤테이션:
      · `_library_axis`의 폐기 검사를 union **뒤로** 옮김 → 폐기 전용 스냅샷에서 슬롯이
        `TRUNCATED`가 되는데 집합에는 `ROWS_DISCARDED`만 있어 ①이 실패한다.
      · `_library_observed_axes`의 어느 disjunct를 지우면 ①·②가 실패한다.
      · `_library_observed_axes`가 union 프로퍼티(`enumeration_incomplete`)를 쓰게 바꾸면
        폐기 전용 스냅샷에서 `TRUNCATED`가 섞여 ③이 실패한다.
    """
    axes = _library_observed_axes(library)
    slot = _library_axis(library)

    # ① 고른 하나는 집합 안에 있다.
    if slot is not None:
        assert slot in axes, (name, slot, sorted(axes))
    for entry in library.types:
        mode_slot = _mode_axis(entry)
        if mode_slot is not None:
            assert mode_slot in axes, (name, mode_slot, sorted(axes))

    # ② 집합이 비면 어느 슬롯도 서지 않는다(그 역도 위 ①이 진다).
    if not axes:
        assert slot is None, name
        assert all(_mode_axis(entry) is None for entry in library.types), name

    # ③ 축은 뭉개지지 않는다 — 폐기만 참인 스냅샷에 절단이 섞이지 않는다.
    if name in {"root_rows_discarded", "mode_rows_discarded"}:
        assert axes == {FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED}, (name, sorted(axes))
    if name == "root_discarded_and_truncated":
        assert axes == {
            FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
            FIXTURE_TYPE_LIBRARY_TRUNCATED,
        }, sorted(axes)


def test_r21_the_completeness_helpers_delegate_the_axis_and_never_read_flags():
    """마커의 축이 `_library_axis`·`_mode_axis`에서만 온다 — 플래그를 직접 보지 않는다.

    직접 보면 순서 규율(폐기가 union보다 앞)을 우회해 폐기가 절단으로 뭉개진다.

    죽이는 뮤테이션: `_mode_list_completeness`가 `console_type.modes_truncated`를 직접
    보게 하면 실패한다.
    """
    tree = ast.parse(TYPEMAP_SOURCE)
    for helper in ("_mode_list_completeness", "_library_list_completeness"):
        body = next(
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == helper
        )
        assert "_axis(" in body, helper
        assert "truncated" not in body, helper
        assert "rows_discarded" not in body, helper


def test_r21_the_notice_basis_is_the_row_marker_not_only_the_library_scan():
    """[round21 R20-B] 고지의 근거는 **행이 실은 목록의 완전성**이다 — 형제 절과 겹치지 않는다.

    `_skipped_checks`에는 관측 축 절이 둘이다: `_library_observed_axes`(라이브러리 스냅샷을
    직접 훑는 형제 절, R20-D)와 `_observed_incompleteness_kinds`(행 마커에서 나는 내 절).
    프로덕션 경로에서 둘은 같은 결론을 내지만 **근거가 다르다** — 여기서 그 차이를 실측한다:
    라이브러리 스냅샷은 깨끗하고 행이 실은 `presented_type`만 절단인 계획을 직접 조립하면,
    형제 절은 그것을 볼 수 없고 마커만이 안다. 마커가 불완전이라 말했는데 고지가 비면
    R20-B가 되돌아온 것이다.

    죽이는 뮤테이션: `_skipped_checks`에서 `kind in self._observed_incompleteness_kinds()`
    절을 지우면 실패한다(형제 절은 이 입력을 보지 못한다).
    """
    truncated_type = LibraryType(
        index=1,
        name="MegaPointe",
        modes=(LibraryMode(index=1, name="Mode 1", channel_count=24),),
        mode_child_count=5,
        modes_enumerated_count=1,
        returned_mode_row_count=1,
    )
    clean_library = FixtureTypeLibrary(types=(), child_count=0, returned_row_count=0)
    # 형제 절이 이미 이 입력을 보고 있으면 이 게이트가 공허해진다 — 그것부터 확인한다.
    assert _library_observed_axes(clean_library) == frozenset()

    plan = TypeResolutionPlan(
        assumption_72=ASSUMPTION_72_GO,
        library=clean_library,
        resolutions=(
            TypeResolution(
                request=request("c1"),
                status=TYPE_NEEDS_CONFIRMATION,
                reason=CANDIDATES_PRESENTED_REASON,
                mode_candidates=truncated_type.modes,
                presented_type=truncated_type,
            ),
        ),
    )
    payload = plan.to_dict()
    marker = row_by_id(payload, "c1")[MODE_OPTIONS_COMPLETENESS_COLUMN]
    assert marker["complete"] is False
    assert marker["incompleteness_kind"] == FIXTURE_TYPE_LIBRARY_TRUNCATED
    assert FIXTURE_TYPE_LIBRARY_TRUNCATED in skipped_kinds(payload)


@pytest.mark.parametrize("name,library", _R21_AXIS_SNAPSHOTS, ids=lambda v: str(v)[:20])
def test_r21_incompleteness_is_false_exactly_when_an_axis_is_named(name: str, library):
    """[round21 R20-B · 등가 근거] `complete is False` ⟺ `incompleteness_kind is not None`.

    이 쌍-함의를 **못박아 두는 것**이 처방이다. 못박히면 `_observed_incompleteness_kinds`의
    `complete is False and kind is not None`을 `complete is not True and kind is not None`으로
    바꾼 뮤턴트가 **등가**임이 코드로 증명된다(둘 중 어느 절도 혼자 못 쓸 정보를 더하지 않는다).
    못박히지 않으면 그 뮤턴트가 "모른다"를 "못 봤다"로 바꾸는 진짜 결함이 될 수 있다.

    죽이는 뮤테이션: `_mode_list_completeness`가 축이 있는데 `complete=None`을 내게 하거나
    (또는 축이 없는데 `False`를 내게) 하면 실패한다.
    """
    for statement in (
        _library_list_completeness(library),
        *(_mode_list_completeness(entry) for entry in library.types),
    ):
        assert (statement.complete is False) == (statement.incompleteness_kind is not None), (
            name,
            statement,
        )


@pytest.mark.parametrize("index", range(len(_R21_AXIS_SNAPSHOTS)))
def test_r21_deleting_any_axis_snapshot_row_loses_a_configuration(index: int):
    """축 스냅샷 표 행삭제 프로브 — 어느 행을 지워도 잃는 구성이 있다.

    특히 **폐기·절단 동시 참** 행이 사라지면 "축을 뭉개지 않는다"를 아무도 재지 않는다.
    """
    assert _R21_COMBINED_AXIS_INDEX >= 0, "폐기·절단이 동시에 참인 스냅샷이 표에서 사라졌다"
    shrunk = _R21_AXIS_SNAPSHOTS[:index] + _R21_AXIS_SNAPSHOTS[index + 1 :]
    names = {name for name, _library in shrunk}
    assert names != {name for name, _library in _R21_AXIS_SNAPSHOTS}
    combined = [name for name, library in shrunk if len(_library_observed_axes(library)) >= 2]
    if index == _R21_COMBINED_AXIS_INDEX:
        # 그 행이 **유일한** 조합 스냅샷이다 — 지우면 "축을 뭉개지 않는다"를 아무도 재지 않는다.
        assert combined == [], "조합 스냅샷이 둘이면 이 프로브가 공허하다"
    else:
        assert combined, "조합 스냅샷이 표에서 사라졌다"


#: 폐기·절단이 **동시에 참인** 스냅샷의 자리. 위 프로브가 그 행의 소실을 특별히 짚는다.
_R21_COMBINED_AXIS_INDEX = next(
    (
        index
        for index, (_name, library) in enumerate(_R21_AXIS_SNAPSHOTS)
        if len(_library_observed_axes(library)) >= 2
    ),
    -1,
)


#: 이번 반영이 세운 **대조군 이름 등기부**. 이름을 지우거나 개명하면 아래 게이트가 실패한다 —
#: round19의 "근거 칸이 실재하는 테스트를 가리킨다"와 같은 장치다. 대조군을 조용히 없애는 것이
#: 이 SPEC의 반복 실패 하나이므로, 대조군 자신도 등기 대상이다.
_R21_GATE_REGISTRY = (
    ("재현", "test_r21_a_partial_mode_list_is_never_presented_as_the_whole_choice"),
    ("처분 축 불변", "test_r21_the_disposition_axis_stays_pending_on_a_truncated_option_list"),
    ("코퍼스 건전성", "test_r21_the_completeness_corpus_reaches_every_axis"),
    ("마커⇒고지 불변식", "test_r21_an_incomplete_marker_always_carries_a_notice"),
    ("마커 근거 구별", "test_r21_the_notice_basis_is_the_row_marker_not_only_the_library_scan"),
    ("사유 발산 차단", "test_r21_the_notice_axis_table_and_the_reason_helper_do_not_diverge"),
    ("라벨 축 구별성", "test_r21_the_three_axes_have_distinct_labels_and_reasons"),
    ("목록 자리 전단사", "test_r21_the_list_site_registry_is_a_bijection_onto_server_vwx"),
    ("증인 실재", "test_r21_every_stated_row_names_a_witness_that_actually_exists"),
    ("목록↔완전성 짝", "test_r21_every_list_key_in_a_produced_row_has_a_completeness_column"),
    ("필수 인자 구조", "test_r21_row_cannot_be_assembled_without_a_completeness_statement"),
    ("부분집합 불변식", "test_r21_the_presented_mode_list_is_a_subset_of_the_enumerated_modes"),
    ("삼치 구별", "test_r21_no_basis_is_not_the_same_as_nothing_missing"),
    ("등가 근거 쌍-함의", "test_r21_incompleteness_is_false_exactly_when_an_axis_is_named"),
    ("축 채널 무모순", "test_r21_the_single_slot_axis_never_contradicts_the_axis_set"),
    ("축 위임", "test_r21_the_completeness_helpers_delegate_the_axis_and_never_read_flags"),
    # 행삭제 프로브와 등기 게이트 자신도 등기 대상이다 — 표를 좁히는 것을 막는 장치가
    # 표 밖에 있으면 그 장치부터 지워진다.
    ("목록 자리 행삭제", "test_r21_deleting_any_list_site_row_breaks_the_bijection"),
    ("코퍼스 행삭제", "test_r21_deleting_any_corpus_row_loses_axis_coverage_or_a_scenario"),
    ("축 스냅샷 행삭제", "test_r21_deleting_any_axis_snapshot_row_loses_a_configuration"),
    ("대조군 등기 실재", "test_r21_every_registered_gate_actually_exists_and_is_collected"),
    ("대조군 등기 행삭제", "test_r21_deleting_any_gate_registry_row_breaks_the_bijection"),
    ("왕복 비용 0", "test_r21_the_completeness_statement_costs_no_console_round_trip"),
)


def test_r21_every_registered_gate_actually_exists_and_is_collected():
    """[round21 R20-B] 등기된 대조군이 **실재하고 수집된다**.

    대조군을 지우거나 개명해 무력화하는 것을 여기서 잡는다 — 프로덕션 뮤턴트만 재고
    대조군 자신의 소실을 아무도 재지 않으면, 다음 라운드는 게이트가 있다고 믿으면서
    비어 있는 파일을 물려받는다.

    죽이는 뮤테이션:
      · 어느 등기 대조군 함수 이름을 `_disabled_...`로 바꾸면 ①이 실패한다.
      · 등기부에서 행을 지우면 ②가 실패한다(내 섹션의 `test_r21_` 전수와 어긋난다).
    """
    module = globals()
    for topic, gate in _R21_GATE_REGISTRY:
        # ① 이름이 실재하고 호출 가능하다.
        assert callable(module.get(gate)), (topic, gate)
        assert topic.strip()

    # ② 등기부가 **이 섹션의** `test_r21_` 전수와 1:1이다. 섹션 경계는 형제 섹션 머리말로
    #    닫는다 — 뒤에 형제가 섹션을 덧붙여도 내 등기부가 그 이름을 요구하지 않는다.
    text = Path("server/tests/test_autopatch_types.py").read_text(encoding="utf-8")
    header = "# --- round21 목록 완전성 침묵 차단 (ModeSilence) ---"
    start = text.index(header)
    following = text.find("\n# --- round21 ", start + len(header))
    first_line = text[:start].count("\n") + 1
    last_line = text[:following].count("\n") + 1 if following != -1 else text.count("\n") + 1
    mine = {
        node.name
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_r21_")
        and first_line <= node.lineno <= last_line
    }
    assert mine == {gate for _topic, gate in _R21_GATE_REGISTRY}, sorted(
        mine ^ {gate for _topic, gate in _R21_GATE_REGISTRY}
    )


def test_r21_the_completeness_statement_costs_no_console_round_trip():
    """[round21 R20-B · 왕복 비용] 완전성 진술은 **추가 질의 0회**다.

    처방 ⓐ와 같은 근거다: 필요한 계수(`childCount` · 반환 행 수)는 이미 읽은 스냅샷에
    들어 있고, 마커는 그것을 메모리에서 옮긴다. 조작자 화면 조립(`to_dict`)이 포트를 한
    번이라도 더 부르면 이 처방은 비용 제약을 깬 것이다 — 표적 스윕을 전수 스윕 대신 고른
    것과 같은 규율이 노출 쪽에도 걸린다.

    죽이는 뮤테이션: `_mode_list_completeness`가 채널 수를 다시 읽는 구현으로 바뀌면
    (또는 `row()`이 포트를 잡고 있으면) 호출 수가 늘어 실패한다.
    """
    port = _R21ShortModePort(_R21_FIVE_MODE_LIBRARY, declared=5, carried=2, flag=True)
    plan = _r21_plan(port, mode="Mode 1", footprint=96)
    after_resolve = (len(port.state_calls), len(port.property_calls))

    payload = plan.to_dict()
    assert (len(port.state_calls), len(port.property_calls)) == after_resolve

    # 진술은 실제로 비어 있지 않다 — 0회 주장이 공허하지 않다.
    marker = row_by_id(payload, "c1")[MODE_OPTIONS_COMPLETENESS_COLUMN]
    assert (marker["complete"], marker["unseen_count"]) == (False, 3)

    # 두 번 조립해도 늘지 않는다(캐시가 아니라 파생임을 잰다).
    plan.to_dict()
    assert (len(port.state_calls), len(port.property_calls)) == after_resolve


@pytest.mark.parametrize("index", range(len(_R21_GATE_REGISTRY)))
def test_r21_deleting_any_gate_registry_row_breaks_the_bijection(index: int):
    """대조군 등기부 행삭제 프로브."""
    shrunk = _R21_GATE_REGISTRY[:index] + _R21_GATE_REGISTRY[index + 1 :]
    assert {gate for _topic, gate in shrunk} != {gate for _topic, gate in _R21_GATE_REGISTRY}


# ==========================================================================
# --- round21 슬롯 미확립 행 계수 (SlotDiscard) ---
#
# [round20 R20-D] `typemap`은 열거 응답의 행을 **계수 없이** 버렸다:
#   `read_fixture_type_library`: `if index is None or not listed: continue`
#   `_read_type`:                `if mode_index is None: continue`
# 그래서 *"슬롯이 확립되지 않았다"*가 *"라이브러리에 없다"*로 바뀌었고, 목록이 잘린 것이
# 아니므로 `truncated`도 서지 않아 어느 축에도 걸리지 않았다.
#
# 결정적 대조: **같은 스냅샷**을 형제 `patchplan._existing_fids_from_console`에 먹이면
# `complete=False` + "슬롯 번호가 없거나 중복인 행 3개를 쓰지 못했다"를 낸다. 같은 형태,
# 반대 처리 — 그 비대칭 자체를 아래 `test_r21_both_readers_treat_the_same_snapshot_alike`가
# 대조군으로 고정한다.
#
# 세 축은 **조치가 다르므로** 끝까지 갈라 둔다(형제 `patchplan.ExistingFidRead`가 이미
# 그렇게 센다):
#   절단(`unseen_count`)      — 목록이 예산에 잘렸다        → 표적 스윕
#   폐기(`unusable_row_count`) — 행은 왔는데 슬롯 번호가 없다 → responder 확인
#   판독 실패(`*_unreadable`)  — 값을 못 읽었다              → 재시도
# ==========================================================================


#: M8 라이브 세션 실측 형태(2026-08-08) — `Patch/FixtureTypes` childCount=3.
_R21_THREE_TYPE_LIBRARY = [
    ("Robin MMX Spot", [("Mode 1", 24), ("Mode 2", 20), ("Mode 3", 18), ("Mode 4", 16)]),
    ("FixtureType 2", [("Default", 12)]),
    ("Robin LEDBeam 350", [("Mode 1", 16), ("Mode 2", 14), ("Mode 3", 12)]),
]


class _R21DiscardPort(LibraryRigPort):
    """열거 응답의 행 일부가 **슬롯 번호(`i`)를 갖고 있지 않은** 포트.

    `ok=true`이고 목록도 끝까지 온다 — 절단도 판독 실패도 아니다. responder
    `safe_children`의 `probe_slots` 통째 nil / per-child `slot_confirms` 폴백이 실제로
    만드는 스냅샷이고, PRESERVE `server/prechk/inventory.py` 독스트링이 슬롯 부재를
    "documented responder behaviour rather than a hypothesis"라 못박은 그 형태다.

    `declared_extra_*`는 **절단 축**을 따로 켠다(선언 총계만 늘려 열거를 짧게 만든다) —
    폐기와 절단이 **동시에 참인** 입력을 만들기 위한 것이다.
    """

    def __init__(
        self,
        types,
        *,
        slotless_types=(),
        slotless_modes=(),
        junk_type_rows=0,
        junk_mode_rows=0,
        duplicate_type_slot=None,
        duplicate_mode_slot=None,
        declared_extra_types=0,
        declared_extra_modes=0,
        **kwargs,
    ):
        super().__init__(types, **kwargs)
        self.slotless_types = frozenset(slotless_types)
        self.slotless_modes = frozenset(slotless_modes)
        self.junk_type_rows = junk_type_rows
        self.junk_mode_rows = junk_mode_rows
        self.duplicate_type_slot = duplicate_type_slot
        self.duplicate_mode_slot = duplicate_mode_slot
        self.declared_extra_types = declared_extra_types
        self.declared_extra_modes = declared_extra_modes

    @staticmethod
    def _mangle(children, slotless, junk, duplicate, declared_extra, node):
        rows = [dict(row) for row in children]
        for row in rows:
            if row.get("i") in slotless:
                row.pop("i")
        if duplicate is not None:
            rows.append(dict(next(row for row in children if row.get("i") == duplicate)))
        rows.extend(["not-a-mapping"] * junk)
        declared = dict(node)
        declared["childCount"] = declared["childCount"] + declared_extra
        return rows, declared

    def query_state(self, path: str) -> dict:
        state = super().query_state(path)
        if state.get("ok") is not True:
            return state
        if path == FIXTURE_TYPE_LIBRARY_ROOT:
            rows, node = self._mangle(
                state["children"],
                self.slotless_types,
                self.junk_type_rows,
                self.duplicate_type_slot,
                self.declared_extra_types,
                state["node"],
            )
            return {**state, "children": rows, "node": node}
        if path.endswith(f"/{DMX_MODES_SEGMENT}"):
            rows, node = self._mangle(
                state["children"],
                self.slotless_modes,
                self.junk_mode_rows,
                self.duplicate_mode_slot,
                self.declared_extra_modes,
                state["node"],
            )
            return {**state, "children": rows, "node": node}
        return state


class _R21RawLibraryPort:
    """`Patch/FixtureTypes` 응답 하나만 돌려주는 최소 포트.

    자식 조회가 **한 번도 일어나지 않음**을 구조적으로 증명한다 — 전 행이 폐기되면
    `_read_type`이 호출될 이유가 없고, 호출되면 여기서 즉시 터진다.
    """

    def __init__(self, children, child_count):
        self.children = children
        self.child_count = child_count

    def query_state(self, path: str) -> dict:
        if path != FIXTURE_TYPE_LIBRARY_ROOT:
            raise AssertionError(f"폐기된 행의 자식을 조회했다: {path}")
        return {
            "ok": True,
            "path": path,
            "node": {"name": "FixtureTypes", "childCount": self.child_count},
            "children": self.children,
            "truncated": False,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        raise AssertionError(f"폐기된 행의 프로퍼티를 조회했다: {path}")


class _R21FidPort:
    """형제 리더(`patchplan._existing_fids_from_console`)에 **같은 스냅샷**을 먹이는 포트."""

    def __init__(self, children, child_count):
        self.children = children
        self.child_count = child_count

    def query_state(self, path: str) -> dict:
        return {
            "ok": True,
            "path": path,
            "node": {"childCount": self.child_count},
            "children": self.children,
            "truncated": False,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        return {"ok": True, "path": path, "value": int(path.rsplit("/", 1)[1])}


def _r21_text(payload: object) -> str:
    """payload 전체를 사람이 읽는 문자열로 — 어느 칸에 실렸든 문장을 잡는다."""
    return repr(payload)


def _r21_library(**kwargs):
    return read_fixture_type_library(_R21DiscardPort(**kwargs), read_channel_counts=True)


# --- 감사 실증 ① 타입 3종 전부 `i` 없음 -----------------------------------


def test_r21_a_library_whose_rows_all_lack_slot_numbers_is_not_called_absent():
    """[round20 R20-D 실증①] 라이브러리는 **온전히 있다** — 부재를 단정하지 않는다.

    구판 산출: `library_absent` + `fixture_type_not_in_library` +
    "콘솔에서 GDTF 라이브러리 임포트를 먼저 수행해야". 세 문장 전부 거짓이었다.

    죽이는 뮤테이션:
      · `read_fixture_type_library`의 `unusable_rows += 1`을 지우면 `rows_discarded`가
        0이 되어 `_library_axis`가 `None`을 돌려주고 `library_absent`로 되돌아간다.
      · `_library_axis`의 폐기 갈래를 지워도 같다.
    """
    from server.vwx.typemap import LIBRARY_ROWS_DISCARDED_REASON, TYPE_ABSENT_REASON
    from server.vwx.verdicts import FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED

    payload = resolve_fixture_types(
        [request("a", instrument_type="Robin MMX Spot")],
        library_port=_R21DiscardPort(_R21_THREE_TYPE_LIBRARY, slotless_types=(1, 2, 3)),
    ).to_dict()
    row = row_by_id(payload, "a")

    assert row["status"] == TYPE_LIBRARY_INCOMPLETE
    assert row["status"] != TYPE_LIBRARY_ABSENT
    assert hard_stop_codes(payload) == []
    assert FIXTURE_TYPE_NOT_IN_LIBRARY not in hard_stop_codes(payload)
    assert row["reason"] == LIBRARY_ROWS_DISCARDED_REASON
    assert FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED in skipped_kinds(payload)

    # 계수가 실제로 나간다 — "못 읽은 행이 있다"를 몇 개인지와 함께 말한다.
    library = payload["library"]
    assert library["unusable_row_count"] == 3
    assert library["unparsable_row_count"] == 0
    assert library["rows_discarded_count"] == 3
    assert library["type_count"] == 0
    assert library["child_count"] == 3

    # **거짓이 나가지 않는다**: 라이브러리는 온전히 있으므로 임포트를 시키지 않는다.
    text = _r21_text(payload)
    assert TYPE_ABSENT_REASON not in text
    assert "GDTF 라이브러리 임포트" not in text
    assert "라이브러리에 도면 타입에 대응하는 FixtureType이 없다" not in text


def test_r21_no_child_is_queried_when_every_row_is_discarded():
    """폐기된 행의 자식을 조회하지 않는다 — 슬롯이 없으면 물어볼 경로 자체가 없다."""
    library = read_fixture_type_library(
        _R21RawLibraryPort([{"name": "A"}, {"name": "B"}, {"name": "C"}], 3)
    )

    assert library.types == ()
    assert library.unusable_row_count == 3
    assert library.available is True
    assert library.truncated is False


# --- 감사 실증 ② DMXModes 2개 중 1개 `i` 없음 -----------------------------

#: 실증②의 라이브러리 — 도면이 요구한 16ch 모드가 **실재한다**(슬롯 3).
_R21_MODE_LIBRARY = [("MegaPointe", [("Mode 1", 24), ("Mode 2", 16)])]


def _r21_mode_discard_payload():
    return resolve_fixture_types(
        [request("a", instrument_type="MegaPointe", mode="Mode 1", footprint=16)],
        library_port=_R21DiscardPort(_R21_MODE_LIBRARY, slotless_modes=(2,)),
        type_aliases={"MegaPointe": {"type": "MegaPointe", "mode": "Mode 1"}},
        assumption_72=ASSUMPTION_72_GO,
    ).to_dict()


def test_r21_a_slotless_mode_row_blocks_the_footprint_hard_stop():
    """[round20 R20-D 실증②] 맞는 16ch 모드가 **실재하는데** 하드 스톱이 나갔다.

    구판 산출: `designed_footprint_matches_no_console_mode` + 사유가
    "모드 열거를 전부 읽었고 절단도 없었다"(거짓) + "고칠 것은 도면의 DMX Footprint
    값이다"(틀린 지시 — 맞는 모드가 라이브러리에 있다).

    죽이는 뮤테이션: `_absence_assertable`에서 `not console_type.mode_rows_discarded`를
    지우면 하드 스톱이 되살아나고 위 두 문장이 다시 나간다.
    """
    from server.vwx.typemap import (
        FOOTPRINT_MISMATCH_UNVERIFIED_REASON,
        FOOTPRINT_UNMATCHABLE_REASON,
    )
    from server.vwx.verdicts import (
        DESIGNED_FOOTPRINT_MATCHES_NO_MODE,
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
    )

    # 전제: 도면이 요구한 16ch 모드가 라이브러리에 **실재한다**. 이것이 참이 아니면
    # "틀린 지시"라는 주장이 성립하지 않는다.
    assert ("Mode 2", 16) in _R21_MODE_LIBRARY[0][1]

    payload = _r21_mode_discard_payload()
    row = row_by_id(payload, "a")

    assert row["status"] == TYPE_LIBRARY_INCOMPLETE
    assert hard_stop_codes(payload) == []
    assert DESIGNED_FOOTPRINT_MATCHES_NO_MODE not in hard_stop_codes(payload)
    assert row["reason"] == FOOTPRINT_MISMATCH_UNVERIFIED_REASON
    assert FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED in skipped_kinds(payload)

    entry = payload["library"]["types"][0]
    assert entry["unusable_mode_row_count"] == 1
    assert entry["mode_rows_discarded_count"] == 1
    assert entry["mode_count"] == 1
    assert entry["mode_child_count"] == 2

    text = _r21_text(payload)
    assert FOOTPRINT_UNMATCHABLE_REASON not in text
    assert "모드 열거를 전부 읽었고 절단도 없었다" not in text
    assert "고칠 것은 도면의 DMX Footprint" not in text


def test_r21_the_unverified_sentence_names_the_discard_axis():
    """사유 문장이 **관측 사실을 참으로** 말한다.

    round19판 문장은 "절단됐거나 채널 수를 읽지 못한 모드가 있다" 둘만 열거했다 —
    폐기로 이 갈래에 온 스냅샷에서 그 문장은 거짓이다(R20-D가 고발한 형태 그 자체).

    [round25 R24-1] 채널 수 절이 **이 문장에서 빠졌다.** 그 원인은 목록의 결함이 아니라
    원소의 한 칸이 빈 것이라 조치도 다르고(목록 재열거가 아니라 그 모드의 채널 수
    재판독), 두 완전성 마커가 `complete:true`인 채로 "목록을 전수로 보지 못했다"를 실어
    자기모순이었다. 절을 지운 것이 아니라 **자기 문장으로 옮겼다** — 그 사실을 여기서
    잰다(옮긴 곳에 없으면 이 시험이 운다).

    죽이는 뮤테이션: 사유에서 "슬롯 번호가 없어 쓰지 못한 행" 절을 지우면 실패한다.
    """
    from server.vwx.typemap import (
        FOOTPRINT_MISMATCH_CHANNEL_COUNTS_UNREAD_REASON,
        FOOTPRINT_MISMATCH_UNVERIFIED_REASON,
    )

    assert "슬롯 번호가 없어 쓰지 못한 행" in FOOTPRINT_MISMATCH_UNVERIFIED_REASON
    assert "미관측분" in FOOTPRINT_MISMATCH_UNVERIFIED_REASON
    assert "채널 수를 읽지 못한" in FOOTPRINT_MISMATCH_CHANNEL_COUNTS_UNREAD_REASON
    # 목록 축 문장은 채널 수를 **탓하지 않는다** — 그 갈래는 여기 오지 않는다.
    assert "채널 수를 읽지 못한" not in FOOTPRINT_MISMATCH_UNVERIFIED_REASON
    # 이 갈래에 실제로 닿는지 — 닿지 않으면 위 단정들은 장식이다.
    assert row_by_id(_r21_mode_discard_payload(), "a")["reason"] == (
        FOOTPRINT_MISMATCH_UNVERIFIED_REASON
    )


# --- 형제 리더와의 비대칭 대조군 -------------------------------------------


def test_r21_both_readers_treat_the_same_snapshot_alike():
    """[round20 R20-D 결정적 대조] **같은 스냅샷 · 같은 처리.**

    구판: `patchplan`은 `complete=False` + "슬롯 번호가 없거나 중복인 행 3개를 쓰지
    못했다", `typemap`은 `library_absent`. 같은 형태, 반대 처리였다.

    죽이는 뮤테이션: `read_fixture_type_library`의 폐기 계수를 지우면 두 계수가 갈린다.
    """
    from server.vwx.patchplan import _existing_fids_from_console

    rows = [{"name": "A"}, {"name": "B"}, {"name": "C"}]

    sibling = _existing_fids_from_console(_R21FidPort(rows, 3))
    ours = read_fixture_type_library(_R21RawLibraryPort(rows, 3))

    # ㉠ 형제가 무엇을 했는지 — 이 값이 0이면 대조군의 전제가 무너진다.
    assert sibling.unusable_rows == 3
    assert sibling.complete is False
    assert "슬롯 번호가 없거나 중복인 행 3개를 쓰지 못했다" in sibling.reason()

    # ㉡ 우리도 **같은 수**를 센다.
    assert ours.unusable_row_count == sibling.unusable_rows
    assert ours.unparsable_row_count == sibling.unparsable_rows
    assert ours.child_count == sibling.child_count

    # ㉢ 그래서 우리도 부재를 단정하지 않는다.
    assert ours.enumeration_incomplete is True


def test_r21_both_readers_count_non_mapping_rows_the_same_way():
    """매핑이 아닌 행 — 형제의 `unparsable_rows`와 같은 산식인지."""
    from server.vwx.patchplan import _existing_fids_from_console

    rows = [{"i": 1, "name": "A"}, "not-a-mapping", 42]

    sibling = _existing_fids_from_console(_R21FidPort(rows, 3))
    ours = read_fixture_type_library(_R21RawLibraryPort([{"name": "A"}, "not-a-mapping", 42], 3))

    assert sibling.unparsable_rows == 2
    assert ours.unparsable_row_count == 2


# --- 계수 상보식 (returned == enumerated + unusable + unparsable) ----------

#: 행 형태 코퍼스 — 축이 하나씩, 그리고 둘이 함께 참인 입력.
_R21_ROW_SHAPES = (
    ("clean", {}),
    ("slotless_type", {"slotless_types": (2,)}),
    ("duplicate_type_slot", {"duplicate_type_slot": 1}),
    ("junk_type_row", {"junk_type_rows": 1}),
    ("slotless_mode", {"slotless_modes": (2,)}),
    ("junk_mode_row", {"junk_mode_rows": 1}),
    ("duplicate_mode_slot", {"duplicate_mode_slot": 1}),
    ("truncated_only", {"declared_extra_types": 2}),
    ("truncated_and_discarded", {"declared_extra_types": 2, "slotless_types": (2,)}),
)


@pytest.mark.parametrize("label,kwargs", _R21_ROW_SHAPES, ids=[row[0] for row in _R21_ROW_SHAPES])
def test_r21_the_row_census_is_complementary(label: str, kwargs: dict):
    """**계수가 서로를 검산한다** — 어느 축이 조용히 새면 즉시 깨진다.

    `returned == enumerated + unusable + unparsable`. 이 등식이 성립해야 "폐기가 절단
    축으로 샜다"가 산술로 잡힌다.

    죽이는 뮤테이션:
      · `returned_row_count=len(raw_rows)`를 `len(rows)`로 되돌리면 매핑 아닌 행 형태에서
        좌변이 하나 모자라 실패한다.
      · `unusable_rows += 1`을 지우면 슬롯 미확립 형태에서 우변이 모자라 실패한다.
    """
    library = _r21_library(types=_R21_THREE_TYPE_LIBRARY, **kwargs)

    assert library.returned_row_count == (
        library.enumerated_count + library.unusable_row_count + library.unparsable_row_count
    ), label
    for entry in library.types:
        assert entry.returned_mode_row_count == (
            entry.modes_enumerated_count
            + entry.unusable_mode_row_count
            + entry.unparsable_mode_row_count
        ), (label, entry.name)


def test_r21_the_row_shape_corpus_actually_exercises_every_discard_form():
    """대조군 건전성 — 코퍼스가 네 형태(무슬롯·중복·비매핑 × 루트/모드)를 실제로 만든다.

    전부 0이면 위 상보식 게이트는 아무것도 지키지 않는다.
    """
    observed = {
        "root_unusable": 0,
        "root_unparsable": 0,
        "mode_unusable": 0,
        "mode_unparsable": 0,
        "unseen": 0,
    }
    for _label, kwargs in _R21_ROW_SHAPES:
        library = _r21_library(types=_R21_THREE_TYPE_LIBRARY, **kwargs)
        observed["root_unusable"] += library.unusable_row_count
        observed["root_unparsable"] += library.unparsable_row_count
        observed["unseen"] += library.unseen or 0
        for entry in library.types:
            observed["mode_unusable"] += entry.unusable_mode_row_count
            observed["mode_unparsable"] += entry.unparsable_mode_row_count

    assert all(count > 0 for count in observed.values()), observed


def test_r21_a_clean_snapshot_declares_no_discard():
    """비공허성 반대편 — 깨끗한 스냅샷에서 폐기 축은 **0이고 조용하다**.

    죽이는 뮤테이션: `unusable_rows`를 상수 1로 두면 여기서 실패한다(항상 불완전을
    말하는 판정은 판정이 아니다).
    """
    from server.vwx.verdicts import FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED

    payload = resolve_fixture_types(
        [request("a", instrument_type="Robin MMX Spot")],
        library_port=_R21DiscardPort(_R21_THREE_TYPE_LIBRARY),
    ).to_dict()

    assert payload["library"]["rows_discarded_count"] == 0
    assert all(entry["mode_rows_discarded_count"] == 0 for entry in payload["library"]["types"])
    assert FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED not in skipped_kinds(payload)
    assert payload["library"]["enumeration_incomplete"] is False


# --- 절단 ∧ 폐기 동시 참 --------------------------------------------------


def test_r21_truncation_and_discard_are_carried_on_separate_axes():
    """[Main 지시] **셋이 동시에 참일 수 있다** — 한 칸으로 뭉개지 않는다.

    조치가 다르기 때문이다: 절단은 표적 스윕, 폐기는 responder 확인. 하나로 합치면
    조작자가 무엇을 할지 고를 수 없다.

    죽이는 뮤테이션:
      · `to_dict`에서 `rows_discarded_count`를 지우면 폐기 규모가 사라진다.
      · `_library_observed_axes`에서 절단 갈래를 지우면 절단 고지가 사라진다.
      · 같은 함수에서 절단 판정을 union(`enumeration_incomplete`)으로 바꾸면
        아래 `test_r21_a_discard_only_snapshot_does_not_claim_truncation`이 실패한다.
    """
    from server.vwx.verdicts import (
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
    )

    payload = resolve_fixture_types(
        [request("a", instrument_type="Robin MMX Spot")],
        library_port=_R21DiscardPort(
            _R21_THREE_TYPE_LIBRARY, slotless_types=(2,), declared_extra_types=2
        ),
    ).to_dict()
    library = payload["library"]

    # 두 축이 **각각** 0이 아니고, **서로 다른 칸**에 실린다.
    assert library["rows_discarded_count"] == 1
    assert library["unusable_row_count"] == 1
    assert library["unseen_count"] == 3
    assert library["unseen_count"] != library["rows_discarded_count"]

    # 두 고지가 **함께** 나간다 — 조작자가 두 조치를 모두 볼 수 있다.
    kinds = skipped_kinds(payload)
    assert FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED in kinds
    assert FIXTURE_TYPE_LIBRARY_TRUNCATED in kinds

    # 폐기 고지에는 계수가 동봉된다.
    discard = next(
        check
        for check in payload["skipped_checks"]
        if check["kind"] == FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED
    )
    assert discard["discarded_row_count"] == 1
    assert discard["unusable_row_count"] == 1
    assert discard["unparsable_row_count"] == 0


def test_r21_a_discard_only_snapshot_does_not_claim_truncation():
    """폐기만 있는 스냅샷에서 **절단을 말하지 않는다** — 없는 사실을 고지하지 않는다.

    `_library_observed_axes`가 절단 판정에 union(`enumeration_incomplete`)을 쓰면 union이
    폐기를 삼키므로 "열거에 미관측분이 남았다"는 거짓 고지가 나간다. 축을 가르려고 만든
    자리에서 축을 다시 뭉개는 형태다.
    """
    from server.vwx.verdicts import (
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
    )

    payload = resolve_fixture_types(
        [request("a", instrument_type="Robin MMX Spot")],
        library_port=_R21DiscardPort(_R21_THREE_TYPE_LIBRARY, slotless_types=(2,)),
    ).to_dict()

    assert payload["library"]["unseen_count"] == 1  # 폐기된 행이 관측에서 빠진 결과다
    assert payload["library"]["enumeration_short"] is False
    kinds = skipped_kinds(payload)
    assert FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED in kinds
    assert FIXTURE_TYPE_LIBRARY_TRUNCATED not in kinds


def test_r21_the_discard_axis_is_resolved_before_the_union():
    """[Main 지시] **순서가 규율이다** — 순서를 뒤집는 뮤턴트가 여기서 죽는다.

    union 프로퍼티가 폐기를 논리합으로 삼키므로, union을 먼저 보면 폐기 전용 축은
    **도달 불가**가 된다(R18-C·R18-E와 같은 계열).

    죽이는 뮤테이션: `_library_axis`·`_mode_axis`에서 폐기 갈래를 union 뒤로 옮기면
    두 단정이 모두 `TRUNCATED`를 받아 실패한다.
    """
    from server.vwx.typemap import _library_axis, _mode_axis
    from server.vwx.verdicts import FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED

    library = _r21_library(
        types=_R21_THREE_TYPE_LIBRARY, slotless_types=(2,), declared_extra_types=2
    )
    assert library.enumeration_incomplete is True  # union은 이미 참이다
    assert _library_axis(library) == FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED

    console_type = _r21_library_type(unusable_mode_row_count=1, mode_child_count=2)
    assert console_type.modes_incomplete is True
    assert _mode_axis(console_type) == FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED


# --- `_absence_assertable` 전제 등기부 -------------------------------------


def _r21_library_type(**overrides) -> LibraryType:
    """전제를 **하나만** 위반시킬 수 있는 깨끗한 기준 타입."""
    base = dict(
        index=1,
        name="MegaPointe",
        modes=(LibraryMode(index=1, name="Mode 1", channel_count=24),),
        modes_available=True,
        modes_truncated=False,
        mode_child_count=1,
        modes_enumerated_count=1,
        returned_mode_row_count=1,
        unusable_mode_row_count=0,
        unparsable_mode_row_count=0,
    )
    base.update(overrides)
    return LibraryType(**base)


def _r21_function_node(name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in ast.walk(ast.parse(TYPEMAP_SOURCE))
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(matches) == 1, f"{name}이 {len(matches)}개다 — 스캐너가 무엇을 재는지 불명확하다"
    return matches[0]


def _r21_attributes(name: str) -> frozenset[str]:
    return frozenset(
        child.attr
        for child in ast.walk(_r21_function_node(name))
        if isinstance(child, ast.Attribute)
    )


#: `_absence_assertable`이 쓰는 **전제 전수** — 속성 이름 -> 그 전제가 말하는 것.
#: [round20 R20-D] 이 표가 있어야 "네 번째 전제가 또 있을 수 있다"가 강제된다: 표현식에
#: 갈래가 늘면 등기 전까지 아래 전단사 게이트가 막는다.
_R21_ABSENCE_PREMISES = {
    "modes_available": "모드 열거 응답 자체를 받았다",
    "modes_truncated": "예산 절단 플래그가 서지 않았다",
    "modes_enumeration_short": "열거 행 수가 선언 총계에 미치지 못한 것이 아니다",
    # [round23 R22-B] 반대 방향. `modes_incomplete` union에 갈래가 늘면 이 등기 전단사가
    # 술어를 함께 끌어온다 — round19가 20줄 거리에서 형제를 빠뜨린 것이 R20-D였다.
    "modes_over_enumerated": "열거 행 수가 선언 총계를 넘은 것도 아니다",
    "mode_rows_discarded": "슬롯 번호가 없어 버린 모드 행이 없다",
    # [round24 R23-1] **대조 기준 자체.** 위 세 계수 갈래는 전부 `mode_child_count`가
    # `None`이면 거짓이 되므로, 이 행이 없으면 "어긋난 것이 관측되지 않았다"가
    # "전수다"로 읽힌다 — 형제 `_mode_list_completeness`는 그 상태를 `complete=None`으로
    # 적어 확정을 막고 있었고, 이 술어만 통과시켰다.
    "mode_child_count": "선언된 모드 총계를 읽어 대조할 기준이 있다",
    "channel_count": "모드마다 채널 수를 **실제로 읽었다**",
    "modes": "측정 모집단은 읽어 들인 모드 전부다(부분집합을 재고 전수라 말하지 않는다)",
}

#: 그중 **목록 완전성** 갈래 — `LibraryType.modes_incomplete`와 전단사여야 한다.
_R21_LIST_COMPLETENESS_PREMISES = frozenset(
    {
        "modes_truncated",
        "modes_enumeration_short",
        "modes_over_enumerated",
        "mode_rows_discarded",
    }
)


def test_r21_the_absence_premise_registry_is_a_bijection_onto_the_predicate():
    """[round20 R20-D] 등기부가 `_absence_assertable`의 AST 전수와 1:1이다.

    죽이는 뮤테이션:
      · 술어에서 갈래를 지우면 스캔에서 속성이 사라져 어긋난다.
      · 등기부에서 행을 지워도 어긋난다(아래 행삭제 프로브가 전 행 확인).
      · 갈래를 등기 없이 새로 더해도 어긋난다.
    """
    assert _r21_attributes("_absence_assertable") == frozenset(_R21_ABSENCE_PREMISES)
    assert all(len(text) > 8 for text in _R21_ABSENCE_PREMISES.values())


@pytest.mark.parametrize("premise", sorted(_R21_ABSENCE_PREMISES))
def test_r21_deleting_any_absence_premise_row_breaks_the_registry(premise: str):
    """행 삭제 프로브 — 어느 행을 지워도 술어 전수와 어긋난다."""
    shrunk = {key: value for key, value in _R21_ABSENCE_PREMISES.items() if key != premise}
    assert frozenset(shrunk) != _r21_attributes("_absence_assertable")


def test_r21_the_list_completeness_premises_match_the_union_property():
    """**두 층이 조용히 갈라지지 못한다.**

    `_absence_assertable`은 `modes_incomplete`를 부르지 않고 그 갈래를 펼친다(갈래마다
    뮤테이션이 성립해야 하므로). 그 대신 여기서 전단사를 건다 — union에 네 번째 갈래가
    생기면 술어가 그것을 빠뜨린 채로 통과하지 못한다. **round19가 20줄 거리에서 형제를
    빠뜨린 것이 R20-D였다.**
    """
    assert _r21_attributes("modes_incomplete") == _R21_LIST_COMPLETENESS_PREMISES
    assert frozenset(_R21_ABSENCE_PREMISES) >= _R21_LIST_COMPLETENESS_PREMISES


def test_r21_the_absence_predicate_refuses_an_unconfirmed_type():
    """확정된 타입이 없으면 전제를 잴 대상 자체가 없다 — 등기부 밖의 네 번째 가드."""
    from server.vwx.typemap import _absence_assertable

    assert _absence_assertable(None) is False
    node = _r21_function_node("_absence_assertable")
    assert any(
        isinstance(child, ast.Compare)
        and any(isinstance(op, ast.Is) for op in child.ops)
        and any(isinstance(c, ast.Constant) and c.value is None for c in child.comparators)
        for child in ast.walk(node)
    ), "`is None` 가드가 사라졌다"


#: 전제 -> 그 전제 **하나만** 위반한 타입.
_R21_PREMISE_VIOLATIONS = {
    "modes_available": {"modes_available": False},
    "modes_truncated": {"modes_truncated": True},
    "modes_enumeration_short": {"mode_child_count": 2},
    # [round23 R22-B] 선언 0인데 모드 1개가 실렸다 — 초과만 단독으로 참이 된다
    # (`modes_enumeration_short`는 `0 > 1`이 거짓이라 서지 않는다).
    "modes_over_enumerated": {"mode_child_count": 0},
    "mode_rows_discarded": {"unusable_mode_row_count": 1},
    # [round24 R23-1] 총계 칸 자체가 없다. 계수 갈래 셋은 **전부 거짓**이 되고
    # (`modes_enumeration_short`·`modes_over_enumerated`가 `None`에서 조기 반환한다),
    # 구판은 그래서 이 입력을 전수로 읽었다 — 이 행이 그 갈래를 행동으로 잡는다.
    "mode_child_count": {"mode_child_count": None},
    "channel_count": {"modes": (LibraryMode(index=1, name="Mode 1", channel_count=None),)},
}


def test_r21_the_absence_predicate_holds_when_no_premise_is_violated():
    """비공허성 — 깨끗한 타입에서는 **참이다**. 거짓이면 아래 대조군이 전부 공허하다."""
    from server.vwx.typemap import _absence_assertable

    assert _absence_assertable(_r21_library_type()) is True


@pytest.mark.parametrize("premise", sorted(_R21_PREMISE_VIOLATIONS))
def test_r21_violating_any_single_premise_withdraws_the_absence_claim(premise: str):
    """전제마다 **행동 대조군** — 그 하나만 위반해도 부재를 단정하지 않는다.

    죽이는 뮤테이션: `_absence_assertable`에서 그 갈래를 지우면 해당 행이 실패한다.
    """
    from server.vwx.typemap import _absence_assertable

    console_type = _r21_library_type(**_R21_PREMISE_VIOLATIONS[premise])
    assert _absence_assertable(console_type) is False, premise


def test_r21_every_boolean_premise_has_a_behavioural_control():
    """등기부의 불리언 전제 전수가 위 대조군 표에 있다 — `modes`만 예외다.

    `modes`는 **모집단**이라 그 자체를 위반시킬 수 없다(빈 목록은 이 갈래에 도달하지
    못한다). 대신 아래 `test_r21_the_measured_population_is_the_presented_one`이
    "측정한 것과 보여준 것이 같은 목록인가"를 행동으로 잰다.
    """
    assert frozenset(_R21_PREMISE_VIOLATIONS) | {"modes"} == frozenset(_R21_ABSENCE_PREMISES)


def test_r21_the_measured_population_is_the_presented_one():
    """`modes` 전제의 행동 대조군 — **잰 목록과 보여준 목록이 같다.**

    부분집합을 재고 전체를 보여주면(또는 반대면) "전 모드를 실측했다"가 거짓이 된다.
    """
    payload = _r21_mode_discard_payload()
    row = row_by_id(payload, "a")
    entry = payload["library"]["types"][0]

    assert len(row["mode_options"]) == entry["mode_count"]
    assert [option["name"] for option in row["mode_options"]] == ["Mode 1"]
    assert all(option["channel_count"] is not None for option in row["mode_options"])


# --- [HARD] 형제 표면 전수 — 열거 행을 버리는 자리 -------------------------
#
# 기제는 *"열거 응답의 행을 버리면서 버렸다는 사실을 안 남긴다"*이다. 두 부류를 각각
# 기계적으로 전수한다:
#   ㉠ **원시 행**을 직접 꺼내는 자리(`state["children"]`) — 스스로 세야 한다.
#   ㉡ PRESERVE `prechk.Inventory`를 **소비**하는 자리 — 계수는 이미 실려 온다.
# 모든 부재가 결함은 아니다. 그 구별을 표가 들고 있어야 다음 라운드가 오독하지 않는다.


def _r21_scan_raw_row_readers() -> set[tuple[str, str]]:
    """`server/vwx/` 전 모듈에서 열거 응답의 **행 목록**을 직접 꺼내는 함수 전수."""
    found: set[tuple[str, str]] = set()
    for path in iter_vwx_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Constant) and inner.value == "children":
                    found.add((vwx_module_label(path), node.name))
    return found


def _r21_scan_inventory_consumers() -> set[tuple[str, str]]:
    """`server/vwx/` 전 모듈에서 PRESERVE `prechk.Inventory`를 인자로 받는 함수 전수.

    스코프는 `server/vwx/*.py`뿐이다 — `server/prechk/`도 `console/`도 읽지 않는다.
    `Inventory`는 계수(절단·미판독)를 **이미 들고 오는** 열거 산출물이라, 이 부류는
    스스로 세지 않는 것이 옳다. 그 구별을 등기부가 들고 있어야 다음 라운드가
    "여기도 안 센다"를 결함으로 오독하지 않는다.
    """
    found: set[tuple[str, str]] = set()
    for path in iter_vwx_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            args = [*node.args.args, *node.args.posonlyargs, *node.args.kwonlyargs]
            if any(
                isinstance(arg.annotation, ast.Name) and arg.annotation.id == "Inventory"
                for arg in args
            ):
                found.add((vwx_module_label(path), node.name))
    return found


#: (모듈, 함수, **자기가 세는가**, 근거). 원시 행을 직접 꺼내는 자리는 전부 세야 한다.
_R21_RAW_ROW_READERS = (
    (
        "patchplan.py",
        "_existing_fids_from_console",
        True,
        "`unusable_rows`(슬롯 번호 없음·중복)와 `unparsable_rows`(매핑 아님)를 따로 세고 "
        "`complete`가 둘 다 읽는다 — round15 N06이 그 두 번째 축을 세운 자리다.",
    ),
    (
        "typemap.py",
        "read_fixture_type_library",
        True,
        "[round21 R20-D] `unusable_row_count`·`unparsable_row_count`를 형제와 같은 이름으로 "
        "센다. 구판은 `if index is None or not listed: continue`로 계수 없이 버렸고, 그래서 "
        "슬롯 미확립이 `library_absent`로 바뀌어 나갔다.",
    ),
    (
        "typemap.py",
        "_read_type",
        True,
        "[round21 R20-D] 모드 행도 같은 규율 — `unusable_mode_row_count`·"
        "`unparsable_mode_row_count`. 한 모듈 안에서 규율이 갈리면 그 자체가 결함이다.",
    ),
)

#: (모듈, 함수, **자기가 세는가**, 근거). 소비 자리는 세지 않는 것이 옳다.
_R21_INVENTORY_CONSUMERS = (
    (
        "apply.py",
        "read_console_fixtures",
        False,
        "PRESERVE `prechk.Inventory`가 절단·미판독을 이미 계수해 들고 온다. 여기서 다시 "
        "세면 같은 슬롯을 두 축으로 세게 되고, round14 T01/T03이 만든 '선언 2대 중 4대를 "
        "읽지 못했다'는 산술 불가능 문구가 되살아난다.",
    ),
    (
        "apply.py",
        "console_read_caveat",
        False,
        "같은 `Inventory`의 계수를 **읽어서 고지로 옮기는** 자리다 — 세는 자리가 아니라 "
        "말하는 자리이므로 계수를 다시 만들면 두 층이 갈린다.",
    ),
    (
        "apply.py",
        "screen_console_read",
        False,
        "`Inventory.complete`를 읽어 **생성을 막는** 자리다. 판정을 소비할 뿐이고 자기 "
        "계수를 갖지 않는다 — 갖게 되면 막는 근거가 둘이 된다.",
    ),
    (
        "diff.py",
        "_console_rows",
        False,
        "1단계 계층(AC-AUTOPATCH-025 무변경)이고 `Inventory.fixtures`를 정규화만 한다. "
        "계수 판정은 그 층의 소관이 아니다 — 우리 층이 고칠 권한도 없다.",
    ),
    (
        "diff.py",
        "compare",
        False,
        "같은 1단계 계층. 콘솔 부재·수량 판정은 여기서 나지만 열거 계수는 `Inventory`가 "
        "들고 오고, 그 불완전성 고지는 2단계(`typemap`·`patchplan`)가 낸다.",
    ),
)


def test_r21_the_raw_row_reader_registry_is_a_bijection_onto_server_vwx():
    """[HARD] 열거 **원시 행**을 꺼내는 자리가 전부 등기돼 있다.

    새 모듈·새 함수가 `state["children"]`을 꺼내면 등기 없이는 통과하지 못한다 —
    열한 라운드 연속 FAIL의 기제가 **표 밖에 있던 형제 자리**였다.
    """
    scanned = _r21_scan_raw_row_readers()
    registered = {(row[0], row[1]) for row in _R21_RAW_ROW_READERS}
    assert scanned == registered, (
        f"열거 행 판독 자리가 등기부와 다르다 — 미등록: {sorted(scanned - registered)} / "
        f"유령: {sorted(registered - scanned)}"
    )


def test_r21_every_raw_row_reader_counts_what_it_discards():
    """[HARD] 원시 행을 꺼내는 자리는 **예외 없이** 버린 것을 센다.

    이 부류에서 `counts=False`인 행이 생기면 그것이 R20-D와 같은 결함이다 — 표가
    "안 센다"를 정당화하는 자리가 아니다.
    """
    for module, function, counts, rationale in _R21_RAW_ROW_READERS:
        assert counts is True, f"{module}:{function}이 버린 것을 세지 않는다"
        assert len(rationale) > 40, f"{module}:{function}의 근거가 비어 있다"


def test_r21_the_inventory_consumer_registry_is_a_bijection_onto_server_vwx():
    """[HARD] `Inventory` 소비 자리 전수 — **모든 부재가 결함은 아니다.**

    이쪽은 세지 않는 것이 옳다(계수가 이미 실려 온다). 그 구별을 표가 들고 있어야
    다음 라운드가 "여기도 안 센다"를 결함으로 오독하지 않는다.
    """
    scanned = _r21_scan_inventory_consumers()
    registered = {(row[0], row[1]) for row in _R21_INVENTORY_CONSUMERS}
    assert scanned == registered, (
        f"`Inventory` 소비 자리가 등기부와 다르다 — 미등록: {sorted(scanned - registered)} / "
        f"유령: {sorted(registered - scanned)}"
    )
    for module, function, counts, rationale in _R21_INVENTORY_CONSUMERS:
        assert counts is False, f"{module}:{function}이 계수를 중복해서 만든다"
        assert len(rationale) > 40, f"{module}:{function}의 근거가 비어 있다"


@pytest.mark.parametrize("index", range(len(_R21_RAW_ROW_READERS) + len(_R21_INVENTORY_CONSUMERS)))
def test_r21_deleting_any_row_filter_row_breaks_its_registry(index: int):
    """행 삭제 프로브 — 두 표 어디서 행을 지워도 프로덕션 전수와 어긋난다."""
    raw = len(_R21_RAW_ROW_READERS)
    if index < raw:
        shrunk = _R21_RAW_ROW_READERS[:index] + _R21_RAW_ROW_READERS[index + 1 :]
        assert {(row[0], row[1]) for row in shrunk} != _r21_scan_raw_row_readers()
    else:
        position = index - raw
        shrunk = _R21_INVENTORY_CONSUMERS[:position] + _R21_INVENTORY_CONSUMERS[position + 1 :]
        assert {(row[0], row[1]) for row in shrunk} != _r21_scan_inventory_consumers()


def test_r21_the_two_registries_are_disjoint():
    """두 부류가 겹치면 같은 자리에 두 판정이 붙는다 — 어느 쪽이 맞는지 사라진다."""
    assert not (_r21_scan_raw_row_readers() & _r21_scan_inventory_consumers())


# --- 회수 경로 == 열거 경로 (같은 계수 규율) -------------------------------


class _R21SweepPort(LibraryRigPort):
    """열거는 2종만 싣고 3번째는 **표적 스윕**으로만 찾을 수 있는 포트.

    두 경로(열거 · 회수)로 온 타입이 **같은 폐기 계수 규율**을 받는지 재기 위한 것이다.
    모든 타입의 두 번째 DMXModes 행에서 슬롯 번호를 뺀다 — 경로가 달라도 입력은 같다.
    """

    def query_state(self, path: str) -> dict:
        probe = re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)", path)
        if probe is not None:
            index = int(probe.group(1))
            return {
                "ok": True,
                "path": path,
                "node": {"name": self.types[index - 1][0], "class": "FixtureType"},
                "children": [],
                "truncated": False,
            }
        state = super().query_state(path)
        if state.get("ok") is not True:
            return state
        if path == FIXTURE_TYPE_LIBRARY_ROOT:
            # 선언은 3종인데 열거는 2종만 싣는다 — 3번은 스윕으로만 닿는다.
            return {**state, "children": [row for row in state["children"] if row["i"] <= 2]}
        if path.endswith(f"/{DMX_MODES_SEGMENT}"):
            children = [dict(row) for row in state["children"]]
            for row in children:
                if row.get("i") == 2:
                    row.pop("i")
            return {**state, "children": children}
        return state


def test_r21_a_recovered_type_carries_the_same_discard_counts():
    """[Main 지시] **경로별로 규율이 갈리지 않는다.**

    표적 스윕이 회수한 타입도 열거로 온 타입과 같은 폐기 계수를 들고 와야 한다.
    `recover_requested_types`의 `LibraryType(...)` 재구성에서 두 필드를 빠뜨리면 회수된
    타입만 조용히 "행을 다 읽었다"가 된다.

    죽이는 뮤테이션: 그 재구성에서 `unusable_mode_row_count=` 줄을 지우면 실패한다.
    """
    from server.vwx.typemap import recover_requested_types

    port = _R21SweepPort(_R21_THREE_TYPE_LIBRARY)
    enumerated = read_fixture_type_library(port)
    # 대조군 전제 ㉠ — 3번은 열거에 없다(있으면 스윕이 돌지 않아 이 게이트가 공허하다).
    assert [entry.index for entry in enumerated.types] == [1, 2]

    recovered = recover_requested_types(port, enumerated, ["Robin LEDBeam 350"])
    by_index = {entry.index: entry for entry in recovered.types}
    # 대조군 전제 ㉡ — 스윕이 실제로 회수했다.
    assert sorted(by_index) == [1, 2, 3]
    assert by_index[3].recovered is True
    assert by_index[1].recovered is False

    # 두 경로가 **같은 계수**를 낸다: 4모드 타입과 3모드 타입 각각 두 번째 행이 폐기다.
    for index in (1, 3):
        entry = by_index[index]
        assert entry.unusable_mode_row_count == 1, index
        assert entry.mode_rows_discarded == 1, index
        assert entry.returned_mode_row_count == (
            entry.modes_enumerated_count
            + entry.unusable_mode_row_count
            + entry.unparsable_mode_row_count
        ), index
    # 모드가 하나뿐인 타입에는 폐기가 없다 — 계수가 상수가 아니라는 반대편 증거.
    assert by_index[2].mode_rows_discarded == 0


# --- 신설 어휘의 라벨 축 구별성 --------------------------------------------


def test_r21_the_discard_vocabulary_is_registered_in_both_closed_sets():
    """신설 어휘 1건이 두 닫힌 어휘에 등재되고 라벨을 갖는다.

    등재를 지우면 `validate_autopatch`가 던지고, 라벨을 지우면 `verdicts` 임포트 자체가
    실패한다(모듈 하단의 표 대조).
    """
    from server.vwx.verdicts import (
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
        SKIPPED_CHECK_KIND,
        TARGET_EXCLUSION_REASON,
        skipped_check_label,
        target_exclusion_label,
    )

    assert FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED in SKIPPED_CHECK_KIND
    assert FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED in TARGET_EXCLUSION_REASON
    assert skipped_check_label(FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED)
    assert target_exclusion_label(FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED)
    assert (
        validate_autopatch("skipped_check_kind", FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED)
        == FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED
    )


def test_r21_the_discard_labels_do_not_borrow_a_sibling_axis_sentence():
    """[round18 M24 형태] 라벨이 **형제 축 문구를 빌려 쓰지 않는다.**

    폐기 축의 조치는 재판독이 아니다 — 같은 범위를 다시 읽어도 같은 행이 온다. 절단·
    판독실패 라벨의 조치 문구를 그대로 쓰면 조작자는 효과 없는 조치를 반복한다.
    """
    from server.vwx.verdicts import (
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
        skipped_check_label,
        target_exclusion_label,
    )

    axes = (
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
    )
    labels = [target_exclusion_label(code) for code in axes] + [
        skipped_check_label(code) for code in axes
    ]
    assert len(set(labels)) == len(labels), labels

    discard_exclusion = target_exclusion_label(FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED)
    assert "슬롯 번호" in discard_exclusion
    assert "다시 읽어야" not in discard_exclusion
    assert "라이브러리" in discard_exclusion  # 고칠 축은 `console_library`다


# --- 뮤테이션 실측이 드러낸 공백 3건 (round21 SlotDiscard 2차) --------------
#
# 1차 실측에서 세 자리가 SURVIVED였다. 전부 "표는 맞는데 그 표를 읽는 대조군이 없다"는
# 형태이고, 이 SPEC이 반복해서 만든 공백과 같다 — 그래서 그대로 남기지 않고 닫는다.


def test_r21_a_duplicate_slot_row_is_discarded_and_counted():
    """[1차 실측 M19/M20 = 진짜 공백] 중복 `i` 행도 **폐기**로 센다.

    형제 `patchplan._existing_fids_from_console`이 같은 형태를 `unusable_rows`로 세고
    (`child_index in read_slots`), 그 근거는 round12 R01이다: 중복이 섞이면
    `len(children)`가 부풀어 총계와 맞아떨어지고 **못 읽은 슬롯이 남았는데 완전으로
    보고된다.** 여기서는 같은 콘솔 경로가 서로 다른 이름으로 두 번 실리기까지 한다.

    죽이는 뮤테이션: `read_fixture_type_library`의 `or index in seen_slots`(또는
    `_read_type`의 `or mode_index in seen_mode_slots`)를 지우면 실패한다.
    """
    root = _r21_library(types=_R21_THREE_TYPE_LIBRARY, duplicate_type_slot=1)
    assert root.unusable_row_count == 1
    assert root.returned_row_count == 4
    assert [entry.index for entry in root.types] == [1, 2, 3]  # 같은 슬롯이 두 번 실리지 않는다
    assert root.observed_type_count == 3
    assert root.unseen == 0

    modes = _r21_library(types=_R21_THREE_TYPE_LIBRARY, duplicate_mode_slot=1)
    first = modes.types[0]
    assert first.unusable_mode_row_count == 1
    assert first.returned_mode_row_count == 5
    assert [mode.index for mode in first.modes] == [1, 2, 3, 4]
    assert first.modes_unseen == 0


def test_r21_a_duplicate_slot_does_not_inflate_the_observed_count():
    """중복을 받아들이면 **부분 관측이 전수로 보고된다** — round12 R01의 실패 양식.

    선언 3종 · 열거 2종 + 2번 슬롯 중복 1행: 중복을 세지 않고 받으면 관측이 3이 되어
    `unseen`이 0으로 닫히고, 3번 타입을 못 봤다는 사실이 사라진다.
    """
    port = _R21DiscardPort(_R21_THREE_TYPE_LIBRARY, duplicate_type_slot=2, declared_extra_types=0)
    library = read_fixture_type_library(port)

    assert library.returned_row_count == 4
    assert library.observed_type_count == 3
    assert library.unusable_row_count == 1
    # 계수 상보식이 중복 형태에서도 성립한다.
    assert library.returned_row_count == (
        library.enumerated_count + library.unusable_row_count + library.unparsable_row_count
    )


def test_r21_the_mode_list_marker_says_incomplete_when_rows_were_discarded():
    """[1차 실측 M09 = 진짜 공백] 목록 옆 **완전성 표시**가 폐기를 말한다.

    `LibraryType.modes_incomplete`(union)의 폐기 갈래를 지우면 `_absence_assertable`은
    자기 갈래로 여전히 막지만, `mode_options_completeness`는 **부분 목록을 전부라고**
    말하게 된다 — 목록을 제시하면서 그 완전성을 거짓으로 붙이는 형태다.

    죽이는 뮤테이션: `modes_incomplete`에서 `or self.mode_rows_discarded > 0`을 지우면
    `complete`가 `True`로 뒤집혀 실패한다.
    """
    from server.vwx.typemap import MODE_OPTIONS_COMPLETENESS_COLUMN
    from server.vwx.verdicts import FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED

    payload = _r21_mode_discard_payload()
    row = row_by_id(payload, "a")
    marker = row[MODE_OPTIONS_COMPLETENESS_COLUMN]

    assert marker["complete"] is False
    assert marker["incompleteness_kind"] == FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED
    assert marker["declared_count"] == 2
    assert marker["observed_count"] == 1

    # payload의 타입별 칸도 같은 말을 해야 한다 — 여기가 `modes_incomplete` union의
    # **직접 소비 자리**다. union에서 폐기 갈래를 빼면 이 칸이 "이 모드 목록은 전수다"로
    # 뒤집혀, 표시(위)와 payload(아래)가 서로 다른 말을 한다.
    entry = payload["library"]["types"][0]
    assert entry["modes_incomplete"] is True
    assert entry["modes_enumeration_short"] is False
    assert entry["modes_truncated"] is False


def test_r21_the_two_discard_axes_are_not_interchangeable():
    """[1차 실측 M25 = 대조군 하중] 폐기 두 축을 **맞바꿔도** 합계는 같다.

    `unusable`(슬롯 번호 없음·중복)과 `unparsable`(매핑 아님)을 서로 바꿔 실어도
    상보식은 그대로 성립한다 — 합만 보는 게이트는 그 뒤바뀜을 못 잡는다. 형제와
    **칸 단위로** 대조하는 자리가 있어야 잡힌다
    (`test_r21_both_readers_treat_the_same_snapshot_alike`가 그 자리다).
    """
    from server.vwx.patchplan import _existing_fids_from_console

    rows = [{"name": "A"}, {"name": "B"}, "not-a-mapping"]
    sibling = _existing_fids_from_console(_R21FidPort(rows, 3))
    ours = read_fixture_type_library(_R21RawLibraryPort(rows, 3))

    # 두 축이 **각각** 0이 아니다 — 하나라도 0이면 뒤바뀜을 잴 수 없다.
    assert (ours.unusable_row_count, ours.unparsable_row_count) == (2, 1)
    assert (sibling.unusable_rows, sibling.unparsable_rows) == (2, 1)
    # 칸 단위 일치 — 합이 아니라 축마다 같다.
    assert ours.unusable_row_count == sibling.unusable_rows
    assert ours.unparsable_row_count == sibling.unparsable_rows
    assert ours.unusable_row_count != ours.unparsable_row_count


# --- round23 스윕 정확성 (SweepCorrectness) ---
#
# R22-A 재구성이 폐기 축을 지운다 · R22-C 조기 종료가 엉뚱한 타입을 확정한다 ·
# R22-F 비용 근거의 유효 범위. 세 갈래 모두 **감사 실증을 그대로** 코퍼스로 삼는다.

from dataclasses import MISSING as _R23_MISSING  # noqa: E402
from dataclasses import fields as _r23_fields  # noqa: E402

from server.vwx.typemap import RECOVERY_COST_EVIDENCE_ROUNDTRIPS  # noqa: E402


def _r23_default(field) -> object:
    """dataclass 필드의 **선언된 기본값**. 기본값이 없으면 어떤 값과도 다른 센티널.

    "이 칸이 기본값이 아니다"를 재기 위한 것이다 — round22 실측(Y02·Y03·C22)이 보인
    것은, 픽스처가 기본값과 같은 값을 만들면 그 칸을 **재구성에서 통째로 지워도**
    대조군이 통과한다는 것이었다. 값이 기본값과 다를 때에만 그 칸이 실제로 지켜진다.
    """
    if field.default is not _R23_MISSING:
        return field.default
    if field.default_factory is not _R23_MISSING:
        return field.default_factory()
    return object()


class _R23DiscardSweepPort(_R21SweepPort):
    """R22-A 감사 실증의 재현 형태 — **절단·폐기·미열거 요청이 동시에 참**인 스냅샷.

    `_R21SweepPort`(선언 3종 · 열거 2종)에 루트 폐기 축을 더한다: 2번 행은 슬롯 번호가
    없고(`unusable`), 매핑이 아닌 행이 하나 더 붙는다(`unparsable`). 그래서 열거는 1종만
    남고 요청된 이름은 열거 밖에 있어 **스윕이 반드시 돈다** — 회수 경로를 지나지 않는
    코퍼스는 R22-A를 잴 수 없다(round22 실측: 상보식 대조군이 이 경로를 한 번도 지나지
    않아 등식이 깨진 채로 나가도 아무도 세지 않았다).

    `nameless`는 응답이 `ok=true`인데 이름을 얻지 못하는 슬롯 — `probe_failures`를
    기본값이 아닌 값으로 만든다.
    """

    def __init__(self, types, *, nameless=(), **kwargs):
        super().__init__(types, **kwargs)
        self.nameless = frozenset(nameless)

    def query_state(self, path: str) -> dict:
        probe = re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)", path)
        if probe is not None and int(probe.group(1)) in self.nameless:
            return {"ok": True, "path": path, "node": {"class": "FixtureType"}, "children": []}
        state = super().query_state(path)
        if path != FIXTURE_TYPE_LIBRARY_ROOT or state.get("ok") is not True:
            return state
        rows = [dict(row) for row in state["children"]]
        for row in rows:
            if row.get("i") == 2:
                row.pop("i")
        rows.append("not-a-mapping")
        return {**state, "children": rows}


def _r23_carry_over_pair():
    """회수 경로를 지난 라이브러리와 그 직전 열거 결과 — 두 축 모두 기본값이 아니다."""
    port = _R23DiscardSweepPort(_R21_THREE_TYPE_LIBRARY, truncated=True, nameless=(2,))
    before = read_fixture_type_library(port)
    after = recover_requested_types(port, before, ["Robin LEDBeam 350"])
    return before, after


#: 스윕이 **바꿔도 되는** 칸. 나머지는 입력 그대로 실려 나가야 한다.
#: [round24 R24-5] `recovery_mode_roundtrips`가 여섯 번째다 — 스윕이 자기 단가를 적는
#: 칸이라 소유가 스윕에 있다. 아래 형제 시험이 "면제 목록에 밀어넣기"를 막는다:
#: 이 목록의 원소는 전부 입력과도 기본값과도 **다른 값**으로 움직여야 한다.
_R23_SWEEP_MUTATED_FIELDS = frozenset(
    {
        "types",
        "recovered_count",
        "recovery_boundary",
        "probe_failures",
        "recovery_probe_count",
        "recovery_mode_roundtrips",
    }
)
#: 스윕이 도달하는 지점에서 **증명 가능하게 상수**라 기본값이 아닌 값을 만들 수 없는 칸.
#: `available=False`면 함수 첫 줄이 입력을 그대로 돌려주므로 재구성이 실행되지 않는다 —
#: 이 칸을 재구성에서 빼는 변조는 **등가 뮤턴트**다(무대조군 오분류 방지 기록).
_R23_SWEEP_CONSTANT_FIELDS = frozenset({"available"})


def test_r23_the_sweep_carries_every_library_field_it_does_not_own():
    """[R22-A] **재구성이 칸을 지우지 못한다** — 전 필드를 이름으로 훑어 단정한다.

    구판은 11칸 중 9칸만 손으로 옮겨 `unusable_row_count`·`unparsable_row_count`가
    기본값 0으로 리셋됐다. 같은 함수 20줄 위 `LibraryType` 재구성은 두 칸을 정확히
    옮기고 있었다 — **루트만 빠졌다.** 인자 두 개를 더 적는 것으로는 다음 칸에서 또
    같은 일이 난다. 그래서 이 게이트는 칸 이름을 손으로 적지 않고
    `dataclasses.fields`로 훑는다: **새 칸이 생기면 아래 분류 단정이 먼저 실패한다.**

    죽이는 뮤테이션: `replace(...)`를 손열거 재구성으로 되돌리고 아무 칸이나 빼면
    (11칸 각각) 그 칸의 등식이 깨진다.
    """
    before, after = _r23_carry_over_pair()
    names = {field.name for field in _r23_fields(FixtureTypeLibrary)}
    carried = names - _R23_SWEEP_MUTATED_FIELDS - _R23_SWEEP_CONSTANT_FIELDS

    # 분류가 전 필드를 덮는다 — 새 칸은 세 집합 어디에도 없어 여기서 먼저 잡힌다.
    assert names == carried | _R23_SWEEP_MUTATED_FIELDS | _R23_SWEEP_CONSTANT_FIELDS
    assert carried, "옮겨야 할 칸이 하나도 없다면 이 게이트는 공허하다"

    for field in _r23_fields(FixtureTypeLibrary):
        if field.name not in carried:
            continue
        value = getattr(before, field.name)
        # 기본값 동형 대조군 금지 — 기본값과 같은 값이면 칸을 지워도 통과한다.
        assert value != _r23_default(field), f"{field.name}: 픽스처가 기본값을 만들었다"
        assert getattr(after, field.name) == value, field.name


def test_r23_the_sweep_actually_moves_the_fields_it_owns():
    """위 게이트의 반대편 — **바꿔도 되는 칸은 실제로 바뀐다**(면제 목록의 공허성 방지).

    `_R23_SWEEP_MUTATED_FIELDS`에 칸을 넣어 두기만 하면 위 시험을 통과시킬 수 있다.
    그 목록의 원소가 전부 이 입력에서 실제로 움직이는지 여기서 값으로 고정한다.
    """
    before, after = _r23_carry_over_pair()

    assert [entry.index for entry in before.types] == [1]
    assert [entry.index for entry in after.types] == [1, 3]
    assert after.types[1].name == "Robin LEDBeam 350"
    assert (before.recovered_count, after.recovered_count) == (0, 1)
    assert (before.recovery_boundary, after.recovery_boundary) == (None, 3)
    assert (before.probe_failures, after.probe_failures) == (0, 1)  # 2번은 이름을 못 얻었다
    assert (before.recovery_probe_count, after.recovery_probe_count) == (0, 2)  # 2·3번
    for field in _r23_fields(FixtureTypeLibrary):
        if field.name not in _R23_SWEEP_MUTATED_FIELDS:
            continue
        # 기본값이 아니고 **입력과도 다르다** — 후자가 없으면 면제 목록에 아무 칸이나
        # 밀어넣어(예: 이미 참인 `truncated`) 위 게이트를 조용히 무력화할 수 있다.
        assert getattr(after, field.name) != _r23_default(field), field.name
        assert getattr(after, field.name) != getattr(before, field.name), field.name


def test_r23_the_census_stays_complementary_through_the_recovery_path():
    """[R22-A] 상보식 `returned == enumerated + unusable + unparsable`이 **회수 뒤에도** 참.

    round21의 상보식 코퍼스는 `read_fixture_type_library`만 지나갔다 — 회수 경로를 한
    번도 밟지 않아, 재구성이 폐기 축을 지워도 등식을 재는 눈이 없었다. 경로가 늘면
    코퍼스도 늘어야 한다는 것이 이 행의 존재 이유다.
    """
    _before, after = _r23_carry_over_pair()

    # 비공허성 — 두 폐기 축이 각각 0이 아니다(0이면 등식이 자동 성립한다).
    assert (after.unusable_row_count, after.unparsable_row_count) == (1, 1)
    assert after.returned_row_count == (
        after.enumerated_count + after.unusable_row_count + after.unparsable_row_count
    )
    assert after.rows_discarded == 2
    assert after.enumeration_incomplete is True


def test_r23_a_swept_library_still_refuses_to_assert_absence():
    """[R22-A 감사 재현] 폐기 축이 살아 있으므로 **부재를 단정하지 않는다**.

    구판에서는 스윕이 폐기 계수를 지워 `enumeration_incomplete`가 거짓으로 내려앉고,
    판정이 `library_incomplete`에서 `library_absent`로 **하강**했다. 그러면서 round21이
    R20-D로 닫은 문장("콘솔 라이브러리에 대응 FixtureType 없음" — 조작자를 GDTF 임포트로
    보내는 지시)이 payload에 되살아났다. 그 문장이 **없음**을 여기서 단정한다.
    """
    payload = resolve_fixture_types(
        [TypeRequest(candidate_id="a", instrument_type="Vari-Lite VL6000", mode="Mode 1")],
        library_port=_R23DiscardSweepPort(_R21_THREE_TYPE_LIBRARY, nameless=(2,)),
    ).to_dict()
    row = row_by_id(payload, "a")

    # 스윕은 돌았고(경계가 섰다) 요청 이름은 끝내 못 찾았다 — 그래도 부재가 아니다.
    assert payload["library"]["recovery_boundary"] == 3
    assert payload["library"]["recovered_count"] == 0
    assert row["status"] == TYPE_LIBRARY_INCOMPLETE
    assert FIXTURE_TYPE_NOT_IN_LIBRARY not in hard_stop_codes(payload)
    assert target_exclusion_label(FIXTURE_TYPE_NOT_IN_LIBRARY) not in _r21_text(payload)
    # 폐기 축이 살아 있어 고지가 나간다.
    assert FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED in skipped_kinds(payload)
    assert payload["library"]["unusable_row_count"] == 1
    assert payload["library"]["unparsable_row_count"] == 1


# --- R22-C 콘솔 이름 쪽 모호성 --------------------------------------------

#: 감사 실증 그대로 — 슬롯2가 요청 이름을 **부분 포함**하는 다른 제품이고 정답은 슬롯3.
_R23_AMBIGUOUS_MODES = [("Mode 1", 16), ("Mode 2", 24)]
_R23_AMBIGUOUS_REQUEST = TypeRequest(
    candidate_id="a",
    instrument_type="Robin MMX Spot",
    gdtf_fixture="Robin MMX Spot",
    mode="Mode 1",
)


def _r23_ambiguous_port():
    return _R21ShortPort(
        _r21_types(["LEDWash 600"]),
        declared_types=3,
        hidden={
            2: ("Robin MMX Spot 15k", list(_R23_AMBIGUOUS_MODES)),
            3: ("Robin MMX Spot", list(_R23_AMBIGUOUS_MODES)),
        },
    )


def test_r23_the_sweep_does_not_collapse_console_name_ambiguity_to_one_slot():
    """[R22-C 감사 재현] 첫 퍼지 일치에서 멈추면 **엉뚱한 제품을 확정**했다.

    `fuzzy_type_equal`은 포함관계 매칭이다. 요청 `Robin MMX Spot`은 슬롯2
    `Robin MMX Spot 15k`에도 걸리고, 조기 종료판은 그것을 회수한 뒤
    `status=resolved · console_type='Robin MMX Spot 15k'`로 확정하며 **정답 슬롯3은
    프로브조차 하지 않았다**. 스윕이 없었으면 `library_incomplete`로 fail-closed
    배제되던 입력이 잘못된 확정으로 바뀐 것이다.
    """
    port = _r23_ambiguous_port()
    swept = recover_requested_types(port, read_fixture_type_library(port), ["Robin MMX Spot"])

    # ① 정답 슬롯이 **프로브된다** — 조기 종료판에서는 3번이 이 목록에 없었다.
    probed = sorted(int(path.rsplit("/", 1)[1]) for path in port.probe_paths)
    assert probed == [2, 3]
    # ② 일치는 전수로 회수된다 — 임의의 한 건으로 붕괴시키지 않는다.
    assert [entry.name for entry in swept.types] == [
        "LEDWash 600",
        "Robin MMX Spot 15k",
        "Robin MMX Spot",
    ]
    assert swept.recovered_count == 2


def test_r23_two_swept_matches_become_a_confirmation_not_a_verdict():
    """[R22-C] 모호성의 처분은 **열거 경로와 같다** — 후보 제시 · 확인 대기."""
    payload = resolve_fixture_types(
        [_R23_AMBIGUOUS_REQUEST], library_port=_r23_ambiguous_port()
    ).to_dict()
    row = row_by_id(payload, "a")

    assert row["status"] == TYPE_NEEDS_CONFIRMATION
    assert row["status"] != TYPE_RESOLVED
    # 엉뚱한 제품이 확정 칸에 앉지 않는다.
    assert row["console_type"] is None
    assert row["confirmation_source"] is None
    assert hard_stop_codes(payload) == []
    assert sorted(row["type_candidates"]) == ["Robin MMX Spot", "Robin MMX Spot 15k"]


def test_r23_the_enumeration_path_and_the_sweep_path_agree_on_ambiguity():
    """[R22-C] 두 경로가 **같은 입력에 같은 처분**을 낸다 — 규율이 경로별로 갈리지 않는다.

    같은 세 타입을 (ㄱ) 전부 열거로 실어 주는 콘솔과 (ㄴ) 두 개를 스윕으로만 닿게 하는
    콘솔에 각각 물어본다. 처분이 갈리면 그것이 R22-C의 기제 그 자체다.
    """
    enumerated_port = LibraryRigPort(
        [
            ("LEDWash 600", list(_R23_AMBIGUOUS_MODES)),
            ("Robin MMX Spot 15k", list(_R23_AMBIGUOUS_MODES)),
            ("Robin MMX Spot", list(_R23_AMBIGUOUS_MODES)),
        ]
    )
    from_enumeration = resolve_fixture_types(
        [_R23_AMBIGUOUS_REQUEST], library_port=enumerated_port
    ).to_dict()
    from_sweep = resolve_fixture_types(
        [_R23_AMBIGUOUS_REQUEST], library_port=_r23_ambiguous_port()
    ).to_dict()

    # 대조군 전제 — 한쪽은 열거로, 다른 쪽은 회수로 후보를 얻었다(경로가 실제로 다르다).
    assert from_enumeration["library"]["recovered_count"] == 0
    assert from_sweep["library"]["recovered_count"] == 2

    for key in ("status", "console_type", "console_mode", "confirmation_source"):
        assert row_by_id(from_enumeration, "a")[key] == row_by_id(from_sweep, "a")[key], key


# --- 경로 대조: 회수된 타입과 열거된 타입은 같은 칸을 들고 온다 -------------


class _R23ModeShapePort(LibraryRigPort):
    """모드 축 칸을 **전부 기본값이 아닌 값**으로 만드는 포트.

    두 번째 모드 행에서 슬롯 번호를 빼고(`unusable`), 매핑이 아닌 행을 하나 붙이며
    (`unparsable`), 선언 총계를 실린 행보다 크게 만들고(`mode_child_count` 대조),
    `truncated` 플래그도 세운다. `enumerate_only`로 루트 열거를 좁히면 같은 타입을
    **회수 경로**로만 닿게 할 수 있다 — 두 경로에 같은 응답을 먹이기 위한 장치다.
    """

    def __init__(self, types, *, enumerate_only=None, **kwargs):
        super().__init__(types, modes_truncated=True, **kwargs)
        self.enumerate_only = enumerate_only

    def query_state(self, path: str) -> dict:
        probe = re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)", path)
        if probe is not None:
            index = int(probe.group(1))
            return {
                "ok": True,
                "path": path,
                "node": {"name": self.types[index - 1][0], "class": "FixtureType"},
                "children": [],
                "truncated": False,
            }
        state = super().query_state(path)
        if state.get("ok") is not True:
            return state
        if path == FIXTURE_TYPE_LIBRARY_ROOT and self.enumerate_only is not None:
            rows = [row for row in state["children"] if row["i"] in self.enumerate_only]
            return {**state, "children": rows}
        if path.endswith(f"/{DMX_MODES_SEGMENT}"):
            rows = [dict(row) for row in state["children"]]
            for row in rows:
                if row.get("i") == 2:
                    row.pop("i")
            rows.append("not-a-mapping")
            node = {**state["node"], "childCount": state["node"]["childCount"] + 2}
            return {**state, "children": rows, "node": node}
        return state


#: 두 시나리오 — 모드 축이 **읽히는** 경우와 **안 읽히는** 경우. `modes_available`은
#: 읽히는 쪽에서 기본값(`True`)과 같아지므로 그 칸은 두 번째 시나리오가 덮는다.
_R23_PARITY_SCENARIOS = (("modes_readable", True), ("modes_unreadable", False))
#: 두 경로에서 **달라도 되는** 칸. `index`·`name`은 동일성 자체이고 `recovered`는
#: 유일하게 달라야 하는 출처 표시다.
_R23_PARITY_EXEMPT = frozenset({"index", "name", "recovered"})


def _r23_parity_entries(modes_readable: bool):
    """같은 타입(3번)을 **열거 경로**와 **회수 경로**로 각각 읽어 돌려준다."""
    types = _R21_THREE_TYPE_LIBRARY
    full = read_fixture_type_library(_R23ModeShapePort(types, modes_readable=modes_readable))
    short_port = _R23ModeShapePort(types, enumerate_only={1, 2}, modes_readable=modes_readable)
    swept = recover_requested_types(
        short_port, read_fixture_type_library(short_port), ["Robin LEDBeam 350"]
    )
    enumerated = next(entry for entry in full.types if entry.index == 3)
    recovered = next(entry for entry in swept.types if entry.index == 3)
    # 대조군 전제 — 한쪽은 열거, 다른 쪽은 회수로 왔다.
    assert enumerated.recovered is False and recovered.recovered is True
    return enumerated, recovered


@pytest.mark.parametrize(
    "label,modes_readable", _R23_PARITY_SCENARIOS, ids=[row[0] for row in _R23_PARITY_SCENARIOS]
)
def test_r23_a_recovered_type_carries_every_field_an_enumerated_one_does(
    label: str, modes_readable: bool
):
    """[R22-A 형제 축] 회수 경로가 `LibraryType`의 **어느 칸도** 떨어뜨리지 않는다.

    round21의 대조군은 칸 이름 아홉 개를 손으로 적었고, 픽스처가 그중 넷을 기본값으로
    만들어 **그 넷은 지워도 통과**했다(round22 실측 Y02·Y03·C22 생존). 여기서는
    `dataclasses.fields`로 훑고, 아래 비공허성 시험이 "각 칸이 최소 한 시나리오에서
    기본값이 아니다"를 따로 단정한다.
    """
    enumerated, recovered = _r23_parity_entries(modes_readable)
    for field in _r23_fields(LibraryType):
        if field.name in _R23_PARITY_EXEMPT:
            continue
        assert getattr(recovered, field.name) == getattr(enumerated, field.name), (
            label,
            field.name,
        )


def test_r23_the_parity_exemption_list_is_not_a_silencer():
    """면제 목록의 **공허성 방지** — 면제된 칸은 동일성이거나 실제로 달라야 한다.

    `_R23_PARITY_EXEMPT`에 칸을 하나 밀어넣으면 위 대조군이 그 칸을 조용히 안 본다.
    round22 실측: 면제 목록에 `modes_truncated`를 더하면 회수 경로가 그 칸을 떨어뜨려도
    아무 시험이 죽지 않았다. 그래서 면제 **사유**를 값으로 검사한다 — `index`·`name`은
    같은 슬롯을 두 경로로 읽은 것이라 같아야 하고, 그 밖의 면제(=`recovered`)는
    달라야 한다. 같은데도 면제된 칸은 사유 없는 면제다.
    """
    for _label, modes_readable in _R23_PARITY_SCENARIOS:
        enumerated, recovered = _r23_parity_entries(modes_readable)
        for name in sorted(_R23_PARITY_EXEMPT):
            pair = (getattr(enumerated, name), getattr(recovered, name))
            if name in ("index", "name"):
                assert pair[0] == pair[1], name
            else:
                assert pair[0] != pair[1], name


def test_r23_the_parity_corpus_makes_every_compared_field_non_default():
    """위 대조군의 **비공허성** — 비교되는 칸마다 기본값이 아닌 값이 최소 한 번은 온다.

    이것이 없으면 회수 경로에서 그 칸을 통째로 빼도 대조군이 통과한다. round22가
    `modes_available`·`modes_truncated`·`unparsable_mode_row_count`에서 실제로 그랬다.
    """
    seen: dict[str, bool] = {}
    for _label, modes_readable in _R23_PARITY_SCENARIOS:
        _enumerated, recovered = _r23_parity_entries(modes_readable)
        for field in _r23_fields(LibraryType):
            if field.name in _R23_PARITY_EXEMPT:
                continue
            non_default = getattr(recovered, field.name) != _r23_default(field)
            seen[field.name] = seen.get(field.name, False) or non_default
    assert seen, "비교 대상이 하나도 없다"
    assert all(seen.values()), sorted(name for name, ok in seen.items() if not ok)


# --- 손열거 재구성 규율을 게이트로 -----------------------------------------
#
# [round23 R23-3] R22-A가 세운 이 게이트는 **전수가 아니었다.** 사각지대는 파일 범위가
# 아니라 **이름 해석**에 있었다 — 구판 해석기는 `if name not in declared: return None`,
# 즉 그 모듈이 **스스로 선언한** dataclass만 봤다. 형제 모듈에서 임포트해 쓰는 타입은
# 통째로 보이지 않았고, 감사가 `apply.py`의 `LuaPatchEntry(...)`(선언은 `luagen.py`)를
# 그 실증으로 지목했다.
#
# 이 결함이 round17 스코프 등기부(`test_autopatch_contract._r17_ast_scanners`)에 걸리지
# 않은 이유가 중요하다: 그 등기부는 스캐너가 **어느 파일을 읽는가**만 재고, 그 파일
# 안에서 **어느 이름을 해석하는가**는 재지 않는다. 파일 범위는 이미 전 모듈이었으므로
# 등기부에는 `ALL`로 올라 있었다 — 넓은 표면 위의 좁은 해석은 그 등기부의 사각이다.
# 그래서 여기서는 해석을 **모듈 속성 조회**로 바꾸고(임포트·재수출된 이름도 같은 규율에
# 들어온다), 스코프를 이 절이 **디스크와 등식으로** 스스로 단정한다.
#
# **등기부에서 빠지는 것을 공시한다.** 순회가 인자 `root`를 받게 되면서 이 스캐너는 그
# 등기부에서 `self_bound`(전 모듈)가 아니라 `caller`로 분류된다 — 즉 "server/vwx 전 모듈을
# 읽는 스캐너" 명단에서 빠진다. 등기에서 조용히 사라지는 것이 이 SPEC의 반복 실패 형태라
# 여기 적어 둔다: 그 자리를 `test_r23_the_reconstruction_gate_reads_every_file_in_its_tree`가
# 대신하고, 그 시험은 등기부의 규율보다 **강하다** — 독스트링에 경로를 적었는지가 아니라
# 스캔한 파일 집합이 디스크의 트리와 **같은지**를 잰다.
#
# **선을 어디에 긋는가 — `server/vwx/**`.**
#
#   ㉠ `diff.py`·`rig.py`(1단계 확정 산출물)도 **안에 둔다.** 실측: 그 둘은 자리 3개를
#      갖고 있고 셋 다 전 칸을 넘긴다. 게다가 두 파일은 이 SPEC이 **바꾸지 않는** 파일이라
#      새 위반이 생길 수 없다 — 「고칠 수 없는 것을 잡는다」는 위험은 **변경되는 파일**에서만
#      실현된다. 오늘 발화하지 않고 내일도 발화할 수 없는 자리를 면제하는 것은 근거 없는
#      면제이며, 근거 없는 면제는 다음 라운드에 면제를 부풀리는 선례가 된다.
#
#   ㉡ 감사가 범위 밖으로 적은 `diff.py:179`는 **다른 형태**다 — `next((...), None)`의 첫
#      일치 붕괴(R22-C 계열)이지 손열거 재구성이 아니다. 이 게이트는 그것을 보지 않는다.
#      그쪽 게이트를 `diff.py`까지 넓히는 것이야말로 고칠 수 없는 것을 잡는 일이고, 그
#      판단은 그 게이트의 소관이다. 형태가 다른 두 축을 여기서 뭉뚱그리지 않는다.
#
#   ㉢ PRESERVE 트리는 **밖에 둔다** — 발화해도 고칠 수 없어 영구 실패가 된다. 그 선을
#      `_R23_UNGATED_TREES`에 사유와 함께 등기하고, 등기가 **공허하지 않음**을(=선 너머에
#      실제로 고칠 수 없는 위반이 있음을) 대조군이 잰다. 등기가 공허하면 그 선은 지킬
#      것이 없는 선이고, 그런 선은 지우는 편이 낫다.

import dataclasses  # noqa: E402
import hashlib  # noqa: E402
import importlib  # noqa: E402

#: 게이트가 강제하는 트리. 이 SPEC의 확장 대상이라 **발화하면 고칠 수 있다**.
_R23_GATED_TREE = Path("server/vwx")

#: 선 **밖**의 트리와 사유. 전부 spec.md §PRESERVE가 무변경으로 못박은 파이썬 트리다 —
#: 게이트를 여기까지 넓히면 고칠 수 없는 위반을 잡아 영구 실패가 된다.
#: (`console/lua/**`도 PRESERVE지만 파이썬이 아니라 애초에 이 스캐너의 사정권 밖이다.)
_R23_UNGATED_TREES = {
    "server/prechk": "8개 파일 전량 무변경 — 이 SPEC은 `precheck_patch`의 소비자다",
    "server/looks": "룩 파이프라인 전량 무변경",
    "server/safety": "안전 게이트 전량 무변경",
    "server/paperwork": "무변경",
}


def _r23_reconstruction_sites(tree, resolve):
    """AST 하나에서 **자기 필드를 손으로 옮겨 담는 생성자 호출**을 전수한다.

    판별 신호는 하나다: 어떤 dataclass `T(...)` 호출의 키워드 인자 중 **이름이 같은
    속성을 그대로 옮기는 것**(`foo=x.foo`)이 하나라도 있으면, 그 자리는 기존 객체의
    칸을 손으로 옮겨 담고 있다는 뜻이다. R22-A가 정확히 그 형태였다.

    [round23 R23-3] 호출 대상은 `T(...)`뿐 아니라 `mod.T(...)`도 본다 — 이름을 어떻게
    적었는지가 규율의 적용 여부를 갈라서는 안 된다. 실제 해석은 `resolve`가 한다.
    """
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called = node.func.id
        elif isinstance(node.func, ast.Attribute):
            called = node.func.attr
        else:
            continue
        target = resolve(called)
        if target is None:
            continue
        keywords = [kw for kw in node.keywords if kw.arg]
        if not any(
            isinstance(kw.value, ast.Attribute) and kw.value.attr == kw.arg for kw in keywords
        ):
            continue
        passed = {kw.arg for kw in keywords}
        missing = [field.name for field in _r23_fields(target) if field.name not in passed]
        found.append((called, node.lineno, missing))
    return found


def _r23_module_resolver(path: Path):
    """파일 경로 → 그 모듈의 **이름 해석기**. 이름을 모듈 **속성**으로 해석한다.

    R23-3의 처방이 이 한 줄이다. 구판은 "그 모듈이 선언한 클래스인가"를 물었고, 그래서
    형제 모듈에서 임포트한 dataclass를 손으로 재구성하는 자리가 전부 사각지대였다.
    속성 조회는 선언 위치를 묻지 않으므로 임포트·재수출된 이름도 같은 규율에 들어온다.
    """
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    module = importlib.import_module(".".join(parts))

    def resolve(name: str):
        target = getattr(module, name, None)
        if isinstance(target, type) and dataclasses.is_dataclass(target):
            return target
        return None

    return resolve


def _r23_reconstruction_files(root) -> list[Path]:
    """지정한 트리 아래 `.py` 파일 **전수** — 공용 순회를 그대로 쓴다.

    `glob`으로 좁히면 오늘은 결과가 같다(`server/vwx`에 하위 패키지가 없다). 그래서
    이 함수는 합성 트리로 따로 잰다 — 오늘 같은 값을 내는 축소는 게이트가 못 잡는다.
    [round24] 재귀성과 제외 규칙은 `iter_vwx_modules` 한 자리에만 있다. 여기서 다시
    `rglob`을 적으면 제외 규칙이 두 벌이 되고, 두 벌은 곧 갈라진다.
    """
    return list(iter_vwx_modules(root))


def _r23_tree_fingerprint(root) -> str:
    """트리의 **내용 지문** — 파일 경로와 본문 해시. 스캔 캐시의 키다.

    수정 시각·크기가 아니라 본문을 읽는다: 같은 크기·같은 mtime으로 내용만 바뀐 파일이
    캐시를 통과하는 구멍을 남기지 않기 위해서다. stale이 **불가능**한 것이지 드문 것이
    아니어야 한다. 비용은 실측으로 무시할 수 있다(지문 0.4ms 대 스캔 22ms).
    """
    digest = hashlib.blake2b(digest_size=16)
    for path in _r23_reconstruction_files(root):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


_R23_SCAN_CACHE: dict[str, tuple[list[str], list[tuple]]] = {}


def _r23_scan_reconstructions(root, resolver=None):
    """지정한 트리를 훑어 `(읽은 파일 전수, 손열거 재구성 자리 전수)`를 낸다.

    스코프는 **인자 `root`**가 정한다 — 이 함수는 무엇을 읽을지 스스로 고르지 않는다.
    기본 해석기로 부른 결과만 내용 지문으로 캐시한다(전 모듈 스캔이 22ms라 호출마다
    다시 도는 것이 수집 시간에 실제로 잡힌다). 지문이 본문 해시라 stale은 성립하지 않는다.
    """
    resolve_for = _r23_module_resolver if resolver is None else resolver
    key = None
    if resolver is None:
        key = f"{Path(root).as_posix()}@{_r23_tree_fingerprint(root)}"
        cached = _R23_SCAN_CACHE.get(key)
        if cached is not None:
            return cached

    files: list[str] = []
    sites: list[tuple] = []
    for path in _r23_reconstruction_files(root):
        files.append(path.as_posix())
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls, lineno, missing in _r23_reconstruction_sites(tree, resolve_for(path)):
            sites.append((path.as_posix(), cls, lineno, tuple(missing)))
    result = (files, sites)
    if key is not None:
        _R23_SCAN_CACHE[key] = result
    return result


def _r23_scan_vwx_reconstructions():
    """`server/vwx` **전 모듈**의 재구성 자리 — 모듈 이름을 손으로 적지 않는다."""
    return _r23_scan_reconstructions(_R23_GATED_TREE)[1]


def _r23_offenders(sites):
    return [site for site in sites if site[3]]


def test_r23_every_hand_written_reconstruction_passes_every_field():
    """[R22-A 규율] 손으로 칸을 옮기는 자리는 **전 칸을 옮긴다** — `server/vwx` 전수.

    R22-A는 한 자리의 실수가 아니라 **형태**의 실수다: 칸을 손으로 열거하는 재구성은
    칸이 늘 때마다 빠뜨릴 자리가 하나씩 는다. 그래서 개별 자리를 고치는 대신 형태에
    게이트를 건다 — 어느 모듈에서든 `foo=x.foo`로 칸을 옮기기 시작했으면 그 dataclass의
    **모든** 칸을 옮겨야 하고, 그럴 수 없으면 `dataclasses.replace()`를 써야 한다.

    새 칸이 dataclass에 생기면 그 타입을 손으로 재구성하는 자리가 **전부 여기서
    실패한다** — 그것이 이 게이트의 목적이다.

    [round23 R23-3] 이 단정은 상한이다: 자리를 고치면 언제나 통과하고, 어느 모듈에서든
    새 위반이 생기면 실패한다. 그래서 규율을 강화하는 편집이 이 단정을 깨뜨리지 않는다.
    """
    offenders = _r23_offenders(_r23_scan_vwx_reconstructions())
    assert not offenders, (
        "손으로 칸을 옮기면서 일부만 옮긴 자리 — 전 칸을 넘기거나 "
        f"`dataclasses.replace()`로 바꿔라:\n{offenders}"
    )


def test_r23_the_reconstruction_gate_resolves_types_declared_in_sibling_modules():
    """[R23-3 주입 대조군] **사각지대였던 자리가 이제 보인다.**

    감사가 지목한 실증 그대로 잰다 — `apply.py`가 `luagen.py`의 `LuaPatchEntry`를 손으로
    지어 담는 자리다. ①넓힌 해석기는 그 자리를 본다. ②구판 해석기(같은 모듈 선언만)는
    **보지 못한다** — 그래야 넓힘이 원인임이 고정된다. ③보기만 하는 것으로는 부족하니
    칸 하나를 뺀 사본을 심어 실제로 결손을 신고하는지 본다. ④같은 타입을 `mod.T(...)`로
    적어도 같은 판정이 난다 — 이름을 어떻게 적었는지가 규율을 갈라서는 안 된다.
    """
    _files, sites = _r23_scan_reconstructions(_R23_GATED_TREE)
    seen = {(path, cls) for path, cls, _lineno, _missing in sites}
    assert ("server/vwx/apply.py", "LuaPatchEntry") in seen, sorted(seen)

    # ② 구판 해석기 재현 — 이름이 **그 모듈에 선언**되어야만 해석한다.
    apply_path = Path("server/vwx/apply.py")
    tree = ast.parse(apply_path.read_text(encoding="utf-8"))
    declared = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    module = importlib.import_module("server.vwx.apply")

    def resolve_same_module_only(name):
        if name not in declared:
            return None
        target = getattr(module, name, None)
        return target if dataclasses.is_dataclass(target) else None

    narrow = {
        cls for cls, _lineno, _missing in _r23_reconstruction_sites(tree, resolve_same_module_only)
    }
    assert "LuaPatchEntry" not in narrow, narrow
    assert narrow, "구판이 아무것도 못 봤다면 ②는 넓힘의 효과를 증명하지 못한다"

    # ③ 그 타입에서 칸을 하나 빼면 신고한다 — 보는 것과 잡는 것은 다르다.
    lua_entry = module.LuaPatchEntry
    names = [field.name for field in _r23_fields(lua_entry)]
    kept = ", ".join(f"{name}=entry.{name}" for name in names[:-1])
    planted = ast.parse(f"def f(entry):\n    return LuaPatchEntry({kept})\n")
    reported = _r23_reconstruction_sites(
        planted, lambda name: lua_entry if name == "LuaPatchEntry" else None
    )
    assert [site[2] for site in reported] == [[names[-1]]], reported

    # ④ 점 표기 호출도 같은 자리다 — 임포트 형태를 바꿔 규율을 피할 수 없다.
    dotted = ast.parse(f"def f(entry):\n    return luagen.LuaPatchEntry({kept})\n")
    assert (
        _r23_reconstruction_sites(
            dotted, lambda name: lua_entry if name == "LuaPatchEntry" else None
        )
        == reported
    )


def test_r23_the_reconstruction_gate_reads_every_file_in_its_tree():
    """[R23-3 범위 축소 대조군] 스캔한 파일 집합이 **디스크의 트리 전부**와 같다.

    기대값을 이 시험이 **독립으로** 계산한다 — 스캐너가 모듈 이름을 손으로 열거하는
    형태로 되돌아가면(round17 #7이 실증한 그 축소) 여기서 등식이 깨진다.
    """
    expected = sorted(path.as_posix() for path in Path("server/vwx").rglob("*.py"))
    files, _sites = _r23_scan_reconstructions(_R23_GATED_TREE)
    assert files == expected
    assert len(expected) >= 10, expected  # 트리가 비면 위 등식은 공허하다


def test_r23_the_reconstruction_scan_descends_into_new_subpackages(tmp_path):
    """[R23-3 새 모듈 사각지대 대조군] 하위 패키지가 생기면 **따라 내려간다**.

    `server/vwx`에 오늘 하위 디렉터리가 없어서 `rglob`을 `glob`으로 좁혀도 결과가 같다 —
    실물만으로는 그 축소를 잴 수 없다. 그래서 합성 트리로 잰다. 해석기를 주입해
    임포트 없이 도는 것도 이 대조군의 요건이다: 사각지대는 **순회**의 문제이지 해석의
    문제가 아니므로 두 축을 섞지 않는다.
    """

    @dataclass(frozen=True)
    class _Grown:
        index: int
        name: str
        added: int = 0

    nested = tmp_path / "pkg" / "deep"
    nested.mkdir(parents=True)
    (tmp_path / "pkg" / "shallow.py").write_text(
        "def f(x):\n    return Grown(index=x.index, name=x.name, added=x.added)\n",
        encoding="utf-8",
    )
    (nested / "buried.py").write_text(
        "def f(x):\n    return Grown(index=x.index, name=x.name)\n", encoding="utf-8"
    )

    files, sites = _r23_scan_reconstructions(
        tmp_path, resolver=lambda _path: lambda name: _Grown if name == "Grown" else None
    )
    assert [Path(name).name for name in files] == ["buried.py", "shallow.py"]
    buried = [site for site in sites if site[0].endswith("buried.py")]
    assert [site[3] for site in buried] == [("added",)], sites
    # 얕은 자리는 전 칸을 넘긴다 — 순회가 넓어져도 위양성을 만들지 않는다.
    assert [site[3] for site in sites if site[0].endswith("shallow.py")] == [()]


def test_r23_the_reconstruction_scan_cache_cannot_go_stale(tmp_path):
    """캐시의 건전성 — 지문이 **본문**을 읽으므로 내용이 바뀌면 반드시 키가 바뀐다.

    캐시를 두는 순간 "고쳤는데 옛 결과가 나온다"가 가능해진다. 크기·수정 시각 지문은
    같은 크기·같은 나노초에 내용만 바뀐 파일을 통과시킨다 — 드문 것과 불가능한 것은
    다르고, 게이트의 근거는 후자여야 한다. 여기서 그 불가능성을 네 축으로 잰다.
    """
    target = tmp_path / "mod.py"
    target.write_text("A = 1\n", encoding="utf-8")
    first = _r23_tree_fingerprint(tmp_path)

    # ① 같은 내용을 다시 읽으면 같은 지문이다(캐시 적중이 정당하다).
    assert _r23_tree_fingerprint(tmp_path) == first
    # ② 같은 크기 · 내용만 다르면 지문이 바뀐다 — mtime에 기대지 않는다는 증거다.
    target.write_text("A = 2\n", encoding="utf-8")
    same_size = _r23_tree_fingerprint(tmp_path)
    assert same_size != first
    # ③ 파일이 늘면 바뀐다.
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "other.py").write_text("A = 2\n", encoding="utf-8")
    grown = _r23_tree_fingerprint(tmp_path)
    assert grown not in (first, same_size)
    # ④ 같은 본문이라도 **경로가 다르면** 다른 지문이다(본문만 이어붙이면 뭉개진다).
    (tmp_path / "sub" / "other.py").rename(tmp_path / "sub" / "renamed.py")
    assert _r23_tree_fingerprint(tmp_path) != grown


def _r23_ungated_scan():
    """등기된 선 밖 트리 각각의 `(자리 수, 위반 목록)`. 등기 키가 스코프를 정한다(caller)."""
    measured = {}
    for tree in _R23_UNGATED_TREES:
        _files, sites = _r23_scan_reconstructions(Path(tree))
        measured[tree] = (len(sites), _r23_offenders(sites))
    return measured


def test_r23_every_ungated_tree_exists_and_is_inside_the_scanners_reach():
    """제외 등기가 **실재**한다 — 디렉터리가 있고, 스캐너가 실제로 자리를 뽑는다.

    이 확인이 없으면 등기에 아무 경로나 밀어넣어 "선을 그었다"고 적을 수 있다. 스캐너가
    자리를 하나도 못 뽑는 트리는 애초에 이 게이트와 무관하므로 제외 사유가 될 수 없다.
    """
    assert _R23_UNGATED_TREES, "제외가 0건이면 아래 대조군이 전부 공허하다"
    measured = _r23_ungated_scan()
    assert sorted(measured) == sorted(_R23_UNGATED_TREES)
    empty = [tree for tree, (count, _offenders) in measured.items() if count == 0]
    assert empty == [], f"스캐너 사정권 밖의 경로가 제외로 등기됐다: {empty}"


def test_r23_the_ungated_line_carries_weight():
    """제외가 **부담을 진다** — 선 너머에 고칠 수 없는 위반이 실제로 있다.

    이것이 0이면 선은 지킬 것이 없는 선이고, 그때는 선을 지우고 전부 게이트하는 편이
    옳다. 즉 이 단정은 제외를 정당화하는 것이 아니라 **제외의 값을 청구**한다.
    """
    measured = _r23_ungated_scan()
    carried = {tree: offenders for tree, (_count, offenders) in measured.items() if offenders}
    assert carried, (
        "제외 트리 전부가 이미 규율을 지킨다 — 선을 지우고 게이트 안으로 옮겨라: "
        f"{ {tree: count for tree, (count, _o) in measured.items()} }"
    )


def test_r23_shrinking_the_ungated_line_keeps_the_gate_green():
    """규율 3 — **제외를 줄이는 것은 개선**이므로 줄여도 통과해야 한다.

    위반이 0인 제외 트리는 게이트 안으로 옮겨도 지금 그대로 통과한다. 그 사실을 실제로
    게이트 판정식에 먹여 확인한다 — 제외가 "혹시 몰라서" 넓게 쳐진 보호막이 아니라는
    증거다. (오늘 그런 트리가 있는지는 실측이 정한다. 전부 위반을 안고 있으면 이 시험은
    옮길 대상이 없다고 보고하고, 그 사실 자체는 위 `carries_weight`가 재고 있다.)
    """
    measured = _r23_ungated_scan()
    assert len(measured) == len(_R23_UNGATED_TREES)
    shrinkable = [tree for tree, (_count, offenders) in measured.items() if not offenders]
    for tree in shrinkable:
        widened = _r23_offenders(_r23_scan_vwx_reconstructions())
        widened += measured[tree][1]
        assert widened == [], (tree, widened)
    assert shrinkable == ["server/paperwork"], (
        "제외 트리의 위반 분포가 바뀌었다 — 줄일 수 있는 제외를 다시 판정하라: "
        f"{ {tree: len(offenders) for tree, (_c, offenders) in measured.items()} }"
    )


def test_r23_every_ungated_tree_is_a_registered_preserve_path():
    """제외 **사유**가 spec.md §PRESERVE 등기와 대조된다 — 사유를 여기서 지어내지 않는다.

    "고칠 수 없다"는 이 시험 파일이 정할 수 있는 사실이 아니다. 정본이 무변경으로 못박은
    트리만 제외될 수 있고, 정본에 없는 경로를 제외로 밀어넣으면 여기서 실패한다.
    """
    spec = Path(".moai/specs/SPEC-COPILOT-AUTOPATCH-001/spec.md").read_text(encoding="utf-8")
    head = spec.index("### PRESERVE — 무변경 대상")
    section = spec[head : spec.index("\n### ", head + 1)]
    assert "server/vwx/**`는 **확장 대상이므로 PRESERVE가 아니다" in section, section[:400]
    for tree in _R23_UNGATED_TREES:
        assert f"`{tree}/**`" in section, (tree, section)


def test_r23_the_reconstruction_scanner_is_not_vacuous():
    """스캐너 건전성 — **실제로 자리를 뽑고**, 칸을 빼면 잡는다.

    게이트가 "아무것도 못 찾는 함수"면 위 시험은 항진식이다. 자리 수를 값으로 못박지는
    않는다(무관한 편집에 밀린다) — 대신 여러 모듈에서 뽑히는지와, 칸을 하나 뺀 소스에
    대해 실제로 결손을 신고하는지를 본다.
    """
    sites = _r23_scan_vwx_reconstructions()
    assert len({module for module, *_rest in sites}) >= 4, sites

    def resolve(name):
        return LibraryType if name == "LibraryType" else None

    seeded = ast.parse(
        "def f(entry):\n"
        "    return LibraryType(index=entry.index, name=entry.name, modes=entry.modes)\n"
    )
    reported = _r23_reconstruction_sites(seeded, resolve)
    assert len(reported) == 1
    assert "unusable_mode_row_count" in reported[0][2]

    # 반대편 — 전 칸을 넘기면 결손이 없다(위양성 아님).
    total = ", ".join(f"{field.name}=entry.{field.name}" for field in _r23_fields(LibraryType))
    clean = ast.parse(f"def f(entry):\n    return LibraryType({total})\n")
    assert _r23_reconstruction_sites(clean, resolve)[0][2] == []


# --- R22-F 비용 근거의 유효 범위 -------------------------------------------


def test_r23_the_cost_ceiling_is_the_number_the_docstring_already_rejected():
    """[R22-F] 상수는 **지어낸 수가 아니다** — 전수 스윕을 기각한 그 왕복 수다.

    근거 없는 상한을 짓지 않는 판단은 round18이 FID 상한에서 이미 내렸다. 여기서도
    새 수를 만들지 않고, 독스트링이 이미 기각 근거로 쓴 값을 이름 붙여 꺼냈다 —
    그래서 근거와 상수가 **같은 자리에서 검증된다**.
    """
    assert RECOVERY_COST_EVIDENCE_ROUNDTRIPS == 3_872
    assert "3,872" in TYPEMAP_SOURCE
    # 판단도 소스에 적혀 있다: 이것은 상한이 아니라 고지다.
    assert "상한이 아니다" in TYPEMAP_SOURCE


def test_r23_a_library_that_was_never_swept_makes_no_cost_claim():
    """[R22-F] 안 훑었으면 왕복 수는 0이고 범위 판정은 **`None`**이다.

    `False`라 적으면 "쟀는데 범위 안이었다"가 되어, 훑지 않은 것과 싸게 훑은 것이 한
    칸에 뭉개진다 — `recovery_boundary`가 `None`인 것과 같은 이유다.
    """
    library = read_fixture_type_library(LibraryRigPort(_r21_types(["LEDWash 600"])))

    assert library.recovery_probe_count == 0
    assert library.recovery_cost_basis_exceeded is None
    assert library.to_dict()["recovery_cost_basis_exceeded"] is None


def test_r23_a_cheap_sweep_reports_its_cost_and_stays_inside_the_evidence():
    """[R22-F] 왕복 수는 **실측 기록**이고, 그 값이 근거 범위 안임을 payload가 말한다."""
    port = _r21_sweep_port()
    swept = recover_requested_types(port, read_fixture_type_library(port), ["MegaPointe"])

    assert swept.recovery_probe_count == len(port.probe_paths) == 29
    assert swept.recovery_cost_basis_exceeded is False
    payload = swept.to_dict()
    assert payload["recovery_probe_count"] == 29
    assert payload["recovery_cost_basis_exceeded"] is False


def test_r23_a_sweep_past_the_evidence_says_so_and_still_recovers():
    """[R22-F] 근거 범위를 넘으면 **고지한다 — 거부하지 않는다**.

    거부하면 느리지만 옳은 답이 임의의 수치 때문에 `fixture_type_not_in_library`
    배제로 바뀌어, 이 스윕이 없애려던 거짓 부재가 돌아온다. 그래서 이 시험은 두 가지를
    함께 단정한다: 고지가 서고, **회수는 그대로 일어난다**.
    """
    declared = RECOVERY_COST_EVIDENCE_ROUNDTRIPS + 2
    port = _R21ShortPort(
        _r21_types(["LEDWash 600"]),
        declared_types=declared,
        hidden={declared: ("MegaPointe", [("Mode 1", 16)])},
    )
    swept = recover_requested_types(port, read_fixture_type_library(port), ["MegaPointe"])

    assert swept.recovery_probe_count == declared - 1
    assert swept.recovery_probe_count >= RECOVERY_COST_EVIDENCE_ROUNDTRIPS
    assert swept.recovery_cost_basis_exceeded is True
    # 고지는 거부가 아니다 — 회수분은 그대로 실려 나간다.
    assert swept.recovered_count == 1
    assert [entry.name for entry in swept.types] == ["LEDWash 600", "MegaPointe"]


# --- R23-2 비용 계수의 빠진 항 · R23-4 경계 --------------------------------
#
# 구판 `recovery_cost_basis_exceeded`는 `recovery_probe_count`(= `U`, 이름 프로브)만
# 봤다. R22-C가 조기 종료를 없애면서 `k`가 `0..U`로 풀렸는데 `_read_type` 왕복
# `k(1 + c·m)`이 계수에서 빠졌다 — **독스트링은 그 항을 알고 적었고 구현만 뺐다.**
# 감사 실측: 선언 300 · U=299 · k=299 · m=20에서 실제 6,578왕복(≈436초)으로 기각선
# 3,872를 넘는데 고지는 `False`였다. `False`는 "쟀는데 범위 안"이라는 **긍정 주장**이라
# (R22-B가 방금 고친 `max(..., 0) = 0`과 같은 기제) 그 자리에서 거짓말이다.
#
# 아래 대조군은 **수열 동등을 쓰지 않는다** — `assert probed == [2..8]`류가 이 SPEC을
# 반복해서 망가뜨린 형태다. 상한 · 불변식 · 단조성 · 경계 등식만 단정하고, 성질
# 하나에 시험 하나를 붙인다.
# --------------------------------------------------------------------------


def _r23_cost_port(*, declared: int, matching: int, modes: int) -> _R21ShortPort:
    """미열거 슬롯이 **전부 응답하는** 포트 — `U`를 고정한 채 `k`만 움직인다.

    슬롯 `2..declared` 중 앞 `matching`개는 요청 이름을 그대로 갖고(= 회수 대상 `k`,
    각각 `modes`개의 모드 = `m`), 나머지는 걸리지 않는 이름이라 **프로브만 먹고
    회수되지 않는다**. 슬롯 1은 열거로 온 무관한 타입이라 스윕 전제를 세운다.
    """
    rows = [(f"Mode {number}", 16) for number in range(1, modes + 1)]
    hidden = {
        index: (("MegaPointe", list(rows)) if offset < matching else (f"Filler {index}", []))
        for offset, index in enumerate(range(2, declared + 1))
    }
    return _R21ShortPort(_r21_types(["LEDWash 600"]), declared_types=declared, hidden=hidden)


def _r23_cost_boundary_port(ceiling: int) -> _R21ShortPort:
    """왕복 상한이 **정확히** `ceiling`이 되는 포트.

    미열거 슬롯은 `ceiling - 1`개(= `U`)이고 그중 마지막 하나만 요청 이름을 갖는다.
    그 하나는 **모드가 없어서**(`m = 0`) `_read_type`이 DMXModes 상태 1회로 끝나므로
    합은 ``(ceiling - 1) + 1``이다.
    """
    hidden = {index: (f"Filler {index}", []) for index in range(2, ceiling + 1)}
    hidden[ceiling] = ("MegaPointe", [])
    return _R21ShortPort(_r21_types(["LEDWash 600"]), declared_types=ceiling, hidden=hidden)


def _r23_cost_sweep(port, *, read_channel_counts: bool = False):
    return recover_requested_types(
        port,
        read_fixture_type_library(port, read_channel_counts=read_channel_counts),
        ["MegaPointe"],
        read_channel_counts=read_channel_counts,
    )


def _r23_cost_sweep_and_spend(port, *, read_channel_counts: bool = False):
    """스윕만 돌리고 **그동안 포트가 실제로 받은 왕복 수**를 함께 돌려준다."""
    enumerated = read_fixture_type_library(port, read_channel_counts=read_channel_counts)
    before = len(port.state_calls) + len(port.property_calls)
    swept = recover_requested_types(
        port, enumerated, ["MegaPointe"], read_channel_counts=read_channel_counts
    )
    return swept, len(port.state_calls) + len(port.property_calls) - before


def test_r23_the_cost_notice_counts_the_read_type_term_it_already_named():
    """[R23-2] 감사가 든 입력에서 고지가 **선다**.

    선언 300 · U=299 · k=299 · m=20 — 실제 6,578왕복(≈436초)이라 기각선 3,872를 한참
    넘는다. `U`만 세는 구판은 299를 보고 "범위 안"이라 적었다.
    """
    swept = _r23_cost_sweep(_r23_cost_port(declared=300, matching=299, modes=20))
    # 대조군 전제 — 감사가 든 그 형상에 실제로 닿았다.
    assert (swept.recovery_probe_count, swept.recovered_count) == (299, 299)
    assert len(swept.types[-1].modes) == 20

    assert swept.recovery_cost_basis_exceeded is True


def test_r23_the_cost_ceiling_never_understates_the_negative_branch_sweep():
    """[R23-2] 불변식 — 고지가 재는 수는 **실제로 쓴 왕복 수보다 작지 않다**.

    방향이 규율이다. `False`는 "쟀는데 범위 안"이라는 긍정 주장이므로 과소보고하는
    계수는 그 주장을 거짓으로 만든다. 과다는 보수적 고지일 뿐, 이 칸은 거부가 아니라
    고지라 스윕을 막지 않는다.
    """
    swept, spent = _r23_cost_sweep_and_spend(_r23_cost_port(declared=30, matching=29, modes=5))
    # 대조군 전제 — 이름 프로브가 비용의 전부가 아니다(전부면 구판도 통과한다).
    assert spent > swept.recovery_probe_count

    assert swept.recovery_roundtrip_ceiling >= spent


def test_r23_the_cost_ceiling_never_understates_the_occupancy_branch_sweep():
    """[R23-2] 같은 불변식을 **점유폭 GO 분기**에서 잰다 — `c = 2`인 쪽이다.

    [round24 R24-5] 이제 스윕이 자기 단가를 기록하므로 이 분기의 계수는 상한이 아니라
    **실측 단가**다. 그래도 단정은 등식이 아니라 `>=`로 남긴다(round22 규율 ①): 등식으로
    못박으면 `_read_type`이 모드당 왕복을 하나 더 쓰게 되는 정당한 수정이 실패로
    나타난다. 단가를 1로 낮추면(= GO 분기를 negative로 아는 척하면) 이 자리에서
    **과소보고**가 되어 고지의 `False`가 방어되지 않는다 — 그 방향을 이 시험이 잡는다.
    """
    swept, spent = _r23_cost_sweep_and_spend(
        _r23_cost_port(declared=30, matching=29, modes=5), read_channel_counts=True
    )
    # 대조군 전제 — GO 분기가 negative보다 실제로 비싸다(같으면 상한을 재지 못한다).
    assert spent > swept.recovery_probe_count + swept.recovered_count * 6

    assert swept.recovery_roundtrip_ceiling >= spent


#: `U`(= 799)와 `m`(= 5)을 고정하고 `k`만 키우는 지점들. 마지막 둘은 기각선을 넘는다.
#: [round24 R24-5] `m`이 2에서 5로 올랐다. **수치를 맞추려 고친 것이 아니라 단위가
#: 바뀌어서다**: 이 계열은 negative 분기라 단가가 `c=1`이고, `m=2`이면 회수 한 건이
#: 3왕복이라 `U=799`를 다 채워도 3,196으로 기각선에 닿지 못한다. 그때 이 계열은
#: **전 구간 `False`**가 되어 아래 두 시험이 공허해진다(단조성은 자명하게 참, 비공허성
#: 단정은 실패). `m=5`면 회수 한 건이 6왕복이라 `k` 항 단독으로 선을 넘는다 —
#: round23판이 `m=2`로도 넘긴 것은 negative 스윕을 GO 단가로 쟀기 때문이고, 그것이
#: R24-5가 고발한 바로 그 과다 판정이다.
_R23_COST_MONOTONE_MATCHES = (0, 300, 620, 799)


def _r23_cost_notices_as_k_grows() -> list[bool | None]:
    return [
        _r23_cost_sweep(
            _r23_cost_port(declared=800, matching=matching, modes=5)
        ).recovery_cost_basis_exceeded
        for matching in _R23_COST_MONOTONE_MATCHES
    ]


def test_r23_the_cost_notice_is_monotone_in_the_recovered_count():
    """[R23-4] 단조성 — 다른 변수를 고정하고 `k`만 키우면 고지는 **내려가지 않는다**."""
    notices = _r23_cost_notices_as_k_grows()

    assert notices == sorted(notices)


def test_r23_the_recovered_count_alone_can_leave_the_cost_basis():
    """[R23-2] `k` 항 **단독으로** 기각선을 넘는다 — 위 단조성이 공허하지 않은 근거다.

    `U`는 799로 고정이라 이름 프로브만으로는 3,872에 닿지 못한다. 그런데도 고지가
    서는 것은 `k(1 + c·m)`을 세기 때문이다 — 구판은 이 구간 전체에서 `False`였다.
    """
    notices = _r23_cost_notices_as_k_grows()

    assert (notices[0], notices[-1]) == (False, True)


def test_r23_the_cost_notice_fires_exactly_on_the_number_that_was_rejected():
    """[R23-4] 경계 등식 — 상한이 **정확히** 기각선이면 고지가 선다.

    ``3,872``는 "여기까지는 괜찮다"가 아니라 **기각당한 그 수**다. 정확히 그 값을
    치렀으면 기각 문장이 이 스윕에도 그대로 적용된다. `>`로 두면 근거가 무효인 바로
    그 한 점에서만 "범위 안"이라는 긍정 주장이 선다 — 감사 뮤턴트 F2가 살아남은 자리다.
    """
    swept = _r23_cost_sweep(_r23_cost_boundary_port(RECOVERY_COST_EVIDENCE_ROUNDTRIPS))
    # 대조군 전제 — 선 위에 정확히 올라섰다.
    assert swept.recovery_roundtrip_ceiling == RECOVERY_COST_EVIDENCE_ROUNDTRIPS

    assert swept.recovery_cost_basis_exceeded is True


def test_r23_one_roundtrip_short_of_the_line_is_still_inside_the_cost_basis():
    """[R23-4] 경계의 반대편 — 한 왕복 모자라면 `False`다.

    이 단정이 없으면 비교를 상수 `True`로 바꾸는 뮤턴트가 살아남고, 고지는 아무것도
    구별하지 않으면서 항상 선다(= 과다 고지가 규율을 삼킨다).
    """
    swept = _r23_cost_sweep(_r23_cost_boundary_port(RECOVERY_COST_EVIDENCE_ROUNDTRIPS - 1))
    # 대조군 전제 — 선 바로 아래다.
    assert swept.recovery_roundtrip_ceiling == RECOVERY_COST_EVIDENCE_ROUNDTRIPS - 1

    assert swept.recovery_cost_basis_exceeded is False


def test_r23_the_live_m8_sweep_stays_inside_the_cost_basis():
    """[R23-2 과차단 금지] 실물 M8 규모(타입 3종)의 스윕은 고지를 세우지 않는다.

    항을 더한 계수가 실물 규모에서 발화하면 고지는 소음이 되고, 조작자는 그것을 무시하는
    법을 배운다 — 참일 때까지 포함해서.
    """
    port = _R21SweepPort(_R21_THREE_TYPE_LIBRARY)
    swept = recover_requested_types(port, read_fixture_type_library(port), ["Robin LEDBeam 350"])
    # 대조군 전제 — 스윕이 실제로 돌아 회수까지 갔다(안 돌면 `None`이라 공허하다).
    assert swept.recovered_count == 1

    assert swept.recovery_cost_basis_exceeded is False


def test_r23_the_cost_payload_carries_the_number_the_notice_measured():
    """[R23-2] 고지가 **무엇을 재서** 참인지 payload가 말한다.

    이름 프로브 수만 실으면 조작자는 `k` 항이 세워 올린 고지를 그 수로 검산하려다
    실패한다 — 수가 맞지 않으면 고지를 못 믿거나, 더 나쁘게는 계수 쪽을 믿는다.
    """
    payload = _r23_cost_sweep(_r23_cost_port(declared=30, matching=29, modes=5)).to_dict()

    assert payload["recovery_roundtrip_ceiling"] > payload["recovery_probe_count"]


def _r23_cost_port_behind(enumerated: int) -> _R21ShortPort:
    """스윕 형상(`U = 3` · `k = 1` · `m = 4`)은 고정하고 **열거 규모만** 키운 포트."""
    rows = [(f"Mode {number}", 16) for number in range(1, 21)]
    listed = _r21_types([f"LEDWash {number}" for number in range(enumerated)], modes=rows)
    return _R21ShortPort(
        listed,
        declared_types=enumerated + 3,
        hidden={
            enumerated + 1: (f"Filler {enumerated + 1}", []),
            enumerated + 2: (f"Filler {enumerated + 2}", []),
            enumerated + 3: ("MegaPointe", rows[:4]),
        },
    )


def test_r23_the_cost_notice_measures_the_sweep_and_not_the_enumeration():
    """[R23-2 형제 누락] 고지는 **스윕이 쓴 것**을 말한다 — 열거 비용은 남의 항이다.

    회수분만 세는 필터(`entry.recovered`)를 잃으면 열거로 온 타입의 `_read_type`까지
    합에 들어가, 싸게 훑은 스윕이 "근거 범위를 벗어났다"고 말한다. 그것은 반대 방향의
    같은 거짓말이고, 조작자는 스윕 폭을 줄이는 헛수고를 하게 된다. 그래서 열거 규모를
    40배로 키워도 **같은 수**여야 한다.
    """
    small = _r23_cost_sweep(_r23_cost_port_behind(1))
    large = _r23_cost_sweep(_r23_cost_port_behind(40))
    # 대조군 전제 — 열거 규모는 실제로 갈렸고 스윕 형상은 같다.
    assert (len(small.types), len(large.types)) == (2, 41)
    assert (small.recovery_probe_count, large.recovery_probe_count) == (3, 3)

    assert large.recovery_roundtrip_ceiling == small.recovery_roundtrip_ceiling


# ==========================================================================
# --- round24 R24-5 비용 상한의 **단위** (EquivDisclosure) ---
#
# 기각선 `RECOVERY_COST_EVIDENCE_ROUNDTRIPS = 3_872`은 `176 × 22`이고 `22`는
# 프로브 1 + DMXModes 상태 1 + 모드 이름 20이다 — 즉 **`c=1`(negative) 단가로 유도된
# 수**다. 그런데 round23판 계수는 늘 `c=2`(GO 단가)로 쟀다. 같은 실제 왕복 수가
# 분기에 따라 다른 판정을 받았고, negative 쪽만 약 1.9배 엄했다.
#
# 감사 실측 오탐: `U=100` · `k=100` · `m=19` · negative → **실제 2,100 왕복**인데
# 상한 4,000으로 `recovery_cost_basis_exceeded=True`. 기각선 아래인데 "근거 범위를
# 벗어났다"고 말한 것이다.
#
# 고친 것은 **기각선이 아니라 계수의 단가**다. 기각선은 벽시계(66.25 ms/왕복 × 3,872
# ≈ 4분)라 분기가 바꾸지 않으므로 하나로 남기고, 스윕이 자기 단가를 기록한다
# (`FixtureTypeLibrary.recovery_mode_roundtrips`). 기록이 없으면 상한으로 떨어진다 —
# **과소보고 금지 방향은 유지한다**: `False`는 "쟀는데 범위 안이다"라는 긍정 주장이다.
#
# **이 수정 자신의 등가 공시**(round24 ⓑ를 자기에게 적용한다). 이 반영은
# **negative 분기에서만 행동이 갈린다**. GO 분기에서는 기록한 단가가 곧 옛 상한과
# 같은 값이라(`RECOVERY_COST_MODE_ROUNDTRIPS_CEILING == RECOVERY_COST_MODE_ROUNDTRIPS_GO`
# — 아래 폴백 시험이 그 등식을 든다) 판정이 한 건도 바뀌지 않고, 단가를 기록하지 못한
# 라이브러리도 폴백이 옛 상한 그대로라 마찬가지다. 실물 M8은 스윕 자체가 돌지 않아
# (`recovery_boundary is None`) **양 분기 전부 무변화**다. 즉 오늘 갈리는 것은 스윕이
# 도는 negative 경로 하나이고, 그 하나가 감사가 든 오탐이다.
#
# 아래 대조군도 round22 규율 ①을 지킨다 — 비용 단정은 상한·불변식·단조성·경계
# 등식뿐이고, 성질 하나에 시험 하나다.
# ==========================================================================

from server.vwx.typemap import (  # noqa: E402  (섹션 지역 임포트 — 공용 헤더를 건드리지 않는다)
    DMX_CHANNELS_SEGMENT,
    RECOVERY_COST_MODE_ROUNDTRIPS_CEILING,
    RECOVERY_COST_MODE_ROUNDTRIPS_GO,
    RECOVERY_COST_MODE_ROUNDTRIPS_NEGATIVE,
)


def test_r24_the_audited_false_notice_is_gone_and_the_recovery_is_not():
    """[R24-5] 감사가 든 오탐 입력에서 고지가 **`False`**다 — 그리고 회수는 그대로다.

    `U=100` · `k=100` · `m=19` · negative 분기: 실제 왕복은 ``100 + 100×20 = 2,100``
    으로 기각선 3,872 아래인데, GO 단가로 재던 구판은 4,000을 보고 고지를 세웠다.

    회수 계수를 함께 단정하는 이유는 **R22-F의 성격**이다: 고지는 상한이 아니므로
    고지가 내려갔다고 회수가 늘거나 줄면 안 된다. 이 칸이 판정에 개입하기 시작하면
    그 순간 "느리지만 옳은 답"이 수치 때문에 배제로 바뀐다.
    """
    swept, spent = _r23_cost_sweep_and_spend(_r23_cost_port(declared=101, matching=100, modes=19))
    # 대조군 전제 — 감사가 든 그 형상에 실제로 닿았고, 실제 비용도 그 수다.
    assert (swept.recovery_probe_count, swept.recovered_count) == (100, 100)
    assert spent == 2_100
    assert spent < RECOVERY_COST_EVIDENCE_ROUNDTRIPS

    assert swept.recovery_cost_basis_exceeded is False
    # 고지가 무엇을 재든 회수분은 그대로 실려 나간다.
    assert len([entry for entry in swept.types if entry.recovered]) == 100


#: 같은 **실제 왕복 수**를 두 분기가 각각 만들어 내는 형상. negative는 모드당 1왕복,
#: GO는 2왕복이므로 모드 수를 반으로 줄이면 `U + k(1 + c·m)`이 정확히 같아진다.
#: 아래는 기각선을 사이에 두고 하나씩 — 둘 다 같은 답이면 "둘 다 False"라는 공허한
#: 일치가 아니라는 근거가 된다.
_R24_COST_PARITY_SHAPES = ((101, 100), (351, 350))


def _r24_cost_parity(declared: int, matching: int):
    """같은 실제 비용을 negative(m=10)와 GO(m=5)로 각각 낸 뒤 (실측, 고지) 쌍을 돌려준다."""
    negative, negative_spent = _r23_cost_sweep_and_spend(
        _r23_cost_port(declared=declared, matching=matching, modes=10)
    )
    occupancy, occupancy_spent = _r23_cost_sweep_and_spend(
        _r23_cost_port(declared=declared, matching=matching, modes=5),
        read_channel_counts=True,
    )
    return (negative_spent, negative.recovery_cost_basis_exceeded), (
        occupancy_spent,
        occupancy.recovery_cost_basis_exceeded,
    )


@pytest.mark.parametrize(("declared", "matching"), _R24_COST_PARITY_SHAPES)
def test_r24_the_same_real_cost_gets_the_same_verdict_in_either_branch(declared, matching):
    """[R24-5] **단위 일치** — 같은 실제 왕복 수면 분기가 달라도 같은 판정이다.

    이것이 이번 수정의 기준이다. 수치를 맞춘 것이 아니라 단위를 맞춘 것이라, 검사도
    "상한이 얼마인가"가 아니라 **"같은 비용이 같은 답을 받는가"**를 묻는다. 구판은
    negative 쪽만 GO 단가로 재서 이 등식이 깨져 있었다.
    """
    (negative_spent, negative_notice), (occupancy_spent, occupancy_notice) = _r24_cost_parity(
        declared, matching
    )
    # 대조군 전제 — 두 분기가 실제로 같은 왕복 수를 썼다(다르면 비교가 성립하지 않는다).
    assert negative_spent == occupancy_spent

    assert negative_notice == occupancy_notice


def test_r24_the_branch_parity_control_straddles_the_rejection_line():
    """[R24-5] 위 일치가 **공허하지 않다** — 두 형상이 기각선 양쪽에 있다.

    두 형상이 모두 `False`면 "판정이 같다"는 단정은 아무것도 구별하지 않는다. 그래서
    선 아래와 위를 하나씩 잡고, 그 판정이 실제로 갈리는 것을 여기서 값으로 고정한다.
    """
    notices = [_r24_cost_parity(*shape)[0][1] for shape in _R24_COST_PARITY_SHAPES]

    assert notices == [False, True]


def test_r24_a_library_that_never_recorded_its_unit_still_never_understates():
    """[R24-5] **과소보고 금지 유지** — 단가 기록이 없으면 상한으로 떨어진다.

    기록을 지우는 것은 계수를 싸게 만드는 가장 쉬운 길이다. 그 길이 열리면 고지의
    `False`("쟀는데 범위 안이다"라는 긍정 주장)가 가장 비싼 분기에서 거짓이 된다.
    가장 비싼 분기(GO)에서 기록만 지우고 같은 불변식을 다시 잰다.
    """
    swept, spent = _r23_cost_sweep_and_spend(
        _r23_cost_port(declared=30, matching=29, modes=5), read_channel_counts=True
    )
    forgotten = replace(swept, recovery_mode_roundtrips=None)
    # 대조군 전제 — 기록이 실제로 지워졌고, 원래 스윕은 GO 분기였다.
    assert (swept.recovery_mode_roundtrips, forgotten.recovery_mode_roundtrips) == (2, None)

    assert forgotten.recovery_roundtrip_ceiling >= spent


def test_r24_the_recorded_unit_is_the_branch_and_not_an_observation():
    """[R24-5] 기록은 **분기 그 자체**다 — 점유폭 응답이 실패해도 비싼 쪽으로 남는다.

    `LibraryMode.channel_count`로 단가를 되짚는 길이 왜 틀리는지를 값으로 고정한다:
    GO 분기에서 DMXChannels 응답이 전부 실패하면 채널 수 칸은 전부 `None`이 되지만
    **왕복은 이미 나갔다.** 관측으로 되짚으면 그 스윕을 negative로 세어 과소보고한다.
    """

    class _NoChannelPort(_R21ShortPort):
        def query_state(self, path: str) -> dict:
            if path.endswith(f"/{DMX_CHANNELS_SEGMENT}"):
                return {"ok": False, "path": path}
            return super().query_state(path)

    port = _NoChannelPort(
        _r21_types(["LEDWash 600"]),
        declared_types=4,
        hidden={2: ("Filler 2", []), 3: ("Filler 3", []), 4: ("MegaPointe", [("Mode 1", 16)])},
    )
    swept, spent = _r23_cost_sweep_and_spend(port, read_channel_counts=True)
    # 대조군 전제 — 점유폭을 못 읽었는데도 그 왕복은 실제로 나갔다.
    assert [mode.channel_count for mode in swept.types[-1].modes] == [None]

    assert swept.recovery_mode_roundtrips == RECOVERY_COST_MODE_ROUNDTRIPS_GO
    assert swept.recovery_roundtrip_ceiling >= spent


def test_r24_the_cost_payload_says_which_unit_judged_this_sweep():
    """[R24-5] payload가 **어느 단가로 판정됐는지** 말한다.

    상한과 프로브 수만 실으면 조작자는 둘의 차이가 `k`에서 났는지 `c`에서 났는지 모르고,
    기각선이 negative 단가로 유도된 수라는 것도 검산할 수 없다.
    """
    negative = _r23_cost_sweep(_r23_cost_port(declared=6, matching=2, modes=3)).to_dict()
    occupancy = _r23_cost_sweep(
        _r23_cost_port(declared=6, matching=2, modes=3), read_channel_counts=True
    ).to_dict()

    assert negative["recovery_mode_roundtrips"] == RECOVERY_COST_MODE_ROUNDTRIPS_NEGATIVE
    assert occupancy["recovery_mode_roundtrips"] == RECOVERY_COST_MODE_ROUNDTRIPS_GO
    assert occupancy["recovery_roundtrip_ceiling"] > negative["recovery_roundtrip_ceiling"]


def test_r24_a_library_that_was_never_swept_records_no_unit():
    """[R24-5] 안 훑었으면 단가도 `None`이다 — `recovery_boundary`와 같은 규율.

    `1`이나 `2`를 적으면 "이 단가로 쟀다"가 되어, 훑지 않은 것과 싸게 훑은 것이 한 칸에
    뭉개진다. 그리고 그 상태에서도 계수는 0이라 고지는 `None`으로 남아야 한다.
    """
    library = read_fixture_type_library(LibraryRigPort(_r21_types(["LEDWash 600"])))

    assert library.recovery_mode_roundtrips is None
    assert library.recovery_roundtrip_ceiling == 0
    assert library.recovery_cost_basis_exceeded is None


def test_r24_the_unrecorded_fallback_is_the_most_expensive_branch():
    """[R24-5] 폴백 단가가 **가장 비싼 분기**와 같다 — 그 등식이 과소보고 금지의 형태다.

    폴백을 negative로 내리면 기록 없는 라이브러리에서 GO 스윕이 싸게 세어진다. 이
    단정이 없으면 그 변조가 위 불변식 시험 하나에만 걸리고, 왜 걸리는지가 어디에도
    적히지 않는다.
    """
    assert RECOVERY_COST_MODE_ROUNDTRIPS_CEILING == RECOVERY_COST_MODE_ROUNDTRIPS_GO
    assert RECOVERY_COST_MODE_ROUNDTRIPS_NEGATIVE < RECOVERY_COST_MODE_ROUNDTRIPS_GO


# ==========================================================================
# --- round24 R24-4 점유폭 부재 게이트의 **등가 공시** (EquivDisclosure) ---
#
# round23은 이 갈래의 부재 단정 가드를 「복사가 아니라 분해」했다.
#   구판(round22) `_r24_absence_assertable(ct) and _confirmable_from(`
#                 `_library_list_completeness(library))`
#   현행(round23) `_r24_absence_unverifiable(library, ct) is None and _r24_absence_assertable(ct)`
#
# round24 감사가 구판 형태로 되돌리는 뮤턴트(M07)를 심었더니 **2,036건 전부 통과**했고,
# 2,048 상태 진리표로 차이 0을 증명했다. 아래 열거로 **독립 재현**한다(대표원 3,840
# 상태, 차이 0). 즉 오늘 이 갈래에서 그 분해는 **행동상 no-op**이고, 실제로 방어하는
# 것은 같은 반영이 `_absence_assertable`에 넣은 `mode_child_count is not None` 전제다.
#
# **문제는 no-op이 아니다** — 구조를 정리하는 등가 변경은 정당하다. 공시하지 않은 것이
# 문제였다. round23은 바로 그 반영에서 형제 자리(`incompleteness_kind`)에는 *"값은
# 구판과 같다"*를 적었고 이 자리에는 적지 않았다. 같은 라운드에 스스로 올린 규율
# (*"「오늘은 결과가 같다」는 사각지대의 서명이다"*)을 자기 처방에 적용하지 않은 것이다.
#
# **등가 자체를 등식으로 잠그지는 않는다.** 잠그면 나중에 `_absence_unverifiable`을
# 정당하게 좁히는 수정이 실패로 나타난다 — round22 규율 ③(*이 단정이 거짓이 되는
# 수정은 결함인가 개선인가*)의 답이 "개선일 수 있다"이므로 그것은 역방향 대조군이다.
# 그래서 셋으로 나눈다.
#   ① **결함 방향만** 불변식으로 — 현행이 구판보다 **느슨해지지 않는다**. 느슨해지는
#      수정에서만 실패하므로 방향이 안전하다.
#   ② **등가의 원인**을 잠근다 — `_absence_assertable`이 게이트의 모드 축을 이미
#      함의한다는 것. 그 전제(M04)가 빠지면 여기서도 죽는다.
#   ③ **차이집합을 등기**한다(오늘 공집합). 갈라지면 실패하지만 처방은 되돌리기가
#      아니라 **등재**다 — `test_vwx_address.py`의 경계 등기부와 같은 성격이고, 실패
#      메시지가 등재할 상태를 찍어 준다. ①이 결함 방향을 따로 지고 있으므로 ③의 실패는
#      "게이트가 일하기 시작했다"는 개선 신호로만 남는다.
#
# **이 절 자신의 등가 공시.** 이 반영은 `server/vwx/` 코드를 한 줄도 바꾸지 않는다 —
# 런타임 행동상 **완전한 no-op**이고, 바뀌는 것은 "무엇이 왜 등가인지"를 기계가 들고
# 있느냐뿐이다. 그것이 R24-4의 요구 그대로다: 문제는 no-op이 아니라 공시하지 않은
# 것이었다. 주석이 아니라 시험으로 적는 이유는 round24 ⓔ다 — 주석은 코드보다 앞서
# 나가지만, 위 셋은 원인이 죽으면 함께 죽는다.
#
# **감사 뮤턴트 M07의 현재 판정도 여기 적는다.** 구판 형태로 되돌리면 오늘은
# **행동 시험 0건 · 구조 시험 1건**이 실패한다
# (`test_r21_row_cannot_be_assembled_without_a_completeness_statement` — `_resolve_one`이
# `_library_list_completeness`를 직접 부르게 되므로 호출자 등기와 어긋난다). 감사가
# SURVIVED로 관측한 것은 행동 쪽이고, 그 관측은 아래 열거가 다시 확인한다. 즉 M07은
# **등가 뮤턴트이며 구조 게이트가 별개 이유로 잡고 있다** — 두 사실을 한 칸에 뭉개면
# "행동 대조군이 있다"는 거짓이 된다.
# ==========================================================================

from itertools import product  # noqa: E402

# 이 절만 쓰는 **별칭 임포트**다. 같은 이름을 뒤 절들이 다시 임포트하고 있어(완전성
# 게이트 절 · R24-1 사유 절) 이름을 그대로 들이면 재정의가 된다 — 두 절의 임포트를
# 하나로 합치는 것은 이번 반영의 범위가 아니라 별칭으로 비켜 간다.
from server.vwx.typemap import _absence_assertable as _r24_absence_assertable  # noqa: E402
from server.vwx.typemap import _absence_unverifiable as _r24_absence_unverifiable  # noqa: E402
from server.vwx.typemap import _confirmable_from as _r24_confirmable_from  # noqa: E402

#: 모드 행 형상 — **채널 수 판독 여부**가 `_absence_assertable`의 마지막 전제다.
_R24_MODE_SHAPES = (
    (),
    (LibraryMode(index=1, name="Mode 1", channel_count=16),),
    (LibraryMode(index=1, name="Mode 1", channel_count=None),),
    (
        LibraryMode(index=1, name="Mode 1", channel_count=16),
        LibraryMode(index=2, name="Mode 2", channel_count=None),
    ),
)


def _r24_type_states() -> dict[tuple, LibraryType]:
    """`LibraryType`의 **파생 상태**마다 대표원 하나.

    밑에 깐 필드 조합(4,608건)을 게이트가 실제로 보는 파생 서명으로 접는다 — 두 술어가
    읽는 것은 필드가 아니라 그 서명이므로, 대표원 하나면 그 상태를 전부 대표한다.
    """
    states: dict[tuple, LibraryType] = {}
    for (
        available,
        declared,
        returned,
        enumerated,
        unusable,
        unparsable,
        truncated,
        modes,
    ) in product(
        (True, False),
        (None, 0, 1, 2),
        (0, 1, 2),
        (0, 1, 2),
        (0, 1),
        (0, 1),
        (True, False),
        _R24_MODE_SHAPES,
    ):
        entry = LibraryType(
            index=1,
            name="MegaPointe",
            modes=modes,
            modes_available=available,
            modes_truncated=truncated,
            mode_child_count=declared,
            modes_enumerated_count=enumerated,
            returned_mode_row_count=returned,
            unusable_mode_row_count=unusable,
            unparsable_mode_row_count=unparsable,
        )
        signature = (
            entry.modes_available,
            entry.modes_truncated,
            entry.modes_enumeration_short,
            entry.modes_over_enumerated,
            bool(entry.mode_rows_discarded),
            entry.mode_child_count is None,
            all(mode.channel_count is not None for mode in entry.modes),
        )
        states.setdefault(signature, entry)
    return states


def _r24_library_states(entry: LibraryType) -> dict[tuple, FixtureTypeLibrary]:
    """`FixtureTypeLibrary`의 파생 상태마다 대표원 하나 — 위 함수의 루트 축 형제."""
    states: dict[tuple, FixtureTypeLibrary] = {}
    for available, declared, returned, enumerated, unusable, unparsable, truncated in product(
        (True, False), (None, 0, 1, 2), (0, 1, 2), (0, 1, 2), (0, 1), (0, 1), (True, False)
    ):
        library = FixtureTypeLibrary(
            types=(entry,),
            available=available,
            truncated=truncated,
            child_count=declared,
            enumerated_count=enumerated,
            returned_row_count=returned,
            unusable_row_count=unusable,
            unparsable_row_count=unparsable,
        )
        signature = (
            library.available,
            library.truncated,
            library.enumeration_short,
            library.over_enumerated,
            bool(library.rows_discarded),
            library.child_count is None,
            library.index_domain_violated,
        )
        states.setdefault(signature, library)
    return states


def _r24_gate_verdicts():
    """상태마다 `(서명, 현행 판정, 구판 판정)`.

    두 판정은 `_resolve_one`의 점유폭 갈래가 `absence_assertable`에 넣는 값 그 자체다 —
    한쪽은 현행 소스에서, 한쪽은 `git show fbfac93`의 구판 표현식에서 왔다. 구판을 손으로
    다시 적는 것이 이 절의 유일한 위험이라, 표현식을 **부품 단위로** 부른다(구판이 실제로
    부르던 두 함수를 그대로 부른다 — 그 함수들의 의미가 바뀌면 이 재현도 함께 움직인다).
    """
    for type_signature, entry in _r24_type_states().items():
        for library_signature, library in _r24_library_states(entry).items():
            current = _r24_absence_unverifiable(library, entry) is None and (
                _r24_absence_assertable(entry)
            )
            replaced = _r24_absence_assertable(entry) and _r24_confirmable_from(
                _library_list_completeness(library)
            )
            yield (library_signature, type_signature), current, replaced


def test_r24_the_shared_gate_is_never_looser_than_the_form_it_replaced():
    """[R24-4 ①] **결함 방향** — 현행 가드가 구판보다 부재를 더 쉽게 단정하지 않는다.

    이 갈래의 단정은 *"도면 점유폭에 맞는 모드가 이 FixtureType에 없다"*이고 처분은
    하드 스톱이다. 가드가 느슨해지면 미관측 구간을 부재로 바꿔 조작자를 "도면을 고쳐라"로
    보낸다 — R23-1이 고발한 그 형태다. 반대 방향(더 엄해짐)은 여기서 실패하지 않는다:
    그것은 결함이 아니라 게이트가 일하기 시작한 것이고, 아래 등기부가 그것을 알린다.
    """
    looser = [
        signature
        for signature, current, replaced in _r24_gate_verdicts()
        if current and not replaced
    ]

    assert not looser, looser


def test_r24_the_absence_predicate_already_answers_the_gate_mode_side():
    """[R24-4 ②] **등가의 원인** — 술어가 게이트의 모드 축을 이미 함의한다.

    `_absence_assertable`이 참이면 그 타입의 모드 축(`_mode_axis`)은 서지 않고 모드 목록
    완전성 진술도 `complete=True`다. 그래서 게이트에 남는 항이 루트 절반 하나뿐이고,
    구판이 그 절반을 따로 적고 있었으므로 둘이 같은 답을 낸다. 이 함의가 오늘 등가의
    **이유**이고, 그것을 세우는 것이 round23이 같은 반영에 넣은 여섯 번째 전제
    (`mode_child_count is not None`)다 — 그 전제를 빼면 여기서 함의가 깨진다.
    """
    states = _r24_type_states()
    broken = [
        signature
        for signature, entry in states.items()
        if _r24_absence_assertable(entry)
        and not (
            _mode_axis(entry) is None and _r24_confirmable_from(_mode_list_completeness(entry))
        )
    ]

    assert not broken, broken


def test_r24_the_recorded_cause_is_the_premise_that_actually_defends():
    """[R24-4 ②] 위 함의가 **공허하지 않다** — 그 전제 하나가 판정을 실제로 뒤집는다.

    전제를 세우는 조건만 지운 짝을 만든다: 다른 다섯 갈래는 전부 깨끗한데 선언 모드
    총계만 못 읽은 상태다. 술어가 여기서 갈리지 않으면 위 함의는 "참인 전건이 없어서"
    성립하는 항진식이 되고, 등가 공시는 아무것도 말하지 않게 된다.
    """
    verified = LibraryType(
        index=1,
        name="MegaPointe",
        modes=(LibraryMode(index=1, name="Mode 1", channel_count=16),),
        mode_child_count=1,
        modes_enumerated_count=1,
        returned_mode_row_count=1,
    )
    unread = replace(verified, mode_child_count=None)
    library = FixtureTypeLibrary(
        types=(unread,), child_count=1, enumerated_count=1, returned_row_count=1
    )

    assert _r24_absence_assertable(verified) is True
    assert _r24_absence_assertable(unread) is False
    # 두 층이 같은 답을 낸다 — 그 일치가 R23-1의 처방이었고, 그래서 게이트가 남는다.
    assert _r24_absence_unverifiable(library, unread) is not None


#: [R24-4 ③] 현행 가드와 구판 가드가 **실제로 갈리는** 상태의 등기부.
#:
#: **오늘 비어 있고, 비어 있다는 것이 공시다**: 이 갈래에서 `_absence_unverifiable`은
#: `_absence_assertable`과 구판의 루트 완전성 항이 이미 막은 것만 막는다. 감사 뮤턴트
#: M07(구판 형태로 되돌리기)이 SURVIVED인 이유가 이것이고, 그것은 대조군 누락이 아니라
#: **등가 뮤턴트**다.
#:
#: 갈래가 늘어 실제로 갈라지면 아래 게이트가 **등재할 상태를 찍어 주며** 실패한다.
#: 그때의 처방은 분해를 되돌리는 것이 아니라 **여기에 적는 것**이다 — 갈라졌다는 것은
#: 게이트가 독립적으로 일하기 시작했다는 뜻이고, 그것은 개선이다. 결함 방향(현행이
#: 느슨해짐)은 이 표가 아니라 위 ① 불변식이 진다.
_R24_ABSENCE_GATE_DIVERGENCES: tuple[tuple, ...] = ()


def test_r24_the_gate_adds_nothing_this_branch_does_not_already_block():
    """[R24-4 ③] 등가 **기록**과 실측이 일치한다 — 「오늘은 결과가 같다」를 기계가 든다."""
    diverged = tuple(
        signature for signature, current, replaced in _r24_gate_verdicts() if current != replaced
    )

    assert diverged == _R24_ABSENCE_GATE_DIVERGENCES, (
        "게이트와 구판 형태가 갈리는 상태가 생겼다 — 되돌리지 말고 "
        "`_R24_ABSENCE_GATE_DIVERGENCES`에 등재하라(등가 공시의 갱신이다):\n"
        + "\n".join(f"    {signature}," for signature in diverged)
    )


def test_r24_the_equivalence_disclosure_is_not_vacuous():
    """[R24-4 ③] 등기가 **공허하지 않다** — 열거가 실재하고 두 답을 모두 낸다.

    차이집합이 비었다는 공시는 열거가 아무것도 세지 않으면 자동으로 참이 된다. 그래서
    세 가지를 함께 못박는다: 상태 수가 실제로 많고, 현행 가드가 참·거짓을 모두 내며,
    구판이 따로 들고 있던 루트 항이 **실제로 어떤 상태를 막는다**(막지 않으면 두 표현의
    비교가 술어 하나의 비교로 붕괴한다).
    """
    verdicts = list(_r24_gate_verdicts())
    assert len(verdicts) > 3_000
    assert {current for _signature, current, _replaced in verdicts} == {True, False}

    predicate_only = [
        signature
        for signature, _current, replaced in verdicts
        if not replaced and _r24_absence_assertable(_r24_type_states()[signature[1]])
    ]
    assert predicate_only, "구판의 루트 완전성 항이 아무 상태도 막지 않는다 — 비교가 공허하다"


# ==========================================================================
# --- round23 완전성 게이트 (CompletenessGate) ---
#
# **R22-E** — round21은 `row()`가 완전성 진술을 **필수 키워드**로 받게 만들었다.
# 그런데 그 값을 **읽는 처분을 만들지 않았다.** 처방의 절반이었고, 그래서 한 행이
# `resolved`와 `complete:false`를 동시에 말했다: 선언 4모드 중 1행(`Mode 10`)만 도착한
# 콘솔에서 도면이 요구한 `Mode 1`이 **포함관계 퍼지**로 그 하나에 붙어 확정까지 갔고,
# 같은 행의 `mode_options_completeness`는 `declared 4 / observed 1 / unseen 3`이라
# 말하면서 `hard_stops`는 비어 있었다. 점유폭이 달라 주소 배치까지 어긋난다.
#
# 처방은 **부분 목록에서 확정하지 않는 것**이다. `len(candidates) == 1`이 *"이 이름에
# 맞는 것은 이것뿐"*을 뜻하려면 그 목록이 전수여야 한다. 두 축(타입·모드)이 같은 규칙을
# 받는다 — 한쪽만 닫으면 다음 라운드가 나머지를 잡는다.
#
# **처분 축은 넓히지 않는다.** 새 상태도 새 배제 코드도 만들지 않았다: 이 갈래의 처분은
# 형제 넷과 같은 `library_incomplete`이고 축도 같은 `_library_incompleteness` 하나에서
# 나온다. `incompleteness_kind`를 **확인 대기** 갈래에 세우는 것이 round19 major#4가 고친
# 모순의 재발 경로이고, 확정을 막는 것과 배제 코드를 바꾸는 것은 다른 일이다.
#
# **R22-B** — 계수 대조가 한 방향만 봤다. `enumeration_short`는 `child_count >
# returned_row_count`만 보고 `unseen`은 `max(..., 0)`으로 음의 차이를 지운다. 과열거
# (선언 2에 3행)·음의 선언 총계에서 `complete=True`라는 **긍정 주장**이 나갔다. 형제
# `patchplan.ExistingFidRead`는 `over_enumerated`를 명시적으로 들고 있는데, round21이
# 그 클래스에서 여덟 칸을 이름까지 그대로 가져오면서 이것만 안 가져왔다.
#
# **R22-D** — 신설 어휘 `fixture_type_library_rows_discarded`의 배제 라벨이 조치 없이
# 원인 진술로 끝났다. R18-E·R20-A에 이어 「막다른 길 라벨」의 **세 번째** 재발이라,
# 이번에는 라벨 하나가 아니라 **그 유형 전체를 어휘 단위로** 단정하는 게이트를 둔다.
import inspect  # noqa: E402

from server.vwx.typemap import (  # noqa: E402  (섹션 지역 임포트 — 공용 헤더를 건드리지 않는다)
    ALIAS_RESOLVED_REASON,
    _confirmable_from,
    _confirmable_lists,
)

#: `Mode 1`이 `Mode 10`에 **포함관계로** 일치한다 — 전수 목록에서는 후보 2건이 되어
#: 확인 대기가 되고, `Mode 10` 한 행만 도착하면 그 하나로 붕괴한다. 붕괴가 결함이다.
_R23_OVERLAPPING_LIBRARY = [
    ("MegaPointe", [("Mode 10", 32), ("Mode 1", 16), ("Mode 2", 20), ("Mode 3", 24)])
]
#: 이름이 서로를 포함하지 않는 라이브러리 — 전수로 오면 **확정된다**(비공허성 대조군).
_R23_CLEAN_LIBRARY = [("MegaPointe", [("Alpha", 24), ("Beta", 16)])]
#: 두 번째 타입 행을 폐기시켜도 **첫 타입은 후보로 남는** 라이브러리 — 루트 폐기 축이
#: 확정 게이트까지 도달하게 하려면 후보가 0건이 되면 안 된다(0건이면 앞선 갈래가 잡는다).
_R23_TWO_TYPE_LIBRARY = [
    ("MegaPointe", [("Alpha", 24), ("Beta", 16)]),
    ("Spare Unit", [("Alpha", 24)]),
]
_R23_ALIASES = {"MegaPointe": {"type": "MegaPointe", "mode": "Alpha"}}
_R23_OVERLAPPING_ALIASES = {"MegaPointe": {"type": "MegaPointe", "mode": "Mode 1"}}


def _r23_plan(port, *, aliases, mode, footprint=None):
    """기본 분기(`negative`)로 계획을 만든다 — 점유폭 대조가 없는 **실제 기본 경로**다.

    GO 분기에서는 점유폭 불일치가 잘못된 확정을 **우연히** 가려낼 수 있다(폭이 다를
    때만). 그 우연에 기대지 않는 자리에서 재는 것이 이 절의 요점이다.
    """
    return resolve_fixture_types(
        [request("c1", instrument_type="MegaPointe", mode=mode, footprint=footprint)],
        library_port=port,
        type_aliases=aliases,
        assumption_72=ASSUMPTION_72_NEGATIVE,
    )


class _R23RootTotalPort(LibraryRigPort):
    """루트 `node.childCount`만 갈아끼우는 포트 — 행 목록은 손대지 않는다.

    `declared=None`이면 총계 칸 자체를 뺀다(= 완전성을 말할 **근거가 없는** 스냅샷).
    """

    def __init__(self, types, *, declared, **kwargs):
        super().__init__(types, **kwargs)
        self._declared = declared

    def query_state(self, path: str) -> dict:
        state = super().query_state(path)
        if path == FIXTURE_TYPE_LIBRARY_ROOT:
            node = dict(state["node"])
            if self._declared is None:
                node.pop("childCount", None)
            else:
                node["childCount"] = self._declared
            return {**state, "node": node}
        return state


class _R23ModeTotalPort(LibraryRigPort):
    """**모드 축**의 `node.childCount`만 갈아끼우는 포트 — `_R23RootTotalPort`의 형제.

    [round24 R23-1] 루트 축에만 이 포트가 있었다. 그래서 *"선언 총계를 못 읽었다"*는
    형태가 모드 축에서는 한 번도 만들어지지 않았고, 두 축이 갈린 채로 열세 번째 감사를
    지나갔다. `declared=None`이면 총계 칸 자체를 뺀다 — 행 목록은 전부 온다(절단도
    폐기도 아니다: 계수 갈래 셋이 전부 거짓인, **판정 근거만 없는** 스냅샷이다).
    """

    def __init__(self, types, *, declared=None, **kwargs):
        super().__init__(types, **kwargs)
        self._declared = declared

    def query_state(self, path: str) -> dict:
        state = super().query_state(path)
        if re.fullmatch(rf"{FIXTURE_TYPE_LIBRARY_ROOT}/\d+/{DMX_MODES_SEGMENT}", path):
            node = dict(state["node"])
            if self._declared is None:
                node.pop("childCount", None)
            else:
                node["childCount"] = self._declared
            return {**state, "node": node}
        return state


def test_r23_a_partial_mode_list_never_confirms_the_only_row_that_arrived():
    """[R22-E 실증 · 모드 축] 선언 4모드 중 **1행만** 도착한 콘솔에서 확정하지 않는다.

    구판 산출: `status=resolved` · `console_mode='Mode 10'` · `hard_stops=[]`,
    그리고 같은 행이 `complete:false / declared 4 / observed 1 / unseen 3`.
    도면은 `Mode 1`을 요구했는데 32ch 모드로 확정돼 주소 배치까지 어긋난다.

    죽이는 뮤테이션:
      · `_resolve_one`의 `if resolved and not _confirmable_lists(...)` 갈래를 지우면
        ①②③이 실패한다(= 완전성 미조회 확정 복귀).
      · `_confirmable_from`의 `is True`를 `is not False`나 truthiness로 바꾸면
        `complete=None` 행에서 새지만, 이 행은 `False`라 아래 코퍼스가 잡는다.
    """
    port = _R21ShortModePort(_R23_OVERLAPPING_LIBRARY, declared=4, carried=1, flag=False)
    payload = _r23_plan(port, aliases=_R23_OVERLAPPING_ALIASES, mode="Mode 1").to_dict()
    row = row_by_id(payload, "c1")
    marker = row[MODE_OPTIONS_COMPLETENESS_COLUMN]

    # ① 도착한 그 하나로 확정하지 않는다.
    assert row["status"] == TYPE_LIBRARY_INCOMPLETE
    assert row["console_mode"] is None
    # ② 그런데 목록은 여전히 보여 준다 — 확인할 것을 감추지 않는다.
    assert row["mode_candidates"] == ["Mode 10"]
    # ③ 마커와 처분이 **같은 말**을 한다. 구판은 여기가 갈렸다.
    assert marker["complete"] is False
    assert (marker["declared_count"], marker["observed_count"], marker["unseen_count"]) == (4, 1, 3)
    assert row["reason"] != ALIAS_RESOLVED_REASON

    # ④ **붕괴의 실체** — 같은 라이브러리가 전수로 오면 후보가 둘이라 확인 대기다.
    #    부분 목록이 그 모호성을 임의의 하나로 붕괴시킨 것이 결함이었다.
    whole = _r23_plan(
        LibraryRigPort(_R23_OVERLAPPING_LIBRARY), aliases=_R23_OVERLAPPING_ALIASES, mode="Mode 1"
    ).to_dict()
    whole_row = row_by_id(whole, "c1")
    assert sorted(whole_row["mode_candidates"]) == ["Mode 1", "Mode 10"]
    assert whole_row["status"] == TYPE_NEEDS_CONFIRMATION
    assert whole_row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is True


def test_r23_a_partial_type_list_never_confirms_the_only_candidate_that_arrived():
    """[R22-E 실증 · 타입 축] **동형이다** — 두 축을 같은 규칙으로 닫는다.

    선언 30종 중 1종만 열거된 콘솔에서 별칭이 그 1종을 가리킨다. 구판은 유일 후보라
    확정했지만, 요청 이름을 부분 포함하는 다른 제품이 미열거 구간에 있을 수 있다
    (`fuzzy_type_equal`이 포함관계다 — R22-C가 스윕에서 고발한 것과 같은 형태).

    죽이는 뮤테이션: `_confirmable_lists`에서 `_library_list_completeness` 절을 지우면
    (= 모드 축만 닫으면) 이 시험이 실패한다.
    """
    port = _R21ShortPort(_r21_types(["MegaPointe"], (("Alpha", 24),)), declared_types=30)
    payload = _r23_plan(port, aliases=_R23_ALIASES, mode="Alpha").to_dict()
    row = row_by_id(payload, "c1")
    marker = row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]

    assert row["status"] == TYPE_LIBRARY_INCOMPLETE
    assert row["console_type"] is None
    # 제시는 남는다 — 조작자가 무엇을 보고 있었는지 payload가 계속 말한다.
    assert row["presented_console_type"] == "MegaPointe"
    assert marker["complete"] is False
    assert (marker["declared_count"], marker["observed_count"], marker["unseen_count"]) == (
        30,
        1,
        29,
    )
    # 모드 축은 이 스냅샷에서 전수다 — 두 축이 **따로** 판정된다는 대조군이다.
    assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is True


#: (이름, 계획 빌더, **확정에 도달해야 하는가**). 확정 가능 행이 있어야 아래 불변식이
#: "아무것도 확정하지 않는다"로 공허하게 성립하지 않는다.
_R23_CONFIRMATION_CORPUS = (
    (
        "whole_lists_confirm",
        lambda: _r23_plan(LibraryRigPort(_R23_CLEAN_LIBRARY), aliases=_R23_ALIASES, mode="Alpha"),
        True,
    ),
    (
        "root_truncated_by_flag",
        lambda: _r23_plan(
            LibraryRigPort(_R23_CLEAN_LIBRARY, truncated=True),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    (
        "mode_list_short_by_count",
        lambda: _r23_plan(
            _R21ShortModePort(_R23_CLEAN_LIBRARY, declared=2, carried=1, flag=False),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    (
        "mode_list_short_by_flag",
        lambda: _r23_plan(
            _R21ShortModePort(_R23_CLEAN_LIBRARY, declared=2, carried=2, flag=True),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    (
        "mode_rows_discarded",
        lambda: _r23_plan(
            _R21DiscardPort(_R23_CLEAN_LIBRARY, slotless_modes=(2,)),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    (
        "root_list_short_by_count",
        lambda: _r23_plan(
            _R21ShortPort(_r21_types(["MegaPointe"], (("Alpha", 24),)), declared_types=30),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    (
        "root_rows_discarded",
        lambda: _r23_plan(
            _R21DiscardPort(_R23_TWO_TYPE_LIBRARY, slotless_types=(2,)),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    (
        "root_over_enumerated",
        lambda: _r23_plan(
            _R23RootTotalPort(_R23_CLEAN_LIBRARY, declared=0),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    (
        "root_total_unreadable",
        lambda: _r23_plan(
            _R23RootTotalPort(_R23_CLEAN_LIBRARY, declared=None),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    # [round24 R23-1] **형제 축.** 위 행은 루트 총계만 뺀다 — 모드 축 총계를 못 읽은
    # 형태가 코퍼스에 없어서, 확정 게이트는 막고 부재 단정은 통과시키던 갈림이 이
    # 표에 잡히지 않았다. 두 축을 **같은 수로** 먹인다.
    (
        "mode_total_unreadable",
        lambda: _r23_plan(
            _R23ModeTotalPort(_R23_CLEAN_LIBRARY),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
    # [round24 R23-1] 루트 초과 열거(`root_over_enumerated`)의 형제. 모드 축 초과를
    # 밟는 행이 없어 커버리지 표가 `modes_incomplete` union 뒤에 그 갈래를 숨기고 있었다.
    (
        "mode_over_enumerated",
        lambda: _r23_plan(
            _R23ModeTotalPort(_R23_CLEAN_LIBRARY, declared=0),
            aliases=_R23_ALIASES,
            mode="Alpha",
        ),
        False,
    ),
)


@pytest.mark.parametrize(
    "name,build,confirmable",
    _R23_CONFIRMATION_CORPUS,
    ids=[row[0] for row in _R23_CONFIRMATION_CORPUS],
)
def test_r23_resolved_never_coexists_with_an_incomplete_list(name: str, build, confirmable: bool):
    """[R22-E 불변식] `resolved`인 행은 **두 완전성 진술이 모두 `True`**다.

    한 행이 `resolved`와 `complete:false`를 동시에 말하는 조합이 이번 라운드의 고발이다.
    여기서는 그 조합이 **0건**임을 코퍼스 전 행에서 잰다. `confirmable` 칸이 있는 이유는
    공허성 차단이다 — 확정에 도달하는 행이 하나도 없으면 이 불변식은 "아무것도 확정하지
    않는다"로 무해하게 성립한다.

    죽이는 뮤테이션:
      · `_resolve_one`의 완전성 갈래를 지우면 `confirmable=False` 행들이 `resolved`로
        뒤집혀 실패한다.
      · 게이트를 과하게 걸어(예: `_confirmable_from`이 항상 거짓) 확정을 전부 막으면
        `whole_lists_confirm` 행이 실패한다.
    """
    plan = build()
    payload = plan.to_dict()
    row = row_by_id(payload, "c1")

    assert (row["status"] == TYPE_RESOLVED) is confirmable, name
    if row["status"] == TYPE_RESOLVED:
        assert row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"] is True, name
        assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is True, name
        assert row["console_type"] is not None and row["console_mode"] is not None, name
    else:
        # 확정하지 못한 이유가 **행에 실려 있다** — 마커 둘 중 하나가 `True`가 아니다.
        markers = (
            row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"],
            row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"],
        )
        assert not all(marker is True for marker in markers), (name, markers)


def _r23_corpus_coverage(rows) -> tuple:
    """코퍼스가 실제로 밟은 것 — 축 코드 · 삼치 · 관측 플래그 · 확정 건수 · 행 수.

    관측 플래그를 함께 세는 이유는 **행삭제 프로브의 감도**다. 축 코드만 보면 여러 행이
    같은 코드(`fixture_type_library_truncated`)를 내므로 초과 열거 행 하나를 지워도
    커버리지가 그대로다 — 그 행이 유일하게 밟는 축(`over_enumerated`)을 세야 잡힌다.

    [round24 R23-1] **플래그가 두 축에 비대칭이었다.** 루트는 네 갈래를 따로 셌는데
    모드 축은 union(`modes_incomplete`) 하나와 폐기뿐이었고, 선언 총계 미판독은
    **루트만** 셌다. 그래서 ⓐ 모드 축 초과 열거와 ⓑ 모드 축 총계 미판독을 밟는 행이
    코퍼스에 하나도 없었고, 두 축이 갈려도 이 표가 잡지 못했다 — R23-1이 그 갈림이다.
    두 축을 **같은 갈래 수로** 센다.
    """
    from server.vwx.apply import _unresolved_type_verdict

    codes: set[str] = set()
    markers: set[object] = set()
    flags: set[str] = set()
    confirmed = 0
    for _name, build, _confirmable in rows:
        plan = build()
        row = row_by_id(plan.to_dict(), "c1")
        markers.add(row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"])
        markers.add(row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"])
        library = plan.library
        for flag in ("truncated", "enumeration_short", "over_enumerated"):
            if getattr(library, flag):
                flags.add(flag)
        if library.rows_discarded:
            flags.add("rows_discarded")
        if library.child_count is None:
            flags.add("declared_total_unreadable")
        for entry in library.types:
            # [round24 R23-1] 루트와 **같은 갈래를 같은 수로** 센다. union
            # (`modes_incomplete`) 하나로 뭉치면 모드 축 초과 열거를 밟는 행이
            # 없어도 표가 통과한다 — 실제로 없었다.
            for mode_flag in (
                "modes_truncated",
                "modes_enumeration_short",
                "modes_over_enumerated",
            ):
                if getattr(entry, mode_flag):
                    flags.add(mode_flag)
            if entry.mode_rows_discarded:
                flags.add("mode_rows_discarded")
            if entry.mode_child_count is None:
                flags.add("mode_declared_total_unreadable")
        if row["status"] == TYPE_RESOLVED:
            confirmed += 1
        else:
            codes.add(_unresolved_type_verdict(plan.resolutions[0])[0])
    return frozenset(codes), frozenset(markers), frozenset(flags), confirmed, len(rows)


def test_r23_the_confirmation_corpus_walks_every_completeness_axis():
    """코퍼스 건전성 — 세 축·삼치 셋·관측 플래그 전수를 밟는다. 아니면 위 불변식이 얕다."""
    codes, markers, flags, confirmed, _count = _r23_corpus_coverage(_R23_CONFIRMATION_CORPUS)

    assert codes == {
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
    }, codes
    # 삼치가 **셋 다** 나온다 — `None`이 없으면 "근거 없음"을 완전으로 읽는 술어를 못 잡는다.
    assert markers == {True, False, None}, markers
    # 관측 플래그도 전수다 — 두 방향 계수 대조와 두 폐기 축이 모두 실제로 발화하고,
    # [round24 R23-1] **두 축이 같은 갈래 수로** 실린다(루트 5 · 모드 5).
    assert flags == {
        "truncated",
        "enumeration_short",
        "over_enumerated",
        "rows_discarded",
        "declared_total_unreadable",
        "modes_truncated",
        "modes_enumeration_short",
        "modes_over_enumerated",
        "mode_rows_discarded",
        "mode_declared_total_unreadable",
    }, flags
    # 확정에 도달하는 행이 있다 — 없으면 불변식이 공허하게 성립한다.
    assert confirmed == 1


@pytest.mark.parametrize("index", range(len(_R23_CONFIRMATION_CORPUS)))
def test_r23_deleting_any_confirmation_corpus_row_loses_coverage(index: int):
    """표 행삭제 프로브 — 어느 행을 지워도 커버리지 벡터가 달라진다."""
    shrunk = _R23_CONFIRMATION_CORPUS[:index] + _R23_CONFIRMATION_CORPUS[index + 1 :]
    assert _r23_corpus_coverage(shrunk) != _r23_corpus_coverage(_R23_CONFIRMATION_CORPUS)


def test_r23_the_gate_does_not_widen_the_disposition_axis():
    """[round19 major#4 불변식 보존] 확정을 막았지 **배제 코드를 바꾸지 않았다**.

    감사가 독립 검증한 판단이다: `incompleteness_kind`를 **확인 대기** 갈래에 세우면
    `apply._unresolved_type_verdict`가 그 칸을 배제 코드로 옮겨, 한 payload가 같은
    후보에 *"확인하면 된다"*와 *"관측이 불완전하다"*를 함께 말하게 된다.

    ① 새 갈래는 확인 대기가 **아니다** — 처분은 형제 넷과 같은 `library_incomplete`다.
    ② 확인 대기 갈래는 그대로다 — `incompleteness_kind`가 `None`이고 배제 코드는
       `type_confirmation_pending`이다.
    ③ 어휘를 늘리지 않았다 — 새 갈래가 내는 코드는 **기존 세 축 안**이다.

    죽이는 뮤테이션: 새 갈래를 `TYPE_NEEDS_CONFIRMATION`으로 바꾸거나, 마지막 반환에
    `incompleteness_kind=...`를 더하면 ①·②가 실패한다.
    """
    from server.vwx.apply import _unresolved_type_verdict
    from server.vwx.verdicts import TYPE_CONFIRMATION_PENDING

    blocked = _r23_plan(
        _R21ShortModePort(_R23_OVERLAPPING_LIBRARY, declared=4, carried=1, flag=False),
        aliases=_R23_OVERLAPPING_ALIASES,
        mode="Mode 1",
    ).resolutions[0]
    # ① 확인 대기가 아니다 — 고를 것이 화면에 없을 수 있는 상태를 그렇게 부르지 않는다.
    assert blocked.status == TYPE_LIBRARY_INCOMPLETE
    assert blocked.incompleteness_kind in {
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
    }
    assert _unresolved_type_verdict(blocked)[0] == blocked.incompleteness_kind

    # ② 별칭이 없어 **원래부터** 확인 대기인 갈래는 손대지 않았다.
    pending = _r23_plan(LibraryRigPort(_R23_CLEAN_LIBRARY), aliases={}, mode="Alpha").resolutions[0]
    assert pending.status == TYPE_NEEDS_CONFIRMATION
    assert pending.incompleteness_kind is None
    assert _unresolved_type_verdict(pending)[0] == TYPE_CONFIRMATION_PENDING

    # ③ 목록이 부분인데 별칭이 없는 갈래도 확인 대기 그대로다 — round21 R20-B의 판단을
    #    이번 처방이 뒤집지 않았음을 같은 자리에서 재확인한다.
    partial_pending = _r23_plan(
        _R21ShortModePort(_R23_CLEAN_LIBRARY, declared=2, carried=1, flag=False),
        aliases={},
        mode="Alpha",
    ).resolutions[0]
    assert partial_pending.status == TYPE_NEEDS_CONFIRMATION
    assert partial_pending.incompleteness_kind is None
    assert _unresolved_type_verdict(partial_pending)[0] == TYPE_CONFIRMATION_PENDING


def test_r23_the_gate_reads_the_statement_the_row_carries():
    """구조 게이트 — 확정 게이트와 행 표시가 **같은 함수**를 본다.

    두 자리가 각자 식을 들면 표시와 처분이 갈릴 수 있고, 그 갈림이 이번 라운드의
    고발 형태다(마커는 `complete:false`, 처분은 `resolved`).

    죽이는 뮤테이션: `_confirmable_lists`가 완전성 함수 대신 `library.truncated` 같은
    다른 근거를 보게 바꾸면 실패한다.
    """
    source = inspect.getsource(_confirmable_lists)
    assert "_library_list_completeness(" in source
    assert "_mode_list_completeness(" in source

    # 삼치를 `is True`로 받는다 — `None`("근거 없음")이 완전으로 새지 않게 하는 자리다.
    assert _confirmable_from(_library_list_completeness(FixtureTypeLibrary(child_count=None))) is (
        False
    )
    assert _confirmable_from(_mode_list_completeness(None)) is False
    whole = read_fixture_type_library(LibraryRigPort(_R23_CLEAN_LIBRARY), read_channel_counts=True)
    assert _confirmable_lists(whole, whole.types[0]) is True


# --- R22-B 계수 대조를 양방향으로 -------------------------------------------
#
# 형제 `patchplan.ExistingFidRead`의 주석: *"관측이 총계와 **어느 방향으로든** 어긋나면
# 완전하다고 말할 수 없다."* round21이 그 클래스에서 여덟 칸을 이름까지 그대로
# 가져오면서 `over_enumerated`만 안 가져왔다.


def _r23_library(*, declared, slots):
    """선언 총계와 슬롯 번호를 **직접** 지정한 스냅샷 — 계수 축만 단독으로 흔든다."""
    return FixtureTypeLibrary(
        types=tuple(LibraryType(index=slot, name=f"Type {slot}") for slot in slots),
        available=True,
        child_count=declared,
        enumerated_count=len(slots),
        returned_row_count=len(slots),
    )


#: (이름, 선언 총계, 열거 슬롯, 초과인가, 짧은가)
_R23_COUNT_DIRECTION_TABLE = (
    ("whole", 2, (1, 2), False, False),
    ("short", 3, (1, 2), False, True),
    ("over_enumerated", 2, (1, 2, 3), True, False),
    ("negative_declared_total", -1, (), True, False),
    ("declared_zero_with_a_row", 0, (1,), True, False),
)


@pytest.mark.parametrize(
    "name,declared,slots,over,short",
    _R23_COUNT_DIRECTION_TABLE,
    ids=[row[0] for row in _R23_COUNT_DIRECTION_TABLE],
)
def test_r23_the_count_comparison_looks_both_ways(name, declared, slots, over, short):
    """[R22-B] 과열거·음의 선언 총계에서 **`complete=True`가 나가지 않는다**.

    구판: `enumeration_short`는 한 방향만 보고 `unseen`은 `max(..., 0)`이 음의 차이를
    지워, 선언 2에 3행이 온 스냅샷과 음의 총계가 **긍정 주장**으로 나갔다.

    죽이는 뮤테이션:
      · `over_enumerated`를 지우거나 리터럴 `False`로 바꾸면 초과·음수 행이 실패한다.
      · `enumeration_incomplete`의 `or self.over_enumerated` 절을 지워도 같다.
      · `unseen`의 `or self.over_enumerated` 절을 지우면 ③이 실패한다
        (`max(..., 0)`이 만든 0이 "못 본 것이 없다"로 읽힌다).
      · `over_enumerated`를 `>=`로 느슨하게 하면 `whole` 행이 실패한다.
    """
    library = _r23_library(declared=declared, slots=slots)
    marker = _library_list_completeness(library)

    # ① 두 방향이 **따로** 발화한다 — 하나로 뭉개면 조작자가 조치를 고를 수 없다.
    assert library.over_enumerated is over, name
    assert library.enumeration_short is short, name
    # ② 완전성 주장은 어느 방향이든 어긋나면 `True`가 아니다.
    assert (marker.complete is True) is not (over or short), name
    assert library.enumeration_incomplete is (over or short), name
    # ③ 초과에서는 미관측 수를 **모른다** — 0이라 적으면 긍정 주장이 된다.
    assert (library.unseen is None) is over, name
    # ④ payload도 같은 말을 한다.
    assert library.to_dict()["over_enumerated"] is over, name
    assert library.to_dict()["unseen_count"] == library.unseen, name


def test_r23_the_two_count_directions_are_not_interchangeable():
    """대조군 하중 — 두 축을 **맞바꾸면** 잡힌다(합만 보는 게이트는 못 잡는다).

    형제 `patchplan`이 `over_enumerated`를 union과 **따로** 실어야 했던 이유가 이것이다:
    `unseen`은 `max(..., 0)` 때문에 초과 스냅샷에서도 무해해 보이므로, boolean이 리터럴
    `False`로 새면 자기모순 스냅샷이 조용히 통과한다.
    """
    over = _r23_library(declared=2, slots=(1, 2, 3))
    short = _r23_library(declared=3, slots=(1, 2))

    assert (over.over_enumerated, over.enumeration_short) == (True, False)
    assert (short.over_enumerated, short.enumeration_short) == (False, True)
    # 두 축이 서로를 대신하지 못한다 — 값이 반대다.
    assert over.over_enumerated is not short.over_enumerated
    assert over.enumeration_short is not short.enumeration_short
    # 절단 쪽은 수를 말할 수 있고 초과 쪽은 말할 수 없다.
    assert short.unseen == 1
    assert over.unseen is None


def _r23_mode_type(*, declared: int, observed: int) -> LibraryType:
    """모드 축을 **계수만** 흔든 타입 — 루트 축 `_r23_library`의 형제 빌더."""
    return _r21_library_type(
        mode_child_count=declared,
        modes_enumerated_count=observed,
        returned_mode_row_count=observed,
        modes=tuple(
            LibraryMode(index=index, name=f"Mode {index}", channel_count=16 + index)
            for index in range(1, observed + 1)
        ),
    )


#: 루트 축 프로퍼티 -> 같은 뜻의 모드 축 프로퍼티. **둘이 갈리면 안 된다.**
_R23_AXIS_PARITY = (
    ("enumeration_short", "modes_enumeration_short"),
    ("over_enumerated", "modes_over_enumerated"),
    ("enumeration_incomplete", "modes_incomplete"),
    ("unseen", "modes_unseen"),
)

#: (이름, 선언, 관측) — 네 형태를 두 축에 **같은 수로** 먹인다.
#: [round24 R23-1] `declared_unreadable`이 없었다. 앞 셋은 전부 *"선언 총계를 읽었고
#: 관측이 그것과 어떻게 어긋나는가"*를 재므로, **총계 자체를 못 읽은 형태**는 어느 행도
#: 밟지 않는다 — 그 형태가 정확히 R23-1이 터진 자리다(두 축이 갈릴 수 있는데 코퍼스가
#: 못 본다). `None`은 `0`이 아니다: `0`은 선언을 읽은 것이라 `over` 행이 이미 덮는다.
_R23_PARITY_SHAPES = (
    ("whole", 2, 2),
    ("short", 3, 2),
    ("over", 1, 2),
    ("declared_unreadable", None, 2),
)


@pytest.mark.parametrize("root,mode", _R23_AXIS_PARITY, ids=[pair[1] for pair in _R23_AXIS_PARITY])
def test_r23_the_mode_axis_gets_the_same_count_discipline_as_the_root(root: str, mode: str):
    """[R22-B 형제 표면] 루트 축과 모드 축의 계수 규율이 **같다**.

    R22-B는 루트에서 "한 방향만 본다"를 고발했다. `LibraryType.modes_enumeration_short`도
    같은 한 방향 비교이므로, 루트만 고치면 **형제 절반만 고친 것**이 되고 선언 1모드에
    2행이 온 스냅샷은 여전히 `complete=True`로 나간다 — 이 SPEC이 반복해 만든 형태가
    정확히 그것이다.

    죽이는 뮤테이션:
      · `modes_over_enumerated`를 지우거나 `modes_incomplete` union에서 빼면 실패한다.
      · `modes_unseen`의 초과 갈래를 지우면 `modes_unseen` 행이 실패한다.
      · 두 축 중 한쪽 비교만 `>=`·`<`로 밀어도 어느 형태에선가 값이 갈려 실패한다.
    """
    for name, declared, observed in _R23_PARITY_SHAPES:
        root_axis = getattr(
            _r23_library(declared=declared, slots=tuple(range(1, observed + 1))), root
        )
        mode_axis = getattr(_r23_mode_type(declared=declared, observed=observed), mode)
        assert root_axis == mode_axis, (name, root, mode, root_axis, mode_axis)


def test_r23_an_over_enumerated_mode_list_withdraws_every_positive_claim():
    """모드 축 초과 열거의 **행동 대조군** — 표시·부재 단정·payload가 함께 물러선다.

    구판 산출: `modes_enumeration_short`가 거짓이고 `modes_unseen`이 `max(..., 0)=0`이라
    `complete=True`가 나가고, 그 위에서 `_absence_assertable`이 참이 되어
    `designed_footprint_matches_no_console_mode` 하드 스톱까지 단정됐다.
    """
    from server.vwx.typemap import _absence_assertable

    over = _r23_mode_type(declared=1, observed=2)

    assert over.modes_over_enumerated is True
    assert over.modes_enumeration_short is False
    assert over.modes_incomplete is True
    assert over.modes_unseen is None
    assert _mode_list_completeness(over).complete is False
    assert _absence_assertable(over) is False

    entry = FixtureTypeLibrary(
        types=(over,), available=True, child_count=1, enumerated_count=1, returned_row_count=1
    ).to_dict()["types"][0]
    assert entry["modes_over_enumerated"] is True
    assert entry["mode_unseen_count"] is None


def test_r23_the_over_enumeration_basis_matches_the_sibling_reader():
    """형제 표면 — **같은 분모**로 잰다: 쓸 수 있었던 슬롯 수다.

    `returned_row_count`로 재면 중복·무효 행이 섞인 정상 스냅샷을 자기모순이라 부른다.
    그 행들은 이미 폐기 축이 세고 상보식이 그것을 보장한다 — 형제
    `patchplan._existing_fids_from_console`도 `len(read_slots) > child_count`로 잰다.

    죽이는 뮤테이션: `over_enumerated`의 `self.enumerated_count`를
    `self.returned_row_count`로 바꾸면 ②가 실패한다(폐기가 초과로 샌다).
    """
    from server.vwx.patchplan import _existing_fids_from_console

    # ① 초과 판정은 형제와 같은 방향으로 난다.
    sibling = _existing_fids_from_console(_R21FidPort([{"i": 1}, {"i": 2}], 1))
    ours = read_fixture_type_library(_R23RootTotalPort(_R23_TWO_TYPE_LIBRARY, declared=1))
    assert sibling.over_enumerated is True
    assert ours.over_enumerated is True

    # ② 중복 행이 실린 스냅샷은 **초과가 아니다** — 폐기 축이 이미 센다.
    duplicated = read_fixture_type_library(
        _R21DiscardPort(_R23_TWO_TYPE_LIBRARY, duplicate_type_slot=1, declared_extra_types=0)
    )
    assert duplicated.returned_row_count > duplicated.child_count
    assert duplicated.unusable_row_count == 1
    assert duplicated.over_enumerated is False
    # 상보식은 그대로다 — 넘친 행이 폐기 축에 정확히 들어 있다.
    assert duplicated.returned_row_count == (
        duplicated.enumerated_count
        + duplicated.unusable_row_count
        + duplicated.unparsable_row_count
    )


# --- R22-B 두 표면이 같은 근거를 본다 ----------------------------------------


def test_r23_the_sweep_reads_the_shared_index_domain_predicate():
    """구조 게이트 — 스윕의 도메인 가드가 **인라인 식을 들고 있지 않다**.

    같은 판정을 두 자리가 따로 적으면 한쪽만 고쳐지고, 그 갈림이 다음 라운드의 결함이
    된다. 가드는 `FixtureTypeLibrary.index_domain_violated`를 부르고 payload도 같은
    값을 싣는다.

    죽이는 뮤테이션: 가드를 `all(1 <= entry.index <= child_count ...)` 인라인으로
    되돌리면 ①이 실패한다.
    """
    sweep = inspect.getsource(recover_requested_types)
    # ① 판정은 프로퍼티 하나에서만 난다.
    assert "index_domain_violated" in sweep
    assert "1 <= entry.index" not in sweep

    # ② payload가 같은 값을 싣는다 — 조작자도 스윕이 무엇을 보고 물러섰는지 읽는다.
    outside = FixtureTypeLibrary(
        types=(LibraryType(index=99, name="Type 99"),),
        available=True,
        child_count=30,
        enumerated_count=1,
        returned_row_count=1,
    )
    assert outside.index_domain_violated is True
    assert outside.to_dict()["index_domain_violated"] is True


def test_r23_a_sweep_refusal_never_sits_beside_a_completeness_claim():
    """[R22-B] 스윕이 물러선 스냅샷을 완전성 진술이 **전수라고 부르지 않는다**.

    두 표면이 같은 스냅샷을 다르게 신뢰하면 조작자는 어느 쪽을 믿을지 모른다. 여기서는
    도메인 가드가 **판정을 좌우하는 자리**까지 온 입력에서 그 일치를 잰다: 그 자리에
    오려면 앞선 가드(`enumerated_count >= child_count`)를 통과해야 하고, 그때는 열거가
    선언보다 짧거나 폐기 행이 있다는 뜻이라 완전성이 이미 `True`가 아니다.

    **인덱스 도메인 자체는 완전성 축이 아니다.** 콘솔 슬롯 풀은 희소할 수 있어
    (`prechk.inventory._probe_slot`) 총계 1에 3번 슬롯 하나가 온 스냅샷은 정상이고 그
    목록은 실제로 전수다 — 형제 `patchplan.ExistingFidRead`도 인덱스 도메인을
    `complete`에 넣지 않는다. 아래 ③이 그 구별을 고정한다.

    죽이는 뮤테이션:
      · 스윕의 도메인 가드를 지우면 ①에서 프로브가 나가 실패한다.
      · `index_domain_violated`를 `enumeration_incomplete`에 넣으면 ③이 실패한다
        (희소 슬롯 콘솔이 통째로 불완전이 된다 — round23 실측에서 형제 표면
        16건이 그 형태로 죽었다).
    """
    port = _R21ShortPort(
        _r21_types(["LEDWash 600"]), declared_types=30, hidden={20: ("MegaPointe", [("M", 16)])}
    )
    read_fixture_type_library(port)
    outside = FixtureTypeLibrary(
        types=(LibraryType(index=99, name="LEDWash 600"),),
        available=True,
        child_count=30,
        enumerated_count=1,
        returned_row_count=1,
    )
    port.probe_paths.clear()

    # ① 스윕은 물러선다.
    swept = recover_requested_types(port, outside, ["MegaPointe"])
    assert port.probe_paths == []
    assert swept.recovery_boundary is None
    # ② **같은 스냅샷**을 완전성 진술도 전수라고 부르지 않는다.
    assert _library_list_completeness(outside).complete is not True
    assert outside.enumeration_incomplete is True

    # ③ 비공허성 — 희소 슬롯 자체는 불완전이 아니다. 총계 1에 3번 슬롯 하나가 와도
    #    그 목록은 전수이고, 스윕은 "훑을 것이 없어서" 물러선다(불신이 아니다).
    sparse = FixtureTypeLibrary(
        types=(LibraryType(index=3, name="LEDWash 600"),),
        available=True,
        child_count=1,
        enumerated_count=1,
        returned_row_count=1,
    )
    assert sparse.index_domain_violated is True
    assert sparse.enumeration_incomplete is False
    assert _library_list_completeness(sparse).complete is True


# --- R22-D 신설 어휘에 조치절 ------------------------------------------------
#
# 「막다른 길 라벨」은 이 SPEC에서 **세 번째**다: R18-E(공허 이름 갈래를 확인 대기로
# 적어 고를 것이 없는 화면을 기다리게 함) · R20-A ⓒ("라이브러리를 다시 읽어야 함" =
# 수행 불가능한 지시) · R22-D(폐기 축 라벨이 원인 진술로 끝남). 세 번 같은 유형이
# 나왔으면 라벨 하나를 고치는 것으로는 부족하다 — **어휘 단위로** 단정한다.


def _r23_action_clause_defect(label: str) -> str | None:
    """배제 라벨이 **조작자가 수행할 조치**를 가리키는가 — 아니면 무엇이 없는지 돌려준다.

    두 가지를 본다. 조치가 **수행 가능한가**와, 애초에 조치가 **있는가**(의무형으로
    끝나는가). 순서가 규율이다: 수행 불가능 쪽을 먼저 본다. R20-A ⓒ의 구판
    *"라이브러리를 다시 읽어야 함"*은 의무형으로 **끝나므로**, 뒤에 두면 그 갈래에
    영영 도달하지 못한다(= 도달 불가가 된 분류 — `typemap._library_axis`가 축 순서에
    쓰는 것과 같은 규율).

    의무형은 `…야 함`으로 잡는다. `해야 함`만 보면 `맞춰야 함`·`재확립해야 함` 같은
    정상 조치를 조치 없음으로 신고해, 게이트가 어휘를 지키는 대신 **어휘를 왜곡**한다
    (round21이 제조사 이름 스캐너에서 고친 위양성과 같은 형태).
    """
    if "다시 읽" in label:
        return "수행 불가능한 조치 — 재판독은 같은 앞부분을 준다"
    if not label.rstrip().endswith("야 함"):
        return "조치절 없음 — 무엇을 하면 되는지가 없다"
    return None


def _r23_observation_limit_vocabulary() -> frozenset[str]:
    """**배제 어휘와 고지 어휘에 함께 사는** 코드 전수 — 소스에서 계산한다.

    손으로 열거하지 않는 이유는 이 절의 존재 이유 그 자체다: 새 관측 한계 축이
    등재되면 표를 고치지 않아도 게이트가 그 축을 집는다. 두 어휘에 함께 사는 코드가
    바로 *"이 확인을 못 했다 → 그래서 이 대상을 뺐다"*를 말하는 자리이고
    (`verdicts.TARGET_EXCLUSION_REASON`의 round19 major#4 주석), 조작자가 조치를
    알아야 하는 자리도 정확히 거기다.
    """
    from server.vwx.verdicts import SKIPPED_CHECK_KIND, TARGET_EXCLUSION_REASON

    return frozenset(TARGET_EXCLUSION_REASON & SKIPPED_CHECK_KIND)


def test_r23_every_observation_limit_label_names_a_performable_action():
    """[R22-D] 관측 한계 어휘 **전수**의 배제 라벨이 조치를 가리킨다.

    구판 산출: `fixture_type_library_rows_discarded`의 라벨이
    *"…콘솔 열거 응답이 슬롯 번호를 주지 않았다"*로 끝났다 — 원인만 있고 조치가 없다.
    형제 두 축은 같은 커밋에서 *"…해야 함"*을 받았는데 이 축만 못 받았다.

    죽이는 뮤테이션:
      · 어느 라벨에서든 조치절을 떼면 실패한다.
      · 조치를 "라이브러리를 다시 읽어야 함"으로 되돌리면 실패한다(R20-A ⓒ 복귀).
      · 새 관측 한계 축을 두 어휘에 등재하면서 라벨에 조치를 안 적어도 실패한다.
    """
    from server.vwx.verdicts import target_exclusion_label

    vocabulary = _r23_observation_limit_vocabulary()
    assert vocabulary >= {
        FIXTURE_TYPE_LIBRARY_TRUNCATED,
        FIXTURE_TYPE_LIBRARY_UNREADABLE,
        FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
    }, vocabulary

    defects = {
        code: _r23_action_clause_defect(target_exclusion_label(code))
        for code in sorted(vocabulary)
        if _r23_action_clause_defect(target_exclusion_label(code)) is not None
    }
    assert defects == {}, defects


def test_r23_the_action_clause_gate_is_not_vacuous():
    """게이트 건전성 — **구판 문구를 넣으면 실제로 잡는다**.

    이 단정이 없으면 위 게이트는 "무엇이든 통과"일 수 있고, 그것이 이 SPEC이 반복해서
    만든 "표는 맞는데 그 표를 읽는 대조군이 없다"는 공백이다.
    """
    from server.vwx.verdicts import target_exclusion_label

    # ① R22-D 구판 — 원인 진술로 끝난다.
    assert (
        _r23_action_clause_defect(
            "FixtureType·DMXMode 열거 행 일부에 슬롯 번호가 없어 쓰지 못함 — "
            "라이브러리 목록을 전수로 세울 수 없어 제외, 콘솔 열거 응답이 슬롯 번호를 주지 않았다"
        )
        == "조치절 없음 — 무엇을 하면 되는지가 없다"
    )
    # ② R20-A ⓒ 구판 — 조치는 있는데 수행할 수 없다.
    assert (
        _r23_action_clause_defect("FixtureType 열거가 절단됨 — 라이브러리를 다시 읽어야 함")
        == "수행 불가능한 조치 — 재판독은 같은 앞부분을 준다"
    )
    # ③ 현행 문구는 통과한다 — 게이트가 정상 라벨을 신고하지 않는다(위양성 차단).
    for code in sorted(_r23_observation_limit_vocabulary()):
        assert _r23_action_clause_defect(target_exclusion_label(code)) is None, code


def test_r23_the_discard_axis_names_the_same_two_actions_as_its_siblings():
    """[R22-D] 폐기 축의 조치는 형제 두 축과 **같은 둘**이다 — 그것이 그대로 유효하다.

    도면 표기 정합 · GDTF 임포트로 슬롯 재확립. 다만 근거는 다르다: 절단·판독 실패는
    재시도 계열이 남아 있지만 폐기는 같은 범위를 다시 읽어도 같은 행이 온다.

    죽이는 뮤테이션: 라벨에서 조치 둘 중 하나를 빼면 실패한다. 형제 축 문구를 그대로
    베껴 와도 아래 구별 단정에서 실패한다.
    """
    from server.vwx.typemap import LIBRARY_ROWS_DISCARDED_REASON
    from server.vwx.verdicts import target_exclusion_label

    discard = target_exclusion_label(FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED)
    for action in ("타입명", "임포트"):
        assert action in discard, action
    # 자기 축의 판별자는 남는다 — 형제 문구를 베껴 오지 않았다.
    assert "슬롯 번호" in discard
    assert discard != target_exclusion_label(FIXTURE_TYPE_LIBRARY_TRUNCATED)
    assert discard != target_exclusion_label(FIXTURE_TYPE_LIBRARY_UNREADABLE)
    # 사유 문장도 같은 조치를 말한다 — 라벨과 문장이 다른 말을 하면 조작자가 갈린다.
    for action in ("타입명", "임포트"):
        assert action in LIBRARY_ROWS_DISCARDED_REASON, action
    assert "다시 읽" not in LIBRARY_ROWS_DISCARDED_REASON


def test_r23_the_discard_reason_keeps_its_sentence_shape():
    """조치절을 더하면서 **문장 형태 불변식**을 깨지 않았다 — 프로덕션 판정자로 잰다.

    한 문장에 ' — '가 둘이면 읽히지 않는다(round17 S17-04). 조치를 덧붙이는 순간
    그 규칙을 넘기 쉬운 자리라 여기서 직접 잰다.
    """
    from server.vwx.patchplan import sentence_shape_violation
    from server.vwx.typemap import LIBRARY_ROWS_DISCARDED_REASON

    assert sentence_shape_violation(LIBRARY_ROWS_DISCARDED_REASON) is None


def test_r23_the_footprint_absence_claim_needs_a_certain_type_identity():
    """[R22-E 형제 표면] 확정 등급의 **부재 단정**도 부분 목록 위에 서지 못한다.

    `_confirmable_lists` 게이트는 `resolved`만 막는다. 그런데 점유폭 갈래는 그 앞에
    있고, 거기서 나가는 `designed_footprint_matches_no_console_mode`는 *"맞는 모드가
    하나도 없다"*는 **확정 등급 주장**이다. 그 주장은 "이 타입이 맞는 타입"을 전제하는데,
    루트 열거가 부분이면 요청 이름을 부분 포함하는 다른 제품이 미관측 구간에 있을 수
    있다 — 그때 "도면 점유폭을 고쳐라"는 거짓 안내다.

    구판 산출(round23 실측): `status=designed_footprint_unmatchable` ·
    `console_type='MegaPointe'` · `hard_stops=['designed_footprint_matches_no_console_mode']`,
    같은 행의 `type_candidates_completeness`는 `complete:false / declared 30 / unseen 29`.

    죽이는 뮤테이션: `absence_assertable`에서 `_absence_unverifiable(...) is None` 절을
    지우면 ①②③이 실패한다.
    """
    port = _R21ShortPort(_r21_types(["MegaPointe"], (("Alpha", 24),)), declared_types=30)
    payload = resolve_fixture_types(
        [request("c1", instrument_type="MegaPointe", mode="Alpha", footprint=99)],
        library_port=port,
        type_aliases=_R23_ALIASES,
        assumption_72=ASSUMPTION_72_GO,
    ).to_dict()
    row = row_by_id(payload, "c1")

    # ① 부재를 단정하지 않는다.
    assert DESIGNED_FOOTPRINT_MATCHES_NO_MODE not in hard_stop_codes(payload)
    assert row["status"] == TYPE_LIBRARY_INCOMPLETE
    # ② 확정 칸도 비운다 — 관측이 불완전한 상태에서 콘솔 타입을 확정으로 내보내지 않는다.
    assert row["console_type"] is None
    # ③ 마커가 그 이유를 말한다.
    assert row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"] is False
    assert row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["unseen_count"] == 29
    # ④ 그래도 고를 것은 보여 준다 — 채널 수까지 실린 모드 목록이 남는다(round19 기준).
    assert [option["channel_count"] for option in row["mode_options"]] == [24]


def test_r23_the_footprint_absence_claim_still_fires_on_a_whole_library():
    """비공허성 — 전수 스냅샷에서는 **여전히 하드 스톱이 나간다**.

    위 게이트가 "무엇이든 막는다"가 되면 round19 major#5가 만든 갈래가 도달 불가가 된다.
    """
    payload = resolve_fixture_types(
        [request("c1", instrument_type="MegaPointe", mode="Alpha", footprint=99)],
        library_port=LibraryRigPort(_R23_CLEAN_LIBRARY),
        type_aliases=_R23_ALIASES,
        assumption_72=ASSUMPTION_72_GO,
    ).to_dict()
    row = row_by_id(payload, "c1")

    assert DESIGNED_FOOTPRINT_MATCHES_NO_MODE in hard_stop_codes(payload)
    assert row["status"] == TYPE_FOOTPRINT_UNMATCHABLE
    assert row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"] is True


# --- [round24 R23-1] 부재 단정 세 자리를 **한 질문**에 묶는다 -----------------
#
# R22-E는 점유폭 부재 갈래에 완전성 전제를 **타입 축에만** 걸고 모드 축은 옛 술어에
# 남겼다. 그래서 선언 모드 총계를 못 읽은 한 스냅샷이 갈래에 따라 반대로 말했다:
# 점유폭 일치에서는 `library_incomplete`로 확정을 막고, 불일치에서는
# `designed_footprint_matches_no_console_mode` 하드 스톱을 *"모드 열거를 전부 읽었고
# 절단도 없었다"*는 사유와 함께 냈다 — **확정을 막는 것보다 강한 주장이 더 느슨한
# 술어로** 나간 것이다.
#
# 전수 확인에서 **형제 둘**이 더 나왔다(감사가 짚지 않은 자리다): 타입 후보 0건의
# `fixture_type_not_in_library`와 모드 후보 0건의 `dmx_mode_not_in_library`도
# `_library_incompleteness`만 물어, 축이 서지 않은 미판독 스냅샷에서 그대로 부재를
# 단정했다. 셋을 `_absence_unverifiable` 한 자리로 묶는다.


#: 이 절의 라이브러리 — 이름이 서로를 포함하지 않아 전수로 오면 확정된다.
#: 포트는 형제 절의 `_R23ModeTotalPort`를 그대로 쓴다(같은 형태를 두 번 만들지 않는다).
_R24_LIB = _R23_CLEAN_LIBRARY


def _r24_footprint_plan(port, *, footprint):
    """점유폭 대조가 **수행되는** 분기(`go`)로 계획을 만든다 — 갈래 비교의 전제다."""
    return resolve_fixture_types(
        [request("c1", instrument_type="MegaPointe", mode="Alpha", footprint=footprint)],
        library_port=port,
        type_aliases=_R23_ALIASES,
        assumption_72=ASSUMPTION_72_GO,
    ).to_dict()


def test_r24_one_snapshot_does_not_say_opposite_things_on_two_branches():
    """[R23-1 직접 대조군] **같은 스냅샷이 갈래에 따라 반대로 말하지 않는다.**

    선언 모드 총계를 못 읽은 한 콘솔에 점유폭 일치(24)와 불일치(99)를 각각 넣는다.
    구판 실측: 일치는 `library_incomplete`(확정 차단 · 고지 1건), 불일치는
    `designed_footprint_unmatchable` + 하드 스톱 1건 · **고지 0건**. 같은 행의
    `mode_options_completeness`는 두 갈래 모두 `complete=None`이었다.

    죽이는 뮤테이션:
      · `_absence_assertable`에서 `mode_child_count is not None`을 지우면 불일치
        갈래가 다시 하드 스톱을 내 ②·③이 실패한다.
      · `_resolve_one` 점유폭 갈래의 `_absence_unverifiable(...) is None` 절을 지워도 같다.
    """
    port_match = _R23ModeTotalPort(_R24_LIB)
    port_mismatch = _R23ModeTotalPort(_R24_LIB)
    match = _r24_footprint_plan(port_match, footprint=24)
    mismatch = _r24_footprint_plan(port_mismatch, footprint=99)
    match_row = row_by_id(match, "c1")
    mismatch_row = row_by_id(mismatch, "c1")

    # ① 대조군 전제 — 두 갈래가 실제로 갈라진다(점유폭 대조가 수행됐고 결과가 다르다).
    assert match_row["footprint_check"]["match"] is True
    assert mismatch_row["footprint_check"]["match"] is False
    assert match["footprint_mismatches"] == []
    assert len(mismatch["footprint_mismatches"]) == 1
    # ② 그런데 **처분의 강도는 같다** — 둘 다 확정도 부재 단정도 하지 않는다.
    assert match_row["status"] == mismatch_row["status"] == TYPE_LIBRARY_INCOMPLETE
    assert hard_stop_codes(match) == hard_stop_codes(mismatch) == []
    # ③ 고지도 같은 수로 나간다 — 구판은 불일치 쪽만 0건이었다.
    assert len(match["skipped_checks"]) == len(mismatch["skipped_checks"])
    assert [check["kind"] for check in mismatch["skipped_checks"]] == [
        FIXTURE_TYPE_LIBRARY_UNREADABLE
    ]
    # ④ 두 행의 완전성 마커가 같은 말을 한다 — 갈림의 근거가 애초에 하나였다.
    for row in (match_row, mismatch_row):
        assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is None
        assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["declared_count"] is None


def test_r24_the_footprint_reasons_do_not_claim_what_was_not_observed():
    """[R23-1 ②] **사유문이 거짓이 아니다.**

    구판 하드 스톱 사유는 *"모드 열거를 전부 읽었고 절단도 없었다"*였는데, 그 문장이
    나간 스냅샷의 `declared_count`는 `null`이었다. 두 방향으로 잰다: 미판독 갈래의
    사유에 전수 주장이 **없을 것**, 그리고 그 갈래의 원인이 사유에 **적혀 있을 것**.

    죽이는 뮤테이션:
      · `FOOTPRINT_MISMATCH_UNVERIFIED_REASON`에서 선언 총계 절을 지우면 ②가 실패한다.
      · 미판독 갈래를 다시 하드 스톱으로 되돌리면 ①이 실패한다(사유가 전수를 주장한다).
      · `FOOTPRINT_UNMATCHABLE_REASON`에서 근거절을 지우면 ③이 실패한다.
    """
    from server.vwx.patchplan import sentence_shape_violation
    from server.vwx.typemap import (
        FOOTPRINT_MISMATCH_UNVERIFIED_REASON,
        FOOTPRINT_UNMATCHABLE_REASON,
        LIBRARY_UNREADABLE_REASON,
    )

    row = row_by_id(_r24_footprint_plan(_R23ModeTotalPort(_R24_LIB), footprint=99), "c1")

    # ① 전수를 주장하지 않는다.
    assert "전부 읽었" not in row["reason"]
    assert "전수임을 확인했" not in row["reason"]
    # ② 실제 원인이 문장에 있다 — 조작자가 무엇을 못 읽었는지 안다.
    assert "선언된 모드 총계를 읽지 못해" in row["reason"]
    assert row["reason"] == FOOTPRINT_MISMATCH_UNVERIFIED_REASON
    # ③ 반대편(전수 스냅샷)의 사유는 **근거를 말한다** — 근거 없는 전수 주장이 아니다.
    assert "선언된 모드 총계와 대조해" in FOOTPRINT_UNMATCHABLE_REASON
    # ④ 미판독 폴백 사유도 관측 사실을 거짓으로 말하지 않는다 — 응답은 받았다.
    assert "선언된 총계를 읽지 못해" in LIBRARY_UNREADABLE_REASON
    # ⑤ 문장 형태 불변식은 그대로다(' — ' 하나).
    for text in (
        FOOTPRINT_UNMATCHABLE_REASON,
        FOOTPRINT_MISMATCH_UNVERIFIED_REASON,
        LIBRARY_UNREADABLE_REASON,
    ):
        assert sentence_shape_violation(text) is None, text


#: (이름, 포트 빌더, 요청 타입명, 요청 모드명, 부재를 단정해도 되는가).
#: **양방향이다** — 정상 부재가 여전히 부재로 나오는 것까지 함께 잰다. 전자를 빠뜨리면
#: "라이브러리에 없는 장비를 요청했는데 서버가 모르겠다고만 한다"가 되고 그것이 더 나쁘다.
_R24_ABSENCE_SITES = (
    (
        "type_absent_whole_library",
        lambda: LibraryRigPort(_R24_LIB),
        "Wholly Unrelated Fixture",
        "Alpha",
        FIXTURE_TYPE_NOT_IN_LIBRARY,
    ),
    (
        "type_absent_declared_total_unreadable",
        lambda: _R23RootTotalPort(_R24_LIB, declared=None),
        "Wholly Unrelated Fixture",
        "Alpha",
        None,
    ),
    (
        "mode_absent_whole_library",
        lambda: LibraryRigPort(_R24_LIB),
        "MegaPointe",
        "Gamma",
        DMX_MODE_NOT_IN_LIBRARY,
    ),
    (
        "mode_absent_declared_total_unreadable",
        lambda: _R23ModeTotalPort(_R24_LIB),
        "MegaPointe",
        "Gamma",
        None,
    ),
)


@pytest.mark.parametrize(
    "name,build_port,type_name,mode_name,expected_stop",
    _R24_ABSENCE_SITES,
    ids=[row[0] for row in _R24_ABSENCE_SITES],
)
def test_r24_every_absence_claim_asks_the_completeness_question(
    name, build_port, type_name, mode_name, expected_stop
):
    """[R23-1 형제 표면 · 양방향] 부재 단정 **세 자리 중 둘**의 전수 대조군.

    (셋째인 점유폭 갈래는 위 두 시험이 잰다.)

    **정상 경로가 살아 있는 것이 절반이다.** 선언 총계를 읽었고 목록이 온전하면
    `..._not_in_library`가 그대로 나가야 한다 — 그것이 라이브러리에 없는 장비를 요청한
    사용자가 받아야 할 응답이다. 미판독일 때만 `library_incomplete`로 내려간다.

    죽이는 뮤테이션:
      · `_resolve_one`의 두 가드를 `_library_incompleteness`로 되돌리면 미판독 행 둘이
        실패한다(부재를 다시 단정한다).
      · `_absence_unverifiable`이 항상 축을 돌려주게 하면 전수 행 둘이 실패한다(과차단).
      · `_absence_unverifiable`에서 `console_type is not None` 가드를 지우면
        `type_absent_whole_library`가 실패한다(제시된 타입이 없는 갈래를 막는다).
    """
    payload = resolve_fixture_types(
        [request("c1", instrument_type=type_name, gdtf_fixture=type_name, mode=mode_name)],
        library_port=build_port(),
    ).to_dict()
    row = row_by_id(payload, "c1")

    if expected_stop is not None:
        assert hard_stop_codes(payload) == [expected_stop], name
        assert row["status"] == TYPE_LIBRARY_ABSENT, name
    else:
        assert hard_stop_codes(payload) == [], name
        assert row["status"] == TYPE_LIBRARY_INCOMPLETE, name
        # 유보의 근거가 행에 실려 있다 — 두 마커 중 하나가 `True`가 아니다.
        markers = (
            row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"],
            row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"],
        )
        assert not all(marker is True for marker in markers), (name, markers)


def test_r24_the_absence_sites_table_walks_both_directions():
    """표 건전성 — 부재를 **내는** 행과 **막는** 행이 둘 다 있고 두 축을 다 밟는다.

    한 방향만 남으면 위 시험은 "전부 막는다" 또는 "전부 낸다"로 공허하게 성립한다.
    """
    stops = [row[4] for row in _R24_ABSENCE_SITES]
    assert set(stops) == {FIXTURE_TYPE_NOT_IN_LIBRARY, DMX_MODE_NOT_IN_LIBRARY, None}
    assert stops.count(None) == 2  # 두 축 각각 하나씩 막힌다


#: 층 동치 대조군의 코퍼스 — `_absence_assertable`의 전제를 **하나씩** 흔든다.
#:
#: [round24 R23-1] 두 번째 표를 손으로 들지 않는다. 처음에는 같은 내용을 여기 다시
#: 적었는데, **행 하나를 지우는 뮤테이션이 살아남았다**: 행삭제 프로브는 축소된
#: 코퍼스를 자기 자신과 비교하므로 "지운 뒤에도 남은 행끼리는 서로 다르다"만 잰다
#: (자기참조 게이트). 등기부 `_R21_PREMISE_VIOLATIONS`에서 **파생**시키면 전제가
#: 늘 때 행이 자동으로 따라오고, 행을 지우려면 등기부를 지워야 하는데 그 자리는
#: 술어 AST와의 전단사가 막는다 — 검사가 한 자리에서 난다.
_R24_SHARED_QUESTION_CORPUS = (("whole", {}),) + tuple(sorted(_R21_PREMISE_VIOLATIONS.items()))


@pytest.mark.parametrize(
    "name,overrides",
    _R24_SHARED_QUESTION_CORPUS,
    ids=[row[0] for row in _R24_SHARED_QUESTION_CORPUS],
)
def test_r24_the_absence_predicate_answers_the_shared_question_identically(name, overrides):
    """[R23-1 ①] 두 층이 **공유 하위질문**에 같은 답을 낸다 — 그 위에 갈래 고유분만 얹힌다.

    `_absence_assertable`과 확정 게이트는 **같은 질문을 하지 않는다**: 부재 단정은
    *채널 수* 위의 술어라 모드마다 채널 수를 읽었어야 하고, 확정 게이트는 그것을 묻지
    않는다. 공유되는 것은 **"이 모드 목록이 전수인가"** 하나이고, R23-1은 바로 그 하나가
    갈린 것이었다. 그래서 복사가 아니라 **분해**를 값으로 고정한다:

        `_absence_assertable(t)` ⟺ 공유 하위질문 ∧ 채널 수 전수 판독

    죽이는 뮤테이션:
      · 술어에서 전제 하나를 지우면(어느 것이든) 그 형태의 행이 어긋난다.
      · `_mode_list_completeness`가 `mode_child_count is None`에서 `True`를 내게 되돌리면
        `declared_total_unreadable` 행이 어긋난다.
      · `_confirmable_from`을 `is not False`로 느슨하게 해도 같은 행이 어긋난다.
    """
    from server.vwx.typemap import _absence_assertable

    console_type = _r21_library_type(**overrides)
    shared = _confirmable_from(_mode_list_completeness(console_type))
    channels_read = all(mode.channel_count is not None for mode in console_type.modes)

    assert _absence_assertable(console_type) is (shared and channels_read), name
    # 공유 하위질문이 거짓이면 **부재 단정도 거짓**이다 — 더 강한 주장이 더 느슨할 수 없다.
    if not shared:
        assert _absence_assertable(console_type) is False, name


def test_r24_the_shared_question_corpus_covers_every_registered_premise():
    """코퍼스 건전성 — **등기부의 행동 가능 전제 전수**를 밟고, 한쪽으로 치우치지 않는다.

    [round24 R23-1] 이것이 손으로 든 두 번째 표였다면, 행 하나를 지우는 뮤테이션이
    살아남았다(실측 확인). 자기참조 행삭제 프로브로는 못 막는다 — 축소된 표를 축소된
    자기 자신과 비교하기 때문이다. 그래서 **등기부와 맞대고** 잰다: 술어에 전제가 늘면
    등기 전단사가 등기부를 강제하고, 등기부가 늘면 이 게이트가 코퍼스를 강제한다.

    죽이는 뮤테이션:
      · `_R21_PREMISE_VIOLATIONS`에서 행을 지우면 ①이 실패한다(등기부 전단사와 함께).
      · 술어에 전제를 등기 없이 더해도 등기 전단사가 먼저 실패한다.
      · 코퍼스에서 `whole` 행을 지우면 ②가 실패한다(전부 거짓이 되어 공허해진다).
    """
    from server.vwx.typemap import _absence_assertable

    names = {name for name, _overrides in _R24_SHARED_QUESTION_CORPUS}
    # ① 등기부의 전제 전수를 밟는다 — `modes`는 모집단이라 위반시킬 수 없다(등기부 주석).
    assert names == {"whole"} | (frozenset(_R21_ABSENCE_PREMISES) - {"modes"}), names

    shared_values = set()
    divergent = 0
    for _name, overrides in _R24_SHARED_QUESTION_CORPUS:
        console_type = _r21_library_type(**overrides)
        shared = _confirmable_from(_mode_list_completeness(console_type))
        shared_values.add(shared)
        if shared and not _absence_assertable(console_type):
            divergent += 1

    # ② 공유 하위질문이 참인 행도 거짓인 행도 있다 — 아니면 동치가 한쪽으로 공허하다.
    assert shared_values == {True, False}
    # ③ 공유 질문은 참인데 부재는 못 말하는 행 — 두 층이 **같은 질문이 아님**의 증거다.
    assert divergent == 1


def test_r24_the_declared_unreadable_shape_refuses_both_axes():
    """[R23-1 ③ 양축 대칭] 새 형태(`declared_unreadable`)가 **두 축에서 같이** 물러선다.

    `_R23_PARITY_SHAPES`에 이 형태가 없었다 — 앞 셋은 전부 총계를 읽은 뒤의 어긋남을
    재므로, 총계 자체가 없는 형태에서 두 축이 갈려도 표가 못 본다. 계수 프로퍼티가
    전부 거짓으로 **일치**하는 것만으로는 얕으므로, 그 위에서 완전성 주장과 부재 단정이
    함께 물러서는지까지 잰다.

    죽이는 뮤테이션:
      · `_library_list_completeness`/`_mode_list_completeness`의 `child_count is None`
        갈래를 `True`로 되돌리면 ②가 실패한다.
      · `_absence_assertable`에서 총계 전제를 지우면 ③이 실패한다.
    """
    from server.vwx.typemap import _absence_assertable

    shape = dict((row[0], row) for row in _R23_PARITY_SHAPES)["declared_unreadable"]
    _name, declared, observed = shape
    library = _r23_library(declared=declared, slots=tuple(range(1, observed + 1)))
    console_type = _r23_mode_type(declared=declared, observed=observed)

    # ① 어느 축도 서지 않는다 — 절단도 폐기도 아니다.
    assert library.enumeration_incomplete is False
    assert console_type.modes_incomplete is False
    # ② 그런데 **전수라고 주장하지도 않는다** — 두 축이 같은 삼치를 낸다.
    assert _library_list_completeness(library).complete is None
    assert _mode_list_completeness(console_type).complete is None
    assert _confirmable_from(_library_list_completeness(library)) is False
    assert _confirmable_from(_mode_list_completeness(console_type)) is False
    # ③ 부재 단정도 물러선다 — 확정보다 강한 주장이 더 느슨할 수 없다.
    assert _absence_assertable(console_type) is False


#: M8 실물 3종의 첫 모드(2026-08-08 세션 실측 형태). `LibraryRigPort`는
#: `childCount == len(children)` · `truncated=false`로 응답한다 — 그 스냅샷 그대로다.
_R24_M8_CASES = (
    ("Robin MMX Spot", "Mode 1", 24),
    ("FixtureType 2", "Default", 12),
    ("Robin LEDBeam 350", "Mode 1", 16),
)


@pytest.mark.parametrize("assumption", [ASSUMPTION_72_NEGATIVE, ASSUMPTION_72_GO])
@pytest.mark.parametrize(
    "type_name,mode_name,channels", _R24_M8_CASES, ids=[row[0] for row in _R24_M8_CASES]
)
def test_r24_the_live_m8_snapshot_still_resolves(assumption, type_name, mode_name, channels):
    """[HARD 과차단 금지] 실물 M8 스냅샷 **6조합**이 그대로 `resolved` · 하드 스톱 0.

    이번 반영은 부재 단정 세 자리에 전제를 더한다 — 과차단이 나면 M8 세션이 회귀하고
    그것이 이 SPEC에서 가장 나쁜 결과다. 실물이 준 형태(선언 총계를 읽었고 열거가
    그것과 일치하며 절단 플래그도 없다)에서는 새 전제가 **전부 참**이어야 한다.

    죽이는 뮤테이션: `_absence_unverifiable`이 미판독 여부와 무관하게 축을 돌려주게
    하거나 `_confirmable_from`을 항상 거짓으로 만들면 6조합이 전부 실패한다.
    """
    payload = resolve_fixture_types(
        [
            request(
                "c1",
                instrument_type=type_name,
                gdtf_fixture=type_name,
                mode=mode_name,
                footprint=channels,
            )
        ],
        library_port=LibraryRigPort(_R21_THREE_TYPE_LIBRARY),
        type_aliases={type_name: {"type": type_name, "mode": mode_name}},
        assumption_72=assumption,
    ).to_dict()
    row = row_by_id(payload, "c1")

    # ① 실물 스냅샷의 형태 전제 — 이것이 깨지면 아래 판정은 M8을 재는 것이 아니다.
    assert payload["library"]["truncated"] is False
    assert payload["library"]["child_count"] == len(payload["library"]["types"])
    # ② 6조합 전부 확정 · 하드 스톱 0.
    assert row["status"] == TYPE_RESOLVED
    assert hard_stop_codes(payload) == []
    # ③ 두 완전성 마커가 전수를 주장한다 — 새 전제가 실물에서 참이라는 직접 증거다.
    assert row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"] is True
    assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is True


def test_r24_the_sibling_mode_resolver_is_reconfirmed_harmless():
    """[R23-1 ④ 등기 · round25 R24-2 재판정] `apply._resolve_library_mode` — **여전히 무해다.**

    **등기를 갱신하는 이유**: round24 판에서 이 시험은 형제 `_resolve_library_type`을
    *"`enumeration_incomplete` 가드가 있으니 닫혀 있다"*고 인용하며 무해를 판정했다.
    그 인용이 틀렸다 — 그 가드의 계수 갈래는 `child_count is None`에서 전부 거짓이라,
    **선언 총계를 못 읽은 스냅샷에서는 가드가 발화하지 않았다**(R24-2). 무해 판정 자체는
    형제의 상태에 기대지 않으므로 결론은 그대로지만, **근거로 든 문장이 거짓이었으므로**
    그 문장을 고친다. 형제는 이제 완전성 술어
    (`typemap._confirmable_from(_library_list_completeness(...))`)로 닫힌다.

    무해의 근거는 하나다 — **이 함수는 부재를 근거로 쓰지 않는다**:

      · 형제 `_resolve_library_type`의 index 형태 해석은 *"그 이름이 열거에 없다"*는
        **부정 증거** 위에 서므로 완전성 술어가 필요하다.
      · `_resolve_library_mode`의 index 해석은 인덱스와 **이름을 동시에** 요구한다 —
        두 해석 모두 긍정 증거이고, `by_name`이 비었다는 사실을 근거로 쓰지 않는다.
        그래서 모드 열거의 선언 총계(`mode_child_count`)를 못 읽어도 판정이 변하지 않는다.
      · 반환값도 부재 **단정**이 아니다: `None`은 "확정하지 못했다"이고 호출자는 그것을
        하드 스톱으로 바꾸지 않는다.

    **남는 노출은 등기한다**(round24 ⓔ — 주석이 코드보다 앞서 나가지 않게): 두 함수 모두
    `_single_unambiguous`의 `len(...) == 1`을 확정 근거로 쓰는데, *"관측 범위 안에서
    유일하다"*는 절단 아래에서 *"유일하다"*를 뜻하지 않는다. 그 잔여는 round11 N01이
    **의도적으로 받은 대가**다 — 긍정 증거까지 버리면 절단이 기본 경로인 이 콘솔에서
    멱등 판정이 영영 성립하지 않는다. 두 표면이 **같은 대가**를 받으므로 갈리지 않는다.

    죽이는 뮤테이션:
      · `by_index`에서 `mode.name == index_match.group(2)` 절을 지우면 ②가 실패한다 —
        그 순간 이 자리도 부정 증거에 기대게 되어 무해 판정이 무너진다.
      · 형제의 가드를 `enumeration_incomplete`로 되돌리면 ①-ⓑ가 실패한다(round24 판은
        이 칸이 없어서 그 뮤턴트를 놓쳤다).
    """
    import ast as _ast
    import inspect as _inspect

    from server.vwx.apply import _resolve_library_mode, _resolve_library_type

    # ①-ⓐ 형제는 미완전 열거에서 index 단독 해석을 거부한다(부정 증거 가드).
    short = read_fixture_type_library(_R21ShortPort(_r21_types(["LEDWash 600"]), declared_types=30))
    assert _resolve_library_type("FixtureType 2", short) is None

    # ①-ⓑ [round25 R24-2] **round24 판이 못 보던 칸.** 축은 하나도 서지 않는데 선언
    #      총계를 못 읽은 스냅샷 — 구판 가드는 여기서 조용히 통과시켰다.
    unread_total = FixtureTypeLibrary(
        types=(LibraryType(index=2, name="LEDWash 600", modes=()),), available=True
    )
    assert unread_total.enumeration_incomplete is False
    assert _resolve_library_type("FixtureType 2", unread_total) is None

    # ② 이쪽은 그 가드가 필요 없다 — index 해석이 **이름까지** 요구한다.
    source = _ast.parse(_inspect.getsource(_resolve_library_mode))
    index_branch = [node for node in _ast.walk(source) if isinstance(node, _ast.comprehension)]
    assert index_branch, "index 해석 컴프리헨션이 사라졌다"
    conditions = " ".join(_ast.unparse(node) for node in index_branch[-1].ifs)
    assert "mode.index" in conditions and "mode.name" in conditions, conditions

    # ③ 부분 열거 위에서도 **긍정 증거만으로** 확정한다 — 과차단도 아니다.
    partial = _r21_library_type(mode_child_count=4, modes_truncated=True)
    assert _resolve_library_mode("Mode 1", partial) is partial.modes[0]
    # ④ 없는 이름은 `None`이지 하드 스톱이 아니다.
    assert _resolve_library_mode("Mode 99", partial) is None
    # ⑤ [round25 R24-2] 모드 축의 **선언 총계 미판독**에서도 판정이 그대로다 —
    #    형제를 무너뜨린 상태가 이 자리에는 도달하지 않는다는 직접 증거다.
    unread_modes = LibraryType(
        index=1,
        name="LEDWash 600",
        modes=(LibraryMode(index=1, name="Mode 1"), LibraryMode(index=2, name="Mode 2")),
    )
    assert unread_modes.mode_child_count is None
    assert unread_modes.modes_incomplete is False
    assert _resolve_library_mode("Mode 1", unread_modes) is unread_modes.modes[0]
    assert _resolve_library_mode("2 Mode 2", unread_modes) is unread_modes.modes[1]


# ==========================================================================
# [round25 R24-1] 사유문 도달집합 — **기계가 센다**
#
# round23은 점유폭 미검증 문장의 도달집합을 손으로 "셋"이라 셌고, round24는 "넷"이라
# 셌다. 둘 다 틀렸다: round24가 그 표현식에 **새로 끌어들인**
# `_absence_unverifiable(library, ...)`가 루트 축을 도달집합에 넣었는데 문장은 모드
# 목록만 탓했고(루트로 온 행은 `mode_options_completeness{complete:true}`와 *"모드
# 목록을 전수로 보지 못했다"*를 같은 payload에 실었다 — R20-D가 고발한 자기모순),
# 채널 수 미판독은 목록이 아니라 **원소의 한 칸**이 빈 것이라 세 번째 갈래였다.
#
# **형제도 같은 병이었다.** `_incompleteness_reason`이 고르는 세 문장 중 둘
# (`LIBRARY_TRUNCATED_REASON` · `LIBRARY_UNREADABLE_REASON`)이 *"FixtureType 열거"*라고
# 루트 목록을 지목하고 있었는데, 그 축 이름은 `_library_axis`와 `_mode_axis`가 **공유**
# 한다. 모드 열거만 어긋난 스냅샷 11행이 그 문장을 냈고 같은 행의
# `type_candidates_completeness`는 `complete:true`였다(실측). round23이 이 문장의 괄호
# 안 원인만 늘리고 주어를 그대로 둔 자리다 — *"셋을 고쳤다"*가 완전하지 않았다.
#
# 손으로 세는 것을 그만둔다. 이 절의 구조:
#   · **요청 형태 × 루트 축 × 모드 축**의 곱집합을 전수 탐색한다(센서스). 요청 형태를
#     축에 넣은 이유가 형제 전수다 — 점유폭 갈래만 돌면 형제 세 자리를 못 본다.
#   · 문장이 하는 **주장**을 등기하고(문장 단위가 아니라 **절 단위**다), 상태마다
#     "그 절이 문장에 있으면 그 행이 그 주장을 지지하는가"를 단정한다. 조건이 **행의
#     칸**이라 이 등기가 곧 자기모순 금지다.
#   · 코퍼스가 축의 **치역 전수**를 밟는지를 프로덕션 AST와 맞대고 잰다 — 축이 늘면
#     코퍼스가 먼저 운다.
# ==========================================================================

from server.vwx.typemap import (  # noqa: E402  (섹션 지역 임포트 — 공용 헤더를 건드리지 않는다)
    FOOTPRINT_MISMATCH_CHANNEL_COUNTS_UNREAD_REASON,
    FOOTPRINT_MISMATCH_TYPE_UNVERIFIED_REASON,
    LIBRARY_TRUNCATED_REASON,
    LIBRARY_UNREADABLE_REASON,
    _absence_unverifiable,
    _footprint_unverified_reason,
    _library_incompleteness,
    _library_unverifiable,
    _mode_unverifiable,
    _resolve_one,
)

#: **루트 축** 관측 형태 — 축 하나씩만 세운다. 계수는 상보식
#: (`returned == enumerated + unusable + unparsable`)을 지킨다: 깨진 스냅샷을 코퍼스로
#: 쓰면 무엇이 축을 세웠는지가 흐려진다.
_R25_ROOT_SHAPES = {
    "whole": {},
    "unavailable": {"available": False},
    "truncated": {"truncated": True},
    "enumeration_short": {"child_count": 2},
    "over_enumerated": {"child_count": 0},
    "rows_discarded": {"unusable_row_count": 1, "child_count": 2, "returned_row_count": 2},
    "declared_unreadable": {"child_count": None},
}

#: **요청 형태** — 같은 스냅샷을 사유가 나는 **네 자리**로 각각 밀어 넣는다.
#: 점유폭 갈래 하나만 돌면 형제 세 자리(확정 게이트 · 모드 부재 가드 · 타입 부재 가드)가
#: 검사받지 않고, 이번 라운드가 형제에서 결함을 찾은 것이 정확히 그 사각지대다.
_R25_REQUEST_SHAPES = {
    "footprint_mismatch": dict(instrument_type="MegaPointe", mode="Mode 1", footprint=99),
    "footprint_match": dict(instrument_type="MegaPointe", mode="Mode 1", footprint=24),
    "mode_absent": dict(instrument_type="MegaPointe", mode="Gamma", footprint=None),
    "type_absent": dict(instrument_type="Wholly Unrelated Fixture", mode="Mode 1", footprint=None),
}


def _r25_mode_shapes() -> dict[str, dict]:
    """**모드 축** 관측 형태. 손으로 두 번째 표를 들지 않는다 — 등기부
    `_R21_PREMISE_VIOLATIONS`에서 파생시킨다(round24가 같은 자리에서 배운 것: 자기참조
    행삭제 프로브는 축소된 표를 축소된 자기 자신과 비교해 아무것도 막지 못한다).

    등기부가 표현하지 못하는 형태 하나를 더한다. 등기부의 `channel_count` 행은 **유일한
    모드**의 채널 수를 지우는데, 그러면 점유폭 대조 자체가 수행되지 않아(`match`가
    `None`) 점유폭 갈래가 열리지 않는다 — 실측으로 확인했다. 채널 수 미판독이 그 갈래에
    닿으려면 확정된 모드는 채널 수를 갖고 **형제 모드**가 비어 있어야 한다. 그 형태는
    모집단(`modes`) 위의 성질이라 "전제 하나만 위반" 등기부에 담기지 않는다.
    """
    shapes = {"whole": {}}
    shapes.update(_R21_PREMISE_VIOLATIONS)
    shapes["sibling_channel_count"] = {
        "modes": (
            LibraryMode(index=1, name="Mode 1", channel_count=24),
            LibraryMode(index=2, name="Zebra", channel_count=None),
        ),
        "mode_child_count": 2,
        "modes_enumerated_count": 2,
        "returned_mode_row_count": 2,
    }
    return shapes


def _r25_library(root_shape: str, mode_shape: str) -> FixtureTypeLibrary:
    base = dict(
        types=(_r21_library_type(**_r25_mode_shapes()[mode_shape]),),
        available=True,
        truncated=False,
        child_count=1,
        enumerated_count=1,
        returned_row_count=1,
    )
    base.update(_R25_ROOT_SHAPES[root_shape])
    return FixtureTypeLibrary(**base)


def _r25_resolve(
    library: FixtureTypeLibrary, request_shape: str = "footprint_mismatch"
) -> tuple[object, dict]:
    """이 스냅샷 하나짜리 계획의 **판정과 조작자 행** — 행 조립까지 프로덕션 자리를 탄다.

    처분(`incompleteness_kind`)은 행 칸이 아니라 판정에 실려 `apply`에서 배제 코드가
    되므로, 문장만이 아니라 처분까지 무회귀임을 보이려면 판정 객체가 필요하다.
    """
    resolution = _resolve_one(
        request("c1", **_R25_REQUEST_SHAPES[request_shape]),
        library,
        {"MegaPointe": {"type": "MegaPointe", "mode": "Mode 1"}},
        footprint_enabled=True,
    )
    payload = TypeResolutionPlan(
        assumption_72=ASSUMPTION_72_GO, library=library, resolutions=(resolution,)
    ).to_dict()
    return resolution, row_by_id(payload, "c1")


def _r25_row(library: FixtureTypeLibrary, request_shape: str = "footprint_mismatch") -> dict:
    return _r25_resolve(library, request_shape)[1]


#: 점유폭 미검증 갈래가 낼 수 있는 **사유 전수**. 센서스가 이 집합과 전단사임을 아래가
#: 단정한다 — 갈래가 하나 더 열리면(= 등기 없는 문장이 나가면) 그 자리에서 운다.
_R25_FOOTPRINT_REASONS = frozenset(
    {
        FOOTPRINT_MISMATCH_TYPE_UNVERIFIED_REASON,
        FOOTPRINT_MISMATCH_UNVERIFIED_REASON,
        FOOTPRINT_MISMATCH_CHANNEL_COUNTS_UNREAD_REASON,
    }
)

#: 센서스는 결정적이라 한 번만 돈다 — 여러 시험이 같은 표를 본다.
_R25_CENSUS_MEMO: dict[str, tuple] = {}


def _r25_census() -> tuple[tuple[str, str, str, FixtureTypeLibrary, dict], ...]:
    """곱집합 **전수** — (요청 형태, 루트 형태, 모드 형태, 스냅샷, 행)."""
    if "all" not in _R25_CENSUS_MEMO:
        _R25_CENSUS_MEMO["all"] = tuple(
            (req, root, mode, library, _r25_row(library, req))
            for req in _R25_REQUEST_SHAPES
            for root in _R25_ROOT_SHAPES
            for mode in _r25_mode_shapes()
            for library in (_r25_library(root, mode),)
        )
    return _R25_CENSUS_MEMO["all"]


def _r25_reached() -> tuple[tuple[str, str, str, FixtureTypeLibrary, dict], ...]:
    """그중 **점유폭 미검증 갈래에 닿은** 상태만."""
    return tuple(entry for entry in _r25_census() if entry[4]["reason"] in _R25_FOOTPRINT_REASONS)


#: 문장이 하는 **주장** 등기 — (이름, 그 주장을 지고 있는 절, 행이 그 주장을 지지하는가).
#:
#: 문장 단위가 아니라 **절 단위**인 것이 요점이다. 한 문장이 여러 주장을 지고, 같은
#: 주장이 두 문장에 나올 수 있다. 문장 단위로 등기하면 "이 문장은 이 갈래에서 참이다"만
#: 재게 되고, 문장 본문을 고쳐 남의 목록을 탓하게 만드는 뮤테이션이 살아남는다 —
#: 그것이 정확히 R24-1이 고발한 형태다(문장이 자기 도달 경로를 모른 채 남의 목록을 탓함).
#:
#: 조건이 **그 행에 실제로 실려 나간 칸**이라는 것이 두 번째 요점이다. 그래서 이 등기가
#: 곧 자기모순 금지다: 같은 payload가 `complete:true`를 싣고 그 목록을 "전수가 아니다"라
#: 말하면 여기서 죽는다. 프로덕션 완전성 함수를 다시 부르지 않는 이유도 같다 — 조작자가
#: 보는 것은 함수가 아니라 행이다.
_R25_SENTENCE_CLAIMS = (
    (
        "root_list_partial",
        "루트 열거가 전수라고 말할 근거가 없어",
        lambda row: row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"] is not True,
    ),
    (
        "mode_list_partial",
        "이 FixtureType의 모드 목록이 전수라고 말할 근거가 없다",
        lambda row: row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is not True,
    ),
    (
        "mode_list_whole",
        "모드 목록은 선언 총계와 대조해 전수임을 확인했지만",
        lambda row: row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is True,
    ),
    (
        "channel_counts_unread",
        "채널 수를 읽지 못한 모드가 있어",
        lambda row: any(option["channel_count"] is None for option in row["mode_options"]),
    ),
    # 형제 셋(`_incompleteness_reason`)은 축 이름을 두 목록이 공유하므로 목록을 지목하지
    # 않는다 — 주장도 그만큼 약하다: **둘 중 하나가** 전수가 아니다.
    (
        "either_list_partial",
        "FixtureType·DMXMode 열거",
        lambda row: (
            not (
                row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"] is True
                and row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is True
            )
        ),
    ),
)


def _r25_returned_names(function_name: str) -> frozenset[str]:
    """그 함수가 **이름으로** 돌려주는 상수 전수 — 손으로 적은 기대 집합을 쓰지 않는다."""
    return frozenset(
        node.value.id
        for node in ast.walk(_r21_function_node(function_name))
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name)
    )


def test_r25_no_sentence_contradicts_the_row_it_rides_on():
    """[R24-1 처방③ · 대조군②] **곱집합 전수에서 자기모순 0건.**

    round23·round24는 도달집합을 손으로 셌고 두 번 다 틀렸다. 여기서는 요청 형태 ×
    루트 축 × 모드 축을 전부 돌려 사유가 나는 **네 자리**를 함께 밟고, 상태마다 문장이
    지고 있는 절의 주장을 **그 행의 칸**과 맞댄다. 도달집합이 다음에 또 넓어지면 새
    경로가 자동으로 이 검사를 받는다.

    죽이는 뮤테이션:
      · 정정을 되돌려 점유폭 사유를 하나로 합치면 루트 축 경로에서
        `mode_list_partial`이 `complete:true`와 부딪혀 실패한다.
      · 루트 축 경로만 되돌려도 같다.
      · 채널 수 갈래를 모드 목록 문장으로 되돌리면 그 경로에서 실패한다.
      · 형제 둘을 *"FixtureType 열거"* 주어로 되돌리면 `either_list_partial`이 그 절을
        못 찾아 아래 ③이 실패하고, 모드 축 11경로가 검사에서 새는 것이 드러난다.
    """
    census = _r25_census()
    offenders = [
        (req, root, mode, name)
        for req, root, mode, _library, row in census
        for name, clause, holds in _R25_SENTENCE_CLAIMS
        if clause in row["reason"] and not holds(row)
    ]
    # ① 문장은 자기가 탄 행과 어긋나지 않는다.
    assert offenders == [], offenders
    # ② 비공허성 — 곱집합의 일부만 점유폭 갈래에 닿는다.
    assert 0 < len(_r25_reached()) < len(census)
    # ③ 사유마다 등기된 절을 **최소 하나** 진다 — 아니면 ①이 그 문장을 비껴간다.
    for reason in _R25_FOOTPRINT_REASONS | {LIBRARY_TRUNCATED_REASON, LIBRARY_UNREADABLE_REASON}:
        assert any(clause in reason for _name, clause, _holds in _R25_SENTENCE_CLAIMS), reason


def test_r25_the_census_reaches_every_registered_sentence_and_no_other():
    """센서스 ↔ 사유 전단사 — **등기 없는 문장이 점유폭 갈래로 나가지 못한다.**

    한쪽 방향은 과소등기를 막고(새 갈래가 문장을 하나 더 내면 집합이 커진다), 다른
    방향은 공허를 막는다(등기만 해 놓고 아무 상태도 닿지 않는 문장은 검사받지 않는다).

    죽이는 뮤테이션:
      · `_footprint_unverified_reason`에 갈래를 등기 없이 더하면 ①이 실패한다.
      · 갈래 하나를 지우면 그 문장이 닿지 않아 ②가 실패한다.
    """
    observed = {row["reason"] for _req, _root, _mode, _library, row in _r25_reached()}
    assert observed == _R25_FOOTPRINT_REASONS


def test_r25_the_request_corpus_opens_every_reason_site():
    """코퍼스 건전성 — 요청 형태 넷이 **서로 다른 자리**를 실제로 연다.

    형제 전수를 요청 축으로 산 것이 이번 처방의 절반이다. 형제 자리가 한 번도 열리지
    않으면 위 자기모순 게이트는 점유폭 갈래만 재고, 그것이 round23이 *"셋을 고쳤다"*고
    적으면서 형제의 주어를 놓친 사각지대다.
    """
    census = _r25_census()
    sites = {
        req: {row["reason"] for entry in census if entry[0] == req for row in (entry[4],)}
        for req in _R25_REQUEST_SHAPES
    }
    # ① 점유폭 갈래 셋은 불일치 요청에서만 난다.
    assert sites["footprint_mismatch"] >= _R25_FOOTPRINT_REASONS
    for req in ("footprint_match", "mode_absent", "type_absent"):
        assert not (_R25_FOOTPRINT_REASONS & sites[req]), req
    # ② 형제 셋의 자리가 나머지 세 요청에서 실제로 열린다.
    for req in ("footprint_match", "mode_absent", "type_absent"):
        assert {LIBRARY_TRUNCATED_REASON, LIBRARY_UNREADABLE_REASON} & sites[req], req


@pytest.mark.parametrize(
    "name", [row[0] for row in _R25_SENTENCE_CLAIMS], ids=[row[0] for row in _R25_SENTENCE_CLAIMS]
)
def test_r25_every_registered_claim_is_exercised_in_both_directions(name: str):
    """[공허화 차단] 등기된 절마다 **그 절을 진 경로와 조건이 거짓인 경로가 둘 다 있다.**

    한쪽만 있으면 위 센서스는 그 절에 대해 공허하다: 절이 아무 문장에도 없으면 함의의
    전건이 늘 거짓이고, 조건이 늘 참이면 후건이 늘 참이라 어느 쪽도 뮤테이션을 잡지
    못한다. round23이 남긴 규율 — *"오늘은 결과가 같다"는 사각지대의 서명* — 을 절마다
    행동으로 확인하는 자리다.

    죽이는 뮤테이션: 조건을 `lambda _row: True`로 공허화하면 그 행이 실패한다.
    """
    clause, holds = next((row[1], row[2]) for row in _R25_SENTENCE_CLAIMS if row[0] == name)
    census = _r25_census()
    carried = [entry[:3] for entry in census if clause in entry[4]["reason"]]
    refuted = [entry[:3] for entry in census if not holds(entry[4])]
    # ① 그 절을 실제로 지고 나가는 경로가 있다.
    assert carried, name
    # ② 조건이 거짓인 경로도 있다 — 그 경로에서 절이 빠지는 것이 센서스의 내용이다.
    assert refuted, name


def test_r25_the_audit_reproduction_paths_name_the_root_axis():
    """[R24-1 감사 재현] 고발된 **3경로**에서 문장이 루트 축을 말한다.

    감사가 든 재현: 루트 `unusable_row_count=1` + 모드 목록 완전(선언 총계 판독 · 채널
    수 판독) + 별칭 확정 + 점유폭 불일치. 구판은 `library_incomplete` /
    kind=`rows_discarded`를 내면서 사유로 *"모드 목록을 전수로 보지 못했다"*를 실었다 —
    조작자는 무효한 모드 재판독으로 유도되고 실제 조치(루트 재열거 · responder 슬롯
    재확립)를 못 찾는다.

    처분 어휘는 **그대로**다: `status`도 `incompleteness_kind`도 구판과 같은 값이고,
    갈린 것은 사람이 읽는 문장뿐이다. 그 사실을 여기서 값으로 못박는다.

    죽이는 뮤테이션:
      · 사유를 다시 하나로 합치면 ②·③이 실패한다.
      · 처분 어휘를 새로 만들어 갈래를 가르면 ④가 실패한다.
    """
    #: 재현 경로 -> 구판이 내던 **처분 축**. 값으로 못박는다 — "셋 중 하나"라 적으면
    #: 축이 바뀌어도 통과해 무회귀 주장이 공허해진다.
    expected_kinds = {
        "rows_discarded": FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
        "truncated": FIXTURE_TYPE_LIBRARY_TRUNCATED,
        "declared_unreadable": FIXTURE_TYPE_LIBRARY_UNREADABLE,
    }
    for root, kind in expected_kinds.items():
        library = _r25_library(root, "whole")
        resolution, row = _r25_resolve(library)
        # ① 전제 — 모드 목록은 **온전하다**. 이것이 참이 아니면 아래 고발이 성립하지 않는다.
        assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is True, root
        assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["unseen_count"] == 0, root
        # ② 문장은 루트 축을 말한다.
        assert row["reason"] == FOOTPRINT_MISMATCH_TYPE_UNVERIFIED_REASON, root
        # ③ 그리고 모드 목록을 탓하지 않는다 — 구판이 여기서 거짓말을 했다.
        assert "이 FixtureType의 모드 목록이 전수라고 말할 근거가 없다" not in row["reason"], root
        assert "모드를 다시 읽어도 이 상태는 풀리지 않는다" in row["reason"], root
        # ④ 처분 어휘는 구판 그대로다 — 갈린 것은 문장뿐이다.
        assert row["status"] == TYPE_LIBRARY_INCOMPLETE, root
        assert resolution.incompleteness_kind == kind, root


def test_r25_the_mode_axis_paths_are_unchanged():
    """[R24-1 대조군③] **기존 모드 축 경로 무회귀** — 진짜 모드 미판독은 그대로다.

    갈래를 가르면서 원래 참이던 자리까지 옮기면 그것도 회귀다. 모드 축으로 온 경로는
    문장도 처분도 구판과 같아야 한다.
    """
    for mode in (
        "modes_truncated",
        "modes_enumeration_short",
        "modes_over_enumerated",
        "mode_rows_discarded",
        "mode_child_count",
    ):
        row = _r25_row(_r25_library("whole", mode))
        assert row["reason"] == FOOTPRINT_MISMATCH_UNVERIFIED_REASON, mode
        assert row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"] is True, mode
        assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is not True, mode


def test_r25_the_channel_count_path_does_not_blame_the_list():
    """[R24-1 셋째 갈래] **두 목록은 전수인데 원소의 한 칸이 비었다.**

    round24판은 이 상태에서도 *"모드 목록을 전수로 보지 못했다"*를 냈다 — 두 완전성
    마커가 `complete:true`인 채로. 목록은 전수로 봤고, 못 읽은 것은 형제 모드의 채널
    수다. 조치도 목록 재열거가 아니라 그 모드의 DMXChannels 자식 수 재판독이다.
    """
    library = _r25_library("whole", "sibling_channel_count")
    row = _r25_row(library)

    # ① 두 목록 다 전수다 — 목록을 탓할 근거가 없다.
    assert row[TYPE_CANDIDATES_COMPLETENESS_COLUMN]["complete"] is True
    assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["complete"] is True
    assert row[MODE_OPTIONS_COMPLETENESS_COLUMN]["unseen_count"] == 0
    # ② 문장이 그 사실을 말하고, 못 읽은 것을 특정한다.
    assert row["reason"] == FOOTPRINT_MISMATCH_CHANNEL_COUNTS_UNREAD_REASON
    assert "채널 수를 읽지 못한 모드가 있어" in row["reason"]
    assert "이 FixtureType의 모드 목록이 전수라고 말할 근거가 없다" not in row["reason"]
    # ③ 원인이 payload에 실제로 있다 — 문장만의 주장이 아니다.
    assert any(option["channel_count"] is None for option in row["mode_options"])
    # ④ 등기부 행으로는 닿지 않는다는 사실 자체를 못박는다(코퍼스 설계 근거).
    assert _r25_row(_r25_library("whole", "channel_count"))["status"] == TYPE_RESOLVED


def test_r25_the_shared_axis_reasons_do_not_name_one_list():
    """[R24-1 형제 전수] 축 이름을 **두 목록이 공유**하므로 그 사유문은 목록을 지목하지 않는다.

    `_incompleteness_reason`은 축 **이름**만 받는다. 그 이름을 `_library_axis`와
    `_mode_axis`가 같이 쓰므로, 그 함수가 고르는 문장은 원리적으로 어느 목록이 어긋났는지
    모른다 — 그런데 둘이 *"FixtureType 열거"*라고 루트를 지목하고 있었다. 전제(축 이름
    공유)를 먼저 값으로 확인하고, 그 위에서 문장 형태를 강제한다.

    죽이는 뮤테이션:
      · 어느 한 문장의 주어를 *"FixtureType 열거"*로 되돌리면 ②가 실패한다.
      · 문장을 하나 더 늘려 등기 없이 내보내도 ①의 계수에서 어긋난다.
    """
    import server.vwx.typemap as typemap_module

    # ① 전제 — 두 축 함수가 **같은 상수**를 돌려준다. 이것이 거짓이면 위 논증이 무너진다.
    assert _r25_returned_names("_mode_axis") <= _r25_returned_names("_library_axis")
    shared = _r25_returned_names("_incompleteness_reason")
    assert len(shared) == 3, shared
    # ② 셋 다 목록을 지목하지 않는다 — 형제 `LIBRARY_ROWS_DISCARDED_REASON`의 규약이다.
    for name in sorted(shared):
        text = getattr(typemap_module, name)
        assert "FixtureType·DMXMode 열거" in text, name
        assert "FixtureType 열거" not in text, name


def test_r25_the_root_corpus_walks_the_whole_axis_codomain():
    """코퍼스 건전성 — 루트 형태가 `_library_axis`의 **치역 전수**를 밟는다.

    프로덕션 AST에서 축 이름을 뽑아 맞댄다. 손으로 적은 기대 집합이면 축이 늘어도
    코퍼스가 조용히 좁아진다 — round24가 도달집합을 손으로 세다 틀린 것과 같은 형태다.
    """
    expected = {None} | {globals()[name] for name in _r25_returned_names("_library_axis")}
    produced = {_library_unverifiable(_r25_library(root, "whole")) for root in _R25_ROOT_SHAPES}
    assert produced == expected, (produced, expected)
    # 완전성 삼치도 전부 밟는다 — `None`(근거 없음)이 빠지면 R23-1 형태가 다시 샌다.
    tri = {
        _library_list_completeness(_r25_library(root, "whole")).complete
        for root in _R25_ROOT_SHAPES
    }
    assert tri == {True, False, None}


def test_r25_the_mode_corpus_is_derived_from_the_premise_registry():
    """코퍼스 건전성 — 모드 형태가 **등기부에서 파생**되고, 추가분은 하나뿐이다.

    [round24가 남긴 규율] 손으로 든 두 번째 표는 행삭제 뮤테이션에 살아남는다. 등기부에
    전제가 늘면 이 코퍼스가 자동으로 따라오고, 등기부를 줄이려면 술어 AST 전단사가 막는다.
    """
    shapes = _r25_mode_shapes()
    assert frozenset(shapes) == frozenset(_R21_PREMISE_VIOLATIONS) | {
        "whole",
        "sibling_channel_count",
    }
    for premise, overrides in _R21_PREMISE_VIOLATIONS.items():
        assert shapes[premise] == overrides, premise
    # 모드 축 치역도 전수로 밟는다.
    produced = {_mode_unverifiable(_r25_library("whole", mode).types[0]) for mode in shapes}
    assert produced == {None} | {globals()[name] for name in _r25_returned_names("_mode_axis")}


def test_r25_the_axis_decomposition_is_behaviourally_a_no_op():
    """[자기 변경 등가 공시] `_absence_unverifiable`의 **분해는 오늘 행동 no-op이다.**

    round23이 남긴 규율 — *"오늘은 결과가 같다"는 사각지대의 서명* — 을 자기 변경에
    적용한다. 루트 절반을 `_library_unverifiable`로 뽑아낸 것은 사유 문장이 "루트가
    막았나"를 물을 자리를 만들기 위해서이고, **돌려주는 축 값은 한 상태도 바뀌지
    않는다**(= `incompleteness_kind` → 배제 코드가 그대로라는 뜻이다). 등가를 주장만
    하지 않고 곱집합 전수에서 값으로 고정한다.

    등가의 내용은 **계약**이지 구판 표현식의 사본이 아니다:
      ㉠ 관측된 축이 있으면 **그 축**을 돌려준다(`_library_incompleteness` 우선).
      ㉡ 없으면 두 미판독 폴백이 판정하고, 값은 판독 실패 하나다.
      ㉢ `None`인 것과 두 축 함수가 모두 `None`인 것은 같은 조건이다.

    죽이는 뮤테이션: 합성 순서를 "루트 전부 → 모드 전부"로 바꾸면 ㉠이 깨진다
    (루트 총계 미판독 × 모드 폐기에서 폐기가 판독 실패로 바뀐다).
    """
    seen = set()
    for _req, _root, _mode, library, _row in _r25_census():
        console_type = library.types[0]
        axis = _absence_unverifiable(library, console_type)
        observed = _library_incompleteness(library, console_type)
        if observed is not None:
            assert axis == observed  # ㉠
        elif axis is not None:
            assert axis == FIXTURE_TYPE_LIBRARY_UNREADABLE  # ㉡
        assert (axis is None) == (  # ㉢
            _library_unverifiable(library) is None and _mode_unverifiable(console_type) is None
        )
        seen.add((observed is None, axis is None))
    # 비공허성 — 세 갈래(㉠·㉡·`None`)가 전부 밟혔다.
    assert seen == {(False, False), (True, False), (True, True)}


def test_r25_the_reason_resolver_reads_the_same_axes_as_the_guard():
    """구조 게이트 — 문장 선택과 축 선택이 **같은 두 함수**를 같은 순서로 본다.

    두 자리가 각자 식을 들면 같은 행의 `incompleteness_kind`와 사유가 다른 원인을 말할
    수 있고, 그 갈림이 이번 라운드가 고발당한 형태다(표시와 처분의 분리).

    죽이는 뮤테이션: 리졸버가 `_library_axis`만 보게 바꾸면 루트 총계 미판독 경로가
    모드 목록 문장으로 새고 ①·③이 실패한다.
    """
    called = [
        node.func.id
        for node in ast.walk(_r21_function_node("_footprint_unverified_reason"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    # ① 두 축 함수를 그 순서로 부른다.
    assert called == ["_library_unverifiable", "_mode_unverifiable"], called
    # ② 형제 합성도 같은 둘을 부른다 — 자리마다 다른 식을 들지 않는다.
    composed = [
        node.func.id
        for node in ast.walk(_r21_function_node("_absence_unverifiable"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert set(composed) >= {"_library_unverifiable", "_mode_unverifiable"}, composed
    # ③ 구조만 재고 값을 안 재면 게이트가 뜬다 — 리졸버가 그 행의 사유를 실제로 낸다.
    for _req, _root, _mode, library, row in _r25_reached():
        assert _footprint_unverified_reason(library, library.types[0]) == row["reason"]


def test_r25_the_three_sentences_keep_their_shape():
    """문장 형태 불변식 — 신설 둘과 개정된 형제 둘이 프로덕션 판정자를 통과한다."""
    from server.vwx.patchplan import sentence_shape_violation

    for text in sorted(
        _R25_FOOTPRINT_REASONS | {LIBRARY_TRUNCATED_REASON, LIBRARY_UNREADABLE_REASON}
    ):
        assert sentence_shape_violation(text) is None, text
    # 세 문장은 서로 다르다 — 같은 문장을 두 이름으로 두면 갈래가 갈리지 않은 것이다.
    assert len(_R25_FOOTPRINT_REASONS) == 3

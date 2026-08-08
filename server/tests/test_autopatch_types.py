from __future__ import annotations

import ast
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

from server.prechk.inventory import COMPLETE, FIXTURE_ROOT, FixtureRecord, Inventory
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

_LIBRARY_NAME_PATTERN = re.compile(
    r"(?i)(robe|robin|megapointe|ledbeam|ledwash|mmx|martin|clay ?paky|ayrton|chauvet|"
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
_R17_TEST_SOURCES = (
    Path("server/tests/test_autopatch_types.py"),
    Path("server/tests/test_autopatch_verify.py"),
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
    """`server/vwx` 전 모듈(`server/vwx/*.py`)의 모호성 판정 자리를 전수로 모은다."""
    census: set[tuple[str, str, str, str]] = set()
    for path in sorted(_VWX_SOURCE_DIR.glob("*.py")):
        census |= ambiguity_candidate_sites(path.read_text(encoding="utf-8"), path.name)
    return census


def declared_test_names() -> set[str]:
    """`server/tests/test_autopatch_types.py`·`test_autopatch_verify.py` 두 파일이 선언한
    `test_*` 함수 이름을 전부 모은다 — 그 두 파일이 이 레지스트리의 대조군 소재지다.
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

#: `server/vwx/` 전 모듈 모호성 판정 자리 — 스캐너 결과와 **양방향 일치**해야 한다.
_R17_AMBIGUITY_SITES = (
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
    for path in sorted(Path("server/vwx").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))

        def walk(node: ast.AST, stack: tuple[str, ...], name: str = path.name) -> None:
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
    modules = tuple(sorted(Path("server/vwx").glob("*.py")))
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
                    sites.add((path.name, markers))
    return tuple(sorted(sites))


#: (모듈, 표지) → 그 서술이 참임을 보장하는 **근거 부류**. 손으로 판정하고
#: 아래 전단사가 프로덕션 스캔과 맞춘다.
_R19_CLAIM_BASIS = {
    ("diff.py", ("콘솔 대조",)): "stage_one_states_its_own_act",
    ("diff.py", ("콘솔 실측",)): "stage_one_states_its_own_act",
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
_R19_REASON_RESOLVERS = ("_incompleteness_reason",)


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

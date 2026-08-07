from __future__ import annotations

import ast
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

from server.prechk.inventory import COMPLETE, FIXTURE_ROOT, FixtureRecord, Inventory
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
    TypeRequest,
    read_fixture_type_library,
    resolve_fixture_types,
)
from server.vwx.verdicts import (
    DMX_MODE_NOT_IN_LIBRARY,
    FIXTURE_TYPE_LIBRARY_TRUNCATED,
    FIXTURE_TYPE_LIBRARY_UNREADABLE,
    FIXTURE_TYPE_NOT_IN_LIBRARY,
    FOOTPRINT_MATCH_DESCOPE,
    TYPE_LIBRARY_ABSENT,
    TYPE_LIBRARY_INCOMPLETE,
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
                assert row["status"] == TYPE_NEEDS_CONFIRMATION, (library, aliases)
                assert row["console_type"] is None, (library, aliases)
                assert row["console_mode"] is None, (library, aliases)
                assert row["confirmation_source"] is None, (library, aliases)
                assert row["reason"] == VACUOUS_TYPE_KEY_REASON, (library, aliases)
                # 찾아보지도 않은 것을 **부재로 단정하지 않는다** — 하드스톱을 내지 않는다.
                assert hard_stop_codes(payload) == [], (library, aliases)

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

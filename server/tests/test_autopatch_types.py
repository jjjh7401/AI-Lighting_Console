from __future__ import annotations

import ast
import re
from copy import deepcopy
from pathlib import Path

import pytest

from server.vwx.rig import fuzzy_type_equal
from server.vwx.typemap import (
    ASSUMPTION_72_GO,
    ASSUMPTION_72_INCONCLUSIVE,
    ASSUMPTION_72_NEGATIVE,
    DMX_MODES_SEGMENT,
    FIXTURE_TYPE_LIBRARY_ROOT,
    FOOTPRINT_UNVERIFIED_COLUMN,
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
        modes_match = re.fullmatch(
            rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)/{DMX_MODES_SEGMENT}", path
        )
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
        match = re.fullmatch(
            rf"{FIXTURE_TYPE_LIBRARY_ROOT}/(\d+)/{DMX_MODES_SEGMENT}/(\d+)", path
        )
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

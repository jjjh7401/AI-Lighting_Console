"""Patch-sheet builder + renderer (SPEC-COPILOT-PAPERWORK-001).

``build_patch_sheet`` rides ``server.prechk.inventory.read_inventory`` — the
SAME chokepoint the pre-check tool uses — so this suite fakes an
``InventoryPort`` (query_state + query_property) the same shape those tests
use, never a real console.
"""

from __future__ import annotations

import pytest

from server.paperwork.data import PatchSheet, build_patch_sheet
from server.paperwork.render import render_patch_sheet
from server.prechk.footprint import (
    REASON_UNRESOLVED,
    ModeFootprint,
    WalkOutcome,
    upper_bound,
)
from server.prechk.inventory import (
    FIXTURE_ROOT,
    UNTRANSLATED_NO_TABLE,
    UNTRANSLATED_SLOT_ABSENT,
    UNTRANSLATED_TREE_UNREADABLE,
    InventoryReadError,
    translate_fixture_type,
)
from server.prechk.mode_read import TypeNameRead


class FakeInventoryPort:
    """Fake StateQueryPort + PropertyQueryPort backed by dicts."""

    def __init__(self, states: dict[str, dict], properties: dict[tuple[str, str], dict]):
        self._states = states
        self._properties = properties
        self.state_queries: list[str] = []
        self.property_queries: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        self.state_queries.append(path)
        if path not in self._states:
            raise LookupError(f"unknown state path: {path}")
        return self._states[path]

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_queries.append((path, property_name))
        key = (path, property_name)
        if key not in self._properties:
            raise LookupError(f"unknown property: {key}")
        return self._properties[key]


def _prop(value: str) -> dict:
    return {"ok": True, "value": value}


def _two_fixture_port() -> FakeInventoryPort:
    states = {
        FIXTURE_ROOT: {
            "ok": True,
            "node": {"name": "Fixtures", "class": "Container", "childCount": 2},
            "children": [{"i": 1, "name": "Spot 1"}, {"i": 2, "name": "Wash 1"}],
        }
    }
    properties = {
        (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
        (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Robe MegaPointe"),
        (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
        (f"{FIXTURE_ROOT}/1", "Name"): _prop("Spot 1"),
        # slot 2: address does not parse — must degrade to raw text, not 0/1.
        (f"{FIXTURE_ROOT}/2", "Patch"): _prop("not-an-address"),
        (f"{FIXTURE_ROOT}/2", "FixtureType"): _prop("Wash Fixture"),
        (f"{FIXTURE_ROOT}/2", "Mode"): _prop("16bit"),
        (f"{FIXTURE_ROOT}/2", "Name"): _prop("Wash 1"),
    }
    return FakeInventoryPort(states, properties)


class TestBuildPatchSheet:
    def test_builds_one_row_per_observed_fixture(self):
        sheet = build_patch_sheet(_two_fixture_port())
        assert isinstance(sheet, PatchSheet)
        assert [row.slot for row in sheet.rows] == [1, 2]
        assert [row.name for row in sheet.rows] == ["Spot 1", "Wash 1"]

    def test_parses_the_universe_and_address_out_of_patch(self):
        sheet = build_patch_sheet(_two_fixture_port())
        row = sheet.rows[0]
        assert row.universe == 1
        assert row.address == 1
        assert row.fixture_type == "Robe MegaPointe"
        assert row.mode == "Standard"

    def test_a_malformed_address_degrades_to_raw_text_never_a_fabricated_number(self):
        sheet = build_patch_sheet(_two_fixture_port())
        row = sheet.rows[1]
        assert row.universe is None
        assert row.address is None
        assert row.patch_raw == "not-an-address"

    def test_reports_completeness_from_the_inventory_read(self):
        sheet = build_patch_sheet(_two_fixture_port())
        assert sheet.completeness == "complete"
        assert sheet.observed_count == 2
        assert sheet.child_count == 2
        assert sheet.root == FIXTURE_ROOT

    def test_unreadable_root_raises_instead_of_an_empty_sheet(self):
        states = {FIXTURE_ROOT: {"ok": False, "error": "path segment not found"}}
        port = FakeInventoryPort(states, {})
        with pytest.raises(InventoryReadError):
            build_patch_sheet(port)

    def test_a_short_root_snapshot_reports_incomplete(self):
        states = {
            FIXTURE_ROOT: {
                "ok": True,
                "node": {"name": "Fixtures", "class": "Container", "childCount": 3},
                "children": [{"i": 1, "name": "Spot 1"}],
            }
        }
        properties = {
            (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
            (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Robe MegaPointe"),
            (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
            (f"{FIXTURE_ROOT}/1", "Name"): _prop("Spot 1"),
        }
        port = FakeInventoryPort(states, properties)
        sheet = build_patch_sheet(port)
        assert sheet.completeness == "incomplete"
        assert sheet.observed_count == 1
        assert sheet.child_count == 3


class TestRenderPatchSheet:
    def test_renders_a_self_contained_html_document(self):
        sheet = build_patch_sheet(_two_fixture_port())
        html = render_patch_sheet(sheet)
        assert html.startswith("<!doctype html>")
        assert "<style>" in html
        assert "<link " not in html  # no external stylesheet
        assert "<script" not in html  # no external/inline script needed either
        assert "Spot 1" in html
        assert "Robe MegaPointe" in html

    def test_escapes_fixture_names_against_html_injection(self):
        states = {
            FIXTURE_ROOT: {
                "ok": True,
                "node": {"name": "Fixtures", "class": "Container", "childCount": 1},
                "children": [{"i": 1, "name": "<script>alert(1)</script>"}],
            }
        }
        properties = {
            (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
            (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Spot"),
            (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
            (f"{FIXTURE_ROOT}/1", "Name"): _prop("<script>alert(1)</script>"),
        }
        sheet = build_patch_sheet(FakeInventoryPort(states, properties))
        html = render_patch_sheet(sheet)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_empty_sheet_still_renders_a_valid_document(self):
        states = {
            FIXTURE_ROOT: {
                "ok": True,
                "node": {"name": "Fixtures", "class": "Container", "childCount": 0},
                "children": [],
            }
        }
        sheet = build_patch_sheet(FakeInventoryPort(states, {}))
        html = render_patch_sheet(sheet)
        assert "관측된 픽스처 없음" in html


class TestChannelWidthUpperBound:
    """``walk`` threads ``server.prechk.footprint.WalkOutcome`` into the
    sheet — never a raw ``max()`` (§3 of the shared contract: a partial mode
    set folded with ``max`` looks like a bound and is smaller than the true
    one)."""

    def test_walk_omitted_leaves_all_three_fields_none(self):
        sheet = build_patch_sheet(_two_fixture_port())
        assert sheet.bound is None
        assert sheet.bound_source is None
        assert sheet.bound_unavailable is None

    def test_walk_omitted_renders_no_bound_line_at_all(self):
        sheet = build_patch_sheet(_two_fixture_port())
        html = render_patch_sheet(sheet)
        assert "upper bound" not in html.lower()

    def test_complete_walk_yields_the_same_value_as_upper_bound(self):
        walk = WalkOutcome(
            complete=True,
            footprints=(
                ModeFootprint(path="Patch/FixtureTypes/1/DMXModes/1/DMXChannels", width=17),
                ModeFootprint(path="Patch/FixtureTypes/1/DMXModes/2/DMXChannels", width=23),
            ),
        )
        sheet = build_patch_sheet(_two_fixture_port(), walk=walk)
        assert sheet.bound == upper_bound(walk) == 23
        assert sheet.bound_unavailable is None

    def test_complete_walk_bound_source_names_the_widest_path(self):
        walk = WalkOutcome(
            complete=True,
            footprints=(
                ModeFootprint(path="Patch/FixtureTypes/1/DMXModes/1/DMXChannels", width=17),
                ModeFootprint(path="Patch/FixtureTypes/1/DMXModes/2/DMXChannels", width=23),
            ),
        )
        sheet = build_patch_sheet(_two_fixture_port(), walk=walk)
        assert sheet.bound_source == "Patch/FixtureTypes/1/DMXModes/2/DMXChannels childCount"

    def test_complete_walk_renders_value_and_source_and_qualifier_in_one_sentence(self):
        walk = WalkOutcome(
            complete=True,
            footprints=(
                ModeFootprint(path="Patch/FixtureTypes/1/DMXModes/1/DMXChannels", width=23),
            ),
        )
        sheet = build_patch_sheet(_two_fixture_port(), walk=walk)
        html = render_patch_sheet(sheet)
        # value + source + the asymmetric qualifier must share ONE meta line —
        # splitting the qualifier into its own sentence loses it on a partial
        # read (OVERLAP-001 M5).
        assert (
            "채널폭 상계: 23 "
            "(source: Patch/FixtureTypes/1/DMXModes/1/DMXChannels childCount) — "
            "이 값 이상의 간격은 겹침 없음 확인; "
            "이하는 미확정." in html
        )

    def test_incomplete_walk_has_no_bound(self):
        walk = WalkOutcome(
            complete=False,
            failure=REASON_UNRESOLVED,
            failure_detail="경로 Patch/FixtureTypes를 이 쇼파일에서 찾지 못했다.",
        )
        sheet = build_patch_sheet(_two_fixture_port(), walk=walk)
        assert sheet.bound is None
        assert sheet.bound_source is None

    def test_incomplete_walk_bound_unavailable_is_the_walks_own_reason_verbatim(self):
        walk = WalkOutcome(
            complete=False,
            failure=REASON_UNRESOLVED,
            failure_detail="경로 Patch/FixtureTypes를 이 쇼파일에서 찾지 못했다.",
        )
        sheet = build_patch_sheet(_two_fixture_port(), walk=walk)
        assert sheet.bound_unavailable == walk.failure_detail

    def test_incomplete_walk_renders_the_unavailable_reason(self):
        walk = WalkOutcome(
            complete=False,
            failure=REASON_UNRESOLVED,
            failure_detail="경로 Patch/FixtureTypes를 이 쇼파일에서 찾지 못했다.",
        )
        sheet = build_patch_sheet(_two_fixture_port(), walk=walk)
        html = render_patch_sheet(sheet)
        assert "채널폭 상계 미확인" in html
        assert "경로 Patch/FixtureTypes를 이 쇼파일에서 찾지 못했다." in html

    def test_partial_mode_set_does_not_leak_a_smaller_bound(self):
        """Non-vacuity: an incomplete walk with SOME footprints already
        enumerated must still yield ``bound is None`` — if a naive ``max()``
        over the partial set snuck in here instead of ``upper_bound()``, this
        assertion is the one that would catch it (a partial-max is smaller
        than the true bound and would clear a gap that isn't actually
        clear)."""
        walk = WalkOutcome(
            complete=False,
            footprints=(
                ModeFootprint(path="Patch/FixtureTypes/1/DMXModes/1/DMXChannels", width=17),
            ),
            notes=("모드 열거가 불완전하다(Patch/FixtureTypes/1/DMXModes)",),
        )
        assert upper_bound(walk) is None
        sheet = build_patch_sheet(_two_fixture_port(), walk=walk)
        assert sheet.bound is None


# --- SPEC-COPILOT-READBACK-002 M1 — 타입명 표를 받아 넘긴다 --------------------
#
# `build_patch_sheet` 은 표를 **매개변수로 받고 스스로 읽지 않는다**
# (REQ-READBACK2-007). 읽기는 호출자로 밀려난다 — 비준된 조회 예산 규칙
# (`server/prechk/inventory.py:469-473`)이 `_name_handle_types` 를 「매핑이
# 아니라 읽은 결과를 받는」 형상으로 못박아 뒀기 때문이다.


def _handle_fixture_port() -> FakeInventoryPort:
    """실기 콘솔이 실제로 돌려주는 형태 — 이름이 아니라 `FixtureType <슬롯>` 핸들.

    슬롯 12 는 표가 이름을 아는 핸들, 슬롯 99 는 표가 **선언하지 않는** 슬롯이다.
    후자가 AC-READBACK2-009 의 대상이다.
    """
    states = {
        FIXTURE_ROOT: {
            "ok": True,
            "node": {"name": "Fixtures", "class": "Container", "childCount": 2},
            "children": [{"i": 1, "name": "Spot 1"}, {"i": 2, "name": "Spot 2"}],
        }
    }
    properties = {
        (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
        (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("FixtureType 12"),
        (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
        (f"{FIXTURE_ROOT}/1", "Name"): _prop("Spot 1"),
        (f"{FIXTURE_ROOT}/2", "Patch"): _prop("1.032"),
        (f"{FIXTURE_ROOT}/2", "FixtureType"): _prop("FixtureType 99"),
        (f"{FIXTURE_ROOT}/2", "Mode"): _prop("Standard"),
        (f"{FIXTURE_ROOT}/2", "Name"): _prop("Spot 2"),
    }
    return FakeInventoryPort(states, properties)


def _names(*pairs: tuple[int, str]) -> TypeNameRead:
    return TypeNameRead(attempted=True, pairs=pairs)


#: 렌더된 **행**에 붙은 미번역 배지의 클래스 속성 전문. 클래스 이름만 세면
#: `<style>` 의 규칙 정의가 함께 잡힌다 — 아래 계수 단언의 계기다.
_BADGE = 'class="badge badge-untranslated"'


class TestTheSheetPrintsNamesNotHandles:
    """AC-READBACK2-010 — 표를 넘기면 시트에 사람이 읽는 이름이 온다."""

    def test_a_handle_becomes_a_name_when_the_table_is_passed(self):
        sheet = build_patch_sheet(
            _handle_fixture_port(), type_names=_names((12, "Robe MegaPointe"))
        )

        assert sheet.rows[0].fixture_type == "Robe MegaPointe"
        assert sheet.rows[0].fixture_type_untranslated is None

    def test_no_handle_shape_survives_into_the_rendered_sheet(self):
        # [HARD] `FixtureType <숫자>` 가 인쇄면에 남으면 시트를 읽는 사람은
        # 무슨 장비인지 알 수 없다.
        sheet = build_patch_sheet(
            _handle_fixture_port(),
            type_names=_names((12, "Robe MegaPointe"), (99, "Source 4 LED")),
        )
        html = render_patch_sheet(sheet)

        assert "FixtureType 12" not in html
        assert "FixtureType 99" not in html
        assert "Robe MegaPointe" in html
        assert "Source 4 LED" in html

    def test_without_a_table_the_handle_stays_and_is_marked(self):
        # 표를 안 넘기면 번역이 **조용히 사라지지 않고** 미번역 표식이 켜진다.
        sheet = build_patch_sheet(_handle_fixture_port())

        assert sheet.rows[0].fixture_type == "FixtureType 12"
        assert sheet.rows[0].fixture_type_untranslated == UNTRANSLATED_NO_TABLE


class TestTheSheetNeverReadsTheTableItself:
    """AC-READBACK2-011 — 함수 내부 타입 표 조회 횟수는 **0** 이다."""

    def test_passing_the_table_adds_no_query_of_its_own(self):
        port = _handle_fixture_port()

        build_patch_sheet(port, type_names=_names((12, "Robe MegaPointe")))

        # 계기의 양성 대조군: 이 포트는 실제로 조회를 기록한다(픽스처 루트 1회).
        assert port.state_queries == [FIXTURE_ROOT]
        # 그리고 그 로그에 타입 트리 경로는 **없다**.
        assert [path for path in port.state_queries if "FixtureType" in path] == []

    def test_omitting_the_table_also_adds_no_query(self):
        port = _handle_fixture_port()

        build_patch_sheet(port)

        assert port.state_queries == [FIXTURE_ROOT]


class TestTranslationFailureIsVisibleOnTheSheet:
    """AC-READBACK2-009 [부정 대조군] — 번역 실패가 인쇄 경계에서 버려지지 않는다.

    **술어 결정(plan-audit D9).** AC-009 의 「시트 위에 보이게 인쇄되며 번역된
    행과 시각적으로 구별된다」를 다음 셋으로 기계 판정한다.

    1. **존재** — 미번역 행의 `<td>` 에 `badge-untranslated` 클래스를 가진
       배지가 있고, 그 배지 텍스트에 사유 문자열(`slot_absent` 등)이 실려 있다.
    2. **구별** — 같은 문서 안에서 `badge-untranslated` 출현 횟수가 미번역 행
       수와 **정확히 같다.** 번역된 행에는 안 붙는다는 뜻이며, 이것이 「구별」의
       기계적 형태다(모든 행에 붙으면 구별이 아니다).
    3. **렌더 가능** — 문서의 `<style>` 블록이 그 클래스를 정의한다. 정의 없는
       클래스명은 문서에 문자열로 존재해도 화면에서 구별되지 않는다.

    **이 술어의 경계 밖은 아래 `TestTheThirdHandleShapeStillPassesUnmarked`
    가 쏜다** — 그리고 그 갈래는 이 SPEC 이 메우지 않고 명시하는 구멍이다
    (REQ-READBACK2-011).

    **계기 주석.** 배지 수를 셀 때 문서 전체에서 `badge-untranslated` 를 세면
    `<style>` 블록의 `.badge-untranslated` **규칙 자체**가 함께 잡혀 항상 1이
    더 나온다(실측: 미번역 2행에 3). 그래서 세는 것은 클래스 이름이 아니라
    **행에 붙은 클래스 속성 전문**(`_BADGE`)이고, 규칙 정의의 존재는
    `test_the_badge_class_is_actually_styled` 가 따로 판정한다.
    """

    def test_an_unresolvable_handle_prints_its_reason_on_the_sheet(self):
        # 슬롯 99 를 선언하지 않는 표 → slot_absent.
        sheet = build_patch_sheet(
            _handle_fixture_port(), type_names=_names((12, "Robe MegaPointe"))
        )
        html = render_patch_sheet(sheet)

        assert sheet.rows[1].fixture_type_untranslated == UNTRANSLATED_SLOT_ABSENT
        assert "badge-untranslated" in html
        assert UNTRANSLATED_SLOT_ABSENT in html

    def test_only_the_untranslated_row_carries_the_badge(self):
        # [HARD] 「구별」의 기계적 형태 — 배지 수 == 미번역 행 수.
        sheet = build_patch_sheet(
            _handle_fixture_port(), type_names=_names((12, "Robe MegaPointe"))
        )
        html = render_patch_sheet(sheet)

        untranslated_rows = sum(
            1 for row in sheet.rows if row.fixture_type_untranslated is not None
        )
        assert untranslated_rows == 1
        assert html.count(_BADGE) == untranslated_rows

    def test_a_fully_translated_sheet_carries_no_badge_at_all(self):
        # 부정 대조군의 반대 팔: 배지가 항상 켜져 있으면 위 계수는 통과해도
        # 아무것도 구별하지 않는다.
        sheet = build_patch_sheet(
            _handle_fixture_port(),
            type_names=_names((12, "Robe MegaPointe"), (99, "Source 4 LED")),
        )
        html = render_patch_sheet(sheet)

        assert html.count(_BADGE) == 0

    def test_the_badge_class_is_actually_styled(self):
        # 정의 없는 클래스명은 문서에 있어도 화면에서 구별되지 않는다.
        sheet = build_patch_sheet(
            _handle_fixture_port(), type_names=_names((12, "Robe MegaPointe"))
        )
        html = render_patch_sheet(sheet)
        style = html.split("<style>", 1)[1].split("</style>", 1)[0]

        assert ".badge-untranslated" in style

    def test_an_unreadable_tree_is_distinguished_from_an_absent_slot(self):
        # 두 사유는 운영자 행동이 다르다 — 재조회 vs 리그 확인. 시트가 사유
        # 문자열을 실으므로 그 구별이 인쇄면까지 산다.
        sheet = build_patch_sheet(_handle_fixture_port(), type_names=TypeNameRead(attempted=False))
        html = render_patch_sheet(sheet)

        assert sheet.rows[0].fixture_type_untranslated == UNTRANSLATED_TREE_UNREADABLE
        assert UNTRANSLATED_TREE_UNREADABLE in html
        assert html.count(_BADGE) == 2


class TestTheThirdHandleShapeStillPassesUnmarked:
    """REQ-READBACK2-011 — 술어의 경계 **밖**을 쏜다. 이 구멍은 열린 채로 남는다.

    `HANDLE_TEXT = ^FixtureType (\\d+)$`(`inventory.py:111`)이 번역의 방아쇠다.
    그 형태가 아닌 값은 **이름으로 간주돼 표식 없이 통과**한다 — 코드 자신이
    그렇게 적어 뒀다(`inventory.py:479-485`). 여섯 소비자를 고쳐도 이 갈래는
    바뀌지 않으므로, 여기서 **현재 동작을 못박아** 미검증 절의 근거로 쓴다.

    이 테스트가 깨지면 누군가 방아쇠 폭을 바꿨다는 뜻이고, 그때는 이 SPEC 의
    미검증 절이 낡는다.
    """

    def test_shapes_outside_the_trigger_are_passed_through_unmarked(self):
        family = [
            "",  # 빈 문자열
            "FixtureType",  # 숫자 없는 핸들
            "FixtureType 12x",  # 접미사가 붙은 핸들
            " FixtureType 12",  # 앞 공백
            "12",  # 접두어 없는 숫자
            "Fixture Type 12",  # 이름처럼 보이는 핸들
            "FixtureType 십이",  # 비ASCII 숫자
            "픽스처타입 12",  # 비ASCII 접두어
        ]
        for raw in family:
            value, reason = translate_fixture_type(raw, {12: "Robe MegaPointe"})

            assert value == raw, raw
            # 표식이 **없다** — 조용히 틀린 것이 아니라 미해결이지도 않다.
            assert reason is None, raw

    def test_none_stays_none(self):
        assert translate_fixture_type(None, {12: "Robe MegaPointe"}) == (None, None)

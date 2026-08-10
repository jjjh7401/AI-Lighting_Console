"""부분 정보 인테이크 — 모자란 값이 **오류가 아니라 질문**으로 나오는가.

이 파일이 지키는 것은 넷이다.

1. **아무것도 안 줘도 죽지 않는다.** 빈 요청은 예외가 아니라 질문 목록을 낸다.
2. **모호하면 고른다고 하지 않고 묻는다.** 이름이 비슷한 타입이 여럿일 때 첫 일치를
   집는 붕괴가 이 SPEC의 반복 결함이었다(`R22-C`).
3. **자동으로 채운 값은 반드시 보고한다.** 조용히 주소를 지어내지 않는다.
4. **막는 것과 안 막는 것을 가른다.** 라벨이 없다고 착수를 막지 않는다.

질문 순서는 grandMA3 Insert New Fixtures 마법사와 같다
(``patch_add_fixtures.html``: 타입 -> 이름 -> 수량 -> 첫 ID -> 첫 주소).
"""

from __future__ import annotations

import pytest

from server.vwx.address import resolve_all
from server.vwx.columns import resolve_columns
from server.vwx.intake import (
    DERIVED_FOOTPRINT,
    DERIVED_NEXT_FREE_ADDRESS,
    DERIVED_NEXT_FREE_FID,
    DERIVED_SOLE_MODE,
    PATCH_MANUAL,
    PATCH_NEXT_FREE,
    FixtureRequest,
    LibraryOption,
    Occupancy,
    apply_answer,
    assess,
)
from server.vwx.mvr import MVR_HEADERS, UNIVERSE_WIDTH
from server.vwx.rig import build_designed_rig

LIBRARY = (
    LibraryOption(
        "MAC Encore Performance CLD",
        "Martin Professional@MAC Encore Performance CLD",
        {"Basic": 38, "Extended": 52},
    ),
    LibraryOption("Mac Aura XB", "Martin@Mac Aura XB", {"Standard (14 ch)": 14}),
    LibraryOption("Rush Par 2 RGBW Zoom", "Martin@Rush Par 2 RGBW Zoom", {"5ch": 5}),
    LibraryOption("Mac Aura PXL", "Martin@Mac Aura PXL", {"Basic": 20}),
)

BUSY = Occupancy(used_absolute=frozenset(range(1, 495)), used_fids=frozenset(range(1, 14)))


def _fields(result) -> set[str]:
    return {q.field for q in result.questions}


def _blocking(result) -> set[str]:
    return {q.field for q in result.blocking_questions}


class TestNothingIsAnError:
    """모자란 입력은 실패가 아니다."""

    def test_an_empty_request_asks_instead_of_raising(self):
        result = assess(FixtureRequest(), LIBRARY)
        assert result.ready is False
        assert result.rows == ()
        assert "instrument_type" in _blocking(result)

    def test_it_asks_in_the_wizard_order(self):
        """MA3 마법사와 같은 순서 — 사용자가 아는 순서로 답할 수 있어야 한다."""
        result = assess(FixtureRequest(), LIBRARY)
        order = [q.field for q in result.questions]
        expected = ["instrument_type", "quantity", "patch_mode"]
        assert [f for f in order if f in expected] == expected

    def test_no_library_still_asks_rather_than_failing(self):
        """라이브러리를 못 읽은 상황에서도 물어본다 — 자유 입력으로."""
        result = assess(FixtureRequest(), ())
        question = next(q for q in result.questions if q.field == "instrument_type")
        assert question.choices == ()
        assert question.kind == "text"

    def test_every_question_says_why(self):
        """이유 없는 질문은 사용자를 막는 벽이다."""
        result = assess(FixtureRequest(), LIBRARY)
        assert all(q.why.strip() for q in result.questions)


class TestAmbiguityIsAskedNotGuessed:
    """이름이 좁혀지지 않으면 **고르지 않는다.**"""

    def test_a_prefix_that_matches_two_types_is_asked(self):
        """'Mac Aura'는 XB와 PXL 둘에 걸린다 — 먼저 걸린 것을 집지 않는다."""
        result = assess(FixtureRequest(instrument_type="Mac Aura"), LIBRARY)
        question = next(q for q in result.questions if q.field == "instrument_type")
        labels = {c.label for c in question.choices}
        assert labels == {"Mac Aura XB", "Mac Aura PXL"}
        assert result.ready is False

    def test_a_prefix_that_matches_one_type_resolves(self):
        """[비공허] 하나로 좁혀지면 묻지 않는다 — 안 그러면 위 시험이 공허하다."""
        result = assess(FixtureRequest(instrument_type="Encore"), LIBRARY)
        assert "instrument_type" not in _fields(result)

    def test_a_type_outside_the_library_is_asked_and_named(self):
        result = assess(FixtureRequest(instrument_type="Clay Paky Sharpy"), LIBRARY)
        question = next(q for q in result.questions if q.field == "instrument_type")
        assert "Clay Paky Sharpy" in question.prompt
        assert question.blocking is True

    def test_a_mode_outside_the_type_is_asked_again(self):
        request = FixtureRequest(instrument_type="Mac Aura XB", mode="Extended (25 ch)")
        result = assess(request, LIBRARY)
        question = next(q for q in result.questions if q.field == "mode")
        assert {c.value for c in question.choices} == {"Standard (14 ch)"}


class TestWhatIsFilledInIsReported:
    """자동으로 채운 값은 전부 되돌려 보고한다."""

    def test_a_sole_mode_is_taken_and_disclosed(self):
        result = assess(FixtureRequest(instrument_type="Mac Aura XB"), LIBRARY)
        assert "mode" not in _fields(result)
        assert DERIVED_SOLE_MODE in {d.source for d in result.derivations}

    def test_two_modes_are_never_taken_silently(self):
        """[비공허] 모드가 둘이면 고르지 않는다."""
        result = assess(FixtureRequest(instrument_type="Encore"), LIBRARY)
        assert "mode" in _blocking(result)
        assert DERIVED_SOLE_MODE not in {d.source for d in result.derivations}

    def test_the_footprint_comes_from_the_library(self):
        result = assess(
            FixtureRequest(
                instrument_type="Encore", mode="Basic", quantity=1, universe="1", address="1"
            ),
            LIBRARY,
        )
        derivation = next(d for d in result.derivations if d.source == DERIVED_FOOTPRINT)
        assert derivation.value == "38"
        assert result.rows[0]["DMX Footprint"] == "38"

    def test_auto_assigned_addresses_are_disclosed(self):
        request = FixtureRequest(
            instrument_type="Mac Aura XB", quantity=3, patch_mode=PATCH_NEXT_FREE
        )
        result = assess(request, LIBRARY, BUSY)
        sources = {d.source for d in result.derivations}
        assert DERIVED_NEXT_FREE_ADDRESS in sources
        assert DERIVED_NEXT_FREE_FID in sources


class TestAutoAssignmentIsSafe:
    """자동 배정이 콘솔을 깨지 않는가."""

    @pytest.fixture()
    def six(self):
        request = FixtureRequest(
            instrument_type="Mac Aura XB", quantity=6, patch_mode=PATCH_NEXT_FREE
        )
        return assess(request, LIBRARY, BUSY)

    def test_it_never_lands_on_an_occupied_channel(self, six):
        for row in six.rows:
            start = int(row["Absolute Address"])
            width = int(row["DMX Footprint"])
            assert not (set(range(start, start + width)) & BUSY.used_absolute)

    def test_the_blocks_do_not_overlap_each_other(self, six):
        taken: set[int] = set()
        for row in six.rows:
            start = int(row["Absolute Address"])
            width = int(row["DMX Footprint"])
            block = set(range(start, start + width))
            assert not (block & taken)
            taken |= block

    def test_a_fixture_never_straddles_a_universe_boundary(self, six):
        """MA3 Patch는 유니버스 안의 주소다 — 걸치면 그 픽스처는 설 자리가 없다."""
        for row in six.rows:
            start = int(row["Absolute Address"])
            width = int(row["DMX Footprint"])
            assert (start - 1) // UNIVERSE_WIDTH == (start + width - 2) // UNIVERSE_WIDTH

    def test_the_boundary_case_actually_occurs_here(self, six):
        """[비공허] 위 시험이 공허하지 않다 — 이 배치는 실제로 경계를 넘어간다."""
        universes = {int(row["Universe"]) for row in six.rows}
        assert len(universes) >= 2

    def test_it_never_reuses_an_occupied_fid(self, six):
        for row in six.rows:
            assert int(row["Fixture ID"]) not in BUSY.used_fids

    def test_an_empty_console_starts_at_one(self):
        request = FixtureRequest(
            instrument_type="Mac Aura XB", quantity=2, patch_mode=PATCH_NEXT_FREE
        )
        result = assess(request, LIBRARY)
        assert result.rows[0]["Absolute Address"] == "1"
        assert result.rows[0]["Fixture ID"] == "1"


class TestManualPatchIsHonoured:
    """사용자가 준 주소는 그대로 쓴다."""

    def test_a_dotted_address_becomes_universe_and_address(self):
        request = apply_answer(
            FixtureRequest(instrument_type="Mac Aura XB", quantity=2), "address", "3.10"
        )
        result = assess(request, LIBRARY)
        assert result.rows[0]["Universe"] == "3"
        assert result.rows[0]["U Address"] == "10"

    def test_the_next_fixture_steps_by_the_footprint(self):
        request = apply_answer(
            FixtureRequest(instrument_type="Mac Aura XB", quantity=3), "address", "1.1"
        )
        result = assess(request, LIBRARY)
        starts = [int(row["Absolute Address"]) for row in result.rows]
        assert starts == [1, 15, 29]

    def test_an_absolute_address_is_accepted_too(self):
        request = apply_answer(
            FixtureRequest(instrument_type="Mac Aura XB", quantity=1), "address", "600"
        )
        result = assess(request, LIBRARY)
        assert result.rows[0]["Universe"] == "2"
        assert result.rows[0]["U Address"] == "88"

    def test_choosing_manual_without_an_address_asks_for_one(self):
        request = FixtureRequest(instrument_type="Mac Aura XB", quantity=1, patch_mode=PATCH_MANUAL)
        result = assess(request, LIBRARY)
        assert "address" in _blocking(result)


class TestOptionalNeverBlocks:
    """라벨이 없다고 착수를 막지 않는다."""

    def test_position_is_asked_but_does_not_block(self):
        request = FixtureRequest(
            instrument_type="Mac Aura XB", quantity=1, patch_mode=PATCH_NEXT_FREE
        )
        result = assess(request, LIBRARY)
        assert "position" in _fields(result)
        assert "position" not in _blocking(result)
        assert result.ready is True

    def test_answering_it_removes_the_question(self):
        request = FixtureRequest(
            instrument_type="Mac Aura XB",
            quantity=1,
            patch_mode=PATCH_NEXT_FREE,
            position="LX1",
        )
        result = assess(request, LIBRARY)
        assert "position" not in _fields(result)
        assert result.rows[0]["Position"] == "LX1"


class TestTheRowsJoinTheSamePipeline:
    """인테이크 산출물이 MVR·시트와 **같은 하류**를 탄다."""

    @pytest.fixture()
    def ready(self):
        request = FixtureRequest(
            instrument_type="Encore",
            mode="Basic",
            quantity=4,
            patch_mode=PATCH_NEXT_FREE,
            position="Backtruss",
            name_prefix="Spot",
        )
        return assess(request, LIBRARY, BUSY)

    def test_the_rows_use_the_shared_header_vocabulary(self, ready):
        for row in ready.rows:
            assert set(row) == set(MVR_HEADERS)

    def test_the_rows_survive_to_a_designed_rig(self, ready):
        columns, failures, excluded = resolve_columns(list(ready.rows))
        resolved, address_failures = resolve_all(columns)
        rig = build_designed_rig(resolved, candidate_count=len(columns))
        assert failures == []
        assert excluded == []
        assert address_failures == []
        assert len(rig.fixtures) == 4
        assert rig.design_overlaps == ()

    def test_names_are_numbered_from_the_prefix(self, ready):
        assert [row["Fixture Name"] for row in ready.rows] == [
            "Spot 1",
            "Spot 2",
            "Spot 3",
            "Spot 4",
        ]


class TestAnswersAccumulate:
    """답을 하나씩 주면 질문이 하나씩 줄어든다."""

    def test_the_blocking_set_shrinks_monotonically(self):
        request = FixtureRequest()
        seen = [len(_blocking(assess(request, LIBRARY, BUSY)))]
        for name, value in (
            ("instrument_type", "Mac Aura XB"),
            ("quantity", "6"),
            ("patch_mode", PATCH_NEXT_FREE),
        ):
            request = apply_answer(request, name, value)
            seen.append(len(_blocking(assess(request, LIBRARY, BUSY))))
        assert seen == sorted(seen, reverse=True)
        assert seen[-1] == 0

    def test_an_unknown_field_is_not_silently_swallowed(self):
        """모르는 필드를 받으면 요청을 바꾸지 않는다 — 조용히 먹지 않는다."""
        request = FixtureRequest(instrument_type="Mac Aura XB")
        assert apply_answer(request, "nonsense", "x") == request

    def test_a_non_numeric_quantity_is_not_accepted(self):
        request = FixtureRequest()
        assert apply_answer(request, "quantity", "여섯").quantity is None

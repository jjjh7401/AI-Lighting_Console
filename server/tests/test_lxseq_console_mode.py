"""t333 — 기존 패치 대조 국면에서 콘솔 픽스처의 Mode 가 판별기가 된다.

라이브러리 판독으로는 폭이 같은 모드가 여럿일 때 좁힐 수 없다 — t128 의
「폭은 판별기가 아니다」가 그 자리다. 그런데 이미 그 자리에 꽂혀 있는 픽스처는
자기 모드를 ``"<DMXModes 슬롯> <이름>"`` 으로 답한다. 실측 2026-09-08(실기 onPC,
응답기 1.6.5): 타입 8종·픽스처 86대에서 앞 숫자가 라이브러리 슬롯과 8/8 일치,
뗀 이름이 라이브러리 이름과 8/8 일치 — ``.moai/reports/t333/preconditions.md`` §2.3.

**조인은 자리+타입이다.** FID 로 잇지 않는다 — inventory 는 FID 를 읽지 않는다
(화이트리스트 밖, ``server/prechk/inventory.py`` 의 ``fid_note`` 독스트링).
자리+타입은 ``already_patched`` 판정이 쓰는 그 술어와 같아서, 이 갈래는 정확히
「이미 패치된 행」에서만 켜진다 — 아직 없는 픽스처를 새로 패치할 때는 읽을 모드가
없으므로 라이브러리 판독이 여전히 유일한 경로다.

**이 갈래는 능력만 더한다.** 못 풀면 수정 전 동작(``mode_unresolved`` +
``mode_overrides`` 안내)이 그대로 유지된다 — 아래 fail-open 케이스들이 그것을
행마다 고정한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.lxseq.mapper import build_import_plan
from server.lxseq.parser import parse_patch_csv
from server.prechk.inventory import COMPLETE, INCOMPLETE, FixtureRecord, Inventory
from server.prechk.mode_read import ModeChoice, TypeModeRead, parse_console_mode_slot
from server.vwx.addressfit import Occupant
from server.vwx.patchplan import ExistingFidRead

FIXTURE_PATH = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")
CSV_TYPE = "Robe Spiider"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _records():
    records = parse_patch_csv(FIXTURE_PATH.read_text(encoding="utf-8")).records
    subset = [r for r in records if r.fixture_type == CSV_TYPE]
    # 비공허성 — 이 파일의 모든 단언은 이 부분집합이 비지 않아야 의미가 있다.
    assert subset, f"{CSV_TYPE} 행이 정본 fixture 에서 사라졌다 — 테스트가 공허해진다"
    return subset


def _present(name: str) -> dict:
    return {"status": "present", "resolved": name, "candidates": []}


def _complete_fid_read() -> ExistingFidRead:
    return ExistingFidRead(
        fids=(),
        child_count=0,
        enumerated_count=0,
        unseen=0,
        unreadable_fids=0,
        unusable_rows=0,
        unparsable_rows=0,
        attempted=True,
    )


def _one_mode(channels: int) -> dict[str, TypeModeRead]:
    """폭이 유일한 모드 하나 — 라이브러리 판독만으로 풀린다."""
    return {
        CSV_TYPE: TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(ModeChoice(name="Only", width=channels, slot=1),),
        )
    }


def _two_same_width_modes(channels: int) -> dict[str, TypeModeRead]:
    """폭이 같은 모드 둘 — 라이브러리 판독만으로는 원리적으로 못 좁힌다.

    CSV 의 ``Mode`` 라벨 토큰으로도 안 걸리도록 이름을 ``A``/``B`` 로 둔다
    (라벨 토큰 갈래가 대신 풀어 버리면 이 파일의 갈래가 안 켜진다).
    """
    return {
        CSV_TYPE: TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="A", width=channels, slot=1),
                ModeChoice(name="B", width=channels, slot=2),
            ),
        )
    }


def _inventory(fixtures: tuple[FixtureRecord, ...], *, complete: bool = True) -> Inventory:
    missing = 0 if complete else 3
    return Inventory(
        path="Root",
        child_count=len(fixtures) + missing,
        enumerated_count=len(fixtures),
        recovered_count=0,
        observed_count=len(fixtures),
        missing_count=missing,
        completeness=COMPLETE if complete else INCOMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
        fixtures=fixtures,
    )


def _console_fixtures(
    records,
    mode_text,
    *,
    fixture_type: str = CSV_TYPE,
    universe_shift: int = 0,
) -> tuple[FixtureRecord, ...]:
    """CSV 행과 같은 자리·같은 타입으로 콘솔에 이미 꽂혀 있는 픽스처들."""
    return tuple(
        FixtureRecord(
            slot=index + 1,
            name=f"SP {record.fid}",
            patch_raw=f"{record.universe + universe_shift}.{record.address:03d}",
            fixture_type=fixture_type,
            mode=mode_text,
        )
        for index, record in enumerate(records)
    )


def _occupants(records, *, fixture_type: str = CSV_TYPE) -> tuple[Occupant, ...]:
    return tuple(
        Occupant(
            universe=record.universe,
            address=record.address,
            name=f"SP {record.fid}",
            fixture_type=fixture_type,
        )
        for record in records
    )


def _plan(records, **overrides):
    kwargs = {
        "records": records,
        "type_resolutions": {CSV_TYPE: _present(CSV_TYPE)},
        "mode_reads": _one_mode(records[0].channels),
        "inventory": _inventory(()),
        "occupants": (),
        "existing_fids": _complete_fid_read(),
    }
    kwargs.update(overrides)
    return build_import_plan(**kwargs)


def _resolution(plan):
    matches = [r for key, r in plan.mode_resolutions.items() if key[0] == CSV_TYPE]
    assert matches, "이 타입의 모드 해석이 기록되지 않았다"
    return matches[0]


# ---------------------------------------------------------------------------
# the parser — 첫 공백 토큰 하나만 뗀다
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode_text,expected",
    [
        # 실측된 8종 전부(preconditions.md §2.3).
        ("1 Extended - Extended", 1),
        ("1 Mode 1", 1),
        ("2 9 channel", 2),
        ("3 Direct", 3),
        ("3 Extended", 3),
        ("4 4 channel", 4),
        ("1 Mode 0", 1),
        # 🔴 두 자리 슬롯. 라이브러리에 `Mode 10` 이 실제로 있다.
        ("10 Mode 10", 10),
    ],
)
def test_parser_takes_the_leading_token_as_the_slot(mode_text, expected):
    assert parse_console_mode_slot(mode_text) == expected


@pytest.mark.parametrize(
    "mode_text,slot,remainder",
    [
        # 실측값을 그대로 박는다 — 파생식으로 쓰면 식이 틀려도 통과할 수 있다.
        # 슬롯과 이름의 첫 숫자가 **다른** 케이스가 함정의 핵심이다(2 vs 9).
        ("4 4 channel", 4, "4 channel"),
        ("2 9 channel", 2, "9 channel"),
    ],
)
def test_parser_keeps_a_name_that_itself_starts_with_a_digit(mode_text, slot, remainder):
    """🔴 앞 숫자를 뗀 나머지가 **또 숫자로 시작한다** — 실측된 함정.

    「숫자를 전부 떼기」류 술어는 여기서 `channel` 만 남기고 조용히 틀린다.
    실패가 아니라 오답으로 나타나는 계열이라 계기로 잡히지 않는다. 그래서
    파서가 무엇을 남기는지를 직접 단언한다.
    """
    assert parse_console_mode_slot(mode_text) == slot
    assert mode_text.partition(" ")[2] == remainder
    assert remainder[0].isdigit()


@pytest.mark.parametrize(
    "mode_text",
    [
        "Direct",  # 앞 토큰이 숫자가 아니다 — 슬롯을 추측하지 않는다
        "Mode 1",
        "",  # 빈 값은 판독 실패와 구별되지 않는다
        "   ",
        None,  # 프로퍼티가 답하지 않았다
        "1.5 Half",  # 정수가 아니다
        "-1 Neg",  # 슬롯은 1부터다
        "0 Zero",
        "7",  # 이름이 없다 — 슬롯만으로는 대조할 것이 없다
        "1\tTabbed",  # 구분자는 공백 하나로 규정한다
    ],
)
def test_parser_refuses_what_it_cannot_read_as_a_slot(mode_text):
    assert parse_console_mode_slot(mode_text) is None


def test_parser_is_not_vacuous():
    """거절만 하는 파서라면 위의 거절 표는 아무것도 증명하지 않는다."""
    assert parse_console_mode_slot("2 B") == 2


# ---------------------------------------------------------------------------
# the resolution branch — 켜지는 조건
# ---------------------------------------------------------------------------


def test_console_mode_resolves_what_the_library_read_cannot():
    records = _records()
    channels = records[0].channels
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(_console_fixtures(records, "2 B")),
        occupants=_occupants(records),
    )
    resolution = _resolution(plan)
    assert resolution.resolution == "resolved"
    assert resolution.console_mode == "B"
    assert resolution.resolved_by == "console_mode"
    assert resolution.channels == channels
    # 자리가 이미 같은 타입으로 차 있으므로 판정은 「이미 패치됨」이다 — 쓰기 0건.
    assert plan.runs == ()
    assert plan.write_count_planned == 0
    assert len(plan.skipped) == len(records)
    assert all(s.kind == "already_patched" for s in plan.skipped)


def test_without_the_branch_these_rows_are_unresolved():
    """대조군 — 콘솔에 아무것도 없으면 같은 입력이 여전히 못 풀린다.

    이게 없으면 위의 통과가 「원래 풀리던 것」인지 「이 갈래가 푼 것」인지
    구별되지 않는다.
    """
    records = _records()
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(records[0].channels),
        inventory=_inventory(()),
    )
    assert _resolution(plan).resolution == "unresolved"
    assert all(s.kind == "mode_unresolved" for s in plan.skipped)


def test_branch_does_not_intercept_a_library_read_that_already_decided():
    """능력만 더한다 — 기존에 풀리던 갈래를 가로채지 않는다."""
    records = _records()
    plan = _plan(
        records,
        inventory=_inventory(_console_fixtures(records, "2 B")),
        occupants=_occupants(records),
    )
    resolution = _resolution(plan)
    assert resolution.resolution == "resolved"
    assert resolution.resolved_by == "width_unique"


def test_an_explicit_override_still_wins():
    """감독이 직접 준 값이 콘솔 판독보다 우선이다."""
    records = _records()
    channels = records[0].channels
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(_console_fixtures(records, "2 B")),
        occupants=_occupants(records),
        mode_overrides={CSV_TYPE: "A"},
    )
    resolution = _resolution(plan)
    assert resolution.resolution == "resolved"
    assert resolution.console_mode == "A"
    assert resolution.resolved_by == "override"


# ---------------------------------------------------------------------------
# fail-open — 못 풀면 수정 전 동작 그대로
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode_text,why",
    [
        ("9 Z", "슬롯이 라이브러리 목록에 없다"),
        ("B", "앞 숫자가 없다"),
        ("", "빈 값"),
        (None, "프로퍼티가 답하지 않았다"),
        ("0 Zero", "슬롯 번호가 될 수 없는 값"),
    ],
)
def test_unresolved_survives_when_the_console_mode_cannot_decide(mode_text, why):
    records = _records()
    channels = records[0].channels
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(_console_fixtures(records, mode_text)),
        occupants=_occupants(records),
    )
    assert _resolution(plan).resolution == "unresolved", why
    assert all(s.kind == "mode_unresolved" for s in plan.skipped), why
    # 안내 문면이 살아 있어야 감독이 다음 행동을 안다.
    assert all("mode_overrides" in s.detail for s in plan.skipped), why


def test_a_different_type_at_that_address_is_not_evidence():
    records = _records()
    channels = records[0].channels
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(_console_fixtures(records, "2 B", fixture_type="Something Else")),
        occupants=_occupants(records, fixture_type="Something Else"),
    )
    assert _resolution(plan).resolution == "unresolved"


def test_the_same_type_at_a_different_address_is_not_evidence():
    records = _records()
    channels = records[0].channels
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(_console_fixtures(records, "2 B", universe_shift=5)),
    )
    assert _resolution(plan).resolution == "unresolved"


def test_a_slot_whose_width_was_never_measured_is_not_a_decision():
    """이름은 찾았는데 폭이 없으면 확정이 아니다 — override 갈래와 같은 규율.

    폭을 잃은 채 확정하면 점유 검사가 검사한 발자국과 실제로 쓰는 발자국이
    달라진다.

    모드를 **셋** 두는 것이 이 시험의 조건이다. 폭이 같은 둘(A·B)이 라이브러리
    판독을 모호하게 만들어 이 갈래까지 내려오게 하고, 콘솔은 폭이 없는 셋째(C)를
    가리킨다. 폭 없는 모드를 둘 중 하나로 두면 「폭이 같은 모드」가 하나로 줄어
    라이브러리 판독이 스스로 풀어 버리고, 이 갈래는 아예 안 켜진다.
    """
    records = _records()
    channels = records[0].channels
    modes = {
        CSV_TYPE: TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="A", width=channels, slot=1),
                ModeChoice(name="B", width=channels, slot=2),
                ModeChoice(name="C", width=None, slot=3),
            ),
        )
    }
    plan = _plan(
        records,
        mode_reads=modes,
        inventory=_inventory(_console_fixtures(records, "3 C")),
        occupants=_occupants(records),
    )
    assert _resolution(plan).resolution == "unresolved"


def test_an_incomplete_console_read_does_not_feed_the_branch():
    """부분 목록으로 결론을 내지 않는다 — 못 본 픽스처가 그 자리의 임자일 수 있다.

    미완전 판독은 이 갈래보다 앞에서 끊긴다: 계획이 아예 서지 않으므로 런도
    모드 해석도 없다. 그래서 「해석이 unresolved 다」가 아니라 「해석이 기록조차
    되지 않는다」가 옳은 단언이다 — 해석을 꺼내려 들면 없는 것을 꺼내려는
    시험이 된다.
    """
    records = _records()
    channels = records[0].channels
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(_console_fixtures(records, "2 B"), complete=False),
        occupants=_occupants(records),
    )
    assert plan.runs == ()
    assert plan.write_count_planned == 0
    assert plan.mode_resolutions == {}
    assert plan.console_read.get("reason")


def test_two_fixtures_disagreeing_at_the_same_address_decide_nothing():
    """같은 자리에 두 모드가 보고되면 어느 쪽도 증거가 아니다.

    앞것을 집으면 t334(중복 이름 조회가 앞것을 조용히 채택한다)와 같은 형태의
    조용한 오답을 이 갈래에 새로 만든다.
    """
    records = _records()
    channels = records[0].channels
    first = _console_fixtures(records, "1 A")
    second = _console_fixtures(records, "2 B")
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(first + second),
        occupants=_occupants(records),
    )
    assert _resolution(plan).resolution == "unresolved"

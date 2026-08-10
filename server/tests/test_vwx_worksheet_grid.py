"""Vectorworks 데이터베이스 워크시트(경로 B) 실물 구조 회귀 — 계수 요약행.

**근거**: 사용자가 제공한 실물 화면 2장(2026-08-08).

1. ``Create Report`` 대화상자 — ``Listing objects with record: Lighting Device``로
   ``Possible Columns``에서 컬럼을 골라 ``Worksheet Columns``로 옮긴다. 거기 표시되는
   이름이 ``Device Type`` · ``Inst Type`` · ``Wattage`` · ``Purpose`` · ``Position`` ·
   ``Unit Number`` · ``Color``다.
2. 생성된 워크시트 ``All LX Data`` — **1행 헤더 / 2행 컬럼별 계수 / 2.1~2.11 데이터**.
   계수행은 ``11 11 11 11 6 8 11``이었고 실제로 ``Unit Number``는 6행,
   ``Color``는 8행만 채워져 있었다.

그 2행이 이 파일이 지키는 것이다. **헤더와 폭이 같아** ``reader.py``의 소계 감지(폭
불일치)를 통과하고, 값이 전부 정수라 ``columns.py``의 최소 유효 레코드 조건도 통과한다.
걸러내지 않으면 ``instrument_type``이 ``"11"``이고 ``universe=11 address=11``인
**조명 한 대**가 패치 후보에 오른다 — 되돌릴 수 없는 콘솔 쓰기 경로다.

이전 픽스처 ``synthetic_path_b_worksheet_grid.csv``는 소계를 **파일 끝에 다른 폭으로**
두었기 때문에(``Totals,4``) 이 결함을 구조적으로 만들 수 없었다. 실물 화면이 없었다면
찾을 수 없었다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.vwx.address import resolve_all
from server.vwx.columns import (
    EXCLUDED_ROW_AGGREGATE,
    resolve_columns,
    resolve_header,
)
from server.vwx.reader import PATH_B, read
from server.vwx.rig import build_designed_rig

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vwx"
MA3_PATCH_GRID = FIXTURES / "vectorworks_worksheet_grid_ma3_patch.csv"

#: 실물 화면(이미지 2)에 찍힌 컬럼 이름 그대로.
SCREENSHOT_COLUMNS = (
    "Device Type",
    "Inst Type",
    "Wattage",
    "Purpose",
    "Position",
    "Unit Number",
    "Color",
    "Dimmer",
)

#: MA3 문서(``patch_add_fixtures.html``)가 픽스처 추가에 요구하는 것 -> 정규 필드.
#: FixtureType·Mode·Patch(universe+address)·ID 하나가 필수다.
MA3_REQUIRED_FIELDS = ("instrument_type", "mode", "universe", "address", "channel")


def _pipeline(path: Path):
    read_result = read(path.read_bytes())
    columns, column_failures, excluded = resolve_columns(list(read_result.records))
    resolved, address_failures = resolve_all(columns)
    rig = build_designed_rig(resolved, candidate_count=len(columns))
    return read_result, columns, column_failures, excluded, address_failures, rig


class TestTheRealWorksheetShape:
    """실물 워크시트 구조가 그대로 판독되는가."""

    def test_the_grid_is_recognised_as_path_b(self):
        """제목행이 앞서므로 헤더가 0행이 아니다 -> 경로 B."""
        result = read(MA3_PATCH_GRID.read_bytes())
        assert result.path_kind == PATH_B

    def test_every_column_the_format_asks_for_resolves(self):
        """포맷이 요구하는 컬럼이 하나라도 별칭표 밖이면 그 축을 통째로 잃는다."""
        result = read(MA3_PATCH_GRID.read_bytes())
        unresolved = [header for header in result.header if resolve_header(header) is None]
        assert unresolved == []

    def test_the_ma3_required_fields_are_all_present(self):
        """MA3 픽스처 추가 마법사가 값을 요구하는 칸이 전부 채워지는가."""
        _r, columns, _cf, _ex, _af, _rig = _pipeline(MA3_PATCH_GRID)
        assert columns
        for record in columns:
            missing = [f for f in MA3_REQUIRED_FIELDS if not record.fields.get(f, "").strip()]
            assert missing == [], f"행 {record.row_index}: {missing}"


class TestTheColumnCountRowIsNotAFixture:
    """계수 요약행이 조명으로 패치되지 않는가 — 이 파일의 본체."""

    def test_the_count_row_is_excluded_and_said_so(self):
        """조용히 버리지 않는다 — 의도적 제외로 보고한다(판독 실패가 아니다)."""
        _r, _c, failures, excluded, _af, _rig = _pipeline(MA3_PATCH_GRID)
        assert [e.kind for e in excluded] == [EXCLUDED_ROW_AGGREGATE]
        assert excluded[0].row == 0
        assert failures == []

    def test_the_drawing_holds_exactly_the_eleven_real_fixtures(self):
        """계수행을 세면 12대가 된다 — 실제 조명은 11대다."""
        _r, _c, _cf, _ex, _af, rig = _pipeline(MA3_PATCH_GRID)
        assert len(rig.fixtures) == 11

    def test_no_fixture_carries_a_bare_integer_as_its_type(self):
        """유령의 서명 — `instrument_type='11'`. 콘솔 라이브러리에 그런 타입은 없다."""
        _r, _c, _cf, _ex, _af, rig = _pipeline(MA3_PATCH_GRID)
        numeric = [f.instrument_type for f in rig.fixtures if str(f.instrument_type).isdigit()]
        assert numeric == []

    def test_the_count_row_would_otherwise_look_like_a_valid_record(self):
        """비공허성 — 이 행이 **왜** 위험한지 고정한다.

        폭이 헤더와 같고(리더의 소계 감지 통과) 타입·주소가 모두 채워져 보인다
        (최소 유효 레코드 조건 통과). 그래서 전용 판별이 필요하다.
        """
        result = read(MA3_PATCH_GRID.read_bytes())
        candidate = result.records[0]
        assert len(candidate) == len(result.header)
        assert candidate["Instrument Type"].isdigit()
        assert candidate["Universe"].isdigit()
        assert candidate["U Address"].isdigit()


class TestTheEqualityAndNotAHeuristic:
    """판별이 「정수처럼 보인다」가 아니라 「계수와 같다」임을 고정한다."""

    def test_an_all_integer_row_that_is_not_the_counts_is_kept(self):
        """[역방향 금지] 정수만 든 행이라고 버리지 않는다.

        계수와 **어긋나면** 통상 경로로 보낸다 — 조용히 삼키면 실제 조명을 잃는다.
        """
        rows = [
            {"Instrument Type": "7", "Universe": "9", "U Address": "3"},
            {"Instrument Type": "Robin MMX Spot", "Universe": "1", "U Address": "1"},
        ]
        records, failures, excluded = resolve_columns(rows)
        assert [e.kind for e in excluded] == []
        assert len(records) + len(failures) == 2

    def test_the_counts_row_is_caught_wherever_the_equality_holds(self):
        """등식이 성립하면 잡는다 — 위치가 아니라 성질이 판별한다."""
        rows = [
            {"Instrument Type": "2", "Universe": "2", "U Address": "1"},
            {"Instrument Type": "Robin MMX Spot", "Universe": "1", "U Address": "1"},
            {"Instrument Type": "Robin LEDBeam 350", "Universe": "1", "U Address": ""},
        ]
        _records, _failures, excluded = resolve_columns(rows)
        assert [e.kind for e in excluded] == [EXCLUDED_ROW_AGGREGATE]
        assert excluded[0].row == 0

    def test_a_single_number_row_is_not_enough_to_be_a_summary(self):
        """한 칸짜리 정수 행(`Totals,4` 류)은 이 판별의 대상이 아니다 — 폭이 다르면
        리더가, 같으면 최소 레코드 조건이 잡는다. 여기서 과잉 포획하지 않는다."""
        rows = [
            {"Instrument Type": "1", "Universe": "", "U Address": ""},
            {"Instrument Type": "Robin MMX Spot", "Universe": "1", "U Address": "1"},
        ]
        _records, _failures, excluded = resolve_columns(rows)
        assert [e.kind for e in excluded] == []


class TestTheScreenshotColumnSetCannotPatch:
    """실물 화면의 컬럼 선택으로는 패치가 **불가능**하다 — 사용자에게 알려야 할 사실."""

    @pytest.mark.parametrize("header", SCREENSHOT_COLUMNS)
    def test_each_screenshot_column_name_is_understood(self, header: str):
        """`Inst Type`이 여기 걸렸었다 — 별칭표에 없어 조명 종류를 통째로 잃었다.

        `Wattage`는 패치에 쓰이지 않으므로 `extra`로 보존되면 충분하다.
        """
        if header == "Wattage":
            pytest.skip("패치 비사용 — extra 보존 대상")
        assert resolve_header(header) is not None

    def test_that_column_set_has_no_dmx_address(self):
        """`Dimmer`는 주소 계열이 아니다 — 그래서 그 선택으로는 패치할 수 없다.

        MA3는 `universe.address`(예: `2.1`)를 요구한다
        (`patch_add_fixtures.html` / Assign DMX Address to Fixtures).
        """
        from server.vwx.columns import has_address_family

        assert has_address_family(list(SCREENSHOT_COLUMNS)) is False

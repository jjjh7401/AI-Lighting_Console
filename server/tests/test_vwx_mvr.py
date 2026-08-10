"""MVR 실물 판독 — 1단계 도면 입력의 두 번째 경로.

**실물 픽스처**: ``demoshow_grandma3.mvr`` (사용자 제공, 2026-08-08).
grandMA3가 내보낸 실제 MVR로 픽스처 176대 · GDTF 5종 · 3DS 지오메트리를 담는다.
합성이 아니다 — 이 파일이 ``ASSUMPTION-70``이 기다리던 「실물 파일 기반 종단 검증」의
근거다(경로 B 워크시트와는 다른 경로지만, 도면 측 입력을 실물로 검증한다는 목적은 같다).

이 파일이 지키는 것은 셋이다.

1. **NUL 후행 바이트** — MA3가 내보낸 XML은 ``\\x00``으로 끝난다. 표준 파서가 거부한다.
2. **주소 표기** — MVR ``Address``는 절대 DMX다. MA3 Patch는 ``universe.address``를
   요구한다(``patch_add_fixtures.html``). 가르는 산술이 틀리면 조명이 엉뚱한 데 선다.
3. **시트와의 등가** — MVR 경로와 사용자 제출 시트 경로가 **같은 rig**를 내야 한다.
   두 경로가 갈리면 어느 쪽이 맞는지 아무도 모른다.
"""

from __future__ import annotations

import dataclasses
import zipfile
from pathlib import Path

import pytest

from server.vwx import mvr
from server.vwx.address import resolve_all
from server.vwx.columns import resolve_columns, resolve_header
from server.vwx.reader import read as read_sheet
from server.vwx.rig import build_designed_rig

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vwx"
DEMOSHOW = FIXTURES / "demoshow_grandma3.mvr"

#: 실물 실측(2026-08-08). 값이 바뀌면 파일이 바뀐 것이다.
EXPECTED_FIXTURES = 176
EXPECTED_TYPE_MODES = 5
EXPECTED_UNIVERSES = 4


def _pipeline(result):
    columns, column_failures, excluded = resolve_columns(list(result.records))
    resolved, address_failures = resolve_all(columns)
    rig = build_designed_rig(resolved, candidate_count=len(columns))
    return rig, column_failures, excluded, address_failures


def _signature(rig) -> list[tuple]:
    """패치에 실제로 쓰이는 축만 뽑은 비교 지문."""
    rows = []
    for fixture in rig.fixtures:
        d = dataclasses.asdict(fixture)
        rows.append(
            (
                d["instrument_type"],
                d["mode"],
                d["universe"],
                d["address"],
                d["footprint"],
                d["channel"],
            )
        )
    return sorted(rows)


@pytest.fixture(scope="module")
def demoshow():
    return mvr.read(DEMOSHOW.read_bytes())


class TestTheRealContainer:
    """실물 컨테이너가 그대로 열리는가."""

    def test_the_file_is_registered_and_is_a_zip(self):
        assert DEMOSHOW.exists()
        assert zipfile.is_zipfile(DEMOSHOW)

    def test_the_scene_xml_ends_with_a_nul_byte(self):
        """이 파일의 존재 이유 — 합성 픽스처는 이렇게 생기지 않는다.

        벗기지 않으면 ``ET.fromstring``이 ``not well-formed``로 거부한다.
        """
        with zipfile.ZipFile(DEMOSHOW) as archive:
            raw = archive.read(mvr.SCENE_ENTRY)
        assert raw.endswith(b"\x00")

    def test_every_bundled_gdtf_also_ends_with_a_nul_byte(self):
        """형제 표면 — 장면 XML만 벗기고 GDTF를 놓치면 채널 수를 통째로 잃는다."""
        with zipfile.ZipFile(DEMOSHOW) as archive:
            specs = [n for n in archive.namelist() if n.endswith(".gdtf")]
            assert specs
            for spec in specs:
                with archive.open(spec) as handle:
                    nested = zipfile.ZipFile(__import__("io").BytesIO(handle.read()))
                assert nested.read("description.xml").endswith(b"\x00")

    def test_reading_it_reports_no_failure(self, demoshow):
        assert demoshow.path_kind == mvr.PATH_MVR
        assert demoshow.read_failures == ()

    def test_it_holds_the_measured_number_of_fixtures(self, demoshow):
        assert len(demoshow.records) == EXPECTED_FIXTURES


class TestFixtureTypesComeFromTheBundledFiles:
    """타입을 이름으로 추측하지 않는다 — 파일이 동봉돼 있다."""

    def test_every_referenced_gdtf_is_in_the_container(self, demoshow):
        assert not [f for f in demoshow.read_failures if f.kind == mvr.READ_FAILURE_GDTF_MISSING]

    def test_the_measured_type_and_mode_count(self, demoshow):
        combos = {(r["GDTF Fixture"], r["GDTF Fixture Mode"]) for r in demoshow.records}
        assert len(combos) == EXPECTED_TYPE_MODES

    def test_the_footprint_is_read_from_the_gdtf_and_not_guessed(self, demoshow):
        """채널 수는 GDTF ``DMXChannel`` 오프셋의 최댓값이다.

        ``MAC Encore Performance CLD`` / ``Basic`` = 38ch. 그래서 이 쇼의 Spot들이
        1 -> 39 -> 77로 정확히 38씩 띄어 서 있다.
        """
        encore = [
            r for r in demoshow.records if r["Instrument Type"] == "MAC Encore Performance CLD"
        ]
        assert encore
        assert {r["DMX Footprint"] for r in encore} == {"38"}
        spots = sorted(int(r["Absolute Address"]) for r in encore)
        assert spots[:3] == [1, 39, 77]

    def test_a_container_without_the_gdtf_says_so(self):
        """[비공허] GDTF가 빠지면 조용히 넘어가지 않는다."""
        import io

        buffer = io.BytesIO()
        with zipfile.ZipFile(DEMOSHOW) as source, zipfile.ZipFile(buffer, "w") as target:
            for name in source.namelist():
                if name.endswith(".gdtf"):
                    continue
                target.writestr(name, source.read(name))
        result = mvr.read(buffer.getvalue())
        kinds = {f.kind for f in result.read_failures}
        assert mvr.READ_FAILURE_GDTF_MISSING in kinds
        assert len(result.records) == EXPECTED_FIXTURES
        assert {r["DMX Footprint"] for r in result.records} == {""}


class TestTheAddressSplit:
    """절대주소를 ``universe.address``로 가르는 산술."""

    @pytest.mark.parametrize(
        ("absolute", "universe", "address"),
        [(1, 1, 1), (512, 1, 512), (513, 2, 1), (1024, 2, 512), (1025, 3, 1), (1834, 4, 298)],
    )
    def test_the_boundaries(self, absolute: int, universe: int, address: int):
        """경계가 이 산술의 전부다 — 512/513이 어긋나면 유니버스 하나가 통째로 밀린다."""
        assert mvr._split_absolute(absolute) == (universe, address)

    def test_every_fixture_lands_inside_a_universe(self, demoshow):
        for record in demoshow.records:
            assert 1 <= int(record["U Address"]) <= mvr.UNIVERSE_WIDTH

    def test_the_measured_universe_spread(self, demoshow):
        universes = {int(r["Universe"]) for r in demoshow.records}
        assert len(universes) == EXPECTED_UNIVERSES

    def test_a_non_numeric_address_is_reported_and_not_guessed(self):
        """[비공허] 주소를 못 읽으면 0으로 때려넣지 않는다."""
        import io

        with zipfile.ZipFile(DEMOSHOW) as source:
            scene = source.read(mvr.SCENE_ENTRY).rstrip(b"\x00").decode("utf-8")
            names = source.namelist()
            blobs = {n: source.read(n) for n in names}
        broken = scene.replace("<Address break=", "<Address x-break=", 1).replace(
            ">1</Address>", ">nope</Address>", 1
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as target:
            for name in names:
                target.writestr(
                    name, broken.encode("utf-8") if name == mvr.SCENE_ENTRY else blobs[name]
                )
        result = mvr.read(buffer.getvalue())
        assert any(f.kind == mvr.READ_FAILURE_ADDRESS_UNREADABLE for f in result.read_failures)


class TestTheWholePipelineAcceptsIt:
    """워크시트 경로와 **같은 하류**를 탄다 — 파이프라인을 두 벌 만들지 않는다."""

    def test_every_header_it_emits_is_understood_downstream(self):
        unresolved = [h for h in mvr.MVR_HEADERS if resolve_header(h) is None]
        assert unresolved == []

    def test_all_fixtures_survive_to_the_designed_rig(self, demoshow):
        rig, column_failures, excluded, address_failures = _pipeline(demoshow)
        assert len(rig.fixtures) == EXPECTED_FIXTURES
        assert column_failures == []
        assert excluded == []
        assert address_failures == []

    def test_nothing_collides_in_the_drawing(self, demoshow):
        """실물이 정합하다는 사실 자체를 고정한다 — 겹침이 생기면 파일이 바뀐 것이다."""
        rig, _cf, _ex, _af = _pipeline(demoshow)
        assert rig.design_overlaps == ()
        assert rig.join_key_conflicts == ()


class TestTheSheetCarriesTheSameThing:
    """사용자가 MVR 없이 시트로 제출해도 **같은 rig**가 나와야 한다."""

    @pytest.mark.parametrize("suffix", ["csv", "xlsx"])
    def test_the_generated_sheet_reproduces_the_mvr_exactly(self, demoshow, tmp_path, suffix):
        from tools.make_patch_template import HEADERS, rows_from_mvr, write_csv, write_xlsx

        rows = rows_from_mvr(DEMOSHOW)
        assert len(rows) == EXPECTED_FIXTURES
        target = tmp_path / f"sheet.{suffix}"
        (write_csv if suffix == "csv" else write_xlsx)(target, rows)

        sheet_rig, _cf, _ex, _af = _pipeline(read_sheet(target.read_bytes()))
        mvr_rig, _cf2, _ex2, _af2 = _pipeline(demoshow)
        assert _signature(sheet_rig) == _signature(mvr_rig)
        assert set(HEADERS) <= set(mvr.MVR_HEADERS)

    def test_the_template_columns_are_all_understood(self):
        """템플릿이 요구하는 컬럼 중 하나라도 해석 불가면 사용자가 채워도 소용없다."""
        from tools.make_patch_template import HEADERS

        assert [h for h in HEADERS if resolve_header(h) is None] == []

    def test_the_template_itself_reads_back(self):
        """배포하는 템플릿이 우리 파이프라인을 통과하는가 — 안 그러면 배포 사고다."""
        template = Path(__file__).resolve().parents[2] / "docs" / "templates"
        for name in ("patch_template.csv", "patch_template.xlsx"):
            path = template / name
            if not path.exists():
                pytest.skip(f"{name} 미생성 — tools/make_patch_template.py로 만든다")
            rig, failures, _ex, address_failures = _pipeline(read_sheet(path.read_bytes()))
            assert failures == []
            assert address_failures == []
            assert len(rig.fixtures) == 3

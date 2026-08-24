"""SPEC-COPILOT-FILEARG-001 M1 — 판별기 + 레지스트리.

AC-FILEARG-002~006 · 009(순서 구간) · 018~020 · 022~029를 소유한다.
AC-021(안전판)은 조건부이며 위임 술어가 실물 변형을 흡수하면 발동하지 않는다.
AC-030(경계 게이트)은 커밋 뒤 트리 대조로 확인하므로 여기서 재지 않는다.
"""

from __future__ import annotations

import io
import pathlib
import zipfile

import pytest

from server.lxseq.parser import CANONICAL_COLUMNS, MissingColumnsError, parse_patch_csv
from server.sheets.registry import (
    CONFIG_ERROR_NO_TARGET_TOOL,
    HANDLER_TAG_SESSION_METHOD,
    HANDLER_TAG_TOOL,
    OUTCOME_AMBIGUOUS,
    OUTCOME_RESOLVED,
    OUTCOME_UNKNOWN,
    OUTCOMES,
    REEXPORT_HINT,
    REGISTRY,
    DelegatedPredicate,
    Discrimination,
    ExactColumns,
    Handler,
    RequiredForbidden,
    SheetKindRow,
    discriminate,
    read_header,
    vectorworks_identity,
)
from server.vwx.mvr import SCENE_ENTRY

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
VWX_DIR = FIXTURES / "vwx"
PATCH_CSV = FIXTURES / "lxseq" / "LXSEQ_RIG_01_ShowBase_r3.patch.csv"

#: vwx/ 디렉터리 12개 항목 중 업로드 페이로드가 아닌 둘(research.md §10 (e)).
NON_PAYLOAD = ("README.md", "stage1_contract_snapshot.json")

#: AC-FILEARG-028 탭 축 날조 대조군 — 장바구니 목록. VW 어휘가 하나도 없다.
FABRICATED_TAB = b"milk\t2\t3000\neggs\t1\t5000\nbread\t3\t2500\n"
FABRICATED_COMMA = b"milk,2,3000\neggs,1,5000\nbread,3,2500\n"


#: zip 갈래 대조군 — 코퍼스에 `.xlsx` 표본이 **0개**라 형상만 인메모리로 세운다.
#: 픽스처가 아니다(실물을 날조하지 않는다) — `SCENE_ENTRY` 유무만 다른 최소 아카이브다.
MVR_SHAPED_ENTRIES = (SCENE_ENTRY, "Resources/model.3ds")
XLSX_SHAPED_ENTRIES = ("[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml")


def _zip_bytes(names: tuple[str, ...]) -> bytes:
    """이름 목록만으로 최소 zip을 만든다 — 항목 내용은 판별의 입력이 아니다."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, "")
    return buffer.getvalue()


def _csv(header: list[str]) -> bytes:
    return (",".join(header) + "\n").encode("utf-8")


def _payloads() -> list[pathlib.Path]:
    """업로드 페이로드 10개.

    `VWX_DIR` 를 직접 훑지 않고 `FIXTURES` 를 재귀로 훑어 `vwx/` 하위만 고른다.
    저장소의 R24 가드(`test_autopatch_contract.py`)가 **경로 꼬리가 `vwx`인 모든
    순회**를 vwx 모듈 순회로 읽어 등기를 요구하는데, 등기처는 A의 경계
    (REQ-FILEARG-024) 밖이다. 여기서 세는 것은 vwx **모듈**이 아니라 테스트
    **픽스처**이므로 그 가드가 지키려는 성질(모듈 순회의 정의는 하나)은 건드리지
    않는다.
    """
    return sorted(
        path
        for path in FIXTURES.rglob("*")
        if path.parent.name == "vwx" and path.is_file() and path.name not in NON_PAYLOAD
    )


class TestPatchSignaturePredicate:
    def test_signature_matches_the_canonical_nine_columns(self):
        result = discriminate(_csv(list(CANONICAL_COLUMNS)))
        assert result.matched == ("patch",)

    def test_signature_tolerates_columns_outside_the_canonical_set(self):
        header = [*CANONICAL_COLUMNS, "Note", "Owner"]
        assert discriminate(_csv(header)).matched == ("patch",)

    def test_signature_ignores_column_order(self):
        header = list(reversed(CANONICAL_COLUMNS))
        assert discriminate(_csv(header)).matched == ("patch",)

    def test_signature_ignores_case_inner_space_and_bom(self):
        header = ["f i d", "GROUP", "fixturetype", "Mode ", " Ch", "universe"]
        header += ["ADDRESS", "addr range", "POSITION"]
        raw = chr(0xFEFF) + ",".join(header) + "\n"
        assert discriminate(raw.encode("utf-8")).matched == ("patch",)

    def test_signature_rejects_when_one_canonical_column_is_missing(self):
        header = [name for name in CANONICAL_COLUMNS if name != "AddrRange"]
        result = discriminate(_csv(header))
        assert "patch" not in result.matched

    def test_signature_never_raises_missing_columns_error(self):
        header = [name for name in CANONICAL_COLUMNS if name != "Universe"]
        try:
            discriminate(_csv(header))
        except MissingColumnsError as error:  # pragma: no cover - 회귀 시에만 발화
            pytest.fail(f"판별이 예외를 제어 흐름으로 썼다: {error}")


def _injected_superset_table() -> tuple[SheetKindRow, ...]:
    """한쪽이 다른 쪽의 상위 집합인 서명 둘 — 등록 행 수와 무관한 시험용 표."""
    return (
        SheetKindRow(
            kind="narrow",
            predicate=RequiredForbidden(required_columns=("Alpha", "Beta")),
            handler=Handler(HANDLER_TAG_TOOL, "import_lxseq_patch"),
        ),
        SheetKindRow(
            kind="wide",
            predicate=RequiredForbidden(required_columns=("Alpha", "Beta", "Gamma")),
            handler=Handler(HANDLER_TAG_TOOL, "import_lxseq_patch"),
        ),
    )


class TestFullSweepCount:
    def test_superset_header_matches_both_injected_signatures(self):
        result = discriminate(_csv(["Alpha", "Beta", "Gamma"]), registry=_injected_superset_table())
        assert set(result.matched) == {"narrow", "wide"}

    def test_superset_header_yields_count_two(self):
        result = discriminate(_csv(["Alpha", "Beta", "Gamma"]), registry=_injected_superset_table())
        assert result.count == 2

    def test_count_always_equals_the_length_of_matched(self):
        for payload in (_csv(list(CANONICAL_COLUMNS)), FABRICATED_TAB, b""):
            result = discriminate(payload)
            assert result.count == len(result.matched)


class TestAmbiguousSheetKind:
    def test_ambiguous_outcome_when_two_signatures_match(self):
        result = discriminate(_csv(["Alpha", "Beta", "Gamma"]), registry=_injected_superset_table())
        assert result.outcome == OUTCOME_AMBIGUOUS

    def test_ambiguous_names_every_matched_kind(self):
        result = discriminate(_csv(["Alpha", "Beta", "Gamma"]), registry=_injected_superset_table())
        assert sorted(result.matched) == ["narrow", "wide"]


class TestUnknownSheetKind:
    def test_unknown_sheet_kind_when_no_signature_matches(self):
        assert discriminate(_csv(["Nope", "Nothing"])).outcome == OUTCOME_UNKNOWN

    def test_unknown_leaves_matched_empty(self):
        assert discriminate(_csv(["Nope", "Nothing"])).matched == ()

    def test_unknown_report_carries_the_header_as_written(self):
        result = discriminate(_csv(["Nope", " Nothing "]))
        assert result.header_read == ("Nope", " Nothing ")

    def test_unknown_report_lists_every_registered_signature(self):
        result = discriminate(_csv(["Nope", "Nothing"]))
        assert [kind for kind, _ in result.signatures] == ["patch", "vectorworks"]
        assert all(description for _, description in result.signatures)

    def test_unknown_records_the_filename_hint_without_branching_on_it(self):
        header = _csv(["Nope", "Nothing"])
        misleading = discriminate(header, filename_hint="LXSEQ_RIG_01.patch.csv")
        assert misleading.filename_hint == "LXSEQ_RIG_01.patch.csv"
        assert misleading.outcome == OUTCOME_UNKNOWN


class TestRegistryTable:
    def test_registry_holds_exactly_two_filled_rows(self):
        assert [row.kind for row in REGISTRY] == ["patch", "vectorworks"]

    def test_registry_patch_row_references_canonical_columns_by_identity(self):
        patch = next(row for row in REGISTRY if row.kind == "patch")
        assert patch.predicate.required_columns is CANONICAL_COLUMNS

    def test_registry_vectorworks_row_delegates_rather_than_copying(self):
        vectorworks = next(row for row in REGISTRY if row.kind == "vectorworks")
        assert isinstance(vectorworks.predicate, DelegatedPredicate)
        assert vectorworks.predicate.excluded_by_other_rows is True

    def test_registry_handlers_carry_their_tag(self):
        tags = {row.kind: (row.handler.kind_tag, row.handler.name) for row in REGISTRY}
        assert tags == {
            "patch": (HANDLER_TAG_TOOL, "import_lxseq_patch"),
            "vectorworks": (HANDLER_TAG_SESSION_METHOD, "upload_vectorworks_export"),
        }

    def test_registry_patch_row_carries_the_passthrough_whitelist(self):
        patch = next(row for row in REGISTRY if row.kind == "patch")
        assert patch.passthrough_args == (
            "action",
            "name_prefix_mode",
            "only_fids",
            "mode_overrides",
        )

    def test_registry_has_no_row_reserved_for_a_later_spec(self):
        assert len(REGISTRY) == 2


class TestDiscriminationOrder:
    def test_no_trial_parse_during_discrimination(self, monkeypatch):
        calls: list[str] = []

        def _spy(text: str):
            calls.append(text[:16])
            raise AssertionError("판별 중 실제 파서가 불렸다")

        monkeypatch.setattr("server.lxseq.parser.parse_patch_csv", _spy)
        result = discriminate(PATCH_CSV.read_bytes())
        assert calls == []
        assert result.matched == ("patch",)

    def test_no_trial_parse_even_when_the_header_is_broken(self, monkeypatch):
        monkeypatch.setattr(
            "server.lxseq.parser.parse_patch_csv",
            lambda text: pytest.fail("판별 중 실제 파서가 불렸다"),
        )
        assert discriminate(_csv(["Nope"])).outcome == OUTCOME_UNKNOWN

    def test_parse_once_after_the_kind_is_resolved(self):
        data = PATCH_CSV.read_bytes()
        result = discriminate(data)
        assert result.outcome == OUTCOME_RESOLVED
        parsed = parse_patch_csv(data.decode("utf-8-sig"))
        assert len(parsed.records) > 0


SYNTHETIC_HEADERS = {
    "dim": ["ID", "Name", "Level", "Purpose"],
    "col": ["ID", "Name", "Value", "Purpose"],
    "bm": ["ID", "Name", "TargetGroup", "Value"],
    "pos": ["ID", "StageMeaning", "TargetGroup", "RecordGuide"],
}


def _synthetic_extended_table() -> tuple[SheetKindRow, ...]:
    """확장 형식(정확 열 집합 + 포함·배제 쌍)으로 쓴 합성 서명 넷."""
    tool = Handler(HANDLER_TAG_TOOL, "import_lxseq_patch")
    return (
        SheetKindRow("dim", ExactColumns(("ID", "Name", "Level", "Purpose")), tool),
        SheetKindRow(
            "col",
            RequiredForbidden(
                required_columns=("ID", "Name", "Value"),
                forbidden_columns=("TargetGroup",),
            ),
            tool,
        ),
        SheetKindRow(
            "bm",
            RequiredForbidden(required_columns=("ID", "Name", "TargetGroup", "Value")),
            tool,
        ),
        SheetKindRow(
            "pos",
            ExactColumns(("ID", "StageMeaning", "TargetGroup", "RecordGuide")),
            tool,
        ),
    )


def _synthetic_inclusion_only_table() -> tuple[SheetKindRow, ...]:
    """비공허성 대조군 — 같은 넷을 포함 검사만으로 쓰면 갈리지 않는다."""
    tool = Handler(HANDLER_TAG_TOOL, "import_lxseq_patch")
    return (
        SheetKindRow("dim", RequiredForbidden(("ID", "Name", "Level", "Purpose")), tool),
        SheetKindRow("col", RequiredForbidden(("ID", "Name", "Value")), tool),
        SheetKindRow("bm", RequiredForbidden(("ID", "Name", "TargetGroup", "Value")), tool),
        SheetKindRow("pos", RequiredForbidden(("ID", "StageMeaning", "TargetGroup")), tool),
    )


class TestFormatSufficiency:
    @pytest.mark.parametrize("kind", sorted(SYNTHETIC_HEADERS))
    def test_format_sufficiency_each_header_matches_exactly_one_kind(self, kind):
        result = discriminate(_csv(SYNTHETIC_HEADERS[kind]), registry=_synthetic_extended_table())
        assert (result.count, result.matched) == (1, (kind,))

    @pytest.mark.parametrize("kind", sorted(SYNTHETIC_HEADERS))
    def test_format_sufficiency_no_header_falls_to_ambiguous(self, kind):
        result = discriminate(_csv(SYNTHETIC_HEADERS[kind]), registry=_synthetic_extended_table())
        assert result.outcome == OUTCOME_RESOLVED

    def test_format_sufficiency_control_inclusion_only_collides(self):
        """비공허성 — 포함 검사만으로 쓰면 bm 헤더가 col 서명에도 맞는다."""
        result = discriminate(
            _csv(SYNTHETIC_HEADERS["bm"]), registry=_synthetic_inclusion_only_table()
        )
        assert result.count == 2
        assert set(result.matched) == {"bm", "col"}


CROSS_CLASSIFY_EXPECTED = {
    "demoshow_grandma3.mvr": "vectorworks",
    "drop_dk_rigging_not_a_vectorworks_export.csv": None,
    "synthetic_path_b_worksheet_grid.csv": "vectorworks",
    "vectorworks_export_instrument_data_no_header.txt": None,
    "vectorworks_export_sample_with_data.csv": "vectorworks",
    "vectorworks_worksheet_absolute_address_only.csv": "vectorworks",
    "vectorworks_worksheet_grid_ma3_patch.csv": "vectorworks",
    "vectorworks_worksheet_multisystem_full.csv": "vectorworks",
    "vwx_worksheet_grid_from_screenshot.csv": "vectorworks",
    "vwx_worksheet_grid_patch_ready.csv": "vectorworks",
}


class TestCrossClassifyRealFixtures:
    def test_cross_classify_covers_exactly_the_ten_payloads(self):
        assert sorted(p.name for p in _payloads()) == sorted(CROSS_CLASSIFY_EXPECTED)

    def test_cross_classify_patch_fixture_is_patch(self):
        result = discriminate(PATCH_CSV.read_bytes(), filename_hint=PATCH_CSV.name)
        assert (result.outcome, result.matched) == (OUTCOME_RESOLVED, ("patch",))

    def test_cross_classify_vectorworks_sample_is_vectorworks(self):
        data = (VWX_DIR / "vectorworks_export_sample_with_data.csv").read_bytes()
        assert discriminate(data).matched == ("vectorworks",)

    @pytest.mark.parametrize("name", sorted(CROSS_CLASSIFY_EXPECTED))
    def test_cross_classify_every_payload(self, name):
        expected = CROSS_CLASSIFY_EXPECTED[name]
        result = discriminate((VWX_DIR / name).read_bytes(), filename_hint=name)
        if expected is None:
            assert result.outcome == OUTCOME_UNKNOWN
        else:
            assert (result.outcome, result.matched) == (OUTCOME_RESOLVED, (expected,))


class TestMvrAndHeaderless:
    def test_mvr_is_not_unknown_sheet_kind(self):
        data = (VWX_DIR / "demoshow_grandma3.mvr").read_bytes()
        assert discriminate(data).outcome != OUTCOME_UNKNOWN

    def test_mvr_resolves_to_vectorworks_with_a_session_handler(self):
        data = (VWX_DIR / "demoshow_grandma3.mvr").read_bytes()
        result = discriminate(data)
        assert result.matched == ("vectorworks",)
        row = next(r for r in REGISTRY if r.kind == "vectorworks")
        assert row.handler == Handler(HANDLER_TAG_SESSION_METHOD, "upload_vectorworks_export")

    def test_mvr_is_the_expected_zip_with_the_scene_entry(self):
        data = (VWX_DIR / "demoshow_grandma3.mvr").read_bytes()
        assert len(data) == 315155
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert SCENE_ENTRY in archive.namelist()

    def test_mvr_is_never_decoded_as_csv_text(self, monkeypatch):
        def _forbidden(*args, **kwargs):  # pragma: no cover - 회귀 시에만 발화
            raise AssertionError(".mvr 바이트를 CSV 텍스트로 해석하려 했다")

        monkeypatch.setattr("server.sheets.registry.decode_bytes", _forbidden)
        data = (VWX_DIR / "demoshow_grandma3.mvr").read_bytes()
        assert discriminate(data).matched == ("vectorworks",)

    def test_mvr_never_enters_either_openpyxl_path(self, monkeypatch):
        def _forbidden(*args, **kwargs):  # pragma: no cover - 회귀 시에만 발화
            raise AssertionError("판독기 read()가 불려 xlsx 경로가 열렸다")

        monkeypatch.setattr("server.vwx.reader.read", _forbidden)
        data = (VWX_DIR / "demoshow_grandma3.mvr").read_bytes()
        result = discriminate(data)
        assert result.matched == ("vectorworks",)
        assert "unapproved_dependency" not in repr(result)

    def test_headerless_txt_is_unknown_sheet_kind(self):
        data = (VWX_DIR / "vectorworks_export_instrument_data_no_header.txt").read_bytes()
        assert discriminate(data).outcome == OUTCOME_UNKNOWN


class TestZipShapes:
    """zip 갈래는 **둘로 갈라진다** — 두 형상 모두 신원 참이다.

    `REQ-FILEARG-019`는 `.xlsx`의 계속 동작을 약속하는데, `SCENE_ENTRY`만 묻는
    술어는 `SCENE_ENTRY` 없는 zip(=진짜 `.xlsx`)을 거짓으로 읽어
    `unknown_sheet_kind`로 떨어뜨렸다(§E.2 G-2). 리드 재정: **Vectorworks가
    내보낼 수 있는 형식이면 신원은 참**이고, *어느* zip인가는 신원이 아니라
    뒷단이 가른다.

    **코퍼스에 `.xlsx` 표본은 0개다.** 여기 쓰는 zip은 픽스처가 아니라 인메모리
    형상 대조군이며, 실물 `.xlsx` 왕복은 여기서 검증하지 않는다.
    """

    def test_zip_with_the_scene_entry_is_identity_true(self):
        """갈래 ① `.mvr` 형상 — 재정 전후로 참이 유지되는 쪽이다."""
        assert vectorworks_identity(_zip_bytes(MVR_SHAPED_ENTRIES)) is True

    def test_zip_without_the_scene_entry_is_identity_true(self):
        """갈래 ② `.xlsx` 형상 — 재정으로 **새로 참이 되는** 쪽이다."""
        assert vectorworks_identity(_zip_bytes(XLSX_SHAPED_ENTRIES)) is True

    def test_zip_without_the_scene_entry_resolves_to_vectorworks(self):
        result = discriminate(_zip_bytes(XLSX_SHAPED_ENTRIES), filename_hint="book.xlsx")
        assert (result.outcome, result.matched) == (OUTCOME_RESOLVED, ("vectorworks",))

    def test_zip_magic_that_is_not_a_readable_archive_is_identity_false(self):
        """재정이 **넓히지 않은** 경계 — 판독 불가 아카이브는 거짓 그대로다.

        이 단언이 없으면 `PK`이면 무조건 참을 내는 구현도 위 둘을 통과시킨다.
        이 시험이 두 갈래 참을 **판별력 있는** 주장으로 만든다.
        """
        assert vectorworks_identity(b"PK\x03\x04" + b"\x00" * 64) is False

    def test_the_two_zip_shapes_are_genuinely_different_inputs(self):
        """비공허성 — 두 형상이 실제로 `SCENE_ENTRY` 유무로 갈리는가."""
        with zipfile.ZipFile(io.BytesIO(_zip_bytes(MVR_SHAPED_ENTRIES))) as archive:
            assert SCENE_ENTRY in archive.namelist()
        with zipfile.ZipFile(io.BytesIO(_zip_bytes(XLSX_SHAPED_ENTRIES))) as archive:
            assert SCENE_ENTRY not in archive.namelist()

    def test_neither_zip_shape_enters_the_reader_during_discrimination(self, monkeypatch):
        """신원 단계에서는 어느 zip도 판독기에 닿지 않는다 — openpyxl은 뒷단 몫이다."""

        def _forbidden(*args, **kwargs):  # pragma: no cover - 회귀 시에만 발화
            raise AssertionError("판별 중 판독기가 불렸다")

        monkeypatch.setattr("server.vwx.reader.read", _forbidden)
        monkeypatch.setattr("server.sheets.registry.decode_bytes", _forbidden)
        for entries in (MVR_SHAPED_ENTRIES, XLSX_SHAPED_ENTRIES):
            assert discriminate(_zip_bytes(entries)).matched == ("vectorworks",)


def _broken_handler_table() -> tuple[SheetKindRow, ...]:
    healthy = SheetKindRow(
        kind="patch",
        predicate=RequiredForbidden(required_columns=CANONICAL_COLUMNS),
        handler=Handler(HANDLER_TAG_TOOL, "import_lxseq_patch"),
    )
    return (
        healthy,
        SheetKindRow(
            "ghost_tool",
            RequiredForbidden(required_columns=("FID",)),
            Handler(HANDLER_TAG_TOOL, "no_such_tool_anywhere"),
        ),
        SheetKindRow(
            "ghost_method",
            RequiredForbidden(required_columns=("FID",)),
            Handler(HANDLER_TAG_SESSION_METHOD, "no_such_session_method"),
        ),
        SheetKindRow(
            "untagged",
            RequiredForbidden(required_columns=("FID",)),
            "import_lxseq_patch",
        ),
    )


class TestHandlerResolution:
    def test_handler_resolution_drops_unresolvable_rows_from_the_count(self):
        result = discriminate(_csv(list(CANONICAL_COLUMNS)), registry=_broken_handler_table())
        assert result.matched == ("patch",)
        assert result.count == 1

    def test_handler_resolution_reports_every_broken_row(self):
        result = discriminate(_csv(list(CANONICAL_COLUMNS)), registry=_broken_handler_table())
        assert sorted(e.kind for e in result.config_errors) == [
            "ghost_method",
            "ghost_tool",
            "untagged",
        ]

    def test_handler_resolution_reports_the_declared_error_reason(self):
        result = discriminate(_csv(list(CANONICAL_COLUMNS)), registry=_broken_handler_table())
        assert {e.reason for e in result.config_errors} == {CONFIG_ERROR_NO_TARGET_TOOL}

    def test_handler_resolution_surfaces_errors_at_discrimination_time(self):
        result = discriminate(FABRICATED_COMMA, registry=_broken_handler_table())
        assert result.config_errors, "판별 결과가 설정 오류를 싣고 올라오지 않았다"

    def test_handler_resolution_never_excludes_todays_two_rows(self):
        result = discriminate(PATCH_CSV.read_bytes())
        assert result.config_errors == ()
        assert discriminate((VWX_DIR / "demoshow_grandma3.mvr").read_bytes()).config_errors == ()


class TestNoImplicitElse:
    @pytest.mark.parametrize(
        "payload",
        [
            b"",
            b"\x00\x01\x02",
            FABRICATED_TAB,
            FABRICATED_COMMA,
            b"only,one,row\n",
        ],
    )
    def test_no_implicit_else_outcome_is_always_a_declared_value(self, payload):
        assert discriminate(payload).outcome in OUTCOMES

    def test_no_implicit_else_resolved_kind_always_comes_from_a_declared_row(self):
        declared = {row.kind for row in REGISTRY}
        for path in [PATCH_CSV, *_payloads()]:
            result = discriminate(path.read_bytes())
            assert set(result.matched) <= declared

    def test_no_implicit_else_zero_matches_is_the_declared_unknown_outcome(self):
        result = discriminate(FABRICATED_COMMA)
        assert (result.matched, result.outcome) == ((), OUTCOME_UNKNOWN)


class TestPatchIdentity:
    def test_patch_identity_is_a_single_match(self):
        result = discriminate(PATCH_CSV.read_bytes())
        assert (result.count, result.matched) == (1, ("patch",))

    def test_patch_identity_excludes_vectorworks(self):
        assert "vectorworks" not in discriminate(PATCH_CSV.read_bytes()).matched

    def test_patch_identity_needs_the_exclusion_clause_to_hold(self):
        """배제 절이 무엇을 막는지 기계로 고정한다 — 원시 신원 술어는 참이다."""
        assert vectorworks_identity(PATCH_CSV.read_bytes()) is True


class TestNegativeControl:
    def test_negative_control_is_rejected(self):
        data = (VWX_DIR / "drop_dk_rigging_not_a_vectorworks_export.csv").read_bytes()
        assert discriminate(data).outcome == OUTCOME_UNKNOWN

    def test_negative_control_fails_the_identity_predicate(self):
        data = (VWX_DIR / "drop_dk_rigging_not_a_vectorworks_export.csv").read_bytes()
        assert vectorworks_identity(data) is False


class TestAliasThreshold:
    def test_alias_threshold_single_alias_is_not_vectorworks(self):
        from server.vwx.columns import match_count

        header = ["Position", "장바구니", "메모"]
        assert match_count(header) == 1
        assert vectorworks_identity(_csv(header)) is False

    def test_alias_threshold_headerless_txt_scores_below_the_floor(self):
        from server.vwx.reader import _best_header_candidate, _choose_delimiter, decode_bytes

        data = (VWX_DIR / "vectorworks_export_instrument_data_no_header.txt").read_bytes()
        text, _encoding = decode_bytes(data)
        _delimiter, rows, _index, _score = _choose_delimiter(text)
        index, score = _best_header_candidate(rows)
        assert (index, score) == (-1, 1)


class TestFabricatedControl:
    def test_fabricated_control_tab_axis_is_not_vectorworks(self):
        result = discriminate(FABRICATED_TAB)
        assert result.outcome == OUTCOME_UNKNOWN
        assert "vectorworks" not in result.matched

    def test_fabricated_control_comma_axis_is_not_vectorworks(self):
        result = discriminate(FABRICATED_COMMA)
        assert result.outcome == OUTCOME_UNKNOWN
        assert "vectorworks" not in result.matched

    def test_fabricated_control_fails_the_identity_predicate_on_both_axes(self):
        assert vectorworks_identity(FABRICATED_TAB) is False
        assert vectorworks_identity(FABRICATED_COMMA) is False


class TestReexportHint:
    def test_reexport_hint_appears_for_the_real_headerless_txt(self):
        data = (VWX_DIR / "vectorworks_export_instrument_data_no_header.txt").read_bytes()
        assert discriminate(data).hint == REEXPORT_HINT

    def test_reexport_hint_appears_for_the_tab_fabricated_control(self):
        assert discriminate(FABRICATED_TAB).hint == REEXPORT_HINT

    def test_reexport_hint_carries_a_conditional_clause(self):
        assert "이라면" in REEXPORT_HINT
        assert "Export field names as first record" in REEXPORT_HINT

    def test_reexport_hint_does_not_change_the_classification(self):
        data = (VWX_DIR / "vectorworks_export_instrument_data_no_header.txt").read_bytes()
        result = discriminate(data)
        assert result.outcome == OUTCOME_UNKNOWN
        assert result.matched == ()

    def test_reexport_hint_is_absent_when_the_shape_is_not_a_headerless_grid(self):
        assert discriminate(_csv(["Nope", "Nothing"])).hint is None
        assert discriminate(PATCH_CSV.read_bytes()).hint is None


class TestInputBoundary:
    def test_header_is_unreadable_for_zip_archives(self):
        assert read_header((VWX_DIR / "demoshow_grandma3.mvr").read_bytes()) is None

    def test_header_is_unreadable_for_undecodable_bytes(self):
        assert read_header(b"\xff\xfe\x00\x01\x02\x03") is None

    def test_discrimination_result_is_the_declared_shape(self):
        assert isinstance(discriminate(b""), Discrimination)

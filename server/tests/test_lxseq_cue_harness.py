"""큐 하네스의 인구조사·큐 단위 자르기·유출 탐지 검사.

이 파일이 못 박는 것은 하나다: **`Note` 텍스트는 영상 콜 판별기가 될 수 없다.**
다음 사람이 「`Note` 로 매칭하면 되지 않나」를 다시 생각하지 못하도록, 왜 안 되는지가
검사에 박혀 있어야 한다 — 실측으로 6 중 5만 걸리고, 5/6 은 그럴듯해서 눈에 안 띈다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.tools.lxseq_cues_e2e import (
    VIDEO_CALL_GROUP,
    CanonicalHeaderRequired,
    census,
    leaked_commands,
    main,
    read_rows,
    slice_by_cue,
    tool_arguments,
)

CUE_CSV = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "Lighting_Designer"
    / "03_곡파일_Sugar"
    / "LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv"
)


@pytest.fixture(scope="module")
def sheet() -> dict:
    return census(read_rows(CUE_CSV))


def test_census_splits_console_rows_from_video_calls(sheet: dict) -> None:
    """89 를 하나로 뭉개지 않는다 — 콘솔 대상과 영상 콜을 나란히 센다."""
    assert sheet["total_rows"] == 89
    assert sheet["cue_count"] == 18
    assert sheet["video_call_rows"] == 6
    assert sheet["console_rows"] == 83
    assert sheet["console_rows"] + sheet["video_call_rows"] == sheet["total_rows"]


def test_note_text_is_not_a_discriminator(sheet: dict) -> None:
    """🔴 이 검사가 이 파일의 이유다.

    `Note` 로 매칭하면 6 행 중 5 행만 걸린다. 남는 1 행(Q170 「영상 페이드아웃 동기」)은
    콘솔 명령으로 새고, 집계는 5/6 이라 그럴듯해 보여 눈에 띄지 않는다. 유출 사고가
    났던 자리에서 가장 안 보이는 형태로 새는 것이다.

    그러므로 판별기는 그룹명 하나여야 한다.
    """
    assert sheet["note_pattern_hits"] == 5
    assert sheet["note_pattern_would_miss"] == 1
    assert sheet["note_pattern_hits"] < sheet["video_call_rows"], (
        "Note 패턴이 그룹 판별과 같은 수를 잡으면 이 검사의 전제가 바뀐 것이다 — "
        "시트가 바뀌었는지 확인하고, 판별기를 Note 로 되돌리지는 마라."
    )


def test_group_discriminator_catches_every_video_row() -> None:
    """그룹명 판별은 전수다 — Note 가 어떻게 쓰였든 걸린다."""
    rows = read_rows(CUE_CSV)
    by_group = [row for row in rows if row["Group"] == VIDEO_CALL_GROUP]
    assert len(by_group) == 6
    # 그중 하나는 Note 가 LW- 형태가 아니다. 그래도 그룹으로는 걸린다.
    off_pattern = [row for row in by_group if "LW-" not in (row.get("Note") or "")]
    assert len(off_pattern) == 1
    assert off_pattern[0]["Q#"] == "Q170"


def _cues_in(payload: bytes) -> list[str]:
    lines = [line for line in payload.decode("utf-8").splitlines() if line.strip()]
    order: list[str] = []
    for line in lines[1:]:
        cue = line.split(",")[0]
        if cue not in order:
            order.append(cue)
    return order


def _rows_in(payload: bytes) -> int:
    return len([line for line in payload.decode("utf-8").splitlines() if line.strip()]) - 1


def test_slice_never_splits_a_cue() -> None:
    """§11.1 1열 「부분집합 금지 — 모든 큐에 최소 1행」.

    형제 프리셋 하네스는 행으로 자르지만 큐는 그러면 안 된다. 경계에 걸린 큐가
    반쪽이 되면 발사기가 스스로 명세서를 어긴다.
    """
    rows = read_rows(CUE_CSV)
    first_cue = rows[0]["Q#"]
    expected_rows = len([row for row in rows if row["Q#"] == first_cue])
    assert expected_rows > 1, "첫 큐가 1행뿐이면 이 검사가 아무것도 구분하지 못한다"

    payload = slice_by_cue(CUE_CSV, 1)
    assert _cues_in(payload) == [first_cue]
    assert _rows_in(payload) == expected_rows


def test_slice_skip_moves_by_cue_not_by_row() -> None:
    rows = read_rows(CUE_CSV)
    order = list(dict.fromkeys(row["Q#"] for row in rows))
    payload = slice_by_cue(CUE_CSV, 1, skip=1)
    assert _cues_in(payload) == [order[1]]


def test_slice_with_no_limit_keeps_every_row() -> None:
    payload = slice_by_cue(CUE_CSV, None)
    assert _rows_in(payload) == 89
    assert len(_cues_in(payload)) == 18


def test_leak_detector_fires_on_a_fabricated_leak() -> None:
    """양성 대조군. 안 터지는 탐지기는 0 을 증거로 쓸 수 없다."""
    leaking = [("Group 9 At 55", "Group " + VIDEO_CALL_GROUP + " At 55")]
    assert len(leaked_commands(leaking)) == 1


def test_leak_detector_is_silent_on_clean_bundles() -> None:
    clean = [("Group 1 At 55", "Group 2 At 40")]
    assert leaked_commands(clean) == []


class TestSequenceName:
    """`--sequence-name` 은 필수이고 파일명에서 유도하지 않는다.

    `map_cues` 는 시퀀스를 이름으로 찾거나 만드는데 그 이름이 CSV 바이트에 없다.
    파일명에서 꺼내려면 명명 규약을 가정해야 하고, **그 이름은 콘솔에 영구히
    남는다** — 틀린 이름이 쇼파일에 박히느니 인자를 요구한다.
    """

    def test_missing_flag_fails_before_touching_the_console(self, capsys) -> None:
        with pytest.raises(SystemExit):
            main(["--cue-csv", str(CUE_CSV), "--listen-port", "9005"])
        message = capsys.readouterr().err
        assert "--sequence-name" in message

    def test_blank_value_fails_with_the_reason(self, capsys) -> None:
        """`required=True` 는 플래그 유무만 본다 — 빈 문자열은 통과한다."""
        with pytest.raises(SystemExit):
            main(
                [
                    "--cue-csv",
                    str(CUE_CSV),
                    "--listen-port",
                    "9005",
                    "--sequence-name",
                    "   ",
                ]
            )
        message = capsys.readouterr().err
        assert "파일명에서 유도하지 않는" in message, (
            "왜 유도하지 않는지가 사유에 있어야 한다 — 다음 사람이 유도기를 붙이지 못하게"
        )
        assert "영구히" in message

    def test_name_is_carried_into_the_tool_arguments(self) -> None:
        args = tool_arguments("Ym9keQ==", "preview", "Sugar")
        assert args["sequence_name"] == "Sugar"
        assert args["action"] == "preview"
        assert args["file_content_base64"] == "Ym9keQ=="

    def test_tool_arguments_carries_no_extra_key(self) -> None:
        """스키마가 `additionalProperties: False` 라 여분 키는 거절된다."""
        args = tool_arguments("x", "apply", "Sugar")
        assert sorted(args) == ["action", "file_content_base64", "sequence_name"]

    def test_omitted_preset_and_fx_sheets_add_no_keys(self) -> None:
        """안 준 종류는 조용히 빈 문자열이 아니라 키 자체가 없다."""
        args = tool_arguments("x", "preview", "Sugar")
        assert "preset_dim_content_base64" not in args
        assert "preset_col_content_base64" not in args
        assert "preset_bm_content_base64" not in args
        assert "fx_content_base64" not in args
        assert "cue_sheet_xlsx_base64" not in args

    def test_supplied_preset_and_fx_sheets_are_carried_through(self) -> None:
        args = tool_arguments(
            "x",
            "preview",
            "Sugar",
            preset_dim="dGVzdA==",
            preset_col="dGVzdA==",
            preset_bm="dGVzdA==",
            fx="dGVzdA==",
            cue_sheet_xlsx="dGVzdA==",
        )
        assert args["preset_dim_content_base64"] == "dGVzdA=="
        assert args["preset_col_content_base64"] == "dGVzdA=="
        assert args["preset_bm_content_base64"] == "dGVzdA=="
        assert args["fx_content_base64"] == "dGVzdA=="
        assert args["cue_sheet_xlsx_base64"] == "dGVzdA=="


def _variant_header_csv(tmp_path: Path) -> Path:
    """헤더만 소문자 + 공백 삽입으로 변형. 데이터 행은 정본 그대로."""
    lines = CUE_CSV.read_text(encoding="utf-8-sig").splitlines()
    variant = lines[0].lower().replace("q#", "q #")
    target = tmp_path / "variant.cue-ex.csv"
    target.write_text("\n".join([variant] + lines[1:]) + "\n", encoding="utf-8")
    return target


def test_non_canonical_header_fails_with_a_reason(tmp_path: Path) -> None:
    """조용히 `KeyError` 로 죽지 않는다 — 어느 열이 없고 무엇이 있었는지 말한다.

    파서는 헤더를 정규화해 이 시트를 받아준다(실측: records 89 / cues 18).
    이 하네스는 일부러 안 받는다 — 정규화가 두 벌이면 두 벌이 같이 틀렸을 때
    대조가 「일치」라고 답하고, 독립 분모라는 존재 이유가 사라진다.
    """
    variant = _variant_header_csv(tmp_path)

    with pytest.raises(CanonicalHeaderRequired) as caught:
        read_rows(variant)

    error = caught.value
    assert "Q#" in error.missing
    assert error.found, "시트에 있던 헤더 목록이 비어 있으면 진단이 안 된다"
    message = str(error)
    assert "Q#" in message
    assert "정규화" in message, "왜 관대하게 받지 않는지가 메시지에 있어야 한다"


def test_non_canonical_header_is_not_a_bare_keyerror(tmp_path: Path) -> None:
    """회귀 방지: 예전에는 `KeyError: 'Q#'` 로 죽었고 아무도 이유를 몰랐다."""
    variant = _variant_header_csv(tmp_path)
    with pytest.raises(CanonicalHeaderRequired):
        read_rows(variant)
    try:
        read_rows(variant)
    except CanonicalHeaderRequired:
        pass
    except KeyError:  # pragma: no cover - 회귀했을 때만 도달한다
        pytest.fail("맨 KeyError 로 되돌아갔다 — 사유를 말하는 실패여야 한다")


def test_canonical_header_still_reads(tmp_path: Path) -> None:
    """대조군. 엄격해진 검사가 정본까지 막으면 아무것도 못 잰다."""
    assert len(read_rows(CUE_CSV)) == 89


# -- SPEC-COPILOT-MUSICSYNC-001 M1 — 정본 전량 회귀 --------------------------
#
# 합성 시트만으로는 **실제 열 자리**가 증명되지 않는다. 정본 곡파일 두 장
# (CUE-EX CSV 89행 + xlsx)을 그대로 통과시켜, 18 큐 전부가 시각을 얻고 미확정도
# 단조성 위반도 0 건임을 잰다. 이 수치가 흔들리면 시트가 바뀐 것이거나 열
# 인덱스가 밀린 것이다 — 둘 다 조용히 지나가면 안 되는 변화다.

CUE_XLSX = CUE_CSV.parent / "LXSEQ_SAMPLE_01_Sugar_r3.xlsx"


def _canonical_timing_payload() -> dict:
    import base64
    import json

    from server.llm.types import ToolCall
    from server.orchestrator.tools import build_toolset
    from server.tests.test_lxseq_tool import Answers, FakeConsole, FakeDeploy, FakeExec

    console = FakeConsole(fixtures=[dict(name="BACK")])
    registry = build_toolset(
        execution_port=FakeExec(console),
        state_port=console,
        property_port=console,
        deploy_pipeline=FakeDeploy(console),
        question_port=Answers(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="musicsync-canonical",
            name="import_lxseq_cues",
            arguments=dict(
                file_content_base64=base64.b64encode(CUE_CSV.read_bytes()).decode("ascii"),
                sequence_name="Sugar",
                cue_sheet_xlsx_base64=base64.b64encode(CUE_XLSX.read_bytes()).decode("ascii"),
            ),
        )
    )
    assert execution.result.is_error is False
    return json.loads(execution.result.content)


def test_the_canonical_song_file_yields_a_time_for_every_cue() -> None:
    if not CUE_XLSX.exists():  # pragma: no cover - 정본 부재 환경
        pytest.skip(f"정본 곡파일이 없다: {CUE_XLSX}")
    timing = _canonical_timing_payload()["cue_timing"]
    assert len(timing["cues"]) == 18
    assert timing["undetermined"] == []
    assert timing["monotonicity_violations"] == []
    assert len(timing["timeline"]["sections"]) == 18
    assert timing["timeline"]["excluded_preroll"] == []


def test_the_canonical_song_file_declares_itself_derived() -> None:
    """🔴 이 시트는 스스로 「음원 청취 미검증」이라고 적어 뒀다. 산출물이 그
    자백을 삼키면 파생물 전부가 확정본처럼 읽힌다(표준 §2.4)."""
    if not CUE_XLSX.exists():  # pragma: no cover - 정본 부재 환경
        pytest.skip(f"정본 곡파일이 없다: {CUE_XLSX}")
    timing = _canonical_timing_payload()["cue_timing"]
    assert timing["head"]["tc_source"] == "LTC"
    assert timing["head"]["tc_method"].startswith("DERIVED")
    assert "리허설 LTC 대조 전까지 실행 확정본이 아님" in timing["warning"]


def test_the_canonical_csv_alone_still_reads_and_says_its_limit() -> None:
    """CSV 만 준 회귀 — 17열 정확 집합은 그대로이고 시간은 0건이다."""
    import base64
    import json

    from server.llm.types import ToolCall
    from server.orchestrator.tools import build_toolset
    from server.tests.test_lxseq_tool import Answers, FakeConsole, FakeDeploy, FakeExec

    console = FakeConsole(fixtures=[dict(name="BACK")])
    registry = build_toolset(
        execution_port=FakeExec(console),
        state_port=console,
        property_port=console,
        deploy_pipeline=FakeDeploy(console),
        question_port=Answers(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="musicsync-canonical-csv",
            name="import_lxseq_cues",
            arguments=dict(
                file_content_base64=base64.b64encode(CUE_CSV.read_bytes()).decode("ascii"),
                sequence_name="Sugar",
            ),
        )
    )
    assert execution.result.is_error is False
    payload = json.loads(execution.result.content)
    assert payload["read"] == 89
    assert len(payload["cue_numbers"]) == 18
    assert payload["cue_timing"]["cues"] == []
    assert "시간 정보 없음" in payload["cue_timing"]["reason"]
    assert "manual_go" in payload["cue_timing"]["reason"]

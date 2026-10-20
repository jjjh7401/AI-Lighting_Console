"""정본 곡파일(Sugar) 큐 시각 전량 회귀 — `import_lxseq_cues` 툴 경유.

(옛 `server/tools/lxseq_cues_e2e` 하네스 검사는 하네스와 함께 삭제했다. 아래는
하네스가 아니라 **앱이 쓰는 툴**을 정본 파일에 대고 재는 회귀라서 남긴다.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

CUE_CSV = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "Lighting_Designer"
    / "03_곡파일_Sugar"
    / "LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv"
)

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

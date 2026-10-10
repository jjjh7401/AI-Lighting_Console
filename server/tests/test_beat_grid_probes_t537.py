"""SPEC-LDBEAT-001 M7 — M1 9항목 판정의 실시간 읽기 (카드 t537, REQ-LDBEAT-003(b)).

이 시험이 재는 것: (1) progress.md의 실제 M1 표 모양을 그대로 파싱하는지
(2) ⑩⑪ 확장 항목은 제외하는지 (3) 표 부재·파싱 실패 시 9항목 전부
"미확인"(지어낸 PASS 0건)으로 떨어지는지 — AC-LDBEAT-009(c)(d).
"""

from __future__ import annotations

from server.design.beat_grid_probes import (
    DEFAULT_PROBE_IDS,
    UNCONFIRMED_STATUS,
    parse_m1_probe_table,
    read_m1_probe_results,
    read_m1_probe_results_from_path,
)

# progress.md의 실제 M1 표(PR #583 머지분, 2026-10-10) — 그대로 옮긴 조각.
_REAL_TABLE = """\
| 항목 | 판정 | 무엇을 봤나 | 근거 |
|---|---|---|---|
| ① 타임코드 트랙 ≥3(목표 6) | **통과(구조)** | TC 30 에 시퀀스 트랙 6개(228→233) | `live/p1/` |
| ② Goto 2번 이후·여러 시퀀스 동시 | **미확인** | 줄은 전부 OK | `live/p2_on/` |
| ③ 프리셋 수정 전파 | **부분** | v2 거절 → v3 받음 | `live/p3_a/` |
| ④ 효과 프리셋의 SM15·Measure | **미확인** | 감독 「다 같이 깜빡임」 | `live/p4_a/` |
| ⑤ 위치 프리셋 위 상대값(원) | **움직임 없음** | 감독 「멈춰 있음」 | `live/p5_a/` |
| ⑥ 타임코드 중간 재생 | **미확인 — 문법 불명** | User Canceled Command | `live/p6_a/` |
| ⑦ 큐에 선택 + Step 2 | **부분(결과 기록)** | 큐1 「다 같이 깜빡임」 | `live/p7_a/` |
| ⑧ 같은 그룹 두 시퀀스 분담 | **통과** | 감독 「켜지고 틸트가 조금 기울어짐」 | `live/p8_a/` |
| ⑨ circle·발리후·wave | wave **움직임 없음** · circle·발리후 **미확인** \
| wave 감독 「멈춰 있음」 | `live/p9_a/` |
| ⑩ 디머 위상 펼침(추가) | **통과** | 감독 「물결처럼 차례로」 | `live/p10_a/` |
| ⑪ t520 줄 순서 재현(추가) | **통과(가설 반증)** | 감독 「둘 다 깜빡임」 | `live/p11_a/` |
"""


class TestParseM1ProbeTable:
    def test_extracts_the_verbatim_status_text_for_all_nine_items(self) -> None:
        parsed = parse_m1_probe_table(_REAL_TABLE)

        assert parsed[1] == "통과(구조)"
        assert parsed[2] == "미확인"
        assert parsed[3] == "부분"
        assert parsed[4] == "미확인"
        assert parsed[5] == "움직임 없음"
        assert parsed[6] == "미확인 — 문법 불명"
        assert parsed[7] == "부분(결과 기록)"
        assert parsed[8] == "통과"
        # ⑨는 두 판정이 섞인 칸 — 전체 셀 텍스트가 그대로 보존된다(해석 없음).
        assert parsed[9] == "wave 움직임 없음 · circle·발리후 미확인"

    def test_extension_items_ten_and_eleven_are_excluded(self) -> None:
        parsed = parse_m1_probe_table(_REAL_TABLE)

        assert 10 not in parsed
        assert 11 not in parsed

    def test_an_empty_or_unrelated_text_yields_no_matches(self) -> None:
        assert parse_m1_probe_table("") == {}
        assert parse_m1_probe_table("# 아무 제목\n\n본문만 있는 문서.") == {}

    def test_header_and_separator_rows_are_not_mistaken_for_an_item(self) -> None:
        table_with_no_data_rows = "| 항목 | 판정 |\n|---|---|\n"

        assert parse_m1_probe_table(table_with_no_data_rows) == {}


class TestReadM1ProbeResultsSuccessPath:
    def test_all_nine_ids_are_present_and_match_the_table(self) -> None:
        results = read_m1_probe_results(_REAL_TABLE)

        assert set(results.keys()) == set(DEFAULT_PROBE_IDS)
        assert results[1] == "통과(구조)"
        assert results[9] == "wave 움직임 없음 · circle·발리후 미확인"

    def test_an_item_missing_from_the_table_falls_back_to_unconfirmed(self) -> None:
        table_missing_item_five = _REAL_TABLE.replace(
            "| ⑤ 위치 프리셋 위 상대값(원) | **움직임 없음** | 감독 「멈춰 있음」 "
            "| `live/p5_a/` |\n",
            "",
        )

        results = read_m1_probe_results(table_missing_item_five)

        assert results[5] == UNCONFIRMED_STATUS
        assert results[1] == "통과(구조)"  # 나머지는 그대로


class TestReadM1ProbeResultsFailurePath:
    """REQ-LDBEAT-003(b)/AC-LDBEAT-009(d) — 표 부재·파싱 실패 → 9항목 전부
    "미확인", 지어낸 PASS 0건."""

    def test_none_text_yields_all_nine_unconfirmed(self) -> None:
        results = read_m1_probe_results(None)

        assert results == {i: UNCONFIRMED_STATUS for i in DEFAULT_PROBE_IDS}

    def test_empty_text_yields_all_nine_unconfirmed(self) -> None:
        results = read_m1_probe_results("")

        assert results == {i: UNCONFIRMED_STATUS for i in DEFAULT_PROBE_IDS}

    def test_garbled_text_with_no_table_yields_all_nine_unconfirmed(self) -> None:
        results = read_m1_probe_results("이 파일은 표가 깨졌습니다 — 아무 데이터도 없음.")

        assert results == {i: UNCONFIRMED_STATUS for i in DEFAULT_PROBE_IDS}
        assert "pass" not in results.values()
        assert "통과" not in results.values()

    def test_a_missing_file_on_disk_yields_all_nine_unconfirmed(self, tmp_path) -> None:
        missing = tmp_path / "does-not-exist" / "progress.md"

        results = read_m1_probe_results_from_path(missing)

        assert results == {i: UNCONFIRMED_STATUS for i in DEFAULT_PROBE_IDS}

    def test_a_real_file_on_disk_is_read_and_parsed(self, tmp_path) -> None:
        path = tmp_path / "progress.md"
        path.write_text(_REAL_TABLE, encoding="utf-8")

        results = read_m1_probe_results_from_path(path)

        assert results[1] == "통과(구조)"
        assert results[8] == "통과"

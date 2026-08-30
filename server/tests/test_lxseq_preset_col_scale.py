"""t134 — col 시트의 0-255 를 콘솔 퍼센트로 옮긴다 (SPEC-COPILOT-LXSEQ-003).

**이 파일은 측정 뒤에 쓰였다.** 임포터가 col 6행을 막던 사유는
「RGB 가 0-255 로 적혔고 콘솔은 0-100 퍼센트다. 두 축의 대응은 미측정이라
변환이 해석이 된다」였다. 미측정이라는 말은 옳았고, 이제 쟀다.

    2026-08-30 · onPC pid 38706 · 응답기 1.6.2 · MOVER-D 521 (Robe Spiider) 3.001
    ColorRGB_R = COARSE 1 / FINE 2 (16비트)

    At 100                   -> 255 / 255
    At 70.6                  -> 180 / 188   180*256+188 = 46268
                                            round(70.6/100*65535) = 46268   오차 0
    At Absolute Decimal8 180 -> 180 / 0     FINE 이 188->0 이라 적용이지 무시가 아니다

그래서 콘솔은 퍼센트를 16비트로 **선형** 매핑한다. `make_ma3.py:85-87` 이
이미 쓰던 `r/255*100` 이 옳았고, 이제 근거가 선언이 아니라 측정이다.

증거 전문: `.moai/reports/t134/col-scale.md` 13절.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from pathlib import Path

from server.lxseq.preset_parser import (
    HOLD_NO_RGB_VALUE,
    col_rgb_percents,
    parse_preset_csv,
)
from server.presets.store import preset_apply_color_command

RIG = Path("src/Lighting_Designer/02_RIG팩")
CSV = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-col.csv"


def _records():
    return parse_preset_csv(CSV.read_text(encoding="utf-8")).records


class TestTheSixRgbRowsOpen:
    """여는 것은 **6행이지 8행이 아니다.**"""

    def test_the_rgb_rows_are_storable_and_the_kelvin_rows_are_not(self):
        by_id = dict((r.preset_id, r) for r in _records())
        storable = sorted(pid for pid, r in by_id.items() if r.storable)
        assert storable == ["COL.01", "COL.04", "COL.05", "COL.06", "COL.07", "COL.08"]
        assert not by_id["COL.02"].storable
        assert not by_id["COL.03"].storable

    def test_the_kelvin_rows_keep_their_own_reason(self):
        """스케일을 풀어도 켈빈 2행은 안 열린다 — 사유가 다르고 소유자가 다르다(t133)."""
        by_id = dict((r.preset_id, r) for r in _records())
        for pid in ("COL.02", "COL.03"):
            assert by_id[pid].hold_classes == (HOLD_NO_RGB_VALUE,)

    def test_no_row_still_carries_the_scale_reason(self):
        """이 카드가 지운 사유가 정말 없어졌는지 — 개수가 아니라 부재로 잰다."""
        assert not [r for r in _records() if "scale_unconverted" in r.hold_classes]


class TestTheReaderAndTheJudgeShareOnePredicate:
    """판정기가 통과시킨 값을 판독기가 못 읽으면 임포터가 통째로 거절한다(t97)."""

    def test_every_storable_row_yields_three_percents(self):
        for record in _records():
            if record.storable:
                assert col_rgb_percents(record.value_raw) is not None

    def test_every_held_row_yields_nothing(self):
        for record in _records():
            if not record.storable:
                assert col_rgb_percents(record.value_raw) is None

    def test_a_partial_triplet_is_held_not_passed(self):
        """`R2` 만 있고 G·B 가 없는 값 — 옛 술어(`R\\s*\\d`)는 통과시켰다."""
        from server.lxseq.preset_parser import classify_storability

        storable, reasons = classify_storability("preset-col", "R2 뭔가")
        assert storable is False
        assert reasons
        assert col_rgb_percents("R2 뭔가") is None

    def test_an_out_of_range_component_is_held(self):
        from server.lxseq.preset_parser import classify_storability

        storable, reasons = classify_storability("preset-col", "R300 G0 B0")
        assert storable is False
        assert reasons


class TestTheConversion:
    def test_the_measured_point_reproduces(self):
        """실측 한 점: 시트 R=180 -> 70.6 -> 콘솔 COARSE 180."""
        assert col_rgb_percents("R255 G180 B60") == (100.0, 70.6, 23.5)

    def test_the_sheet_values_round_trip_without_loss(self):
        """이 시트의 18개 값에 한해 무손실 — **전 구간 무손실이 아니다.**

        콘솔 모델(실측 2점 적합): coarse = round(pct/100*65535) // 256.
        소수 1자리로는 0-255 중 12개가 ±1 로 어긋난다
        (7 8 9 10 20 21 234 235 245 246 247 248). 이 시트는 그중 하나도 안 쓴다.
        """
        for record in _records():
            percents = col_rgb_percents(record.value_raw)
            if percents is None:
                continue
            raw = [int(t) for t in __import__("re").findall(r"[RGB]\s*(\d+)", record.value_raw)]
            for original, pct in zip(raw, percents, strict=True):
                assert round(pct / 100 * 65535) // 256 == original

    def test_the_lossy_values_are_named_not_hidden(self):
        """시트가 바뀌어 저 12개가 들어오면 ±1 이 생긴다 — 그 사실을 검사로 고정한다."""

        def coarse(v: int) -> int:
            return round(round(v / 255 * 100, 1) / 100 * 65535) // 256

        assert [v for v in range(256) if coarse(v) != v] == [
            7,
            8,
            9,
            10,
            20,
            21,
            234,
            235,
            245,
            246,
            247,
            248,
        ]


class TestTheApplyLine:
    def test_the_line_matches_the_sibling_producer_byte_for_byte(self):
        """`make_ma3.py:85-87` 이 방출하는 것과 **같은 숫자 문면**이어야 한다."""
        line = preset_apply_color_command(1, (100.0, 70.6, 23.5))
        assert line == (
            "Group 1 ; Attribute 'ColorRGB_R' At 100.0"
            " ; Attribute 'ColorRGB_G' At 70.6"
            " ; Attribute 'ColorRGB_B' At 23.5"
        )

    def test_it_refuses_a_bad_group_number(self):
        import pytest

        from server.spatial.pointing import SpatialPointingError

        with pytest.raises(SpatialPointingError):
            preset_apply_color_command(0, (1.0, 2.0, 3.0))

    def test_it_refuses_a_percent_outside_the_console_range(self):
        import pytest

        from server.spatial.pointing import SpatialPointingError

        with pytest.raises(SpatialPointingError):
            preset_apply_color_command(1, (100.1, 0.0, 0.0))

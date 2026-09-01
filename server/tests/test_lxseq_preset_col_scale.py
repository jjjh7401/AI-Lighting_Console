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
    classify_storability,
    col_rgb_percents,
    parse_preset_csv,
)
from server.presets.store import preset_apply_color_command

RIG = Path("src/Lighting_Designer/02_RIG팩")
CSV = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-col.csv"


def _records():
    return parse_preset_csv(CSV.read_text(encoding="utf-8")).records


class TestTheSixRgbRowsOpen:
    """t134 가 RGB 6행을, t229 가 켈빈 2행을 열어 **8행 전부**가 열린다."""

    def test_every_row_including_the_kelvin_pair_is_storable(self):
        """t134 가 RGB 6행을, **t229 가 켈빈 2행**을 열어 8행 전부가 열린다."""
        by_id = dict((r.preset_id, r) for r in _records())
        storable = sorted(pid for pid, r in by_id.items() if r.storable)
        assert storable == [
            "COL.01",
            "COL.02",
            "COL.03",
            "COL.04",
            "COL.05",
            "COL.06",
            "COL.07",
            "COL.08",
        ]

    def test_the_no_rgb_reason_is_still_reachable(self):
        """정본에서 그 사유가 사라진 것은 **켈빈이 열렸기 때문**이지 클래스가 죽은
        것이 아니다. 숫자만 바꾸고 여기를 지우면 그 사유가 조용히 고아가 된다 —
        정의역 밖 색온도로 직접 쏴서 살아 있음을 고정한다."""
        assert not [r for r in _records() if HOLD_NO_RGB_VALUE in r.hold_classes]
        storable, holds = classify_storability("preset-col", "~40000K")
        assert not storable
        assert [h.hold_class for h in holds] == [HOLD_NO_RGB_VALUE]

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
        """정본 col 은 t229 이후 보류가 0이라 이 루프만으로는 **공허하다.**
        아래 합성 값이 판별력을 진다."""
        for record in _records():
            if not record.storable:
                assert col_rgb_percents(record.value_raw) is None
        for value in ("~40000K", "R2 뭔가", "현장 레코드"):
            storable, _holds = classify_storability("preset-col", value)
            assert not storable, value
            assert col_rgb_percents(value) is None, value

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
            # 시트에 RGB 가 **적힌** 행만 이 왕복의 대상이다. 켈빈 행은 원문에
            # 숫자 삼원색이 없으므로 아래 별도 검사가 변환값으로 잰다.
            raw = [int(t) for t in __import__("re").findall(r"[RGB]\s*(\d+)", record.value_raw)]
            if len(raw) != 3:
                continue
            for original, pct in zip(raw, percents, strict=True):
                assert round(pct / 100 * 65535) // 256 == original

    def test_the_converted_kelvin_values_round_trip_too(self):
        """켈빈 행도 같은 척도를 탄다 — 변환값이 저 12개 손실 값에 걸리면 여기서 걸린다."""
        from server.lxseq.preset_parser import _col_components

        for value in ("~3200K", "~5600K"):
            components = _col_components(value)
            percents = col_rgb_percents(value)
            assert components is not None and percents is not None, value
            for original, pct in zip(components, percents, strict=True):
                assert round(pct / 100 * 65535) // 256 == original, (value, original, pct)

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

    def test_the_format_is_pinned_to_one_decimal(self):
        """🔴 이 검사도 뮤테이션이 살아남아서 쓰였다.

        위 검사의 값(100.0 · 70.6 · 23.5)은 `f"{v}"` 와 `f"{v:.1f}"` 가 **우연히
        같다.** 그래서 `%.1f` 를 떼어내도 아무도 안 잡았다. 두 형태가 갈리는 값으로
        재야 자리수가 실제로 고정된다.
        """
        line = preset_apply_color_command(1, (70.588, 0.0, 100.0))
        assert "At 70.6 " in line
        assert "70.588" not in line
        assert line.endswith("At 100.0")

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


class _RecordingPort:
    """발화를 기록만 한다. `test_lxseq_preset_value_path.py` 의 포트와 같은 모양이되
    풀 목록이 **Color** 를 답한다 — 풀 번호는 콘솔 목록에서만 온다(AC-LXSEQ3-006)."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str):
        from server.orchestrator.ports import ExecutionResult

        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")

    def query_state(self, path: str) -> dict:
        if path.endswith("PresetPools"):
            return dict(
                children=[dict(i=1, name="Dimmer"), dict(i=4, name="Color")],
                node=dict(childCount=2),
            )
        return dict(children=[], node=dict(childCount=0), truncated=False)

    def query_property(self, path: str, name: str) -> dict:
        return dict(ok=False, error="not readable")


class _Approval:
    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return True


def _dispatch_col():
    import base64
    import json

    from server.llm.types import ToolCall
    from server.orchestrator.tools import build_toolset

    port = _RecordingPort()
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=_Approval(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t134",
            name="import_lxseq_presets",
            arguments=dict(
                file_content_base64=base64.b64encode(CSV.read_bytes()).decode("ascii"),
                action="apply",
            ),
        )
    )
    return json.loads(execution.result.content), port


class TestTheColorValueReachesTheConsole:
    """🔴 이 클래스는 뮤테이션이 살아남아서 쓰였다.

    `_lxseq_preset_apply_command` 의 col 분기를 통째로 꺼도 검사가 전부 초록이었다 —
    임포터가 **실제로 색 줄을 내보내는지** 아무도 안 재고 있었다. 이 카드의 핵심
    동작인데 그랬다.
    """

    def test_every_rgb_row_puts_its_three_components_on_the_wire(self):
        _payload, port = _dispatch_col()
        expected = [
            "Group 1 ; Attribute 'ColorRGB_R' At 100.0"
            " ; Attribute 'ColorRGB_G' At 70.6 ; Attribute 'ColorRGB_B' At 23.5",
            "Group 1 ; Attribute 'ColorRGB_R' At 100.0"
            " ; Attribute 'ColorRGB_G' At 23.5 ; Attribute 'ColorRGB_B' At 62.0",
            "Group 1 ; Attribute 'ColorRGB_R' At 35.3"
            " ; Attribute 'ColorRGB_G' At 16.9 ; Attribute 'ColorRGB_B' At 78.4",
            "Group 1 ; Attribute 'ColorRGB_R' At 18.0"
            " ; Attribute 'ColorRGB_G' At 84.7 ; Attribute 'ColorRGB_B' At 84.7",
            "Group 1 ; Attribute 'ColorRGB_R' At 100.0"
            " ; Attribute 'ColorRGB_G' At 41.6 ; Attribute 'ColorRGB_B' At 15.7",
            "Group 1 ; Attribute 'ColorRGB_R' At 11.8"
            " ; Attribute 'ColorRGB_G' At 23.5 ; Attribute 'ColorRGB_B' At 100.0",
        ]
        for line in expected:
            assert line in port.executed, "이 줄이 안 나갔다: " + line + " / " + repr(port.executed)

    def test_the_bundle_order_is_apply_then_store_then_clear(self):
        """t108 이 세운 계약 — ClearAll 이 적용보다 앞이면 빈 프로그래머가 저장된다."""
        _payload, port = _dispatch_col()
        first = next(i for i, c in enumerate(port.executed) if c.startswith("Group 1 ; Attribute"))
        assert port.executed[first + 1].startswith("Store Preset 4.")
        assert port.executed[first + 2].startswith("Label Preset 4.")
        assert port.executed[first + 3] == "ClearAll"

    def test_the_two_kelvin_rows_are_stored_too(self):
        """t229 이후 **8행 전부** 나간다 — 발화에도 그렇게 나타나야 한다.

        t134 시점에는 「6행이지 8행이 아니다」였고 두 화이트 행이 라벨에 없는 것이
        그 증거였다. 켈빈이 열렸으므로 이제 반대가 증거다.
        """
        _payload, port = _dispatch_col()
        stores = [c for c in port.executed if c.startswith("Store Preset")]
        assert len(stores) == 8, port.executed
        labels = [c for c in port.executed if c.startswith("Label Preset")]
        white = [c for c in labels if "화이트" in c]
        assert len(white) == 2, labels

    def test_the_pool_number_comes_from_the_console_listing(self):
        """비공허성 — 4 는 상수가 아니라 콘솔이 답한 `Color` 의 번호다."""
        _payload, port = _dispatch_col()
        assert all(c.startswith("Store Preset 4.") for c in port.executed if "Store Preset" in c)

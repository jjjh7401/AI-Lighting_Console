"""t229 — 켈빈→RGB 변환과 그 **지뢰**.

이 파일이 지키는 것은 넷이다.

1. **판정기와 판독기가 갈라지지 않는다.** `tools.py` 의 경고문이 그 자리를
   지목한다 — 「판정기가 통과시킨 값을 판독기가 못 읽었다는 뜻이다. 둘은 같은
   술어를 쓰므로 여기 오면 술어가 갈라진 것이다」.
2. **갈라졌을 때 무슨 일이 나는지**를 재현으로 고정한다. 읽어서 낸 결론이 아니라
   돌려본 결과다.
3. **근사를 숨기지 않는다** — 승인 카드에 원값과 변환값이 나란히 뜬다.
4. **기존 6행을 죽이지 않았다** — 8행 전부 나가고 `apply_untranslatable` 은 0건.

변환식의 출처는 `preset_parser.planckian_xy` · `kelvin_to_rgb` 독스트링에 있다
(Kim et al. 2002 · IEC 61966-2-1). 아래 앵커 검사가 그 계수를 **독립 기준**으로
검산한다 — 식을 만드는 데 쓰지 않은 값들이다.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.lxseq import preset_parser
from server.lxseq.preset_parser import (
    col_conversion_note,
    col_rgb_percents,
    kelvin_to_rgb,
    parse_preset_csv,
    planckian_xy,
)
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset

COL = Path("src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-col.csv")

#: 정본 col 시트의 행 수와, 켈빈 단독인 두 행. 파일을 열어 확인한 값이다.
COL_ROWS = 8
KELVIN_ROWS = ("COL.02", "COL.03")


class _Port:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")

    def query_state(self, path: str) -> dict:
        if path.endswith("PresetPools"):
            return dict(children=[dict(i=4, name="Color")], node=dict(childCount=1))
        return dict(children=[], node=dict(childCount=0), truncated=False)

    def query_property(self, path: str, name: str) -> dict:
        return dict(ok=False, error="not readable")


class _Approval:
    def request_approval(self, request) -> bool:
        return True


def _dispatch(action: str = "apply"):
    port = _Port()
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=_Approval(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t229",
            name="import_lxseq_presets",
            arguments=dict(
                file_content_base64=base64.b64encode(COL.read_bytes()).decode("ascii"),
                action=action,
            ),
        )
    )
    return json.loads(execution.result.content), port


class TestTheCoefficientsAreAnchored:
    """계수를 **독립 기준**으로 검산한다. 기억에서 쓴 숫자를 그대로 믿지 않는다."""

    def test_illuminant_a_is_the_anchor_that_must_match(self):
        """CIE 표준광 A(2856K)는 **플랑크 복사체**다 — 여기가 맞아야 계수가 맞다."""
        x, y = planckian_xy(2856.0)
        assert abs(x - 0.4476) < 0.001, x
        assert abs(y - 0.4074) < 0.001, y

    def test_daylight_illuminants_deviate_and_that_is_correct(self):
        """D65·D50 은 **주광 궤적** 위에 있어 플랑크 궤적에서 떨어져 있다.

        어긋나는 것이 정답이다 — 안 어긋나면 오히려 계수가 틀린 것이다. 다만
        어긋남이 작아야 한다(Duv 규모). 이 검사가 없으면 위 앵커 하나만으로
        「우연히 한 점이 맞았다」와 구분되지 않는다.
        """
        for kelvin, ref_y in ((6504.0, 0.3290), (5003.0, 0.3585)):
            _x, y = planckian_xy(kelvin)
            gap = abs(y - ref_y)
            assert 0.001 < gap < 0.02, (kelvin, y, ref_y, gap)

    def test_d65_white_point_encodes_to_srgb_white(self):
        """D65 가 sRGB 백색이라는 것은 **규격의 정의**다 — 행렬을 그 정의로 검산한다.

        `kelvin_to_rgb` 를 그대로 부르지 않고 백색점 `xy` 를 직접 넣는 이유: 6504K
        의 **플랑크 궤적 위 점**은 D65 백색점과 미세하게 다르다(주광 궤적 offset).
        행렬을 재려면 궤적이 아니라 **백색점 자체**를 넣어야 한다.
        """
        rgb = preset_parser._xy_to_srgb(0.3127, 0.3290)
        assert rgb == (255, 255, 255), rgb

    def test_blue_to_red_ratio_rises_with_temperature(self):
        """단조성 — 뜨거울수록 파래야 한다. 역전이 하나라도 있으면 식이 틀렸다."""
        previous = None
        for kelvin in (2000, 2400, 2856, 3200, 4000, 5000, 5600, 6504, 8000, 10000):
            red, _green, blue = kelvin_to_rgb(float(kelvin))
            ratio = blue / max(red, 1)
            if previous is not None:
                assert ratio > previous, (kelvin, ratio, previous)
            previous = ratio

    def test_outside_the_published_domain_is_held_not_extrapolated(self):
        """Kim et al. 정의역은 1667K-25000K 다. 밖으로 끌면 조용히 틀린 색이 나간다."""
        for value in ("~900K", "~40000K"):
            storable, holds = preset_parser.classify_storability("preset-col", value)
            assert not storable, value
            assert "no_rgb_value" in [h.hold_class for h in holds], value

    def test_the_domain_edges_are_inside(self):
        """대조군 — 정의역 안이면 열린다. 없으면 위 검사가 「무조건 막힌다」와 안 갈린다."""
        for value in ("~1667K", "~25000K"):
            storable, _holds = preset_parser.classify_storability("preset-col", value)
            assert storable, value


class TestJudgeAndReaderCannotDiverge:
    """조건 1 — `tools.py` 의 경고문이 지목한 자리를 검사로 못박는다.

    「판정기가 통과시킨 값을 판독기가 못 읽었다는 뜻이다. 둘은 같은 술어를 쓰므로
    여기 오면 술어가 갈라진 것이다 — 추측하지 않는다.」

    갈라지면 `_lxseq_preset_apply_command` 가 `None` 을 내고 소비 루프가 번들을
    통째로 버린다. 그래서 이 등가는 성능이 아니라 **안전**이다.
    """

    def test_storable_iff_the_reader_can_read_it(self):
        result = parse_preset_csv(COL.read_text(encoding="utf-8-sig"))
        assert len(result.records) == COL_ROWS
        for record in result.records:
            readable = col_rgb_percents(record.value_raw) is not None
            assert record.storable == readable, (
                record.preset_id
                + ": 판정 "
                + str(record.storable)
                + " · 판독 "
                + str(readable)
                + " — 술어가 갈라졌다. 이 상태로 apply 하면 col 시트가 통째로 0건이다."
            )

    def test_the_equivalence_holds_on_synthetic_values_too(self):
        """정본 시트 8행만으로는 경계가 안 잡힌다 — 합성 값으로 정의역 가장자리까지."""
        for value in (
            "~3200K",
            "~1667K",
            "~25000K",
            "~1666K",
            "~25001K",
            "R255 G0 B0",
            "R999 G0 B0",
            "현장 레코드",
            "",
        ):
            storable, _holds = preset_parser.classify_storability("preset-col", value)
            readable = col_rgb_percents(value) is not None
            assert storable == readable, (value, storable, readable)


class TestTheLandmineIsReproduced:
    """조건 2 — 읽어서 낸 결론이 아니라 **돌려본 결과**로 고정한다.

    판정기만 열고 판독기를 그대로 두면 col 시트가 통째로 0건이 된다. 「2행을
    얻으려다 8행을 잃는」 형태다.
    """

    def test_opening_the_judge_alone_kills_every_row(self, monkeypatch):
        real = preset_parser.classify_storability

        def judge_only(kind, value_raw):
            storable, holds = real(kind, value_raw)
            if not storable and "K" in value_raw:
                return True, ()
            return storable, holds

        # 판독기는 그대로 두고 판정기만 연다 — 갈라진 상태를 만든다.
        monkeypatch.setattr(preset_parser, "classify_storability", judge_only)
        monkeypatch.setattr(
            preset_parser,
            "_col_components",
            lambda value_raw: preset_parser._rgb_components(value_raw),
        )
        payload, port = _dispatch()

        assert payload.get("refusal") == "apply_untranslatable", payload.get("refusal")
        assert port.executed == [], "갈라졌는데 발화했다: " + repr(port.executed)
        blocked = [item.get("preset_id") for item in (payload.get("untranslatable") or [])]
        assert blocked == list(KELVIN_ROWS), blocked

    def test_the_control_is_that_the_same_sheet_fires_unpatched(self):
        """대조군 — 패치 없이는 여덟 행이 다 나간다. 없으면 위 검사가
        「이 시트는 원래 안 나간다」와 구분되지 않는다."""
        payload, port = _dispatch()
        assert payload.get("refusal") is None, payload.get("refusal")
        assert port.executed, "대조군이 아무것도 안 쐈다"


class TestTheSixExistingRowsAreNotKilled:
    """조건 4 — 이 카드의 제일 큰 실패 모드가 「2행을 얻으려다 8행을 잃는」 것이다."""

    def test_every_row_is_storable(self):
        result = parse_preset_csv(COL.read_text(encoding="utf-8-sig"))
        held = [r.preset_id for r in result.records if not r.storable]
        assert held == [], held
        assert len(result.records) == COL_ROWS

    def test_nothing_is_untranslatable(self):
        payload, _port = _dispatch()
        assert payload.get("untranslatable") in (None, []), payload.get("untranslatable")
        assert payload.get("refusal") is None, payload.get("refusal")

    def test_all_eight_rows_reach_the_console(self):
        _payload, port = _dispatch()
        applies = [c for c in port.executed if "ColorRGB_R" in c]
        stores = [c for c in port.executed if c.startswith("Store Preset ")]
        assert len(applies) == COL_ROWS, port.executed
        assert len(stores) == COL_ROWS, port.executed

    def test_the_author_rgb_wins_over_the_approximation(self):
        """COL.01 은 RGB 와 켈빈을 **둘 다** 싣는다. 시트가 명시한 값이 이겨야 한다.

        지면 근사가 저자의 선택을 조용히 덮는다 — `R255 G180 B60` 이
        `R255 G160 B66` 으로 바뀐다.
        """
        percents = col_rgb_percents("R255 G180 B60 / ~2400K")
        assert percents == (100.0, 70.6, 23.5), percents


class TestTheApproximationIsDisclosed:
    """조건 3 — 근사가 조용히 나가면 「조용히 틀린 것이 크게 없는 것보다 나쁘다」에 걸린다."""

    def test_the_converted_rows_carry_both_values(self):
        payload, _port = _dispatch(action="preview")
        rows = dict([(r["preset_id"], r) for r in payload["planned"]])
        for preset_id in KELVIN_ROWS:
            note = rows[preset_id].get("converted")
            assert note, preset_id + " 에 변환 고지가 없다 — 근사가 조용히 나간다"
            assert rows[preset_id]["value"] in note, note
            assert " R" in note and " G" in note and " B" in note, note

    def test_the_note_names_the_standard(self):
        note = col_conversion_note("~3200K")
        assert note is not None
        assert "Kim et al. 2002" in note, note
        assert "IEC 61966-2-1" in note, note

    def test_rows_that_were_not_converted_carry_no_note(self):
        """항상 붙이면 「변환됨」이 의미를 잃는다."""
        assert col_conversion_note("R255 G60 B158") is None
        assert col_conversion_note("R255 G180 B60 / ~2400K") is None
        payload, _port = _dispatch(action="preview")
        for row in payload["planned"]:
            if row["preset_id"] not in KELVIN_ROWS:
                assert "converted" not in row, row

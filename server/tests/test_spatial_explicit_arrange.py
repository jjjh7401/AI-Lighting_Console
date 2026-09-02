"""t224 — 임의 좌표 쓰기 경로(`explicit`)와 라벨 출처 꼬리.

`arrange_fixtures` 의 기존 프리셋은 전부 **기하 도형**이다 — 도형을 계산해서
좌표를 만든다. 이 카드가 필요한 것은 그 반대다: **CSV 가 이미 들고 있는
장비별 좌표**를 그대로 콘솔에 올린다. 도형이 없으므로 기존 프리셋 어느 것도
쓸 수 없고, 그렇다고 백업 → 정적 범위검사 → 쓰기 → 되읽기 봉투를 우회할
이유도 없다. 그래서 봉투는 그대로 두고 **계획 산출 단계만** 새로 붙인다.

콘솔 접촉 0 — 전부 인메모리. 가짜 콘솔은 `test_spatial_arrange` 의 것을 그대로
쓴다: 측정된 거짓말(부호 탈락·조용한 무시·float32)을 재현하는 그 모델이 이
경로에도 그대로 걸려야 한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.lxseq.position_derive import (
    DERIVED_LABEL_SUFFIX,
    SYNTHETIC_LABEL_SUFFIX,
    derive_position_presets,
    parse_position_sheet,
    preset_id_from_console_head,
)
from server.orchestrator.tools import ARRANGE_PRESETS, EXPLICIT_PRESET
from server.spatial.presets import (
    SPATIAL_PRESET_MAX_ABS,
    SpatialPresetError,
    explicit_placements,
)
from server.tests.test_spatial_arrange import ArrangeConsole, arrange, registry, rig
from server.tools.lxseq_coords_write import parse_coords_sheet


def _rows(entries):
    return [dict(fid=fid, x=x, y=y, z=z) for fid, x, y, z in entries]


class TestExplicitPlacements:
    """순수층 — 콘솔도 도형도 없다. 검증과 양자화만 한다."""

    def test_it_keeps_the_given_coordinates_and_their_order(self):
        plan = explicit_placements(_rows([(11, -5.0, -9.0, 7.5), (13, 1.0, 2.0, 0.2)]))

        assert plan.preset == EXPLICIT_PRESET
        assert plan.fids == (11, 13)
        assert [(p.x, p.y, p.z) for p in plan.placements] == [
            (-5.0, -9.0, 7.5),
            (1.0, 2.0, 0.2),
        ]
        assert plan.resolved["fid_order"] == [11, 13]
        assert plan.resolved["count"] == 2

    def test_it_quantises_through_the_same_bound_the_shapes_use(self):
        plan = explicit_placements(_rows([(11, 1.000049999, -0.0, 2.0)]))

        # 4자리 양자화 + 음의 0 정규화 — 도형 경로와 같은 술어(`_quantise`).
        assert plan.placements[0].x == 1.0
        assert str(plan.placements[0].y) == "0.0"

    def test_it_refuses_a_coordinate_past_the_sanity_bound(self):
        with pytest.raises(SpatialPresetError):
            explicit_placements(_rows([(11, SPATIAL_PRESET_MAX_ABS + 1.0, 0.0, 0.0)]))

    def test_it_refuses_a_non_finite_coordinate(self):
        with pytest.raises(SpatialPresetError):
            explicit_placements(_rows([(11, float("inf"), 0.0, 0.0)]))

    def test_it_refuses_a_repeated_fid(self):
        with pytest.raises(SpatialPresetError):
            explicit_placements(_rows([(11, 0.0, 0.0, 0.0), (11, 1.0, 0.0, 0.0)]))

    def test_it_refuses_a_missing_axis(self):
        with pytest.raises(SpatialPresetError):
            explicit_placements([dict(fid=11, x=0.0, y=0.0)])

    def test_it_refuses_an_unknown_key(self):
        # 오타 난 축이 조용히 무시되면 그 장비는 원래 자리에 남는다.
        with pytest.raises(SpatialPresetError):
            explicit_placements([dict(fid=11, x=0.0, y=0.0, z=0.0, rotx=90.0)])

    def test_it_refuses_a_non_numeric_coordinate(self):
        with pytest.raises(SpatialPresetError):
            explicit_placements([dict(fid=11, x="1.0", y=0.0, z=0.0)])

    def test_it_refuses_a_boolean_coordinate(self):
        # `True` 는 파이썬에서 int 라 숫자 검사를 그냥 통과하면 1.0 미터가 된다.
        with pytest.raises(SpatialPresetError):
            explicit_placements([dict(fid=11, x=True, y=0.0, z=0.0)])

    def test_it_refuses_an_empty_list(self):
        with pytest.raises(SpatialPresetError):
            explicit_placements([])


class TestExplicitArrangeTool:
    """봉투 — 백업 → 정적 범위검사 → 쓰기 → 되읽기 가 그대로 걸리는가."""

    def test_it_writes_exactly_the_given_coordinates_and_verifies_them(self):
        console = rig(4)

        _execution, payload = arrange(
            console,
            dict(
                preset=EXPLICIT_PRESET,
                fids=[11, 13],
                positions=_rows([(11, -5.0, -9.0, 7.5), (13, 1.0, 2.0, 0.2)]),
            ),
        )

        assert payload["status"] == "arranged"
        assert payload["verified"] is True
        assert console.coordinates(11) == pytest.approx((-5.0, -9.0, 7.5))
        assert console.coordinates(13) == pytest.approx((1.0, 2.0, 0.2))
        # 이름 없는 장비는 안 움직인다.
        assert console.coordinates(12) == (0.0, 0.0, 0.0)
        assert console.written_fids == set([11, 13])

    def test_the_backup_is_read_before_the_first_write(self):
        console = rig(4)

        arrange(
            console,
            dict(preset=EXPLICIT_PRESET, fids=[11], positions=_rows([(11, 1.0, 2.0, 3.0)])),
        )

        kinds = [kind for kind, _detail in console.calls]
        assert "write" in kinds
        assert kinds.index("read") < kinds.index("write")

    def test_the_restore_bundle_carries_the_original_coordinates(self):
        console = ArrangeConsole([(1, 11, "PAR 1", 4.25, -1.5, 9.9)])

        _execution, payload = arrange(
            console,
            dict(preset=EXPLICIT_PRESET, fids=[11], positions=_rows([(11, 0.0, 0.0, 0.0)])),
        )

        assert payload["backup"] == [dict(fid=11, slot=1, name="PAR 1", x=4.25, y=-1.5, z=9.9)]
        assert payload["restore_bundle"] == [
            "Set Fixture 11 Posx '4.25'",
            "Set Fixture 11 Posy '-1.5'",
            "Set Fixture 11 Posz '9.9'",
        ]

    def test_a_lying_console_is_caught_by_the_readback(self):
        # 실측된 거짓말: 부호를 떨어뜨리고도 OK 를 답한다(§E.2.6a).
        console = ArrangeConsole(
            [(1, 11, "PAR 1", 0.0, 0.0, 0.0)], lies=dict([((11, "Posx"), 5.0)])
        )

        execution, payload = arrange(
            console,
            dict(preset=EXPLICIT_PRESET, fids=[11], positions=_rows([(11, -5.0, 0.0, 0.0)])),
        )

        assert execution.result.is_error is True
        assert payload["status"] == "verification_failed"
        assert payload["verified"] is False
        assert payload["mismatches"][0]["axis"] == "Posx"

    def test_a_target_whose_coordinates_cannot_be_read_cancels_the_whole_write(self):
        console = rig(4, unreadable=set([(1, "posx")]))

        execution, payload = arrange(
            console,
            dict(
                preset=EXPLICIT_PRESET,
                fids=[11, 12],
                positions=_rows([(11, 1.0, 0.0, 0.0), (12, 2.0, 0.0, 0.0)]),
            ),
        )

        assert execution.result.is_error is True
        assert payload["status"] == "refused"
        assert console.writes == []


class TestExplicitScopeDeclaration:
    """`fids` 와 `positions` 가 어긋나면 아무것도 안 나간다.

    두 자리에 같은 목록을 적게 하는 것은 중복이 아니라 **선언**이다:
    `fids` 는 이 호출이 건드리겠다고 선언한 범위이고, 정적 범위검사
    (`arrange_scope_violations`)가 바로 그 목록에 대고 명령문을 검사한다.
    선언과 좌표가 어긋난 채 통과하면 그 정적 검사가 자기 자신을 검사하게 된다.
    """

    def test_a_fid_missing_from_the_declared_scope_is_refused(self):
        console = rig(4)

        execution, _payload = arrange(
            console,
            dict(
                preset=EXPLICIT_PRESET,
                fids=[11],
                positions=_rows([(11, 1.0, 0.0, 0.0), (12, 2.0, 0.0, 0.0)]),
            ),
        )

        assert execution.result.is_error is True
        assert console.calls == []

    def test_a_different_order_is_refused(self):
        console = rig(4)

        execution, _payload = arrange(
            console,
            dict(
                preset=EXPLICIT_PRESET,
                fids=[12, 11],
                positions=_rows([(11, 1.0, 0.0, 0.0), (12, 2.0, 0.0, 0.0)]),
            ),
        )

        assert execution.result.is_error is True
        assert console.calls == []

    def test_the_matching_declaration_is_accepted(self):
        # 팔 2 — 위 두 거절이 「이 경로는 늘 거절한다」가 아님을 보인다.
        console = rig(4)

        execution, payload = arrange(
            console,
            dict(
                preset=EXPLICIT_PRESET,
                fids=[11, 12],
                positions=_rows([(11, 1.0, 0.0, 0.0), (12, 2.0, 0.0, 0.0)]),
            ),
        )

        assert execution.result.is_error is False
        assert payload["verified"] is True

    def test_explicit_takes_no_shape_parameters(self):
        console = rig(4)

        execution, _payload = arrange(
            console,
            dict(
                preset=EXPLICIT_PRESET,
                fids=[11],
                positions=_rows([(11, 1.0, 0.0, 0.0)]),
                spacing=2.0,
            ),
        )

        assert execution.result.is_error is True
        assert console.calls == []


class TestExplicitSchema:
    def test_the_preset_vocabulary_gained_exactly_one_entry(self):
        assert ARRANGE_PRESETS == ("grid", "row", "circle", "triangle", "elevation", "explicit")

    def test_the_schema_advertises_it(self):
        definition = next(d for d in registry(rig()).definitions() if d.name == "arrange_fixtures")
        assert definition.parameters["properties"]["preset"]["enum"] == list(ARRANGE_PRESETS)
        assert "positions" in definition.parameters["properties"]


_POS_SHEET = "\n".join(
    [
        "ID,StageMeaning,TargetGroup,RecordGuide",
        "POS.01,보컬 센터 페이스,KEY,보컬 얼굴",
    ]
)


class TestLabelProvenance:
    """라벨 꼬리가 **좌표의 출처**를 나른다 — 조인 키는 첫 토큰 그대로.

    기본값은 「산출값」(조준값이 계산된 것)이지만, 좌표 자체가 합성이면 그것이
    더 강한 주장이라 호출자가 꼬리를 바꿔 실을 수 있어야 한다. 「· 산출값」만
    붙은 라벨은 **좌표는 실측인데 조준만 계산했다**로 읽힌다.
    """

    def _derive(self, **kwargs):
        rows = parse_position_sheet(_POS_SHEET)
        members = dict(KEY=(101, 102))
        coordinates = dict([(101, (-2.0, 4.0, 6.0)), (102, (2.0, 4.0, 6.0))])
        return derive_position_presets(rows, members, coordinates, **kwargs)

    def test_the_default_suffix_is_unchanged(self):
        assert DERIVED_LABEL_SUFFIX == "산출값"
        derived = self._derive().derived
        assert derived[0].label.endswith(" · 산출값")

    def test_a_caller_can_declare_the_coordinates_synthetic(self):
        assert SYNTHETIC_LABEL_SUFFIX == "합성좌표"
        derived = self._derive(label_suffix=SYNTHETIC_LABEL_SUFFIX).derived
        # 첫 어절은 `POS01` — 콘솔이 `.` 을 지우므로 우리가 먼저 뺀다(t224 실측).
        assert derived[0].label == "POS01 보컬 센터 페이스 · 합성좌표"

    def test_the_join_key_stays_the_first_token(self):
        default = self._derive().derived[0].label
        synthetic = self._derive(label_suffix=SYNTHETIC_LABEL_SUFFIX).derived[0].label
        assert default.split()[0] == synthetic.split()[0] == "POS01"
        # 그리고 그 어절은 시트 정본 키로 되돌아간다 — 꼬리와 무관하게.
        assert preset_id_from_console_head(default.split()[0]) == "POS.01"

    def test_an_empty_suffix_is_refused(self):
        # 꼬리를 지우는 것은 출처 표기를 지우는 것이다.
        with pytest.raises(ValueError):
            self._derive(label_suffix="   ")


class TestCoordsSheetParser:
    """좌표 CSV 판독 — 조용히 건너뛰지 않는다.

    한 대가 빠진 리그는 좌표가 0 인 리그보다 알아보기 어렵다: 나머지 85대가
    제자리에 있으면 그 한 대는 눈에 안 띈다. 그래서 결손·비숫자는 거절이다.
    """

    def test_it_reads_the_four_load_bearing_columns(self):
        text = "\n".join(
            [
                "FID,Group,FixtureType,Position,X,Y,Z",
                "101,KEY,ETC S4,FOH 브리지,-5.0,-9.0,7.5",
                "102,KEY,ETC S4,FOH 브리지,-3.0,-9.0,7.5",
            ]
        )

        assert parse_coords_sheet(text) == [
            dict(fid=101, x=-5.0, y=-9.0, z=7.5),
            dict(fid=102, x=-3.0, y=-9.0, z=7.5),
        ]

    def test_a_missing_column_is_refused(self):
        with pytest.raises(ValueError):
            parse_coords_sheet("FID,X,Y\n101,1.0,2.0\n")

    def test_a_non_numeric_coordinate_is_refused_rather_than_skipped(self):
        with pytest.raises(ValueError):
            parse_coords_sheet("FID,X,Y,Z\n101,1.0,2.0,TBD\n")

    def test_an_empty_sheet_is_refused(self):
        with pytest.raises(ValueError):
            parse_coords_sheet("FID,X,Y,Z\n")

    def test_the_canonical_rig_sheet_parses_to_eighty_six_rows(self):
        # 정본에 대고 잰다 — 합성 파일이 「없다」를 만들어 내지 않게.
        path = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "Lighting_Designer"
            / "02_RIG팩"
            / "LXSEQ_RIG_01_ShowBase_r3.coords.csv"
        )
        rows = parse_coords_sheet(path.read_text(encoding="utf-8-sig"))

        assert len(rows) == 86
        assert len(set(row["fid"] for row in rows)) == 86
        # t221 이 잰 퇴화(전 축 span 0)의 반대 — 이 시트는 폭을 갖는다.
        assert max(r["x"] for r in rows) - min(r["x"] for r in rows) > 1.0
        assert max(r["y"] for r in rows) - min(r["y"] for r in rows) > 1.0

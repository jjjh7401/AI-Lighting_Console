"""SPEC-LDBEAT-001 M8 — ``app_movement``·``evidence`` 구조화 필드 + 검증
(카드 t548). 콘솔 접촉 0건, 콘솔 쓰기 0건.

이 시험이 재는 것:

1. 레거시/일부 선언 칸 정규화 — ``app_movement``·``evidence`` 둘 다 `label`
   파싱 없이 명시적으로만 채워진다(REQ-LDBEAT-006(ii-2)와 같은 금지,
   AC-LDBEAT-016(n)).
2. LOVE ATTACK 네 목표 칸(MOVER-U bar 11·18, MOVER-D bar 7·22)이
   `app_movement`로 채워졌는지(AC-016(n)).
3. 12칸의 `evidence.grade`(AC-016(o))·`evidence.approval`(AC-016(p)) —
   `.moai/reports/t543/proposal-table.md` 전수 재독 기준 측정 2·다른 그룹
   실측 2·이름만 8.
4. 같은 축 배타성 검증(AC-016(t))과 기준 위치 Pan 단독 경고(감독 결정④).
5. `evidence`/`source_ref` 분리 보존(§B 위험 16 — plan.md M8 (4)).
"""

from __future__ import annotations

from server.design.beat_grid import (
    LOVE_ATTACK_TITLE,
    check_app_movement_axis_conflict,
    check_evidence_approval,
    default_beat_grid,
    normalize_beat_grid_cue,
    pan_only_vertical_base_warning,
)

_PROPOSAL_TABLE = ".moai/reports/t543/proposal-table.md"
_APPROVAL_DATE = "2026-10-10"


def _grid():
    return default_beat_grid(LOVE_ATTACK_TITLE)


def _cues_by_name(grid):
    return {t["group_name"]: {c["bar"]: c for c in t["cues"]} for t in grid["tracks"]}


class TestNormalizeAppMovementAndEvidence:
    def test_legacy_cell_has_both_fields_none(self) -> None:
        cue = normalize_beat_grid_cue({"bar": 1, "label": "레거시"})
        assert cue["app_movement"] is None
        assert cue["evidence"] is None

    def test_declared_app_movement_normalizes_every_sub_field(self) -> None:
        cue = normalize_beat_grid_cue(
            {
                "bar": 11,
                "label": "기울인 자리에서 느린 팬 흔들기",
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Pan"],
                    "period_unit": None,
                    "period_value": None,
                    "phase_spread": None,
                },
            }
        )
        assert cue["app_movement"] == {
            "shape": "wave",
            "axes": ("Pan",),
            "period_unit": None,
            "period_value": None,
            "phase_spread": None,
        }

    def test_declared_evidence_normalizes_grade_and_approval(self) -> None:
        cue = normalize_beat_grid_cue(
            {
                "bar": 7,
                "label": "FOH 켬",
                "evidence": {
                    "grade": "name_only",
                    "approval": {"by": "supervisor", "date": "2026-10-10", "source": "x#1"},
                },
            }
        )
        assert cue["evidence"] == {
            "grade": "name_only",
            "approval": {"by": "supervisor", "date": "2026-10-10", "source": "x#1"},
        }

    def test_partial_evidence_without_approval_normalizes_approval_to_none(self) -> None:
        cue = normalize_beat_grid_cue({"bar": 0, "label": "x", "evidence": {"grade": "measured"}})
        assert cue["evidence"] == {"grade": "measured", "approval": None}

    def test_label_parsing_for_app_movement_or_evidence_is_absent_from_source(self) -> None:
        import inspect

        from server.design import beat_grid as beat_grid_module

        source = inspect.getsource(beat_grid_module)
        # REQ-LDBEAT-006(ii-2) 확장 — label 파싱용 정규식/문자열 분해가 전혀
        # 없다는 사실은 이미 (ii-2) 시험이 재지만, app_movement/evidence도
        # 같은 금지에 묶인다는 것을 이 시험이 명시적으로 재확인한다.
        assert "pan_sway" not in source
        assert "tilt_wave" not in source


class TestFourTargetCellsCarryAppMovement:
    """AC-LDBEAT-016(n) — MOVER-U bar 11·18, MOVER-D bar 7·22."""

    def test_mover_u_bar11_pan_wave_no_period(self) -> None:
        cue = _cues_by_name(_grid())["MOVER-U"][11]
        assert cue["app_movement"] == {
            "shape": "wave",
            "axes": ("Pan",),
            "period_unit": None,
            "period_value": None,
            "phase_spread": None,
        }

    def test_mover_u_bar18_pan_wave_two_beats(self) -> None:
        cue = _cues_by_name(_grid())["MOVER-U"][18]
        assert cue["app_movement"]["shape"] == "wave"
        assert cue["app_movement"]["axes"] == ("Pan",)
        assert cue["app_movement"]["period_unit"] == "beat"
        assert cue["app_movement"]["period_value"] == 2
        # position_preset_no는 그대로 보존(§B 위험 16).
        assert cue["position_preset_no"] == "2.1"

    def test_mover_d_bar7_tilt_wave_two_bars_phase_spread(self) -> None:
        cue = _cues_by_name(_grid())["MOVER-D"][7]
        assert cue["app_movement"]["shape"] == "wave"
        assert cue["app_movement"]["axes"] == ("Tilt",)
        assert cue["app_movement"]["period_unit"] == "bar"
        assert cue["app_movement"]["period_value"] == 2
        assert cue["app_movement"]["phase_spread"] is True

    def test_mover_d_bar22_tilt_wave_two_beats(self) -> None:
        cue = _cues_by_name(_grid())["MOVER-D"][22]
        assert cue["app_movement"]["shape"] == "wave"
        assert cue["app_movement"]["axes"] == ("Tilt",)
        assert cue["app_movement"]["period_unit"] == "beat"
        assert cue["app_movement"]["period_value"] == 2

    def test_mover_u_bar11_has_no_period_invented(self) -> None:
        # bar 11 레이블은 주기를 말하지 않는다 — 지어내지 않는다(REQ-015(f)와
        # 같은 원칙).
        cue = _cues_by_name(_grid())["MOVER-U"][11]
        assert cue["app_movement"]["period_unit"] is None
        assert cue["app_movement"]["period_value"] is None


class TestEvidenceGradeAndApproval:
    """AC-LDBEAT-016(o)(p) — 12칸, `.moai/reports/t543/proposal-table.md`
    전수 재독 기준(측정 2·다른 그룹 실측 2·이름만 8), 전부 승인."""

    # (group_name, bar, 제안표 행 번호, grade)
    _TWELVE = (
        ("FOH", 7, 1, "name_only"),
        ("BACK", 3, 5, "name_only"),
        ("BACK", 7, 6, "name_only"),
        ("BACK", 18, 9, "name_only"),
        ("BACK", 22, 10, "name_only"),
        ("SIDE-ALL", 11, 14, "name_only"),
        ("SIDE-ALL", 14, 15, "name_only"),
        ("MOVER-U", 14, 22, "measured"),
        ("MOVER-U", 18, 23, "measured"),
        ("MOVER-D", 14, 29, "measured_other_group"),
        ("MOVER-D", 18, 30, "measured_other_group"),
        ("BLIND", 17, 32, "name_only"),
    )

    def test_all_twelve_cells_carry_the_expected_grade(self) -> None:
        by_name = _cues_by_name(_grid())
        for group_name, bar, _row, grade in self._TWELVE:
            cue = by_name[group_name][bar]
            assert cue["evidence"] is not None, f"{group_name}@{bar} missing evidence"
            assert cue["evidence"]["grade"] == grade, f"{group_name}@{bar}"

    def test_grade_classification_counts_two_two_eight(self) -> None:
        grades = [grade for *_rest, grade in self._TWELVE]
        assert grades.count("measured") == 2
        assert grades.count("measured_other_group") == 2
        assert grades.count("name_only") == 8

    def test_all_twelve_cells_carry_complete_supervisor_approval(self) -> None:
        by_name = _cues_by_name(_grid())
        for group_name, bar, row, _grade in self._TWELVE:
            cue = by_name[group_name][bar]
            approval = cue["evidence"]["approval"]
            assert approval is not None, f"{group_name}@{bar} missing approval"
            assert approval["by"] == "supervisor"
            assert approval["date"] == _APPROVAL_DATE
            assert _PROPOSAL_TABLE in approval["source"]
            assert f"#{row}" in approval["source"]

    def test_source_ref_untouched_for_cells_that_already_had_it(self) -> None:
        # §B 위험 16 — evidence 신설이 기존 source_ref 값을 바꾸지 않는다.
        by_name = _cues_by_name(_grid())
        assert by_name["FOH"][7]["source_ref"] == "reports/effect-arrangement-rules-20261007.md:106"
        assert (
            by_name["BACK"][7]["source_ref"] == "reports/effect-arrangement-rules-20261007.md:106"
        )

    def test_negative_case_unapproved_cell_has_no_evidence_approval(self) -> None:
        # 음성 사례 — 제안표에 없는 임의의 13번째 "name_only" 칸을 흉내낸
        # fixture. check_evidence_approval이 그 칸을 거절해야 한다.
        unapproved = normalize_beat_grid_cue(
            {
                "bar": 99,
                "label": "임의 칸",
                "position_preset_no": "2.9",
                "evidence": {"grade": "name_only", "approval": None},
            }
        )
        assert check_evidence_approval(unapproved) is not None
        assert "REQ-LDBEAT-015" in check_evidence_approval(unapproved)

    def test_cell_with_no_preset_number_needs_no_approval(self) -> None:
        cue = normalize_beat_grid_cue({"bar": 0, "label": "앞박 1회"})
        assert check_evidence_approval(cue) is None

    def test_approved_measured_cell_passes(self) -> None:
        by_name = _cues_by_name(_grid())
        cue = by_name["MOVER-U"][14]
        assert check_evidence_approval(cue) is None


class TestSameAxisExclusivity:
    """AC-LDBEAT-016(t) — REQ-LDBEAT-006(vi-7)."""

    def test_tilt_app_movement_with_tilt_effect_conflicts(self) -> None:
        cue = normalize_beat_grid_cue(
            {
                "bar": 1,
                "label": "x",
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Tilt"],
                    "period_unit": "beat",
                    "period_value": 2,
                    "phase_spread": None,
                },
                "effect_preset_no": "21.9",
                "effect_kind": "position",
            }
        )
        reason = check_app_movement_axis_conflict(cue)
        assert reason is not None

    def test_mixed_effect_kind_also_conflicts(self) -> None:
        cue = normalize_beat_grid_cue(
            {
                "bar": 1,
                "label": "x",
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Pan"],
                    "period_unit": "beat",
                    "period_value": 2,
                    "phase_spread": None,
                },
                "effect_preset_no": "21.1",
                "effect_kind": "mixed",
            }
        )
        assert check_app_movement_axis_conflict(cue) is not None

    def test_non_overlapping_axes_do_not_conflict(self) -> None:
        # 양성 대조 — 밝기 효과 프리셋(dimmer) + Pan app_movement는 축이
        # 겹치지 않는다.
        cue = normalize_beat_grid_cue(
            {
                "bar": 1,
                "label": "x",
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Pan"],
                    "period_unit": "beat",
                    "period_value": 2,
                    "phase_spread": None,
                },
                "effect_preset_no": "21.1",
                "effect_kind": "dimmer",
            }
        )
        assert check_app_movement_axis_conflict(cue) is None

    def test_color_effect_kind_does_not_conflict(self) -> None:
        cue = normalize_beat_grid_cue(
            {
                "bar": 1,
                "label": "x",
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Tilt"],
                    "period_unit": "beat",
                    "period_value": 2,
                    "phase_spread": None,
                },
                "effect_preset_no": "4.5",
                "effect_kind": "color",
            }
        )
        assert check_app_movement_axis_conflict(cue) is None

    def test_no_app_movement_never_conflicts(self) -> None:
        cue = normalize_beat_grid_cue(
            {"bar": 1, "label": "x", "effect_preset_no": "21.1", "effect_kind": "mixed"}
        )
        assert check_app_movement_axis_conflict(cue) is None

    def test_mover_u_bar18_real_cell_has_no_conflict(self) -> None:
        # 실제 LOVE ATTACK 칸(position_preset_no만, effect_preset_no 없음)은
        # 당연히 충돌이 없다.
        cue = _cues_by_name(_grid())["MOVER-U"][18]
        assert check_app_movement_axis_conflict(cue) is None


class TestPanOnlyVerticalBaseWarning:
    """감독 결정④ — Pan 단독 + position_preset_no 없음은 경고(거절 아님)."""

    def test_pan_only_without_base_preset_warns(self) -> None:
        cue = normalize_beat_grid_cue(
            {
                "bar": 11,
                "label": "느린 팬 흔들기",
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Pan"],
                    "period_unit": None,
                    "period_value": None,
                    "phase_spread": None,
                },
            }
        )
        assert cue["position_preset_no"] is None
        assert pan_only_vertical_base_warning(cue) is not None

    def test_pan_only_with_base_preset_has_no_warning(self) -> None:
        cue = normalize_beat_grid_cue(
            {
                "bar": 18,
                "label": "x",
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Pan"],
                    "period_unit": "beat",
                    "period_value": 2,
                    "phase_spread": None,
                },
                "position_preset_no": "2.1",
            }
        )
        assert pan_only_vertical_base_warning(cue) is None

    def test_tilt_only_never_warns_regardless_of_base(self) -> None:
        cue = normalize_beat_grid_cue(
            {
                "bar": 7,
                "label": "x",
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Tilt"],
                    "period_unit": "bar",
                    "period_value": 2,
                    "phase_spread": True,
                },
            }
        )
        assert pan_only_vertical_base_warning(cue) is None

    def test_no_app_movement_never_warns(self) -> None:
        cue = normalize_beat_grid_cue({"bar": 0, "label": "x"})
        assert pan_only_vertical_base_warning(cue) is None

    def test_mover_u_bar11_real_cell_warns(self) -> None:
        # 실측(MOVER-U bar11)은 position_preset_no가 없다 — 경고가 떠야 한다.
        cue = _cues_by_name(_grid())["MOVER-U"][11]
        assert pan_only_vertical_base_warning(cue) is not None

    def test_mover_u_bar18_real_cell_does_not_warn(self) -> None:
        cue = _cues_by_name(_grid())["MOVER-U"][18]
        assert pan_only_vertical_base_warning(cue) is None

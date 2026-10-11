"""SPEC-LDBEAT-001 M3 — 새 서버측 그리드 편집 연산 ``apply_beat_grid_edit``
(카드 t551, REQ-LDBEAT-007~009·015).

이 모듈은 콘솔에 아무것도 쓰지 않는다 — 콘솔 접촉 0건, 콘솔 쓰기 0건.
``cue_sheet_edit.py`` 와 같은 모양(t281): 입력도 출력도 순수 파이썬 사전뿐,
명령 문자열도 ``ToolCall`` 도 여기 없다.

이 시험이 재는 것:

1. 편집 세 길(직접 고르기·문장·AI 제안)이 수렴하는 **하나의** 연산 —
   화이트리스트 밖 칸·값·그룹은 단일-원인 사유로 거절되고, 부분 적용은
   0건이다(REQ-LDBEAT-007/008).
2. 그룹/역할 스코프(REQ-LDBEAT-009, AC-LDBEAT-014) — 그룹 이름 또는 층
   역할 중 하나로 트랙을 고르고, 매칭 안 된 트랙은 diff 0.
3. 모양 어휘 닫힌 집합 + "⚠ 미확인" 플래그(REQ-LDBEAT-010) — circle·
   발리후는 거절이 아니라 경고.
4. 프리셋 풀 번호대(REQ-LDBEAT-015(a)(b)) — `effect_preset_no` 는 그
   `effect_kind` 의 풀 번호대 밖이면 거절. 번호대는 config/data 파일에서
   읽는다(코드 상수 아님).
5. 밝기 단일모드(REQ-LDBEAT-015(c))·근거 승인 재사용(REQ-LDBEAT-015(f)(g),
   `check_evidence_approval` 재사용)·ASCII 신규 프리셋 이름(REQ-LDBEAT-015(d)).
"""

from __future__ import annotations

import copy

import pytest

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_edit import (
    EDITABLE_CUE_FIELD_LABELS,
    BeatGridEditError,
    apply_beat_grid_edit,
    load_preset_pool_policy,
    resolve_track_scope,
    validate_preset_pool_assignment,
)


def _grid():
    return default_beat_grid(LOVE_ATTACK_TITLE)


def _cue(grid, group_name, bar):
    for track in grid["tracks"]:
        if track["group_name"] == group_name:
            for cue in track["cues"]:
                if cue["bar"] == bar:
                    return cue
    return None


def _policy_with_confirmed(confirmed: bool):
    """카드 t551 계속 — 실제 `preset_pools.yaml` 번호대는 그대로 두고
    ``confirmed`` 플래그만 바꾼 정책을 돌려주는 `load_preset_pool_policy`
    대체 호출자(monkeypatch 대상). 번호대 리터럴을 시험에 새로 베끼지
    않는다(코디네이터 지시 조건 1 — 번호대는 오직 yaml에서만)."""
    real_pools = load_preset_pool_policy()["pools"]

    def _loader(path=None):
        return {"confirmed": confirmed, "pools": real_pools}

    return _loader


# -- 변환 없음(기본 거절) ------------------------------------------------------


class TestNoPartialApply:
    def test_empty_changes_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(grid, bar=11, target="MOVER-U", changes={})

    def test_unknown_field_rejected_with_single_cause(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(grid, bar=11, target="MOVER-U", changes={"not_a_real_field": 1})
        message = str(excinfo.value)
        assert "not_a_real_field" in message
        # 단일 원인 — 수정 가능한 항목 안내가 함께 실려야 한다.
        assert any(label in message for label in EDITABLE_CUE_FIELD_LABELS.values())

    def test_rejected_edit_does_not_mutate_original_grid(self) -> None:
        grid = _grid()
        before = copy.deepcopy(grid)
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(grid, bar=11, target="MOVER-U", changes={})
        assert grid == before


# -- 그룹/역할 스코프(REQ-LDBEAT-009, AC-LDBEAT-014) --------------------------


class TestTrackScopeResolution:
    def test_exact_group_name_match_is_case_insensitive(self) -> None:
        grid = _grid()
        scope = resolve_track_scope(grid["tracks"], "mover-u")
        names = [grid["tracks"][i]["group_name"] for i in scope]
        assert names == ["MOVER-U"]

    def test_role_name_matches_every_track_sharing_that_role(self) -> None:
        grid = _grid()
        scope = resolve_track_scope(grid["tracks"], "mover")
        names = sorted(grid["tracks"][i]["group_name"] for i in scope)
        assert names == ["MOVER-D", "MOVER-U"]

    def test_unknown_target_resolves_to_empty_scope(self) -> None:
        grid = _grid()
        assert resolve_track_scope(grid["tracks"], "NO-SUCH-GROUP") == []


class TestGroupScopedEdit:
    def test_unknown_target_rejected_naming_known_tracks(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=11,
                target="NO-SUCH-GROUP",
                changes={"entry": {"fade_bars": 1, "mib_mode": None}},
            )
        message = str(excinfo.value)
        assert "NO-SUCH-GROUP" in message
        assert "MOVER-U" in message  # 이 곡의 알려진 트랙 하나가 안내에 실린다

    def test_exact_group_name_edits_only_that_track(self) -> None:
        grid = _grid()
        updated, report = apply_beat_grid_edit(
            grid,
            bar=11,
            target="MOVER-U",
            changes={"entry": {"fade_bars": 2, "mib_mode": None}},
        )
        assert _cue(updated, "MOVER-U", 11)["entry"]["fade_bars"] == 2
        # MOVER-D 는 같은 bar 11 에 큐가 있지만 건드리지 않는다.
        assert _cue(updated, "MOVER-D", 11) == _cue(grid, "MOVER-D", 11)
        assert any("MOVER-U" in line for line in report)

    def test_role_scope_edits_every_mapped_track_and_nothing_else(self) -> None:
        grid = _grid()
        updated, _report = apply_beat_grid_edit(
            grid,
            bar=11,
            target="mover",
            changes={"entry": {"fade_bars": 3, "mib_mode": None}},
        )
        assert _cue(updated, "MOVER-U", 11)["entry"]["fade_bars"] == 3
        assert _cue(updated, "MOVER-D", 11)["entry"]["fade_bars"] == 3
        # 다른 트랙(예: BACK)은 diff 0.
        assert _cue(updated, "BACK", 11) == _cue(grid, "BACK", 11)

    def test_editing_a_bar_with_no_existing_cue_creates_one(self) -> None:
        grid = _grid()
        assert _cue(grid, "STROBE", 5) is None
        updated, _report = apply_beat_grid_edit(
            grid,
            bar=5,
            target="STROBE",
            changes={"entry": {"fade_bars": 0, "mib_mode": None}},
        )
        new_cue = _cue(updated, "STROBE", 5)
        assert new_cue is not None
        assert new_cue["entry"]["fade_bars"] == 0

    def test_editing_one_field_preserves_source_ref_and_other_fields(self) -> None:
        # §B 위험 16 과 같은 원칙 — 다른 칸을 고쳐도 source_ref 는 안 바뀐다.
        grid = _grid()
        before = _cue(grid, "BACK", 7)
        assert before["source_ref"] is not None
        updated, _report = apply_beat_grid_edit(
            grid,
            bar=7,
            target="BACK",
            changes={"entry": {"fade_bars": 1, "mib_mode": None}},
        )
        after = _cue(updated, "BACK", 7)
        assert after["source_ref"] == before["source_ref"]
        assert after["brightness"] == before["brightness"]


# -- 모양 어휘 닫힌 집합 + 미확인 플래그(REQ-LDBEAT-010) ----------------------


class TestShapeVocabularyAndUnverifiedFlag:
    def test_invented_shape_name_is_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=11,
                target="MOVER-U",
                changes={
                    "app_movement": {
                        "shape": "pan_sway",
                        "axes": ["Pan"],
                        "period_unit": None,
                        "period_value": None,
                        "phase_spread": None,
                    }
                },
            )
        assert "pan_sway" in str(excinfo.value)

    def test_wave_shape_is_not_flagged_unverified(self) -> None:
        grid = _grid()
        _updated, report = apply_beat_grid_edit(
            grid,
            bar=11,
            target="MOVER-U",
            changes={
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Pan"],
                    "period_unit": "beat",
                    "period_value": 2,
                    "phase_spread": None,
                }
            },
        )
        assert not any("미확인" in line for line in report)

    def test_circle_shape_is_allowed_but_flagged_unverified(self) -> None:
        grid = _grid()
        _updated, report = apply_beat_grid_edit(
            grid,
            bar=11,
            target="MOVER-U",
            changes={
                "app_movement": {
                    "shape": "circle",
                    "axes": ["Pan", "Tilt"],
                    "period_unit": "beat",
                    "period_value": 4,
                    "phase_spread": None,
                }
            },
        )
        assert any("미확인" in line for line in report)

    def test_ballyhoo_shape_is_allowed_but_flagged_unverified(self) -> None:
        grid = _grid()
        _updated, report = apply_beat_grid_edit(
            grid,
            bar=18,
            target="MOVER-D",
            changes={
                "app_movement": {
                    "shape": "ballyhoo",
                    "axes": ["Tilt"],
                    "period_unit": "bar",
                    "period_value": 2,
                    "phase_spread": None,
                }
            },
        )
        assert any("미확인" in line for line in report)

    def test_invalid_axes_value_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(
                grid,
                bar=11,
                target="MOVER-U",
                changes={
                    "app_movement": {
                        "shape": "wave",
                        "axes": ["Yaw"],
                        "period_unit": None,
                        "period_value": None,
                        "phase_spread": None,
                    }
                },
            )

    def test_seconds_unit_rejected(self) -> None:
        # REQ-LDBEAT-006(vi-4) — 초 단위는 shall not.
        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=11,
                target="MOVER-U",
                changes={
                    "app_movement": {
                        "shape": "wave",
                        "axes": ["Pan"],
                        "period_unit": "seconds",
                        "period_value": 3,
                        "phase_spread": None,
                    }
                },
            )
        assert "seconds" in str(excinfo.value)

    def test_negative_period_value_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(
                grid,
                bar=11,
                target="MOVER-U",
                changes={
                    "app_movement": {
                        "shape": "wave",
                        "axes": ["Pan"],
                        "period_unit": "beat",
                        "period_value": -1,
                        "phase_spread": None,
                    }
                },
            )

    def test_same_axis_conflict_with_effect_preset_is_rejected(self) -> None:
        # REQ-LDBEAT-006(vi-7) — check_app_movement_axis_conflict 재사용.
        # SIDE-ALL bar 3 에는 기존 app_movement 가 없다 — 이번 변경만으로
        # 축 충돌이 나는지(기존 칸이 아니라) 깨끗하게 가린다. 풀/승인은
        # 먼저 통과시키고(근거 승인 포함) 축 충돌만 남겨 검사한다.
        grid = _grid()
        policy = load_preset_pool_policy()
        band = policy["pools"]["position_effect"]
        inside = str((float(band["start"]) + float(band["end"])) / 2)
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=3,
                target="SIDE-ALL",
                changes={
                    "effect_preset_no": inside,
                    "effect_kind": "position",
                    "evidence": {
                        "grade": "name_only",
                        "approval": {
                            "by": "supervisor",
                            "date": "2026-10-11",
                            "source": ".moai/reports/t551/approval.md#1",
                        },
                    },
                    "app_movement": {
                        "shape": "wave",
                        "axes": ["Tilt"],
                        "period_unit": "beat",
                        "period_value": 2,
                        "phase_spread": None,
                    },
                },
            )
        assert "REQ-LDBEAT-006" in str(excinfo.value)


# -- 밝기 단일모드(REQ-LDBEAT-015(c)) -----------------------------------------


class TestBrightnessSingleMode:
    def test_two_brightness_modes_at_once_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(
                grid,
                bar=7,
                target="FOH",
                changes={
                    "brightness": {
                        "mode": "value",
                        "value_percent": 50,
                        "preset_no": "1.5",
                    }
                },
            )

    def test_single_value_mode_is_accepted(self) -> None:
        grid = _grid()
        updated, _report = apply_beat_grid_edit(
            grid,
            bar=3,
            target="BACK",
            changes={"brightness": {"mode": "value", "value_percent": 40, "preset_no": None}},
        )
        cue = _cue(updated, "BACK", 3)
        assert cue["brightness"]["mode"] == "value"
        assert cue["brightness"]["value_percent"] == 40

    def test_value_percent_out_of_range_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(
                grid,
                bar=3,
                target="BACK",
                changes={
                    "brightness": {
                        "mode": "value",
                        "value_percent": 150,
                        "preset_no": None,
                    }
                },
            )


# -- 프리셋 풀 번호대(REQ-LDBEAT-015(a)(b), config/data 소스) -----------------


class TestPresetPoolPolicy:
    def test_policy_loads_from_data_file_not_hardcoded_in_module(self) -> None:
        import inspect

        from server.design import beat_grid_edit as module

        policy = load_preset_pool_policy()
        assert isinstance(policy, dict)
        assert "pools" in policy
        assert "confirmed" in policy
        source = inspect.getsource(module)
        # 번호대 숫자 리터럴이 모듈 소스에 상수로 적혀 있지 않다 — 데이터
        # 파일에서 읽는다(카드 지시 — "do not hardcode").
        assert "2.61" not in source
        assert "4.41" not in source

    def test_number_inside_declared_band_passes(self) -> None:
        policy = load_preset_pool_policy()
        band = policy["pools"]["position_effect"]
        midpoint = str((float(band["start"]) + float(band["end"])) / 2)
        assert validate_preset_pool_assignment("position", midpoint, policy) is None

    def test_number_outside_declared_band_is_rejected(self) -> None:
        policy = load_preset_pool_policy()
        reason = validate_preset_pool_assignment("position", "99.99", policy)
        assert reason is not None
        assert "REQ-LDBEAT-015" in reason

    def test_base_pool_fields_are_not_band_checked(self) -> None:
        # position_preset_no/color_preset_no 는 기본 풀 참조라 번호대 검사
        # 대상이 아니다(REQ-LDBEAT-015(b) — 효과 풀만 분리 대상).
        grid = _grid()
        updated, _report = apply_beat_grid_edit(
            grid,
            bar=3,
            target="BACK",
            changes={"position_preset_no": "2.99"},
        )
        assert _cue(updated, "BACK", 3)["position_preset_no"] == "2.99"

    def test_effect_preset_outside_pool_band_rejected_via_apply(self, monkeypatch) -> None:
        # 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 3) — 번호대 밖
        # 거절은 이제 confirmed:true 일 때만 unconditional 하다. 이 시험은
        # confirmed:true 로 monkeypatch 해 그 경로를 그대로 격리해서 잰다
        # (실제 preset_pools.yaml 은 confirmed:false 라, 이 monkeypatch 없이는
        # 이 시험이 "번호대 거절"이 아니라 "근거 승인 누락" 거절을 재는
        # 것으로 조용히 바뀐다 — 아래 `_policy_with_confirmed` 참조).
        import server.design.beat_grid_edit as module

        monkeypatch.setattr(module, "load_preset_pool_policy", _policy_with_confirmed(True))
        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=11,
                target="MOVER-U",
                changes={"effect_preset_no": "99.99", "effect_kind": "position"},
            )
        assert "REQ-LDBEAT-015" in str(excinfo.value)


class TestPresetPoolBandWarningWhileUnconfirmed:
    """카드 t551 계속(코디네이터 지시 2026-10-11, 조건 3) — confirmed:false
    인 동안 번호대 밖 숫자는 거절이 아니라 경고다(REQ-LDBEAT-010의 "실기
    미확인 모양" 경고-아닌-거절 관행과 같은 모양). confirmed:true면 거절은
    그대로 유지한다(회귀 방지). 두 호출 경로(effect_preset_no·
    brightness.mode=="dimmer_effect") 모두 TDD한다.

    근거 승인(REQ-LDBEAT-015(f)(g))과 섞이지 않도록 모든 양성(수락) 시험은
    완전한 ``evidence.approval``을 함께 보낸다 — 아니면 번호대가 통과해도
    근거 승인 누락으로 다시 거절돼 이 시험이 무엇을 재는지 흐려진다."""

    _APPROVAL = {
        "grade": "name_only",
        "approval": {"by": "supervisor", "date": "2026-10-11", "source": "t551 band-warning test"},
    }

    def test_effect_preset_out_of_band_warns_not_rejects_while_unconfirmed(
        self, monkeypatch
    ) -> None:
        import server.design.beat_grid_edit as module

        monkeypatch.setattr(module, "load_preset_pool_policy", _policy_with_confirmed(False))
        grid = _grid()
        updated, report = apply_beat_grid_edit(
            grid,
            bar=3,
            target="BACK",
            changes={
                "effect_preset_no": "99.99",
                "effect_kind": "position",
                "evidence": self._APPROVAL,
            },
        )
        assert _cue(updated, "BACK", 3)["effect_preset_no"] == "99.99"
        assert any("번호대 미확인" in line for line in report)

    def test_effect_preset_out_of_band_still_rejected_when_confirmed(self, monkeypatch) -> None:
        import server.design.beat_grid_edit as module

        monkeypatch.setattr(module, "load_preset_pool_policy", _policy_with_confirmed(True))
        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=3,
                target="BACK",
                changes={
                    "effect_preset_no": "99.99",
                    "effect_kind": "position",
                    "evidence": self._APPROVAL,
                },
            )
        assert "REQ-LDBEAT-015" in str(excinfo.value)

    def test_dimmer_effect_preset_out_of_band_warns_not_rejects_while_unconfirmed(
        self, monkeypatch
    ) -> None:
        import server.design.beat_grid_edit as module

        monkeypatch.setattr(module, "load_preset_pool_policy", _policy_with_confirmed(False))
        grid = _grid()
        updated, report = apply_beat_grid_edit(
            grid,
            bar=3,
            target="BACK",
            changes={
                "brightness": {
                    "mode": "dimmer_effect",
                    "value_percent": None,
                    "preset_no": "99.99",
                },
                "evidence": self._APPROVAL,
            },
        )
        assert _cue(updated, "BACK", 3)["brightness"]["preset_no"] == "99.99"
        assert any("번호대 미확인" in line for line in report)

    def test_dimmer_effect_preset_out_of_band_still_rejected_when_confirmed(
        self, monkeypatch
    ) -> None:
        import server.design.beat_grid_edit as module

        monkeypatch.setattr(module, "load_preset_pool_policy", _policy_with_confirmed(True))
        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=3,
                target="BACK",
                changes={
                    "brightness": {
                        "mode": "dimmer_effect",
                        "value_percent": None,
                        "preset_no": "99.99",
                    },
                    "evidence": self._APPROVAL,
                },
            )
        assert "REQ-LDBEAT-015" in str(excinfo.value)


# -- 근거 승인 재사용(REQ-LDBEAT-015(f)(g), check_evidence_approval) ----------


class TestEvidenceApprovalReuse:
    def test_new_effect_preset_number_without_approval_is_rejected(self) -> None:
        grid = _grid()
        policy = load_preset_pool_policy()
        band = policy["pools"]["position_effect"]
        inside = str((float(band["start"]) + float(band["end"])) / 2)
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=11,
                target="MOVER-U",
                changes={"effect_preset_no": inside, "effect_kind": "position"},
            )
        assert "REQ-LDBEAT-015" in str(excinfo.value)

    def test_new_effect_preset_number_with_full_approval_is_accepted(self) -> None:
        # BACK bar 3 에는 기존 app_movement 가 없다 — MOVER-U bar 11(기존
        # app_movement=Pan)을 쓰면 effect_kind="position"의 축 모호성과
        # 충돌해 다른 이유로 거절된다(별도 시험이 그 경로를 직접 가린다).
        grid = _grid()
        policy = load_preset_pool_policy()
        band = policy["pools"]["position_effect"]
        inside = str((float(band["start"]) + float(band["end"])) / 2)
        updated, _report = apply_beat_grid_edit(
            grid,
            bar=3,
            target="BACK",
            changes={
                "effect_preset_no": inside,
                "effect_kind": "position",
                "evidence": {
                    "grade": "name_only",
                    "approval": {
                        "by": "supervisor",
                        "date": "2026-10-11",
                        "source": ".moai/reports/t551/approval.md#1",
                    },
                },
            },
        )
        cue = _cue(updated, "BACK", 3)
        assert cue["effect_preset_no"] == inside
        assert cue["evidence"]["approval"]["by"] == "supervisor"


# -- evidence.grade 닫힌 집합 ---------------------------------------------


class TestEvidenceGradeClosedSet:
    def test_invalid_grade_value_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(
                grid,
                bar=7,
                target="FOH",
                changes={"evidence": {"grade": "pretty_sure", "approval": None}},
            )


# -- 들어올 때(entry)/MIB(REQ-LDBEAT-006(i-4)) --------------------------------


class TestEntryField:
    def test_negative_fade_bars_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(
                grid,
                bar=7,
                target="BACK",
                changes={"entry": {"fade_bars": -1, "mib_mode": None}},
            )

    def test_unknown_mib_mode_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit(
                grid,
                bar=7,
                target="BACK",
                changes={"entry": {"fade_bars": 0, "mib_mode": "not_a_mode"}},
            )

    def test_valid_mib_mode_accepted(self) -> None:
        grid = _grid()
        updated, _report = apply_beat_grid_edit(
            grid,
            bar=7,
            target="BACK",
            changes={"entry": {"fade_bars": 1, "mib_mode": "dark"}},
        )
        assert _cue(updated, "BACK", 7)["entry"]["mib_mode"] == "dark"


# -- ASCII 신규 프리셋 이름(REQ-LDBEAT-015(d)) --------------------------------


class TestAsciiPresetLabel:
    def test_korean_characters_in_new_preset_label_rejected(self) -> None:
        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit(
                grid,
                bar=11,
                target="MOVER-U",
                changes={"new_preset_label": "느린 웨이브"},
            )
        assert "ASCII" in str(excinfo.value) or "영문" in str(excinfo.value)

    def test_ascii_only_new_preset_label_is_accepted_and_reported(self) -> None:
        grid = _grid()
        updated, report = apply_beat_grid_edit(
            grid,
            bar=11,
            target="MOVER-U",
            changes={"new_preset_label": "Slow Wave"},
        )
        assert any("Slow Wave" in line for line in report)
        # new_preset_label 은 칸 필드로 저장되지 않는다(요청 메타데이터일 뿐).
        assert "new_preset_label" not in _cue(updated, "MOVER-U", 11)


# -- 마디 범위(mockup 「22~25마디」 그대로, 카드 t551 후속) -------------------


class TestApplyRange:
    def test_range_edits_every_existing_cue_in_bounds(self) -> None:
        from server.design.beat_grid_edit import apply_beat_grid_edit_range

        grid = _grid()
        # MOVER-U 는 0,3,7,11,14,18,22 마디에 큐가 있다 — 3~14 범위엔 3/7/11/14.
        updated, report = apply_beat_grid_edit_range(
            grid,
            bar_start=3,
            bar_end=14,
            target="MOVER-U",
            changes={"entry": {"fade_bars": 1, "mib_mode": None}},
        )
        for bar in (3, 7, 11, 14):
            assert _cue(updated, "MOVER-U", bar)["entry"]["fade_bars"] == 1
        # 범위 밖(0·18·22)은 그대로.
        assert _cue(updated, "MOVER-U", 0) == _cue(grid, "MOVER-U", 0)
        assert _cue(updated, "MOVER-U", 18) == _cue(grid, "MOVER-U", 18)
        assert len(report) == 4

    def test_range_with_no_matching_cues_is_rejected_with_boundaries(self) -> None:
        from server.design.beat_grid_edit import apply_beat_grid_edit_range

        grid = _grid()
        with pytest.raises(BeatGridEditError) as excinfo:
            apply_beat_grid_edit_range(
                grid,
                bar_start=100,
                bar_end=110,
                target="MOVER-U",
                changes={"entry": {"fade_bars": 1, "mib_mode": None}},
            )
        assert "100" in str(excinfo.value) and "110" in str(excinfo.value)

    def test_range_does_not_create_new_cues(self) -> None:
        from server.design.beat_grid_edit import apply_beat_grid_edit_range

        grid = _grid()
        assert _cue(grid, "STROBE", 5) is None
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit_range(
                grid,
                bar_start=0,
                bar_end=25,
                target="STROBE",
                changes={"entry": {"fade_bars": 1, "mib_mode": None}},
            )

    def test_range_rejection_leaves_grid_unchanged(self) -> None:
        from server.design.beat_grid_edit import apply_beat_grid_edit_range

        grid = _grid()
        before = copy.deepcopy(grid)
        with pytest.raises(BeatGridEditError):
            apply_beat_grid_edit_range(
                grid,
                bar_start=3,
                bar_end=14,
                target="MOVER-U",
                changes={"not_a_real_field": 1},
            )
        assert grid == before

    def test_single_bar_range_matches_apply_beat_grid_edit(self) -> None:
        from server.design.beat_grid_edit import apply_beat_grid_edit_range

        grid = _grid()
        updated, report = apply_beat_grid_edit_range(
            grid,
            bar_start=7,
            bar_end=7,
            target="BACK",
            changes={"entry": {"fade_bars": 2, "mib_mode": None}},
        )
        assert _cue(updated, "BACK", 7)["entry"]["fade_bars"] == 2
        assert len(report) == 1

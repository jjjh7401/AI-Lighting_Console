"""SPEC-LDBEAT-001 M4 후속 — 측정된 무빙 허용목록 (카드 t553,
REQ-LDBEAT-001/006(vi)).

M1 ⑤⑦⑨가 progress.md 표에서 "통과"로 찍히지 않았어도, 이 리그에서 실기로
움직임이 확인된 (그룹, 모양, 축) 조합만 `beat_grid_emit`의 M1 게이트를
우회한다 — "부분 적용 0건" 원칙은 유지한다(매칭되지 않는 칸은 그대로 막힌다).
콘솔 접촉 0건 — 데이터 파일 하나를 읽는 순수 함수만 시험한다.
"""

from __future__ import annotations

from server.design.beat_grid_measured import MEASURED_MOVEMENTS, is_movement_measured_open


class TestMeasuredMovementsData:
    def test_mover_d_tilt_wave_is_recorded_with_any_base_condition(self) -> None:
        entry = next(
            e
            for e in MEASURED_MOVEMENTS
            if e.group_no == 12 and e.shape == "wave" and e.axes == frozenset({"Tilt"})
        )
        assert entry.base_condition == "any"
        assert entry.source  # 근거 경로가 비어있지 않다(지어내지 않음)

    def test_mover_d_pan_wave_is_recorded_but_base_is_unverifiable(self) -> None:
        entry = next(
            e
            for e in MEASURED_MOVEMENTS
            if e.group_no == 12 and e.shape == "wave" and e.axes == frozenset({"Pan"})
        )
        assert entry.base_condition == "requires_tilted_base_unverifiable"
        assert entry.source


class TestIsMovementMeasuredOpen:
    def test_mover_d_tilt_wave_group_12_is_open(self) -> None:
        # t548 D1(2마디 주기+위상 펼침)·D3(2박 주기) — 둘 다 축은 Tilt 하나.
        assert is_movement_measured_open(12, "wave", ("Tilt",)) is True

    def test_mover_d_pan_wave_group_12_is_measured_but_stays_closed(self) -> None:
        # t548 D2(기준 2.1, 판정 불가) / D2'(기준 Tilt 45, 움직임) — 기준이
        # 기울어야 보이는데 앱은 position_preset_no가 기운 기준인지 못
        # 읽는다(M1 ⑥과 같은 한계) → 기록은 있어도 게이트는 영구히 닫힌다.
        assert is_movement_measured_open(12, "wave", ("Pan",)) is False

    def test_mover_u_pan_wave_group_11_is_measured_but_stays_closed(self) -> None:
        # 2026-10-11 대체 고지(카드 t553 실기): 원래 「group 11 Pan 단독은 잰 적
        # 없음」이었다. 실기로 336(Tilt 45 기준) 움직임, 337·338(bar 18 칸 기준
        # At Preset 2.1) 판정 불가 — 기울인 기준에서만 보인다. 기록은 생겼지만
        # MOVER-D Pan 과 같은 이유로 게이트는 닫힌 채다(감독 결정 대상).
        from server.design.beat_grid_measured import MEASURED_MOVEMENTS

        recorded = [
            e
            for e in MEASURED_MOVEMENTS
            if e.group_no == 11 and e.shape == "wave" and e.axes == frozenset({"Pan"})
        ]
        assert len(recorded) == 1
        assert recorded[0].base_condition == "requires_tilted_base_unverifiable"
        assert is_movement_measured_open(11, "wave", ("Pan",)) is False

    def test_unknown_group_is_closed(self) -> None:
        assert is_movement_measured_open(999, "wave", ("Tilt",)) is False

    def test_unknown_shape_is_closed(self) -> None:
        assert is_movement_measured_open(12, "circle", ("Tilt",)) is False

    def test_axes_must_match_exactly_not_as_a_subset(self) -> None:
        # Tilt 단독 엔트리가 Pan+Tilt 칸을 느슨하게 덮지 않는다(감독 지시
        # "do not loosen the mapping").
        assert is_movement_measured_open(12, "wave", ("Pan", "Tilt")) is False

    def test_group_no_none_is_closed(self) -> None:
        assert is_movement_measured_open(None, "wave", ("Tilt",)) is False

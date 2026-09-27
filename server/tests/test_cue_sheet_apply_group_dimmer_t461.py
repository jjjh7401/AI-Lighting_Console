"""카드 t461 ⚠1(리드 판정) — 그룹별 조도가 서로 다르면 기존 반영 경로 안에서
그룹별 Dimmer 줄로 나눠 보낸다. 새 콘솔 경로가 아니다(``plan_cue_console_apply``
의 value_line 한 줄 뒤에 덧붙는다 — back 레이어 줄과 같은 last-wins 방식).

- 모든 그룹 값이 같으면 명령은 바이트 동일(수정 전 스냅샷 그대로).
- 그룹을 콘솔 그룹 번호로 못 풀면 지어내지 않고 기존처럼 한 값 + 사유.
"""

from __future__ import annotations

from server.design.cue_sheet_apply import plan_cue_console_apply

_MAPPING = [
    {"group_name": "Key Wash", "group_no": 11, "role": "key"},
    {"group_name": "Back Light", "group_no": 12, "role": "back"},
]
_LEGEND = {"블루": "#0D33FF", "앰버": "#FF8C0D"}
_BLUE = "Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 100"
_AMBER = (
    "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 55 ; Attribute 'ColorRGB_B' At 5"
)


def _section(key: int, back: int, **extra: object) -> dict:
    return {
        "cue_number": 3,
        "label": "Chorus",
        "intensity": [{"group": "KEY", "level": key}, {"group": "BACK", "level": back}],
        "palette_primary": "블루",
        "fade_seconds": 1.5,
        **extra,
    }


def test_equal_levels_are_byte_identical_to_before() -> None:
    """수정 전 출력(`.moai/reports/t461/apply_commands_before.txt`) 그대로."""
    plan = plan_cue_console_apply(_section(90, 90), None, _MAPPING, _LEGEND)
    assert plan.value_line == f"Group 11 + 12 ; Attribute 'Dimmer' At 90 ; {_BLUE}"
    assert plan.summary == "조도 90% · 컬러 블루 · 페이드 1.5초"
    assert plan.skips == ()

    plan = plan_cue_console_apply(
        _section(80, 80, palette_secondary="앰버"), None, _MAPPING, _LEGEND
    )
    assert plan.value_line == (
        f"Group 11 + 12 ; Attribute 'Dimmer' At 80 ; {_BLUE} ; Group 12 ; {_AMBER}"
    )


def test_lower_group_gets_its_own_dimmer_line_after_the_colour() -> None:
    plan = plan_cue_console_apply(_section(90, 70), None, _MAPPING, _LEGEND)
    assert plan.value_line == (
        f"Group 11 + 12 ; Attribute 'Dimmer' At 90 ; {_BLUE} ; Group 12 ; Attribute 'Dimmer' At 70"
    )
    assert "BACK 70%" in plan.summary
    assert plan.skips == ()


def test_key_lower_with_secondary_colour() -> None:
    plan = plan_cue_console_apply(
        _section(50, 90, palette_secondary="앰버"), None, _MAPPING, _LEGEND
    )
    assert plan.value_line == (
        f"Group 11 + 12 ; Attribute 'Dimmer' At 90 ; {_BLUE} ; Group 12 ; {_AMBER} ; "
        "Group 11 ; Attribute 'Dimmer' At 50"
    )


def test_unresolvable_group_falls_back_to_one_value_with_a_reason() -> None:
    """KEY 는 번호를 모른다(주소록에 없음) — 한 값만 보내고 사유를 단다."""
    mapping = [{"group_name": "MOVER-U", "group_no": 12, "role": "back"}]
    section = _section(50, 90, fixture_groups=["MOVER-U"])
    plan = plan_cue_console_apply(section, None, mapping, _LEGEND)
    assert plan.value_line == f"Group 12 ; Attribute 'Dimmer' At 90 ; {_BLUE}"
    details = [skip.detail for skip in plan.skips]
    assert any("그룹별 조도를 나눠 보내지 못했습니다" in d and "KEY" in d for d in details)


def test_group_not_addressed_by_the_cue_adds_no_second_reason() -> None:
    """BACK 자체가 이 큐의 대상에서 이미 빠졌다(기존 사유) — 덮어쓰기 줄도 새 사유도 없다."""
    plan = plan_cue_console_apply(_section(90, 70), None, _MAPPING[:1], _LEGEND)
    assert plan.value_line == f"Group 11 ; Attribute 'Dimmer' At 90 ; {_BLUE}"
    assert [skip.detail for skip in plan.skips] == [
        "일부 대상만 반영했습니다 — 콘솔 그룹 번호를 모르는 대상: BACK"
    ]

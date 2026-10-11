"""SPEC-LDBEAT-001 M3 — 박자 격자 편집 경로 ②(문장) 규칙 파서 (카드 t551
후속, 리드 지시 — "편집 세 길이 전부 서버 연산에 도달하게 배선").

정해진 꼴은 mockup 명령창(`reports/ldbeat-runbook-ui-proposal-20261008.html`
`#cmdIn`/`#bRule`, 2026-10-08)의 실제 정규식과 같은 모양이다 — NLU가
아니라 고정된 문장 모양의 규칙 파서(REQ-LDBEAT-007 "문장" 경로). 이해
못 하는 문장은 지어내지 않고 `None`(호출자가 단일-원인 거절을 낸다).

mockup과의 의도적 차이(카탈로그 부재로 인한 부분집합·deviation)는 모듈
docstring과 progress.md "## Missing Inputs"에 기록돼 있다 — "효과" 항목
미지원, 위치/색 값이 이름이 아니라 번호."""

from __future__ import annotations

from server.design.beat_grid_sentence import parse_beat_grid_sentence


class TestBrightnessForm:
    def test_percent_with_sign_parses(self) -> None:
        parsed = parse_beat_grid_sentence("11마디 MOVER-U 밝기를 70%로")
        assert parsed == {
            "bar": 11,
            "bar_end": 11,
            "target": "MOVER-U",
            "changes": {"brightness": {"mode": "value", "value_percent": 70, "preset_no": None}},
        }

    def test_percent_without_sign_parses(self) -> None:
        parsed = parse_beat_grid_sentence("18마디 mover 밝기를 40으로")
        assert parsed["changes"]["brightness"]["value_percent"] == 40
        assert parsed["target"] == "mover"
        assert parsed["bar_end"] == 18


class TestPresetForms:
    def test_position_preset_form_parses(self) -> None:
        parsed = parse_beat_grid_sentence("7마디 BACK 위치를 2.5로")
        assert parsed == {
            "bar": 7,
            "bar_end": 7,
            "target": "BACK",
            "changes": {"position_preset_no": "2.5"},
        }

    def test_color_preset_form_parses(self) -> None:
        parsed = parse_beat_grid_sentence("3마디 FOH 색을 4.9로")
        assert parsed == {
            "bar": 3,
            "bar_end": 3,
            "target": "FOH",
            "changes": {"color_preset_no": "4.9"},
        }


class TestBarRangeForm:
    """mockup 명령창 기본 문구 "22~25마디 MOVER-D 효과를 Sweep 2박으로"와
    같은 범위 모양(효과 항목 자체는 미지원, 아래 TestUnparseable 참조)."""

    def test_range_form_parses_start_and_end(self) -> None:
        parsed = parse_beat_grid_sentence("22~25마디 MOVER-D 밝기를 70%로")
        assert parsed["bar"] == 22
        assert parsed["bar_end"] == 25
        assert parsed["target"] == "MOVER-D"

    def test_range_form_with_spaces_around_tilde(self) -> None:
        parsed = parse_beat_grid_sentence("7 ~ 10마디 BACK 위치를 2.1로")
        assert parsed["bar"] == 7
        assert parsed["bar_end"] == 10

    def test_reversed_range_returns_none(self) -> None:
        assert parse_beat_grid_sentence("10~7마디 BACK 위치를 2.1로") is None


class TestUnparseable:
    def test_unrelated_sentence_returns_none(self) -> None:
        assert parse_beat_grid_sentence("오늘 날씨가 좋습니다") is None

    def test_effect_field_token_is_not_supported(self) -> None:
        # mockup의 네 번째 항목 "효과"는 프리셋 이름→번호 카탈로그 검색이
        # 필요하다(이 앱에 그 카탈로그 경로가 없다) — 지어내지 않고 None.
        assert parse_beat_grid_sentence("22~25마디 MOVER-D 효과를 Sweep 2박으로") is None

    def test_old_field_label_position_no_longer_matches(self) -> None:
        # "포지션"은 mockup 어휘가 아니다(mockup은 "위치") — 이제 안 받는다.
        assert parse_beat_grid_sentence("7마디 BACK 포지션을 2.5로") is None

    def test_missing_bar_token_returns_none(self) -> None:
        assert parse_beat_grid_sentence("MOVER-U 밝기를 70%로") is None

    def test_non_numeric_brightness_value_returns_none(self) -> None:
        assert parse_beat_grid_sentence("11마디 MOVER-U 밝기를 많이로") is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_beat_grid_sentence("") is None

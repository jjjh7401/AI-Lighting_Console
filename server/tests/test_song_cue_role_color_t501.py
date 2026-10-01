"""카드 t501 — SPEC-LDRENDER-001 M4, REQ-LDRENDER-004/005/006.

``song_cue_render._role_color_value_lines``(감독 결정 3의 층→색 배정 — 역할별
델타 색 줄, `_role_dimmer_value_lines`와 같은 그룹-주소 패턴)와
``_song_color_value_lines``(M2 의 베이스라인 + 이 카드의 역할별 배정 통합)를
직접 겨눈다.

층→색 배정(spec.md §3.2 [HARD], 감독 결정 3): `back`+`mover` = 지배색
(`palette[0]`, 베이스라인이 이미 낸다 — 델타 불필요), `side`+`wash` = 보조색
(`palette[1]`), `key` = 표준 팔레트의 웜화이트(새 RGB 금지). `color_usage=
single`(REQ-006)일 때 보조색이 지배색과 같아지면 델타 줄을 내지 않는다
(REQ-004 "네 그룹을 하나로 합친 선택에 동일 색 한 줄만" — 값-비교 생략으로
자연히 처리, 새 분기 없음).
"""

from __future__ import annotations

from dataclasses import dataclass

from server.design.color_names import resolve_color_name
from server.design.song_cue_render import (
    _group_color_apply_command,
    _role_color_value_lines,
    _song_color_value_lines,
)


@dataclass(frozen=True)
class _ColorOnlyCue:
    """``_role_color_value_lines``가 실제로 읽는 한 필드(``kind``)만 채운
    대역 — 전체 ``ComposedCue``를 짓는 비용 없이 역할 배정 로직만 겨눈다."""

    kind: str = "section"


#: t379 실측과 같은 다중 그룹 매핑(M3 `test_song_cue_role_dimmer_t501.py`의
#: `_MULTI_GROUP_SIDE_MAPPING`과 동형 — 독립 임포트 대신 이 파일 전용으로
#: 다시 선언한다, 두 파일이 서로 다른 축을 겨눠 공유 픽스처로 묶으면 결합도만
#: 올라간다).
_LAYER_MAPPING = (
    {"role": "key", "group_no": 2, "group_name": "KEY"},
    {"role": "back", "group_no": 4, "group_name": "BACK"},
    {"role": "side", "group_no": 7, "group_name": "SIDE-ALL"},
    {"role": "wash", "group_no": 10, "group_name": "WASH-ALL"},
    {"role": "mover", "group_no": 13, "group_name": "MOVER-ALL"},
    {"role": "effect", "group_no": 14, "group_name": "BLIND"},
    {"role": "audience", "group_no": 3, "group_name": "FOH"},
)

_BLUE = resolve_color_name("blue")
_AMBER = resolve_color_name("amber")
_WARM_WHITE = resolve_color_name("Warm White")
assert _BLUE is not None and _AMBER is not None and _WARM_WHITE is not None


class TestRoleColorValueLines:
    """REQ-LDRENDER-004 — back+mover=지배색(델타 없음)·side+wash=보조색·
    key=웜화이트."""

    def test_side_and_wash_get_the_accent_colour_back_and_mover_get_nothing(self) -> None:
        """back/mover 는 베이스라인이 이미 지배색이라 델타 줄이 없다."""
        lines = _role_color_value_lines(_ColorOnlyCue(), _LAYER_MAPPING, ("blue", "amber"), _BLUE)
        assert set(lines) == {
            _group_color_apply_command(7, _AMBER),  # side
            _group_color_apply_command(10, _AMBER),  # wash
            _group_color_apply_command(2, _WARM_WHITE),  # key
        }
        assert "Group 4" not in " ".join(lines), "back 은 베이스라인과 같은 값 — 델타 금지"
        assert "Group 13" not in " ".join(lines), "mover 은 베이스라인과 같은 값 — 델타 금지"

    def test_effect_role_never_receives_a_colour_delta_line(self) -> None:
        """R3(REQ-LDRENDER-007) HARD 불변식 — effect 역할 그룹은 색 포함 어떤
        값 줄에도 실리지 않는다(M5 를 기다리지 않는 구조적 가드)."""
        lines = _role_color_value_lines(_ColorOnlyCue(), _LAYER_MAPPING, ("blue", "amber"), _BLUE)
        assert "Group 14" not in " ".join(lines)

    def test_audience_role_never_receives_a_colour_delta_line(self) -> None:
        """audience 는 REQ-004 의 배정 축(back/mover/side/wash/key)에 없다."""
        lines = _role_color_value_lines(_ColorOnlyCue(), _LAYER_MAPPING, ("blue", "amber"), _BLUE)
        assert "Group 3" not in " ".join(lines)

    def test_a_mono_colour_palette_emits_no_role_assignment_at_all(self) -> None:
        """REQ-004 본문 "팔레트가 2개 이상의 색을 담고 있으면" — 단색이면
        key 웜화이트 배정도 하지 않는다(발명 금지, 오늘처럼 베이스라인 하나)."""
        lines = _role_color_value_lines(_ColorOnlyCue(), _LAYER_MAPPING, ("blue",), _BLUE)
        assert lines == ()

    def test_a_third_and_later_colour_is_never_fired(self) -> None:
        """len(palette) > 2 여도 3번째 이후 색은 쓰지 않는다(§6.3 동시성 상한)."""
        lines = _role_color_value_lines(
            _ColorOnlyCue(), _LAYER_MAPPING, ("blue", "amber", "magenta"), _BLUE
        )
        assert all("Magenta" not in line for line in lines)
        magenta_rgb = resolve_color_name("magenta")
        assert all(str(magenta_rgb) not in line for line in lines)

    def test_single_mode_merge_no_duplicate_line_when_accent_equals_dominant(self) -> None:
        """REQ-006(§D5) — `color_usage=single`이면 보조색이 지배색과 같아져
        side/wash 델타가 베이스라인과 같은 값이 된다 — 중복 발화하지 않는다
        (별도 분기 없이 값-비교 하나로 자연히 생략됨, REQ-004 "네 그룹을
        하나로 합친 선택에 동일 색 한 줄만")."""
        lines = _role_color_value_lines(_ColorOnlyCue(), _LAYER_MAPPING, ("blue", "blue"), _BLUE)
        # key 는 웜화이트라 여전히 배정된다 — "병합"은 side/wash 축에만 해당.
        assert lines == (_group_color_apply_command(2, _WARM_WHITE),)

    def test_dominant_already_warm_white_skips_the_key_delta(self) -> None:
        """지배색이 이미 웜화이트면 key 델타도 중복 — 베이스라인이 이미 처리."""
        lines = _role_color_value_lines(
            _ColorOnlyCue(), _LAYER_MAPPING, ("Warm White", "amber"), _WARM_WHITE
        )
        assert "Group 2" not in " ".join(lines)
        assert lines == (
            _group_color_apply_command(7, _AMBER),
            _group_color_apply_command(10, _AMBER),
        )

    def test_an_unresolvable_accent_name_emits_no_accent_delta_but_key_still_fires(self) -> None:
        """보조색 이름이 표준 팔레트 10색에 없으면 지어내지 않고 생략한다
        (지배색과 무관한 축 — key 웜화이트 배정은 영향받지 않는다)."""
        lines = _role_color_value_lines(_ColorOnlyCue(), _LAYER_MAPPING, ("blue", "gold"), _BLUE)
        assert "Group 7" not in " ".join(lines)
        assert "Group 10" not in " ".join(lines)
        assert lines == (_group_color_apply_command(2, _WARM_WHITE),)

    def test_a_role_missing_from_the_layer_mapping_is_simply_omitted(self) -> None:
        """side/wash 가 층 매핑에 없으면(리그에 그 그룹이 없는 경우) 줄을 안
        낸다 — 0 을 지어내지 않는다."""
        mapping = tuple(e for e in _LAYER_MAPPING if e["role"] not in {"side", "wash"})
        lines = _role_color_value_lines(_ColorOnlyCue(), mapping, ("blue", "amber"), _BLUE)
        assert lines == (_group_color_apply_command(2, _WARM_WHITE),)

    def test_empty_layer_mapping_emits_nothing(self) -> None:
        """단일 레이어 리그(AC-003 과 같은 경계) — 역할 배정 줄이 전혀 없다."""
        lines = _role_color_value_lines(_ColorOnlyCue(), (), ("blue", "amber"), _BLUE)
        assert lines == ()

    def test_a_non_section_kind_emits_nothing(self) -> None:
        lines = _role_color_value_lines(
            _ColorOnlyCue(kind="mib_premove"), _LAYER_MAPPING, ("blue", "amber"), _BLUE
        )
        assert lines == ()

    def test_the_group_colour_command_uses_group_addressing_not_fixture(self) -> None:
        """`_color_apply_command`의 그룹-주소 쌍둥이 — `Group <n>` 문법."""
        line = _group_color_apply_command(7, (100, 55, 5))
        assert line == (
            "Group 7 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 55 ; Attribute 'ColorRGB_B' At 5"
        )

    def test_role_delta_lines_are_unique_strings_alongside_the_dimmer_delta_lines(self) -> None:
        """REQ-FXLIB-011 계승 — 값 라인 충돌 가드(유일 문자열)는 역할별 색
        줄이 늘어도 그대로 지켜진다(Group 주소가 다르면 문자열도 다르다)."""
        lines = _role_color_value_lines(_ColorOnlyCue(), _LAYER_MAPPING, ("blue", "amber"), _BLUE)
        assert len(lines) == len(set(lines)), lines


# --------------------------------------------------------------------------
# `_song_color_value_lines` 통합 — 베이스라인 + 역할 배정이 한 번에 나온다.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Color:
    palette: tuple[str, ...]


@dataclass(frozen=True)
class _FullCue:
    kind: str
    cue_number: float
    cue_name: str
    color: _Color


class TestSongColorValueLinesIntegration:
    def test_baseline_plus_role_assignment_both_appear_in_order(self) -> None:
        cue = _FullCue(
            kind="section", cue_number=101.0, cue_name="Verse", color=_Color(("blue", "amber"))
        )
        lines, failure = _song_color_value_lines(cue, (1, 2, 3, 4), layer_mapping=_LAYER_MAPPING)
        assert failure is None
        # 베이스라인(전체 fids, 지배색) 이 먼저, 역할 델타가 뒤 — last-wins 순서.
        r, g, b = _BLUE
        assert lines[0] == (
            f"Fixture 1 + 2 + 3 + 4 ; Attribute 'ColorRGB_R' At {r} ; "
            f"Attribute 'ColorRGB_G' At {g} ; Attribute 'ColorRGB_B' At {b}"
        )
        assert _group_color_apply_command(7, _AMBER) in lines
        assert _group_color_apply_command(10, _AMBER) in lines
        assert _group_color_apply_command(2, _WARM_WHITE) in lines
        assert len(lines) == 4

    def test_no_layer_mapping_is_byte_identical_to_before_m4(self) -> None:
        """레거시 호출부 호환 — `layer_mapping=()`(기본값)이면 베이스라인
        한 줄만 나간다(오늘과 바이트 동일, AC-LDRENDER-005 modulate 비교
        기준과 같은 불변식)."""
        cue = _FullCue(
            kind="section", cue_number=101.0, cue_name="Verse", color=_Color(("blue", "amber"))
        )
        lines, failure = _song_color_value_lines(cue, (1, 2, 3, 4))
        assert failure is None
        assert len(lines) == 1
        assert f"ColorRGB_R' At {_BLUE[0]}" in lines[0]

    def test_unresolvable_dominant_colour_still_reports_failure_and_no_role_lines(self) -> None:
        cue = _FullCue(
            kind="section", cue_number=101.0, cue_name="Verse", color=_Color(("gold", "amber"))
        )
        lines, failure = _song_color_value_lines(cue, (1, 2, 3, 4), layer_mapping=_LAYER_MAPPING)
        assert lines == ()
        assert failure is not None and "gold" in failure

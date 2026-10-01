"""카드 t501 M5 — SPEC-LDRENDER-001, REQ-LDRENDER-007/008, 리드 결정 (g) (2026-10-01).

``song_cue_render._effect_group_numbers``·``_effect_dimmer_zero_lines``를
직접 겨눈다 — 공유 ``fids``에서 effect 기구를 빼는 대신(fid 멤버십 판독
경로 부재, ``.moai/reports/t501/M5.md`` §블로커), 그룹 주소로 비액센트
큐의 BLIND/STROBE/HAZE 를 0 으로 내리는 outcome-equivalent 구현이다.

세 축으로 나눠 겨눈다:
  - ``TestEffectGroupNumbers``       : 여러 effect 그룹을 전부 모으는
    집계 함수 자체(``_role_group_numbers``의 last-wins 단일값과 다름).
  - ``TestEffectDimmerZeroLines``    : 큐 스텁 수준에서 0-줄 생성 로직
    (비액센트/액센트/복귀 큐 갈래, kind 가드, 중복 가드).
  - ``TestReviewedSongCommandsIntegration`` : 실제 ``reviewed_song_commands``
    를 통과시켜 t498 cue 11(100→80 역방향)이 고쳐졌는지, 줄 순서가
    배차서 요구사항 1(전체 디머 → 역할 디머(effect=0 포함) → 효과 recall
    → 액센트)과 일치하는지 끝까지 확인한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.design.song_cue_composer import CueAccentFixtureData, CueColorData, CueDimmerData
from server.design.song_cue_render import (
    _effect_dimmer_zero_lines,
    _effect_group_numbers,
    reviewed_song_commands,
)
from server.design.song_plan import TimingPlan

# --------------------------------------------------------------------------
# 공유 픽스처 — 실기 그룹 번호(REAL_GROUPS, .moai/reports/t501/measure_ac001_8songs.py
# 와 바이트 동일한 14=BLIND·15=STROBE·16=HAZE)와 같은 그룹 번호를 쓴다.
# --------------------------------------------------------------------------

_LAYER_MAPPING_THREE_EFFECT_GROUPS = (
    {"role": "key", "group_no": 2, "group_name": "KEY"},
    {"role": "back", "group_no": 4, "group_name": "BACK"},
    {"role": "effect", "group_no": 14, "group_name": "BLIND"},
    {"role": "effect", "group_no": 15, "group_name": "STROBE"},
    {"role": "effect", "group_no": 16, "group_name": "HAZE"},
)

_LAYER_MAPPING_NO_EFFECT = (
    {"role": "key", "group_no": 2, "group_name": "KEY"},
    {"role": "back", "group_no": 4, "group_name": "BACK"},
)


@dataclass(frozen=True)
class _Dimmer:
    """``_effect_dimmer_zero_lines``가 실제로 읽는 한 필드(``key_pct``)만 채운 대역."""

    key_pct: float | None


@dataclass(frozen=True)
class _Cue:
    """``_effect_dimmer_zero_lines``가 실제로 읽는 세 필드(``kind``·``dimmer``·
    ``accent_fixture``)만 채운 대역."""

    kind: str
    dimmer: _Dimmer
    accent_fixture: CueAccentFixtureData | None = None


def _section_cue(key_pct: float = 100.0, accent_fixture=None) -> _Cue:
    return _Cue(kind="section", dimmer=_Dimmer(key_pct=key_pct), accent_fixture=accent_fixture)


class TestEffectGroupNumbers:
    """`_role_group_numbers`의 last-wins 단일값과 달리 **전부** 모은다."""

    def test_collects_all_three_effect_groups_sorted(self) -> None:
        assert _effect_group_numbers(_LAYER_MAPPING_THREE_EFFECT_GROUPS) == (14, 15, 16)

    def test_non_effect_roles_are_excluded(self) -> None:
        mapping = (
            {"role": "key", "group_no": 2, "group_name": "KEY"},
            {"role": "back", "group_no": 4, "group_name": "BACK"},
        )
        assert _effect_group_numbers(mapping) == ()

    def test_empty_mapping_yields_empty_tuple(self) -> None:
        assert _effect_group_numbers(()) == ()

    def test_duplicate_entries_for_the_same_group_are_deduplicated(self) -> None:
        """같은 콘솔 그룹이 매핑 목록에 두 번 들어와도(이론상 소비자 중복
        호출) 줄은 한 번만 — 중복 줄 가드(배차서 요구사항 1)의 전제."""
        mapping = (
            {"role": "effect", "group_no": 14, "group_name": "BLIND"},
            {"role": "effect", "group_no": 14, "group_name": "BLIND"},
        )
        assert _effect_group_numbers(mapping) == (14,)

    def test_order_is_deterministic_regardless_of_input_order(self) -> None:
        """콘솔 그룹 풀 재조회 순서가 바뀌어도(응답기 order 비보장) 줄 순서는
        그룹 번호 오름차순으로 고정 — 매 실행 바이트 동일(§실행 재현성)."""
        reversed_mapping = (
            {"role": "effect", "group_no": 16, "group_name": "HAZE"},
            {"role": "effect", "group_no": 15, "group_name": "STROBE"},
            {"role": "effect", "group_no": 14, "group_name": "BLIND"},
        )
        assert _effect_group_numbers(reversed_mapping) == (14, 15, 16)

    def test_non_int_or_bool_group_no_is_skipped(self) -> None:
        mapping = (
            {"role": "effect", "group_no": None, "group_name": "BLIND"},
            # bool is a subclass of int in Python — not a valid group_no.
            {"role": "effect", "group_no": True, "group_name": "STROBE"},
            {"role": "effect", "group_no": 16, "group_name": "HAZE"},
        )
        assert _effect_group_numbers(mapping) == (16,)


class TestEffectDimmerZeroLines:
    """0-줄 생성 로직 — 비액센트/액센트/복귀 갈래, kind 가드, 중복 가드."""

    def test_non_accent_section_cue_zeroes_every_effect_group(self) -> None:
        cue = _section_cue(key_pct=100.0)
        lines = _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS)
        assert lines == (
            "Group 14 ; Attribute 'Dimmer' At 0",
            "Group 15 ; Attribute 'Dimmer' At 0",
            "Group 16 ; Attribute 'Dimmer' At 0",
        )

    def test_accent_cue_excludes_only_the_accent_targeted_group(self) -> None:
        """REQ-LDRENDER-008/리드 결정 g — 「그 그룹엔 액센트 값만 낸다」: 블라인더
        (그룹 14)가 액센트일 때, STROBE(15)·HAZE(16)는 여전히 0 으로 내려가지만
        14 는 이 함수에서 생략된다(`_accent_fixture_value_lines`가 그 그룹의
        상승 값을 따로 낸다)."""
        accent = CueAccentFixtureData(rung="climax accent", group_no=14, dimmer_pct=80.0)
        cue = _section_cue(key_pct=100.0, accent_fixture=accent)
        lines = _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS)
        assert "Group 14" not in " ".join(lines)
        assert lines == (
            "Group 15 ; Attribute 'Dimmer' At 0",
            "Group 16 ; Attribute 'Dimmer' At 0",
        )

    def test_return_cue_excludes_the_group_the_accent_machinery_already_zeroes(self) -> None:
        """복귀 큐(이 큐는 액센트가 없고, 앞 큐가 블라인더를 켜 둠) — 그룹 14 의
        "At 0" 은 `_accent_fixture_value_lines`의 복귀 줄 하나로만 난다. 이
        함수가 또 내면 문자열이 중복된다(배차서 요구사항 1, 중복 줄 가드를
        복귀 큐까지 일관 적용한 추가 가드 — M5b.md §해석 노트)."""
        previous_fixture = CueAccentFixtureData(rung="climax accent", group_no=14, dimmer_pct=80.0)
        cue = _section_cue(key_pct=100.0, accent_fixture=None)
        lines = _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS, previous_fixture)
        assert "Group 14" not in " ".join(lines)
        assert lines == (
            "Group 15 ; Attribute 'Dimmer' At 0",
            "Group 16 ; Attribute 'Dimmer' At 0",
        )

    def test_return_cue_group_exclusion_does_not_apply_when_this_cue_has_its_own_accent(
        self,
    ) -> None:
        """``previous_fixture``가 있어도 **이** 큐 자신이 또 다른 그룹을
        액센트로 켜면(드문 연속 액센트), 복귀-그룹 가드는 현재 큐의
        ``accent_fixture`` 가 ``None`` 일 때만 적용된다 — `cue.accent_fixture
        is None` 가드가 그 분기를 막는다."""
        previous_fixture = CueAccentFixtureData(rung="climax accent", group_no=14, dimmer_pct=80.0)
        new_accent = CueAccentFixtureData(rung="climax accent", group_no=15, dimmer_pct=80.0)
        cue = _section_cue(key_pct=100.0, accent_fixture=new_accent)
        lines = _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS, previous_fixture)
        # 그룹 14(이전 액센트, 이 큐에선 액센트가 아님)·16(HAZE) 은 여전히 0 으로
        # 내려간다 — previous_fixture 가 아니라 cue.accent_fixture(그룹 15)만
        # 생략 대상이다.
        assert lines == (
            "Group 14 ; Attribute 'Dimmer' At 0",
            "Group 16 ; Attribute 'Dimmer' At 0",
        )

    def test_blackout_cue_zero_key_pct_emits_nothing(self) -> None:
        cue = _section_cue(key_pct=0.0)
        assert _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS) == ()

    def test_none_key_pct_emits_nothing(self) -> None:
        cue = _Cue(kind="section", dimmer=_Dimmer(key_pct=None))
        assert _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS) == ()

    def test_mib_premove_kind_emits_nothing(self) -> None:
        cue = _Cue(kind="mib_premove", dimmer=_Dimmer(key_pct=100.0))
        assert _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS) == ()

    def test_climax_return_kind_is_included(self) -> None:
        """``_ROLE_VALUE_LINE_KINDS``에 ``climax_return``도 들어 있다 — M3 후속이
        이미 연 kind 집합을 이 함수도 공유한다(§모듈 상수 docstring)."""
        cue = _Cue(kind="climax_return", dimmer=_Dimmer(key_pct=100.0))
        lines = _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS)
        assert len(lines) == 3

    def test_no_effect_group_mapped_emits_nothing_byte_identical_fallback(self) -> None:
        """배차서 요구사항 4 — 매핑된 effect 역할 그룹이 없으면(리그에 그룹 자체가
        없거나 층 매핑이 아직 역할을 해석 못함) 오늘과 바이트 동일(빈 튜플)."""
        cue = _section_cue(key_pct=100.0)
        assert _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_NO_EFFECT) == ()
        assert _effect_dimmer_zero_lines(cue, ()) == ()

    def test_non_section_non_climax_return_kind_emits_nothing(self) -> None:
        cue = _Cue(kind="blackout", dimmer=_Dimmer(key_pct=100.0))
        assert _effect_dimmer_zero_lines(cue, _LAYER_MAPPING_THREE_EFFECT_GROUPS) == ()


class TestReviewedSongCommandsIntegration:
    """``reviewed_song_commands`` 끝까지 통과 — 줄 순서(배차서 요구사항 1)와
    REQ-LDRENDER-008(t498 cue 11, 100→80 역방향 재현 0건)을 직접 확인한다."""

    @staticmethod
    def _bundle(cues):
        @dataclass
        class _Bundle:
            cues: tuple
            timed_cues: tuple = ()
            song_title: str = "Test"
            sequence_name: str = "Test Sequence"

        return _Bundle(cues=tuple(cues))

    @staticmethod
    def _full_cue(
        cue_number: float,
        *,
        key_pct: float,
        accent_fixture=None,
        rgb=(255, 0, 0),
        kind: str = "section",
    ):
        @dataclass
        class _Position:
            stored: str | None = None

        @dataclass
        class _Cue:
            cue_number: float
            cue_name: str
            kind: str
            dimmer: CueDimmerData
            color: CueColorData
            position: _Position
            fade_seconds: float | None
            accent_fixture: CueAccentFixtureData | None

        return _Cue(
            cue_number=cue_number,
            cue_name=f"Cue {cue_number:g}",
            kind=kind,
            dimmer=CueDimmerData(
                key_pct=key_pct, back_pct=None, budget_range_pct=(0.0, 100.0), role_pct={}
            ),
            color=CueColorData(palette=(_rgb_name(rgb),), saturation="full"),
            position=_Position(),
            fade_seconds=None,
            accent_fixture=accent_fixture,
        )

    def test_line_order_whole_fixture_then_role_dimmer_incl_effect_zero_then_accent(
        self,
    ) -> None:
        """배차서 요구사항 1 — 줄 순서: 전체 기구 키 디머 → 역할 디머 줄(effect=0
        포함) → 효과 recall → 액센트. (색 줄은 역할 디머 줄 앞, 기존 순서 불변
        — 배차서가 다루는 축 밖이다.)"""
        cue = self._full_cue(cue_number=1, key_pct=100.0)
        bundle = self._bundle([cue])
        commands, _failures = reviewed_song_commands(
            bundle,
            sequence_no=211,
            fids=list(range(1, 10)),
            timing=TimingPlan(mode="manual_go", timecode_number=None),
            position_slots={},
            phaser_slots={},
            white_presets=None,
            layer_mapping=_LAYER_MAPPING_THREE_EFFECT_GROUPS,
        )
        store_lines = [c for c in commands if "Fixture" in c or c.startswith("Group")]
        assert store_lines[0].startswith("Fixture ") and "Dimmer" in store_lines[0]
        group_lines = [c for c in store_lines if c.startswith("Group")]
        # 역할 디머 줄(그룹 4=back, role_pct 가 비어 있어 안 남 — 이 테스트는
        # effect=0 셋만 검증)과 effect=0 셋이 전체 기구 디머 줄 뒤에 온다.
        assert group_lines == [
            "Group 14 ; Attribute 'Dimmer' At 0",
            "Group 15 ; Attribute 'Dimmer' At 0",
            "Group 16 ; Attribute 'Dimmer' At 0",
        ]
        # group_lines 는 store_lines 에서 전체 기구 디머 줄보다 뒤에 있어야 한다.
        fixture_index = store_lines.index(next(c for c in store_lines if c.startswith("Fixture")))
        for group_line in group_lines:
            assert store_lines.index(group_line) > fixture_index

    def test_t498_cue_11_regression_fixed_accent_rises_not_falls(self) -> None:
        """REQ-LDRENDER-008 — t498 큐 11(verdict.md: "Group 4 80 · Group 14(BLIND)
        80", 전체 디머 100 뒤에 액센트 80 이 와서 100→80 **하강**이었다). M5
        적용 후: 큐 1(비액센트, 그룹 14 를 0 으로 내림) → 큐 2(액센트, 전체
        디머가 다시 100 을 내지만 그룹 14 는 이 함수가 건너뛰어 effect=0 줄이
        안 나가고, 액센트 줄 하나만 80 을 낸다 — "그 그룹엔 액센트 값만
        낸다", 리드 결정 g) → 큐 3(복귀, 14 를 다시 0)."""

        def _group14_lines_in_block(commands, cue_number: float) -> list[str]:
            start = next(
                i for i, c in enumerate(commands) if f"Store Sequence 211 Cue {cue_number:g}" in c
            )
            clear_indexes = (i for i in range(start) if commands[i] == "ClearAll")
            block_start = max(clear_indexes, default=-1) + 1
            block = commands[block_start:start]
            return [line for line in block if line.startswith("Group 14")]

        accent = CueAccentFixtureData(rung="climax accent", group_no=14, dimmer_pct=80.0)
        cue_before = self._full_cue(cue_number=1, key_pct=100.0)
        cue_accent = self._full_cue(cue_number=2, key_pct=100.0, accent_fixture=accent)
        cue_after = self._full_cue(cue_number=3, key_pct=100.0)
        bundle = self._bundle([cue_before, cue_accent, cue_after])
        commands, _failures = reviewed_song_commands(
            bundle,
            sequence_no=211,
            fids=list(range(1, 10)),
            timing=TimingPlan(mode="manual_go", timecode_number=None),
            position_slots={},
            phaser_slots={},
            white_presets=None,
            layer_mapping=_LAYER_MAPPING_THREE_EFFECT_GROUPS,
        )
        # 큐 1(직전, 비액센트) — 그룹 14 는 0 으로 내려가 있다(이전 비점등 상태).
        assert _group14_lines_in_block(commands, 1) == ["Group 14 ; Attribute 'Dimmer' At 0"]
        # 큐 2(액센트) — 그룹 14 에 대한 명시 줄은 액센트 80 **하나뿐**이다.
        # effect=0 함수가 자기 그룹을 건너뛰므로, 전체 디머 100(경쟁 값)을 내는
        # 명시 "Group 14" 줄 자체가 존재하지 않는다 — 100→80 역방향 재현 0건.
        assert _group14_lines_in_block(commands, 2) == ["Group 14 ; Attribute 'Dimmer' At 80"]
        # 큐 3(복귀) — `_accent_fixture_value_lines`가 다시 0으로 내린다, 중복 없음.
        assert _group14_lines_in_block(commands, 3) == ["Group 14 ; Attribute 'Dimmer' At 0"]

    def test_return_cue_after_accent_has_no_duplicate_group_line(self) -> None:
        """복귀 큐(그림 14 를 다시 0으로)에서 "Group 14 ; ... At 0" 줄이 정확히
        한 번만 나온다 — 효과-0 함수와 액센트 복귀 줄이 겹치면 안 된다(중복
        줄 가드)."""
        accent = CueAccentFixtureData(rung="climax accent", group_no=14, dimmer_pct=80.0)
        cue_accent = self._full_cue(cue_number=1, key_pct=100.0, accent_fixture=accent)
        cue_return = self._full_cue(cue_number=2, key_pct=100.0)
        bundle = self._bundle([cue_accent, cue_return])
        commands, _failures = reviewed_song_commands(
            bundle,
            sequence_no=211,
            fids=list(range(1, 10)),
            timing=TimingPlan(mode="manual_go", timecode_number=None),
            position_slots={},
            phaser_slots={},
            white_presets=None,
            layer_mapping=_LAYER_MAPPING_THREE_EFFECT_GROUPS,
        )
        cue2_start = next(i for i, c in enumerate(commands) if "Store Sequence 211 Cue 2" in c)
        block_start = max(i for i in range(cue2_start) if commands[i] == "ClearAll") + 1
        cue2_block = commands[block_start:cue2_start]
        group14_lines = [line for line in cue2_block if line.startswith("Group 14")]
        assert group14_lines == ["Group 14 ; Attribute 'Dimmer' At 0"]

    def test_no_effect_groups_in_layer_mapping_is_byte_identical_to_pre_m5(self) -> None:
        """배차서 요구사항 4 — effect 역할 그룹이 매핑에 하나도 없으면(이 리그
        층 매핑이 역할을 전혀 해석 못 함) M5 적용 전후 명령이 바이트 동일
        (effect-zero 줄이 아예 안 섞여 들어간다)."""
        cue = self._full_cue(cue_number=1, key_pct=100.0)
        bundle = self._bundle([cue])
        commands_with_no_effect, _ = reviewed_song_commands(
            bundle,
            sequence_no=211,
            fids=list(range(1, 10)),
            timing=TimingPlan(mode="manual_go", timecode_number=None),
            position_slots={},
            phaser_slots={},
            white_presets=None,
            layer_mapping=(),
        )
        commands_with_no_mapping, _ = reviewed_song_commands(
            bundle,
            sequence_no=211,
            fids=list(range(1, 10)),
            timing=TimingPlan(mode="manual_go", timecode_number=None),
            position_slots={},
            phaser_slots={},
            white_presets=None,
        )
        assert commands_with_no_effect == commands_with_no_mapping
        assert not any(c.startswith("Group") for c in commands_with_no_effect)


def _rgb_name(rgb: tuple[int, int, int]) -> str:
    """팔레트 색 이름 — 표준 10색 중 ``resolve_color_name``이 실제로 아는 이름만
    쓴다(지어낸 RGB 는 `_song_color_value_lines` 가 실패 사유를 낸다)."""
    from server.design.color_names import resolve_color_name

    for name in ("red", "blue", "amber", "green", "white", "Warm White"):
        if resolve_color_name(name) == rgb:
            return name
    return "red"

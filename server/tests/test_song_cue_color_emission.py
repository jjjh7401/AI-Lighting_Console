"""SPEC-LDDESIGN-001 M2 — 감독 확정 경로가 컨셉 색을 콘솔로 보낸다.

**고치기 전에 실측한 것** (2026-09-22, 트리 `c4eed85e`,
`reports/lddesign-m2-cue-path/`): 감독이 화면에서 확정한 큐는 **색 없이**
콘솔로 나갔다. 설계층(`compose_song_cue_bundle`)은 구간마다 다른 팔레트를
제대로 들고 있었는데(`CueColorData(palette=('blue','cyan'))` 등), 명령
생성기(`_reviewed_song_commands`)가 위치 프리셋과 밝기만 내고 색을 떨어뜨렸다
— 22줄 중 색 줄 0.

같은 판별 기준을 코파일럿 경로(`build_songcue_bundle`)에 쏘면 색 줄이 5개
나온다(양쪽 팔 대조군). 즉 계기가 색을 못 보는 게 아니라 이 경로가 색을
안 보냈다.

이 파일이 지키는 것:

1. 구간 큐는 팔레트 주색을 ``ColorRGB_R/G/B`` 값 라인으로 낸다.
2. 값은 지어내지 않는다 — ``resolve_color_name`` 이 모르는 이름은 색 줄을
   내지 않고 **사유를 남긴다**(조용히 넘어가지 않는다, `_phaser_failure_note`
   와 같은 관행).
3. 맨 흰색("흰색"·"화이트"·"white")은 **감독 결정 대기로 남는다** — 표준
   팔레트에 `Warm White` 와 `Cool White` 가 둘 다 있어 이 SPEC 이 한쪽으로
   몰면 값을 지어내는 것이 된다. 카드 t409 가 이미 이 경계를 그었다
   (`TestThePlainWhiteStaysUnruled` 참고). 실제 곡은 막히지 않는다 —
   운영 아크(`_ARC_PALETTE`)는 갈래를 명시한 ``warm white`` 를 쓴다.
"""

from __future__ import annotations

import pytest

from server.design.color_names import resolve_color_name
from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import (
    AccentDecision,
    ApprovalState,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
)
from server.web.session import (
    ChatSession,
    _color_failure_note,
    _song_color_value_lines,
)

_FIDS = (1, 2, 3, 4)


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 41)
    ]
    return build_rig_profile(
        patch=patch, groups={}, coords=[], declared_layers={"key": [1, 2], "back": [3, 4]}
    )


def _section(index: int, label: str, start_ms: int, d_level: int, colors: tuple[str, ...]):
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=d_level, source="section_mood"),
        palette=PaletteDecision(colors=colors, source="director"),
        position=PositionDecision(preset="Center", source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), disabled=(), density=0),
        accent=AccentDecision(accents=()),
        cue_number=100 + index,
    )


def _composition(*section_colors: tuple[str, ...]):
    sections = tuple(
        _section(i, label, (i - 1) * 20_000, min(2 + i, 5), colors)
        for i, (label, colors) in enumerate(
            zip(("Intro", "Verse", "Chorus"), section_colors, strict=False), start=1
        )
    )
    plan = UnifiedSongLightingPlan(
        song_title="Color Emission Test",
        sequence_name="Color Seq",
        sections=sections,
        timing=TimingPlan.timecode(9),
        music_profile=MusicProfile(bpm=120.0, palette=("blue", "warm white")),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="director"),
    )
    return compose_song_cue_bundle(plan)


class _Stub:
    """`_reviewed_song_commands` 가 실제로 쓰는 두 자리만 채운 대역."""

    def __init__(self) -> None:
        self._last_phaser_failures: dict[str, str] = {}
        self._last_color_failures: dict[str, str] = {}

    def _phaser_slots_for_bundle(self, bundle):
        return {}, {}

    _reviewed_song_timing_commands = ChatSession._reviewed_song_timing_commands


def _commands(composition) -> tuple[tuple[str, ...], _Stub]:
    stub = _Stub()
    commands = ChatSession._reviewed_song_commands(
        stub,
        composition,
        sequence_no=210,
        preset_start=1,
        fids=list(_FIDS),
        timing=TimingPlan.timecode(9),
        layer_mapping=(),
    )
    return commands, stub


def _color_lines(commands) -> list[str]:
    return [line for line in commands if "ColorRGB_R" in line]


class TestTheConfirmedPathNowSendsColor:
    """실측 결함의 정면 — 감독 확정 경로가 색을 낸다."""

    def test_each_section_cue_carries_its_own_palette_colour(self) -> None:
        composition = _composition(("blue", "cyan"), ("amber", "red"), ("magenta", "red"))
        commands, _ = _commands(composition)

        lines = _color_lines(commands)
        assert len(lines) == 3, commands

        # 값을 지어내지 않았는지 — 사전이 답한 RGB 와 **글자 그대로** 같아야 한다.
        for line, name in zip(lines, ("blue", "amber", "magenta"), strict=True):
            red, green, blue = resolve_color_name(name)
            assert f"Attribute 'ColorRGB_R' At {red}" in line
            assert f"Attribute 'ColorRGB_G' At {green}" in line
            assert f"Attribute 'ColorRGB_B' At {blue}" in line

    def test_the_colour_line_selects_the_same_fixtures_as_the_dimmer_line(self) -> None:
        """값 라인은 선택 접두어를 들고 있어야 한다(명령 중복 제거 계약)."""
        commands, _ = _commands(_composition(("blue", "cyan")))
        selection = " + ".join(str(fid) for fid in _FIDS)
        for line in _color_lines(commands):
            assert line.startswith(f"Fixture {selection} ;")

    def test_the_colour_line_lands_before_the_store_line_of_its_own_cue(self) -> None:
        """Store 앞에 값이 서야 프로그래머 상태가 그 큐에 담긴다."""
        commands, _ = _commands(_composition(("blue", "cyan")))
        colour_at = next(i for i, c in enumerate(commands) if "ColorRGB_R" in c)
        store_at = next(i for i, c in enumerate(commands) if c.startswith("Store Sequence"))
        assert colour_at < store_at, commands


class TestTheValueIsNeverInvented:
    """표준 팔레트 10색에 없는 이름은 지어내지 않고 사유를 남긴다."""

    @pytest.mark.parametrize("unknown", ["gold", "warm special", "핑크", "오렌지"])
    def test_an_unresolvable_name_emits_no_colour_line(self, unknown: str) -> None:
        commands, _ = _commands(_composition((unknown, "cyan")))
        assert _color_lines(commands) == []

    def test_an_unresolvable_name_is_reported_not_swallowed(self) -> None:
        _, stub = _commands(_composition(("gold", "cyan")))
        assert stub._last_color_failures, "사유 없이 조용히 넘어갔다"
        assert any("gold" in reason for reason in stub._last_color_failures.values())

    def test_the_failure_note_names_the_colour_in_the_reply(self) -> None:
        _, stub = _commands(_composition(("gold", "cyan")))
        note = _color_failure_note(stub._last_color_failures)
        assert "gold" in note
        assert note.strip().endswith(".")

    def test_no_failures_means_no_note(self) -> None:
        _, stub = _commands(_composition(("blue", "cyan")))
        assert stub._last_color_failures == {}
        assert _color_failure_note(stub._last_color_failures) == ""


class TestThePlainWhiteStaysUnruled:
    """맨 흰색은 **감독 결정 대기** — 이 SPEC 이 대신 정하지 않는다.

    표준 팔레트에는 `Warm White`(100,75,40)와 `Cool White`(85,95,100)가
    **둘 다** 있다. 무대에서 눈에 띄게 다른 두 색이라 맨 "흰색"이 어느
    쪽인지는 감독만 정할 수 있다.

    카드 t409 가 이미 이 자리를 지났다: 퍼플/보라는 판정해 배선했지만
    화이트/흰색/하양은 "감독 판정 대상 목록에는 있었지만 배선 대상은
    아니다"로 남겼다(`test_cue_sheet_apply.py`
    `test_words_the_director_did_not_rule_on_still_fail_loudly`). M2 는 그
    경계를 그대로 둔다 — 한쪽으로 몰면 값을 지어내는 것이고, 그 시험이
    빨개진다(실측 2026-09-23: 몰았더니 3건 FAIL).
    """

    @pytest.mark.parametrize("name", ["white", "White", "흰색", "화이트", "하양"])
    def test_a_plain_white_is_not_resolved(self, name: str) -> None:
        assert resolve_color_name(name) is None

    def test_the_explicit_whites_do_resolve(self) -> None:
        """갈래를 명시하면 값이 있다 — 못 찾는 게 아니라 못 고르는 것이다."""
        assert resolve_color_name("Warm White") == (100, 75, 40)
        assert resolve_color_name("Cool White") == (85, 95, 100)

    def test_the_arc_palette_white_resolves_so_real_songs_are_unaffected(self) -> None:
        """운영 아크(`_ARC_PALETTE`)는 "warm white" 를 쓴다 — 실제 곡은 막히지 않는다."""
        assert resolve_color_name("warm white") == (100, 75, 40)

    def test_a_plain_white_cue_is_reported_not_swallowed(self) -> None:
        """감독 결정 대기 상태가 조용히 묻히지 않는다."""
        _, stub = _commands(_composition(("흰색", "cyan")))
        assert any("흰색" in reason for reason in stub._last_color_failures.values())


class TestTheFabricatedControl:
    """날조 대조군 — 색을 안 내던 옛 동작을 되돌리면 위 단정이 빨개진다.

    빈 팔레트로는 옛 동작을 흉내 낼 수 없다: `PaletteDecision` 이 빈 색
    목록을 거부한다(`song_plan.py:212`, 실측). 그래서 고치기 **전의 그
    자리**를 되돌린다 — 값 라인 생성기가 아무 것도 내지 않던 상태.
    """

    def test_silencing_the_colour_helper_brings_the_measured_defect_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        composition = _composition(("blue", "cyan"), ("amber", "red"))

        # 비공허성 — 지금은 실제로 색이 나간다.
        before = _color_lines(_commands(composition)[0])
        assert len(before) == 2

        # 옛 동작 복원: 값 라인 생성기가 빈손으로 돌아온다.
        monkeypatch.setattr(
            "server.web.session._song_color_value_lines", lambda cue, fids: ((), None)
        )
        after = _color_lines(_commands(composition)[0])
        assert after == [], "옛 동작을 되돌렸는데도 색이 나갔다 — 다른 자리가 내고 있다"

    def test_the_helper_itself_answers_both_ways(self) -> None:
        """헬퍼 단위 — 아는 색은 줄을, 모르는 색은 사유를 낸다."""
        known = _composition(("blue", "cyan")).bundle.cues[0]
        lines, failure = _song_color_value_lines(known, _FIDS)
        assert lines and failure is None

        unknown = _composition(("gold", "cyan")).bundle.cues[0]
        lines, failure = _song_color_value_lines(unknown, _FIDS)
        assert lines == () and failure is not None and "gold" in failure

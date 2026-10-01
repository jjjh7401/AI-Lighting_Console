"""카드 t501 M3 후속 — SPEC-LDRENDER-001, AC-LDRENDER-001 climax_return 결함.

M4 보고서(`.moai/reports/t501/M4.md` §4 Gaps 1)가 플래그한 결함: climax_return
큐(``kind == "climax_return"``)는 ``_song_color_value_lines``·
``_role_dimmer_value_lines``·``_role_color_value_lines``·``_white_palette_name``
전부 ``cue.kind != "section"``에 걸려 역할별 줄을 하나도 못 낸다. 그런데
``position_cue_bundle``(``server/spatial/mib.py``)의 전체 기구 키 디머 줄은
kind 와 무관하게 항상 나가 전체 기구를 ``key_pct`` 하나로 되감는다 —
back/mover/side/wash 가 전부 뭉개져 ``ldrender_gate.layer_diversity`` 의 LIT
버킷이 무너진다(8곡 중 8곡, 곡마다 climax_return 큐 1개씩, AC-001 FAIL).

이 파일은 ``cue.kind`` 허용 집합을 ``_ROLE_VALUE_LINE_KINDS =
frozenset({"section", "climax_return"})``로 넓힌 수정을 직접 겨눈다 —
acceptance.md AC-001 본문이 명시하는 두 예외(블랙아웃 큐
``cue.dimmer.blackout``, MIB 사전이동 큐 ``kind == "mib_premove"``)는 여전히
제외 대상이다. climax_return 은 그 둘에 들지 않는다(acceptance.md AC-001:
"블랙아웃 큐... 및 MIB 사전이동 큐... 는 명시 예외" — climax_return 은 이
예외 목록에 없다).

두 축을 나눠 겨눈다:
  - ``TestStubLevel*``   : 전체 ``ComposedCue``를 짓지 않고 각 함수가 실제로
    읽는 필드만 채운 대역으로, kind 허용집합 자체를 직접 겨눈다(기존
    `test_song_cue_role_dimmer_t501.py`/`test_song_cue_role_color_t501.py`
    와 같은 패턴).
  - ``TestComposerIntegration`` : 실제 ``compose_song_cue_bundle``이 만든
    climax/climax_return 큐 쌍으로 "climax_return 이 climax 큐 자신의 값을
    그대로 재사용하는가"(``_climax_return()``이 ``dimmer``/``color`` 필드를
    교체 없이 복사만 한다는 것, song_cue_composer.py:1024-1049)를 직접
    확인한다 — 이 축이 없으면 "같은 값을 재사용한다"는 주장이 스텁 수준의
    가정일 뿐 실제 조립 경로로 검증되지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.design.color_names import resolve_color_name
from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import CueDimmerData, compose_song_cue_bundle
from server.design.song_cue_render import (
    _role_color_value_lines,
    _role_dimmer_value_lines,
    _song_color_value_lines,
    _white_palette_name,
)
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

# --------------------------------------------------------------------------
# 공유 픽스처 — 다중 그룹 매핑(t379 실측과 같은 모양, 기존 t501 테스트 파일들과
# 동형이지만 결합도를 피하려고 이 파일 전용으로 다시 선언한다).
# --------------------------------------------------------------------------

_LAYER_MAPPING = (
    {"role": "key", "group_no": 2, "group_name": "KEY"},
    {"role": "back", "group_no": 4, "group_name": "BACK"},
    {"role": "side", "group_no": 7, "group_name": "SIDE-ALL"},
    {"role": "wash", "group_no": 10, "group_name": "WASH-ALL"},
    {"role": "mover", "group_no": 13, "group_name": "MOVER-ALL"},
)

_BLUE = resolve_color_name("blue")
_AMBER = resolve_color_name("amber")
_WARM_WHITE = resolve_color_name("Warm White")
assert _BLUE is not None and _AMBER is not None and _WARM_WHITE is not None


def _dimmer(role_pct: dict[str, float], *, key_pct: float = 80.0, blackout: bool = False):
    return CueDimmerData(
        key_pct=key_pct,
        back_pct=role_pct.get("back"),
        budget_range_pct=(0.0, 100.0),
        blackout=blackout,
        role_pct=role_pct,
    )


@dataclass(frozen=True)
class _DimmerCue:
    """``_role_dimmer_value_lines``가 읽는 두 필드(``kind``·``dimmer``)만."""

    kind: str
    dimmer: CueDimmerData


@dataclass(frozen=True)
class _Color:
    palette: tuple[str, ...]


@dataclass(frozen=True)
class _ColorCue:
    """``_role_color_value_lines``/``_white_palette_name``이 읽는 필드만."""

    kind: str = "section"
    color: _Color = _Color(())


@dataclass(frozen=True)
class _FullColorCue:
    """``_song_color_value_lines``가 읽는 필드 전부."""

    kind: str
    cue_number: float
    cue_name: str
    color: _Color


class TestStubLevelRoleDimmerValueLines:
    """``_role_dimmer_value_lines`` — ``_ROLE_VALUE_LINE_KINDS`` 직접 겨눔."""

    def test_climax_return_emits_the_same_role_lines_as_section(self) -> None:
        """climax_return 은 section 과 같은 역할별 델타 줄을 낸다 — M4 결함의
        핵심 수정 지점(AC-001 이 재는 LIT 버킷 복원)."""
        role_pct = {"key": 80.0, "back": 64.0, "side": 50.0, "wash": 45.0, "mover": 55.0}
        section_lines = _role_dimmer_value_lines(
            _DimmerCue(kind="section", dimmer=_dimmer(role_pct)), _LAYER_MAPPING
        )
        climax_return_lines = _role_dimmer_value_lines(
            _DimmerCue(kind="climax_return", dimmer=_dimmer(role_pct)), _LAYER_MAPPING
        )
        assert climax_return_lines == section_lines
        assert climax_return_lines != ()

    def test_mib_premove_still_emits_nothing(self) -> None:
        """AC-001 명시 예외 — MIB 사전이동 큐는 climax_return 과 달리 여전히
        아무 줄도 안 낸다(두 팔 중 하나 — 예외 보존 확인)."""
        role_pct = {"key": 80.0, "back": 64.0, "side": 50.0}
        cue = _DimmerCue(kind="mib_premove", dimmer=_dimmer(role_pct))
        assert _role_dimmer_value_lines(cue, _LAYER_MAPPING) == ()

    def test_climax_return_blackout_zero_key_pct_still_emits_nothing(self) -> None:
        """AC-001 명시 예외 — 블랙아웃은 kind 가 아니라 key_pct<=0 가드로
        막힌다(section 이든 climax_return 이든 동일). climax_return 이 kind
        허용집합에 들어갔다고 이 가드까지 뚫리면 안 된다."""
        cue = _DimmerCue(
            kind="climax_return",
            dimmer=_dimmer({"key": 0.0, "back": 0.0, "side": 0.0}, key_pct=0.0, blackout=True),
        )
        assert _role_dimmer_value_lines(cue, _LAYER_MAPPING) == ()


class TestStubLevelRoleColorValueLines:
    """``_role_color_value_lines`` — 같은 kind 허용집합을 색 축에서 겨눔."""

    def test_climax_return_emits_the_same_role_colour_lines_as_section(self) -> None:
        section_lines = _role_color_value_lines(
            _ColorCue(kind="section"), _LAYER_MAPPING, ("blue", "amber"), _BLUE
        )
        climax_return_lines = _role_color_value_lines(
            _ColorCue(kind="climax_return"), _LAYER_MAPPING, ("blue", "amber"), _BLUE
        )
        assert climax_return_lines == section_lines
        assert climax_return_lines != ()

    def test_mib_premove_still_emits_nothing(self) -> None:
        lines = _role_color_value_lines(
            _ColorCue(kind="mib_premove"), _LAYER_MAPPING, ("blue", "amber"), _BLUE
        )
        assert lines == ()


class TestStubLevelSongColorValueLines:
    """``_song_color_value_lines`` — 베이스라인 + 역할 배정 통합 축."""

    def test_climax_return_emits_the_same_lines_as_section(self) -> None:
        section_cue = _FullColorCue(
            kind="section", cue_number=12.0, cue_name="Chorus 2", color=_Color(("blue", "amber"))
        )
        climax_return_cue = _FullColorCue(
            kind="climax_return",
            cue_number=12.5,
            cue_name="Chorus 2 Return",
            color=_Color(("blue", "amber")),
        )
        section_lines, section_failure = _song_color_value_lines(
            section_cue, (1, 2, 3, 4), layer_mapping=_LAYER_MAPPING
        )
        return_lines, return_failure = _song_color_value_lines(
            climax_return_cue, (1, 2, 3, 4), layer_mapping=_LAYER_MAPPING
        )
        assert return_failure is None and section_failure is None
        assert return_lines == section_lines
        assert return_lines != ()
        assert len(return_lines) == 4  # 베이스라인 1 + side/wash/key 델타 3

    def test_mib_premove_still_emits_nothing(self) -> None:
        cue = _FullColorCue(
            kind="mib_premove", cue_number=3.5, cue_name="Move", color=_Color(("blue", "amber"))
        )
        lines, failure = _song_color_value_lines(cue, (1, 2, 3, 4), layer_mapping=_LAYER_MAPPING)
        assert lines == () and failure is None

    def test_no_layer_mapping_climax_return_is_byte_identical_to_section_legacy(self) -> None:
        """레거시 호출부 호환(``layer_mapping=()``) 은 climax_return 에도
        그대로 적용된다 — 베이스라인 한 줄만."""
        cue = _FullColorCue(
            kind="climax_return", cue_number=12.5, cue_name="Return", color=_Color(("blue",))
        )
        lines, failure = _song_color_value_lines(cue, (1, 2, 3, 4))
        assert failure is None
        assert len(lines) == 1


class TestStubLevelWhitePaletteName:
    """``_white_palette_name`` — W 채널 흰색 프리셋 선택 경로의 같은 축."""

    def test_climax_return_resolves_a_white_dominant_colour(self) -> None:
        cue = _ColorCue(kind="climax_return", color=_Color(("Warm White",)))
        assert _white_palette_name(cue) == "Warm White"

    def test_mib_premove_still_resolves_nothing(self) -> None:
        assert (
            _white_palette_name(_ColorCue(kind="mib_premove", color=_Color(("Warm White",))))
            is None
        )


# --------------------------------------------------------------------------
# 조립기(compose) 통합 — 실제 climax/climax_return 큐 쌍.
# --------------------------------------------------------------------------


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 41)
    ]
    declared_layers = {
        "key": [1, 2],
        "back": [3, 4],
        "side": [5, 6],
        "wash": [7, 8],
        "mover": [9, 10],
    }
    return build_rig_profile(patch=patch, groups={}, coords=[], declared_layers=declared_layers)


def _section(index: int, label: str, start_ms: int, d_level: int, accents=()):
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=d_level, source="section_mood"),
        palette=PaletteDecision(colors=("blue", "amber"), source="director"),
        position=PositionDecision(preset="Center", source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), disabled=(), density=0),
        accent=AccentDecision(accents=tuple(accents)),
        cue_number=index,
    )


#: t462 와 같은 모양(`test_song_cue_arc_t462.py` `_SONG`) — Chorus 2 가 절정
#: 액센트를 달아 블라인더+climax_return 을 만든다.
_SONG = (
    ("Intro", 2, ()),
    ("Verse 1", 3, ()),
    ("Chorus 1", 5, ()),
    ("Verse 2", 4, ()),
    ("Chorus 2", 5, ("climax accent",)),
    ("Finale", 5, ()),
)
_BLIND_GROUP = 14


def _plan():
    sections = tuple(
        _section(i, label, (i - 1) * 16_000, d, accents)
        for i, (label, d, accents) in enumerate(_SONG, start=1)
    )
    return UnifiedSongLightingPlan(
        song_title="t501 Climax Return Test",
        sequence_name="Climax Return Seq",
        sections=sections,
        timing=TimingPlan.trig_time(),
        music_profile=MusicProfile(bpm=120.0),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="director"),
        blinder_group_no=_BLIND_GROUP,
    )


def _cue(bundle, name):
    return next(cue for cue in bundle.cues if cue.cue_name == name)


class TestComposerIntegration:
    """``compose_song_cue_bundle``이 실제로 만든 climax/climax_return 큐 쌍."""

    def test_the_bundle_contains_exactly_one_climax_return_cue(self) -> None:
        bundle = compose_song_cue_bundle(_plan()).bundle
        returns = [cue for cue in bundle.cues if cue.kind == "climax_return"]
        assert len(returns) == 1

    def test_climax_return_dimmer_and_color_are_the_same_object_as_the_climax_cue(self) -> None:
        """``_climax_return()``(song_cue_composer.py:1024-1049)이
        ``dataclasses.replace``로 ``dimmer``/``color`` 를 교체 인자로 주지
        않는다는 사실의 직접 증거 — 복사가 아니라 같은 참조다."""
        bundle = compose_song_cue_bundle(_plan()).bundle
        climax = _cue(bundle, "Chorus 2")
        ret = next(cue for cue in bundle.cues if cue.kind == "climax_return")
        assert ret.dimmer is climax.dimmer
        assert ret.color is climax.color

    def test_role_dimmer_value_lines_are_byte_identical_between_climax_and_its_return(
        self,
    ) -> None:
        bundle = compose_song_cue_bundle(_plan()).bundle
        climax = _cue(bundle, "Chorus 2")
        ret = next(cue for cue in bundle.cues if cue.kind == "climax_return")
        climax_lines = _role_dimmer_value_lines(climax, _LAYER_MAPPING)
        return_lines = _role_dimmer_value_lines(ret, _LAYER_MAPPING)
        assert return_lines == climax_lines
        assert return_lines != (), "climax 큐 자신도 역할별 델타 줄을 내야 의미 있는 대조다"

    def test_song_color_value_lines_are_byte_identical_between_climax_and_its_return(
        self,
    ) -> None:
        bundle = compose_song_cue_bundle(_plan()).bundle
        climax = _cue(bundle, "Chorus 2")
        ret = next(cue for cue in bundle.cues if cue.kind == "climax_return")
        fids = tuple(range(1, 41))
        climax_lines, climax_failure = _song_color_value_lines(
            climax, fids, layer_mapping=_LAYER_MAPPING
        )
        return_lines, return_failure = _song_color_value_lines(
            ret, fids, layer_mapping=_LAYER_MAPPING
        )
        assert climax_failure is None and return_failure is None
        assert return_lines == climax_lines
        assert return_lines != ()

    def test_finale_section_cue_is_unaffected_sanity_check(self) -> None:
        """비교 대조 — climax_return 이 아닌 보통 section 큐는 이 변경으로
        전혀 달라지지 않는다."""
        bundle = compose_song_cue_bundle(_plan()).bundle
        finale = _cue(bundle, "Finale")
        assert finale.kind == "section"
        lines = _role_dimmer_value_lines(finale, _LAYER_MAPPING)
        assert lines != ()

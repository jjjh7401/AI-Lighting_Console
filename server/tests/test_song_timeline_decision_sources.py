"""카드 t387 — 「음악을 어떻게 분석했고 큐를 어떻게 만들었는지」 설명 리포트의
재료가 되는, 구간별 결정의 **출처**가 타임라인 페이로드에 실제로 실리는지 재는
시험.

감독의 요구는 "왜 이렇게 만들었는지 설명해서 수정을 요청할 수 있게" 하는 것.
그러려면 팔레트·D 레벨·포지션·텍스처가 **어디서 왔는지**(director / genre /
section_mood / standard 등)를 알아야 한다. 지금까지 `_song_timeline_payload`
는 값(`palette`, `d_level`, `position`, `texture`)만 내보내고 그 출처
(`decision.palette.source` 등)는 버렸다 — `SectionDecision` 은 이미 각 축마다
`source` 필드를 갖고 있으므로(song_plan.py), 이건 새로 지어내는 값이 아니라
이미 있는 필드를 흘려보내지 않던 통로를 여는 것이다.

원칙은 같다: 없는 것보다 틀린 것이 나쁘다. 출처가 없으면 필드 자체가 없어야
한다(지어내지 않는다).
"""

from __future__ import annotations

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
from server.web.session import _song_timeline_payload


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 41)
    ]
    return build_rig_profile(
        patch=patch,
        groups={},
        coords=[],
        declared_layers={"key": [1, 2], "back": [3, 4]},
    )


def _section(
    index: int,
    label: str,
    start_ms: int,
    *,
    d_level: int,
    d_source: str = "section_mood",
    palette_source: str = "director",
    position_source: str = "director",
    position_candidates: tuple[str, ...] = (),
    texture_source: str = "genre",
    role: str | None = None,
) -> SectionDecision:
    return SectionDecision(
        section=TimestampedSection(
            index=index, label=label, start_ms=start_ms, source="song_design_interview"
        ),
        d=DLevelDecision(level=d_level, source=d_source),
        palette=PaletteDecision(colors=("hot_pink", "gold_amber"), source=palette_source),
        position=PositionDecision(
            preset="Center", source=position_source, candidates=position_candidates
        ),
        texture=TextureDecision(label="long fade", source=texture_source),
        fx=FxDecision(),
        accent=AccentDecision(),
        cue_number=index * 10,
        role=role,
    )


def _plan(sections: tuple[SectionDecision, ...]) -> UnifiedSongLightingPlan:
    return UnifiedSongLightingPlan(
        song_title="Sugar",
        sequence_name="Sugar Seq",
        sections=sections,
        timing=TimingPlan.timecode(77),
        music_profile=MusicProfile(bpm=120.0, meter="4/4", key_mode="D♭ major"),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="LD"),
    )


def _payload(sections: tuple[SectionDecision, ...]) -> dict:
    plan = _plan(sections)
    return _song_timeline_payload(
        plan,
        compose_song_cue_bundle(plan),
        lifecycle="pending_approval",
        sequence_no=1,
    )


class TestSectionDecisionSourcesReachTheTimeline:
    def test_palette_source_rides_along_with_the_palette_value(self) -> None:
        payload = _payload((_section(1, "INTRO", 0, d_level=2, palette_source="director"),))
        section = payload["sections"][0]
        assert section["palette_source"] == "director"

    def test_d_level_source_rides_along_with_the_d_level_value(self) -> None:
        payload = _payload((_section(1, "INTRO", 0, d_level=2, d_source="section_mood"),))
        section = payload["sections"][0]
        assert section["d_source"] == "section_mood"

    def test_position_source_and_candidates_both_ride_along(self) -> None:
        payload = _payload(
            (
                _section(
                    1,
                    "INTRO",
                    0,
                    d_level=2,
                    position_source="director",
                    position_candidates=("Center", "Full"),
                ),
            )
        )
        section = payload["sections"][0]
        assert section["position_source"] == "director"
        assert section["position_candidates"] == ["Center", "Full"]

    def test_position_candidates_absent_when_the_plan_never_offered_any(self) -> None:
        payload = _payload((_section(1, "INTRO", 0, d_level=2, position_candidates=()),))
        section = payload["sections"][0]
        assert "position_candidates" not in section

    def test_texture_source_rides_along_with_the_texture_label(self) -> None:
        payload = _payload((_section(1, "INTRO", 0, d_level=2, texture_source="genre"),))
        section = payload["sections"][0]
        assert section["texture_source"] == "genre"

    def test_arc_role_reaches_the_timeline_when_the_decision_carries_one(self) -> None:
        payload = _payload((_section(1, "CHORUS1", 0, d_level=5, role="chorus"),))
        section = payload["sections"][0]
        assert section["role"] == "chorus"

    def test_arc_role_is_absent_when_the_decision_never_set_one(self) -> None:
        payload = _payload((_section(1, "INTRO", 0, d_level=2, role=None),))
        section = payload["sections"][0]
        assert "role" not in section

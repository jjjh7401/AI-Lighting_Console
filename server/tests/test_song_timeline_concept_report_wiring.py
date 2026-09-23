"""카드 t439 — SPEC-LDDESIGN-001 M6 §④b. 컨셉 v2 파이프라인이
``_song_timeline_payload``(session.py 진입점, ``_song_compose``·
``_song_send_timeline`` 양쪽 호출자가 공유) 를 통해 실제로 배선됐는가.

``test_song_timeline_decision_sources.py`` 와 같은 패턴 — 공개 함수
``_song_timeline_payload`` 를 직접 불러(콘솔 접촉 0건) 반환 payload에
``concept_report`` 키가 실제로 실리는지 잰다. ADDITIVE 원칙 확인이 핵심:
``concept_report`` 값과 무관하게 나머지 payload(구간·큐·린트 등)는
바뀌지 않는다.
"""

from __future__ import annotations

import pytest

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
        patch=patch, groups={}, coords=[], declared_layers={"key": [1, 2], "back": [3, 4]}
    )


def _section(index: int, label: str, start_ms: int, end_ms: int | None = None) -> SectionDecision:
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms, end_ms=end_ms),
        d=DLevelDecision(level=3, source="section_mood"),
        palette=PaletteDecision(colors=("blue",), source="director"),
        position=PositionDecision(preset="Center", source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), disabled=(), density=0),
        accent=AccentDecision(accents=()),
        cue_number=100 + index,
    )


def _plan(*, bpm: float | None, sections: tuple[SectionDecision, ...]) -> UnifiedSongLightingPlan:
    return UnifiedSongLightingPlan(
        song_title="Timeline Wiring Test",
        sequence_name="Timeline Wiring Seq",
        sections=sections,
        timing=TimingPlan.timecode(9),
        music_profile=MusicProfile(bpm=bpm),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="director"),
    )


def _payload(*, bpm: float | None, sections: tuple[SectionDecision, ...]) -> dict:
    plan = _plan(bpm=bpm, sections=sections)
    return _song_timeline_payload(
        plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
    )


class TestConceptReportKeyIsAlwaysPresentOnTimelinePayload:
    """REQ-073/074 §④b — ``_song_timeline_payload`` 는 항상
    ``concept_report`` 키를 갖는다(``_song_compose``·``_song_send_timeline``
    두 호출자 모두 이 함수를 거친다)."""

    def test_bpm_declared_payload_has_concept_report(self) -> None:
        sections = (
            _section(1, "Intro", 0, 13_000),
            _section(2, "Verse", 13_000, 26_000),
            _section(3, "Chorus 1", 26_000, 39_000),
            _section(4, "Finale", 39_000, None),
        )
        payload = _payload(bpm=120.0, sections=sections)

        assert "concept_report" in payload
        assert payload["concept_report"]["available"] is True
        assert "G1 어휘 닫힘" in payload["concept_report"]["gates"]

    def test_bpm_undeclared_payload_still_has_concept_report_unavailable(self) -> None:
        sections = (_section(1, "Intro", 0, 13_000), _section(2, "Verse", 13_000, None))
        payload = _payload(bpm=None, sections=sections)

        assert payload["concept_report"] == {
            "available": False,
            "reason": "BPM이 선언되지 않았다 — 컨셉 파이프라인의 마디 계산 전제가 없다",
        }


class TestConceptReportIsAdditiveNotBreaking:
    def test_concept_report_does_not_change_section_payload_shape(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 컨셉 파이프라인이 예외를 던져 concept_report 가 available:False
        # 여도 sections 페이로드(기존 `_song_timeline_payload` 필드)는
        # 손상되지 않는다. (이 카드가 쓰던 실패 유발원 — Outro 없이 곡이
        # 끝나 g9 이 예외 — 은 카드 t452 가 고쳐서 build_song 을 바꿔치기한다.)
        def _boom(raw_song):
            raise RuntimeError("t452 주입 실패")

        monkeypatch.setattr("server.concept.session_bridge.build_song", _boom)
        sections = (_section(1, "Intro", 0, 13_000), _section(2, "Chorus 1", 13_000, None))
        payload = _payload(bpm=100.0, sections=sections)

        assert payload["concept_report"]["available"] is False
        assert len(payload["sections"]) == 2
        assert payload["sections"][0]["label"] == "Intro"
        assert payload["song_title"] == "Timeline Wiring Test"


class TestConceptReportFollowsColorUsage:
    """카드 t439 — 감독 결정(2026-09-23): 곡별 ``per_chorus`` 선택이면 부가
    리포트의 G7(후렴 주색 동일)은 n/a, 기본값이면 실제로 판정한다."""

    _SECTIONS = (
        _section(1, "Intro", 0, 13_000),
        _section(2, "Verse", 13_000, 26_000),
        _section(3, "Chorus 1", 26_000, 39_000),
        _section(4, "Verse", 39_000, 52_000),
        _section(5, "Chorus 2", 52_000, 65_000),
        _section(6, "Finale", 65_000, None),
    )

    def _g7(self, color_usage: str) -> object:
        plan = _plan(bpm=120.0, sections=self._SECTIONS)
        payload = _song_timeline_payload(
            plan,
            compose_song_cue_bundle(plan),
            lifecycle="pending_approval",
            sequence_no=1,
            color_usage=color_usage,
        )
        report = payload["concept_report"]
        assert report["available"] is True
        return report["gates"]["G7 후렴 주색 동일"]["passed"]

    def test_per_chorus_song_reports_g7_not_applicable(self) -> None:
        assert self._g7("per_chorus") is None

    def test_default_song_judges_g7(self) -> None:
        assert self._g7("modulate") is not None

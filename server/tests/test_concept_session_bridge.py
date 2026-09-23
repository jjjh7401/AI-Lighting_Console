"""세션/툴 경로 ↔ 컨셉 파이프라인 다리 시험 — SPEC-LDDESIGN-001 M6 §④b
(REQ-LDDESIGN-073·074, 카드 t439).

``build_concept_report`` 가 콘솔 명령 경로에 배선되기 전, 그 함수
자체가 세 갈래를 정확히 구분하는지 확인한다 — (1) BPM 이 선언된 정상
곡은 게이트/MIB/린트/에너지 요약을 낸다, (2) BPM 미선언은 예외 없이
``available: False`` 로 명시된 사유와 함께 되돌린다, (3) 컨셉 파이프라인
내부가 예외를 던져도(몽키패치) 이 다리가 삼켜 콘솔 명령 경로를 막지
않는다(ADDITIVE 원칙).
"""

from __future__ import annotations

import pytest

from server.concept import gates as gates_module
from server.concept.session_bridge import (
    build_concept_report,
    build_concept_report_from_songcue_sections,
)
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
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


def _rig():
    return build_rig_profile(patch=[], groups={}, coords=[])


def _section(index: int, label: str, start_ms: int, end_ms: int | None) -> SectionDecision:
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


def _plan(*, bpm: float | None, labels: tuple[str, ...]) -> UnifiedSongLightingPlan:
    # 각 구간 13초 — 컨셉 v2 g8 빌드업 삽입(REQ-037 "5마디 이상")과 부딪히지
    # 않도록 넉넉히 둔다. 마지막 구간만 end_ms 를 비워 §"알려진 격차" 의
    # 고정 꼬리(fallback tail) 경로를 같이 확인한다.
    sections = []
    start = 0
    for i, label in enumerate(labels, start=1):
        end = start + 13_000
        is_last = i == len(labels)
        sections.append(_section(i, label, start, None if is_last else end))
        start = end
    return UnifiedSongLightingPlan(
        song_title="Bridge Test",
        sequence_name="Bridge Seq",
        sections=tuple(sections),
        timing=TimingPlan.timecode(9),
        music_profile=MusicProfile(bpm=bpm),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="director"),
    )


class TestAvailableReportForRecognizedVocabulary:
    """정상 경로 — 라벨이 9종 어휘와 맞아떨어지는 곡."""

    def test_bpm_declared_song_produces_available_report(self) -> None:
        plan = _plan(bpm=120.0, labels=("Intro", "Verse", "Chorus 1", "Chorus 2", "Finale"))
        report = build_concept_report(plan)

        assert report["available"] is True
        assert set(report["gates"]) == set(gates_module.GATE_NAMES)
        assert len(report["mib"]) > 0
        assert report["lint_finding_count"] >= 0
        assert report["energy_report_count"] > 0
        # G1(어휘 닫힘)은 통과해야 한다 — 이 픽스처의 라벨은 인식 가능한
        # 패턴(Intro/Verse/Chorus/Finale)으로만 골랐다.
        assert report["gates"]["G1 어휘 닫힘"]["passed"] is True

    def test_last_section_without_end_ms_uses_fallback_tail_without_raising(self) -> None:
        # `_plan` 은 마지막 구간의 end_ms 를 항상 None 으로 둔다 — 이
        # 시험은 그 경로가 예외 없이 리포트를 낸다는 것만 확인한다
        # (정확한 곡 길이를 안다고 주장하지 않는다, 모듈 독스트링). 마지막
        # 구간을 "Finale"(Outro 로 재매핑됨)로 둔다 — 곡이 Chorus 에서
        # 바로 끝나면(다음 절 시험의 발견 참고) gates.py 자신의 기존
        # g9(cue_only 누출 검사)가 별도 사유로 실패해, 이 시험이 확인하려는
        # "fallback tail 자체가 예외를 안 낸다"는 것과 다른 것을 재게 된다.
        plan = _plan(bpm=100.0, labels=("Intro", "Verse", "Chorus 1", "Finale"))
        report = build_concept_report(plan)
        assert report["available"] is True


class TestUnrecognizedLabelsFallBackNotRaise:
    """라벨이 9종 패턴과 안 맞아도(중립 이름 등) gates.py 의 기존
    "Rap/Solo/Dance Break" 낙하 동작으로 흡수된다 — 이 다리가 새 실패
    모드를 만들지 않는다."""

    def test_neutral_labels_still_produce_available_report(self) -> None:
        plan = _plan(bpm=120.0, labels=("S1", "S2", "S3"))
        report = build_concept_report(plan)
        assert report["available"] is True


class TestSongEndingOnCueOnlyPhraseIsJudged:
    """카드 t439 발견·t452 수정 — 곡이 (프레이즈 층의) ``cue_only`` 큐
    바로 뒤에서 끝나면(예: Outro 없이 Chorus 로 곡이 끝남), 안전 마지막
    큐가 참조하는 ``song_release_reference`` 가 그 cue_only 행에 붙어
    g9(``tracking.verify_no_cue_only_leak``)의 cue_only 필터링과 함께
    걸러졌고 ``VocabError`` 로 리포트 전체가 ``available: False`` 가
    됐다. t452 이후 기준 이름은 마지막 track 행에 붙으므로 리포트가 선다."""

    def test_chorus_with_no_outro_is_judged(self) -> None:
        plan = _plan(bpm=100.0, labels=("Intro", "Verse", "Chorus 1"))
        report = build_concept_report(plan)

        assert report["available"] is True, report
        g9 = next(v for k, v in report["gates"].items() if k.startswith("G9"))
        assert g9["passed"] is True, g9


class TestBpmUndeclaredIsUnavailableNotRaised:
    def test_bpm_none_returns_unavailable_with_reason(self) -> None:
        plan = _plan(bpm=None, labels=("Intro", "Verse", "Chorus 1"))
        report = build_concept_report(plan)

        assert report == {
            "available": False,
            "reason": "BPM이 선언되지 않았다 — 컨셉 파이프라인의 마디 계산 전제가 없다",
        }


class TestConceptPipelineFailureIsSwallowed:
    """ADDITIVE 원칙 — 컨셉 파이프라인 내부가 예외를 던져도 이 다리는
    그 예외를 삼키고 사유를 담아 되돌린다(콘솔 명령 경로를 막지 않는다)."""

    def test_build_song_exception_does_not_propagate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _boom(raw_song):
            raise RuntimeError("실측 실패 시뮬레이션")

        monkeypatch.setattr("server.concept.session_bridge.build_song", _boom)
        plan = _plan(bpm=120.0, labels=("Intro", "Verse", "Chorus 1"))

        report = build_concept_report(plan)

        assert report["available"] is False
        assert "실측 실패 시뮬레이션" in report["reason"]


class TestBuildConceptReportFromSongcueSections:
    """tools.py 경로(``prepare_songcue`` 사다리) 어댑터 —
    ``(baseline_name, start_ms)`` 쌍 목록을 직접 받는다. ``label``+
    ``instance`` 를 호출자가 이미 합쳐 넘긴다는 계약(모듈 독스트링)을
    이 시험이 검증한다."""

    def test_label_instance_pairs_produce_available_report(self) -> None:
        # label+instance 를 미리 "Chorus 2" 류로 합친 것이 이 함수의
        # 계약이다 — SongCueSection 타입 자체를 가져오지 않는다(결합도
        # 최소화, 모듈 독스트링).
        sections = [
            ("Intro", 0),
            ("Verse", 13_000),
            ("Chorus 1", 26_000),
            ("Finale", 39_000),
        ]
        report = build_concept_report_from_songcue_sections("Ladder Test", 100.0, sections)

        assert report["available"] is True
        assert set(report["gates"]) == set(gates_module.GATE_NAMES)

    def test_bpm_none_returns_unavailable_with_reason(self) -> None:
        sections = [("Intro", 0), ("Verse", 13_000)]
        report = build_concept_report_from_songcue_sections("Ladder Test", None, sections)

        assert report == {
            "available": False,
            "reason": "BPM이 선언되지 않았다 — 컨셉 파이프라인의 마디 계산 전제가 없다",
        }

    def test_empty_sections_returns_unavailable_without_raising(self) -> None:
        report = build_concept_report_from_songcue_sections("Ladder Test", 120.0, [])
        assert report == {"available": False, "reason": "구간이 없다"}

    def test_last_section_uses_fallback_tail_since_songcue_has_no_end_ms(self) -> None:
        # SongCueSection 자체에 end_ms 필드가 없다(songcue.py) — 이 시험은
        # 그 구조적 결손이 예외로 새지 않는다는 것만 확인한다.
        sections = [("Intro", 0), ("Verse", 13_000), ("Chorus 1", 26_000), ("Finale", 39_000)]
        report = build_concept_report_from_songcue_sections("Ladder Test", 100.0, sections)
        assert report["available"] is True

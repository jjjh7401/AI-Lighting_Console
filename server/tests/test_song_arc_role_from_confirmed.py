"""카드 t393 — 오디오 확정 구간이 연출 인터뷰로 넘어가면 role 이 항상 "other"
로 떨어져 팔레트/이펙트/텍스처 세 표가 동시에 우회되는 결함의 재현·회귀
테스트.

재현: 이름이 중립 ASCII(``S<n>``)이고 무드가 빈 확정 구간은
``_section_role`` 이 자연어 판독만 하므로 전부 "other" 로 판독된다. 이
테스트는 감독의 실제 곡(``reports/t383/real_song_probe.py`` 가 측정한
D 레벨 배열)과 같은 모양의 확정 기록을 세션에 심고, 지시문에 구간을 하나도
적지 않은 채(그래서 확정 기록만이 정본인 채) 연출 인터뷰를 돌려 timeline
페이로드의 팔레트/이펙트/텍스처 다양성을 잰다.
"""

from __future__ import annotations

from collections import Counter

from server.web.question import ConfirmedSongAnalysis, ConfirmedSongSection
from server.web.session import _infer_confirmed_role, _section_role

from .test_runner_self_correction import ScriptedProvider
from .test_web_session import TestSongDesignInterviewSession as _Harness
from .test_web_session import _session

# 카드 t383 실측 — reports/t383/probe-output.txt 의 "measured d_level list".
# 실제 감독 곡(걸그룹DinoDino_C_max최고품질.wav) 16개 채택 구간의 D 레벨.
_MEASURED_D_LEVELS = (2, 4, 4, 5, 5, 2, 2, 5, 4, 5, 4, 5, 1, 4, 2, 5)


def _confirmed_record(d_levels: tuple[int, ...]) -> ConfirmedSongAnalysis:
    sections = []
    cursor_ms = 0
    for index, level in enumerate(d_levels):
        end_ms = cursor_ms + 5_000
        sections.append(
            ConfirmedSongSection(
                index=index,
                label=f"S{index + 1}",
                start_ms=cursor_ms,
                end_ms=end_ms,
                d_level=level,
                selected=True,
            )
        )
        cursor_ms = end_ms
    from server.design.profile import BpmResolution

    return ConfirmedSongAnalysis(
        source_sha256="0" * 64,
        source_file_name="track.wav",
        confirmed_at="2026-09-13T00:00:00+00:00",
        bpm=BpmResolution(bpm=126.048, source="measured", reason="측정."),
        sections=tuple(sections),
    )


class TestSectionRoleFromConfirmedSections:
    """단위 판정 — role 필드 우선순위 · D 레벨 역할 추정기."""

    def test_confirmed_sections_with_empty_mood_all_read_as_other_without_role(self):
        """재현(RED 대상): 이름·무드만 보면 확정 구간은 전부 'other' 다."""
        from server.spatial.position_cuesheet import PositionSheetSection

        sections = [
            PositionSheetSection(name=f"S{i}", start_ms=i * 5000, mood="")
            for i in range(1, len(_MEASURED_D_LEVELS) + 1)
        ]
        roles = [
            _section_role(section, section_index=i, section_count=len(sections))
            for i, section in enumerate(sections, start=1)
        ]
        assert roles == ["other"] * len(sections)

    def test_explicit_role_field_wins_over_empty_mood_reading(self):
        from server.spatial.position_cuesheet import PositionSheetSection

        section = PositionSheetSection(name="S1", start_ms=0, mood="", role="chorus")
        assert _section_role(section, section_index=1, section_count=5) == "chorus"

    def test_infer_confirmed_role_first_and_last_are_intro_and_finale(self):
        roles = [
            _infer_confirmed_role(i, list(_MEASURED_D_LEVELS))
            for i in range(len(_MEASURED_D_LEVELS))
        ]
        assert roles[0] == "intro"
        assert roles[-1] == "finale"

    def test_infer_confirmed_role_produces_more_than_one_distinct_role(self):
        roles = [
            _infer_confirmed_role(i, list(_MEASURED_D_LEVELS))
            for i in range(len(_MEASURED_D_LEVELS))
        ]
        assert len(set(roles)) > 1
        # 최고 D 레벨(5) 구간은 chorus 로 잡혀야 한다.
        for index, level in enumerate(_MEASURED_D_LEVELS):
            if level == max(_MEASURED_D_LEVELS) and 0 < index < len(_MEASURED_D_LEVELS) - 1:
                assert roles[index] == "chorus"


class TestConfirmedSongDesignArcDiversity:
    """통합 재현 — 확정 기록만으로 연출 인터뷰를 돌렸을 때의 팔레트/이펙트/
    텍스처 다양성. 고침 전에는 셋 다 distinct count 1 이었다(실측, 본문
    참조)."""

    def _run(self, tmp_path):
        harness = _Harness()
        session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
        session._registry = harness._registry([])
        session._song_analysis = _confirmed_record(_MEASURED_D_LEVELS)

        class _Channel:
            def __init__(self, answers):
                self.answers = list(answers)

            def ask(self, request, **_kwargs):
                return self.answers.pop(0) if self.answers else "UNANSWERED"

        session._question_channel = _Channel(
            ["우주", "우주 색 조합", "Ring In", "우주 컨셉 우선 배치", "템포 맞춤 (BPM 기준)"]
        )
        session.run_instruction("디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7")
        timeline_events = [event for event in sent if event.get("type") == "song_timeline"]
        assert timeline_events, "song_timeline 이벤트가 발생하지 않았습니다"
        return timeline_events[0]["timeline"]["sections"]

    def test_palette_fx_texture_are_not_all_collapsed_to_one_value(self, tmp_path):
        sections = self._run(tmp_path)
        assert len(sections) >= len(_MEASURED_D_LEVELS)
        palette_counts = Counter(tuple(section["palette"]) for section in sections)
        fx_counts = Counter(tuple(section["fx"]) for section in sections)
        texture_counts = Counter(section["texture"] for section in sections)
        # 고침 전: 세 표 모두 distinct count 1 (본문 실측 — 팔레트 1종·이펙트
        # 1종·텍스처 1종). 고침 후에는 최소 2종 이상이어야 한다.
        assert len(palette_counts) > 1, f"palette 여전히 1종: {palette_counts}"
        assert len(fx_counts) > 1, f"fx 여전히 1종: {fx_counts}"
        assert len(texture_counts) > 1, f"texture 여전히 1종: {texture_counts}"

    def test_role_is_not_all_other(self, tmp_path):
        sections = self._run(tmp_path)
        # role 자체는 payload 에 실리지 않으므로 텍스처/팔레트/이펙트 다양성으로
        # 간접 확인한다(위 테스트). 여기서는 인트로/피날레에 해당하는 극단
        # 구간의 팔레트가 서로 달라야 함을 명시적으로 잰다.
        first, last = sections[0], sections[-1]
        assert (
            tuple(first["palette"]) != tuple(last["palette"]) or first["texture"] != last["texture"]
        )

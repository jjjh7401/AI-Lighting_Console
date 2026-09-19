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
            [
                "우주",
                "우주 색 조합",
                "",  # Q2B_COLOR_USAGE default-accepted
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
            ]
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


class TestBridgeRequiresALowAbsoluteBand:
    """카드 t396 — bridge 는 이웃보다 낮기만 해서는 안 되고 **절대 대역**도 낮아야 한다.

    정본 6절 표가 breakdown·bridge 를 20~35% 대역에 두므로, 낮은 대역(D1·D2)이 아닌
    구간이 bridge 룩(``_ARC_PALETTE`` 의 lavender 단색)을 받으면 무대에서 어긋난다.

    실측 2026-09-15 origin/main@47da882, 감독 실제 음원 8곡을 end-to-end 로 태워 확인:
    이웃 대비만 보는 오늘 규칙은 **밝은 bridge 5건**(Cut and Run 2 · Morning 1 ·
    Rain 1 · scott-buckley-neon 1, 전부 D4 이상)과 **연속 저강도 verse 4건**
    (Too Cool 2 · scott-buckley-neon 2, 전부 D2 이하)을 낸다. 뒤쪽은 낮은 구간이
    둘 연속이라 서로가 서로의 이웃이 되어 이웃 조건이 깨지는 자리다.

    같은 계열의 실수를 이 저장소는 t371·t375 에서 두 번 겪었고, 둘 다 상대 문턱에
    절대 대역을 섞어 고쳤다 — 그 처방을 따른다.
    """

    def test_a_bright_dip_is_not_a_bridge(self):
        # D4 가 D5 둘 사이에 낀 자리 — 이웃보다는 낮지만 밝은 대역이다.
        levels = [1, 5, 4, 5, 5]
        assert _infer_confirmed_role(2, levels) == "verse"

    def test_a_low_band_dip_is_still_a_bridge(self):
        # 양성 대조군 — 낮은 대역이면 오늘처럼 bridge 다.
        levels = [1, 5, 2, 5, 5]
        assert _infer_confirmed_role(2, levels) == "bridge"

    def test_two_consecutive_low_sections_are_both_bridges(self):
        # 연속 저강도 — 이웃 조건은 깨지지만 절대 대역이 낮으므로 bridge 다.
        levels = [5, 5, 2, 2, 5, 5]
        assert _infer_confirmed_role(2, levels) == "bridge"
        assert _infer_confirmed_role(3, levels) == "bridge"

    def test_the_measured_songs_have_no_bright_bridge(self):
        # 실측 음원에서 나온 D 레벨 배열 넷 — 어느 자리도 D4 이상 bridge 가 아니다.
        measured = {
            "Cut and Run": [4, 5, 5, 5, 3, 5, 3, 5, 4, 5, 5, 4, 5, 3, 5, 5, 2],
            "Morning": [5, 4, 5, 5, 5, 5, 5, 5, 5, 4, 4, 5, 3],
            "Rain": [2, 3, 3, 5, 5, 3, 5, 5, 5, 4, 5, 1],
            "scott-buckley-neon": [2, 2, 2, 4, 4, 4, 4, 5, 5, 4, 3, 5, 4, 5, 5, 5, 4],
        }
        for name, levels in measured.items():
            bright = [
                index
                for index, level in enumerate(levels)
                if _infer_confirmed_role(index, levels) == "bridge" and level >= 4
            ]
            assert bright == [], f"{name} 에 밝은 bridge 가 남았다: {bright}"

    def test_the_measured_songs_have_no_low_verse(self):
        # 뒷면 — 낮은 대역이 verse 로 남지 않는다(연속 저강도 누락 축).
        measured = {
            "Too Cool": [5, 5, 5, 5, 5, 5, 5, 3, 3, 4, 5, 5, 5, 5, 3, 5, 5, 5, 2, 2, 4, 4, 4],
            "scott-buckley-neon": [2, 2, 2, 4, 4, 4, 4, 5, 5, 4, 3, 5, 4, 5, 5, 5, 4],
        }
        for name, levels in measured.items():
            low = [
                index
                for index, level in enumerate(levels)
                if _infer_confirmed_role(index, levels) == "verse" and level <= 2
            ]
            assert low == [], f"{name} 에 저강도 verse 가 남았다: {low}"

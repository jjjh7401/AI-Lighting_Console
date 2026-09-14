"""앱 경로가 실제로 여러 등급의 구간을 낸다 (t411·t412 가드).

## 이 파일이 존재하는 이유

t411(구간 하한을 마디로) 과 t412(등급 포화 해소) 는 둘 다 `server/audio/analyze.py`
안에서 시험됐다. 그런데 **부품이 초록인 것은 경로가 이어진 것이 아니다** — 분석기가
좋은 값을 내도 앱이 그것을 소비하지 않으면 감독의 화면은 그대로다.

그래서 이 파일은 분석기를 직접 부르지 않고 `ChatSession.analyse_song_audio` 를 탄다 —
`server/web/app.py` 가 부르는 바로 그 메서드다. 확인 카드까지 포함한 실제 배관이며,
카드는 `_AnsweringChannel` 이 「확인」으로 즉시 수락한다(사람 대신).

## 실측 기록 (2026-09-14, `src/Club Diver.mp3` 141초 BPM 139.7)

이 경로를 실제 곡으로 태운 결과 — 저장소에 곡을 두지 않으므로 시험은 합성 트랙을
쓰고, 이 숫자는 기록으로만 남긴다:

    제안 구간 13 · 채택 13 · 제외 0 · BPM 정본 139.675 (measured)
    D 등급  D1 D5 D2 D5 D5 D5 D5 D3 D5 D5 D5 D5 D1   → 고유 4종

t411 전에는 같은 곡이 39구간이었고 D 등급은 2종(D5 12개 + D3 1개)이었다.

## 합성 트랙으로 재현할 수 없는 것 (실측으로 확인)

처음에 이득을 0.80~1.00 에 몰아 「압축된 클럽 트랙」을 만들려 했으나 **구간이 1개만
나왔다.** 이 합성기는 구간당 이득이 상수라 구간 평균과 프레임 레벨이 같고, 0.80→0.95
는 로그 계단 0.17 로 `_MIN_LOG_STEP`(0.25)에 못 미쳐 경계가 아예 생기지 않는다.

실제 클럽 트랙은 구간 **평균**이 비슷해도 경계에서 순간적으로 급락하므로 프레임 계단은
살아 있다 — 그래서 실제 곡은 13구간이 나왔다. 즉 **압축 조건은 이 합성기의 표현 범위
밖**이고, 그것은 `_grading_is_degenerate` 를 실제 곡의 실측 구간 평균으로 직접 재는
`test_audio_grade_saturation.py` 가 맡는다.

따라서 이 파일은 이득에 뚜렷한 계단을 주어 **배선**을 잰다.

## 무엇을 단언하고 무엇을 단언하지 않는가

**단언한다**: 8마디 간격으로 심은 경계가 앱 경로 끝까지 도착하고, 여러 등급으로
갈리며, 4마디 미만 구간이 없고, 구간이 곡 전체를 덮는다.

**단언하지 않는다**: 그 등급이 음악적으로 옳은지. 이 시험은 배관이지 판정이 아니다 —
「D5 가 맞는 구간인가」는 사람이 확인 카드에서 답할 몫이다(REQ-MUSICSYNC-015).
그리고 위에 적은 대로 **압축 조건은 이 파일이 재는 것이 아니다.**
"""

from __future__ import annotations

import base64

import pytest

from server.audio.analyze import analysis_available

from .fixtures.audio import FIXTURE_BPM, synthesize_track_with_steps
from .test_web_song_audio import _AnsweringChannel, _session

pytestmark = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa/soundfile 이 없으면 분석기를 돌릴 수 없다.",
)

#: 이웃 사이 로그 계단이 모두 `_MIN_LOG_STEP`(0.25) 위인 이득. 가장 작은 계단이
#: log(0.55/0.30) = 0.61 이므로 경계 여섯이 전부 검출된다 — 위 docstring 의 「합성
#: 트랙으로 재현할 수 없는 것」 참조.
_STEPPED_GAINS = (0.20, 0.55, 0.30, 0.95, 0.35, 0.75)

#: 8마디(128 BPM 에서 15000ms) 간격. t411 의 4마디 하한 위이므로 경계가 전부 살아야 한다.
_EIGHT_BAR_BOUNDARIES = tuple(15_000 * i for i in range(6))
_DURATION_MS = 90_000


def _stepped_track_b64() -> str:
    track = synthesize_track_with_steps(
        bpm=FIXTURE_BPM,
        duration_ms=_DURATION_MS,
        boundaries_ms=_EIGHT_BAR_BOUNDARIES,
        gains=_STEPPED_GAINS,
    )
    return base64.b64encode(track).decode("ascii")


@pytest.fixture
def analysed(tmp_path):
    """실제 앱 경로 — `app.py` 가 부르는 그 메서드를 그대로 탄다."""
    channel = _AnsweringChannel("확인")
    session = _session(tmp_path, None, question_channel=channel)
    session.upload_song_audio("stepped.wav", "audio/wav", _stepped_track_b64())
    session.analyse_song_audio()
    record = session.song_analysis
    assert record is not None, "확인 카드가 서지 않아 확정 기록이 없다 — 배관이 끊겼다"
    return record


class TestThePathIsWiredNotJustTested:
    def test_the_app_path_produces_a_confirmed_record(self, analysed):
        """분석기가 아니라 **세션**이 기록을 만든다 — 이 단언이 배관의 존재다."""
        assert analysed.source_file_name == "stepped.wav"
        assert analysed.bpm.bpm is not None

    def test_every_planted_boundary_becomes_a_section(self, analysed):
        """8마디 간격은 t411 하한(4마디) 위이므로 하나도 지워지지 않는다."""
        assert len(analysed.sections) == len(_EIGHT_BAR_BOUNDARIES)
        assert len(analysed.accepted) == len(_EIGHT_BAR_BOUNDARIES)
        assert analysed.dropped_count == 0


class TestTheGradesReachTheAppSpread:
    def test_the_grades_do_not_arrive_as_one_level(self, analysed):
        """등급이 한 종류로 도착하면 팔레트·효과·질감 세 표가 모두 같은 항목을 고른다."""
        levels = [section.d_level for section in analysed.accepted]

        assert len(set(levels)) >= 3, f"등급 {levels} — 앱까지 오는 동안 뭉개졌다"

    def test_the_loudest_and_quietest_sections_differ(self, analysed):
        """양성 대조 — 방향이 살아 있는가. 이득 순서와 등급 순서가 맞물려야 한다."""
        levels = [section.d_level for section in analysed.accepted]
        loudest_index = _STEPPED_GAINS.index(max(_STEPPED_GAINS))
        quietest_index = _STEPPED_GAINS.index(min(_STEPPED_GAINS))

        assert levels[loudest_index] > levels[quietest_index], f"등급 {levels}"

    def test_the_sections_cover_the_whole_track_without_gaps(self, analysed):
        """구간이 곡 전체를 겹침·공백 없이 덮는다 — 빠진 구간은 조명이 없는 시간이다."""
        accepted = analysed.accepted

        assert accepted[0].start_ms == 0
        for earlier, later in zip(accepted[:-1], accepted[1:], strict=True):
            assert earlier.end_ms == later.start_ms, f"{earlier.end_ms} != {later.start_ms}"


class TestTheSectionsAreMusicallyScaled:
    def test_no_section_is_shorter_than_four_bars(self, analysed):
        """t411 의 불변식이 앱 경로에서도 지켜진다.

        4마디 미만 구간이 도착하면 감독의 화면이 다시 박자 격자가 된다.
        """
        bar_ms = 4.0 * 60_000.0 / analysed.bpm.bpm
        short = [
            (section.start_ms, section.end_ms)
            for section in analysed.accepted
            if (section.end_ms - section.start_ms) < bar_ms * 4 - 1
        ]

        assert short == [], f"4마디 미만 구간 {short} · 1마디 {bar_ms:.0f}ms"

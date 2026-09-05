"""M2 — 분석 코어의 정답 폭과 실패 형상 (AC-MUSICSYNC-011).

정답이 알려진 합성 트랙(``server/tests/fixtures/audio``)으로만 판정한다. 실제
곡은 저장소에 없고(AC-MUSICSYNC-012), 있어도 정답이 없어 기준이 못 된다.

판정 폭은 SPEC 이 정한 그대로다 — BPM ±3%, 구간 경계 ±1000ms, D 등급 일치.
폭을 여기서 다시 정하지 않고 인수 문서의 숫자를 그대로 쓴다.

**콘솔 접촉 0건.** 이 파일은 페이크 콘솔조차 만들지 않는다 — 분석기는 콘솔을
모르는 것이 요구다(REQ-MUSICSYNC-010, 기계 고정은 ``test_audio_boundary.py``).
"""

from __future__ import annotations

import socket

import pytest

from server.audio.analyze import AnalysisFailure, AnalysisResult, analysis_available, analyze

from .fixtures.audio import (
    FIXTURE_BOUNDARIES_MS,
    FIXTURE_BPM,
    FIXTURE_D_LEVELS,
    synthesize_track,
)

BPM_TOLERANCE_RATIO = 0.03
BOUNDARY_TOLERANCE_MS = 1000

pytestmark = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa 미설치 — 폴백 경로는 test_audio_fallback.py 가 판정한다",
)


@pytest.fixture(scope="module")
def track() -> bytes:
    return synthesize_track()


@pytest.fixture(scope="module")
def result(track: bytes) -> AnalysisResult:
    outcome = analyze(track)
    assert isinstance(outcome, AnalysisResult), getattr(outcome, "reason", outcome)
    return outcome


class TestTheSyntheticTrackIsWhatItClaims:
    """픽스처 자체의 비-공허성 — 정답을 안 담은 트랙으로는 아무것도 판정 못 한다."""

    def test_the_track_is_a_riff_wav_of_the_declared_length(self, track: bytes):
        assert track[:4] == b"RIFF"
        assert track[8:12] == b"WAVE"
        # 40초 · 22050Hz · 16비트 모노 ≈ 1.76MB. 8 MiB 업로드 상한 아래다.
        assert 1_000_000 < len(track) < 8 * 1024 * 1024

    def test_the_four_declared_d_levels_are_all_different(self):
        # 넷이 같으면 「등급 일치」가 무엇도 판정하지 못한다.
        assert len(set(FIXTURE_D_LEVELS)) == 4


class TestMeasuredBpmLandsInTheDeclaredBand:
    def test_bpm_is_within_three_percent_of_128(self, result: AnalysisResult):
        low = FIXTURE_BPM * (1.0 - BPM_TOLERANCE_RATIO)
        high = FIXTURE_BPM * (1.0 + BPM_TOLERANCE_RATIO)
        assert low <= result.bpm <= high, f"bpm={result.bpm}"

    def test_the_band_would_reject_a_wrong_answer(self, result: AnalysisResult):
        # 대조군: 폭이 무엇이든 통과시키는 폭이면 위 시험은 공허하다.
        low = FIXTURE_BPM * (1.0 - BPM_TOLERANCE_RATIO)
        high = FIXTURE_BPM * (1.0 + BPM_TOLERANCE_RATIO)
        assert not (low <= 96.0 <= high)
        assert not (low <= 160.0 <= high)

    def test_confidence_is_a_reported_number_in_the_unit_interval(self, result: AnalysisResult):
        assert 0.0 <= result.bpm_confidence <= 1.0

    def test_a_metronomic_track_reports_high_confidence(self, result: AnalysisResult):
        # 박 간격이 정확히 일정한 트랙에서 낮은 확신이 나오면 그 숫자는
        # 규칙성을 재는 것이 아니라 아무것이나 재고 있는 것이다.
        assert result.bpm_confidence > 0.5


class TestSectionBoundariesLandWithinOneSecond:
    def test_every_declared_boundary_has_a_detected_boundary_near_it(self, result: AnalysisResult):
        misses = [
            expected
            for expected in FIXTURE_BOUNDARIES_MS
            if not any(
                abs(found - expected) <= BOUNDARY_TOLERANCE_MS for found in result.boundaries_ms
            )
        ]
        assert misses == [], f"미검출 경계 {misses} · 검출 {result.boundaries_ms}"

    def test_no_spurious_boundary_survives(self, result: AnalysisResult):
        # 반대 방향: 경계를 촘촘히 흩뿌리면 위 시험은 언제나 통과한다.
        strays = [
            found
            for found in result.boundaries_ms
            if not any(
                abs(found - expected) <= BOUNDARY_TOLERANCE_MS for expected in FIXTURE_BOUNDARIES_MS
            )
        ]
        assert strays == [], f"정답에 없는 경계 {strays}"

    def test_boundaries_are_sorted_and_start_at_zero(self, result: AnalysisResult):
        assert list(result.boundaries_ms) == sorted(result.boundaries_ms)
        assert result.boundaries_ms[0] == 0


class TestDCandidatesMatchTheDeclaredGrades:
    def test_one_candidate_per_detected_section(self, result: AnalysisResult):
        assert len(result.d_candidates) == len(result.boundaries_ms)

    def test_the_grades_are_the_declared_sequence(self, result: AnalysisResult):
        assert [c.d_level for c in result.d_candidates] == list(FIXTURE_D_LEVELS)

    def test_every_candidate_carries_the_span_it_graded(self, result: AnalysisResult):
        for candidate in result.d_candidates:
            assert candidate.end_ms > candidate.start_ms
            assert 1 <= candidate.d_level <= 5


class TestOnsetsAndRmsAreReported:
    def test_onsets_track_the_beat_grid(self, result: AnalysisResult):
        # 128 BPM · 40초면 박이 약 85개다. 온셋이 그 눈금에 못 미치면
        # (또는 터무니없이 많으면) 온셋 검출이 아니라 잡음을 세고 있다.
        assert 60 <= len(result.onsets_ms) <= 130

    def test_the_rms_curve_is_non_empty_and_finite(self, result: AnalysisResult):
        assert len(result.rms_curve) > 100
        assert all(value >= 0.0 for value in result.rms_curve)


class TestNonAudioBytesComeBackAsAFailureNotAnException:
    """AC-MUSICSYNC-011 둘째 Given — 실패는 실패 결과로 돌아온다.

    셋을 하나로 묶지 않는다(design.md §7) — 묶으면 하나가 다른 하나를 가린다.
    """

    @pytest.mark.parametrize(
        ("name", "payload"),
        [
            ("빈 바이트열", b""),
            ("잘린 RIFF 헤더", b"RIFF\x00\x00\x00\x00WA"),
            ("오디오가 아닌 텍스트", "이건 음악이 아니라 문장입니다".encode()),
            ("PNG 헤더", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64),
        ],
    )
    def test_each_malformed_payload_yields_a_failure_with_a_reason(self, name, payload):
        outcome = analyze(payload)
        assert isinstance(outcome, AnalysisFailure), f"{name}: {outcome!r}"
        assert outcome.reason, f"{name}: 사유가 비었다"

    def test_a_failure_is_not_a_partial_result_wearing_a_success_shape(self):
        outcome = analyze(b"")
        assert not isinstance(outcome, AnalysisResult)
        assert not hasattr(outcome, "bpm")

    def test_the_control_still_succeeds(self, result: AnalysisResult):
        # 대조군: 전부 실패로 답하는 함수라면 위 시험들은 공허하다.
        assert isinstance(result, AnalysisResult)


class TestTheAnalysisTouchesNoFilesystemOrNetwork:
    """AC-MUSICSYNC-011 — 호출 동안 파일 시스템·네트워크 접촉 0건.

    ⚠️ 모듈 **최초 import** 는 이 판정에서 제외한다. librosa/numba 는 import 시점에
    캐시 파일을 열고, 그것은 분석 행위가 아니라 적재 행위다. 그래서 가드를 걸기
    전에 먼저 한 번 분석해 import 를 데워 두고(``result`` 픽스처가 그 일을 한다),
    **데워진 뒤의 호출**만 가드 아래에서 잰다. 이 제외를 숨기지 않고 여기 적는다.
    """

    def test_a_warmed_analysis_opens_no_file_and_no_socket(
        self, track: bytes, result: AnalysisResult, monkeypatch
    ):
        assert isinstance(result, AnalysisResult)  # import 는 이미 데워졌다

        opened: list[str] = []
        connected: list[str] = []
        real_open = open

        def refusing_open(*args, **kwargs):
            opened.append(repr(args[0] if args else kwargs))
            raise AssertionError(f"분석 중 파일을 열었다: {opened[-1]}")

        def refusing_socket(*args, **kwargs):
            connected.append(repr(args))
            raise AssertionError(f"분석 중 소켓을 만들었다: {connected[-1]}")

        monkeypatch.setattr("builtins.open", refusing_open)
        monkeypatch.setattr(socket, "socket", refusing_socket)
        try:
            second = analyze(track)
        finally:
            monkeypatch.setattr("builtins.open", real_open)

        assert isinstance(second, AnalysisResult)
        assert opened == []
        assert connected == []

    def test_the_guard_would_catch_a_real_open(self, monkeypatch, tmp_path):
        # 대조군: 가드가 아무것도 못 잡는 가드라면 위 시험은 공허하다.
        def refusing_open(*args, **kwargs):
            raise AssertionError("caught")

        monkeypatch.setattr("builtins.open", refusing_open)
        with pytest.raises(AssertionError, match="caught"):
            # 컨텍스트 매니저를 쓰지 않는 것이 이 대조군의 요점이다 — 가드가
            # ``open`` 진입에서 이미 막는지를 보는 것이라 파일이 열리지 않는다.
            open(tmp_path / "x", "w")  # noqa: SIM115


class TestTheSameBytesGiveTheSameAnswer:
    def test_analysis_is_deterministic(self, track: bytes, result: AnalysisResult):
        again = analyze(track)
        assert isinstance(again, AnalysisResult)
        assert again.bpm == result.bpm
        assert again.boundaries_ms == result.boundaries_ms
        assert [c.d_level for c in again.d_candidates] == [c.d_level for c in result.d_candidates]

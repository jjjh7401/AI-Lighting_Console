"""M2 폴백 — 분석기가 없는 배포본에서도 카드 경로와 기본값 고지가 산다.

plan.md §C 결정 1 · AC-MUSICSYNC-017.

번들 델타가 상한(300MB)을 넘으면 분석은 **개발 모드 전용**이 되고, 패키징된
앱은 **같은 확인 카드**로 수동 BPM 입력을 받는다. 그때 살아 있어야 하는 것은
둘이다 — 카드 경로, 그리고 ``bpm_is_default`` 고지.

이 파일은 그 폴백을 **시뮬레이션이 아니라 실제 import 실패로** 만든다:
``sys.modules['librosa'] = None`` 이면 CPython 의 ``import librosa`` 가
``ImportError`` 를 낸다. 「없는 셈 친다」가 아니라 정말로 없을 때의 경로다.

콘솔 접촉: 0건.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

from server.audio.analyze import (
    MANUAL_BPM_FALLBACK_REASON,
    AnalysisFailure,
    AnalysisResult,
    analysis_available,
    analyze,
)
from server.design.interview import _tempo_band_texture
from server.design.profile import BPM_SOURCE_DEFAULT, MusicProfile, resolve_bpm
from server.web.question import build_song_confirmation_card, parse_confirmed_bpm

from .fixtures.audio import synthesize_track


@pytest.fixture
def librosa_is_absent(monkeypatch):
    """이 배포본에 분석기가 없다 — 진짜 ``ImportError`` 로."""
    for name in ("librosa", "numpy", "soundfile"):
        monkeypatch.setitem(sys.modules, name, None)
    real_find_spec = importlib.util.find_spec

    def missing(name, *args, **kwargs):
        if name in ("librosa", "numpy", "soundfile"):
            return None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", missing)


class TestTheFallbackIsDetectedNotGuessed:
    def test_analysis_reports_itself_unavailable(self, librosa_is_absent):
        assert analysis_available() is False

    def test_analysis_reports_itself_available_in_this_tree(self):
        # 대조군: 항상 False 를 답하면 위 시험은 공허하다. 이 워크트리에는
        # librosa 가 설치돼 있으므로 참이어야 한다.
        assert analysis_available() is True


class TestAnalysisDegradesToANamedFailureNotAnException:
    def test_analysis_returns_a_failure_carrying_the_manual_bpm_reason(self, librosa_is_absent):
        outcome = analyze(synthesize_track(duration_ms=3000))
        assert isinstance(outcome, AnalysisFailure)
        assert outcome.reason == MANUAL_BPM_FALLBACK_REASON

    def test_the_reason_tells_the_operator_what_to_do(self, librosa_is_absent):
        outcome = analyze(synthesize_track(duration_ms=3000))
        assert "BPM" in outcome.reason
        assert any("가" <= ch <= "힣" for ch in outcome.reason)

    def test_no_partial_result_is_dressed_as_a_success(self, librosa_is_absent):
        outcome = analyze(synthesize_track(duration_ms=3000))
        assert not isinstance(outcome, AnalysisResult)

    def test_the_same_bytes_succeed_when_the_analyser_is_present(self):
        # 대조군: 픽스처가 원래 못 읽히는 바이트열이면 위 시험들은 공허하다.
        assert isinstance(analyze(synthesize_track(duration_ms=3000)), AnalysisResult)


class TestTheCardPathSurvivesTheFallback:
    """AC-MUSICSYNC-017 — 폴백을 택해도 확인 카드 경로가 살아 있다."""

    def _fallback_card(self, librosa_absent_outcome):
        return build_song_confirmation_card(
            proposals=(),
            measured_bpm=None,
            fallback_reason=librosa_absent_outcome.reason,
        )

    def test_a_card_still_stands(self, librosa_is_absent):
        card = self._fallback_card(analyze(synthesize_track(duration_ms=3000)))
        assert card.prompt
        assert "BPM" in card.why

    def test_the_card_says_why_the_dsp_proposed_nothing(self, librosa_is_absent):
        card = self._fallback_card(analyze(synthesize_track(duration_ms=3000)))
        assert MANUAL_BPM_FALLBACK_REASON in card.why

    def test_a_typed_bpm_still_reaches_the_profile_through_that_card(self, librosa_is_absent):
        card = self._fallback_card(analyze(synthesize_track(duration_ms=3000)))
        assert card.multi is True
        confirmed = parse_confirmed_bpm("BPM 128", measured_bpm=None)
        profile = MusicProfile(bpm=resolve_bpm(measured_bpm=confirmed).bpm)
        assert profile.bpm_is_default is False
        assert profile.effective_bpm == 128.0


class TestTheDefaultDisclosureSurvivesTheFallback:
    """AC-MUSICSYNC-017 — 폴백에서도 ``bpm_is_default`` 고지가 산다.

    폴백에서 아무도 BPM 을 적어 주지 않으면 오늘과 똑같아야 한다. 폴백이
    「BPM 을 몰라도 대충 120 으로 간다」를 조용히 만들면, 그 조용함이 곧
    지어낸 숫자다.
    """

    def test_no_typed_bpm_leaves_the_default_marker_on(self, librosa_is_absent):
        resolution = resolve_bpm(measured_bpm=parse_confirmed_bpm("네", measured_bpm=None))
        assert resolution.source == BPM_SOURCE_DEFAULT
        assert MusicProfile(bpm=resolution.bpm).bpm_is_default is True

    def test_the_disclosure_string_is_still_attached(self, librosa_is_absent):
        resolution = resolve_bpm(measured_bpm=parse_confirmed_bpm("네", measured_bpm=None))
        _texture, reason = _tempo_band_texture(MusicProfile(bpm=resolution.bpm))
        assert "BPM 미지정, 120 기본값" in reason

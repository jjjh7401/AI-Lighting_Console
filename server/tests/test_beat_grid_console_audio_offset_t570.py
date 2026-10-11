"""SPEC-LDBEAT-001 M9 step 7 — 「콘솔 같이」 음원 지연 데이터 (카드 t570,
REQ-LDBEAT-024(a)).

코디네이터 정정(2026-10-11, 카드 t570 중간 지시): 콘솔 타임코드 시작 뒤
음원이 맞춰 시작되는 지연(t520 실측 3.002초)은 코드 상수가 아니라
`beat_grid_data/console_audio_offset.yaml`에 근거와 함께 산다. 이 시험은
그 데이터 파일을 읽는 순수 함수만 본다 — 콘솔 접촉 0건.
"""

from __future__ import annotations

from server.design.beat_grid_console_audio_offset import (
    CONSOLE_AUDIO_OFFSET_SECONDS,
    CONSOLE_AUDIO_OFFSET_SOURCE,
)


class TestConsoleAudioOffsetData:
    def test_offset_is_the_t520_measured_value(self) -> None:
        assert CONSOLE_AUDIO_OFFSET_SECONDS == 3.002

    def test_source_cites_t520_and_is_not_empty(self) -> None:
        assert CONSOLE_AUDIO_OFFSET_SOURCE
        assert "t520" in CONSOLE_AUDIO_OFFSET_SOURCE

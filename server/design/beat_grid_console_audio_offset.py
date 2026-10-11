"""「콘솔 같이」 음원 지연 — 콘솔 접촉 0건 (카드 t570, REQ-LDBEAT-024(a)).

이 모듈은 콘솔에 아무것도 쓰지 않는다. `beat_grid_data/
console_audio_offset.yaml` 하나를 읽는 순수 함수뿐이다(``server.design.
beat_grid_measured``와 같은 모양). "콘솔 같이" 토글이 켜지면(이 카드
범위 밖인 콘솔 송신 경로가 생긴 뒤) 콘솔 타임코드가 시작된 뒤 음원이
시작돼야 할 지연(초)은 코드 상수가 아니라 이 데이터 파일에서 온다 —
이 모듈 코드 안에는 리그 전용 숫자 리터럴이 없다(카드 t570 코디네이터
정정 2026-10-11, REQ-LDBEAT-006(vi-6)과 같은 원칙).

``BeatGridView.console_audio_offset_seconds``(``beat_grid.py``
``default_beat_grid``)가 이 모듈의 ``CONSOLE_AUDIO_OFFSET_SECONDS``를
그대로 실어 UI로 보낸다 — UI 쪽 순수 헬퍼
(``ui/src/components/beatgrid/consoleSyncAudio.ts``
``consoleSyncAudioStartOffsetSeconds``)는 그 값을 받아서 검증만 한다.
"""

from __future__ import annotations

from pathlib import Path

import yaml

__all__ = [
    "CONSOLE_AUDIO_OFFSET_SECONDS",
    "CONSOLE_AUDIO_OFFSET_SOURCE",
]

_DATA_PATH = Path(__file__).resolve().parent / "beat_grid_data" / "console_audio_offset.yaml"


def _load() -> tuple[float | None, str | None]:
    with _DATA_PATH.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict):
        return None, None
    raw_seconds = document.get("audio_after_timecode_seconds")
    raw_source = document.get("source")
    seconds = float(raw_seconds) if isinstance(raw_seconds, (int, float)) else None
    source = str(raw_source) if raw_source is not None else None
    return seconds, source


#: 모듈 로드 시 한 번 읽는다(``beat_grid_measured.MEASURED_MOVEMENTS``와
#: 같은 캐싱 — 이 값은 호출마다 바뀌는 인자가 없다).
CONSOLE_AUDIO_OFFSET_SECONDS, CONSOLE_AUDIO_OFFSET_SOURCE = _load()

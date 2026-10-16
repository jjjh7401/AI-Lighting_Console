"""새 곡 분석으로 새 작업본 타임라인을 만든다 — SPEC-LDRHYTHM-001 (리드 지시 2026-10-16).

곡을 새로 첨부·분석해 구간을 확인하고 마디 지도까지 저장하면, 그 곡의 작업본은 분석이 낸 구간과
마디 지도, 빈 격자로 새로 시작해야 한다. 예전에는 마디 지도만 옛 작업본에 붙어 옛 구간·옛 칸·옛
타임코드가 그대로 남았다. 이 모듈은 순수 함수뿐이다(파일·콘솔·라이브러리 무접촉).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from server.design.beat_grid import default_beat_grid

__all__ = ["ANALYSIS_SOURCE_KEY", "build_analysis_timeline"]

#: 이 작업본을 만든 분석의 오디오 해시. 같은 분석으로 다시 만들지 않으려고 본다.
ANALYSIS_SOURCE_KEY = "analysis_source_sha256"

_LAYOUT_KEYS = ("group_no", "group_no_confirmed", "group_name", "layer_role")


class AnalysisSection(Protocol):
    label: str
    start_ms: int
    end_ms: int
    d_level: int


def _bar_at(bars: Sequence[Mapping[str, Any]], start_ms: int) -> int:
    """``start_ms`` 를 품은 마디 — 시작 시각이 ``start_ms`` 이하인 마지막 마디. 앞이면 첫 마디."""
    found = int(bars[0]["bar"])
    for entry in bars:
        if int(entry["start_ms"]) <= start_ms:
            found = int(entry["bar"])
        else:
            break
    return found


def build_analysis_timeline(
    *,
    song_title: str,
    sections: Sequence[AnalysisSection],
    bar_map: Mapping[str, Any],
    layout: Sequence[Mapping[str, Any]],
    source_sha256: str,
) -> dict[str, Any]:
    """확정 분석 구간 · 마디 지도 · 줄 구성으로 새 타임라인을 만든다.

    - ``sections`` 는 채택된 분석 구간이다. 이름·시각·D 레벨을 그대로 옮기고, 마디 지도로
      ``bar_start``·``bar_count`` 를 붙인다. 같은 마디에서 시작하는 구간은 앞의 것만 남긴다.
    - 격자는 ``layout`` 의 줄 구성만 가져오고 칸은 비운다. 데이터 범위는 마디 지도 전체다.
    - 옛 작업본의 타임코드·시퀀스 번호·콘솔 기록은 싣지 않는다 — 새 작업본이다.
    """
    bars = sorted(bar_map["bars"], key=lambda entry: int(entry["bar"]))
    first_bar, last_bar = int(bars[0]["bar"]), int(bars[-1]["bar"])
    starts: list[tuple[int, AnalysisSection]] = []
    for section in sorted(sections, key=lambda item: item.start_ms):
        bar = _bar_at(bars, int(section.start_ms))
        if starts and starts[-1][0] == bar:
            continue
        starts.append((bar, section))
    timeline_sections = []
    for position, (bar, section) in enumerate(starts):
        next_bar = starts[position + 1][0] if position + 1 < len(starts) else last_bar + 1
        timeline_sections.append(
            {
                "index": position + 1,
                "label": section.label,
                "start_ms": int(section.start_ms),
                "end_ms": int(section.end_ms),
                "d_level": section.d_level,
                "bar_start": bar,
                "bar_count": next_bar - bar,
            }
        )
    tracks = [{**{key: track.get(key) for key in _LAYOUT_KEYS}, "cues": []} for track in layout]
    return {
        "song_title": song_title,
        "sections": timeline_sections,
        "bar_map": dict(bar_map),
        # 격자 뼈대(M1 판정·콘솔 오디오 지연 등)는 기본 격자 것을 쓰고, 칸·메모는 비운다.
        "beat_grid": {
            **default_beat_grid(song_title),
            "bar_range": {"start": first_bar, "end": last_bar},
            "tracks": tracks,
            "scene_memos": [],
            "source": "analysis",
            "note": None,
        },
        ANALYSIS_SOURCE_KEY: source_sha256,
    }

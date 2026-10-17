"""새 곡 분석으로 새 작업본 타임라인을 만든다 — SPEC-LDRHYTHM-001 (리드 지시 2026-10-16).

곡을 새로 첨부·분석해 구간을 확인하고 마디 지도까지 저장하면, 그 곡의 작업본은 분석이 낸 구간과
마디 지도, 빈 격자로 새로 시작해야 한다. 예전에는 마디 지도만 옛 작업본에 붙어 옛 구간·옛 칸·옛
타임코드가 그대로 남았다. 이 모듈은 순수 함수뿐이다(파일·콘솔·라이브러리 무접촉).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from server.audio.bar_map_store import validate_bar_map
from server.design.arrange_segments import split_sections
from server.design.beat_grid import default_beat_grid

__all__ = [
    "ANALYSIS_CONFIRMED_KEY",
    "ANALYSIS_SOURCE_KEY",
    "build_analysis_timeline",
    "section_kinds_from_bar_map",
    "timeline_meter_from_bar_map",
]

#: 이 작업본을 만든 분석의 오디오 해시. 같은 분석으로 다시 만들지 않으려고 본다.
ANALYSIS_SOURCE_KEY = "analysis_source_sha256"
#: 이 작업본을 만든 분석 확인 시각. 같은 오디오라도 다시 분석·확인하면 시각이 달라 새 작업본이다
#: (1차 전체 실행 B-01 — 해시만 보면 같은 곡 재분석이 옛 격자에 마디 지도만 붙였다).
ANALYSIS_CONFIRMED_KEY = "analysis_confirmed_at"

_LAYOUT_KEYS = ("group_no", "group_no_confirmed", "group_name", "layer_role")

#: 배치 생성기의 구간 종류(``arrange_segments.split_sections``) → 화면 구간 종류
#: (``beat_grid_ui_values.SECTION_KIND_COLORS`` 의 키). 빌드는 프리 후렴,
#: 마지막 후렴은 final-chorus 다.
_SEGMENT_SCREEN_KIND = {
    "intro": "intro",
    "verse": "verse",
    "build": "pre-chorus",
    "chorus": "chorus",
    "bridge": "bridge",
    "drop": "drop",
    "last_chorus": "final-chorus",
    "outro": "outro",
}


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


def section_kinds_from_bar_map(
    spans: Sequence[tuple[int, int]], bar_map: Mapping[str, Any]
) -> list[str | None]:
    """화면 구간마다(``(시작 마디, 마디 수)``) 화면 구간 종류를 정한다.

    종류는 배치 생성기와 같은 출처 — 마디 지도의 사건으로 나눈 구간(``split_sections``)이다. 화면
    구간(분석 구간)과 사건 구간은 경계가 다를 수 있어서, 화면 구간과 가장 많은 마디가 겹치는 사건
    구간의 종류를 쓴다(같으면 앞 구간). 그래서 화면에 「후렴」이라 적힌 구간은 생성기도 후렴으로
    배치한다(같은 종류 = 같은 처리, 인수 A-09·D-04). 겹치는 마디가 없거나 마디 지도가 저장 모양
    검증을 통과하지 못하면 ``None`` 이다(종류를 지어내지 않는다)."""
    if validate_bar_map(bar_map) is not None:
        return [None] * len(spans)
    segments = split_sections(bar_map)
    kinds: list[str | None] = []
    for start, count in spans:
        end = start + max(int(count), 1) - 1
        best: tuple[int, str] | None = None
        for segment in segments:
            overlap = min(end, segment.end_bar) - max(start, segment.start_bar) + 1
            if overlap > 0 and (best is None or overlap > best[0]):
                best = (overlap, segment.kind)
        kinds.append(None if best is None else _SEGMENT_SCREEN_KIND.get(best[1]))
    return kinds


def timeline_meter_from_bar_map(
    bar_map: Mapping[str, Any] | None, bpm: float | None = None
) -> dict[str, Any]:
    """마디 지도에서 타임라인 박자 머리값(``time_signature``·``bar_count``·``seconds_per_bar``).

    화면은 한 마디 길이(``seconds_per_bar``)로 재생 위치를 마디로 바꾼다 — 없으면 시계만
    가고 격자 스크롤·재생선·마디 표시·무대가 0 에 멈춘다(2차 전체 실행 N9). 한 마디 길이는
    **선언된** BPM 과 박자표 분자가 다 있을 때만 낸다(``session._song_seconds_per_bar`` 와
    같은 규칙 — 지어내지 않는다). ``bpm`` 은 분석이 확정한 BPM 이고, 없으면 마디 지도의
    BPM 을 쓴다. 모르는 값은 키를 뺀다."""
    meter: dict[str, Any] = {}
    if not isinstance(bar_map, Mapping):
        return meter
    signature = bar_map.get("time_signature")
    beats: int | None = None
    if isinstance(signature, (list, tuple)) and len(signature) == 2:
        top, bottom = signature
        if all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in (top, bottom)):
            beats = int(top)
            meter["time_signature"] = f"{top}/{bottom}"
    bars = bar_map.get("bars")
    if isinstance(bars, list) and bars:
        meter["bar_count"] = len(bars)
    song_bpm = bpm if bpm is not None else bar_map.get("bpm")
    valid_bpm = (
        isinstance(song_bpm, (int, float)) and not isinstance(song_bpm, bool) and song_bpm > 0
    )
    if valid_bpm and beats is not None:
        meter["seconds_per_bar"] = beats * 60.0 / float(song_bpm)
    return meter


def build_analysis_timeline(
    *,
    song_title: str,
    sections: Sequence[AnalysisSection],
    bar_map: Mapping[str, Any],
    layout: Sequence[Mapping[str, Any]],
    source_sha256: str,
    bpm: float | None = None,
    confirmed_at: str | None = None,
) -> dict[str, Any]:
    """확정 분석 구간 · 마디 지도 · 줄 구성으로 새 타임라인을 만든다.

    - ``sections`` 는 채택된 분석 구간이다. 이름·시각·D 레벨을 그대로 옮기고, 마디 지도로
      ``bar_start``·``bar_count`` 를 붙인다. 같은 마디에서 시작하는 구간은 앞의 것만 남긴다.
    - 격자는 ``layout`` 의 줄 구성만 가져오고 칸은 비운다. 데이터 범위는 마디 지도 전체다.
    - 구간마다 종류(``kind``)를 마디 지도의 사건 구간으로 정해 싣는다(``section_kinds_from_bar_map``
      — 배치 생성기와 같은 출처). 이름은 분석 이름 그대로다 — 이름으로 판정하는 곳이 있어 이름은
      바꾸지 않는다. 화면은 종류 이름을 따로 붙여 보인다.
    - ``bpm`` 은 분석이 확정한 BPM 이다. 없으면 마디 지도의 BPM 을 쓴다.
    - 큐 번호(``cue_number``)는 구간 순서(1부터)다 — 화면 계약이 숫자를 요구한다(B-09).
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
    spans = [
        (bar, (starts[position + 1][0] if position + 1 < len(starts) else last_bar + 1) - bar)
        for position, (bar, _section) in enumerate(starts)
    ]
    kinds = section_kinds_from_bar_map(spans, bar_map)
    timeline_sections = [
        {
            "index": position + 1,
            "cue_number": position + 1,
            "label": section.label,
            "start_ms": int(section.start_ms),
            "end_ms": int(section.end_ms),
            "d_level": section.d_level,
            "kind": kinds[position],
            "bar_start": bar,
            "bar_count": count,
        }
        for position, ((bar, section), (_bar, count)) in enumerate(zip(starts, spans, strict=True))
    ]
    tracks = [{**{key: track.get(key) for key in _LAYOUT_KEYS}, "cues": []} for track in layout]
    song_bpm = bpm if bpm is not None else bar_map.get("bpm")
    timeline: dict[str, Any] = {
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
    if confirmed_at is not None:
        timeline[ANALYSIS_CONFIRMED_KEY] = confirmed_at
    if isinstance(song_bpm, (int, float)) and not isinstance(song_bpm, bool) and song_bpm > 0:
        timeline["bpm"] = float(song_bpm)
    timeline.update(timeline_meter_from_bar_map(bar_map, song_bpm))
    return timeline

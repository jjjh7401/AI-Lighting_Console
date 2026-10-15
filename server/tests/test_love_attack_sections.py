"""LOVE ATTACK 구간 시험 — §3 구간 배치가 측정 마디 지도 위에 맞게 놓였는지 본다.

구간 시작 시각은 고정 박 시각 픽스처를 ``derive_bars`` 로 다시 계산한 값과 같아야 하고,
구간 띠가 쓰는 환산(시작 시각 ÷ 112 BPM 마디 길이)도 같은 마디 번호를 내야 한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.audio.bar_map import BarMapFailure, derive_bars
from server.design.love_attack_timeline import build_love_attack_timeline

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LOVE_ATTACK_BEAT_GRID_PATH = FIXTURES_DIR / "love_attack_beat_grid.json"

#: 구간 띠가 시작 시각을 마디로 바꿀 때 쓰는 마디 길이(초) — 112 BPM, 4/4.
_SECONDS_PER_BAR = 240.0 / 112.0
#: 마지막 마디 번호 — 픽스처를 ``derive_bars`` 로 읽으면 마디 0(못갖춘 박)~82, 83마디다.
_LAST_BAR = 82
#: §3 표에서 옮긴 구간 시작 마디. 킥 멈춤(33·61마디)은 뒤 구간에 붙인다.
_EXPECTED_STARTS = [0, 7, 14, 18, 33, 42, 46, 61, 63, 67, 82]
#: 구간 이름 일곱 종류가 §3 순서대로 나온다(같은 종류가 다시 나오면 번호를 붙인다).
_EXPECTED_KINDS = [
    "인트로",
    "벌스",
    "프리",
    "후렴",
    "벌스",
    "프리",
    "후렴",
    "브리지",
    "드롭",
    "후렴",
    "아웃트로",
]


def _measured_bar_starts_ms() -> list[int]:
    """마디 번호를 색인으로 하는 시작 시각 목록 — 0은 못갖춘 박, 1부터는 다운비트다."""
    raw = json.loads(LOVE_ATTACK_BEAT_GRID_PATH.read_text(encoding="utf-8"))
    bars = derive_bars(raw["beat_times_ms"], raw["expected_first_beat_offset"])
    assert not isinstance(bars, BarMapFailure)
    return [bars.pickup_beats_ms[0], *bars.downbeats_ms]


def test_section_starts_and_kinds_follow_the_rules_table() -> None:
    sections = build_love_attack_timeline()["sections"]

    assert [section["bar_start"] for section in sections] == _EXPECTED_STARTS
    assert [str(section["label"]).split(" ")[0] for section in sections] == _EXPECTED_KINDS


def test_sections_are_numbered_and_cover_the_bar_map_without_gaps() -> None:
    sections = build_love_attack_timeline()["sections"]

    assert [section["index"] for section in sections] == list(range(1, len(sections) + 1))
    for current, following in zip(sections, sections[1:], strict=False):
        assert current["end_ms"] == following["start_ms"]
        assert current["bar_count"] == following["bar_start"] - current["bar_start"]
    assert sections[-1]["bar_start"] == _LAST_BAR
    # 곡의 끝은 픽스처에 없으므로 마지막 구간은 끝 시각과 마디 수를 적지 않는다.
    assert "end_ms" not in sections[-1]
    assert "bar_count" not in sections[-1]


def test_section_start_times_are_the_measured_bar_starts() -> None:
    measured = _measured_bar_starts_ms()
    sections = build_love_attack_timeline()["sections"]

    assert len(sections) == len(_EXPECTED_STARTS)
    for section in sections:
        assert section["start_ms"] == measured[section["bar_start"]]


def test_section_bars_match_what_the_beat_grid_screen_derives() -> None:
    # 구간 띠(ui/src/components/BeatGrid.tsx deriveSectionBlocks)는 시작 시각을 마디 길이로
    # 나눠 마디를 얻는다. 같은 환산에서 같은 마디가 나와야 띠가 맞는 자리에 선다.
    sections = build_love_attack_timeline()["sections"]

    assert len(sections) == len(_EXPECTED_STARTS)
    for section in sections:
        assert round(section["start_ms"] / 1000 / _SECONDS_PER_BAR) == section["bar_start"]

"""카드 t486 ③ — 컨셉 패널 큐 설명에서 「최대 N%」 수치를 뺀다(리드 결정 A, 2026-09-28).

원인(``.moai/reports/t486/brightness_probe.txt``): 설명의 밝기는 D 레벨을 읽지 않는다.
컨셉 파이프라인은 구간의 라벨·시각·팔레트만 받고 밝기는 자체 고정 사다리
(``server/concept/density.py`` — 1번 후렴 75)에서 낸다. 같은 화면의 CUE SHEET KEY 는
조립기의 D 예산 중간값이다. 실측 10구간 중 1구간만 일치했고, Chorus 1 의 D 를 5 → 2 로
바꾸면 시트는 100 → 50 으로 움직이는데 설명은 75 에 머물렀다. 틀린 숫자는 없는
숫자보다 나쁘다 — 설명은 변화 서술(복원·그룹 ±·색·남김)만 남긴다.

``describe()`` 자체(REQ-023)는 그대로다. 수치를 빼는 곳은 화면으로 나가는 유일한
자리인 ``session_bridge._concept_rows`` 다.
"""

from __future__ import annotations

import dataclasses
import re

from server.concept.session_bridge import build_concept_report
from server.design.song_plan import DLevelDecision, PaletteDecision
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section

_PERCENT = re.compile(r"\d+\s*%")

SONG = (
    ("Intro", 2, "blue"),
    ("Verse 1", 3, "blue"),
    ("Pre-Chorus 1", 4, "amber"),
    ("Chorus 1", 5, "red"),
    ("Verse 2", 3, "blue"),
    ("Chorus 2", 5, "red"),
    ("Bridge", 2, "cyan"),
    ("Chorus 3", 5, "red"),
    ("Outro", 3, "blue"),
)


def _report(song):
    sections = tuple(
        dataclasses.replace(
            _section(i + 1, label, i * 12_000),
            d=DLevelDecision(level=d, source="section_mood"),
            palette=PaletteDecision(colors=(color,), source="director"),
        )
        for i, (label, d, color) in enumerate(song)
    )
    report = build_concept_report(_plan(bpm=120.0, sections=sections))
    assert report["available"] is True, report
    return report


def _descriptions(report) -> list[str]:
    return [row["description"] for row in report["rows"]]


class TestNoBrightnessNumberOnScreen:
    def test_no_description_carries_a_percent_number(self):
        leaked = [text for text in _descriptions(_report(SONG)) if _PERCENT.search(text)]
        assert leaked == []

    def test_changing_d_level_cannot_bring_a_number_back(self):
        """대조군 — 시트가 움직이는 입력(D 5 → 2)에서도 설명은 숫자를 내지 않는다."""
        changed = list(SONG)
        changed[3] = ("Chorus 1", 2, "red")
        leaked = [text for text in _descriptions(_report(changed)) if _PERCENT.search(text)]
        assert leaked == []


class TestChangeNarrativeIsKept:
    def test_every_description_is_non_empty(self):
        assert all(text for text in _descriptions(_report(SONG)))

    def test_group_colour_and_restore_clauses_survive(self):
        texts = _descriptions(_report(SONG))
        assert any(text.startswith("+") for text in texts), texts
        assert any("색 red" in text for text in texts), texts
        assert any("복원" in text for text in texts), texts

    def test_a_row_that_only_had_brightness_says_so_without_a_number(self):
        texts = _descriptions(_report(SONG))
        assert "그룹·색 변화 없음" in texts, texts

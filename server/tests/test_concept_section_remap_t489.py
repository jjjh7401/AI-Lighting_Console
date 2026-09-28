"""카드 t489 — 구간 재매핑이 Pre-Chorus·Post-Chorus·Outro 라벨을 제 이름으로 둔다.

``remap_baseline_sections`` 는 판정기가 내는 역할 5종(intro·verse·chorus·
bridge·finale)만 알았고, 그 밖의 이름은 전부 "Rap/Solo/Dance Break" 로
떨어뜨렸다. 직접 지시 경로는 자유 라벨(``Pre-Chorus 1``, ``Outro``)을
그대로 넘기므로 9종 어휘에 이미 있는 이름이 엉뚱한 칸으로 갔다
(t486 실측: 곡 10구간 중 3구간). 8곡 픽스처는 판정기 이름만 써서 이
결함을 못 잡는다 — 그래서 이 파일이 따로 있다.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from server.concept.gates import remap_baseline_sections
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import DLevelDecision, PaletteDecision
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section
from server.web.session import _infer_confirmed_role, _song_timeline_payload

FALLBACK = "Rap/Solo/Dance Break"
PILOT = Path(__file__).parent / "fixtures" / "pilot_baseline.json"


def _raw(*names: str) -> list[dict[str, object]]:
    return [
        {"baseline_name": n, "start": f"0:{i * 10:02d}", "end": f"0:{i * 10 + 10:02d}"}
        for i, n in enumerate(names)
    ]


def _sections(*names: str) -> list[str]:
    return [s.section for s in remap_baseline_sections(_raw(*names))]


class TestVocabularyLabelsKeepTheirName:
    def test_pre_chorus_post_chorus_outro_are_not_fallback(self) -> None:
        got = _sections("Intro", "Pre-Chorus 1", "Chorus 1", "Post-Chorus 1", "Outro")
        assert got == ["Intro", "Pre-Chorus", "Chorus", "Post-Chorus", "Outro"]

    def test_occurrence_counts_per_section(self) -> None:
        got = remap_baseline_sections(_raw("Pre-Chorus 1", "Chorus 1", "Pre-Chorus 2"))
        assert [(s.section, s.occurrence) for s in got] == [
            ("Pre-Chorus", 1),
            ("Chorus", 1),
            ("Pre-Chorus", 2),
        ]


class TestExistingBehaviourUnchanged:
    def test_finale_still_becomes_outro(self) -> None:
        assert _sections("Verse 1", "Finale") == ["Verse", "Outro"]

    def test_unknown_label_still_falls_back(self) -> None:
        assert _sections("Intro", "Solo", "Instrumental") == ["Intro", FALLBACK, FALLBACK]

    def test_last_of_three_choruses_still_promoted(self) -> None:
        got = _sections("Chorus 1", "Pre-Chorus 1", "Chorus 2", "Chorus 3", "Outro")
        assert got == ["Chorus", "Pre-Chorus", "Chorus", "Final Chorus", "Outro"]

    def test_pilot_fixture_has_no_fallback(self) -> None:
        """8곡 픽스처는 판정기 이름만 쓴다 — 고치기 전에도 0 이었고 지금도 0."""
        songs = json.loads(PILOT.read_text(encoding="utf-8"))
        songs = songs if isinstance(songs, list) else list(songs.values())
        valid = [s for s in songs if "error" not in s]
        assert len(valid) == 8
        fell = [
            x.section
            for s in valid
            for x in remap_baseline_sections(s["sections"])
            if x.section == FALLBACK
        ]
        assert fell == []


SONG = [
    ("Intro", 2, "blue"),
    ("Verse 1", 3, "blue"),
    ("Pre-Chorus 1", 4, "amber"),
    ("Chorus 1", 5, "red"),
    ("Verse 2", 3, "blue"),
    ("Pre-Chorus 2", 4, "amber"),
    ("Chorus 2", 5, "red"),
    ("Bridge", 2, "cyan"),
    ("Chorus 3", 5, "red"),
    ("Outro", 3, "blue"),
]


def _payload() -> dict:
    d_levels = [d for _, d, _ in SONG]
    sections = tuple(
        dataclasses.replace(
            _section(i + 1, label, i * 12_000),
            d=DLevelDecision(level=d, source="section_mood"),
            palette=PaletteDecision(colors=(color,), source="director"),
            role=_infer_confirmed_role(i, d_levels),
        )
        for i, (label, d, color) in enumerate(SONG)
    )
    plan = _plan(bpm=120.0, sections=sections)
    bundle = compose_song_cue_bundle(plan)
    return _song_timeline_payload(plan, bundle, lifecycle="pending_approval", sequence_no=1)


class TestSessionPathSectionNames:
    """t486 이 잰 실경로 곡 — 화면 구간마다 컨셉 행의 구간 이름을 본다."""

    def test_every_screen_section_gets_its_own_concept_section(self) -> None:
        payload = _payload()
        rows = {
            r["screen_position"]: r["section"]
            for r in payload["concept_report"]["rows"]
            if r["kind"] == "section" and r["screen_position"] is not None
        }
        got = [rows.get(i) for i in range(len(SONG))]
        assert got == [
            "Intro",
            "Verse",
            "Pre-Chorus",
            "Chorus",
            "Verse",
            "Pre-Chorus",
            "Chorus",
            "Bridge",
            "Final Chorus",
            "Outro",
        ]

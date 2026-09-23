"""카드 t455·t456 — 런북 화면이 읽을 서버 데이터(SPEC-LDDESIGN-001 M7).

- t456: 구간 행에 주색·보조색 HEX(``palette_primary_hex``·
  ``palette_secondary_hex``). 값은 ``server/design/color_names.py`` 가
  해석한 것만 — 해석 못 하면 ``None``(흰색 미배선 경계 그대로).
- t455: ``concept_report`` 에 행 단위 표(``rows``)와 짝짓기 상태
  (``row_pairing``). 짝 규칙(리드 승인 2026-09-23): k번째 section 행 ↔ 화면
  구간 k(순서 기준), phrase 행은 바로 앞 section 행의 구간, safety 행은
  ``None``, 원샷은 ts 가 같은 section 행에 붙는다. section 행 수와 화면 구간
  수가 다르면 짝을 짓지 않는다(전 행 ``None`` + 사유).

두 카드 모두 기존 키는 그대로 두고 추가만 한다(lane-1 t454 가 지금 키로
화면을 짓는다).
"""

from __future__ import annotations

from dataclasses import replace

from server.concept.gates import build_song
from server.concept.session_bridge import _concept_rows, _raw_sections_from_pairs
from server.design.color_names import color_hex
from server.design.song_plan import PaletteDecision
from server.tests.test_song_timeline_concept_report_wiring import _payload, _section

#: t454 가 잰 8구간 곡(``.moai/reports/t454/measure_payload.py``) 그대로.
_LABELS = (
    ("Intro", 0),
    ("Verse 1", 15000),
    ("Chorus 1", 40000),
    ("Verse 2", 60000),
    ("Chorus 2", 85000),
    ("Bridge", 105000),
    ("Chorus 3", 125000),
    ("Outro", 150000),
)

#: t454 가 실측한 기존 구간 행 키 26개(``measure_payload.out.txt``).
_T454_SECTION_KEYS = {
    "accents", "bar_count", "bar_start", "cue_number", "d_level", "d_source",
    "duration_ms", "end_ms", "fade_seconds", "fx", "index", "intensity", "label",
    "mib", "movement", "palette", "palette_primary", "palette_source", "plan_status",
    "position", "position_source", "start_ms", "texture", "texture_source", "trans",
    "trig_time_seconds",
}  # fmt: skip
_T454_REPORT_KEYS = {
    "available", "gates", "mib", "lint_finding_count", "lint_disabled_rule_count",
    "energy_report_count",
}  # fmt: skip


def _sections(palettes: dict[int, tuple[str, ...]] | None = None):
    built = []
    for i, (label, start) in enumerate(_LABELS):
        section = _section(i + 1, label, start)
        if palettes and i in palettes:
            section = replace(
                section, palette=PaletteDecision(colors=palettes[i], source="director")
            )
        built.append(section)
    return tuple(built)


# --- t456 ------------------------------------------------------------------


class TestColorHex:
    def test_standard_palette_name(self) -> None:
        # Blue (5, 20, 100) — 0-100 을 0-255 로 반올림: 13, 51, 255
        assert color_hex("Blue") == "#0D33FF"
        assert color_hex("blue") == "#0D33FF"

    def test_korean_name_goes_through_the_same_table(self) -> None:
        assert color_hex("블루") == color_hex("Blue")

    def test_unresolved_names_are_none(self) -> None:
        # 흰색은 배선하지 않는다(color_names.py — 감독 판정 전), gold 는 10색 밖
        assert color_hex("흰색") is None
        assert color_hex("gold") is None
        assert color_hex("") is None


class TestSectionHexInPayload:
    def test_primary_and_secondary_hex(self) -> None:
        payload = _payload(bpm=120.0, sections=_sections({0: ("blue", "Amber")}))
        first = payload["sections"][0]
        assert first["palette_primary_hex"] == "#0D33FF"
        assert first["palette_secondary_hex"] == color_hex("Amber")

    def test_unresolved_or_missing_colour_is_null_not_absent(self) -> None:
        payload = _payload(bpm=120.0, sections=_sections({0: ("흰색", "gold")}))
        first, second = payload["sections"][0], payload["sections"][1]
        assert first["palette_primary_hex"] is None
        assert first["palette_secondary_hex"] is None
        # 보조색이 아예 없는 구간도 키는 있고 값은 None
        assert second["palette_secondary_hex"] is None

    def test_existing_section_keys_are_untouched(self) -> None:
        payload = _payload(bpm=120.0, sections=_sections())
        keys = set(payload["sections"][0])
        assert keys >= _T454_SECTION_KEYS
        assert keys - _T454_SECTION_KEYS == {"palette_primary_hex", "palette_secondary_hex"}


# --- t455 ------------------------------------------------------------------


class TestConceptRowsOnPayload:
    def _report(self) -> dict:
        return _payload(bpm=120.0, sections=_sections())["concept_report"]

    def test_existing_report_keys_are_untouched(self) -> None:
        report = self._report()
        assert report["available"] is True, report
        assert set(report) - _T454_REPORT_KEYS == {"rows", "row_pairing"}

    def test_one_row_per_concept_cue_with_the_fixed_fields(self) -> None:
        report = self._report()
        rows = report["rows"]
        assert len(rows) == len(report["mib"]) == 20
        assert [row["q"] for row in rows] == list(range(1, 21))
        assert set(rows[0]) == {
            "q", "ts", "kind", "section", "occurrence", "trigger", "tracking",
            "mib", "one_shot", "evidence", "screen_position",
        }  # fmt: skip

    def test_mib_matches_the_existing_mib_list(self) -> None:
        report = self._report()
        assert [row["mib"] for row in report["rows"]] == [
            None if entry is None else entry["status"] for entry in report["mib"]
        ]

    def test_evidence_is_null_everywhere(self) -> None:
        # 큐마다 근거 등급을 매기는 생산자가 없다(리드 결정 A — 생산자는 t457)
        assert all(row["evidence"] is None for row in self._report()["rows"])

    def test_pairing_follows_the_approved_rule(self) -> None:
        report = self._report()
        assert report["row_pairing"] == {"available": True, "reason": None}
        by_q = {row["q"]: row for row in report["rows"]}
        section_rows = [row for row in report["rows"] if row["kind"] == "section"]
        # k번째 section 행 ↔ 화면 구간 k
        assert [row["screen_position"] for row in section_rows] == list(range(8))
        # safety 는 곡 구간 바깥
        assert by_q[1]["screen_position"] is None
        assert by_q[20]["screen_position"] is None
        # Pre-Chorus(화면에 없는 이름)는 앞 section — Verse 1·Verse 2·Bridge
        assert (by_q[5]["section"], by_q[5]["screen_position"]) == ("Pre-Chorus", 1)
        assert by_q[9]["screen_position"] == 3
        assert by_q[14]["screen_position"] == 5
        # 후렴 phrase 는 그 후렴
        assert by_q[18]["screen_position"] == 6

    def test_one_shots_sit_on_the_section_row_with_the_same_ts(self) -> None:
        rows = self._report()["rows"]
        shots = {row["q"]: row["one_shot"] for row in rows if row["one_shot"] is not None}
        assert shots == {
            6: {"shot": "White hit", "target": "KEY+FOH"},
            10: {"shot": "White hit", "target": "KEY+FOH"},
            15: {"shot": "Blinder hit", "target": "BLIND"},
        }


class TestPairingRefusesOnCountMismatch:
    def test_mismatch_nulls_every_position_with_a_reason(self) -> None:
        raw = _raw_sections_from_pairs([(label, start) for label, start in _LABELS])
        build = build_song({"song": "t455", "bpm": 120.0, "sections": raw})
        rows, pairing = _concept_rows(build, screen_count=7)
        assert pairing["available"] is False
        assert "8" in pairing["reason"] and "7" in pairing["reason"]
        assert all(row["screen_position"] is None for row in rows)
        assert len(rows) == 20

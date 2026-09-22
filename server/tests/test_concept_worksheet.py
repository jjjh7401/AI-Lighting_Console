"""워크시트 YAML 스키마 시험 — SPEC-LDDESIGN-001 M1 (REQ-LDDESIGN-011~016).

REQ-011 의 4개 최상위 구획(palette/concept/sections/notes)이 실제로 전부
파싱 결과에 존재하는지, REQ-012~015 의 필드가 값대로 읽히는지, REQ-016 의
거부가 어느 필드에 어떤 값이 왔는지 메시지에 명시하는지를 잰다.

``sections`` 최상위 구획은 구간 줄(REQ-014, 하위 목록 ``rows``)과 원샷
목록(REQ-015, 하위 목록 ``one_shots``) 두 하위 목록을 갖는 매핑으로
설계했다 — acceptance.md AC-LDDESIGN-029 가 점 표기 ``sections.one_shots``
로 명시하고 있어(REQ-015 인용), ``one_shots`` 가 ``sections`` 아래 중첩된
키라는 근거가 spec.md/acceptance.md 안에 있다. spec.md 자신은 리터럴
YAML 예시를 주지 않으므로 ``rows`` 라는 하위 목록 이름 자체는 이 구현의
설계 결정이다(보고서에 명시).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from server.concept.worksheet import (
    OneShotRow,
    Palette,
    SectionRow,
    Worksheet,
    WorksheetError,
    load_worksheet,
    parse_worksheet,
)

_VALID_WORKSHEET_YAML = """
palette:
  primary: "Blue"
  secondary: "White"
  climax: "Red"
concept: >
  이 곡은 에너제틱한 걸그룹 곡 → 그래서 주조색은 레드 →
  무대는 뜨겁고 직선적인 분위기 → 그래서 후렴마다 White hit 으로 터뜨린다
sections:
  rows:
    - section: Intro
      occurrence: 1
      operation: retain
    - section: Chorus
      occurrence: 1
      trigger: 보컬 시작
      operation: add
      memo: "1절 후렴 시작"
  one_shots:
    - shot: White hit
      anchor_section: Chorus
      anchor_occurrence: 1
      at: "1박째"
    - shot: Dimmer bump
      anchor_section: Chorus
      anchor_occurrence: 1
      at: 2.5
notes: "감독 메모 — 자유 텍스트"
"""


def _valid_raw() -> dict:
    return yaml.safe_load(_VALID_WORKSHEET_YAML)


class TestWorksheetFourTopLevelSections:
    """REQ-011 — 최소 4개 최상위 구획이 전부 파싱 결과에 존재한다."""

    def test_round_trip_produces_a_worksheet_instance(self):
        worksheet = parse_worksheet(_valid_raw())
        assert isinstance(worksheet, Worksheet)

    def test_all_four_top_level_sections_are_populated(self):
        worksheet = parse_worksheet(_valid_raw())
        assert isinstance(worksheet.palette, Palette)
        assert isinstance(worksheet.concept, str) and worksheet.concept.strip() != ""
        assert isinstance(worksheet.sections, tuple) and len(worksheet.sections) == 2
        assert isinstance(worksheet.notes, str) and worksheet.notes != ""

    def test_missing_top_level_section_is_rejected(self):
        raw = _valid_raw()
        del raw["palette"]
        with pytest.raises(WorksheetError) as excinfo:
            parse_worksheet(raw)
        assert "palette" in str(excinfo.value)


class TestPaletteFourFields:
    """REQ-012 — palette 는 정확히 4개 필드(reserved 기본값은 climax와 동일)."""

    def test_explicit_fields_round_trip(self):
        worksheet = parse_worksheet(_valid_raw())
        assert worksheet.palette.primary == "Blue"
        assert worksheet.palette.secondary == "White"
        assert worksheet.palette.climax == "Red"

    def test_reserved_defaults_to_climax_when_omitted(self):
        worksheet = parse_worksheet(_valid_raw())
        assert worksheet.palette.reserved == ("Red",)

    def test_reserved_explicit_value_overrides_default(self):
        raw = _valid_raw()
        raw["palette"]["reserved"] = ["Gold", "Amber"]
        worksheet = parse_worksheet(raw)
        assert worksheet.palette.reserved == ("Gold", "Amber")

    def test_missing_primary_is_rejected(self):
        raw = _valid_raw()
        del raw["palette"]["primary"]
        with pytest.raises(WorksheetError) as excinfo:
            parse_worksheet(raw)
        assert "palette" in str(excinfo.value)
        assert "primary" in str(excinfo.value)


class TestConceptCausalField:
    """REQ-013 — concept 는 인과 문장을 담는 자유 문자열 필드."""

    def test_concept_is_the_free_sentence_verbatim(self):
        worksheet = parse_worksheet(_valid_raw())
        assert "레드" in worksheet.concept
        assert "White hit" in worksheet.concept


class TestSectionRowsFields:
    """REQ-014 — sections.rows 각 줄의 최소 필드."""

    def test_rows_carry_the_required_fields(self):
        worksheet = parse_worksheet(_valid_raw())
        intro, chorus = worksheet.sections
        assert isinstance(intro, SectionRow)
        assert intro.section == "Intro"
        assert intro.occurrence == 1
        assert intro.operation == "retain"
        assert intro.trigger is None  # trigger 는 생략 가능

        assert chorus.section == "Chorus"
        assert chorus.occurrence == 1
        assert chorus.trigger == "보컬 시작"
        assert chorus.operation == "add"
        assert chorus.memo == "1절 후렴 시작"

    def test_memo_is_optional_free_text_outside_vocab_check(self):
        raw = _valid_raw()
        raw["sections"]["rows"][0]["memo"] = (
            "어휘에 없는 임의 문장이어도 통과해야 한다 — REQ-016 검사 밖"
        )
        worksheet = parse_worksheet(raw)
        assert "임의 문장" in worksheet.sections[0].memo


class TestOneShotSubList:
    """REQ-015 — sections.one_shots 하위 목록 각 항목의 필드."""

    def test_one_shots_carry_the_required_fields(self):
        worksheet = parse_worksheet(_valid_raw())
        assert len(worksheet.one_shots) == 2
        first, second = worksheet.one_shots
        assert isinstance(first, OneShotRow)
        assert first.shot == "White hit"
        assert first.anchor_section == "Chorus"
        assert first.anchor_occurrence == 1
        assert first.at == "1박째"  # 상대 위치 서술 형태

        assert second.shot == "Dimmer bump"
        assert second.at == 2.5  # 초 단위 숫자 형태


class TestRejectionNamesFieldAndValue:
    """REQ-016 — section/trigger/operation/shot 밖 값은 필드+값을 명시해 거부.

    memo·notes 자유 필드는 이 검사 밖이다(위 memo 시험이 함께 증명).
    """

    def test_out_of_vocab_section_is_rejected_with_field_and_value(self):
        raw = _valid_raw()
        raw["sections"]["rows"][0]["section"] = "Interlude"
        with pytest.raises(WorksheetError) as excinfo:
            parse_worksheet(raw)
        message = str(excinfo.value)
        assert "section" in message
        assert "Interlude" in message

    def test_out_of_vocab_trigger_is_rejected_with_field_and_value(self):
        raw = _valid_raw()
        raw["sections"]["rows"][1]["trigger"] = "보컬 등장"
        with pytest.raises(WorksheetError) as excinfo:
            parse_worksheet(raw)
        message = str(excinfo.value)
        assert "trigger" in message
        assert "보컬 등장" in message

    def test_out_of_vocab_operation_is_rejected_with_field_and_value(self):
        raw = _valid_raw()
        raw["sections"]["rows"][1]["operation"] = "delete"
        with pytest.raises(WorksheetError) as excinfo:
            parse_worksheet(raw)
        message = str(excinfo.value)
        assert "operation" in message
        assert "delete" in message

    def test_out_of_vocab_shot_is_rejected_with_field_and_value(self):
        raw = _valid_raw()
        raw["sections"]["one_shots"][0]["shot"] = "Kick accent"
        with pytest.raises(WorksheetError) as excinfo:
            parse_worksheet(raw)
        message = str(excinfo.value)
        assert "shot" in message
        assert "Kick accent" in message

    def test_out_of_vocab_anchor_section_is_rejected(self):
        raw = _valid_raw()
        raw["sections"]["one_shots"][0]["anchor_section"] = "Interlude"
        with pytest.raises(WorksheetError) as excinfo:
            parse_worksheet(raw)
        message = str(excinfo.value)
        assert "anchor_section" in message
        assert "Interlude" in message


class TestLoadWorksheetFromFile:
    """REQ-011 — YAML 파일 경로에서 워크시트를 읽는다."""

    def test_load_worksheet_reads_a_real_file(self, tmp_path: Path):
        path = tmp_path / "worksheet.yaml"
        path.write_text(_VALID_WORKSHEET_YAML, encoding="utf-8")
        worksheet = load_worksheet(path)
        assert worksheet.palette.primary == "Blue"
        assert len(worksheet.sections) == 2
        assert len(worksheet.one_shots) == 2

    def test_load_worksheet_missing_file_raises_worksheet_error(self, tmp_path: Path):
        missing = tmp_path / "does-not-exist.yaml"
        with pytest.raises(WorksheetError):
            load_worksheet(missing)

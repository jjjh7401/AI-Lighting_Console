from __future__ import annotations

import ast
from pathlib import Path

import pytest

import server.looks.songcue as songcue
from server.looks.matching import DYNAMICS_TERMS
from server.looks.songcue import SectionTimeError, parse_sections


def test_parse_normalizes_three_time_formats_to_integer_ms_in_input_order():
    sections = parse_sections(
        (
            ("Intro", "0:18"),
            ("Verse", "0:18.500"),
            ("Chorus", "19.25"),
        )
    )

    assert [section.name for section in sections] == ["Intro", "Verse", "Chorus"]
    assert [section.index for section in sections] == [0, 1, 2]
    assert [section.start_ms for section in sections] == [18_000, 18_500, 19_250]
    assert [type(section.start_ms) for section in sections] == [int, int, int]


def test_parse_rejects_regression_with_index_reason_and_original_order():
    with pytest.raises(SectionTimeError) as raised:
        parse_sections((("Verse", "0:52"), ("Chorus", "0:18")))

    error = raised.value
    assert error.index == 1
    assert error.reason == "starts_before_previous"
    assert "index 1" in str(error)
    assert [section.name for section in error.sections] == ["Verse", "Chorus"]
    assert [section.start_ms for section in error.sections] == [52_000, 18_000]


def test_parse_rejects_duplicate_with_duplicate_reason_and_original_order():
    with pytest.raises(SectionTimeError) as raised:
        parse_sections((("Intro", "0:00"), ("Verse", "18.0"), ("Chorus", "0:18.000")))

    error = raised.value
    assert error.index == 2
    assert error.reason == "duplicates_previous_start"
    assert "index 2" in str(error)
    assert [section.name for section in error.sections] == ["Intro", "Verse", "Chorus"]
    assert [section.start_ms for section in error.sections] == [0, 18_000, 18_000]


def test_parser_imports_matching_vocabulary_and_defines_no_mapping_literals():
    source_paths = (Path(songcue.__file__),)
    imported = _matching_import_identifiers(source_paths)

    assert imported
    assert "DYNAMICS_TERMS" in imported
    assert _dict_literal_lines(source_paths) == []


def test_known_section_dynamics_keeps_matching_band_tuple():
    sections = parse_sections((("Chorus 1", "0:00"), ("Drop", "0:30")))

    assert sections[0].dynamics == DYNAMICS_TERMS["chorus"]
    assert sections[1].dynamics == DYNAMICS_TERMS["drop"]
    assert type(sections[0].dynamics) is tuple
    assert type(sections[1].dynamics) is tuple
    assert sections[0].requires_explicit_dynamics is False
    assert sections[1].requires_explicit_dynamics is False


def test_unknown_section_requires_explicit_dynamics_without_failing_known_sections():
    sections = parse_sections((("Verse", "0:00"), ("Breakdown", "0:30"), ("Chorus", "1:00")))

    assert sections[0].dynamics == DYNAMICS_TERMS["verse"]
    assert sections[0].requires_explicit_dynamics is False
    assert sections[1].dynamics is None
    assert sections[1].requires_explicit_dynamics is True
    assert sections[2].dynamics == DYNAMICS_TERMS["chorus"]
    assert sections[2].requires_explicit_dynamics is False


def _matching_import_identifiers(paths: tuple[Path, ...]) -> set[str]:
    identifiers: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "server.looks.matching":
                identifiers.update(alias.name for alias in node.names)
    return identifiers


def _dict_literal_lines(paths: tuple[Path, ...]) -> list[int]:
    lines: list[int] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                lines.append(node.lineno)
    return lines

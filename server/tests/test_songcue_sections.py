from __future__ import annotations

import ast
from pathlib import Path

import pytest

import server.looks.songcue as songcue
from server.looks.section_vocab import SECTION_TERMS
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


def test_parser_imports_the_section_vocabulary_and_defines_no_mapping_literals():
    """파서는 어휘를 **들여온다** — 자기 표를 만들지 않는다.

    들여오는 곳이 ``matching`` 에서 ``section_vocab`` 으로 옮겨간 것은 카드 t362 다.
    옮긴 이유는 어휘가 넓어져서가 아니라 **판정 규칙이 갈렸기** 때문이다 — 운영자 질의는
    합집합, 구간 라벨은 최장 일치(``section_vocab`` 독스트링). ``section_vocab`` 자신이
    ``matching.DYNAMICS_TERMS`` 를 들여와 합치므로 어휘는 여전히 한 벌이고, 같은 말이
    두 대역을 가지면 import 시각에 깨진다.

    dict 리터럴 금지는 그대로다: 파서 안에 매핑을 적는 순간 어휘가 두 벌이 된다.
    """
    source_paths = (Path(songcue.__file__),)
    imported = _import_identifiers(source_paths, "server.looks.section_vocab")

    assert imported
    assert "SECTION_TERMS" in imported
    assert "resolve_section_dynamics" in imported
    # 옛 통로는 닫혔다 — 합집합 판정이 구간 라벨로 되돌아오면 ``Post-Chorus`` 가 다시
    # (3,4,5) 로 읽힌다.
    assert _import_identifiers(source_paths, "server.looks.matching") == set()
    assert _dict_literal_lines(source_paths) == []


def test_known_section_dynamics_keeps_matching_band_tuple():
    sections = parse_sections((("Chorus 1", "0:00"), ("Drop", "0:30")))

    assert sections[0].dynamics == SECTION_TERMS["chorus"]
    assert sections[1].dynamics == SECTION_TERMS["drop"]
    assert type(sections[0].dynamics) is tuple
    assert type(sections[1].dynamics) is tuple
    assert sections[0].requires_explicit_dynamics is False
    assert sections[1].requires_explicit_dynamics is False


def test_unknown_section_requires_explicit_dynamics_without_failing_known_sections():
    """읽히지 않는 이름 하나가 **옆 구간을 끌고 내려가지 않는다.**

    가운데 예가 ``Breakdown`` 이었다 — 카드 t362 가 그 이름을 어휘에 실었으므로(정본
    §2.2) 이제 읽힌다. 불변식은 그대로이고 예만 어휘 밖의 이름으로 바꾼다.
    """
    sections = parse_sections((("Verse", "0:00"), ("Zzyzx", "0:30"), ("Chorus", "1:00")))

    assert sections[0].dynamics == SECTION_TERMS["verse"]
    assert sections[0].requires_explicit_dynamics is False
    assert sections[1].dynamics is None
    assert sections[1].requires_explicit_dynamics is True
    assert sections[2].dynamics == SECTION_TERMS["chorus"]
    assert sections[2].requires_explicit_dynamics is False


def test_the_breakdown_that_used_to_produce_no_cue_now_reads_as_a_still_low_section():
    """카드 t362 가 고친 자리 — 정본 §6 「breakdown · bridge」 행(20~35% · 무빙 정지).

    고치기 전 실측(main ``0c0237b``): ``Breakdown`` 은 ``dynamics=None`` 이었고 그래서
    ``requires_explicit_dynamics`` 가 참, ``_map_section_to_look`` 이 그 구간을 버렸다.
    **엉뚱한 룩이 아니라 큐가 없었다.**
    """
    sections = parse_sections((("Breakdown", "0:00"), ("브레이크다운", "0:30"), ("Bridge", "1:00")))

    assert [section.dynamics for section in sections] == [(1,), (1,), (1,)]
    assert all(section.requires_explicit_dynamics is False for section in sections)


def _import_identifiers(paths: tuple[Path, ...], module: str) -> set[str]:
    identifiers: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == module:
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

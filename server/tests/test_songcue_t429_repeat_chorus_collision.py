"""t429 — 회차별 라벨을 쓰는 업로드 경로에서 반복 코러스가 충돌로 사라지면 안 된다.

**고치기 전에 실측한 것**(카드 t429 보고): 업로드 경로가 실제로 쓰는 섹션 이름은
``Chorus 1``, ``Chorus 2`` ... 처럼 **회차마다 다른 라벨**이다(`server/tests/
test_looks_instantiate.py` 의 동일 라벨 반복 데이터와 다르다). 이 경로에서는
``_numbered_by_label`` 이 라벨마다 순번을 매기므로, 회차마다 라벨이 다르면 모든
섹션이 자기 라벨의 1회차(``section.instance == 1``)가 된다.

같은 룩을 고르는 두 번째 코러스가 값 충돌을 피하려고 ``_distinct_values_line`` /
``_ensure_marking_accent`` 로 스스로 찍는 액센트(예: ``zoom_pinch``)를 얻어도,
``_finalize_marking_accents`` 의 1회차 액센트 걷어내기(``_strip_marking_accent_
from_base_occurrence``)가 "1회차는 액센트를 받지 않는다"는 규율을
**재배열(``_reorder_yields_by_repetition``)이 실제로 건드린 자리인지 보지 않고**
모든 ``instance < 2`` 번들에 무차별로 적용해, 방금 스스로 얻은 액센트를 도로
걷어내 버렸다 — 그 결과 두 번째 코러스의 값 라인이 첫 번째 코러스와 다시
같아지고 ``build_songcue_bundle`` 이 ``movement_line_collision`` 으로 실패했다
(``Ice cream.mp3`` 9곡 표본표 중 7곡, 2 이상 반복 코러스가 있는 모든 곡).

이 파일은 실제 업로드 경로 진입점(``build_songcue_bundle``)과 실제 룩 라이브러리
(``load_library_from_dir``)로 이 회귀를 지킨다 — 손으로 만든 룩 픽스처가 아니다.
"""

from __future__ import annotations

import pytest

from server.looks.loader import load_library_from_dir
from server.looks.songcue import (
    SongCueBundleError,
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)
from server.tests.test_looks_instantiate import FULL_RIG, _groups

#: 카드 t429 보고에 실린 ``pilot_baseline.json`` 원본 (이름, 시작 시각) 쌍 —
#: 두 코러스뿐인 최소 재현(Ice cream)과, 코러스·버스가 섞여 반복되는 더 큰 재현
#: (Rain, 코러스 6회)을 함께 지킨다.
_ICE_CREAM_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Intro", "0:00"),
    ("Verse 1", "0:17"),
    ("Bridge 1", "0:27"),
    ("Chorus 1", "0:37"),
    ("Bridge 2", "0:47"),
    ("Chorus 2", "0:58"),
    ("Finale", "1:08"),
)

_RAIN_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Intro", "0:00"),
    ("Verse 1", "0:20"),
    ("Verse 2", "0:33"),
    ("Chorus 1", "0:49"),
    ("Chorus 2", "1:06"),
    ("Verse 3", "1:19"),
    ("Chorus 3", "1:46"),
    ("Chorus 4", "2:03"),
    ("Chorus 5", "2:18"),
    ("Verse 4", "2:46"),
    ("Chorus 6", "2:59"),
    ("Finale", "3:29"),
)


@pytest.mark.parametrize(
    ("song", "raw_sections", "bpm"),
    (
        ("Ice cream.mp3", _ICE_CREAM_SECTIONS, 100.4),
        ("Rain.mp3", _RAIN_SECTIONS, 76.0),
    ),
)
def test_repeat_chorus_labels_do_not_collide(
    song: str, raw_sections: tuple[tuple[str, str], ...], bpm: float
) -> None:
    library = load_library_from_dir()
    sections = parse_sections(raw_sections)
    selections = map_sections_to_looks(sections, library, "rock")

    bundle = build_songcue_bundle(
        song,
        selections,
        sequences_section={"objects": [], "truncated": False, "total": 0},
        groups_section=_groups(*FULL_RIG),
        bpm=bpm,
    )

    chorus_labels = {label for label, _ in raw_sections if label.startswith("Chorus")}
    stored_labels = {
        section_bundle.section.label
        for section_bundle in bundle.sections
        if section_bundle.commands
    }
    missing = chorus_labels - stored_labels
    assert not missing, f"{song}: chorus sections dropped from the bundle: {sorted(missing)}"


def test_repeat_chorus_labels_do_not_raise_for_every_genre() -> None:
    """리그레션 표(카드 t429): rock·edm 두 장르 모두에서 실패하지 않는다."""
    library = load_library_from_dir()
    sections = parse_sections(_ICE_CREAM_SECTIONS)
    for genre in ("rock", "edm"):
        selections = map_sections_to_looks(sections, library, genre)
        try:
            build_songcue_bundle(
                "Ice cream.mp3",
                selections,
                sequences_section={"objects": [], "truncated": False, "total": 0},
                groups_section=_groups(*FULL_RIG),
                bpm=100.4,
            )
        except SongCueBundleError as error:
            pytest.fail(f"genre={genre!r} raised {error}")

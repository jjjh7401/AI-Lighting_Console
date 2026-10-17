"""구간 종류를 마디 지도(배치 생성기와 같은 사건 구간)로 정한다 — 인수 A-09·D-04 (리드 2026-10-17).

전체 실행(full1)에서 타임라인 구간 이름이 「0:37–1:09 · D5」뿐이고 종류가 없었다. 같은 오디오를 다시
분석하면 새 작업본 경로를 타지 않고 옛 작업본에 마디 지도만 붙이기 때문이다. 이제 마디 지도를 붙일
때, 새 작업본을 만들 때, 화면 값을 만들 때 모두 생성기와 같은 출처로 종류를 싣는다.
콘솔 접촉 0건 — 마디 지도는 실제 LOVE ATTACK 분석 픽스처다.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from server.design.analysis_timeline import section_kinds_from_bar_map
from server.design.arrange_segments import split_sections
from server.design.beat_grid_ui_values import attach_beat_grid_ui_values, attach_section_kinds

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "love_attack_shape_timeline.json"

#: full1 저장본의 분석 구간 10개(이름·마디) — pw/full1-p1-tl-afteranalysis.json 에서 옮김.
_FULL1_SECTIONS = [
    ("0:00–0:13 · D1", 0, 6),
    ("0:13–0:28 · D4", 6, 7),
    ("0:28–0:37 · D3", 13, 4),
    ("0:37–1:09 · D5", 17, 15),
    ("1:09–1:22 · D4", 32, 6),
    ("1:22–1:37 · D4", 38, 7),
    ("1:37–2:11 · D5", 45, 16),
    ("2:11–2:24 · D3", 61, 6),
    ("2:24–2:58 · D5", 67, 15),
    ("2:58–3:17 · D1", 82, 1),
]
_EXPECTED = [
    "intro",
    "verse",
    "pre-chorus",
    "chorus",
    "verse",
    "verse",
    "chorus",
    "drop",
    "final-chorus",
    "outro",
]


def _bar_map() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["bar_map"]


def _full1_timeline() -> dict:
    """종류 없이 이름이 D 레벨뿐인 옛 작업본에 마디 지도가 붙은 모양(full1 과 같다)."""
    return {
        "song_title": "LOVE ATTACK",
        "sections": [
            {
                "index": i + 1,
                "label": label,
                "start_ms": 0,
                "d_level": 3,
                "bar_start": bar,
                "bar_count": count,
            }
            for i, (label, bar, count) in enumerate(_FULL1_SECTIONS)
        ],
        "bar_map": _bar_map(),
    }


def test_each_screen_section_takes_the_kind_of_the_generator_section_it_overlaps_most() -> None:
    spans = [(bar, count) for _label, bar, count in _FULL1_SECTIONS]
    assert section_kinds_from_bar_map(spans, _bar_map()) == _EXPECTED


def test_the_screen_choruses_are_exactly_where_the_generator_places_choruses() -> None:
    # 같은 종류 = 같은 처리: 화면 「후렴」 구간의 마디는 생성기도 후렴으로 배치한다.
    generator = {
        bar: segment.kind
        for segment in split_sections(_bar_map())
        for bar in range(segment.start_bar, segment.end_bar + 1)
    }
    for (_label, bar, count), kind in zip(_FULL1_SECTIONS, _EXPECTED, strict=True):
        if kind in ("chorus", "final-chorus"):
            bars = range(bar, bar + count)
            inside = sum(generator[b] in ("chorus", "last_chorus") for b in bars)
            assert inside > count / 2, (bar, count)


def test_storing_a_bar_map_on_an_old_timeline_fills_the_kinds_without_renaming() -> None:
    timeline = _full1_timeline()
    before = copy.deepcopy(timeline)
    stored = attach_section_kinds(timeline)
    assert timeline == before  # 원본은 그대로
    assert [s["kind"] for s in stored["sections"]] == _EXPECTED
    assert [s["label"] for s in stored["sections"]] == [label for label, *_ in _FULL1_SECTIONS]


def test_a_section_whose_name_says_its_kind_keeps_the_name_kind() -> None:
    timeline = _full1_timeline()
    timeline["sections"][1]["label"] = "Chorus 1"  # 이름이 종류를 말한다
    stored = attach_section_kinds(timeline)
    assert "kind" not in stored["sections"][1]
    view = attach_beat_grid_ui_values(stored)
    assert view["sections"][1]["kind"] == "chorus"


def test_the_screen_value_carries_the_kind_and_a_korean_kind_name() -> None:
    view = attach_beat_grid_ui_values(_full1_timeline())  # 저장된 종류가 없어도 마디 지도로 붙인다
    assert [s["kind"] for s in view["sections"]] == _EXPECTED
    assert [s["kind_label"] for s in view["sections"]] == [
        "인트로",
        "벌스",
        "프리",
        "후렴",
        "벌스",
        "벌스",
        "후렴",
        "드롭",
        "마지막 후렴",
        "아웃트로",
    ]
    assert view["sections"][3]["label"] == "0:37–1:09 · D5"  # 이름은 서버 값 그대로


def test_a_stale_stored_kind_loses_to_the_bar_map() -> None:
    # 예전 D 레벨 추정(D2 → bridge)이 저장돼 있어도 화면은 생성기와 같은 출처를 따른다.
    timeline = _full1_timeline()
    timeline["sections"][3]["kind"] = "bridge"
    assert attach_beat_grid_ui_values(timeline)["sections"][3]["kind"] == "chorus"


def test_no_bar_map_means_no_invented_kind() -> None:
    timeline = _full1_timeline()
    del timeline["bar_map"]
    assert all("kind" not in s for s in attach_section_kinds(timeline)["sections"])
    assert all("kind_label" not in s for s in attach_beat_grid_ui_values(timeline)["sections"])


def test_sections_without_bar_numbers_are_placed_by_their_start_time() -> None:
    bar_map = _bar_map()
    by_bar = {int(entry["bar"]): int(entry["start_ms"]) for entry in bar_map["bars"]}
    timeline = _full1_timeline()
    for section in timeline["sections"]:
        section["start_ms"] = by_bar[section.pop("bar_start")]
        del section["bar_count"]
    assert [s["kind"] for s in attach_section_kinds(timeline)["sections"]] == _EXPECTED


def test_the_session_bar_map_store_path_saves_the_kinds(tmp_path) -> None:
    # full1 이 탄 경로 — 같은 오디오라 새 작업본을 만들지 않고 옛 작업본에 마디 지도만 붙인다.
    from server.web.session import SongTimelineStore

    from .test_session_bar_map_store import _new_session

    store = SongTimelineStore()
    old = _full1_timeline()
    bar_map = old.pop("bar_map")
    store.latest = old
    session, console = _new_session(tmp_path, store=store, sent=[])
    session.store_timeline_bar_map(bar_map)
    assert store.latest["bar_map"] == bar_map
    assert [s["kind"] for s in store.latest["sections"]] == _EXPECTED
    assert console.executed == []

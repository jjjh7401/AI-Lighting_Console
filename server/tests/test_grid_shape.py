"""격자 모양 비교 도구 시험 — 정답지(손 설계 기본 격자)로 계기를 먼저 교정한다.

원칙: 같은 격자는 「비슷함」, 전부 1마디는 「다름」이고, 여섯 지표는 각자가 재는 변화에만
반응한다(한 지표만 흔들면 그 지표만 실패한다). 입력은 저장소 픽스처와 순수 함수뿐이다.
콘솔·실서버 접촉 0.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from server.audio.bar_map import BarFeatures, classify_bar_events, compute_bar_energy
from server.audio.bar_map_store import build_bar_map_payload
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.grid_shape import (
    DEFAULT_THRESHOLDS,
    REST_LABEL,
    Cell,
    ShapeCheckError,
    accent_hits,
    alignment_share,
    build_auto_candidate,
    build_context,
    cells_for_track,
    compare_grids,
    count_passes,
    length_bin,
    main,
    pattern_category,
    total_variation,
)
from server.design.love_attack_timeline import build_love_attack_timeline
from server.design.preset_plan import load_preset_annotations

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SHAPE_TIMELINE = FIXTURES / "love_attack_shape_timeline.json"


def _timeline() -> dict:
    return json.loads(SHAPE_TIMELINE.read_text(encoding="utf-8"))


def _base() -> dict:
    return default_beat_grid(LOVE_ATTACK_TITLE)


def _context():
    return build_context(_timeline(), load_preset_annotations(LOVE_ATTACK_TITLE))


def _track(grid: dict, name: str) -> dict:
    return next(track for track in grid["tracks"] if track["group_name"] == name)


# --- 계기 부품 -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "category"),
    [
        ("킥 1·2·4박 60%", "킥"),
        ("펄스 1·2·4박", "1·2·4박"),
        ("체이스 2·4박", "2·4박"),
        ("SIDE-L/R 2·4박 번갈이", "2·4박"),
        ("앞박 1회", "앞박"),
        ("17마디 3·4박 전부 비움(예고)", "3·4박"),
        ("마디 4박마다", "4박"),
        ("블라인드 2박", "2박"),
        ("5마디 1박 위치 한 칸 올림", "1박"),
        ("11마디 1박 새 자리, 정지", "1박"),
        ("바닥 쪽 좁은 빔, 정지", "정지"),
        ("정지", "정지"),
        ("유지", "유지"),
        ("—", "쉼"),
        ("팬 웨이브 2마디", "기타"),
        ("가속(마디마다 두 배)", "기타"),
        ("", "기타"),
    ],
)
def test_pattern_category_follows_priority_and_rests(label: str, category: str) -> None:
    assert pattern_category(label) == category


@pytest.mark.parametrize(
    ("length", "expected"),
    [(1, "1"), (2, "2"), (4, "4"), (8, "8"), (16, "16+"), (19, "16+"), (3, "기타"), (7, "기타")],
)
def test_length_bin_keeps_three_and_seven_visible_as_other(length: int, expected: str) -> None:
    assert length_bin(length) == expected


def test_total_variation_is_zero_for_same_and_one_for_disjoint() -> None:
    assert total_variation({"a": 1.0}, {"a": 1.0}) == 0.0
    assert total_variation({"a": 1.0}, {"b": 1.0}) == 1.0
    assert total_variation({"a": 0.5, "b": 0.5}, {"a": 1.0}) == pytest.approx(0.5)


def test_cells_end_at_next_cue_and_are_clipped_to_the_window() -> None:
    cues = [
        {"bar": 0, "label": "a"},
        {"bar": 2, "label": "b"},
        {"bar": 6, "label": "c"},
        {"bar": 12, "label": "d"},
    ]
    cells = cells_for_track(cues, (0, 9), track_name="T", color_cells=frozenset())
    assert [(cell.start, cell.length) for cell in cells] == [(0, 2), (2, 4), (6, 4)]


def test_a_cell_is_colored_by_an_annotation_inside_its_span_or_by_its_own_field() -> None:
    plain = [{"bar": 7, "label": "a"}, {"bar": 14, "label": "b"}]
    # 주석 9 는 첫 칸(7~13) 안에 든다 — 둘째 칸은 주석도 필드도 없다.
    by_annotation = cells_for_track(
        plain, (0, 25), track_name="WASH", color_cells=frozenset({("WASH", 9)})
    )
    assert [cell.colored for cell in by_annotation] == [True, False]
    # 주석 20 은 둘째 칸(14~25) 안에 든다.
    by_later_annotation = cells_for_track(
        plain, (0, 25), track_name="WASH", color_cells=frozenset({("WASH", 20)})
    )
    assert [cell.colored for cell in by_later_annotation] == [False, True]
    # 칸 필드의 색 번호도 칸을 색이 정해진 칸으로 센다.
    by_field = cells_for_track(
        [{"bar": 7, "label": "a"}, {"bar": 14, "label": "b", "color_preset_no": "3"}],
        (0, 25),
        track_name="WASH",
        color_cells=frozenset(),
    )
    assert [cell.colored for cell in by_field] == [False, True]


def test_alignment_share_counts_cell_starts_on_boundary_bars() -> None:
    cells = [Cell("T", start, 1, "") for start in (0, 3, 7, 11, 14, 18, 22)]
    assert alignment_share(cells, frozenset({0, 7, 14, 18})) == pytest.approx(4 / 7)


def test_accent_hits_skip_rests_and_allow_a_one_bar_lead_in() -> None:
    cells = [
        Cell("BLIND", 4, 1, "블라인드 2박"),
        Cell("BLIND", 17, 1, "17마디 3·4박 전부 비움(예고)"),
        Cell("BLIND", 18, 1, "18마디 1박 BLIND 100% 2박"),
        Cell("BLIND", 30, 1, REST_LABEL),
    ]
    hits = frozenset({18, 46, 63, 64, 65, 66, 67})
    # 위치 3개(쉼 제외): 4는 큰 히트 밖, 17은 예고 한 마디, 18은 후렴 진입.
    assert accent_hits(cells, hits, tolerance=1) == (3, 2)


@pytest.mark.parametrize(
    ("base", "candidate", "passes"),
    [
        (7, 5, True),
        (7, 4, True),
        (7, 10, True),
        (7, 3, False),
        (7, 11, False),
        (1, 1, True),
        (1, 2, True),  # 칸 1개 줄에 2개는 같은 종류다(최소 1칸 허용).
        (1, 3, False),
        (2, 1, True),
        (2, 4, False),
        (0, 0, True),
        (0, 1, True),  # 빈 줄도 최소 1칸 허용 안에 든다.
        (0, 2, False),
        (26, 7, False),
    ],
)
def test_count_rule_allows_half_the_base_and_at_least_one_cell(
    base: int, candidate: int, passes: bool
) -> None:
    """① 칸 수: |후보 − 기본| ≤ max(1, 0.5 × 기본)이면 같은 종류다(양쪽 방향 모두)."""
    assert count_passes(base, candidate, DEFAULT_THRESHOLDS.count_share) is passes


def test_rests_off_cells_and_advance_blanks_are_not_counted() -> None:
    cues = [
        {"bar": 0, "label": "—"},
        {"bar": 2, "label": "17마디 3·4박 전부 비움(예고)"},
        {"bar": 4, "label": "블라인드 2박", "brightness": {"mode": "value", "value_percent": 0}},
        {"bar": 6, "label": "꺼짐"},
        {"bar": 8, "label": "펄스 1·2·4박", "brightness": {"mode": "value", "value_percent": 100}},
    ]
    cells = cells_for_track(cues, (0, 25), track_name="T", color_cells=frozenset())
    # 쉼(—), 예고(비움), 밝기 0%, 「꺼짐」 라벨은 줄의 칸으로 세지 않는다.
    assert [cell.counted for cell in cells] == [False, False, False, False, True]


def test_context_reads_chorus_starts_drop_bars_and_colour_cells_from_the_fixture() -> None:
    context = _context()
    assert context.section_starts == frozenset({0, 7, 14, 18, 33, 42, 46, 61, 63, 67, 82})
    assert context.chorus_bars == frozenset({18, 46, 67})
    assert context.drop_bars == frozenset({63, 64, 65, 66})
    assert context.color_cells == frozenset(
        {("WASH-ALL", 7), ("WASH-ALL", 14), ("WASH-ALL", 18), ("WASH-ALL", 22), ("BACK", 0)}
    )


def test_fixture_matches_its_production_derivation() -> None:
    beat = json.loads((FIXTURES / "love_attack_beat_grid.json").read_text(encoding="utf-8"))
    feat = json.loads((FIXTURES / "love_attack_bar_features_real.json").read_text(encoding="utf-8"))
    features = [
        BarFeatures(
            bar=row["bar"],
            volume_norm=row["volume_norm"],
            low_band_norm=row["low_band_norm"],
            vocal_band_ratio=row["vocal_band_ratio"],
            onset_count=row["onset_count"],
        )
        for row in feat["bar_features"]
    ]
    bar_map = build_bar_map_payload(
        beat["beat_times_ms"],
        feat["first_beat_offset"],
        bpm=beat["bpm"],
        time_signature=(4, 4),
        events=classify_bar_events(features),
        bar_energy=compute_bar_energy(features),
    )
    stored = _timeline()
    assert stored["bar_map"] == json.loads(json.dumps(bar_map, ensure_ascii=False))
    assert [s["label"] for s in stored["sections"]] == [
        s["label"] for s in build_love_attack_timeline()["sections"]
    ]


# --- 정답지 대조 (계기 교정) -------------------------------------------------------


def test_identical_grid_is_similar_to_itself() -> None:
    base = _base()
    report = compare_grids(base, copy.deepcopy(base), _context())
    assert report.verdict == "비슷함"
    assert report.failing == ()


def test_base_counts_exclude_rests_and_advance_blanks() -> None:
    """정답지의 ① 칸 수는 쉼·꺼짐·예고를 뺀 수다. SIDE-ALL 은 쉼 다섯 칸을 뺀 둘이다."""
    base = _base()
    report = compare_grids(base, copy.deepcopy(base), _context())
    counted = {row.name: row.base_count for row in report.rows}
    assert counted == {
        "FOH": 1,
        "WASH-ALL": 4,
        "BACK": 5,
        "SIDE-ALL": 2,
        "MOVER-U": 7,
        "MOVER-D": 7,
        "BLIND": 1,
        "STROBE": 0,
    }


def test_an_all_one_bar_grid_fails_count_length_and_alignment() -> None:
    base = _base()
    start, end = base["bar_range"]["start"], base["bar_range"]["end"]
    candidate = copy.deepcopy(base)
    for track in candidate["tracks"]:
        track["cues"] = [{"bar": bar, "label": REST_LABEL} for bar in range(start, end + 1)]
    report = compare_grids(base, candidate, _context())
    assert report.verdict == "다름"
    assert {"count", "length", "alignment"} <= set(report.failing)


def _shift_all(grid: dict) -> dict:
    out = copy.deepcopy(grid)
    for track in out["tracks"]:
        for cue in track["cues"]:
            cue["bar"] = int(cue["bar"]) + 1
    return out


def _shift_non_aligned(grid: dict) -> dict:
    starts = _context().section_starts
    out = copy.deepcopy(grid)
    for track in out["tracks"]:
        if track.get("layer_role") == "effect":
            continue
        for cue in track["cues"]:
            if int(cue["bar"]) not in starts:
                cue["bar"] = int(cue["bar"]) + 1
    return out


def _relabel_non_rest(grid: dict) -> dict:
    """비강조 줄의 박 라벨을 모두 바꾼다. 강조 줄(예고 칸 포함)은 건드리지 않는다."""
    out = copy.deepcopy(grid)
    for track in out["tracks"]:
        if track.get("layer_role") == "effect":
            continue
        for cue in track["cues"]:
            if cue.get("label") not in (None, "", REST_LABEL):
                cue["label"] = "확인 라벨"
    return out


def _move_blind_hit(grid: dict) -> dict:
    out = copy.deepcopy(grid)
    for cue in _track(out, "BLIND")["cues"]:
        if int(cue["bar"]) == 18:
            cue["bar"] = 10
    return out


def _color_back_cells(grid: dict) -> dict:
    out = copy.deepcopy(grid)
    for cue in _track(out, "BACK")["cues"]:
        cue["color_preset_no"] = "1"
    return out


def _add_counted_cues_to_back(grid: dict) -> dict:
    """BACK 줄에 세는 칸을 다섯 개 더한다. 기본 5칸의 50%(2.5칸)를 넘는 차이다."""
    out = copy.deepcopy(grid)
    cues = _track(out, "BACK")["cues"]
    for bar in (1, 2, 9, 12, 13):
        cues.append(
            {
                "bar": bar,
                "label": "펄스 1·2·4박",
                "brightness": {"mode": "value", "value_percent": 100},
            }
        )
    return out


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_shift_all, "alignment"),
        (_shift_non_aligned, "length"),
        (_relabel_non_rest, "pattern"),
        (_move_blind_hit, "accent"),
        (_color_back_cells, "color"),
        (_add_counted_cues_to_back, "count"),
    ],
    ids=["alignment", "length", "pattern", "accent", "color", "count"],
)
def test_a_single_perturbation_fails_only_its_own_check(mutate, expected: str) -> None:
    base = _base()
    report = compare_grids(base, mutate(base), _context())
    assert report.failing == (expected,)


# --- 자동 배치 경로(운영과 같은 순서로 오프라인) ---------------------------------------


def test_auto_candidate_has_every_track_and_one_cue_per_bar_of_the_map() -> None:
    timeline = _timeline()
    candidate = build_auto_candidate(timeline, _base())
    assert [t["group_name"] for t in candidate["tracks"]] == [
        t["group_name"] for t in _base()["tracks"]
    ]
    bars = len(timeline["bar_map"]["bars"])
    assert all(len(track["cues"]) == bars for track in candidate["tracks"])


def test_auto_candidate_refuses_a_timeline_without_a_bar_map() -> None:
    with pytest.raises(ShapeCheckError):
        build_auto_candidate({"song_title": LOVE_ATTACK_TITLE, "sections": []}, _base())


# --- 명령줄 ------------------------------------------------------------------------


def test_cli_writes_the_markdown_table_with_all_six_checks(tmp_path: Path) -> None:
    out = tmp_path / "shape.md"
    code = main(["--timeline", str(SHAPE_TIMELINE), "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert code == 0
    assert "## 판정" in text
    assert "다름" in text
    for label in ("① 칸 수", "② 칸 길이", "③ 경계 정렬", "④ 박 패턴", "⑤ 강조 위치", "⑥ 색 지정"):
        assert label in text


def test_cli_fail_on_different_returns_one_for_the_auto_candidate(tmp_path: Path) -> None:
    code = main(
        ["--timeline", str(SHAPE_TIMELINE), "--out", str(tmp_path / "x.md"), "--fail-on-different"]
    )
    assert code == 1


def test_cli_accepts_a_candidate_json_and_passes_when_it_is_the_base(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(_base(), ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "same.md"
    code = main(
        [
            "--timeline",
            str(SHAPE_TIMELINE),
            "--candidate",
            str(candidate_path),
            "--out",
            str(out),
            "--fail-on-different",
        ]
    )
    assert code == 0
    assert "비슷함" in out.read_text(encoding="utf-8")


def test_row_accent_text_reads_near_hits_over_positions_in_that_order() -> None:
    """강조 칸은 「큰 히트 근처 수/위치 수」다. 순서가 바뀌면 2/1 이 나온다."""
    base = _base()
    report = compare_grids(base, _move_blind_hit(base), _context())
    blind = next(row for row in report.rows if row.name == "BLIND")
    assert (blind.base_accent, blind.cand_accent) == ("2/2", "1/2")

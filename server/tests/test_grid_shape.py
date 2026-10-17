"""격자 모양 비교 도구 시험 — 정답지(손 설계 기본 격자)로 계기를 먼저 교정한다.

원칙: 같은 격자는 「비슷함」, 전부 1마디는 「다름」이고, 여섯 지표는 각자가 재는 변화에만
반응한다(한 지표만 흔들면 그 지표만 실패한다). 입력은 저장소 픽스처와 순수 함수뿐이다.
콘솔·실서버 접촉 0.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from server.audio.bar_map import BarFeatures, classify_bar_events, compute_bar_energy
from server.audio.bar_map_store import build_bar_map_payload
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_planned import annotated_cell_colors
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
    miss_annotation,
    off_hit_bars,
    pattern_category,
    render_markdown,
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
    # 줄의 첫 색은 시작 상태라 세지 않는다. 앞에 색이 있는 줄에서 새로 색을 정하는 칸만 센다.
    plain = [
        {"bar": 3, "label": "a", "color_preset_no": "1"},
        {"bar": 7, "label": "a"},
        {"bar": 14, "label": "b"},
    ]
    # 주석 9 는 둘째 칸(7~13) 안에 든다 — 셋째 칸은 주석도 필드도 없다.
    by_annotation = cells_for_track(
        plain, (0, 25), track_name="WASH", color_cells=frozenset({("WASH", 9)})
    )
    assert [cell.colored for cell in by_annotation] == [False, True, False]
    # 주석 20 은 셋째 칸(14~25) 안에 든다.
    by_later_annotation = cells_for_track(
        plain, (0, 25), track_name="WASH", color_cells=frozenset({("WASH", 20)})
    )
    assert [cell.colored for cell in by_later_annotation] == [False, False, True]
    # 칸 필드의 색 번호가 앞 색과 다르면 색을 정한 칸이다.
    by_field = cells_for_track(
        [*plain[:2], {"bar": 14, "label": "b", "color_preset_no": "3"}],
        (0, 25),
        track_name="WASH",
        color_cells=frozenset(),
    )
    assert [cell.colored for cell in by_field] == [False, False, True]


def test_a_color_number_counts_only_where_the_color_changes() -> None:
    # 프리셋 계획은 켜는 칸마다 색 번호를 붙인다. 같은 번호가 이어지거나 쉼 뒤에 같은 번호로 다시
    # 켜지면 색을 새로 정한 것이 아니다. 줄의 첫 번호도 시작 상태라 세지 않는다.
    cues = [
        {"bar": 0, "label": "a", "color_preset_no": "4.1"},
        {"bar": 4, "label": "a", "color_preset_no": "4.1"},
        {"bar": 8, "label": "—"},
        {"bar": 12, "label": "a", "color_preset_no": "4.1"},
        {"bar": 16, "label": "a", "color_preset_no": "4.2"},
    ]
    cells = cells_for_track(cues, (0, 25), track_name="BACK", color_cells=frozenset())
    assert [cell.colored for cell in cells] == [False, False, False, False, True]


def test_a_planned_color_counts_like_the_color_number_it_becomes() -> None:
    # 프리셋 계획은 계획 색을 색 번호로 바꿀 뿐이다. 번호가 붙기 전과 뒤의 ⑥ 이 같아야 한다.
    planned = [
        {"bar": 0, "label": "a", "planned_color": [1, 2, 3]},
        {"bar": 4, "label": "a", "planned_color": [1, 2, 3]},
        {"bar": 8, "label": "a", "planned_color": [9, 9, 9]},
    ]
    numbered = [
        {
            **cue,
            "color_preset_no": {(1, 2, 3): "4.1", (9, 9, 9): "4.2"}[tuple(cue["planned_color"])],
        }
        for cue in planned
    ]
    for cues in (planned, numbered):
        cells = cells_for_track(cues, (0, 25), track_name="MOVER-U", color_cells=frozenset())
        assert [cell.colored for cell in cells] == [False, False, True]


def test_a_mover_rest_before_a_position_change_is_a_pre_move_cell() -> None:
    # 무빙 줄에서 쉼 뒤 켜는 칸의 위치가 쉼 앞 켜는 칸과 다르면 그 쉼은 사전이동(MIB) 칸이다.
    cues = [
        {"bar": 0, "label": "정지", "planned_position": "Home"},
        {"bar": 4, "label": "—"},
        {"bar": 8, "label": "정지", "planned_position": "Center"},
        {"bar": 12, "label": "—"},
        {"bar": 16, "label": "정지", "position_preset_no": "Center"},
    ]
    cells = cells_for_track(
        cues, (0, 25), track_name="MOVER-U", color_cells=frozenset(), mover=True
    )
    assert [cell.pre_move for cell in cells] == [False, True, False, False, False]
    # 무빙이 아닌 줄의 쉼은 사전이동 칸이 아니다.
    other = cells_for_track(cues, (0, 25), track_name="BACK", color_cells=frozenset())
    assert not any(cell.pre_move for cell in other)


def test_pre_move_cells_are_left_out_of_the_beat_pattern_on_both_sides() -> None:
    # 손설계엔 사전이동 쉼 개념이 없다. 그 칸만 다른 두 격자는 ④ 박 패턴 거리가 0 이다.
    def grid(with_pre_move: bool) -> dict:
        cues = [{"bar": 0, "label": "정지", "planned_position": "Home"}]
        if with_pre_move:
            cues.append({"bar": 4, "label": "—"})
        cues.append({"bar": 8, "label": "팬 웨이브", "planned_position": "Center"})
        return {"tracks": [{"group_name": "MOVER-U", "layer_role": "mover", "cues": cues}]}

    context = build_context({"sections": [{"label": "벌스", "bar_start": 0}]}, {})
    report = compare_grids(grid(False), grid(True), context, window=(0, 15))
    pattern = next(check for check in report.checks if check.key == "pattern")
    assert pattern.passed is True
    assert pattern.detail == "거리 0.000"


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
    """BACK 칸마다 색을 번갈아 바꾼다(같은 번호를 늘어놓는 것은 색을 바꾼 것이 아니다)."""
    out = copy.deepcopy(grid)
    for index, cue in enumerate(_track(out, "BACK")["cues"]):
        cue["color_preset_no"] = str(index % 2 + 1)
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


def test_auto_candidate_has_every_track_and_cues_only_where_the_value_changes() -> None:
    # 운영 경로(구간 생성기)와 같은 모양: 값이 바뀌는 마디에만 칸이 있고 첫 마디에는 꼭 있다.
    timeline = _timeline()
    candidate = build_auto_candidate(timeline, _base())
    assert [t["group_name"] for t in candidate["tracks"]] == [
        t["group_name"] for t in _base()["tracks"]
    ]
    bar_numbers = {entry["bar"] for entry in timeline["bar_map"]["bars"]}
    for track in candidate["tracks"]:
        cue_bars = [cue["bar"] for cue in track["cues"]]
        assert cue_bars == sorted(set(cue_bars))
        assert set(cue_bars) <= bar_numbers
        assert cue_bars[0] == min(bar_numbers)
    # 옛 생성기처럼 마디마다 칸을 내면 이 조건이 깨진다: 값이 이어지는 마디는 칸 하나로 묶인다.
    assert any(len(track["cues"]) < len(bar_numbers) for track in candidate["tracks"])


def test_auto_candidate_paints_the_annotated_cells_with_their_planned_color() -> None:
    # 운영 경로(beat_grid_draft_propose)는 곡별 주석 색을 건넨다. 자동 후보도 같은 색을 실어야 한다.
    annotated = annotated_cell_colors(load_preset_annotations(LOVE_ATTACK_TITLE))
    assert annotated, "LOVE ATTACK 계획 주석에 칸 색이 있어야 이 시험이 의미가 있다"
    candidate = build_auto_candidate(_timeline(), _base())
    painted = {
        (track["group_name"], cue["bar"]): tuple(cue["planned_color"])
        for track in candidate["tracks"]
        for cue in track["cues"]
        if "planned_color" in cue and (track["group_name"], cue["bar"]) in annotated
    }
    assert painted, "주석 칸 가운데 계획 색이 실린 칸이 하나도 없다"
    assert {key: color for key, color in painted.items() if color != annotated[key]} == {}


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
    assert "**비슷함**" in text
    for label in ("① 칸 수", "② 칸 길이", "③ 경계 정렬", "④ 박 패턴", "⑤ 강조 위치", "⑥ 색 지정"):
        assert label in text


def test_cli_fail_on_different_returns_zero_for_the_auto_candidate(tmp_path: Path) -> None:
    # 운영 경로 자동 배치(구간 생성기)는 손설계 LOVE ATTACK 과 「비슷함」이다.
    code = main(
        ["--timeline", str(SHAPE_TIMELINE), "--out", str(tmp_path / "x.md"), "--fail-on-different"]
    )
    assert code == 0


def test_cli_fail_on_different_returns_one_for_a_different_candidate(tmp_path: Path) -> None:
    base = _base()
    candidate = copy.deepcopy(base)
    for track in candidate["tracks"]:
        track["cues"] = [{"bar": bar, "label": REST_LABEL} for bar in range(0, 26)]
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
    code = main(
        [
            "--timeline",
            str(SHAPE_TIMELINE),
            "--candidate",
            str(candidate_path),
            "--out",
            str(tmp_path / "x.md"),
            "--fail-on-different",
        ]
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


_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _cells(row: str) -> list[str]:
    """마크다운 표 한 줄의 칸들. 가리지 않은 | 만 칸의 경계로 본다."""
    return _UNESCAPED_PIPE.split(row.strip())[1:-1]


def _table_rows(text: str, header_prefix: str) -> list[str]:
    """머리 줄이 header_prefix 로 시작하는 표의 본문 줄들(머리와 구분선 다음부터)."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(header_prefix))
    rows: list[str] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


def test_table_cells_escape_pipes_so_every_row_keeps_its_columns() -> None:
    """표 칸 안의 | 는 \\| 로 가린다. 가리지 않으면 GFM 에서 열이 밀린다."""
    base = _base()
    text = render_markdown(
        compare_grids(base, copy.deepcopy(base), _context()), inputs={"기본 격자": "LOVE ATTACK"}
    )
    criteria = _table_rows(text, "| 지표 |")
    track = _table_rows(text, "| 줄 |")
    assert len(criteria) == 14
    assert len(track) == 8
    assert {len(_cells(row)) for row in criteria} == {7}
    assert {len(_cells(row)) for row in track} == {8}
    assert "\\|후보 − 기본\\|" in text


def test_off_hit_positions_are_marked_with_their_bar_and_event_kind() -> None:
    """큰 히트 밖의 강조 칸은 마디와 마디 지도 사건을 적는다. 판정 계산은 그대로다."""
    base = _base()
    candidate = copy.deepcopy(base)
    _track(candidate, "BLIND")["cues"].append(
        {"bar": 4, "label": "BLIND 2박", "brightness": {"mode": "value", "value_percent": 100}}
    )
    report = compare_grids(base, candidate, _context())
    blind = next(c for c in report.checks if c.key == "accent" and c.track == "BLIND")
    assert blind.passed is False
    assert blind.detail == "4마디 분석 불일치(킥 진입, 큰 히트 아님)"


def test_an_off_hit_mark_without_an_event_says_only_that_it_is_not_a_big_hit() -> None:
    base = _base()
    report = compare_grids(base, _move_blind_hit(base), _context())
    blind = next(c for c in report.checks if c.key == "accent" and c.track == "BLIND")
    assert blind.detail == "10마디 분석 불일치(큰 히트 아님)"


def test_a_clean_accent_track_has_no_mark() -> None:
    base = _base()
    report = compare_grids(base, copy.deepcopy(base), _context())
    assert all(c.detail == "" for c in report.checks if c.key == "accent")


def test_off_hit_bars_list_only_non_rest_cells_outside_the_hits() -> None:
    cells = [
        Cell("BLIND", 4, 1, "BLIND 2박"),
        Cell("BLIND", 17, 1, "17마디 3·4박 전부 비움(예고)"),
        Cell("BLIND", 18, 1, "18마디 1박 BLIND 100% 2박"),
        Cell("BLIND", 30, 1, REST_LABEL),
    ]
    assert off_hit_bars(cells, frozenset({18}), tolerance=1) == [4]


def test_the_mark_names_the_event_kind_at_its_bar_when_there_is_one() -> None:
    kick = miss_annotation(4, frozenset({(4, "kick_entry")}))
    assert kick == "4마디 분석 불일치(킥 진입, 큰 히트 아님)"
    build = miss_annotation(15, frozenset({(15, "build")}))
    assert build == "15마디 분석 불일치(빌드업, 큰 히트 아님)"
    assert miss_annotation(10, frozenset()) == "10마디 분석 불일치(큰 히트 아님)"


def test_context_keeps_the_event_kind_of_each_bar_from_the_map() -> None:
    context = _context()
    assert (4, "kick_entry") in context.event_bars
    assert (15, "build") in context.event_bars
    assert (65, "drop") in context.event_bars

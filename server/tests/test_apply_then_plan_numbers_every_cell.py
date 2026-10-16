"""자동 배치 적용 → 프리셋 계획 승인 뒤, 칸마다 번호가 빠짐없이 붙는지 — 리드 지시 2026-10-16.

감독 지적 「흰 띠에 색·위치 미정이 왜 이렇게 많냐」. 시드 격자 위에 운영 경로와 같은 초안을 적용하고
(``generate_segment_draft`` → ``apply_arrangement_draft``), 그 격자로 프리셋 계획을 세워 저장 줄을
붙이고 승인한다. 그러면 켜진 칸은 전부 색 번호, 무빙 칸은 전부 위치 번호, 웨이브 칸은 전부 효과
번호를 가져야 한다. 콘솔 접촉 0건 — 풀 판독·그룹 소속·컬러 채널·장비 좌표는 전부 시험 픽스처다.
"""

from __future__ import annotations

from server.design.beat_grid import LOVE_ATTACK_TITLE
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.preset_plan import (
    apply_plan_references,
    build_preset_plan,
    load_preset_annotations,
)
from server.design.preset_plan_store import attach_color_store, attach_floor_position_store

from .test_planned_color_presets import _COLOR_POOL, _applied_grid, _fake_reads
from .test_preset_plan import _POSITION_CHILDREN
from .test_preset_plan_store_all import _FRAMES, _MEMBERS

#: 효과 풀 21 — 1~7 이 찼다고 두는 픽스처. 첫 빈 번호는 8.
_EFFECT_POOL = (21, {slot: f"EFX {slot}" for slot in range(1, 8)})
_POSITION_POOL = (2, _POSITION_CHILDREN)
_NO_COLOR_ROLES = {"key", "effect"}


def _director_numbered(grid: dict) -> tuple[str, int]:
    """곡 주석 색(SKY)이 붙는 BACK 0마디에 감독이 색 번호를 넣고 콘솔 반영까지 승인한 상태로 만든다.
    주석 색 후보는 이 칸과 같은 그룹·같은 색의 계획 색 칸을 함께 담는다."""
    track = next(t for t in grid["tracks"] if t["group_name"] == "BACK")
    cue = next(c for c in track["cues"] if c["bar"] == 0)
    assert _lit(cue)
    cue["color_preset_no"] = "4.1"
    cue["evidence"] = {
        "grade": None,
        "approval": {"by": "supervisor", "date": "2026-10-16", "source": "beat_grid_apply:abc"},
    }
    return "BACK", 0


def _approved_grid(*, director_cell: bool = False) -> tuple[dict, dict]:
    grid = _applied_grid()
    if director_cell:
        _director_numbered(grid)
    plan = build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=_COLOR_POOL,
        position_pool=_POSITION_POOL,
        dimmer_attributes={},
        effect_pool=_EFFECT_POOL,
        bpm=128.0,
        beats_per_bar=4,
    )
    members, channels = _fake_reads(grid)
    # 무빙 그룹만 좌표 픽스처의 장비로 바꾼다(위치 조준은 장비 좌표가 있어야 줄을 만든다).
    movers = {group: _MEMBERS[group] for group in ("MOVER-U", "MOVER-D")}
    members = {**members, **movers}
    rgb = next(iter(channels.values()))
    channels = {**channels, **{fid: list(rgb) for fids in movers.values() for fid in fids}}
    plan = attach_color_store(plan, grid, members=members, channel_names=channels)
    plan = attach_floor_position_store(plan, grid, members=members, frames=_FRAMES)
    approved = apply_plan_references(
        grid,
        plan,
        by="supervisor",
        date="2026-10-16T00:00:00+00:00",
        source="preset_plan:test",
        planned_from=grid,
    )
    return grid, approved


def _cells(grid: dict):
    for track in grid["tracks"]:
        for cue in track["cues"]:
            yield track, cue


def _lit(cue: dict) -> bool:
    value = (cue.get("brightness") or {}).get("value_percent")
    return isinstance(value, int) and value > 0


def test_every_lit_cell_gets_a_color_number() -> None:
    _grid, approved = _approved_grid()
    missing = [
        (track["group_name"], cue["bar"], cue["label"])
        for track, cue in _cells(approved)
        if track.get("layer_role") not in _NO_COLOR_ROLES
        and _lit(cue)
        and cue.get("planned_color") is not None
        and cue.get("color_preset_no") is None
    ]
    assert missing == []


def test_every_lit_colored_line_cell_has_a_planned_color_to_number() -> None:
    # 시드 손 설계 칸(BACK 「킥 1·2·4박」 등)도 초안 칸으로 바뀌어 계획 색을 가진다.
    grid, _approved = _approved_grid()
    uncolored = [
        (track["group_name"], cue["bar"], cue["label"])
        for track, cue in _cells(grid)
        if track.get("layer_role") not in _NO_COLOR_ROLES
        and _lit(cue)
        and cue.get("planned_color") is None
        and cue.get("color_preset_no") is None
    ]
    assert uncolored == []


def test_every_lit_mover_cell_gets_a_position_number() -> None:
    _grid, approved = _approved_grid()
    movers = [(t, c) for t, c in _cells(approved) if t.get("layer_role") == "mover" and _lit(c)]
    assert movers, "픽스처에 켜진 무빙 칸이 있어야 한다"
    missing = [
        (track["group_name"], cue["bar"])
        for track, cue in movers
        if not cue.get("position_preset_no")
    ]
    assert missing == []


def test_every_wave_cell_gets_an_effect_number() -> None:
    # 승인은 움직임을 효과 번호로 바꾸므로 웨이브 칸은 승인 전 격자에서 고른다.
    grid, approved = _approved_grid()
    waves = {
        (track["group_name"], cue["bar"])
        for track, cue in _cells(grid)
        if (cue.get("app_movement") or {}).get("shape") == "wave"
    }
    assert waves, "픽스처에 웨이브 칸이 있어야 한다"
    numbered = {
        (track["group_name"], cue["bar"])
        for track, cue in _cells(approved)
        if cue.get("effect_preset_no")
    }
    assert waves - numbered == set()


def test_a_director_numbered_cell_does_not_hold_the_rest_of_its_color_candidate() -> None:
    # 같은 색 후보의 칸 하나에 감독 번호가 있어도 나머지 칸은 번호를 받는다. 예전엔 후보 전체가
    # 「번호가 이미 있는 칸이라 덮어쓰지 않음」으로 보류돼 계획 색 칸이 번호 없이 남았다.
    _grid, approved = _approved_grid(director_cell=True)
    missing = [
        (track["group_name"], cue["bar"])
        for track, cue in _cells(approved)
        if track.get("layer_role") not in _NO_COLOR_ROLES
        and _lit(cue)
        and cue.get("planned_color") is not None
        and cue.get("color_preset_no") is None
    ]
    assert missing == []
    back = next(t for t in approved["tracks"] if t["group_name"] == "BACK")
    assert next(c for c in back["cues"] if c["bar"] == 0)["color_preset_no"] == "4.1"

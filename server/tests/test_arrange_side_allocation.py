"""자동 배치가 모든 리듬 줄에 켜는 칸을 주는가 — 카드 WT-side-allocation(SPEC-LDRHYTHM-001).

새 곡 실측(fresh2 candidate grid): SIDE-L·SIDE-R 은 83마디 중 14~17·42~45·61~66 마디에서만 켜졌다.
구간마다 켜는 리듬층 둘을 구간 종류로 고정해서, 도입·벌스·후렴에서는 「무빙 + BACK」만 켜졌다.
규칙서 3번(리듬층은 보통 둘)은 지키되, 4번(4마디마다 주인공 교대)처럼 보조층을 창마다 돌린다.
역할을 이름으로 정하지 못한 줄(다른 리그의 「PAR」 등)도 체이스층으로 리듬에 들어간다.
"""

from __future__ import annotations

from server.design.arrange_generator import REST_LABEL
from server.design.arrange_segments import generate_segment_draft, split_sections
from server.tests.test_arrange_segments import SYNTHETIC_EVENTS, _bar_map, _layout, _state

RHYTHM_ROLES = ("back", "side", "mover")


def _split_side_layout() -> list[dict]:
    """새 곡과 같은 짜임 — SIDE-ALL 대신 SIDE-L·SIDE-R 두 줄, 역할 못 정한 PAR 줄 하나."""
    layout = [track for track in _layout() if track["group_name"] != "SIDE-ALL"]
    layout += [
        {"group_no": 5, "group_no_confirmed": True, "group_name": "SIDE-L", "layer_role": "side"},
        {"group_no": 6, "group_no_confirmed": True, "group_name": "SIDE-R", "layer_role": "side"},
        {"group_no": 30, "group_no_confirmed": True, "group_name": "PAR", "layer_role": None},
    ]
    return layout


def _lit_bars(draft: dict, name: str, start: int, end: int) -> list[int]:
    return [bar for bar in range(start, end + 1) if _state(draft, name, bar)["label"] != REST_LABEL]


def test_side_lines_are_lit_inside_choruses_and_the_intro() -> None:
    draft = generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), _split_side_layout())
    # 후렴 18~32 는 창이 셋(18~21, 22~25, 26~32), 도입이 없는 곡(1~40)은 창이 열이다.
    for name in ("SIDE-L", "SIDE-R"):
        assert _lit_bars(draft, name, 18, 32), name
    plain = generate_segment_draft(_bar_map([]), _split_side_layout())
    for name in ("SIDE-L", "SIDE-R", "BACK"):
        lit = _lit_bars(plain, name, 1, 40)
        assert 12 <= len(lit) <= 28, (name, len(lit))


def test_every_rhythm_line_gets_lit_in_every_section_of_two_windows_or_more() -> None:
    bar_map = _bar_map(SYNTHETIC_EVENTS)
    layout = _split_side_layout()
    draft = generate_segment_draft(bar_map, layout)
    windows = draft["windows"]
    for section in split_sections(bar_map):
        inside = [w for w in windows if section.start_bar <= w["start_bar"] <= section.end_bar]
        if len(inside) < 2:
            continue
        for track in layout:
            if track["layer_role"] in RHYTHM_ROLES or track["layer_role"] is None:
                name = track["group_name"]
                assert _lit_bars(draft, name, section.start_bar, section.end_bar), (
                    name,
                    section,
                )


def test_a_line_without_a_role_follows_the_chase_layer_instead_of_staying_dark() -> None:
    draft = generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), _split_side_layout())
    par = _lit_bars(draft, "PAR", 1, 40)
    side = _lit_bars(draft, "SIDE-L", 1, 40)
    assert par and par == side


def test_a_rig_with_only_unknown_role_lines_still_moves_with_the_music() -> None:
    layout = [
        {"group_no": n, "group_no_confirmed": True, "group_name": f"PAR {n}", "layer_role": None}
        for n in (1, 2)
    ]
    draft = generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), layout)
    for track in layout:
        assert _lit_bars(draft, track["group_name"], 1, 40), track["group_name"]

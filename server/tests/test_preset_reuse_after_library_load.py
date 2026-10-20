"""SPEC-LDRHYTHM-001 WT-preset-reuse — 저장한 작업본을 불러와도 콘솔에 있는 같은 프리셋을 다시 쓴다.

실측(2026-10-20, LOVE ATTACK 감독 경로 E2E · 감사 기록 ``audit-20261020.jsonl`` 15393행):
「콘솔에 반영」 카드가 프리셋 21개를 전부 새 번호로 저장했다(재사용 0). DIM-100 은 콘솔
1.925 에 이미 있는데 1.939 에 또 저장됐다. 감사 기록 전체에서 'DIM-100' 이 14개 번호,
'FLOOR MOVER-U' 가 9개 번호를 차지했다.

원인: 재사용 판정은 격자의 저장 기록(``CONSOLE_PRESET_RECORD_KEYS``)을 읽는데, 라이브러리
불러오기(``timeline_api.load_timeline``)가 지금 작업본을 저장된 옛 작업본으로 통째로 바꾸면서
그 기록을 버린다. 앱 저장본·라이브러리 판독(읽기 전용): 새 분석 직전 작업본(「LOVE ATTACK 분석
전 백업 (자동 v14)」 12:40:52)은 기록이 0개였고, 그 칸은 2026-10-15 라이브러리 항목 「LOVE
ATTACK」과 같았다. 그 전 작업본(「Aside 새 연출 v6」)에는 1.925–1.938 기록이 있었다. 새 분석은
기록을 이어받지만(#819) 이어받을 기록이 이미 사라진 뒤였다.

내용 대조: 1.925 는 서브 광원 범위 줄 없이 저장됐고(10-18 05:10, 그룹 꼴 한 줄) 오늘 계획은
범위 줄(``Fixture 201 Thru 212.``)을 붙였다. 이름만 같고 내용이 다르면 재사용하지 않는다 —
디머 기록에 서브 광원 범위를 남기고 대조한다.

콘솔 접촉 0건.
"""

from __future__ import annotations

import copy

from fastapi.testclient import TestClient

from server.design.beat_grid import LOVE_ATTACK_TITLE
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.preset_plan import (
    _reusable_dimmer_slot,
    apply_plan_references,
    build_preset_plan,
    load_preset_annotations,
    save_commands,
    with_dimmer_sub_selections,
)
from server.web.app import create_app
from server.web.session import SongTimelineStore

from .test_new_preset_dialog_t589 import _new_session, _timeline_for_apply
from .test_preset_plan import (
    _ATTRIBUTES,
    _COLOR_CHILDREN,
    _DIMMER_CHILDREN,
    _POSITION_CHILDREN,
    _love_attack_grid,
    _pool_children_payload,
    _pool_list_payload,
    _state_tree,
)
from .test_sub_geometry_selection import _AURA, _cap
from .test_web_beat_grid_send_t563 import _deps as _web_deps

_GROUPS = [("Dimmer", (2, 3))]
_DIM100 = {"percent": 100, "attribute_group_nos": [["Dimmer", [2, 3]]]}


def _load(deps, entry_id: str) -> None:
    with TestClient(create_app(deps)) as client:
        loaded = client.post(f"/api/timelines/{entry_id}/load")
        assert loaded.status_code == 200, loaded.text


def test_loading_a_saved_copy_keeps_the_console_preset_records_of_the_working_copy(
    tmp_path,
) -> None:
    deps = _web_deps(tmp_path)
    store = deps.song_timeline_store
    # 기록이 없는 옛 작업본을 라이브러리에 둔다(실측: 2026-10-15 「LOVE ATTACK」).
    older = copy.deepcopy(store.latest)
    entry = deps.timeline_library.save("LOVE ATTACK", older)
    # 지금 작업본은 콘솔에 저장한 DIM-100 기록을 갖고 있다.
    store.latest = {
        **older,
        "beat_grid": {
            **older["beat_grid"],
            "dimmer_presets": {"1.925": dict(_DIM100)},
            "preset_labels": {"2.99": "FLOOR MOVER-U"},
        },
    }

    _load(deps, entry["id"])

    grid = store.latest["beat_grid"]
    # 콘솔 풀(이름만 읽힌다)에 같은 이름(콘솔이 붙인 「#숫자」)이 그대로 있다 → 재사용.
    console = (1, {925: "DIM-100#5"})
    assert _reusable_dimmer_slot(grid, console, "DIM-100", 100, _GROUPS) == "1.925"
    assert grid["preset_labels"] == {"2.99": "FLOOR MOVER-U"}


def test_loading_keeps_the_saved_copy_records_and_the_working_copy_wins_a_shared_number(
    tmp_path,
) -> None:
    deps = _web_deps(tmp_path)
    store = deps.song_timeline_store
    base = copy.deepcopy(store.latest)
    saved = {
        **base,
        "beat_grid": {
            **base["beat_grid"],
            "dimmer_presets": {
                "1.900": {"percent": 50, "attribute_group_nos": [["Dimmer", [2]]]},
                "1.925": {"percent": 0, "attribute_group_nos": [["Dimmer", [9]]]},
            },
        },
    }
    entry = deps.timeline_library.save("OLD COPY", saved)
    store.latest = {
        **base,
        "beat_grid": {**base["beat_grid"], "dimmer_presets": {"1.925": dict(_DIM100)}},
    }

    _load(deps, entry["id"])

    records = store.latest["beat_grid"]["dimmer_presets"]
    # 불러온 작업본의 기록도 콘솔의 사실이라 남긴다. 같은 번호는 지금 작업본(더 최근)이 이긴다.
    assert records == {
        "1.900": {"percent": 50, "attribute_group_nos": [["Dimmer", [2]]]},
        "1.925": _DIM100,
    }


# -- 내용 대조: 서브 광원 범위가 다르면 이름이 같아도 재사용하지 않는다 --------------------------


def _plan(grid, *, dimmer=(1, _DIMMER_CHILDREN), dimmer_sub_selections=None):
    return build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=dimmer,
        color_pool=(4, _COLOR_CHILDREN),
        position_pool=(2, _POSITION_CHILDREN),
        dimmer_attributes=_ATTRIBUTES,
        dimmer_sub_selections=dimmer_sub_selections,
    )


def _dimmer(plan, percent: int):
    (preset,) = [p for p in plan.presets if p.kind == "dimmer" and p.value_percent == percent]
    return preset


def _stored_with(sub_ranges):
    """첫 계획을 저장하고(승인 뒤 기록), DIM-100 이 쓰는 첫 그룹에 서브 범위가 있으면 싣는다."""
    grid = _love_attack_grid()
    probe = _dimmer(_plan(grid), 100)
    ranges = {probe.group_nos[0]: "Fixture 201 Thru 212."} if sub_ranges else {}
    first = with_dimmer_sub_selections(_plan(grid, dimmer_sub_selections=ranges), ranges)
    dim100 = _dimmer(first, 100)
    assert dim100.ready and not dim100.reused
    applied = apply_plan_references(grid, first, by="supervisor", date="2026-10-20", source="t")
    pool_no, slot = (int(part) for part in dim100.slot.split("."))
    regrid = {**grid, "dimmer_presets": applied["dimmer_presets"]}
    console = (pool_no, {**_DIMMER_CHILDREN, slot: "DIM-100#14"})
    return regrid, console, dim100, probe.group_nos[0]


def test_the_same_sub_range_is_the_same_content_and_is_reused() -> None:
    regrid, console, dim100, group_no = _stored_with(sub_ranges=True)

    second = _plan(
        regrid, dimmer=console, dimmer_sub_selections={group_no: "Fixture 201 Thru 212."}
    )

    again = _dimmer(second, 100)
    assert again.reused is True
    assert again.slot == dim100.slot
    assert not any(f"Preset {dim100.slot}" in line for line in save_commands(second))


def test_a_preset_stored_without_the_sub_range_is_not_reused_when_the_plan_needs_it() -> None:
    # 실측 1.925: 범위 줄 없이 저장 → 오늘 계획은 범위 줄이 필요하다 → 다른 내용, 새로 저장.
    regrid, console, dim100, group_no = _stored_with(sub_ranges=False)

    second = _plan(
        regrid, dimmer=console, dimmer_sub_selections={group_no: "Fixture 201 Thru 212."}
    )

    again = _dimmer(second, 100)
    assert again.reused is False
    assert again.slot != dim100.slot


# -- 세션: 계획 전에 구한 서브 범위 표가 저장 줄과 재사용 대조에 같이 쓰인다 --------------

_BACK_RANGE = "Fixture 111 Thru 112."
#: 픽스처 격자의 BACK 줄 콘솔 그룹 번호(DIM-60 이 이 그룹만 쓴다).
_BACK_NO = 4
_DIM60_SLOT = 40


def _card_with(tmp_path, monkeypatch, *, record) -> list[str]:
    grid = {**_love_attack_grid(), "dimmer_presets": {f"1.{_DIM60_SLOT}": record}}
    store = SongTimelineStore()
    store.latest = _timeline_for_apply(beat_grid=grid)
    state_tree = {
        **_state_tree(),
        "DataPool/PresetPools": _pool_list_payload(
            {"Dimmer": 1, "Position": 2, "Color": 4, "All 1": 21}
        ),
        # 콘솔에는 앱이 전에 저장한 DIM-60 이 「#숫자」 붙은 이름으로 있다.
        "DataPool/PresetPools/1": _pool_children_payload(
            {**_DIMMER_CHILDREN, _DIM60_SLOT: "DIM-60#3"}
        ),
        "DataPool/PresetPools/2": _pool_children_payload(_POSITION_CHILDREN),
        "DataPool/PresetPools/4": _pool_children_payload(_COLOR_CHILDREN),
    }
    session, _console, approval, _audit = _new_session(
        tmp_path, store=store, decisions=(False,), state_tree=state_tree
    )
    monkeypatch.setattr(session, "_beat_grid_preset_dimmer_attributes", lambda names: _ATTRIBUTES)
    monkeypatch.setattr(
        session, "_beat_grid_dimmer_sub_ranges", lambda grid, members: {_BACK_NO: _BACK_RANGE}
    )
    session.beat_grid_preset_plan()
    assert len(approval.requests) == 1
    return list(approval.requests[0].commands)


def test_the_session_reuses_a_console_preset_with_the_same_name_and_sub_range(
    tmp_path, monkeypatch
) -> None:
    record = {
        "percent": 60,
        "attribute_group_nos": [["Dimmer", [_BACK_NO]]],
        "sub_selections": [[_BACK_NO, _BACK_RANGE]],
    }

    card = _card_with(tmp_path, monkeypatch, record=record)

    assert not any("'DIM-60'" in line for line in card)
    assert not any(line.endswith("At 60") for line in card)


def test_the_session_stores_again_when_the_console_preset_lacks_the_sub_range(
    tmp_path, monkeypatch
) -> None:
    record = {"percent": 60, "attribute_group_nos": [["Dimmer", [_BACK_NO]]]}

    card = _card_with(tmp_path, monkeypatch, record=record)

    assert f"{_BACK_RANGE} ; Attribute 'Dimmer' At 60" in card
    assert any(line.startswith("Label Preset 1.") and "'DIM-60'" in line for line in card)
    assert f"Store Preset 1.{_DIM60_SLOT}" not in card  # 다른 내용 — 그 번호에 덮어쓰지 않는다


def test_the_sub_range_table_covers_only_groups_with_dimmer_value_cells(
    tmp_path, monkeypatch
) -> None:
    store = SongTimelineStore()
    store.latest = _timeline_for_apply(beat_grid=_love_attack_grid())
    session, _console, _approval, _audit = _new_session(tmp_path, store=store, decisions=())
    monkeypatch.setattr(
        session, "_rig_fixture_capabilities", lambda: {fid: _cap(fid, _AURA) for fid in (111, 112)}
    )
    members = {"BACK": [111, 112], "FOH": [111, 112]}  # FOH 는 디머 값 칸이 없다

    ranges = session._beat_grid_dimmer_sub_ranges(_love_attack_grid(), members)

    assert ranges == {_BACK_NO: _BACK_RANGE}

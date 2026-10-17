"""콘솔 그룹으로 배치 줄을 정한다 — 소속 장비 기준 (카드 WT-all-fixtures).

감독 지시(2026-10-18): 「조명장비가 있는데 마디 배치에 넣지 않는게 말이 돼?」 — 콘솔에 패치된
장비가 배치에서 조용히 빠지면 안 된다. 묶음 그룹(ALL 류)을 빼는 판단은 **이름이 아니라 소속
장비가 겹치는지**로 한다. 그래서 시험의 그룹 이름은 일부러 리그와 무관한 이름도 섞는다.
"""

from __future__ import annotations

from server.design.console_tracks import (
    REASON_INCOMPLETE,
    REASON_NO_DIMMER,
    REASON_NO_GROUP,
    REASON_SMOKE,
    is_smoke_fixture,
    plan_console_tracks,
)


def _group(no: int, name: str, fids: list[int], *, complete: bool = True) -> dict:
    return {"group_no": no, "group_name": name, "member_fids": fids, "complete": complete}


#: 「이 리그」와 같은 모양 — 개별 그룹 + 그 묶음 + 홀짝 + 전체.
RIG = [
    _group(1, "ALL", [101, 102, 111, 112, 201, 202, 621]),
    _group(2, "KEY", [101, 102]),
    _group(3, "FOH", [111, 112]),
    _group(4, "BACK", [201, 202]),
    _group(16, "HAZE", [621]),
    _group(17, "ODD", [101, 111, 201]),
    _group(18, "EVEN", [102, 112, 202]),
]
ALL_FIDS = [101, 102, 111, 112, 201, 202, 621]


def _names(plan) -> list[str]:
    return [track["group_name"] for track in plan.added]


def test_new_song_gets_one_row_per_disjoint_group_and_every_fixture_is_covered() -> None:
    plan = plan_console_tracks(groups=RIG, fixture_fids=ALL_FIDS, existing_names=[])
    assert _names(plan) == ["KEY", "FOH", "BACK", "HAZE"]
    assert plan.uncovered == ()
    for track in plan.added:
        assert track["group_no_confirmed"] is True
        assert track["cues"] == []


def test_bundle_groups_are_left_out_by_membership_not_by_name() -> None:
    # 묶음 그룹 이름을 아무거나 붙여도 같다 — 소속이 다른 줄과 겹치면 뺀다.
    renamed = [_group(g["group_no"], f"G{g['group_no']}", g["member_fids"]) for g in RIG]
    plan = plan_console_tracks(groups=renamed, fixture_fids=ALL_FIDS, existing_names=[])
    assert _names(plan) == ["G2", "G3", "G4", "G16"]
    excluded = {entry["group_name"] for entry in plan.excluded}
    assert excluded == {"G1", "G17", "G18"}


def test_existing_rows_stay_and_only_missing_fixtures_get_new_rows() -> None:
    # LOVE ATTACK 모양 — FOH·BACK 줄은 있는데 KEY 가 없다.
    plan = plan_console_tracks(groups=RIG, fixture_fids=ALL_FIDS, existing_names=["FOH", "back"])
    assert _names(plan) == ["KEY", "HAZE"]
    assert plan.uncovered == ()


def test_a_smoke_machine_is_left_out_on_purpose_and_listed_as_such() -> None:
    # 감독 2026-10-18 「이건 조명연출이 아니라 헤이즈 즉 연기를 만드는 장비야」 — 일부러 뺀다.
    plan = plan_console_tracks(
        groups=RIG,
        fixture_fids=ALL_FIDS,
        existing_names=["FOH", "BACK"],
        dimmerless_fids={621},
        smoke_fids={621},
    )
    assert _names(plan) == ["KEY"]
    assert plan.uncovered == (
        {"fid": 621, "group_names": ["HAZE"], "reason": REASON_SMOKE, "intentional": True},
    )


def test_a_fixture_without_dimmer_that_is_not_smoke_is_shown_as_a_problem() -> None:
    plan = plan_console_tracks(
        groups=RIG, fixture_fids=ALL_FIDS, existing_names=["FOH", "BACK"], dimmerless_fids={621}
    )
    assert _names(plan) == ["KEY"]
    assert plan.uncovered == (
        {"fid": 621, "group_names": ["HAZE"], "reason": REASON_NO_DIMMER, "intentional": False},
    )


def test_a_fixture_in_no_group_is_reported() -> None:
    plan = plan_console_tracks(groups=RIG, fixture_fids=[*ALL_FIDS, 999], existing_names=[])
    assert plan.uncovered == (
        {"fid": 999, "group_names": [], "reason": REASON_NO_GROUP, "intentional": False},
    )


def test_smoke_is_judged_by_channel_attributes_not_by_names() -> None:
    assert is_smoke_fixture(["Haze1", "Blower1"]) is True
    assert is_smoke_fixture(["Fog", "Fan"]) is True
    assert is_smoke_fixture(["Haze", "Dimmer"]) is False  # 밝기가 있으면 조명이다
    assert is_smoke_fixture(["Shutter1", "Gobo1"]) is False  # 밝기는 없지만 연기도 아니다
    assert is_smoke_fixture([]) is False


def test_a_group_whose_members_were_not_fully_read_is_not_guessed() -> None:
    groups = [*RIG[:1], _group(2, "KEY", [101], complete=False), *RIG[2:]]
    plan = plan_console_tracks(groups=groups, fixture_fids=ALL_FIDS, existing_names=["FOH", "BACK"])
    assert "KEY" not in _names(plan)
    reasons = {entry["fid"]: entry["reason"] for entry in plan.uncovered}
    assert reasons[101] == REASON_INCOMPLETE


def test_when_an_existing_row_was_not_fully_read_nothing_is_added() -> None:
    # 기존 줄이 무엇을 덮는지 모르면, 새 줄이 그 줄과 겹치는지도 모른다 — 짐작하지 않는다.
    groups = [_group(3, "FOH", [111], complete=False), *RIG[1:2], *RIG[3:]]
    plan = plan_console_tracks(groups=groups, fixture_fids=ALL_FIDS, existing_names=["FOH"])
    assert plan.added == ()
    assert any("FOH" in line for line in plan.unread)


def test_role_comes_from_the_existing_role_resolver() -> None:
    plan = plan_console_tracks(groups=RIG, fixture_fids=ALL_FIDS, existing_names=[])
    roles = {track["group_name"]: track["layer_role"] for track in plan.added}
    assert roles["KEY"] == "key"
    assert roles["BACK"] == "back"

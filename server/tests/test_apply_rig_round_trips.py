"""「⇪ 반영」이 리그와 무대를 읽을 때의 콘솔 왕복 수 — LOVE ATTACK 규모의 가짜 콘솔.

반영 버튼 뒤 승인 카드까지 실기에서 약 63초가 걸렸다. 그 안의 리그 판독(`read_design_rig`)이
콘솔에 보내는 질의 수를 센다. 콘솔 왕복 한 번의 값은 기기마다 다르므로 여기서는 질의 수만 본다.
실기 접촉 0 — 가짜 콘솔만 쓴다.
"""

from __future__ import annotations

import json
from collections import Counter

from server.design.beat_grid_stage import read_beat_grid_stage
from server.design.fixture_snapshot import FixtureSnapshotPort
from server.design.rig_capability_read import read_design_rig

from .test_beat_grid_stage_round_trips import TRACKS
from .test_capability_verdict import _FIXTURE_ROOT, _TYPES, _TYPES_ROOT, _FakeConsole

#: 실기 무대 규모(장비 80대), 기종은 두 가지를 번갈아 쓴다.
FIXTURE_COUNT = 80


class _CountingPort:
    """가짜 콘솔을 감싸 질의 종류별로 세기만 한다(답은 그대로 넘긴다)."""

    def __init__(self, inner: _FakeConsole) -> None:
        self._inner = inner
        self.calls: Counter[str] = Counter()

    def _category(self, path: str) -> str:
        if path.startswith(_FIXTURE_ROOT):
            return "fixture"
        if path.startswith(_TYPES_ROOT) and "DMXModes" in path:
            return "type-mode"
        if path.startswith(_TYPES_ROOT):
            return "type-library"
        return "other"

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls[f"state:{self._category(path)}"] += 1
        return self._inner.query_state(path, offset=offset)

    def query_property(self, path: str, name: str) -> dict:
        self.calls[f"prop:{self._category(path)}"] += 1
        return self._inner.query_property(path, name)

    def query_properties(self, path: str, property_names, *, offset: int | None = None) -> dict:
        self.calls[f"props:{self._category(path)}"] += 1
        if offset is None:
            return self._inner.query_properties(path, property_names)
        return self._inner.query_properties(path, property_names, offset=offset)


class _BulkFidFake(_FakeConsole):
    """실기 응답기는 묶음 읽기에서도 FID 를 준다 — 가짜 콘솔의 묶음 답에 FID 를 채운다."""

    def query_properties(self, path: str, property_names) -> dict:
        payload = super().query_properties(path, property_names)
        if path.startswith(_FIXTURE_ROOT):
            for read in payload.get("reads", []):
                if str(read.get("n", "")).upper() == "FID":
                    read["v"] = super().query_property(path, "FID")["value"]
        return payload


GROUPS = "ShowData/DataPools/Default/Groups"


def _sf(slot: int) -> int:
    return 1000 + 2 * (slot - 1)


class _ApplyFake(_BulkFidFake):
    """리그 판독과 무대 소속 판독이 함께 쓰는 가짜 콘솔 — 장비 80대, LOVE ATTACK 그룹 8개."""

    def __init__(self, fixtures: dict, groups: dict[int, tuple[str, list[int]]]) -> None:
        super().__init__(fixtures)
        self._groups = groups

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        if path != GROUPS:
            return super().query_state(path, offset=offset)
        children = [
            {"i": no, "name": name, "class": "Group"} for no, (name, _) in self._groups.items()
        ]
        return {
            "ok": True,
            "path": path,
            "offset": offset,
            "node": {"childCount": len(children)},
            "children": children[offset:],
            "truncated": False,
        }

    def query_properties(self, path: str, property_names, *, offset: int | None = None) -> dict:
        if path.startswith(GROUPS + "/"):
            no = int(path.rsplit("/", 1)[1])
            _, members = self._groups[no]
            entries = [{"sf_index": sf} for sf in members]
            start = offset or 0
            read = {
                "n": "SELECTIONDATA",
                "ok": True,
                "t": "table",
                "v": json.dumps(entries[start:]),
                "offset": start,
                "total": len(entries),
                "truncated": False,
            }
            return {"ok": True, "path": path, "reads": [read], "truncated": False}
        payload = super().query_properties(path, property_names)
        slot = int(path.rsplit("/", 1)[1])
        positions = {"POSX": f"{slot % 9}.0", "POSY": f"{slot % 5}.0", "POSZ": "2.0"}
        for read in payload.get("reads", []):
            key = str(read.get("n", "")).upper()
            if key == "SUBFIXTUREINDEX":
                read["v"] = str(_sf(slot))
            elif key in positions:
                read["v"] = positions[key]
        return payload


def _apply_rig() -> tuple[_CountingPort, dict]:
    type_slots = list(_TYPES)
    fixtures = {
        slot: (type_slots[(slot - 1) % len(type_slots)], 100 + slot)
        for slot in range(1, FIXTURE_COUNT + 1)
    }
    groups: dict[int, tuple[str, list[int]]] = {}
    cursor = 0
    for name, number, members in TRACKS:
        groups[number] = (name, [_sf(((cursor + k) % FIXTURE_COUNT) + 1) for k in range(members)])
        cursor += members
    return _CountingPort(_ApplyFake(fixtures, groups)), groups


def _rig() -> _CountingPort:
    type_slots = list(_TYPES)
    fixtures = {
        slot: (type_slots[(slot - 1) % len(type_slots)], 100 + slot)
        for slot in range(1, FIXTURE_COUNT + 1)
    }
    return _CountingPort(_BulkFidFake(fixtures))


def test_rig_read_round_trips_at_show_scale() -> None:
    port = _rig()
    read = read_design_rig(port, fixture_types_root=_TYPES_ROOT)
    total = sum(port.calls.values())
    print(f"\n[rig round trips, plain] {dict(port.calls)} total={total} gap={read.gap!r}")
    assert total > 0


def test_rig_read_through_the_snapshot_gives_the_same_rig_with_fewer_fixture_trips() -> None:
    plain = _rig()
    expected = read_design_rig(plain, fixture_types_root=_TYPES_ROOT)

    shared = _rig()
    snapshot = FixtureSnapshotPort(shared, fixture_root=_FIXTURE_ROOT)
    shared_read = read_design_rig(snapshot, fixture_types_root=_TYPES_ROOT)
    total = sum(shared.calls.values())
    print(f"\n[rig round trips, snapshot] {dict(shared.calls)} total={total}")

    assert shared_read == expected
    # 장비마다 질의 한 번(묶음)만 — FID 와 속성 읽기가 같은 답을 함께 쓴다.
    fixture_trips = shared.calls["props:fixture"] + shared.calls["prop:fixture"]
    assert fixture_trips == FIXTURE_COUNT
    assert total < sum(plain.calls.values())


def test_apply_rig_then_stage_round_trips_shrink_with_the_shared_snapshot() -> None:
    names = [name for name, _, _ in TRACKS]

    plain, _ = _apply_rig()
    rig_plain = read_design_rig(plain, fixture_types_root=_TYPES_ROOT)
    stage_plain = read_beat_grid_stage(
        plain, fixtures_path=_FIXTURE_ROOT, groups_path=GROUPS, track_names=names
    )
    total_plain = sum(plain.calls.values())

    shared, _ = _apply_rig()
    snapshot = FixtureSnapshotPort(shared, fixture_root=_FIXTURE_ROOT)
    rig_shared = read_design_rig(snapshot, fixture_types_root=_TYPES_ROOT)
    stage_shared = read_beat_grid_stage(
        snapshot, fixtures_path=_FIXTURE_ROOT, groups_path=GROUPS, track_names=names
    )
    total_shared = sum(shared.calls.values())
    print(
        f"\n[apply round trips] plain={total_plain} shared={total_shared} "
        f"shared-detail={dict(shared.calls)}"
    )

    assert rig_shared == rig_plain
    assert stage_shared == stage_plain
    assert stage_plain["groups"], "the stage read must find the LOVE ATTACK groups"
    assert all(group["complete"] for group in stage_plain["groups"])
    assert total_shared < total_plain

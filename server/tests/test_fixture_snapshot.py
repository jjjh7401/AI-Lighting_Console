"""반영 안의 장비 판독 재사용 포트 — 답의 모양·재사용·되돌림 시험 (카드 apply-latency).

실기 접촉 0. 입력 포트는 질의 수를 세는 가짜다.
"""

from __future__ import annotations

from collections import Counter

import pytest

from server.design.fixture_snapshot import FixtureSnapshotPort

ROOT = "Patch/Stages/1/Fixtures"


class _Inner:
    """장비 속성을 값 ``<이름>-<슬롯>`` 으로 답하는 가짜. 질의 종류를 센다."""

    def __init__(self, *, fail_union: bool = False) -> None:
        self.calls: Counter[str] = Counter()
        self.fail_union = fail_union

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls["state"] += 1
        return {"ok": True, "path": path, "node": {"childCount": 1}, "children": []}

    def query_property(self, path: str, property_name: str) -> dict:
        self.calls["prop"] += 1
        slot = path.rsplit("/", 1)[1]
        return {"ok": True, "value": f"{property_name}-{slot}"}

    def query_properties(self, path: str, property_names, *, offset: int | None = None) -> dict:
        self.calls["props"] += 1
        if self.fail_union:
            raise RuntimeError("union read failed")
        names = tuple(property_names)
        slot = path.rsplit("/", 1)[1]
        reads = [{"n": name, "ok": True, "v": f"{name}-{slot}"} for name in names]
        return {"ok": True, "path": path, "reads": reads, "truncated": False}


def test_one_union_read_serves_later_single_and_bulk_reads_of_the_same_fixture() -> None:
    inner = _Inner()
    snap = FixtureSnapshotPort(inner, fixture_root=ROOT)
    assert snap.query_property(f"{ROOT}/3", "FID") == {"ok": True, "value": "FID-3"}
    assert snap.query_properties(f"{ROOT}/3", ("Patch", "Mode")) == {
        "ok": True,
        "path": f"{ROOT}/3",
        "reads": [
            {"n": "Patch", "ok": True, "v": "Patch-3"},
            {"n": "Mode", "ok": True, "v": "Mode-3"},
        ],
        "truncated": False,
    }
    assert inner.calls["props"] == 1
    assert inner.calls["prop"] == 0


def test_names_are_matched_case_insensitively_and_relabelled_to_the_asked_name() -> None:
    inner = _Inner()
    snap = FixtureSnapshotPort(inner, fixture_root=ROOT)
    reply = snap.query_properties(f"{ROOT}/2", ("fid", "posx"))
    assert [read["n"] for read in reply["reads"]] == ["fid", "posx"]
    assert snap.query_property(f"{ROOT}/2", "posz") == {"ok": True, "value": "posz-2"}
    assert inner.calls["props"] == 1


def test_names_outside_the_union_and_other_paths_pass_straight_through() -> None:
    inner = _Inner()
    snap = FixtureSnapshotPort(inner, fixture_root=ROOT, names=("FID",))
    snap.query_property(f"{ROOT}/1", "FID")  # 한 번 받아 둔다
    snap.query_property(f"{ROOT}/1", "Zoom")  # 묶음 밖 이름
    snap.query_state(ROOT)  # 장비 목록은 늘 원래 포트
    snap.query_property("ShowData/DataPools/Default/Groups/3", "SELECTIONDATA")
    assert inner.calls["prop"] == 2
    assert inner.calls["state"] == 1


def test_a_failed_union_read_is_not_retried_and_the_caller_gets_the_plain_answer() -> None:
    inner = _Inner(fail_union=True)
    snap = FixtureSnapshotPort(inner, fixture_root=ROOT)
    first = snap.query_property(f"{ROOT}/5", "FID")
    second = snap.query_property(f"{ROOT}/5", "Mode")
    assert first == {"ok": True, "value": "FID-5"}
    assert second == {"ok": True, "value": "Mode-5"}
    assert inner.calls["props"] == 1  # 묶음은 한 번만 시도한다
    assert inner.calls["prop"] == 2


@pytest.mark.parametrize("path", [f"{ROOT}/x", f"{ROOT}/", "Other/Fixtures/1"])
def test_non_slot_paths_are_never_treated_as_fixtures(path: str) -> None:
    inner = _Inner()
    snap = FixtureSnapshotPort(inner, fixture_root=ROOT)
    snap.query_property(path, "FID")
    assert inner.calls["props"] == 0
    assert inner.calls["prop"] == 1

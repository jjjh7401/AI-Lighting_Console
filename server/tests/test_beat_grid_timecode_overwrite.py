"""SPEC-LDRHYTHM-001 — 앱이 만든 타임코드(`LDBEAT Timecode N`) 덮어쓰기 규칙.

소유권 레코드 없이 같은 번호를 다시 반영할 때: 이름이 앱 접두이고 트랙이 가리키는
시퀀스가 전부 앱 소유(`LDBEAT `)면 허용(승인 카드에 덮어쓰기 위험 줄), 아니면 거절.
콘솔 접촉 0건 — FakeConsole 만 쓴다.
"""

from __future__ import annotations

from server.design.beat_grid_send import timecode_overwrite_note
from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    TIMECODE_NUMBER,
    _empty_pool_state_tree,
    _new_session,
    _timeline,
)

OVERWRITE_LINE = f"기존 LDBEAT Timecode {TIMECODE_NUMBER} 을 덮어씁니다"


def _tree(timecode_name: str, sequences: list[tuple[int, str]]) -> dict:
    tree = _empty_pool_state_tree()
    tree["DataPool/Sequences"] = {"children": [{"i": i, "name": n} for i, n in sequences]}
    tree["DataPool/Timecodes"] = {
        "children": [{"i": TIMECODE_NUMBER, "name": timecode_name}],
        "node": {"childCount": 1},
    }
    tree[f"DataPool/Timecodes/{TIMECODE_NUMBER}/1"] = {
        "children": [{"i": 1, "class": "Marker"}, {"i": 2, "class": "Track"}],
        "node": {"childCount": 2},
    }
    return tree


def _apply(tmp_path, tree: dict, targets: dict[str, object]):
    store = SongTimelineStore()
    store.latest = _timeline()
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)

    def query_properties(path, property_names, **_kw):
        if path not in targets:
            raise RuntimeError(f"no props at {path}")
        return {"reads": [{"n": "TARGET", "ok": True, "v": targets[path]}]}

    console.query_properties = query_properties
    return session, console, approval


TARGET_PATH = f"DataPool/Timecodes/{TIMECODE_NUMBER}/1/2"


def test_pure_verdict_cases() -> None:
    names = {5: "LDBEAT BACK", 6: "Foreign"}
    note, why = timecode_overwrite_note(20, "LDBEAT Timecode 20", [5], names)
    assert note == "기존 LDBEAT Timecode 20 을 덮어씁니다" and why is None
    note, why = timecode_overwrite_note(20, "LDBEAT Timecode 20", ["Sequence 5"], names)
    assert note is not None
    note, why = timecode_overwrite_note(20, "LDBEAT Timecode 20", [5, 6], names)
    assert note is None and why
    assert timecode_overwrite_note(20, "LDBEAT Timecode 20", [], names)[0] is None
    assert timecode_overwrite_note(20, "Foreign", [5], names) == (None, None)


def test_app_owned_timecode_is_overwritten_with_warning(tmp_path) -> None:
    tree = _tree(f"LDBEAT Timecode {TIMECODE_NUMBER}", [(5, "LDBEAT BACK")])
    session, console, approval = _apply(tmp_path, tree, {TARGET_PATH: 5})
    event = session.beat_grid_apply()
    assert event["ok"] is True, event
    assert len(approval.requests) == 1
    assert any(OVERWRITE_LINE in r for i in approval.requests[0].items for r in i.risk_reasons)
    assert console.executed  # 승인 뒤 실제로 나갔다(FakeConsole)


def test_foreign_named_timecode_is_refused(tmp_path) -> None:
    tree = _tree("Foreign", [(5, "LDBEAT BACK")])
    session, console, approval = _apply(tmp_path, tree, {TARGET_PATH: 5})
    event = session.beat_grid_apply()
    assert event["ok"] is False
    assert "이미 'Foreign'" in event["reason"]
    assert console.executed == [] and approval.requests == []


def test_app_named_timecode_pointing_at_foreign_sequence_is_refused(tmp_path) -> None:
    tree = _tree(f"LDBEAT Timecode {TIMECODE_NUMBER}", [(5, "Someone Else")])
    session, console, approval = _apply(tmp_path, tree, {TARGET_PATH: 5})
    event = session.beat_grid_apply()
    assert event["ok"] is False
    assert console.executed == [] and approval.requests == []


def test_unreadable_targets_fail_closed(tmp_path) -> None:
    tree = _tree(f"LDBEAT Timecode {TIMECODE_NUMBER}", [(5, "LDBEAT BACK")])
    session, console, _approval = _apply(tmp_path, tree, {})
    assert session.beat_grid_apply()["ok"] is False
    assert console.executed == []


def test_empty_timecode_behaves_as_before(tmp_path) -> None:
    session, console, approval = _apply(tmp_path, _empty_pool_state_tree(), {})
    event = session.beat_grid_apply()
    assert event["ok"] is True, event
    assert not any(OVERWRITE_LINE in r for i in approval.requests[0].items for r in i.risk_reasons)

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


# --- TARGET 해석 폭 (SPEC-LDRHYTHM-001) -----------------------------------------

_NAMES = {16: "LDBEAT BACK", 17: "LDBEAT LEAD", 6: "Foreign"}


def test_parse_track_target_accepts_every_form() -> None:
    from server.design.beat_grid_send import parse_track_target

    cases = [
        (16, 16),
        ("Sequence 16", 16),
        ("16", 16),
        ("LDBEAT BACK", 16),
        ("DataPool/Sequences/16", 16),
        ("ShowData/DataPools/Default/Sequences/16", 16),
        ("13.1.6.16", 16),
        ({"no": 16}, 16),
        ("Sequence 16 'LDBEAT BACK'", 16),
    ]
    for value, number in cases:
        assert parse_track_target(value, _NAMES)[0] == number, value
    assert parse_track_target(None, _NAMES) == (None, None)
    assert parse_track_target("Foreign", _NAMES) == (6, "Foreign")


def test_note_accepts_all_target_forms_and_rejects_foreign() -> None:
    for value in (16, "Sequence 16", "DataPool/Sequences/16", "13.1.6.16", "LDBEAT BACK"):
        note, why = timecode_overwrite_note(4, "LDBEAT Timecode 4", [value], _NAMES)
        assert note is not None and why is None, value
    note, _ = timecode_overwrite_note(4, "LDBEAT Timecode 4", ["Sequences/6"], _NAMES)
    assert note is None


def test_unreadable_target_falls_back_to_track_name() -> None:
    ok = {"target": None, "track_name": "LDBEAT BACK"}
    assert timecode_overwrite_note(4, "LDBEAT Timecode 4", [ok], _NAMES)[0] is not None
    bad = {"target": None, "track_name": "Someone"}
    assert timecode_overwrite_note(4, "LDBEAT Timecode 4", [bad], _NAMES)[0] is None
    none = {"target": None, "track_name": None}
    assert timecode_overwrite_note(4, "LDBEAT Timecode 4", [none], _NAMES)[0] is None


def test_persisted_allocation_is_trusted_without_reading_target(tmp_path) -> None:
    tree = _tree(f"LDBEAT Timecode {TIMECODE_NUMBER}", [(5, "Someone Else")])
    session, console, approval = _apply(tmp_path, tree, {})
    store = session._timeline_store
    store.set_beat_grid_allocation(
        ("other", "song"),
        {"timecode_number": TIMECODE_NUMBER, "timecode_name": f"LDBEAT Timecode {TIMECODE_NUMBER}"},
    )
    event = session.beat_grid_apply()
    assert event["ok"] is True, event
    assert any(OVERWRITE_LINE in r for i in approval.requests[0].items for r in i.risk_reasons)


def test_path_form_target_through_session(tmp_path) -> None:
    tree = _tree(f"LDBEAT Timecode {TIMECODE_NUMBER}", [(5, "LDBEAT BACK")])
    session, _console, _approval = _apply(
        tmp_path, tree, {TARGET_PATH: "ShowData/DataPools/Default/Sequences/5"}
    )
    assert session.beat_grid_apply()["ok"] is True


def test_real_console_shape_with_empty_default_track(tmp_path) -> None:
    """실측(onPC 2.4.2): Marker + 앱 트랙 + 콘솔이 만든 빈 'Track 9'(TARGET 읽기 불가)."""
    base = f"DataPool/Timecodes/{TIMECODE_NUMBER}/1"
    tree = _tree(f"LDBEAT Timecode {TIMECODE_NUMBER}", [(5, "LDBEAT BACK"), (6, "LDBEAT FOH")])
    tree[base] = {
        "children": [
            {"class": "MarkerTrack", "i": 1, "name": "Marker"},
            {"class": "Track", "i": 2, "name": "<LDBEAT FOH#3>"},
            {"class": "Track", "i": 3, "name": "<LDBEAT BACK#3>"},
            {"class": "Track", "i": 4, "name": "Track 9"},
        ],
        "node": {"childCount": 4},
    }
    session, _console, _approval = _apply(tmp_path, tree, {})
    shapes = {
        f"{base}/1": [
            {"e": "property not readable: TARGET", "n": "TARGET", "ok": False},
            {"n": "NAME", "ok": True, "t": "string", "v": "Marker"},
        ],
        f"{base}/2": [
            {"n": "TARGET", "ok": True, "t": "userdata", "v": "Sequence 6"},
            {"n": "NAME", "ok": True, "t": "string", "v": "<LDBEAT FOH#3>"},
        ],
        f"{base}/3": [
            {"n": "TARGET", "ok": True, "t": "userdata", "v": "Sequence 5"},
            {"n": "NAME", "ok": True, "t": "string", "v": "<LDBEAT BACK#3>"},
        ],
        f"{base}/4": [
            {"e": "property not readable: TARGET", "n": "TARGET", "ok": False},
            {"n": "NAME", "ok": True, "t": "string", "v": "Track 9"},
        ],
    }
    session._rig_capability_port.query_properties = lambda path, names, **_k: {
        "reads": shapes[path]
    }
    targets = session._beat_grid_timecode_track_targets(TIMECODE_NUMBER)
    assert [t["target"] for t in targets] == ["Sequence 6", "Sequence 5"]
    assert session.beat_grid_apply()["ok"] is True


def test_unreadable_target_on_named_foreign_track_still_refused(tmp_path) -> None:
    base = f"DataPool/Timecodes/{TIMECODE_NUMBER}/1"
    tree = _tree(f"LDBEAT Timecode {TIMECODE_NUMBER}", [(5, "LDBEAT BACK")])
    tree[base] = {
        "children": [{"class": "Track", "i": 2, "name": "Someone's Track"}],
        "node": {"childCount": 1},
    }
    session, _console, _approval = _apply(tmp_path, tree, {})
    session._rig_capability_port.query_properties = lambda path, names, **_k: {
        "reads": [
            {"e": "property not readable: TARGET", "n": "TARGET", "ok": False},
            {"n": "NAME", "ok": True, "t": "string", "v": "Someone's Track"},
        ]
    }
    assert session.beat_grid_apply()["ok"] is False

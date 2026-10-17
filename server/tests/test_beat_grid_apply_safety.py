"""SPEC-LDRHYTHM-001 — 「콘솔에 반영」 안전 결함 넷(D14~D17), 가짜 콘솔만 쓴다.

D14 시퀀스 번호가 쌓임 · D15 승인 목록에 없는 SaveShow · D16 쓰기 잠김인데 반영 ·
D17 승인 카드 첫 줄에 대상 타임코드가 없음. 콘솔 접촉 0건(``FakeConsole``).
"""

from __future__ import annotations

from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    TIMECODE_NUMBER,
    _empty_pool_state_tree,
    _new_session,
    _timeline,
)

_BASE = f"DataPool/Timecodes/{TIMECODE_NUMBER}/1"
_TC_NAME = f"LDBEAT Timecode {TIMECODE_NUMBER}"


def _old_app_tree(sequences: list[tuple[int, str]]) -> dict:
    """앱이 만든 옛 타임코드 하나 + 그 트랙들이 각자 시퀀스를 가리키는 콘솔 상태."""
    tree = _empty_pool_state_tree()
    tree["DataPool/Sequences"] = {"children": [{"i": i, "name": n} for i, n in sequences]}
    tree["DataPool/Timecodes"] = {
        "children": [{"i": TIMECODE_NUMBER, "name": _TC_NAME}],
        "node": {"childCount": 1},
    }
    tree[_BASE] = {
        "children": [{"i": 1, "class": "Marker"}]
        + [{"i": 2 + k, "class": "Track"} for k in range(len(sequences))],
        "node": {"childCount": 1 + len(sequences)},
    }
    return tree


def _session(tmp_path, tree: dict, targets: dict[int, int]):
    store = SongTimelineStore()
    store.latest = _timeline()
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)

    def query_properties(path, property_names, **_kw):
        slot = int(path.rsplit("/", 1)[1])
        if path.startswith(_BASE) and slot in targets:
            return {"reads": [{"n": "TARGET", "ok": True, "v": targets[slot]}]}
        raise RuntimeError(f"no props at {path}")

    console.query_properties = query_properties
    return session, console, approval


def _reasons(approval) -> list[str]:
    return [r for item in approval.requests[0].items for r in item.risk_reasons]


# --- D14 ----------------------------------------------------------------------


def test_d14_reapply_over_app_timecode_reuses_its_sequence_and_allocates_none(tmp_path) -> None:
    tree = _old_app_tree([(5, "LDBEAT BACK")])
    session, console, approval = _session(tmp_path, tree, {2: 5})

    event = session.beat_grid_apply()

    assert event["ok"] is True, event
    # 새 시퀀스를 만드는 줄(Store Sequence <n> 만)이 없고, 큐는 옛 시퀀스 5 로 간다.
    assert not any(c.startswith("Store Sequence 1 ") for c in console.executed), console.executed
    # 재실행 4 — 옛 시퀀스 5 는 통째로 지우고 같은 번호로 다시 만든다(새 번호 0개).
    assert any(c.startswith("Store Sequence 5 Cue ") for c in console.executed), console.executed
    assert any(f"Assign Sequence 5 At Timecode {TIMECODE_NUMBER}.1." in c for c in console.executed)
    assert [c for c in console.executed if c.startswith("Delete Sequence")] == [
        "Delete Sequence 5 /NoConfirm"
    ]
    assert any("재사용(새 번호 0개)" in r for r in _reasons(approval))


def test_d14_unmatched_old_app_sequence_is_deleted_inside_the_same_card(tmp_path) -> None:
    tree = _old_app_tree([(5, "LDBEAT BACK"), (6, "LDBEAT OLDGROUP")])
    session, console, approval = _session(tmp_path, tree, {2: 5, 3: 6})

    event = session.beat_grid_apply()

    assert event["ok"] is True, event
    assert len(approval.requests) == 1
    # 재실행 4 — 재사용하는 5 는 큐보다 먼저 지우고 다시 만들고, 짝 없는 6 은 타임코드를 지운 뒤에
    # 지운다.
    order = [c for c in console.executed if c.startswith("Delete ")]
    assert order == [
        "Delete Sequence 5 /NoConfirm",
        f"Delete Timecode {TIMECODE_NUMBER} /NoConfirm",
        "Delete Sequence 6 /NoConfirm",
    ]
    assert any(
        "옛 앱 시퀀스 1개를 지웁니다" in r and "6 'LDBEAT OLDGROUP'" in r
        for r in _reasons(approval)
    )


def test_d14_foreign_sequences_are_never_deleted_or_reused(tmp_path) -> None:
    tree = _old_app_tree([(5, "LDBEAT BACK")])
    tree["DataPool/Sequences"]["children"].append({"i": 9, "name": "Someone Else"})
    session, console, _approval = _session(tmp_path, tree, {2: 5})

    assert session.beat_grid_apply()["ok"] is True
    assert not any("Sequence 9" in c for c in console.executed)


# --- D15 ----------------------------------------------------------------------


def test_d15_gate_backup_is_declared_in_the_card_and_the_approved_list(tmp_path) -> None:
    session, console, approval = _session(tmp_path, _empty_pool_state_tree(), {})
    session._gate.use_showfile_backup()

    event = session.beat_grid_apply()

    assert event["ok"] is True, event
    assert console.executed[0] == "SaveShow"
    verdict = event["approval_vs_sent"]
    assert verdict["sent_not_approved"] == [] and verdict["approved_not_sent"] == []
    assert verdict["match"] is True
    assert any("SaveShow" in r for r in _reasons(approval))


def test_d15_without_backup_manager_no_saveshow_is_sent_or_declared(tmp_path) -> None:
    session, console, approval = _session(tmp_path, _empty_pool_state_tree(), {})

    event = session.beat_grid_apply()

    assert event["ok"] is True, event
    assert "SaveShow" not in console.executed
    assert not any("SaveShow" in r for r in _reasons(approval))
    assert event["approval_vs_sent"]["match"] is True


# --- D16 ----------------------------------------------------------------------

_ROWS = "①②③④⑤⑥⑦⑧⑨"


def _progress(tmp_path, statuses: dict[int, str]):
    path = tmp_path / "progress.md"
    lines = ["| 항목 | 판정 | 무엇을 봤나 |", "|---|---|---|"]
    lines += [f"| {_ROWS[i - 1]} x | {statuses.get(i, '통과')} | y |" for i in range(1, 10)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _two_cue_timeline() -> dict:
    """1마디는 ①만 필요한 위치 칸(통과), 2마디는 ⑨ 의존 움직임 칸(⑨ 미통과 -> 보류)."""
    timeline = _timeline()
    evidence = {"approval": {"by": "supervisor", "date": "2026-10-16", "source": "t"}}
    timeline["beat_grid"]["tracks"][0]["cues"] = [
        {"bar": 1, "position_preset_no": "1.1", "evidence": evidence},
        {
            "bar": 2,
            "position_preset_no": "1.1",
            "app_movement": {"shape": "circle", "axes": ["pan"]},
            "evidence": evidence,
        },
    ]
    return timeline


def test_d16_apply_proceeds_and_only_probe_dependent_cells_are_held(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "server.web.session.default_progress_md_path",
        lambda: _progress(tmp_path, {9: "미확인", 5: "움직임 없음"}),
    )
    store = SongTimelineStore()
    store.latest = _two_cue_timeline()
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_empty_pool_state_tree()
    )

    event = session.beat_grid_apply()

    assert event["ok"] is True, event
    assert console.executed  # 전체 거절이 아니다
    blocked = event["blocked_cells"]
    assert len(blocked) == 1 and blocked[0]["bar"] == 2 and blocked[0]["group_name"] == "BACK"
    assert any("M1 프로브 미통과로 보류된 칸 1개" in r for r in _reasons(approval))


def test_d16_no_held_line_when_every_probe_passed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "server.web.session.default_progress_md_path", lambda: _progress(tmp_path, {})
    )
    session, _console, approval = _session(tmp_path, _empty_pool_state_tree(), {})

    assert session.beat_grid_apply()["ok"] is True
    assert not any("보류된 칸" in r for r in _reasons(approval))


def test_d16_grid_view_counts_held_cells_for_the_badge() -> None:
    from server.design.beat_grid_emit import m1_held_cells

    grid = _two_cue_timeline()["beat_grid"]
    grid["probe_results"] = {i: "통과" for i in range(1, 10)} | {9: "미확인"}
    assert m1_held_cells(grid) == [("BACK", 2)]
    grid["probe_results"] = {i: "통과" for i in range(1, 10)}
    assert m1_held_cells(grid) == []


# --- D17 ----------------------------------------------------------------------


def test_d17_card_leads_with_target_timecode_sequences_and_cue_count(tmp_path) -> None:
    session, _console, approval = _session(tmp_path, _empty_pool_state_tree(), {})

    assert session.beat_grid_apply()["ok"] is True

    first = _reasons(approval)[0]
    assert first.startswith(f"대상: Timecode {TIMECODE_NUMBER} '{_TC_NAME}' · 시퀀스 1 · 큐 1개"), (
        first
    )

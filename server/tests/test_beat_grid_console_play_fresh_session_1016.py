"""SPEC-LDRHYTHM-001 — 새 접속·제목 어긋남에서도 「콘솔 같이」 ▶ 가 적용된 타임코드를 재생한다.

콘솔 접촉 0건 — FakeConsole 만 쓴다.
"""

from __future__ import annotations

from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import TIMECODE_NUMBER, _new_session, _timeline
from .test_beat_grid_timecode_overwrite import TARGET_PATH, _tree


def _session(tmp_path, *, name, seq_name="LDBEAT BACK", record=None, timeline=None):
    store = SongTimelineStore()
    store.latest = timeline or _timeline()
    if record is not None:
        store.set_beat_grid_allocation(*record)
    tree = _tree(name, [(5, seq_name)])
    session, console, approval, _a = _new_session(tmp_path, store=store, state_tree=tree)

    def query_properties(path, property_names, **_kw):
        if path != TARGET_PATH:
            raise RuntimeError(path)
        return {"reads": [{"n": "TARGET", "ok": True, "v": 5}]}

    console.query_properties = query_properties
    return session, console


def _tc_lines(console):
    return [c for c in console.executed if "Timecode" in c]


def test_fresh_session_plays_app_owned_field_timecode(tmp_path) -> None:
    session, console = _session(tmp_path, name=f"LDBEAT Timecode {TIMECODE_NUMBER}")
    status = session.beat_grid_console_play()
    assert status["ok"] is True, status
    assert _tc_lines(console) == [
        f"Top Timecode {TIMECODE_NUMBER}",
        f"Go Timecode {TIMECODE_NUMBER}",
    ]


def test_foreign_timecode_is_refused(tmp_path) -> None:
    session, console = _session(tmp_path, name="Foreign")
    assert session.beat_grid_console_play()["ok"] is False
    assert _tc_lines(console) == []


def test_app_named_timecode_with_foreign_sequence_is_refused(tmp_path) -> None:
    session, console = _session(
        tmp_path, name=f"LDBEAT Timecode {TIMECODE_NUMBER}", seq_name="Someone Else"
    )
    assert session.beat_grid_console_play()["ok"] is False
    assert _tc_lines(console) == []


def test_record_under_grid_title_is_found_after_title_changed(tmp_path) -> None:
    timeline = _timeline(song_title="LOVE ATTACK 손설계 1016")
    timeline["beat_grid"]["song_title"] = "LOVE ATTACK"
    name = f"LDBEAT Timecode {TIMECODE_NUMBER}"
    timeline["timecode_number"] = None
    session, console = _session(
        tmp_path,
        name=name,
        timeline=timeline,
        record=(
            ("LOVE ATTACK", timeline["sequence_number"]),
            {
                "timecode_number": TIMECODE_NUMBER,
                "timecode_name": name,
                # WT-play-stale-owner — 타임코드가 가리키는 5번은 이 곡이 쓴 것이다.
                "tracks": {
                    "BACK": {"sequence_number": 5, "sequence_name": "LDBEAT BACK", "cues": {}}
                },
            },
        ),
    )
    assert session.beat_grid_console_play()["ok"] is True
    assert _tc_lines(console)[0] == f"Top Timecode {TIMECODE_NUMBER}"


def test_no_record_and_no_field_is_refused(tmp_path) -> None:
    timeline = _timeline()
    timeline["timecode_number"] = None
    session, console = _session(
        tmp_path, name=f"LDBEAT Timecode {TIMECODE_NUMBER}", timeline=timeline
    )
    assert session.beat_grid_console_play()["ok"] is False
    assert _tc_lines(console) == []

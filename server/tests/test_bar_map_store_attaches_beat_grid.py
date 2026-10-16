"""마디 지도 분석 뒤 송신 프레임에 격자가 실린다 — 「분석 뒤 박자 배치 빈 화면」.

마디 지도는 초안의 ``bar_map`` 키에만 저장된다(SPEC-LDBARMAP-002 AC-LDBARENTRY-004 (5)).
그런데 격자가 없는 초안을 보내면 화면은 「박자 격자 데이터가 아직 없습니다」를 보인다.
그래서 송신 프레임에만 곡 기본 격자를 붙인다. 저장소의 원본은 그대로 둔다.
"""

from __future__ import annotations

from server.design.beat_grid import default_beat_grid
from server.web.session import SongTimelineStore

from .test_session_bar_map_store import _new_session, _valid_payload


def _pushed_grids(sent: list[dict]) -> list[dict]:
    return [
        event["timeline"]["beat_grid"]
        for event in sent
        if event.get("type") == "song_timeline" and event["timeline"].get("beat_grid") is not None
    ]


#: 계획 표시(화면 전용) — 콘솔에 아직 없는 계획 색·계획 이름. 구조 비교에서는 뺀다.
_PLANNED_DISPLAY_KEYS = ("color_planned", "planned_dimmer_name", "planned_position_name")


def _without_planned_marks(tracks: list[dict]) -> list[dict]:
    stripped = []
    for track in tracks:
        cues = []
        for cue in track["cues"]:
            body = {key: value for key, value in cue.items() if key not in _PLANNED_DISPLAY_KEYS}
            if cue.get("color_planned"):
                body.pop("color_rgb", None)
            cues.append(body)
        stripped.append({**track, "cues": cues})
    return stripped


def test_analysed_draft_without_a_grid_pushes_the_default_note(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = {"song_title": "Maroon 5 — Sugar", "sequence_number": 0}
    sent: list[dict] = []
    session, _console = _new_session(tmp_path, store=store, sent=sent)

    session.store_timeline_bar_map(_valid_payload())

    [grid] = _pushed_grids(sent)[-1:]
    assert grid["tracks"] == []
    assert "기본값 없음" in grid["note"]
    # 저장소 원본은 그대로다(bar_map 말고는 바뀌지 않는다).
    assert "beat_grid" not in store.latest


def test_analysed_love_attack_draft_pushes_its_registered_tracks(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = {"song_title": "LOVE ATTACK", "sequence_number": None}
    sent: list[dict] = []
    session, _console = _new_session(tmp_path, store=store, sent=sent)

    session.store_timeline_bar_map(_valid_payload())

    [grid] = _pushed_grids(sent)[-1:]
    # 계획 표시(화면 전용 색·이름)를 뺀 구조는 곡 기본 격자와 같다 — 트랙 구조는 그대로 송신된다.
    assert _without_planned_marks(grid["tracks"]) == default_beat_grid("LOVE ATTACK")["tracks"]
    assert grid["tracks"], "LOVE ATTACK 기본 격자에 트랙이 있어야 한다"
    # 계획 표시는 화면 송신 프레임에 붙는다. 저장소 원본에는 붙지 않는다.
    wash = next(track for track in grid["tracks"] if track["group_name"] == "WASH-ALL")
    assert next(cue for cue in wash["cues"] if cue["bar"] == 18)["color_planned"] is True
    assert "beat_grid" not in store.latest


def test_analysis_keeps_an_existing_grid_in_the_pushed_frame(tmp_path) -> None:
    existing = {"tracks": [], "note": "감독이 적은 격자", "marker": "keep-me"}
    store = SongTimelineStore()
    store.latest = {
        "song_title": "LOVE ATTACK",
        "sequence_number": None,
        "beat_grid": existing,
    }
    sent: list[dict] = []
    session, _console = _new_session(tmp_path, store=store, sent=sent)

    session.store_timeline_bar_map(_valid_payload())

    assert store.latest["beat_grid"] == existing
    [grid] = _pushed_grids(sent)[-1:]
    assert grid["marker"] == "keep-me"
    assert grid["note"] == "감독이 적은 격자"

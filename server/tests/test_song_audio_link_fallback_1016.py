"""리드 1016 — 불러오기로 제목이 바뀐 타임라인도 격자의 원래 제목 열쇠로 음원 링크를 찾는다."""

from __future__ import annotations

from server.web.session import ChatSession


class _Store:
    latest = {
        "song_title": "LOVE ATTACK 손설계 1016",
        "sequence_number": None,
        "beat_grid": {"song_title": "LOVE ATTACK"},
    }


def test_fallback_key_uses_grid_song_title() -> None:
    session = ChatSession.__new__(ChatSession)
    session._timeline_store = _Store()
    assert session._song_audio_fallback_key(("LOVE ATTACK 손설계 1016", None)) == (
        "LOVE ATTACK",
        None,
    )


def test_fallback_key_none_when_same_title() -> None:
    session = ChatSession.__new__(ChatSession)
    session._timeline_store = _Store()
    session._timeline_store.latest = {
        "song_title": "LOVE ATTACK",
        "beat_grid": {"song_title": "LOVE ATTACK"},
    }
    assert session._song_audio_fallback_key(("LOVE ATTACK", None)) is None

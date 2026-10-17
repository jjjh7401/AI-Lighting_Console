"""SPEC-LDRHYTHM-001 재실행 2 N2 — 화면 머리말(BPM·마디 수·박자표)을 마디 지도에서 채운다.

#793 이전에 만든 새 분석 작업본은 ``bpm`` 키 없이 ``bar_map`` 만 실었고, 같은 음원이면 작업본을
다시 만들지 않아 상단 바·런북 헤더가 「BPM —」로 남았다(실서버 재실행 2 백업 파일에서 확인).
"""

from __future__ import annotations

from server.web.messages import song_timeline_event


def _bar_map() -> dict:
    return {
        "bpm": 112.00191993244025,
        "time_signature": [4, 4],
        "bars": [{"bar": n, "start_ms": n * 2143} for n in range(1, 84)],
    }


def test_missing_header_keys_are_filled_from_the_bar_map() -> None:
    timeline = {"song_title": "LOVE ATTACK", "sections": [], "bar_map": _bar_map()}
    sent = song_timeline_event(timeline=timeline)["timeline"]
    assert sent["bpm"] == 112.00191993244025
    assert sent["bar_count"] == 83
    assert sent["time_signature"] == "4/4"
    # 재생 환산이 읽는 값은 채우지 않는다 — 표시만 고친다.
    assert "seconds_per_bar" not in sent
    # 저장본은 건드리지 않는다.
    assert "bpm" not in timeline


def test_existing_header_keys_win() -> None:
    timeline = {"bpm": 120.0, "bar_count": 10, "time_signature": "3/4", "bar_map": _bar_map()}
    sent = song_timeline_event(timeline=timeline)["timeline"]
    assert (sent["bpm"], sent["bar_count"], sent["time_signature"]) == (120.0, 10, "3/4")


def test_nothing_is_invented_without_a_bar_map_value() -> None:
    sent = song_timeline_event(timeline={"bar_map": {"bpm": None, "bars": []}})["timeline"]
    assert "bpm" not in sent and "bar_count" not in sent and "time_signature" not in sent
    assert song_timeline_event(timeline={"song_title": "x"})["timeline"] == {"song_title": "x"}

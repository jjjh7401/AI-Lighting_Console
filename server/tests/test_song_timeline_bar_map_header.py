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
    assert "bar_origin_seconds" not in sent
    assert song_timeline_event(timeline={"song_title": "x"})["timeline"] == {"song_title": "x"}


# 3차 전체 실행 G-19 — 화면은 「마디 = 초 ÷ 한 마디 길이」로 0초를 0마디 시작에 두었다. LOVE ATTACK
# 마디 지도의 1마디 첫 박은 1.498초라 화면 마디 경계가 콘솔 큐(마디 지도 시각)보다 0.645초 늦었다.
# 화면이 콘솔과 같은 기준을 쓰도록 「0마디가 시작하는 곡 시각」을 함께 보낸다 — 콘솔 큐 시각과
# 같은 식(1마디 첫 박 + (마디 − 1) × 한 마디 길이, ``SongTiming.bar_start_seconds``)이다.
def _love_attack_bars() -> list[dict]:
    return [
        {"bar": 0, "start_ms": 964, "beats_ms": [964]},
        {"bar": 1, "start_ms": 1498, "beats_ms": [1498, 2043, 2577, 3111]},
        {"bar": 2, "start_ms": 3657, "beats_ms": [3657, 4203, 4725, 5259]},
    ]


def test_the_bar_origin_follows_the_bar_map_first_downbeat() -> None:
    spb = 240 / 112.00191993244025
    timeline = {
        "seconds_per_bar": spb,
        "bar_map": {**_bar_map(), "bars": _love_attack_bars()},
    }
    sent = song_timeline_event(timeline=timeline)["timeline"]
    assert abs(sent["bar_origin_seconds"] - (1.498 - spb)) < 1e-9
    # 1마디 경계가 마디 지도의 1마디 첫 박과 같다.
    assert abs(sent["bar_origin_seconds"] + 1 * spb - 1.498) < 1e-9
    assert "bar_origin_seconds" not in timeline


def test_no_origin_without_the_playback_bar_length_or_a_first_bar() -> None:
    bar_map = {**_bar_map(), "bars": _love_attack_bars()}
    sent = song_timeline_event(timeline={"bar_map": bar_map})["timeline"]
    assert "bar_origin_seconds" not in sent
    no_bar1 = {**bar_map, "bars": [_love_attack_bars()[0]]}
    sent = song_timeline_event(timeline={"seconds_per_bar": 2.0, "bar_map": no_bar1})["timeline"]
    assert "bar_origin_seconds" not in sent

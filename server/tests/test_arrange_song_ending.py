"""곡 끝은 음악을 따른다 — 자동 배치(구간 생성기)의 마지막 구간 시험(카드 WT-song-ending).

감독 요청(2026-10-21): 곡의 꼬리는 조명 연출로 자연스럽게 끝나야 한다. 곡마다 끝이 다르다 —
항상 페이드로 끝내는 규칙이 아니라, 음악이 실제로 어떻게 끝나는지(잦아드는지, 큰 한 방으로
끊기는지, 끝까지 큰지)를 따른다.

실측 결함(LOVE ATTACK, PR #859 로 마디 지도가 오디오 끝 92마디까지 늘어난 뒤): 84마디부터 에너지
~0, 89~92마디 0(무음). 분류기가 무음을 82·86·90 마디 「브레이크」로 읽었고, 자동 배치는 킥이
없는 83·87·91 마디에 BACK 「킥 1·2·4박」을, 86·90 마디에 무빙 팬 웨이브를, 무음 속 90 마디에
FOH 「켬」 칸을 냈다. 92 마디에서야 한꺼번에 꺼졌다.

규칙은 곡·리그·그룹·번호 상수가 아니라 마디 지도가 이미 가진 특징(마디 에너지·리듬 블록의 큰
히트·사건)에서 나온다. 시험은 색이 아니라 동작을 본다:

1. 잦아드는 끝(꼬리 무음 포함) — 조용한 꼬리에서 리듬 층이 쉬고, 새로 켜지는 줄이 없고, 정지
   조명은 잦아드는 동안 남았다가 음악이 끝나는 마디(무음 시작)에서 모두 꺼진다.
2. 큰 한 방으로 끝나고 무음 — 그 마디에 강조(임팩트) 칸이 서고, 다음 마디부터 모두 꺼진다.
3. 끝까지 큰 곡 — 끝 규칙이 아무것도 바꾸지 않는다(리듬 층이 마지막까지 돈다).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.audio.bar_map_store import attach_rhythm, build_bar_map_payload
from server.design.arrange_policy import ArrangementPolicy
from server.design.arrange_segments import generate_segment_draft, split_sections
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BEAT_MS = 500

#: 리듬을 타는 칸의 규칙 종류(방향 값 ``effect_kind``). 음악에 박이 없으면 이 칸이 서면 안 된다.
RHYTHMIC_KINDS = frozenset({"pulse", "chase", "motion", "blind", "strobe"})


def _ev(kind: str, start: int, end: int | None = None) -> dict:
    return {"kind": kind, "start_bar": start, "end_bar": start if end is None else end}


#: 합성 곡의 몸통 — 도입(1~8) → 벌스(9 킥) → 빌드(14~17) → 후렴(18 킥부터 끝까지).
BODY_EVENTS = [_ev("kick_entry", 9), _ev("build", 14, 17), _ev("kick_entry", 18)]


def _energy(last_bar: int, tail: dict[int, float]) -> dict[int, float]:
    """마디 에너지(곡 안 상대값 0~1). 도입 0.3·벌스 0.5·빌드 0.6~0.75·후렴 0.9, 끝은 ``tail``."""
    energy: dict[int, float] = {}
    for bar in range(1, last_bar + 1):
        if bar <= 8:
            energy[bar] = 0.3
        elif bar <= 13:
            energy[bar] = 0.5
        elif bar <= 17:
            energy[bar] = 0.6 + 0.05 * (bar - 14)
        else:
            energy[bar] = 0.9
    energy.update(tail)
    return energy


def _bar_map(
    bars: int,
    *,
    tail: dict[int, float],
    events: list[dict],
    last_bar_beats: int = 4,
    with_energy: bool = True,
) -> dict:
    """4/4·박 500 ms 합성 마디 지도. 마지막 마디는 ``last_bar_beats`` 박(꼬리 마디)일 수 있다."""
    beats = [index * BEAT_MS for index in range((bars - 1) * 4 + last_bar_beats)]
    return build_bar_map_payload(
        beats,
        0,
        bpm=120.0,
        events=events,
        bar_energy=_energy(bars, tail) if with_energy else None,
    )


def _with_big_hit(bar_map: dict, bar: int) -> dict:
    """리듬 블록을 붙인다. 큰 히트는 ``bar`` 마디 첫 박 하나다."""
    beats = [
        {
            "bar": entry["bar"],
            "beat": index,
            "t_ms": time_ms,
            "kick": 0.5,
            "snare": 0.5,
            "onset": 0.5,
            "kick_hit": False,
            "snare_hit": False,
        }
        for entry in bar_map["bars"]
        for index, time_ms in enumerate(entry["beats_ms"], start=1)
    ]
    hit_ms = next(item["t_ms"] for item in beats if item["bar"] == bar and item["beat"] == 1)
    first, last = bar_map["bars"][0], bar_map["bars"][-1]
    rhythm = {
        "beats": beats,
        "hits": [{"bar": bar, "beat": 1, "t_ms": hit_ms, "strength": 0.95, "kind": "big"}],
        "sections": [
            {
                "start_bar": first["bar"],
                "end_bar": last["bar"],
                "bars": last["bar"] - first["bar"] + 1,
                "start_ms": first["start_ms"],
                "end_ms": last["beats_ms"][-1] + BEAT_MS,
                "d_level": 4,
            }
        ],
    }
    return attach_rhythm(bar_map, rhythm)


def _layout() -> list[dict]:
    return list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])


def _state(draft: dict, name: str, bar: int) -> dict:
    """그 마디에 적용되는 칸(희소 초안: 마디 이하에서 가장 가까운 칸)의 방향 값."""
    track = next(item for item in draft["tracks"] if item["group_name"] == name)
    return [cue for cue in track["cues"] if cue["bar"] <= bar][-1]["direction"]


def _lit(draft: dict, name: str, bar: int) -> bool:
    return _state(draft, name, bar)["brightness_percent"] > 0


def _names(draft: dict) -> list[str]:
    return [track["group_name"] for track in draft["tracks"]]


def _assert_nothing_new_from(draft: dict, first_bar: int) -> None:
    """``first_bar`` 부터 곡 끝까지 꺼져 있던 줄이 새로 켜지는 마디가 없다."""
    end = draft["bar_range"]["end"]
    for name in _names(draft):
        for bar in range(first_bar, end + 1):
            if _lit(draft, name, bar):
                assert _lit(draft, name, bar - 1), f"{name} 이 꼬리 {bar}마디에서 새로 켜진다"


def _assert_no_rhythm_from(draft: dict, first_bar: int) -> None:
    end = draft["bar_range"]["end"]
    for name in _names(draft):
        for bar in range(first_bar, end + 1):
            state = _state(draft, name, bar)
            if state["brightness_percent"] > 0:
                assert state["effect_kind"] not in RHYTHMIC_KINDS, (
                    f"{name} 이 박이 없는 {bar}마디에서 {state['effect_kind']} 로 돈다"
                )


def _assert_all_dark_from(draft: dict, first_bar: int) -> None:
    end = draft["bar_range"]["end"]
    for name in _names(draft):
        for bar in range(first_bar, end + 1):
            assert not _lit(draft, name, bar), f"{name} 이 음악이 끝난 {bar}마디에 켜져 있다"


def _assert_no_lit_cell_from(draft: dict, first_bar: int) -> None:
    """``first_bar`` 부터는 켜는 칸(다시 찍는 칸 포함)이 하나도 서지 않는다."""
    for track in draft["tracks"]:
        for cue in track["cues"]:
            if cue["bar"] >= first_bar:
                assert cue["direction"]["brightness_percent"] == 0, (
                    f"{track['group_name']} {cue['bar']}마디에 켜는 칸 「{cue['label']}」"
                )


# -- 1. 잦아드는 끝 + 꼬리 무음 -----------------------------------------------------------

#: 후렴(0.9)이 24 마디까지, 25~26 잦아듦(음악), 27~29 조용한 꼬리(울림), 30~32 무음.
#: 분류기는 저역이 빠진 꼬리를 4마디마다 브레이크로 읽는다(27·31 — LOVE ATTACK 86·90 과 같은 모양).
DECAY_TAIL = {25: 0.5, 26: 0.25, 27: 0.08, 28: 0.05, 29: 0.03, 30: 0.0, 31: 0.0, 32: 0.0}
DECAY_EVENTS = [*BODY_EVENTS, _ev("break", 27), _ev("break", 31)]
DECAY_QUIET_START = 27
DECAY_SILENCE_START = 30


def _decay_map(**kwargs: object) -> dict:
    return _bar_map(32, tail=DECAY_TAIL, events=DECAY_EVENTS, last_bar_beats=2, **kwargs)


def test_a_decaying_ending_stops_every_rhythmic_layer_in_the_quiet_tail() -> None:
    draft = generate_segment_draft(_decay_map(), _layout())
    _assert_no_rhythm_from(draft, DECAY_QUIET_START)


def test_a_decaying_ending_turns_nothing_on_in_the_quiet_tail() -> None:
    draft = generate_segment_draft(_decay_map(), _layout())
    _assert_nothing_new_from(draft, DECAY_QUIET_START)
    # 꼬리 첫 마디에서 움직임이 멈추는 칸(웨이브 → 정지)뿐, 그 뒤로는 켜는 칸을 다시 찍지 않는다.
    _assert_no_lit_cell_from(draft, DECAY_QUIET_START + 1)


def test_a_decaying_ending_resolves_out_where_the_music_ends() -> None:
    draft = generate_segment_draft(_decay_map(), _layout())
    _assert_all_dark_from(draft, DECAY_SILENCE_START)


def test_static_light_settles_with_the_decay_instead_of_cutting_at_its_start() -> None:
    """잦아드는 동안(조용한 꼬리, 무음 전)에는 정지 조명이 남는다 — 리듬만 빠지고 바로 꺼지지
    않는다."""
    draft = generate_segment_draft(_decay_map(), _layout())
    for name in ("FOH", "WASH-ALL"):
        assert _lit(draft, name, DECAY_QUIET_START - 1)
        assert _lit(draft, name, DECAY_SILENCE_START - 1), f"{name} 이 잦아드는 중에 꺼졌다"


def test_breaks_inside_the_quiet_tail_are_not_section_boundaries() -> None:
    """꼬리의 브레이크(27·31)로 꼬리를 쪼개지 않는다. 조용한 꼬리는 곡 끝까지 아웃트로 한 구간이다
    (화면 구간 이름도 「아웃트로」로 읽힌다)."""
    sections = split_sections(_decay_map())
    assert 31 not in [section.start_bar for section in sections]
    last = sections[-1]
    assert (last.start_bar, last.end_bar, last.kind) == (DECAY_QUIET_START, 32, "outro")


def test_the_ending_rule_is_a_per_song_default_that_can_be_turned_off() -> None:
    """곡별 정책으로 끄면 예전처럼 꼬리에서도 구간 규칙대로 돈다(규칙은 기본값이지 강제가
    아니다)."""
    draft = generate_segment_draft(
        _decay_map(), _layout(), ArrangementPolicy(ending_follows_music=False)
    )
    end = draft["bar_range"]["end"]
    assert any(
        _state(draft, name, bar)["effect_kind"] in RHYTHMIC_KINDS and _lit(draft, name, bar)
        for name in _names(draft)
        for bar in range(DECAY_QUIET_START, end)
    )


# -- 2. 큰 한 방으로 끝나고 무음 ----------------------------------------------------------

#: 후렴(0.9)이 28 마디의 마지막 한 방까지, 29~32 무음. 분류기는 29 마디를 브레이크로 읽는다.
HIT_TAIL = {29: 0.0, 30: 0.0, 31: 0.0, 32: 0.0}
HIT_EVENTS = [*BODY_EVENTS, _ev("break", 29)]
FINAL_HIT_BAR = 28


@pytest.mark.parametrize("with_rhythm", [True, False], ids=["big-hit-in-rhythm", "abrupt-cut"])
def test_a_final_hit_lands_an_impact_look_then_everything_goes_out(with_rhythm: bool) -> None:
    bar_map = _bar_map(32, tail=HIT_TAIL, events=HIT_EVENTS)
    if with_rhythm:
        bar_map = _with_big_hit(bar_map, FINAL_HIT_BAR)
    draft = generate_segment_draft(bar_map, _layout())
    impact = _state(draft, "BLIND", FINAL_HIT_BAR)
    assert impact["brightness_percent"] > 0
    assert impact["effect_kind"] == "blind"
    _assert_all_dark_from(draft, FINAL_HIT_BAR + 1)
    _assert_no_lit_cell_from(draft, FINAL_HIT_BAR + 1)


# -- 3. 끝까지 큰 곡 ----------------------------------------------------------------------


def test_a_song_loud_to_the_very_end_keeps_its_rhythm_to_the_last_bar() -> None:
    bar_map = _bar_map(32, tail={}, events=BODY_EVENTS, last_bar_beats=2)
    draft = generate_segment_draft(bar_map, _layout())
    # 끝 규칙은 에너지가 조용한 꼬리를 만들 때만 손댄다 — 에너지를 빼고 만든 초안과 같다.
    assert draft == generate_segment_draft(
        _bar_map(32, tail={}, events=BODY_EVENTS, last_bar_beats=2, with_energy=False), _layout()
    )
    assert any(
        _lit(draft, name, 31) and _state(draft, name, 31)["effect_kind"] in RHYTHMIC_KINDS
        for name in _names(draft)
    )
    # 마지막(꼬리) 마디에서 끝 칸으로 정리된다(4차 전체 실행 D-11 규칙 그대로).
    _assert_all_dark_from(draft, 32)


# -- LOVE ATTACK 실측 꼬리(오디오 끝 92 마디까지) ----------------------------------------


def _love_attack_bar_map() -> dict:
    with (FIXTURES_DIR / "love_attack_bar_map_audio_end.json").open(encoding="utf-8") as handle:
        return json.load(handle)["bar_map"]


def test_love_attack_tail_follows_the_music_out() -> None:
    """84 마디부터 에너지 ~0(울림), 88 마디부터 사실상 무음. 리듬 층은 84 마디부터 쉬고, 무음
    속에서 켜지는 줄이 없고, 무음이 시작하면 모두 꺼진다. 무음을 브레이크로 읽은 86·90 마디는
    구간 경계가 아니다."""
    bar_map = _love_attack_bar_map()
    draft = generate_segment_draft(bar_map, _layout())
    _assert_no_rhythm_from(draft, 84)
    _assert_nothing_new_from(draft, 84)
    _assert_no_lit_cell_from(draft, 85)
    _assert_all_dark_from(draft, 88)
    starts = [section.start_bar for section in split_sections(bar_map)]
    assert 86 not in starts and 90 not in starts
    assert split_sections(bar_map)[-1].kind == "outro"

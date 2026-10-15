"""배치 초안 생성기 시험 — SPEC-LDARRANGE-001 AC-002·003·004·005·006·007·011·012·013·014·015·016.

합성 마디 지도(4/4, 박 500밀리초, 40마디)와 LOVE ATTACK 기본 격자의 트랙 구성으로 규칙을
잡는다. 리듬층 세기(AC-005·006)는 리듬을 타는 트랙 수로 센다. 강조(BLIND·STROBE)와 정지·유지
칸은 세지 않는다.
"""

from __future__ import annotations

import inspect
import re

import pytest

from server.audio.bar_map_store import build_bar_map_payload
from server.design import arrange_generator, arrange_policy
from server.design.arrange_generator import generate_arrangement_draft
from server.design.arrange_policy import ArrangementPolicy
from server.design.beat_grid import (
    LOVE_ATTACK_TITLE,
    default_beat_grid,
    find_overlapping_group_tracks,
)
from server.design.rig import RIG_LAYER_ROLES

BARS = 40
#: 킥 진입은 9마디, 드롭은 17~18마디에서 시작한다.
EVENTS = [
    {"kind": "kick_entry", "start_bar": 9, "end_bar": 9, "start_beat": 1, "grade": "measured"},
    {"kind": "drop", "start_bar": 17, "end_bar": 18, "start_beat": 1, "grade": "measured"},
]
#: 교정 전 SPEC 역할 라벨. 트랙 이름으로 쓰면 안 된다(AC-LDARRANGE-014).
SPEC_ROLE_LABELS = {
    "SCENE",
    "BACK PULSE",
    "SIDE CHASE",
    "MOVER-U MOVE",
    "MOVER-D MOVE",
    "ACCENT",
}
RHYTHMIC_ROLES = {"back", "side", "mover"}
RHYTHMIC_LABELS = {
    arrange_generator.PULSE_LABEL,
    arrange_generator.CHASE_LABEL,
    arrange_generator.MOTION_LABEL,
}


def _bar_map(events: list[dict] | None = None) -> dict:
    beats = [index * 500 for index in range(BARS * 4)]
    return build_bar_map_payload(beats, 0, bpm=120.0, events=EVENTS if events is None else events)


def _layout() -> list[dict]:
    return list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])


def _draft(policy: ArrangementPolicy | None = None, events: list[dict] | None = None) -> dict:
    return generate_arrangement_draft(_bar_map(events), _layout(), policy)


def _labels(draft: dict, name: str) -> dict[int, str]:
    track = next(item for item in draft["tracks"] if item["group_name"] == name)
    return {cue["bar"]: cue["label"] for cue in track["cues"]}


def _rhythmic_count(draft: dict, bar: int) -> int:
    count = 0
    for track in draft["tracks"]:
        if track["layer_role"] not in RHYTHMIC_ROLES:
            continue
        label = next(cue["label"] for cue in track["cues"] if cue["bar"] == bar)
        if label in RHYTHMIC_LABELS:
            count += 1
    return count


def _window_bars(window: dict) -> range:
    return range(window["start_bar"], window["end_bar"] + 1)


def test_ac002_every_cell_is_a_value_or_an_explicit_rest() -> None:
    draft = _draft()
    all_bars = set(range(1, BARS + 1))
    for track in draft["tracks"]:
        assert {cue["bar"] for cue in track["cues"]} == all_bars
        for cue in track["cues"]:
            assert cue["label"], "빈 라벨은 정의되지 않은 칸이다"
    assert _labels(draft, "BACK")[1] == arrange_generator.PULSE_LABEL


def test_ac003_accents_appear_only_on_impact_bars() -> None:
    draft = _draft()
    strobe_hits = {bar for bar, label in _labels(draft, "STROBE").items() if label != "—"}
    blind_hits = {bar for bar, label in _labels(draft, "BLIND").items() if label != "—"}
    assert strobe_hits == {17}, "스트로브는 드롭 시작 마디에만 있다"
    assert blind_hits == {9}, "블라인드는 킥 진입 마디에만 있다"


def test_ac004_slow_song_gets_no_strobe() -> None:
    draft = _draft(ArrangementPolicy(slow_song=True))
    assert set(_labels(draft, "STROBE").values()) == {arrange_generator.REST_LABEL}
    assert _labels(draft, "BLIND")[9] == arrange_generator.BLIND_LABEL


def test_ac005_non_drop_windows_keep_at_most_two_rhythmic_tracks() -> None:
    draft = _draft()
    checked = 0
    for window in draft["windows"]:
        if window["drop"]:
            continue
        for bar in _window_bars(window):
            assert _rhythmic_count(draft, bar) <= 2
            checked += 1
    assert checked > 0


def test_ac006_drop_windows_allow_three_rhythmic_tracks_and_no_more() -> None:
    draft = _draft()
    drop_windows = [window for window in draft["windows"] if window["drop"]]
    assert drop_windows, "드롭 구간이 있어야 시험이 의미가 있다"
    counts = []
    for window in drop_windows:
        for bar in _window_bars(window):
            count = _rhythmic_count(draft, bar)
            assert count <= 3
            counts.append(count)
    assert max(counts) == 3, "드롭 구간에서는 셋까지 실제로 움직인다"


def test_ac007_lead_role_never_holds_more_than_eight_bars() -> None:
    draft = _draft()
    longest = 0
    run = 0
    previous = None
    for window in draft["windows"]:
        length = window["end_bar"] - window["start_bar"] + 1
        run = run + length if window["lead"] == previous else length
        previous = window["lead"]
        longest = max(longest, run)
    assert longest <= 8


def test_motion_alternates_between_the_two_movers_and_the_other_holds() -> None:
    draft = _draft()
    turns = []
    for window in draft["windows"]:
        if "motion" not in window["active"]:
            continue
        start = window["start_bar"]
        upper = _labels(draft, "MOVER-U")[start]
        lower = _labels(draft, "MOVER-D")[start]
        assert {upper, lower} == {arrange_generator.MOTION_LABEL, arrange_generator.HOLD_LABEL}
        turns.append("U" if upper == arrange_generator.MOTION_LABEL else "D")
    assert len(turns) >= 2
    assert all(left != right for left, right in zip(turns, turns[1:], strict=False))


def test_ac011_no_membership_claims_and_no_coordinate_inputs() -> None:
    params = set(inspect.signature(generate_arrangement_draft).parameters)
    assert not params & {"x", "y", "z", "pan", "tilt", "coordinates", "position"}
    draft = _draft()
    labels = {cue["label"] for track in draft["tracks"] for cue in track["cues"]}
    assert not any(re.search(r"멤버\s*\d+\s*대", label) for label in labels)
    assert not any("fid" in label.lower() for label in labels)


def test_ac012_same_input_gives_the_same_draft() -> None:
    assert _draft() == _draft()


def test_ac013_generator_source_has_no_console_calls() -> None:
    for module in (arrange_generator, arrange_policy):
        source = inspect.getsource(module)
        for token in ("ConsoleLink", ".exec(", ".deploy("):
            assert token not in source


def test_ac014_roles_and_track_names_follow_the_rig_vocabulary() -> None:
    draft = _draft()
    for track in draft["tracks"]:
        assert track["layer_role"] in RIG_LAYER_ROLES
        assert track["group_name"] not in SPEC_ROLE_LABELS
        assert isinstance(track["group_no"], int)
    names = [track["group_name"] for track in draft["tracks"]]
    assert find_overlapping_group_tracks(names) is None


def test_ac015_missing_bar_map_returns_a_note_without_raising() -> None:
    draft = generate_arrangement_draft(None, _layout())
    assert draft["tracks"] == []
    assert draft["windows"] == []
    assert arrange_generator.UNCONFIRMED_NOTE in (draft["note"] or "")


def test_invalid_bar_map_returns_the_same_note() -> None:
    draft = generate_arrangement_draft({"schema_version": 99}, _layout())
    assert draft["tracks"] == []
    assert arrange_generator.UNCONFIRMED_NOTE in (draft["note"] or "")


def test_overlapping_group_tracks_are_rejected() -> None:
    layout = _layout() + [
        {
            "group_no": 99,
            "group_no_confirmed": True,
            "group_name": "MOVER-ALL",
            "layer_role": "mover",
        }
    ]
    with pytest.raises(ValueError):
        generate_arrangement_draft(_bar_map(), layout)


def test_unknown_layer_role_is_rejected() -> None:
    layout = [
        {"group_no": 1, "group_no_confirmed": True, "group_name": "EXTRA", "layer_role": "laser"}
    ]
    with pytest.raises(ValueError):
        generate_arrangement_draft(_bar_map(), layout)


def test_track_without_a_role_stays_at_rest() -> None:
    layout = [
        {"group_no": 1, "group_no_confirmed": True, "group_name": "EXTRA", "layer_role": None}
    ]
    draft = generate_arrangement_draft(_bar_map(), layout)
    assert set(_labels(draft, "EXTRA").values()) == {arrange_generator.REST_LABEL}


def test_ac016_policy_is_per_song_and_has_no_numeric_module_constants() -> None:
    slow = _draft(ArrangementPolicy(slow_song=True))
    default = _draft(ArrangementPolicy())
    assert _labels(default, "STROBE")[17] == arrange_generator.STROBE_LABEL
    assert _labels(slow, "STROBE")[17] == arrange_generator.REST_LABEL
    assert ArrangementPolicy().slow_song is False
    for module in (arrange_generator, arrange_policy):
        numeric = [
            name
            for name, value in vars(module).items()
            if name.isupper() and isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        assert numeric == []


def test_policy_rejects_nonsense_values() -> None:
    with pytest.raises(ValueError):
        ArrangementPolicy(window_bars=0)
    with pytest.raises(ValueError):
        ArrangementPolicy(base_layer_cap=3, drop_layer_cap=2)

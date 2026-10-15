"""프리셋 값 파서·읽기·기억·색 배선 (응답기 1.7.0 `presetdata`).

🔴 아래 픽스처의 모양은 **그럴듯하게 지어낸 것**이다. 실기 onPC 2.4.2 의
`GetPresetData` 가 실제로 돌려주는 테이블 모양은 아직 관측되지 않았다 — 실기에서
확인해야 한다(PR 의 「실기 확인 절차」). 이 시험이 고정하는 것은 파서의 **방어
규율**(모르는 모양은 빈 결과, 범위 밖은 버림, 지어내지 않음)과 전송 합성(창 나눠
읽기·기억)이지 콘솔의 실제 모양이 아니다.
"""

from __future__ import annotations

import json

import pytest

from server.design.beat_grid_color_presets import (
    attach_color_rgb_to_cues,
    attach_color_rgb_to_drawer,
    color_preset_rgb,
    color_preset_rgbs,
)
from server.design.preset_values import (
    PositionValue,
    PresetValueCache,
    PresetValues,
    parse_preset_data,
    preset_path,
    read_preset_table,
    read_preset_values,
)

# -- 픽스처: 그럴듯한 GetPresetData 결과(실기 모양 미확인) ---------------------------

TWO_COLOR_GROUPS = [
    {"fixtures": "Group 1", "ColorRGB_R": 100, "ColorRGB_G": 0, "ColorRGB_B": 0},
    {"fixtures": "Group 2", "ColorRGB_R": 0, "ColorRGB_G": 0, "ColorRGB_B": 100},
]

# 같은 색을 쓰는 장비가 여럿 — 서로 다른 색만 순서대로 남는다
REPEATED_COLOR = [
    {"ColorRGB_R": 100, "ColorRGB_G": 0, "ColorRGB_B": 0},
    {"ColorRGB_R": 100.0, "ColorRGB_G": 0.0, "ColorRGB_B": 0.0},
    {"ColorRGB_R": 0, "ColorRGB_G": 100, "ColorRGB_B": 0},
]

# 모듈 접두가 붙은 속성 이름 + {"value": n} 한 겹
PREFIXED = {
    "Fixture 101": {
        "Main Module#2_ColorRGB_R": {"value": 50},
        "Main Module#2_ColorRGB_G": {"value": 25},
        "Main Module#2_ColorRGB_B": {"value": 12.5},
    }
}

# {name, value} 쌍의 목록
PAIR_LIST = [
    {"attribute": "ColorRGB_R", "value": 10},
    {"attribute": "ColorRGB_G", "value": 20},
    {"attribute": "ColorRGB_B", "value": 30},
]


class TestParseColor:
    def test_two_groups_give_two_distinct_colors_in_order(self):
        values = parse_preset_data(TWO_COLOR_GROUPS)
        assert values.color_rgbs == ((100.0, 0.0, 0.0), (0.0, 0.0, 100.0))

    def test_repeated_color_is_listed_once(self):
        values = parse_preset_data(REPEATED_COLOR)
        assert values.color_rgbs == ((100.0, 0.0, 0.0), (0.0, 100.0, 0.0))

    def test_module_prefix_and_value_wrapper(self):
        assert parse_preset_data(PREFIXED).color_rgbs == ((50.0, 25.0, 12.5),)

    def test_name_value_pair_list(self):
        values = parse_preset_data(PAIR_LIST)
        assert values.color_rgbs == ((10.0, 20.0, 30.0),)
        assert values.positions == () and values.dimmers == ()  # 쌍을 이중 계산하지 않는다

    def test_coloradd_used_when_no_colorrgb(self):
        table = {"ColorAdd_R": 100, "ColorAdd_G": 50, "ColorAdd_B": 0}
        assert parse_preset_data(table).color_rgbs == ((100.0, 50.0, 0.0),)

    def test_colorrgb_wins_over_coloradd_in_the_same_container(self):
        table = {
            "ColorRGB_R": 1,
            "ColorRGB_G": 2,
            "ColorRGB_B": 3,
            "ColorAdd_R": 90,
            "ColorAdd_G": 90,
            "ColorAdd_B": 90,
        }
        assert parse_preset_data(table).color_rgbs == ((1.0, 2.0, 3.0),)

    def test_triple_form(self):
        assert parse_preset_data({"ColorRGB_RGB": [10, 20, 30]}).color_rgbs == ((10.0, 20.0, 30.0),)

    def test_numeric_strings_are_accepted(self):
        table = {"ColorRGB_R": "100", "ColorRGB_G": "50.5", "ColorRGB_B": "0"}
        assert parse_preset_data(table).color_rgbs == ((100.0, 50.5, 0.0),)


class TestParseNeverInvents:
    @pytest.mark.parametrize(
        "table",
        [
            None,
            "",
            "ColorRGB_R",
            42,
            [],
            {},
            [[], {}, [[]]],
            {"foo": {"bar": [1, 2, 3]}},
            {"ColorRGB_R": 50, "ColorRGB_G": 50},  # B 없음 — 반쪽 색은 색이 아니다
            {"ColorRGB_R": 50, "ColorRGB_G": 50, "ColorRGB_B": None},
            {"ColorRGB_R": True, "ColorRGB_G": False, "ColorRGB_B": True},  # bool 은 수가 아니다
            {"ColorRGB_R": float("nan"), "ColorRGB_G": 0, "ColorRGB_B": 0},
            {"ColorRGB_R": 255, "ColorRGB_G": 0, "ColorRGB_B": 0},  # 퍼센트 아님 — 환산 안 함
            {"ColorRGB_R": -1, "ColorRGB_G": 0, "ColorRGB_B": 0},
            {"Dimmer": 150},
            {"Dimmer": "bright"},
            {"ColorRGB_RGB": [1, 2]},
            {"notColorRGB_R": 1, "notColorRGB_G": 2, "notColorRGB_B": 3},
        ],
    )
    def test_unknown_or_invalid_shape_returns_nothing(self, table):
        assert parse_preset_data(table) == PresetValues()
        assert parse_preset_data(table).empty

    def test_mixed_valid_and_invalid_keeps_only_the_valid(self):
        table = [
            {"ColorRGB_R": 255, "ColorRGB_G": 0, "ColorRGB_B": 0},
            {"ColorRGB_R": 0, "ColorRGB_G": 100, "ColorRGB_B": 0},
        ]
        assert parse_preset_data(table).color_rgbs == ((0.0, 100.0, 0.0),)

    def test_depth_is_bounded(self):
        node: object = {"ColorRGB_R": 1, "ColorRGB_G": 2, "ColorRGB_B": 3}
        for _ in range(40):
            node = {"x": node}
        assert parse_preset_data(node).empty  # 너무 깊으면 포기(재귀 폭주 없음)


class TestParseDimmerAndPosition:
    def test_dimmer(self):
        assert parse_preset_data({"Dimmer": 75}).dimmers == (75.0,)
        assert parse_preset_data([{"Dimmer": 75}, {"Dimmer": 75}, {"Dimmer": 0}]).dimmers == (
            75.0,
            0.0,
        )

    def test_pan_tilt_pair(self):
        table = [{"Pan": -45.5, "Tilt": 20}, {"Pan": 10, "Tilt": 20}]
        assert parse_preset_data(table).positions == (
            PositionValue(-45.5, 20.0),
            PositionValue(10.0, 20.0),
        )

    def test_lone_pan_keeps_tilt_unknown(self):
        assert parse_preset_data({"Pan": 12}).positions == (PositionValue(12.0, None),)

    def test_pair_list_position(self):
        table = [{"name": "Pan", "value": 5}, {"name": "Tilt", "value": 6}]
        assert parse_preset_data(table).positions == (PositionValue(5.0, 6.0),)


# -- 읽기: 창 나눠 읽기 합성 ---------------------------------------------------------


class FakePort:
    """`presetdata` 창 응답을 흉내 낸다(응답기 1.7.0 §4.9 규약)."""

    def __init__(self, table, *, window=1, echo=True, fail_after=None):
        self.table = table
        self.window = window
        self.echo = echo
        self.fail_after = fail_after
        self.calls: list[tuple[str, int]] = []

    def query_preset_data(self, path, *, offset=0):
        self.calls.append((path, offset))
        if self.fail_after is not None and len(self.calls) > self.fail_after:
            raise RuntimeError("console silent")
        if isinstance(self.table, list):
            entries = self.table
            window = entries[offset : offset + self.window]
            data = json.dumps(window)
        else:
            items = sorted(self.table.items())
            entries = items
            data = json.dumps(dict(items[offset : offset + self.window]))
        total = len(entries)
        payload = {
            "ok": True,
            "kind": "presetdata",
            "path": path,
            "offset": offset if self.echo else offset + 1,
            "total": total,
            "truncated": offset + self.window < total,
            "data": data,
        }
        return payload


class TestReadTable:
    def test_reassembles_windows(self):
        port = FakePort(TWO_COLOR_GROUPS, window=1)
        assert read_preset_table(port, "DataPool/PresetPools/4/22") == TWO_COLOR_GROUPS
        assert [offset for _path, offset in port.calls] == [0, 1]

    def test_hash_windows_merge(self):
        table = {"a": {"Dimmer": 1}, "b": {"Dimmer": 2}, "c": {"Dimmer": 3}}
        assert read_preset_table(FakePort(table, window=2), "p") == table

    def test_wrong_echo_means_not_fully_read(self):
        assert read_preset_table(FakePort(TWO_COLOR_GROUPS, echo=False), "p") is None

    def test_failed_reply_is_none(self):
        class Failing:
            def query_preset_data(self, path, *, offset=0):
                return {"ok": False, "error": "x"}

        assert read_preset_table(Failing(), "p") is None

    def test_non_json_or_scalar_data_is_none(self):
        class Bad:
            def __init__(self, data):
                self.data = data

            def query_preset_data(self, path, *, offset=0):
                return {"ok": True, "offset": offset, "truncated": False, "data": self.data}

        assert read_preset_table(Bad("not json"), "p") is None
        assert read_preset_table(Bad("42"), "p") is None

    def test_stuck_window_is_none(self):
        class Stuck:
            def query_preset_data(self, path, *, offset=0):
                return {"ok": True, "offset": offset, "truncated": True, "data": "[]"}

        assert read_preset_table(Stuck(), "p") is None

    def test_page_cap_stops_a_runaway(self):
        class Endless:
            def __init__(self):
                self.n = 0

            def query_preset_data(self, path, *, offset=0):
                self.n += 1
                return {"ok": True, "offset": offset, "truncated": True, "data": "[1]"}

        port = Endless()
        assert read_preset_table(port, "p") is None
        assert port.n <= 64


class TestReadValues:
    def test_preset_path(self):
        assert preset_path("DataPool/PresetPools/", "4.22") == "DataPool/PresetPools/4/22"
        assert preset_path("DataPool/PresetPools", "4") is None
        assert preset_path("DataPool/PresetPools", "a.b") is None

    def test_read_values_end_to_end(self):
        port = FakePort(TWO_COLOR_GROUPS, window=1)
        values = read_preset_values(port, "DataPool/PresetPools", "4.22")
        assert values is not None
        assert values.color_rgbs == ((100.0, 0.0, 0.0), (0.0, 0.0, 100.0))
        assert port.calls[0][0] == "DataPool/PresetPools/4/22"

    def test_bad_preset_number_makes_no_console_call(self):
        port = FakePort([])
        assert read_preset_values(port, "DataPool/PresetPools", "nope") is None
        assert port.calls == []


class TestCache:
    def test_remembers_reads_and_empty_results(self):
        port = FakePort(TWO_COLOR_GROUPS, window=5)
        cache = PresetValueCache()
        cache.refresh(port, "DataPool/PresetPools", ["4.22", "4.22"])
        assert len(port.calls) == 1
        assert cache.colors("4.22") == ((100.0, 0.0, 0.0), (0.0, 0.0, 100.0))
        cache.refresh(port, "DataPool/PresetPools", ["4.22"])
        assert len(port.calls) == 1  # 기억 — 다시 묻지 않는다
        assert cache.colors("4.99") is None

    def test_empty_reading_is_remembered_but_gives_no_colors(self):
        port = FakePort([{"unknown": 1}], window=5)
        cache = PresetValueCache()
        cache.refresh(port, "DataPool/PresetPools", ["4.30"])
        cache.refresh(port, "DataPool/PresetPools", ["4.30"])
        assert len(port.calls) == 1
        assert cache.colors("4.30") is None

    def test_console_error_stops_the_batch_and_is_not_remembered(self):
        port = FakePort(TWO_COLOR_GROUPS, window=5, fail_after=0)
        cache = PresetValueCache()
        cache.refresh(port, "DataPool/PresetPools", ["4.1", "4.2", "4.3"])
        assert len(port.calls) == 1  # 첫 오류에서 멈춘다 — 낡은 응답기에 타임아웃을 쌓지 않는다
        assert cache.get("4.1") is None

    def test_limit_bounds_round_trips(self):
        port = FakePort(TWO_COLOR_GROUPS, window=5)
        cache = PresetValueCache()
        cache.refresh(port, "DataPool/PresetPools", [f"4.{i}" for i in range(1, 11)], limit=3)
        assert len(port.calls) == 3

    def test_invalidate(self):
        port = FakePort(TWO_COLOR_GROUPS, window=5)
        cache = PresetValueCache()
        cache.refresh(port, "DataPool/PresetPools", ["4.22"])
        cache.invalidate("4.22")
        assert cache.get("4.22") is None


# -- 색 배선: 앱 기록 뒤의 폴백 ------------------------------------------------------


def _grid():
    return {
        "preset_colors": {"4.41": {"r": 50, "g": 0, "b": 12.5}},
        "tracks": [
            {
                "group_name": "G1",
                "cues": [
                    {"bar": 1, "color_preset_no": "4.41"},
                    {"bar": 2, "color_preset_no": "4.22"},
                    {"bar": 3, "color_preset_no": "4.7"},
                ],
            }
        ],
    }


def _console(preset_no):
    return {"4.22": ((100.0, 0.0, 0.0), (0.0, 0.0, 100.0)), "4.41": ((9.0, 9.0, 9.0),)}.get(
        preset_no
    )


class TestColorWiring:
    def test_default_behaviour_unchanged_without_console_colors(self):
        assert color_preset_rgb(_grid(), "4.22") is None
        assert color_preset_rgbs(_grid(), "4.22") == []

    def test_app_record_wins_over_console(self):
        grid = _grid()
        assert color_preset_rgb(grid, "4.41", console_colors=_console) == (50.0, 0.0, 12.5)
        assert color_preset_rgbs(grid, "4.41", console_colors=_console) == [(50.0, 0.0, 12.5)]

    def test_console_fallback_gives_first_color_and_all_colors(self):
        grid = _grid()
        assert color_preset_rgb(grid, "4.22", console_colors=_console) == (100.0, 0.0, 0.0)
        assert color_preset_rgbs(grid, "4.22", console_colors=_console) == [
            (100.0, 0.0, 0.0),
            (0.0, 0.0, 100.0),
        ]
        assert color_preset_rgb(grid, "4.7", console_colors=_console) is None

    def test_cues_carry_color_rgb_and_color_rgbs(self):
        cues = attach_color_rgb_to_cues(_grid(), console_colors=_console)["tracks"][0]["cues"]
        assert cues[0]["color_rgb"] == [50.0, 0.0, 12.5]
        assert cues[0]["color_rgbs"] == [[50.0, 0.0, 12.5]]
        assert cues[1]["color_rgb"] == [100.0, 0.0, 0.0]
        assert cues[1]["color_rgbs"] == [[100.0, 0.0, 0.0], [0.0, 0.0, 100.0]]
        assert "color_rgb" not in cues[2] and "color_rgbs" not in cues[2]

    def test_cues_without_console_colors_still_only_app_records(self):
        cues = attach_color_rgb_to_cues(_grid())["tracks"][0]["cues"]
        assert cues[0]["color_rgbs"] == [[50.0, 0.0, 12.5]]
        assert "color_rgb" not in cues[1]

    def test_drawer_entries(self):
        sections = [
            {
                "pool_name": "Color",
                "entries": [
                    {"preset_no": "4.41"},
                    {"preset_no": "4.22"},
                    {"preset_no": "4.7"},
                ],
            },
            {"pool_name": "Dimmer", "entries": [{"preset_no": "1.1"}]},
        ]
        out = attach_color_rgb_to_drawer(sections, _grid(), console_colors=_console)
        color = {e["preset_no"]: e for e in out[0]["entries"]}
        assert color["4.22"]["rgb"] == [100.0, 0.0, 0.0]
        assert color["4.22"]["rgbs"] == [[100.0, 0.0, 0.0], [0.0, 0.0, 100.0]]
        assert color["4.41"]["rgbs"] == [[50.0, 0.0, 12.5]]
        assert "rgb" not in color["4.7"]
        assert "rgb" not in out[1]["entries"][0]

"""카드 t607(SPEC-LDBEAT-001, REQ-LDBEAT-015(h)/(b) 계속) — 「＋ 새 프리셋
만들기」 창이 "혼합"(mixed) 효과 종류의 콘솔 점유를 **틀린 풀**로 확인하던
결함.

실측(``.moai/reports/t543/r1_pools.json``, 카드 t604): `PresetPools` 풀
21은 이름 "All 1"(슬롯 1~7, 301 점유), 풀 22는 이름 "All 2"(슬롯 1
점유). `beat_grid_presets._POOL_NAME_TO_EFFECT_KIND`는 "mixed"를 **이름**
"All 1"(=풀 21)에 매어 두고, `preset_pools.yaml`의 ``mixed_all`` **번호대**
는 풀 22(``22.0``~``22.99``)다 — 이름과 번호대가 어긋난다. 옛 다이얼로그는
이름으로 풀 21을 읽어, 풀 22 번호대의 빈 자리를 **풀 21의 점유**로
판정했다 — 다른 풀의 자리로 이 후보가 비었는지를 판단한 셈이다.

리드 결정(이 카드): 번호대가 쓰는 풀은 **번호**로 직접 읽는다 — 풀
**이름** 규칙은 전혀 쓰지 않는다(이름은 쇼마다 바뀔 수 있다).
`read_effect_pools_by_number`(새 순수 함수)가 ``preset_pools.yaml``이
``kind``에 선언한 번호대의 풀 번호만으로 읽고, `first_free_preset_number`
는 그 번호로 가른 지도에서만 점유를 본다. 콘솔 접촉: 0건(쓰기) —
`FakeConsole.executed`로 직접 잰다."""

from __future__ import annotations

from server.design.beat_grid_presets import (
    first_free_preset_number,
    read_effect_pools_by_number,
)
from server.web.session import SongTimelineStore

from .test_new_preset_dialog_t589 import (
    _FX_RECIPE,
    _cue_of,
    _grid_with_effect_cell,
    _new_session,
    _pool_children_payload,
    _pool_list_payload,
    _state_tree,
    _timeline,
)

_CREATED = "박자 격자 새 프리셋"


class _FakeQuery:
    """``StateQuery``와 같은 모양 — ``test_beat_grid_presets_t551.py``의
    ``_FakeQuery``와 같은 관행(이 카드 전용으로 호출 경로를 세는 계수기를
    더한다). 풀 목록(``named_pools``)은 **의도적으로** 아무 응답에도 쓰이지
    않는다 — `read_effect_pools_by_number`는 풀 이름을 전혀 조회하지 않는다
    (이 사실 자체가 이 시험의 잠금이다)."""

    def __init__(
        self,
        *,
        pool_root: str = "DataPool/PresetPools",
        pool_children: dict[int, dict[int, str] | None] | None = None,
    ) -> None:
        self._pool_root = pool_root
        self._pool_children = pool_children or {}
        self.queried_paths: list[str] = []

    def __call__(self, probe_id: str, arguments: dict) -> object | None:
        path = arguments.get("path")
        self.queried_paths.append(str(path))
        for pool_no, children in self._pool_children.items():
            if path == f"{self._pool_root}/{pool_no}":
                if children is None:
                    return None  # 판독 실패 흉내.
                return {"children": [{"i": s, "name": n} for s, n in children.items()]}
        return None


_MIXED_POLICY = {
    "confirmed": False,
    "pools": {"mixed_all": {"start": "22.0", "end": "22.99"}},
}


# == ① `read_effect_pools_by_number` — 번호로만 읽는다 =========================


class TestReadEffectPoolsByNumber:
    def test_mixed_kind_reads_pool_22_never_touches_pool_21(self) -> None:
        query = _FakeQuery(
            pool_children={
                21: {1: "P1", 2: "P2", 3: "P3", 4: "P4", 5: "P5", 6: "P6", 7: "P7", 301: "P301"},
                22: {1: "Piano Solo"},
            }
        )
        result = read_effect_pools_by_number(
            query, "DataPool/PresetPools", "mixed", policy=_MIXED_POLICY, probe_prefix="t"
        )
        assert result == {22: {1: "Piano Solo"}}
        # 풀 21 경로는 한 번도 조회되지 않았다 — 이름 규칙이 전혀 없다.
        assert all("PresetPools/21" not in path for path in query.queried_paths)

    def test_pool_name_list_is_never_consulted(self) -> None:
        # 풀 "목록"(이름→번호) 경로를 아예 응답하지 않는 가짜 콘솔이라도
        # 번호 직접 읽기는 그대로 성공한다 — 이름 해석을 거치지 않는다.
        query = _FakeQuery(pool_children={22: {1: "Foo-named-preset"}})
        result = read_effect_pools_by_number(
            query, "DataPool/PresetPools", "mixed", policy=_MIXED_POLICY, probe_prefix="t"
        )
        assert result == {22: {1: "Foo-named-preset"}}
        assert "DataPool/PresetPools" not in query.queried_paths

    def test_unreadable_pool_is_absent_from_the_map_not_none(self) -> None:
        query = _FakeQuery(pool_children={22: None})
        result = read_effect_pools_by_number(
            query, "DataPool/PresetPools", "mixed", policy=_MIXED_POLICY, probe_prefix="t"
        )
        assert result == {}  # 지어내지 않는다 — 못 읽은 풀은 지도에 없다.

    def test_dimmer_two_sub_bands_sharing_one_pool_are_read_once(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {
                "dimmer_effect_a": {"start": "1.21", "end": "1.26"},
                "dimmer_effect_b": {"start": "1.31", "end": "1.33"},
            },
        }
        query = _FakeQuery(pool_children={1: {21: "A"}})
        result = read_effect_pools_by_number(
            query, "DataPool/PresetPools", "dimmer", policy=policy, probe_prefix="t"
        )
        assert result == {1: {21: "A"}}
        assert query.queried_paths.count("DataPool/PresetPools/1") == 1

    def test_position_and_color_pick_their_own_declared_pool_numbers(self) -> None:
        query = _FakeQuery(pool_children={2: {41: "Center"}, 4: {21: "LA Pink"}})
        position_policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        color_policy = {
            "confirmed": False,
            "pools": {"color_effect": {"start": "4.41", "end": "4.99"}},
        }
        assert read_effect_pools_by_number(
            query, "DataPool/PresetPools", "position", policy=position_policy, probe_prefix="t"
        ) == {2: {41: "Center"}}
        assert read_effect_pools_by_number(
            query, "DataPool/PresetPools", "color", policy=color_policy, probe_prefix="t"
        ) == {4: {21: "LA Pink"}}

    def test_kind_with_no_declared_band_reads_nothing(self) -> None:
        query = _FakeQuery(pool_children={22: {1: "x"}})
        result = read_effect_pools_by_number(
            query, "DataPool/PresetPools", "nonsense", policy=_MIXED_POLICY, probe_prefix="t"
        )
        assert result == {}
        assert query.queried_paths == []


# == ② `first_free_preset_number` — 다른 풀의 점유를 빌려 쓰지 않는다 ===========


class TestFirstFreePresetNumberNeverBorrowsAnotherPool:
    def test_pool_21_occupancy_never_blocks_a_pool_22_candidate(self) -> None:
        # 실측 그대로: 풀 21(이름 "All 1") 슬롯 0 점유, 풀 22(번호대가 실제로
        # 가리키는 풀)은 비어 있다. 다른 풀의 점유를 빌려 쓰지 않고 번호로만
        # 보면 풀 22의 첫 슬롯 "22.1"을 내준다(슬롯 0은 콘솔에 없다, 카드 t619).
        console_children = {21: {0: "Unrelated Pool 21 Preset"}, 22: {}}
        preset_no, reason, warning = first_free_preset_number(
            "mixed", policy=_MIXED_POLICY, grid={"tracks": []}, console_children=console_children
        )
        assert reason is None
        assert preset_no == "22.1"
        assert warning is None  # 풀 22는 실제로 읽혔다(빈 딕셔너리라도 읽음).

    def test_a_slot_free_in_21_but_occupied_in_22_is_correctly_skipped(self) -> None:
        # 거울상: 풀 21은 슬롯 0이 비었지만(이름 기반 옛 코드라면 "22.0"을
        # 내줬을 것) 실제 풀 22는 슬롯 0이 점유돼 있다 — 번호로 읽으면
        # "22.1"로 건너뛴다.
        console_children = {21: {}, 22: {0: "Occupied Mixed Preset"}}
        preset_no, reason, _warning = first_free_preset_number(
            "mixed", policy=_MIXED_POLICY, grid={"tracks": []}, console_children=console_children
        )
        assert reason is None
        assert preset_no == "22.1"


# == ③ 서버 핸들러(「효과」 다이얼로그, kind="mixed") — 전수 왕복 ===============


def _mixed_session(tmp_path, *, pool21: dict[int, str], pool22: dict[int, str] | None):
    """``pool22=None``은 "그 풀을 콘솔에서 못 읽음"(판독 실패)을 흉내 낸다 —
    경로를 아예 state_tree에서 빼면 `FakeConsole.query_state`가 예외를 던져
    `_registry_state_query`가 ``None``으로 떨어진다(`test_safety_gate.
    FakeConsole`과 같은 관행)."""
    store = SongTimelineStore()
    store.latest = _timeline(beat_grid=_grid_with_effect_cell("mixed"))
    pools: dict[str, dict] = {
        # 카드 t604 실측 그대로: 풀 21 이름 "All 1", 풀 22 이름 "All 2".
        "DataPool/PresetPools": _pool_list_payload({"All 1": 21, "All 2": 22}),
        "DataPool/PresetPools/21": _pool_children_payload(pool21),
    }
    if pool22 is not None:
        pools["DataPool/PresetPools/22"] = _pool_children_payload(pool22)
    state_tree = _state_tree(**pools)
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=state_tree)
    return session, store, console, approval


class TestMixedDialogReadsThePoolByNumber:
    def test_pool_21_occupancy_does_not_block_assignment_from_pool_22(self, tmp_path) -> None:
        session, store, console, _approval = _mixed_session(
            tmp_path,
            pool21={1: "P1", 2: "P2", 3: "P3", 4: "P4", 5: "P5", 6: "P6", 7: "P7", 301: "P301"},
            pool22={0: "Occupied Mixed Preset"},
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "effect", "LA Mix", "부드러운 혼합", fx=_FX_RECIPE
        )
        assert event.get("summary") == _CREATED, event
        number = _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"]
        # 풀 21의 점유(슬롯 0 비어 있음)를 빌려 "22.0"을 내주지 않는다 —
        # 풀 22(진짜 번호대 풀)의 슬롯 0 점유를 보고 "22.1"로 건너뛴다.
        assert number == "22.1"
        assert console.executed == []  # 읽기만(쓰기 0건).

    def test_renaming_the_pools_arbitrarily_gives_the_same_result(self, tmp_path) -> None:
        # 이름 규칙이 전혀 없다는 증거 — 풀 목록을 아예 다른 이름("Foo")으로
        # 지어도 결과가 바뀌지 않는다(번호로만 읽으므로).
        store = SongTimelineStore()
        store.latest = _timeline(beat_grid=_grid_with_effect_cell("mixed"))
        state_tree = _state_tree(
            **{
                "DataPool/PresetPools": _pool_list_payload({"Foo": 22, "Bar": 21}),
                "DataPool/PresetPools/21": _pool_children_payload({0: "Should Not Matter"}),
                "DataPool/PresetPools/22": _pool_children_payload({0: "Occupied Mixed Preset"}),
            }
        )
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "effect", "LA Mix", "부드러운 혼합", fx=_FX_RECIPE
        )
        assert event.get("summary") == _CREATED, event
        number = _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"]
        assert number == "22.1"
        assert console.executed == []

    def test_unreadable_pool_22_still_assigns_but_warns(self, tmp_path) -> None:
        session, store, console, _approval = _mixed_session(
            tmp_path,
            pool21={1: "P1"},
            pool22=None,  # 풀 22를 콘솔에서 못 읽음.
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "effect", "LA Mix", "부드러운 혼합", fx=_FX_RECIPE
        )
        assert event.get("summary") == _CREATED, event
        number = _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"]
        assert number == "22.1"  # 격자 참조만 보고 골랐다 — 풀 21로 대신 보지 않는다.
        assert "⚠ 콘솔 빈칸 미확인" in event["text"]
        assert console.executed == []

    def test_position_effect_field_is_unaffected_by_this_fix(self, tmp_path) -> None:
        # 회귀 방지 — "효과" 창이 위치 종류일 때는 그대로 풀 2를 번호로 읽는다
        # (이름 자리와 번호대 풀이 어긋나지 않는 종류라 동작이 그대로다).
        store = SongTimelineStore()
        store.latest = _timeline(beat_grid=_grid_with_effect_cell("position"))
        state_tree = _state_tree(
            **{
                "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
                "DataPool/PresetPools/2": _pool_children_payload({}),
            }
        )
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "effect", "LA Wave", "따뜻한 흰색", fx=_FX_RECIPE
        )
        assert event.get("summary") == _CREATED, event
        number = _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"]
        assert number == "2.61"
        assert console.executed == []

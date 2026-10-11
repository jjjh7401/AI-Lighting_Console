"""SPEC-LDBEAT-001 M3 — 박자 격자 편집의 프리셋 카탈로그 판독 (카드 t551
후속, 리드 지시 2026-10-11 "이미 있는 읽기 길을 써라 — 콘솔 쓰기 0 규칙은
읽기를 막지 않는다").

콘솔 접촉 0건 — 이 시험은 전부 가짜 풀 데이터로 돈다
(`test_preset_label_lookup_t232.py`의 `_FakeRegistry`/`_PoolHost`와 같은
관행). 새 판독 규율은 만들지 않는다 — `server.design.console_slots`
(paged_pool_children/resolve_named_pool_no, t480)와
`server.design.preset_names`(match_preset_name_across_pools, t477)를
그대로 재사용한다."""

from __future__ import annotations

from server.design.beat_grid_presets import (
    POOL_NAME_BY_FIELD,
    build_preset_drawer,
    pool_name_to_effect_kind,
    resolve_effect_preset_name,
    resolve_preset_name,
)


class _FakeQuery:
    """``query(probe_id, arguments) -> payload|None`` — ``console_slots.
    StateQuery``와 같은 모양. 풀 이름 해석(``DataPool/PresetPools``)과
    각 풀의 자식 판독을 고정 응답으로 흉내 낸다."""

    def __init__(
        self,
        *,
        pool_root: str = "DataPool/PresetPools",
        named_pools: dict[str, int] | None = None,
        pool_children: dict[int, dict[int, str] | None] | None = None,
    ) -> None:
        self._pool_root = pool_root
        self._named_pools = named_pools or {}
        self._pool_children = pool_children or {}

    def __call__(self, probe_id: str, arguments: dict) -> object | None:
        path = arguments.get("path")
        if path == self._pool_root:
            # 풀 목록 — resolve_named_pool_no 가 이 하나의 응답으로 이름→번호를 찾는다.
            children = [{"i": no, "name": name} for name, no in self._named_pools.items()]
            return {"children": children}
        for pool_no, children in self._pool_children.items():
            if path == f"{self._pool_root}/{pool_no}":
                if children is None:
                    return None  # 판독 실패 흉내 — POOL_UNREAD 로 떨어져야 한다.
                return {"children": [{"i": s, "name": n} for s, n in children.items()]}
        return None


class TestResolvePresetNameByField:
    def test_position_field_resolves_exact_name(self) -> None:
        query = _FakeQuery(
            named_pools={"Position": 2},
            pool_children={2: {41: "Center", 42: "Stage Left"}},
        )
        match = resolve_preset_name(
            query, "DataPool/PresetPools", "위치", "Center", probe_prefix="t"
        )
        assert match.pool_no == 2
        assert match.slot == 41

    def test_color_field_resolves_via_color_pool(self) -> None:
        query = _FakeQuery(
            named_pools={"Color": 4},
            pool_children={4: {21: "LA Pink", 22: "LA Blue"}},
        )
        match = resolve_preset_name(
            query, "DataPool/PresetPools", "색", "LA Pink", probe_prefix="t"
        )
        assert match.pool_no == 4
        assert match.slot == 21

    def test_effect_field_searches_every_pool_and_reports_which_matched(self) -> None:
        query = _FakeQuery(
            named_pools={"Position": 2, "Color": 4, "Dimmer": 1, "All 1": 21},
            pool_children={
                2: {61: "LA Sweep 2"},
                4: {},
                1: {},
                21: {},
            },
        )
        match = resolve_preset_name(
            query, "DataPool/PresetPools", "효과", "LA Sweep 2", probe_prefix="t"
        )
        assert match.pool_no == 2
        assert match.slot == 61

    def test_absent_name_is_name_absent(self) -> None:
        query = _FakeQuery(named_pools={"Position": 2}, pool_children={2: {41: "Center"}})
        match = resolve_preset_name(
            query, "DataPool/PresetPools", "위치", "No Such", probe_prefix="t"
        )
        assert match.slot is None
        assert match.kind == "absent"

    def test_ambiguous_name_is_name_ambiguous(self) -> None:
        query = _FakeQuery(
            named_pools={"Position": 2}, pool_children={2: {41: "Center", 42: "Center"}}
        )
        match = resolve_preset_name(
            query, "DataPool/PresetPools", "위치", "Center", probe_prefix="t"
        )
        assert match.slot is None
        assert match.kind == "ambiguous"

    def test_unread_pool_is_pool_unread_not_absent(self) -> None:
        # 풀 번호는 해석됐지만(이름 찾음) 그 풀의 자식 판독이 실패 — POOL_UNREAD.
        query = _FakeQuery(named_pools={"Position": 2}, pool_children={2: None})
        match = resolve_preset_name(
            query, "DataPool/PresetPools", "위치", "Center", probe_prefix="t"
        )
        assert match.slot is None
        assert match.kind == "pool_unread"

    def test_unknown_pool_name_is_also_pool_unread(self) -> None:
        # 풀 자체를 콘솔에서 못 찾음(이름 목록에 없음) — 이름 부재와는 다른 사유.
        query = _FakeQuery(named_pools={}, pool_children={})
        match = resolve_preset_name(
            query, "DataPool/PresetPools", "위치", "Center", probe_prefix="t"
        )
        assert match.slot is None
        assert match.kind == "pool_unread"

    def test_field_pool_mapping_matches_req_ldbeat_015_b(self) -> None:
        assert POOL_NAME_BY_FIELD == {"위치": "Position", "색": "Color", "밝기": "Dimmer"}


class TestResolveEffectPresetName:
    def test_returns_match_and_the_pool_name_it_matched(self) -> None:
        query = _FakeQuery(
            named_pools={"Position": 2, "Color": 4, "Dimmer": 1, "All 1": 21},
            pool_children={2: {}, 4: {21: "LA Pink"}, 1: {}, 21: {}},
        )
        match, pool_name = resolve_effect_preset_name(
            query, "DataPool/PresetPools", "LA Pink", probe_prefix="t"
        )
        assert match.pool_no == 4
        assert pool_name == "Color"
        assert pool_name_to_effect_kind(pool_name) == "color"

    def test_absent_name_returns_none_pool_name(self) -> None:
        query = _FakeQuery(
            named_pools={"Position": 2, "Color": 4, "Dimmer": 1, "All 1": 21},
            pool_children={2: {}, 4: {}, 1: {}, 21: {}},
        )
        match, pool_name = resolve_effect_preset_name(
            query, "DataPool/PresetPools", "No Such", probe_prefix="t"
        )
        assert match.slot is None
        assert pool_name is None


class TestPoolNameToEffectKind:
    def test_known_pool_names_map_to_kinds(self) -> None:
        assert pool_name_to_effect_kind("Position") == "position"
        assert pool_name_to_effect_kind("Color") == "color"
        assert pool_name_to_effect_kind("Dimmer") == "dimmer"
        assert pool_name_to_effect_kind("All 1") == "mixed"

    def test_unknown_pool_name_returns_none(self) -> None:
        assert pool_name_to_effect_kind("Gobo") is None


class TestBuildPresetDrawer:
    def _grid(self):
        return {
            "tracks": [
                {
                    "group_name": "MOVER-U",
                    "cues": [
                        {
                            "bar": 11,
                            "brightness": {"mode": None, "value_percent": None, "preset_no": None},
                            "position_preset_no": "2.41",
                            "color_preset_no": None,
                            "effect_preset_no": None,
                        },
                        {
                            "bar": 18,
                            "brightness": {"mode": None, "value_percent": None, "preset_no": None},
                            "position_preset_no": "2.41",
                            "color_preset_no": None,
                            "effect_preset_no": None,
                        },
                    ],
                },
                {
                    "group_name": "BACK",
                    "cues": [
                        {
                            "bar": 7,
                            "brightness": {
                                "mode": "dimmer_preset",
                                "value_percent": None,
                                "preset_no": "1.1",
                            },
                            "position_preset_no": None,
                            "color_preset_no": "4.21",
                            "effect_preset_no": None,
                        }
                    ],
                },
            ]
        }

    def test_three_pool_sections_match_mockup_titles(self) -> None:
        sections = build_preset_drawer(
            self._grid(),
            pools={
                "Dimmer": (1, {1: "LA Full"}),
                "Position": (2, {41: "Center"}),
                "Color": (4, {21: "LA Pink"}),
            },
            policy={"confirmed": True, "pools": {}},
        )
        titles = [section["title"] for section in sections]
        assert titles == [
            "디머 풀 1 — 밝기·밝기 효과",
            "위치 풀 2 — 위치·움직임(상대값)",
            "색 풀 4",
        ]

    def test_usage_counts_match_cues_referencing_that_slot(self) -> None:
        sections = build_preset_drawer(
            self._grid(),
            pools={
                "Dimmer": (1, {1: "LA Full"}),
                "Position": (2, {41: "Center"}),
                "Color": (4, {21: "LA Pink"}),
            },
            policy={"confirmed": True, "pools": {}},
        )
        position_section = next(s for s in sections if s["pool_name"] == "Position")
        assert position_section["entries"][0] == {
            "preset_no": "2.41",
            "name": "Center",
            "usage_count": 2,
            "used_by": [{"group_name": "MOVER-U", "bar": 11}, {"group_name": "MOVER-U", "bar": 18}],
            # 조건1(코디네이터 지시 2026-10-11) — 빈 ``pools`` 정책이라 어느
            # kind도 선언된 효과 풀이 없다 → 전부 False(효과로 분류하지
            # 않는다, 모르면 base 쪽에 남긴다).
            "is_effect_band": False,
            # 카드 t568(REQ-LDBEAT-023(c)) — 콘솔 풀 자식 판독
            # (``paged_pool_children``, t480)은 슬롯 번호·이름만 돌려주고
            # 설명 텍스트를 읽는 경로가 이 저장소에 없다(아래
            # TestPresetDrawerDescription 참조) — 지어내지 않고 명시적
            # ``None``.
            "description": None,
            # 카드 t569 — 앱이 저장한 설명이 없으면 콘솔에서 읽은 쇼 프리셋.
            "description_source": "show",
        }
        dimmer_section = next(s for s in sections if s["pool_name"] == "Dimmer")
        assert dimmer_section["entries"][0]["usage_count"] == 1
        color_section = next(s for s in sections if s["pool_name"] == "Color")
        assert color_section["entries"][0]["usage_count"] == 1

    def test_unread_pool_section_marks_pool_no_none_and_entries_empty(self) -> None:
        sections = build_preset_drawer(
            self._grid(),
            pools={"Dimmer": None, "Position": (2, {41: "Center"}), "Color": (4, {21: "LA Pink"})},
            policy={"confirmed": True, "pools": {}},
        )
        dimmer_section = next(s for s in sections if s["pool_name"] == "Dimmer")
        assert dimmer_section["pool_no"] is None
        assert dimmer_section["entries"] == []
        assert dimmer_section["unread"] is True

    def test_confirmed_false_is_carried_onto_every_section(self) -> None:
        sections = build_preset_drawer(
            self._grid(),
            pools={"Dimmer": (1, {}), "Position": (2, {}), "Color": (4, {})},
            policy={"confirmed": False, "pools": {}},
        )
        assert all(section["bands_confirmed"] is False for section in sections)

    def test_does_not_fabricate_entries_for_slots_not_in_the_pool_read(self) -> None:
        # 큐가 참조하는 2.41 번호가 풀 판독 결과에 없으면(삭제됐거나 판독
        # 불완전) 이름을 지어내지 않는다 — entries 는 판독된 슬롯만 담는다.
        sections = build_preset_drawer(
            self._grid(),
            pools={"Dimmer": (1, {}), "Position": (2, {}), "Color": (4, {})},
            policy={"confirmed": True, "pools": {}},
        )
        position_section = next(s for s in sections if s["pool_name"] == "Position")
        assert position_section["entries"] == []


class TestPresetDrawerEffectBand:
    """카드 t551 계속(코디네이터 지시 2026-10-11, 조건 1·"lead 가 옵션 A를
    골랐다" — mockup 자신이 같은 풀 안에서 번호대로 기본/효과 프리셋을
    가른다는 근거, `ldbeat-runbook-mockup-20261008.md` 14-17행·26-29행).
    번호대는 `server.design.beat_grid_edit.validate_preset_pool_assignment`
    + 실제 `preset_pools.yaml`을 그대로 재사용한다 — 이 시험도 이 모듈도
    번호대 리터럴을 새로 만들지 않는다(조건1)."""

    def _grid(self):
        return {
            "tracks": [
                {"group_name": "MOVER-U", "cues": []},
            ]
        }

    def test_position_entry_inside_effect_band_is_flagged(self) -> None:
        from server.design.beat_grid_edit import load_preset_pool_policy

        policy = load_preset_pool_policy()
        band = policy["pools"]["position_effect"]
        midpoint_slot = int((float(band["start"]) + float(band["end"])) / 2 * 100) % 100
        sections = build_preset_drawer(
            self._grid(),
            pools={"Dimmer": None, "Position": (2, {midpoint_slot: "LA Pan Wave"}), "Color": None},
            policy=policy,
        )
        position_section = next(s for s in sections if s["pool_name"] == "Position")
        assert position_section["entries"][0]["is_effect_band"] is True

    def test_position_entry_outside_effect_band_is_not_flagged(self) -> None:
        from server.design.beat_grid_edit import load_preset_pool_policy

        policy = load_preset_pool_policy()
        sections = build_preset_drawer(
            self._grid(),
            # slot 41 → "2.41", REQ-LDBEAT-015 증거 칸의 기본 위치 풀
            # 예시대로 position_effect(2.61~2.68) 밖이다.
            pools={"Dimmer": None, "Position": (2, {41: "Center"}), "Color": None},
            policy=policy,
        )
        position_section = next(s for s in sections if s["pool_name"] == "Position")
        assert position_section["entries"][0]["is_effect_band"] is False

    def test_dimmer_entry_inside_either_effect_sub_band_is_flagged(self) -> None:
        from server.design.beat_grid_edit import load_preset_pool_policy

        policy = load_preset_pool_policy()
        band_b = policy["pools"]["dimmer_effect_b"]
        midpoint_slot = int((float(band_b["start"]) + float(band_b["end"])) / 2 * 100) % 100
        sections = build_preset_drawer(
            self._grid(),
            pools={"Dimmer": (1, {midpoint_slot: "LA Chase"}), "Position": None, "Color": None},
            policy=policy,
        )
        dimmer_section = next(s for s in sections if s["pool_name"] == "Dimmer")
        assert dimmer_section["entries"][0]["is_effect_band"] is True

    def test_dimmer_entry_outside_both_effect_sub_bands_is_not_flagged(self) -> None:
        from server.design.beat_grid_edit import load_preset_pool_policy

        policy = load_preset_pool_policy()
        sections = build_preset_drawer(
            self._grid(),
            pools={"Dimmer": (1, {1: "LA Full"}), "Position": None, "Color": None},
            policy=policy,
        )
        dimmer_section = next(s for s in sections if s["pool_name"] == "Dimmer")
        assert dimmer_section["entries"][0]["is_effect_band"] is False

    def test_undeclared_pool_policy_defaults_every_entry_to_not_effect_band(self) -> None:
        # pools 가 비어 있으면(아직 확정 안 됨) "모른다"를 True 로 지어내지
        # 않고 False(= base 쪽에 남긴다)로 떨어진다.
        sections = build_preset_drawer(
            self._grid(),
            pools={"Dimmer": (1, {1: "LA Full"}), "Position": None, "Color": None},
            policy={"confirmed": False, "pools": {}},
        )
        dimmer_section = next(s for s in sections if s["pool_name"] == "Dimmer")
        assert dimmer_section["entries"][0]["is_effect_band"] is False


class TestPresetDrawerDescription:
    """카드 t568(REQ-LDBEAT-023(c)) — 칩 툴팁이 쓰는 프리셋 "설명 텍스트"의
    서버 쪽 출처 조사. 이 카드 범위에서 콘솔에 새 프로브를 추가하지
    않는다는 전제로, 이미 있는 읽기 경로를 뒤졌다:

    - ``server.design.console_slots.paged_pool_children``(t480) — 풀
      자식을 판독하지만 응답기가 돌려주는 필드는 ``i``(슬롯 번호)와
      ``name``(짧은 이름)뿐이다(PROTOCOL §4.2, 이 모듈의 ``_FakeQuery``가
      흉내 내는 그 모양) — 설명 텍스트 필드가 없다.
    - ``server/design/beat_grid_data/*.yaml``(measured_console.yaml·
      preset_pools.yaml 등) — grep으로 "description"/"설명" 키를 찾았으나
      0건(이 파일 자신이 그 grep으로 조사했다).

    그래서 ``build_preset_drawer``는 ``description`` 을 지어내지 않고
    명시적 ``None`` 으로 채운다(생략이 아니라 명시 — "이 자리는 비었다"는
    사실 자체가 정보, REQ-LDBEAT-015(f)와 같은 원칙). 클라이언트
    `presetChipTooltip.ts`의 `formatPresetChipTooltip`은 이미
    `null`/`undefined`를 사용 수만 보이는 것으로 처리한다(카드 t560,
    변경 없음) — 이 카드가 메운 것은 그 필드가 **항상** 응답에 명시적으로
    존재한다는 것뿐이다."""

    def _grid(self):
        return {"tracks": []}

    def test_every_entry_carries_an_explicit_none_description(self) -> None:
        sections = build_preset_drawer(
            self._grid(),
            pools={
                "Dimmer": (1, {1: "LA Full"}),
                "Position": (2, {41: "Center"}),
                "Color": (4, {21: "LA Pink"}),
            },
            policy={"confirmed": True, "pools": {}},
        )
        for section in sections:
            for entry in section["entries"]:
                assert "description" in entry
                assert entry["description"] is None

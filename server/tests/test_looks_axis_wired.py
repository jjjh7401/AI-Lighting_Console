"""t350 — 축 부재 보류가 **생산 경로**에서 발사된다.

t348 은 `_plan_stores` 에 축 부재 rung 을 만들고 `build_instantiation(axes=...)` 를
열었지만, 그것을 넘기는 생산 호출자가 **0** 이었다. 그래서 형제 파일
(`test_looks_axis_hold.py`)이 전부 초록인 채로 실제 룩 저장은 아무것도 대조하지 않고
있었다 — 부품은 초록인데 경로가 안 이어진 형태(t343->t229 · t344->t351 이 이미 두 번
겪었다).

이 파일은 그래서 **판정기를 직접 넣어주지 않는다.** 모델이 들어오는 자리
(`registry.dispatch("instantiate_look")`)로 들어가고, 능력은 가짜 콘솔이 답한다.
`axes=` 배선을 지우면 여기가 빨개지고 형제 파일은 초록으로 남는다 — 그 갈림이 이
파일의 존재 이유다.

## 이 파일의 값이 어디서 왔는지 (섞지 말 것)

* **실측 replay** — Robin MegaPointe(FixtureType 11, Mode 1) Zoom
  `PHYSICALFROM=42.0 PHYSICALTO=1.8`. 2026-09-10, onPC / 응답기 1.6.5, 읽기 전용.
  `test_lxseq_preset_group_range.py` · `test_capability_read.py` 와 **같은 표본**이다.
  기종 이름이 콘솔 쪽 `Robin` 인 것도 그 실측이다(시트는 `Robe`).
* **실측 replay** — Source Four 에 Pan/Tilt 가 없다는 것(t344 리그 실측 15기종 중
  4기종). `MEASURED_ATTRIBUTE_SPELLINGS` 가 `Dimmer` · `Zoom` 둘인 것도 그 실측이다.
* 🔴 **구성된 대조군** — Source Four 의 채널이 `Dimmer` 하나뿐이라는 것, 그 물리
  범위 `0.0~100.0`, 그리고 아래 왕복 수 전부. 이 저장소에 그 판독 기록은 **없다**.
  「줌 없는 기종이 섞인 리그」라는 **모양**을 만들기 위한 값이며 그 기종이 그렇다는
  주장이 아니다(형제 파일들의 `Pan Only` · Spiider 와 같은 규율).

콘솔 접촉 0. 발화 포트는 인메모리 기록기이고, 실기 콘솔에 나간 명령은 한 건도 없다.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.looks.instantiate import AXIS_ABSENT, CONFLICT, NO_FREE_SLOT
from server.looks.rig_axes import MEASURED_ATTRIBUTE_SPELLINGS
from server.orchestrator.tools import build_toolset
from server.tests.test_looks_tool import (
    DEFAULT_GROUPS,
    DEFAULT_POOLS,
    GROUPS_PATH,
    POOLS_PATH,
    _child,
    _library,
    _look,
    _payload,
    _RecordingPort,
)

TOOL = "instantiate_look"
TYPES_ROOT = "Patch/FixtureTypes"
FIXTURE_ROOT = "Patch/Stages/1/Fixtures"

#: 정본 라이브러리 실제 룩. Dimmer 72 · ColorRGB 셋 · **Zoom 35** 을 나른다
#: (`server/looks/library/edm.yaml`). 구성한 룩이 아니라 배포되는 룩이라, 이 카드가
#: 이은 경로가 실제 데이터에 닿는다는 것까지 함께 잰다.
LOOK_ID = "edm-build-magenta"

MEGAPOINTE = "Robin MegaPointe"
SOURCE_FOUR = "Source Four"

#: 기종 슬롯 -> (콘솔이 답하는 이름, 채널 슬롯 -> (속성, PHYSICALFROM, PHYSICALTO)).
_ZOOMLESS_TYPE = (SOURCE_FOUR, {1: ("Dimmer", 0.0, 100.0)})
_ZOOM_TYPE = (MEGAPOINTE, {1: ("Dimmer", 0.0, 100.0), 2: ("Zoom", 42.0, 1.8)})


class _RigConsole:
    """룩 두 섹션 **과** 능력 판독 경로를 함께 답하는 가짜 포트.

    `test_looks_tool.py::_RigStatePort` 는 룩 섹션만 답하고, 형제
    `test_lxseq_preset_group_range.py::_FakeConsole` 은 능력 경로만 답한다. 이 카드가
    이은 배선은 **한 dispatch 안에서 둘 다** 일어나므로 하나로 합쳐야 한다. 섹션
    페이로드 모양은 사본을 만들지 않고 `test_looks_tool` 의 `_payload`/`_child` 를
    그대로 쓴다.

    세 읽기를 **센다** — 왕복 예산이 이 카드의 산출물 하나라, 숫자를 문장이 아니라
    값으로 남긴다.
    """

    def __init__(
        self,
        *,
        types: dict[int, tuple[str, dict[int, tuple[str, float, float]]]],
        fixtures: dict[int, tuple[int, int | None]],
        groups: tuple[tuple[int | None, str], ...] = DEFAULT_GROUPS,
        pools: tuple[tuple[int | None, str], ...] = DEFAULT_POOLS,
        contents: dict[int, list[dict]] | None = None,
        answer_capability_paths: bool = True,
    ) -> None:
        self._types = types
        self._fixtures = fixtures
        self._answer = answer_capability_paths
        contents = contents or {}
        self._sections = {
            GROUPS_PATH: _payload(GROUPS_PATH, [_child(n, name) for n, name in groups]),
            POOLS_PATH: _payload(POOLS_PATH, [_child(n, name) for n, name in pools]),
        }
        for no, _name in pools:
            if no is None:
                continue
            path = f"{POOLS_PATH}/{no}"
            self._sections[path] = _payload(path, contents.get(no, []))
        self.calls = {"query_state": 0, "query_property": 0, "query_properties": 0}
        self.queried: list[str] = []

    # -- 왕복 계기 -----------------------------------------------------------

    @property
    def round_trips(self) -> int:
        return sum(self.calls.values())

    @property
    def capability_round_trips(self) -> int:
        """룩 섹션 판독을 뺀 왕복 — 이 카드가 **더한** 비용."""
        return self.round_trips - len([p for p in self.queried if p in self._sections])

    # -- 세 읽기 -------------------------------------------------------------

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls["query_state"] += 1
        self.queried.append(path)
        if path in self._sections:
            return self._sections[path]
        if not self._answer:
            return dict(ok=False)
        parts = path.split("/")
        if path == TYPES_ROOT:
            children = [dict(i=slot, name=name) for slot, (name, _) in self._types.items()]
            return dict(ok=True, node=dict(childCount=len(children)), children=children)
        if path == FIXTURE_ROOT:
            children = [dict(i=slot, name="fixture " + str(slot)) for slot in self._fixtures]
            return dict(ok=True, node=dict(childCount=len(children)), children=children)
        if len(parts) >= 4 and parts[3] == "DMXModes":
            type_slot = int(parts[2])
            if type_slot not in self._types:
                return dict(ok=False)
            channels = self._types[type_slot][1]
            if len(parts) == 4:
                return dict(ok=True, children=[dict(i=1, name="Mode 1")])
            if len(parts) == 6 and parts[5] == "DMXChannels":
                return dict(
                    ok=True,
                    children=[
                        dict(i=slot, name="Main Module_" + spec[0])
                        for slot, spec in channels.items()
                    ],
                )
            if len(parts) == 7:
                spec = channels.get(int(parts[6]))
                if spec is None:
                    return dict(ok=True, children=[])
                return dict(ok=True, children=[dict(i=1, name=spec[0])])
            if len(parts) == 8:
                return dict(ok=True, children=[dict(i=1, name=channels[int(parts[6])][0] + " 1")])
        return dict(ok=False)

    def query_property(self, path: str, name: str) -> dict:
        self.calls["query_property"] += 1
        if not self._answer:
            return dict(ok=False)
        if path.startswith(FIXTURE_ROOT) and name == "FID":
            entry = self._fixtures.get(int(path.split("/")[-1]))
            if entry is None or entry[1] is None:
                return dict(ok=False)
            return dict(ok=True, value=str(entry[1]))
        return dict(ok=True, value="32")

    def query_properties(self, path: str, property_names) -> dict:
        self.calls["query_properties"] += 1
        if not self._answer:
            return dict(ok=False)
        parts = path.split("/")
        if path.startswith(FIXTURE_ROOT):
            slot = int(parts[-1])
            type_slot = self._fixtures[slot][0]
            values = {
                "Patch": "1.001",
                "FixtureType": "FixtureType " + str(type_slot),
                "Mode": "1 Mode 1",
                "Name": "fixture " + str(slot),
            }
            return dict(
                ok=True,
                reads=[dict(n=name, ok=True, v=values.get(name, "")) for name in property_names],
            )
        attribute, physical_from, physical_to = self._types[int(parts[2])][1][int(parts[6])]
        values = {
            "ATTRIBUTE": attribute,
            "DMXFROM": "0",
            "DMXTO": "255",
            "PHYSICALFROM": str(physical_from),
            "PHYSICALTO": str(physical_to),
            "DEFAULT": "0",
        }
        return dict(ok=True, reads=[dict(n=key, ok=True, v=value) for key, value in values.items()])


class _DeadConsole:
    """룩 섹션만 답하고 능력 경로에서는 예외를 던지는 포트.

    「콘솔이 안 답한다」와 「장비가 그 축을 못 낸다」를 가르는 대조군이다. 예외를
    던지는 형태를 쓰는 이유는 프로덕션 포트가 그렇게 실패하기 때문이다
    (`server.safety` 의 `StateQueryError`).
    """

    def __init__(self) -> None:
        self._inner = _RigConsole(types={}, fixtures={})
        self.queried: list[str] = []

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.queried.append(path)
        if path in self._inner._sections:
            return self._inner._sections[path]
        raise RuntimeError("state query failed: " + path)

    def query_property(self, path: str, name: str) -> dict:
        raise RuntimeError("property query failed: " + path)

    def query_properties(self, path: str, property_names) -> dict:
        raise RuntimeError("properties query failed: " + path)


# ── dispatch ────────────────────────────────────────────────────────────────


def _dispatch(state, *, look_id: str = LOOK_ID, execution=None, library=None):
    """기본값은 **정본 라이브러리**다 — `look_library` 를 넘기지 않으면 배포되는
    라이브러리가 로드되므로, 이 카드가 이은 경로가 실제 데이터에 닿는다."""
    port = execution or _RecordingPort()
    kwargs = {} if library is None else {"look_library": library}
    registry = build_toolset(execution_port=port, state_port=state, property_port=state, **kwargs)
    execution_result = registry.dispatch(
        ToolCall(id="t350", name=TOOL, arguments={"look_id": look_id})
    )
    return json.loads(execution_result.result.content), port


def _rig(*, zoom: bool, extra: dict[int, tuple[int, int | None]] | None = None) -> _RigConsole:
    """줌 있는 리그 / 없는 리그. 장비 수·기종 수는 같게 두어 축만 갈린다."""
    types = {11: _ZOOM_TYPE if zoom else _ZOOMLESS_TYPE}
    fixtures: dict[int, tuple[int, int | None]] = {slot: (11, 500 + slot) for slot in range(1, 5)}
    fixtures.update(extra or {})
    return _RigConsole(types=types, fixtures=fixtures)


def _skipped(payload: dict, family: str) -> dict | None:
    hits = [s for s in payload["report"]["skipped"] if s["family"] == family]
    assert len(hits) <= 1, hits
    return hits[0] if hits else None


def _families_created(payload: dict) -> set[str]:
    return {c["family"] for c in payload["report"]["created"]}


# ── 이 카드가 고치러 온 결함 ────────────────────────────────────────────────


class TestTheRungFiresThroughTheProductionPath:
    """🔴 판정기를 직접 넣어주는 시험은 여기서 **충분하지 않다.** t348 의 부품은
    이미 초록이었고 경로가 안 이어져 있었다. 그래서 모델이 들어오는 자리로 들어간다.
    """

    def test_a_real_zoom_look_on_a_zoomless_rig_is_held_by_the_axis_rung(self):
        payload, _port = _dispatch(_rig(zoom=False))
        hold = _skipped(payload, "Focus")
        assert hold is not None, payload["report"]["skipped"]
        # 사유 문자열을 단언한다 — 「건너뜀」만 보면 이 보류와 NO_FREE_SLOT·CONFLICT
        # 를 구별할 수 없고 그 셋은 고칠 곳이 서로 다르다.
        assert hold["reason"] == AXIS_ABSENT
        assert hold["reason"] not in (NO_FREE_SLOT, CONFLICT)

    def test_the_detail_names_the_attribute_that_drove_the_hold(self):
        payload, _port = _dispatch(_rig(zoom=False))
        assert "Zoom" in _skipped(payload, "Focus")["detail"]

    def test_the_hold_does_not_swallow_the_families_the_rig_can_do(self):
        payload, _port = _dispatch(_rig(zoom=False))
        assert {"Dimmer", "Color"} <= _families_created(payload)
        assert "Focus" not in _families_created(payload)
        assert payload["report"]["complete"] is False

    def test_no_store_command_for_the_held_family_reaches_the_execution_port(self):
        payload, port = _dispatch(_rig(zoom=False))
        stores = [c for c in port.executed if c.startswith("Store Preset")]
        focus_pool = next(no for no, name in DEFAULT_POOLS if name == "Focus")
        assert stores, "저장이 하나도 안 나가면 아래 부재 단언이 공허하다"
        assert all(not c.startswith(f"Store Preset {focus_pool}.") for c in stores)

    def test_the_payload_says_the_comparison_actually_ran(self):
        payload, _port = _dispatch(_rig(zoom=False))
        capability = payload["capability"]
        assert capability["ok"] is True
        assert capability["gap"] is None
        assert capability["fixtures_read"] == 4
        assert capability["types_read"] == [SOURCE_FOUR]
        assert capability["judged"] == list(MEASURED_ATTRIBUTE_SPELLINGS)

    def test_the_capability_clause_is_on_the_empty_bundle_branch_too(self):
        """전부 보류되면 payload 모양이 갈린다 — 가장 중요한 경우(전부 보류)가 왜
        그랬는지 못 말하면 안 된다.

        정본 룩으로는 이 갈래에 **닿을 수 없다.** `Color` family 의 `ColorRGB_*` 는
        철자가 미측정이라 절대 보류되지 않고(`MEASURED_ATTRIBUTE_SPELLINGS`), 그래서
        `edm-build-magenta` 는 언제나 명령을 하나는 낸다. 판정 대상 둘만 나르는
        룩을 구성해야 이 갈래가 열린다 — 구성된 대조군이고, 배포되는 룩이 아니다.
        """
        judged_only = _look(attributes=(("Dimmer", 72), ("Zoom", 35)))
        state = _RigConsole(
            types={11: ("Pan Only Control", {1: ("Pan", -270.0, 270.0)})},
            fixtures={1: (11, 501)},
        )
        payload, port = _dispatch(state, look_id=judged_only.look_id, library=_library(judged_only))
        assert payload["executed"] is False
        assert port.executed == []
        assert payload["capability"]["ok"] is True
        # 두 family 다 축 부재로 보류 — 그래서 명령이 없다. 사유가 이것이 아니면
        # 「빈 번들」이 「역할을 못 붙였다」와 구별되지 않는다.
        assert {s["reason"] for s in payload["report"]["skipped"]} == {AXIS_ABSENT}
        assert {s["family"] for s in payload["report"]["skipped"]} == {"Dimmer", "Focus"}


class TestControlProbes:
    """대조군 — 이것들이 없으면 위 보류가 다른 사유가 우연히 낸 것과 구별되지 않는다."""

    def test_the_same_look_on_a_rig_that_has_zoom_stores_the_focus_preset(self):
        payload, _port = _dispatch(_rig(zoom=True))
        assert _skipped(payload, "Focus") is None, payload["report"]["skipped"]
        assert "Focus" in _families_created(payload)
        # 보류가 **하나도** 없다 — 이 리그에서 갈리는 것은 축뿐이다.
        assert payload["report"]["skipped"] == []
        assert payload["capability"]["types_read"] == [MEGAPOINTE]

    def test_complete_is_false_for_a_reason_that_is_not_the_axis_rung(self):
        """비공허성 — 위 시험이 `complete` 를 안 재는 이유를 값으로 남긴다.

        이 룩은 역할이 셋(`백라이트` · `사이드` · `탑`)이고 대조군 리그에는 그룹이
        하나뿐이라 둘은 `unmapped` 다. 그것이 `complete=False` 를 만들며 축 보류와
        **다른 사실**이다 — 둘을 섞으면 축 배선을 지워도 `complete` 는 그대로 거짓이라
        회귀가 안 보인다.
        """
        payload, _port = _dispatch(_rig(zoom=True))
        assert payload["report"]["complete"] is False
        assert payload["report"]["skipped"] == []
        assert {u["role"] for u in payload["report"]["unmapped"]} == {"사이드", "탑"}

    def test_an_unreadable_console_does_not_hold_anything(self):
        """부재를 성공으로 읽히게 하지 않는 쪽의 거울상: **판독 실패를 부재로 읽지
        않는다.** 콘솔이 안 닿는다고 되던 저장이 멈추면 안 된다."""
        payload, _port = _dispatch(_DeadConsole())
        assert AXIS_ABSENT not in {s["reason"] for s in payload["report"]["skipped"]}
        assert "Focus" in _families_created(payload)
        assert payload["capability"]["ok"] is False
        assert payload["capability"]["gap"] == "rig_unreadable"
        assert payload["capability"]["fixtures_read"] == 0

    def test_a_partial_read_does_not_claim_absence(self):
        """🔴 이 게이트가 `RigAxisPresence` 가 아니라 **배선 쪽**에 있는 이유.

        판정기는 `RigCapabilities` 만 받으므로 인벤토리 절단을 못 본다. 잘린 목록에
        Zoom 장비가 없다는 것은 부재의 증거가 아니다 — FID 를 못 읽은 슬롯 하나로
        그 상태를 만든다.
        """
        state = _rig(zoom=False, extra={9: (11, None)})
        payload, _port = _dispatch(state)
        assert payload["capability"]["ok"] is False
        assert payload["capability"]["gap"] == "fid_partial"
        # 판독 자체는 4대를 데려왔다 — 「아무것도 못 읽었다」가 아니라 「부분이다」.
        assert payload["capability"]["fixtures_read"] == 4
        assert AXIS_ABSENT not in {s["reason"] for s in payload["report"]["skipped"]}
        assert "Focus" in _families_created(payload)

    def test_the_whole_read_and_the_partial_read_differ_only_in_that_one_slot(self):
        """비공허성 — 위 두 시험의 갈림이 슬롯 하나라는 것. 다른 것이 갈렸으면
        「부분 판독이 보류를 막았다」는 결론이 안 선다."""
        whole, _ = _dispatch(_rig(zoom=False))
        partial, _ = _dispatch(_rig(zoom=False, extra={9: (11, None)}))
        assert whole["capability"]["fixtures_read"] == partial["capability"]["fixtures_read"]
        assert whole["capability"]["ok"] is not partial["capability"]["ok"]


class TestTheLookSectionsAreStillReadFirst:
    def test_the_capability_read_does_not_get_in_front_of_the_two_sections(self):
        """형제 게이트가 `queried[:2]` 를 재고 있다 — 능력 판독을 앞에 두면 그쪽이
        빨개진다. 그 순서 요구를 여기서도 값으로 고정한다."""
        state = _rig(zoom=False)
        _dispatch(state)
        assert state.queried[:2] == [GROUPS_PATH, POOLS_PATH]


# ── 왕복 예산 ───────────────────────────────────────────────────────────────


class TestRoundTripBudget:
    """이 배선이 저장 한 번마다 더하는 콘솔 왕복 — 감독의 결정 재료.

    🔴 아래 숫자는 **구성된 대조군**이다. 실기 콘솔 실측이 아니고, 형태가 같은 가짜
    포트에서 센 값이다. 여기 두는 이유는 「비싸다/싸다」를 문장으로 남기면 다음 카드가
    다시 재야 하기 때문이다 — 배선이 왕복 수를 바꾸면 이 시험이 그 사실을 알린다.
    """

    #: 실측한 닫힌 식 — 세 축(장비 · (기종,모드) 쌍 · 채널)을 따로 스윕해 46개 점에서
    #: 검산했고 안 맞는 점은 **0** 이다
    #: (`.moai/reports/t350/verify_formula.py`, 출력은 나란한 `.out.txt`).
    #:
    #: 🔴 채널 항이 지배한다 — 이 자리에서 한 번 틀렸다. 1차 계기
    #: (`measure_types.py`)는 채널 2개짜리 기종을 복제해 기종 수만 늘렸으므로
    #: 「기종 1종당 10 왕복」을 냈고, 그 10 은 기종 항 4 와 채널 항 3x2 가 **섞인**
    #: 값이었다. 정본 리그의 Spiider Mode 1 은 49ch 라, 그 혼합식을 그대로 쓰면
    #: 추정이 255 로 나오고 실제는 **669** 다(2.6배 과소). 항을 가르지 않은 회귀식은
    #: 재본 범위 밖에서 조용히 틀린다.
    @staticmethod
    def _predicted(fixtures: int, channels_per_type: list[int]) -> int:
        return 2 * fixtures + 4 * len(channels_per_type) + 3 * sum(channels_per_type) + 3

    def test_the_added_cost_matches_the_measured_formula(self):
        state = _rig(zoom=True)
        _dispatch(state)
        # `_ZOOM_TYPE` 은 채널 둘(Dimmer · Zoom), 장비 넷.
        assert state.capability_round_trips == self._predicted(4, [2])

    def test_the_cost_grows_with_the_fixture_count_not_with_the_look(self):
        """두 배 리그가 장비 항만큼 더 내는 것 — 이 판독이 **리그 전수**임을 값으로
        확인한다. 룩은 그대로다."""
        small = _RigConsole(
            types={11: _ZOOM_TYPE}, fixtures={s: (11, 500 + s) for s in range(1, 5)}
        )
        large = _RigConsole(
            types={11: _ZOOM_TYPE}, fixtures={s: (11, 500 + s) for s in range(1, 9)}
        )
        _dispatch(small)
        _dispatch(large)
        assert small.capability_round_trips == self._predicted(4, [2])
        assert large.capability_round_trips == self._predicted(8, [2])
        assert large.capability_round_trips - small.capability_round_trips == 8

    def test_the_channel_count_dominates_the_cost_not_the_type_count(self):
        """🔴 이 카드가 여기서 한 번 틀렸다 — 항을 갈라서 값으로 못박는다.

        기종을 하나 더하면 4 왕복이고, 채널을 하나 더하면 3 왕복이다. 채널 39개짜리
        기종 하나가 채널 2개짜리 기종 여덟보다 비싸다는 것이 정본 리그 추정을 지배한다.
        """
        many_thin_types = _RigConsole(
            types={
                slot: (f"Thin {slot}", {1: ("Dimmer", 0.0, 100.0), 2: ("Zoom", 42.0, 1.8)})
                for slot in range(11, 19)
            },
            fixtures={s: (11 + (s - 1) % 8, 500 + s) for s in range(1, 9)},
        )
        one_fat_type = _RigConsole(
            types={11: ("Fat", {c: (f"Attr{c}", 0.0, 100.0) for c in range(1, 40)})},
            fixtures={s: (11, 500 + s) for s in range(1, 9)},
        )
        _dispatch(many_thin_types)
        _dispatch(one_fat_type)
        assert many_thin_types.capability_round_trips == self._predicted(8, [2] * 8)
        assert one_fat_type.capability_round_trips == self._predicted(8, [39])
        # 기종 8종·채널 16 < 기종 1종·채널 39 — 채널 항이 이긴다.
        assert one_fat_type.capability_round_trips > many_thin_types.capability_round_trips

    def test_an_unreferenced_library_type_costs_nothing(self):
        """🔴 기종·채널 항은 **참조된** 것만 센다 — 라이브러리 크기가 아니다.

        정본 콘솔 라이브러리는 15종인데 패치된 것은 8쌍이다. 라이브러리 크기로 곱하면
        재보지도 않은 7종의 채널까지 예산에 실린다. 라이브러리에만 있는 기종을 하나
        더해도 값이 안 오르는 것을 값으로 재서 그 갈림을 고정한다.
        """
        referenced_only = _RigConsole(
            types={11: _ZOOM_TYPE},
            fixtures={s: (11, 500 + s) for s in range(1, 5)},
        )
        with_spare_library_type = _RigConsole(
            # 슬롯 12 는 라이브러리에만 있다 — 어느 장비도 참조하지 않는다.
            types={11: _ZOOM_TYPE, 12: _ZOOMLESS_TYPE},
            fixtures={s: (11, 500 + s) for s in range(1, 5)},
        )
        _dispatch(referenced_only)
        _dispatch(with_spare_library_type)
        assert with_spare_library_type.capability_round_trips == self._predicted(4, [2])
        assert (
            with_spare_library_type.capability_round_trips == referenced_only.capability_round_trips
        )

    def test_the_canonical_rig_shape_costs_what_the_formula_says(self):
        """정본 리그 모양의 예산 — 감독이 읽는 숫자를 값으로 고정한다.

        장비 86 · (기종,모드) 8쌍 · 채널 합 154 는 정본 패치 시트 실측이다
        (`src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv`,
        `cut -d, -f3,4,5 | sort | uniq -c` 전수). 🔴 다만 **채널 수는 시트가 선언한
        값**이고 콘솔 라이브러리가 답하는 값은 안 쟀다 — 판독은 콘솔에서 오므로 이
        숫자는 시트 기준 추정이다. 그 갈림이 있으면 실제 값이 이보다 크거나 작다.
        """
        canonical = [25, 9, 12, 49, 39, 4, 14, 2]
        assert sum(canonical) == 154
        assert self._predicted(86, canonical) == 669
        # 쌍당 상한(`read_rig_capabilities(budget=256)`)은 가장 비싼 쌍도 안 넘긴다 —
        # 넘기면 판독이 잘리고 `whole` 이 거짓이 되어 이 rung 이 아예 안 걸린다.
        assert 3 * max(canonical) < 256

    def test_a_second_dispatch_pays_it_again(self):
        """🔴 캐시가 **없다**는 것을 값으로 남긴다. 캐시를 넣으면 이 시험이
        빨개지고, 그때 낡은 값의 방향(거짓 부재)을 함께 판단하게 된다."""
        state = _rig(zoom=True)
        _dispatch(state)
        first = state.capability_round_trips
        _dispatch(state)
        assert state.capability_round_trips == 2 * first

    def test_the_look_sections_are_a_small_part_of_the_total(self):
        """비공허성 — 위 `capability_round_trips` 가 전체에서 뺀 것이 실제로 있다."""
        state = _rig(zoom=True)
        _dispatch(state)
        assert 0 < state.round_trips - state.capability_round_trips < state.round_trips

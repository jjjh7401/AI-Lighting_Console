"""`server.design.capability_join` — fid 를 타입·모드·조정 가능한 축으로 조인한다.

가짜 포트만 쓴다. **콘솔에 한 바이트도 안 보낸다** — 쓰기는 물론 읽기도 없다.

고정값의 출처는 실측이다(2026-09-10, onPC / 응답기 1.6.5, 읽기 전용):

* FixtureType 11 = Robin MegaPointe, Mode 1, DMXChannels 32개
* ``Zoom`` PHYSICALFROM=42.0 PHYSICALTO=1.8 — **역방향**
* ``Frost1`` 0.0 -> 1.0 (정규화; Zoom 은 도(degree) — 단위가 축마다 다르다)
* 리그 15기종 중 9기종에 Pan/Tilt 가 있고 4기종에 없다(Source 4 · CuePix Blinder ·
  Atomic 3000 · Rush Par 2). ``Prism`` 은 15기종 전부에 없다.
"""

from __future__ import annotations

from server.design.capability_join import (
    UNREAD_TYPE_SLOT_UNKNOWN,
    FixtureTypeRef,
    read_rig_capabilities,
)
from server.prechk.capability_read import CHANNEL_FUNCTION_PROPERTIES

_ROOT = "Patch/FixtureTypes"

#: 속성 이름 -> (PHYSICALFROM, PHYSICALTO). 실측 두 건(Zoom·Frost1)과 그 밖의 축.
_RANGES = {
    "Pan": ("-270.0", "270.0"),
    "Tilt": ("-125.0", "125.0"),
    "Zoom": ("42.0", "1.8"),
    "Frost1": ("0.0", "1.0"),
    "Dimmer": ("0.0", "1.0"),
}

#: 타입 슬롯 -> (타입 이름, 채널 슬롯 -> 속성 이름).
#: Source 4 는 팬틸트가 없는 고정 장비다 — 그래서 축이 Dimmer 하나뿐이다.
_TYPES = {
    11: ("Robin MegaPointe", {1: "Pan", 2: "Tilt", 3: "Zoom", 4: "Frost1"}),
    5: ("Source 4", {1: "Dimmer"}),
}

_TYPE_NAMES = {slot: name for slot, (name, _) in _TYPES.items()}


class _FakeConsole:
    """실측한 트리 모양만 흉내내는 가짜 포트.

    ``truncate_type`` 에 타입 슬롯을 주면 그 타입의 ``DMXChannels`` 가 childCount 를
    실제보다 크게 선언하고 다음 페이지에 답하지 않는다 — 실측한 절단(선언 32, 응답
    15)을 재현한다.
    """

    def __init__(self, *, truncate_type: int | None = None) -> None:
        self.truncate_type = truncate_type
        self.state_calls: list[str] = []
        self.prop_calls: list[tuple[str, str]] = []
        self.props_calls: list[str] = []

    # ── query_state: 열거 ──────────────────────────────────────────────
    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.state_calls.append(path if offset == 0 else f"{path}#offset={offset}")
        parts = path.split("/")

        if path == _ROOT:  # 타입 라이브러리
            return {
                "ok": True,
                "children": [{"i": slot, "name": name} for slot, name in _TYPE_NAMES.items()],
            }

        # Patch/FixtureTypes/<타입>/DMXModes...
        if len(parts) >= 4 and parts[3] == "DMXModes":
            type_slot = int(parts[2])
            if type_slot not in _TYPES:
                return {"ok": False}
            channels = _TYPES[type_slot][1]
            if len(parts) == 4:  # 모드 목록
                return {"ok": True, "children": [{"i": 1, "name": "Mode 1"}]}
            if len(parts) == 6 and parts[5] == "DMXChannels":  # 채널 목록
                payload: dict = {
                    "ok": True,
                    "children": [
                        {"i": slot, "name": f"Main Module_{attr}"}
                        for slot, attr in channels.items()
                    ],
                }
                if type_slot == self.truncate_type:
                    if offset:  # 다음 페이지에 답하지 않는다 = 절단
                        return {"ok": False}
                    payload["node"] = {"childCount": len(channels) + 2}
                return payload
            if len(parts) == 7:  # 채널 -> 논리채널 목록
                attr = channels.get(int(parts[6]))
                if attr is None:
                    return {"ok": True, "children": []}
                return {"ok": True, "children": [{"i": 1, "name": attr}]}
            if len(parts) == 8:  # 논리채널 -> 채널함수 목록
                attr = channels[int(parts[6])]
                return {"ok": True, "children": [{"i": 1, "name": f"{attr} 1"}]}
        return {"ok": False}

    # ── query_property: mode_read 가 폭을 읽는 통로 ─────────────────────
    def query_property(self, path: str, name: str) -> dict:
        self.prop_calls.append((path, name))
        return {"ok": True, "value": "32"}

    # ── query_properties: capability_read 가 범위를 읽는 통로 ───────────
    def query_properties(self, path: str, property_names) -> dict:
        self.props_calls.append(path)
        parts = path.split("/")
        attr = _TYPES[int(parts[2])][1][int(parts[6])]
        physical_from, physical_to = _RANGES[attr]
        values = {
            "ATTRIBUTE": attr,
            "DMXFROM": "0",
            "DMXTO": "16777216",
            "PHYSICALFROM": physical_from,
            "PHYSICALTO": physical_to,
            "DEFAULT": "0",
        }
        return {
            "ok": True,
            "reads": [
                {"n": key, "ok": True, "v": values[key]} for key in CHANNEL_FUNCTION_PROPERTIES
            ],
        }


def _join(fixtures, **kwargs):
    console = _FakeConsole(**kwargs)
    result = read_rig_capabilities(
        console,
        console,
        root=_ROOT,
        fixtures=fixtures,
        type_names=_TYPE_NAMES,
    )
    return console, result


def _ref(fid: int, type_slot: int) -> FixtureTypeRef:
    return FixtureTypeRef(fid=fid, type_raw=f"FixtureType {type_slot}", mode_raw="1 Mode 1")


class TestMeasuredShape:
    def test_a_moving_head_carries_its_type_and_mode(self):
        _, result = _join([_ref(1, 11)])
        cap = result.fixtures[1]
        assert cap.type_name == "Robin MegaPointe"
        assert cap.type_slot == 11
        assert cap.mode_slot == 1
        assert cap.mode_name == "Mode 1"
        assert cap.mode_width == 32
        assert cap.whole

    def test_attribute_spellings_come_through_verbatim(self):
        """콘솔 철자 그대로 — 이름을 바꾸는 것은 t344 B 의 몫이다."""
        _, result = _join([_ref(1, 11)])
        assert result.fixtures[1].attributes == ("Frost1", "Pan", "Tilt", "Zoom")

    def test_a_reversed_zoom_range_keeps_its_direction(self):
        """🔴 Zoom 은 42.0 -> 1.8 이다. 정렬하는 회귀가 들어오면 여기가 빨개진다."""
        _, result = _join([_ref(1, 11)])
        zoom = result.fixtures[1].axis("Zoom")
        assert zoom is not None
        assert zoom.physical_from == 42.0
        assert zoom.physical_to == 1.8
        assert zoom.descending is True

    def test_frost_is_normalised_not_a_percentage(self):
        """단위는 축마다 다르다 — Frost 는 0~1, Zoom 은 도. 퍼센트는 어디에도 없다."""
        _, result = _join([_ref(1, 11)])
        frost = result.fixtures[1].axis("Frost1")
        assert frost is not None
        assert (frost.physical_from, frost.physical_to) == (0.0, 1.0)
        assert frost.descending is False


class TestPanTiltScope:
    def test_a_fixed_fixture_has_neither_pan_nor_tilt(self):
        """Source 4 는 고정 장비다 — 포지션 프리셋을 줄 수 없는 쪽."""
        _, result = _join([_ref(7, 5)])
        cap = result.fixtures[7]
        assert cap.attributes == ("Dimmer",)
        assert not cap.has_attribute("Pan")
        assert not cap.has_attribute("Tilt")

    def test_a_moving_head_has_both_pan_and_tilt(self):
        """대조군. 이게 없으면 위 검사는 「아무것도 안 돌려주는 조인」도 통과한다."""
        _, result = _join([_ref(1, 11)])
        cap = result.fixtures[1]
        assert cap.has_attribute("Pan")
        assert cap.has_attribute("Tilt")

    def test_prism_is_absent_on_both_measured_types(self):
        """실측: 15기종 전부에 Prism 이 없다. 부재는 목록에 없음으로 나타난다."""
        _, result = _join([_ref(1, 11), _ref(7, 5)])
        assert not result.fixtures[1].has_attribute("Prism")
        assert not result.fixtures[7].has_attribute("Prism")


class TestUnreadIsNotAbsence:
    def test_a_truncated_read_is_reported_as_unread_with_a_reason(self):
        """🔴 절단은 부재가 아니다 — 사유 문자열까지 단언한다.

        「비어서 왔다」만 보는 검사는 진짜 부재와 실패한 판독을 못 가른다.
        """
        _, result = _join([_ref(1, 11)], truncate_type=11)
        cap = result.fixtures[1]
        assert cap.whole is False
        reason = result.incomplete[1]
        assert "잘렸다" in reason
        assert "DMXChannels" in reason
        # 읽힌 축은 그대로 살아 있다 — 절단이 판독 전체를 버리지 않는다.
        assert cap.has_attribute("Zoom")

    def test_a_name_shaped_type_reading_has_no_slot(self):
        """핸들이 아니면 슬롯을 모른다 — 추측하지 않고 사유를 남긴다."""
        _, result = _join([FixtureTypeRef(fid=9, type_raw="Robin MegaPointe", mode_raw="1 Mode 1")])
        assert 9 not in result.fixtures
        assert result.unread[9] == UNREAD_TYPE_SLOT_UNKNOWN

    def test_an_unparsable_mode_reading_is_unread(self):
        _, result = _join([FixtureTypeRef(fid=9, type_raw="FixtureType 11", mode_raw=None)])
        assert 9 not in result.fixtures
        assert 9 in result.unread


class TestRoundTripBudget:
    def test_two_fids_of_one_type_cause_one_mode_read(self):
        """같은 (타입, 모드)를 fid 마다 다시 읽는 것은 순수한 낭비다."""
        console, result = _join([_ref(1, 11), _ref(2, 11)])
        assert set(result.fixtures) == {1, 2}
        assert result.mode_reads == 1
        assert result.capability_reads == 1
        # 가짜 포트 호출 수로 검산 — 세는 계기가 결과와 독립이어야 한다.
        assert console.state_calls.count(f"{_ROOT}/11/DMXModes") == 1
        assert console.state_calls.count(f"{_ROOT}/11/DMXModes/1/DMXChannels") == 1
        assert len(console.props_calls) == len(set(console.props_calls))

    def test_two_types_cause_two_reads_each(self):
        console, result = _join([_ref(1, 11), _ref(2, 11), _ref(7, 5)])
        assert result.mode_reads == 2
        assert result.capability_reads == 2
        assert result.round_trips == 4
        assert console.state_calls.count(f"{_ROOT}/5/DMXModes/1/DMXChannels") == 1

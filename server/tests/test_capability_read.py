"""`server.prechk.capability_read` — 장비가 무엇을 조정할 수 있는지 읽는다.

고정 케이스는 **실측**이다(2026-09-10, onPC / 응답기 1.6.5, 읽기 전용, 콘솔 쓰기 0):
Patch/FixtureTypes/11 = Robin MegaPointe, Mode 1, DMXChannels 32개 중

    채널 27  Main Module_Frost1  -> LogicalChannel Frost1 -> 'Frost1 1'
             ATTRIBUTE=Frost1  DMXFROM=0  DMXTO=3487029
             PHYSICALFROM=0.0  PHYSICALTO=1.0  DEFAULT=0
    채널 28  Main Module_Zoom    -> LogicalChannel Zoom   -> 'Zoom 1'
             ATTRIBUTE=Zoom    DMXFROM=0  DMXTO=16777216
             PHYSICALFROM=42.0 PHYSICALTO=1.8

Zoom 의 두 끝이 **역순**인 것이 이 파일의 핵심 고정값이다 — 정렬해서 저장하는 회귀가
들어오면 `test_a_descending_axis_keeps_its_direction` 이 빨개진다.
"""

from __future__ import annotations

import pytest

from server.prechk.capability_read import (
    CHANNEL_FUNCTION_PROPERTIES,
    AxisRange,
    read_mode_capabilities,
)

_ROOT = "Patch/FixtureTypes"

#: 실측 표본 — 채널 슬롯 -> (채널 이름, 논리채널 이름, 함수 프로퍼티)
_MEASURED = {
    27: (
        "Main Module_Frost1",
        "Frost1",
        {
            "ATTRIBUTE": "Frost1",
            "DMXFROM": "0",
            "DMXTO": "3487029",
            "PHYSICALFROM": "0.0",
            "PHYSICALTO": "1.0",
            "DEFAULT": "0",
        },
    ),
    28: (
        "Main Module_Zoom",
        "Zoom",
        {
            "ATTRIBUTE": "Zoom",
            "DMXFROM": "0",
            "DMXTO": "16777216",
            "PHYSICALFROM": "42.0",
            "PHYSICALTO": "1.8",
            "DEFAULT": "0",
        },
    ),
}


class _FakeConsole:
    """실측한 트리 모양만 흉내내는 가짜 — 콘솔에 한 바이트도 안 보낸다.

    `_MEASURED` 에 없는 채널은 논리채널이 0개인 것으로 답한다. 32채널 전량을 적는
    대신 표본 둘만 두는 이유는, 이 검사가 재려는 것이 「채널 32개를 다 읽는가」가
    아니라 **읽은 것을 어떤 모양으로 나르는가** 이기 때문이다.
    """

    def __init__(self, *, channels: int = 32, missing_range: bool = False) -> None:
        self.channels = channels
        self.missing_range = missing_range
        self.state_calls: list[str] = []
        self.prop_calls: list[tuple[str, str]] = []

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.state_calls.append(path if offset == 0 else f"{path}#offset={offset}")
        prefix = f"{_ROOT}/11/DMXModes/1/DMXChannels"
        if path == prefix:
            return {
                "ok": True,
                "children": [
                    {"i": slot, "name": _name_for(slot)} for slot in range(1, self.channels + 1)
                ],
            }
        if path.startswith(f"{prefix}/"):
            rest = path[len(prefix) + 1 :].split("/")
            slot = int(rest[0])
            if len(rest) == 1:  # 채널 -> 논리채널 목록
                if slot not in _MEASURED:
                    return {"ok": True, "children": []}
                return {"ok": True, "children": [{"i": 1, "name": _MEASURED[slot][1]}]}
            if len(rest) == 2:  # 논리채널 -> 채널함수 목록
                return {"ok": True, "children": [{"i": 1, "name": f"{_MEASURED[slot][1]} 1"}]}
        return {"ok": False}

    def query_properties(self, path: str, property_names) -> dict:
        self.prop_calls.append((path, tuple(property_names)))
        prefix = f"{_ROOT}/11/DMXModes/1/DMXChannels/"
        slot = int(path[len(prefix) :].split("/")[0])
        values = dict(_MEASURED[slot][2])
        if self.missing_range:
            values["PHYSICALFROM"] = None
            values["PHYSICALTO"] = None
        return {
            "ok": True,
            "reads": [
                {"n": name, "ok": values.get(name) is not None, "v": values.get(name)}
                for name in CHANNEL_FUNCTION_PROPERTIES
            ],
        }


def _name_for(slot: int) -> str:
    return _MEASURED[slot][0] if slot in _MEASURED else f"Main Module_Ch{slot}"


def _read(**kwargs):
    console = _FakeConsole(**kwargs)
    return console, read_mode_capabilities(console, console, root=_ROOT, type_slot=11, mode_slot=1)


class TestMeasuredShape:
    def test_the_two_measured_axes_come_back(self):
        _, caps = _read()
        assert caps.attempted and caps.mode_found
        assert caps.channel_count == 32
        assert caps.attributes == ("Frost1", "Zoom")

    def test_frost_carries_its_measured_range(self):
        _, caps = _read()
        frost = caps.axis("Frost1")
        assert frost == AxisRange(
            attribute="Frost1",
            channel_name="Main Module_Frost1",
            dmx_from=0,
            dmx_to=3487029,
            physical_from=0.0,
            physical_to=1.0,
            default=0.0,
        )

    def test_a_descending_axis_keeps_its_direction(self):
        """🔴 Zoom 은 42.0 -> 1.8 이다. 정렬하면 이 검사가 빨개진다.

        방향을 잃으면 어느 끝이 DMX 0 인지 모르게 되고, 그러면 「넓게」가 「좁게」로
        나간다 — 조용히 틀린 자리에 가는 실패다.
        """
        _, caps = _read()
        zoom = caps.axis("Zoom")
        assert zoom is not None
        assert (zoom.physical_from, zoom.physical_to) == (42.0, 1.8)
        assert zoom.descending is True
        assert caps.axis("Frost1").descending is False


class TestCapabilityQuestion:
    """연출이 실제로 묻는 질문 — 「이 장비로 이걸 할 수 있나」."""

    def test_an_absent_axis_answers_no(self):
        """팬틸트 없는 장비에 포지션 프리셋을 주지 않기 위한 그 판정이다."""
        _, caps = _read()
        assert caps.has_attribute("Pan") is False
        assert caps.has_attribute("Tilt") is False
        assert caps.axis("Pan") is None

    def test_a_present_axis_answers_yes_case_insensitively(self):
        _, caps = _read()
        assert caps.has_attribute("zoom") is True
        assert caps.has_attribute("  FROST1  ") is True

    def test_a_prefix_is_not_a_match(self):
        """`Zoom` 으로 물어 `ZoomMSpeed` 가 걸리면 안 된다 — 다른 축이다(t139 계열).

        실측 32채널에 `Main Module_ZoomMSpeed`(채널 12)가 실재한다. 접두 일치를 쓰면
        줌 각도를 물었는데 줌 이동 속도가 답한다.
        """
        console = _FakeConsole()
        _MEASURED[12] = (
            "Main Module_ZoomMSpeed",
            "ZoomMSpeed",
            {
                "ATTRIBUTE": "ZoomMSpeed",
                "DMXFROM": "0",
                "DMXTO": "255",
                "PHYSICALFROM": "0.0",
                "PHYSICALTO": "1.0",
                "DEFAULT": "0",
            },
        )
        try:
            caps = read_mode_capabilities(console, console, root=_ROOT, type_slot=11, mode_slot=1)
            assert caps.has_attribute("Zoom") is True
            assert caps.has_attribute("ZoomMSpeed") is True
            assert caps.axis("Zoom").attribute == "Zoom"
            assert caps.axis("Zoom").physical_from == 42.0
        finally:
            del _MEASURED[12]


class TestGapsAreNotDefaults:
    def test_an_unread_range_leaves_the_axis_unmeasurable(self):
        """못 읽은 범위를 0 으로 채우지 않는다 — 부재와 미판독은 다른 상태다."""
        _, caps = _read(missing_range=True)
        zoom = caps.axis("Zoom")
        assert zoom is not None
        assert zoom.physical_from is None and zoom.physical_to is None
        assert zoom.measurable is False
        assert zoom.descending is None

    def test_an_unreadable_channel_list_is_reported_not_silently_empty(self):
        class _Dead:
            def query_state(self, path: str, *, offset: int = 0) -> dict:
                return {"ok": False}

            def query_properties(self, path: str, property_names) -> dict:  # pragma: no cover
                raise AssertionError("채널 목록이 죽었으면 프로퍼티를 읽지 않는다")

        dead = _Dead()
        caps = read_mode_capabilities(dead, dead, root=_ROOT, type_slot=11, mode_slot=1)
        assert caps.attempted is True
        assert caps.mode_found is False
        assert caps.axes == ()
        assert "채널 목록을 읽지 못했다" in caps.detail

    def test_the_budget_stops_the_walk_and_says_so(self):
        """예산이 끊기면 잘렸다고 적는다 — 잘린 목록을 완전한 것처럼 주지 않는다."""
        console = _FakeConsole()
        caps = read_mode_capabilities(
            console, console, root=_ROOT, type_slot=11, mode_slot=1, budget=3
        )
        assert any("예산" in gap for gap in caps.gaps)
        assert len(console.state_calls) <= 3

    def test_a_raising_port_becomes_a_gap_not_a_crash(self):
        """프로덕션 포트는 판독 실패를 예외로 낸다 — 그것을 응답으로 접는다."""

        class _Raises:
            def __init__(self) -> None:
                self.inner = _FakeConsole()

            def query_state(self, path: str, *, offset: int = 0) -> dict:
                return self.inner.query_state(path, offset=offset)

            def query_properties(self, path: str, property_names) -> dict:
                raise TimeoutError(path)

        port = _Raises()
        caps = read_mode_capabilities(port, port, root=_ROOT, type_slot=11, mode_slot=1)
        assert caps.axes == ()
        assert any("TimeoutError" in gap for gap in caps.gaps)


class TestReadOnly:
    def test_only_the_two_read_verbs_are_used(self):
        """콘솔 쓰기 0 — 이 모듈은 읽기 두 개만 쓴다."""
        console, caps = _read()
        assert caps.axes  # 실제로 읽었다
        assert all(path.startswith(_ROOT) for path in console.state_calls)
        for _path, names in console.prop_calls:
            assert names == CHANNEL_FUNCTION_PROPERTIES


@pytest.mark.parametrize(
    ("attribute", "expected"),
    [("Frost1", False), ("Zoom", True)],
)
def test_direction_per_measured_axis(attribute: str, expected: bool):
    _, caps = _read()
    assert caps.axis(attribute).descending is expected

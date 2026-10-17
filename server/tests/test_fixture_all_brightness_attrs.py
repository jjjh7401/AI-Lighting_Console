"""기종의 밝기 계열 속성을 다 연다 — 감독 보고 「콘솔에서 일부 장비만 동작」(2026-10-17).

콘솔 기구 시트: MOVER-U(501~508)는 켜지고 MOVER-D(521~, Robin Spiider)는 Dim 은 같은 디머
프리셋 값인데 Dim2 = 「closed」라 빛이 안 나왔다. 계획 카드의 디머 줄은
``Group 3 + 10 + 4 + 7 + 11 + 12 + 14 + 15 ; Attribute 'Dimmer' At 100`` 하나뿐이었다.

원인(기존 판독, `.moai/reports/t520/dim2_readonly.txt`): Spiider ch26
``Main Module_Dimmer2`` 의 **LogicalChannel** 이름·ATTRIBUTE 는 ``Dimmer2`` 인데, 그 아래
**ChannelFunction** 의 ATTRIBUTE 는 ``Dimmer`` 다. 명령이 받는 이름은 LogicalChannel 쪽이다
(``Group 12 ; Attribute 'Dimmer2' At 70`` 로 켜짐 — t548 v0b·t520 §18-1). 능력 판독이
ChannelFunction 쪽 이름을 먼저 써서 Spiider 의 속성 목록에 ``Dimmer2`` 가 없었고, 디머 계획은
MOVER-D 를 ``Dimmer`` 하나로 골랐다.
"""

from __future__ import annotations

from server.design.preset_plan import save_commands
from server.prechk.capability_read import CHANNEL_FUNCTION_PROPERTIES, read_mode_capabilities

from .test_preset_plan import _ATTRIBUTES, _plan

_ROOT = "Patch/FixtureTypes"
_CHANNELS = f"{_ROOT}/4/DMXModes/1/DMXChannels"

#: 판독 표본(t520 dim2_readonly · t238 채널 목록) — 채널 슬롯 -> (채널, 논리채널, 함수 ATTRIBUTE)
_SPIIDER = {
    24: ("Main Module_Dimmer", "Dimmer", "Dimmer"),
    26: ("Main Module_Dimmer2", "Dimmer2", "Dimmer"),
}


class _SpiiderConsole:
    """Spiider 모드 1 의 디머 두 채널만 흉내낸다 — 콘솔에 한 바이트도 안 보낸다."""

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        if path == _CHANNELS:
            return {
                "ok": True,
                "children": [
                    {"i": slot, "name": name} for slot, (name, _l, _a) in _SPIIDER.items()
                ],
            }
        rest = path[len(_CHANNELS) + 1 :].split("/")
        slot = int(rest[0])
        if len(rest) == 1:
            return {"ok": True, "children": [{"i": 1, "name": _SPIIDER[slot][1]}]}
        if len(rest) == 2:
            return {"ok": True, "children": [{"i": 1, "name": "Dimmer 1"}]}
        return {"ok": False}

    def query_properties(self, path: str, property_names) -> dict:
        slot = int(path[len(_CHANNELS) + 1 :].split("/")[0])
        values = {
            "ATTRIBUTE": _SPIIDER[slot][2],
            "DMXFROM": "0",
            "DMXTO": "16777216",
            "PHYSICALFROM": "0.0",
            "PHYSICALTO": "1.0",
            "DEFAULT": "0",
        }
        return {
            "ok": True,
            "reads": [
                {"n": name, "ok": True, "v": values[name]} for name in CHANNEL_FUNCTION_PROPERTIES
            ],
        }


def test_the_second_dimmer_is_read_under_its_logical_channel_name() -> None:
    console = _SpiiderConsole()
    read = read_mode_capabilities(console, console, root=_ROOT, type_slot=4, mode_slot=1)
    assert read.attributes == ("Dimmer", "Dimmer2")


def _dimmer_lines(attributes) -> list[str]:
    return [
        line for line in save_commands(_plan(attributes=attributes)) if "Attribute 'Dimmer" in line
    ]


def test_a_group_with_a_second_dimmer_gets_its_own_preset_with_both_dimmers_on_one_line() -> None:
    # 2차 전체 실행 G-13 — 다른 그룹과 한 프리셋에 저장하면 콘솔 프리셋에 Dimmer2 가 빠졌다.
    # 실기 1.906 꼴: 둘째 디머를 가진 그룹만, 두 속성을 한 줄에.
    attributes = {**_ATTRIBUTES, "MOVER-D": ("Dimmer", "Dimmer2")}
    lines = _dimmer_lines(attributes)
    assert "Group 4 + 7 + 11 + 14 ; Attribute 'Dimmer' At 100" in lines
    assert "Group 12 ; Attribute 'Dimmer' At 100 ; Attribute 'Dimmer2' At 100" in lines
    assert not [line for line in lines if "'Dimmer2'" in line and not line.startswith("Group 12 ;")]
    card = save_commands(_plan(attributes=attributes))
    labels = [line for line in card if line.startswith("Label Preset 1.")]
    assert any(line.endswith("'DIM-100 DIMMER2'") for line in labels), labels


def test_groups_with_one_dimmer_keep_their_exact_lines() -> None:
    lines = _dimmer_lines(_ATTRIBUTES)
    assert not [line for line in lines if "Dimmer2" in line]
    assert "Group 4 + 7 + 11 + 12 + 14 ; Attribute 'Dimmer' At 100" in lines

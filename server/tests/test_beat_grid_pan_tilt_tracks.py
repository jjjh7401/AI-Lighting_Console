"""줄마다 조준 표시(``pan_tilt``)를 다는 판정 — 소속 장비의 능력으로만 가른다.

1018 aura 기록: BACK·SIDE 줄에 계획 위치가 없으면 헤드가 가운데에 머문다. 기본 위치는 조준할 수
있는 줄에만 주므로, 그 줄이 조준할 수 있는지를 먼저 알아야 한다. 모르면 표시를 달지 않는다.
"""

from __future__ import annotations

from server.design.beat_grid_stage import mark_pan_tilt_tracks


class _Capability:
    """``fixture_pan_tilt`` 가 보는 두 가지 — 속성 조회와 판독이 전수인지."""

    def __init__(self, attributes: set[str], *, whole: bool = True) -> None:
        self._attributes = attributes
        self.whole = whole

    def has_attribute(self, attribute: str) -> bool:
        return attribute in self._attributes


def _marks(tracks, members, capabilities) -> dict[str, object]:
    marked = mark_pan_tilt_tracks(tracks, members, capabilities)
    return {track["group_name"]: track.get("pan_tilt", "없음") for track in marked}


def test_a_line_is_marked_when_any_member_can_pan_or_tilt() -> None:
    tracks = [{"group_name": "BACK"}, {"group_name": "SIDE-ALL"}]
    members = {"BACK": [201, 202], "SIDE-ALL": [301, 302]}
    capabilities = {
        201: _Capability({"Dimmer", "Pan", "Tilt"}),
        202: _Capability({"Dimmer"}),
        301: _Capability({"Dimmer"}),
        302: _Capability({"Dimmer"}),
    }
    assert _marks(tracks, members, capabilities) == {"BACK": True, "SIDE-ALL": False}


def test_a_line_with_an_unread_or_partly_read_member_stays_unmarked() -> None:
    tracks = [{"group_name": "WASH"}, {"group_name": "KEY"}, {"group_name": "BLIND"}]
    members = {"WASH": [401, 402], "KEY": [101, 102], "BLIND": [501]}
    capabilities = {
        401: _Capability({"Dimmer"}),
        # 부분 판독 — 속성이 안 보인 것은 「없다」가 아니라 「못 읽었다」다
        402: _Capability({"Dimmer"}, whole=False),
        101: _Capability({"Dimmer"}),
        # 102 는 판독되지 않았다. 501 은 능력 표에 없다.
    }
    assert _marks(tracks, members, capabilities) == {
        "WASH": "없음",
        "KEY": "없음",
        "BLIND": "없음",
    }


def test_a_line_without_known_members_is_not_marked() -> None:
    assert _marks([{"group_name": "MOVER-U"}], {}, {}) == {"MOVER-U": "없음"}


def test_the_input_tracks_are_not_changed() -> None:
    tracks = [{"group_name": "BACK"}]
    mark_pan_tilt_tracks(tracks, {"BACK": [201]}, {201: _Capability({"Pan"})})
    assert tracks == [{"group_name": "BACK"}]

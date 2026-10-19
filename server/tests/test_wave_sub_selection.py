"""카드 WT-wave-custom 리드 실기 시험 결함 1 — 웨이브 저장도 서브 광원 줄의 선택 꼴을 따른다.

줄을 본체 그룹(``Group 7``)으로만 고르면 Aura XB 의 서브 광원에 빛이 나오지 않는다(t520 §14,
#826·#828 과 같은 규칙). 서브 광원에 밝기가 실린 기종의 연속 장비 줄은 뒤 점 범위
(``Fixture a Thru b.``)로 고른다. 웨이브 묶음도 일반 저장과 같은 선택을 써야 한다.

실제 세션 · 안전 게이트 · 승인 포트를 쓰고 콘솔만 가짜(``FakeConsole``)다.
"""

from __future__ import annotations

from .test_beat_grid_wave_presets import _session, _tree
from .test_sub_geometry_selection import _AURA, _cap

_SINE_2B = {"shape": "sine", "beats": 2, "label": "MY SINE 2B", "display_name": "내 사인 2박"}
#: 픽스처 ``_timeline()`` 의 BACK 줄 콘솔 그룹 번호.
_BACK_GROUP_NO = 7


def _aura_back(session) -> None:
    """BACK 소속을 본체·서브가 이어진 201~212 로, 기종은 서브 광원에 밝기가 실리는 Aura 로 준다."""
    session._beat_grid_group_members = lambda names, **_: {"BACK": list(range(201, 213))}
    session._rig_fixture_capabilities = lambda: {fid: _cap(fid, _AURA) for fid in range(201, 213)}


def _plain_back(session) -> None:
    """서브 광원 밝기가 없는 줄 — 이어지지도 않는 두 장비라 그룹 꼴 그대로 둔다."""
    session._beat_grid_group_members = lambda names, **_: {"BACK": [101, 102]}
    session._rig_fixture_capabilities = lambda: {}


class TestTheWaveFollowsTheSubSelection:
    def test_an_aura_line_is_saved_with_the_dot_range_not_the_bare_group(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}))
        _aura_back(session)

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is True
        assert len(approval.requests) == 1
        assert "Fixture 201 Thru 212." in console.executed
        assert f"Group {_BACK_GROUP_NO}" not in console.executed

    def test_a_plain_line_keeps_the_group_selection(self, tmp_path) -> None:
        session, console, _approval = _session(tmp_path, tree=_tree({}))
        _plain_back(session)

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is True
        assert f"Group {_BACK_GROUP_NO}" in console.executed
        assert not any(line.startswith("Fixture ") for line in console.executed)

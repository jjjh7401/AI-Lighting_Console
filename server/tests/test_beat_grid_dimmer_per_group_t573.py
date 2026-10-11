"""카드 t573(SPEC-LDBEAT-001 REQ-011~013) — 박자 격자 송신의 디머 속성을
트랙 그룹마다 고른다.

전에는 「리그 전 기종이 같은 디머 속성일 때만」 모든 트랙에 같은 속성을
냈다(t563). 이제 무대 칸 판독(t565 ``read_beat_grid_stage``)의 그룹 소속
(``member_fids``)과 리그 능력 판독(``read_design_rig``)으로 그룹마다
고르고, 못 고르는 트랙만 그 사유로 막는다.

기종 이름·속성 이름은 시험 데이터일 뿐이다 — 코드 쪽에는 상수가 없다.
콘솔 접촉: ``FakeConsole`` 만, 실기 쓰기 0건.
"""

from __future__ import annotations

from server.design import beat_grid_emit
from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle
from server.design.beat_grid_send import resolve_group_dimmer_attributes
from server.design.capability_join import FixtureCapability, RigCapabilities
from server.design.rig_capability_read import DesignRigRead
from server.prechk.capability_read import AxisRange
from server.web import session as session_module
from server.web.session import SongTimelineStore

from .test_beat_grid_send_t563 import _APPROVED_EVIDENCE, _new_session, _timeline


def _capability(fid: int, type_name: str, attributes: tuple[str, ...], *, whole: bool = True):
    axes = tuple(AxisRange(attribute=name, channel_name=name) for name in attributes)
    return FixtureCapability(
        fid=fid,
        type_slot=1,
        type_name=type_name,
        mode_slot=1,
        mode_name="Mode 1",
        mode_width=None,
        channel_count=1,
        axes=axes,
        gaps=() if whole else ("some_gap",),
    )


def _rig(*capabilities: FixtureCapability, gap: str = "") -> DesignRigRead:
    caps = RigCapabilities(fixtures={c.fid: c for c in capabilities})
    return DesignRigRead(attempted=True, gap=gap, capabilities=caps)


#: 기종마다 디머 속성이 다른 리그 — 전 기종 규칙이면 아무 트랙도 못 받는다.
_MIXED_RIG = _rig(
    _capability(11, "TYPE-TWO-DIMMERS", ("Dimmer", "Dimmer2", "Pan")),
    _capability(12, "TYPE-TWO-DIMMERS", ("Dimmer", "Dimmer2", "Pan")),
    _capability(21, "TYPE-ONE-DIMMER", ("Dimmer", "ColorRGB_R")),
    _capability(22, "TYPE-ONE-DIMMER", ("Dimmer", "ColorRGB_R")),
)


class TestResolveGroupDimmerAttributes:
    def test_each_group_gets_the_dimmer_attributes_of_its_own_members(self):
        resolved, reasons = resolve_group_dimmer_attributes(
            _MIXED_RIG, ["SPIDERS", "PARS"], {"SPIDERS": [11, 12], "PARS": [21, 22]}
        )
        assert resolved == {"SPIDERS": ("Dimmer", "Dimmer2"), "PARS": ("Dimmer",)}
        assert reasons == {}

    def test_a_group_mixing_dimmer_attribute_sets_is_blocked_alone(self):
        resolved, reasons = resolve_group_dimmer_attributes(
            _MIXED_RIG, ["ALL", "PARS"], {"ALL": [11, 21], "PARS": [21, 22]}
        )
        assert resolved == {"PARS": ("Dimmer",)}
        assert set(reasons) == {"ALL"}
        assert "섞여" in reasons["ALL"]
        assert "fid 11" in reasons["ALL"] and "fid 21" in reasons["ALL"]

    def test_a_member_whose_capability_was_not_read_blocks_only_that_group(self):
        resolved, reasons = resolve_group_dimmer_attributes(
            _MIXED_RIG, ["SPIDERS", "GHOST"], {"SPIDERS": [11], "GHOST": [21, 99]}
        )
        assert resolved == {"SPIDERS": ("Dimmer", "Dimmer2")}
        assert "99" in reasons["GHOST"]

    def test_a_partially_read_member_capability_is_not_trusted(self):
        rig = _rig(
            _capability(11, "T", ("Dimmer",), whole=False), _capability(12, "T", ("Dimmer",))
        )
        resolved, reasons = resolve_group_dimmer_attributes(rig, ["G"], {"G": [11, 12]})
        assert resolved == {}
        assert "11" in reasons["G"]

    def test_a_group_whose_members_have_no_dimmer_is_blocked(self):
        rig = _rig(_capability(31, "STROBE", ("Strobe",)))
        resolved, reasons = resolve_group_dimmer_attributes(rig, ["S"], {"S": [31]})
        assert resolved == {}
        assert "디머 속성이 없습니다" in reasons["S"]

    def test_unknown_membership_falls_back_to_the_rig_wide_rule(self):
        uniform = _rig(
            _capability(1, "A", ("Dimmer", "Dimmer2")), _capability(2, "B", ("Dimmer", "Dimmer2"))
        )
        resolved, reasons = resolve_group_dimmer_attributes(uniform, ["X"], {})
        assert resolved == {"X": ("Dimmer", "Dimmer2")}
        assert reasons == {}

    def test_unknown_membership_on_a_mixed_rig_is_blocked_with_a_reason(self):
        resolved, reasons = resolve_group_dimmer_attributes(_MIXED_RIG, ["X"], {})
        assert resolved == {}
        assert "소속" in reasons["X"]

    def test_a_partial_rig_still_resolves_groups_whose_members_were_all_read(self):
        # 리그 어딘가가 부분 판독이어도(gap) 이 그룹 장비는 다 읽혔다.
        rig = _rig(_capability(11, "T", ("Dimmer", "Dimmer2")), gap="fid_partial")
        resolved, reasons = resolve_group_dimmer_attributes(rig, ["G"], {"G": [11]})
        assert resolved == {"G": ("Dimmer", "Dimmer2")}
        assert reasons == {}

    def test_an_unreadable_rig_blocks_every_group(self):
        rig = DesignRigRead(attempted=True, gap="rig_unreadable")
        resolved, reasons = resolve_group_dimmer_attributes(rig, ["G"], {"G": [11]})
        assert resolved == {}
        assert "읽지 못해" in reasons["G"]


def _brightness_track(name: str, group_no: int) -> dict:
    return {
        "group_name": name,
        "group_no": group_no,
        "group_no_confirmed": True,
        "cues": [
            {
                "bar": 1,
                "brightness": {"mode": "value", "value_percent": 60},
                "evidence": _APPROVED_EVIDENCE,
            }
        ],
    }


class TestEmitterUsesTheSpecificReason:
    def test_the_blocked_cell_carries_the_resolver_reason(self):
        timing = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=0.0)
        result = emit_beat_grid_write_bundle(
            [_brightness_track("ALL", 3)],
            timing=timing,
            sequence_numbers={"ALL": 201},
            timecode_numbers={"ALL": 20},
            dimmer_attributes={},
            probe_results={n: "통과" for n in range(1, 10)},
            dimmer_attribute_reasons={"ALL": "섞인 그룹 사유"},
        )
        assert result.blocked_cells == (("ALL", 1, "섞인 그룹 사유"),)

    def test_without_a_specific_reason_the_old_generic_reason_stays(self):
        assert (
            "dimmer_attributes 누락"
            in beat_grid_emit._cue_attribute_commands(
                {"bar": 1, "brightness": {"mode": "value", "value_percent": 60}},
                group_name="ALL",
                group_no=3,
                timing=SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=0.0),
                dimmer_attributes={},
            )[1]
        )


class TestSendPathPicksPerGroup:
    """세션 송신 경로 — 소속 판독과 리그 판독을 대역으로 바꿔, 그룹마다 다른
    디머 속성 줄이 실제 콘솔 명령으로 나가는지 본다."""

    def _session(self, tmp_path, monkeypatch, groups: list[dict]):
        store = SongTimelineStore()
        timeline = _timeline()
        timeline["beat_grid"]["tracks"] = [
            _brightness_track("SPIDERS", 4),
            _brightness_track("PARS", 5),
            _brightness_track("ALL", 6),
        ]
        store.latest = timeline
        session, console, approval, _audit = _new_session(tmp_path, store=store)
        session._rig_paths = {**session._rig_paths, "fixtures": "F", "groups": "G"}
        monkeypatch.setattr(session_module, "read_design_rig", lambda *a, **k: _MIXED_RIG)
        monkeypatch.setattr(
            session_module,
            "read_beat_grid_stage",
            lambda *a, **k: {"fixtures": [], "groups": groups, "unread": []},
        )
        return session, console

    def test_each_track_sends_its_own_dimmer_attributes_and_the_mixed_one_is_blocked(
        self, tmp_path, monkeypatch
    ):
        session, console = self._session(
            tmp_path,
            monkeypatch,
            [
                {"group_no": 4, "group_name": "Spiders", "member_fids": [11, 12], "complete": True},
                {"group_no": 5, "group_name": "PARS", "member_fids": [21, 22], "complete": True},
                {"group_no": 6, "group_name": "ALL", "member_fids": [11, 21], "complete": True},
            ],
        )
        event = session.beat_grid_apply()
        assert event["ok"] is True
        sent = console.executed
        assert "Group 4 ; Attribute 'Dimmer' At 60" in sent
        assert "Group 4 ; Attribute 'Dimmer2' At 60" in sent
        assert "Group 5 ; Attribute 'Dimmer' At 60" in sent
        assert "Group 5 ; Attribute 'Dimmer2' At 60" not in sent
        assert not any(cmd.startswith("Group 6 ;") for cmd in sent)
        blocked = {(row["group_name"], row["bar"]): row["reason"] for row in event["blocked_cells"]}
        assert "섞여" in blocked[("ALL", 1)]

    def test_an_incomplete_membership_read_is_not_used(self, tmp_path, monkeypatch):
        session, console = self._session(
            tmp_path,
            monkeypatch,
            [{"group_no": 4, "group_name": "SPIDERS", "member_fids": [11], "complete": False}],
        )
        event = session.beat_grid_apply()
        # 세 트랙 모두 소속을 모르고(부분 판독은 버린다) 리그가 섞여 있다 —
        # 밝기 값 줄은 하나도 안 나가고, 칸마다 소속 사유로 막힌다.
        assert not any("Attribute" in cmd for cmd in console.executed)
        reasons = {row["group_name"]: row["reason"] for row in event["blocked_cells"]}
        assert set(reasons) == {"SPIDERS", "PARS", "ALL"}
        assert all("소속" in reason for reason in reasons.values())

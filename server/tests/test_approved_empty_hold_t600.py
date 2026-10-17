"""카드 t600 — 이미 승인된 칸이 빈 프리셋 번호를 가리킨 채 콘솔로 나가는 구멍.

t590 가드 D 는 승인 대기 칸만 보류했다. 이미 승인된(``evidence.approval``이 완전한)
칸이 콘솔 풀에 slot 이 없는 번호를 가리키면, 에미터는 그 칸을 막지 않아 빈 번호를
가리킨 큐가 그대로 나갔다(t595 판정서 「state: approved」). 리드 방향(2026-10-11):
반영 때 승인된 칸도 승인 대기 칸과 **같은 규칙**으로 묶는다 — 만들 수 있는 위치
번호는 t592 길로 만들고, 아니면 사유를 달고 칸 단위로 송신 보류한다. 승인=송신
대조는 보류 칸을 송신으로 세지 않는다. 콘솔 접촉 0건(가짜 콘솔).
"""

from __future__ import annotations

from server.design.beat_grid import (
    CELL_HOLD,
    EMPTY_PRESET_HOLD,
    POOL_UNREAD_HOLD,
    POSITION_CREATE_ON_APPLY,
    check_evidence_approval,
    empty_preset_cells,
)
from server.design.beat_grid_emit import emit_beat_grid_write_bundle
from server.web.session import SongTimelineStore

from .test_apply_time_approval_t577 import _cue_of, _new_session, _state_tree, _timeline
from .test_position_preset_create_t592 import _FRAMES, _MEMBERS, _RECIPE, _pool

_APPROVED = {"approval": {"by": "supervisor", "date": "2026-10-10", "source": "t600-fixture"}}


def _approved(bar: int, **numbers: object) -> dict:
    return {"bar": bar, "effect_kind": "position", "evidence": dict(_APPROVED), **numbers}


def _apply(tmp_path, cues: list[dict], *, extra_tree=None, grid_extra=None):
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = cues
    if grid_extra:
        timeline["beat_grid"].update(grid_extra)
    tree = _state_tree()  # 풀 4 = slot 21 만
    tree.update(extra_tree or {})
    store = SongTimelineStore()
    store.latest = timeline
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)
    session._beat_grid_group_members = lambda names, **_: {
        n: _MEMBERS[n] for n in names if n in _MEMBERS
    }
    session._beat_grid_pointing_frames = lambda: _FRAMES
    status = session.beat_grid_apply()
    return status, store, approval, console


def _sent(approval) -> list[str]:
    return [item.command for request in approval.requests for item in request.items]


def _risk(approval) -> str:
    return " ".join(approval.requests[0].items[0].risk_reasons)


class TestApprovedCellWithEmptyNumberIsHeld:
    def test_empty_effect_number_is_not_sent(self, tmp_path) -> None:
        status, store, approval, console = _apply(
            tmp_path, [_approved(1, effect_preset_no="4.21"), _approved(2, effect_preset_no="4.99")]
        )
        assert status["ok"] is True
        sent = _sent(approval)
        assert any("At Preset 4.21" in c for c in sent), "대조군(있는 번호)이 나가지 않았다"
        assert not [c for c in sent if "4.99" in c]
        assert not [c for c in console.executed if "4.99" in c]
        risk = _risk(approval)
        assert f"{EMPTY_PRESET_HOLD}(송신 보류) 1개" in risk
        assert "BACK 2마디" in risk and "4.99" in risk
        # 승인=송신 대조 — 보류 칸은 승인 목록에도 송신 목록에도 없다.
        assert status["approval_vs_sent"]["match"] is True
        # 승인은 지우지 않는다(다음 반영 때 다시 판정).
        assert check_evidence_approval(_cue_of(store.latest["beat_grid"], "BACK", 2)) is None

    def test_unreadable_pool_is_held_with_its_own_reason(self, tmp_path) -> None:
        # 풀 6 은 상태 트리에 없다 → 판독 실패.
        status, _store, approval, _console = _apply(
            tmp_path, [_approved(1, effect_preset_no="4.21"), _approved(2, color_preset_no="6.5")]
        )
        assert status["ok"] is True
        assert not [c for c in _sent(approval) if "6.5" in c]
        assert POOL_UNREAD_HOLD in _risk(approval)
        assert status["approval_vs_sent"]["match"] is True

    def test_hold_is_per_cell(self, tmp_path) -> None:
        # 한 칸에 있는 번호(4.21) + 빈 번호(4.99) → 칸 전체 보류.
        status, _store, approval, _console = _apply(
            tmp_path,
            [
                _approved(1, effect_preset_no="4.21", color_preset_no="4.99"),
                _approved(2, effect_preset_no="4.21"),
            ],
        )
        assert status["ok"] is True
        sent = _sent(approval)
        assert not [c for c in sent if "4.99" in c]
        risk = _risk(approval)
        assert "BACK 1마디" in risk and CELL_HOLD in risk
        assert status["approval_vs_sent"]["match"] is True

    def test_pending_cell_still_gets_recorded_alongside(self, tmp_path) -> None:
        pending = {
            "bar": 1,
            "effect_preset_no": "4.21",
            "effect_kind": "position",
            "evidence": None,
        }
        status, store, approval, _console = _apply(
            tmp_path, [pending, _approved(2, effect_preset_no="4.99")]
        )
        assert status["ok"] is True
        assert "콘솔에 이미 있는 프리셋을 쓰는 칸 1개(새로 저장하지 않음)" in _risk(approval)
        assert check_evidence_approval(_cue_of(store.latest["beat_grid"], "BACK", 1)) is None
        assert not [c for c in _sent(approval) if "4.99" in c]


class TestApprovedEmptyPositionIsCreated:
    def test_creation_lines_precede_the_cue_that_uses_it(self, tmp_path) -> None:
        status, _store, approval, _console = _apply(
            tmp_path,
            [_approved(1, position_preset_no="2.71")],
            extra_tree={"DataPool/PresetPools/2": _pool("DataPool/PresetPools/2", [1, 2])},
            grid_extra=_RECIPE,
        )
        assert status["ok"] is True
        sent = _sent(approval)
        store_at = sent.index("Store Preset 2.71")
        uses = [i for i, c in enumerate(sent) if "At Preset 2.71" in c]
        assert uses, "승인된 칸의 큐가 나가지 않았다"
        assert min(uses) > store_at
        assert "새로 만드는 위치 프리셋 1개" in _risk(approval)
        assert status["approval_vs_sent"]["match"] is True

    def test_missing_recipe_holds_the_approved_cell(self, tmp_path) -> None:
        status, _store, approval, _console = _apply(
            tmp_path,
            [_approved(1, effect_preset_no="4.21"), _approved(2, position_preset_no="2.71")],
            extra_tree={"DataPool/PresetPools/2": _pool("DataPool/PresetPools/2", [1])},
        )
        assert status["ok"] is True
        sent = _sent(approval)
        assert not [c for c in sent if "2.71" in c]
        assert "위치 프리셋 목표 좌표가 없음" in _risk(approval)
        assert "이미 승인된 칸" in _risk(approval)


class TestMarksNoLongerSayApproved:
    def _grid(self, cues: list[dict], **extra) -> dict:
        grid = {
            "tracks": [
                {"group_name": "BACK", "group_no": 7, "group_no_confirmed": True, "cues": cues}
            ]
        }
        grid.update(extra)
        return grid

    def test_approved_empty_cell_is_marked_held(self) -> None:
        cells = empty_preset_cells(
            self._grid([_approved(2, effect_preset_no="4.99")]), {4: {21: "P21"}}
        )
        assert [c["state"] for c in cells] == ["held"]

    def test_approved_empty_position_with_recipe_is_marked_create(self) -> None:
        cells = empty_preset_cells(
            self._grid([_approved(1, position_preset_no="2.71")], **_RECIPE), {2: {1: "P1"}}
        )
        assert [c["state"] for c in cells] == ["create"]
        assert cells[0]["fields"][0]["reason"] == POSITION_CREATE_ON_APPLY


class TestEmitterHeldCells:
    def test_held_cell_emits_nothing_and_takes_no_cue_number(self) -> None:
        from server.design.beat_grid_emit import SongTiming

        track = {
            "group_name": "BACK",
            "group_no": 7,
            "group_no_confirmed": True,
            "cues": [_approved(1, effect_preset_no="4.21"), _approved(2, effect_preset_no="4.21")],
        }
        timing = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=0.0)
        kwargs = dict(
            timing=timing,
            sequence_numbers={"BACK": 300},
            timecode_numbers={"BACK": 20},
            dimmer_attributes={},
            probe_results={1: "통과", 2: "통과", 4: "통과", 5: "통과", 7: "통과", 9: "통과"},
        )
        result = emit_beat_grid_write_bundle(
            [track], held_cells={("BACK", 1): EMPTY_PRESET_HOLD}, **kwargs
        )
        cues = {c.bar: c for c in result.tracks[0].cues}
        assert cues[1].commands == () and cues[1].blocked_reason == EMPTY_PRESET_HOLD
        assert cues[2].commands and cues[2].cue_number == 1

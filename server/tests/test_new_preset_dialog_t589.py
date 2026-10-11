"""카드 t589 — 「＋ 새 프리셋 만들기」 창 (REQ-LDBEAT-015(h-1)~(h-6) 계속).

영문 콘솔 이름·한국어 설명을 받아 `preset_pools.yaml` 번호대에서 빈 번호를
골라 **일반 편집과 같은 길**(`apply_beat_grid_edit`)로 씌운다 — 새 콘솔
쓰기 경로를 만들지 않는다(AC-LDBEAT-005). 그래서 번호는 다른 신규 번호와
똑같이 「⇪ 콘솔에 반영」 승인 전까지 승인 대기로 남는다.

세 층을 가른다: ① 순수 번호 배정 함수(`first_free_preset_number`) ②
서버 핸들러(`ChatSession.beat_grid_new_preset`) ③ 프로토콜 파서
(`parse_client_message`). 콘솔 접촉: 0건(쓰기). 읽기는 드로워가 이미
쓰는 `read_named_pool` 재사용 — `FakeConsole`만 쓰고 실기 포트로는 한
바이트도 나가지 않는다(`console.executed == []`로 직접 잰다).
"""

from __future__ import annotations

import json

import pytest

from server.design.beat_grid import pending_preset_approvals
from server.design.beat_grid_effect_presets import EFFECT_RECIPE_MISSING
from server.design.beat_grid_presets import (
    app_preset_description,
    app_preset_label,
    first_free_preset_number,
)
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import ProtocolError, parse_client_message
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole

PROTOCOL_VERSION = 1


class RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("이 경로는 모델을 부르지 않는다")


class ScriptedApproval:
    """``test_apply_time_approval_t577.ScriptedApproval``과 같은 모양(카드
    t577과 같은 이유로 이 파일 안에 복제한다 — 결정적이고 짧다)."""

    def __init__(self, decisions=(True,)):
        self.decisions = list(decisions)
        self.requests = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        if not self.decisions:
            return False
        return self.decisions.pop(0)


#: `console_slots.resolve_named_pool_no`/`paged_pool_children`이 한
#: 창(페이징 불필요)으로 완결로 읽도록 — `test_session_beat_grid_edit_
#: t551.py`의 같은 이름 헬퍼와 바이트 동일.
def _pool_list_payload(pools: dict[str, int]) -> dict:
    children = [{"i": no, "name": name} for name, no in pools.items()]
    return {"children": children, "node": {"childCount": len(children)}}


def _pool_children_payload(entries: dict[int, str]) -> dict:
    children = [{"i": slot, "name": name} for slot, name in entries.items()]
    return {"children": children, "node": {"childCount": len(children)}}


_SEQUENCES_SECTION = {"children": []}
_TIMECODE_POOL_CHILDREN_EMPTY = {"children": [], "node": {"childCount": 0, "enumeration": "ok"}}


def _bar_map(bpm: float = 112.35, beats_per_bar: int = 4) -> dict:
    return {
        "bpm": bpm,
        "time_signature": [beats_per_bar, 4],
        "bars": [
            {"bar": n, "start_ms": 1000 + (n - 1) * 2000, "beats_ms": [1000 + (n - 1) * 2000]}
            for n in range(1, 10)
        ],
    }


def _grid_with_effect_cell(effect_kind: str = "position") -> dict:
    """ "효과" 필드가 쓰는, effect_kind 는 이미 정해졌지만 번호는 아직
    미정인 칸 하나를 가진 최소 격자."""
    return {
        "tracks": [
            {
                "group_name": "BACK",
                "group_no": 7,
                "group_no_confirmed": True,
                "cues": [
                    {
                        "bar": 1,
                        "effect_kind": effect_kind,
                        "effect_preset_no": None,
                        "evidence": None,
                    }
                ],
            }
        ],
        "probe_results": {},
    }


def _timeline(**overrides: object) -> dict:
    base: dict[str, object] = {
        "song_title": "LOVE ATTACK",
        "sequence_number": 210,
        "beat_grid": _grid_with_effect_cell(),
    }
    base.update(overrides)
    return base


def _timeline_for_apply(**overrides: object) -> dict:
    """``beat_grid_apply``가 필요로 하는 bar_map·timecode_number까지
    갖춘 완전한 타임라인(``test_apply_time_approval_t577.py`` `_timeline`
    과 같은 모양)."""
    base: dict[str, object] = {
        "song_title": "LOVE ATTACK",
        "sequence_number": 210,
        "bar_map": _bar_map(),
        "timecode_number": 20,
        "beat_grid": _grid_with_effect_cell(),
    }
    base.update(overrides)
    return base


def _state_tree(**pools: dict) -> dict:
    base = {
        "DataPool/Sequences": _SEQUENCES_SECTION,
        "DataPool/Timecodes": _TIMECODE_POOL_CHILDREN_EMPTY,
    }
    base.update(pools)
    return base


def _new_session(
    tmp_path,
    *,
    store: SongTimelineStore,
    decisions=(True, True, True, True, True),
    state_tree: dict | None = None,
    sent: list[dict] | None = None,
):
    console = FakeConsole(state_tree=state_tree if state_tree is not None else {})
    audit = AuditLog(tmp_path / "audit")
    approval = ScriptedApproval(decisions=decisions)
    gate = SafetyGate(console=console, audit=audit, approval_port=approval)
    channel = ApprovalChannel(timeout_seconds=1.0)
    session = ChatSession(
        gate=gate,
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=(sent.append if sent is not None else (lambda event: None)),
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    return session, console, approval, audit


def _cue_of(grid, group_name: str, bar: int) -> dict:
    track = next(t for t in grid["tracks"] if t["group_name"] == group_name)
    return next(c for c in track["cues"] if c["bar"] == bar)


# == ① 순수 번호 배정 함수 ====================================================


class TestFirstFreePresetNumber:
    def test_first_free_slot_in_an_empty_band(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        grid = {"tracks": []}
        preset_no, reason, warning = first_free_preset_number(
            "position", policy=policy, grid=grid, console_children={}
        )
        assert reason is None
        assert preset_no == "2.61"
        assert warning is None  # 콘솔 읽음(빈 딕셔너리라도 None 이 아니다)

    def test_skips_a_number_the_grid_already_references(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        grid = {
            "tracks": [
                {"group_name": "BACK", "cues": [{"bar": 1, "effect_preset_no": "2.61"}]},
            ]
        }
        preset_no, reason, _warning = first_free_preset_number(
            "position", policy=policy, grid=grid, console_children={}
        )
        assert reason is None
        assert preset_no == "2.62"

    def test_skips_a_number_the_console_already_occupies(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        grid = {"tracks": []}
        preset_no, reason, _warning = first_free_preset_number(
            "position", policy=policy, grid=grid, console_children={61: "Existing Show Preset"}
        )
        assert reason is None
        assert preset_no == "2.62"

    def test_skips_an_occupied_slot_whose_name_is_empty(self) -> None:
        # `paged_pool_children`은 이름 없는 프리셋을 `{slot: None}`으로 돌려준다
        # — 키가 있으면 콘솔에 그 번호가 있다(이름 유무와 무관).
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        preset_no, reason, _warning = first_free_preset_number(
            "position", policy=policy, grid={"tracks": []}, console_children={61: None}
        )
        assert reason is None
        assert preset_no == "2.62"

    def test_dimmer_sub_band_a_before_b(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {
                "dimmer_effect_a": {"start": "1.21", "end": "1.26"},
                "dimmer_effect_b": {"start": "1.31", "end": "1.33"},
            },
        }
        # 서브 밴드 a 를 전부 격자 참조로 채운다 — b 의 첫 슬롯이 나와야 한다.
        grid = {
            "tracks": [
                {
                    "group_name": "BACK",
                    "cues": [
                        {"bar": n, "effect_preset_no": f"1.{slot}"}
                        for n, slot in enumerate(range(21, 27), start=1)
                    ],
                }
            ]
        }
        preset_no, reason, _warning = first_free_preset_number(
            "dimmer", policy=policy, grid=grid, console_children={}
        )
        assert reason is None
        assert preset_no == "1.31"

    def test_full_band_is_rejected_not_silently_overflowed(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.61"}},
        }
        grid = {
            "tracks": [
                {"group_name": "BACK", "cues": [{"bar": 1, "effect_preset_no": "2.61"}]},
            ]
        }
        preset_no, reason, _warning = first_free_preset_number(
            "position", policy=policy, grid=grid, console_children={}
        )
        assert preset_no is None
        assert reason is not None
        assert "모두 찼습니다" in reason

    def test_unread_console_pool_still_assigns_but_warns(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        grid = {"tracks": []}
        preset_no, reason, warning = first_free_preset_number(
            "position", policy=policy, grid=grid, console_children=None
        )
        assert reason is None
        assert preset_no == "2.61"
        assert warning is not None
        assert "콘솔" in warning

    def test_kind_with_no_declared_band_is_rejected_without_fabricating_one(self) -> None:
        policy = {"confirmed": False, "pools": {}}
        preset_no, reason, _warning = first_free_preset_number(
            "nonsense", policy=policy, grid={"tracks": []}, console_children={}
        )
        assert preset_no is None
        assert reason is not None
        assert "번호대를 지어내지 않습니다" in reason


# == ② 서버 핸들러 ===========================================================


class TestBeatGridNewPresetHandler:
    def test_ascii_label_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", "effect", "라이트 웨이브", "따뜻한 흰색")
        assert "영문" in event["text"]
        assert console.executed == []

    def test_empty_label_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", "effect", "   ", "따뜻한 흰색")
        assert "이름이 비어" in event["text"]
        assert console.executed == []

    def test_empty_description_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", "effect", "LA Wave", "   ")
        assert "설명이 비어" in event["text"]
        assert console.executed == []

    @pytest.mark.parametrize("field", ["dimmer_preset", "position", "color"])
    def test_base_pool_fields_rejected_with_the_no_band_reason(self, tmp_path, field) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", field, "LA Wave", "따뜻한 흰색")
        assert "번호대를 지어내지 않습니다" in event["text"]
        assert console.executed == []
        # 거절 시 격자 상태는 바이트까지 그대로다.
        assert store.latest["beat_grid"] == _grid_with_effect_cell()

    def test_effect_cell_is_assigned_within_its_declared_band(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = _state_tree(
            **{
                "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
                "DataPool/PresetPools/2": _pool_children_payload({}),
            }
        )
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )
        event = session.beat_grid_new_preset(1, "BACK", "effect", "LA Wave", "따뜻한 흰색")
        assert "거절" not in event.get("summary", ""), event["text"]
        assert "2.61" in event["text"]
        assert "승인 대기" in event["text"]
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert cue["effect_preset_no"] == "2.61"
        assert cue["effect_kind"] == "position"
        assert console.executed == []  # 읽기만(콘솔 점유 확인) — 쓰기 0건

    def test_assigned_number_is_pending_not_approved(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = _state_tree(
            **{
                "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
                "DataPool/PresetPools/2": _pool_children_payload({}),
            }
        )
        session, _console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )
        session.beat_grid_new_preset(1, "BACK", "effect", "LA Wave", "따뜻한 흰색")
        grid = store.latest["beat_grid"]
        cue = _cue_of(grid, "BACK", 1)
        assert cue["evidence"] is None  # 아직 승인 없음
        pending = pending_preset_approvals(grid)
        assert any(
            entry["group_name"] == "BACK" and entry["bar"] == 1 and entry["value"] == "2.61"
            for entry in pending
        )

    def test_label_and_description_are_stored_and_survive_a_later_edit(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = _state_tree(
            **{
                "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
                "DataPool/PresetPools/2": _pool_children_payload({}),
            }
        )
        session, _console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )
        session.beat_grid_new_preset(1, "BACK", "effect", "LA Wave", "따뜻한 흰색")
        grid = store.latest["beat_grid"]
        assert app_preset_label(grid, "2.61") == "LA Wave"
        assert app_preset_description(grid, "2.61") == "따뜻한 흰색"
        # 이후 다른 편집(무관한 칸)이 두 표를 지우지 않는지 확인 — round-trip.
        session.beat_grid_edit(
            bar=1, target="BACK", changes={"entry": {"fade_bars": 1, "mib_mode": None}}
        )
        after = store.latest["beat_grid"]
        assert app_preset_label(after, "2.61") == "LA Wave"
        assert app_preset_description(after, "2.61") == "따뜻한 흰색"

    def test_zero_console_writes(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        state_tree = _state_tree(
            **{
                "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
                "DataPool/PresetPools/2": _pool_children_payload({61: "Existing"}),
            }
        )
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )
        session.beat_grid_new_preset(1, "BACK", "effect", "LA Wave", "따뜻한 흰색")
        assert console.executed == []

    def test_no_timeline_refuses_without_console_contact(self, tmp_path) -> None:
        store = SongTimelineStore()  # latest 는 None
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", "effect", "LA Wave", "따뜻한 흰색")
        assert "박자 격자가 아직 없습니다" in event["text"]
        assert console.executed == []

    def test_unknown_field_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", "not_a_real_field", "LA Wave", "설명")
        assert "not_a_real_field" in event["text"]
        assert console.executed == []

    def test_effect_cell_without_a_known_effect_kind_is_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        # effect_kind 가 아직 없는 칸(새 바).
        store.latest = _timeline(beat_grid=_grid_with_effect_cell(effect_kind="position"))
        store.latest["beat_grid"]["tracks"][0]["cues"][0]["effect_kind"] = None
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", "effect", "LA Wave", "설명")
        assert "효과 종류" in event["text"]
        assert console.executed == []


# == 승인 카드: 이름·설명 노출 + 「송신 보류」 한 줄 =============================
# 카드 t590(REQ-LDBEAT-015(i-1)) 이후 콘솔에 없는 번호는 송신 보류다. 앱이 만든
# 번호는 빈 번호라 늘 보류 줄에 온다 — 리드 판단(2026-10-11)대로 경고는 t590
# 보류 문구 한 줄로 합치고, 그 줄에 이름·설명을 그대로 보인다(이 잠금은 유지).


class TestApprovalCardShowsLabelAndDescription:
    def test_risk_reason_carries_label_description_and_the_console_creation_note(
        self, tmp_path
    ) -> None:
        store = SongTimelineStore()
        store.latest = _timeline_for_apply()
        state_tree = _state_tree(
            **{
                "DataPool/PresetPools": _pool_list_payload({"Position": 2}),
                "DataPool/PresetPools/2": _pool_children_payload({}),
            }
        )
        session, _console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=state_tree
        )
        new_preset_event = session.beat_grid_new_preset(
            1, "BACK", "effect", "LA Wave", "따뜻한 흰색"
        )
        assert "거절" not in new_preset_event.get("summary", ""), new_preset_event["text"]

        apply_event = session.beat_grid_apply()
        assert apply_event["ok"] is True
        assert len(approval.requests) == 1
        risk_reasons = approval.requests[0].items[0].risk_reasons
        joined = " ".join(risk_reasons)
        # 빈 번호라 「새로 만드는 프리셋」(승인 기록 대상)이 아니라 보류 줄에 온다.
        assert "새로 만드는 프리셋" not in joined
        assert "빈 프리셋 — 아직 콘솔에 만들 길 없음(송신 보류) 1개" in joined
        # 이름·설명은 그 보류 줄에 그대로 보인다(t589 잠금). 카드 t593 부터 빈 효과
        # 번호는 레시피가 있으면 반영 때 만들어지므로, 항목 사유는 못 만드는 까닭이다.
        assert f"2.61 'LA Wave' — 따뜻한 흰색({EFFECT_RECIPE_MISSING})" in joined
        # 경고는 한 줄 — t589 의 옛 별도 문장은 없다.
        assert "콘솔에는 아직 만들어지지 않음" not in joined
        assert joined.count("(송신 보류)") == 1

    def test_a_directly_picked_new_number_without_a_label_is_not_mislabeled(self, tmp_path) -> None:
        # t577 류의 "번호를 직접 고르는" 승인 대기 — `app_preset_label`이
        # `None`이라 이름·설명이 붙지 않아야 한다(회귀 방지). 풀을 못 읽은
        # 번호라 t590 규칙대로 보류 줄에 온다.
        store = SongTimelineStore()
        store.latest = _timeline_for_apply()
        session, _console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_state_tree()
        )
        edit_event = session.beat_grid_edit(
            bar=1, target="BACK", changes={"effect_preset_no": "2.65", "effect_kind": "position"}
        )
        assert "승인 대기" in edit_event["text"]
        apply_event = session.beat_grid_apply()
        assert apply_event["ok"] is True
        risk_reasons = approval.requests[0].items[0].risk_reasons
        joined = " ".join(risk_reasons)
        assert "빈 프리셋 — 아직 콘솔에 만들 길 없음(송신 보류) 1개" in joined
        assert "2.65(풀을 못 읽어 빈 프리셋인지 확인 못 함)" in joined
        assert "2.65 '" not in joined  # 이름이 붙지 않았다


# == ③ 프로토콜 파서 =========================================================


class TestParseClientMessageBeatGridNewPreset:
    def _valid_payload(self, **overrides: object) -> dict:
        payload = {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_new_preset",
            "bar": 1,
            "target": "BACK",
            "field": "effect",
            "label": "LA Wave",
            "description": "따뜻한 흰색",
        }
        payload.update(overrides)
        return payload

    def _parse(self, payload: dict) -> dict:
        return parse_client_message(json.dumps(payload))

    def test_valid_payload_parses(self) -> None:
        parsed = self._parse(self._valid_payload())
        assert parsed["type"] == "beat_grid_new_preset"
        assert parsed["bar"] == 1
        assert parsed["target"] == "BACK"
        assert parsed["field"] == "effect"
        assert parsed["label"] == "LA Wave"
        assert parsed["description"] == "따뜻한 흰색"

    def test_missing_bar_is_rejected(self) -> None:
        payload = self._valid_payload()
        del payload["bar"]
        with pytest.raises(ProtocolError):
            self._parse(payload)

    def test_non_integer_bar_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            self._parse(self._valid_payload(bar="1"))

    def test_empty_target_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            self._parse(self._valid_payload(target="  "))

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            self._parse(self._valid_payload(field="dimmer"))

    def test_empty_label_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            self._parse(self._valid_payload(label=""))

    def test_non_string_label_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            self._parse(self._valid_payload(label=123))

    def test_empty_description_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            self._parse(self._valid_payload(description="   "))

    @pytest.mark.parametrize(
        "field", ["dimmer_preset", "dimmer_effect", "position", "color", "effect"]
    )
    def test_all_five_fields_are_accepted(self, field) -> None:
        parsed = self._parse(self._valid_payload(field=field))
        assert parsed["field"] == field

"""카드 t593 — 새 효과 프리셋을 콘솔에 실제로 만든다(REQ-LDBEAT-015(i-4)(i-7)(i-8)).

값 = 곡 격자 ``preset_fx_recipes["22.n"]``(효과 템플릿 ``fx_id`` + 음악 단위 주기)를
fx 라이브러리 템플릿에 입혀 ``build_fx_preset_bundle``(``/Universal``, 실기 선례)로
만든 줄. 속도 = 곡 BPM ÷ 한 주기 박 수(``app_movement.py`` 선례). 이름 =
``preset_labels["22.n"]``(t589 와 같은 키·모양).

핵심 잠금(t592 와 같다): ``Store Preset`` 은 풀 판독에서 slot 이 **비었다고 읽힌**
번호에만 나간다(덮어쓰기 0). 한 반영 묶음에 효과 프리셋을 몇 개 만들어도 전부
나간다(카드 t605) — 모든 효과 묶음이 같은 스텝 전환 줄을 내지만(``server/fx/
library/movement.yaml`` 머리 주석), 카드 t601 이 송신 중복 제거를 "앞선 호출에서
실행된 줄만" 건너뛰도록 고쳐 묶음 안 반복을 더는 건너뛰지 않는다. 콘솔 접촉 0건.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid import (
    CELL_HOLD,
    EMPTY_PRESET_HOLD,
    POOL_UNREAD_HOLD,
    check_evidence_approval,
    empty_preset_cells,
)
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.beat_grid_effect_presets import (
    EFFECT_BAND_UNKNOWN,
    EFFECT_CREATE_ON_APPLY,
    EFFECT_DIMMER_OUT_OF_SCOPE,
    EFFECT_GROUP_UNCONFIRMED,
    EFFECT_LABEL_INVALID,
    EFFECT_LABEL_MISSING,
    EFFECT_MULTI_GROUP,
    EFFECT_RECIPE_MISSING,
    EFFECT_TEMPLATE_KIND_MISMATCH,
    EFFECT_TEMPLATE_UNKNOWN,
    EFFECT_TEMPO_MISSING,
    effect_preset_outcomes,
    effect_preset_recipe,
    record_effect_preset_recipe,
)
from server.design.beat_grid_position_presets import plan_cells
from server.fx.loader import load_library_from_dir
from server.web.session import SongTimelineStore

from .test_apply_time_approval_t577 import _cue_of, _new_session, _state_tree, _timeline

# -- 픽스처 -------------------------------------------------------------------

_LIBRARY = load_library_from_dir()
_POLICY = load_preset_pool_policy()
_BPM, _BEATS_PER_BAR = 120.0, 4


def _track(name: str, group_no: int, cues: list[dict], *, confirmed: bool = True) -> dict:
    return {
        "group_name": name,
        "group_no": group_no,
        "group_no_confirmed": confirmed,
        "cues": cues,
    }


def _grid(cues: list[dict], *, confirmed: bool = True, **extra: object) -> dict:
    grid: dict = {"tracks": [_track("BACK", 7, cues, confirmed=confirmed)]}
    grid.update(extra)
    return grid


def _held(value: str, *, bar: int = 1, field: str = "effect_preset_no", reason=None) -> dict:
    return {
        "group_name": "BACK",
        "bar": bar,
        "field": field,
        "field_label": field,
        "value": value,
        "hold_reason": reason or EMPTY_PRESET_HOLD,
    }


def _recipe(number: str = "22.1", fx_id: str = "sweep-soft-wide", label: str = "LA Wave") -> dict:
    return {
        "preset_fx_recipes": {number: {"fx_id": fx_id, "period_unit": "beat", "period_value": 2}},
        "preset_labels": {number: label},
    }


def _outcomes(grid, numbers, *, bpm=_BPM, beats_per_bar=_BEATS_PER_BAR, library=_LIBRARY):
    return effect_preset_outcomes(
        grid,
        numbers,
        library=library,
        policy=_POLICY,
        bpm=bpm,
        beats_per_bar=beats_per_bar,
    )


def _plan(grid, held, **kwargs):
    numbers = sorted(
        {
            str(e["value"])
            for e in held
            if e["field"] == "effect_preset_no" and e["hold_reason"] == EMPTY_PRESET_HOLD
        }
    )
    outcomes = {("effect_preset_no", n): o for n, o in _outcomes(grid, numbers, **kwargs).items()}
    return plan_cells(held, outcomes)


_CUE = {"bar": 1, "effect_preset_no": "22.1", "effect_kind": "mixed", "evidence": None}


# -- 저장 자리 -----------------------------------------------------------------


class TestRecordRecipe:
    def test_records_a_copy_keyed_by_pool_slot(self) -> None:
        grid = _grid([])
        updated = record_effect_preset_recipe(
            grid, "22.1", fx_id="sweep-soft-wide", period_unit="bar", period_value=2
        )
        assert "preset_fx_recipes" not in grid, "원본을 바꿨다"
        assert effect_preset_recipe(updated, "22.1") == {
            "fx_id": "sweep-soft-wide",
            "period_unit": "bar",
            "period_value": 2,
        }

    @pytest.mark.parametrize(
        ("number", "fx_id", "unit", "value"),
        [
            ("22", "sweep-soft-wide", "beat", 2),
            ("22.1", "", "beat", 2),
            ("22.1", "sweep-soft-wide", "second", 2),
            ("22.1", "sweep-soft-wide", "beat", 0),
            ("22.1", "sweep-soft-wide", "beat", 1.5),
            ("22.1", "sweep-soft-wide", "beat", True),
        ],
    )
    def test_refuses_malformed_recipes(self, number, fx_id, unit, value) -> None:
        with pytest.raises(ValueError):
            record_effect_preset_recipe(
                _grid([]), number, fx_id=fx_id, period_unit=unit, period_value=value
            )

    def test_missing_or_malformed_recipe_reads_as_none(self) -> None:
        assert effect_preset_recipe(_grid([]), "22.1") is None
        bad = {"preset_fx_recipes": {"22.1": {"fx_id": "x", "period_unit": "beat"}}}
        assert effect_preset_recipe(bad, "22.1") is None


# -- 만들기 줄(순수) -------------------------------------------------------------


class TestCreationLines:
    def test_lines_follow_the_universal_preset_shape(self) -> None:
        grid = _grid([dict(_CUE)], **_recipe())
        commands, reason = _outcomes(grid, ["22.1"])["22.1"]
        assert reason is None
        assert commands[:3] == ("ChangeDestination Root", "ClearAll", "Group 7")
        store_at = commands.index("Store Preset 22.1 'LA Wave' /Universal")
        assert commands[store_at + 1] == "Label Preset 22.1 'LA Wave'"
        assert commands[-1] == "ClearAll"

    def test_speed_is_bpm_over_beats_per_cycle(self) -> None:
        # 120 BPM, 한 주기 2박 → 60. 템플릿의 speed(14)는 쓰지 않는다.
        grid = _grid([dict(_CUE)], **_recipe())
        commands, _ = _outcomes(grid, ["22.1"])["22.1"]
        assert "Attribute 'Pan' At Speed 60" in commands
        assert not [c for c in commands if "At Speed 14" in c]

    def test_bar_period_uses_beats_per_bar(self) -> None:
        extra = _recipe()
        extra["preset_fx_recipes"]["22.1"] = {
            "fx_id": "sweep-soft-wide",
            "period_unit": "bar",
            "period_value": 2,
        }
        commands, _ = _outcomes(_grid([dict(_CUE)], **extra), ["22.1"])["22.1"]
        # 2마디 × 4박 = 8박 → 120 / 8 = 15
        assert "Attribute 'Pan' At Speed 15" in commands


class TestEveryMissingPieceHoldsWithItsReason:
    @pytest.mark.parametrize(
        ("number", "extra", "confirmed", "reason"),
        [
            ("22.1", {"preset_labels": {"22.1": "LA Wave"}}, True, EFFECT_RECIPE_MISSING),
            ("22.1", _recipe(fx_id="no-such-fx"), True, EFFECT_TEMPLATE_UNKNOWN),
            (
                "22.1",
                {k: v for k, v in _recipe().items() if k != "preset_labels"},
                True,
                EFFECT_LABEL_MISSING,
            ),
            ("22.1", _recipe(label="한글 이름"), True, EFFECT_LABEL_INVALID),
            ("22.1", _recipe(), False, EFFECT_GROUP_UNCONFIRMED),
            # 디머 효과 대역(1.21~) — REQ-LDBEAT-015(i-6) 범위 밖.
            ("1.21", _recipe(number="1.21", fx_id="pulse-beat"), True, EFFECT_DIMMER_OUT_OF_SCOPE),
            # 어느 효과 대역에도 없는 번호.
            ("9.5", _recipe(number="9.5"), True, EFFECT_BAND_UNKNOWN),
            # 위치 효과 대역(2.61~)에 색 템플릿.
            (
                "2.61",
                _recipe(number="2.61", fx_id="chase-warm-cool"),
                True,
                EFFECT_TEMPLATE_KIND_MISMATCH,
            ),
        ],
    )
    def test_missing_piece(self, number, extra, confirmed, reason) -> None:
        cue = {**_CUE, "effect_preset_no": number}
        commands, got = _outcomes(_grid([cue], confirmed=confirmed, **extra), [number])[number]
        assert commands is None
        assert got == reason

    def test_missing_tempo_holds(self) -> None:
        grid = _grid([dict(_CUE)], **_recipe())
        commands, reason = _outcomes(grid, ["22.1"], bpm=None)["22.1"]
        assert (commands, reason) == (None, EFFECT_TEMPO_MISSING)

    def test_position_band_accepts_a_pan_tilt_template(self) -> None:
        cue = {**_CUE, "effect_preset_no": "2.61"}
        grid = _grid([cue], **_recipe(number="2.61"))
        commands, reason = _outcomes(grid, ["2.61"])["2.61"]
        assert reason is None and "Store Preset 2.61 'LA Wave' /Universal" in commands

    def test_two_groups_on_one_number_holds(self) -> None:
        grid = {
            "tracks": [
                _track("BACK", 7, [dict(_CUE)]),
                _track("SIDE", 8, [{**_CUE, "bar": 2}]),
            ],
            **_recipe(),
        }
        assert _outcomes(grid, ["22.1"])["22.1"] == (None, EFFECT_MULTI_GROUP)

    def test_one_group_on_two_tracks_is_one_selection(self) -> None:
        grid = {
            "tracks": [
                _track("BACK", 7, [dict(_CUE)]),
                _track("BACK-2", 7, [{**_CUE, "bar": 2}]),
            ],
            **_recipe(),
        }
        commands, reason = _outcomes(grid, ["22.1"])["22.1"]
        assert reason is None and commands[2] == "Group 7"

    def test_unconfirmed_track_of_another_cell_holds_the_number(self) -> None:
        # 이미 승인된 다른 칸의 트랙이라도 같은 번호를 부르면 그룹 확인이 필요하다.
        grid = {
            "tracks": [
                _track("BACK", 7, [dict(_CUE)]),
                _track("SIDE", 7, [{**_CUE, "bar": 2}], confirmed=False),
            ],
            **_recipe(),
        }
        assert _outcomes(grid, ["22.1"])["22.1"] == (None, EFFECT_GROUP_UNCONFIRMED)


class TestBothEffectsInOneBatchAreBuilt:
    """카드 t605 — t601 뒤로는 번호마다 독립으로 판정한다. 같은 반영에 효과
    프리셋 둘이 있어도(스텝 전환 줄이 겹쳐도) 둘 다 만들기 줄을 받는다 — 보류로
    밀리지 않는다."""

    def test_second_number_is_also_built_not_held(self) -> None:
        extra = _recipe("22.1")
        extra["preset_fx_recipes"]["22.2"] = {
            "fx_id": "wave-soft-rise",
            "period_unit": "beat",
            "period_value": 4,
        }
        extra["preset_labels"]["22.2"] = "LA Rise"
        cues = [dict(_CUE), {**_CUE, "bar": 2, "effect_preset_no": "22.2"}]
        outcomes = _outcomes(_grid(cues, **extra), ["22.1", "22.2"])
        commands_1, reason_1 = outcomes["22.1"]
        commands_2, reason_2 = outcomes["22.2"]
        assert reason_1 is None and reason_2 is None
        assert commands_1 is not None and commands_2 is not None
        assert "Store Preset 22.1 'LA Wave' /Universal" in commands_1
        assert "Store Preset 22.2 'LA Rise' /Universal" in commands_2

    def test_a_failed_first_number_does_not_block_the_second(self) -> None:
        extra = _recipe("22.2", label="LA Rise")
        extra["preset_labels"]["22.1"] = "LA Wave"  # 22.1 은 레시피 없음
        cues = [dict(_CUE), {**_CUE, "bar": 2, "effect_preset_no": "22.2"}]
        outcomes = _outcomes(_grid(cues, **extra), ["22.1", "22.2"])
        assert outcomes["22.1"] == (None, EFFECT_RECIPE_MISSING)
        assert outcomes["22.2"][1] is None


# -- 칸 판정(공용 plan_cells) ------------------------------------------------------


class TestCellScope:
    def test_buildable_number_releases_its_cell(self) -> None:
        plan = _plan(_grid([dict(_CUE)], **_recipe()), [_held("22.1")])
        assert plan.held == []
        assert [e["value"] for e in plan.released] == ["22.1"]
        assert set(plan.creations) == {"22.1"}
        assert plan.creation_fields == {"22.1": "effect_preset_no"}

    def test_unreadable_pool_never_creates(self) -> None:
        plan = _plan(_grid([dict(_CUE)], **_recipe()), [_held("22.1", reason=POOL_UNREAD_HOLD)])
        assert plan.creations == {}
        assert plan.held[0]["hold_reason"] == POOL_UNREAD_HOLD

    def test_plan_cells_own_entrance_refuses_a_non_empty_hold(self) -> None:
        # 호출자가 만들기 줄을 넘겨도, 「풀은 읽혔고 slot 이 없다」가 아닌 보류는 후보가
        # 아니다 — 덮어쓰기 0 의 근거가 이 함수 입구 하나에 있다(REQ-LDBEAT-015(i-7)).
        lines = ("Store Preset 22.1 'LA Wave' /Universal",)
        outcomes = {("effect_preset_no", "22.1"): (lines, None)}
        for reason in (POOL_UNREAD_HOLD, CELL_HOLD):
            plan = plan_cells([_held("22.1", reason=reason)], outcomes)
            assert plan.creations == {}, reason
            assert plan.released == [], reason

    def test_cell_with_another_empty_kind_stays_held(self) -> None:
        cue = {**_CUE, "color_preset_no": "4.99"}
        held = [_held("22.1"), _held("4.99", field="color_preset_no")]
        plan = _plan(_grid([cue], **_recipe()), held)
        assert plan.creations == {}
        reasons = {e["value"]: e["hold_reason"] for e in plan.held}
        assert reasons == {"22.1": CELL_HOLD, "4.99": EMPTY_PRESET_HOLD}


# -- 빈 프리셋 표식(t595 넓힘) ------------------------------------------------------


class TestEmptyMarkCreateOnApply:
    def test_buildable_pending_effect_number_is_marked_create(self) -> None:
        grid = _grid([dict(_CUE)], **_recipe())
        (cell,) = empty_preset_cells(grid, {22: {}})
        assert cell["state"] == "create"
        assert cell["fields"][0]["kind"] == "create_on_apply"
        assert cell["fields"][0]["reason"] == EFFECT_CREATE_ON_APPLY

    def test_missing_recipe_stays_empty_with_the_reason(self) -> None:
        grid = _grid([dict(_CUE)], preset_labels={"22.1": "LA Wave"})
        (cell,) = empty_preset_cells(grid, {22: {}})
        assert cell["state"] == "held"
        assert cell["fields"][0]["kind"] == "empty"
        assert EFFECT_RECIPE_MISSING in cell["fields"][0]["reason"]


# -- 세션 배선(가짜 콘솔) --------------------------------------------------------


def _pool(path: str, slots: list[int]) -> dict:
    return {"children": [{"i": slot, "name": f"P{slot}"} for slot in slots], "path": path}


def _apply(
    tmp_path,
    cues: list[dict],
    *,
    pool22: list[int] | None,
    grid_extra=None,
    decisions=(True, True, True, True, True),
):
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = cues
    timeline["beat_grid"].update(_recipe() if grid_extra is None else grid_extra)
    tree = _state_tree()
    if pool22 is not None:
        tree["DataPool/PresetPools/22"] = _pool("DataPool/PresetPools/22", pool22)
    store = SongTimelineStore()
    store.latest = timeline
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, state_tree=tree, decisions=decisions
    )
    status = session.beat_grid_apply()
    return status, store, approval, console


def _sent(approval) -> list[str]:
    return [item.command for request in approval.requests for item in request.items]


def _risk(approval) -> str:
    return " ".join(approval.requests[0].items[0].risk_reasons)


class TestApplyCreatesTheEffect:
    def test_creation_lines_ride_the_batch_and_cell_is_approved(self, tmp_path) -> None:
        status, store, approval, _console = _apply(tmp_path, [dict(_CUE)], pool22=[5])
        assert status["ok"] is True
        sent = _sent(approval)
        store_at = sent.index("Store Preset 22.1 'LA Wave' /Universal")
        assert sent[store_at + 1] == "Label Preset 22.1 'LA Wave'"
        risk = _risk(approval)
        assert "새로 만드는 효과 프리셋 1개" in risk
        assert "22.1 'LA Wave'" in risk and "sweep-soft-wide" in risk
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(cue) is None
        assert status["approval_vs_sent"]["match"] is True

    def test_occupied_slot_is_never_stored(self, tmp_path) -> None:
        status, _store, approval, _console = _apply(tmp_path, [dict(_CUE)], pool22=[1])
        assert status["ok"] is True
        assert not [c for c in _sent(approval) if c.startswith("Store Preset")]

    def test_unreadable_pool_is_never_stored(self, tmp_path) -> None:
        status, store, approval, _console = _apply(tmp_path, [dict(_CUE)], pool22=None)
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "22.1" in c]
        assert POOL_UNREAD_HOLD in status["reason"]
        assert check_evidence_approval(_cue_of(store.latest["beat_grid"], "BACK", 1)) is not None

    def test_missing_recipe_holds_with_reason(self, tmp_path) -> None:
        status, store, approval, _console = _apply(
            tmp_path, [dict(_CUE)], pool22=[5], grid_extra={"preset_labels": {"22.1": "LA Wave"}}
        )
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "22.1" in c]
        assert EFFECT_RECIPE_MISSING in status["reason"]
        assert check_evidence_approval(_cue_of(store.latest["beat_grid"], "BACK", 1)) is not None

    def test_two_new_effects_send_both_stores(self, tmp_path) -> None:
        """재현(카드 t605) — t593 우회(``EFFECT_BATCH_COLLISION``)가 걷히기 전에는
        한 반영에 효과 프리셋 둘을 실으면 둘째가 다음 반영으로 보류됐다. t601 뒤로
        ``run_commands`` 가 묶음 안 반복을 더는 건너뛰지 않으므로, 이제는 두 묶음
        전부(``ChangeDestination Root``·``Step 2`` 포함) 통째로, 그 순서대로
        콘솔까지 간다."""
        extra = _recipe("22.1")
        extra["preset_fx_recipes"]["22.2"] = {
            "fx_id": "wave-soft-rise",
            "period_unit": "beat",
            "period_value": 4,
        }
        extra["preset_labels"]["22.2"] = "LA Rise"
        cues = [dict(_CUE), {**_CUE, "bar": 2, "effect_preset_no": "22.2"}]
        grid = _grid(cues, **extra)
        # ``_apply``가 쓰는 ``_timeline()``의 곡 BPM(112.35)·박자(4)로 맞춰 계산해야
        # 콘솔로 나가는 줄과 글자까지 같다(기본 ``_BPM`` 120.0 과는 속도 줄이 다르다).
        outcomes = _outcomes(grid, ["22.1", "22.2"], bpm=112.35, beats_per_bar=4)
        bundle_1, reason_1 = outcomes["22.1"]
        bundle_2, reason_2 = outcomes["22.2"]
        assert reason_1 is None and reason_2 is None, (reason_1, reason_2)
        assert bundle_1 is not None and bundle_2 is not None

        status, _store, approval, console = _apply(tmp_path, cues, pool22=[5], grid_extra=extra)
        assert status["ok"] is True
        sent = _sent(approval)
        stores = [c for c in sent if c.startswith("Store Preset")]
        assert stores == [
            "Store Preset 22.1 'LA Wave' /Universal",
            "Store Preset 22.2 'LA Rise' /Universal",
        ]
        # 두 묶음이 겹치지 않고, 각자 만든 그대로 순서대로 콘솔에 닿는다.
        start_1 = sent.index(bundle_1[0])
        assert sent[start_1 : start_1 + len(bundle_1)] == list(bundle_1)
        start_2 = sent.index(bundle_2[0], start_1 + len(bundle_1))
        assert sent[start_2 : start_2 + len(bundle_2)] == list(bundle_2)
        assert console.executed == sent
        assert status["approval_vs_sent"]["match"] is True
        risk = _risk(approval)
        assert "새로 만드는 효과 프리셋 2개" in risk

    def test_refused_approval_creates_nothing(self, tmp_path) -> None:
        status, _store, _approval, console = _apply(
            tmp_path, [dict(_CUE)], pool22=[5], decisions=(False,)
        )
        assert status["ok"] is False
        assert not [c for c in console.executed if "Preset" in c]

    def test_overlap_with_a_cue_line_no_longer_stops_the_apply(self, tmp_path, monkeypatch) -> None:
        """재현(카드 t605) — t593 가 둔 겹침 가드(「효과 줄이 큐 줄과 겹치면 반영
        중단」)가 걷히기 전에는 큐 줄에 효과 줄과 같은 글자(``Step 2``)가 끼면
        반영 전체가 0 송신으로 멈췄다. t601 뒤로 그 글자가 겹쳐도 승인된 줄 모두가
        콘솔에 닿는다 — 가드가 막던 결함(묶음 안 반복 건너뛰기) 자체가 없다."""
        from server.web.session import ChatSession

        original = ChatSession._beat_grid_apply_cells

        def _with_step(result):
            return [*original(result), ("Step 2",)]

        monkeypatch.setattr(ChatSession, "_beat_grid_apply_cells", staticmethod(_with_step))
        status, _store, approval, console = _apply(tmp_path, [dict(_CUE)], pool22=[5])
        assert status["ok"] is True
        sent = _sent(approval)
        # 효과 묶음 안의 ``Step 2`` + 주입한 큐 줄의 ``Step 2`` — 둘 다 나간다.
        assert sent.count("Step 2") == 2
        assert "Store Preset 22.1 'LA Wave' /Universal" in sent
        assert console.executed == sent
        assert status["approval_vs_sent"]["match"] is True

    def test_approved_cell_empty_effect_is_created_too(self, tmp_path) -> None:
        # 카드 t600 규칙(승인된 칸의 빈 번호도 같은 보류·생성 규칙)이 효과에도 먹는다.
        approved = {"approval": {"by": "supervisor", "date": "2026-10-10", "source": "t593"}}
        status, store, approval, _console = _apply(
            tmp_path, [{**_CUE, "evidence": approved}], pool22=[5]
        )
        assert status["ok"] is True
        assert "Store Preset 22.1 'LA Wave' /Universal" in _sent(approval)
        risk = _risk(approval)
        assert "새로 만드는 효과 프리셋 1개" in risk
        assert "새로 만드는 프리셋 " not in risk  # 이미 승인된 칸 — 승인 기록 대상이 아니다
        assert check_evidence_approval(_cue_of(store.latest["beat_grid"], "BACK", 1)) is None

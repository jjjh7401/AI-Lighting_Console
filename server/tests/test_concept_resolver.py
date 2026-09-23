"""큐 상태 해석기 + 큐 모델 v2 + description 생성기 시험 — SPEC-LDDESIGN-001
M2 (REQ-LDDESIGN-017~025, 053~057, 062~063).

각 클래스는 REQ 를 명시적으로 인용한다. reduce 기준 상태 시험(AC-010)은
날조 대조군을 함께 쏜다(``verification-claim-integrity`` "양팔 대조") —
REQ-021 이 금지하는 "직전 트래킹 값 기준" 연쇄 곱셈을 손으로 직접
재현해, 정상 경로 시험의 비교가 그 결함을 실제로 구분해 낸다는 것을
보인다(비교가 공허하지 않음을 증명).
"""

from __future__ import annotations

import pytest

from server.concept.cue_model import (
    CueState,
    CueV2,
    Headroom,
    RemainingLevels,
    Timing,
    layer_limit_warning,
)
from server.concept.description import describe
from server.concept.resolver import (
    MOVE_SECONDS,
    SETTLE_SECONDS,
    apply,
    compute_headroom,
    mib_verdict,
    resolve_sequence,
    section_base_name,
)
from server.concept.vocab import VocabError


def _state(dim=None, color=None, pos="home", motion=0):
    return CueState(dim=dim or {}, color=color, pos=pos, motion=motion)


def _make_cue_v2(
    *,
    layer=frozenset({"visibility"}),
    operation="retain",
    tracking="track",
    evidence="designed_rule",
    description="테스트 큐",
    timing=None,
    headroom=None,
    mib=None,
    state=None,
):
    return CueV2(
        layer=layer,
        operation=operation,
        tracking=tracking,
        timing=timing or Timing(kind="short", seconds=1.0, attr_split=False, stagger=None),
        evidence=evidence,
        headroom=headroom
        or Headroom(
            unused_groups=5,
            reserved_colors=(),
            reserved_effects=(),
            remaining=RemainingLevels(motion=3, dimmer=100),
        ),
        mib=mib,
        description=description,
        state=state or _state(),
    )


class TestApplyEachOperation:
    """REQ-LDDESIGN-019 — 9종 동작 각각을 개별로 잰다."""

    def test_retain_leaves_state_unchanged(self):
        start = _state(dim={"KEY": 50}, color="Blue", pos="home", motion=1)
        result = apply(start, [{"op": "retain"}], {})
        assert result.dim == {"KEY": 50}
        assert result.color == "Blue"
        assert result.pos == "home"
        assert result.motion == 1

    def test_add_takes_max_of_existing_and_new(self):
        start = _state(dim={"KEY": 50})
        result = apply(start, [{"op": "add", "roles": ["KEY", "FOH"], "dimmer": 30}], {})
        # KEY 는 기존 50 이 30 보다 크므로 유지, FOH 는 새로 30.
        assert result.dim == {"KEY": 50, "FOH": 30}

    def test_remove_zeroes_named_roles(self):
        start = _state(dim={"KEY": 50, "FOH": 40})
        result = apply(start, [{"op": "remove", "roles": ["KEY"]}], {})
        assert result.dim == {"KEY": 0, "FOH": 40}

    def test_reduce_scales_referenced_base_by_factor(self):
        base = _state(dim={"KEY": 50, "FOH": 50})
        result = apply(
            _state(dim={"KEY": 999}),
            [{"op": "reduce", "factor": 0.5, "ref": "Verse 1"}],
            {"Verse 1": base},
        )
        assert result.dim == {"KEY": 25, "FOH": 25}

    def test_replace_sets_color(self):
        start = _state(color="Blue")
        result = apply(start, [{"op": "replace", "color": "Red"}], {})
        assert result.color == "Red"

    def test_isolate_keeps_only_named_role(self):
        start = _state(dim={"KEY": 50, "FOH": 40, "BACK": 30})
        result = apply(start, [{"op": "isolate", "role": "FOH", "dimmer": 90}], {})
        assert result.dim == {"KEY": 0, "FOH": 90, "BACK": 0}

    def test_expand_sets_absolute_value(self):
        start = _state(dim={"KEY": 10})
        result = apply(start, [{"op": "expand", "roles": ["KEY"], "dimmer": 80}], {})
        assert result.dim == {"KEY": 80}

    def test_restore_copies_dim_color_motion(self):
        base = _state(dim={"KEY": 75}, color="Amber", pos="back", motion=2)
        start = _state(dim={"KEY": 10}, color="Blue", pos="front", motion=0)
        result = apply(start, [{"op": "restore", "ref": "Chorus 1"}], {"Chorus 1": base})
        assert result.dim == {"KEY": 75}
        assert result.color == "Amber"
        assert result.motion == 2

    def test_restore_does_not_restore_position(self):
        """AC-LDDESIGN-030 — restore 는 포지션을 복원하지 않는다(REQ-020)."""
        base = _state(pos="back")
        start = _state(pos="front")
        result = apply(start, [{"op": "restore", "ref": "Chorus 1"}], {"Chorus 1": base})
        assert result.pos == "front"

    def test_release_sets_role_dimmer(self):
        start = _state(dim={"BLIND": 0})
        result = apply(start, [{"op": "release", "role": "BLIND", "dimmer": 90}], {})
        assert result.dim == {"BLIND": 90}

    def test_pos_and_motion_keys_apply_after_op(self):
        start = _state(pos="home", motion=0)
        result = apply(
            start,
            [{"op": "expand", "roles": ["KEY"], "dimmer": 50, "pos": "side", "motion": 2}],
            {},
        )
        assert result.pos == "side"
        assert result.motion == 2

    def test_restore_with_unknown_ref_raises(self):
        with pytest.raises(VocabError):
            apply(_state(), [{"op": "restore", "ref": "Chorus 9"}], {})

    def test_unknown_operation_rejected(self):
        with pytest.raises(VocabError):
            apply(_state(), [{"op": "explode"}], {})


class TestReduceBaseSelection:
    """REQ-LDDESIGN-021 — reduce 의 기준 상태는 (a) 명시된 ref 또는 (b) 그
    구간의 자기 1회차 값이다 — 직전 트래킹 상태(연쇄 곱셈)를 참조하지
    않는다."""

    def test_reduce_without_ref_falls_back_to_section_base(self):
        section_base = section_base_name("Verse")
        base = _state(dim={"KEY": 50})
        result = apply(
            _state(dim={"KEY": 999}),
            [{"op": "reduce", "factor": 0.5}],
            {section_base: base},
            section_base=section_base,
        )
        assert result.dim == {"KEY": 25}

    def test_reduce_with_unknown_ref_raises(self):
        with pytest.raises(VocabError):
            apply(_state(), [{"op": "reduce", "factor": 0.5, "ref": "Verse 9"}], {})

    def test_reduce_with_no_ref_and_no_section_base_raises(self):
        with pytest.raises(VocabError):
            apply(_state(dim={"KEY": 40}), [{"op": "reduce", "factor": 0.5}], {})

    def test_reduce_with_missing_ref_never_falls_back_to_section_base(self):
        """ref 가 주어졌는데 bases 에 없으면, section_base 가 (다른 이름으로)
        있어도 그쪽으로 조용히 바꿔 타지 않고 그대로 예외를 던진다."""
        section_base = section_base_name("Verse")  # "Verse 1"
        with pytest.raises(VocabError):
            apply(
                _state(),
                [{"op": "reduce", "factor": 0.5, "ref": "Verse 99"}],  # bases 에 없는 이름
                {section_base: _state(dim={"KEY": 10})},  # section_base 만 있음
                section_base=section_base,
            )

    def test_same_factor_on_occurrence_2_and_3_yields_identical_top_brightness(self):
        """AC-LDDESIGN-010 — Too Cool 실측(구간 기준 50 에 factor 0.5 를
        연쇄 적용해 50→25→12 로 겹쳐 곱해진 결함)을 재현하지 않는다: 절 1
        기준 50 에 factor 0.5 를 2·3회차에 똑같이 적용하면 둘 다 25 다 —
        한쪽이 다른 쪽의 결과를 기준으로 삼지 않는다."""
        rows = [
            {
                "section": "Verse",
                "occurrence": 1,
                "ops": [{"op": "expand", "roles": ["KEY"], "dimmer": 50}],
            },
            {"section": "Verse", "occurrence": 2, "ops": [{"op": "reduce", "factor": 0.5}]},
            {"section": "Verse", "occurrence": 3, "ops": [{"op": "reduce", "factor": 0.5}]},
        ]
        states = resolve_sequence(rows)
        tops = {max(s.dim.values()) for s in states[1:]}
        assert tops == {25}
        assert states[1].dim == {"KEY": 25}
        assert states[2].dim == {"KEY": 25}

    def test_fabricated_control_reproduces_forbidden_chained_reduction(self):
        """날조 대조군(verification-claim-integrity "양팔 대조") — REQ-021 가
        금지하는 "직전 트래킹 값 기준" reduce 를 손으로 직접 재현해, 위
        시험의 비교가 그 결함을 실제로 구분해 낸다는 것을 보인다. 이
        대조군은 해석기가 아니라 금지된 대안(직전 결과를 기준 상태로
        재등록)을 흉내 낸다 — 해석기 자체가 이 결함을 갖고 있다는 주장이
        아니다.
        """
        base = _state(dim={"KEY": 50})
        step_1 = apply(
            base, [{"op": "reduce", "factor": 0.5}], {"carry": base}, section_base="carry"
        )
        # 금지된 모양: 직전 결과(step_1)를 다음 reduce 의 기준으로 재등록한다.
        step_2 = apply(
            step_1,
            [{"op": "reduce", "factor": 0.5}],
            {"carry": step_1},
            section_base="carry",
        )
        assert step_1.dim == {"KEY": 25}
        assert step_2.dim == {"KEY": 12}  # 50 → 25 → 12, 겹쳐 곱해짐(금지된 모양)
        # 위 정상 경로 시험의 결과({25, 25})와 이 대조군의 결과(12)가
        # 다르므로, 그 비교는 이 결함을 실제로 구분해 낸다.
        assert step_2.dim != {"KEY": 25}


class TestResolveSequenceTracking:
    """REQ-LDDESIGN-053~057 — Track 누적, Cue Only 비전파."""

    def test_track_carries_forward(self):
        rows = [
            {
                "section": "Intro",
                "occurrence": 1,
                "ops": [{"op": "expand", "roles": ["KEY"], "dimmer": 10}],
                "tracking": "track",
            },
            {
                "section": "Intro",
                "occurrence": 1,
                "ops": [{"op": "add", "roles": ["FOH"], "dimmer": 20}],
                "tracking": "track",
            },
        ]
        states = resolve_sequence(rows)
        assert states[1].dim == {"KEY": 10, "FOH": 20}

    def test_cue_only_does_not_carry_to_next_cue(self):
        """REQ-057 — cue_only 큐는 다음 큐로 전파되지 않는다: 다음 큐는 그
        cue_only 큐 이전 상태에서 시작한다."""
        rows = [
            {
                "section": "Chorus",
                "occurrence": 1,
                "ops": [{"op": "expand", "roles": ["KEY"], "dimmer": 70}],
                "tracking": "track",
            },
            {
                "section": "Chorus",
                "occurrence": 1,
                "ops": [{"op": "add", "roles": ["WASH-U"], "dimmer": 90}],
                "tracking": "cue_only",
            },
            {
                "section": "Chorus",
                "occurrence": 1,
                "ops": [{"op": "add", "roles": ["FOH"], "dimmer": 50}],
                "tracking": "track",
            },
        ]
        states = resolve_sequence(rows)
        assert states[1].dim == {"KEY": 70, "WASH-U": 90}
        assert "WASH-U" not in states[2].dim
        assert states[2].dim == {"KEY": 70, "FOH": 50}

    def test_base_name_registers_explicit_ref(self):
        rows = [
            {
                "section": "Chorus",
                "occurrence": 1,
                "ops": [{"op": "expand", "roles": ["KEY"], "dimmer": 75}],
                "base_name": "Chorus 1",
            },
            {"section": "Chorus", "occurrence": 2, "ops": [{"op": "restore", "ref": "Chorus 1"}]},
        ]
        states = resolve_sequence(rows)
        assert states[1].dim == {"KEY": 75}


class TestVocabRejection:
    """REQ-LDDESIGN-016 과 같은 방향 — 어휘 밖 값은 조립을 거부한다."""

    def test_empty_layer_rejected(self):
        with pytest.raises(VocabError):
            _make_cue_v2(layer=frozenset())

    def test_bad_layer_rejected(self):
        with pytest.raises(VocabError):
            _make_cue_v2(layer=frozenset({"lighting"}))

    def test_bad_operation_rejected(self):
        with pytest.raises(VocabError):
            _make_cue_v2(operation="explode")

    def test_bad_tracking_rejected(self):
        with pytest.raises(VocabError):
            _make_cue_v2(tracking="looping")

    def test_bad_evidence_rejected(self):
        with pytest.raises(VocabError):
            _make_cue_v2(evidence="guessed")

    def test_bad_timing_kind_rejected(self):
        with pytest.raises(VocabError):
            Timing(kind="medium", seconds=1.0, attr_split=False, stagger=None)


class TestCueV2EndToEnd:
    """AC-LDDESIGN-030 — 큐 모델 v2 필드 7종 전부 채워짐."""

    def test_restore_carrying_chorus_cue_has_all_seven_fields_and_nonempty_description(self):
        chorus_1_state = _state(dim={"KEY": 75, "FOH": 75}, color="Warm", pos="back", motion=1)
        bases = {"Chorus 1": chorus_1_state}
        prev = _state(dim={"KEY": 20}, color="Cool", pos="side", motion=0)
        ops = [
            {"op": "restore", "ref": "Chorus 1"},
            {
                "op": "expand",
                "roles": ["WASH-U", "WASH-D"],
                "dimmer": 90,
                "pos": "front",
                "motion": 2,
            },
        ]
        state = apply(prev, ops, bases)
        headroom = compute_headroom(
            state,
            all_groups=["KEY", "FOH", "WASH-U", "WASH-D", "MOVER-U", "MOVER-D"],
            reserved_colors_remaining=["흰색"],
            reserved_effects=["STROBE"],
        )
        description = describe(prev, state, ops, headroom)
        cue = CueV2(
            layer=frozenset({"visibility", "environment"}),
            operation="restore",
            tracking="track",
            timing=Timing(
                kind="snap", seconds=0.3, attr_split=("color",), stagger="0→0.4s 중앙→외곽"
            ),
            evidence="designed_rule",
            headroom=headroom,
            mib=None,
            description=description,
            state=state,
        )
        # REQ-017 — 7필드 전부 채워짐.
        assert cue.layer and cue.layer <= {
            "visibility",
            "environment",
            "architecture",
            "motion",
            "punctuation",
        }
        assert cue.operation == "restore"
        assert cue.tracking in ("block", "track", "cue_only", "release")
        assert cue.timing.kind == "snap"
        assert cue.evidence in ("verified", "practitioner_pattern", "designed_rule", "director")
        assert cue.headroom.unused_groups >= 0
        assert cue.mib is None  # 포지션 변화는 있었지만 mib 는 이 시험 범위 밖(REQ-062 별도)
        # description — 비어 있지 않고, 복원·색 변화를 서술한다(REQ-023/070).
        assert cue.description != ""
        assert "Chorus 1 복원" in cue.description
        # restore 는 색을 포함해 복원한다(REQ-020) — Cool 에서 Warm 으로.
        assert state.color == "Warm"


class TestLayerLimitWarning:
    """REQ-LDDESIGN-018 — 초과 시 린트 경고, 이내면 None."""

    def test_section_cue_within_limit_is_none(self):
        assert layer_limit_warning("section", {"visibility", "environment", "architecture"}) is None

    def test_section_cue_over_limit_warns(self):
        warning = layer_limit_warning(
            "section", {"visibility", "environment", "architecture", "motion"}
        )
        assert warning is not None

    def test_phrase_cue_within_limit_is_none(self):
        assert layer_limit_warning("phrase", {"visibility", "environment"}) is None

    def test_phrase_cue_over_limit_warns(self):
        warning = layer_limit_warning("phrase", {"visibility", "environment", "architecture"})
        assert warning is not None

    def test_beat_accent_exactly_punctuation_is_none(self):
        assert layer_limit_warning("beat_accent", {"punctuation"}) is None

    def test_beat_accent_with_extra_layer_warns(self):
        warning = layer_limit_warning("beat_accent", {"punctuation", "motion"})
        assert warning is not None


class TestComputeHeadroom:
    """REQ-LDDESIGN-025/050 — 4축."""

    def test_four_axes_computed(self):
        state = _state(dim={"KEY": 60, "FOH": 60}, motion=1)
        headroom = compute_headroom(
            state,
            all_groups=["KEY", "FOH", "BACK", "SIDE-L"],
            reserved_colors_remaining=["흰색"],
            reserved_effects=["STROBE", "BLIND"],
        )
        assert headroom.unused_groups == 2  # BACK, SIDE-L
        assert headroom.reserved_colors == ("흰색",)
        assert headroom.reserved_effects == ("STROBE", "BLIND")
        assert headroom.remaining.motion == 2  # 3 - 1
        assert headroom.remaining.dimmer == 40  # 100 - 60


class TestMibVerdict:
    """REQ-LDDESIGN-062 — dark/mark/live 각각을 잰다."""

    MOVERS = ("MOVER-U", "MOVER-D")

    def test_no_position_change_is_none(self):
        prev = _state(pos="home")
        cur = _state(pos="home")
        assert mib_verdict(prev, cur, ts=10.0, dark_since=0.0, movers=self.MOVERS) is None

    def test_dark_when_movers_stay_off(self):
        prev = _state(dim={"MOVER-U": 0}, pos="home")
        cur = _state(dim={"MOVER-U": 0}, pos="back")
        verdict = mib_verdict(prev, cur, ts=1.0, dark_since=0.0, movers=self.MOVERS)
        assert verdict.status == "dark"

    def test_mark_when_off_long_enough(self):
        prev = _state(dim={"MOVER-U": 0}, pos="home")
        cur = _state(dim={"MOVER-U": 50}, pos="back")
        window_ts = MOVE_SECONDS + SETTLE_SECONDS + 1.0
        verdict = mib_verdict(prev, cur, ts=window_ts, dark_since=0.0, movers=self.MOVERS)
        assert verdict.status == "mark"
        assert verdict.mark_insert_at is not None

    def test_live_when_movers_stay_on(self):
        prev = _state(dim={"MOVER-U": 50}, pos="home")
        cur = _state(dim={"MOVER-U": 50}, pos="back")
        verdict = mib_verdict(prev, cur, ts=1.0, dark_since=0.0, movers=self.MOVERS)
        assert verdict.status == "live"
        assert verdict.mark_insert_at is None

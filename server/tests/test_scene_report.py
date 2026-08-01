"""Scene report tests (M5 — AC-SCENE-015, AC-SCENE-016, AC-SCENE-024).

REQ-SCENE-014 asks for one thing above all: the report must keep FOUR claims
apart. Three of them are about what was NOT established, and the whole SPEC
turns on a reader not collapsing them into "확인했다":

* (a)  the artifact exists — machine-confirmed, but only by a re-query, and a
       re-query proves EXISTENCE and nothing else.
* (a′) the value line carried the uniform set in order — machine-confirmed by a
       static read of the emitted string, never by asking the console.
* (b)  the effect — never machine-confirmable. Unconditional on every path.
* (c)  tracking neutralisation — not merely unconfirmed but UNOBSERVABLE: there
       is no channel at all (spec.md §C.1).
* (d)  the attributes this scene does not assert — enumerated, and claimed only
       as "이월될 수 있다".

The failure mode this file exists to prevent is (a′) being read as evidence for
(c). That was the `/CueOnly` failure, the policy changed, and the cognitive trap
did not (design.md §6.2) — so the tests below assert the two are separate
constants, in separate paragraphs, and that (c)'s own wording denies the
inference rather than staying silent about it.

Verification is by CONSTANT IDENTITY (`payload[...] == CONSTANT`), never by
prose substring — `test_a_substring_check_would_miss_a_truncated_notice` proves
why with a mutation a substring check demonstrably lets through.
"""

from __future__ import annotations

import pytest

from server.fx.instantiate import CROSS_CALL_COLLISION
from server.scene.compile import SCENE_UNIFORM_ATTRIBUTES, SceneCompilation
from server.scene.report import (
    ARTIFACT_CONFIRMED_NOTE,
    ARTIFACT_UNVERIFIED_NOTE,
    COLLIDED_ENUMERATION_NOTE,
    COMPLETE,
    CROSS_CALL_COLLISION_NOTE,
    EFFECT_EVIDENCE_NOTICE,
    PARTIAL,
    PLANNED,
    TRACKING_UNOBSERVABLE_NOTICE,
    UNCLAIMED_ENUMERATION_NOTE,
    UNIFORM_CONFIRMED_NOTE,
    UNIFORM_NOT_APPLICABLE_NOTE,
    SceneReport,
    build_report,
    to_korean,
)

LOOK_VALUE_LINE = (
    "Attribute 'Dimmer' At 80 ; Attribute 'ColorRGB_R' At 10 ; "
    "Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 30"
)
BROKEN_VALUE_LINE = (
    "Attribute 'ColorRGB_R' At 10 ; Attribute 'Dimmer' At 80 ; "
    "Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 30"
)


def _commands(*, value_line: str | None = LOOK_VALUE_LINE, steps: bool = True) -> tuple[str, ...]:
    lines = ["ChangeDestination Root", "ClearAll", "Group 11"]
    if value_line is not None:
        lines.append(value_line)
    if steps:
        lines.extend(["Attribute 'Dimmer' At 100", "Step 2", "Attribute 'Dimmer' At 0"])
    lines.extend(["Store Sequence 21 Cue 3 'SCN X'", "ClearAll"])
    return tuple(lines)


def _compilation(**overrides) -> SceneCompilation:
    data = {
        "scene_id": "blue-wave",
        "display_name": "파란 웨이브",
        "label": "SCN X",
        "group": 11,
        "sequence": 21,
        "cue": 3,
        "look_id": "look-blue",
        "fx_id": "pulse-beat",
        "commands": _commands(),
        "collided_attributes": ("Dimmer",),
        "unclaimed_attributes": ("Iris", "Pan", "Tilt", "Zoom"),
    }
    data.update(overrides)
    return SceneCompilation(**data)


def _outcome(command: str, status: str) -> dict:
    return {"command": command, "status": status}


def _all_ok(compilation: SceneCompilation) -> list[dict]:
    return [_outcome(c, "executed_ok") for c in compilation.commands]


class TestClaimsAreSeparateConstants:
    """AC-SCENE-015 — four claims, four constants, no merging."""

    def test_every_claim_is_its_own_constant(self):
        claims = [
            ARTIFACT_CONFIRMED_NOTE,
            UNIFORM_CONFIRMED_NOTE,
            EFFECT_EVIDENCE_NOTICE,
            TRACKING_UNOBSERVABLE_NOTICE,
            UNCLAIMED_ENUMERATION_NOTE,
        ]
        assert len(set(claims)) == len(claims)

    def test_the_payload_carries_each_claim_by_identity(self):
        payload = build_report(_compilation()).to_dict()
        assert payload["claims"]["artifact"] == ARTIFACT_UNVERIFIED_NOTE
        assert payload["claims"]["uniform"] == UNIFORM_CONFIRMED_NOTE
        assert payload["claims"]["effect"] == EFFECT_EVIDENCE_NOTICE
        assert payload["claims"]["tracking"] == TRACKING_UNOBSERVABLE_NOTICE
        assert payload["claims"]["unclaimed"] == UNCLAIMED_ENUMERATION_NOTE

    def test_the_tracking_claim_names_the_absent_channel(self):
        # (c) is not "unconfirmed", it is UNOBSERVABLE — a different fact, and
        # the one a reader is most likely to soften.
        assert "관측 채널" in TRACKING_UNOBSERVABLE_NOTICE

    def test_the_tracking_claim_denies_the_uniformity_inference(self):
        # Mutation ③: wording the uniform check as grounds for neutralisation.
        # Silence is not enough — the notice must refuse the inference out loud,
        # because the reader makes it by default (design.md §6.2).
        assert "증거가 아닙니다" in TRACKING_UNOBSERVABLE_NOTICE
        for affirmative in ("무해해졌습니다", "해결됐습니다", "트래킹이 차단"):
            assert affirmative not in TRACKING_UNOBSERVABLE_NOTICE

    def test_the_effect_claim_says_a_human_must_look(self):
        assert "사람" in EFFECT_EVIDENCE_NOTICE
        assert "기계 확인 불가" in EFFECT_EVIDENCE_NOTICE


class TestTheEffectClaimIsUnconditional:
    """AC-SCENE-015 (b) — every path, success included."""

    @pytest.mark.parametrize(
        "outcomes",
        [
            None,
            "all_ok",
            "failed",
            "collided",
        ],
    )
    def test_the_effect_notice_is_present_on_every_path(self, outcomes):
        compilation = _compilation()
        if outcomes == "all_ok":
            listed = _all_ok(compilation)
        elif outcomes == "failed":
            listed = [_outcome(compilation.commands[0], "failed")]
        elif outcomes == "collided":
            listed = [_outcome("Step 2", "skipped_already_executed")]
        else:
            listed = None
        report = build_report(compilation, listed)
        assert report.to_dict()["claims"]["effect"] == EFFECT_EVIDENCE_NOTICE
        assert EFFECT_EVIDENCE_NOTICE in to_korean(report)

    def test_the_success_path_still_carries_it(self):
        compilation = _compilation()
        report = build_report(compilation, _all_ok(compilation))
        assert report.verdict == COMPLETE
        assert report.succeeded is True
        assert EFFECT_EVIDENCE_NOTICE in to_korean(report)


class TestUniformityAndTrackingStayApart:
    """AC-SCENE-015 — (a′) and (c) never share a paragraph."""

    def test_no_single_line_carries_both_claims(self):
        text = to_korean(build_report(_compilation()))
        for line in text.splitlines():
            assert not (UNIFORM_CONFIRMED_NOTE in line and TRACKING_UNOBSERVABLE_NOTICE in line)

    def test_the_two_claims_sit_under_different_headings(self):
        lines = to_korean(build_report(_compilation())).splitlines()
        uniform_at = next(i for i, line in enumerate(lines) if UNIFORM_CONFIRMED_NOTE in line)
        tracking_at = next(
            i for i, line in enumerate(lines) if TRACKING_UNOBSERVABLE_NOTICE in line
        )
        between = lines[uniform_at + 1 : tracking_at]
        # Something separates them; adjacency is what makes the misreading easy.
        assert between
        assert any(line.strip().startswith("기계 확인 불가") for line in between)


class TestUniformityClaimTracksTheEmittedString:
    """AC-SCENE-015 (a′) — a STATIC read of the bundle, not a promise."""

    def test_a_look_bearing_scene_reports_the_uniform_attributes_in_order(self):
        report = build_report(_compilation())
        assert report.uniform_attributes == SCENE_UNIFORM_ATTRIBUTES
        assert report.to_dict()["uniform_attributes"] == list(SCENE_UNIFORM_ATTRIBUTES)

    def test_an_fx_only_scene_is_not_subject_to_the_claim(self):
        compilation = _compilation(
            look_id=None,
            commands=_commands(value_line=None),
            collided_attributes=(),
        )
        report = build_report(compilation)
        assert report.uniform_attributes == ()
        assert report.to_dict()["claims"]["uniform"] == UNIFORM_NOT_APPLICABLE_NOTE

    def test_a_value_line_out_of_order_is_reported_as_such(self):
        # The claim is derived from the emitted string, so a bundle that does
        # not carry the order cannot produce the confirming notice.
        compilation = _compilation(commands=_commands(value_line=BROKEN_VALUE_LINE))
        report = build_report(compilation)
        assert report.uniform_attributes != SCENE_UNIFORM_ATTRIBUTES
        assert report.to_dict()["claims"]["uniform"] != UNIFORM_CONFIRMED_NOTE


class TestArtifactClaimNeedsARequery:
    """AC-SCENE-015 (a) — firing is not existing."""

    def test_without_a_requery_the_artifact_is_not_claimed_as_confirmed(self):
        payload = build_report(_compilation()).to_dict()
        assert payload["claims"]["artifact"] == ARTIFACT_UNVERIFIED_NOTE
        assert payload["requery"] is None

    def test_with_a_requery_the_names_and_cue_no_are_carried(self):
        report = build_report(
            _compilation(),
            requery={"sequence_name": "Sequence 21", "cue_name": "SCN X", "cue_no": 3},
        )
        payload = report.to_dict()
        assert payload["claims"]["artifact"] == ARTIFACT_CONFIRMED_NOTE
        assert payload["requery"] == {
            "sequence_name": "Sequence 21",
            "cue_name": "SCN X",
            "cue_no": 3,
        }

    def test_the_artifact_notice_limits_itself_to_existence(self):
        assert "존재" in ARTIFACT_CONFIRMED_NOTE
        assert "효과" not in ARTIFACT_CONFIRMED_NOTE


class TestTwoEnumerationsAreDistinguished:
    """AC-SCENE-016 + AC-SCENE-024 — collided ≠ unclaimed."""

    def test_both_enumerations_reach_the_payload(self):
        payload = build_report(_compilation()).to_dict()
        assert payload["collided_attributes"] == ["Dimmer"]
        assert payload["unclaimed_attributes"] == ["Iris", "Pan", "Tilt", "Zoom"]

    def test_each_enumeration_has_its_own_heading(self):
        text = to_korean(build_report(_compilation()))
        assert COLLIDED_ENUMERATION_NOTE in text
        assert UNCLAIMED_ENUMERATION_NOTE in text
        assert COLLIDED_ENUMERATION_NOTE != UNCLAIMED_ENUMERATION_NOTE

    def test_the_unclaimed_notice_claims_only_possibility(self):
        # Mutation ⑥ — "이월됩니다" is a claim about what happened, and nothing
        # can observe that (AC-SCENE-024, same discipline as (c)).
        assert "이월될 수 있습니다" in UNCLAIMED_ENUMERATION_NOTE
        assert "이월됩니다" not in UNCLAIMED_ENUMERATION_NOTE
        # 부정형("이월됐다는 뜻이 아닙니다")은 있어야 하고 단정형은 없어야 한다 —
        # `"이월됐"` 자체를 금지하면 그 부정문까지 잡는 위양성이 된다.
        assert "이월됐다는 뜻이 아닙니다" in UNCLAIMED_ENUMERATION_NOTE
        assert "이월됐습니다" not in UNCLAIMED_ENUMERATION_NOTE

    def test_the_enumeration_is_sorted_deterministically(self):
        # Mutation ⑦ — set iteration order must not reach the report. The
        # compiler already sorts; the report sorts again rather than trusting
        # its input, because a caller can build a SceneCompilation by hand.
        report = build_report(_compilation(unclaimed_attributes=("Zoom", "Pan", "Iris", "Tilt")))
        assert report.unclaimed_attributes == ("Iris", "Pan", "Tilt", "Zoom")

    def test_the_collided_enumeration_is_sorted_too(self):
        report = build_report(_compilation(collided_attributes=("Dimmer", "ColorRGB_R")))
        assert report.collided_attributes == ("ColorRGB_R", "Dimmer")

    def test_pan_and_tilt_appear_for_a_scene_that_drives_neither(self):
        # spec.md §D — the axis uniformity cannot close is named, not hidden.
        text = to_korean(build_report(_compilation()))
        assert "Pan" in text
        assert "Tilt" in text


class TestExecutionResultsPropagate:
    """AC-SCENE-016 — failures, not_executed and folded lines all surface."""

    def test_no_outcomes_is_a_planned_verdict(self):
        report = build_report(_compilation())
        assert report.verdict == PLANNED
        assert report.executed is False
        assert report.succeeded is False
        assert "실행 결과를 관측하지 않은" in to_korean(report)

    def test_a_failure_is_partial_and_never_success(self):
        compilation = _compilation()
        listed = [
            _outcome(compilation.commands[0], "executed_ok"),
            _outcome(compilation.commands[1], "failed"),
            _outcome(compilation.commands[2], "not_executed"),
        ]
        report = build_report(compilation, listed)
        assert report.verdict == PARTIAL
        assert report.succeeded is False
        assert report.failed == (compilation.commands[1],)
        assert report.not_executed == (compilation.commands[2],)
        text = to_korean(report)
        assert compilation.commands[1] in text
        assert compilation.commands[2] in text


class TestCrossCallCollisionForbidsSuccess:
    """AC-SCENE-011 (b) / AC-SCENE-016 — a folded non-exempt line is a failure."""

    def test_a_non_exempt_fold_is_reported_as_a_cross_call_collision(self):
        compilation = _compilation()
        listed = [
            _outcome("Step 2", "skipped_already_executed"),
            _outcome("Store Sequence 21 Cue 3 'SCN X'", "executed_ok"),
        ]
        report = build_report(compilation, listed)
        assert report.verdict == CROSS_CALL_COLLISION
        assert report.succeeded is False
        assert report.collided == ("Step 2",)

    def test_the_collision_text_warns_that_an_incomplete_cue_may_exist(self):
        compilation = _compilation()
        report = build_report(compilation, [_outcome("Step 2", "skipped_already_executed")])
        text = to_korean(report)
        assert CROSS_CALL_COLLISION_NOTE in text
        assert "불완전" in CROSS_CALL_COLLISION_NOTE

    def test_an_exempt_fold_is_not_a_collision(self):
        # `ClearAll` repeats harmlessly; treating it as a collision would make
        # the guard cry wolf on every ordinary bundle.
        compilation = _compilation()
        listed = [
            _outcome("ClearAll", "skipped_already_executed"),
            *(_outcome(c, "executed_ok") for c in compilation.commands if c != "ClearAll"),
        ]
        report = build_report(compilation, listed)
        assert report.collided == ()
        assert report.verdict == COMPLETE


class TestKoreanReportIsTwoTier:
    """AC-SCENE-016 — a summary tier and a detail tier, both present."""

    def test_the_summary_line_names_the_artifact_and_the_verdict(self):
        text = to_korean(build_report(_compilation()))
        first = text.splitlines()[0]
        assert "시퀀스 21" in first
        assert "큐 3" in first
        assert "SCN X" in first

    def test_the_detail_tier_exists(self):
        text = to_korean(build_report(_compilation()))
        assert any(line.startswith("상세:") for line in text.splitlines())

    def test_the_report_names_the_look_and_the_fx(self):
        text = to_korean(build_report(_compilation()))
        assert "look-blue" in text
        assert "pulse-beat" in text


class TestConstantIdentityIsRequired:
    """plan.md §B M5 mutation ④ — why prose comparison is banned."""

    def test_a_substring_check_would_miss_a_truncated_notice(self):
        tampered = EFFECT_EVIDENCE_NOTICE[: len(EFFECT_EVIDENCE_NOTICE) // 2]
        # A substring assertion passes on the mutilated text...
        assert tampered in EFFECT_EVIDENCE_NOTICE
        # ...while identity catches it. That gap is the whole argument for
        # `payload[...] == CONSTANT` (선례 test_songcue_report.py:119).
        assert tampered != EFFECT_EVIDENCE_NOTICE


class TestReportShape:
    def test_build_report_returns_a_scene_report(self):
        assert isinstance(build_report(_compilation()), SceneReport)

    def test_the_payload_carries_the_compilation_facts(self):
        payload = build_report(_compilation()).to_dict()
        for key in ("scene_id", "sequence", "cue", "label", "group", "look_id", "fx_id"):
            assert key in payload
        assert payload["command_count"] == len(_compilation().commands)


class TestOptionalAxesReachTheDetailTier:
    """AC-SCENE-016 — what the bundle carried must be readable in the report."""

    def test_a_trigger_is_named_with_its_absolute_time(self):
        report = build_report(_compilation(trig_type="Follow", trig_time=14.0))
        text = to_korean(report)
        assert "트리거 Follow" in text
        assert "14" in text

    def test_an_executor_is_named_and_marked_explicit(self):
        # REQ-SCENE-017 — an executor is never automatic, so the report says
        # whose decision it was.
        text = to_korean(build_report(_compilation(executor=7)))
        assert "익스큐터 7" in text
        assert "사용자 명시 지정" in text

    def test_a_requery_is_rendered_with_names_and_cue_no(self):
        report = build_report(
            _compilation(),
            requery={"sequence_name": "Sequence 21", "cue_name": "SCN X", "cue_no": 3},
        )
        text = to_korean(report)
        assert "재조회" in text
        assert "Sequence 21" in text
        assert "cueNo 3" in text

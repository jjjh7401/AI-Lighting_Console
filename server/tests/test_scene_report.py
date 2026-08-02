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

Placement is verified by INDEX, not by presence. `to_korean` files (a) under
whichever of the two headings its wording actually matches, and a report that
prints both headings passes every `in text` check no matter which claim sits
under which — that gap is what let an unverified artifact live under
`기계 확인됨:` all the way to a pre-merge review.
"""

from __future__ import annotations

import pytest

from server.fx.instantiate import CROSS_CALL_COLLISION
from server.fx.loader import load_library_from_dir as load_fx_library
from server.looks.loader import load_library_from_dir as load_look_library
from server.orchestrator.tools import rig_section
from server.scene.compile import SCENE_UNIFORM_ATTRIBUTES, SceneCompilation, compile_scene
from server.scene.loader import load_library_from_dir as load_scene_library
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
    UNIFORM_BROKEN_NOTE,
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

# `_speed_line`의 실물 산출(`server/fx/instantiate.py:417`) — fx도 `;` 체인을 낸다.
# 이 모양이 픽스처에 없었던 것이 판별식의 그물이 공허했던 구조적 원인이다:
# `_look_value_line`을 순진한 `';' in line`으로 퇴화시켜도 입력에 적수가 하나도
# 없어 아무 단언도 죽지 않았다. 출하 `club-circle-motion`(fx 단독)이 실제로 이
# 줄을 담고 있으므로 그 뮤턴트는 생산에서 순수 허위 경보다.
FX_SPEED_CHAIN = "Attribute 'Pan' At Speed 112 ; Attribute 'Tilt' At Speed 112"
# `_phase_lines`는 체인하지 않는다 — 한 줄에 하나이며 값이 아니라 키워드를 낸다.
FX_PHASE_LINE = "Attribute 'Pan' At Phase 0 Thru 360"
# 절대값 세그먼트와 수식자 세그먼트가 섞인 체인. 판별식의 `all(...)`을 `any(...)`로
# 푼 변형만 이 줄을 값 라인으로 받아들인다.
MIXED_CHAIN = "Attribute 'Dimmer' At 80 ; Attribute 'Pan' At Speed 112"

# `uniform_claim`의 닫힌 3분기. 배타성 단언이 이 튜플을 돈다.
UNIFORM_BRANCHES = (UNIFORM_NOT_APPLICABLE_NOTE, UNIFORM_CONFIRMED_NOTE, UNIFORM_BROKEN_NOTE)

# `to_korean`의 두 표제. 완전 일치로만 판정한다 — `EFFECT_EVIDENCE_NOTICE`의 문면
# 자체가 "기계 확인 불가"를 담고 있어 부분 일치는 그 주장 줄을 표제로 오인한다.
CONFIRMED_HEADING = "기계 확인됨:"
UNCONFIRMED_HEADING = "기계 확인 불가:"
HEADINGS = (CONFIRMED_HEADING, UNCONFIRMED_HEADING)
OTHER_HEADING = {
    CONFIRMED_HEADING: UNCONFIRMED_HEADING,
    UNCONFIRMED_HEADING: CONFIRMED_HEADING,
}

REQUERY = {"sequence_name": "Sequence 21", "cue_name": "SCN X", "cue_no": 3}


def _commands(*, value_line: str | None = LOOK_VALUE_LINE, steps: bool = True) -> tuple[str, ...]:
    lines = ["ChangeDestination Root", "ClearAll", "Group 11"]
    if value_line is not None:
        lines.append(value_line)
    if steps:
        # 스텝 값 라인은 체인하지 않고, 수식자 라인은 체인하되 절대값이 아니다 —
        # 판별식이 갈라야 하는 두 모양을 픽스처가 모두 담는다(교리 8).
        lines.extend(
            [
                "Attribute 'Dimmer' At 100",
                "Step 2",
                "Attribute 'Dimmer' At 0",
                FX_PHASE_LINE,
                FX_SPEED_CHAIN,
            ]
        )
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


def _is_heading(line: str) -> bool:
    return line in HEADINGS


def _line_index(lines: list[str], claim: str) -> int:
    """상수와 **완전 일치**하는 줄의 인덱스.

    부분 일치를 쓰면 잘려 나간 문면도 통과한다
    (`test_a_substring_check_would_miss_a_truncated_notice`). 중복도 실패로 —
    같은 주장이 두 표제 아래 동시에 실리면 배치 단언 자체가 무의미해진다.
    """
    found = [index for index, line in enumerate(lines) if line.strip() == claim]
    assert len(found) == 1, f"expected exactly one line carrying the claim, got {len(found)}"
    return found[0]


def _heading_index(lines: list[str], heading: str) -> int:
    found = [index for index, line in enumerate(lines) if line == heading]
    assert len(found) == 1, f"expected exactly one {heading!r} heading, got {len(found)}"
    return found[0]


def _headed_sections(text: str) -> dict[str, list[str]]:
    """표제 → 그 아래 본문 줄들.

    주장 블록은 보고의 마지막 블록이므로 첫 표제 이후의 모든 줄은 어느 한
    표제의 소속이다. 그 앞의 요약·상세 줄은 어느 표제에도 넣지 않는다.
    """
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if _is_heading(line):
            current = sections.setdefault(line, [])
            continue
        if current is not None:
            current.append(line.strip())
    return sections


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

    def test_exactly_one_heading_separates_the_two_claims(self):
        # "표제가 하나 있다"가 아니라 "정확히 하나다". 둘 사이에 표제가 둘이면
        # 그 사이에 세 번째 구획이 생겼다는 뜻이고, 배치 규약이 바뀐 것이다.
        lines = to_korean(build_report(_compilation())).splitlines()
        uniform_at = _line_index(lines, UNIFORM_CONFIRMED_NOTE)
        tracking_at = _line_index(lines, TRACKING_UNOBSERVABLE_NOTICE)
        assert uniform_at < tracking_at
        between = [line for line in lines[uniform_at + 1 : tracking_at] if _is_heading(line)]
        assert between == [UNCONFIRMED_HEADING]


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
        # 긍정 동일성. `!= UNIFORM_CONFIRMED_NOTE`는 "CONFIRMED가 아니다"만
        # 말하며, BROKEN 분기가 `UNIFORM_NOT_APPLICABLE_NOTE`("이 씬은 룩 값
        # 라인이 없어(이펙트 단독)")를 돌려주도록 바뀌어도 통과한다 — 룩을 가진
        # 씬에 대한 거짓 단정이자 경고의 통째 소실인데도. 이 파일 도크스트링이
        # 선언한 CONSTANT IDENTITY 규율은 여기에도 적용된다.
        assert report.uniform_attributes == ("ColorRGB_R", "Dimmer", "ColorRGB_G", "ColorRGB_B")
        assert report.uniform_attributes != SCENE_UNIFORM_ATTRIBUTES
        assert report.to_dict()["claims"]["uniform"] == UNIFORM_BROKEN_NOTE


class TestTheValueLineDiscriminantHasAnAdversary:
    """AC-SCENE-015 (a′) — `;` 체인이라는 것만으로는 룩 값 라인이 아니다.

    판별식(`_look_value_line`)은 **모든 세그먼트가 절대값**(`Attribute 'X' At
    <수>`)인 체인만 값 라인으로 받는다. 그 조건이 그물을 갖는 것은 입력에
    적수 — 체인이지만 절대값이 아닌 줄 — 이 있을 때뿐이고, 그것이 없었기
    때문에 판별식을 `';' in line`으로 퇴화시킨 변형이 스위트 전체를 통과했다.
    """

    def test_the_fixture_actually_carries_the_adversary(self):
        # 비공허성. 이 줄이 거짓이면 아래 단언들은 아무것도 막지 않는다.
        assert FX_SPEED_CHAIN in _commands(value_line=None)
        assert ";" in FX_SPEED_CHAIN

    def test_an_fx_only_bundle_that_chains_still_has_no_look_value_line(self):
        report = build_report(
            _compilation(
                look_id=None,
                commands=_commands(value_line=None),
                collided_attributes=(),
            )
        )
        assert report.has_look_value_line is False
        assert report.uniform_attributes == ()
        assert report.to_dict()["claims"]["uniform"] == UNIFORM_NOT_APPLICABLE_NOTE

    def test_a_look_bearing_bundle_picks_the_absolute_chain_over_the_speed_chain(self):
        # 대조군 — 판별식이 "체인이면 전부 거절"로 퇴화해도 잡힌다. 대조군이
        # 없으면 "아무것도 값 라인이 아니다"가 위 단언을 통과시킨다.
        report = build_report(_compilation())
        assert report.has_look_value_line is True
        assert report.uniform_attributes == SCENE_UNIFORM_ATTRIBUTES

    @pytest.mark.parametrize(
        "line",
        [FX_SPEED_CHAIN, FX_PHASE_LINE, MIXED_CHAIN, "Attribute 'Dimmer' At 100"],
        ids=["speed_chain", "phase_modifier", "mixed_chain", "unchained_absolute"],
    )
    def test_a_non_value_line_never_becomes_the_value_line(self, line):
        report = build_report(
            _compilation(
                look_id=None,
                commands=("ChangeDestination Root", "ClearAll", "Group 11", line),
                collided_attributes=(),
            )
        )
        assert report.has_look_value_line is False
        assert report.to_dict()["claims"]["uniform"] == UNIFORM_NOT_APPLICABLE_NOTE


class TestTheThreeUniformBranchesAreMutuallyExclusive:
    """AC-SCENE-015 (a′) — 세 분기는 세 개의 다른 사실이다.

    하나가 다른 것을 대신해도 형상은 성공처럼 보인다: NOT_APPLICABLE은 "룩 값
    라인이 없다"는 **단정**이라 룩을 가진 씬에 붙으면 BROKEN 경고를 통째로
    삼킨다. 그래서 각 분기를 긍정 동일성으로 고정하고, 나머지 둘이 **아님**을
    같은 자리에서 함께 말한다.
    """

    def test_the_three_notes_are_three_distinct_constants(self):
        assert len(set(UNIFORM_BRANCHES)) == 3

    @pytest.mark.parametrize(
        ("look_id", "value_line", "expected"),
        [
            (None, None, UNIFORM_NOT_APPLICABLE_NOTE),
            ("look-blue", LOOK_VALUE_LINE, UNIFORM_CONFIRMED_NOTE),
            ("look-blue", BROKEN_VALUE_LINE, UNIFORM_BROKEN_NOTE),
        ],
        ids=["fx_only", "in_order", "out_of_order"],
    )
    def test_each_branch_is_its_own_note_and_not_either_other(self, look_id, value_line, expected):
        report = build_report(
            _compilation(
                look_id=look_id,
                commands=_commands(value_line=value_line),
                collided_attributes=("Dimmer",) if look_id else (),
            )
        )
        claim = report.to_dict()["claims"]["uniform"]
        assert claim == expected
        assert claim not in set(UNIFORM_BRANCHES) - {expected}
        # 산문 보고와 구조화 보고가 같은 분기를 말한다 — 둘이 갈리면 사람이 읽는
        # 것과 모델이 읽는 것이 다른 사실을 말하게 된다.
        assert report.uniform_claim == expected
        assert expected in to_korean(report)


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


class TestTheArtifactClaimSitsUnderTheHeadingThatMatchesIt:
    """AC-SCENE-015 (a) — 표제와 그 아래 줄이 서로를 반박하지 않는다.

    (a)의 문면은 재조회 여부에 따라 **사실이 반대**다. 미확인 문면("재조회를
    수행하지 않았습니다")을 `기계 확인됨:` 아래 놓으면 표제만 훑는 독자에게
    산출물이 기계 확인된 것으로 제시된다 — 발화 ≠ 효과 교리가 가장 막고 싶어
    하는 오독이고, 툴은 `requery=`를 넘기지 않으므로 그것이 **모든 생산
    리포트의 모양**이었다. 배치는 인덱스로만 판정한다: 두 표제가 존재하기만
    하면 `in text`는 어느 주장이 어느 표제 아래 있든 통과하며, 그 그물이
    이 결함을 사전 머지 리뷰까지 살려 두었다.
    """

    @pytest.mark.parametrize(
        ("requery", "claim", "heading"),
        [
            (None, ARTIFACT_UNVERIFIED_NOTE, UNCONFIRMED_HEADING),
            (REQUERY, ARTIFACT_CONFIRMED_NOTE, CONFIRMED_HEADING),
        ],
        ids=["unverified", "requeried"],
    )
    def test_the_claim_is_filed_under_its_own_heading(self, requery, claim, heading):
        sections = _headed_sections(to_korean(build_report(_compilation(), requery=requery)))
        assert claim in sections[heading]
        assert claim not in sections[OTHER_HEADING[heading]]

    @pytest.mark.parametrize(
        ("requery", "claim", "heading"),
        [
            (None, ARTIFACT_UNVERIFIED_NOTE, UNCONFIRMED_HEADING),
            (REQUERY, ARTIFACT_CONFIRMED_NOTE, CONFIRMED_HEADING),
        ],
        ids=["unverified", "requeried"],
    )
    def test_no_other_heading_intervenes_before_the_claim(self, requery, claim, heading):
        lines = to_korean(build_report(_compilation(), requery=requery)).splitlines()
        own = _heading_index(lines, heading)
        other = _heading_index(lines, OTHER_HEADING[heading])
        claim_at = _line_index(lines, claim)
        assert own < claim_at
        assert not (own < other < claim_at)

    @pytest.mark.parametrize("requery", [None, REQUERY], ids=["unverified", "requeried"])
    def test_both_headings_are_present_and_neither_is_empty(self, requery):
        # 한쪽 표제가 비면 "전부 반대편으로 보내기" 회귀가 표제만 남긴 채 통과한다.
        sections = _headed_sections(to_korean(build_report(_compilation(), requery=requery)))
        assert set(sections) == {CONFIRMED_HEADING, UNCONFIRMED_HEADING}
        assert sections[CONFIRMED_HEADING]
        assert sections[UNCONFIRMED_HEADING]

    @pytest.mark.parametrize("requery", [None, REQUERY], ids=["unverified", "requeried"])
    def test_exactly_one_of_the_two_artifact_notes_is_printed(self, requery):
        lines = to_korean(build_report(_compilation(), requery=requery)).splitlines()
        stripped = [line.strip() for line in lines]
        printed = [
            note for note in (ARTIFACT_CONFIRMED_NOTE, ARTIFACT_UNVERIFIED_NOTE) if note in stripped
        ]
        assert len(printed) == 1

    def test_without_a_requery_the_confirmed_heading_carries_only_the_uniform_claim(self):
        sections = _headed_sections(to_korean(build_report(_compilation())))
        assert sections[CONFIRMED_HEADING] == [UNIFORM_CONFIRMED_NOTE]
        assert sections[UNCONFIRMED_HEADING] == [
            ARTIFACT_UNVERIFIED_NOTE,
            EFFECT_EVIDENCE_NOTICE,
            TRACKING_UNOBSERVABLE_NOTICE,
        ]

    def test_a_requery_moves_the_artifact_claim_and_nothing_else(self):
        sections = _headed_sections(to_korean(build_report(_compilation(), requery=REQUERY)))
        assert sections[CONFIRMED_HEADING] == [ARTIFACT_CONFIRMED_NOTE, UNIFORM_CONFIRMED_NOTE]
        assert sections[UNCONFIRMED_HEADING] == [
            EFFECT_EVIDENCE_NOTICE,
            TRACKING_UNOBSERVABLE_NOTICE,
        ]


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


# =============================================================================
# the shipped assets — the discriminant trained on a REAL adversary
#
# Everything above runs on in-memory fixtures, so the value-line discriminant
# only ever meets shapes this file authored. `club-circle-motion` ships an
# fx-only bundle carrying `Attribute 'Pan' At Speed 112 ; Attribute 'Tilt' At
# Speed 112` — a real `;` chain that is NOT a value line. Under the naive
# `';' in line` reading that asset reports `has_look_value_line=True` and
# `UNIFORM_BROKEN_NOTE` for a scene that carries no look at all: a pure false
# alarm on shipped content, invisible at runtime (every line returns `ok:true`
# and a re-query cannot read cue content, spec.md §C.1).
# =============================================================================

_REAL_LOOKS = load_look_library()
_REAL_FX = load_fx_library()
_REAL_SCENES = load_scene_library().scenes


def _empty_section() -> dict:
    return rig_section([], {"truncated": False, "node": {"childCount": 0}})


def _real_report(scene):
    look = _REAL_LOOKS.by_id(scene.look_id) if scene.look_id else None
    fx = _REAL_FX.by_id(scene.fx_id) if scene.fx_id else None
    compilation = compile_scene(
        scene,
        look=look,
        fx=fx,
        group=11,
        sequences_section=_empty_section(),
        cues_section=_empty_section(),
    )
    return look, build_report(compilation)


class TestTheShippedAssetsExerciseTheDiscriminant:
    """AC-SCENE-015 (a′) over the LIBRARY, not over fixtures."""

    def test_the_sweep_covers_both_compositions(self):
        # 비공허성 — 한쪽 구성만 출하되면 아래 스윕은 한 분기만 밟고 판별식은
        # 여전히 훈련되지 않는다.
        assert {scene.look_id is None for scene in _REAL_SCENES} == {True, False}

    def test_a_shipped_fx_only_asset_carries_a_semicolon_chain(self):
        # 적수가 실물에 존재한다는 사실 자체가 단언 대상이다. 사라지면 아래
        # 스윕은 조용히 공허해진다.
        chained = [
            scene.scene_id
            for scene in _REAL_SCENES
            if scene.look_id is None
            for _look, report in [_real_report(scene)]
            if any(";" in line for line in report.compilation.commands)
        ]
        assert chained

    @pytest.mark.parametrize("scene", _REAL_SCENES, ids=lambda s: s.scene_id)
    def test_every_shipped_scene_claims_uniformity_by_its_composition(self, scene):
        look, report = _real_report(scene)
        claim = report.to_dict()["claims"]["uniform"]
        if look is None:
            assert report.has_look_value_line is False
            assert report.uniform_attributes == ()
            assert claim == UNIFORM_NOT_APPLICABLE_NOTE
        else:
            # compile.py가 UNIFORM_ATTRIBUTES_INCOMPLETE로 거절하고 core-4를
            # 앞으로 정렬하므로, 룩을 가진 출하 씬은 CONFIRMED 외의 값을 낼 수
            # 없다 — BROKEN이 나오면 컴파일러와 보고가 갈린 것이다.
            assert report.has_look_value_line is True
            assert report.uniform_attributes == SCENE_UNIFORM_ATTRIBUTES
            assert claim == UNIFORM_CONFIRMED_NOTE

    @pytest.mark.parametrize("scene", _REAL_SCENES, ids=lambda s: s.scene_id)
    def test_every_shipped_scene_files_its_artifact_claim_as_unverified(self, scene):
        # 툴은 `requery=`를 넘기지 않는다 — 이것이 모든 생산 리포트의 모양이다.
        _look, report = _real_report(scene)
        sections = _headed_sections(to_korean(report))
        assert sections[UNCONFIRMED_HEADING][0] == ARTIFACT_UNVERIFIED_NOTE
        assert ARTIFACT_UNVERIFIED_NOTE not in sections[CONFIRMED_HEADING]
        assert ARTIFACT_CONFIRMED_NOTE not in sections[CONFIRMED_HEADING]

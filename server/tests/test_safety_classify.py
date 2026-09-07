"""Risk classification tests (M4 stage ② — REQ-MVP-013/026/036b).

Classification is command-SYNTAX based (acceptance edge case: a blacklist
keyword inside a quoted object NAME must not match). Keyword matching is
abbreviation-aware (case-insensitive exact OR a >=3-char prefix of the keyword;
options abbreviate from 1 char) — over-matching is acceptable (FP resolved by
human approval), under-matching is the FN direction the design forbids.
"""

from __future__ import annotations

import pytest

from server.safety.audit import AuditLog
from server.safety.classify import RECOGNIZED_REFERENCE_TYPES, classify_command
from server.safety.console import StateBodyFetcher
from server.safety.expand import evaluate_reference
from server.safety.gate import SafetyGate
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

from .test_safety_expand import DictBodyFetcher
from .test_safety_gate import FakeConsole, ScriptedApproval

RULESET = load_ruleset()

#: 옵션 축을 재는 검사 셋이 공유하는 리터럴 — `TestBlacklistMatching` 의
#: `test_plain_store_is_safe` · `test_option_abbreviation_still_matches` ·
#: `test_store_with_quoted_overwrite_text_is_safe` 가 읽는다. 그 셋이 재는 축은
#: `Store` 를 위험하게 만드는 것이 동사가 아니라 `/overwrite` **옵션**이라는 것이고,
#: 따라서 리터럴의 오브젝트는 폐집합 **밖**이어야 한다.
#:
#: 갱신 근거 (t299 Phase 3): 옛 리터럴은 `Store Cue 5` 였고 v7 이 그 오브젝트를
#: 폐집합에 넣었다. Phase 1·2 가 세운 「안전한 예 리터럴은 프로그래머 값 계열로
#: 옮긴다」 규율을 이 자리에는 쓸 수 없다 — 동사가 축의 일부라서 비-`Store` 명령으로는
#: 축이 사라진다. 그래서 폐집합 밖의 `Store` 오브젝트를 쓰고, 그 전제를
#: `test_the_option_axis_literal_is_still_outside_the_closed_set` 이 따로 지킨다.
_OPTION_AXIS_OBJECT = "Store Page 3"


def _classify(line: str):
    result = validate(line)
    assert result.ok, f"test line must parse: {line!r} ({result.reason})"
    return classify_command(result.parsed, RULESET)


class TestBlacklistMatching:
    @pytest.mark.parametrize(
        "line,entry",
        [
            ("Delete Sequence 5", "Delete"),
            ("delete sequence 5", "Delete"),
            ("Remove Sequence 5", "Remove"),
            ("Off Everything", "Off Everything"),
            ("Store Cue 5 /overwrite", "Store /overwrite"),
            ("Shutdown", "Shutdown"),
            ("Format Disk", "Format"),
            # v5 (SPEC-COPILOT-CLASSIFYGAP-001, 카드 t299 Phase 1). 폐집합 핀은
            # 항목이 목록에 **있는지**만 세므로, 그 항목이 실제로 명령을 잡는지는
            # 아무 검사도 보지 않고 있었다 — 이전 리비전들은 각자 자기 SPEC
            # 파일에서 그 짝을 들었지만 t299 는 자기 파일이 없다. 여기 둔다.
            ("Store Group 3", "Store Group"),
            ("Store Timecode 9", "Store Timecode"),
            # v6 (같은 SPEC, 카드 t299 Phase 2). 같은 이유로 여기 둔다 — 이 줄이
            # 없으면 `Store Sequence` 항목을 지워도 장부 핀(폐집합 멤버십·버전·
            # Store 계열 목록)만 빨개지고 「카드가 안 뜨게 됐다」는 아무 검사도
            # 말하지 않는다. 뮤테이션으로 확인한 성질이다.
            ("Store Sequence 210 Cue 3 /Merge", "Store Sequence"),
            # v7 (같은 SPEC, 카드 t299 Phase 3). 같은 이유로 여기 둔다 — 이 줄이
            # 없으면 `Store Cue` 항목을 지워도 장부 핀(폐집합 멤버십·버전)만
            # 빨개지고 「카드가 안 뜨게 됐다」는 아무 검사도 말하지 않는다.
            # Phase 1·2 가 같은 자리에서 뮤테이션으로 확인한 성질이다.
            ("Store Cue 1", "Store Cue"),
        ],
    )
    def test_direct_blacklist_commands_are_blacklisted(self, line, entry):
        finding = _classify(line)
        assert finding.category == "blacklisted"
        assert finding.risky is True
        assert finding.matched_entry == entry

    def test_verb_abbreviation_still_matches(self):
        # MA3 accepts abbreviated keywords (Del -> Delete); the classifier
        # matches >=3-char prefixes so abbreviation cannot bypass the set.
        assert _classify("Del Sequence 5").category == "blacklisted"
        assert _classify("Rem Sequence 5").category == "blacklisted"

    def test_option_abbreviation_still_matches(self):
        """갱신 근거 (t299 Phase 3): 이 검사가 **가려질 수 있게** 됐다.

        옛 형태는 `Store Cue 5 /o` 의 `category == "blacklisted"` 만 봤다. v7 이
        `Store Cue` 를 폐집합에 넣은 뒤로는 옵션을 아예 못 읽어도 오브젝트가
        걸려서 초록이 된다 — 재려던 축(옵션 축약)이 다른 축에 가려지는 모양이다.
        빨개지지 않았으므로 비용 33건에는 안 들어갔지만, 갱신하지 않으면 조용히
        공허해진다.

        그래서 둘을 바꿨다: 리터럴을 폐집합 밖 오브젝트로 옮기고, `category` 대신
        **어느 항목에 걸렸는지**를 단언한다. 이제 옵션 축약이 실제로 읽히지 않으면
        이 검사가 붉어진다.
        """
        for option in ("/o", "/over"):
            finding = _classify(f"{_OPTION_AXIS_OBJECT} {option}")
            assert finding.category == "blacklisted", option
            assert finding.matched_entry == "Store /overwrite", option

    def test_the_option_axis_literal_is_still_outside_the_closed_set(self):
        """옵션 축 리터럴의 **전제**를 따로 잰다 — 축과 전제를 갈라 놓는다.

        이 검사가 없으면, 후속 카드가 `Store Page` 를 넣는 날 아래 세 검사가
        「옵션 축이 깨졌다」처럼 빨개진다. 실제로 깨진 것은 축이 아니라 리터럴의
        전제이므로, 그 구분을 검사 하나로 못 박아 둔다.
        """
        object_entry = " ".join(_OPTION_AXIS_OBJECT.split()[:2])
        assert object_entry not in RULESET.blacklist, (
            f"옵션 축 리터럴 {_OPTION_AXIS_OBJECT!r} 의 오브젝트({object_entry!r})가 "
            "폐집합에 들어왔다. 아래 세 검사가 재는 것은 `/overwrite` **옵션** 축이지 "
            "이 오브젝트가 아니다 — `_OPTION_AXIS_OBJECT` 를 아직 폐집합 밖인 다른 "
            "`Store` 오브젝트로 옮기고, 그 리비전의 헤더에 이 이동을 함께 적어라. "
            "비-`Store` 명령으로는 이 축을 잴 수 없다(동사가 축의 일부다)."
        )

    def test_plain_store_is_safe(self):
        # 옵션이 없으면 안전하다 — 위 `("Store Cue 5 /overwrite", "Store /overwrite")`
        # 행과 짝을 이루는 대조군이다.
        finding = _classify(_OPTION_AXIS_OBJECT)
        assert finding.category == "safe"
        assert finding.risky is False

    def test_blacklist_keyword_inside_quoted_name_does_not_match(self):
        # Acceptance edge case: quoted object names never match keywords.
        finding = _classify("Label Sequence 3 'Delete old look'")
        assert finding.category == "safe"

    def test_store_with_quoted_overwrite_text_is_safe(self):
        # 인용된 `/overwrite` 는 옵션이 아니라 이름이다 — 걸리면 안 된다.
        finding = _classify(f"{_OPTION_AXIS_OBJECT} '/overwrite'")
        assert finding.category == "safe"


class TestUnspecifiedTargetDetection:
    # REQ-MVP-036b / AC-MVP-024: deterministic, harness-level detection of
    # destructive commands lacking an explicit target (>=5-case corpus).
    @pytest.mark.parametrize(
        "line",
        [
            "Delete",  # no target at all
            "Delete *",  # wildcard
            "Delete Sequence Thru",  # open-ended Thru (all sequences)
            "Delete Thru 10",  # open start
            "Remove All",  # broad keyword
            "Off Everything",  # inherently broad
        ],
    )
    def test_unspecified_or_broad_destructive_commands_are_flagged(self, line):
        finding = _classify(line)
        assert finding.category == "blacklisted"
        assert finding.unspecified_target is True
        assert any("target" in r for r in finding.reasons)

    def test_bounded_range_is_specified(self):
        finding = _classify("Delete Sequence 1 Thru 10")
        assert finding.category == "blacklisted"
        assert finding.unspecified_target is False

    def test_explicit_target_is_specified(self):
        finding = _classify("Delete Sequence 5")
        assert finding.unspecified_target is False


class TestInvokingDetection:
    @pytest.mark.parametrize(
        "line,reference",
        [
            ("Go Macro 5", "Macro 5"),
            ("Go+ Executor 201", "Executor 201"),  # REQ-EXECREF-001/002
            ("Goto Cue 3", None),
            ("On Sequence 2", "Sequence 2"),
            ("Off Sequence 3", "Sequence 3"),
            ("Toggle Sequence 2", "Sequence 2"),
            ("Call Macro 7", "Macro 7"),
            ("Temp Sequence 4", "Sequence 4"),
            ("Flash Sequence 4", "Sequence 4"),
        ],
    )
    def test_invoking_verbs_are_detected_with_reference(self, line, reference):
        finding = _classify(line)
        assert finding.category == "invoking"
        assert finding.reference == reference

    @pytest.mark.parametrize(
        "line,reference",
        [
            ("Macro 5", "Macro 5"),
            ("Plugin 7", "Plugin 7"),
            ('Plugin "CopilotResponder" "ping x"', "Plugin CopilotResponder"),
        ],
    )
    def test_bare_object_forms_are_detected(self, line, reference):
        finding = _classify(line)
        assert finding.category == "invoking"
        assert finding.reference == reference

    def test_off_everything_wins_over_off_as_invoking_verb(self):
        # Blacklist matching has priority over invoking-verb detection.
        assert _classify("Off Everything").category == "blacklisted"

    def test_verb_abbreviation_of_invoking_verb_is_detected(self):
        finding = _classify("Got Macro 5")  # >=3-char prefix of Goto
        assert finding.category == "invoking"

    def test_plain_commands_are_not_invoking(self):
        # 갱신 근거 (t299 Phase 3): 재는 축은 「호출 동사가 아니면 invoking 이 아니다」
        # 이고, 옛 리터럴 `Store Cue 5` 는 v7 이 폐집합에 넣어 `blacklisted` 가 됐다.
        # 이 축에는 `Store` 가 필요 없으므로 Phase 1·2 의 규율대로 **프로그래머 값**
        # 으로 옮긴다.
        #
        # 갱신 근거 (t325 Phase 4): 셋째 줄도 같은 이유로 옮긴다. 옛 리터럴
        # `Assign Sequence 1 At Executor 201` 을 v8 이 폐집합에 넣었다.
        #
        # **여기서 규율의 근거가 바뀐다.** Phase 3 은 「폐집합은 쇼파일 쓰기 **오브젝트**
        # 만 담으므로 어떤 리비전도 이 리터럴을 다시 잡지 않는다」라고 적었다. v8 뒤로
        # 그 문장은 거짓이다 — 폐집합이 `Store` 밖의 동사(`Assign`·`Copy`)로 넓어졌으니
        # 「비-`Store` 명령이면 안전하다」는 성립하지 않는다.
        #
        # 새 규율: 옮길 곳은 **선택·프로그래머 상태** 명령이다. 그쪽이 안전한 이유는
        # 목록의 현재 내용이 아니라 의미다 — 선택(`Fixture 1 Thru 12`)과 프로그래머 값
        # (`Fixture 1 At 50`)은 쇼파일을 만들거나 덮지 않으므로, 어떤 리비전도 그것을
        # 「쇼파일 쓰기」로 넣을 수 없다. 오브젝트 목록에 기대는 근거는 리비전마다
        # 만료되지만 이 근거는 안 만료된다.
        assert _classify("Fixture 1 At 50").category == "safe"
        assert _classify("List").category == "safe"
        assert _classify("Fixture 1 Thru 12").category == "safe"


class TestQuotedPropertyCommandContent:
    # M6c-2 Finding 1 (REQ-MVP-013): the M6b-1r2 macro-authoring recipe
    # (`Set Macro <pool>.<line> Property 'Command' '<text>'`) persists a
    # command LINE as a quoted property value. The outer assignment syntax
    # (verb "Set", args Macro/1.1/Property/"Command") is not itself blacklist
    # or invoking-verb shaped, so without recursion a destructive string
    # smuggled this way would classify as "safe" with zero approval.
    def test_destructive_content_in_command_property_is_blacklisted(self):
        finding = _classify('Set Macro 1.1 Property "Command" "Delete Everything"')
        assert finding.category == "blacklisted"
        assert finding.risky is True
        assert finding.matched_entry == "Delete"

    def test_legacy_cmd_property_name_spelling_is_also_recursed(self):
        # Older MA3 material calls the property `Cmd` instead of `Command`.
        finding = _classify('Set Macro 1.1 Property "Cmd" "Delete Everything"')
        assert finding.category == "blacklisted"
        assert finding.risky is True

    def test_assign_verb_legacy_form_adjacent_equivalent_is_also_recursed(self):
        # Detection is verb-agnostic (shape-driven on Property/Command/value),
        # so a different outer verb still catches the smuggled content.
        finding = _classify('Assign Macro 1.1 Property "Command" "Delete Everything"')
        assert finding.category == "blacklisted"
        assert finding.risky is True

    def test_benign_quoted_macro_command_stays_low_risk(self):
        # Must NOT over-block every quoted property assignment.
        finding = _classify('Set Macro 1.1 Property "Command" "Group \'Vocals\' At Full"')
        assert finding.category == "safe"
        assert finding.risky is False

    def test_nested_quoted_name_reference_is_not_a_command_and_does_not_false_positive(self):
        # A standalone quoted-name object reference (`Preset 'Blue'`-style,
        # per the 00_grammar.md object-by-name rule) carries no `Property`
        # keyword at all -> the detector must never engage on it.
        finding = _classify("At Preset 4.1")
        assert finding.category == "safe"
        finding = _classify("Select Preset 'Blue'")
        assert finding.category == "safe"


class TestExecutorReferenceRecognition:
    """SPEC-COPILOT-EXECREF-001 M1 (REQ-EXECREF-001/002/003): Executor joins
    the closed set of recognized reference types -- a deliberate, documented
    revision of RECOGNIZED_REFERENCE_TYPES (classify.py:33), not a second
    classification path (classify_command stays the single entry point)."""

    def test_executor_is_in_the_recognized_reference_type_closed_set(self):
        assert "Executor" in RECOGNIZED_REFERENCE_TYPES

    @pytest.mark.parametrize(
        "line,reference",
        [
            ("Go+ Executor 191", "Executor 191"),
            ("Go Executor 5", "Executor 5"),
            ("Off Executor 3", "Executor 3"),
        ],
    )
    def test_invoking_verbs_extract_executor_reference(self, line, reference):
        finding = _classify(line)
        assert finding.category == "invoking"
        assert finding.reference == reference

    def test_quoted_executor_token_is_still_skipped(self):
        # Existing semantics preserved (acceptance.md §D edge case 3): a
        # quoted token is never treated as a type-word match.
        finding = _classify('Go+ "Executor 201"')
        assert finding.category == "invoking"
        assert finding.reference is None

    def test_single_classification_entry_point_unchanged(self):
        # REQ-EXECREF-003: classify_command stays the ONE matching semantics;
        # Executor recognition is a closed-set data change, not a new branch.
        import inspect

        assert set(inspect.signature(classify_command).parameters.keys()) == {
            "parsed",
            "ruleset",
            "reference_types",
        }


class TestExecutorRenameInvariance:
    """AC-EXECREF-015 / REQ-EXECREF-007: reference extraction is derived
    purely from the executor NUMBER token in the raw command text -- it never
    reads a display/assigned-sequence name. Renaming the sequence assigned to
    an executor (e.g. 'Sequence 71' -> 'Cyan Look') must not change the
    extracted reference or the hold/risky screening result."""

    def test_reference_extraction_ignores_the_assigned_sequence_name(self):
        finding = _classify("Go+ Executor 202")
        assert finding.category == "invoking"
        assert finding.reference == "Executor 202"  # number-only, never a name

    @pytest.mark.parametrize(
        "body_content",
        [
            # 갱신 근거 (t299 Phase 3): 옛 본문은 두 파라미터 모두 `("Store Cue 1",)`
            # 였고, v7 이 `Store Cue` 를 폐집합에 넣어 「깨끗한 본문」이 아니게 됐다.
            # 재는 축은 이름 변경이 **어느 본문을 읽는지**를 바꾸지 않는다는 것이므로
            # 본문의 내용은 축과 무관하다 — Phase 1·2 의 규율대로 프로그래머 값으로
            # 옮긴다(폐집합은 쇼파일 쓰기 오브젝트만 담으므로 다시 안 잡힌다).
            #
            # 옮기면서 관측한 것도 적어 둔다: 두 파라미터의 본문이 **바이트 동일**해서
            # 이 parametrize 는 before/after 를 구분하지 못한다(id 만 다르다). 실제
            # 이름-무관성은 아래 `test_before_and_after_rename_outcomes_are_byte_identical`
            # 이 재고, 이 검사가 재는 것은 「깨끗한 본문이면 hold 가 안 걸린다」다.
            # 그 성질을 문면으로 남긴다 — 고치지는 않았다(이 SPEC 의 범위가 아니다).
            ("Fixture 1 At 50",),  # 'Sequence 71'-era body content
            ("Fixture 1 At 50",),  # 'Cyan Look'-era body content (post-rename)
        ],
        ids=["before-rename", "after-rename"],
    )
    def test_screening_result_is_identical_across_rename(self, body_content):
        # Both fixtures key on the SAME reference string ("Executor 202") --
        # proving the rename never changes which body the gate consults,
        # because the reference is number-derived, not name-derived.
        finding = _classify("Go+ Executor 202")
        fetcher = DictBodyFetcher({"Executor 202": body_content})
        outcome = evaluate_reference(finding.reference, ruleset=RULESET, fetcher=fetcher)
        assert outcome.hold is False
        assert outcome.risky is False

    def test_before_and_after_rename_outcomes_are_byte_identical(self):
        finding = _classify("Go+ Executor 202")
        before = DictBodyFetcher({"Executor 202": ("Delete Sequence 5",)})
        after = DictBodyFetcher({"Executor 202": ("Delete Sequence 5",)})
        outcome_before = evaluate_reference(finding.reference, ruleset=RULESET, fetcher=before)
        outcome_after = evaluate_reference(finding.reference, ruleset=RULESET, fetcher=after)
        assert outcome_before.hold == outcome_after.hold
        assert outcome_before.risky == outcome_after.risky


class TestExecutorNoOpBeforeBodyPath:
    """design.md §2.1 (EXECREF-001) + REQ-EXECBODY-004 (EXECBODY-001 M4): an
    Executor reference always holds -- never risky -- regardless of whether
    its identity resolves. Pre-M4 (EXECREF-001), 'Executor' had no body path
    at all and short-circuited with 'no body path mapping' without ever
    querying the console. As of M4, StateBodyFetcher DOES query the console
    for the assigned-sequence identity (REQ-EXECBODY-003/004); when that
    query itself cannot resolve an identity, the hold REASON now reads
    'identity query failed for ...' instead -- the observable
    hold=True/risky=False shape is unchanged (fail-closed, REQ-EXECBODY-006)."""

    def test_executor_reference_with_unresolvable_identity_still_holds_not_risky(self):
        finding = _classify("Go+ Executor 201")
        assert finding.reference == "Executor 201"  # newly recognized (was None pre-M1)

        def _failing_query(path: str) -> dict:
            raise RuntimeError("no console reply")

        fetcher = StateBodyFetcher(query=_failing_query)
        outcome = evaluate_reference(finding.reference, ruleset=RULESET, fetcher=fetcher)
        assert outcome.hold is True
        assert outcome.risky is False
        assert "identity query failed for 'Executor 201'" in outcome.reasons[0]

    def test_none_reference_and_executor_reference_produce_the_same_hold_shape(self):
        # design.md §2.1: both the pre-M1 (`reference=None`) and post-M1
        # (`reference="Executor 201"`, no body path) states hold with
        # risky=False -- the gate's OBSERVABLE decision is unchanged.
        none_outcome = evaluate_reference(None, ruleset=RULESET, fetcher=DictBodyFetcher({}))
        executor_outcome = evaluate_reference(
            "Executor 201", ruleset=RULESET, fetcher=StateBodyFetcher(query=lambda p: {})
        )
        assert none_outcome.hold == executor_outcome.hold is True
        assert none_outcome.risky == executor_outcome.risky is False


class TestExecutorSinglePressClearance:
    """AC-EXECREF-001: a resolvable, benign-body Executor reference clears
    through the FULL gate pipeline with zero approval requests and console
    execution recorded as exactly the one bundled command -- no 'SaveShow'
    (SHOWUI M3's measured shape ["SaveShow", "Go+ Executor 201"] is the
    defect this SPEC corrects at the recognition layer). This scenario
    injects an in-memory body_fetcher directly into SafetyGate (bypassing
    console.py's StateBodyFetcher/DEFAULT_BODY_PATHS entirely, since S2
    body-path interpretation is DESCOPED for this milestone) -- it proves
    the gate's general screening machine handles a recognized Executor
    reference correctly, not that this path is reachable in production
    (acceptance.md AC-EXECREF-001 note)."""

    def test_benign_executor_body_clears_with_no_approval_and_no_saveshow(self, tmp_path):
        console = FakeConsole()
        approval = ScriptedApproval(decisions=[])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(tmp_path / "audit"),
            approval_port=approval,
            # 갱신 근거 (t299 Phase 3): 옛 본문은 `("Store Cue 1",)` 이고 v7 이
            # `Store Cue` 를 폐집합에 넣었다. 이 검사가 재는 축은 「**양성(benign)**
            # 본문이면 승인 없이 통과한다」이므로, 본문이 쇼파일 쓰기가 된 뒤에는
            # 축 자체가 성립하지 않는다 — 확대가 틀린 것이 아니라 리터럴이 더는
            # benign 이 아니다. Phase 1·2 의 규율대로 프로그래머 값으로 옮긴다.
            body_fetcher=DictBodyFetcher({"Executor 201": ("Fixture 1 At 50",)}),
        )
        command = "Go+ Executor 201"
        decision = gate.screen([command])
        assert decision.cleared is True
        assert approval.requests == []  # zero approval requests
        # panel.py's fire() executes ONLY after screen() clears (REQ-SHOWUI-022
        # ordering) -- mirror that two-step production flow here.
        gate.execution_port.execute(command)
        assert console.executed == ["Go+ Executor 201"]  # exact shape, no "SaveShow"

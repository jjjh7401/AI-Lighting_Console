"""Destructive-content scan tests (M7 — REQ-MVP-027, AC-MVP-010 ③ / AC-MVP-018 ①).

The scan extracts ``Cmd()`` string-literal arguments from submitted Lua source
and classifies each through the SAME closed-set semantics the gate uses
(grammar.validate + classify.classify_command — one matching semantics,
abbreviation-aware). It is a BEST-EFFORT reviewer-assist signal: dynamic
string assembly evades it, so the human review gate stays authoritative
(REQ-MVP-027 residual-risk framing). False positives are acceptable; the
destructive flag only ever errs in the safe direction.
"""

from __future__ import annotations

import pytest

from server.deploy.scan import BEST_EFFORT_CAVEAT, scan_lua_source
from server.safety.ruleset import load_ruleset


@pytest.fixture(scope="module")
def ruleset():
    return load_ruleset()  # the real SSOT file — corpus follows revisions


def _scan(source, ruleset):
    return scan_lua_source(source, ruleset)


class TestBlacklistedFindings:
    def test_delete_cmd_is_destructive_with_line_number(self, ruleset):
        source = 'local function main()\n    Cmd("Delete Sequence 5")\nend\n'
        report = _scan(source, ruleset)
        assert report.destructive is True
        (finding,) = report.findings
        assert finding.kind == "blacklisted"
        assert finding.line == 2
        assert finding.command == "Delete Sequence 5"
        assert finding.matched_entry == "Delete"

    def test_abbreviated_keyword_matches(self, ruleset):
        # classify.py abbreviation-aware matching must be reused verbatim:
        # MA3 accepts `Del` for `Delete`.
        report = _scan('Cmd("Del 1")', ruleset)
        assert report.destructive is True
        assert report.findings[0].matched_entry == "Delete"

    def test_single_quoted_lua_literal(self, ruleset):
        report = _scan("Cmd('Off Everything')", ruleset)
        assert report.destructive is True
        assert report.findings[0].matched_entry == "Off Everything"

    def test_call_sugar_without_parentheses(self, ruleset):
        # Lua allows `Cmd"..."` and `Cmd[[...]]` (single-string call sugar).
        assert _scan('Cmd"Delete Group 2"', ruleset).destructive is True
        assert _scan("Cmd[[Delete Group 2]]", ruleset).destructive is True

    def test_every_ssot_entry_is_detected(self, ruleset):
        # Closed-set completeness: the scan must detect ALL current entries.
        for entry in ruleset.blacklist:
            report = _scan(f'Cmd("{entry} 1")', ruleset)
            assert report.destructive is True, entry

    def test_multiline_formatted_cmd_call_is_still_detected(self, ruleset):
        # M6c-2 Finding 2: only space/tab were skipped between `Cmd(` and its
        # argument, so a newline-formatted call evaded classification.
        source = 'local function main()\n    Cmd(\n        "Delete Everything"\n    )\nend\n'
        report = _scan(source, ruleset)
        assert report.destructive is True
        (finding,) = report.findings
        assert finding.kind == "blacklisted"
        assert finding.matched_entry == "Delete"

    def test_multiple_findings_report_each_line(self, ruleset):
        # 갱신 근거 (t299 Phase 3): 재는 축은 「findings 가 **줄 번호**를 각각 보고한다」
        # 이고, 1행은 그 번호가 밀리지 않는지 보이기 위한 **안전한** 줄이다. 옛 리터럴
        # `Store Cue 1` 은 v7(SPEC-COPILOT-CLASSIFYGAP-001)이 폐집합에 넣어 1행도
        # finding 이 됐고, 그러면 「2행·3행만 걸린다」는 기대가 성립하지 않는다.
        # Phase 1·2 의 규율대로 프로그래머 값으로 옮긴다.
        source = 'Cmd("Fixture 1 At 50")\nCmd("Delete 1")\nCmd("Remove 2")\n'
        report = _scan(source, ruleset)
        assert report.destructive is True
        assert [(f.line, f.matched_entry) for f in report.findings] == [
            (2, "Delete"),
            (3, "Remove"),
        ]


class TestSafeAndNonDestructive:
    def test_safe_commands_yield_no_findings(self, ruleset):
        # t299 (ruleset v5): the first literal was `Store Group 3` until v5
        # blacklisted `Store Group`. The axis here is "a source with nothing
        # destructive in it yields no findings", so the literal moves and the
        # assertion stays. `Group 4` is a selection command, not a write — chosen
        # over another `Store` object so this fixture stops colliding with Store
        # revisions (the v4 blacklist header predicted this exact collision).
        report = _scan('Cmd("Group 4")\nCmd("List")', ruleset)
        assert report.destructive is False
        assert report.findings == ()
        assert report.dynamic_calls == ()

    def test_quoted_object_name_never_matches(self, ruleset):
        # Same acceptance edge case as the gate: a blacklist keyword inside a
        # quoted object name is NOT a destructive command.
        #
        # 갱신 근거 (t299 Phase 3) — 이 자리는 plan 단계(§D.2 각주)가 함정으로
        # 예고한 곳이다. 옛 리터럴은 `Store Cue 5 'Delete'` 이고, 인용된 `'Delete'` 가
        # **안 걸리는** 성질을 재려는 것이었다. v7 이 `Store Cue` 를 폐집합에 넣자
        # 비인용부가 걸려서 재려던 성질이 **가려졌다** — 확대가 틀린 것이 아니라
        # 리터럴이 축을 못 나른다.
        #
        # 그래서 리터럴을 바꾸면서 축을 **더 날카롭게** 했다. 옛 형태는 인용어가
        # `Delete` 라 동사(`Store`)가 `Delete` 항목의 첫 키워드와 애초에 안 맞았고,
        # 인용을 무시해도 안 걸렸다 — 즉 인용 규칙을 껐어도 초록이었다. 새 형태는
        # 동사가 `Store` 로 항목 `Store Cue` 의 첫 키워드와 **맞고**, `Cue` 는 오직
        # 인용된 토큰으로만 나타난다. 인용 규칙이 꺼지면 이 줄은 곧바로 걸린다.
        report = _scan("Cmd(\"Store Page 3 'Cue'\")", ruleset)
        assert report.destructive is False
        assert report.findings == ()
        # 비공허성 짝: 같은 줄에서 인용만 벗기면 걸려야 한다. 이것이 없으면 위
        # 단언은 「이 스캐너가 아무것도 안 걸린다」로도 통과한다.
        unquoted = _scan('Cmd("Store Page 3 Cue")', ruleset)
        assert unquoted.destructive is True
        assert [f.matched_entry for f in unquoted.findings] == ["Store Cue"]

    def test_source_without_cmd_calls(self, ruleset):
        report = _scan("local x = 1\nreturn x", ruleset)
        assert report.destructive is False
        assert report.findings == ()

    def test_identifier_suffix_cmd_is_not_matched(self, ruleset):
        # `MyCmd(...)` is a different function — not the MA3 global.
        report = _scan('MyCmd("Delete 1")\nlocal SendCmd = f\nSendCmd("Delete 2")', ruleset)
        assert report.findings == ()


class TestInvokingFindings:
    def test_indirect_invocation_is_a_reviewer_signal_not_a_flag(self, ruleset):
        # `Cmd("Go Macro 5")` cannot be verified at deploy time. It is
        # surfaced to the reviewer but does NOT drive the destructive flag
        # (the invocation-time expand-or-hold gate covers execution).
        report = _scan('Cmd("Go Macro 5")', ruleset)
        assert report.destructive is False
        (finding,) = report.findings
        assert finding.kind == "invoking"


class TestDynamicAssembly:
    def test_non_literal_argument_is_recorded_as_dynamic(self, ruleset):
        report = _scan("local c = build()\nCmd(c)", ruleset)
        assert report.destructive is False
        (call,) = report.dynamic_calls
        assert call.line == 2

    def test_concatenated_literal_prefix_is_still_classified(self, ruleset):
        # Best-effort hardening: `Cmd("Delete " .. target)` — the literal
        # prefix classifies as blacklisted AND the call is marked dynamic.
        report = _scan('Cmd("Delete " .. target)', ruleset)
        assert report.destructive is True
        assert report.findings[0].kind == "blacklisted"
        assert len(report.dynamic_calls) == 1

    def test_string_format_call_is_dynamic(self, ruleset):
        report = _scan('Cmd(string.format("Delete %d", n))', ruleset)
        assert report.destructive is False
        assert len(report.dynamic_calls) == 1

    def test_multiline_concatenation_is_still_detected_as_dynamic(self, ruleset):
        # M6c-2 Finding 2: the trailing-concatenation check only stripped
        # space/tab, so a `..` split across a line break evaded the dynamic
        # signal while the literal prefix is still classified (best-effort).
        report = _scan('Cmd("Delete "\n    .. target)', ruleset)
        assert report.destructive is True
        assert report.findings[0].kind == "blacklisted"
        assert len(report.dynamic_calls) == 1


class TestUnparseableLiterals:
    def test_unparseable_literal_is_surfaced_not_flagged(self, ruleset):
        # A literal the gate grammar cannot parse is a reviewer-assist
        # warning; the human review stays the authoritative control.
        report = _scan('Cmd("\'unbalanced")', ruleset)
        assert report.destructive is False
        (finding,) = report.findings
        assert finding.kind == "unparseable"


class TestReportShape:
    def test_report_carries_the_best_effort_caveat(self, ruleset):
        report = _scan('Cmd("Delete 1")', ruleset)
        assert report.caveat == BEST_EFFORT_CAVEAT
        assert "best-effort" in report.caveat

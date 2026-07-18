"""Measurement corpus schema tests (M6a — AC-MVP-002 corpus + AC-MVP-028 ③).

The corpus is the acceptance-defined standard scenario set for the grammar
error-rate and round-trip measurements: >=20 standard Korean instructions =
the 10 representative task types (AC-MVP-001) x >=2 variants each, with >=3
variants using Korean field terminology from the rulebook term dictionary
(AC-MVP-028 ③ — cross-checked against the REAL dictionary axis, not a copy).

The corpus is DATA consumed identically by the M6a mock runner and the M6b
live runs; the loader enforces structure so a malformed corpus fails fast.
"""

from __future__ import annotations

import pytest

from server.measurement.corpus import (
    TASK_TYPES,
    CorpusError,
    Scenario,
    load_corpus,
)
from server.rulebook.assembly import korean_term_entries
from server.safety.grammar import validate


@pytest.fixture(scope="module")
def corpus() -> tuple[Scenario, ...]:
    return load_corpus()


def _dictionary_terms() -> set[str]:
    """Every Korean term in the rulebook dictionary axis (split multi-term cells)."""
    terms: set[str] = set()
    for entry in korean_term_entries():
        for part in entry.korean.split(","):
            if part.strip():
                terms.add(part.strip())
    return terms


class TestCorpusSchema:
    def test_task_type_catalog_is_the_ten_representative_tasks(self):
        # AC-MVP-001's closed set of 10 representative task types.
        assert len(TASK_TYPES) == 10
        assert len(set(TASK_TYPES)) == 10

    def test_corpus_loads_with_at_least_20_scenarios(self, corpus):
        # Acceptance "문법 오류율 측정 방법" §1: standard scenarios >= 20.
        assert len(corpus) >= 20

    def test_every_task_type_has_at_least_two_variants(self, corpus):
        # 10 task types x >=2 Korean instruction variants each.
        counts: dict[str, int] = {t: 0 for t in TASK_TYPES}
        for scenario in corpus:
            counts[scenario.task_type] += 1
        lacking = {t: n for t, n in counts.items() if n < 2}
        assert lacking == {}, f"task types below 2 variants: {lacking}"

    def test_scenario_ids_are_unique_and_non_empty(self, corpus):
        ids = [s.id for s in corpus]
        assert all(ids)
        assert len(ids) == len(set(ids))

    def test_instructions_are_non_empty_korean_text(self, corpus):
        for scenario in corpus:
            assert scenario.instruction.strip(), scenario.id
            # Natural-Korean corpus: every instruction carries Hangul syllables.
            assert any("가" <= ch <= "힣" for ch in scenario.instruction), scenario.id

    def test_every_scenario_has_exactly_one_mock_action(self, corpus):
        for scenario in corpus:
            assert scenario.mock.kind in ("commands", "query", "plugin"), scenario.id
            if scenario.mock.kind == "commands":
                assert scenario.mock.commands, scenario.id
            elif scenario.mock.kind == "query":
                assert scenario.mock.query_path, scenario.id
            else:
                assert scenario.mock.plugin_name and scenario.mock.plugin_source, scenario.id


class TestFieldTerminologyCoverage:
    def test_at_least_three_scenarios_use_dictionary_field_terms(self, corpus):
        # AC-MVP-028 ③: >=3 corpus instruction variants use Korean field
        # terminology (샤막/워시 등) from the rulebook dictionary axis.
        tagged = [s for s in corpus if s.field_terms]
        assert len(tagged) >= 3, "corpus must tag >=3 field-terminology scenarios"

    def test_declared_field_terms_exist_in_dictionary_and_instruction(self, corpus):
        dictionary = _dictionary_terms()
        for scenario in corpus:
            for term in scenario.field_terms:
                assert term in dictionary, f"{scenario.id}: {term!r} not in the rulebook dictionary"
                assert term in scenario.instruction, (
                    f"{scenario.id}: declared field term {term!r} missing from instruction"
                )

    def test_field_term_scenarios_cover_at_least_three_distinct_terms(self, corpus):
        distinct = {term for s in corpus for term in s.field_terms}
        assert len(distinct) >= 3


class TestMockCommandsClearTheOfflineGate:
    def test_all_mock_command_lines_pass_the_grammar_validator(self, corpus):
        # The happy-path corpus is the mock baseline: every mock command line
        # must be structurally valid (grammar rejections are injected by the
        # runner tests, never by the baseline corpus).
        for scenario in corpus:
            for command in scenario.mock.commands:
                result = validate(command)
                assert result.ok, f"{scenario.id}: {command!r} -> {result.reason}"


class TestLoaderValidation:
    def test_unknown_task_type_is_rejected(self, tmp_path):
        bad = tmp_path / "corpus.yaml"
        bad.write_text(
            "version: 1\n"
            "scenarios:\n"
            "  - id: x-1\n"
            "    task_type: not_a_task\n"
            '    instruction: "그룹 만들어줘"\n'
            "    mock:\n"
            '      commands: ["Store Group 1"]\n',
            encoding="utf-8",
        )
        with pytest.raises(CorpusError):
            load_corpus(bad)

    def test_duplicate_ids_are_rejected(self, tmp_path):
        bad = tmp_path / "corpus.yaml"
        bad.write_text(
            "version: 1\n"
            "scenarios:\n"
            "  - id: dup\n"
            "    task_type: group_create\n"
            '    instruction: "그룹 만들어줘"\n'
            "    mock:\n"
            '      commands: ["Store Group 1"]\n'
            "  - id: dup\n"
            "    task_type: group_create\n"
            '    instruction: "그룹 하나 더"\n'
            "    mock:\n"
            '      commands: ["Store Group 2"]\n',
            encoding="utf-8",
        )
        with pytest.raises(CorpusError):
            load_corpus(bad)

    def test_mock_block_with_two_actions_is_rejected(self, tmp_path):
        bad = tmp_path / "corpus.yaml"
        bad.write_text(
            "version: 1\n"
            "scenarios:\n"
            "  - id: x-1\n"
            "    task_type: state_query\n"
            '    instruction: "상태 알려줘"\n'
            "    mock:\n"
            '      commands: ["Store Group 1"]\n'
            '      query_path: "DataPool/Sequences"\n',
            encoding="utf-8",
        )
        with pytest.raises(CorpusError):
            load_corpus(bad)

    def test_duplicate_instruction_text_across_different_ids_is_rejected(self, tmp_path):
        # A copy-paste authoring mistake: two distinct scenario ids sharing the
        # exact same instruction text would silently double-count that
        # instruction's contribution to the measurement statistics.
        bad = tmp_path / "corpus.yaml"
        bad.write_text(
            "version: 1\n"
            "scenarios:\n"
            "  - id: a-1\n"
            "    task_type: group_create\n"
            '    instruction: "그룹 만들어줘"\n'
            "    mock:\n"
            '      commands: ["Store Group 1"]\n'
            "  - id: a-2\n"
            "    task_type: group_create\n"
            '    instruction: "그룹 만들어줘"\n'
            "    mock:\n"
            '      commands: ["Store Group 2"]\n',
            encoding="utf-8",
        )
        with pytest.raises(CorpusError):
            load_corpus(bad)

    def test_instructions_differing_only_by_surrounding_whitespace_are_duplicates(self, tmp_path):
        # This is an EXACT-duplicate check, not fuzzy similarity — leading/
        # trailing (or repeated internal) whitespace must not create a
        # false-negative "these are distinct" reading.
        bad = tmp_path / "corpus.yaml"
        bad.write_text(
            "version: 1\n"
            "scenarios:\n"
            "  - id: a-1\n"
            "    task_type: group_create\n"
            '    instruction: "그룹 만들어줘"\n'
            "    mock:\n"
            '      commands: ["Store Group 1"]\n'
            "  - id: a-2\n"
            "    task_type: group_create\n"
            '    instruction: "  그룹   만들어줘  "\n'
            "    mock:\n"
            '      commands: ["Store Group 2"]\n',
            encoding="utf-8",
        )
        with pytest.raises(CorpusError):
            load_corpus(bad)

    def test_default_corpus_has_no_duplicate_instruction_false_positive(self):
        # Regression guard: the real DEFAULT_CORPUS_PATH must still load
        # cleanly — no false positive on legitimately distinct scenarios.
        scenarios = load_corpus()
        assert len(scenarios) >= 20

"""Parser unit tests for last-created-look session tracking (AC-DEPLOY-021, #4).

``parse_last_created`` extracts the just-created sequence and its executor from
the executed command strings of one turn, so the session can inject that target
identity into the next turn's conversation. It is a pure, snapshot-only parser
(the single most-recent look, not an accumulating history).
"""

from __future__ import annotations

from server.orchestrator.last_created import LastCreated, parse_last_created


class TestParseLastCreated:
    def test_store_only_captures_the_sequence_without_an_executor(self):
        assert parse_last_created(["Store Sequence 71"]) == LastCreated(sequence=71, executor=None)

    def test_assign_only_captures_both_sequence_and_executor(self):
        assert parse_last_created(["Assign Sequence 71 At Executor 201"]) == LastCreated(
            sequence=71, executor=201
        )

    def test_store_then_assign_pairs_the_sequence_with_its_executor(self):
        commands = ["Store Sequence 71", "Assign Sequence 71 At Executor 201"]
        assert parse_last_created(commands) == LastCreated(sequence=71, executor=201)

    def test_lua_plugin_assign_form_is_recognized(self):
        # The Lua-plugin-built form (project memory: FID/Seq via AddSequence).
        assert parse_last_created(["Assign Sequence 16 At Executor 193"]) == LastCreated(
            sequence=16, executor=193
        )

    def test_multiple_sequences_keeps_only_the_last(self):
        commands = [
            "Store Sequence 71",
            "Assign Sequence 71 At Executor 201",
            "Store Sequence 72",
            "Assign Sequence 72 At Executor 202",
        ]
        assert parse_last_created(commands) == LastCreated(sequence=72, executor=202)

    def test_new_store_after_an_assign_drops_the_prior_executor(self):
        commands = [
            "Store Sequence 71",
            "Assign Sequence 71 At Executor 201",
            "Store Sequence 72",
        ]
        # Seq 72 is the newest look and has no executor assigned yet — the
        # executor 201 belonged to Seq 71, so it must NOT leak onto Seq 72.
        assert parse_last_created(commands) == LastCreated(sequence=72, executor=None)

    def test_none_when_no_sequence_command_is_present(self):
        assert parse_last_created(["Store Group 3", "Go+ Executor 1"]) is None

    def test_empty_command_list_returns_none(self):
        assert parse_last_created([]) is None

    def test_store_cue_referencing_a_sequence_is_not_a_creation(self):
        # A Store Cue that names a sequence in a modifier must not be read as a
        # "Store Sequence" creation — anchoring at the verb prevents that.
        assert parse_last_created(["Store Cue 1 Sequence 71"]) is None

    def test_case_insensitive_keywords(self):
        assert parse_last_created(["store sequence 5"]) == LastCreated(sequence=5, executor=None)

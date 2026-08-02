"""Sequence/executor + preset integrity checks (SPEC-COPILOT-PRESHOW-001)."""

from __future__ import annotations

from server.looks.loader import LookSchemaError
from server.preshow.checks import (
    check_preset_library_integrity,
    check_preset_pools_exist,
    check_sequences_exist,
)


class FakeStatePort:
    def __init__(self, responses: dict[str, dict] | None = None, *, error: Exception | None = None):
        self._responses = responses or {}
        self._error = error

    def query_state(self, path: str) -> dict:
        if self._error is not None:
            raise self._error
        return self._responses[path]


class TestCheckSequencesExist:
    def test_pass_when_children_present(self):
        port = FakeStatePort({"DataPool/Sequences": {"node": {"childCount": 3}}})
        result = check_sequences_exist(port)
        assert result.status == "pass"
        assert result.data == {"path": "DataPool/Sequences", "child_count": 3}

    def test_fail_when_zero_children(self):
        port = FakeStatePort({"DataPool/Sequences": {"node": {"childCount": 0}}})
        result = check_sequences_exist(port)
        assert result.status == "fail"

    def test_fail_when_payload_unreadable(self):
        port = FakeStatePort({"DataPool/Sequences": {"node": {}}})
        result = check_sequences_exist(port)
        assert result.status == "fail"
        assert "판독하지 못했다" in result.detail

    def test_skip_when_port_raises(self):
        port = FakeStatePort(error=TimeoutError("no console"))
        result = check_sequences_exist(port)
        assert result.status == "skip"

    def test_respects_custom_path(self):
        port = FakeStatePort({"Custom/Path": {"node": {"childCount": 1}}})
        result = check_sequences_exist(port, path="Custom/Path")
        assert result.status == "pass"
        assert result.data["path"] == "Custom/Path"


class TestCheckPresetPoolsExist:
    def test_pass_when_children_present(self):
        port = FakeStatePort({"DataPool/PresetPools": {"node": {"childCount": 5}}})
        result = check_preset_pools_exist(port)
        assert result.status == "pass"

    def test_fail_when_zero_children(self):
        port = FakeStatePort({"DataPool/PresetPools": {"node": {"childCount": 0}}})
        result = check_preset_pools_exist(port)
        assert result.status == "fail"

    def test_skip_when_port_raises(self):
        port = FakeStatePort(error=RuntimeError("boom"))
        result = check_preset_pools_exist(port)
        assert result.status == "skip"


class TestCheckPresetLibraryIntegrity:
    def test_pass_with_real_library(self):
        result = check_preset_library_integrity()
        assert result.status == "pass"
        assert result.data["count"] > 0

    def test_fail_on_schema_error(self):
        def _broken_loader():
            raise LookSchemaError("bad schema")

        result = check_preset_library_integrity(_broken_loader)
        assert result.status == "fail"
        assert "스키마 오류" in result.detail

    def test_never_skips_on_broken_library(self):
        # Unlike the console-state checks, a local file defect is always
        # catchable — it must never degrade to skip.
        def _broken_loader():
            raise LookSchemaError("duplicate look id")

        result = check_preset_library_integrity(_broken_loader)
        assert result.status != "skip"

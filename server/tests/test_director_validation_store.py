"""SPEC-LDWIRE-001 M2 -- REQ-LDWIRE-006/007.

ValidationReport persistence + validation_id round trip on DirectorStore
(design.md section "na" alternative A -- DirectorStore extension, not a
separate store module). RED first: this file is written before
DirectorStore grows save_validation/get_validation/compute_validation_id,
so importing them fails until M2 GREEN step lands.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.director.store import DirectorStore, ValidationRecord, compute_validation_id

PROJECT = "proj-wire-1"
PLAN_ID = "plan-wire-1"


@pytest.fixture()
def store(tmp_path: Path) -> DirectorStore:
    return DirectorStore(tmp_path / "director.sqlite3")


def _record(
    *,
    validation_id: str,
    project_id: str = PROJECT,
    plan_id: str = PLAN_ID,
    plan_digest: str = "sha256:" + "a" * 64,
    context_digest: str = "sha256:" + "b" * 64,
    compiled_digest: str = "sha256:" + "c" * 64,
    outcome: str = "ready_for_review",
    created_at: str = "2026-09-19T00:00:00Z",
    expires_at: str = "2026-09-19T00:10:00Z",
) -> ValidationRecord:
    return ValidationRecord(
        validation_id=validation_id,
        project_id=project_id,
        plan_id=plan_id,
        plan_digest=plan_digest,
        context_digest=context_digest,
        compiled_digest=compiled_digest,
        outcome=outcome,
        diagnostics=[dict(rule_id="LD-REF-001", pointer="", status="accepted")],
        compiled=dict(available=True),
        created_at=created_at,
        expires_at=expires_at,
    )


class TestValidationIdIsDeterministic:
    def test_same_inputs_produce_the_same_id(self) -> None:
        a = compute_validation_id(
            plan_digest="sha256:" + "a" * 64, revision=1, context_digest="sha256:" + "b" * 64
        )
        b = compute_validation_id(
            plan_digest="sha256:" + "a" * 64, revision=1, context_digest="sha256:" + "b" * 64
        )
        assert a == b

    def test_different_revision_produces_a_different_id(self) -> None:
        a = compute_validation_id(
            plan_digest="sha256:" + "a" * 64, revision=1, context_digest="sha256:" + "b" * 64
        )
        b = compute_validation_id(
            plan_digest="sha256:" + "a" * 64, revision=2, context_digest="sha256:" + "b" * 64
        )
        assert a != b


class TestSaveAndGetRoundTrip:
    def test_saved_validation_round_trips_byte_identical(self, store: DirectorStore) -> None:
        record = _record(validation_id="validation-wire-1")
        store.save_validation(record)

        fetched = store.get_validation(project_id=PROJECT, validation_id="validation-wire-1")

        assert fetched == record

    def test_missing_validation_id_returns_none(self, store: DirectorStore) -> None:
        assert store.get_validation(project_id=PROJECT, validation_id="does-not-exist") is None

    def test_different_project_id_does_not_leak_the_validation(self, store: DirectorStore) -> None:
        record = _record(validation_id="validation-wire-2", project_id=PROJECT)
        store.save_validation(record)

        other = store.get_validation(project_id="other-project", validation_id="validation-wire-2")
        assert other is None

    def test_saving_the_same_validation_id_twice_does_not_overwrite(
        self, store: DirectorStore
    ) -> None:
        first = _record(validation_id="validation-wire-3", outcome="ready_for_review")
        store.save_validation(first)
        second = _record(validation_id="validation-wire-3", outcome="blocked")
        store.save_validation(second)

        fetched = store.get_validation(project_id=PROJECT, validation_id="validation-wire-3")
        assert fetched == first


class TestStoreValidationProviderHonestRejection:
    """REQ-LDWIRE-007 / AC-LDWIRE-007 -- a missing or cross-project validation_id
    is rejected honestly, never promoted."""

    def test_get_resolves_a_saved_validation(self, store: DirectorStore) -> None:
        from server.director.provision import StoreValidationProvider

        record = _record(validation_id="validation-provider-1")
        store.save_validation(record)
        provider = StoreValidationProvider(store)

        ref = provider.get(PROJECT, "validation-provider-1")

        assert ref.validation_id == "validation-provider-1"
        assert ref.plan_digest == record.plan_digest
        assert ref.outcome == record.outcome

    def test_get_rejects_a_missing_validation_id(self, store: DirectorStore) -> None:
        from server.director.models import ExchangeError
        from server.director.provision import StoreValidationProvider

        provider = StoreValidationProvider(store)
        with pytest.raises(ExchangeError) as excinfo:
            provider.get(PROJECT, "does-not-exist")
        assert excinfo.value.code == "NOT_FOUND"

    def test_get_rejects_a_cross_project_validation_id(self, store: DirectorStore) -> None:
        from server.director.models import ExchangeError
        from server.director.provision import StoreValidationProvider

        record = _record(validation_id="validation-provider-2", project_id=PROJECT)
        store.save_validation(record)
        provider = StoreValidationProvider(store)

        with pytest.raises(ExchangeError) as excinfo:
            provider.get("some-other-project", "validation-provider-2")
        assert excinfo.value.code == "NOT_FOUND"

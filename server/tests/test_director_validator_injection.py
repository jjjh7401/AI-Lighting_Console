"""SPEC-LDWIRE-001 M4 -- REQ-LDWIRE-006 (PipelineValidator injection part) + M2 glue.

PUT plan actually invokes PipelineValidator (design.md section "da" alternative A --
route-layer per-request reconstruction, service.py/validate/pipeline.py untouched),
and the resulting validation is resolvable by validation_id afterwards
(REQ-LDWIRE-006 storage + retrieval). RED first: director_api.py PUT plan still
calls deps.service.submit() with its construction-time validator, so a fresh
per-request PipelineValidator never sees the request and the response carries no
validation_id.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.director.approvals import ApprovalRegistry
from server.director.auth import (
    CredentialRegistry,
    PairingSecretStore,
    encode_bearer_token,
)
from server.director.director_api import DirectorApiDeps, build_director_router
from server.director.knowledge import KnowledgeService
from server.director.provision import (
    RealContextProvider,
    StoreValidationProvider,
    issue_operator_credential,
)
from server.director.store import DirectorStore, compute_validation_id
from server.director.validate.pipeline import PipelineValidator
from server.safety.ruleset import SafetyRuleset

PROJECT = "proj-wire-m4"
PLAN_ID = "plan-wire-m4"
TRUSTED_ORIGIN = "http://127.0.0.1:37123"
DEFAULT_HOST = "127.0.0.1:37123"


def _ruleset() -> SafetyRuleset:
    return SafetyRuleset(
        version=1, blacklist=(), invoking_verbs=("At",), bare_object_forms=("Fixture",)
    )


def _plan(*, base_revision: int = 0) -> dict[str, Any]:
    return dict(
        project_id=PROJECT,
        plan_id=PLAN_ID,
        base_revision=base_revision,
        title="synthetic plan",
        bindings=dict(context_id="ctx-placeholder"),
    )


@pytest.fixture()
def store(tmp_path: Path) -> DirectorStore:
    return DirectorStore(tmp_path / "director.sqlite3")


@pytest.fixture()
def credential_registry() -> CredentialRegistry:
    return CredentialRegistry()


@pytest.fixture()
def secret_store() -> PairingSecretStore:
    return PairingSecretStore()


@pytest.fixture()
def client(
    store: DirectorStore, credential_registry: CredentialRegistry, secret_store: PairingSecretStore
):
    db_path = store.path
    deps_holder: dict[str, Any] = {}

    @contextlib.asynccontextmanager
    async def _lifespan(app: FastAPI):
        route_store = DirectorStore(db_path)
        credential, secret = issue_operator_credential(
            registry=credential_registry, secrets_store=secret_store, project_id=PROJECT
        )
        deps_holder["credential"] = (credential, secret)
        deps = DirectorApiDeps(
            store=route_store,
            knowledge=KnowledgeService(),
            registry=credential_registry,
            secrets=secret_store,
            allowed_hosts=(DEFAULT_HOST.split(":")[0],),
            trusted_origins=(TRUSTED_ORIGIN,),
            approvals=ApprovalRegistry(),
            validator=PipelineValidator(),
            context_provider=RealContextProvider(
                ruleset=_ruleset(), console_host="127.0.0.1", console_port=8000
            ),
            validation_provider=StoreValidationProvider(route_store),
        )
        deps_holder["deps"] = deps
        app.include_router(build_director_router(deps))
        yield
        route_store.close()

    app = FastAPI(lifespan=_lifespan)
    with TestClient(app) as test_client:
        test_client.deps = deps_holder["deps"]
        test_client.credential = deps_holder["credential"]
        yield test_client


def _headers(credential_id: str, secret: str) -> dict[str, str]:
    return dict(
        authorization=f"Bearer {encode_bearer_token(credential_id, secret)}",
        host=DEFAULT_HOST,
        origin=TRUSTED_ORIGIN,
    )


def test_put_plan_response_carries_a_resolvable_validation_id(client) -> None:
    credential, secret = client.credential
    response = client.put(
        f"/api/director/v1/projects/{PROJECT}/plans/{PLAN_ID}",
        json=dict(
            plan=_plan(),
            expected_revision=0,
            idempotency_key="key-m4-1",
        ),
        headers=_headers(credential.credential_id, secret),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    validation_id = body["validation"]["validation_id"]
    assert isinstance(validation_id, str) and validation_id

    context_response = client.get(
        f"/api/director/v1/projects/{PROJECT}/context",
        headers=_headers(credential.credential_id, secret),
    )
    assert context_response.status_code == 200, context_response.text
    context_digest = context_response.json()["context_digest"]
    expected_id = compute_validation_id(
        plan_digest=body["record"]["plan_digest"],
        revision=body["record"]["revision"],
        context_digest=context_digest,
    )
    assert validation_id == expected_id


def test_post_validations_uses_pipeline_validator_not_not_installed(client) -> None:
    credential, secret = client.credential
    response = client.post(
        f"/api/director/v1/projects/{PROJECT}/validations",
        json=dict(plan=_plan()),
        headers=_headers(credential.credential_id, secret),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    reasons = [d["reason"] for d in body["diagnostics"]]
    assert "validator-not-installed" not in reasons


def test_post_validations_time_reference_stage_sees_real_context(client) -> None:
    """This is the test that actually distinguishes M4 wiring from a bare non-None
    deps.validator: without per-request context injection, the time_reference stage
    always reports LD-TIME-001 unsupported ("ContextSnapshot without which time
    cannot be judged") no matter which validator class deps.validator holds."""
    credential, secret = client.credential
    response = client.post(
        f"/api/director/v1/projects/{PROJECT}/validations",
        json=dict(plan=_plan()),
        headers=_headers(credential.credential_id, secret),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # The "no context at all" reason is the one and only signal that
    # distinguishes M4 wiring from a bare non-None deps.validator -- other
    # LD-TIME-001 unsupported diagnostics (missing music_sections, an empty
    # cue list) are expected and honest per design.md section "la" (audio
    # stays an unobserved axis in this SPEC).
    no_context_reasons = [
        d["reason"]
        for d in body["diagnostics"]
        if d["rule_id"] == "LD-TIME-001" and "ContextSnapshot" in d["reason"]
    ]
    assert no_context_reasons == []

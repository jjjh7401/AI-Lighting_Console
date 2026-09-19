"""SPEC-LDWIRE-001 M5 -- REQ-LDWIRE-001/002/003.

Operator credential issuance: mints one app-human Credential per call (design.md
section "ga" alternative A -- reissue every boot). RED first:
issue_operator_credential does not exist yet.
"""

from __future__ import annotations

from server.director.auth import (
    APP_HUMAN_SCOPES,
    AUDIENCE_APP_HUMAN,
    CredentialRegistry,
    PairingSecretStore,
    authenticate,
    encode_bearer_token,
)
from server.director.provision import issue_operator_credential

PROJECT = "default"
TRUSTED_ORIGIN = "http://127.0.0.1:37123"
DEFAULT_HOST = "127.0.0.1:37123"


class TestIssueOperatorCredential:
    def test_issued_credential_has_app_human_scopes(self) -> None:
        registry = CredentialRegistry()
        secrets_store = PairingSecretStore()
        credential, secret = issue_operator_credential(
            registry=registry, secrets_store=secrets_store, project_id=PROJECT
        )
        assert credential.audience == AUDIENCE_APP_HUMAN
        assert credential.scopes == APP_HUMAN_SCOPES
        assert isinstance(secret, str) and len(secret) > 0
        assert registry.get(credential.credential_id) is credential

    def test_issued_secret_actually_authenticates(self) -> None:
        registry = CredentialRegistry()
        secrets_store = PairingSecretStore()
        credential, secret = issue_operator_credential(
            registry=registry, secrets_store=secrets_store, project_id=PROJECT
        )
        result = authenticate(
            authorization_header=(
                f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
            ),
            host_header=DEFAULT_HOST,
            origin_header=TRUSTED_ORIGIN,
            required_scope="plan:apply",
            registry=registry,
            secrets_store=secrets_store,
            trusted_origins=(TRUSTED_ORIGIN,),
        )
        assert result.credential_id == credential.credential_id

    def test_secret_is_never_returned_inside_the_credential_object(self) -> None:
        registry = CredentialRegistry()
        secrets_store = PairingSecretStore()
        credential, secret = issue_operator_credential(
            registry=registry, secrets_store=secrets_store, project_id=PROJECT
        )
        assert not hasattr(credential, "secret")
        assert secret not in repr(credential)

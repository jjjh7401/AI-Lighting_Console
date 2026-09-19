"""Production wiring for the director HTTP layer (SPEC-LDWIRE-001).

Four of this SPEC new seams live here:

- RealContextProvider (M3, REQ-LDWIRE-004/005) -- identity/expiry/policy are really
  observed; the other six axes are filled with context.py honest-unobserved states
  (design.md section "la", confirmed 2026-09-19). This module never talks OSC -- it
  only reads what the already-constructed console stack already knows at boot
  (SafetyRuleset, the configured console host/port). A full console identity
  round-trip is out of this SPEC scope (spec.md section 5: this SPEC is not a
  console gate).
- StoreValidationProvider (M2, REQ-LDWIRE-007) -- resolves a validation_id back to
  the ValidationReport DirectorStore persisted, honestly rejecting a missing or
  cross-project id rather than promoting a guess.
- issue_operator_credential (M5, REQ-LDWIRE-001/002/003) -- mints one app-human
  Credential per server boot (design.md section "ga" alternative A, confirmed
  2026-09-19: reissue every boot, no new persistence schema).
- build_director_deps (M6, REQ-LDWIRE-008/009/010) -- assembles exactly one
  DirectorApiDeps, reusing the already-built SafetyGate/ruleset -- no second
  SafetyGate or OSC path is created. MUST be called from the FastAPI event-loop
  thread: DirectorStore / ExecutionJournal both sqlite3.connect() with the
  default check_same_thread=True (director_api.py module docstring).
"""

from __future__ import annotations

import secrets as _secrets
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from server.director.approvals import ApprovalRegistry, ValidationRef
from server.director.auth import (
    APP_HUMAN_SCOPES,
    AUDIENCE_APP_HUMAN,
    Credential,
    CredentialRegistry,
    PairingSecretStore,
    encode_bearer_token,
    generate_secret,
)
from server.director.context import ContextObservations, build_snapshot, should_reissue
from server.director.director_api import DirectorApiDeps
from server.director.execution import ApplyCoordinator, ExecutionJournal, GatePort
from server.director.knowledge import KnowledgeService
from server.director.models import Detail, ExchangeError
from server.director.service import DirectorService
from server.director.store import DirectorStore
from server.director.validate.pipeline import PipelineValidator

#: The single-console deployment default -- this server assembles ONE
#: DirectorApiDeps for the ONE console it is configured to talk to at boot
#: (REQ-LDWIRE-008), so every route in this process serves the same project_id.
DEFAULT_PROJECT_ID = "default"

#: Design.md section "la" default expiry window for an issued context snapshot --
#: matches the 30-minute window already established for validation/approval
#: expiry elsewhere in this test suite (test_director_approvals.py).
_CONTEXT_WINDOW_MINUTES = 30

#: SPEC-LDWIRE-001 M2 -- a ValidationReport stays resolvable for the same window.
_VALIDATION_WINDOW_MINUTES = 30


class RulesetView(Protocol):
    """The SafetyRuleset surface RealContextProvider reads (structural typing --
    server.safety.ruleset.SafetyRuleset satisfies this without inheriting it)."""

    @property
    def version(self) -> int: ...

    @property
    def blacklist(self) -> tuple[str, ...]: ...

    @property
    def invoking_verbs(self) -> tuple[str, ...]: ...

    @property
    def bare_object_forms(self) -> tuple[str, ...]: ...


def _fmt(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _round_window_end(moment: datetime, window_minutes: int) -> datetime:
    """Rounds the expiry to a stable window boundary (REQ-LDWIRE-005).

    Without rounding, expires_at would be recomputed every single GET context call
    (now + window), which would never equal the previous call value and would
    spuriously trip context.should_reissue on EVERY repeated call -- defeating the
    very suppression REQ-LDWIRE-005 requires. Rounding to the window boundary keeps
    expires_at stable for repeated calls inside the same window, while still
    advancing forward at each boundary crossing.
    """
    epoch_minutes = int(moment.timestamp() // 60)
    window_start_minutes = epoch_minutes - (epoch_minutes % window_minutes)
    window_start = datetime.fromtimestamp(window_start_minutes * 60, tz=UTC)
    return window_start + timedelta(minutes=window_minutes)


class RealContextProvider:
    """SPEC-LDWIRE-001 M3 -- the director_api.ContextProvider Protocol, wired for real.

    identity/expiry/policy (three axes) are filled from genuinely observable
    server-side facts: the configured console host/port (identity), a policy-computed
    TTL window (expiry), and the live SafetyRuleset version + rule lists (policy). The
    other six axes (show/audio/group_membership/preset_content/compiler/capability)
    stay in context.py honest-unobserved states -- this SPEC does not add new
    observation wiring for them (design.md section "la", confirmed 2026-09-19).
    """

    def __init__(
        self,
        *,
        ruleset: RulesetView,
        console_host: str,
        console_port: int,
        environment: str = "production",
        window_minutes: int = _CONTEXT_WINDOW_MINUTES,
    ) -> None:
        self._ruleset = ruleset
        self._console_host = console_host
        self._console_port = console_port
        self._environment = environment
        self._window_minutes = window_minutes
        self._session_id = f"director-session-{_secrets.token_urlsafe(8)}"
        self._cache: dict[str, dict[str, Any]] = {}

    def _observe(self, project_id: str) -> ContextObservations:
        moment = datetime.now(UTC)
        created_at = _fmt(moment)
        expires_at = _fmt(_round_window_end(moment, self._window_minutes))

        evidence_refs: list[str] = []
        if self._console_host:
            evidence_refs.append("boot_config:console_host")
        if self._console_port:
            evidence_refs.append("boot_config:console_port")
        identity_status = "observed" if evidence_refs else "unreadable"
        target = dict(
            console_id=f"{self._console_host}:{self._console_port}",
            session_id=self._session_id,
            identity_status=identity_status,
            identity_evidence_refs=evidence_refs,
            mode="unknown",
            destination=dict(show_id="", sequence_id=""),
        )

        safety = dict(
            blacklist=list(self._ruleset.blacklist),
            invoking_verbs=list(self._ruleset.invoking_verbs),
            bare_object_forms=list(self._ruleset.bare_object_forms),
        )

        return ContextObservations(
            environment=self._environment,
            context_id="pending",
            project_id=project_id,
            show_id="",
            show_revision=0,
            created_at=created_at,
            expires_at=expires_at,
            audio=dict(status="unreadable", sha256=""),
            music_revision=0,
            rig_revision=0,
            capability_revision=0,
            safety_policy_revision=self._ruleset.version,
            compiler=dict(status="unreadable"),
            target=target,
            sources=[],
            evidence=[],
            music_sections=[],
            beat_map=dict(status="absent", segments=[]),
            groups=[],
            presets=[],
            capabilities=[],
            safety=safety,
        )

    def current(self, project_id: str) -> dict[str, Any]:
        """The director_api.ContextProvider.current() Protocol method.

        REQ-LDWIRE-005: a repeated call whose observations have not moved returns the
        SAME context_id/context_digest with only created_at refreshed -- so a plan
        already ready_for_review against the current context never goes stale just
        because someone called GET context again.
        """
        observations = self._observe(project_id)
        cached = self._cache.get(project_id)
        if cached is not None and not should_reissue(cached, observations):
            reused = dict(cached)
            reused["created_at"] = observations.created_at
            self._cache[project_id] = reused
            return reused

        new_context_id = f"ctx-{_secrets.token_urlsafe(12)}"
        final_observations = observations.replace(context_id=new_context_id)
        snapshot = build_snapshot(final_observations)
        self._cache[project_id] = snapshot
        return snapshot


class StoreValidationProvider:
    """SPEC-LDWIRE-001 M2 -- the director_api.ValidationProvider Protocol, backed by
    DirectorStore.get_validation() (REQ-LDWIRE-007).

    A missing or cross-project validation_id is rejected honestly (NOT_FOUND) --
    get_validation() is itself project_id-scoped, so this class adds no extra logic,
    only the Protocol adapter shape.
    """

    def __init__(self, store: DirectorStore) -> None:
        self._store = store

    def get(self, project_id: str, validation_id: str) -> ValidationRef:
        record = self._store.get_validation(project_id=project_id, validation_id=validation_id)
        if record is None:
            raise ExchangeError(
                "NOT_FOUND",
                404,
                f"No such validation: {validation_id}.",
                (Detail("/validation_id", ""),),
            )
        return ValidationRef(
            validation_id=record.validation_id,
            plan_digest=record.plan_digest,
            context_digest=record.context_digest,
            compiled_digest=record.compiled_digest,
            expires_at=record.expires_at,
            outcome=record.outcome,
        )


def issue_operator_credential(
    *,
    registry: CredentialRegistry,
    secrets_store: PairingSecretStore,
    project_id: str,
    principal_id: str = "operator",
    expires_in: float = 86400.0,
    now: float | None = None,
    credential_id: str | None = None,
) -> tuple[Credential, str]:
    """SPEC-LDWIRE-001 M5 -- mints + registers one app-human Credential
    (REQ-LDWIRE-001/002/003).

    Reissue-every-boot policy (design.md section "ga" alternative A, confirmed
    2026-09-19): CredentialRegistry stays a pure in-memory dict -- calling this once
    per server boot IS the whole persistence story, no new keystore schema is added
    by this SPEC. The returned secret is the ONLY place it ever appears outside
    PairingSecretStore -- the caller (the boot path) must not log it, put it in an
    error response, or otherwise let it leave this one issuance surface
    (REQ-LDWIRE-001/002; Credential itself has no secret field at all --
    auth.py Credential -- so this is the single spot secret plaintext exists
    in-process).

    Does not touch fail-closed behaviour: a route called before this function ever
    runs still hits the existing authenticate() 401 UNAUTHENTICATED path unchanged
    (REQ-LDWIRE-003) -- this function only ever ADDS a credential, it never bypasses
    the check that rejects when none exists yet.
    """
    moment = time.time() if now is None else now
    cred_id = credential_id or f"director-operator-{_secrets.token_urlsafe(8)}"
    credential = Credential(
        credential_id=cred_id,
        audience=AUDIENCE_APP_HUMAN,
        project_id=project_id,
        principal_id=principal_id,
        session_id=_secrets.token_urlsafe(8),
        scopes=APP_HUMAN_SCOPES,
        issued_at=moment,
        expires_at=moment + expires_in,
    )
    secret = generate_secret()
    registry.register(credential)
    secrets_store.set(cred_id, secret)
    return credential, secret


@dataclass(frozen=True, slots=True)
class DirectorBoot:
    """SPEC-LDWIRE-001 M6 -- the result of build_director_deps().

    deps is the ONE DirectorApiDeps instance (REQ-LDWIRE-008). bearer_token is the
    fresh operator credential encoded ready for an Authorization header -- the boot
    path (serve.py) is responsible for the actual reveal channel (REQ-LDWIRE-001).
    """

    deps: DirectorApiDeps
    #: None when the OS credential store was unavailable at boot (REQ-LDWIRE-003 --
    #: startup must not abort; the registry just stays empty and every director
    #: route answers the existing 401 UNAUTHENTICATED fail-closed path until a
    #: reissue succeeds).
    bearer_token: str | None
    credential_id: str | None


def build_director_deps(
    *,
    db_path: Path,
    gate: GatePort,
    ruleset: RulesetView,
    console_host: str,
    console_port: int,
    environment: str = "production",
    project_id: str = DEFAULT_PROJECT_ID,
) -> DirectorBoot:
    """SPEC-LDWIRE-001 M6 -- assembles the ONE DirectorApiDeps (REQ-LDWIRE-008/009)
    and mints the initial operator credential (REQ-LDWIRE-001).

    MUST be called from the FastAPI event-loop thread (REQ-LDWIRE-010) --
    DirectorStore / ExecutionJournal both sqlite3.connect() with the default
    check_same_thread=True, so constructing them anywhere else risks
    sqlite3.ProgrammingError the first time a route handler touches them from the
    event loop.

    Reuses the caller-supplied gate/ruleset -- never constructs a second SafetyGate
    or a separate OSC send path (REQ-LDWIRE-008); the caller (server.web.serve)
    passes the SAME stack.gate/stack.ruleset it already built via
    server.safety.bootstrap.build_console_stack().
    """
    store = DirectorStore(db_path)
    journal = ExecutionJournal(db_path)
    registry = CredentialRegistry()
    secrets_store = PairingSecretStore()
    bearer_token: str | None = None
    credential_id: str | None = None
    try:
        credential, secret = issue_operator_credential(
            registry=registry, secrets_store=secrets_store, project_id=project_id
        )
    except ExchangeError as error:
        # REQ-LDWIRE-003 -- an unavailable OS credential store must not abort
        # startup (matches build_runtime inject_active_provider_key degrade
        # pattern). The registry just stays empty, so every director route
        # answers the existing 401 UNAUTHENTICATED fail-closed path until an
        # operator retries issuance once the store recovers.
        print(
            f"[director] OS credential store unavailable ({error}); no operator "
            "credential issued this boot -- director routes stay unauthenticated "
            "until a reissue succeeds.",
            file=sys.stderr,
        )
    else:
        bearer_token = encode_bearer_token(credential.credential_id, secret)
        credential_id = credential.credential_id
    context_provider = RealContextProvider(
        ruleset=ruleset,
        console_host=console_host,
        console_port=console_port,
        environment=environment,
    )
    approvals = ApprovalRegistry()
    apply_coordinator = ApplyCoordinator(
        journal=journal, approvals=approvals, store=store, gate=gate
    )
    deps = DirectorApiDeps(
        store=store,
        knowledge=KnowledgeService(),
        service=DirectorService(store),
        registry=registry,
        secrets=secrets_store,
        validator=PipelineValidator(),
        context_provider=context_provider,
        approvals=approvals,
        validation_provider=StoreValidationProvider(store),
        apply_coordinator=apply_coordinator,
        execution_journal=journal,
    )
    return DirectorBoot(deps=deps, bearer_token=bearer_token, credential_id=credential_id)

"""SPEC-LDRECV-001 M1 · REQ-LDPLUGIN-019 · AC-LDPLUGIN-019.

evidence 신뢰 경계: `actor_ref`/`origin`/`confirmation` 은 클라이언트 주장일
뿐이며 같은 project/principal/scope 의 immutable 서버 record 로 역참조됐을
때만 인정한다 (계약 §5 LD-AUTH-003). audio 외부 전송은 앱 명시 동의 +
목적/수신자/범위 기록 없이는 차단한다 (LD-AUTH-004).
"""

from __future__ import annotations

import pytest

from server.director.auth import (
    UNCONFIRMED,
    AudioTransferRecord,
    EvidenceClaim,
    ServerRecord,
    authorize_audio_transfer,
    resolve_trust,
)
from server.director.models import ExchangeError


class _FakeEvidenceRegistry:
    """`EvidenceRegistry` Protocol 의 시험용 구현 — 고정된 record 목록만 답한다."""

    def __init__(self, records: tuple[ServerRecord, ...] = ()) -> None:
        self._records = records

    def lookup(self, *, project_id: str, principal_id: str, scope: str) -> ServerRecord | None:
        for record in self._records:
            if (
                record.project_id == project_id
                and record.principal_id == principal_id
                and record.scope == scope
            ):
                return record
        return None


# ---------------------------------------------------------------------------
# claim 만으로는 승격하지 않는다 (LD-AUTH-003)
# ---------------------------------------------------------------------------


def test_claim_alone_does_not_promote_without_server_record() -> None:
    """actor_ref/origin/confirmation 을 아무리 강하게 주장해도 서버 record 가
    없으면 unconfirmed 다 — 이것이 이 시험의 핵심 부정 사례다.
    """
    claim = EvidenceClaim(actor_ref="user:123", origin="human_confirmed", confirmation="approved")
    registry = _FakeEvidenceRegistry(records=())  # 아무 record 도 없음
    result = resolve_trust(
        claim,
        project_id="p1",
        principal_id="u1",
        scope="plan:approve",
        registry=registry,
    )
    assert result == UNCONFIRMED


def test_backref_to_matching_immutable_record_promotes() -> None:
    """양성 대조 — 같은 project/principal/scope 의 서버 record 가 있으면 그
    record 의 kind 로 인정한다. claim 의 origin 이 record 와 달라도(여기서는
    claim.origin="derived") 판정은 오직 서버 record 에서 온다.
    """
    record = ServerRecord(
        record_id="r1",
        project_id="p1",
        principal_id="u1",
        scope="plan:approve",
        kind="human_confirmed",
    )
    claim = EvidenceClaim(actor_ref="user:123", origin="derived", confirmation=None)
    registry = _FakeEvidenceRegistry(records=(record,))
    result = resolve_trust(
        claim,
        project_id="p1",
        principal_id="u1",
        scope="plan:approve",
        registry=registry,
    )
    assert result == "human_confirmed"


def test_backref_to_approved_feedback_record_promotes() -> None:
    record = ServerRecord(
        record_id="r2",
        project_id="p1",
        principal_id="u1",
        scope="feedback:approve",
        kind="approved_feedback",
    )
    claim = EvidenceClaim(actor_ref=None, origin="authored", confirmation="approved")
    registry = _FakeEvidenceRegistry(records=(record,))
    result = resolve_trust(
        claim,
        project_id="p1",
        principal_id="u1",
        scope="feedback:approve",
        registry=registry,
    )
    assert result == "approved_feedback"


@pytest.mark.parametrize(
    ("record_project", "record_principal", "record_scope"),
    [
        ("OTHER-PROJECT", "u1", "plan:approve"),
        ("p1", "OTHER-PRINCIPAL", "plan:approve"),
        ("p1", "u1", "feedback:approve"),
    ],
)
def test_backref_requires_exact_project_principal_scope_match(
    record_project: str, record_principal: str, record_scope: str
) -> None:
    """project/principal/scope 중 하나라도 어긋나면 역참조가 성립하지 않는다 —
    남의 승인 record 를 빌려 다른 project/principal/scope 를 승격시킬 수 없다.
    """
    record = ServerRecord(
        record_id="r3",
        project_id=record_project,
        principal_id=record_principal,
        scope=record_scope,
        kind="human_confirmed",
    )
    claim = EvidenceClaim(actor_ref="user:123", origin="human_confirmed", confirmation="approved")
    registry = _FakeEvidenceRegistry(records=(record,))
    result = resolve_trust(
        claim, project_id="p1", principal_id="u1", scope="plan:approve", registry=registry
    )
    assert result == UNCONFIRMED


# ---------------------------------------------------------------------------
# audio 외부 전송 — 명시 동의 + 목적/수신자/범위 기록 (LD-AUTH-004)
# ---------------------------------------------------------------------------


def test_audio_transfer_blocked_without_explicit_consent() -> None:
    with pytest.raises(ExchangeError) as excinfo:
        authorize_audio_transfer(
            explicit_consent=False,
            purpose="translation review",
            recipient="vendor-x",
            scope="full-song",
        )
    assert excinfo.value.code == "FORBIDDEN"
    assert excinfo.value.http_status == 403


@pytest.mark.parametrize(
    ("purpose", "recipient", "scope"),
    [
        ("", "vendor-x", "full-song"),
        ("translation review", "", "full-song"),
        ("translation review", "vendor-x", ""),
    ],
)
def test_audio_transfer_blocked_without_full_purpose_recipient_scope_record(
    purpose: str, recipient: str, scope: str
) -> None:
    """동의가 있어도 목적/수신자/범위 중 하나라도 비면 여전히 차단한다."""
    with pytest.raises(ExchangeError) as excinfo:
        authorize_audio_transfer(
            explicit_consent=True, purpose=purpose, recipient=recipient, scope=scope
        )
    assert excinfo.value.code == "FORBIDDEN"


def test_audio_transfer_allowed_with_full_consent_and_record() -> None:
    """양성 대조 — 동의 + 목적/수신자/범위가 전부 있으면 통과하고 기록을 남긴다."""
    record = authorize_audio_transfer(
        explicit_consent=True,
        purpose="translation review",
        recipient="vendor-x",
        scope="full-song",
    )
    assert record == AudioTransferRecord(
        purpose="translation review", recipient="vendor-x", scope="full-song"
    )

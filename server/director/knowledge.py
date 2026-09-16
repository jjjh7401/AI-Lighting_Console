"""지식 seed 검색 (SPEC-LDSTORE-001 M3 · REQ-LDPLUGIN-027).

design.md §3 의 검토된 5주제(음악 근거 규칙 · tracking 규칙 · 연출 case · rig·preset 규칙 ·
적용·안전 규칙)를 bounded inline typed details 로 제공한다. feedback seed(design.md §3 의
6번째 행)는 이 모듈의 범위 밖이다 — `SPEC-LDPLUGIN-001` 이 소유하는 `director-feedback`
패키지가 feedback 워크플로 전체(proposal·review·scope binding)를 맡는다. 이 모듈은 검색만
한다.

## 이 모듈이 승격하지 않는 것

이 패키지는 판단하지 않는다(`spec.md` §1). 사례는 법칙이 아니다 — 계약 §3 의
`KnowledgeRecord`: *"사례는 법칙이 아니며 조건·예외·권리 범위를 보존한다."* 그래서:

- 어떤 문자열도 "강제 법칙" 또는 "학습된 가중치" 로 표시하지 않는다(:data:`FORBIDDEN_LABELS`).
  이 검사는 seed 레코드 조립 시점에 한 번 더 돈다 — 통과한 값만 :data:`SEED_RECORDS` 가 된다.
- ``reviewed`` 가 아닌 지식은 검색에 노출하지 않는다 — 검토되지 않은 지식은 근거가 없다.
- proprietary archive 를 외부 공개 라이선스로 재표시하지 않는다 — ``rights_scope`` 가
  이 제약을 레코드마다 명시적으로 남긴다.

## cursor 는 current context 에 결합한다

계약 §3 `KnowledgePage`: *"cursor는 project/principal/query/context_id/context_digest/
retrieval revision에 묶인 opaque 서버 값이다. 곡·context·승인/철회 지식 revision이 바뀌면
409 CURSOR_STALE 다."* 이 모듈은 그 다섯 값을 cursor 에 인코딩하고, 다음 호출에서 하나라도
어긋나면 :class:`~server.director.models.ExchangeError` (``CURSOR_STALE``) 를 낸다.

## rights_scope 는 계약의 최소 shape 을 넘는 이 SPEC 의 추가 필드다

계약 §3 이 규정한 `KnowledgeRecord` 의 정확한 shape 에는 ``rights_scope`` 가 없다. 하지만
`REQ-LDPLUGIN-027` 은 "권리 범위" 보존을 명시적으로 요구하고, `KnowledgeRecord`/
`KnowledgePage` 는 다섯 exchange message_type 중 하나가 아니라 계약 §3 의 envelope
정의라 `exchange.schema.json` 의 closed-world 검사 대상이 아니다. 그래서 이 필드를 추가해도
계약의 wire shape 을 깨지 않는다. 실제 HTTP 표면(추후 `LDRECV` 가 붙인다)이 이 필드를 그대로
노출할지, ``provenance.rationale`` 로 접을지는 이 모듈의 범위 밖이다.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from server.director.knowledge_seed import RAW_TOPICS
from server.director.models import Detail, ExchangeError

#: 계약 §3 `KnowledgeRecord` 의 kind variant.
KIND_RULE = "rule"
KIND_CASE = "case"
KIND_APPROVED_FEEDBACK = "approved_feedback"
_KINDS: frozenset[str] = frozenset({KIND_RULE, KIND_CASE, KIND_APPROVED_FEEDBACK})

#: 계약 §3 `KnowledgeRecord`/§6.4 `FeedbackRecord` 의 scope enum.
SCOPE_THIS_SONG = "this_song"
SCOPE_THIS_SHOW = "this_show"
SCOPE_USER_STYLE = "user_style"
_SCOPES: frozenset[str] = frozenset({SCOPE_THIS_SONG, SCOPE_THIS_SHOW, SCOPE_USER_STYLE})

#: 계약 §3 `KnowledgeRecord`/`KnowledgePage` 의 상한.
_MAX_STRING_CHARS = 4096
_MAX_APPLICABILITY = 32
_MAX_EXCEPTIONS = 32
_MAX_PROCEDURE = 32
_MAX_AVOID = 32
_MAX_SEQUENCE = 64
_MAX_LIMITATIONS = 32
_MAX_FEEDBACK_CHANGES = 128
_MAX_QUERY_CHARS = 2048
_MAX_CURSOR_CHARS = 2048
_MIN_LIMIT = 1
_MAX_LIMIT = 50
_MAX_RECORD_BYTES = 64 * 1024
_MAX_PAGE_BYTES = 256 * 1024

#: design §3: *"사례는 법칙이 아니며..."* · REQ-LDPLUGIN-027: *"사례·retrieval memory를
#: 강제 법칙이나 weight training으로 표시하지 않는다."* 이 문구가 어느 레코드에도 있으면
#: 안 된다.
FORBIDDEN_LABELS: tuple[str, ...] = (
    "강제 법칙",
    "학습된 가중치",
    "mandatory rule",
    "learned weight",
)

#: kind → 그 kind 가 허용하는 `details` 키 집합 (계약 §3: *"kind와 details variant는
#: 일치해야 한다"*).
_DETAIL_KEYS: Mapping[str, frozenset[str]] = {
    KIND_RULE: frozenset({"procedure", "avoid"}),
    KIND_CASE: frozenset({"music_context", "sequence", "outcome", "limitations"}),
    KIND_APPROVED_FEEDBACK: frozenset(
        {"feedback_id", "plan_id", "plan_revision", "plan_digest", "changes"}
    ),
}

#: provenance 가 반드시 갖춰야 하는 다섯 필드 (스키마 `$defs.provenance` 와 같은 shape).
_PROVENANCE_FIELDS: frozenset[str] = frozenset(
    {"origin", "actor_ref", "source_refs", "evidence_refs", "rationale"}
)


class KnowledgeError(Exception):
    """seed 데이터 자체가 계약 shape 을 어길 때. 검색 이전에, 조립 시점에 막는다."""


def _check_bound(name: str, items: Sequence[Any], limit: int) -> None:
    if len(items) > limit:
        raise KnowledgeError(f"{name} 이 상한 {limit} 을 넘었습니다: {len(items)}")
    if len(items) == 0:
        raise KnowledgeError(f"{name} 이 비어 있습니다 — bounded 지만 typed 내용은 있어야 합니다.")


def _validate_details(record_id: str, kind: str, details: Mapping[str, Any]) -> None:
    allowed = _DETAIL_KEYS.get(kind)
    if allowed is None:
        raise KnowledgeError(f"{record_id}: 알 수 없는 kind 입니다: {kind!r}")
    unknown = set(details) - allowed
    missing = allowed - set(details)
    if unknown or missing:
        raise KnowledgeError(
            f"{record_id}: {kind} details 가 계약 shape 과 어긋납니다 — "
            f"unknown={sorted(unknown)}, missing={sorted(missing)}"
        )
    if kind == KIND_RULE:
        _check_bound("procedure", details["procedure"], _MAX_PROCEDURE)
        _check_bound("avoid", details["avoid"], _MAX_AVOID)
    elif kind == KIND_CASE:
        _check_bound("sequence", details["sequence"], _MAX_SEQUENCE)
        _check_bound("limitations", details["limitations"], _MAX_LIMITATIONS)
    elif kind == KIND_APPROVED_FEEDBACK:
        _check_bound("changes", details["changes"], _MAX_FEEDBACK_CHANGES)


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    """계약 §3 `KnowledgeRecord` — bounded inline typed details 를 담는다.

    ``rights_scope`` 는 이 SPEC 의 추가 필드다 (모듈 docstring 참고).

    ``reviewed`` 는 검색 노출 여부를 가르는 내부 플래그다 — 계약 §3 의 "검토된 revision만
    반환" 을 이 모듈이 집행하는 자리다. 외부 표현(:meth:`as_dict`)에는 없다 — 노출되는
    레코드는 이미 전부 검토된 것이기 때문이다.
    """

    record_id: str
    kind: str
    scope: str
    summary: str
    applicability: tuple[str, ...]
    exceptions: tuple[str, ...]
    provenance: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    resource_id: str
    reviewed_revision: int
    rights_scope: str
    details: Mapping[str, Any]
    reviewed: bool = True

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise KnowledgeError(f"{self.record_id}: 알 수 없는 kind 입니다: {self.kind!r}")
        if self.scope not in _SCOPES:
            raise KnowledgeError(f"{self.record_id}: 알 수 없는 scope 입니다: {self.scope!r}")
        if not (1 <= len(self.summary) <= _MAX_STRING_CHARS):
            raise KnowledgeError(f"{self.record_id}: summary 길이가 범위를 벗어났습니다.")
        if len(self.applicability) == 0 or len(self.applicability) > _MAX_APPLICABILITY:
            raise KnowledgeError(
                f"{self.record_id}: applicability(조건)가 비었거나 상한을 넘었습니다."
            )
        if len(self.exceptions) == 0 or len(self.exceptions) > _MAX_EXCEPTIONS:
            raise KnowledgeError(
                f"{self.record_id}: exceptions(예외)가 비었거나 상한을 넘었습니다."
            )
        if self.reviewed_revision < 1:
            raise KnowledgeError(
                f"{self.record_id}: reviewed_revision(검토 revision)이 1 미만입니다."
            )
        if not self.rights_scope:
            raise KnowledgeError(f"{self.record_id}: rights_scope(권리 범위)가 없습니다.")
        if set(self.provenance) < _PROVENANCE_FIELDS:
            missing = _PROVENANCE_FIELDS - set(self.provenance)
            raise KnowledgeError(f"{self.record_id}: provenance 에 {sorted(missing)} 가 없습니다.")
        _validate_details(self.record_id, self.kind, self.details)

    @classmethod
    def from_seed(cls, raw: Mapping[str, Any]) -> KnowledgeRecord:
        """`knowledge_seed` 의 순수 dict 를 레코드로. 여기서만 dataclass 가 만들어진다."""
        return cls(
            record_id=raw["record_id"],
            kind=raw["kind"],
            scope=raw["scope"],
            summary=raw["summary"],
            applicability=tuple(raw["applicability"]),
            exceptions=tuple(raw["exceptions"]),
            provenance=dict(raw["provenance"]),
            evidence_refs=tuple(raw["evidence_refs"]),
            resource_id=raw["resource_id"],
            reviewed_revision=int(raw["reviewed_revision"]),
            rights_scope=raw["rights_scope"],
            details=dict(raw["details"]),
            reviewed=bool(raw.get("reviewed", True)),
        )

    def as_dict(self) -> dict[str, Any]:
        """계약 §3 `KnowledgeRecord` 형태 + ``rights_scope``. ``reviewed`` 는 내부
        플래그라 여기 없다."""
        return {
            "record_id": self.record_id,
            "kind": self.kind,
            "scope": self.scope,
            "summary": self.summary,
            "applicability": list(self.applicability),
            "exceptions": list(self.exceptions),
            "provenance": dict(self.provenance),
            "evidence_refs": list(self.evidence_refs),
            "resource_id": self.resource_id,
            "reviewed_revision": self.reviewed_revision,
            "rights_scope": self.rights_scope,
            "details": dict(self.details),
        }


def _flatten(value: Any) -> str:
    """검사·검색 대상 텍스트로 dict/list 를 평평하게 편다."""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, Sequence):
        return " ".join(_flatten(v) for v in value)
    return str(value)


def _record_text(record: KnowledgeRecord) -> str:
    """레코드의 모든 검색·검사 대상 문자열을 하나로 이어붙인다."""
    parts = [record.summary, record.rights_scope, str(record.provenance.get("rationale", ""))]
    parts.extend(record.applicability)
    parts.extend(record.exceptions)
    parts.append(_flatten(record.details))
    return " ".join(parts)


def forbidden_label_offenders(
    records: Sequence[KnowledgeRecord],
) -> tuple[tuple[str, str], ...]:
    """어느 레코드가 금지 문구를 담고 있는지. 빈 tuple 이 통과다.

    (record_id, label) 쌍을 낸다 — 어느 레코드의 어느 문구인지 알아야 고칠 수 있다.
    """
    offenders: list[tuple[str, str]] = []
    for record in records:
        text = _record_text(record)
        for label in FORBIDDEN_LABELS:
            if label in text:
                offenders.append((record.record_id, label))
    return tuple(offenders)


#: design §3 의 검토된 5주제. `RAW_TOPICS` 는 순수 데이터이므로 여기서만 레코드가 된다.
SEED_RECORDS: tuple[KnowledgeRecord, ...] = tuple(
    KnowledgeRecord.from_seed(topic) for topic in RAW_TOPICS
)

_seed_offenders = forbidden_label_offenders(SEED_RECORDS)
if _seed_offenders:  # pragma: no cover — seed 데이터 자체가 깨진 경우에만 닿는다
    raise KnowledgeError(f"seed 레코드에 금지 문구가 있습니다: {_seed_offenders}")


@dataclass(frozen=True, slots=True)
class KnowledgePage:
    """계약 §3 `KnowledgePage`."""

    context_id: str
    context_digest: str
    items: tuple[KnowledgeRecord, ...]
    next_cursor: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "context_id": self.context_id,
            "context_digest": self.context_digest,
            "items": [item.as_dict() for item in self.items],
        }
        if self.next_cursor is not None:
            payload["next_cursor"] = self.next_cursor
        return payload


def _cursor_stale(message: str) -> ExchangeError:
    return ExchangeError("CURSOR_STALE", 409, message, (Detail("/cursor", "cursor stale"),))


def _encode_cursor(binding: Mapping[str, Any], offset: int) -> str:
    payload = {"binding": dict(binding), "offset": offset}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str) -> dict[str, Any]:
    if not (1 <= len(cursor) <= _MAX_CURSOR_CHARS):
        raise ExchangeError(
            "SCHEMA_INVALID",
            422,
            "cursor 길이가 범위를 벗어났습니다.",
            (Detail("/cursor", "length"),),
        )
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception as error:
        # cursor 는 계약상 opaque 서버 값이다 — 호출자가 무엇을 보냈든(깨진 base64, 임의
        # 문자열) 해석 실패는 전부 같은 처리를 받는다: 새 검색으로 다시 시작하라는 stale.
        raise _cursor_stale("cursor 를 해석할 수 없습니다.") from error
    if not isinstance(payload, dict) or "binding" not in payload or "offset" not in payload:
        raise _cursor_stale("cursor 형태가 올바르지 않습니다.")
    return payload


class KnowledgeService:
    """지식 seed 검색. 제출된 레코드는 ``reviewed`` 가 아니면 절대 노출하지 않는다."""

    def __init__(self, records: Sequence[KnowledgeRecord] = SEED_RECORDS) -> None:
        self._records = tuple(records)

    def search(
        self,
        *,
        project_id: str,
        principal_id: str,
        query: str,
        limit: int,
        context_id: str,
        context_digest: str,
        cursor: str | None = None,
    ) -> KnowledgePage:
        """계약 §3 `ld_search_knowledge` (`KnowledgePage`).

        cursor 는 project/principal/query/context_id/context_digest/retrieval revision 에
        결합된다 (계약 §3). 다섯 중 하나라도 이전 호출과 다르면 ``CURSOR_STALE`` 이다.
        """
        if not (1 <= len(query) <= _MAX_QUERY_CHARS):
            raise ExchangeError(
                "SCHEMA_INVALID",
                422,
                "query 길이가 1..2048 범위를 벗어났습니다.",
                (Detail("/query", "length"),),
            )
        if not (_MIN_LIMIT <= limit <= _MAX_LIMIT):
            raise ExchangeError(
                "SCHEMA_INVALID",
                422,
                "limit 이 1..50 범위를 벗어났습니다.",
                (Detail("/limit", "range"),),
            )

        retrieval_revision = self._retrieval_revision()
        binding = {
            "project_id": project_id,
            "principal_id": principal_id,
            "query": query,
            "context_id": context_id,
            "context_digest": context_digest,
            "retrieval_revision": retrieval_revision,
        }

        offset = 0
        if cursor is not None:
            state = _decode_cursor(cursor)
            if state.get("binding") != binding:
                raise _cursor_stale(
                    "cursor 가 결합된 project/principal/query/context/retrieval revision 중 "
                    "하나가 이전 호출과 다릅니다."
                )
            offset = int(state["offset"])

        matches = sorted(
            (
                record
                for record in self._records
                if record.reviewed and self._matches(record, query)
            ),
            key=lambda record: record.record_id,
        )

        page_items = tuple(matches[offset : offset + limit])
        self._enforce_bounds(page_items)

        next_offset = offset + len(page_items)
        next_cursor = _encode_cursor(binding, next_offset) if next_offset < len(matches) else None

        return KnowledgePage(
            context_id=context_id,
            context_digest=context_digest,
            items=page_items,
            next_cursor=next_cursor,
        )

    def _retrieval_revision(self) -> str:
        """검토된 지식의 현재 상태를 나타내는 값.

        검토된 레코드 집합이나 그 revision 이 바뀌면 이 값도 바뀐다 — 계약 §3:
        *"승인/철회 지식 revision이 바뀌면 409 CURSOR_STALE."* 이 모듈은 승인/철회를
        구현하지 않지만, 이 값을 레코드 집합의 함수로 둠으로써 그 계약을 미리 만족한다.
        """
        reviewed = sorted(
            (record.record_id, record.reviewed_revision)
            for record in self._records
            if record.reviewed
        )
        raw = json.dumps(reviewed, sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @staticmethod
    def _matches(record: KnowledgeRecord, query: str) -> bool:
        return query.strip().lower() in _record_text(record).lower()

    @staticmethod
    def _enforce_bounds(items: Sequence[KnowledgeRecord]) -> None:
        """계약 §3: *"record 직렬화 상한 64 KiB, page 상한 256 KiB이며 상세를 잘라 성공으로
        반환하지 않는다."*"""
        total = 0
        for item in items:
            size = len(json.dumps(item.as_dict(), ensure_ascii=False).encode("utf-8"))
            if size > _MAX_RECORD_BYTES:
                raise ExchangeError(
                    "PAYLOAD_TOO_LARGE",
                    413,
                    f"{item.record_id} 의 직렬화 크기가 상한 {_MAX_RECORD_BYTES} bytes 를 "
                    "넘었습니다.",
                )
            total += size
        if total > _MAX_PAGE_BYTES:
            raise ExchangeError(
                "PAYLOAD_TOO_LARGE",
                413,
                f"page 직렬화 크기가 상한 {_MAX_PAGE_BYTES} bytes 를 넘었습니다.",
            )

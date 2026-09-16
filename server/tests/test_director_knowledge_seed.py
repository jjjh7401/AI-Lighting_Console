"""지식 seed 검색 (SPEC-LDSTORE-001 M3 · AC-LDPLUGIN-027).

이 파일이 고정하는 것은 인수기준의 다섯 PASS 조건이다 — 어느 하나가 빠지면
REQ-LDPLUGIN-027 이 막으려는 것(법칙으로 오인되는 사례, current context 를 벗어난
cursor 재사용, 미검토 지식의 노출)이 조용히 통과한다.

1. seed 주제가 정확히 5개이고, 각 항목이 provenance·조건·예외·검토 revision·권리 범위를
   가진다.
2. 검색 결과가 bounded inline typed details 를 담는다 — 요약 문자열이 아니라 typed 구조.
3. current context 가 바뀌면 이전 cursor 는 stale 로 답한다.
4. 미승인 지식이 검색에 노출되지 않는다 (count == 0).
5. 응답 어디에도 사례/retrieval memory 를 "강제 법칙" 또는 "학습된 가중치" 로 표시하지 않는다.

**양성 대조 필수**: 전부 거부하는 필터도 "미승인은 0" 류 시험을 그냥 통과한다. 그래서 4번은
같은 질의 계열에서 **승인된 레코드가 실제로 나오는지**를 함께 확인한다. 5번도 마찬가지로
날조된 위반 레코드를 넣어 검사기가 실제로 잡는지 확인한다.
"""

from __future__ import annotations

import base64
import json
from collections import Counter
from typing import Any

import pytest

from server.director import knowledge as kb
from server.director.models import ExchangeError

_CONTEXT_ID = "context-001"
_CONTEXT_DIGEST_A = "sha256:" + "a" * 64
_CONTEXT_DIGEST_B = "sha256:" + "b" * 64
_PROJECT_ID = "project-001"
_PRINCIPAL_ID = "principal-001"


def _search(service: kb.KnowledgeService, **overrides: Any) -> kb.KnowledgePage:
    params: dict[str, Any] = {
        "project_id": _PROJECT_ID,
        "principal_id": _PRINCIPAL_ID,
        "query": "규칙",
        "limit": 50,
        "context_id": _CONTEXT_ID,
        "context_digest": _CONTEXT_DIGEST_A,
    }
    params.update(overrides)
    return service.search(**params)


@pytest.fixture
def service() -> kb.KnowledgeService:
    return kb.KnowledgeService()


# ---------------------------------------------------------------------------
# 1. 정확히 5개, 다섯 필드 존재
# ---------------------------------------------------------------------------


def test_exactly_five_seed_topics() -> None:
    assert len(kb.SEED_RECORDS) == 5, [r.record_id for r in kb.SEED_RECORDS]


def test_seed_topics_cover_four_rules_and_one_case() -> None:
    """design §3 의 5주제 — feedback seed(6번째 행)는 이 모듈의 범위 밖이다."""
    kinds = Counter(record.kind for record in kb.SEED_RECORDS)
    assert kinds == Counter({"rule": 4, "case": 1})


def test_record_ids_are_unique() -> None:
    ids = [record.record_id for record in kb.SEED_RECORDS]
    assert len(ids) == len(set(ids)), ids


@pytest.mark.parametrize("record", kb.SEED_RECORDS, ids=lambda r: r.record_id)
def test_every_record_has_the_five_required_fields(record: kb.KnowledgeRecord) -> None:
    """provenance · 조건(applicability) · 예외(exceptions) · 검토 revision · 권리 범위.

    존재만이 아니라 **비어 있지 않음**을 단언한다 — 빈 dict/tuple 은 "필드가 있다" 를
    형식적으로만 만족시키고 실제로는 아무 내용도 없는 상태다.
    """
    assert record.provenance, f"{record.record_id} 에 provenance 가 없습니다"
    assert set(record.provenance) >= {
        "origin",
        "actor_ref",
        "source_refs",
        "evidence_refs",
        "rationale",
    }
    assert len(record.applicability) >= 1, f"{record.record_id} 에 조건(applicability)이 없습니다"
    assert len(record.exceptions) >= 1, f"{record.record_id} 에 예외(exceptions)가 없습니다"
    assert record.reviewed_revision >= 1, f"{record.record_id} 의 검토 revision 이 비정상입니다"
    assert record.rights_scope, f"{record.record_id} 에 권리 범위(rights_scope)가 없습니다"


def test_missing_field_is_caught_not_silently_accepted() -> None:
    """음성 대조 — provenance 가 빈 dict 인 레코드는 생성 시점에 거부된다."""
    raw = dict(kb.RAW_TOPICS[0])
    raw = {**raw, "provenance": {}}
    with pytest.raises(Exception):  # noqa: B017 — KnowledgeError 또는 KeyError 어느 쪽이든 거부되어야 한다
        kb.KnowledgeRecord.from_seed(raw)


# ---------------------------------------------------------------------------
# 2. bounded inline typed details — 요약 문자열이 아니다
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("record", kb.SEED_RECORDS, ids=lambda r: r.record_id)
def test_details_is_a_typed_structure_not_a_summary_string(record: kb.KnowledgeRecord) -> None:
    assert isinstance(record.details, dict)
    assert record.details != record.summary

    if record.kind == kb.KIND_RULE:
        assert set(record.details) == {"procedure", "avoid"}
        assert 1 <= len(record.details["procedure"]) <= 32
        assert 1 <= len(record.details["avoid"]) <= 32
        assert all(isinstance(step, str) and step for step in record.details["procedure"])
    elif record.kind == kb.KIND_CASE:
        assert set(record.details) == {"music_context", "sequence", "outcome", "limitations"}
        assert 1 <= len(record.details["sequence"]) <= 64
        for step in record.details["sequence"]:
            assert set(step) == {
                "section_role",
                "intent",
                "actions_summary",
                "transition_summary",
            }
        assert 1 <= len(record.details["limitations"]) <= 32


def test_search_results_carry_full_details_inline(service: kb.KnowledgeService) -> None:
    """레코드를 다시 조회하지 않고도 결과 안에서 절차/사례 전문을 읽을 수 있다."""
    page = _search(service, query="음악")

    assert page.items, "검색 결과가 비어 있으면 이하 단언이 공허합니다"
    for item in page.items:
        payload = item.as_dict()
        assert isinstance(payload["details"], dict)
        assert payload["details"]  # 비어 있지 않다 — resource_id 만 있는 것이 아니다


def test_page_and_record_shape_match_the_contract() -> None:
    """계약 §3 `KnowledgePage`/`KnowledgeRecord` 의 top-level 키 집합."""
    service = kb.KnowledgeService()
    page = _search(service, query="규칙")

    payload = page.as_dict()
    assert set(payload) >= {"context_id", "context_digest", "items"}

    for item in page.items:
        record_payload = item.as_dict()
        assert set(record_payload) == {
            "record_id",
            "kind",
            "scope",
            "summary",
            "applicability",
            "exceptions",
            "provenance",
            "evidence_refs",
            "resource_id",
            "reviewed_revision",
            "rights_scope",
            "details",
        }


# ---------------------------------------------------------------------------
# 3. current context 변경 시 cursor 는 stale
# ---------------------------------------------------------------------------


def test_matching_context_cursor_continues_the_page(service: kb.KnowledgeService) -> None:
    """양성 대조 — 같은 context 로 재사용한 cursor 는 다음 페이지를 낸다."""
    first = _search(service, query="규칙", limit=1)
    assert first.next_cursor is not None
    assert len(first.items) == 1

    second = _search(service, query="규칙", limit=1, cursor=first.next_cursor)
    assert len(second.items) == 1
    assert second.items[0].record_id != first.items[0].record_id


def test_context_change_makes_the_cursor_stale(service: kb.KnowledgeService) -> None:
    first = _search(service, query="규칙", limit=1, context_digest=_CONTEXT_DIGEST_A)
    assert first.next_cursor is not None

    with pytest.raises(ExchangeError) as caught:
        _search(
            service,
            query="규칙",
            limit=1,
            cursor=first.next_cursor,
            context_digest=_CONTEXT_DIGEST_B,
        )

    assert caught.value.code == "CURSOR_STALE"
    assert caught.value.http_status == 409


def test_query_change_makes_the_cursor_stale(service: kb.KnowledgeService) -> None:
    """cursor 는 query 에도 결합된다 (계약 §3) — 검색어를 바꿔 재사용하면 다른 범위다."""
    first = _search(service, query="규칙", limit=1)

    with pytest.raises(ExchangeError) as caught:
        _search(service, query="안전", limit=1, cursor=first.next_cursor)

    assert caught.value.code == "CURSOR_STALE"


def test_malformed_cursor_is_rejected(service: kb.KnowledgeService) -> None:
    with pytest.raises(ExchangeError) as caught:
        _search(service, query="규칙", limit=1, cursor="not-a-real-cursor!!")

    assert caught.value.code == "CURSOR_STALE"


# ---------------------------------------------------------------------------
# 4. 미승인 지식 — count == 0 (양성 대조 포함)
# ---------------------------------------------------------------------------


def _unreviewed_variant(*, record_id: str, token: str, reviewed: bool) -> dict[str, Any]:
    raw = dict(kb.RAW_TOPICS[0])
    return {
        **raw,
        "record_id": record_id,
        "summary": f"{token} 을 담은 판정용 합성 레코드.",
        "reviewed": reviewed,
    }


def test_unreviewed_knowledge_never_surfaces() -> None:
    approved = kb.KnowledgeRecord.from_seed(
        _unreviewed_variant(
            record_id="kb-synthetic-approved", token="zzz-approved-marker", reviewed=True
        )
    )
    pending = kb.KnowledgeRecord.from_seed(
        _unreviewed_variant(
            record_id="kb-synthetic-pending", token="zzz-pending-marker", reviewed=False
        )
    )
    service = kb.KnowledgeService(records=(*kb.SEED_RECORDS, approved, pending))

    # 양성 대조 — 같은 필터를 통과하는 승인 레코드는 실제로 나온다.
    approved_page = _search(service, query="zzz-approved-marker")
    assert len(approved_page.items) == 1
    assert approved_page.items[0].record_id == "kb-synthetic-approved"

    pending_page = _search(service, query="zzz-pending-marker")
    assert len(pending_page.items) == 0


# ---------------------------------------------------------------------------
# 5. "강제 법칙"/"학습된 가중치" 로 표시하지 않는다 (날조 대조군 포함)
# ---------------------------------------------------------------------------


def test_no_seed_record_labels_itself_a_mandatory_rule_or_trained_weight() -> None:
    assert kb.forbidden_label_offenders(kb.SEED_RECORDS) == ()


def test_forbidden_label_sweep_actually_catches_a_violation() -> None:
    """날조 대조군 — 검사기가 헛돌지 않는지 확인한다."""
    tainted_raw = dict(kb.RAW_TOPICS[2])  # case 항목 — outcome 에 심는다
    tainted_raw = {
        **tainted_raw,
        "record_id": "kb-synthetic-tainted",
        "details": {**tainted_raw["details"], "outcome": "이것은 강제 법칙이다."},
    }
    tainted = kb.KnowledgeRecord.from_seed(tainted_raw)

    offenders = kb.forbidden_label_offenders((tainted,))

    assert offenders == (("kb-synthetic-tainted", "강제 법칙"),)


# ---------------------------------------------------------------------------
# 경계 — query/limit 검사
# ---------------------------------------------------------------------------


def test_empty_query_is_rejected(service: kb.KnowledgeService) -> None:
    with pytest.raises(ExchangeError) as caught:
        _search(service, query="")
    assert caught.value.code == "SCHEMA_INVALID"


@pytest.mark.parametrize("limit", [0, 51])
def test_limit_out_of_range_is_rejected(service: kb.KnowledgeService, limit: int) -> None:
    with pytest.raises(ExchangeError) as caught:
        _search(service, query="규칙", limit=limit)
    assert caught.value.code == "SCHEMA_INVALID"


def test_cursor_round_trips_as_opaque_base64_json(service: kb.KnowledgeService) -> None:
    """cursor 는 opaque 서버 값이다 — 형태를 단언하되 호출자가 해석하지 않는다."""
    page = _search(service, query="규칙", limit=1)
    assert page.next_cursor is not None

    decoded = json.loads(base64.urlsafe_b64decode(page.next_cursor.encode("ascii")))
    assert "binding" in decoded and "offset" in decoded

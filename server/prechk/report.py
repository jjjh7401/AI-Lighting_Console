"""Two-tier pre-check report: aggregate plus per-fixture, in Korean.

Shape and obligations (REQ-PRECHK-015, REQ-PRECHK-016, REQ-PRECHK-017):

  * the aggregate is not an independent number -- it is computed from the same
    rows the report prints, so a drift between them is impossible rather than
    merely tested;
  * every judgement code comes from a closed vocabulary
    (:mod:`server.prechk.verdicts`), and the label tables below are keyed by
    exactly those sets;
  * ``skipped_checks`` merges BOTH producers: the patch judge contributes the
    range-overlap descope, the macro axis contributes its own reason. A report
    that showed one and dropped the other would look complete while hiding a
    check nobody ran.

Label policy, and why it differs from ``server/looks/report.py``. That module's
``reason_label`` deliberately passes an unknown code through, because its
section-failure reasons come from the console as free strings and an invented
translation would keep the user from searching for the original. A pre-check
judgement has no such origin -- it is always a member of one of five closed sets
-- so an unknown code here means a bug upstream, and :func:`label` raises
(AC-PRECHK-012 ⑤ d).

That leaves nothing to reuse from the looks report at the STRING level: the two
vocabularies are disjoint (its keys are look/preset reasons, ours are patch
verdicts), and its one overlapping key, ``complete``, means "every look stored"
there and "the enumeration was not short" here -- borrowing it would mislabel
the number that matters most. What IS inherited is the PATTERN: labels live in
the presentation layer behind a public accessor, never in the schema or the
assets. Nothing private is imported from it, which
``server/tests/test_prechk_report.py`` enforces by AST scan (AC-PRECHK-012 ④).
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from server.prechk.macro import MacroResult
from server.prechk.patch import PatchEvaluation
from server.prechk.verdicts import (
    COLLISION_KIND,
    COMPLETENESS,
    FIXTURE_VERDICT,
    READ_FAILURE_KIND,
    SKIPPED_CHECK_KIND,
    UnknownVerdict,
    validate,
)

COMPLETENESS_LABELS = {
    "complete": "열거 완전 — 보고된 자식 수를 전량 읽었다",
    # NOT "there are unread fixtures": per-slot recovery can observe every
    # declared child while the read stays incomplete, because the index domain's
    # upper bound is unknown (design slot A). M8's live end-to-end run recovered
    # all 19 fixtures with missing_count 0 and this label still claimed unread
    # fixtures existed — a false statement in the one string the user reads
    # first. The count is reported separately, and only when it is non-zero.
    "incomplete": "열거 불완전 — 루트 열거가 짧았고 인덱스 정의역 상한을 모른다",
}

FIXTURE_VERDICT_LABELS = {
    "observed_clear": "이상 없음(관측 범위)",
    "collision": "충돌",
    "read_failed": "판독 실패",
    "not_assessed": "미판정 — 관측되지 않음",
}

COLLISION_KIND_LABELS = {
    "address_duplicate": "주소 중복 — 같은 유니버스·주소를 둘 이상이 점유",
    "range_overlap": "구간 겹침 — 채널 점유 구간이 서로 물림",
}

READ_FAILURE_KIND_LABELS = {
    "property_unreadable": "프로퍼티 판독 불가 — 콘솔이 값을 주지 않았다",
    "shape_invalid": "값 형태 부적합 — 함수 참조나 부재값 문자열",
    "address_parse_failed": "주소 파싱 실패 — 유니버스·주소 정수를 얻지 못했다",
    "type_mode_unresolved": "타입·모드 미확정 — 점유폭을 잇지 못했다",
}

SKIPPED_CHECK_KIND_LABELS = {
    "range_overlap_descope": "구간 겹침 판정 미수행",
    "macro_descope": "매크로 저작 미수행",
    "macro_no_groups": "매크로 대상 그룹 없음",
    "gate_unapproved": "초크포인트 승인 없음",
}

#: Every label table, keyed by vocabulary name. The test asserts each table's
#: key set equals its vocabulary exactly, in both directions.
VOCABULARY_LABELS = MappingProxyType(
    {
        "completeness": MappingProxyType(COMPLETENESS_LABELS),
        "fixture_verdict": MappingProxyType(FIXTURE_VERDICT_LABELS),
        "collision_kind": MappingProxyType(COLLISION_KIND_LABELS),
        "read_failure_kind": MappingProxyType(READ_FAILURE_KIND_LABELS),
        "skipped_check_kind": MappingProxyType(SKIPPED_CHECK_KIND_LABELS),
    }
)

# Sanity: a table that drifted from its vocabulary is a defect at import time,
# not at report time. The sets come from the vocabulary module so this cannot be
# satisfied by retyping the codes here.
for _vocabulary, _codes in (
    ("completeness", COMPLETENESS),
    ("fixture_verdict", FIXTURE_VERDICT),
    ("collision_kind", COLLISION_KIND),
    ("read_failure_kind", READ_FAILURE_KIND),
    ("skipped_check_kind", SKIPPED_CHECK_KIND),
):
    if set(VOCABULARY_LABELS[_vocabulary]) != set(_codes):
        raise UnknownVerdict(f"label table for {_vocabulary} does not match its vocabulary")

VISUAL_CONFIRMATION_NOTICE = "매크로 실행 결과는 응답 증거가 아니다 — 사람이 눈으로 확인해야 한다"


def label(vocabulary: str, code: str) -> str:
    """The Korean label for ``code``; an unrecognized code raises.

    :func:`server.prechk.verdicts.validate` runs first, so an unknown vocabulary
    and an unknown code both fail before any lookup. Nothing is returned as a
    fallback and the raw code is never handed back dressed as a label.
    """
    validate(vocabulary, code)
    return VOCABULARY_LABELS[vocabulary][code]


def _labelled_counts(vocabulary: str, counts: dict[str, int]) -> list[str]:
    """Non-zero counts as ``<label> <n>건``, in the vocabulary's sorted order."""
    return [
        f"{label(vocabulary, code)} {counts[code]}건" for code in sorted(counts) if counts[code] > 0
    ]


@dataclass(frozen=True)
class PrecheckReport:
    """The whole user-facing payload for one pre-check run.

    ``macro`` is optional because ``design.md`` §5.1 marks the section as present
    "매크로 요청 시": a permanent null would make every caller special-case it and
    would put an empty macro block in a report nobody asked a macro for.
    """

    evaluation: PatchEvaluation
    macro: MacroResult | None = None

    def skipped_checks(self) -> tuple[dict[str, str], ...]:
        """Both producers' skipped checks, patch first, deduplicated by kind."""
        rows = [check.to_dict() for check in self.evaluation.skipped_checks]
        if self.macro is not None:
            rows.extend(self.macro.skipped_checks())
        seen: set[str] = set()
        merged: list[dict[str, str]] = []
        for row in rows:
            kind = validate("skipped_check_kind", row["kind"])
            if kind in seen:
                continue
            seen.add(kind)
            merged.append(row)
        return tuple(merged)

    def summary_ko(self) -> str:
        """One-paragraph Korean summary whose every claim is a printed number.

        The completeness label leads, so an incomplete read cannot be skimmed as
        a clean bill of health -- the mistake ``research.md`` §4.8 records the
        investigation itself making.
        """
        inventory = self.evaluation.inventory
        parts = [
            label("completeness", inventory.completeness),
            f"관측 {inventory.observed_count}개 / 보고된 자식 수 {inventory.child_count}개",
        ]
        if inventory.missing_count:
            parts.append(f"미관측 {inventory.missing_count}개")
        parts.append(f"충돌 {self.evaluation.collision_total}건")
        verdicts = _labelled_counts("fixture_verdict", dict(self.evaluation.verdict_counts))
        if verdicts:
            parts.append(" · ".join(verdicts))
        failures = _labelled_counts("read_failure_kind", dict(self.evaluation.read_failure_counts))
        if failures:
            parts.append(" · ".join(failures))
        skipped = self.skipped_checks()
        if skipped:
            names = " · ".join(label("skipped_check_kind", row["kind"]) for row in skipped)
            parts.append(f"미수행 판정: {names}")
        if self.macro is not None:
            parts.append(VISUAL_CONFIRMATION_NOTICE)
        return ". ".join(parts) + "."

    def to_dict(self) -> dict:
        """The report payload (``design.md`` §5.1 top-level keys).

        ``verdict_counts`` and ``read_failure_counts`` are carried alongside the
        designed keys: ``AC-PRECHK-012`` ② requires a STORED aggregate that can be
        checked against the per-fixture rows, and a derived-on-read number gives
        the test nothing to compare.
        """
        payload = self.evaluation.to_dict()
        payload["skipped_checks"] = [dict(row) for row in self.skipped_checks()]
        if self.macro is not None:
            payload["macro"] = self.macro.to_dict()
        payload["summary_ko"] = self.summary_ko()
        return payload


def build_report(evaluation: PatchEvaluation, macro: MacroResult | None = None) -> PrecheckReport:
    """Compose one pre-check report from the patch verdict and optional macro."""
    return PrecheckReport(evaluation=evaluation, macro=macro)

"""버스킹 준비 마법사 — 집계 보고 계층 (SPEC-COPILOT-BUSKWIZ-001, M3).

REQ-BUSKWIZ-013 (집계 + 룩별 2단 구조화 보고) · REQ-BUSKWIZ-015 (한국어 1급).

번들 조립과 **다른 관심사**라 별도 모듈로 둔다: 한국어 표현 매핑은 커맨드
생성과 무관하고, `busking.py`는 이미 조회·원장·결합으로 세 책임을 진다.

@MX:NOTE: [AUTO] 이 모듈은 **읽고 세기만 한다**. 실행 포트·게이트·재시도
  경로를 갖지 않는다 — 중단된 번들을 다시 보내는 판단은 사람 몫이고, 같은
  instruction 안에서 재발화하면 앞서 성공한 `Store Preset`/`Label Preset`이
  dedupe에 조용히 접힌다(면제 집합 밖이다). 보고가 실행을 건드리는 순간
  "무엇이 일어났는가"를 말하는 문서가 "무엇을 더 할까"를 정하는 주체가 된다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from server.looks.busking import VALUE_LINE_COLLISION, GenreBundle
from server.looks.instantiate import (
    CONFLICT,
    NO_FREE_SLOT,
    POOL_UNADDRESSABLE,
    POOL_UNRESOLVED,
    CreatedPreset,
    SkippedStore,
)
from server.looks.resolver import UNADDRESSABLE
from server.looks.roles import AMBIGUOUS, NO_MATCH

__all__ = [
    "COMPLETE",
    "MATCH_VERDICT",
    "NONE",
    "PARTIAL",
    "SECTION_FAILURE",
    "BuskingReport",
    "LookVerdict",
    "UnmappedPair",
    "build_report",
    "reason_label",
    "to_korean",
    "verdict_label",
]

# 룩별 판정 3종. 닫힌 집합이며 "부분"을 "성공"으로 접지 않는다.
COMPLETE = "complete"
PARTIAL = "partial"
NONE = "none"

# 미매핑 사유의 **부류**. 둘은 서로 다른 사실이고 사용자의 조치도 다르다:
# 전자는 리그의 문제(그룹을 만들거나 이름을 고치면 해소)이고, 후자는 **관측
# 자체가 실패한 것**(같은 리그를 다시 읽으면 달라질 수 있다). 후자를 "이
# 리그에 백라이트가 없다"로 보고하면 보지 않은 리그에 대한 주장이 된다.
MATCH_VERDICT = "match_verdict"
SECTION_FAILURE = "section_failure"

_MATCH_VERDICTS = frozenset({AMBIGUOUS, NO_MATCH, UNADDRESSABLE})

# 표현 계층의 한국어 라벨. **자산이나 스키마가 아니라 여기** 산다 —
# `matching.py:17-19`가 장르 별칭을 자산이 아닌 코드 표에 둔 것과 같은 이유다
# (REQ-BUSKWIZ-015). 모르는 코드는 지어내지 않고 그대로 통과시킨다.
_REASON_LABELS = {
    CONFLICT: "이름 충돌 — 같은 이름의 프리셋이 이미 있음",
    NO_FREE_SLOT: "점유 미관측 — 빈 슬롯을 확정할 수 없음",
    POOL_UNRESOLVED: "해당 풀 없음",
    POOL_UNADDRESSABLE: "풀은 있으나 번호가 없음",
    VALUE_LINE_COLLISION: "값 라인이 앞선 룩과 동일 — 빈 저장을 막기 위해 건너뜀",
    AMBIGUOUS: "이름이 여러 역할에 걸림",
    NO_MATCH: "맞는 그룹 없음",
    UNADDRESSABLE: "그룹은 있으나 번호가 없음",
}

_VERDICT_LABELS = {COMPLETE: "전량 성공", PARTIAL: "부분", NONE: "저장 0건"}


def reason_label(code: str) -> str:
    """사유 코드의 한국어 라벨. 모르는 코드는 **그대로** 돌려준다.

    지어낸 번역은 사용자가 원문으로 검색할 수 없게 만들고, 섹션 실패 사유처럼
    콘솔·리그 계층에서 그대로 올라오는 문자열이 그 부류다.
    """
    return _REASON_LABELS.get(code, code)


def verdict_label(code: str) -> str:
    return _VERDICT_LABELS.get(code, code)


@dataclass(frozen=True)
class UnmappedPair:
    """미매핑 **하나** — 단위는 `(룩, 역할)` 쌍이다.

    리그를 1회만 해석하므로(REQ-BUSKWIZ-004) 하나의 미매핑 역할은 그것을
    선언한 모든 룩에서 반복된다. distinct 역할 수로 세면 룩별 합계와 어긋나
    산술 정합이 깨진다.
    """

    look_id: str
    role: str
    reason: str
    kind: str


@dataclass(frozen=True)
class LookVerdict:
    """룩 하나의 판정. 장르의 모든 룩이 정확히 한 번씩 여기 나타난다."""

    look_id: str
    display_name: str
    verdict: str
    created: int = 0
    skipped: int = 0
    unmapped: int = 0
    not_executed: int = 0
    failed: int = 0


@dataclass(frozen=True)
class BuskingReport:
    """집계 + 룩별 2단 보고. 집계만 내고 룩별을 생략하는 것은 금지다."""

    genre: str
    executed: bool = False
    looks: tuple[LookVerdict, ...] = ()
    created: tuple[CreatedPreset, ...] = ()
    unmapped: tuple[UnmappedPair, ...] = ()
    unmapped_roles: tuple[str, ...] = ()
    skipped: tuple[SkippedStore, ...] = ()
    not_executed: int = 0
    failed: int = 0
    drilldown_capped: bool = False

    @property
    def created_count(self) -> int:
        return len(self.created)

    @property
    def skipped_count(self) -> int:
        """N in "N개 건너뜀" — 단위는 프리셋 저장 1회이지 룩이 아니다."""
        return len(self.skipped)

    def to_dict(self) -> dict:
        """구조화 보고 (REQ-BUSKWIZ-013). 사람이 읽을 요약은 ``to_korean``."""
        return {
            "genre": self.genre,
            "executed": self.executed,
            "created": [
                {"family": c.family, "pool": c.pool, "slot": c.slot, "label": c.label}
                for c in self.created
            ],
            "skipped": [
                {
                    "family": s.family,
                    "reason": s.reason,
                    "reason_ko": reason_label(s.reason),
                    "pool": s.pool,
                    "slot": s.slot,
                    "detail": s.detail,
                }
                for s in self.skipped
            ],
            "unmapped": [
                {
                    "look_id": u.look_id,
                    "role": u.role,
                    "reason": u.reason,
                    "reason_ko": reason_label(u.reason),
                    "kind": u.kind,
                }
                for u in self.unmapped
            ],
            "unmapped_roles": list(self.unmapped_roles),
            "looks": [
                {
                    "look_id": v.look_id,
                    "display_name": v.display_name,
                    "verdict": v.verdict,
                    "created": v.created,
                    "skipped": v.skipped,
                    "unmapped": v.unmapped,
                    "not_executed": v.not_executed,
                    "failed": v.failed,
                }
                for v in self.looks
            ],
            "created_count": self.created_count,
            "skipped_count": self.skipped_count,
            "unmapped_count": self.unmapped_count,
            "not_executed": self.not_executed,
            "failed": self.failed,
            "drilldown_capped": self.drilldown_capped,
        }

    @property
    def unmapped_count(self) -> int:
        """`(룩, 역할)` 쌍의 개수. 사람이 읽을 목록은 ``unmapped_roles``."""
        return len(self.unmapped)


def _status_of(outcome: object) -> str:
    return getattr(outcome, "status", outcome) if outcome is not None else ""


def _kind_of(reason: str) -> str:
    return MATCH_VERDICT if reason in _MATCH_VERDICTS else SECTION_FAILURE


def build_report(bundle: GenreBundle, outcomes: Sequence[object] | None = None) -> BuskingReport:
    """번들과 (있다면) 실행 결과에서 2단 보고를 만든다.

    ``outcomes``는 ``run_commands``의 per-command status다. **룩별 판정은 실행
    결과에서 산출한다** — 계획 결과에는 중단 정보가 없기 때문이다. 귀속은
    ``bundle.spans``가 다리를 놓는다(결합 규칙을 여기서 다시 구현하지 않는다).

    ``outcomes``가 없으면 계획 수준 보고이며 ``executed=False``가 그 사실을
    말한다 — 실행하지 않은 것을 실행한 것처럼 보고하지 않는다.
    """
    statuses = [_status_of(o) for o in (outcomes or ())]
    executed = bool(statuses)

    created: list[CreatedPreset] = []
    skipped: list[SkippedStore] = []
    unmapped: list[UnmappedPair] = []
    verdicts: list[LookVerdict] = []
    total_not_executed = 0
    total_failed = 0

    spans = bundle.spans or ((0, 0),) * len(bundle.looks)
    for plan, (start, end) in zip(bundle.looks, spans, strict=False):
        created.extend(plan.created)
        skipped.extend(plan.skipped)
        for entry in plan.unmapped:
            unmapped.append(
                UnmappedPair(
                    look_id=plan.look_id,
                    role=entry.role,
                    reason=entry.reason,
                    kind=_kind_of(entry.reason),
                )
            )
        window = statuses[start:end]
        not_executed = window.count("not_executed")
        failed = window.count("failed")
        total_not_executed += not_executed
        total_failed += failed
        verdicts.append(
            LookVerdict(
                look_id=plan.look_id,
                display_name=plan.display_name,
                verdict=_verdict_for(plan, not_executed, failed),
                created=len(plan.created),
                skipped=plan.skipped_count,
                unmapped=len(plan.unmapped),
                not_executed=not_executed,
                failed=failed,
            )
        )

    return BuskingReport(
        genre=bundle.genre,
        executed=executed,
        looks=tuple(verdicts),
        created=tuple(created),
        unmapped=tuple(unmapped),
        unmapped_roles=tuple(sorted({pair.role for pair in unmapped})),
        skipped=tuple(skipped),
        not_executed=total_not_executed,
        failed=total_failed,
        drilldown_capped=any(plan.drilldown_capped for plan in bundle.looks),
    )


def _verdict_for(plan, not_executed: int, failed: int) -> str:
    if not plan.created:
        return NONE
    if plan.skipped or plan.unmapped or not_executed or failed:
        return PARTIAL
    return COMPLETE


def to_korean(report: BuskingReport) -> str:
    """사용자 대면 요약. 집계 한 단, 룩별 한 단 — 둘 다 낸다."""
    lines = [
        f"[{report.genre}] 생성 {report.created_count}개 · "
        f"건너뜀 {report.skipped_count}개 · "
        f"미매핑 {report.unmapped_count}건({len(report.unmapped_roles)}종) · "
        f"미실행 {report.not_executed}개",
    ]
    if not report.executed:
        lines.append("  ※ 실행 결과를 관측하지 않은 계획 단계 보고입니다.")
    if report.drilldown_capped:
        lines.append("  ※ 리그 조회가 상한에 걸렸습니다 — 관측이 완전하지 않습니다.")

    for preset in report.created:
        lines.append(f"  + {preset.pool}.{preset.slot} '{preset.label}' ({preset.family})")
    for store in report.skipped:
        where = f"{store.pool}.{store.slot}" if store.slot is not None else f"{store.pool}"
        lines.append(f"  - 건너뜀 {store.family} {where} — {reason_label(store.reason)}")
    for pair in report.unmapped:
        lines.append(f"  ? 미매핑 [{pair.look_id}] {pair.role} — {reason_label(pair.reason)}")

    lines.append("룩별:")
    for verdict in report.looks:
        detail = f"생성 {verdict.created} · 건너뜀 {verdict.skipped}"
        if verdict.not_executed:
            detail += f" · 미실행 {verdict.not_executed}"
        lines.append(f"  {verdict.display_name}: {verdict_label(verdict.verdict)} ({detail})")
    return "\n".join(lines)

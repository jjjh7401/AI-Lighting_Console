"""Result + report types for the pre-show checklist.

Every check reports one of three closed statuses. There is deliberately no
"warn" status: a pitfall that could not be verified reports ``skip`` (per the
project's no-unobserved-claim invariant — see ``server/preshow/pitfalls.py``),
never a soft pass dressed up as a caution.
"""

from __future__ import annotations

from dataclasses import dataclass

STATUS_VALUES = frozenset({"pass", "fail", "skip"})

#: Traffic-light signal for the whole checklist run.
SIGNAL_VALUES = frozenset({"green", "yellow", "red"})

SIGNAL_LABELS = {
    "green": "정상 — 전 항목 통과",
    "yellow": "주의 — 일부 항목 미확인(SKIP)",
    "red": "위험 — 실패 항목 있음",
}


@dataclass(frozen=True)
class CheckResult:
    """One checklist item's outcome.

    ``data`` carries whatever machine-readable evidence the check collected
    (a console payload, a computed count) — never required by callers, but
    kept alongside ``detail`` so a report consumer does not have to re-parse
    the human-readable string.
    """

    name: str
    status: str
    detail: str
    data: dict | None = None

    def __post_init__(self) -> None:
        if self.status not in STATUS_VALUES:
            raise ValueError(
                f"unknown check status {self.status!r} (allowed: {sorted(STATUS_VALUES)})"
            )

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "detail": self.detail, "data": self.data}


@dataclass(frozen=True)
class PreshowReport:
    """The whole pre-show checklist run: every check plus one traffic-light signal.

    The signal is computed from ``checks``, never stored independently, so it
    can never drift from the rows it summarizes:

    * any ``fail`` -> ``red`` (do not go on stage)
    * else any ``skip`` -> ``yellow`` (unverified — proceed with judgement)
    * else -> ``green`` (every item was actually checked and passed)
    """

    checks: tuple[CheckResult, ...]

    @property
    def signal(self) -> str:
        statuses = {check.status for check in self.checks}
        if "fail" in statuses:
            return "red"
        if "skip" in statuses:
            return "yellow"
        return "green"

    def counts(self) -> dict[str, int]:
        counts = {status: 0 for status in STATUS_VALUES}
        for check in self.checks:
            counts[check.status] += 1
        return counts

    def summary(self) -> str:
        counts = self.counts()
        return (
            f"{SIGNAL_LABELS[self.signal]} "
            f"(pass {counts['pass']} / fail {counts['fail']} / skip {counts['skip']})"
        )

    def to_dict(self) -> dict:
        return {
            "signal": self.signal,
            "summary": self.summary(),
            "checks": [check.to_dict() for check in self.checks],
        }

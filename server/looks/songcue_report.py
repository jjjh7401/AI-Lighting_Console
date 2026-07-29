from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.looks.report import COMPLETE, NONE, PARTIAL, reason_label, verdict_label
from server.looks.songcue import (
    EXPLICIT_DYNAMICS_REQUIRED,
    ROLE_UNMAPPED,
    UNMAPPED_LOOK,
    SongCueBundle,
    SongCueSectionBundle,
)

PROPERTY_UNOBSERVED_NOTE = (
    "State query confirms cue existence and names only; CueFade and TrigType are not "
    "present in state snapshots, while the responder prop command can read them when "
    "a separate property readback is explicitly requested."
)

UNKNOWN_VOCABULARY = "unknown_vocabulary"
DYNAMICS_LOOK_MISSING = "dynamics_look_missing"
ROLE_UNADDRESSED = "role_unaddressed"
VALUE_SKIPPED = "value_skipped"
VERDICTS = frozenset({COMPLETE, PARTIAL, NONE})


@dataclass(frozen=True)
class SongCueSectionVerdict:
    index: int
    name: str
    cue_number: int
    cue_name: str
    verdict: str
    reason: str | None = None
    reason_kind: str | None = None
    not_executed: int = 0
    failed: int = 0


@dataclass(frozen=True)
class SongCueReport:
    bundle: SongCueBundle
    section_verdicts: tuple[SongCueSectionVerdict, ...]
    generated_cues: tuple[dict[str, object], ...]
    unmapped_sections: tuple[dict[str, object], ...]
    skipped_saves: tuple[dict[str, object], ...]
    not_executed: int
    failed: int
    requery: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "song_title": self.bundle.song_title,
            "sequence": self.bundle.sequence_number,
            "sequence_name": self.bundle.sequence_name,
            "generated_cues": list(self.generated_cues),
            "unmapped_sections": list(self.unmapped_sections),
            "skipped_saves": list(self.skipped_saves),
            "sections": [
                {
                    "index": verdict.index,
                    "name": verdict.name,
                    "cue_number": verdict.cue_number,
                    "cue_name": verdict.cue_name,
                    "verdict": verdict.verdict,
                    "verdict_ko": verdict_label(verdict.verdict),
                    "reason": verdict.reason,
                    "reason_ko": reason_label(verdict.reason) if verdict.reason else None,
                    "reason_kind": verdict.reason_kind,
                    "not_executed": verdict.not_executed,
                    "failed": verdict.failed,
                }
                for verdict in self.section_verdicts
            ],
            "summary": {
                "section_count": len(self.bundle.sections),
                "generated_count": len(self.generated_cues),
                "unmapped_count": len(self.unmapped_sections),
                "skipped_save_count": len(self.skipped_saves),
                "not_executed": self.not_executed,
                "failed": self.failed,
            },
            "property_unobserved": PROPERTY_UNOBSERVED_NOTE,
            "requery": self.requery,
        }

    def to_korean(self) -> str:
        data = self.to_dict()
        summary = data["summary"]
        lines = [
            f"섹션 {summary['section_count']}개 · 큐 {summary['generated_count']}개 · "
            f"미매핑 {summary['unmapped_count']}개 · 건너뜀 {summary['skipped_save_count']}개 · "
            f"미실행 {summary['not_executed']}개"
        ]
        for verdict in self.section_verdicts:
            reason = f" — {reason_label(verdict.reason)}" if verdict.reason else ""
            lines.append(f"{verdict.name}: {verdict_label(verdict.verdict)}{reason}")
        lines.append(PROPERTY_UNOBSERVED_NOTE)
        return "\n".join(lines)


def build_songcue_report(
    bundle: SongCueBundle,
    outcomes: Sequence[object] | None = None,
    requery_payload: Mapping[str, object] | None = None,
) -> SongCueReport:
    statuses = [_status_of(outcome) for outcome in (outcomes or ())]
    position = 1
    verdicts: list[SongCueSectionVerdict] = []
    generated: list[dict[str, object]] = []
    unmapped: list[dict[str, object]] = []
    skipped_saves: list[dict[str, object]] = []
    not_executed_total = 0
    failed_total = 0
    for section in bundle.sections:
        width = len(section.commands)
        window = statuses[position : position + width] if width else []
        position += width
        not_executed = window.count("not_executed")
        failed = window.count("failed")
        not_executed_total += not_executed
        failed_total += failed
        verdict = _section_verdict(section, not_executed, failed)
        verdicts.append(verdict)
        if section.commands:
            generated.append(_generated_cue(bundle, section))
        if verdict.reason_kind in {UNKNOWN_VOCABULARY, DYNAMICS_LOOK_MISSING, ROLE_UNADDRESSED}:
            unmapped.append(_unmapped_section(verdict))
        if verdict.reason_kind == VALUE_SKIPPED:
            skipped_saves.append(_skipped_save(verdict))
    return SongCueReport(
        bundle=bundle,
        section_verdicts=tuple(verdicts),
        generated_cues=tuple(generated),
        unmapped_sections=tuple(unmapped),
        skipped_saves=tuple(skipped_saves),
        not_executed=not_executed_total,
        failed=failed_total,
        requery=_verify_requery(bundle, requery_payload) if requery_payload is not None else None,
    )


def _section_verdict(
    section: SongCueSectionBundle,
    not_executed: int,
    failed: int,
) -> SongCueSectionVerdict:
    reason = section.skipped[0].reason if section.skipped else None
    reason_kind = _reason_kind(reason)
    if section.commands and not not_executed and not failed:
        verdict = COMPLETE
    elif section.commands:
        verdict = PARTIAL
    else:
        verdict = NONE
    return SongCueSectionVerdict(
        index=section.section.index,
        name=section.section.name,
        cue_number=section.cue_number,
        cue_name=section.cue_name,
        verdict=verdict,
        reason=reason,
        reason_kind=reason_kind,
        not_executed=not_executed,
        failed=failed,
    )


def _reason_kind(reason: str | None) -> str | None:
    if reason == EXPLICIT_DYNAMICS_REQUIRED:
        return UNKNOWN_VOCABULARY
    if reason == UNMAPPED_LOOK:
        return DYNAMICS_LOOK_MISSING
    if reason == ROLE_UNMAPPED:
        return ROLE_UNADDRESSED
    if reason:
        return VALUE_SKIPPED
    return None


def _generated_cue(bundle: SongCueBundle, section: SongCueSectionBundle) -> dict[str, object]:
    return {
        "sequence": bundle.sequence_number,
        "cue_number": section.cue_number,
        "name": section.cue_name,
        "section_index": section.section.index,
    }


def _unmapped_section(verdict: SongCueSectionVerdict) -> dict[str, object]:
    return {
        "index": verdict.index,
        "name": verdict.name,
        "cue_number": verdict.cue_number,
        "reason": verdict.reason,
        "reason_kind": verdict.reason_kind,
    }


def _skipped_save(verdict: SongCueSectionVerdict) -> dict[str, object]:
    return {
        "index": verdict.index,
        "name": verdict.name,
        "cue_number": verdict.cue_number,
        "reason": verdict.reason,
    }


def _verify_requery(bundle: SongCueBundle, payload: Mapping[str, object]) -> dict[str, object]:
    observed = _observed_cues(payload)
    expected = [
        {"cue_number": section.cue_number, "name": section.cue_name}
        for section in bundle.stored_sections
    ]
    return {
        "matched": observed == expected,
        "expected": expected,
        "observed": observed,
    }


def _observed_cues(payload: Mapping[str, object]) -> list[dict[str, object]]:
    children = payload.get("children")
    if not isinstance(children, list):
        return []
    observed: list[dict[str, object]] = []
    for child in children:
        if not isinstance(child, Mapping):
            continue
        if child.get("class") != "Cue":
            continue
        number = child.get("cueNo", child.get("i"))
        name = child.get("name")
        if isinstance(number, int) and isinstance(name, str):
            observed.append({"cue_number": number, "name": name})
    return sorted(observed, key=lambda item: int(item["cue_number"]))


def _status_of(outcome: object) -> str:
    return getattr(outcome, "status", outcome) if outcome is not None else ""

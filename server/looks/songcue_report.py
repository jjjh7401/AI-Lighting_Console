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

# 큐를 못 받은 구간의 사유를 **감독의 말**로 옮긴 것. 역할 부재만 리그 지문에
# 달려 있어 역할 이름을 받아 조립하고(``_gap_reason``), 나머지 셋은 코드 하나로
# 결정되므로 여기서 끝난다.
_NOTICE_REASONS: dict[str, str] = {
    DYNAMICS_LOOK_MISSING: "이 장르에 맞는 룩이 없습니다",
    UNKNOWN_VOCABULARY: "구간 이름에서 세기를 읽지 못했습니다",
    VALUE_SKIPPED: "앞 구간과 조명 값이 같습니다",
}


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

    def to_operator_notice(self) -> str:
        """큐를 못 받은 구간을 감독이 읽는 **한 문장**으로. 없으면 빈 문자열.

        ``to_korean`` 과 갈라 두는 이유는 독자가 다르다는 것 하나다. 그쪽은
        모델이 읽는 전량 보고(구간마다 한 줄 + 판정 코드)이고, 이쪽은 감독이
        채팅에서 스쳐 읽는 고지다 — 확정 고지 「구간 N건 채택 · M건 제외.」와
        같은 결이어야 하고, 그 문장 옆에 나란히 서면서 길어지면 안 된다.

        건너뜀이 **0건이면 빈 문자열**이다. 이 값이 조립되는 자리(요약 문면)는
        오늘의 출력과 바이트 동일해야 하고, 침묵이 결함인 것은 사라진 큐가
        있을 때뿐이다 — 없을 때 한 줄 더 붙이는 것은 소음이다.

        단위는 「명령」이 아니라 **구간**이다. 감독이 화면에서 센 것이 구간이고,
        2026-09-06 실기에서 어긋난 것도 「구간 4건 확인 → 큐 3건 저장」이었다.
        """
        gaps = [
            (verdict, section)
            for verdict, section in zip(self.section_verdicts, self.bundle.sections, strict=True)
            if not section.commands
        ]
        if not gaps:
            return ""
        clauses = " · ".join(
            f"'{verdict.name}': {_gap_reason(verdict, section)}" for verdict, section in gaps
        )
        return (
            f"구간 {len(self.bundle.sections)}건 중 큐 {len(self.generated_cues)}건만 "
            f"저장했습니다 — {clauses}."
        )

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


def _gap_reason(verdict: SongCueSectionVerdict, section: SongCueSectionBundle) -> str:
    """구간 하나가 큐를 못 받은 이유 — 역할 부재면 **없는 역할을 이름으로** 댄다.

    이름을 대는 것이 이 함수의 값이다. 「역할이 안 묶였습니다」는 감독이 할 수
    있는 일이 없는 문장이지만, 「배경 역할 그룹이 없습니다」는 그룹을 만들거나
    이름을 고치면 해소된다고 말한다.
    """
    if verdict.reason_kind == ROLE_UNADDRESSED:
        # dict.fromkeys — 같은 역할이 두 번 들어와도 한 번만, 순서는 그대로.
        roles = " · ".join(dict.fromkeys(entry.role for entry in section.unmapped))
        if roles:
            return f"이 리그에 {roles} 역할 그룹이 없습니다"
        # 역할 목록이 비어 오는 갈래가 있다(리그 구간 자체가 안 온 경우). 지어내지
        # 않고 범위를 좁히지 않은 채로 말한다.
        return "이 리그에 필요한 역할 그룹이 없습니다"
    fixed = _NOTICE_REASONS.get(verdict.reason_kind or "")
    if fixed is not None:
        return fixed
    # 모르는 사유는 원문 그대로 — 지어낸 번역은 감독이 검색할 수 없게 만든다.
    return reason_label(verdict.reason) if verdict.reason else "사유가 기록되지 않았습니다"


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
        # F-2(M0 실측): 모든 시퀀스는 암묵 시스템 큐 `OffCue`·`CueZero`를 갖는다.
        # `cueNo`가 없는 자식(`OffCue`)은 응답기가 "번호를 확신할 수 없다"고 말한 것이므로
        # 나열 위치 `i`로 대체 추정하지 않는다 — 그 추정이 사용자 큐 1번과 충돌해
        # `requery.matched`를 구조적으로 거짓으로 만들었다(M7 라이브 실측).
        # 생성 큐 번호는 항상 1 이상이므로(REQ-SONGCUE-007) 0 이하는 시스템 큐다.
        # 표시 이름으로 걸러내지 않는다 — 이름에서 정체성을 끌어내는 것은 금지다.
        number = child.get("cueNo")
        name = child.get("name")
        if isinstance(number, int) and number >= 1 and isinstance(name, str):
            observed.append({"cue_number": number, "name": name})
    return sorted(observed, key=lambda item: int(item["cue_number"]))


def _status_of(outcome: object) -> str:
    return getattr(outcome, "status", outcome) if outcome is not None else ""

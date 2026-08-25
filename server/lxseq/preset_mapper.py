"""LX-SEQ PRESET 매퍼 (SPEC-COPILOT-LXSEQ-003 M2).

순수 함수다 — 콘솔·네트워크 입출력 0, 명령 문자열 조립 0.
**`Store Preset` 문형을 여기서 만들지 않는다.** 번역은 툴 층이 기존 빌더로 한다.

## 왜 번역이 여기 없는가 (REQ-LXSEQ3-009 를 「툴 층」으로 읽은 근거)

문면은 「매퍼가 기존 빌더를 재사용한다」인데 그 빌더는 `server/web/session.py`
에 있고, 매퍼가 그것을 임포트하면 **순환**이 난다:
`lxseq.preset_mapper -> web.session -> orchestrator.tools -> lxseq.*`.
002 의 `server/groupgen/write.py` 독스트링이 같은 순환을 이미 적어 뒀다.
그리고 AC-LXSEQ3-009 의 기계 검증(`grep "Store Preset" server/lxseq/` 빈 출력)은
번역이 툴 층에 있을 때만 만족된다 — AC 의 검사가 옳고 REQ 의 산문이 층을 잘못
적었다. 같은 이유로 REQ-LXSEQ3-010(번들 바이트 계측)도 툴 층이 한다 — 명령이
있어야 바이트를 잴 수 있다. 문면 정정은 카드 t75, 판정 근거는 progress.md §E.2.

## 보류를 버리지 않는다

파서가 19행을 전부 읽고 그중 6건만 저장 가능하다고 판정한다. 매퍼는 저장
가능한 것만 계획하되 **보류 13건을 사유 클래스와 함께 그대로 나른다.** 그래야
최종 보고가 「6건 성공」이 아니라 **「19 중 6 계획 · 13 보류(클래스별)」**로 나온다.
버리면 나머지가 어디로 갔는지 아무도 모르고, 다음 사람이 무엇을 풀어야 하는지도
모른다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.lxseq.preset_parser import LxseqPresetRecord

#: 풀을 못 읽었다 — 빈 슬롯을 잴 수 없으므로 계획을 내지 않는다.
POOL_UNREADABLE = "pool_unreadable"

#: 풀 목록이 절단됐다 — 안 보이는 슬롯이 점유돼 있을 수 있다.
POOL_TRUNCATED = "pool_truncated"

#: 필요한 만큼 빈 슬롯이 없다 — 부분 계획을 내지 않는다.
SLOT_SHORTFALL = "slot_shortfall"


@dataclass(frozen=True)
class PresetPlacement:
    """한 프리셋의 배정 — RIG ID 와 콘솔 슬롯의 대응.

    이 표가 산출물에 남아야 다음 단계(큐, LXSEQ-004)가 `COL.01` 같은 RIG ID 로
    콘솔 슬롯을 찾을 수 있다. 시트에는 슬롯 번호가 없고 배정은 콘솔이 답한 빈
    슬롯에서 오므로, 기록하지 않으면 대응이 사라진다.
    """

    preset_id: str
    name: str
    kind: str
    value_raw: str
    slot: int


@dataclass(frozen=True)
class PresetHold:
    """계획에 못 들어간 한 건 — 사유 클래스와 산문을 함께 나른다."""

    preset_id: str
    kind: str
    hold_classes: tuple[str, ...]
    details: tuple[str, ...]


@dataclass(frozen=True)
class SlotShortfall:
    """필요와 가용의 대조표. 부분 계획 대신 이것을 낸다."""

    needed: int
    available: int
    missing: int


@dataclass(frozen=True)
class PresetMapResult:
    """매퍼 산출물.

    `refusal` 이 있으면 `planned` 는 반드시 비어 있다 — 어긋나면 0건이다.
    `held` 는 `refusal` 과 무관하게 항상 실린다.
    """

    planned: tuple[PresetPlacement, ...]
    held: tuple[PresetHold, ...]
    refusal: str | None
    refusal_detail: str
    shortfall: SlotShortfall | None
    #: 확인 한계 — 산출물이 스스로 말한다(REQ-LXSEQ3-014).
    unverified: tuple[str, ...] = ("value_match",)
    unverified_reason: str = (
        "슬롯 점유는 되읽어 확인할 수 있지만 **값이 맞는지는 이 채널로 읽히지 "
        "않는다**. 「슬롯이 찼다」는 「무언가 저장됐다」까지만 말한다 — "
        "「검증된 N건」으로 읽으면 틀린 값이 조용히 영속한다"
    )


def _held_from(record: LxseqPresetRecord) -> PresetHold:
    return PresetHold(
        preset_id=record.preset_id,
        kind=record.kind,
        hold_classes=record.hold_classes,
        details=tuple(reason.detail for reason in record.hold_reasons),
    )


def _occupied_slots(section: Mapping[str, object]) -> set[int] | None:
    """콘솔이 답한 점유 슬롯 집합. 못 읽으면 None — **추측하지 않는다.**"""
    listed = section.get("objects")
    if not isinstance(listed, list):
        return None
    occupied: set[int] = set()
    for entry in listed:
        number = entry.get("no") if isinstance(entry, Mapping) else None
        if not isinstance(number, int):
            # 한 항목의 번호를 못 읽으면 **어느 슬롯도** 비었다고 말할 수 없다.
            # 002 의 `_group_numbers` 가 같은 판단을 한다.
            return None
        occupied.add(number)
    return occupied


def map_presets(
    records: Sequence[LxseqPresetRecord],
    *,
    pool_section: Mapping[str, object],
) -> PresetMapResult:
    """저장 가능한 레코드에 **콘솔이 답한 빈 슬롯**을 배정한다.

    슬롯을 세지 않는다 — 점유 집합에 없는 번호를 오름차순으로 고른다.
    점유 슬롯에는 절대 쓰지 않는다(REQ-LXSEQ3-007): 프리셋은 경고 없이 덮어쓰고,
    값은 되읽을 수 없어 덮어쓴 것을 복구할 방법이 없다.

    풀을 못 읽었거나 빈 슬롯이 모자라면 **부분 계획 대신 0건**을 낸다
    (REQ-LXSEQ3-008). 반쯤 맞는 프리셋이 쇼파일에 남고 다음 단계(큐)가 그것을
    참조하는 것이 최악이기 때문이다.
    """
    held = tuple(_held_from(r) for r in records if not r.storable)
    storable = [r for r in records if r.storable]

    if section_reason := section_refusal(pool_section):
        return PresetMapResult(
            planned=(),
            held=held,
            refusal=section_reason[0],
            refusal_detail=section_reason[1],
            shortfall=None,
        )

    occupied = _occupied_slots(pool_section)
    if occupied is None:
        return PresetMapResult(
            planned=(),
            held=held,
            refusal=POOL_UNREADABLE,
            refusal_detail=(
                "풀 목록의 항목 하나에서 슬롯 번호를 못 읽었다 — 어느 슬롯도 "
                "비었다고 말할 수 없다. 추측해서 배정하지 않는다"
            ),
            shortfall=None,
        )

    ceiling = int(pool_section.get("capacity") or 0) or None
    empty: list[int] = []
    candidate = 1
    while len(empty) < len(storable):
        if ceiling is not None and candidate > ceiling:
            break
        if candidate not in occupied:
            empty.append(candidate)
        candidate += 1

    if len(empty) < len(storable):
        shortfall = SlotShortfall(
            needed=len(storable), available=len(empty), missing=len(storable) - len(empty)
        )
        return PresetMapResult(
            planned=(),
            held=held,
            refusal=SLOT_SHORTFALL,
            refusal_detail=(
                "필요 "
                + str(shortfall.needed)
                + " · 가용 "
                + str(shortfall.available)
                + " — 부분 계획을 내지 않는다"
            ),
            shortfall=shortfall,
        )

    planned = tuple(
        PresetPlacement(
            preset_id=record.preset_id,
            name=record.name,
            kind=record.kind,
            value_raw=record.value_raw,
            slot=slot,
        )
        for record, slot in zip(storable, empty, strict=True)
    )
    return PresetMapResult(
        planned=planned, held=held, refusal=None, refusal_detail="", shortfall=None
    )


def section_refusal(section: Mapping[str, object]) -> tuple[str, str] | None:
    """풀 단면 자체가 못 쓸 상태인가. 쓸 수 있으면 None."""
    if section.get("ok") is False or isinstance(section.get("reason"), str):
        return (
            POOL_UNREADABLE,
            "프리셋 풀을 못 읽었다: " + str(section.get("reason") or "not-ok"),
        )
    if section.get("truncated"):
        return (
            POOL_TRUNCATED,
            "풀 목록이 절단됐다 — 안 보이는 슬롯이 점유돼 있을 수 있으므로 "
            "어느 슬롯도 비었다고 말하지 않는다",
        )
    return None

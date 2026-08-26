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

## 보류를 버리지 않는다 — 바구니는 셋이다

파서가 19행을 전부 읽고 그중 6건만 저장 가능하다고 판정한다. 매퍼는 저장
가능한 것만 계획하되 **보류 13건을 사유 클래스와 함께 그대로 나른다.** 그래야
최종 보고가 「6건 성공」이 아니라 **「19 중 6 계획 · 13 보류(클래스별)」**로 나온다.
버리면 나머지가 어디로 갔는지 아무도 모르고, 다음 사람이 무엇을 풀어야 하는지도
모른다.

**세 번째 바구니가 있다**(SPEC-COPILOT-PRESETIDEM-001, 카드 t87): 이름이 이미
풀에 있어 계획에 안 들어간 것은 `already_present` 로 나른다. `held` 에 섞지
않는다 — 섞으면 「19 중 6 계획 · 13 보류」 집계가 **콘솔 상태 의존**이 되어
같은 CSV 가 날마다 다른 수를 보고한다(REQ-IDEM-003).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.lxseq.preset_parser import LxseqPresetRecord
from server.presets.store import preset_label_refusal
from server.rig.section import (
    SECTION_TRUNCATED,
    SECTION_UNREAD,
)
from server.rig.section import section_refusal as rig_section_refusal

#: 풀을 못 읽었다 — 빈 슬롯을 잴 수 없으므로 계획을 내지 않는다.
POOL_UNREADABLE = "pool_unreadable"

#: 풀 목록이 절단됐다 — 안 보이는 슬롯이 점유돼 있을 수 있다.
POOL_TRUNCATED = "pool_truncated"

#: 필요한 만큼 빈 슬롯이 없다 — 부분 계획을 내지 않는다.
SLOT_SHORTFALL = "slot_shortfall"

#: 같은 이름이 이미 있다 — 그 레코드의 **목표 상태가 이미 달성돼 있다**.
#: 거절 사유가 아니라 보류 사유다. 부분 계획이 아니라 수렴이기 때문이다.
NAME_TAKEN = "name_taken"

#: 확인 한계 — 점유 슬롯 중 이름을 못 읽은 것이 있어 그 슬롯과는 대조하지 못했다.
NAME_COLLISION_UNVERIFIED = "name_collision"

#: 이름을 명령에 실을 수 없다 — 따옴표가 `Label Preset` 의 구분자라 문법이 깨진다.
#: 거절 사유가 아니라 보류 사유다: 나머지 레코드는 멀쩡히 나갈 수 있다.
NAME_UNSENDABLE = "name_unsendable"

_VALUE_MATCH_REASON = (
    "슬롯 점유는 되읽어 확인할 수 있지만 **값이 맞는지는 이 채널로 읽히지 "
    "않는다**. 「슬롯이 찼다」는 「무언가 저장됐다」까지만 말한다 — "
    "「검증된 N건」으로 읽으면 틀린 값이 조용히 영속한다"
)

_NAME_UNREADABLE_REASON = (
    "점유 슬롯 중 **이름을 못 읽은 것**이 있어 그 슬롯과는 이름을 대조하지 "
    "못했다. 같은 이름이 이미 있는데도 계획에 들어갔을 수 있다 — 「중복은 "
    "없다」로 읽지 마라"
)


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

    `refusal` 이 없을 때 **세 바구니의 합이 읽은 수와 같다**(REQ-IDEM-004):
    `planned` + `held` + `already_present`. 이 합이 깨지면 세 번째 바구니를
    안 읽는 소비자가 생겼다는 신호다.
    """

    planned: tuple[PresetPlacement, ...]
    held: tuple[PresetHold, ...]
    refusal: str | None
    refusal_detail: str
    shortfall: SlotShortfall | None
    #: 이름이 이미 풀에 있어 계획에 안 들어간 것. `held` 와 **섞지 않는다** —
    #: 섞으면 파서 판정 집계가 콘솔 상태에 따라 달라진다(REQ-IDEM-003).
    #: 풀을 못 읽은 거절 경로에서는 비어 있다 — 이름을 알 수 없기 때문이다.
    already_present: tuple[PresetHold, ...] = ()
    #: 확인 한계 — 산출물이 스스로 말한다(REQ-LXSEQ3-014).
    unverified: tuple[str, ...] = ("value_match",)
    unverified_reason: str = _VALUE_MATCH_REASON


def _held_from(record: LxseqPresetRecord) -> PresetHold:
    return PresetHold(
        preset_id=record.preset_id,
        kind=record.kind,
        hold_classes=record.hold_classes,
        details=tuple(reason.detail for reason in record.hold_reasons),
    )


def _unsendable_name_from(record: LxseqPresetRecord, reason: str) -> PresetHold:
    """이름을 명령에 실을 수 없어 보류된 한 건.

    거르는 자리는 **배정 전**이다 — 배정 후에 거르면 쓰지도 않을 슬롯을 예약해
    없는 부족분이 생긴다(`name_taken` 이 같은 이유로 같은 자리에 있다).

    판정은 `preset_label_refusal` 이 한다. 여기서 다시 세지 않는 이유는, 술어가
    갈라지면 계획이 통과시킨 이름에서 빌더가 터지기 때문이다 — 그것이 이 보류가
    막으려는 결함 그 자체다(t97).
    """
    return PresetHold(
        preset_id=record.preset_id,
        kind=record.kind,
        hold_classes=(NAME_UNSENDABLE,),
        details=(
            "이 이름은 콘솔에 못 보낸다: "
            + record.name
            + " — "
            + reason
            + ". 계획에 넣지 않는 이유는 넣으면 사용자가 「보낼 수 있다」고 적힌 "
            "목록을 승인한 **뒤에** 예외를 보기 때문이다. 시트에서 이름을 고쳐 "
            "다시 부르면 된다",
        ),
    )


def _already_present_from(record: LxseqPresetRecord) -> PresetHold:
    """이름이 이미 있어 보류된 한 건.

    **「이미 있음」은 「맞게 있음」이 아니다.** 값은 되읽히지 않으므로 이름만
    같고 값이 다른 프리셋이 그대로 남는다. 그 한계를 산문에 적어 둔다.
    """
    return PresetHold(
        preset_id=record.preset_id,
        kind=record.kind,
        hold_classes=(NAME_TAKEN,),
        details=(
            "같은 이름이 이미 있다: "
            + record.name
            + " — 목표 상태가 이미 달성돼 있어 계획에 넣지 않는다. 덮어쓰지 "
            "않는 이유는 프리셋이 경고 없이 덮이고 값을 되읽을 수 없어 복구 "
            "수단이 없기 때문이다(REQ-LXSEQ3-007). **값이 맞는지는 확인 못 "
            "한다** — 이름만 같고 값이 다를 수 있다",
        ),
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


def _occupied_names(section: Mapping[str, object]) -> tuple[set[str], bool]:
    """콘솔이 답한 점유 **이름** 집합과 「못 읽은 이름이 있었나」.

    이름은 이미 와 있다 — `rig_object` 가 `no` 와 `name` 을 둘 다 내고 툴이
    그대로 싣는다. 안 볼 뿐이었다(SPEC-COPILOT-PRESETIDEM-001 §A.3).

    **번호와 달리 이름은 못 읽어도 거절하지 않는다.** 번호를 틀리면 점유 슬롯을
    덮어써 복구가 불가능하지만, 이름을 모르면 생기는 것은 **중복**이다. 무게가
    달라 처방도 다르다 — 거절 대신 `unverified` 에 한계를 싣는다(REQ-IDEM-005).
    잘 도는 임포트를 한 번도 본 적 없는 상태를 근거로 통째로 막지 않는다.
    """
    listed = section.get("objects")
    names: set[str] = set()
    if not isinstance(listed, list):
        return names, True
    incomplete = False
    for entry in listed:
        raw = entry.get("name") if isinstance(entry, Mapping) else None
        text = raw if isinstance(raw, str) else ""
        if not text:
            # 이름 없는 점유 슬롯 — 이 슬롯과는 대조 자체가 성립하지 않는다.
            incomplete = True
            continue
        names.add(text)
    return names, incomplete


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

    **이름이 이미 있으면 그 레코드만 보류한다**(REQ-IDEM-001). 점유 슬롯을 피하는
    것은 **슬롯 보증**이지 **동일성 보증**이 아니어서, 이름을 안 보면 같은 시트를
    두 번 돌릴 때 전부 복제된다. 거르는 자리는 **배정 전**이다 — 배정 후에 거르면
    쓰지도 않을 슬롯을 예약해 없는 부족분이 생긴다.
    """
    held_list = [_held_from(r) for r in records if not r.storable]
    # 못 보내는 이름은 **여기서** 걸러진다 — 배정 전이자 거절 판정 전이다.
    # 거절 경로도 `held` 를 그대로 나르므로, 풀을 못 읽어 0건이 된 회신에도
    # 이 보류가 실린다. 사용자가 시트를 고칠 근거는 콘솔 상태와 무관하다(t97).
    storable: list[LxseqPresetRecord] = []
    for record in records:
        if not record.storable:
            continue
        if (reason := preset_label_refusal(record.name)) is not None:
            held_list.append(_unsendable_name_from(record, reason))
            continue
        storable.append(record)
    held = tuple(held_list)

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

    pool_names, names_incomplete = _occupied_names(pool_section)
    unverified: tuple[str, ...] = ("value_match",)
    unverified_reason = _VALUE_MATCH_REASON
    if names_incomplete:
        unverified = unverified + (NAME_COLLISION_UNVERIFIED,)
        unverified_reason = _VALUE_MATCH_REASON + "\n\n" + _NAME_UNREADABLE_REASON

    # 한 CSV 안의 중복도 같은 술어로 막는다 — 파서는 `duplicate_id` 만 보고
    # 이름은 안 본다(REQ-IDEM-006). 안 막으면 이 가드가 **첫 실행에서** 복제한다.
    taken = set(pool_names)
    to_plan: list[LxseqPresetRecord] = []
    already: list[PresetHold] = []
    for record in storable:
        if record.name in taken:
            already.append(_already_present_from(record))
            continue
        taken.add(record.name)
        to_plan.append(record)
    already_present = tuple(already)

    ceiling = int(pool_section.get("capacity") or 0) or None
    empty: list[int] = []
    candidate = 1
    while len(empty) < len(to_plan):
        if ceiling is not None and candidate > ceiling:
            break
        if candidate not in occupied:
            empty.append(candidate)
        candidate += 1

    if len(empty) < len(to_plan):
        shortfall = SlotShortfall(
            needed=len(to_plan), available=len(empty), missing=len(to_plan) - len(empty)
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
            already_present=already_present,
            unverified=unverified,
            unverified_reason=unverified_reason,
        )

    planned = tuple(
        PresetPlacement(
            preset_id=record.preset_id,
            name=record.name,
            kind=record.kind,
            value_raw=record.value_raw,
            slot=slot,
        )
        for record, slot in zip(to_plan, empty, strict=True)
    )
    return PresetMapResult(
        planned=planned,
        held=held,
        refusal=None,
        refusal_detail="",
        shortfall=None,
        already_present=already_present,
        unverified=unverified,
        unverified_reason=unverified_reason,
    )


#: 공유 술어의 코드 -> 이 도메인의 사유 코드. 술어는 하나지만 어휘는 도메인마다
#: 다르다 — 하류(`held_by_class`, 산출물 문면)가 이 파일의 코드를 세므로 그대로
#: 둔다. 판정 로직만 공유하고 어휘는 안 바꾼다.
_SECTION_REFUSAL_CODES = dict(
    [(SECTION_UNREAD, POOL_UNREADABLE), (SECTION_TRUNCATED, POOL_TRUNCATED)]
)


def section_refusal(section: Mapping[str, object]) -> tuple[str, str] | None:
    """풀 단면 자체가 못 쓸 상태인가. 쓸 수 있으면 None.

    판정은 `server/rig/section.py` 하나가 한다 — 이 자리에 사본을 두면 술어가
    갈라지고, 갈라진 날 한쪽만 고쳐진다. 이 파일이 원래 그 사본이었다(t109).

    여기서 하는 일은 **어휘 번역뿐**이다: 공유 코드를 이 도메인의 사유 코드로
    옮긴다. 문면은 술어가 낸 것을 그대로 나른다 — 다시 쓰면 두 문면이 갈린다.
    """
    verdict = rig_section_refusal(section)
    if verdict is None:
        return None
    code, detail = verdict
    return (_SECTION_REFUSAL_CODES[code], detail)

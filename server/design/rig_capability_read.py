"""콘솔 -> 리그 능력 판독 배선 — 연출 계획이 실제로 부르는 진입점.

t344 B. A 편의 :func:`server.design.capability_join.read_rig_capabilities` 는
``fid -> (FixtureType, Mode)`` 를 **이미 읽은 값으로** 받는다. 이 모듈이 그 값을
콘솔에서 만든다.

## 조인 키 — 측정으로 확정했다 (2026-09-11)

배차 전제는 「fid <-> 기종 조인 키가 이 경로에 없다」였다. **그 전제는 이 저장소에
대해 틀렸다.** 두 판독이 같은 슬롯 도메인을 쓴다:

    prechk.inventory.FIXTURE_ROOT      = 'Patch/Stages/1/Fixtures'   (:52)
    vwx.patchplan.FID_FIXTURE_ROOT     = 'Patch/Stages/1/Fixtures'   (:44)

    read_inventory(...)      -> FixtureRecord.slot -> (fixture_type, mode)
    read_existing_fids(...)  -> ExistingFidRead.fid_slots -> (slot, fid)

``prechk.inventory`` 가 FID 를 화이트리스트 밖에 둔 것은 **그 모듈의 정책**이고
(``inventory.fid_note`` 독스트링), 콘솔의 한계가 아니다 —
``vwx.patchplan.read_existing_fids`` 가 슬롯마다 ``FID`` 프로퍼티를 실제로 읽고
``fid_slots`` 로 슬롯과 값을 **함께** 나른다(round23 R21-A). 그래서 슬롯을 fid 로
승격시키는 추측 없이 조인이 된다. 슬롯을 fid 인 척 쓰는 것은 여전히 금지다 — 이
모듈은 그 두 판독을 슬롯으로 맞물릴 뿐이다.

🔴 **부분 판독은 조인 결과를 좁힌다.** ``ExistingFidRead.complete`` 가 거짓이면
``fid_slots`` 는 부분집합이고, 못 맞물린 슬롯은 사라지는 대신 :attr:`DesignRigRead.gap`
에 코드로 남는다. 조용히 줄어든 리그는 「장비가 적은 리그」와 바이트 동일하다.

**읽기 전용.** ``query_state`` · ``query_property`` · ``query_properties`` 뿐이다.
콘솔 쓰기 0.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from server.design.capability_join import (
    FixtureTypeRef,
    RigCapabilities,
    read_rig_capabilities,
)
from server.design.capability_verdict import patch_records
from server.prechk.inventory import COMPLETE, read_inventory
from server.prechk.mode_read import read_fixture_type_names
from server.vwx.patchplan import read_existing_fids

__all__ = [
    "RIG_GAP_FID_PARTIAL",
    "RIG_GAP_INVENTORY_PARTIAL",
    "RIG_GAP_UNREADABLE",
    "DesignRigRead",
    "notice_for",
    "read_design_rig",
]

#: 판독이 왜 부분인지 — **코드**다(문면이 아니다). ``session`` 의 좌표 결손 코드와
#: 같은 규율: 호출자마다 감독에게 할 말이 다르고, 문면을 여기서 만들면 호출자가
#: 그것을 잘라 붙인다(카드 t311).
RIG_GAP_UNREADABLE = "rig_unreadable"
RIG_GAP_FID_PARTIAL = "fid_partial"
RIG_GAP_INVENTORY_PARTIAL = "inventory_partial"


@dataclass(frozen=True)
class DesignRigRead:
    """연출 계획이 쓰는 리그 판독 — 읽힌 것과 **못 읽은 것**.

    ``gap`` 이 비어 있지 않으면 ``patch`` 는 부분집합이고, 그때 「이 리그에 그 장비가
    없다」는 결론을 낼 수 없다. ``attempted`` 가 거짓이면 조회 자체를 하지 않았다 —
    기본 인스턴스가 「읽었고 리그가 비었다」로 읽히면 안 된다(``ExistingFidRead`` 의
    round15 N01 과 같은 함정).
    """

    attempted: bool = False
    patch: tuple[dict[str, object], ...] = ()
    capabilities: RigCapabilities | None = None
    gap: str = ""
    detail: str = ""
    unread_fids: Mapping[int, str] = field(default_factory=dict)
    incomplete_fids: Mapping[int, str] = field(default_factory=dict)

    @property
    def whole(self) -> bool:
        """이 판독을 전수로 읽어도 되는가."""
        return self.attempted and not self.gap


def read_design_rig(
    port: object,
    *,
    fixture_types_root: str,
    budget: int = 256,
) -> DesignRigRead:
    """콘솔에서 리그 능력을 읽어 ``build_rig_profile(patch=...)`` 재료로 만든다.

    ``port`` 는 게이트의 상태 포트다 — ``query_state(path, *, offset=0)`` ·
    ``query_property`` · ``query_properties`` 세 읽기를 다 갖춘 하나의 물건
    (``SafetyGate.state_port``). 세 하위 판독이 각자 다른 Protocol 로 그것을 보므로
    어댑터가 필요 없다.

    콘솔이 안 답하면 **빈 리그를 만들지 않는다** — :data:`RIG_GAP_UNREADABLE` 을
    실은 판독을 돌려주고, 호출자가 그것을 고지한다. 예외 형태는 포트 구현마다
    다르고(프로덕션 포트는 ``server.safety`` 의 ``StateQueryError`` 를 던진다) 이
    모듈은 ``server.safety`` 를 임포트할 수 없어(A 편·``FidPropertyPort`` 와 같은
    층 규율) 폭넓게 잡아 코드로 번역한다.
    """
    try:
        type_names_read = read_fixture_type_names(port, root=fixture_types_root)
        type_names = dict(type_names_read.pairs)
        # 🔴 `type_names` 를 **넘기지 않는다**. 넘기면 `read_inventory` 가
        # `fixture_type` 을 핸들에서 이름으로 갈아끼우고(`_name_handle_types`),
        # A 편의 `_type_slot` 은 핸들 문법(`FixtureType 11`)에서만 슬롯을 뽑으므로
        # 모든 fid 가 `type_slot_unknown` 으로 미판독이 된다(이 카드가 실제로
        # 밟은 함정). 번역은 A 편이 같은 표로 한 번만 한다.
        inventory = read_inventory(port)
        fid_read = read_existing_fids(port)
    except Exception as error:  # noqa: BLE001 — 위 독스트링: 층 경계상 형태를 모른다
        return DesignRigRead(
            attempted=True,
            gap=RIG_GAP_UNREADABLE,
            detail=f"{type(error).__name__}: {error}",
        )

    if not fid_read.attempted or fid_read.root_unreadable:
        return DesignRigRead(
            attempted=True,
            gap=RIG_GAP_UNREADABLE,
            detail="FID 판독이 루트에서 실패했습니다",
        )

    slot_to_fid = dict(fid_read.fid_slots)
    refs: list[FixtureTypeRef] = []
    unjoined = 0
    for record in inventory.fixtures:
        fid = slot_to_fid.get(record.slot)
        if fid is None:
            # 슬롯을 fid 로 **승격시키지 않는다**. 조인 키가 없는 슬롯은 빠지고,
            # 그 사실은 아래 gap 으로 나간다 — 틀린 fid 에 능력을 붙이는 것보다
            # 낫다(그쪽은 조용히 엉뚱한 장비를 가리킨다).
            unjoined += 1
            continue
        refs.append(FixtureTypeRef(fid=fid, type_raw=record.fixture_type, mode_raw=record.mode))

    caps = read_rig_capabilities(
        port,
        port,
        root=fixture_types_root,
        fixtures=refs,
        type_names=type_names,
        budget=budget,
    )

    gap = ""
    detail = ""
    if unjoined:
        gap = RIG_GAP_FID_PARTIAL
        detail = f"슬롯 {unjoined}개는 FID 를 못 읽어 능력 판독에서 빠졌습니다"
    elif type_names_read.whole_unconfirmed or inventory.completeness != COMPLETE:
        gap = RIG_GAP_INVENTORY_PARTIAL
        detail = (
            f"인벤토리 판독이 부분입니다(완전성 {inventory.completeness}, "
            f"기종 목록 미확정 {type_names_read.whole_unconfirmed})"
        )
    elif caps.unread or caps.incomplete:
        gap = RIG_GAP_INVENTORY_PARTIAL
        detail = f"능력 미판독 {len(caps.unread)}대 · 부분 판독 {len(caps.incomplete)}대"

    return DesignRigRead(
        attempted=True,
        patch=patch_records(caps),
        capabilities=caps,
        gap=gap,
        detail=detail,
        unread_fids=dict(caps.unread),
        incomplete_fids=dict(caps.incomplete),
    )


def notice_for(read: DesignRigRead) -> str:
    """감독이 읽는 한 줄 — 결손이 없으면 빈 문자열.

    지어낸 리그를 내지 않는다는 규칙의 관측 가능한 면이다(카드 t277·t311 과 같은 결).
    """
    if not read.attempted:
        return ""
    if read.gap == RIG_GAP_UNREADABLE:
        return (
            "장비 능력을 콘솔에서 읽지 못해 기종별 판정(팬틸트·줌 범위) 없이 "
            f"설계했습니다 — {read.detail}"
        )
    if read.gap:
        return f"장비 능력 판독이 부분입니다 — {read.detail}"
    return ""

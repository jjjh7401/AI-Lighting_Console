"""M5 — 실행 전달(사람) · 검증 인계 (REQ-AUTOPATCH-004·018·020·021).

**이 모듈은 콘솔에 아무것도 쓰지 않는다.** 서버가 패치를 실행하지 않는 것은 구현 편의가
아니라 실측 결과다 — `AddFixtures` 자동 실행은 실행 경로 10가지 · 인자 변형 8종에서
픽스처를 **한 대도** 만들지 못했다(`progress.md` §E.2 M0 1~5차). v0.1.3 반자동 모델에서
서버의 일은 **검토용 Lua 소스와 실행 절차를 사람에게 넘기는 것**까지이고, 그 다음 동작은
사람의 실행이 끝난 뒤의 **검증 읽기**(REQ-AUTOPATCH-023, M6)다.

**금지를 검사가 아니라 구조로 둔다** — `luagen`이 목적지 변경 명령을 만들 수 없게 한 것과
같은 방식이다(design.md §5 슬롯 C). 이 모듈은 실행 포트도 배포 파이프라인도 **인자로 받지
않고 import하지도 않는다.** 발화할 대상이 없으므로 "승인이 있으면 서버가 실행한다"는 분기가
애초에 조립될 수 없다(AC-AUTOPATCH-015②③ · 018 · 019).

**전달물의 본체는 `luagen.render_addfixtures_plugin(entries)`다.** 이 모듈은 그 결과에
자유 문자열을 덧붙이지 않는다 — Lua 본문에 닿는 유일한 통로는 `LuaPatchEntry`의 6필드이며,
생성기가 거부한 항목은 **조용히 고치지 않고 사유와 함께 제외**한다(M4 계약).

**드라이런과 전달의 차이는 한 줄(`delivered = not dry_run`)이다.** 드라이런도 Lua 소스
전문을 낸다(REQ-AUTOPATCH-003 · AC-AUTOPATCH-004②). 다르게 만드는 것은 **실행 절차와
검증 인계**뿐이며, 한 호출 안에서 드라이런이 전달로 승격되는 경로는 없다(AC-019④).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.vwx.luagen import (
    LuaGenerationError,
    LuaPatchEntry,
    render_addfixtures_call,
    render_addfixtures_plugin,
)
from server.vwx.patchplan import (
    IRREVERSIBLE_WARNING,
    AddressPlan,
    PatchCandidate,
    PatchTargetExclusion,
)
from server.vwx.typemap import TypeResolution
from server.vwx.verdicts import (
    FID_NOT_ASSIGNED,
    FIXTURE_NAME_MISSING,
    LUA_GENERATION_REFUSED,
    TYPE_CONFIRMATION_PENDING,
    TYPE_RESOLVED,
)

HANDOFF_STATUS_DRY_RUN = "dry_run"
HANDOFF_STATUS_DELIVERED = "delivered"

NEXT_STEP_REVIEW = "review_dry_run"
NEXT_STEP_HUMAN_EXECUTION = "human_execution_then_verification_read"

EXECUTION_PERFORMED_BY = "human"

# 함정 4 — 플러그인이 오류 없이 끝난 것은 성공이 아니다. 2026-08-06 실물 재현:
# `exec`가 OK를 반환하고 픽스처는 0건 생성됐다.
PLUGIN_EXIT_IS_NOT_SUCCESS = (
    "플러그인이 오류 없이 끝난 것은 성공이 아니다 — AddFixtures는 실패해도 nil을 반환할 뿐이다. "
    "생성 여부는 서버의 검증 읽기로만 확정된다."
)

# 정직 고지 — 사람이 실행하는 경로의 종단 성공은 이 빌드에서 아직 확인되지 않았다.
END_TO_END_UNVERIFIED = (
    "이 절차의 종단 성공은 이 빌드에서 아직 확인되지 않았다 — 서버 자동 실행 경로는 "
    "전부 0건이었고, "
    "사람이 실행하는 경로의 종단 확인은 라이브 검증 마일스톤에 남아 있다."
)

# 실행 절차는 실측으로 확정된 것만 적는다(`progress.md` §0 항목 4·9, 함정 9·11).
# 반증된 처방(패치 편집기 선행 · 목적지 이동)은 **적지 않는다** — REQ-AUTOPATCH-024 [v0.1.3].
HUMAN_EXECUTION_PROCEDURE = (
    "1. 아래 Lua 소스를 플러그인 라이브러리 파일로 저장한다.",
    "2. 콘솔에서 Import Plugin '<파일명>' 으로 임포트한다 — 이 빌드의 deploy 동사는 "
    "플러그인 소스를 쓰지 못하므로(객체만 생기고 소스는 빈 상태로 조용히 실행된다) 쓰지 않는다.",
    "3. 같은 이름으로 재임포트하면 소스가 갱신되지 않는다 — 새 이름을 쓰거나 "
    "슬롯을 비우고 임포트한다.",
    "4. 임포트한 플러그인을 콘솔에서 사람이 실행한다. 서버는 이 실행을 대행하지 않는다.",
    "5. 실행이 끝나면 서버에 검증 읽기를 요청한다 — 생성 여부는 그 재조회로만 확정된다.",
)

DELIVERY_WARNINGS = (IRREVERSIBLE_WARNING, PLUGIN_EXIT_IS_NOT_SUCCESS, END_TO_END_UNVERIFIED)


@dataclass(frozen=True)
class HandoffEntry:
    """전달물에 남은 항목 하나. `address`는 **언제나 도면 주소 그대로**다."""

    candidate_id: str
    fid: int
    name: str
    console_type: str
    console_mode: str
    universe: int
    address: int
    footprint: int

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "fid": self.fid,
            "name": self.name,
            "console_type": self.console_type,
            "console_mode": self.console_mode,
            "universe": self.universe,
            "address": self.address,
            "footprint": self.footprint,
        }


@dataclass(frozen=True)
class PatchHandoff:
    dry_run: bool
    delivered: bool
    status: str
    next_step: str
    lua_source: str | None
    entries: tuple[HandoffEntry, ...] = ()
    exclusions: tuple[PatchTargetExclusion, ...] = ()
    procedure: tuple[str, ...] = ()
    warnings: tuple[str, ...] = DELIVERY_WARNINGS

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": True,
            "status": self.status,
            "dry_run": self.dry_run,
            "delivered": self.delivered,
            "next_step": self.next_step,
            "execution_performed_by": EXECUTION_PERFORMED_BY,
            "lua_source": self.lua_source,
            "entries": [entry.to_dict() for entry in self.entries],
            "exclusions": [exclusion.to_dict() for exclusion in self.exclusions],
            "procedure": list(self.procedure),
            "warnings": list(self.warnings),
        }


def build_patch_handoff(
    targets: Sequence[PatchCandidate],
    *,
    address_plan: AddressPlan,
    resolutions: Sequence[TypeResolution],
    names: Mapping[str, str],
    dry_run: bool = True,
) -> PatchHandoff:
    """계획된 항목을 **사람이 콘솔에서 실행할 전달물**로 만든다 (REQ-AUTOPATCH-018).

    서버는 여기서 아무것도 발화하지 않는다 — 실행 포트도 배포 파이프라인도 이 함수의
    어휘에 없다. 승인(`dry_run=false`)이 있어도 달라지는 것은 **실행 절차와 검증 인계를
    함께 내보내는지**뿐이며, 실행 자체는 사람의 몫이다(AC-AUTOPATCH-015②③).

    `names`는 호출자가 주는 픽스처 이름이다 — 이 계층은 이름을 **지어내지 않는다**.
    비어 있거나 생성기가 거부하면 그 항목을 **제외하고 사유를 보고**한다.
    """
    delivered = not dry_run

    target_by_id = {target.id: target for target in targets}
    resolution_by_id = {resolution.request.candidate_id: resolution for resolution in resolutions}

    entries: list[HandoffEntry] = []
    lua_entries: list[LuaPatchEntry] = []
    exclusions: list[PatchTargetExclusion] = list(address_plan.exclusions)

    for planned in address_plan.entries:
        target = target_by_id.get(planned.candidate_id)
        if target is None:
            raise ValueError(
                f"주소 계획에 대상 없는 항목이 있다: {planned.candidate_id!r} — "
                "계획과 대상 집합은 같은 호출에서 나온 것이어야 한다."
            )

        resolution = resolution_by_id.get(planned.candidate_id)
        if (
            resolution is None
            or resolution.status != TYPE_RESOLVED
            or resolution.console_type is None
            or resolution.console_mode is None
        ):
            exclusions.append(
                _exclusion(
                    target,
                    TYPE_CONFIRMATION_PENDING,
                    "콘솔 타입·모드가 확정되지 않았다 — "
                    "확인 전에 되돌릴 수 없는 생성을 전달하지 않는다.",
                )
            )
            continue

        if target.assigned_fid is None:
            exclusions.append(
                _exclusion(
                    target,
                    FID_NOT_ASSIGNED,
                    "FID가 배정되지 않았다 — 배정 없이 생성하면 엉뚱한 픽스처를 덮을 수 있다.",
                )
            )
            continue

        name = names.get(planned.candidate_id)
        if not isinstance(name, str) or not name.strip():
            exclusions.append(
                _exclusion(
                    target,
                    FIXTURE_NAME_MISSING,
                    "픽스처 이름이 제공되지 않았다 — 이름을 지어내지 않고 제외한다.",
                )
            )
            continue

        lua_entry = LuaPatchEntry(
            console_type=resolution.console_type.name,
            console_mode=resolution.console_mode.name,
            fid=target.assigned_fid,
            name=name,
            universe=planned.universe,
            address=planned.address,
        )
        try:
            render_addfixtures_call(lua_entry)
        except LuaGenerationError:
            # 거부 사유에 **거부된 입력을 되싣지 않는다** — 그 이름이 목적지 토큰을 담고 있으면
            # 사유 문구가 산출물 스캐너에 거짓 양성을 내 AC-AUTOPATCH-014①이 강제력을 잃는다.
            exclusions.append(
                _exclusion(
                    target,
                    LUA_GENERATION_REFUSED,
                    "Lua 생성기가 이 항목의 이름을 거부했다 — 조용히 고치지 않고 제외한다. "
                    "이름을 고쳐 다시 요청하라.",
                )
            )
            continue

        lua_entries.append(lua_entry)
        entries.append(
            HandoffEntry(
                candidate_id=planned.candidate_id,
                fid=target.assigned_fid,
                name=name,
                console_type=resolution.console_type.name,
                console_mode=resolution.console_mode.name,
                universe=planned.universe,
                address=planned.address,
                footprint=planned.footprint,
            )
        )

    lua_source = render_addfixtures_plugin(lua_entries) if lua_entries else None

    return PatchHandoff(
        dry_run=dry_run,
        delivered=delivered,
        status=HANDOFF_STATUS_DELIVERED if delivered else HANDOFF_STATUS_DRY_RUN,
        next_step=NEXT_STEP_HUMAN_EXECUTION if delivered else NEXT_STEP_REVIEW,
        lua_source=lua_source,
        entries=tuple(entries),
        exclusions=tuple(exclusions),
        procedure=HUMAN_EXECUTION_PROCEDURE if delivered else (),
    )


def _exclusion(target: PatchCandidate, code: str, reason: str) -> PatchTargetExclusion:
    return PatchTargetExclusion(
        candidate_id=target.id,
        code=code,
        reason=reason,
        proposed_fid=target.assigned_fid,
    )

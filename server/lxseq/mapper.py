"""LX-SEQ 패치 레코드 → 패치 런 계획 (SPEC-COPILOT-LXSEQ-001 M2).

콘솔 접촉은 **읽기 결과를 주입받는 것**뿐이다. 이 모듈은 포트를 직접 열지
않고, 쓰기 수단은 이름조차 다루지 않는다(REQ-LXSEQ-009 — AST 스캔으로 확인).

REQ-LXSEQ-004: 타입은 `resolve_fixture_type` 계약으로만 확정한다.
REQ-LXSEQ-005: 모드는 실측 폭이 유일할 때만 채운다 — CSV `Mode` 문자열은 못 믿는다.
REQ-LXSEQ-006: 런을 만들기 전에 행 단위로 점유를 판정한다.
REQ-LXSEQ-007: 읽기가 전수가 아니면 런 0 — 빈 자리라고 말할 수 없으면 쓰지 않는다.
REQ-LXSEQ-008: 남은 행을 최대 연속 구간으로 묶어 순서 있는 계획을 낸다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any

from server.lxseq.parser import LxseqPatchRecord
from server.prechk.inventory import Inventory
from server.prechk.mode_read import TypeModeRead, parse_console_mode_slot
from server.prechk.patch import normalize_address
from server.vwx.addressfit import Occupant, evaluate
from server.vwx.apply import console_read_caveat
from server.vwx.patchplan import ExistingFidRead
from server.vwx.verdicts import CONSOLE_READ_INCOMPLETE

# `resolve_fixture_type` 계약의 status 어휘. `present`만 런에 들어간다.
_STATUS_PRESENT = "present"

_TYPE_SKIP_DETAIL = {
    "ambiguous": "콘솔 라이브러리에 후보가 여럿이다 — 후보: {candidates}",
    "absent": "콘솔 라이브러리에 없다 — 콘솔에서 타입 추가 후 재실행하라.",
    "library_unreadable": (
        "라이브러리를 읽지 못했다 — 없다고 단정하지 않는다. 콘솔 연결을 확인하라."
    ),
}


@dataclass(frozen=True)
class ModeResolution:
    console_type: str
    channels: int
    resolution: str  # resolved | unresolved | tree_unread
    console_mode: str | None = None
    #: width_unique | label_token | override | console_mode
    resolved_by: str | None = None
    measured_modes: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        """폭 없는 판정은 애초에 만들지 못하게 한다.

        `ModeChoice.width` 는 `int | None` 이고, 콘솔이 `TotalFootprint` 를 답하지
        못하면 실제로 `None` 이 온다. 그 `None` 이 여기까지 실려 오면 두 갈래로
        새는데 **둘 다 조용하다**: 하나는 한참 아래 산술에서 TypeError 로 죽고,
        다른 하나는 `channels_per_fixture=None` 인 런을 `footprint_source=
        console_measured` 로 내보낸다 — 재지 못한 폭을 「콘솔 실측」이라 적는 것이다.
        크래시만 막으면 후자만 남는다. 그래서 입구에서 막는다(t15 HIGH-2).
        """
        if not isinstance(self.channels, int) or isinstance(self.channels, bool):
            raise ValueError(
                f"채널 폭이 정수가 아니다({self.channels!r}) — "
                f"{self.console_type}: 폭을 재지 못했으면 확정이 아니다"
            )


@dataclass(frozen=True)
class SkippedRow:
    fid: int
    address: str
    kind: str
    detail: str
    occupant: dict[str, Any] | None = None
    occupied_fid: int | None = None
    #: 이 행의 모드를 무엇이 확정했는가 — `ModeResolution.resolved_by` 와 같은 어휘.
    #: 모드가 확정되기 **전에** 걸러진 행(`type_unresolved` · `mode_unresolved`)에는
    #: 보고할 해석이 없어 `None` 이다. 빈 문자열이나 `"unknown"` 으로 채우면
    #: 「풀렸는데 이름을 잃었다」와 구별되지 않고, 두 상태는 감독이 취할 다음
    #: 행동이 다르다 — 하나는 `mode_overrides` 를 주는 것이고 다른 하나는 버그다.
    resolved_by: str | None = None


@dataclass(frozen=True)
class PatchRun:
    index: int
    group: str
    console_type: str
    address: str
    count: int
    channels_per_fixture: int
    fids: tuple[int, ...]
    name_prefix: str
    footprint_source: str
    console_mode: str | None = None
    #: 이 런의 모드를 무엇이 확정했는가. `console_mode` 가 **무엇으로** 정해졌는지를
    #: 말하므로 둘은 중복이 아니다 — 같은 모드 이름이 폭 유일성으로도, 감독의
    #: override 로도, 그 자리 임자의 판독으로도 나올 수 있다.
    resolved_by: str | None = None

    @property
    def width_confirmed(self) -> bool:
        """폭을 쓰기 경로에 넘길 수 있는가.

        `as_tool_arguments` 가 폭을 넘기는 조건과 **같은 술어**다. 계수를 이
        술어로 세지 않고 따로 판별하면, 미리보기가 세는 수와 실제로 나가는
        인자가 갈린다 — 그 갈림이 바로 이 카드가 고치는 결함이다.
        """
        return self.footprint_source == "console_measured"

    def as_tool_arguments(self) -> dict[str, Any]:
        """`patch_fixtures` 호출 인자 그대로 — 스키마 밖 키를 만들지 않는다."""
        args: dict[str, Any] = {
            "console_type": self.console_type,
            "address": self.address,
            "count": self.count,
            "fids": list(self.fids),
            "name_prefix": self.name_prefix,
        }
        # 폭을 빼고 넘기면 `patch_fixtures` 는 스스로 재려 하고, 못 재면
        # `footprint_unknown` 으로 0대를 만든 뒤 그 런에서 파일 전체가 멈춘다 —
        # 미리보기는 N대를 약속한 뒤였다(t15 MED-3).
        #
        # 다만 **콘솔이 확인해 준 폭일 때만** 넘긴다. `tree_unread` 의 폭은 CSV 가
        # 주장하는 값이지 콘솔이 재 준 값이 아니고, `patch_fixtures` 의
        # `footprint_unknown` 은 바로 그런 값으로 쓰지 말라고 있는 문이다. 무턱대고
        # 넘기면 「거절」이 「배포」로 바뀐다 — 실측: 인자 없이는 commands_sent=0,
        # 인자를 넣으면 deploy_status='deployed' 로 2건이 나갔다. 검사를 넓혀
        # 하류 가드를 고아로 만드는 것은 이 커밋이 고치는 결함 계열 그 자체다.
        if self.width_confirmed:
            args["channels_per_fixture"] = self.channels_per_fixture
        if self.console_mode is not None:
            args["console_mode"] = self.console_mode
        return args


@dataclass(frozen=True)
class ImportPlan:
    runs: tuple[PatchRun, ...]
    fid_map: dict[int, dict[str, Any]]
    skipped: tuple[SkippedRow, ...]
    write_count_planned: int
    types_requested: tuple[str, ...]
    # 키는 (CSV 타입, 채널수, CSV 모드라벨) — 타입 단독이 아니다. 한 타입이 두 폭으로
    # 오는 입력이 있고, 그때 해석은 폭마다 갈려야 한다.
    mode_resolutions: dict[tuple[str, int, str], ModeResolution]
    console_read: dict[str, Any]
    blind_spot: str = ""
    name_prefix_mode: str = "group"

    # 계수는 하나로 뭉치지 않는다. 폭이 `tree_unread` 인 런은 `as_tool_arguments`
    # 가 폭을 빼고 넘기고, `patch_fixtures` 가 `footprint_unknown` 으로 거절하며,
    # 그 런에서 파일 전체가 멈춘다. 거절은 의도된 안전장치다 — 고칠 것은 거절이
    # 아니라 **미리보기가 그 사실을 고지하지 않는 것**이다. N대를 약속하고
    # 0대를 만든다.
    #
    # 두 수는 `runs` 에서 **계산**한다. 따로 들고 다니면 런 목록과 갈린다.

    @property
    def write_count_applicable(self) -> int:
        """폭이 확인돼 실제로 나갈 수 있는 대수."""
        return sum(run.count for run in self.runs if run.width_confirmed)

    @property
    def write_count_width_unconfirmed(self) -> int:
        """폭 미확정이라 거절될 대수. 0이 아니면 미리보기가 그대로 말해야 한다."""
        return sum(run.count for run in self.runs if not run.width_confirmed)

    @property
    def resolved_by_counts(self) -> dict[str | None, int]:
        """무엇이 모드를 확정했는지의 행 단위 집계. `None` 은 「못 풀었다」.

        **런과 건너뛴 행을 함께 센다.** 한 행은 런으로도 건너뛴 행으로도 끝나므로
        한쪽만 세면 합이 행 수에 못 미치고, 그 결손은 「0건이었다」로 읽힌다. 런은
        여러 대를 묶은 단위라 `count` 로 센다 — 런 개수로 세면 묶인 대수가 사라진다.

        `mode_resolutions` 표로 이 집계를 대신할 수 없다. 그 표는 (타입, 폭, 라벨)
        키마다 하나이고 해석은 **행 단위**라, 같은 키의 행들이 갈리면 표에는 먼저
        도달한 해석만 남는다 — 일부만 풀린 키가 전부 풀린 것으로 보인다.
        """
        counts: dict[str | None, int] = {}
        for run in self.runs:
            counts[run.resolved_by] = counts.get(run.resolved_by, 0) + run.count
        for row in self.skipped:
            counts[row.resolved_by] = counts.get(row.resolved_by, 0) + 1
        return counts


def _address_text(record: LxseqPatchRecord) -> str:
    return f"{record.universe}.{record.address}"


def _console_mode_slots_by_seat(
    inventory: Inventory | None,
) -> dict[tuple[int, int, str], frozenset[int]]:
    """자리+타입마다, 그 자리에 앉아 있는 픽스처들이 답한 DMXModes 슬롯 집합.

    키에 타입이 들어가는 이유: 어떤 모드인지는 **어떤 타입인지가 정해진 뒤에만**
    의미가 있다. 자리만으로 이으면 다른 타입이 그 자리를 쓰던 경우에 그 타입의
    슬롯 번호를 이 행의 모드로 읽는다 — 번호는 어느 타입에서나 유효해 보이므로
    그 오답은 조용하다.

    값이 집합인 이유: 한 자리에 여러 대가 보고될 수 있고, 그때 **앞것을 집으면 안
    된다.** 그것이 t334(이름이 겹치는 타입 조회가 경고 없이 앞것을 채택한다)와
    같은 형태의 조용한 오답을 이 갈래에 새로 만드는 길이다. 부르는 쪽은 집합의
    크기가 1일 때만 채택한다.

    주소를 못 읽은 픽스처는 **버린다** — 0이나 1로 채우면 그 가짜 자리가 대조에
    들어간다(`occupants_from_patch_values` 의 같은 이유).
    """
    seats: dict[tuple[int, int, str], set[int]] = {}
    for fixture in inventory.fixtures if inventory is not None else ():
        fixture_type = fixture.fixture_type
        if not fixture_type:
            continue
        slot = parse_console_mode_slot(fixture.mode)
        if slot is None:
            continue
        parsed = normalize_address(fixture.patch_raw)
        if not parsed.ok or parsed.universe is None or parsed.address is None:
            continue
        seats.setdefault((parsed.universe, parsed.address, fixture_type), set()).add(slot)
    return {key: frozenset(slots) for key, slots in seats.items()}


def _resolve_mode_from_console_seat(
    record: LxseqPatchRecord,
    console_type: str,
    mode_read: TypeModeRead | None,
    seats: dict[tuple[int, int, str], frozenset[int]],
) -> ModeResolution | None:
    """그 자리에 이미 앉아 있는 픽스처의 모드로 해석을 확정한다. 못 하면 `None`.

    라이브러리 판독은 폭이 같은 모드가 여럿일 때 원리적으로 못 좁힌다(t128:
    「폭은 판별기가 아니다」 — 폭 25 가 Aura XB 의 Extended 3종을 남긴다). 그런데
    **이미 그 자리에 꽂혀 있는 픽스처는 자기 모드를 답한다.** 벽은 원리적 한계가
    아니라 판독 지점의 문제였다 — 실측 2026-09-08, 타입 8종·86대에서 픽스처
    `Mode` 의 앞 숫자가 라이브러리 슬롯과 8/8 일치
    (`.moai/reports/t333/preconditions.md` §2.3).

    **이름을 비교하지 않는다.** 슬롯으로 집으므로 t334(같은 이름 타입 둘 중 앞것이
    조용히 이긴다)를 원리적으로 우회한다.

    **켜지는 범위는 「이미 패치됨」 국면 하나다.** 조건이 자리+타입 일치이고 그것은
    `_occupancy_skip` 의 `already_patched` 술어와 같으므로, 아직 없는 픽스처를 새로
    패치하는 국면에서는 읽을 모드가 없어 이 갈래가 아예 안 켜진다 — 그쪽은
    라이브러리 판독이 여전히 유일한 경로다.

    `None` 을 돌려주면 부르는 쪽은 수정 전 동작(`mode_unresolved` +
    `mode_overrides` 안내)을 그대로 낸다. 이 함수는 능력만 더하고 무엇도 대체하지
    않는다.
    """
    if mode_read is None:
        return None
    slots = seats.get((record.universe, record.address, console_type))
    # 한 자리에서 두 모드가 보고되면 어느 쪽도 증거가 아니다.
    if not slots or len(slots) != 1:
        return None
    (slot,) = slots
    matched = next((choice for choice in mode_read.modes if choice.slot == slot), None)
    # 슬롯을 라이브러리 목록에서 못 찾았거나 폭을 못 쟀으면 확정이 아니다 —
    # override 갈래와 같은 규율이다(t15 HIGH-2). 폭을 잃은 채 확정하면 점유
    # 검사가 검사한 발자국과 실제로 쓰는 발자국이 갈린다.
    if matched is None or matched.width is None:
        return None
    return ModeResolution(
        console_type=console_type,
        channels=matched.width,
        resolution="resolved",
        console_mode=matched.name,
        resolved_by="console_mode",
        measured_modes=tuple(
            {"name": choice.name, "channels": choice.width} for choice in mode_read.modes
        ),
    )


def _effective_width(record: LxseqPatchRecord, mode) -> int:
    """콘솔이 실제로 밟을 폭.

    CSV 의 `Ch` 가 아니다 — 모드가 확정되면 자리를 정하는 것은 실측 폭이다. 점유
    검사 · 런 경계 · 런 폭이 **모두 이 한 식**을 써야 한다. 하나라도 CSV 폭을 쓰면
    「검사한 자리」와 「실제로 쓰는 자리」가 갈라진다(PR #72 D4 ③).
    """
    return mode.channels if mode.resolution != "tree_unread" else record.channels


def _reject_plan_overlaps(placeable):
    """계획 안에서 서로 겹치는 행을 실측 폭 기준으로 걸러낸다.

    파서의 `address_overlap_in_file` 은 **CSV 폭**으로 도는 검사라, 모드 확정으로
    발자국이 넓어져 생긴 겹침은 그 시야 밖이다. 점유 검사도 못 본다 — 그쪽은 콘솔의
    기존 점유만 본다. 그래서 계획이 자기 자신과 겹쳐도 조용히 통과했다.

    파서의 R2 와 같은 정책을 쓴다: 관여한 행을 **전부** 거부한다. 어느 쪽이 옳은
    자리인지 도구가 정할 수 없기 때문이다.
    """
    spans = []
    for record, _console_type, mode in placeable:
        width = _effective_width(record, mode)
        spans.append((record.universe, record.address, record.address + width - 1, width))

    involved: set[int] = set()
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            u1, s1, e1, _ = spans[i]
            u2, s2, e2, _ = spans[j]
            if u1 == u2 and s1 <= e2 and s2 <= e1:
                involved.add(i)
                involved.add(j)

    kept = [item for index, item in enumerate(placeable) if index not in involved]
    rejected = [
        SkippedRow(
            fid=placeable[index][0].fid,
            address=_address_text(placeable[index][0]),
            kind="address_overlap_in_plan",
            detail=(
                f"확정된 모드의 폭 {spans[index][3]}채널로는 계획 안의 다른 행과 "
                f"{spans[index][0]}.{spans[index][1]}–{spans[index][2]} 구간이 겹친다. "
                "CSV 폭으로는 겹치지 않았다 — 관여한 행을 전부 거부한다."
            ),
            # 이 행은 모드가 **확정된 뒤에** 거부된다 — 겹침을 만든 것이 확정된 폭
            # 이므로, 무엇이 그 폭을 정했는지가 이 거부의 원인 사슬에 들어 있다.
            resolved_by=placeable[index][2].resolved_by,
        )
        for index in sorted(involved)
    ]
    return kept, rejected


def _distinct_types(records: tuple[LxseqPatchRecord, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for record in records:
        if record.fixture_type not in seen:
            seen.append(record.fixture_type)
    return tuple(seen)


def _judge_console_read(
    inventory: Inventory | None, existing_fids: ExistingFidRead
) -> tuple[bool, str]:
    """전수 판독인가. 아니면 왜 아닌가.

    **절단은 미판독이 아니다.** 판정은 `completeness` 라벨이 아니라
    `console_read_caveat`의 caveat 종류로 내린다 — 그것이 이 저장소의 정본 규약이고,
    형제 호출부 둘(`orchestrator/tools.py`의 `patch_fixtures`, `vwx/apply.py`)이 이미
    같은 잣대를 쓴다. 그 함수의 독스트링이 두 상태를 갈라 놓았다:

    * `missing_count > 0` (또는 주소 미판독) — 이 상태의 «없음»은 관측이 아니라
      미판독이다. **막는다.**
    * `missing_count == 0` 인데 열거만 짧다(`index_domain_unknown`) — 선언된 자식을
      전부 관측했고 `childCount`가 진짜 총계라 **수량 비교는 정확하다.** 주의는
      남기되 막지 않는다.

    라벨만 보던 이전 판은 두 번째 갈래까지 막았다. 실물 콘솔의 열거는 픽스처
    19대에서 절단되므로, 그 판정으로는 리그가 그 선을 넘는 순간 이 매퍼가 **어떤
    계획도 세우지 못한다**(2026-08-21 M4 실기: 86대 패치 후 재실행이 86행 전부
    `console_read_incomplete`). 안전한 방향이었으나 툴이 무력해졌다.
    """
    if inventory is None:
        return False, "인벤토리를 읽지 않았다"

    # 타입 이름을 못 얻었으면 「이미 패치됨」 비교 자체가 성립하지 않는다.
    # 그대로 계획하면 이미 있는 행이 `fid_occupied` 로 나가고 그 라벨이 지시하는
    # 다음 행동은 «다른 FID 로 다시 패치하라» — 같은 리그를 한 벌 더 만든다.
    # 이 앱에 실행 취소는 없다. 판독 실패를 「자리가 비었다」로 읽지 않는다.
    #
    # 좁게 건다: 콘솔이 이름을 돌려주는 경로에서는 미번역이 0건이라 이 갈래가
    # 아예 안 탄다 — 핸들이 왔는데 이름을 못 얻은 경우에만 막힌다.
    untranslated = [fixture for fixture in inventory.fixtures if fixture.fixture_type_untranslated]
    if untranslated:
        reasons = sorted({str(f.fixture_type_untranslated) for f in untranslated})
        return False, (
            f"타입 이름을 얻지 못한 장비 {len(untranslated)}대"
            f"({' · '.join(reasons)}) — 「이미 패치됨」 비교가 성립하지 않아"
            " 점유를 판정할 수 없다"
        )

    caveat = console_read_caveat(inventory)
    if caveat is not None and caveat["kind"] == CONSOLE_READ_INCOMPLETE:
        return False, str(caveat["reason"])
    if not existing_fids.attempted:
        return False, "기존 FID를 조회하지 않았다"
    if existing_fids.root_unreadable:
        return False, "FID 루트를 읽지 못했다"
    unresolved = (
        (existing_fids.unseen or 0)
        + existing_fids.unreadable_fids
        + existing_fids.unusable_rows
        + existing_fids.unparsable_rows
    )
    if unresolved > 0:
        return False, f"FID 판독 미해결 {unresolved}건"
    return True, ""


def _resolve_mode(
    console_type: str,
    csv_type: str,
    channels: int,
    mode_read: TypeModeRead | None,
    override: str | None,
) -> ModeResolution:
    """모드 이름은 콘솔이 안다 — CSV `Mode` 문자열에서 추측하지 않는다."""
    measured = tuple(
        {"name": choice.name, "channels": choice.width}
        for choice in (mode_read.modes if mode_read else ())
    )

    # 모드 트리를 못 읽었으면 폭은 호출자 값을 쓰되 미검증임을 표시한다.
    if mode_read is None or not mode_read.attempted or not mode_read.type_found:
        return ModeResolution(
            console_type=console_type,
            channels=channels,
            resolution="tree_unread",
            console_mode=override,
            resolved_by="override" if override else None,
            measured_modes=measured,
        )

    if override is not None:
        # 이름만 찾으면 폭을 잃는다. override 는 「CSV 폭과 같은 실측 모드가 없다」일 때
        # 쓰는 해법이라 폭이 다른 것이 정상이고, 그때 자리를 정하는 것은 실측 폭이다.
        matched = next(
            (c for c in mode_read.modes if c.name.lower() == override.lower()),
            None,
        )
        # 이름은 찾았는데 폭을 못 쟀으면 확정이 아니다 — override 없는 갈래는
        # `c.width == channels` 가 None 과 안 맞아 **우연히** 여기서 빠져나갔다.
        # 이쪽만 그 우연을 못 받아 크래시했다(t15 HIGH-2).
        if matched is not None and matched.width is not None:
            return ModeResolution(
                console_type=console_type,
                channels=matched.width,
                resolution="resolved",
                console_mode=matched.name,
                resolved_by="override",
                measured_modes=measured,
            )
        return ModeResolution(
            console_type=console_type,
            channels=channels,
            resolution="unresolved",
            measured_modes=measured,
        )

    same_width = [c for c in mode_read.modes if c.width == channels]
    if len(same_width) == 1:
        return ModeResolution(
            console_type=console_type,
            channels=channels,
            resolution="resolved",
            console_mode=same_width[0].name,
            resolved_by="width_unique",
            measured_modes=measured,
        )

    # 폭이 같은 모드가 여럿이면 CSV `Mode` 라벨의 토큰이 딱 하나에만 걸릴 때만 채택.
    if len(same_width) > 1:
        matched = _match_by_label_token(csv_type, same_width)
        if matched is not None:
            return ModeResolution(
                console_type=console_type,
                channels=channels,
                resolution="resolved",
                console_mode=matched,
                resolved_by="label_token",
                measured_modes=measured,
            )

    return ModeResolution(
        console_type=console_type,
        channels=channels,
        resolution="unresolved",
        measured_modes=measured,
    )


def _match_by_label_token(mode_label: str, candidates: list) -> str | None:
    tokens = [t for t in re.split(r"[^0-9A-Za-z가-힣]+", mode_label) if t]
    hits = [
        choice.name
        for choice in candidates
        if any(token.lower() in choice.name.lower() for token in tokens)
    ]
    return hits[0] if len(hits) == 1 else None


def _occupancy_skip(
    record: LxseqPatchRecord,
    console_type: str,
    channels: int,
    occupants: tuple[Occupant, ...],
    existing_fid_set: frozenset[int],
) -> SkippedRow | None:
    """자리·FID 점유를 행 단위로 판정한다. 덮어쓰는 경로는 존재하지 않는다.

    **자리를 먼저 본다.** 이미 패치된 행은 자리 충돌과 FID 점유가 **동시에** 참인데,
    FID 를 먼저 보면 `fid_occupied`("그 번호는 쓰인다")로 나가고 그 라벨이 지시하는
    다음 행동은 «다른 FID 로 다시 패치하라»다 — 같은 리그를 한 벌 더 만든다. 이 앱에는
    실행 취소가 없다. 두 조건이 겹칠 때 정직한 답은 `already_patched`(할 일 없음)다.
    """
    address = _address_text(record)

    # 구간 **안에서 시작하는** 장비만 확정 충돌이다(addressfit 규약 그대로).
    fit = evaluate(address, count=1, width=channels, occupants=occupants)
    first = fit.collisions[0] if fit.collisions else None
    occupant = (
        {
            "address": f"{first.universe}.{first.address}",
            "name": first.name,
            "fixture_type": first.fixture_type,
        }
        if first is not None
        else None
    )

    if (
        first is not None
        and (first.fixture_type or "") == console_type
        and first.universe == record.universe
        and first.address == record.address
    ):
        return SkippedRow(
            fid=record.fid,
            address=address,
            kind="already_patched",
            detail="같은 타입이 같은 자리에 이미 있다 — 이미 패치됨",
            occupant=occupant,
        )

    if record.fid in existing_fid_set:
        return SkippedRow(
            fid=record.fid,
            address=address,
            kind="fid_occupied",
            detail=f"FID {record.fid}는 콘솔에 이미 있다",
            occupant=occupant,
            occupied_fid=record.fid,
        )

    # 판정이 서지 않았으면 「자리가 비었다」가 아니다. 이 함수는 `collisions` 만 보고
    # 있었는데, `evaluate` 는 요청 자체가 성립하지 않을 때 충돌을 **계산하기도 전에**
    # 사유만 담아 돌아온다 — 그때 `collisions` 가 비는 것은 자리가 비어서가 아니다.
    # 실측 폭이 유니버스 끝을 넘는 행이 바로 그 경우이고(t15 HIGH-1), 폭이 음수인
    # 행도 같은 문에 닿는다(t15 LOW-5). 둘 다 조용히 계획에 실렸다.
    #
    # 라벨은 `universe_overflow` 를 **재사용한다**. 파서가 CSV 폭으로 내는 것과 같은
    # 사실을, 모드가 확정된 뒤 실측 폭으로 다시 발견한 것뿐이다. 새 라벨을 만들면
    # REQ-LXSEQ-011 의 닫힌 어휘 8종을 깬다 — 툴 계층 단언(`_SKIP_KINDS`)은 `<=`
    # 라 당장은 조용히 통과하지만, 실제 페이로드가 그 값을 내는 순간 빨개진다.
    if not fit.ok and not fit.collisions:
        return SkippedRow(
            fid=record.fid,
            address=address,
            kind="universe_overflow",
            detail=fit.error or "그 자리에 놓을 수 있는지 판정하지 못했다",
            occupant=occupant,
        )

    if first is not None:
        return SkippedRow(
            fid=record.fid,
            address=address,
            kind="address_occupied",
            detail="그 자리를 다른 장비가 쓰고 있다",
            occupant=occupant,
        )
    return None


def build_import_plan(
    *,
    records: tuple[LxseqPatchRecord, ...],
    type_resolutions: dict[str, dict[str, Any]],
    mode_reads: dict[str, TypeModeRead],
    inventory: Inventory | None,
    occupants: tuple[Occupant, ...] = (),
    existing_fids: ExistingFidRead | None = None,
    mode_overrides: dict[str, str] | None = None,
    name_prefix_mode: str = "group",
) -> ImportPlan:
    """레코드를 패치 런 계획으로 바꾼다."""
    records = tuple(records)
    existing_fids = existing_fids or ExistingFidRead()
    mode_overrides = mode_overrides or {}
    types_requested = _distinct_types(records)

    read_complete, reason = _judge_console_read(inventory, existing_fids)
    console_read = {
        "complete_enough_to_judge_absence": read_complete,
        "reason": reason,
    }

    # 읽기가 전수가 아니면 계획을 세우지 않는다 — 빈 자리라고 말할 수 없다.
    if not read_complete:
        return ImportPlan(
            runs=(),
            fid_map={},
            skipped=tuple(
                SkippedRow(
                    fid=record.fid,
                    address=_address_text(record),
                    kind="console_read_incomplete",
                    detail=reason,
                )
                for record in records
            ),
            write_count_planned=0,
            types_requested=types_requested,
            mode_resolutions={},
            console_read=console_read,
            name_prefix_mode=name_prefix_mode,
        )

    skipped: list[SkippedRow] = []
    mode_resolutions: dict[tuple[str, int, str], ModeResolution] = {}
    existing_fid_set = frozenset(existing_fids.fids)
    # 한 번 만들어 행마다 조회한다. 이 함수에 도달했다는 것은 위의
    # `_judge_console_read` 를 통과했다는 뜻이므로, 여기 실린 목록은 부분 목록이
    # 아니다 — 미완전 판독은 이 지점 앞에서 계획 없이 끊긴다.
    console_mode_seats = _console_mode_slots_by_seat(inventory)

    # 타입 해석은 **서로 다른 타입마다 한 번씩** — 행 수만큼 부르지 않는다.
    console_types: dict[str, str | None] = {}
    for csv_type in types_requested:
        resolution = type_resolutions.get(csv_type) or {
            "status": "library_unreadable",
            "candidates": [],
        }
        status = resolution.get("status")
        if status == _STATUS_PRESENT:
            console_types[csv_type] = resolution.get("resolved") or csv_type
        else:
            console_types[csv_type] = None

    placeable: list[tuple[LxseqPatchRecord, str, ModeResolution]] = []
    for record in records:
        csv_type = record.fixture_type
        console_type = console_types.get(csv_type)
        if console_type is None:
            resolution = type_resolutions.get(csv_type) or {
                "status": "library_unreadable",
                "candidates": [],
            }
            status = str(resolution.get("status", "library_unreadable"))
            template = _TYPE_SKIP_DETAIL.get(status, _TYPE_SKIP_DETAIL["library_unreadable"])
            candidates = ", ".join(resolution.get("candidates") or [])
            skipped.append(
                SkippedRow(
                    fid=record.fid,
                    address=_address_text(record),
                    kind="type_unresolved",
                    detail=template.format(candidates=candidates),
                )
            )
            continue

        # 한 타입이 두 폭으로 오면 해석도 둘이어야 한다. 키가 타입 단독이면 첫 행의
        # 해석이 같은 타입 전체에 재사용돼, 폭이 다른 뒤 행들이 조용히 밀린다.
        resolution_key = (csv_type, record.channels, record.mode_label)
        if resolution_key not in mode_resolutions:
            mode_resolutions[resolution_key] = _resolve_mode(
                console_type=console_type,
                csv_type=record.mode_label,
                channels=record.channels,
                mode_read=mode_reads.get(csv_type) or mode_reads.get(console_type),
                override=mode_overrides.get(csv_type) or mode_overrides.get(console_type),
            )
        mode = mode_resolutions[resolution_key]

        # 라이브러리 판독으로 못 좁힌 행만 그 자리의 임자에게 물어본다. 이 갈래는
        # **행 단위**로 판정하되 해석표에는 캐시하지 않는다 — 같은 (타입, 폭, 라벨)
        # 키의 행들이 서로 다른 자리에 앉아 있고, 자리마다 임자가 있을 수도 없을
        # 수도 있다. 한 행의 성공을 키 전체에 퍼뜨리면 임자가 없는 행까지 그 모드로
        # 확정된다.
        #
        # `tree_unread` 는 건드리지 않는다. 그때는 라이브러리 목록 자체가 없어
        # 슬롯을 조회할 대상이 없다.
        if mode.resolution == "unresolved":
            from_seat = _resolve_mode_from_console_seat(
                record=record,
                console_type=console_type,
                mode_read=mode_reads.get(csv_type) or mode_reads.get(console_type),
                seats=console_mode_seats,
            )
            if from_seat is not None:
                mode = from_seat
                # 🔴 해석표에 **쓰지 않는다.** t333 은 여기서 `from_seat` 를 키에
                # 써 넣었고, 그것이 바로 위 캐시 주석이 금지한 일이었다: 같은 키의
                # 다음 행이 그 값을 물려받아, **자기 자리에 임자가 없는데도** 그
                # 모드로 확정되고 그대로 쓰기 계획이 된다. 이 앱에 실행 취소는
                # 없으므로 그 확정은 되돌릴 수 없는 쓰기로 이어진다.
                #
                # 그 결함이 t333 회차에 안 드러난 이유: 그 쇼의 24행이 전부 자리에
                # 임자가 있어 물려받은 값과 실측값이 우연히 같았다. 임자가 일부에만
                # 있는 쇼에서 갈린다.
                #
                # 표는 **라이브러리 판독의 결과**로 남긴다. 행마다 다른 해석은
                # 행에 실린다(`SkippedRow.resolved_by` · `PatchRun.resolved_by`) —
                # 키 하나에 값 하나인 표는 애초에 그 갈림을 담을 수 없다.

        if mode.resolution == "unresolved":
            measured = ", ".join(f"{m['name']}({m['channels']})" for m in mode.measured_modes)
            hint = (
                "실측 목록에 없음. "
                if mode_overrides.get(csv_type) or mode_overrides.get(console_type)
                else ""
            )
            skipped.append(
                SkippedRow(
                    fid=record.fid,
                    address=_address_text(record),
                    kind="mode_unresolved",
                    detail=(
                        f"{hint}모드를 확정하지 못했다 — 실측 모드: [{measured}]. "
                        f'mode_overrides: {{"{csv_type}": "<콘솔 모드 이름>"}} 로 재호출하라.'
                    ),
                )
            )
            continue

        # 점유 검사도 콘솔이 실제로 밟을 폭으로 돌아야 한다. CSV 폭으로 돌면 검사한
        # 발자국과 실제로 쓰는 발자국이 달라진다(PR #72 D4 ③).
        occupied = _occupancy_skip(
            record,
            console_type,
            _effective_width(record, mode),
            occupants,
            existing_fid_set,
        )
        if occupied is not None:
            # 해석은 여기서 얹는다 — `_occupancy_skip` 은 자리만 보는 함수이고,
            # 거기에 모드를 넘기면 자리 판정이 모드에 의존하는 것처럼 읽힌다.
            skipped.append(replace(occupied, resolved_by=mode.resolved_by))
            continue

        placeable.append((record, console_type, mode))

    placeable, plan_overlaps = _reject_plan_overlaps(placeable)
    skipped.extend(plan_overlaps)

    runs = _group_into_runs(placeable, name_prefix_mode=name_prefix_mode)
    fid_map = {
        fid: {
            "address": run.address
            if index == 0
            else f"{run.address.split('.')[0]}."
            f"{int(run.address.split('.')[1]) + index * run.channels_per_fixture}",
            "console_type": run.console_type,
            "run_index": run.index,
        }
        for run in runs
        for index, fid in enumerate(run.fids)
    }
    for row in skipped:
        fid_map.setdefault(
            row.fid, {"address": row.address, "console_type": None, "run_index": None}
        )

    return ImportPlan(
        runs=runs,
        fid_map=fid_map,
        skipped=tuple(skipped),
        write_count_planned=sum(run.count for run in runs),
        types_requested=types_requested,
        mode_resolutions=mode_resolutions,
        console_read=console_read,
        blind_spot=evaluate("1.1", count=1, width=1, occupants=()).blind_spot,
        name_prefix_mode=name_prefix_mode,
    )


def _group_into_runs(
    placeable: list[tuple[LxseqPatchRecord, str, ModeResolution]],
    *,
    name_prefix_mode: str,
) -> tuple[PatchRun, ...]:
    """최대 연속 구간으로 묶는다 — 건너뛴 행이 끼면 런이 갈라진다."""
    runs: list[PatchRun] = []
    current: list[tuple[LxseqPatchRecord, str, ModeResolution]] = []

    def boundary_key(item) -> tuple:
        record, console_type, mode = item
        # 폭이 빠지면 폭이 다른 행이 한 런으로 뭉치고, 런 폭은 머리 행 값이 된다.
        #
        # `resolved_by` 가 같은 이유로 들어간다. 이것이 빠지면 해석이 다른 행이 한
        # 런으로 뭉치고 런의 `resolved_by` 는 머리 행 값이 된다 — 보고가 거짓이 된다.
        # 도달 가능한 조합이다: 같은 타입에서 CSV `Mode` 라벨이 달라 한 키는 라벨
        # 토큰으로 풀리고 다른 키는 모호해 그 자리 임자로 풀렸는데, 두 키가 같은
        # 콘솔 모드·같은 폭에 닿으면 나머지 키 성분이 전부 같아진다.
        key = (
            console_type,
            mode.resolution,
            mode.console_mode,
            mode.resolved_by,
            _effective_width(record, mode),
            record.universe,
        )
        if name_prefix_mode == "group":
            key = (*key, record.group)
        return key

    def flush() -> None:
        if not current:
            return
        head_record, console_type, mode = current[0]
        width = _effective_width(head_record, mode)
        runs.append(
            PatchRun(
                index=len(runs),
                group=head_record.group,
                console_type=console_type,
                console_mode=mode.console_mode,
                address=_address_text(head_record),
                count=len(current),
                channels_per_fixture=width,
                fids=tuple(r.fid for r, _, _ in current),
                name_prefix=head_record.group if name_prefix_mode == "group" else console_type,
                footprint_source=(
                    "caller_unverified" if mode.resolution == "tree_unread" else "console_measured"
                ),
                resolved_by=mode.resolved_by,
            )
        )
        current.clear()

    for item in placeable:
        if not current:
            current.append(item)
            continue
        prev_record, _, prev_mode = current[-1]
        record, _, _ = item
        # 연속인지는 콘솔이 실제로 밟을 폭으로 따진다. CSV 폭으로 따지면 폭이 다를 때
        # 「CSV 상으로는 연속」인 행들이 한 런에 들어가고, 콘솔은 더 좁은 보폭으로 놓아
        # 뒤 행이 CSV 가 지정한 자리보다 앞으로 밀린다.
        contiguous = record.address == prev_record.address + _effective_width(
            prev_record, prev_mode
        )
        if boundary_key(item) == boundary_key(current[-1]) and contiguous:
            current.append(item)
        else:
            flush()
            current.append(item)
    flush()

    return tuple(runs)

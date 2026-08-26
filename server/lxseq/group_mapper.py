"""LX-SEQ v2.1 RIG 팩 GROUP 매퍼 (SPEC-COPILOT-LXSEQ-002 M2).

순수 함수다 — 콘솔·네트워크 입출력 0. 콘솔이 답한 값은 **주입받는다**.
그룹 레코드와 패치 라벨 표를 `create_arrangement_groups` 가 받는 인자
배치로 바꾼다. 쓰기 수단의 이름도 명령 문자열도 여기 없다.

REQ-LXSEQ2-004: 기본 12종의 멤버는 패치 라벨 표에서 온다.
REQ-LXSEQ2-005: 파생 6종은 아래 닫힌 규칙에서 온다. 데이터에서 유추하지 않는다.
REQ-LXSEQ2-006: 닫힌 어휘 밖 이름은 건너뛴다. 추측하지 않는다.
REQ-LXSEQ2-007: Members 의 개수는 교차검증에만 쓴다.
REQ-LXSEQ2-008: 콘솔에 없는 FID 는 안 넣는다. 실측이 전수 아니면 0배치.
REQ-LXSEQ2-009: 측정 슬롯이 시트 GroupNo 와 어긋나면 0배치 + 대조표.
REQ-LXSEQ2-010: 배치는 엔진 상한 이하로 나눈다. 기본 먼저, 파생 나중.
REQ-LXSEQ2-011: 명령 한 줄의 인코딩 바이트가 예산을 넘으면 그 그룹을 건너뛴다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.groupgen.write import DEFAULT_GROUP_PLAN_CAP
from server.lxseq.group_parser import LxseqGroupRecord
from server.rig.section import section_refusal
from server.spatial.choreography import build_compact_fixture_selection

__all__ = [
    "DEFAULT_LINE_BYTE_BUDGET",
    "DERIVED_GROUP_NAMES",
    "GroupBatch",
    "GroupBucket",
    "GroupMapResult",
    "GroupSkip",
    "SlotDivergence",
    "build_label_fid_table",
    "map_groups",
    "measure_command_bytes",
]

# 줄 단위 예산.
#
# @MX:ANCHOR: [AUTO] 단위가 「번들」이 아니라 「줄」인 이유.
# @MX:REASON: `run_commands` 가 `for command in commands:` 로 한 줄씩
#   발화한다(server/orchestrator/tools.py). 5줄을 합친 길이가 아니라 가장
#   긴 한 줄이 전송 상한에 걸린다. 그리고 전송층의 예산 검사기
#   `_validate_plugin_call_budget` 은 introspect 와 props 에만 걸려 있고
#   **exec 에는 안 걸려 있다**(server/bridge/protocol.py) — 실측: 5475바이트
#   명령이 build_exec_request 를 예외 없이 통과했고 같은 크기에서
#   build_introspect_query 는 ProtocolError 를 던졌다. 그러므로 이 게이트가
#   그룹 쓰기 경로의 유일한 방어선이다. 넘으면 조용히 버려지고, 멤버십은
#   되읽히지 않으므로 사후 적발 수단이 없다.
# 값의 유래 — **이 값은 실측이 아니다.** 프레이밍 상한에서 역산한 것이다.
# `server/bridge/protocol.py` 의 MAX_PLUGIN_CALL_BYTES = 2048 에서 exec
# 프레이밍(`Plugin "<이름>" "exec <요청id> ..."`) 실측 42바이트를 빼고 여유를
# 48로 잡아 2000 을 둔다. 2048 자체가 **프로토콜이 스스로 정한 상한**이지
# 콘솔이 받아 주는 실제 상한이 아니다.
#
# 실측으로 아는 것 (t66, 2026-08-25) — 방향·대상·단위를 반드시 함께 읽어라:
#   방향: 서버 -> 콘솔 (요청)      대상: 선택 줄 `Fixture a + Fixture b + …`
#   단위: UTF-8 바이트             결과: 86개 = 1201B 까지 **상한을 못 찾았다**
#   (이분 탐색이 n=1(11B)·n=86(1201B) 둘 다 `OK` 를 받아 경계가 안 나왔다.
#    상한이 없다는 증명이 아니라, 1201B 아래에서는 안 걸린다는 관측이다.)
#
# @MX:WARN: [AUTO] 이것을 회신 방향 경계 `[1200, 1208)` 와 **섞지 마라.**
# @MX:REASON: 그 값은 콘솔 -> 서버 스냅샷 payload 절단 경계이고
#   (`docs/runbooks/fake-real-parity-method.md` §3), 같은 문서 §4 가 스스로
#   "이 방법은 쓰기 경로를 못 닫는다"고 적어 놨다. t66 에서 실제로 그 수를
#   요청 방향에 갖다 붙인 오진이 나왔다 — 1201 이 1200 을 1바이트 넘긴 것은
#   두 방향의 수가 우연히 가까운 것이지 귀속이 아니다. 방향·대상·단위가 안
#   적혀 있으면 다음 사람도 같은 실수를 한다.
#
# 요청 방향 실측 상한이 생기면 고칠 자리는 **이 상수와 이 주석 둘뿐이다**
# (`measure_command_bytes` 는 프레이밍을 안 더하므로 손댈 필요 없다).
#
# @MX:ANCHOR: [AUTO] 이 상수와 프레이밍 여유는 전송층을 임포트하지 않고
#   선언된 값이다. `server/lxseq/` 는 `server.bridge` 를 임포트할 수 없다
#   (server/tests/test_lxseq_mapper.py 의 _FORBIDDEN_IMPORTS — 001이 세운
#   경계다).
# @MX:REASON: 그래서 이 값이 실제 상한·프레이밍과 맞는지는 **테스트가**
#   양쪽을 임포트해 잰다. 여기 적어 두기만 하면 드리프트하고, 그 드리프트는
#   조용하다 — 넘친 명령은 응답기가 에러 없이 버리고 멤버십은 되읽히지
#   않아 사후 적발 수단이 없다.
DEFAULT_LINE_BYTE_BUDGET = 2000

# 파생 6종의 닫힌 어휘. 이 여섯 밖은 만들지 않는다.
DERIVED_GROUP_NAMES: tuple[str, ...] = (
    "ALL",
    "SIDE-ALL",
    "WASH-ALL",
    "MOVER-ALL",
    "ODD",
    "EVEN",
)

# 합집합 파생 — 이름에서 구성 라벨로. 산문 열을 읽지 않고 여기서 온다.
_UNION_RULES: Mapping[str, tuple[str, ...]] = dict(
    [
        ("SIDE-ALL", ("SIDE-L", "SIDE-R")),
        ("WASH-ALL", ("WASH-U", "WASH-D")),
        ("MOVER-ALL", ("MOVER-U", "MOVER-D")),
    ]
)

# Members 열에서 개수만 뽑는 정규식. 개수를 안 적은 행은 대조 대상이 아니다.
_COUNT_PATTERN = re.compile(r"(\d+)\s*대")


@dataclass(frozen=True)
class GroupBucket:
    """한 그룹의 쓰기 단위 — `create_arrangement_groups` 의 groups 원소 하나."""

    group_no: int
    name: str
    fids: tuple[int, ...]
    longest_line_bytes: int


@dataclass(frozen=True)
class GroupBatch:
    """한 번의 `create_arrangement_groups` 호출로 나갈 묶음."""

    index: int
    buckets: tuple[GroupBucket, ...]


@dataclass(frozen=True)
class GroupSkip:
    """계획에서 빠진 그룹 — 닫힌 kind 3부류."""

    group_no: int
    name: str
    kind: str
    detail: str


@dataclass(frozen=True)
class SlotDivergence:
    """시트가 선언한 슬롯 순열과 콘솔이 답한 빈 슬롯 순열의 대조표."""

    sheet_slots: tuple[int, ...]
    measured_slots: tuple[int, ...]
    detail: str


@dataclass(frozen=True)
class GroupMapResult:
    batches: tuple[GroupBatch, ...]
    skipped: tuple[GroupSkip, ...]
    slot_divergence: SlotDivergence | None
    console_read_incomplete: bool


def build_label_fid_table(patch_rows: Sequence[Mapping[str, str]]) -> dict[str, tuple[int, ...]]:
    """패치 행에서 「Group 라벨 -> FID 목록」 표를 만든다 (REQ-LXSEQ2-004).

    멤버십의 **유일한** 출처다. FID_BASE 같은 산술로 만들지 않는다 — 이
    쇼파일에서는 두 방식이 같은 값을 내지만, 산술은 패치가 바뀌면 조용히
    틀린 값을 내고 멤버십은 되읽히지 않아 적발되지 않는다.

    FID 는 라벨 안에서 오름차순으로 낸다. 선택 줄의 순서가 곧 방향이므로
    (`build_spatial_selection_chain` 독스트링) 여기서 확정하고 하류에서
    다시 정렬하지 않는다.
    """
    table: dict[str, list[int]] = dict()
    for row in patch_rows:
        label = (row.get("Group") or "").strip()
        raw = (row.get("FID") or "").strip()
        if not label or not raw:
            continue
        table.setdefault(label, []).append(int(raw))
    return dict((label, tuple(sorted(fids))) for label, fids in table.items())


def measure_command_bytes(command: str) -> int:
    """이 명령 한 줄이 차지하는 바이트 수 — **프레이밍 제외**.

    프레이밍을 여기서 더하지 않는 이유는 그 값이 전송층에 있고 이 층이
    전송층을 임포트할 수 없기 때문이다(위 ANCHOR). 예산
    `DEFAULT_LINE_BYTE_BUDGET` 이 프레이밍 여유를 이미 뺀 값이므로 둘을
    함께 쓰면 같은 판정이 나온다. 그 등가성은 테스트가 잰다.
    """
    return len(command.encode("utf-8"))


def _derived_fids(name: str, table: Mapping[str, tuple[int, ...]]) -> tuple[int, ...] | None:
    """파생 6종의 멤버. 닫힌 규칙 밖이면 None."""
    if name == "ALL":
        everything: list[int] = []
        for fids in table.values():
            everything.extend(fids)
        return tuple(sorted(everything))
    if name in _UNION_RULES:
        joined: list[int] = []
        for label in _UNION_RULES[name]:
            joined.extend(table.get(label, ()))
        return tuple(sorted(joined))
    if name in ("ODD", "EVEN"):
        mover = _derived_fids("MOVER-ALL", table)
        if mover is None:
            return None
        want_odd = name == "ODD"
        return tuple(f for f in mover if (f % 2 == 1) == want_odd)
    return None


def _declared_count(members_raw: str) -> int | None:
    """Members 가 적은 개수. 개수를 안 적은 행이면 None (대조 대상 아님)."""
    found = _COUNT_PATTERN.search(members_raw)
    return int(found.group(1)) if found else None


def _measure_empty_slots(groups_section: Mapping[str, object], count: int) -> tuple[int, ...]:
    """빈 슬롯을 오름차순으로 count 개 잰다. **단면이 관측일 때만** 부른다.

    `server/groupgen/write.py` 의 `measure_empty_slots` 와 같은 규칙이다.
    그 함수를 부르지 않는 이유는 이 층이 계획을 세우는 곳이지 쓰는 곳이
    아니고, 그 함수는 풀 판독 실패에 예외를 던지기 때문이다 — 여기서는
    어긋남을 **보고**해야 하지 던지면 안 된다. 두 규칙이 같은지는 테스트가
    잰다.

    「관측일 때만」이 호출 규약이다 — 이 함수는 단면의 사용 가능 여부를 **안
    본다.** 판정은 `map_groups` 가 호출 **전에** `server/rig/section.py` 로
    한다. 이 함수 안에 검사를 또 두면 술어가 둘이 된다.

    이 규약이 없던 동안 `.get("objects") or ()` 가 판독 실패 단면(키 자체가
    없다)을 빈 점유 집합으로 읽었고, 슬롯 1..N 이 비었다고 답했다 — 콘솔이
    답한 적 없는 자리에 그룹을 쓰는 계획이 됐다(t109 C4).
    """
    occupied = set()
    for entry in groups_section.get("objects") or ():
        number = entry.get("no") if isinstance(entry, Mapping) else None
        if isinstance(number, int):
            occupied.add(number)
    empty: list[int] = []
    candidate = 1
    while len(empty) < count:
        if candidate not in occupied:
            empty.append(candidate)
        candidate += 1
    return tuple(empty)


def map_groups(
    *,
    group_records: Sequence[LxseqGroupRecord],
    patch_rows: Sequence[Mapping[str, str]],
    console_fids: Sequence[int],
    console_fids_complete: bool,
    groups_section: Mapping[str, object],
    line_byte_budget: int = DEFAULT_LINE_BYTE_BUDGET,
    batch_cap: int = DEFAULT_GROUP_PLAN_CAP,
) -> GroupMapResult:
    """그룹 레코드를 `create_arrangement_groups` 인자 배치로 바꾼다.

    어긋나면 아무것도 만들지 않는다. 부분 계획은 이 도메인에서 최악의
    결과다 — 반쯤 맞는 그룹이 쇼파일에 남고, 멤버십은 되읽히지 않아
    사후에 갈리지 않는다.
    """
    if not console_fids_complete:
        return GroupMapResult(
            batches=(),
            skipped=(),
            slot_divergence=None,
            console_read_incomplete=True,
        )

    table = build_label_fid_table(patch_rows)
    live = set(console_fids)
    skipped: list[GroupSkip] = []
    base: list[GroupBucket] = []
    derived: list[GroupBucket] = []

    for record in group_records:
        name = record.name
        if name in DERIVED_GROUP_NAMES:
            fids = _derived_fids(name, table)
        elif name in table:
            fids = table[name]
        else:
            skipped.append(
                GroupSkip(
                    group_no=record.group_no,
                    name=name,
                    kind="unknown_group_name",
                    detail="패치 라벨도 파생 6종도 아니다 — 추측하지 않는다",
                )
            )
            continue

        # 콘솔에 실재하는 FID 만 남긴다. 없는 FID 를 고르면 Store 가 빈
        # 프로그래머에 대해 실행되고 콘솔은 그래도 ok 를 답한다.
        present = tuple(f for f in (fids or ()) if f in live)

        declared = _declared_count(record.members_raw)
        if declared is not None and declared != len(present):
            skipped.append(
                GroupSkip(
                    group_no=record.group_no,
                    name=name,
                    kind="member_count_mismatch",
                    detail=(
                        "시트가 적은 개수 "
                        + str(declared)
                        + " 와 실제 FID 수 "
                        + str(len(present))
                        + " 가 다르다"
                    ),
                )
            )
            continue

        chain = build_compact_fixture_selection(present)
        line_bytes = measure_command_bytes(chain)
        if line_bytes > line_byte_budget:
            skipped.append(
                GroupSkip(
                    group_no=record.group_no,
                    name=name,
                    kind="line_over_budget",
                    detail=(
                        "선택 줄이 "
                        + str(line_bytes)
                        + " 바이트로 예산 "
                        + str(line_byte_budget)
                        + " 을 넘는다 — 넘으면 조용히 버려진다"
                    ),
                )
            )
            continue

        bucket = GroupBucket(
            group_no=record.group_no, name=name, fids=present, longest_line_bytes=line_bytes
        )
        (derived if name in DERIVED_GROUP_NAMES else base).append(bucket)

    # @MX:ANCHOR: [AUTO] 배치 순서는 **GroupNo 오름차순**이다. 기본 먼저가 아니다.
    # @MX:REASON: `build_group_write_plan` 은 `measure_empty_slots` 가 낸 빈
    #   슬롯을 **준 순서대로** 짝지어 배정한다(zip). 그러므로 GroupNo 순서가
    #   아닌 어떤 순서로 넘겨도 18개 전부 번호가 밀린다 — 곡 파일이 그룹
    #   번호를 참조하므로 그것은 쇼의 의미를 조용히 깨는 변경이다.
    #   plan-phase 는 「기본 12 먼저, 파생 6 나중」으로 적었는데 그것은
    #   REQ-LXSEQ2-009(슬롯을 시트대로)와 **양립하지 않는다.** 구현에서
    #   드러났고 SPEC 을 고쳤다. 카드의 "12는 옮기고 6은 규칙으로 만든다"는
    #   멤버십의 **출처**에 대한 말이지 배치 순서에 대한 말이 아니었다.
    planned = sorted(base + derived, key=lambda bucket: bucket.group_no)
    if not planned:
        return GroupMapResult(
            batches=(),
            skipped=tuple(skipped),
            slot_divergence=None,
            console_read_incomplete=False,
        )

    # [HARD] 재기 **전에** 단면이 관측인지 묻는다. 술어는 이 저장소에 하나뿐이고
    # (`server/rig/section.py`), 슬롯을 재는 자리는 전부 그것을 부른다.
    #
    # 여기서 `slot_divergence` 로 보고하면 안 된다 — 「어긋났다」는 시트를 고치러
    # 가라는 신호인데, 실제로는 콘솔을 못 읽은 것이라 시트를 고쳐도 안 낫는다.
    # 그래서 이미 있는 `console_read_incomplete` 로 답한다. 그 필드가 원래
    # 「콘솔 쪽을 못 읽었다」는 뜻이고, 이것이 정확히 그 경우다.
    if section_refusal(groups_section) is not None:
        return GroupMapResult(
            batches=(),
            skipped=tuple(skipped),
            slot_divergence=None,
            console_read_incomplete=True,
        )

    sheet_slots = tuple(bucket.group_no for bucket in planned)
    measured = _measure_empty_slots(groups_section, len(planned))
    if measured != sheet_slots:
        return GroupMapResult(
            batches=(),
            skipped=tuple(skipped),
            slot_divergence=SlotDivergence(
                sheet_slots=sheet_slots,
                measured_slots=measured,
                detail=(
                    "시트가 선언한 슬롯 순열과 콘솔이 답한 빈 슬롯 순열이 다르다. "
                    "번호를 옮겨 배정하지 않는다 — 곡 파일이 그룹 번호를 참조한다"
                ),
            ),
            console_read_incomplete=False,
        )

    batches: list[GroupBatch] = []
    for index, chunk_start in enumerate(range(0, len(planned), batch_cap)):
        window = tuple(planned[chunk_start : chunk_start + batch_cap])
        batches.append(GroupBatch(index=index, buckets=window))

    return GroupMapResult(
        batches=tuple(batches),
        skipped=tuple(skipped),
        slot_divergence=None,
        console_read_incomplete=False,
    )

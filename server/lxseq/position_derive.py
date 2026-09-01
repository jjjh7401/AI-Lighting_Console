"""POS.xx 포지션 프리셋 **산출** — 시트가 적어 둔 무대 의미를 좌표에서 값으로.

순수 함수다 — 콘솔·네트워크 입출력 0.

## 왜 이 모듈이 있나

`preset-pos` 시트는 열이 `ID,StageMeaning,TargetGroup,RecordGuide` 라 **값 열이
없다.** 그래서 `preset_parser.py` 가 이 시트를 자기 경로에서 명시적으로 뺐고
(REQ-LXSEQ3-002), `import_lxseq_cues` 의 `preset_slots` 조인(ID->Name->슬롯)도
POS 에서만 서지 않았다. 결과는 큐 12칸 · 큐 8개가 통째로 안 나가는 것이다 —
t207 이후 파이프라인이 전부 아니면 전무라서, 한 행이 보류되면 배치가 거절된다.

이 모듈은 **없는 값 열을 만들어 내지 않는다.** 시트가 이미 적어 둔 두 열
(`StageMeaning` · `TargetGroup`)을 리그 좌표에 대고 기하로 푼다. 산출한 값은
현장 레코드의 **대체물이 아니라 출발점**이다 — RIG 노트의 「POS.01~08 포지션
프리셋 전부 현장 레코드 필요」는 이 카드 뒤에도 그대로 유효하고, 그래서 라벨이
「· 산출값」을 달고 나간다(사람이 산출과 레코드를 구별할 수 있어야 한다).

## 두 좌표계를 섞지 않는다

- **조준 대상**(어느 장비를 움직이나)은 그 행의 `TargetGroup` 이다. 전 픽스처가
  아니다 — 시트는 보컬 페이스를 요구했는데 리그 전체를 흔들면 안 된다.
- **무대 기준틀**(어디를 겨누나)은 **리그 전체** 좌표에서 나온다. 선택한 장비가
  6대라고 무대가 좁아지지는 않는다. `KEY` 6대만으로 `front_y` 를 잡으면 보컬
  포인트가 FOH 브리지 2m 앞, 즉 객석 안이 된다.

이 갈래를 안 지키면 산출값이 조용히 틀린다 — 명령은 성공하고 빔만 엉뚱한 데 간다.

## 못 푸는 행은 건너뛴다

날조보다 결손이 낫다. 못 푼 행은 `SkippedPosition` 으로 사유와 함께 나오고,
한 행이 못 풀려도 나머지는 산다. 사유 어휘:

| 사유 | 뜻 |
|---|---|
| `unknown_group` | 그룹 이름이 배정표에 없다 |
| `no_coordinates` | 좌표를 아예 못 읽었다 (그룹 전체 또는 리그 전체) |
| `degenerate_rig` | **좌표는 읽혔는데 리그가 한 점에 접혀 있다** (t222) |
| `unaimable` | 필요 tilt 가 조준 상한을 넘는다 |
| `target_coincides` | 목표점이 장비 자신 — 빔 방향이 정의되지 않는다 |
| `unaimable_mixed` | 한 행 안에서 위 두 원인이 섞였다 |

## 퇴화한 리그는 **전 행**을 거절한다 (t222)

t221 이 실측한 상태: 콘솔 86대의 `Posx/Posy/Posz` 가 전부 0.0 인데도 세 행
(POS.01·05·06)이 초록으로 나왔다. 전 대상이 `Pan 180 / Tilt 128.7` 한 값이고
라벨은 「· 산출값」을 달아 사람이 **출발점으로 읽는다.** 눈으로는 진짜 산출과
구별되지 않는 그럴듯한 날조다 — 이 모듈이 스스로 세운 「날조보다 결손이 낫다」에
정면으로 어긋난다.

그래서 `rig_is_degenerate` 가 참이면 한 행도 산출하지 않는다. 술어를 무엇으로
고를지는 열려 있었고, 후보 둘을 코퍼스에 대고 재서 골랐다 — 근거는 그 함수의
독스트링에 있다.

**이 가드는 큐를 하나도 열지 않는다.** 사고를 막을 뿐이고, 병목은 여전히 좌표
데이터다(`arrange_fixtures` 가 `Posx/Posy/Posz` 를 쓸 수 있으니 막힌 것은 능력이
아니라 값이다).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.lxseq.group_parser import parse_group_csv
from server.lxseq.parser import parse_patch_csv
from server.presets.store import preset_store_commands
from server.spatial.pointing import (
    _VOCAL_DOWNSTAGE_OFFSET,
    _VOCAL_HEIGHT,
    POINTING_TILT_LIMIT_DEGREES,
    POSITION_PRESET_POOL,
    PointingTargetCoincidesError,
    PointingTiltLimitError,
    SpatialPointingError,
    aim_pan_tilt,
    aimed_commands,
    fan_chain,
    fan_pan_tilt,
)
from server.spatial.rows import SPATIAL_ROW_NOISE_SPAN

# 보컬 포인트의 위치·높이는 `basic_position_presets` 의 Vocal DSC 와 **같은 점**
# 이어야 해서 비공개 이름 둘을 직접 든다. 여기에 숫자를 다시 적으면 한쪽만 바뀌는
# 날 두 경로의 보컬 자리가 조용히 갈린다.

__all__ = [
    "POSITION_RULES",
    "POSITION_SHEET_COLUMNS",
    "DerivedPosition",
    "PositionDerivationResult",
    "PositionRule",
    "PositionSheetRow",
    "SkippedPosition",
    "UnknownPositionSheetError",
    "rig_is_degenerate",
    "derive_position_presets",
    "group_members_from_sheets",
    "parse_position_sheet",
    "position_preset_bundles",
]

#: 정본 `preset-pos` 시트의 **정확** 열 집합. `preset_parser.PRESET_SHEET_COLUMNS`
#: 의 세 종류와 쌍마다 구별된다 — 그래서 포함 검사가 필요 없다.
POSITION_SHEET_COLUMNS: tuple[str, ...] = ("ID", "StageMeaning", "TargetGroup", "RecordGuide")

#: 시트 ID 접두.
POSITION_ID_PREFIX = "POS."

#: 콘솔 라벨 꼬리. 이 문자열이 「이 값은 사람이 현장에서 잡은 것이 아니다」를
#: 나른다 — 라벨이 유일하게 콘솔 화면에 남는 자리라서 여기에 붙인다.
DERIVED_LABEL_SUFFIX = "산출값"


class UnknownPositionSheetError(ValueError):
    """열 집합이 preset-pos 가 아니다."""


@dataclass(frozen=True)
class PositionSheetRow:
    """`preset-pos` 시트 1행."""

    preset_id: str
    stage_meaning: str
    target_group: str
    record_guide: str


@dataclass(frozen=True)
class PositionRule:
    """한 POS ID 의 산출 규칙.

    `stage_meaning` 은 **시트 문면 핀**이다. 규칙은 시트의 그 문장을 기하로 옮긴
    것이므로, 시트가 바뀌면 규칙도 다시 봐야 한다. 검사가 이 값과 정본 CSV 를
    대조해서 어긋나면 빨개진다 — 조용히 낡지 않게 하는 유일한 기전이다.
    """

    preset_id: str
    stage_meaning: str
    target_group: str
    kind: str
    #: 라벨·보고에 그대로 실리는 산출 근거 한 줄.
    summary: str


#: POS.01~06 만 규칙이 있다. 07·08 은 시트가 스스로 「예비 (타 곡 대비)」라 적었고
#: 정본 큐시트가 한 번도 참조하지 않는다(정본 CSV 전수: POS.01~06 만 12칸).
#: 안 쓰는 프리셋을 콘솔에 올리는 것은 이득 없는 쓰기다.
POSITION_RULES: tuple[PositionRule, ...] = (
    PositionRule(
        "POS.01",
        "보컬 센터 페이스",
        "KEY",
        "focus_vocal",
        "리그 중심 x · 최전열보다 2m 앞 · 높이 1.6m 의 센터 마이크 지점을 대상 전원이 조준",
    ),
    PositionRule(
        "POS.02",
        "무대 전체 커버",
        "MOVER-D",
        "spread_floor",
        "리그 x 폭을 대상 대수로 등분한 착지점을 무대 중앙 깊이 바닥에 한 줄로",
    ),
    PositionRule(
        "POS.03",
        "밴드 라인 백",
        "BACK",
        "silhouette_line",
        "각 장비 x 를 유지한 채 무대 중앙 깊이 · 머리 높이 1.6m — 실루엣 각이고 "
        "착지점이 무대 위라 객석 직사가 없다",
    ),
    PositionRule(
        "POS.04",
        "틸트업 스타트 (무대 안쪽)",
        "MOVER-U",
        "floor_inside",
        "각 장비 x 를 유지한 채 무대 중앙 깊이 바닥 — 상승 시작점",
    ),
    PositionRule(
        "POS.05",
        "팬아웃 종점 (객석 상단)",
        "MOVER-ALL",
        "fan_out",
        "다운스테이지 기준 tilt 45도에서 좌우 30도 부채꼴 (fan_pan_tilt out)",
    ),
    PositionRule(
        "POS.06",
        "센터 집중 (브리지)",
        "KEY+BACK",
        "focus_vocal",
        "POS.01 과 같은 보컬 포인트를 KEY+BACK 이 함께 조준 — 1인 포커스",
    ),
)

#: 산출 규칙 갈래. 닫힌 어휘다 — 새 갈래는 여기와 `_aims_for` 양쪽에 넣어야 한다.
RULE_KINDS: tuple[str, ...] = tuple(dict.fromkeys(rule.kind for rule in POSITION_RULES))

_RULE_BY_ID: dict[str, PositionRule] = {rule.preset_id: rule for rule in POSITION_RULES}


@dataclass(frozen=True)
class DerivedPosition:
    """콘솔에 올릴 수 있게 풀린 한 행."""

    preset_id: str
    slot: int
    label: str
    target_group: str
    rule_kind: str
    summary: str
    aims: tuple[tuple[int, float, float], ...]
    #: 이 룩에서 조준이 안 된 FID. 클램프하지 않고 이름을 남긴다.
    skipped_fids: tuple[int, ...]


@dataclass(frozen=True)
class SkippedPosition:
    """못 푼 한 행 — 사유를 들고 나온다."""

    preset_id: str
    target_group: str
    reason: str
    detail: str


@dataclass(frozen=True)
class PositionDerivationResult:
    """산출물. 확인 한계를 스스로 말한다(형제 매퍼들과 같은 규약)."""

    derived: tuple[DerivedPosition, ...]
    skipped: tuple[SkippedPosition, ...]
    unverified: tuple[str, ...] = ("field_record",)
    unverified_reason: str = (
        "좌표 기하에서 산출한 값이다 — 현장에서 실제 빔 착지를 보고 잡은 값이 아니다"
    )


def _strip_bom(text: str) -> str:
    """BOM 을 걷어낸다 — 정본 CSV 들이 UTF-8 BOM 을 달고 있다(tools.py 와 같은 관용구)."""
    return text.removeprefix(chr(0xFEFF))


def parse_position_sheet(text: str) -> tuple[PositionSheetRow, ...]:
    """`preset-pos` CSV 를 행으로. 열 집합이 다르면 거절한다."""
    reader = csv.DictReader(io.StringIO(_strip_bom(text)))
    fieldnames = tuple(_strip_bom(name or "").strip() for name in (reader.fieldnames or ()))
    if fieldnames != POSITION_SHEET_COLUMNS:
        raise UnknownPositionSheetError("열 집합이 preset-pos 가 아니다: " + repr(fieldnames))
    rows: list[PositionSheetRow] = []
    for raw in reader:
        preset_id = (raw.get("ID") or "").strip()
        if not preset_id.startswith(POSITION_ID_PREFIX):
            continue
        rows.append(
            PositionSheetRow(
                preset_id=preset_id,
                stage_meaning=(raw.get("StageMeaning") or "").strip(),
                target_group=(raw.get("TargetGroup") or "").strip(),
                record_guide=(raw.get("RecordGuide") or "").strip(),
            )
        )
    return tuple(rows)


def group_members_from_sheets(patch_text: str, group_text: str) -> dict[str, tuple[int, ...]]:
    """그룹 이름 -> FID 들. 기본 그룹은 patch 시트, 합집합 그룹은 group 시트.

    patch 시트의 `Group` 열이 기본 소속을 준다(FID 하나는 기본 그룹 하나에 든다).
    group 시트의 `Members` 가 「A + B」 꼴이고 양쪽이 이미 아는 기본 그룹이면
    **합집합 그룹**으로 편다 — `MOVER-ALL` · `SIDE-ALL` · `WASH-ALL` 이 그렇다.
    그 꼴이 아닌 `Members`(「전 픽스처 (FOLLOW 제외)」·「MOVER-ALL 홀수 FID」)는
    산문이라 **풀지 않는다** — 추측해서 펴면 없는 멤버십을 만든다.
    """
    base: dict[str, list[int]] = {}
    for record in parse_patch_csv(patch_text).records:
        base.setdefault(record.group, []).append(record.fid)
    members: dict[str, tuple[int, ...]] = {}
    for name, fids in base.items():
        members[name] = tuple(sorted(fids))
    for record in parse_group_csv(group_text).records:
        if record.name in members:
            continue
        parts = [part.strip() for part in record.members_raw.split("+")]
        if len(parts) < 2 or not all(part in members for part in parts):
            continue
        union: set[int] = set()
        for part in parts:
            union.update(members[part])
        members[record.name] = tuple(sorted(union))
    return members


def _resolve_group(name: str, members: Mapping[str, Sequence[int]]) -> tuple[int, ...] | None:
    """`KEY+BACK` 처럼 시트가 직접 쓴 합집합 표기까지 편다."""
    parts = [part.strip() for part in name.split("+") if part.strip()]
    if not parts:
        return None
    union: set[int] = set()
    for part in parts:
        if part not in members:
            return None
        union.update(members[part])
    return tuple(sorted(union))


def _slot_of(preset_id: str) -> int:
    return int(preset_id.removeprefix(POSITION_ID_PREFIX))


#: 퇴화 리그 사유. 「좌표는 읽혔는데 리그가 한 점에 접혀 있다」 — `no_coordinates`
#: (아예 못 읽었다)와 **다른 상태**라 사유를 갈라 둔다.
DEGENERATE_RIG_REASON = "degenerate_rig"


def rig_is_degenerate(coordinates: Mapping[int, tuple[float, float, float]]) -> bool:
    """수평면(x·y)에 폭이 없으면 참 — 이 리그에서는 어떤 행도 산출하지 않는다.

    ## 왜 이 술어인가 (두 후보를 코퍼스에 대고 재고 골랐다)

    후보 A(직접 계산한 span)와 후보 B(`get_spatial_context` 응답의
    `analysis.low_confidence` 신뢰)의 경계는 **겹치지 않는다.** 코퍼스 8종 실측
    (`.moai/reports/t222/evidence/predicate.txt`):

    - B 는 `weak_gap_separation` 에서도 참이다. 그 리그는 x 폭 4m · y 폭 8m 의
      **멀쩡한 리그**이고 등분도 조준도 성립한다 — B 를 그대로 쓰면 **거짓 거절**이다.
      `low_confidence` 가 답하는 질문은 「열 분할이 모호한가」이지 「조준할 폭이
      있는가」가 아니다.
    - A 를 span 이 정확히 0 일 때로 잡으면 `vertical_spread_only`(x·y 는 한 점,
      z 만 벌어짐)와 노이즈 폭 아래 미세 편차를 놓친다. 둘 다 목표점이 한 점으로
      접혀 산출이 무의미하다.

    그래서 채택한 것은 **수평면만 노이즈 폭에 거는 술어**다. 실측상 이것은
    `low_confidence and confidence_reason in (no_spatial_spread,
    vertical_spread_only)` 와 코퍼스 8종에서 **전부 일치**한다 — 즉 B 의 부분집합을
    순수 함수 안에서 재현한다. 라이브 도구 응답을 이 순수 모듈로 끌고 들어오지 않아도
    같은 판정이 선다.

    **z 는 일부러 뺀다.** 한 트러스에 매단 리그는 z span 이 0 이고 그것은 정상이다.
    세 축 전부를 요구하면 가장 흔한 리그를 거절한다(코퍼스 `single_bar_9`).

    임계값은 `server.spatial.rows.SPATIAL_ROW_NOISE_SPAN` 을 **빌려 쓴다** — 여기에
    숫자를 다시 적으면 한쪽만 바뀌는 날 두 판정이 조용히 갈린다.
    """
    if not coordinates:
        return False
    xs = [position[0] for position in coordinates.values()]
    ys = [position[1] for position in coordinates.values()]
    return max(max(xs) - min(xs), max(ys) - min(ys)) <= SPATIAL_ROW_NOISE_SPAN


@dataclass(frozen=True)
class _StageFrame:
    """무대 기준틀 — **리그 전체** 좌표에서만 나온다(모듈 독스트링 참조)."""

    cx: float
    cy: float
    min_x: float
    max_x: float
    vocal_point: tuple[float, float, float]


def _stage_frame(coordinates: Mapping[int, tuple[float, float, float]]) -> _StageFrame:
    xs = [position[0] for position in coordinates.values()]
    ys = [position[1] for position in coordinates.values()]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    front_y = min(ys)
    return _StageFrame(
        cx=cx,
        cy=cy,
        min_x=min(xs),
        max_x=max(xs),
        vocal_point=(cx, front_y - _VOCAL_DOWNSTAGE_OFFSET, _VOCAL_HEIGHT),
    )


def derive_position_presets(
    rows: Sequence[PositionSheetRow],
    members: Mapping[str, Sequence[int]],
    coordinates: Mapping[int, tuple[float, float, float]],
) -> PositionDerivationResult:
    """시트 행 + 그룹 멤버십 + 리그 좌표 -> 콘솔에 올릴 조준값.

    `coordinates` 는 **리그 전체**를 담아야 한다 — 무대 기준틀이 여기서 나온다.
    규칙이 없는 ID(POS.07·08)는 조용히 건너뛴다: 결손이 아니라 범위 밖이다.
    """
    ruled = [row for row in rows if row.preset_id in _RULE_BY_ID]
    if not coordinates:
        return PositionDerivationResult(
            (),
            tuple(
                SkippedPosition(row.preset_id, row.target_group, "no_coordinates", "리그 좌표 0건")
                for row in ruled
            ),
        )
    if rig_is_degenerate(coordinates):
        # 좌표는 읽혔지만 리그가 한 점에 접혀 있다. 여기서 한 행이라도 산출하면
        # 그럴듯한 날조가 나간다 — t221 실측: 전 대상이 Pan 180 / Tilt 128.7 한 값
        # 이고 라벨은 「· 산출값」을 달아 사람이 출발점으로 읽는다. 전 행을 거절한다.
        xs = [position[0] for position in coordinates.values()]
        ys = [position[1] for position in coordinates.values()]
        detail = (
            f"좌표 {len(coordinates)}대를 읽었지만 수평 폭이 없다 "
            f"(x span {max(xs) - min(xs):.3f}m · y span {max(ys) - min(ys):.3f}m "
            f"<= {SPATIAL_ROW_NOISE_SPAN}m) — 목표점이 한 점으로 접혀 산출값이 "
            "무의미하다. 리그 좌표를 콘솔에 넣어야 풀린다"
        )
        return PositionDerivationResult(
            (),
            tuple(
                SkippedPosition(row.preset_id, row.target_group, DEGENERATE_RIG_REASON, detail)
                for row in ruled
            ),
        )
    frame = _stage_frame(coordinates)
    derived: list[DerivedPosition] = []
    skipped: list[SkippedPosition] = []
    for row in ruled:
        rule = _RULE_BY_ID[row.preset_id]
        fids = _resolve_group(row.target_group, members)
        if fids is None:
            skipped.append(
                SkippedPosition(
                    row.preset_id, row.target_group, "unknown_group", "그룹 이름이 배정표에 없다"
                )
            )
            continue
        placed = [(fid, coordinates[fid]) for fid in fids if fid in coordinates]
        if not placed:
            skipped.append(
                SkippedPosition(
                    row.preset_id,
                    row.target_group,
                    "no_coordinates",
                    f"그룹 {len(fids)}대 중 좌표가 확인된 장비 0대",
                )
            )
            continue
        aims, unaimable, causes = _aims_for(rule.kind, placed, frame)
        if not aims:
            reason, detail = _skip_for_unaimable(len(placed), causes)
            skipped.append(SkippedPosition(row.preset_id, row.target_group, reason, detail))
            continue
        derived.append(
            DerivedPosition(
                preset_id=row.preset_id,
                slot=_slot_of(row.preset_id),
                label=f"{row.preset_id} {rule.stage_meaning} · {DERIVED_LABEL_SUFFIX}",
                target_group=row.target_group,
                rule_kind=rule.kind,
                summary=rule.summary,
                aims=aims,
                skipped_fids=unaimable,
            )
        )
    return PositionDerivationResult(tuple(derived), tuple(skipped))


#: 조준 실패 원인 어휘. 닫힌 집합이고, **사유 문자열이 원인마다 달라야 한다** —
#: 서로 다른 원인이 같은 사유를 내면 그 사유는 판정을 못 돕는다(t221 실측).
CAUSE_TILT_LIMIT = "tilt_limit"
CAUSE_TARGET_COINCIDES = "target_coincides"

#: 사유별 한 줄. `unaimable` 이름은 그대로 둔다 — 이 사유를 이미 읽는 자리가 있고,
#: 갈라야 할 것은 이름이 아니라 **둘이 한 이름을 쓰던 상태**였다.
_REASON_BY_CAUSE = dict(
    [
        (CAUSE_TILT_LIMIT, "unaimable"),
        (CAUSE_TARGET_COINCIDES, "target_coincides"),
    ]
)
_MIXED_REASON = "unaimable_mixed"


def _cause_of(error: SpatialPointingError) -> str:
    """예외 **종류**로 원인을 가른다. 문면 매칭이 아니다."""
    if isinstance(error, PointingTargetCoincidesError):
        return CAUSE_TARGET_COINCIDES
    if isinstance(error, PointingTiltLimitError):
        return CAUSE_TILT_LIMIT
    # 닫힌 어휘에 없는 새 갈래. 조용히 tilt_limit 로 접으면 이 함수가 다시
    # 두 원인을 한 이름으로 만든다 — 그래서 자기 이름으로 내보낸다.
    return "unclassified"


def _skip_for_unaimable(count: int, causes: frozenset[str]) -> tuple[str, str]:
    """(사유, 상세) — 원인 집합이 사유 문자열을 정한다."""
    if causes == frozenset([CAUSE_TARGET_COINCIDES]):
        return (
            _REASON_BY_CAUSE[CAUSE_TARGET_COINCIDES],
            f"대상 {count}대 전부 목표점이 장비 자신과 같은 자리다 (거리 0) — "
            "빔 방향이 정의되지 않는다. 조준 한계와는 무관하다",
        )
    limit_note = (
        f"조준 상한 {POINTING_TILT_LIMIT_DEGREES:.0f}° 를 넘는다. "
        "⚠️ 이 상한은 실측이 아니라 다른 리그 기종(Robe LEDBeam 350 / MMX)에서 온 "
        "모듈 상수다 — 이 쇼의 기종 가동범위로 다시 재야 한다"
    )
    if causes == frozenset([CAUSE_TILT_LIMIT]):
        return (_REASON_BY_CAUSE[CAUSE_TILT_LIMIT], f"대상 {count}대 전부 {limit_note}")
    if CAUSE_TILT_LIMIT in causes and CAUSE_TARGET_COINCIDES in causes:
        return (
            _MIXED_REASON,
            f"대상 {count}대가 두 원인으로 갈려 실패했다 — 일부는 거리 0(빔 방향 "
            f"미정의), 일부는 {limit_note}",
        )
    return (
        _REASON_BY_CAUSE[CAUSE_TILT_LIMIT],
        f"대상 {count}대 전부 조준 실패 — 분류되지 않은 원인 {sorted(causes)}",
    )


def _aims_for(
    kind: str,
    placed: Sequence[tuple[int, tuple[float, float, float]]],
    frame: _StageFrame,
) -> tuple[tuple[tuple[int, float, float], ...], tuple[int, ...], frozenset[str]]:
    """한 규칙 갈래의 (aims, 조준 실패 FID, **실패 원인 집합**).

    실패는 클램프하지 않고 이름을 남긴다. 세 번째 값이 t222 에서 붙었다 —
    이전에는 서로 다른 두 원인(한계 밖 / 거리 0)이 호출자에서 **바이트 동일한**
    사유 한 줄로 접혔고, 그것이 t221 의 오진(「물리적 도달 불가인가?」)을 만들었다.
    원인은 예외 **종류**로 가른다. 문면 매칭이 아니다 — 문면은 조용히 바뀐다.
    """
    if kind == "fan_out":
        # 팬은 체인 순서의 함수라 한 대라도 한계를 넘으면 부채꼴 전체가 거절된다 —
        # 여기서 부분 조준을 만들면 시트가 요구한 모양이 아니다.
        try:
            return fan_pan_tilt(fan_chain(list(placed)), mode="out"), (), frozenset()
        except SpatialPointingError as error:
            return (
                (),
                tuple(fid for fid, _position in placed),
                frozenset([_cause_of(error)]),
            )

    pairs: list[tuple[int, tuple[float, float, float], tuple[float, float, float]]]
    if kind == "spread_floor":
        ordered_fids = fan_chain(list(placed))
        by_fid = dict(placed)
        count = len(ordered_fids)
        span = frame.max_x - frame.min_x
        pairs = [
            (
                fid,
                by_fid[fid],
                (
                    frame.cx if count == 1 else frame.min_x + index * span / (count - 1),
                    frame.cy,
                    0.0,
                ),
            )
            for index, fid in enumerate(ordered_fids)
        ]
    elif kind == "focus_vocal":
        pairs = [(fid, position, frame.vocal_point) for fid, position in placed]
    elif kind == "silhouette_line":
        pairs = [
            (fid, position, (position[0], frame.cy, _VOCAL_HEIGHT)) for fid, position in placed
        ]
    elif kind == "floor_inside":
        pairs = [(fid, position, (position[0], frame.cy, 0.0)) for fid, position in placed]
    else:  # pragma: no cover - 닫힌 어휘라 도달하지 않는다
        raise ValueError("unknown rule kind " + repr(kind))

    aims: list[tuple[int, float, float]] = []
    failed: list[int] = []
    causes: set[str] = set()
    for fid, position, target in pairs:
        try:
            pan, tilt = aim_pan_tilt(position, target)
        except SpatialPointingError as error:
            failed.append(fid)
            causes.add(_cause_of(error))
        else:
            aims.append((fid, pan, tilt))
    return tuple(aims), tuple(failed), frozenset(causes)


def position_preset_bundles(
    derived: Sequence[DerivedPosition],
    *,
    pool_no: int = POSITION_PRESET_POOL,
) -> tuple[tuple[str, ...], ...]:
    """룩마다 적용 -> Store -> Label -> ClearAll 한 번들.

    `server/web/session.py` 의 `_store_position_preset_looks` 와 **같은 순서**다 —
    한 룩이 거절돼도 나머지가 살고, ClearAll 이 프로그래머를 비워 다음 룩이 앞 룩의
    값을 물고 가지 않는다. 문형 사본을 새로 적지 않으려고 두 빌더를 그대로 부른다.
    """
    return tuple(
        (
            *aimed_commands(item.aims),
            *preset_store_commands(pool_no, item.slot, item.label),
            "ClearAll",
        )
        for item in derived
    )

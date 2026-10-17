"""SPEC-LDRHYTHM-001 stage 2 — LOVE ATTACK 연출 프리셋 계획 (순수 함수).

격자 칸이 쓰는 값(디머 %·색·방향)을 모아 「새로 만들 프리셋」 목록을 만든다.

- 같은 값은 한 프리셋으로 묶고 칸 수를 센다(de-dup).
- 번호는 콘솔 풀을 **읽은** 결과에서 빈 번호만 고른다 — 있는 번호는 덮지 않는다.
- 값·이름·대상 그룹이 확정되지 않은 것은 「미정」으로 남긴다(지어내지 않는다).

이 모듈은 콘솔에 아무것도 쓰지 않는다. 콘솔 풀 판독 결과와 디머 속성은 인자로 받는다.
승인 카드에 실을 저장 줄은 `save_commands`가 만들고, 칸의 번호 참조는 승인 **뒤에만**
`apply_plan_references`가 적는다 — 카드가 거절되면 격자는 바이트까지 그대로다.

저장 범위: 기본 디머 프리셋은 `save_commands` 가 속성으로 직접 만든다. 같은 값을 여러 그룹이 쓰면
프리셋은 하나이고, 저장은 그룹 한 선택(``Group 4 + 7 …``)으로 한 번에 한다. 색과 위치는 값이
정해지면 후보(``deferred``)로 남고, 콘솔 판독(그룹 소속 · 컬러 채널 · 장비 좌표)을 마친 뒤
`preset_plan_store` 가 기존 색(t594)·위치(t592) 경로의 조각으로 저장 줄(``PlanPreset.store``)을
붙인다 — 줄이 붙은 항목만 이 카드에 실리고, 못 붙인 항목은 사유와 함께 「미정」으로 남는다. 위치는
그룹마다 따로 저장한다(방향 하나가 그 방향을 쓰는 그룹 수만큼의 프리셋이 된다). 앱이 기본값을 쓴
항목은 「감독이 고칠 값」으로 모아 승인 카드에 보인다 — 콘솔의 값은 덮어쓰지 않는다.

칸 하나의 왼쪽·오른쪽 따로 색(``split``): 색이 정해진 쪽마다 색 후보 한 줄을 낸다
(``PlanPreset.split_side``). 콘솔 이름은 감독이 정하므로 이름은 비워 두고, 저장 줄도 칸 참조도
만들지 않는다 — ``save_commands``·``apply_plan_references`` 가 이 줄을 건너뛴다. 색이 비어 있는
쪽은 후보 없이 「미정」 줄만 남긴다.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from server.design.app_movement import movement_effect_store_commands
from server.design.arrange_policy import MOVER_POSITION_LADDER
from server.design.beat_grid import (
    apply_pending_approval,
    check_evidence_approval,
    pending_preset_approvals,
    preset_pool_no,
)
from server.design.beat_grid_cell_split import (
    CELL_SPLIT_SIDES,
    cell_split_side_rgb,
    validate_cell_split,
)
from server.design.beat_grid_color_presets import (
    color_preset_groups,
    color_preset_rgb,
    record_color_preset_rgb,
)
from server.design.beat_grid_edit import (
    apply_beat_grid_edit,
    beats_per_bar_from_timeline,
    speed_master_of,
)
from server.design.beat_grid_measured import canonical_axes
from server.design.beat_grid_mib import cue_is_lit
from server.design.beat_grid_presets import (
    app_preset_label,
    first_free_base_color_number,
    first_free_base_dimmer_number,
    first_free_base_position_number,
    record_app_preset_label,
)
from server.design.beat_grid_send import build_song_timing_from_bar_map
from server.design.cell_direction import assign_color_names
from server.design.color_names import COLOR_PALETTE_SEQUENCE, resolve_color_name
from server.design.preset_names import same_console_name

__all__ = [
    "LoveAttackPlan",
    "PlanCell",
    "PlanPreset",
    "apply_plan_references",
    "card_reason",
    "load_preset_annotations",
    "build_preset_plan",
    "resolve_preset",
    "save_commands",
    "saved_presets",
    "saved_summary",
]

#: 곡별 계획 주석 폴더 — 곡 제목 슬러그와 이름이 같은 YAML 이 있으면 그 곡의 색·방향 대응을 읽는다.
_ANNOTATIONS_DIR = Path(__file__).resolve().parent / "beat_grid_data" / "preset_annotations"

#: 디머 프리셋 콘솔 이름 접두 — 값으로 이름을 짓는다(같은 값 = 같은 이름).
_DIMMER_NAME_PREFIX = "DIM"

#: 디머 속성 기본 이름 — 콘솔 판독에서 그룹의 디머 속성을 못 얻었을 때만 쓴다(감독이 고칠 값).
_DEFAULT_DIMMER_ATTRIBUTE = "Dimmer"

#: 칸 하나의 왼쪽·오른쪽 색 후보의 보류 사유 머리 — 콘솔 이름은 앱이 짓지 않고 감독이 정한다.
_SPLIT_NAME_HOLD = "콘솔 이름 미정 — 칸 색 이름은 감독이 정한다"

#: 칸 하나의 쪽 이름 — 데이터 키 left·right 를 사유 문장에서 사람이 읽는 말로 바꾼다.
_SPLIT_SIDE_LABEL = {"left": "왼쪽", "right": "오른쪽"}

#: 칸 하나의 왼쪽·오른쪽 색 후보의 보류 사유 — 이름을 감독이 정할 때까지 이 카드는 저장 줄을
#: 만들지 않고, 색 저장은 기존 색 경로(t594)로 간다.
_COLOR_PATH_HOLD = "색 저장은 기존 「＋ 새 프리셋」 색 경로(t594)로 만든다 — 이 카드 범위 밖"

#: 칸·번호가 다 있는 색·위치 후보의 사유 — 저장 줄은 콘솔 판독을 마친 뒤
#: `preset_plan_store` 가 붙인다.
_COLOR_STORE_HOLD = "저장 줄 미정 — 콘솔에서 그룹 소속·컬러 채널을 읽은 뒤 만든다"
_POSITION_STORE_HOLD = "저장 줄 미정 — 콘솔에서 그룹 소속·장비 좌표를 읽은 뒤 만든다"
#: 무빙 기본 위치 사다리 이름 → 계획표 말.
#: 사다리 순서는 바닥 쪽 < 무대 중앙 < 위로 연 자리 < 객석 상단이다.
_POSITION_LABEL_KO = {
    "Home": "바닥 쪽",
    "Center": "무대 중앙",
    "Ring In": "위로 연 자리",
    "Audience": "객석 상단",
}

#: 움직임 효과 프리셋을 저장할 콘솔 풀(판독 이름 「All 1」, 풀 21).
#: 리드 결정으로 21번대를 쓴다. 번호대는 preset_pools.yaml 에 선언돼 있지 않으니
#: 「감독이 고칠 값」으로 싣는다.
#: 빈 번호는 콘솔 판독에서 고른다(있는 번호는 덮지 않는다).
MOVEMENT_EFFECT_POOL_NAME = "All 1"

#: 효과 프리셋 값의 화면 이름 — 모양 어휘를 사람이 읽는 말로.
_EFFECT_SHAPE_LABEL = {"wave": "웨이브"}

#: 효과 풀을 콘솔에서 읽지 못해 빈 번호를 정하지 못했을 때의 사유.
_EFFECT_POOL_HOLD = "효과 풀을 콘솔에서 읽지 못해 빈 번호를 정하지 못함"

#: 프리셋 종류의 화면 이름 — 저장 개수 요약(``saved_summary``)이 쓴다.
_KIND_LABEL = {"dimmer": "디머", "color": "색", "position": "위치", "effect": "효과"}

#: 저장한 색·위치·효과 프리셋을 칸에서 가리키는 필드.
_REFERENCE_FIELD = {
    "color": "color_preset_no",
    "position": "position_preset_no",
    "effect": "effect_preset_no",
}

#: 풀 판독 결과 — ``(풀 번호, {슬롯: 이름 또는 None})``. 못 읽었으면 ``None``.
PoolRead = tuple[int, Mapping[int, object]] | None


@dataclass(frozen=True)
class PlanCell:
    """계획이 쓰는 칸 하나(그룹 이름 + 마디)."""

    group_name: str
    bar: int


@dataclass(frozen=True)
class PlanPreset:
    """계획표의 프리셋 한 줄.

    ``slot``은 이 계획이 고른 **후보** 번호다(콘솔 풀에서 빈 것). ``ready``가 참이면 이 카드가
    저장 줄을 싣는다. 거짓이면 ``hold``가 사유다 — ``deferred``가 참이면 값은 정해졌고 저장 줄만
    아직 없다(「이 카드 밖」), 거짓이면 「미정」이다."""

    kind: str  # "dimmer" | "color" | "position" | "effect"
    value: str  # 사람이 읽는 값: "40%" · "RGB 55 35 100" · "바닥 쪽 (대략: …)"
    name: str  # 콘솔 이름(영문·숫자·공백·_.-)
    slot: str | None  # 후보 "pool.slot"; 풀을 못 읽으면 None
    cells: tuple[PlanCell, ...]
    groups: tuple[str, ...]  # 쓰는 그룹 이름(첫 등장 순)
    ready: bool
    hold: str | None  # ready 가 아니면 사유, ready 이면 None
    value_percent: int | None = None
    group_no: int | None = None  # 디머만 — 그룹이 하나일 때 그 번호(확인된 것)
    attributes: tuple[str, ...] = ()  # 디머만 — 저장 줄의 디머 속성 이름
    group_nos: tuple[int, ...] = ()  # 디머만 — 저장 선택 ``Group a + b`` 의 번호(확인된 것)
    #: 디머만 — 속성마다 그 속성을 가진 그룹 번호. 둘째 디머(``Dimmer2``)처럼 일부 기종에만 있는
    #: 속성은 그 그룹만 골라 낸다. 비면 ``attributes`` × ``group_nos`` 한 선택이다.
    attribute_group_nos: tuple[tuple[str, tuple[int, ...]], ...] = ()
    #: 값은 정해졌고 저장 줄만 아직 없다. 색·위치는 콘솔 판독 뒤 `preset_plan_store` 가 줄을
    #: 붙이거나 사유와 함께 「미정」으로 내리고(``resolve_preset``), 칸 쪽 색 후보는 기존 색
    #: 경로(t594)로 간다.
    deferred: bool = False
    #: 칸 하나의 왼쪽·오른쪽 따로 색 후보면 그 쪽(``"left"`` | ``"right"``), 아니면 ``None``.
    #: 값이 있으면 이 줄은 저장 줄도 칸 번호 참조도 만들지 않는다(이름은 감독이 정한다).
    split_side: str | None = None
    rgb: tuple[float, ...] | None = None  # 계획 RGB(0~100%), 화면이 쓴다
    #: 이 카드가 보낼 저장 줄 — 색·위치만(`preset_plan_store` 가 콘솔 판독 뒤 붙인다). 디머는
    #: 속성으로 `save_commands` 가 직접 만든다. ``None`` 인 색·위치는 ``ready`` 여도 카드에
    #: 실리지 않는다.
    store: tuple[str, ...] | None = None
    #: 콘솔에 이미 있는 같은 RGB·같은 그룹의 색 번호를 다시 쓴다 — 저장 줄은 없고(``store`` 없음),
    #: 칸은 그 번호를 가리키기만 한다(``saved_presets`` 가 넣고, ``save_commands`` 가 건너뛴다).
    reused: bool = False
    #: 효과 프리셋만 — 승인 뒤 격자에 남기는 내용 기록 ``(그룹 번호, 움직임 서명, BPM)``.
    #: 다음 계획이 같은 이름·같은 내용의 프리셋을 다시 만들지 않고 재사용하는 근거다.
    effect_record: tuple[object, ...] | None = None
    #: 위치 후보의 조준 기준. 기본 위치 이름(``Home``·``Center``·``Ring In``·``Audience``)이면
    #: 그 리그 조준값을 쓴다. ``None`` 이면 주석의 바닥 점(「바닥 쪽」) 규칙이다.
    aim: str | None = None


@dataclass(frozen=True)
class LoveAttackPlan:
    presets: tuple[PlanPreset, ...]
    #: 「미정」 목록 — 사람이 정해야 할 것(사유 문장). 계획표 밖 항목(상대 이동·SCENE 메모) 포함.
    unresolved: tuple[str, ...]
    #: 격자에 이미 있는 고정 번호와 그 칸 수 — 계획은 이것을 건드리지 않는다.
    kept: tuple[tuple[str, int], ...]
    #: 「이 카드 밖」 목록 — 값은 정해졌고 저장 줄만 아직 없다(사유 문장).
    deferred: tuple[str, ...] = ()
    #: 「감독이 고칠 값」 목록 — 앱이 기본값을 쓴 항목(무엇을 · 왜 · 어디서 고칠지).
    supervisor_fixes: tuple[str, ...] = ()


def _annotations_slug(song_title: object) -> str:
    """곡 제목 → 주석 파일 이름(영소문자·숫자·밑줄). 한글만 있는 제목은 빈 문자열이다."""
    return re.sub(r"[^0-9a-z]+", "_", str(song_title or "").casefold()).strip("_")


def load_preset_annotations(song_title: object, path: Path | None = None) -> dict[str, object]:
    """그 곡의 계획 주석 YAML을 읽는다. 주석 파일이 없는 곡이면 빈 주석(디머 계획만)이다 —
    색·방향을 지어내지 않는다. 읽기 실패는 숨기지 않고 그대로 올린다."""
    if path is None:
        slug = _annotations_slug(song_title)
        if not slug or not (_ANNOTATIONS_DIR / f"{slug}.yaml").exists():
            return {}
        path = _ANNOTATIONS_DIR / f"{slug}.yaml"
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return dict(document) if isinstance(document, Mapping) else {}


def _grid_cues(grid: Mapping[str, object]) -> list[tuple[str, object, bool, Mapping[str, object]]]:
    """(그룹 이름, 그룹 번호, 번호 확인 여부, 칸)을 트랙 순서대로 돌려준다."""
    rows: list[tuple[str, object, bool, Mapping[str, object]]] = []
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        group = str(track.get("group_name"))
        group_no = track.get("group_no")
        confirmed = bool(track.get("group_no_confirmed"))
        for cue in track.get("cues") or []:
            if isinstance(cue, Mapping):
                rows.append((group, group_no, confirmed, cue))
    return rows


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return tuple(seen)


def _preset_label(preset: PlanPreset) -> str:
    """계획표 아래 사유 줄의 머리 — 이름이 있으면 이름이다. 칸 하나의 왼쪽·오른쪽 색 후보는 이름이
    없으므로(감독이 정한다) 어느 칸의 어느 쪽인지로 적는다. 그 밖의 줄은 예전과 똑같다."""
    if preset.name or preset.split_side is None:
        return preset.name
    cell = preset.cells[0]
    return f"{cell.group_name} {cell.bar}마디 {_SPLIT_SIDE_LABEL[preset.split_side]} 칸"


def _outside_line(preset: PlanPreset) -> str:
    """저장하지 않는 줄이 「이 카드 밖」·「미정」 목록에 싣는 사유 문장 한 줄."""
    return (
        f"{_preset_label(preset)} {preset.value}(칸 {len(preset.cells)}개, 후보 "
        f"{preset.slot or '없음'}): {preset.hold}"
    )


def _dimmer_value_lines(
    group_nos: Sequence[int], value_percent: int, attributes: Sequence[str]
) -> tuple[str, ...]:
    """디머 값 줄 — 같은 값을 여러 그룹에 **한 선택**(``Group 4 + 7``)으로 낸다. 기존 묶음 꼴
    (cue_sheet 의 ``Group 11 + 12 ; Attribute 'Dimmer' At 90``)과 같다. 속성마다 한 줄이고,
    그룹이 하나면 ``Group N ; Attribute 'X' At V`` 꼴이 된다."""
    selection = "Group " + " + ".join(str(number) for number in group_nos)
    return tuple(f"{selection} ; Attribute '{attr}' At {value_percent}" for attr in attributes)


def _reserve_next(
    pool: PoolRead,
    first_free,
    *,
    policy: Mapping[str, object],
    grid: Mapping[str, object],
    reserved: Sequence[str],
) -> str | None:
    """콘솔이 쥔 빈 번호 중 다음 것을 고른다. 이 계획이 이미 고른 번호는 점유처럼 가린다
    — 같은 풀에서 두 번째 후보가 첫 번째와 겹치지 않게."""
    if pool is None:
        return None
    pool_no, children = pool
    taken = {
        int(number.partition(".")[2]): None
        for number in reserved
        if preset_pool_no(number) == pool_no
    }
    number, _reason = first_free(
        policy=policy, grid=grid, console_children=(pool_no, {**children, **taken})
    )
    return number


#: 격자가 기억하는 앱이 저장한 디머 프리셋 — 번호 -> {"percent", "attribute_group_nos"}.
#: 이름만으로는 내용이 같은지 모른다(같은 DIM-100 이 다른 그룹으로 저장됐을 수 있다).
_DIMMER_RECORD_KEY = "dimmer_presets"


def _reusable_dimmer_slot(
    grid: Mapping[str, object],
    dimmer_pool: PoolRead,
    name: str,
    percent: int,
    attribute_group_nos: Sequence[tuple[str, tuple[int, ...]]],
) -> str | None:
    """콘솔에 이미 있는 같은 디머 프리셋 번호(「pool.slot」) — 콘솔 이름이 ``name``(콘솔이 붙인
    「#숫자」 허용)이고, 격자의 저장 기록이 같은 값이며 이번에 필요한 속성·그룹을 전부 덮어야
    한다. 기록이 없는 번호(이 기록을 남기기 전 저장분)는 재사용하지 않는다."""
    if dimmer_pool is None:
        return None
    records = grid.get(_DIMMER_RECORD_KEY)
    if not isinstance(records, Mapping):
        return None
    pool_no, children = dimmer_pool
    for slot in sorted(children):
        number = f"{pool_no}.{slot}"
        if not same_console_name(children[slot], name):
            continue
        record = records.get(number)
        if not isinstance(record, Mapping) or record.get("percent") != percent:
            continue
        stored = {
            str(attr): set(nos)
            for attr, nos in record.get("attribute_group_nos") or []
            if isinstance(nos, list)
        }
        if all(set(nos) <= stored.get(attr, set()) for attr, nos in attribute_group_nos):
            return number
    return None


def _annotated_cells(
    raw: object,
    by_cell: Mapping[tuple[str, int], object],
    missing: list[tuple[str, int]],
) -> tuple[PlanCell, ...]:
    """주석의 칸 목록 → 격자에 실제로 있는 칸만.

    없는 칸은 조용히 버리지 않고 ``missing`` 에 모은다. 계획 끝에 한 줄로 알린다
    (`_missing_annotation_line`)."""
    cells: list[PlanCell] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, Mapping):
            continue
        group = str(item.get("group_name"))
        bar = int(item.get("bar"))  # type: ignore[arg-type]
        if (group, bar) in by_cell:
            cells.append(PlanCell(group, bar))
        else:
            missing.append((group, bar))
    return tuple(cells)


def _hold_through_lit_run(
    cells: Sequence[PlanCell],
    rows: Sequence[tuple[str, object, bool, Mapping[str, object]]],
    *,
    claimed: set[tuple[str, int]],
) -> tuple[PlanCell, ...]:
    """주석 방향 칸 뒤로 같은 줄이 켜진 채 이어지는 칸까지 그 방향을 잇는다.

    주석은 칸 하나에 위치를 정하지만, 자동 배치는 그 뒤 칸에 제 위치를 둔다. 둘 다 켜져 있으면
    무빙이 켜진 채 옮긴다(full2 D-09: 0마디 바닥 쪽 → 4마디 Home). 그래서 주석 위치는 처음 꺼지는
    칸(``cue_is_lit`` — 반영 단계 MIB 와 같은 판정)까지 머물고, 그 어둠 뒤에서 계획 위치로 간다.
    번호가 이미 있는 칸, 자동 배치가 위치를 정하지 않은 칸(손설계), 다른 주석이 잡은 칸
    (``claimed``)에서도 멈춘다."""
    cues_of: dict[str, list[Mapping[str, object]]] = {}
    for group, _no, _confirmed, cue in rows:
        bar = cue.get("bar")
        if isinstance(bar, int) and not isinstance(bar, bool):
            cues_of.setdefault(group, []).append(cue)
    held = list(cells)
    seen = {(cell.group_name, cell.bar) for cell in cells}
    for cell in cells:
        later = sorted(
            (cue for cue in cues_of.get(cell.group_name, ()) if int(cue["bar"]) > cell.bar),  # type: ignore[call-overload]
            key=lambda cue: int(cue["bar"]),  # type: ignore[call-overload]
        )
        for cue in later:
            key = (cell.group_name, int(cue["bar"]))  # type: ignore[call-overload]
            # 자동 배치가 위치를 정한 칸(``planned_position``)만 잇는다 — 감독이 손으로 설계한 칸
            # (상대 이동·새 자리 등)은 제 위치가 있으니 거기서 멈춘다.
            if (
                not cue_is_lit(cue)
                or cue.get("position_preset_no") is not None
                or not isinstance(cue.get("planned_position"), str)
            ):
                break
            if key in claimed and key not in seen:
                break
            if key not in seen:
                seen.add(key)
                held.append(PlanCell(*key))
    return tuple(held)


def _missing_annotation_line(missing: Sequence[tuple[str, int]]) -> str | None:
    """격자에 없는 주석 칸을 한 줄로 — 같은 칸은 한 번만, 그룹마다 마디를 모은다.

    새 배치(예: 워시는 구간마다 한 칸)는 주석이 가리키던 마디에 칸을 두지 않을 수 있다. 그 주석은
    이 계획에서 건너뛴다는 사실만 알린다(주석 파일은 고치지 않는다)."""
    cells = sorted(set(missing))
    if not cells:
        return None
    groups: dict[str, list[int]] = {}
    for group, bar in cells:
        groups.setdefault(group, []).append(bar)
    where = ", ".join(
        f"{group} {'·'.join(str(bar) for bar in bars)}마디" for group, bars in groups.items()
    )
    return (
        f"주석 칸 {len(cells)}개가 이 격자에 없어 건너뜀: {where} "
        "(그 마디에 칸이 없는 배치다 — 칸이 생기면 다시 쓴다)"
    )


def _grid_cue(grid: Mapping[str, object], cell: PlanCell) -> Mapping[str, object] | None:
    for group, _no, _confirmed, cue in _grid_cues(grid):
        if group == cell.group_name and cue.get("bar") == cell.bar:
            return cue
    return None


def _rgb_key(value: object) -> tuple[int, int, int] | None:
    """세 채널(0~100)이면 정수 튜플, 아니면 None. 계획 색·주석 색을 같은 키로 맞춘다."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    for channel in value:
        if isinstance(channel, bool) or not isinstance(channel, (int, float)):
            return None
        if not 0 <= channel <= 100:
            return None
    return (int(value[0]), int(value[1]), int(value[2]))


def _planned_base_names(annotations: Mapping[str, object]) -> dict[tuple[int, int, int], str]:
    """계획 색 RGB → 확정된 콘솔 영문 이름. 곡 주석의 콘솔 이름을 먼저 쓰고, 없으면
    표준 팔레트 이름(대문자). 이 표 밖의 색은 여기서 이름을 정하지 않고
    ``cell_direction.assign_color_names`` 가 가장 가까운 이름에 번호를 붙여 정한다."""
    names: dict[tuple[int, int, int], str] = {}
    for entry in annotations.get("colors") or []:
        if not isinstance(entry, Mapping):
            continue
        console = str(entry.get("console_name") or "").strip()
        rgb = _rgb_key(entry.get("rgb"))
        if rgb is None:
            rgb = _rgb_key(resolve_color_name(str(entry.get("name") or "")))
        if console and rgb is not None:
            names.setdefault(rgb, console)
    for label, rgb in COLOR_PALETTE_SEQUENCE:
        names.setdefault(rgb, label.upper())
    return names


def _reusable_color_slot(
    grid: Mapping[str, object],
    color_pool: PoolRead,
    rgb: tuple[int, int, int] | None,
    group: str,
) -> str | None:
    """콘솔에 이미 있는 같은 RGB·같은 그룹의 색 번호(「pool.slot」).
    격자가 그 번호의 RGB 를 기록하고 있고, 그 번호에 **이 그룹의 값이 담겨 있어야** 한다.

    - 저장할 때 담은 그룹이 기록돼 있으면(``preset_colors[...]["group"/"groups"]``) 그 그룹들만
      쓴다.
    - 기록이 없는 옛 번호는 누가 담겼는지 모른다 — 그 번호를 쓰는 칸이 있고 전부 이 그룹일
      때만 쓴다. 쓰는 칸이 없으면 쓰지 않는다(1차 전체 실행: 4.106 은 WASH-ALL 만 담겼는데,
      새 분석으로 격자가 비자 무빙 그룹들이 같은 RGB 라며 재사용해 색이 안 들어갈 수 있었다).
    빠진 그룹은 새 번호로 저장한다 — 다른 그룹을 기존 번호에 ``/Merge`` 로 더하는 줄은
    실기로 잰 적이 없다(t531 p3_c 는 같은 그룹 값 교체만 쟀다)."""
    if color_pool is None or rgb is None:
        return None
    pool_no, children = color_pool
    for slot in sorted(children):
        number = f"{pool_no}.{slot}"
        recorded = color_preset_rgb(grid, number)
        if recorded is None or not all(
            abs(a - b) < 0.5 for a, b in zip(recorded, rgb, strict=True)
        ):
            continue
        stored_for = color_preset_groups(grid, number)
        if stored_for is not None:
            # 대화 상자 대상은 손 입력일 수 있다 — 대소문자는 가리지 않는다.
            if group.casefold() in {name.casefold() for name in stored_for}:
                return number
            continue
        users = {
            str(track.get("group_name"))
            for track in grid.get("tracks") or []
            for cue in track.get("cues") or []
            if cue.get("color_preset_no") == number
        }
        if users == {group}:
            return number
    return None


def _prior_approval_source(grid: Mapping[str, object], cell: PlanCell) -> str | None:
    """칸에 이미 완전한 승인이 있었다면 그 출처. 승인 기록을 덮지 않고 덧붙이려고 본다."""
    cue = _grid_cue(grid, cell)
    if cue is None or check_evidence_approval(cue) is not None:
        return None
    evidence = cue.get("evidence")
    approval = evidence.get("approval") if isinstance(evidence, Mapping) else None
    source = approval.get("source") if isinstance(approval, Mapping) else None
    return str(source) if source else None


def _effect_signature(movement: Mapping[str, object]) -> tuple[object, ...]:
    """같은 움직임 값을 한 프리셋으로 묶는 키 — 모양·축·주기·위상 펼침."""
    axes = tuple(sorted(canonical_axes(movement.get("axes") or ())))
    return (
        movement.get("shape"),
        axes,
        movement.get("period_unit"),
        movement.get("period_value"),
        bool(movement.get("phase_spread")),
    )


def _period_of(movement: Mapping[str, object]) -> tuple[str, int] | None:
    """움직임 주기 — (단위, 수). 단위가 박·마디가 아니거나 수가 양의 정수가 아니면 None."""
    unit = movement.get("period_unit")
    value = movement.get("period_value")
    if unit not in ("beat", "bar"):
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    return str(unit), value


def _period_words(period: tuple[str, int]) -> str:
    """주기 한 쌍을 계획표 말로 — ``("beat", 2)`` 는 「박 2」."""
    unit, value = period
    return f"{'박' if unit == 'beat' else '마디'} {value}"


def _period_donor(
    rows: Sequence[tuple[str, object, bool, Mapping[str, object]]],
    *,
    group_name: str,
    bar: int,
) -> tuple[int, tuple[str, int]] | None:
    """주기가 빈 칸의 기본값 출처 — 같은 줄(그룹)에서 주기가 온전한 움직임 칸.

    앞쪽(마디가 작은 쪽)에서 가장 가까운 칸을 쓰고, 앞쪽에 없으면 가장 가까운 칸을 쓴다.
    돌려주는 것은 ``(그 칸의 마디, (주기 단위, 수))``. 같은 줄에 그런 칸이 없으면 None.
    """
    found: list[tuple[int, tuple[str, int]]] = []
    for other_group, _no, _confirmed, other in rows:
        other_bar = other.get("bar")
        movement = other.get("app_movement")
        if other_group != group_name or other_bar == bar:
            continue
        if not isinstance(other_bar, int) or isinstance(other_bar, bool):
            continue
        if not isinstance(movement, Mapping):
            continue
        period = _period_of(movement)
        if period is not None:
            found.append((other_bar, period))
    if not found:
        return None
    before = [entry for entry in found if entry[0] < bar]
    if before:
        return max(before, key=lambda entry: entry[0])
    return min(found, key=lambda entry: abs(entry[0] - bar))


def _effect_name(movement: Mapping[str, object]) -> str:
    """효과 프리셋 콘솔 이름 — ASCII 대문자. 예: ``WAVE PAN 2 BEAT``. 주기가 없으면 모양·축만."""
    shape = str(movement.get("shape") or "").upper()
    axes = "+".join(axis.upper() for axis in canonical_axes(movement.get("axes") or ()))
    period = _period_of(movement)
    if period is None:
        return f"{shape} {axes}"
    unit, value = period
    return f"{shape} {axes} {value} {unit.upper()}"


def _effect_value(movement: Mapping[str, object]) -> str:
    """계획표 값 칸 — 「효과 · 웨이브 · Pan · 박 2」. 화면은 이 머리말로 효과 줄을 알아본다.
    주기가 없으면 「주기 미정」(지어내지 않는다)."""
    shape = str(movement.get("shape") or "")
    axes = "·".join(canonical_axes(movement.get("axes") or ()))
    shape_word = _EFFECT_SHAPE_LABEL.get(shape, shape)
    period = _period_of(movement)
    period_text = "주기 미정" if period is None else _period_words(period)
    return f"효과 · {shape_word} · {axes} · {period_text}"


def _beats_per_cycle(movement: Mapping[str, object], beats_per_bar: int | None) -> float | None:
    """주기 한 바퀴의 박 수 — 박 단위면 그대로, 마디 단위면 박자표 분자를 곱한다. 모르면 None."""
    value = movement.get("period_value")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    if movement.get("period_unit") == "beat":
        return float(value)
    if movement.get("period_unit") == "bar" and beats_per_bar:
        return float(value * beats_per_bar)
    return None


def effect_plan_timing(timeline: object) -> tuple[float | None, int | None]:
    """움직임 효과 프리셋의 BPM·마디당 박 수 — 곡 데이터에서만 읽는다(지어내지 않는다).

    BPM 은 에미터와 같은 출처(``bar_map`` 의 타이밍)다. 못 읽으면 None 이고, 그러면 그 줄은
    「미정」으로 남는다.
    """
    bar_map = timeline.get("bar_map") if isinstance(timeline, Mapping) else None
    timing = build_song_timing_from_bar_map(bar_map if isinstance(bar_map, Mapping) else None)
    bpm = timing.bpm if timing is not None else None
    return bpm, beats_per_bar_from_timeline(timeline)


def _first_free_effect_slot(effect_pool: PoolRead, reserved: set[str]) -> tuple[int, int] | None:
    """효과 풀에서 빈 번호 하나. 콘솔 판독에 키가 없는 번호여야 한다(이름이 없어도
    있으면 찬 것). 격자·이번 계획이 이미 쓰는 번호는 뺀다. 가장 작은 번호(1부터).
    풀을 못 읽었으면 None."""
    if effect_pool is None:
        return None
    pool_no, children = effect_pool
    number = 1
    while f"{pool_no}.{number}" in reserved or number in children:
        number += 1
    return pool_no, number


#: 곡 격자에 효과 프리셋의 내용을 남기는 자리 — ``{"21.8": {group_no, signature, bpm}}``.
_EFFECT_RECORD_KEY = "preset_movements"


def _json_signature(signature: tuple[object, ...]) -> list[object]:
    """움직임 서명을 JSON 을 한 번 거친 모양(튜플 → 리스트)으로 — 저장했다 읽어도 같게 비교한다."""
    return json.loads(json.dumps(signature))


def _record_matches(
    record: object, group_no: object, signature: tuple[object, ...], bpm: float | None
) -> bool:
    if not isinstance(record, Mapping):
        return False
    if record.get("group_no") != group_no or record.get("signature") != _json_signature(signature):
        return False
    recorded_bpm = record.get("bpm")
    return recorded_bpm is None or bpm is None or abs(float(recorded_bpm) - bpm) < 0.01


def _reusable_effect_slot(
    grid: Mapping[str, object],
    effect_pool: PoolRead,
    *,
    name: str,
    group_name: str,
    group_no: object,
    movement: Mapping[str, object],
    bpm: float | None,
) -> str | None:
    """콘솔에 이미 있는 같은 이름·같은 내용의 앱이 만든 효과 프리셋 번호(「pool.slot」).

    색 재사용(``_reusable_color_slot``)과 같은 틀이다 — 격자가 그 번호의 이름(``preset_labels``)을
    기록하고 있고, 콘솔 풀에 그 번호가 아직 있으며, 내용이 같아야 한다. 내용은 격자의
    ``preset_movements`` 기록(그룹 번호·움직임 서명·BPM)으로 가른다. 기록이 없는 옛 프리셋은
    이름이 같고 위상 펼침이 없으며, 그 번호를 쓰는 칸이 전부 이 그룹일 때만 쓴다(다른 그룹이
    쓰면 그룹이 달라 재사용하지 않는다). 풀을 못 읽었으면 있는지 알 수 없어 재사용하지 않는다."""
    if effect_pool is None:
        return None
    pool_no, children = effect_pool
    signature = _effect_signature(movement)
    records = grid.get(_EFFECT_RECORD_KEY)
    for slot in sorted(children):
        number = f"{pool_no}.{slot}"
        if app_preset_label(grid, number) != name:
            continue
        record = records.get(number) if isinstance(records, Mapping) else None
        if record is not None:
            if _record_matches(record, group_no, signature, bpm):
                return number
            continue
        if movement.get("phase_spread"):
            continue
        users = {
            str(track.get("group_name"))
            for track in grid.get("tracks") or []
            for cue in track.get("cues") or []
            if cue.get("effect_preset_no") == number
        }
        if users == {group_name}:
            return number
    return None


def _movement_effect_presets(
    rows: Sequence[tuple[str, object, bool, Mapping[str, object]]],
    *,
    grid: Mapping[str, object],
    effect_pool: PoolRead,
    bpm: float | None,
    beats_per_bar: int | None,
    reserved: set[str],
    policy: Mapping[str, object] | None = None,
) -> tuple[tuple[PlanPreset, ...], tuple[str, ...], tuple[str, ...]]:
    """칸의 ``app_movement`` 마다 효과 프리셋 한 줄 — 같은 그룹·같은 움직임은 한 프리셋이다.

    돌려주는 것은 ``(프리셋들, 「미정」 사유들, 「감독이 고칠 값」들)``.
    번호 자리(풀 판독)나 그룹 번호가 없으면 「미정」이다 — 지어내지 않는다.
    저장 줄은 번호와 그룹이 다 정해진 줄에만 붙는다. 번호도 저장 줄이 붙는 줄에만 쓴다.
    실기 기록으로 열린 움직임(Tilt 웨이브)도 Pan 과 같이 효과 프리셋 후보다.
    주기가 빈 칸은 같은 줄의 주기 값을 기본으로 빌리고 「감독이 고칠 값」에 적는다.
    """
    buckets: dict[tuple[str, object, tuple[object, ...]], list[PlanCell]] = {}
    movements: dict[tuple[str, object, tuple[object, ...]], Mapping[str, object]] = {}
    confirmed_of: dict[tuple[str, object, tuple[object, ...]], bool] = {}
    # 주기가 빈 칸이 같은 줄의 주기 값을 빌린 기록 — 키 → [(칸 마디, 출처 마디, (단위, 수))]
    defaults: dict[
        tuple[str, object, tuple[object, ...]], list[tuple[int, int, tuple[str, int]]]
    ] = {}
    for group_name, group_no, confirmed, cue in rows:
        movement = cue.get("app_movement")
        bar = cue.get("bar")
        if not isinstance(movement, Mapping) or movement.get("shape") is None:
            continue
        if not isinstance(bar, int) or isinstance(bar, bool):
            continue
        # 이미 효과 번호를 받은 칸은 움직임(app_movement)을 그대로 두므로 다시 후보로 세지 않는다 —
        # 계획을 다시 돌려도 같은 칸에 프리셋이 겹으로 생기지 않는다.
        if cue.get("effect_preset_no") is not None:
            continue
        # 실기 기록으로 열린 움직임(MOVER-D Tilt 웨이브)도 효과 프리셋으로 만든다. 예전엔 ④(효과
        # 프리셋 리콜)가 미확인이라 바꾸면 새로 막혔지만, ④는 2026-10-16 실기 통과다(리드 지시).
        donor = None
        if _period_of(movement) is None:
            donor = _period_donor(rows, group_name=group_name, bar=bar)
            if donor is not None:
                movement = {**movement, "period_unit": donor[1][0], "period_value": donor[1][1]}
        key = (group_name, group_no, _effect_signature(movement))
        buckets.setdefault(key, []).append(PlanCell(group_name=group_name, bar=bar))
        movements.setdefault(key, movement)
        confirmed_of[key] = bool(confirmed) and confirmed_of.get(key, True)
        if donor is not None:
            defaults.setdefault(key, []).append((bar, donor[0], donor[1]))

    presets: list[PlanPreset] = []
    unresolved: list[str] = []
    fixes: list[str] = []
    for key, cells in buckets.items():
        group_name, group_no, _signature = key
        movement = movements[key]
        name = _effect_name(movement)
        placement = _first_free_effect_slot(effect_pool, reserved)
        bundle: tuple[str, ...] | None = None
        reason: str | None = None
        reusable: str | None = None
        # 그룹 번호는 확인된 것만 쓴다(디머와 같은 규칙). 확인 안 됐으면 저장 줄을 붙이지 않는다.
        if not isinstance(group_no, int) or isinstance(group_no, bool) or not confirmed_of[key]:
            reason = f"그룹 번호가 확인되지 않음: {group_name}"
        elif _period_of(movement) is None:
            reason = "칸에 움직임 주기(박 또는 마디 수)가 없다 — 감독이 고칠 값"
        elif (
            reusable := _reusable_effect_slot(
                grid,
                effect_pool,
                name=name,
                group_name=group_name,
                group_no=group_no,
                movement=movement,
                bpm=bpm,
            )
        ) is not None:
            pass  # 콘솔에 같은 프리셋이 이미 있다 — 새로 만들지 않는다.
        elif placement is None:
            reason = _EFFECT_POOL_HOLD
        else:
            bundle, reason = movement_effect_store_commands(
                movement,
                group_no=group_no,
                preset_pool=placement[0],
                preset=placement[1],
                label=name,
                bpm=bpm,
                beats_per_bar=beats_per_bar,
                speed_master=speed_master_of(policy or {}),
            )
        # 번호는 저장 줄이 붙는 줄에만 쓴다 — 못 붙는 줄이 번호를 먼저 잡으면 다음 줄 번호가 밀린다.
        slot: str | None = reusable
        if reusable is None and bundle is not None and reason is None and placement is not None:
            slot = f"{placement[0]}.{placement[1]}"
            reserved.add(slot)
        ready = slot is not None
        presets.append(
            PlanPreset(
                kind="effect",
                value=_effect_value(movement),
                name=name,
                slot=slot,
                cells=tuple(cells),
                groups=(group_name,),
                ready=ready,
                hold=None if ready else (reason or _EFFECT_POOL_HOLD),
                store=bundle if ready and reusable is None else None,
                reused=reusable is not None,
                effect_record=(group_no, _effect_signature(movement), bpm) if ready else None,
            )
        )
        if not ready:
            unresolved.append(
                f"{group_name} 움직임 효과 프리셋({name}): {reason or _EFFECT_POOL_HOLD}"
            )

    if presets:
        pool_text = (
            f"풀 {effect_pool[0]}({MOVEMENT_EFFECT_POOL_NAME})"
            if effect_pool is not None
            else f"풀 {MOVEMENT_EFFECT_POOL_NAME}"
        )
        fixes.append(
            f"효과 프리셋 번호대 — {pool_text}은 preset_pools.yaml 에 선언돼 있지 않다. "
            "빈 번호는 콘솔 판독으로 골랐다. 감독이 고칠 값: 번호대 선언 여부와 번호"
        )
        # 빌린 주기는 줄 머리를 프리셋 이름으로 해서 그 줄에 붙인다.
        for key, borrowed in defaults.items():
            for cell_bar, donor_bar, period in borrowed:
                fixes.append(
                    f"{_effect_name(movements[key])} — {key[0]} {cell_bar}마디: "
                    f"움직임 주기가 칸에 없어 {donor_bar}마디의 주기({_period_words(period)})를 "
                    "기본으로 썼다. 감독이 고칠 값: 주기 단위·수"
                )
        for key in buckets:
            movement = movements[key]
            cycle = _beats_per_cycle(movement, beats_per_bar)
            if bpm is not None and cycle:
                master = speed_master_of(policy or {})
                how = (
                    f"At Speed {bpm / cycle:g} 로 프리셋에 굽는다(SpeedMaster 아님 — "
                    "preset_pools.yaml 에 speed_master 가 없다)"
                    if master is None
                    else f"스피드 마스터 {master} 에 묶는다(Master 3.{master} At BPM {bpm:g} · "
                    f"At SpeedMaster {master} · At Measure {cycle:g})"
                )
                fixes.append(
                    f"움직임 속도 — {_effect_name(movement)}: 박 {cycle:g} 주기를 {how}. "
                    "감독이 고칠 값: 속도 기준"
                )
            if movement.get("phase_spread") is None:
                fixes.append(
                    f"위상 펼침 — {_effect_name(movement)}: 칸에 값이 없어 펼치지 않는다. "
                    "감독이 고칠 값: 위상 펼침 여부"
                )
        fixes.append(
            "실콘솔 판정 — 효과 프리셋을 쓰는 칸은 M1 ④ 프로브가 「통과」해야 "
            "풀린다(④ = 효과 프리셋 SM15·Measure). "
            "프리셋을 만든 것만으로는 풀리지 않는다."
        )
    return tuple(presets), tuple(unresolved), tuple(fixes)


def _planned_color_presets(
    rows: Sequence[tuple[str, object, bool, Mapping[str, object]]],
    *,
    grid: Mapping[str, object],
    annotations: Mapping[str, object],
    color_pool: PoolRead,
    policy: Mapping[str, object],
    presets: list[PlanPreset],
    reserved: list[str],
    unresolved: list[str],
    fixes: list[str],
) -> None:
    """자동 배치가 칸에 실은 계획 색(``planned_color``)을 색 후보로 센다. 결과는 ``presets`` 에
    새 후보·재사용으로 더하거나, 같은 그룹의 주석 색 후보에 칸을 보탠다.

    - 키는 RGB. 같은 RGB 는 한 프리셋에 쓰는 그룹을 전부 담는다(2차 전체 실행 E-08 — 그룹마다
      따로 저장해 색 18개·고유 RGB 6개였다). 저장 줄은 ``Group 10 + 7`` 한 선택이다.
    - 같은 RGB 의 주석 색 후보가 이 그룹을 담고 있으면(재사용) 그 후보에 칸을 보탠다. 저장 줄을
      기다리는 주석 후보면 남은 그룹을 그 후보에 더한다(한 프리셋).
    - 콘솔에 같은 RGB 이고 이 그룹을 담아 저장한 번호가 있으면 그 번호를 재사용한다(저장 줄 없음,
      2차 전체 실행 I-08). 번호가 그룹마다 다를 수 있다 — 칸은 자기 그룹이 담긴 번호를 부른다.
    - 재사용할 번호가 없는 그룹만 모아 콘솔 색 풀의 빈 번호 하나에 새 저장 후보를 낸다. 이름은 색
      이름이다. 색 이름은 곡 주석의 콘솔 이름 → 칸의 방향 값에 실린 이름 → 팔레트 표 → 가장 가까운
      이름(+번호) 순으로 정해서 이름이 빈 후보가 없다(``assign_color_names``).
    - 번호가 이미 있는 칸, 칸 쪽 색(split), 살아 있는 주석 색 후보가 잡은 칸은 건드리지 않는다.
    """
    base_names = _planned_base_names(annotations)
    # 곡 주석 색이 잡은 칸은 그 후보가 지금 저장 줄을 기다리든(색 풀 판독 전이라) 보류 중이든
    # 주석 색이 이긴다 — 계획 색이 이름을 얻는 이제는 주석 칸에 계획 색 후보가 겹쳐 서면 안 된다.
    taken = {
        (cell.group_name, cell.bar)
        for preset in presets
        if preset.kind == "color"
        for cell in preset.cells
    }
    #: 칸의 방향 값이 이미 들고 있는 색 이름 — 라벨·무대와 프리셋 이름이 같은 이름을 쓰게 한다.
    direction_names: dict[tuple[int, int, int], str] = {}
    #: RGB → 그룹 → 칸(첫 등장 순). 그룹 순서가 저장 선택(``Group a + b``)의 순서다.
    cells_of: dict[tuple[int, int, int], dict[str, list[PlanCell]]] = {}
    # 계획 색이 있는 칸은 역할과 무관하게 후보에 센다. 컬러 채널이 있는지는 역할로 짐작하지 않고
    # 저장 단계(``preset_plan_store``)가 장비 채널을 읽어 가른다 — 없으면 그 후보는 사유와 함께
    # 「미정」으로 남는다(리드 지시 2026-10-17, 인수 C-06).
    for group, _no, _confirmed, cue in rows:
        bar = cue.get("bar")
        if not isinstance(bar, int) or isinstance(bar, bool):
            continue
        if cue.get("color_preset_no") is not None or (group, bar) in taken:
            continue
        if validate_cell_split(cue.get("split"), group_name=group, bar=bar) is not None:
            continue
        rgb = _rgb_key(cue.get("planned_color"))
        if rgb is None:
            continue
        direction = cue.get("direction")
        color = direction.get("color") if isinstance(direction, Mapping) else None
        hinted = color.get("name") if isinstance(color, Mapping) else None
        if isinstance(hinted, str) and hinted.strip() and _rgb_key(color.get("rgb")) == rgb:
            direction_names.setdefault(rgb, hinted.strip())
        cells_of.setdefault(rgb, {}).setdefault(group, []).append(
            PlanCell(group_name=group, bar=bar)
        )

    # 이 계획이 다루는 색 전부의 이름을 한 번에 정한다 — 이름 없는 색은 없고 색마다 이름이 다르다.
    color_names = assign_color_names(
        set(cells_of),
        preferred={rgb: base_names[rgb] for rgb in cells_of if rgb in base_names},
        hints=direction_names,
    )

    for rgb, by_group in cells_of.items():
        channels = " ".join(str(channel) for channel in rgb)
        value = f"RGB {channels}"
        name = color_names[rgb]
        remaining: list[str] = []
        for group, group_cells in by_group.items():
            # 같은 색의 주석 후보가 이 그룹을 이미 담고 있다 — 그 번호에 칸을 보탠다(한 프리셋).
            annotated = next(
                (
                    index
                    for index, preset in enumerate(presets)
                    if preset.kind == "color"
                    and (preset.deferred or preset.reused)
                    and group in preset.groups
                    and _rgb_key(preset.rgb) == rgb
                ),
                None,
            )
            if annotated is None:
                remaining.append(group)
                continue
            current = presets[annotated]
            presets[annotated] = replace(current, cells=current.cells + tuple(group_cells))
        # 그룹마다 그 그룹을 담아 저장한 번호가 있으면 재사용한다 — 번호별로 칸을 모은다.
        reuse_groups: dict[str, list[str]] = {}
        for group in remaining:
            reused_slot = _reusable_color_slot(grid, color_pool, rgb, group)
            if reused_slot is not None:
                reuse_groups.setdefault(reused_slot, []).append(group)
        for reused_slot, groups in reuse_groups.items():
            presets.append(
                PlanPreset(
                    kind="color",
                    value=value,
                    name=name,
                    slot=reused_slot,
                    cells=tuple(cell for group in groups for cell in by_group[group]),
                    groups=tuple(groups),
                    ready=True,
                    hold=None,
                    rgb=rgb,
                    reused=True,
                )
            )
        reused_any = {group for groups in reuse_groups.values() for group in groups}
        remaining = [group for group in remaining if group not in reused_any]
        if not remaining:
            continue
        cells = tuple(cell for group in remaining for cell in by_group[group])
        # 저장 줄을 기다리는 같은 색 주석 후보가 있으면 남은 그룹을 그 후보에 더한다(한 프리셋).
        pending = next(
            (
                index
                for index, preset in enumerate(presets)
                if preset.kind == "color"
                and preset.deferred
                and not preset.reused
                and _rgb_key(preset.rgb) == rgb
            ),
            None,
        )
        if pending is not None:
            current = presets[pending]
            presets[pending] = replace(
                current,
                cells=current.cells + cells,
                groups=_unique((*current.groups, *remaining)),
            )
            continue
        holds: list[str] = []
        slot: str | None = None
        if color_pool is None:
            holds.append("색 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
        else:
            slot = _reserve_next(
                color_pool,
                first_free_base_color_number,
                policy=policy,
                grid=grid,
                reserved=reserved,
            )
            if slot is None:
                holds.append("콘솔 색 풀에 빈 번호가 없음")
            else:
                reserved.append(slot)
        candidate = not holds
        if candidate:
            holds.append(_COLOR_STORE_HOLD)
            fixes.append(
                f"{name} RGB {channels}: 자동 배치가 칸에 실은 계획 색(팔레트 값). "
                "감독이 고칠 값: 실기 색이 다르면 팔레트 값을 고친다."
            )
        presets.append(
            PlanPreset(
                kind="color",
                value=value,
                name=name,
                slot=slot,
                cells=cells,
                groups=tuple(remaining),
                ready=False,
                hold="; ".join(holds),
                deferred=candidate,
                rgb=rgb,
            )
        )


#: 격자가 기억하는 앱이 저장한 위치 프리셋 — 번호 -> {"group", "aim", "value"}.
#: ``aim`` 은 기본 위치 이름(주석 바닥 점이면 None), ``value`` 는 계획표의 값 글자(바닥 점의
#: 대략 목표가 여기 담긴다). 이름만으로는 같은 조준인지 모른다.
_POSITION_RECORD_KEY = "preset_positions"


def _position_record(group: str, aim: str | None, value: str) -> dict[str, object]:
    return {"group": group, "aim": aim, "value": value}


def _reusable_position_slot(
    grid: Mapping[str, object],
    position_pool: PoolRead,
    name: str,
    record: Mapping[str, object],
) -> str | None:
    """콘솔에 이미 있는 같은 위치 번호(「pool.slot」) — 콘솔 이름이 ``name``(콘솔이 붙인
    「#숫자」 허용)이고, 격자의 저장 기록이 ``record``(그룹·기본 위치·값)와 같아야 한다. 기록이
    없는 번호(이 기록을 남기기 전 저장분)는 재사용하지 않는다(3차 전체 실행 I-08)."""
    if position_pool is None:
        return None
    records = grid.get(_POSITION_RECORD_KEY)
    if not isinstance(records, Mapping):
        return None
    pool_no, children = position_pool
    for slot in sorted(children):
        number = f"{pool_no}.{slot}"
        if records.get(number) == record and same_console_name(children[slot], name):
            return number
    return None


def _planned_position_presets(
    rows: Sequence[tuple[str, object, bool, Mapping[str, object]]],
    *,
    grid: Mapping[str, object],
    position_pool: PoolRead,
    policy: Mapping[str, object],
    presets: list[PlanPreset],
    reserved: list[str],
    fixes: list[str],
) -> None:
    """자동 배치가 무빙 칸에 정한 계획 위치(``planned_position``)를 위치 프리셋 후보로 센다.

    - 키는 (그룹, 위치 이름). 위치 저장도 한 그룹의 장비만 고른다 — 2.31·2.32 처럼 그룹마다 따로다.
    - 번호가 이미 있는 칸과 살아 있는 위치 후보(주석 바닥 점)가 잡은 칸은 건드리지 않는다.
    - 후보는 값이 정해진 「이 카드 밖」이다. 저장 줄은 콘솔 판독 뒤 ``preset_plan_store`` 가 붙인다.
    - 이름은 「이름 그룹」(예: ``CENTER MOVER-U``). 후보마다 「감독이 고칠 값」 한 줄을 싣는다.
    """
    taken = {
        (cell.group_name, cell.bar)
        for preset in presets
        if preset.kind == "position" and (preset.deferred or preset.ready)
        for cell in preset.cells
    }
    movers = {
        str(track.get("group_name"))
        for track in grid.get("tracks") or []
        if track.get("layer_role") == "mover"
    }
    order: list[tuple[str, str]] = []
    cells_of: dict[tuple[str, str], list[PlanCell]] = {}
    for group, _no, _confirmed, cue in rows:
        look = cue.get("planned_position")
        bar = cue.get("bar")
        if not isinstance(look, str) or not isinstance(bar, int) or isinstance(bar, bool):
            continue
        if group not in movers or cue.get("position_preset_no") is not None:
            continue
        if (group, bar) in taken:
            continue
        key = (group, look)
        if key not in cells_of:
            cells_of[key] = []
            order.append(key)
        cells_of[key].append(PlanCell(group_name=group, bar=bar))

    for group, look in order:
        cells = tuple(cells_of[(group, look)])
        name = f"{look.upper()} {group}"
        value = f"{_POSITION_LABEL_KO.get(look, look)} (계획)"
        if look not in MOVER_POSITION_LADDER:
            # 「이 카드 밖」·「미정」 목록은 뒤의 공통 줄이 사유와 함께 싣는다.
            presets.append(
                PlanPreset(
                    kind="position",
                    value=value,
                    name=name,
                    slot=None,
                    cells=cells,
                    groups=(group,),
                    ready=False,
                    hold="계획 위치 이름이 기본 위치 사다리에 없음",
                )
            )
            continue
        reused = _reusable_position_slot(
            grid, position_pool, name, _position_record(group, look, value)
        )
        if reused is not None:
            # 콘솔에 이미 있는 번호를 쓴다 — 저장 줄 없이 칸만 그 번호를 가리킨다(「재사용」).
            presets.append(
                PlanPreset(
                    kind="position",
                    value=value,
                    name=name,
                    slot=reused,
                    cells=cells,
                    groups=(group,),
                    ready=True,
                    hold=None,
                    aim=look,
                    reused=True,
                )
            )
            continue
        holds: list[str] = []
        slot: str | None = None
        if position_pool is None:
            holds.append("위치 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
        else:
            slot = _reserve_next(
                position_pool,
                first_free_base_position_number,
                policy=policy,
                grid=grid,
                reserved=reserved,
            )
            if slot is None:
                holds.append("콘솔 위치 풀에 빈 번호가 없음")
            else:
                reserved.append(slot)
        candidate = not holds
        if candidate:
            holds.append(_POSITION_STORE_HOLD)
            fixes.append(
                f"{name} — 자동 배치가 무빙 칸에 정한 계획 위치({_POSITION_LABEL_KO[look]}, "
                f"기본 위치 {look}). 감독이 고칠 값: 실기 조준이 다르면 위치 이름을 고른다."
            )
        presets.append(
            PlanPreset(
                kind="position",
                value=value,
                name=name,
                slot=slot,
                cells=cells,
                groups=(group,),
                ready=False,
                hold="; ".join(holds),
                deferred=candidate,
                aim=look,
            )
        )


def build_preset_plan(
    grid: Mapping[str, object],
    *,
    annotations: Mapping[str, object],
    policy: Mapping[str, object],
    dimmer_pool: PoolRead,
    color_pool: PoolRead,
    position_pool: PoolRead,
    dimmer_attributes: Mapping[str, Sequence[str]],
    effect_pool: PoolRead = None,
    bpm: float | None = None,
    beats_per_bar: int | None = None,
) -> LoveAttackPlan:
    """격자 칸에서 새로 만들 프리셋 계획을 만든다(콘솔 무접촉, 순수 함수).

    - 디머: 칸의 ``brightness.value_percent``를 값으로 묶는다(같은 값 = 한 프리셋).
    - 색·방향: ``annotations``(``preset_plan.yaml``)가 칸에 붙인 색·방향만 쓴다.
    - 칸 하나의 왼쪽·오른쪽 색: 칸의 ``split`` 에서 색이 정해진 쪽마다 후보 한 줄(``split_side``)을
      낸다. 색이 비어 있는 쪽은 후보 없이 ``unresolved`` 한 줄이다. 모양이 틀린 ``split`` 은
      ``ValueError``(그룹·마디를 말한다)로 올린다.
    - 번호: 풀 판독(``dimmer_pool``·``color_pool``·``position_pool``)에서 빈 것만 고른다.
    - 이미 있는 번호는 ``kept``로 세기만 하고 건드리지 않는다.
    - 앱이 기본값을 쓴 항목은 ``supervisor_fixes``(「감독이 고칠 값」)에 모은다.
    """
    rows = _grid_cues(grid)
    by_cell: dict[tuple[str, int], tuple[object, bool]] = {}
    for group, group_no, confirmed, cue in rows:
        if isinstance(cue.get("bar"), int):
            by_cell[(group, int(cue["bar"]))] = (group_no, confirmed)  # type: ignore[index]

    unresolved: list[str] = []
    missing_cells: list[tuple[str, int]] = []
    deferred_lines: list[str] = []
    fixes: list[str] = []
    presets: list[PlanPreset] = []
    reserved: list[str] = []

    # -- 밝기 결정: 리드가 정한 칸 밝기(brightness_decisions)
    brightness_notes: dict[tuple[str, int], str] = {}
    for entry in annotations.get("brightness_decisions") or []:
        if not isinstance(entry, Mapping):
            continue
        for cell in _annotated_cells(entry.get("cells"), by_cell, missing_cells):
            brightness_notes[(cell.group_name, cell.bar)] = str(entry.get("note") or "").strip()

    # -- 디머: 칸의 value_percent 와 그룹의 밝기 속성 구성으로 묶는다(첫 등장 순) ------
    # 2차 전체 실행 G-13 — 그룹 8개(3·10 포함)를 한 프리셋에 저장하면 콘솔 프리셋에 ``Dimmer2`` 가
    # 담기지 않았다. 실기(2026-10-17): 3·10 이 섞인 1.903·1.904·1.905 는 빠짐, 3·10 이 없는 1.907 과
    # ``Dimmer2`` 를 가진 그룹만 담은 1.906 은 담김. 콘솔 안의 이유는 모른다 — 확인된 꼴(1.906)대로
    # 밝기 속성 구성이 다르면 프리셋을 나눈다.
    uses: dict[tuple[int, tuple[str, ...]], list[tuple[str, object, bool, int]]] = {}
    for group, group_no, confirmed, cue in rows:
        brightness = cue.get("brightness")
        if not isinstance(brightness, Mapping) or brightness.get("mode") != "value":
            continue
        percent = brightness.get("value_percent")
        if percent is None:
            continue
        if isinstance(percent, bool) or not isinstance(percent, int):
            unresolved.append(f"{group} {cue.get('bar')}마디: 밝기 값 {percent!r}은 정수 %가 아님")
            continue
        signature = tuple(dimmer_attributes.get(group) or ()) or (_DEFAULT_DIMMER_ATTRIBUTE,)
        uses.setdefault((percent, signature), []).append(
            (group, group_no, confirmed, int(cue["bar"]))  # type: ignore[arg-type]
        )

    for (percent, signature), uses_of_value in uses.items():
        # 밝기 속성이 하나면 「DIM-100」, 더 있으면 그 속성 이름을 붙인다(「DIM-100 DIMMER2」).
        name = " ".join(
            (f"{_DIMMER_NAME_PREFIX}-{percent}", *(attr.upper() for attr in signature[1:]))
        )
        cells = tuple(PlanCell(group, bar) for group, _no, _c, bar in uses_of_value)
        groups = _unique(group for group, _no, _c, _bar in uses_of_value)
        holds: list[str] = []
        if dimmer_pool is None:
            holds.append("디머 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
        # 그룹 번호는 확인된 것만 쓴다(지어내지 않는다). 확인 안 된 그룹이 있으면 보류한다.
        confirmed_no: dict[str, int] = {}
        for group, raw_no, confirmed, _bar in uses_of_value:
            if not confirmed or not isinstance(raw_no, int) or isinstance(raw_no, bool):
                continue
            if raw_no > 0:
                confirmed_no.setdefault(group, raw_no)
        unconfirmed = [group for group in groups if group not in confirmed_no]
        if unconfirmed:
            holds.append(f"그룹 번호가 확인되지 않음: {', '.join(unconfirmed)}")
        group_nos = tuple(confirmed_no[group] for group in groups if group in confirmed_no)
        # 디머 속성: 판독값을 쓴다. 못 얻은 그룹은 기본 이름으로 둔다(감독이 고칠 값).
        attributes_of: dict[str, tuple[str, ...]] = {}
        defaulted: list[str] = []
        for group in groups:
            read = tuple(dimmer_attributes.get(group) or ())
            if read:
                attributes_of[group] = read
            else:
                attributes_of[group] = (_DEFAULT_DIMMER_ATTRIBUTE,)
                defaulted.append(group)
        attributes = _unique(attr for group in groups for attr in attributes_of[group])
        # 속성마다 그 속성을 가진 그룹만 고른다 — 기종의 밝기 속성을 다 열되, 없는 기종을 같은
        # 선택에 넣지 않는다(``Group 12 ; Attribute 'Dimmer2'`` 꼴만 실측됨, t548·t520).
        attribute_group_nos = tuple(
            (
                attr,
                tuple(
                    confirmed_no[group]
                    for group in groups
                    if group in confirmed_no and attr in attributes_of[group]
                ),
            )
            for attr in attributes
        )
        # 전체 실행 E-10·I-08 — 콘솔에 같은 이름(콘솔이 붙인 「#숫자」 허용)·같은 값·같은 그룹을
        # 덮는 디머 프리셋이 있고 격자가 그 저장을 기록하고 있으면 다시 저장하지 않고 재사용한다.
        reused_slot = (
            _reusable_dimmer_slot(grid, dimmer_pool, name, percent, attribute_group_nos)
            if not holds
            else None
        )
        if reused_slot is not None:
            slot: str | None = reused_slot
        else:
            slot = _reserve_next(
                dimmer_pool,
                first_free_base_dimmer_number,
                policy=policy,
                grid=grid,
                reserved=reserved,
            )
            if slot is not None:
                reserved.append(slot)
        ready = not holds and slot is not None
        if ready and len(groups) > 1:
            selection = " + ".join(str(number) for number in group_nos)
            fixes.append(
                f"{name} 다중 그룹 저장 — 그룹 {len(groups)}개를 한 선택(Group {selection})으로 "
                "한 번에 저장한다(같은 값 = 한 프리셋). 감독이 고칠 값: 그룹마다 따로 저장하려면 "
                "이 줄을 나눈다."
            )
        if ready:
            for group in defaulted:
                fixes.append(
                    f"{name} 의 그룹 '{group}' 디머 속성을 콘솔 판독에서 얻지 못해 기본 "
                    f"'{_DEFAULT_DIMMER_ATTRIBUTE}' 으로 저장한다. "
                    "감독이 고칠 값: 실기 속성 이름을 확인한다."
                )
        presets.append(
            PlanPreset(
                kind="dimmer",
                value=f"{percent}%",
                name=name,
                slot=slot,
                cells=cells,
                groups=groups,
                ready=ready,
                hold=None if ready else "; ".join(holds),
                value_percent=percent,
                group_no=group_nos[0] if len(group_nos) == 1 else None,
                attributes=attributes if ready else (),
                group_nos=group_nos if ready else (),
                attribute_group_nos=attribute_group_nos if ready else (),
                reused=reused_slot is not None,
            )
        )
        # 밝기 결정이 붙은 칸을 쓰는 디머 줄은 「감독이 고칠 값」으로 드러낸다(줄마다 한 번).
        for note in _unique(
            brightness_notes[(cell.group_name, cell.bar)]
            for cell in cells
            if (cell.group_name, cell.bar) in brightness_notes
        ):
            fixes.append(
                f"{name} 밝기 {percent}% — {note} 감독이 고칠 값: 실기와 다르면 칸 밝기를 고친다."
            )

    # -- 색: 칸에 붙인 색 이름. RGB 는 주석 → 색 표 순, 없으면 「미정」
    for entry in annotations.get("colors") or []:
        if not isinstance(entry, Mapping):
            continue
        cells = _annotated_cells(entry.get("cells"), by_cell, missing_cells)
        groups = _unique(cell.group_name for cell in cells)
        name = str(entry.get("console_name") or "")
        label = str(entry.get("name") or "")
        rgb = entry.get("rgb")
        from_palette = rgb is None
        if rgb is None:
            rgb = resolve_color_name(label)  # 표준 팔레트 이름으로만 찾는다(없으면 None)
        # 같은 RGB 이고 이 그룹들을 전부 담은 색 번호가 콘솔에 이미 있으면 새로 잡지 않고 그 번호를
        # 쓴다. 그룹마다 번호가 다르면 한 번호로 묶을 수 없으니 새로 저장한다.
        reused = None
        if cells:
            slots = {_reusable_color_slot(grid, color_pool, _rgb_key(rgb), g) for g in groups}
            if len(slots) == 1:
                (reused,) = slots
        # 칸이 없는 색은 번호를 잡지 않는다 — 쓰지 않을 빈 번호를 점유하지 않으려고.
        slot = reused
        if slot is None and cells:
            slot = _reserve_next(
                color_pool,
                first_free_base_color_number,
                policy=policy,
                grid=grid,
                reserved=reserved,
            )
            if slot is not None:
                reserved.append(slot)
        holds = []
        if not cells:
            holds.append("칸 미정 — 이 색을 쓸 격자 칸이 주석에 없다(감독이 칸 배정을 정한다)")
        if color_pool is None:
            holds.append("색 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
        if rgb is None:
            holds.append(f"RGB 미정 — {str(entry.get('note') or '').strip()}")
            presets.append(
                PlanPreset(
                    kind="color",
                    value="RGB 미정",
                    name=name,
                    slot=slot,
                    cells=cells,
                    groups=groups,
                    ready=False,
                    hold="; ".join(holds),
                )
            )
            continue
        channels = " ".join(str(channel) for channel in rgb)
        if reused is not None:
            # 콘솔에 이미 있는 번호를 쓴다 — 저장 줄 없이 칸만 그 번호를 가리킨다(「재사용」).
            presets.append(
                PlanPreset(
                    kind="color",
                    value=f"RGB {channels}",
                    name=name,
                    slot=reused,
                    cells=cells,
                    groups=groups,
                    ready=True,
                    hold=None,
                    rgb=tuple(rgb),
                    reused=True,
                )
            )
            continue
        # 칸·번호가 다 있으면 저장 후보다 — 저장 줄은 콘솔 판독 뒤 `preset_plan_store` 가 붙인다.
        # 하나라도 비면 그 사유가 보류 이유이고 「미정」이다.
        candidate = not holds
        if candidate:
            holds.append(_COLOR_STORE_HOLD)
        if from_palette:
            fixes.append(
                f"{name} RGB {channels}: 「{label}」 표준 슬롯 기본값. "
                "감독이 고칠 값: 실기 색이 다르면 색 표에서 바꾼다."
            )
        elif entry.get("director_tunable") is True:
            # 앱이 고른 기본값은 「감독이 고칠 값」으로 드러낸다(주석에 적은 값이어도).
            fixes.append(
                f"{name} RGB {channels}: 「{label}」 앱이 고른 기본값. "
                "감독이 고칠 값: 실기 색이 다르면 주석 파일의 rgb 를 고친다."
            )
        presets.append(
            PlanPreset(
                kind="color",
                value=f"RGB {channels}",
                name=name,
                slot=slot,
                cells=cells,
                groups=groups,
                ready=False,
                hold="; ".join(holds),
                deferred=candidate,
                rgb=tuple(rgb),
            )
        )

    # -- 자동 배치가 칸에 실은 계획 색: 주석 색 뒤에 그룹·RGB 마다 색 후보를 센다
    _planned_color_presets(
        rows,
        grid=grid,
        annotations=annotations,
        color_pool=color_pool,
        policy=policy,
        presets=presets,
        reserved=reserved,
        unresolved=unresolved,
        fixes=fixes,
    )

    # -- 칸 하나의 왼쪽·오른쪽 따로 색: 색이 정해진 쪽마다 색 후보 한 줄 ------------------
    # 주석 색 뒤에 번호를 잡는다(주석 쪽 번호가 그대로 유지된다). 콘솔 이름은 감독이 정하므로
    # 이름은 비우고, 저장·칸 참조는 하지 않는다(`split_side` — `save_commands`·
    # `apply_plan_references` 가 건너뛴다).
    for group, _no, _confirmed, cue in rows:
        split = validate_cell_split(cue.get("split"), group_name=group, bar=cue.get("bar"))
        if split is None:
            continue
        bar = int(cue["bar"])  # type: ignore[arg-type]
        for side in CELL_SPLIT_SIDES:
            color = split[side]["color"]
            if color is None or not color.strip():
                unresolved.append(
                    f"{group} {bar}마디 {_SPLIT_SIDE_LABEL[side]} 칸 색 미정 — 감독이 정한다"
                )
                continue
            slot = _reserve_next(
                color_pool,
                first_free_base_color_number,
                policy=policy,
                grid=grid,
                reserved=reserved,
            )
            if slot is not None:
                reserved.append(slot)
            holds = [_SPLIT_NAME_HOLD]
            if color_pool is None:
                holds.append("색 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
            rgb = cell_split_side_rgb(color)
            if rgb is None:
                holds.append(f"RGB 미정 — 「{color}」은(는) 표준 색 표에 없어 RGB 를 알 수 없음")
            else:
                holds.append(_COLOR_PATH_HOLD)
            presets.append(
                PlanPreset(
                    kind="color",
                    value="RGB 미정" if rgb is None else "RGB " + " ".join(map(str, rgb)),
                    name="",
                    slot=slot,
                    cells=(PlanCell(group, bar),),
                    groups=(group,),
                    ready=False,
                    hold="; ".join(holds),
                    deferred=rgb is not None,
                    split_side=side,
                )
            )

    # -- 위치: 방향마다 대략 목표(target)가 있으면 값으로 싣는다. 없으면 「미정」 --------
    # 위치 프리셋은 **그룹마다 따로** 저장한다 — 방향 하나가 그 방향을 쓰는 그룹 수만큼의 줄이 되고,
    # 번호도 줄마다 따로 잡는다. 이름은 「콘솔 이름 + 그룹 이름」이라 줄마다 다르다.
    directions = [e for e in annotations.get("directions") or [] if isinstance(e, Mapping)]
    claimed = {
        (cell.group_name, cell.bar)
        for entry in directions
        for cell in _annotated_cells(entry.get("cells"), by_cell, [])
    }
    for entry in directions:
        cells = _hold_through_lit_run(
            _annotated_cells(entry.get("cells"), by_cell, missing_cells), rows, claimed=claimed
        )
        label = str(entry.get("name") or "")
        console_name = str(entry.get("console_name") or "")
        target_text = str(entry.get("target") or "").strip()
        value = f"{label} (대략: {target_text})" if target_text else label
        if target_text:
            fixes.append(
                f"{label} 목표 — 대략값 {target_text}. "
                "감독이 고칠 값: 콘솔에서 위치를 맞춘다(앱은 덮어쓰지 않음)."
            )
        # 칸이 하나도 없는 방향은 자리표시 한 줄만 낸다(그룹 이름이 빈 줄 — 번호를 잡지 않는다).
        for group in _unique(cell.group_name for cell in cells) or ("",):
            group_cells = tuple(cell for cell in cells if cell.group_name == group)
            name = f"{console_name} {group}".strip()
            reused_slot = (
                _reusable_position_slot(
                    grid, position_pool, name, _position_record(group, None, value)
                )
                if group_cells and target_text
                else None
            )
            if reused_slot is not None:
                # 콘솔에 이미 있는 번호를 쓴다 — 저장 줄 없이 칸만 그 번호를 가리킨다(「재사용」).
                presets.append(
                    PlanPreset(
                        kind="position",
                        value=value,
                        name=name,
                        slot=reused_slot,
                        cells=group_cells,
                        groups=(group,),
                        ready=True,
                        hold=None,
                        reused=True,
                    )
                )
                continue
            slot = None
            if group_cells:
                slot = _reserve_next(
                    position_pool,
                    first_free_base_position_number,
                    policy=policy,
                    grid=grid,
                    reserved=reserved,
                )
            if slot is not None:
                reserved.append(slot)
            holds = []
            if not group_cells:
                holds.append(
                    "칸 미정 — 이 방향을 쓸 격자 칸이 주석에 없다(감독이 칸 배정을 정한다)"
                )
            if position_pool is None:
                holds.append("위치 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
            if not target_text:
                holds.append(
                    "목표 좌표 미정 — 프로젝트에 방향→좌표 표가 없어 위치 프리셋을 만들 수 없음"
                )
            # 칸·번호·목표가 다 있으면 저장 후보다 — 저장 줄은 콘솔 판독 뒤
            # `preset_plan_store` 가 붙인다.
            candidate = not holds
            if candidate:
                holds.append(_POSITION_STORE_HOLD)
            presets.append(
                PlanPreset(
                    kind="position",
                    value=value,
                    name=name,
                    slot=slot,
                    cells=group_cells,
                    groups=(group,) if group else (),
                    ready=False,
                    hold="; ".join(holds),
                    deferred=candidate,
                )
            )

    # -- 자동 배치가 무빙 칸에 정한 계획 위치: 기본 위치 이름마다 그룹별 위치 후보를 센다.
    # 주석 방향 뒤에 둔다 — 주석 바닥 점이 잡은 칸은 계획 위치가 건드리지 않는다.
    _planned_position_presets(
        rows,
        grid=grid,
        position_pool=position_pool,
        policy=policy,
        presets=presets,
        reserved=reserved,
        fixes=fixes,
    )

    # -- 밖으로 나가는 항목: 이 카드 밖(값은 정해짐) · 미정(사유) -----------------------
    for preset in presets:
        if preset.ready:
            continue
        (deferred_lines if preset.deferred else unresolved).append(_outside_line(preset))
    for entry in annotations.get("relative_position_cells") or []:
        if not isinstance(entry, Mapping):
            continue
        group = str(entry.get("group_name"))
        bar = entry.get("bar")
        if (group, bar) in by_cell:
            label = entry.get("label")
            unresolved.append(
                f"{group} {bar}마디 「{label}」 — 상대 이동·새 자리라 위치 프리셋이 아님. "
                "이번 계획에서 제외(미정)"
            )
    for memo in grid.get("scene_memos") or []:
        if isinstance(memo, Mapping):
            unresolved.append(
                f"SCENE 메모 {memo.get('bar')}마디(칸이 아니라 계획 밖, 이번 계획에서 제외): "
                f"{memo.get('text')}"
            )
    if policy.get("confirmed") is not True:
        slots = ", ".join(preset.slot for preset in presets if preset.slot) or "없음"
        fixes.append(
            f"프리셋 번호대는 잠정(preset_pools.yaml confirmed: false) — 후보 번호({slots})는 "
            "콘솔 판독 기준의 빈 번호다. 감독이 고칠 값: 쇼 파일과 대조한 뒤 번호대를 확정한다."
        )

    # -- 칸에 이미 있는 고정 번호(건드리지 않음) -----------------------------------
    kept_counts: dict[str, int] = {}
    for _group, _no, _confirmed, cue in rows:
        numbers: list[str] = []
        brightness = cue.get("brightness")
        if (
            isinstance(brightness, Mapping)
            and brightness.get("mode") in ("dimmer_preset", "dimmer_effect")
            and brightness.get("preset_no") is not None
        ):
            numbers.append(str(brightness["preset_no"]))
        for field in ("position_preset_no", "color_preset_no", "effect_preset_no"):
            if cue.get(field) is not None:
                numbers.append(str(cue[field]))
        for number in numbers:
            kept_counts[number] = kept_counts.get(number, 0) + 1

    effect_presets, effect_unresolved, effect_fixes = _movement_effect_presets(
        rows,
        grid=grid,
        effect_pool=effect_pool,
        bpm=bpm,
        beats_per_bar=beats_per_bar,
        reserved={*kept_counts, *(preset.slot for preset in presets if preset.slot), *reserved},
        policy=policy,
    )
    presets.extend(effect_presets)
    unresolved.extend(effect_unresolved)
    fixes.extend(effect_fixes)
    missing_line = _missing_annotation_line(missing_cells)
    if missing_line is not None:
        unresolved.append(missing_line)

    return LoveAttackPlan(
        presets=tuple(presets),
        unresolved=tuple(unresolved),
        kept=tuple(sorted(kept_counts.items())),
        deferred=tuple(deferred_lines),
        supervisor_fixes=tuple(fixes),
    )


def saved_presets(plan: LoveAttackPlan) -> tuple[PlanPreset, ...]:
    """이 카드가 저장하는 프리셋 — 준비됐고(``ready``) 칸 쪽 색 후보가 아니며, 색·위치는 저장 줄이
    붙은 것. 저장 줄 · 칸 참조 · 사유 문장이 모두 이 목록 하나를 따른다(셋이 어긋나지 않게)."""
    return tuple(
        preset
        for preset in plan.presets
        if preset.ready
        and preset.split_side is None
        and preset.slot is not None
        and (preset.kind == "dimmer" or preset.store is not None or preset.reused)
    )


def saved_summary(plan: LoveAttackPlan) -> str:
    """저장 개수 한 줄 — ``프리셋 11개(디머 5 · 색 4 · 위치 2)``. 0개인 종류는 뺀다. 콘솔에 이미
    있던 번호를 다시 쓰는 것(재사용)은 저장이 아니라서 따로 센다."""
    everything = saved_presets(plan)
    saved = [preset for preset in everything if not preset.reused]
    reused = len(everything) - len(saved)
    counts = [
        (label, sum(1 for preset in saved if preset.kind == kind))
        for kind, label in _KIND_LABEL.items()
    ]
    detail = " · ".join(f"{label} {count}" for label, count in counts if count)
    text = f"프리셋 {len(saved)}개" + (f"({detail})" if detail else "")
    return text + (f" · 재사용 {reused}개" if reused else "")


def _append_bundle(lines: list[str], bundle: Sequence[str]) -> None:
    """저장 묶음을 카드 줄에 잇는다. 첫 묶음 앞에 ClearAll 을 한 번 두고, 앞 줄이 이미 ClearAll 이면
    묶음 머리의 ClearAll(색 레시피 t594 꼴)은 겹치므로 뺀다 — 묶음 모양 자체는 그대로다."""
    if not lines:
        lines.append("ClearAll")
    start = 1 if bundle[0] == "ClearAll" and lines[-1] == "ClearAll" else 0
    lines.extend(bundle[start:])


def save_commands(plan: LoveAttackPlan) -> tuple[str, ...]:
    """승인 카드에 실을 저장 줄. 준비된 기본 디머 프리셋과, 저장 줄이 붙은 색·위치 프리셋을 계획
    순서대로 싣는다(``saved_presets``).

    디머 묶음 꼴은 색 레시피(t594)와 같다 — ClearAll → 선택+값 → Store Preset → Label Preset
    → ClearAll. 그룹이 여럿이면 선택은 ``Group 4 + 7 + …`` 한 줄이다. 색·위치 묶음은
    ``PlanPreset.store`` 그대로다. 첫 묶음 앞에만 ClearAll 을 한 번 두고, 묶음마다 ClearAll 로
    닫는다."""
    lines: list[str] = []
    for preset in saved_presets(plan):
        if preset.reused:
            # 재사용은 콘솔에 이미 있는 번호다 — 저장 줄이 없다(칸 참조만 적는다).
            continue
        if preset.kind == "dimmer":
            assert preset.group_nos and preset.value_percent is not None
            pairs = tuple(
                preset.attribute_group_nos
                or ((attr, preset.group_nos) for attr in preset.attributes)
            )
            if len({tuple(numbers) for _attr, numbers in pairs}) == 1:
                # 모든 속성이 같은 그룹이면 한 줄(``Group 12 + 14 ; Attribute 'Dimmer' At 100 ;
                # Attribute 'Dimmer2' At 100``) — 실기 1.906 이 Dimmer·Dimmer2 를 다 담은 꼴이다.
                values = " ; ".join(
                    f"Attribute '{attr}' At {preset.value_percent}" for attr, _numbers in pairs
                )
                selection = "Group " + " + ".join(str(number) for number in pairs[0][1])
                value_lines: tuple[str, ...] = (f"{selection} ; {values}",)
            else:
                value_lines = tuple(
                    line
                    for attr, numbers in pairs
                    for line in _dimmer_value_lines(numbers, preset.value_percent, (attr,))
                )
            bundle: Sequence[str] = (
                *value_lines,
                f"Store Preset {preset.slot}",
                f"Label Preset {preset.slot} '{preset.name}'",
                "ClearAll",
            )
        else:
            assert preset.store is not None
            bundle = preset.store
        _append_bundle(lines, bundle)
    return tuple(lines)


def resolve_preset(
    plan: LoveAttackPlan,
    preset: PlanPreset,
    *,
    store: tuple[str, ...] | None,
    hold: str | None = None,
    fixes: Sequence[str] = (),
    cells: tuple[PlanCell, ...] | None = None,
) -> LoveAttackPlan:
    """저장 줄을 기다리던 색·위치 후보(``deferred``) 한 줄을 마무리한 새 계획을 돌려준다.

    ``cells`` 를 주면 후보의 칸을 그 칸들로 줄인다(이미 번호가 있는 칸을 뺄 때).

    ``store`` 가 있으면 그 줄을 이 카드가 저장한다(``ready``). 없으면 ``hold`` 를 사유로
    「미정」으로 내린다. 후보였을 때 「이 카드 밖」·「미정」 목록에 있던 사유 문장도 함께 바꾼다 —
    카드가 저장한다면서 같은 프리셋을 「이 카드 밖」에 적지 않게. ``fixes`` 는 「감독이 고칠 값」
    끝에 붙는다."""
    resolved = replace(
        preset,
        ready=store is not None,
        deferred=False,
        hold=None if store is not None else hold,
        store=store,
        cells=preset.cells if cells is None else cells,
    )
    old_line = _outside_line(preset)
    deferred = [line for line in plan.deferred if line != old_line]
    unresolved = [line for line in plan.unresolved if line != old_line]
    if not resolved.ready:
        unresolved.append(_outside_line(resolved))
    index = next((i for i, item in enumerate(plan.presets) if item is preset), -1)
    if index < 0:
        raise ValueError("이 계획에 없는 프리셋이다.")
    return replace(
        plan,
        presets=(*plan.presets[:index], resolved, *plan.presets[index + 1 :]),
        unresolved=tuple(unresolved),
        deferred=tuple(deferred),
        supervisor_fixes=(*plan.supervisor_fixes, *fixes),
    )


def card_reason(plan: LoveAttackPlan) -> str:
    """승인 카드에 보일 사유 한 줄 — 저장 · 이 카드 밖 · 미정(제외) · 감독이 고칠 값을 모두 싣는다.

    빈칸을 두지 않는다. 값이 정해진 항목은 「이 카드 밖」에, 정해지지 않은 항목은 「미정」에
    사유와 함께 적힌다."""
    saved = saved_presets(plan)
    head = f"{saved_summary(plan)} 저장"
    if saved:
        head += ": " + ", ".join(f"{preset.name}({preset.value})" for preset in saved)
    parts = [head]
    if plan.deferred:
        parts.append("이 카드 밖(저장 안 함): " + " / ".join(plan.deferred))
    if plan.unresolved:
        parts.append("미정(이번 계획에서 제외): " + " / ".join(plan.unresolved))
    if plan.supervisor_fixes:
        parts.append("감독이 고칠 값: " + " / ".join(plan.supervisor_fixes))
    return " · ".join(parts)


def plan_table_markdown(plan: LoveAttackPlan) -> str:
    """계획표(마크다운) — 만들 프리셋·후보 번호·칸 수·상태를 표로 적고, 아래에 「이 카드 밖」·
    「미정」·「감독이 고칠 값」을 그대로 싣는다(빈칸 없이)."""
    lines = ["| 만들 프리셋 | 값 | 후보 번호 | 칸 수 | 상태 |", "|---|---|---|---|---|"]
    for preset in plan.presets:
        if preset.reused:
            status = "재사용(이 카드)"
        elif preset.ready:
            status = "저장(이 카드)"
        elif preset.deferred:
            status = "이 카드 밖"
        else:
            status = "미정"
        slot = preset.slot or "콘솔 읽은 뒤 정함"
        cells = len(preset.cells)
        # 칸 하나의 왼쪽·오른쪽 색 후보는 이름이 아직 없다 — 빈 칸 대신 줄표를 둔다(화면이 표를
        # 읽을 때 빈 이름 칸이 되지 않게). 어느 칸의 어느 쪽인지는 아래 사유 줄이 말한다.
        name = preset.name or ("—" if preset.split_side is not None else "")
        lines.append(f"| {name} | {preset.value} | {slot} | {cells} | {status} |")
    sections = (
        ("이 카드 밖", plan.deferred),
        ("미정(이번 계획에서 제외)", plan.unresolved),
        ("감독이 고칠 값", plan.supervisor_fixes),
    )
    for title, items in sections:
        if items:
            lines.append("")
            lines.append(f"**{title}**")
            lines.extend(f"- {item}" for item in items)
    return "\n".join(lines)


def _reference_changes(preset: PlanPreset) -> dict[str, object]:
    """저장한 프리셋을 칸이 가리키게 하는 편집 — 디머는 밝기, 색·위치는 그 번호 필드."""
    if preset.kind == "dimmer":
        return {
            "brightness": {"mode": "dimmer_preset", "value_percent": None, "preset_no": preset.slot}
        }
    if preset.kind == "effect":
        # 움직임은 저장한 효과 프리셋이 맡는다. 칸의 app_movement 는 지우지 않는다 — 화면의 무빙
        # 빔과 방향 값이 움직임을 계속 읽어야 한다. 대신 ``movement_effect_no`` 에 같은 번호를
        # 적어(칸을 고치기 전에 ``_mark_movement_carrier`` 가 적는다) 앱 2단계 줄은 보내지 않고
        # 게이트 요구를 (5,7,9)에서 (4)로 옮긴다(``beat_grid.movement_carried_by_effect``).
        return {"effect_preset_no": preset.slot, "effect_kind": "position"}
    return {_REFERENCE_FIELD[preset.kind]: preset.slot}


def _mark_movement_carrier(grid: dict[str, object], cell: PlanCell, slot: str | None) -> None:
    """칸에 「이 효과 번호가 칸의 움직임을 대신 낸다」는 표식(``movement_effect_no``)을 적는다.
    칸을 효과 번호로 고치는 편집이 같은 칸의 축 충돌 검사(``check_app_movement_axis_conflict``)를
    거치기 전에 적어 둬야 그 검사가 이 칸을 충돌로 보지 않는다. ``grid`` 는 호출한 쪽이 이미 깊은
    사본으로 가진 것이다."""
    if slot is None:
        return
    for track in grid.get("tracks") or []:  # type: ignore[union-attr]
        if str(track.get("group_name")) != cell.group_name:
            continue
        for cue in track.get("cues") or []:
            if cue.get("bar") == cell.bar and (cue.get("app_movement") or {}).get("shape"):
                cue["movement_effect_no"] = slot


def apply_plan_references(
    grid: Mapping[str, object],
    plan: LoveAttackPlan,
    *,
    by: str,
    date: str,
    source: str,
    planned_from: Mapping[str, object] | None = None,
    record_approval: bool = True,
) -> dict[str, object]:
    """**승인 뒤에만** 부른다. 저장한 프리셋(디머 · 색 · 위치, ``saved_presets``)을 그 칸에서
    참조시키고, 참조가 바뀐 칸·필드를 승인으로 적는다. 색은 RGB 를, 색·위치는 콘솔 이름을 격자에
    남긴다(칸의 ``color_rgb`` 는 여기서 파생된다). 칸에 이미 있던 승인은 출처를 덧붙여 남긴다
    (기록 유실 방지).

    이 함수는 ``grid`` 를 건드리지 않고 새 사본을 돌려준다. 승인 전에는 호출하지 않는다 —
    카드가 거절되면 격자는 바이트까지 그대로다.

    ``planned_from`` — 계획을 세운 때의 격자. 승인 창이 떠 있는 사이 감독이 고친 칸을 지우지
    않으려고, 승인 뒤 **지금** 격자(``grid``)를 넘기고 계획 시점 격자를 여기 넘긴다. 그 사이
    이 편집이 바꿀 필드(디머는 밝기, 색·위치는 그 번호 필드)가 바뀐(또는 사라진) 칸은 건너뛴다 —
    감독의 새 편집이 계획보다 우선이다."""
    updated: dict[str, object] = copy.deepcopy(dict(grid))
    touched: dict[PlanCell, str | None] = {}
    for preset in saved_presets(plan):
        changes = _reference_changes(preset)
        for cell in preset.cells:
            cue = _grid_cue(grid, cell)
            if planned_from is not None:
                planned_cue = _grid_cue(planned_from, cell)
                if (
                    cue is None
                    or planned_cue is None
                    or any(cue.get(field) != planned_cue.get(field) for field in changes)
                ):
                    continue
            prior = _prior_approval_source(grid, cell)
            if preset.kind == "effect":
                _mark_movement_carrier(updated, cell, preset.slot)
            evidence = cue.get("evidence") if cue is not None else None
            grade = evidence.get("grade") if isinstance(evidence, Mapping) else None
            # 옛 승인은 옛 번호의 것이라 이 편집에서 비운다(grade 는 보존). 안 비우면 승인 기록이
            # 새 번호 1.x 를 덮어 "승인됨"으로 거짓 통과한다. 공유 편집 경로도 이제 디머 기본
            # 프리셋 번호 변경을 승인 대기로 세지만, 여기서는 명시적으로 비운 뒤 아래에서 이
            # 카드의 승인을 적는다.
            updated, _report = apply_beat_grid_edit(
                updated,
                bar=cell.bar,
                target=cell.group_name,
                changes={**changes, "evidence": {"grade": grade, "approval": None}},
            )
            touched.setdefault(cell, prior)
        # 콘솔에는 이미 이 프리셋이 있다 — 칸이 하나도 안 바뀌어도 값·이름은 격자에 남긴다.
        # 재사용한 번호는 이미 기록돼 있으므로 그 기록을 덮지 않는다.
        if preset.kind == "color" and not preset.reused:
            assert preset.rgb is not None and preset.slot is not None
            # 담은 그룹도 남긴다 — 다음 계획의 재사용이 「저장한 그룹만」을 가른다.
            updated = record_color_preset_rgb(updated, preset.slot, preset.rgb, preset.groups)
        if preset.kind != "dimmer" and not preset.reused:
            assert preset.slot is not None
            updated = record_app_preset_label(updated, preset.slot, preset.name)
        if preset.kind == "dimmer" and not preset.reused and preset.slot:
            dimmer_records = updated.get(_DIMMER_RECORD_KEY)
            dimmer_records = dict(dimmer_records) if isinstance(dimmer_records, Mapping) else {}
            dimmer_records[preset.slot] = {
                "percent": preset.value_percent,
                "attribute_group_nos": [
                    [attr, list(nos)] for attr, nos in preset.attribute_group_nos
                ],
            }
            updated[_DIMMER_RECORD_KEY] = dimmer_records
        if preset.kind == "position" and preset.groups and not preset.reused and preset.slot:
            position_records = updated.get(_POSITION_RECORD_KEY)
            position_records = (
                dict(position_records) if isinstance(position_records, Mapping) else {}
            )
            position_records[preset.slot] = _position_record(
                preset.groups[0], preset.aim, preset.value
            )
            updated[_POSITION_RECORD_KEY] = position_records
        if preset.kind == "effect" and preset.effect_record is not None and preset.slot:
            records = updated.get(_EFFECT_RECORD_KEY)
            records = dict(records) if isinstance(records, Mapping) else {}
            if not preset.reused or preset.slot not in records:
                group_no, signature, bpm = preset.effect_record
                records[preset.slot] = {
                    "group_no": group_no,
                    "signature": _json_signature(signature),  # type: ignore[arg-type]
                    "bpm": bpm,
                }
                updated[_EFFECT_RECORD_KEY] = records
    if not record_approval:
        return updated
    pending = pending_preset_approvals(updated)
    for cell, prior in touched.items():
        entries = [
            entry
            for entry in pending
            if entry["group_name"] == cell.group_name and entry["bar"] == cell.bar
        ]
        if not entries:
            continue
        cell_source = source if prior is None else f"{prior} | {source}"
        updated = apply_pending_approval(updated, entries, by=by, date=date, source=cell_source)
    return updated

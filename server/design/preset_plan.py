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
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

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
from server.design.beat_grid_color_presets import record_color_preset_rgb
from server.design.beat_grid_edit import apply_beat_grid_edit
from server.design.beat_grid_presets import (
    first_free_base_color_number,
    first_free_base_dimmer_number,
    first_free_base_position_number,
    record_app_preset_label,
)
from server.design.color_names import resolve_color_name

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

#: 프리셋 종류의 화면 이름 — 저장 개수 요약(``saved_summary``)이 쓴다.
_KIND_LABEL = {"dimmer": "디머", "color": "색", "position": "위치"}

#: 저장한 색·위치 프리셋을 칸에서 가리키는 필드.
_REFERENCE_FIELD = {"color": "color_preset_no", "position": "position_preset_no"}

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

    kind: str  # "dimmer" | "color" | "position"
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


def _annotated_cells(
    raw: object,
    by_cell: Mapping[tuple[str, int], object],
    unresolved: list[str],
) -> tuple[PlanCell, ...]:
    """주석의 칸 목록 → 격자에 실제로 있는 칸만.

    없는 칸은 조용히 버리지 않고 「미정」 목록으로 알린다."""
    cells: list[PlanCell] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, Mapping):
            continue
        group = str(item.get("group_name"))
        bar = int(item.get("bar"))  # type: ignore[arg-type]
        if (group, bar) in by_cell:
            cells.append(PlanCell(group, bar))
        else:
            unresolved.append(f"주석 칸 {group} {bar}마디가 격자에 없음 — 주석을 고쳐야 함")
    return tuple(cells)


def _grid_cue(grid: Mapping[str, object], cell: PlanCell) -> Mapping[str, object] | None:
    for group, _no, _confirmed, cue in _grid_cues(grid):
        if group == cell.group_name and cue.get("bar") == cell.bar:
            return cue
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


def build_preset_plan(
    grid: Mapping[str, object],
    *,
    annotations: Mapping[str, object],
    policy: Mapping[str, object],
    dimmer_pool: PoolRead,
    color_pool: PoolRead,
    position_pool: PoolRead,
    dimmer_attributes: Mapping[str, Sequence[str]],
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
    deferred_lines: list[str] = []
    fixes: list[str] = []
    presets: list[PlanPreset] = []
    reserved: list[str] = []

    # -- 밝기 결정: 리드가 정한 칸 밝기(brightness_decisions)
    brightness_notes: dict[tuple[str, int], str] = {}
    for entry in annotations.get("brightness_decisions") or []:
        if not isinstance(entry, Mapping):
            continue
        for cell in _annotated_cells(entry.get("cells"), by_cell, unresolved):
            brightness_notes[(cell.group_name, cell.bar)] = str(entry.get("note") or "").strip()

    # -- 디머: 칸의 value_percent 를 값으로 묶는다(첫 등장 순) -------------------
    uses: dict[int, list[tuple[str, object, bool, int]]] = {}
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
        uses.setdefault(percent, []).append((group, group_no, confirmed, int(cue["bar"])))  # type: ignore[arg-type]

    for percent, uses_of_value in uses.items():
        name = f"{_DIMMER_NAME_PREFIX}-{percent}"
        cells = tuple(PlanCell(group, bar) for group, _no, _c, bar in uses_of_value)
        groups = _unique(group for group, _no, _c, _bar in uses_of_value)
        slot = _reserve_next(
            dimmer_pool, first_free_base_dimmer_number, policy=policy, grid=grid, reserved=reserved
        )
        if slot is not None:
            reserved.append(slot)
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
        cells = _annotated_cells(entry.get("cells"), by_cell, unresolved)
        groups = _unique(cell.group_name for cell in cells)
        # 칸이 없는 색은 번호를 잡지 않는다 — 쓰지 않을 빈 번호를 점유하지 않으려고.
        slot = None
        if cells:
            slot = _reserve_next(
                color_pool,
                first_free_base_color_number,
                policy=policy,
                grid=grid,
                reserved=reserved,
            )
        if slot is not None:
            reserved.append(slot)
        name = str(entry.get("console_name") or "")
        label = str(entry.get("name") or "")
        holds = []
        if not cells:
            holds.append("칸 미정 — 이 색을 쓸 격자 칸이 주석에 없다(감독이 칸 배정을 정한다)")
        if color_pool is None:
            holds.append("색 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
        rgb = entry.get("rgb")
        from_palette = rgb is None
        if rgb is None:
            rgb = resolve_color_name(label)  # 표준 팔레트 이름으로만 찾는다(없으면 None)
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
    for entry in annotations.get("directions") or []:
        if not isinstance(entry, Mapping):
            continue
        cells = _annotated_cells(entry.get("cells"), by_cell, unresolved)
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
                    name=f"{console_name} {group}".strip(),
                    slot=slot,
                    cells=group_cells,
                    groups=(group,) if group else (),
                    ready=False,
                    hold="; ".join(holds),
                    deferred=candidate,
                )
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
        and (preset.kind == "dimmer" or preset.store is not None)
    )


def saved_summary(plan: LoveAttackPlan) -> str:
    """저장 개수 한 줄 — ``프리셋 11개(디머 5 · 색 4 · 위치 2)``. 0개인 종류는 뺀다."""
    saved = saved_presets(plan)
    counts = [
        (label, sum(1 for preset in saved if preset.kind == kind))
        for kind, label in _KIND_LABEL.items()
    ]
    detail = " · ".join(f"{label} {count}" for label, count in counts if count)
    return f"프리셋 {len(saved)}개" + (f"({detail})" if detail else "")


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
        if preset.kind == "dimmer":
            assert preset.group_nos and preset.value_percent is not None
            bundle: Sequence[str] = (
                *_dimmer_value_lines(preset.group_nos, preset.value_percent, preset.attributes),
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
) -> LoveAttackPlan:
    """저장 줄을 기다리던 색·위치 후보(``deferred``) 한 줄을 마무리한 새 계획을 돌려준다.

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
        if preset.ready:
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
    return {_REFERENCE_FIELD[preset.kind]: preset.slot}


def apply_plan_references(
    grid: Mapping[str, object],
    plan: LoveAttackPlan,
    *,
    by: str,
    date: str,
    source: str,
    planned_from: Mapping[str, object] | None = None,
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
        if preset.kind == "color":
            assert preset.rgb is not None and preset.slot is not None
            updated = record_color_preset_rgb(updated, preset.slot, preset.rgb)
        if preset.kind != "dimmer":
            assert preset.slot is not None
            updated = record_app_preset_label(updated, preset.slot, preset.name)
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

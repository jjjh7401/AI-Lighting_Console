"""큐마다 그룹·장비가 무엇을 켜는가 — 저장 내용과 존재 확인 표(1차 전체 실행 G 단계).

콘솔이 실제로 내는 값(DMX)은 이 표가 재지 않는다. 응답기는 큐 파트의 값·프리셋 참조를
직렬화하지 않는다(실측 ``.moai/reports/t230/verdict.md`` §1 · ``t255`` 첫머리 · ``t538``
``r16_part_sizes.txt`` — 파트 자식 0, ``OWNDATAPRESENT`` 와 크기만 답한다). 그래서 이 표는
세 가지를 맞대어 보인다:

1. **앱이 그 큐에 저장한 것** — 격자 칸(밝기·색·위치·효과 프리셋 참조)과 반영 기록의 큐 번호.
2. **그 프리셋에 담아 저장한 것** — 감사 기록에서 콘솔이 ``OK`` 로 받은 줄을 순서대로 따라가
   ``Store Preset`` 직전의 프로그래머 내용(그룹·장비별 속성)을 되살린다.
3. **기종이 가진 것** — 장비 능력 판독(속성 이름). 밝기 계열(``Dimmer``·``Dimmer2``…)과 색 속성
   가운데 그 그룹의 프리셋이 안 연 것을 표시한다(규칙은 리그 번호가 아니라 속성 이름으로).

순수 함수뿐이다 — 파일·콘솔 무접촉. 읽기는 ``server/tools/cue_output_table.py`` 가 한다.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from server.design.app_movement import dimmer_attribute_names

__all__ = [
    "CueRow",
    "FixtureFinding",
    "StoredPreset",
    "fixture_findings",
    "planned_cue_rows",
    "render_markdown",
    "stored_presets_from_audit",
]

_SELECTION = re.compile(r"^(Group|Fixture) (\d+(?: \+ \d+)*) ; (.+)$")
_ATTRIBUTE = re.compile(r"^Attribute '([^']+)' At (.+)$")
_AT_PRESET = re.compile(r"^At Preset (\d+\.\d+)$")
_STORE_PRESET = re.compile(r"^Store Preset (\d+\.\d+)\b")
_LABEL_PRESET = re.compile(r"^Label Preset (\d+\.\d+) '([^']*)'")
_SHUTTER = re.compile(r"shutter\d*")
_COLOR = re.compile(r"color.*")

#: 표 머리에 늘 싣는 한계 문장 — 「실제 출력」으로 읽히지 않게.
LIMIT_NOTE = (
    "이 표는 콘솔의 실제 출력(DMX)이 아니라 「앱이 저장한 것 + 콘솔에 그 큐·프리셋이 있는가」다. "
    "응답기는 큐 파트의 값을 꺼내 주지 않는다(t230·t255·t538 실측). 실제 빛은 콘솔 화면으로 본다."
)


@dataclass
class StoredPreset:
    """``Store Preset`` 한 번이 담은 프로그래머 내용 — 콘솔이 ``OK`` 로 받은 줄로만 만든다."""

    slot: str
    label: str | None = None
    #: 그룹 번호 -> {속성: 값}
    groups: dict[int, dict[str, str]] = field(default_factory=dict)
    #: 장비 번호 -> {속성: 값}
    fixtures: dict[int, dict[str, str]] = field(default_factory=dict)
    #: 그룹 번호 -> 프리셋 안에서 다시 부른 프리셋(``At Preset``)
    group_refs: dict[int, str] = field(default_factory=dict)
    stored_at: str | None = None

    def attributes_for(self, group_no: int | None, fid: int | None = None) -> dict[str, str]:
        """그 그룹(그리고 그 장비)에 담긴 속성. 장비 줄이 그룹 줄을 덮는다."""
        merged = dict(self.groups.get(group_no, {})) if group_no is not None else {}
        if fid is not None:
            merged.update(self.fixtures.get(fid, {}))
        return merged


def _accepted_commands(entries: Iterable[Mapping[str, object]]) -> Iterable[tuple[str, str]]:
    for entry in entries:
        if entry.get("event") != "executed" or entry.get("kind") != "command":
            continue
        if entry.get("ok") is not True:
            continue
        command = entry.get("command")
        if isinstance(command, str):
            yield command.strip(), str(entry.get("ts") or "")


def stored_presets_from_audit(entries: Iterable[Mapping[str, object]]) -> dict[str, StoredPreset]:
    """감사 기록(시각 순) → 프리셋 칸(``pool.slot``)마다 **마지막으로** 저장한 내용.

    ``ClearAll`` 이 프로그래머를 비우고, ``Group a + b ; Attribute 'X' At v`` 가 그룹마다 값을
    올리며, ``Store Preset P`` 가 그 순간의 내용을 ``P`` 로 굳힌다. 모르는 줄은 프로그래머를
    바꾸지 않는다고 본다(지어내지 않는다 — 그런 줄은 표에 나오지 않을 뿐이다)."""
    groups: dict[int, dict[str, str]] = {}
    fixtures: dict[int, dict[str, str]] = {}
    refs: dict[int, str] = {}
    presets: dict[str, StoredPreset] = {}
    for command, ts in _accepted_commands(entries):
        if command == "ClearAll":
            groups, fixtures, refs = {}, {}, {}
            continue
        if (match := _STORE_PRESET.match(command)) is not None:
            slot = match.group(1)
            label = presets[slot].label if slot in presets else None
            presets[slot] = StoredPreset(
                slot=slot,
                label=label,
                groups={no: dict(attrs) for no, attrs in groups.items()},
                fixtures={no: dict(attrs) for no, attrs in fixtures.items()},
                group_refs=dict(refs),
                stored_at=ts,
            )
            continue
        if (match := _LABEL_PRESET.match(command)) is not None:
            if match.group(1) in presets:
                presets[match.group(1)].label = match.group(2)
            continue
        if (match := _SELECTION.match(command)) is None:
            continue
        kind, numbers, rest = match.groups()
        targets = [int(number) for number in numbers.split(" + ")]
        table = groups if kind == "Group" else fixtures
        for op in (part.strip() for part in rest.split(" ; ")):
            if (attribute := _ATTRIBUTE.match(op)) is not None:
                for target in targets:
                    table.setdefault(target, {})[attribute.group(1)] = attribute.group(2)
            elif (preset := _AT_PRESET.match(op)) is not None and kind == "Group":
                for target in targets:
                    refs[target] = preset.group(1)
    return presets


@dataclass(frozen=True)
class CueRow:
    """한 그룹 시퀀스의 큐 하나 — 격자 칸 하나다. 비어 있는 칸(``—``)은 앞 큐 값이 이어진다."""

    group_name: str
    group_no: int | None
    sequence_number: int | None
    cue_number: int | None
    bar: int
    dimmer: str
    color_preset: str | None
    position_preset: str | None
    effect_preset: str | None
    movement: str | None

    @property
    def presets(self) -> tuple[str, ...]:
        dimmer = self.dimmer.removeprefix("프리셋 ") if self.dimmer.startswith("프리셋 ") else None
        return tuple(
            slot
            for slot in (dimmer, self.color_preset, self.position_preset, self.effect_preset)
            if slot
        )


def _dimmer_text(cue: Mapping[str, object]) -> str:
    brightness = cue.get("brightness")
    if not isinstance(brightness, Mapping):
        return ""
    mode = brightness.get("mode")
    if mode in ("dimmer_preset", "dimmer_effect") and brightness.get("preset_no") is not None:
        return f"프리셋 {brightness['preset_no']}"
    if mode == "value" and brightness.get("value_percent") is not None:
        return f"값 {brightness['value_percent']}%"
    return ""


def _slot(value: object) -> str | None:
    return str(value) if value is not None and str(value).strip() else None


def planned_cue_rows(
    grid: Mapping[str, object], allocation: Mapping[str, object] | None
) -> list[CueRow]:
    """격자 칸 → 큐 표. 큐·시퀀스 번호는 반영 기록(``beat_grid_allocations``)에서만 온다 —
    반영한 적 없는 트랙·칸은 번호가 ``None`` 이다(번호를 지어내지 않는다)."""
    tracks_record = allocation.get("tracks") if isinstance(allocation, Mapping) else None
    tracks_record = tracks_record if isinstance(tracks_record, Mapping) else {}
    rows: list[CueRow] = []
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        name = str(track.get("group_name") or "")
        record = tracks_record.get(name)
        record = record if isinstance(record, Mapping) else {}
        sequence = record.get("sequence_number")
        cue_numbers = record.get("cues") if isinstance(record.get("cues"), Mapping) else {}
        group_no = track.get("group_no") if track.get("group_no_confirmed") else None
        cues = [cue for cue in track.get("cues") or [] if isinstance(cue, Mapping)]
        for cue in sorted(cues, key=lambda item: int(item.get("bar") or 0)):
            bar = int(cue.get("bar") or 0)
            movement = cue.get("app_movement")
            shape = movement.get("shape") if isinstance(movement, Mapping) else None
            number = cue_numbers.get(str(bar))
            rows.append(
                CueRow(
                    group_name=name,
                    group_no=group_no if isinstance(group_no, int) else None,
                    sequence_number=sequence if isinstance(sequence, int) else None,
                    cue_number=number if isinstance(number, int) else None,
                    bar=bar,
                    dimmer=_dimmer_text(cue),
                    color_preset=_slot(cue.get("color_preset_no")),
                    position_preset=_slot(cue.get("position_preset_no")),
                    effect_preset=_slot(cue.get("effect_preset_no")),
                    movement=str(shape) if shape else None,
                )
            )
    return rows


@dataclass(frozen=True)
class FixtureFinding:
    """장비 하나가 그 그룹 프리셋으로 무엇을 받는가 — 기종 속성과 맞대어."""

    group_name: str
    fid: int
    type_name: str
    brightness_attributes: tuple[str, ...]
    opened: tuple[str, ...]  # 프리셋들이 이 장비에 연 밝기 계열 속성
    not_opened: tuple[str, ...]  # 기종에 있는데 어느 디머 프리셋도 안 연 밝기 계열 속성
    shutter_attributes: tuple[str, ...]
    color_attributes: tuple[str, ...]
    color_stored: tuple[str, ...]  # 색 프리셋들이 이 장비에 담은 색 속성
    color_mismatch: bool  # 색 프리셋을 받는데 그 속성이 이 기종 색 속성과 하나도 안 겹친다
    whole: bool  # 능력 판독이 전수인가 — 아니면 「없다」를 단정하지 않는다


def fixture_findings(
    rows: Sequence[CueRow],
    presets: Mapping[str, StoredPreset],
    group_members: Mapping[str, Sequence[int]],
    capabilities: Mapping[int, object],
) -> list[FixtureFinding]:
    """그룹 소속 장비마다 기종 속성 vs 그 그룹이 쓰는 프리셋들이 담은 속성.

    ``capabilities`` 는 fid -> ``FixtureCapability``(``attributes``·``type_name``·``whole``).
    밝기 계열은 ``dimmer_attribute_names``(``^dimmer\\d*$``), 셔터는 ``shutter\\d*``, 색은
    ``color…`` 이름 — 기종 이름·리그 번호는 보지 않는다."""
    used: dict[str, dict[str, set[str]]] = {}
    for row in rows:
        kinds = used.setdefault(row.group_name, {"dimmer": set(), "color": set()})
        if row.dimmer.startswith("프리셋 "):
            kinds["dimmer"].add(row.dimmer.removeprefix("프리셋 "))
        if row.color_preset:
            kinds["color"].add(row.color_preset)
    group_nos = {row.group_name: row.group_no for row in rows}
    findings: list[FixtureFinding] = []
    for group_name, fids in group_members.items():
        group_no = group_nos.get(group_name)
        kinds = used.get(group_name, {"dimmer": set(), "color": set()})
        for fid in fids:
            capability = capabilities.get(fid)
            if capability is None:
                continue
            attributes = tuple(getattr(capability, "attributes", ()))
            brightness = dimmer_attribute_names(attributes)
            shutters = tuple(a for a in attributes if _SHUTTER.fullmatch(a.casefold()))
            colors = tuple(a for a in attributes if _COLOR.fullmatch(a.casefold()))
            opened: set[str] = set()
            for slot in kinds["dimmer"]:
                if slot in presets:
                    opened.update(presets[slot].attributes_for(group_no, fid))
            color_stored: set[str] = set()
            for slot in kinds["color"]:
                if slot in presets:
                    color_stored.update(
                        a
                        for a in presets[slot].attributes_for(group_no, fid)
                        if _COLOR.fullmatch(a.casefold())
                    )
            opened_brightness = tuple(a for a in brightness if a in opened)
            findings.append(
                FixtureFinding(
                    group_name=group_name,
                    fid=fid,
                    type_name=str(getattr(capability, "type_name", "")),
                    brightness_attributes=brightness,
                    opened=opened_brightness,
                    not_opened=tuple(a for a in brightness if a not in opened)
                    if kinds["dimmer"]
                    else (),
                    shutter_attributes=shutters,
                    color_attributes=colors,
                    color_stored=tuple(sorted(color_stored)),
                    color_mismatch=bool(color_stored) and not (color_stored & set(colors)),
                    whole=bool(getattr(capability, "whole", False)),
                )
            )
    return findings


def _cell(value: str | None) -> str:
    return value if value else "—"


def _console_cell(console: Mapping[tuple[int, int], str] | None, row: CueRow) -> str:
    if console is None:
        return "안 읽음"
    if row.sequence_number is None or row.cue_number is None:
        return "반영 기록 없음"
    return console.get((row.sequence_number, row.cue_number), "콘솔에 없음")


def render_markdown(
    rows: Sequence[CueRow],
    presets: Mapping[str, StoredPreset],
    *,
    findings: Sequence[FixtureFinding] = (),
    console_cues: Mapping[tuple[int, int], str] | None = None,
    console_presets: Mapping[str, str] | None = None,
    notes: Sequence[str] = (),
) -> str:
    """사람이 읽는 표. ``console_*`` 가 ``None`` 이면 콘솔을 안 읽은 것이다(「없다」가 아니다)."""
    lines = ["# 큐별 그룹·장비 표 — 저장 내용과 존재 확인", "", f"> {LIMIT_NOTE}", ""]
    lines.extend(f"- {note}" for note in notes)
    if notes:
        lines.append("")

    problems = [f for f in findings if f.not_opened or f.color_mismatch]
    lines.append("## 1. 장비가 받지 못하는 속성")
    lines.append("")
    if not findings:
        lines.append(
            "장비 판독이 없어 이 절은 비었다(`--read-console` 로 소속·기종 속성을 읽는다)."
        )
    elif not problems:
        lines.append(
            "모든 장비가 기종의 밝기 계열 속성을 다 받고, 색 프리셋도 기종 색 속성과 맞다."
        )
    else:
        lines.append("| 그룹 | 장비 | 기종 | 안 연 밝기 속성 | 색 | 판독 |")
        lines.append("|---|---|---|---|---|---|")
        for f in problems:
            fixture_colors = ", ".join(f.color_attributes) or "없음"
            color = (
                f"프리셋 {', '.join(f.color_stored)} ↔ 기종 {fixture_colors}"
                if f.color_mismatch
                else "맞음"
            )
            lines.append(
                f"| {f.group_name} | {f.fid} | {f.type_name} | {', '.join(f.not_opened) or '—'} | "
                f"{color} | {'전수' if f.whole else '부분 — 단정 못 함'} |"
            )
    lines.append("")

    lines.append("## 2. 그룹별 장비 밝기·셔터·색 속성")
    lines.append("")
    if findings:
        lines.append("| 그룹 | 장비 | 기종 | 밝기 계열 | 프리셋이 연 것 | 셔터 | 색 속성 |")
        lines.append("|---|---|---|---|---|---|---|")
        for f in findings:
            lines.append(
                f"| {f.group_name} | {f.fid} | {f.type_name} | "
                f"{', '.join(f.brightness_attributes) or '없음'} | {', '.join(f.opened) or '—'} | "
                f"{', '.join(f.shutter_attributes) or '없음'} | "
                f"{', '.join(f.color_attributes) or '없음'} |"
            )
    else:
        lines.append("장비 판독 없음.")
    lines.append("")

    lines.append("## 3. 프리셋이 그룹마다 담은 것 (감사 기록의 OK 줄)")
    lines.append("")
    slots = sorted({slot for row in rows for slot in row.presets}, key=_slot_key)
    if not slots:
        lines.append("큐가 부르는 프리셋이 없다.")
    else:
        lines.append("| 프리셋 | 이름 | 그룹 | 담은 속성 | 콘솔 |")
        lines.append("|---|---|---|---|---|")
        for slot in slots:
            preset = presets.get(slot)
            console = "안 읽음" if console_presets is None else console_presets.get(slot, "없음")
            if preset is None:
                lines.append(f"| {slot} | — | — | 감사 기록에 저장 줄 없음 | {console} |")
                continue
            groups = sorted(set(preset.groups) | set(preset.group_refs))
            if not groups and not preset.fixtures:
                # 효과 줄 등 이 해석기가 모르는 형식은 내용을 되살리지 못한다 — 「비었다」가 아니다.
                lines.append(
                    f"| {slot} | {_cell(preset.label)} | — | "
                    f"그룹·속성 줄을 못 알아봄(효과 등) | {console} |"
                )
            for no in groups:
                attrs = ", ".join(f"{k}={v}" for k, v in preset.groups.get(no, {}).items())
                ref = preset.group_refs.get(no)
                attrs = attrs + (f" · 프리셋 {ref}" if ref else "")
                lines.append(f"| {slot} | {_cell(preset.label)} | {no} | {attrs} | {console} |")
            if preset.fixtures:
                lines.append(
                    f"| {slot} | {_cell(preset.label)} | 장비 {len(preset.fixtures)}대 | "
                    f"{', '.join(sorted({a for v in preset.fixtures.values() for a in v}))} | "
                    f"{console} |"
                )
    lines.append("")

    lines.append("## 4. 큐마다 그룹이 켜는 것")
    lines.append("")
    lines.append("칸이 「—」이면 그 큐는 그 값을 바꾸지 않는다(앞 큐 값이 이어진다).")
    lines.append("")
    lines.append("| 그룹 | 시퀀스 | 큐 | 마디 | 밝기 | 색 | 위치 | 효과·무빙 | 콘솔 큐 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        motion = " · ".join(v for v in (row.effect_preset, row.movement) if v) or None
        lines.append(
            f"| {row.group_name} | {_cell(str(row.sequence_number or ''))} | "
            f"{_cell(str(row.cue_number or ''))} | {row.bar} | {_cell(row.dimmer)} | "
            f"{_cell(row.color_preset)} | {_cell(row.position_preset)} | {_cell(motion)} | "
            f"{_console_cell(console_cues, row)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _slot_key(slot: str) -> tuple[int, ...]:
    return tuple(int(part) for part in slot.split(".") if part.isdigit())

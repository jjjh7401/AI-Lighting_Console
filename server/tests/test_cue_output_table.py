"""큐별 그룹·장비 표 — 1차 전체 실행 G 단계(16항목 SKIP)의 측정 수단.

응답기는 큐 파트 값을 못 꺼낸다(t230·t255·t538 실측). 그래서 표는 「앱이 저장한 것 + 그 프리셋이
담은 것(감사 기록의 OK 줄) + 콘솔에 그 큐·프리셋이 있는가 + 기종 속성」을 맞댄다. 이 시험은
콘솔에 한 바이트도 보내지 않는다 — 콘솔 읽기는 가짜 포트로 흉내낸다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from server.design.cue_output_table import (
    LIMIT_NOTE,
    fixture_findings,
    planned_cue_rows,
    render_markdown,
    stored_presets_from_audit,
)
from server.tools import cue_output_table as tool


def _ok(command: str, ts: str = "t") -> dict:
    return {"event": "executed", "kind": "command", "ok": True, "command": command, "ts": ts}


#: 리드 계획 카드(rr2-card-1) 모양 — #800 전의 디머 프리셋은 그룹 12 에 Dimmer 만 담았다.
_AUDIT = [
    _ok("ClearAll"),
    _ok("Group 4 + 11 + 12 ; Attribute 'Dimmer' At 100"),
    _ok("Store Preset 1.20"),
    _ok("Label Preset 1.20 'DIM-100'"),
    _ok("ClearAll"),
    _ok("Group 12 ; Attribute 'ColorRGB_R' At 55 ; Attribute 'ColorRGB_G' At 35"),
    _ok("Store Preset 4.106"),
    _ok("ClearAll"),
    # 콘솔이 거절한 줄은 프리셋 내용이 아니다.
    {"event": "executed", "kind": "command", "ok": False, "command": "Store Preset 1.99"},
    {"event": "executed", "kind": "props_query", "ok": True, "command": "Store Preset 1.98"},
]

_GRID = {
    "tracks": [
        {
            "group_name": "MOVER-D",
            "group_no": 12,
            "group_no_confirmed": True,
            "cues": [
                {"bar": 4, "brightness": {"mode": "dimmer_preset", "preset_no": "1.20"}},
                {
                    "bar": 0,
                    "brightness": {"mode": "dimmer_preset", "preset_no": "1.20"},
                    "color_preset_no": "4.106",
                },
            ],
        },
        {"group_name": "FOH", "group_no": 3, "group_no_confirmed": True, "cues": [{"bar": 0}]},
    ]
}
_ALLOCATION = {"tracks": {"MOVER-D": {"sequence_number": 60, "cues": {"0": 1, "4": 2}}}}


@dataclass
class _Capability:
    attributes: tuple[str, ...]
    type_name: str = "Robin Spiider"
    whole: bool = True


def test_preset_contents_come_only_from_accepted_command_lines() -> None:
    presets = stored_presets_from_audit(_AUDIT)
    assert sorted(presets) == ["1.20", "4.106"]
    assert presets["1.20"].label == "DIM-100"
    assert presets["1.20"].groups == {
        4: {"Dimmer": "100"},
        11: {"Dimmer": "100"},
        12: {"Dimmer": "100"},
    }
    assert presets["4.106"].groups == {12: {"ColorRGB_R": "55", "ColorRGB_G": "35"}}


def test_the_last_store_of_a_slot_wins() -> None:
    later = [*_AUDIT, _ok("Group 12 ; Attribute 'Dimmer2' At 100"), _ok("Store Preset 1.20")]
    assert stored_presets_from_audit(later)["1.20"].groups == {12: {"Dimmer2": "100"}}


def test_cue_rows_follow_bars_and_take_numbers_only_from_the_reflect_record() -> None:
    rows = planned_cue_rows(_GRID, _ALLOCATION)
    mover = [row for row in rows if row.group_name == "MOVER-D"]
    assert [(row.bar, row.cue_number, row.sequence_number) for row in mover] == [
        (0, 1, 60),
        (4, 2, 60),
    ]
    assert mover[0].presets == ("1.20", "4.106")
    [foh] = [row for row in rows if row.group_name == "FOH"]
    assert (foh.sequence_number, foh.cue_number, foh.dimmer) == (None, None, "")


def test_a_fixture_whose_second_dimmer_no_preset_opens_is_flagged() -> None:
    # 감독 보고 「일부 장비만 동작」 — Spiider(Dimmer·Dimmer2)에 Dimmer 만 담긴 프리셋.
    rows = planned_cue_rows(_GRID, _ALLOCATION)
    caps = {
        521: _Capability(
            ("ColorRGB_B", "ColorRGB_G", "ColorRGB_R", "Dimmer", "Dimmer2", "Shutter1")
        ),
    }
    [finding] = fixture_findings(rows, stored_presets_from_audit(_AUDIT), {"MOVER-D": [521]}, caps)
    assert finding.brightness_attributes == ("Dimmer", "Dimmer2")
    assert finding.opened == ("Dimmer",)
    assert finding.not_opened == ("Dimmer2",)
    assert finding.shutter_attributes == ("Shutter1",)
    assert finding.color_mismatch is False
    text = render_markdown(rows, stored_presets_from_audit(_AUDIT), findings=[finding])
    assert "| MOVER-D | 521 | Robin Spiider | Dimmer2 |" in text
    assert LIMIT_NOTE in text


def test_a_color_preset_in_another_color_system_is_flagged() -> None:
    rows = planned_cue_rows(_GRID, _ALLOCATION)
    caps = {530: _Capability(("ColorAdd_C", "ColorAdd_M", "Dimmer"), type_name="CMY")}
    [finding] = fixture_findings(rows, stored_presets_from_audit(_AUDIT), {"MOVER-D": [530]}, caps)
    assert finding.color_mismatch is True
    assert finding.not_opened == ()


def test_nothing_is_flagged_when_every_attribute_is_opened() -> None:
    audit = [*_AUDIT[:2], _ok("Group 12 ; Attribute 'Dimmer2' At 100"), *_AUDIT[2:]]
    rows = planned_cue_rows(_GRID, _ALLOCATION)
    caps = {521: _Capability(("ColorRGB_R", "Dimmer", "Dimmer2"))}
    [finding] = fixture_findings(rows, stored_presets_from_audit(audit), {"MOVER-D": [521]}, caps)
    assert finding.not_opened == ()
    assert "모든 장비가 기종의 밝기 계열 속성을 다 받고" in render_markdown(
        rows, stored_presets_from_audit(audit), findings=[finding]
    )


class _FakePort:
    """응답기 읽기(state·props)만 흉내낸다 — exec 은 없다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls.append(("state", path))
        tree = {
            "DataPool/Sequences/60": [{"i": 1, "name": "OffCue"}, {"i": 3, "cueNo": 1}],
            "DataPool/Sequences/60/3": [{"i": 1, "name": "Part"}],
            "DataPool/PresetPools/1": [{"i": 20, "name": "DIM-100"}],
            "DataPool/PresetPools/4": [],
        }
        return {"ok": True, "children": tree.get(path, []), "truncated": False}

    def query_properties(self, path: str, names) -> dict:
        self.calls.append(("props", path))
        values = {"OWNDATAPRESENT": "true", "MEMORYFOOTPRINT": "3216", "PRESETMODE": "Selective"}
        return {"ok": True, "reads": [{"n": n, "ok": True, "v": values[n]} for n in names]}


def test_console_reads_mark_present_and_missing_cues_and_presets() -> None:
    port = _FakePort()
    cues = tool.read_console_cues(port, [60, 60], "DataPool/Sequences")
    assert cues == {(60, 1): "있음 · 데이터 있음 · 3216"}
    presets = tool.read_console_presets(port, {"1.20", "4.106"}, "DataPool/PresetPools")
    # 프리셋 모드(PRESETMODE)도 응답기로 읽혀 표에 실린다(t538 실측 "Selective"·"Universal").
    assert presets == {"1.20": "있음 'DIM-100' · 데이터 있음 · Selective", "4.106": "콘솔에 없음"}
    assert {kind for kind, _path in port.calls} <= {"state", "props"}
    text = render_markdown(planned_cue_rows(_GRID, _ALLOCATION), {}, console_cues=cues)
    assert "| MOVER-D | 60 | 2 | 4 |" in text and "콘솔에 없음" in text


def test_the_cli_reads_files_only_without_the_console_flag(tmp_path, capsys) -> None:
    store = tmp_path / "song_timeline.json"
    key = json.dumps(["LOVE ATTACK", None], ensure_ascii=False)
    timeline = {"song_title": "LOVE ATTACK", "beat_grid": _GRID}
    store.write_text(
        json.dumps({"timeline": timeline, "beat_grid_allocations": {key: _ALLOCATION}}),
        encoding="utf-8",
    )
    audit = tmp_path / "audit.jsonl"
    audit.write_text("\n".join(json.dumps(entry) for entry in _AUDIT) + "\n", encoding="utf-8")
    out = tmp_path / "table.md"
    code = tool.main(
        ["--store", str(store), "--audit", str(audit), "--listen-port", "9005", "--out", str(out)]
    )
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "| MOVER-D | 60 | 1 | 0 | 프리셋 1.20 | 4.106 |" in text
    assert "| 1.20 | DIM-100 | 12 | Dimmer=100 | 안 읽음 |" in text


def test_a_cue_whose_preset_lacks_its_group_is_marked() -> None:
    # 1차 전체 실행 — 4.106 은 「Group 10 ; …」(WASH-ALL)만 담겼는데
    # 무빙 그룹 큐가 그 번호를 불렀다.
    audit = [
        _ok("ClearAll"),
        _ok("Group 10 ; Attribute 'ColorRGB_R' At 55"),
        _ok("Store Preset 4.106"),
        _ok("ClearAll"),
        _ok("Group 12 ; Attribute 'Dimmer' At 100"),
        _ok("Store Preset 1.20"),
    ]
    rows = planned_cue_rows(_GRID, _ALLOCATION)
    text = render_markdown(rows, stored_presets_from_audit(audit))
    assert "| MOVER-D | 60 | 1 | 0 | 프리셋 1.20 | 4.106 ⚠그룹 없음 |" in text
    # 밝기 프리셋은 그룹 12 를 담았다 — 표시가 없다.
    assert "프리셋 1.20 ⚠" not in text

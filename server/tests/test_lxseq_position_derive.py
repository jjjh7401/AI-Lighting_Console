"""t220 — POS.xx 포지션 프리셋 산출 + 큐 조인.

재현 우선: 정본 큐시트의 POS 참조는 오늘 **콘솔 슬롯으로 안 풀린다**. POS 시트에
Name 열이 없어 ID -> Name -> 슬롯 조인이 설 수 없었고, 한 행이 보류되면 t207 이후
배치가 통째로 거절된다(`rows_held`). 이 파일의 `TestCueJoin` 이 그 거절을 먼저
고정하고, 산출 라벨이 풀에 있을 때 같은 시트가 계획으로 넘어가는 것을 잰다.

콘솔 접촉 0 — 상태 포트는 경로별로 답하는 가짜다.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.lxseq.cue_parser import CANONICAL_CUE_COLUMNS
from server.lxseq.position_derive import (
    DERIVED_LABEL_SUFFIX,
    POSITION_RULES,
    UnknownPositionSheetError,
    console_label_head,
    derive_position_presets,
    group_members_from_sheets,
    parse_position_sheet,
    position_preset_bundles,
    preset_id_from_console_head,
)
from server.orchestrator.tools import build_toolset

RIG = Path("src/Lighting_Designer/02_RIG팩")
POS_CSV = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-pos.csv"
PATCH_CSV = RIG / "LXSEQ_RIG_01_ShowBase_r3.patch.csv"
GROUP_CSV = RIG / "LXSEQ_RIG_01_ShowBase_r3.group.csv"
CUE_CSV = Path("src/Lighting_Designer/03_곡파일_Sugar/LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _rows():
    return parse_position_sheet(_text(POS_CSV))


def _members():
    return group_members_from_sheets(_text(PATCH_CSV), _text(GROUP_CSV))


#: 합성 리그 — 조준이 성립하는 최소 좌표. y 가 클수록 업스테이지(pointing 규약).
SYNTHETIC = dict(
    [
        (101, (-2.0, 0.0, 6.0)),
        (102, (0.0, 0.0, 6.0)),
        (103, (2.0, 0.0, 6.0)),
        (201, (-3.0, 8.0, 6.0)),
        (202, (0.0, 8.0, 6.0)),
        (203, (3.0, 8.0, 6.0)),
        (501, (-3.0, 6.0, 7.0)),
        (502, (0.0, 6.0, 7.0)),
        (503, (3.0, 6.0, 7.0)),
        (521, (-3.0, 2.0, 7.0)),
        (522, (0.0, 2.0, 7.0)),
        (523, (3.0, 2.0, 7.0)),
    ]
)

SYNTHETIC_MEMBERS = dict(
    [
        ("KEY", (101, 102, 103)),
        ("BACK", (201, 202, 203)),
        ("MOVER-U", (501, 502, 503)),
        ("MOVER-D", (521, 522, 523)),
        ("MOVER-ALL", (501, 502, 503, 521, 522, 523)),
    ]
)


class TestSheetTripwire:
    """규칙은 시트 문면을 기하로 옮긴 것이다 — 문면이 바뀌면 여기가 빨개진다."""

    def test_every_rule_matches_the_canonical_sheet_row(self):
        by_id = dict((row.preset_id, row) for row in _rows())
        for rule in POSITION_RULES:
            row = by_id[rule.preset_id]
            assert rule.stage_meaning == row.stage_meaning
            assert rule.target_group == row.target_group

    def test_every_pos_reference_in_the_canonical_cue_sheet_has_a_rule(self):
        referenced = set()
        for line in _text(CUE_CSV).splitlines()[1:]:
            cells = line.split(",")
            if len(cells) > 4 and cells[4].strip().startswith("POS."):
                referenced.add(cells[4].strip())
        assert referenced
        assert referenced <= set(rule.preset_id for rule in POSITION_RULES)

    def test_a_sheet_with_other_columns_is_refused(self):
        with pytest.raises(UnknownPositionSheetError):
            parse_position_sheet("ID,Name,Value,Purpose\nCOL.01,x,y,z\n")


class TestDerivation:
    def _derived(self, coordinates=None, members=None):
        result = derive_position_presets(
            _rows(),
            SYNTHETIC_MEMBERS if members is None else members,
            SYNTHETIC if coordinates is None else coordinates,
        )
        return result

    def test_the_six_ruled_rows_resolve_and_the_two_spares_do_not_appear(self):
        result = self._derived()
        assert [item.preset_id for item in result.derived] == [
            "POS.01",
            "POS.02",
            "POS.03",
            "POS.04",
            "POS.05",
            "POS.06",
        ]
        assert result.skipped == ()

    def test_aims_cover_the_target_group_only(self):
        by_id = dict((item.preset_id, item) for item in self._derived().derived)
        assert set(fid for fid, _p, _t in by_id["POS.01"].aims) == set(SYNTHETIC_MEMBERS["KEY"])
        assert set(fid for fid, _p, _t in by_id["POS.03"].aims) == set(SYNTHETIC_MEMBERS["BACK"])
        # KEY+BACK — 시트가 직접 쓴 합집합 표기가 펴진다.
        assert set(fid for fid, _p, _t in by_id["POS.06"].aims) == set(
            SYNTHETIC_MEMBERS["KEY"]
        ) | set(SYNTHETIC_MEMBERS["BACK"])

    def test_the_stage_frame_is_the_whole_rig_not_the_target_group(self):
        """대상 그룹만으로 기준틀을 잡으면 보컬 포인트가 FOH 브리지 앞(객석)이 된다.

        팔 1 — 리그에 더 앞선 장비가 하나 생기면 KEY 좌표가 그대로여도 POS.01 이
        움직인다. 팔 2 — 같은 자극에 대해 그룹 좌표만 보는 계산은 안 움직인다,
        즉 이 검사가 잡는 것이 실제로 기준틀 축이다.
        """
        widened = dict(SYNTHETIC)
        widened[901] = (0.0, -4.0, 6.0)
        widened_members = dict(SYNTHETIC_MEMBERS)
        base = dict((i.preset_id, i.aims) for i in self._derived().derived)
        after = dict(
            (i.preset_id, i.aims)
            for i in self._derived(coordinates=widened, members=widened_members).derived
        )
        assert base["POS.01"] != after["POS.01"]

    def test_an_unknown_group_is_skipped_with_its_reason(self):
        members = dict(SYNTHETIC_MEMBERS)
        del members["BACK"]
        result = self._derived(members=members)
        skipped = dict((item.preset_id, item.reason) for item in result.skipped)
        # POS.03(BACK) 과 POS.06(KEY+BACK) 둘 다 못 편다.
        assert skipped["POS.03"] == "unknown_group"
        assert skipped["POS.06"] == "unknown_group"
        assert "POS.01" not in skipped

    def test_a_group_without_coordinates_is_skipped_not_invented(self):
        coordinates = dict(
            (fid, position)
            for fid, position in SYNTHETIC.items()
            if fid not in SYNTHETIC_MEMBERS["BACK"]
        )
        result = self._derived(coordinates=coordinates)
        skipped = dict((item.preset_id, item.reason) for item in result.skipped)
        assert skipped["POS.03"] == "no_coordinates"
        assert (
            "좌표가 확인된 장비 0대"
            in dict((item.preset_id, item.detail) for item in result.skipped)["POS.03"]
        )

    def test_no_coordinates_at_all_yields_no_derivation(self):
        result = self._derived(coordinates=dict())
        assert result.derived == ()
        assert set(item.reason for item in result.skipped) == set(["no_coordinates"])


class TestLabelAndCommands:
    def _derived(self):
        return derive_position_presets(_rows(), SYNTHETIC_MEMBERS, SYNTHETIC).derived

    def test_the_label_leads_with_the_id_so_the_join_can_key_on_it(self):
        """t224 정정 — 콘솔이 `.` 을 지우므로 **점 없는 형태로 보낸다.**

        그래야 보낸 라벨과 되읽은 라벨이 바이트 동일해지고, 이 저장소의 유일한
        판정 수단인 되읽기 대조가 성립한다. 조인은 여전히 첫 어절에 걸린다 —
        키가 `POS.01` 에서 `POS01` 로 바뀌었을 뿐이고, 그 왕복은
        `preset_id_from_console_head` 한 자리가 책임진다.
        """
        for item in self._derived():
            head = item.label.split(" ")[0]
            assert head == console_label_head(item.preset_id)
            assert "." not in head
            assert preset_id_from_console_head(head) == item.preset_id

    def test_the_label_says_the_value_was_computed_not_recorded(self):
        """RIG 노트의 「현장 레코드 필요」는 이 카드 뒤에도 유효하다 — 라벨이
        산출과 레코드를 구별하는 유일한 자리다."""
        for item in self._derived():
            assert item.label.endswith(DERIVED_LABEL_SUFFIX)

    def test_the_slot_follows_the_id_digits(self):
        assert [item.slot for item in self._derived()] == [1, 2, 3, 4, 5, 6]

    def test_each_bundle_is_apply_then_store_then_label_then_clear(self):
        derived = self._derived()
        bundles = position_preset_bundles(derived)
        assert len(bundles) == len(derived)
        first = bundles[0]
        assert first[-1] == "ClearAll"
        assert first[-2].startswith("Label Preset 2.1 ")
        assert first[-3] == "Store Preset 2.1"
        assert all(command.startswith("Fixture ") for command in first[:-3])
        assert all("Attribute" in command for command in first[:-3])


def _obj(no: int, name: str) -> dict:
    return dict([("class", "Object"), ("i", no), ("name", name)])


def _reply(children: list) -> dict:
    return dict(
        ok=True,
        truncated=False,
        offset=0,
        node=dict(childCount=len(children)),
        children=list(children),
    )


class _FakeState:
    """경로별로 답하는 상태 포트. 콘솔 접촉 0."""

    def __init__(self, position_children: list, pool_no: int = 2) -> None:
        self.position_children = list(position_children)
        #: 풀 번호는 콘솔이 답하는 값이다 — 가짜에서도 상수 2 로 굳히지
        #: 않는다. 굳히면 「2 를 하드코딩」 뮤턴트가 살아남는다.
        self.pool_no = pool_no

    def query_state(self, path: str, offset: int = 0) -> dict:
        if path == "DataPool/PresetPools":
            return _reply([_obj(self.pool_no, "Position"), _obj(4, "Color")])
        if path == "DataPool/PresetPools/" + str(self.pool_no):
            return _reply(self.position_children)
        if path == "DataPool/Groups":
            return _reply([_obj(4, "BACK")])
        return _reply([])


class _RecordingExec:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def execute(self, command):
        self.sent.append(command)
        return type("R", (), dict(command=command, ok=True, detail="OK"))()


class _AcceptAll:
    def request_approval(self, request) -> bool:
        return True


def _cue_body() -> bytes:
    header = ",".join(CANONICAL_CUE_COLUMNS)
    row = ",".join(["Q010", "BACK", "55", "", "POS.03"] + [""] * 10 + ["", ""])
    return (header + "\n" + row + "\n").encode("utf-8")


def _run(position_children, action="preview", pool_no=2):
    exec_port = _RecordingExec()
    state = _FakeState(position_children, pool_no=pool_no)
    registry = build_toolset(
        execution_port=exec_port,
        state_port=state,
        property_port=state,
        group_approval_port=_AcceptAll(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t220",
            name="import_lxseq_cues",
            arguments=dict(
                file_content_base64=base64.b64encode(_cue_body()).decode("ascii"),
                sequence_name="t220 Sugar",
                action=action,
            ),
        )
    )
    assert execution.result.is_error is False
    return json.loads(execution.result.content), exec_port


class TestCueJoin:
    """재현 우선 — 이 클래스가 t220 의 빨강/초록이다."""

    def test_an_empty_position_pool_holds_the_row_and_refuses_the_batch(self):
        """오늘의 상태. `DataPool/PresetPools/2` childCount 0 (리드 실측)."""
        payload, _exec = _run([])
        assert payload["refusal"] == "rows_held"
        held = payload["held"]
        assert len(held) == 1
        assert "unresolved_preset" in held[0]["classes"]
        assert payload["planned_cues"] == []

    def test_a_derived_label_lets_the_same_sheet_plan(self):
        payload, _exec = _run([_obj(3, "POS.03 밴드 라인 백 · 산출값")])
        assert payload["refusal"] is None
        assert payload["held"] == []
        assert [c["cue_no"] for c in payload["planned_cues"]] == ["Q010"]
        assert payload["preset_slots_resolved"] == 1

    def test_a_label_without_the_id_does_not_resolve(self):
        """팔 2 — 조인은 라벨 첫 어절의 ID 에 걸린다. 무대 의미만 적힌 라벨은
        오늘의 이름 조인과 마찬가지로 안 풀린다."""
        payload, _exec = _run([_obj(3, "밴드 라인 백")])
        assert payload["refusal"] == "rows_held"
        assert payload["preset_slots_resolved"] == 0

    def test_the_cue_command_recalls_the_position_preset(self):
        """`row.pos` 는 명령 조립 루프에 아예 없었다 — 슬롯이 풀려도 큐가
        포지션을 부르지 않았다. 두 번째 구멍이고 이 검사가 그것을 잡는다."""
        payload, exec_port = _run([_obj(3, "POS.03 밴드 라인 백 · 산출값")], action="apply")
        assert payload["approval"] == "granted"
        assert any("At Preset 2.3" in command for command in exec_port.sent)

    def test_the_pool_number_comes_from_the_console_reply_not_a_constant(self):
        """풀 번호는 되읽은 목록에서 나온다 — 이름이 Position 인 풀의 `no`."""
        payload, exec_port = _run(
            [_obj(7, "POS.03 밴드 라인 백 · 산출값")], action="apply", pool_no=12
        )
        assert payload["refusal"] is None
        assert any("At Preset 12.7" in command for command in exec_port.sent)


class TestConsoleDropsTheDotInLabels:
    """t224 재현 — **콘솔이 저장한 이름**으로 조인이 서야 한다.

    실측(2026-09-01, onPC 2.4.2 · 응답기 1.6.2): 보낸 것과 되읽은 것이 다르다.

        보냄   Label Preset 2.1 'POS.01 보컬 센터 페이스 · 합성좌표'  → executed_ok
        되읽음 "POS01 보컬 센터 페이스 · 합성좌표"

    같은 판독 채널이 Color 풀의 `"골드 앰버 (=P1)"` 는 괄호·`=` 까지 그대로
    답하므로 판독기가 문장부호를 지우는 것이 아니다 — **콘솔이 `.` 만** 지운다.

    위 `TestCueJoin` 은 우리가 **보낸** 문자열을 그대로 풀에 심어서 이 갈래를
    못 봤다. 가짜가 콘솔보다 정직하면 그 가짜로는 이 결함을 볼 수 없다.
    """

    def test_the_name_the_console_actually_stores_resolves(self):
        payload, _exec = _run([_obj(3, "POS03 밴드 라인 백 · 합성좌표")])

        assert payload["refusal"] is None
        assert payload["held"] == []
        assert payload["preset_slots_resolved"] == 1
        assert [c["cue_no"] for c in payload["planned_cues"]] == ["Q010"]

    def test_the_dotted_form_still_resolves(self):
        # 정규화가 기존 갈래를 안 죽인다 — 시트·산출 라벨은 점을 들고 있다.
        payload, _exec = _run([_obj(3, "POS.03 밴드 라인 백 · 산출값")])

        assert payload["refusal"] is None
        assert payload["preset_slots_resolved"] == 1

    def test_the_recall_command_uses_the_console_slot(self):
        payload, exec_port = _run([_obj(3, "POS03 밴드 라인 백 · 합성좌표")], action="apply")

        assert payload["approval"] == "granted"
        assert any("At Preset 2.3" in command for command in exec_port.sent)

    def test_normalising_the_dot_does_not_widen_the_predicate(self):
        """팔 2 — 정규화가 인접한 이름까지 삼키지 않는다.

        길이·숫자 검사는 그대로다. 점을 지우는 것이 「POS 로 시작하면 뭐든」이
        되면 사람이 붙인 라벨이 다른 ID 를 삼킨다.
        """
        for label in ("POS001 밴드", "POSA1 밴드", "POS.1 밴드", "POS 03 밴드"):
            payload, _exec = _run([_obj(3, label)])
            assert payload["preset_slots_resolved"] == 0, label
            assert payload["refusal"] == "rows_held", label

"""t220 — POS.xx 포지션 프리셋 산출 + 큐 조인.

재현 우선: 정본 큐시트의 POS 참조는 오늘 **콘솔 슬롯으로 안 풀린다**. POS 시트에
Name 열이 없어 ID -> Name -> 슬롯 조인이 설 수 없었고, 한 행이 보류되면 t207 이후
그 큐가 통째로 빠진다 -- 이 파일의 시트는 큐가 Q010 하나뿐이라 성한 큐가 남지
않아 배치 거절(`rows_held`)까지 간다(입도는 t228 로 큐 단위가 됐다). 이 파일의
`TestCueJoin` 이 그 거절을 먼저
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
    CAUSE_TARGET_COINCIDES,
    CAUSE_TILT_LIMIT,
    DEGENERATE_RIG_REASON,
    DERIVED_LABEL_SUFFIX,
    POSITION_RULES,
    SYNTHETIC_LABEL_SUFFIX,
    UnknownPositionSheetError,
    _cause_of,
    _skip_for_unaimable,
    console_label_head,
    derive_position_presets,
    group_members_from_sheets,
    parse_position_sheet,
    position_preset_bundles,
    preset_id_from_console_head,
    rig_is_degenerate,
)
from server.orchestrator.tools import build_toolset
from server.spatial.pointing import (
    POINTING_TILT_LIMIT_DEGREES,
    PointingTargetCoincidesError,
    PointingTiltLimitError,
    SpatialPointingError,
)
from server.spatial.rows import SPATIAL_ROW_NOISE_SPAN

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


class TestDegenerateRig:
    """t222 — 좌표가 한 점에 접힌 리그는 **전 행**을 거절한다.

    재현: t221 이 콘솔에서 실측한 상태(86대 전부 Posx/Posy/Posz = 0.0)를 그대로
    넣으면 이 가드가 붙기 전에는 POS.01·05·06 이 초록으로 나왔고, 전 대상이
    `Pan 180 / Tilt 128.7` 한 값이었다. 눈으로는 진짜 산출과 구별되지 않는다.
    """

    #: t221 실측 상태 — 판독은 성공했고 값이 전부 원점이다.
    ORIGIN = dict((fid, (0.0, 0.0, 0.0)) for fid in SYNTHETIC)

    def _result(self, coordinates):
        return derive_position_presets(_rows(), SYNTHETIC_MEMBERS, coordinates)

    def test_a_rig_collapsed_to_one_point_derives_nothing(self):
        result = self._result(self.ORIGIN)
        assert result.derived == ()
        assert set(item.preset_id for item in result.skipped) == set(
            rule.preset_id for rule in POSITION_RULES
        )
        assert set(item.reason for item in result.skipped) == set([DEGENERATE_RIG_REASON])

    def test_the_three_rows_that_used_to_be_green_are_the_ones_this_kills(self):
        """가드가 실제로 무엇을 껐는지 이름으로 고정한다 — 셋이 아니면 빨개진다."""
        was_green = set(["POS.01", "POS.05", "POS.06"])
        skipped = dict((item.preset_id, item.reason) for item in self._result(self.ORIGIN).skipped)
        assert was_green <= set(skipped)
        assert set(skipped[preset_id] for preset_id in was_green) == set([DEGENERATE_RIG_REASON])

    def test_the_refusal_says_what_is_missing_not_just_that_it_refused(self):
        detail = self._result(self.ORIGIN).skipped[0].detail
        assert "수평 폭이 없다" in detail
        assert "x span" in detail and "y span" in detail
        assert "리그 좌표를 콘솔에 넣어야" in detail

    def test_a_rig_with_real_spread_is_untouched_by_the_guard(self):
        """팔 2 — 기존 상태에서는 이 가드가 아무것도 안 잡는다."""
        assert rig_is_degenerate(SYNTHETIC) is False
        assert len(self._result(SYNTHETIC).derived) == len(POSITION_RULES)

    def test_no_coordinates_at_all_keeps_its_own_reason(self):
        """`degenerate_rig` 는 `no_coordinates` 를 삼키지 않는다 — 다른 상태다."""
        result = self._result(dict())
        assert set(item.reason for item in result.skipped) == set(["no_coordinates"])
        assert rig_is_degenerate(dict()) is False

    def test_a_single_truss_rig_flat_in_z_is_not_degenerate(self):
        """z span 0 은 정상이다 — 세 축 전부를 요구하면 가장 흔한 리그를 거절한다."""
        bar = dict((100 + i, (-4.0 + i, 0.0, 6.0)) for i in range(9))
        assert rig_is_degenerate(bar) is False

    def test_a_vertical_only_rig_is_degenerate(self):
        """x·y 가 한 점이면 z 가 벌어져 있어도 목표점이 접힌다."""
        column = dict((100 + i, (0.0, 0.0, 4.0 + 0.5 * i)) for i in range(8))
        assert rig_is_degenerate(column) is True

    def test_a_spread_below_the_noise_span_is_degenerate(self):
        """정확히 0 만 잡으면 노이즈 폭 아래 미세 편차를 놓친다."""
        tiny = dict((100 + i, (0.01 * i, 0.0, 6.0)) for i in range(6))
        assert max(0.01 * i for i in range(6)) > 0.0
        assert rig_is_degenerate(tiny) is True

    def test_the_threshold_is_borrowed_not_restated(self):
        """임계를 여기에 다시 적으면 한쪽만 바뀌는 날 두 판정이 조용히 갈린다."""
        just_under = dict([(101, (0.0, 0.0, 6.0)), (102, (SPATIAL_ROW_NOISE_SPAN, 0.0, 6.0))])
        just_over = dict([(101, (0.0, 0.0, 6.0)), (102, (SPATIAL_ROW_NOISE_SPAN * 1.5, 0.0, 6.0))])
        assert rig_is_degenerate(just_under) is True
        assert rig_is_degenerate(just_over) is False


class TestUnaimableReasonSplit:
    """t222 — 서로 다른 원인이 **서로 다른 사유**를 낸다.

    t221 이 이 결함을 쓴 대가를 적어 뒀다: 두 원인이 바이트 동일한 사유를 내서
    리드가 「물리적 도달 불가인가」로 오진하고 레인 하나를 픽스처 기하 측정에
    보냈다. 원인이 아니었다.
    """

    def _coordinates(self):
        """수평 폭은 실값 — 퇴화 가드를 통과시킨 뒤 조준 실패만 남긴다."""
        coordinates = dict()
        for index, fid in enumerate(sorted(SYNTHETIC)):
            coordinates[fid] = (-4.0 + 1.0 * index, 0.0, 6.0)
        # y 를 전부 0 으로 깔았으니 기준틀 cy 도 0 이다.
        for fid in SYNTHETIC_MEMBERS["MOVER-U"]:  # floor_inside 목표점 = 장비 자신
            coordinates[fid] = (coordinates[fid][0], 0.0, 0.0)
        for fid in SYNTHETIC_MEMBERS["BACK"]:  # silhouette_line 목표점 = 순수 상방
            coordinates[fid] = (coordinates[fid][0], 0.0, 0.0)
        return coordinates

    def _skipped(self):
        result = derive_position_presets(_rows(), SYNTHETIC_MEMBERS, self._coordinates())
        return dict((item.preset_id, item) for item in result.skipped)

    def test_distance_zero_and_tilt_limit_do_not_share_a_reason(self):
        skipped = self._skipped()
        assert skipped["POS.04"].reason == "target_coincides"
        assert skipped["POS.03"].reason == "unaimable"
        assert skipped["POS.03"].reason != skipped["POS.04"].reason
        # 사유가 갈렸다는 것만으로는 부족하다 — 상세도 바이트 동일이면 안 된다.
        assert skipped["POS.03"].detail != skipped["POS.04"].detail

    def test_the_coincidence_reason_says_it_is_not_a_reach_problem(self):
        detail = self._skipped()["POS.04"].detail
        assert "거리 0" in detail
        assert "조준 한계와는 무관" in detail

    def test_the_tilt_reason_admits_the_ceiling_is_assumed_not_measured(self):
        """이 사유가 상한을 근거로 든다면 그 상한이 가정임을 같이 말해야 한다."""
        detail = self._skipped()["POS.03"].detail
        assert str(int(POINTING_TILT_LIMIT_DEGREES)) in detail
        assert "실측이 아니라" in detail
        assert "Robe LEDBeam 350 / MMX" in detail

    def test_the_cause_is_read_from_the_exception_type_not_its_wording(self):
        """문면 매칭이면 문구를 바꾸는 날 분류가 조용히 무너진다."""
        assert _cause_of(PointingTargetCoincidesError("문면이 무엇이든")) == (
            CAUSE_TARGET_COINCIDES
        )
        assert _cause_of(PointingTiltLimitError("문면이 무엇이든")) == CAUSE_TILT_LIMIT
        assert _cause_of(SpatialPointingError("새 갈래")) == "unclassified"

    def test_a_mixed_row_names_both_causes(self):
        reason, detail = _skip_for_unaimable(
            5, frozenset([CAUSE_TILT_LIMIT, CAUSE_TARGET_COINCIDES])
        )
        assert reason == "unaimable_mixed"
        assert "거리 0" in detail
        assert "조준 상한" in detail


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


class TestTheGuardAndTheLabelCompose:
    """t226 — 두 변경이 **한 함수 안에서** 만나는 자리.

    t222 는 가드를, t224 는 라벨 왕복을 각자 잰다. 아무도 안 잰 것은 둘이 겹치는
    지점이다: 가드를 통과한 행이 여전히 콘솔이 안 삼키는 라벨을 내는가, 그리고
    라벨 인자를 바꾸는 것으로 가드가 열리지는 않는가.

    t222 가 자기 gap 절에 「t224 와 같이 돌려 본 적 없다」를 적었다. 이 클래스가
    그 칸이다.
    """

    def _origin(self):
        return dict((fid, (0.0, 0.0, 0.0)) for fid in SYNTHETIC)

    def test_the_label_argument_does_not_open_the_gate(self):
        """꼬리를 바꿔도 퇴화 리그는 여전히 전 행을 거절한다."""
        result = derive_position_presets(
            _rows(), SYNTHETIC_MEMBERS, self._origin(), label_suffix=SYNTHETIC_LABEL_SUFFIX
        )
        assert result.derived == ()
        assert set(item.reason for item in result.skipped) == set([DEGENERATE_RIG_REASON])

    def test_a_row_that_passes_the_guard_still_leads_with_the_console_head(self):
        """팔 2 — 폭이 있는 리그에서는 6 행이 나오고 라벨이 콘솔 형태다."""
        result = derive_position_presets(
            _rows(), SYNTHETIC_MEMBERS, SYNTHETIC, label_suffix=SYNTHETIC_LABEL_SUFFIX
        )
        assert result.skipped == ()
        assert len(result.derived) == len(POSITION_RULES)
        for item in result.derived:
            head = item.label.split(" ")[0]
            assert head == console_label_head(item.preset_id)
            assert "." not in head, item.label
            assert item.label.endswith("· " + SYNTHETIC_LABEL_SUFFIX)
            assert preset_id_from_console_head(head) == item.preset_id

    def test_an_empty_suffix_is_refused_before_the_guard_can_mask_it(self):
        """빈 꼬리는 프로그래밍 오류다 — 가드의 거절이 그것을 삼키면 안 된다.

        퇴화 리그에서도 `ValueError` 가 먼저 나야 한다. 순서가 뒤집히면 잘못된
        호출이 `degenerate_rig` 로 조용히 접혀 원인이 안 보인다.
        """
        with pytest.raises(ValueError):
            derive_position_presets(_rows(), SYNTHETIC_MEMBERS, self._origin(), label_suffix="   ")
